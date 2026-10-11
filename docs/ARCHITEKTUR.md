# Architektur

Dieses Dokument beschreibt, wie PROJEKT.md umgesetzt ist, und nennt die
Entscheidungen, die der Plan offen gelassen hat.

## Überblick

```
Browser ── HTTPS ── Caddy ──┬── /            statische SvelteKit-Oberfläche (SPA)
                            ├── /api/        Django + Django Ninja (JSON)
                            ├── /verwaltung/ Django-Admin mit Zwei-Faktor-Anmeldung
                            └── /tiles/      Kartenkacheln (PMTiles)
                    Django ──── PostgreSQL 16 + PostGIS
                    Django ──── Löschjournal (SQLite, eigenes Volume)
                    Jobs   ──── Löschdienst stündlich, Aufräumen täglich
```

Oberfläche und API liegen unter derselben Origin. Sitzungs-Cookie
(`HttpOnly`, `Secure`, `SameSite=Lax`), CSRF-Token im Header `X-CSRFToken`,
jede API-Antwort mit `Cache-Control: private, no-store`. Der API-Vertrag
steht in [API.md](API.md).

## Backend (`app/`)

| App          | Aufgabe |
|--------------|---------|
| `heimatsignale` | Einstellungen, URLs, Zustands-Middleware, Fehlertyp |
| `places`     | Ortsliste, Suche, Import, Gemeindefusionen |
| `accounts`   | Konto, Registrierung, Login-Regeln, Proof-of-Work, Nickname, Einladungscodes, Ortsanträge |
| `nearby`     | Sichtbarkeit, Umkreis, Herkunftsgruppen |
| `contacts`   | Anfragen, Versuchszähler, Konversationen, Nachrichten, Blockierungen |
| `moderation` | Meldungen mit Schnappschuss, Stummschaltung, Sperre, Einspruch |
| `deletion`   | Löschdienst, Löschjournal, Nachlauf nach Wiederherstellung |
| `adminpanel` | Admin-Bereich, Audit-Log |
| `jobs`       | Aufräumen, Tageskennzahlen, Pilotbericht |
| `api`        | Django-Ninja-Router und Schemas |

### Wirksamer Zustand

`accounts/states.py` enthält die Berechtigungstabelle aus Abschnitt 6 als
Daten. `effective_state()` rechnet bei jedem Zugriff aus `status`,
`email_verified_at`, `approval_required`, `approved_at`, `muted_until` und
der aktuellen Zeit. Die Middleware (`heimatsignale/middleware.py`) beendet
Sitzungen von Konten, die sich nicht anmelden dürfen, beschränkt Konten in
der Freigabe-Warteschlange auf die Statusseite und prüft den CSRF-Token für
jeden schreibenden API-Aufruf, auch für die Anmeldung.

Für Datenbankabfragen gilt: sichtbar ist, wer `status = 'active'` hat. Das
umfasst wirksam aktive und stummgeschaltete Konten, genau wie in der Tabelle.

### Sichtbarkeit und Radius

Es gibt eine einzige Definition (`nearby/visibility.py`), die Umkreis,
Profile, Anfragen und Meldungen verwenden: Konten mit `status = 'active'`,
deren Wohnort höchstens 20.000 m vom gespeicherten Wohnort des Betrachters
entfernt ist (`ST_DWithin` auf `geography(Point, 4326)`), ohne den
Betrachter selbst, abzüglich Blockierungen in beide Richtungen. Gezählt wird
erst auf dieser Menge. Der Client übergibt weder Suchmitte noch Radius.

`places.center` ist eine generierte Spalte aus `lat` und `lon` mit
GIST-Index. Das Projekt braucht deshalb PostGIS, aber weder GeoDjango noch GDAL.

### Sperrstrategie

