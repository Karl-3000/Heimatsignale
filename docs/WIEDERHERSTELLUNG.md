# Backup und Wiederherstellung

Grundlage: PROJEKT.md, Abschnitt 12.

## Was gesichert wird

| Was            | Wohin                 | Aufbewahrung | Womit |
|----------------|-----------------------|--------------|-------|
| Datenbank      | `backups/`            | 30 Tage      | `ops/backup.sh` (`pg_dump -Fc`) |
| Löschjournal   | `backups-journal/`    | 60 Tage      | `ops/backup.sh` (SQLite-Backup) |

Zu jedem Datenbank-Backup schreibt das Skript eine Datei `*.zeitpunkt` mit
dem Beginn des Backups. Ohne sie lässt sich der Nachlauf nicht ausführen.

Das Löschjournal liegt **außerhalb der Datenbank** auf einem eigenen Volume
(`journal`). Es enthält nur Objektart, Objekt-ID und Zeitstempel und ist nur
anfügbar. `backups/` und `backups-journal/` gehören auf getrennte Speicherorte
und zusätzlich außerhalb des Servers gesichert.

## Warum das Journal nötig ist

Ein Backup kennt die Löschungen nicht, die nach ihm passiert sind. Würde ein
Montags-Backup am Mittwoch eingespielt, wäre ein am Dienstag gelöschtes Konto
wieder da. Deshalb wird jeder Löschauftrag zuerst ins Journal geschrieben,
dann ausgeführt und danach im Journal bestätigt. Nach einer
Wiederherstellung werden alle Aufträge, die jünger sind als das Backup,
erneut ausgeführt.

Journalisiert werden: Kontolöschungen, gelöschte Nachrichten, zurückgezogene
Anfragen und die Konversationen gelöschter Konten.

## Ablauf der Wiederherstellung

```sh
ops/restore.sh backups/db-<Zeitstempel>.dump
```

Das Skript führt genau diese Schritte aus:

1. Oberfläche, Backend und Jobs anhalten.
2. Datenbank leeren und das Backup einspielen. Das Journal-Volume bleibt unberührt.
3. `manage.py wiederherstellung_nachlauf --backup-zeitpunkt <Zeitpunkt>`:
   führt alle bestätigten Löschaufträge seit dem Backup erneut aus
   (mit zehn Minuten Sicherheitsabstand nach hinten).
4. `manage.py aufraeumen`: Tagesjob.
5. Ausgabe prüfen, erst dann mit `docker compose up -d` freigeben.

### Nicht bestätigte Einträge

Meldet der Nachlauf "Nicht bestätigt, bitte prüfen", dann wurde ein
Löschauftrag eingetragen, aber seine Ausführung nicht bestätigt. Das
passiert, wenn die Datenbank den Auftrag abgelehnt hat (dann wurde nichts
gelöscht) oder wenn der Server genau zwischen Ausführung und Bestätigung
ausfiel (dann wurde gelöscht). Der Nachlauf führt solche Einträge nicht von
selbst aus. Nach Prüfung lassen sie sich mit `--auch-unbestaetigte`
nachholen. Im Zweifel gilt: Ein Löschwunsch der betroffenen Person lag vor.

## Grenzen

- Alles andere, was nach dem Backup geschah, ist nach einer
  Wiederherstellung verloren, auch Blockierungen und Meldungen aus dieser
  Zeit. Das Journal sichert nur Löschungen.
- Das Journal hält 60 Tage. Backups, die älter sind als 30 Tage, werden
  gelöscht und dürfen nicht mehr eingespielt werden.
- Geht das Journal-Volume zusammen mit der Datenbank verloren, das
  Journal-Backup aus `backups-journal/` zurückspielen, bevor der Nachlauf
  läuft. Löschungen seit diesem Journal-Backup fehlen dann.

## Wiederherstellungstest

```sh
ops/wiederherstellungstest.sh
```

Der Test spielt den Fall aus dem Plan mit echtem `pg_dump` und `pg_restore`
gegen eine Wegwerf-Datenbank durch: Ausgangslage anlegen, Backup, danach ein
Konto löschen, eine Nachricht löschen und eine Anfrage zurückziehen, Backup
einspielen, Nachlauf, Tagesjob, Prüfung. Er läuft in der CI bei jedem Push
und gehört vor dem Pilot einmal auf den echten Server, dort mit
`ops/backup.sh` und `ops/restore.sh` gegen eine Kopie.
