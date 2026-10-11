# Heimatsignale

Zugezogene aus dem eigenen Heimatort finden. Wer in eine neue Stadt zieht,
sieht andere Zugezogene im Umkreis von 20 km um den eigenen Wohnort und
erkennt Schritt für Schritt, woher sie stammen: Bundesland, Landkreis, Ort.

Der Dienst gilt nur für Deutschland, ist **keine Dating-Plattform** und so
gebaut, dass er sich dafür möglichst schlecht eignet: kein Foto, kein
Geschlecht, kein Freitext-Profil, automatisch vergebener Nickname, Alter nur
als ungefähre Spanne, Nachrichten erst nach angenommener Kontaktanfrage.

Der vollständige Plan steht in [PROJEKT.md](PROJEKT.md). Dort heißt das
Projekt noch "Heimatnah"; der Name ist über `SITE_NAME` einstellbar.

## Aufbau

| Verzeichnis | Inhalt |
|-------------|--------|
| `app/`      | Backend: Python, Django, Django Ninja als JSON-API, PostgreSQL 16 mit PostGIS |
| `web/`      | Oberfläche: SvelteKit, TypeScript, Tailwind, D3 (Herkunftsnetz), MapLibre (Karte) |
| `data/`     | Ortsliste (`places/gemeinden.csv`) und Platz für Kartenkacheln (`tiles/`) |
| `ops/`      | Backup, Wiederherstellung, Jobs, Wiederherstellungstest |
| `docs/`     | Architektur, API-Vertrag, Datenschutz, Moderation, Wiederherstellung, Pilot |

## Schnellstart auf einem Server

Voraussetzung: Docker mit Compose, eine Domain, die auf den Server zeigt.

```sh
cp .env.example .env        # SITE_DOMAIN, SITE_URL, ALLOWED_HOSTS, SECRET_KEY, DB_PASSWORD, E-Mail eintragen
docker compose up -d --build
```

Beim ersten Start werden die Datenbank eingerichtet und die Ortsliste
(10.749 Gemeinden) importiert. Caddy holt das TLS-Zertifikat selbst.

### Admin-Konto anlegen

```sh
docker compose exec app python manage.py admin_anlegen
```

Der Befehl fragt E-Mail-Adresse und Passwort ab (mindestens 12 Zeichen),
legt das Konto mit der Rolle `admin` an und richtet die
Zwei-Faktor-Authentifizierung ein: Er zeigt einen QR-Code für eine
Authenticator-App und acht Notfallcodes. Diese Ausgabe erscheint nur
einmal. Danach meldest du dich unter `https://DEINE-DOMAIN/verwaltung/` mit
E-Mail, Passwort und dem sechsstelligen Code aus der App an.

Weitere Bearbeiter: `admin_anlegen --rolle moderator`. Der Plan verlangt vor
dem Pilot mindestens zwei benannte Bearbeiter plus Vertretung
([docs/MODERATION.md](docs/MODERATION.md)).

### Was der Admin-Bereich kann

- Konten suchen, stummschalten, sperren, entsperren, löschen
- Freigabe-Warteschlange (Registrierungen über dem IP-Limit), nach Alter sortiert
- Heimatort und Wohnort ändern (Pflichtfeld Begründung, Audit-Eintrag ohne Ortswerte)
- Ortsänderungsanträge bestätigen oder ablehnen
- Meldungen als Vorfälle bearbeiten, Einsprüche entscheiden (durch eine andere Person als die Erstentscheidung)
- Einladungscodes für Veranstaltungen erzeugen
- Tageskennzahlen und Audit-Log einsehen

### Backup

```sh
ops/backup.sh                                # täglich per Cron
ops/restore.sh backups/db-<Zeitstempel>.dump # siehe docs/WIEDERHERSTELLUNG.md
```

### Kartenkacheln

Ohne Kacheln zeigt die Karte Wohnort-Knoten und Umkreis auf neutralem
Hintergrund. Für eine Hintergrundkarte eine PMTiles-Datei von Deutschland
(Protomaps-Schema, aus OpenStreetMap) nach `data/tiles/` legen und in `.env`
`PUBLIC_TILES_URL=/tiles/<datei>.pmtiles` setzen, dann `docker compose up -d --build web`.

## Entwicklung

```sh
# Datenbank: PostgreSQL 16 mit PostGIS, Rolle und Datenbank "heimat"
cd app
pip install -r requirements.txt
export DEBUG=1
python manage.py migrate
python manage.py orte_importieren ../data/places/gemeinden.csv
python manage.py demo_daten            # künstliche Konten rund um Marl, Anmeldung demo@example.org
python manage.py runserver

cd ../web
npm install
npm run dev                            # http://localhost:5173, leitet /api an Django weiter
```

E-Mails erscheinen mit `DEBUG=1` in der Konsole des Backends.

### Tests

```sh
cd app && python manage.py test tests --settings=heimatsignale.settings_test
ops/wiederherstellungstest.sh          # Backup, Löschung, Wiederherstellung, Journal-Nachlauf mit echtem pg_dump
cd web && npm run check && npm run test:unit
```

Die Backend-Tests decken ab: Radiusgrenze, Zustandsmatrix, fremder
Nachrichtenzugriff, Blockierung in beide Richtungen einschließlich Zählern,
Anfrage-Zustände mit Ablauf, Gegenseitigkeit und Versuchszähler,
**tatsächlich parallele** Anfragen, Annahmen und Blockierungen, den
vollständigen Löschablauf einschließlich Wiederherstellung, IP-Limit,
Login-Regeln, CSRF und den Admin-Bereich mit Zwei-Faktor-Anmeldung.

## Was vor dem Pilot noch von Menschen zu tun ist

Der Code ist nicht der ganze Plan. Offen sind bewusst:

- Entwürfe in Penpot oder Figma (`design/screens.pen`) und ihre Abnahme
- Prüfung des Netzes an den Aufgaben aus Abschnitt 5 mit echten Testpersonen
- manueller Barrierefreiheits-Durchgang (Tastatur, NVDA, VoiceOver, 200 %, reduzierte Bewegung)
- Messung auf dem Referenzgerät, Lasttest mit dem Doppelten der Lastannahmen
- Datenschutzerklärung, Impressum, Nutzungsbedingungen rechtlich prüfen und Platzhalter füllen
- AV-Verträge mit Hoster und E-Mail-Anbieter
- Abgleich der Ortsliste mit dem amtlichen Auszug ([data/places/README.md](data/places/README.md))
- Moderationsteam benennen, Pilotstadt wählen

Einzelheiten: [docs/PILOT.md](docs/PILOT.md).

## Lizenz

AGPL-3.0, siehe [LICENSE](LICENSE). Ortsdaten: Statistisches Bundesamt
(Destatis), Datenlizenz Deutschland Namensnennung 2.0. Liste der
Wegwerf-Domains: disposable-email-domains (CC0).
