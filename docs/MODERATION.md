# Moderation

Grundlage: PROJEKT.md, Abschnitte 6, 8 und 13.

## Team

Vor dem ersten fremden Nutzer: mindestens zwei benannte Bearbeiter plus eine
Vertretung, jede Person mit eigenem Konto und Zwei-Faktor-Authentifizierung.

```sh
docker compose exec app python manage.py admin_anlegen --rolle admin
docker compose exec app python manage.py admin_anlegen --rolle moderator
```

| Rolle       | Darf |
|-------------|------|
| `moderator` | Meldungen und Einsprüche bearbeiten, Konten ansehen, stummschalten |
| `admin`     | zusätzlich sperren, löschen, Orte ändern, Anträge, Freigaben, Einladungscodes, Bearbeiter verwalten |

Die Vertretung wird unter "Bearbeiter" im Feld "Vertretung für" eingetragen.

## Meldungen

Nutzer melden ein Profil, eine Kontaktanfrage oder eine Nachricht mit einem
Grund aus fester Liste: Dating/Anmache, Belästigung, Spam, Falsche Angaben,
Sonstiges.

- Beim Melden wird der betroffene Text und bei Nachrichten bis zu zehn
  vorherige Nachrichten derselben Konversation als Schnappschuss in die
  Meldung kopiert. Bearbeiter sehen nur diesen Schnappschuss, nie ein Postfach.
- Der Schnappschuss sichert nur, was beim Melden noch existiert. Hat der
  Absender die Nachricht vorher gelöscht, steht dort "Inhalt vom Absender gelöscht".
- Meldungen zum selben Ziel innerhalb von 7 Tagen bilden einen Vorfall.
- Die Liste "Meldungen" ist die Warteschlange: offene zuerst, dann nach
  Schwere (Belästigung, Dating/Anmache, Spam, Falsche Angaben, Sonstiges)
  und nach Zahl der Meldungen im Vorfall.

Ziel: Prüfung innerhalb von 72 Stunden.

### Entscheidung

| Aktion | Wirkung |
|--------|---------|
| Vorfall schließen: kein Verstoß | alle offenen Meldungen des Vorfalls werden geschlossen |
| Vorfall bestätigen und Konto sperren | Konto wird gesperrt, alle Sitzungen enden, E-Mail mit Einspruchslink |

Nutzung zur Partnersuche ist laut Nutzungsbedingungen ein Sperrgrund.

## Automatische Stummschaltung

Auslöser: Meldungen zu einem Konto aus drei verschiedenen Konten innerhalb
von 24 Stunden, jedes meldende Konto seit mindestens 7 Tagen aktiv. Wirkung:
48 Stunden keine neuen Kontaktanfragen. Das Konto bleibt sichtbar, kann
Anfragen empfangen und bestehende Gespräche führen.

Die Stummschaltung endet nach 48 Stunden von selbst. Die Prüfung kann danach
liegen und immer noch sperren oder schließen. Drei abgesprochene Konten
können jemanden also für 48 Stunden am Senden neuer Anfragen hindern, mehr
nicht. Ein IP-Vergleich findet nicht statt.

## Einspruch

- Stummgeschaltete Konten legen den Einspruch in der Oberfläche ein.
- Gesperrte Konten können sich nicht anmelden und nutzen den Link aus der E-Mail.
- Pro Vorfall gibt es einen Einspruch.
- Über den Einspruch entscheidet **eine andere Person** als die
  Erstentscheidung. Der Admin-Bereich verweigert die Entscheidung sonst.
- "Stattgeben" hebt Sperre und Stummschaltung auf.

## Freigabe-Warteschlange

Registrierungen über dem IP-Limit (mehr als 3 in 24 Stunden oder 10 in 7
Tagen von einer IP) warten nach der E-Mail-Bestätigung auf Freigabe:
"Konten", Filter "wartet auf Freigabe", älteste zuerst. Ziel: 7 Tage. Nach
14 Tagen bekommt die Person einmal eine E-Mail mit dem Stand. Konten in der
Warteschlange werden nie automatisch gelöscht. Viele Registrierungen mit
gleichem Heimat- oder Wohnort sind kein Verdachtsmerkmal.

Für Veranstaltungen: Einladungscode mit Gültigkeit und Kontingent anlegen.
Registrierungen mit Code umgehen das IP-Limit.

## Ortsänderungen

Heimatort und Wohnort ändern Nutzer nicht selbst. Sie stellen einen Antrag;
bis zur Entscheidung gilt der alte Wert. Direkte Änderungen durch Admins
verlangen eine Begründung. Im Audit-Log stehen Aktion, Konto und
Begründung, aber keine Ortswerte. Deshalb gehören auch in die Begründung
keine Ortsnamen.

## Nicknames

Nicknames entstehen aus harmlosen Wortlisten (Adjektiv, Tier oder Ding,
Zahl). Zahlen mit einschlägiger Bedeutung (etwa 18, 88) werden nie vergeben.
Das Beispiel "Grauer-Kranich-88" aus dem Plan kann deshalb nicht entstehen.

## Aufbewahrung

| Was | Frist |
|-----|-------|
| Abgeschlossene Meldungen mit Schnappschuss, dazu Einsprüche | 12 Monate nach Abschluss |
| Audit-Log | 24 Monate |
| Ortsänderungsanträge | 30 Tage nach Entscheidung |

## Nicht in v0.1

Eine Blockierung überlebt weder die Löschung noch die Neuregistrierung eines
Kontos. Das wird nach dem Pilot neu bewertet.