| Vorgang | Umsetzung |
|---------|-----------|
| Anfrage senden | beide Nutzerdatensätze in ID-Reihenfolge `FOR NO KEY UPDATE`, dann Zustand, Sichtbarkeit, Kontingent, Versuchszähler, Einfügen; der partielle Unique-Index fängt Doppelte |
| Versuchszähler | `INSERT … ON CONFLICT DO UPDATE SET count = count + 1 WHERE count < 2 RETURNING` |
| Annahme | beide Nutzerdatensätze in ID-Reihenfolge, Anfrage `FOR UPDATE` neu lesen, Blockierung prüfen, Konversation anlegen |
| Blockieren | beide Nutzerdatensätze in ID-Reihenfolge, Konversation `FOR UPDATE`, Block einfügen, offene Anfragen auf `withdrawn`, Konversation markieren |
| Nachricht senden | Konversation `FOR UPDATE`, Zustand beider Konten und Blockierung prüfen, einfügen |
| Einladungscode | ein `UPDATE … WHERE used_count < max_uses AND valid_until > now() RETURNING id` |

Abweichung vom Plan, bewusst: Beim Senden einer Anfrage wird nicht nur der
Absender gesperrt, sondern beide Konten. Sonst könnten sich Anfrage und
Blockieren gegenseitig verklemmen. `FOR NO KEY UPDATE` statt `FOR UPDATE`
auf Nutzerdatensätzen verhindert, dass die Fremdschlüsselprüfung beim
Einfügen einer Nachricht auf eine solche Sperre wartet. Die parallelen
Tests (`app/tests/test_concurrency.py`) haben genau diese Verklemmung
gefunden, bevor sie behoben wurde.

### Löschung

Siehe [WIEDERHERSTELLUNG.md](WIEDERHERSTELLUNG.md). Schritt 1 (Grabstein,
eine Transaktion) macht das Konto sofort unsichtbar; eine
Datenbankbedingung verbietet Grabsteine mit Kontodaten. Schritt 2 läuft
direkt danach und zusätzlich stündlich und ist beliebig wiederholbar.

## Entscheidungen, die der Plan offen ließ

| Thema | Entscheidung |
|-------|--------------|
| Name | Anzeige "Heimatsignale" (wie das Repository), einstellbar über `SITE_NAME` |
| Registrierung | Ein Formular in Schritten, ein Aufruf. Die Antwort verrät nicht, ob die E-Mail schon registriert ist. Den Nickname sieht man nach der E-Mail-Bestätigung, dort einmaliges Neuwürfeln. Spätestens beim ersten Öffnen des Umkreises ist er fest |
| Standortfreigabe | Der Browser sendet auf zwei Nachkommastellen gerundete Koordinaten einmalig an `/api/places/nearest`, im Körper der Anfrage. Sie werden weder gespeichert noch protokolliert |
| Erste Nachricht | Der Text einer angenommenen Anfrage wird zur ersten Nachricht der Konversation |
| Tageskontingent | Zurückgezogene Anfragen zählen weiter zu den 5 neuen Anfragen des Kalendertags, fallen aber sofort aus den 20 offenen |
| Gegenanfrage auf eine abgelehnte Anfrage | zählt als neue Anfrage; nimmt die Gegenseite an, ist die alte erledigt |
| Entblocken | öffnet ein beendetes Gespräch nicht wieder; eine neue Anfrage ist nötig |
| Löschjournal | SQLite mit Triggern (nur anfügbar), Einträge `request` und `confirm` |
| Kennzahlen | zusätzliche Spalten `*_cohort`, die Ergebnisse dem Entstehungstag zuschreiben |
| Admin-Konten | eigene Konten ohne Orte; sie melden sich nur im Admin-Bereich an und erscheinen nie im Umkreis |
| Login-Regeln | gelten auch für die Anmeldung im Admin-Bereich; Fehlversuche werden als Hash von Konto und IP höchstens 24 Stunden gehalten |
| Proof-of-Work | Altcha-Protokoll (SHA-256), Server und Löser selbst umgesetzt, keine fremden Dienste |
| Karte ohne Kacheln | funktioniert: Knoten und Umkreis auf neutralem Hintergrund |
| Oberfläche | SvelteKit als reine SPA (`adapter-static`), weil alles hinter dem Login liegt |

## Nicht umgesetzt

- Entwürfe in Penpot oder Figma, Messung auf dem Referenzgerät, Lasttest,
  manueller Barrierefreiheits-Durchgang: siehe [PILOT.md](PILOT.md).
- Die drei Stellungnahmen (`docs/stellungnahme-codex-*.md`) lagen bei der
  Umsetzung nicht vor und fehlen im Repository.
- E-Mail-Benachrichtigungen bei neuer Anfrage oder Nachricht (v0.2).
