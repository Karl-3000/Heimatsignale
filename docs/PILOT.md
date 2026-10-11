# Pilot

Grundlage: PROJEKT.md, Abschnitte 5, 18 und 19.

## Stand

Umgesetzt und automatisch getestet ist die Software für v0.1. Die folgenden
Punkte aus dem Plan lassen sich nicht programmieren und stehen vor dem
ersten fremden Nutzer aus.

### Gestaltung und Bedienung

- [ ] Entwürfe der drei Kernbildschirme in Penpot oder Figma (`design/screens.pen`), hell und dunkel, Desktop und Mobil. Der Plan sah die Abnahme vor der ersten Zeile Frontend-Code vor; die Oberfläche wurde ohne diese Abnahme gebaut und muss an ihr gemessen werden
- [ ] Netz-Prototyp unter `/dev/netz` (nur im Entwicklungsmodus) mit Testpersonen an den vier Aufgaben prüfen: eigenen Heimatort finden, Zahl der Personen verstehen, Profil öffnen und zurückfinden, zur Liste wechseln und dieselbe Stelle wiederfinden
- [ ] Messung auf dem Referenzgerät (Android-Mittelklasse, drei Jahre alt) bei 50, 150 und 300 Knoten; Canvas nur, wenn die Messung es verlangt
- [ ] Manueller Barrierefreiheits-Durchgang: Registrierung, Netz, Listenwechsel, Profil, Kontaktanfrage, Blockieren, Melden, Löschung; jeweils mit Tastatur allein, NVDA, VoiceOver, 200 % Schriftgröße, reduzierter Bewegung
- [ ] Lighthouse Performance und Accessibility je über 90 auf Mobil (Mindestschwelle, kein Nachweis)

### Betrieb

- [ ] Server, Domain, `.env`, E-Mail-Versand mit AV-Vertrag
- [ ] Kartenkacheln für Deutschland als PMTiles nach `data/tiles/`
- [ ] Ortsliste mit dem amtlichen Auszug aus GV-ISys abgleichen (`data/places/README.md`); der Gebietsstand der mitgelieferten Liste ist nicht exakt gesichert
- [ ] Backup per Cron, Sicherung außerhalb des Servers, Wiederherstellung einmal auf dem echten Server proben ([WIEDERHERSTELLUNG.md](WIEDERHERSTELLUNG.md))
- [ ] Lasttest mit dem Doppelten der Lastannahmen: 4.000 Konten, 400 gleichzeitige Sitzungen, 20 API-Anfragen pro Sekunde

### Recht und Organisation

- [ ] Datenschutzerklärung, Impressum, Nutzungsbedingungen prüfen lassen und Platzhalter füllen
- [ ] Moderationsteam: zwei benannte Bearbeiter plus Vertretung ([MODERATION.md](MODERATION.md))
- [ ] Name: Domain und Markenregister (DPMA) prüfen
- [ ] Pilotstadt wählen (100.000 bis 300.000 Einwohner, hoher Zuzug), Partner für Einladungscodes

## Definitionen im System

- **Aktives Konto**: `status = active` (wirksam aktiv oder stummgeschaltet)
  und `last_activity_at` in den letzten 30 Tagen. `last_activity_at` wird
  gesetzt, wenn jemand den Umkreis öffnet, eine Anfrage sendet oder
  beantwortet oder eine Nachricht schreibt. Der Tagesjob schreibt die Zahl
  nach `daily_stats.active_accounts`.
- **Wiederkehrendes Gespräch**: Beide Seiten haben an mindestens 3
  verschiedenen Tagen innerhalb von 14 Tagen nach Beginn geschrieben. Das
  System zählt es in dem Moment, in dem die Bedingung erfüllt ist.

## Kennzahlen

`daily_stats` hält nur Zahlen, keine IDs, keine Texte. Jedes Objekt wird am
Entstehungstag gezählt, sein Ergebnis am Tag des Eintritts und zusätzlich
beim Entstehungstag (`requests_accepted_cohort`,
`conversations_recurring_cohort`). Spätere Löschungen ändern nichts.

```sh
docker compose exec app python manage.py pilotbericht --von 2027-03-01 --bis 2027-06-14
```

`--von` ist der Beginn der Messphase, `--bis` das Ende der Nachbeobachtung.
Der Bericht wendet die Kohortenregel an: In die Quoten gehen nur Anfragen
und Gespräche ein, die mindestens 14 Tage vor `--bis` entstanden sind.

| Kennzahl | Ziel |
|----------|------|
| Aktive Konten, die mindestens eine Person aus demselben Landkreis im Umkreis sehen | über 50 % |
| Angenommene Kontaktanfragen (Kohorte) | über 40 % |
| Wiederkehrende Gespräche (Kohorte) | über 25 % |
| Meldungen "Dating/Anmache" pro 100 aktive Konten und Monat | unter 3 |
| Moderationszeit pro Woche, alle Bearbeiter zusammen | unter 4 Stunden (von Hand erfassen) |

Gegenprüfung: Wenige Meldungen können auch geringe Nutzung oder einen schwer
auffindbaren Meldeweg bedeuten. Deshalb am Ende der Messphase eine kurze,
freiwillige Befragung aller aktiven Konten.

## Phasen

- **Vorphase**: höchstens 4 Monate ab Freigabe, um 200 aktive Konten zu
  erreichen. Sonst einmalige Verlängerung um 2 Monate oder Abbruch mit
  Ursachenanalyse.
- **Messphase**: 3 Monate ab 200 aktiven Konten, plus 14 Tage Nachbeobachtung.
- Werden die Ziele verfehlt, wird nicht ausgebaut, sondern die Ursache gesucht.
