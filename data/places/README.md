# Quelle der Gemeindedaten (`gemeinden.csv`)

## Bezugsquelle

- Repository: <https://github.com/aproeger/german-municipalities>
- Datei: `german_municipalities.csv`
- Verwendete Commits:
  - `aa8c081ab5ce8e408d7e81d6357524d1fae7ee0e` (HEAD, 26.09.2026): liefert die Spalte `type`
    (City / Municipality / Unincorporated area)
  - `42d2a1d` (erster Commit, 25.09.2026): gleiche Datensätze, Namen noch mit amtlichen
    Zusätzen (", Stadt" usw.); maßgeblich für ARS, Namen und Koordinaten
- Die Kopien beider Dateistände sind nicht Teil dieses Repositorys; `convert.py` dokumentiert die Ableitung.

Das Repository enthält ein Skript (`main.py`), das die amtliche DESTATIS-Datei
`AuszugGV3QAktuell.xlsx` (Gemeindeverzeichnis-Informationssystem GV-ISys, Satzart 60)
nach CSV/JSON umsetzt. Die xlsx-Datei selbst liegt nicht im Repository (`.gitignore`),
die Originaldatei konnte in dieser Umgebung nicht direkt von destatis.de geladen werden.
Es handelt sich also um ein Derivat aus dritter Hand, nicht um die Originaldatei.

## Ursprung und Lizenz

- Ursprung: Statistisches Bundesamt (Destatis), Gemeindeverzeichnis-Informationssystem
  GV-ISys, <https://www.destatis.de/DE/Themen/Laender-Regionen/Regionales/Gemeindeverzeichnis/_inhalt.html>
- Lizenz der Ursprungsdaten: Datenlizenz Deutschland – Namensnennung – Version 2.0
  (<https://www.govdata.de/dl-de/by-2-0>), Quellenvermerk: © Statistisches Bundesamt (Destatis).
  Die Herkunft der Koordinaten im GV-ISys und die Lizenzangabe wurden hier nicht an der
  Originaldatei nachgeprüft. Vor dem Pilot bitte mit dem amtlichen Auszug abgleichen
  (`manage.py orte_importieren --gvisys AuszugGV....xlsx`).
- Das GitHub-Repository selbst enthält keine LICENSE-Datei. Für Skript und Aufbereitung
  des Repository-Autors ist die Lizenz damit ungeklärt; die Sachdaten sind amtliche Daten.

## Gebietsstand

Der Gebietsstand ist im Repository nicht dokumentiert und daher nicht exakt gesichert.

- Der Dateiname `AuszugGV3QAktuell.xlsx` steht nominell für den Quartalsstand 30.09.
- Die Daten enthalten Hanau als kreisfreie Stadt (AGS 06415000, 401 Kreise). Das gilt erst
  seit 01.01.2026. Der Gebietsstand liegt also zwischen 01.01.2026 und dem Commit-Datum
  25.09.2026. Ob es der Stand 30.06.2026 oder ein vorab veröffentlichter Stand 30.09.2026
  ist, ließ sich nicht klären.
- Der Stichtag der Bevölkerungszahlen (nur für den Filter verwendet) ist ebenfalls nicht
  dokumentiert; laut Repository Fortschreibung auf Basis Zensus 2022.

## Ableitung der CSV (`convert.py`)

1. Einlesen beider Dateistände, Abgleich über den 12-stelligen ARS (10.943 Datensätze der Satzart 60).
2. AGS = ARS ohne die vier Stellen des Gemeindeverbands (Land 2 + RB 1 + Kreis 2 + Gemeinde 3).
3. Entfernt wurden 194 gemeindefreie Gebiete, die als solche gekennzeichnet sind und 0 Einwohner
   haben (darunter drei Sonderschlüssel ohne Koordinate: deutsch-luxemburgisches Hoheitsgebiet,
   Küstengewässer und gemeindefreies Gebiet M-V). Die zwei bewohnten gemeindefreien Gebiete
   Lohheide (03351501) und Osterheide (03358501) bleiben enthalten.
4. `name` und `district_name`: amtlicher Name, Zusatz nach dem ersten Komma entfernt
   (", Stadt", ", Landeshauptstadt", ", Hansestadt", ", M", ", GKSt", ", kreisfreie Stadt" usw.).
   Alle vorkommenden Zusätze wurden gesichtet, es sind ausschließlich Titel und Statusbezeichnungen.
   Übrige Namensbestandteile bleiben unverändert, auch zweisprachige amtliche Namen
   (z. B. "Kamenz / Kamjenc") und Kreisnamen wie "Region Hannover" oder "Landkreis Rostock".
5. `district_ags` = erste 5 Stellen, `state_code` = erste 2 Stellen des AGS.
6. `lat`/`lon`: Breiten- und Längengrad aus dem GV-ISys (WGS84), auf 5 Nachkommastellen gerundet.
   Es ist der dort geführte Gemeindemittelpunkt, kein selbst berechneter Flächenschwerpunkt.
7. Sortierung nach AGS, Prüfung auf doppelte AGS und fehlende Koordinaten.

Ergebnis: 10.749 Gemeinden in 401 Kreisen und 16 Ländern.

## Plausibilitätsprüfung

Abgleich mit den Gemeindepolygonen VG250 des BKG (Stand 01.01.2021, aus
<https://github.com/juliuste/german-administrative-areas>, Commit `c3670de`): Für alle
10.742 gemeinsamen AGS liegt die Koordinate innerhalb des Umgebungsrechtecks des jeweiligen
Gemeindepolygons. Sieben AGS fehlen in VG250 2021, weil sie erst danach entstanden sind
(z. B. Hanau 06415000, Eisenach 16063105, Jahnatal 14522275).
