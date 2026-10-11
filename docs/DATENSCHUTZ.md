# Datenschutz: technische Umsetzung

Dieses Dokument beschreibt, was das System speichert und wann es löscht. Es
ist die Arbeitsgrundlage für die Datenschutzerklärung, ersetzt sie aber
nicht und ist keine Rechtsberatung. Grundlage: PROJEKT.md, Abschnitte 12 und 14.

## Was gespeichert wird

| Datum | Wo | Zweck | Rechtsgrundlage | Löschung |
|-------|----|-------|-----------------|----------|
| E-Mail, Passwort-Hash (Argon2id) | `users` | Login, Bestätigung, Benachrichtigung | Vertrag (Art. 6 Abs. 1 b) | sofort bei Kontolöschung |
| Geburtsjahr, Datum der Selbsterklärung | `users` | Altersspanne, Mindestalter 18 | Vertrag | sofort bei Kontolöschung |
| Heimatort, Wohnort (AGS) | `users` | Kernfunktion | Vertrag | sofort bei Kontolöschung |
| Anfragen, Nachrichten | `contact_requests`, `messages` | Kommunikation | Vertrag | durch Nutzer oder mit dem Konto |
| Versuchszähler ohne Text | `request_attempts` | höchstens zwei Anfragen pro Richtung | Vertrag | mit einem der beiden Konten |
| `last_activity_at` | `users` | Pilot-Kennzahl "aktiv" | Berechtigtes Interesse (Art. 6 Abs. 1 f) | sofort bei Kontolöschung |
| Meldungen mit Schnappschuss | `reports` | Moderation, Einspruch | Berechtigtes Interesse | 12 Monate nach Abschluss |
| Einsprüche | `appeals` | Einspruch | Berechtigtes Interesse | mit der Meldung |
| Registrierungs-IP als Hash | `registration_ips` | IP-Limit | Berechtigtes Interesse | 7 Tage, ohne Nutzerzuordnung |
| Fehlversuche beim Login als Hash von Konto und IP | `login_failures` | Login-Regeln | Berechtigtes Interesse | 24 Stunden |
| Audit-Log | `admin_audit_log` | Kontrolle der Admins | Berechtigtes Interesse | 24 Monate |
| Ortsänderungsanträge mit altem und neuem Wert | `place_change_requests` | Berichtigung (Art. 16) | Vertrag | 30 Tage nach Entscheidung |
| Löschjournal: Objektart, ID, Zeitstempel | eigene Datei | Durchsetzung von Löschungen nach Wiederherstellung | Rechtliche Pflicht (Art. 17) | 60 Tage |
| Tageskennzahlen | `daily_stats` | Pilotauswertung | Berechtigtes Interesse | unbegrenzt, ohne Personenbezug |

`login_failures` steht nicht im Plan. Die Tabelle ist nötig, um die
Login-Regeln aus Abschnitt 8 durchzusetzen, und gehört in die
Datenschutzerklärung.

## Was es nicht gibt

Geschlecht, Foto, Freitext-Profil, Hobbys, volles Geburtsdatum,
Gerätekoordinaten, Lesebestätigungen, Online-Status, Anmeldeverlauf,
Aktivitätsverlauf, Auslandsorte, Ortshistorie im Profil. Ein Test prüft,
dass das Kontomodell keines dieser Felder kennt.

- Das Geburtsdatum wird bei der Registrierung geprüft und nicht gespeichert.
- Die Standortfreigabe ist freiwillig. Der Browser rundet auf zwei
  Nachkommastellen (etwa ein Kilometer) und sendet die Koordinaten einmalig
  im Körper einer Anfrage. Der Server sucht die nächste Gemeinde und
  verwirft sie. Die Person bestätigt die Gemeinde ausdrücklich.
- Ob eine Nachricht gelesen wurde, weiß nur der eigene Browser.

## Was andere sehen

Nickname, ungefähre Altersspanne, Heimatort mit Landkreis und Bundesland,
Wohnort (Gemeinde), Mitglied seit (Monat). Nur für angemeldete Konten im
Umkreis von 20 km, nach Abzug der Blockierungen.

**Restrisiko**: Genauer Heimatort, Altersspanne und Wohnort-Gemeinde können
in kleinen Orten auf eine Person hinweisen. Die Vorschau-Seite zeigt das vor
der Registrierung. Die Herkunftsstufen sind Navigation, kein Schutz.

## Löschung

1. **Sofort**: Eintrag ins Löschjournal; das Konto wird zum Grabstein
   (`id`, `status = deleted`, `deleted_at`), alle Kontodaten sind entfernt,
   alle Sitzungen ungültig. Eine Datenbankbedingung verbietet Grabsteine,
   die noch Kontodaten tragen.
2. **Direkt danach, spätestens innerhalb von 24 Stunden**: alle
   Konversationen mit allen Nachrichten beider Seiten, alle Anfragen,
   Versuchszähler, Blockeinträge, Anträge, Einsprüche. Meldungen durch das
   Konto verlieren den Melder; offene Meldungen gegen das Konto werden mit
   "Konto gelöscht" geschlossen.
3. **Grabstein**: bleibt, solange Meldungen oder Audit-Einträge ihn
   referenzieren, längstens 24 Monate.

Backups: 30 Tage. Kontodaten sind damit spätestens 31 Tage nach der Löschung
aus allen Backups verschwunden. Meldungsbelege (bis 12 Monate) und
Audit-Einträge (bis 24 Monate) bleiben bewusst länger und sind deshalb auch
in neueren Backups enthalten. Sie enthalten keine E-Mail und keine Orte,
aber gemeldete Texte können Namen oder Orte enthalten, die jemand selbst
geschrieben hat.

## Protokolle

- Der Webserver (Caddy) schreibt IPs gekürzt (IPv4 ohne letztes Oktett),
  ohne Kopfzeilen und ohne Token aus Links, und hält das Protokoll 7 Tage.
- Das Backend protokolliert Methode, Pfad ohne Abfrageteil, Status und Dauer.
- Pseudonyme Daten (Nutzer-IDs in Audit-Log und Meldungen) sind
  personenbezogen und werden so behandelt.

## Dritte

Keine Tracking-Dienste, keine Werbe-SDKs, keine fremden Schriften oder
Skripte. Kartenkacheln kommen vom eigenen Server. Nötig sind
AV-Verträge mit dem Hoster und dem Anbieter für den E-Mail-Versand.

## Vor dem ersten externen Nutzer

- Datenschutzerklärung, Impressum und Nutzungsbedingungen (Entwürfe in der
  Oberfläche) rechtlich prüfen, Platzhalter füllen, Verantwortlichen benennen
- AV-Verträge abschließen
- Verzeichnis von Verarbeitungstätigkeiten anlegen
- prüfen, ob eine Datenschutz-Folgenabschätzung nötig ist
