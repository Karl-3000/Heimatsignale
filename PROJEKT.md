# Projektplan: Zugezogene aus dem eigenen Heimatort finden

Arbeitstitel: **Heimatnah** (weitere Namensvorschläge in Abschnitt 21)
Stand: 09.10.2026, Fassung 4

Geltungsbereich: **ausschließlich Deutschland**. Heimatort und Wohnort sind
deutsche Gemeinden. Nutzer mit Heimatort außerhalb Deutschlands können sich
im Pilot nicht registrieren; das sagt die Startseite. Erweiterung auf
andere Länder: Abschnitt 15.

Die drei Stellungnahmen zu den Vorfassungen liegen unverändert unter
`docs/`; die daraus abgeleiteten Entscheidungen stehen in Abschnitt 17.

## 1. Idee

Wer in eine neue Stadt zieht, kennt dort oft niemanden. Am leichtesten
findet man Anschluss bei Menschen, die aus derselben Gegend stammen:
gleicher Dialekt, gleiche Vereine, gleiche Erinnerungen. Der Dienst zeigt
dir andere Zugezogene im Umkreis von 20 km um deinen Wohnort und lässt dich
Schritt für Schritt erkennen, woher sie kommen: erst grob nach Bundesland,
dann nach Landkreis, dann nach dem genauen Heimatort.

Der Dienst ist **keine Dating-Plattform** und so gebaut, dass er sich dafür
möglichst schlecht eignet.

## 2. Grundprinzipien (nicht verhandelbar)

| Prinzip                              | Umsetzung                                                                  |
|--------------------------------------|----------------------------------------------------------------------------|
| Nur Deutschland                      | Alle Orte aus dem amtlichen Gemeindeverzeichnis; kein Auslandsfeld         |
| Kein frei wählbarer Nickname         | Wird bei der Registrierung automatisch vergeben, nicht änderbar            |
| Kein Profilfoto                      | Es gibt kein Bildfeld, weder im Profil noch in Nachrichten                 |
| Keine Geschlechtsangabe              | Das Datenmodell kennt kein Geschlecht                                      |
| Keine Hobbys, keine Interessen       | Kein Profilfeld dafür, auch nicht als Auswahlliste                         |
| Minimale Pflichtangaben              | E-Mail, Passwort, Geburtsdatum, Heimatort, Wohnort                         |
| Heimatort ist ein genauer Ort        | Gemeinde oder Stadt, kein Landkreis, kein Bundesland                       |
| Wohnort wird selbst festgelegt       | Gemeinde oder Stadt aus derselben Ortsliste, bei der Registrierung         |
| Heimatort und Wohnort nur einmalig   | Danach ändert sie nur ein Admin auf Antrag                                 |
| Sichtradius maximal 20 km            | Serverseitig erzwungen, gemessen zwischen Gemeindemittelpunkten            |
| Herkunft stufenweise sichtbar        | Bundesland → Landkreis → Ort; der Nutzer zoomt selbst hinein               |
| Herkunft als Netz visualisiert       | Pro Wohnort ein Herkunftsnetz (Knoten und Verbindungen), nicht als Liste   |
| Hochwertige Gestaltung               | Designsystem, ruhige Typografie, Bewegung mit Zweck; kein Hobby-Look       |
| Nachrichten nur nach Kontaktanfrage  | Erste Nachricht ist eine Anfrage, weitere erst nach Annahme                |
| Blockieren jederzeit                 | Wirkt in beide Richtungen, vor jeder Zählung und Anzeige                   |
| Missbrauch wird aktiv unterbunden    | IP-Limits, Rate-Limits, Meldeprozess, Moderation ab v0.1                   |
| Fristen gelten exakt                 | Berechtigungen werden aus Zeitstempeln berechnet, nicht aus Tagesjobs      |

## 3. Orte und Hierarchie

Grundlage ist das Gemeindeverzeichnis des Statistischen Bundesamts
(DESTATIS) mit dem Amtlichen Gemeindeschlüssel (AGS) als Kennung.

```
Bundesland  →  Landkreis / kreisfreie Stadt  →  Gemeinde
```

- **Gebietsstand**: Der Pilot friert einen Gebietsstand ein (den zum
  Pilotstart aktuellen). Spätere Importe brauchen eine Regel für
  Gemeindefusionen: alte AGS werden auf die neue Gemeinde abgebildet, die
  Zuordnung steht in `place_merges`, betroffene Nutzer werden informiert.
- **Heimatort**: Der Nutzer wählt eine Gemeinde per Suchfeld mit
  Vorschlägen. Gespeichert wird der AGS. Landkreis und Bundesland werden
  abgeleitet.
- **Wohnort**: Ebenfalls eine Gemeinde. Gespeichert wird der AGS; der
  Gemeindemittelpunkt kommt aus `places`. **Gerätekoordinaten werden nie
  gespeichert.** Die Standortfreigabe des Browsers darf das Suchfeld
  vorbelegen; der Nutzer bestätigt die Gemeinde ausdrücklich.
- Großstädte sind eine Gemeinde. Stadtteile als Unterebene: nach dem Pilot.
- Die 20 km gelten zwischen Gemeindemittelpunkten. Innerhalb einer großen
  Stadt kann die tatsächliche Entfernung größer sein, Nachbarn jenseits der
  Grenze können herausfallen. Das steht als Hinweis direkt an der Karte.

## 4. Nutzerfluss

### Vor der Registrierung
Eine Vorschau-Seite zeigt, was andere von einem sehen werden:

```
Was andere Zugezogene im Umkreis von dir sehen:
  Stiller-Leuchtturm-412 · etwa 25–34 · aus Sonthofen (Oberallgäu, Bayern)
  wohnt in Musterstadt
Was niemand sieht: E-Mail, Geburtsdatum, genaue Adresse, Online-Status.
```

### Registrierung
1. E-Mail und Passwort eingeben, Bestätigungslink per E-Mail. Ohne
   Bestätigung wird das Konto nach 48 Stunden gelöscht.
2. Geburtsdatum eingeben. Mindestalter 18. **Gespeichert wird nur das
   Geburtsjahr** und der Vermerk "Volljährigkeit selbst erklärt am …".
   Angezeigt wird eine Altersspanne, die aus dem Kalenderjahr berechnet
   wird (Alter = laufendes Jahr minus Geburtsjahr) und deshalb an den
   Grenzen um ein Jahr abweichen kann. Sie heißt darum überall "etwa
   25–34". Die Angabe ist eine Selbstauskunft, keine Verifikation.
3. Heimatort wählen (Suchfeld, deutsche Gemeinde).
4. Wohnort wählen (Suchfeld, deutsche Gemeinde). Optional: Standortfreigabe
   zum Vorbelegen.
5. Zusammenfassung mit beiden Orten und dem Hinweis, dass sie danach nur
   über einen Admin geändert werden können.
6. Nickname wird erzeugt, z. B. `Stiller-Leuchtturm-412`. Einmaliges
   Neuwürfeln erlaubt, danach fest.
7. Falls die Registrierung das IP-Limit überschreitet (Abschnitt 8), wartet
   das Konto zusätzlich auf Admin-Freigabe. Beide Freigaben (E-Mail, Admin)
   sind getrennte Merkmale; aktiv wird das Konto erst, wenn alle
   notwendigen vorliegen.

### Hauptansicht: Umkreis mit Herkunftsnetzen
- Karte mit dem eigenen Wohnort in der Mitte, Zoom maximal bis 20 km
  Radius. Kleinere Ausschnitte erlaubt, größere nicht.
- Andere Zugezogene erscheinen **nicht als Einzelpunkte**. Jede
  Wohnort-Gemeinde im Umkreis ist ein Knoten, und um diesen Knoten liegt
  bereits in der ersten Ansicht ein **grobes Herkunftsnetz**: Verbindungen
  vom Wohnort zu den Bundesländern, aus denen die dortigen Zugezogenen
  stammen. Linienstärke und Knotengröße entsprechen der Anzahl.
- Klick auf einen Wohnort-Knoten vergrößert sein Netz; "Alle im Umkreis"
  fasst alle Wohnorte zu einem Netz zusammen.

### Herkunftsnetz: stufenweises Hineinzoomen
Das Netz hat drei Stufen, die der Nutzer selbst öffnet. Jeder Knoten lässt
sich aufklappen, die nächste Stufe wächst aus ihm heraus:

```
Stufe 1  (Wohnort) ──── Bayern (12)
                   ──── Nordrhein-Westfalen (7)
                   ──── Sachsen (3)

Stufe 2  Bayern ──── Oberallgäu (4)
                ──── Rosenheim (3)

Stufe 3  Oberallgäu ──── Sonthofen (2) ──── Stiller-Leuchtturm-412 · etwa 25–34
                                       ──── Grauer-Kranich-88 · etwa 35–44
                    ──── Immenstadt (1)
```

Knoten, die zum eigenen Heimatort, Landkreis oder Bundesland gehören, sind
hervorgehoben. Sortierung nach Nähe zum eigenen Heimatort oder nach
Anzahl. Kein Altersfilter. Zu jedem Netz gibt es eine gleichwertige
Listenansicht (Abschnitt 5).

Die Stufen sind Navigation, kein Schutz: Jeder angemeldete Nutzer kann bis
zum Ort durchklicken. Das sagt die Vorschau-Seite vorab.

### Profil eines anderen Nutzers
Zeigt: Nickname, Altersspanne, Heimatort mit Landkreis und Bundesland,
Wohnort (Gemeinde), Mitglied seit. Keine Entfernung in Metern, kein
Online-Status, keine Lesebestätigungen.

Aktionen: Kontaktanfrage senden, blockieren, melden.

### Kontaktanfrage und Nachrichten
Vollständiger Ablauf in Abschnitt 7. Kurz: Anfrage mit Text, Empfänger
nimmt an, lehnt ab oder blockiert; nach Annahme 1:1-Konversation, reiner
Text.

### Später nochmal umziehen oder falscher Heimatort
Antrag im Profil ("Ich bin umgezogen" bzw. "Mein Heimatort ist falsch"),
neue Gemeinde wählen, Admin bestätigt oder lehnt ab. Bis zur Entscheidung
bleibt der alte Wert aktiv.

## 5. Oberfläche und Gestaltung

Der Anspruch: Der Dienst soll aussehen und sich anfühlen wie ein
professionelles Produkt, nicht wie ein Vereinsprojekt. Das ist keine
Verzierung am Ende, sondern eine Anforderung ab dem ersten Bildschirm.

### Das Herkunftsnetz

Das Herkunftsnetz ist das zentrale Bild des Dienstes. Es wird als
**Knoten-Kanten-Graph** gezeichnet, in der Anmutung eines neuronalen
Netzes: ein Wohnort-Knoten in der Mitte, Herkunftsknoten darum, Kanten
dazwischen, deren Stärke der Anzahl entspricht.

| Element          | Festlegung                                                                                   |
|------------------|----------------------------------------------------------------------------------------------|
| Bedeutung        | Eine Kante bedeutet genau: "N Personen, die in [Wohnort] leben, stammen aus [Herkunft]". Die Position der Herkunftsknoten ist **schematisch**, nicht geografisch. Das steht in der Legende |
| Layout           | Radial um den Wohnort: Bundesländer im ersten Ring, Landkreise im zweiten, Orte im dritten. Kräftebasiert (d3-force) mit radialer Bindung |
| Stabilität       | Die Simulation läuft nach jeder Änderung bis zur Ruhe (alpha → 0) und wird dann eingefroren. Beim Aufklappen behalten bestehende Knoten ihre Position; nur neue Knoten werden platziert. Klickziele wandern nicht |
| Knoten           | Kreise, Fläche proportional zur Anzahl (nicht Radius). Eigene Herkunft hervorgehoben |
| Kanten           | Gekrümmte Linien, Stärke nach Anzahl, Deckkraft reduziert; Hover oder Fokus auf einen Knoten hebt seinen Pfad bis zur Mitte hervor |
| Aufklappen       | Klick oder Enter auf einen Knoten: Kinder wachsen mit einer 300-ms-Animation aus ihm heraus; nochmal klappt zu. Eine Teilbaum-Ebene pro Aktion |
| Beschriftung     | Immer lesbar, nie überlappend; bei Platzmangel Kurzform ("NRW"). Der volle Name ist per Tipp, Tastaturfokus und in der Listenansicht erreichbar, nicht nur per Hover |
| Auf der Karte    | Jeder Wohnort-Knoten trägt sein Stufe-1-Netz als Miniatur: die bis zu 5 größten Bundesländer **plus immer das eigene**, Rest als "+3". Beim Hineinzoomen werden Miniaturen größer, beim Herauszoomen schrumpfen sie auf Knoten mit Zahl |
| Überlagerung     | Liegen zwei Wohnort-Knoten in der aktuellen Zoomstufe näher als 48 px, werden sie zu einem Sammelknoten mit Summe zusammengefasst, der sich beim Hineinzoomen wieder trennt. Miniaturen werden nie übereinander gezeichnet |
| Rendering        | Zuerst nur SVG. Auf einem festgelegten Referenzgerät (Android-Mittelklasse, 3 Jahre alt) wird bei 50, 150 und 300 Knoten gemessen. Canvas wird nur eingeführt, wenn die Messung es verlangt; ein zweiter Darstellungsweg ist Aufwand, keine Vorsorge |
| Zurückhaltung    | Keine Partikel, kein Dauerflimmern, kein Glow um alles. Bewegung nur bei Nutzeraktion |
| Listenansicht    | Gleichwertiger Baum mit identischen Daten, sichtbarer Umschalter. Beim Wechsel bleiben Auswahl, aufgeklappte Stufe und Tastaturfokus erhalten. Pflicht unter 640 px Breite und für Screenreader |

### Prüfung des Netzes vor der Abnahme

Der Netz-Prototyp wird mit künstlichen Daten gebaut und an **Aufgaben**
geprüft, nicht nur an Knotenzahlen:

1. Den eigenen Heimatort im Netz finden.
2. Verstehen, wie viele passende Personen es gibt.
3. Ein Profil öffnen, zurückgehen, die Orientierung behalten.
4. Zur Listenansicht wechseln und dieselbe Stelle wiederfinden.

Testdaten decken ab: 5, 50 und 300 Knoten; lange Ortsnamen
("Hohenstein-Ernstthal", "Garmisch-Partenkirchen"); sehr ungleiche Gruppen
(1 neben 80); drei dicht benachbarte Wohnorte; eigene Herkunft außerhalb
der fünf größten Gruppen; leerer Umkreis.

Die Abnahme der statischen Entwürfe lässt Änderungen aus dem Bedienprototyp
ausdrücklich zu.

### Designsystem

- **Tokens zuerst**: Farben, Abstände, Radien, Schatten, Typografie als
  Variablen, aus denen alles abgeleitet wird.
- **Typografie**: eine variable Sans-Serif mit guter Zahlenlesbarkeit
  (z. B. Inter oder Geist), zwei Gewichte, klare Größenskala.
- **Farbe**: neutrales Grundsystem (warmes Grau statt reinem Weiß und
  Schwarz), eine Akzentfarbe für Interaktion, eine zweite für die eigene
  Herkunft im Netz. Bundesländer bekommen keine eigenen Farben. Helles und
  dunkles Thema von Anfang an, Kontrast mindestens WCAG AA.
- **Karte**: eigener, gedämpfter Kartenstil (wenig Farbe, keine
  POI-Symbole), damit das Netz der Vordergrund ist.
- **Bewegung**: 150 bis 300 ms, standardisierte Kurven, respektiert
  `prefers-reduced-motion`.
- **Komponenten**: kleine, konsistente Bibliothek (Button, Eingabe, Dialog,
  Karte, Badge, Tabs, Toast). Ein Icon-Set (z. B. Lucide), eine Strichstärke.
- **Leere Zustände**: Ein leerer Umkreis zeigt eine gestaltete Erklärung
  ("Noch niemand aus deiner Gegend in 20 km, du bist die erste Person aus
  dem Oberallgäu hier"), keine leere Karte.
- **Texte**: knapp, ohne Ausrufezeichen, ohne Emojis, konsistent Du.

### Barrierefreiheit

- Lighthouse Performance und Accessibility je über 90 auf Mobil sind eine
  **Mindestschwelle**, kein Nachweis.
- Vor dem Pilot ein vollständiger manueller Durchgang: Registrierung,
  Netz, Listenwechsel, Profil, Kontaktanfrage, Blockieren, Melden, Löschung.
  Jeweils mit Tastatur allein, mit Screenreader (NVDA und VoiceOver), mit
  200 % Schriftgröße und mit reduzierter Bewegung.
- Alle Dialoge haben Fokusfalle und Escape; alle Aktionen sind per Tastatur
  erreichbar; keine Information nur über Farbe.

### Vorgehen
1. Entwurf der drei Kernbildschirme (Umkreis mit Netzen, aufgeklapptes
   Netz, Konversation) in Penpot oder Figma, hell und dunkel, Desktop und
   Mobil. Abnahme vor der ersten Zeile Frontend-Code, mit dem Vorbehalt
   oben.
2. Netz-Prototyp mit künstlichen Daten, geprüft nach dem Aufgabenkatalog.
   Kann parallel zur Backend-Arbeit beginnen.
3. Danach ein vollständiger senkrechter Durchstich: Registrierung →
   Herkunftsnetz → Kontaktanfrage → Blockierung → Meldung → Löschung. Erst
   daran wird der Pilotaufwand geschätzt.

## 6. Kontostatus und Berechtigungen

### Merkmale am Konto
- `status`: `pending` | `active` | `suspended` | `deleted`
- `email_verified_at`: E-Mail bestätigt
- `approval_required`, `approved_at`: Admin-Freigabe nötig und erteilt
- `muted_until`: Stummschaltung bis Zeitpunkt

Der **wirksame Zustand** wird bei jedem Zugriff aus diesen Merkmalen und
der aktuellen Zeit berechnet, nie aus einem Tagesjob:

| Wirksamer Zustand      | Bedingung                                                        |
|------------------------|------------------------------------------------------------------|
| unbestätigt            | `status=pending`, `email_verified_at` leer                       |
| wartet auf Freigabe    | `status=pending`, E-Mail bestätigt, `approval_required`, `approved_at` leer |
| aktiv                  | `status=active`, `muted_until` leer oder in der Vergangenheit    |
| stummgeschaltet        | `status=active`, `muted_until` in der Zukunft                    |
| gesperrt               | `status=suspended`                                               |
| gelöscht               | `status=deleted`                                                 |

`status` wechselt von `pending` auf `active`, sobald alle nötigen Freigaben
vorliegen (bei Registrierung ohne Admin-Freigabe: mit der E-Mail-Bestätigung).

### Berechtigungen

| Zustand             | Login | Sichtbar für andere | Zählt in Gruppen | Bestehende Gespräche | Neue Anfragen senden | Anfragen empfangen | Einspruch |
|---------------------|-------|---------------------|------------------|----------------------|----------------------|--------------------|-----------|
| unbestätigt         | nein  | nein                | nein             | –                    | nein                 | nein               | –         |
| wartet auf Freigabe | ja (nur Statusseite) | nein     | nein             | –                    | nein                 | nein               | –         |
| aktiv               | ja    | ja                  | ja               | ja                   | ja                   | ja                 | –         |
| stummgeschaltet     | ja    | ja                  | ja               | ja                   | **nein**             | ja                 | ja        |
| gesperrt            | nein  | nein                | nein             | nein                 | nein                 | nein               | ja (per E-Mail) |
| gelöscht            | nein  | nein                | nein             | gelöscht             | nein                 | nein               | –         |

### Fristen
- Unbestätigte Konten: Löschung 48 Stunden nach Registrierung.
- Konten in der Freigabe-Warteschlange werden **nicht** automatisch
  gelöscht. Ziel für die Admin-Entscheidung: 7 Tage. Nach 14 Tagen ohne
  Entscheidung bekommt der Nutzer eine E-Mail mit Stand; das Konto bleibt
  in der Warteschlange, sortiert nach Alter.

### Blockierungen
Blockierungen gelten unabhängig vom Zustand: Blockierte und Blockierende
sehen sich gegenseitig nicht, werden gegenseitig nicht gezählt und können
sich nicht anschreiben. **Die Filterung passiert vor jeder Aggregation.**
Das verhindert, dass ausgeblendete Personen mitgezählt werden; es
garantiert nicht, dass eine Blockierung unbemerkt bleibt. In kleinen
Gruppen kann ein verschwundenes Profil auffallen. Das lässt sich in keinem
System mit sichtbaren Zählern vermeiden, und der Plan verspricht es nicht.

Technisch: Ein Middleware-Check nach dem Django-Login berechnet den
wirksamen Zustand und erzwingt die Tabelle. Django kennt diese Zustände
nicht von selbst.

## 7. Kontaktanfragen: Zustände und Regeln

### Zustände
```
open ──(Annahme)──> accepted  →  Konversation wird angelegt
open ──(Ablehnung)──> declined  (für den Absender weiterhin "offen")
open | declined ──(Absender zieht zurück)──> withdrawn
open | declined ──(expires_at erreicht)──> expired
```

- **Ablaufzeit**: `expires_at = created_at + 30 Tage`. Ob eine Anfrage
  abgelaufen ist, wird bei jedem Zugriff aus `expires_at` berechnet; der
  Tagesjob setzt nur nachträglich den Status und löscht. Der Absender sieht
  `open` und `declined` gleichermaßen als "offen", danach "abgelaufen".
  Weder Anzeige noch Kontingent verraten eine Ablehnung.
- **Kontingent**: höchstens 5 neue Anfragen pro Kalendertag und höchstens
  20 Anfragen mit Status `open` oder `declined` und `expires_at` in der
  Zukunft. Zurückgezogene fallen **sofort** aus dem Kontingent.
- **Zurückziehen**: jederzeit möglich, solange `open` oder `declined`. Der
  Empfänger sieht die Anfrage dann nicht mehr.
- **Erneut anfragen**: pro Richtung höchstens zwei Versuche insgesamt. Der
  Zähler steht in `request_attempts(from_user, to_user, count)` ohne Text
  und überlebt die Löschung der Anfragen. Nach dem zweiten Versuch ist
  diese Richtung zu; die Gegenseite kann weiterhin anfragen.
- **Gegenseitige Anfragen**: Stellt B eine Anfrage an A, während A→B
  `open` ist, gelten beide als angenommen und die Konversation wird
  angelegt.
- **Höchstens eine aktive Anfrage pro Richtung**: erzwungen durch einen
  partiellen Unique-Index
  `UNIQUE (from_user, to_user) WHERE status IN ('open','declined')`.
- **Inhalt**: eine Textnachricht, höchstens 500 Zeichen, keine Links.

### Konversation
- Nur nach `accepted`. Reiner Text, keine Bilder, keine Anhänge.
- Links erst nach 10 ausgetauschten Nachrichten.
- Höchstens 60 Nachrichten pro Stunde pro Konversation.
- Eigene Nachrichten kann man löschen; sie verschwinden für beide Seiten
  und werden ins Löschjournal eingetragen (Abschnitt 12).
- Keine Lesebestätigung, kein Online-Status. Lesestatus nur im Client.
- Blockieren beendet die Konversation sofort für beide. Melden bleibt
  möglich, weil die Meldung einen Schnappschuss mitnimmt (Abschnitt 8).

### Gleichzeitigkeit
Eine Transaktion mit erneutem Lesen reicht unter der Standard-Isolation
(Read Committed) nicht. Festgelegte Strategie:

| Vorgang                 | Absicherung                                                                                   |
|-------------------------|-----------------------------------------------------------------------------------------------|
| Anfrage senden          | `SELECT … FOR UPDATE` auf dem Datensatz des Absenders, dann Kontingent zählen und einfügen. Partieller Unique-Index fängt Doppelte |
| Versuchszähler          | `INSERT … ON CONFLICT DO UPDATE SET count = count + 1 WHERE count < 2`; schlägt die Zeile fehl, ist die Richtung zu |
| Annahme                 | Beide Nutzerdatensätze in ID-Reihenfolge `FOR UPDATE` sperren, Blockierung prüfen, Anfrage auf `accepted`, Konversation einfügen (Unique-Constraint) |
| Blockieren              | Beide Nutzerdatensätze in ID-Reihenfolge `FOR UPDATE` sperren, Block einfügen, offene Anfragen zwischen beiden auf `withdrawn`, Konversation markieren |
| Nachricht senden        | Konversationsdatensatz `FOR UPDATE` sperren, Blockierung und Status beider Konten prüfen, einfügen. Blockieren sperrt denselben Datensatz, also serialisiert |
| Einladungscode          | `UPDATE invite_codes SET used_count = used_count + 1 WHERE id = ? AND used_count < max_uses AND valid_until > now() RETURNING id`; keine Zeile zurück bedeutet verbraucht |

Die Tests dafür enthalten **tatsächlich parallele** Aktionen (zwei
Transaktionen, die gleichzeitig denselben Kontingentplatz oder dieselbe
Annahme versuchen), nicht nur sequentielle Abläufe.

## 8. Schutz vor Missbrauch

### Registrierung
- **IP-Limit, abgestuft**: höchstens 3 Registrierungen pro IP in 24
  Stunden und 10 in 7 Tagen. Darüber kein harter Block, sondern schwererer
  Proof-of-Work und `approval_required = true`; das Konto wartet auf
  Admin-Freigabe (Abschnitt 6).
- **Einladungscodes** für Veranstaltungen: Ein Admin erzeugt einen Code
  mit Gültigkeit und Kontingent; Registrierungen mit Code umgehen das
  IP-Limit und werden dem Code zugeordnet. Verbrauch atomar (Abschnitt 7).
- Eine E-Mail-Adresse, ein Konto. Wegwerf-Domains werden abgelehnt.
- Proof-of-Work vor dem Absenden (Altcha, selbst gehostet).
- Passwort mindestens 12 Zeichen, Argon2id.
- Häufungen gleicher Heimat- und Wohnorte sind **kein** Verdachtsmerkmal.

### Login
- Pro Konto und IP: nach 5 Fehlversuchen 15 Minuten Sperre.
- Pro Konto über alle IPs: nach 20 Fehlversuchen in einer Stunde
  zusätzlicher Proof-of-Work, **keine** harte Sperre.
- Pro IP: nach 50 Fehlversuchen in einer Stunde eine Stunde Sperre.

### Abgreifen von Daten
- Alles nur hinter Login. Keine öffentliche Seite zeigt Nutzer.
- Suchmitte ist immer der gespeicherte Wohnort. Der Client übergibt keine
  Koordinaten.
- Umkreis- und Herkunftsabfragen: höchstens 120 pro Stunde.
- Keine Massen-Endpunkte, kein Export, feste Seitengrößen.
- Nutzerabhängige API-Antworten: `Cache-Control: private, no-store`; kein
  CDN-Caching der API.

### Melden
- Ziel einer Meldung ist ein Profil, eine Kontaktanfrage oder eine
  Nachricht (`target_type`, `target_id`). Beim Melden wird der betroffene
  Text und bei Nachrichten bis zu 10 vorherige Nachrichten derselben
  Konversation als **Schnappschuss in die Meldung kopiert**. Moderatoren
  sehen nie das ganze Postfach.
- **Grenze des Schnappschusses**: Er sichert nur, was beim Melden noch
  existiert. Hat der Absender seine Nachricht vorher gelöscht, enthält die
  Meldung nur den Hinweis "Inhalt vom Absender gelöscht" und die
  Beschreibung des Meldenden. Das steht im Meldeformular.
- Grund aus fester Liste: "Dating/Anmache", "Belästigung", "Spam",
  "Falsche Angaben", "Sonstiges".
- Meldungen zum selben Ziel innerhalb von 7 Tagen erhalten denselben
  `incident_key` und erscheinen als ein Vorfall.
- Melden ist auch nach Blockieren möglich (aus der Blockliste heraus).

### Stummschaltung (automatisch, begrenzt)
- Auslöser: Meldungen zu einem Nutzer aus **drei verschiedenen Konten**
  innerhalb von 24 Stunden, wobei jedes meldende Konto seit mindestens
  7 Tagen aktiv ist. Ein IP-Vergleich findet nicht statt; die dafür
  nötigen Daten werden absichtlich nicht so lange gespeichert.
- Wirkung: `muted_until = now() + 48 Stunden`. Gilt ab diesem Moment,
  berechnet bei jedem Zugriff.
- **Endet nach 48 Stunden von selbst.** Die Admin-Prüfung (Ziel 72
  Stunden) kann danach liegen; das ist Absicht. Die Prüfung kann dann
  immer noch sperren oder den Vorfall schließen. Eine abgesprochene
  Meldung trifft damit niemanden dauerhaft.
- Ein bestätigter Vorfall führt zu `suspended`; dagegen gibt es einmal
  Einspruch an eine zweite Admin-Person.
- Restrisiko, akzeptiert: Drei abgesprochene Konten können einen Nutzer
  für 48 Stunden am Senden neuer Anfragen hindern. Mehr nicht.

### Moderationsteam
- Mindestens zwei benannte Bearbeiter plus eine Vertretung.
- Ziel: Prüfung innerhalb von 72 Stunden. Warteschlange nach Schwere und
  Häufung sortiert.

### Nutzungsbedingungen
Zweck des Dienstes ist klar benannt; Nutzung zur Partnersuche ist ein
Sperrgrund.

### Offen, nicht in v0.1
Kontenübergreifender Schutz (Blockierung überlebt Kontolöschung oder
Neuregistrierung) ist **nicht** vorgesehen. Wird nach dem Pilot neu
bewertet.

## 9. Anti-Dating-Maßnahmen

Keine einzelne Maßnahme verhindert eine Zweckentfremdung; die Wirkung
ergibt sich aus der Summe:

- Kein Foto, kein Geschlecht, kein Freitext, keine Hobbys.
- Keine Likes, kein Swipen, keine Favoriten, kein Online-Status, keine
  Lesebestätigungen.
- Automatischer Nickname: keine Bühne zur Selbstdarstellung.
- Alter nur als ungefähre Spanne, kein Altersfilter.
- Kontaktanfrage mit Annahme statt freier Erstnachricht.
- Enge Kontingente und ein eigener Meldegrund "Dating/Anmache".
- Keine Entfernungsangabe unterhalb der Gemeinde.

## 10. Datenmodell

```
places                        (Import DESTATIS, read-only, fester Gebietsstand)
  ags            text PK
  name           text
  district_ags   text
  district_name  text
  state_code     text
  center         geography(Point, 4326)
  INDEX GIST (center)

place_merges
  old_ags, new_ags, valid_from

users
  id                    uuid PK
  email                 citext UNIQUE NULL
  password_hash         text NULL
  nickname              text UNIQUE NULL
  birth_year            smallint NULL
  adult_self_declared_at date NULL
  home_ags              text FK places NULL
  residence_ags         text FK places NULL
  status                enum: pending | active | suspended | deleted
  email_verified_at     timestamptz NULL
  approval_required     boolean default false
  approved_at           timestamptz NULL
  muted_until           timestamptz NULL
  last_activity_at      timestamptz NULL     (nur ein Zeitstempel, kein Verlauf)
  created_at, deleted_at
  -- Grabstein nach Löschung: id, status='deleted', deleted_at; alles andere NULL

contact_requests
  id, from_user FK users, to_user FK users
  body        text (<= 500)
  status      enum: open | accepted | declined | withdrawn | expired
  created_at, expires_at, decided_at
  UNIQUE (from_user, to_user) WHERE status IN ('open','declined')   -- partiell

request_attempts
  from_user, to_user, count smallint     PK (from_user, to_user)
  -- bleibt bis Löschung eines Beteiligten; kein Text

conversations
  id, user_a, user_b (user_a < user_b), created_at, blocked boolean
  UNIQUE (user_a, user_b)

messages
  id, conversation_id FK ON DELETE CASCADE, sender_id FK users, body, created_at

blocks
  blocker_id, blocked_id, created_at      PK (blocker_id, blocked_id)

reports
  id, reporter_id FK users NULL
  reported_user_id FK users
  target_type enum: profile | request | message
  target_id   uuid NULL
  snapshot    jsonb
  reason enum, note text, incident_key text, created_at
  resolved_at, resolved_by, outcome

appeals
  id, report_id, user_id, text, created_at, decided_at, decided_by, outcome

place_change_requests
  id, user_id FK, field enum: home | residence, new_ags FK places
  created_at, decided_at, decided_by, decision

admin_audit_log
  id, admin_id, action, target_user_id, reason, created_at
  -- enthält keine Ortswerte, keine E-Mails, keine Texte;
  -- Admin- und Nutzerreferenzen sind pseudonyme Personendaten

registration_ips
  ip_hash, created_at, invite_code_id NULL   (7 Tage; keine Nutzerzuordnung)

invite_codes
  id, code, label, valid_until, max_uses, used_count, created_by

moderators
  user_id, role enum: moderator | admin, deputy_of NULL

daily_stats                   (aggregierte Pilot-Kennzahlen, keine Texte, keine IDs)
  day, registrations, active_accounts, requests_sent, requests_accepted,
  conversations_started, conversations_recurring, reports_dating, deletions
```

**Löschjournal (außerhalb dieser Datenbank)**, siehe Abschnitt 12:
```
deletion_journal              (append-only, eigener Speicherort)
  object_type enum: account | message | conversation | request
  object_id uuid, requested_at timestamptz
  -- 60 Tage, länger als die Backup-Aufbewahrung
```

Die `ON DELETE`-Regeln an Fremdschlüsseln sind Sicherheitsnetz bei echten
Löschungen. **Sie sind nicht der Mechanismus der Kontolöschung**, weil der
Grabstein per UPDATE entsteht und keine Kaskade auslöst. Den Ablauf führt
der Löschdienst ausdrücklich aus.

Bewusst nicht enthalten: Geschlecht, Foto, Freitext-Profil, Hobbys,
Gerätekoordinaten, volles Geburtsdatum, Lesebestätigungen, Online-Status,
Auslandsorte, Ortshistorie im Profil, Aktivitätsverlauf.

## 11. Kernregeln im Backend

- **Radius**: `ST_DWithin(me.center, other.center, 20000)` auf
  `geography(Point, 4326)`. Gemessen zwischen Gemeindemittelpunkten.
- **Sichtbarkeit**: Grundmenge sind Nutzer im wirksamen Zustand aktiv oder
  stummgeschaltet im Radius, abzüglich Blockierungen in beide Richtungen.
  Erst auf dieser Menge werden Gruppen gezählt.
- **Herkunftsansicht**: Der Server liefert Gruppen auf der angefragten Stufe
  (Bundesland, Landkreis, Ort). Nutzerdaten erst auf der Ortsstufe.
- **Zeitstempel statt Job**: Wirksamer Kontozustand, Stummschaltung,
  Ablauf von Anfragen und Kontingente werden bei jedem Zugriff aus den
  Zeitstempeln berechnet. Der Tagesjob räumt nur auf: setzt abgelaufene
  Anfragen auf `expired` und löscht sie nach weiteren 7 Tagen, löscht
  unbestätigte Konten über 48 Stunden, alte Anträge, alte IP-Hashes,
  abgeschlossene Meldungen nach 12 Monaten, verwaiste Grabsteine.
- **Unveränderlich**: `home_ags` und `residence_ags` haben keine
  Schreib-API für Nutzer. Nur Admin-Endpunkte ändern sie, mit
  Audit-Eintrag ohne Ortswerte.
- **Nachrichten**: Jeder Zugriff prüft Teilnahme, wirksamen Zustand beider
  Konten und Blockierung, unter der Sperre aus Abschnitt 7.
- **Nickname**: Adjektiv + Tier/Ding + Zahl, Sperrliste, DB-Constraint.
- **Alter**: Spanne zur Laufzeit aus `birth_year` über das Kalenderjahr,
  nie gespeichert, immer als "etwa" beschriftet.
- **Aktivität**: `last_activity_at` wird gesetzt, wenn der Nutzer den
  Umkreis öffnet, eine Anfrage sendet oder beantwortet oder eine Nachricht
  schreibt. Nur der letzte Zeitstempel, kein Verlauf.
- **API-Sicherheit**: Oberfläche und API unter derselben Origin.
  Session-Cookies mit `SameSite=Lax`, `Secure`, `HttpOnly`.
  Zustandsändernde Aufrufe tragen den Django-CSRF-Token im Header; der
  Schutz wird mit einem Test geprüft, der ohne Token scheitern muss.
  Nutzerabhängige Antworten mit `Cache-Control: private, no-store`.

## 12. Löschkonzept

### Grundsatz
Löschungen werden **ausdrücklich ausgeführt**, nicht über Kaskaden
erhofft. Jeder Löschauftrag wird zuerst ins Löschjournal geschrieben, dann
ausgeführt.

### Ablauf Kontolöschung
1. **Sofort** (in der Anfrage des Nutzers, eine Transaktion): Eintrag ins
   Löschjournal; `status = deleted`, `deleted_at`; E-Mail, Passwort,
   Nickname, Geburtsjahr, Orte auf NULL; alle Sitzungen ungültig. Ab jetzt
   ist das Konto für niemanden mehr sichtbar oder erreichbar.
2. **Innerhalb von 24 Stunden** (Löschdienst, asynchron): alle
   Konversationen des Nutzers mit allen Nachrichten (beide Seiten), alle
   Anfragen von und an ihn, `request_attempts`, Blockeinträge, Anträge,
   Einsprüche; `reports.reporter_id` auf NULL; offene Meldungen *gegen*
   ihn werden mit Ergebnis "Konto gelöscht" geschlossen. Die Gegenseite
   sieht "Gespräch nicht mehr verfügbar".
3. **Grabstein**: bleibt, solange Meldungen oder Audit-Einträge ihn
   referenzieren, längstens 24 Monate. Der Tagesjob löscht verwaiste
   Grabsteine.

### Weitere Löschfälle

| Auslöser                        | Was passiert                                                                 |
|---------------------------------|------------------------------------------------------------------------------|
| Nutzer löscht eigene Nachricht  | Journal-Eintrag; sofort für beide Seiten entfernt                            |
| Nutzer zieht Anfrage zurück     | Sofort unsichtbar für den Empfänger und aus dem Kontingent; Datensatz wird vom Tagesjob gelöscht |
| Anfrage abgelaufen              | Status `expired`, Löschung nach 7 Tagen                                      |
| Meldung abgeschlossen           | Löschung mit Schnappschuss 12 Monate nach `resolved_at`                      |
| Einspruch entschieden           | Löschung zusammen mit der Meldung                                            |
| Audit-Eintrag                   | Löschung nach 24 Monaten                                                     |

### Backups und Wiederherstellung
- Backups werden 30 Tage aufbewahrt.
- **Das Löschjournal liegt außerhalb der Datenbank** (eigener Speicherort,
  eigenes Backup, 60 Tage), damit es ein zurückgespieltes Backup überlebt.
- Wiederherstellungsablauf: Datenbank einspielen → alle Journal-Einträge,
  die jünger sind als der Backup-Zeitpunkt, erneut ausführen → Tagesjob
  laufen lassen → erst dann freigeben. Ohne das Journal würde ein
  Montags-Backup, das am Mittwoch eingespielt wird, ein am Dienstag
  gelöschtes Konto wiederbeleben.
- **Genau dieser Fall ist Teil des Wiederherstellungstests**, der vor dem
  Pilot durchgeführt wird.

### Was die Datenschutzerklärung dazu sagt
- Kontodaten (E-Mail, Passwort, Nickname, Geburtsjahr, Orte) sind sofort
  aus dem laufenden System entfernt und spätestens 31 Tage nach Löschung
  auch aus allen Backups verschwunden.
- Meldungsbelege (bis 12 Monate) und Audit-Einträge (bis 24 Monate) bleiben
  bewusst länger und sind deshalb auch in neueren Backups enthalten. Sie
  enthalten keine E-Mail und keine Orte, aber gemeldete Texte können
  Namen oder Orte enthalten, die der Nutzer selbst geschrieben hat.

## 13. Admin-Bereich

- Nutzer suchen, stummschalten, sperren, entsperren, löschen.
- Heimatort und Wohnort ändern (Pflichtfeld Begründung, Audit-Eintrag).
- Ortsänderungsanträge bestätigen oder ablehnen.
- Meldungen und Einsprüche bearbeiten (Einspruch durch eine andere Person
  als die Erstentscheidung).
- Freigabe-Warteschlange (Registrierungen über dem IP-Limit), sortiert
  nach Alter, mit Ziel 7 Tage.
- Einladungscodes erzeugen und verwalten.
- Kennzahlen aus `daily_stats`.
- Admin-Login mit Zwei-Faktor-Authentifizierung, eigener Pfad, nur
  benannte Personen.

## 14. Datenschutz (DSGVO)

| Datum                    | Zweck                               | Rechtsgrundlage                     | Aufbewahrung                      | Warum erforderlich                               |
|--------------------------|-------------------------------------|-------------------------------------|-----------------------------------|--------------------------------------------------|
| E-Mail, Passwort-Hash    | Login, Bestätigung, Benachrichtigung| Vertrag (Art. 6 Abs. 1 b)           | bis Kontolöschung                 | ohne Login kein Dienst                           |
| Geburtsjahr, Erklärung   | Altersspanne, Mindestalter 18       | Vertrag                             | bis Kontolöschung                 | Jahr statt Datum genügt für eine ungefähre Spanne |
| Heimatort, Wohnort       | Kernfunktion                        | Vertrag                             | bis Kontolöschung                 | ohne sie kein Umkreis, keine Herkunft            |
| Anfragen, Nachrichten    | Kommunikation                       | Vertrag                             | bis Löschung durch Nutzer/Konto   | Inhalt des Dienstes                              |
| `last_activity_at`       | Pilot-Kennzahl "aktiv"              | Berechtigtes Interesse (Art. 6 Abs. 1 f) | bis Kontolöschung            | ein Zeitstempel, kein Verlauf                    |
| Meldungs-Schnappschüsse  | Moderation, Einspruch               | Berechtigtes Interesse              | 12 Monate nach Abschluss          | Belege für Sperren und Einsprüche                |
| Registrierungs-IP (Hash) | IP-Limit                            | Berechtigtes Interesse              | 7 Tage                            | nur für das Limit, ohne Nutzerzuordnung          |
| Audit-Log                | Nachvollziehbarkeit Admin-Handeln   | Berechtigtes Interesse              | 24 Monate                         | Kontrolle der Admins; Referenzen sind pseudonym, nicht anonym |
| Löschjournal             | Durchsetzung von Löschungen nach Wiederherstellung | Rechtliche Pflicht (Art. 17) | 60 Tage                  | nur Objekt-IDs und Zeitstempel                   |
| `daily_stats`            | Pilotauswertung                     | Berechtigtes Interesse              | unbegrenzt                        | aggregierte Zahlen ohne Personenbezug            |

Weitere Festlegungen:
- Keine Gerätekoordinaten, auch nicht in technischen Logs. Webserver-Logs
  speichern IPs nur gekürzt (letztes Oktett entfernt) und 7 Tage.
- Es gibt **keine dauerhafte Ortshistorie im Profil**. Anträge halten
  zeitweise einen alten und neuen Wert (bis 30 Tage nach Entscheidung),
  Backups bis 30 Tage.
- Pseudonymisierte Daten (Nutzer-IDs in Audit-Log und Meldungen) bleiben
  personenbezogen und werden so behandelt.
- Berichtigung (Art. 16) über den Antragsweg aus Abschnitt 4.
  Löschung (Art. 17) nach Abschnitt 12.
- **Restrisiko, offen benannt**: Genauer Heimatort plus Altersspanne plus
  Wohnort-Gemeinde kann in kleinen Orten auf eine Person hinweisen. Das
  wird vor der Registrierung in der Vorschau gezeigt.
- Keine Tracking-Dienste, keine Werbe-SDKs. Karten-Kacheln vom eigenen
  Server oder von einem Anbieter mit Auftragsverarbeitungsvertrag.
- Datenschutzerklärung, Impressum, AV-Vertrag mit dem Hoster vor dem
  ersten externen Nutzer. Benannter Verantwortlicher im Impressum.

## 15. Technischer Vorschlag

| Bereich       | Entscheidung                                                                 |
|---------------|------------------------------------------------------------------------------|
| Backend       | Python 3 + Django als JSON-API (Django Ninja). Eingebauter Admin; 2FA über `django-otp` |
| Datenbank     | PostgreSQL 16 + PostGIS                                                      |
| Frontend      | SvelteKit + TypeScript + Tailwind mit Design-Tokens                          |
| Herkunftsnetz | D3 (d3-force, d3-hierarchy) in einer Svelte-Komponente; SVG; Canvas nur nach Messung |
| Karte         | MapLibre GL mit eigenem, gedämpftem Kartenstil; Netz-Miniaturen als HTML-Marker |
| Kacheln       | OpenStreetMap, selbst gehostet (Protomaps/PMTiles) oder Anbieter mit AV-Vertrag |
| Auth          | Django-Auth, Argon2id, Session-Cookies, CSRF-Token im Header, E-Mail-Bestätigung, Passwort-Reset |
| Spam-Schutz   | Altcha (selbst gehostet)                                                     |
| Jobs          | Django-Management-Command per Cron (Aufräumen, Statistik)                    |
| Löschjournal  | Append-only-Datei oder kleine SQLite auf separatem Volume mit eigenem Backup |
| Echtzeit      | Polling alle 30 s; WebSockets erst, wenn der Pilot es verlangt               |
| E-Mail        | Transaktionaler Versand über Anbieter mit AV-Vertrag                         |
| Betrieb       | Docker Compose, ein Server, tägliches Backup mit getestetem Wiederherstellungsablauf inkl. Journal |
| Ortsdaten     | Import-Skript für das DESTATIS-Gemeindeverzeichnis inkl. Koordinaten, Gebietsstand im Repo vermerkt |

**Warum SvelteKit statt Django-Templates + HTMX**: nicht, weil Templates
keine Gestaltungsqualität erreichen könnten, sondern weil Karte, Netz und
Listenansicht einen gemeinsamen Zustand teilen (Zoomstufe, aufgeklappte
Stufe, Auswahl, Fokus beim Umschalten), der sich mit serverseitigen
Fragmenten nur umständlich halten lässt. Voraussetzung ist, dass das Team
TypeScript und Svelte beherrscht; sonst ist das die falsche Wahl.

**Lastannahmen für den Pilot**: bis 2.000 Konten, bis 200 gleichzeitig
aktive Sitzungen, Spitze 10 API-Anfragen pro Sekunde, Kartenkacheln
getrennt ausgeliefert. Vor dem Pilot ein Lasttest mit dem Doppelten. Die
Kontenzahl allein sagt nichts über die Kapazität.

Keine native App. Als PWA läuft es auf dem Handy.

Erweiterung auf andere Länder (nach dem Pilot): eigenes Länderfeld, pro
Land eine Ortsliste mit eigener Hierarchie, Heimatort entweder deutsche
Gemeinde oder Auslandsort mit Datenbankbedingung "genau eines von beiden".

## 16. Repository-Struktur

```
heimatnah/
├── README.md
├── PROJEKT.md               (diese Datei)
├── LICENSE                  (AGPL-3.0)
├── docker-compose.yml
├── .env.example
├── app/                     (Django)
│   ├── manage.py
│   ├── heimatnah/           (Settings, URLs, Zustands-Middleware)
│   ├── accounts/            (Registrierung, Freigaben, Login, Nickname, IP-Limit, Einladungscodes)
│   ├── places/              (Ortsliste, Import, Hierarchie, Fusionen)
│   ├── nearby/              (Umkreis, Herkunftsgruppen)
│   ├── contacts/            (Anfragen, Versuche, Konversationen, Nachrichten, Blocks, Sperren)
│   ├── moderation/          (Meldungen, Schnappschüsse, Stummschaltung, Einspruch)
│   ├── deletion/            (Löschdienst, Löschjournal, Wiederherstellungs-Nachlauf)
│   ├── adminpanel/          (Django-Admin-Erweiterungen, Audit)
│   ├── jobs/                (Aufräumen, daily_stats)
│   ├── api/                 (Django-Ninja-Router, Schemas, CSRF)
│   └── tests/               (inkl. paralleler Tests und Wiederherstellungstest)
├── web/                     (SvelteKit)
│   ├── src/
│   │   ├── lib/
│   │   │   ├── tokens/
│   │   │   ├── ui/
│   │   │   ├── map/         (MapLibre-Stil, Marker, Miniatur-Netze, Sammelknoten)
│   │   │   ├── network/     (Herkunftsnetz: Layout, Stabilität, Aufklappen, Listenansicht)
│   │   │   └── api/
│   │   └── routes/
│   ├── static/
│   └── tests/
├── design/
│   └── screens.pen
├── data/
│   └── places/
└── docs/
    ├── stellungnahme-codex-2026-10-09.md
    ├── stellungnahme-codex-2026-10-09-nr2.md
    ├── stellungnahme-codex-2026-10-09-nr3.md
    ├── ARCHITEKTUR.md
    ├── DATENSCHUTZ.md
    ├── MODERATION.md
    ├── WIEDERHERSTELLUNG.md
    └── PILOT.md
```

## 17. Entscheidungen zu den Stellungnahmen

### Erste Stellungnahme (`docs/stellungnahme-codex-2026-10-09.md`)

| Hinweis                                              | Entscheidung                                                         |
|------------------------------------------------------|----------------------------------------------------------------------|
| Erst in einer Stadt erproben, Kriterien vorab        | Übernommen, Abschnitt 18                                             |
| Marktlücke ist nur Hypothese                         | Übernommen, Abschnitt 18                                             |
| Nickname allein schützt kaum                         | Richtig; Wirkung aus der Summe, Abschnitt 9                          |
| Aktivitätswünsche als Gesprächsanlass                | **Nicht übernommen.** Keine Hobbys oder Interessen                   |
| Kontaktanfrage mit Annahme                           | Übernommen, Abschnitt 7                                              |
| Gerätestandort ist kein Wohnort                      | Wohnort wird selbst gewählt, Gerätekoordinaten nie gespeichert       |
| Korrekturweg ab v0.1                                 | Übernommen                                                           |
| Heimat als biografische Zuordnung                    | Verschärft: Heimat ist der genaue Ort                                |
| Gerundete Koordinaten sind keine Anonymität          | Keine Einzelpositionen, nur Sammelpunkte; Restrisiko benannt         |
| Widerspruch "nie Verlauf" vs. Audit-Log              | Audit-Log ohne Ortswerte                                             |
| Moderation vollständig in v0.1                       | Übernommen                                                           |
| Auto-Sperre nach Meldungszahl missbrauchbar          | Nur befristete Stummschaltung mit Selbstaufhebung                    |
| `read_at` verrät Aktivität                           | Kein `read_at`                                                       |
| Zwecke, Rechtsgrundlagen, Fristen                    | Tabelle in Abschnitt 14                                              |
| Geburtsjahr reicht nicht für 18-Prüfung              | Datum wird geprüft, nur Jahr und Erklärung gespeichert               |
| `ST_DWithin` nur mit `geography`                     | Übernommen                                                           |
| Filtern oder nachrangig anzeigen?                    | Alle im Radius, nach Herkunft gruppiert                              |
| Ein Stack statt Katalog                              | Django (API) + PostGIS + SvelteKit + D3 + MapLibre, Abschnitt 15     |

### Zweite Stellungnahme (`docs/stellungnahme-codex-2026-10-09-nr2.md`)

| Hinweis                                                   | Entscheidung                                                                   |
|-----------------------------------------------------------|--------------------------------------------------------------------------------|
| Löschregeln widersprechen sich                            | Einheitliches Löschkonzept, Abschnitt 12                                       |
| Löschkaskade vs. Belege                                   | Grabstein + Schnappschuss; Ablauf jetzt ausdrücklich (siehe dritte Stellungnahme) |
| Backup-Rechnung                                           | Kontodaten sofort entfernt, höchstens 31 Tage; Belege bewusst länger, Abschnitt 12 |
| Erforderlichkeit des vollen Geburtsdatums                 | Nur Geburtsjahr + Erklärung                                                    |
| Ein Konto pro IP und Tag zu restriktiv                    | Abgestuftes IP-Limit, Freigabe-Warteschlange, Einladungscodes                  |
| Gleiche Orte sind kein Verdachtsmerkmal                   | Übernommen                                                                     |
| Login-Sperre: Konto, IP oder Kombination?                 | Festgelegt, Abschnitt 8                                                        |
| Abgelehnte Anfragen und Kontingent                        | Einheitliche 30-Tage-Ablaufzeit, `declined` zählt wie `open`                   |
| Zurückziehen, erneut anfragen, gegenseitige Anfragen      | Festgelegt, Abschnitt 7                                                        |
| Gleichzeitige Aktionen                                    | Sperrstrategie, Abschnitt 7 (siehe dritte Stellungnahme)                       |
| Meldung kann Anfrage nicht referenzieren                  | `target_type` + Schnappschuss                                                  |
| Stummschaltung vs. "alle aktiven Nutzer"                  | Berechtigungstabelle, Abschnitt 6                                              |
| Django kennt die Status nicht                             | Middleware                                                                     |
| "Drei unabhängige Nutzer" nicht prüfbar                   | Drei Konten, je 7 Tage aktiv, 48 h befristet; Restrisiko akzeptiert            |
| Blockierung nach Kontolöschung unklar                     | Gestrichen aus v0.1                                                            |
| Herkunftsstufen sind Navigation, kein Schutz              | Vorschau-Seite vor Registrierung                                               |
| Zähler verraten Blockierungen                             | Filterung vor Aggregation; Zusicherung eingeschränkt (siehe dritte Stellungnahme) |
| 20 km zwischen Mittelpunkten erklären                     | Hinweis an der Karte                                                           |
| "Kein Standortverlauf" zu absolut                         | Umformuliert, Abschnitt 14                                                     |
| Ausländische Orte                                         | Durch Beschränkung auf Deutschland entfallen                                   |
| AGS nicht unveränderlich                                  | Gebietsstand eingefroren, `place_merges`                                       |
| Pilot: Vorphase, "aktiv", Nenner, Stundenzahl             | Abschnitt 18                                                                   |

### Dritte Stellungnahme (`docs/stellungnahme-codex-2026-10-09-nr3.md`)

| Hinweis                                                        | Entscheidung                                                                   |
|----------------------------------------------------------------|--------------------------------------------------------------------------------|
| Netz an Aufgaben prüfen, nicht nur an Knotenzahlen             | Aufgabenkatalog und Testdaten, Abschnitt 5                                     |
| Eigene Herkunft auch außerhalb der Top 6 sichtbar              | Miniatur zeigt 5 größte **plus immer die eigene**                              |
| Überlagerung auf der Karte, schematische Position, Kantenbedeutung | Sammelknoten unter 48 px, Legende, Definition der Kante, Abschnitt 5       |
| Layout muss zur Ruhe kommen, Knoten bleiben am Platz           | Stabilitätsregel, Abschnitt 5                                                  |
| 150-Knoten-Canvas-Grenze ist Annahme                           | Nur SVG; Messung auf Referenzgerät; Canvas nur bei Bedarf                      |
| Abnahme statischer Entwürfe muss Änderungen zulassen           | Übernommen                                                                     |
| Listenwechsel: Auswahl, Stufe, Fokus erhalten; Namen nicht nur per Hover | Übernommen, Abschnitt 5                                              |
| Lighthouse ist kein Barrierefreiheitsnachweis                  | Manueller Durchgang mit Tastatur, Screenreader, 200 %, reduzierter Bewegung    |
| IP-Kriterium der Stummschaltung nicht ausführbar               | **IP-Kriterium gestrichen**; Frist nicht verlängert                            |
| `pending` bedeutet zwei Dinge; Job löscht Warteschlange         | Getrennte Merkmale `email_verified_at`, `approval_required`, `approved_at`; nur Unbestätigte werden gelöscht |
| Tagesjob vs. exakte Fristen                                    | Alle Fristen bei Zugriff aus Zeitstempeln; Job räumt nur auf                   |
| 72-h-Prüfung kann nach 48-h-Stummschaltung liegen              | Bewusst so; Prüfung kann danach noch sperren                                   |
| Versuchszähler geht mit gelöschten Anfragen verloren           | `request_attempts` ohne Text                                                   |
| Zurückgezogene sofort aus dem Kontingent                       | Klargestellt, Abschnitt 7 und 12                                               |
| Grabstein löst kein `ON DELETE` aus                            | Löschdienst führt jeden Schritt ausdrücklich aus; Kaskaden nur Sicherheitsnetz |
| Sofortige Unsichtbarkeit, 24 h nur für Bereinigung             | Übernommen, Abschnitt 12                                                       |
| Regeln für Einsprüche, offene Meldungen, verwaiste Grabsteine  | Festgelegt, Abschnitt 12                                                       |
| Backup enthält spätere Löschaufträge nicht                     | **Löschjournal außerhalb der Datenbank**, Nachlauf bei Wiederherstellung, Teil des Tests |
| "31 Tage" nur für Kontodaten                                   | Eingeschränkt; Belege bewusst länger, in der Datenschutzerklärung benannt      |
| Schnappschuss sichert nur Vorhandenes                          | Grenze benannt, im Meldeformular sichtbar                                      |
| Transaktion allein verhindert keine Parallelkonflikte          | Sperrstrategie mit `FOR UPDATE`, atomaren Zählern, partiellem Unique-Index; parallele Tests |
| `UNIQUE(from,to,created_at)` verhindert nichts                 | Ersetzt durch partiellen Index                                                 |
| Altersspanne aus Jahr an Grenzen ungenau                       | Kalenderjahr-Regel, überall "etwa"                                             |
| `adult_verified_at` suggeriert Verifikation                    | Umbenannt in `adult_self_declared_at`                                          |
| Blockierung in kleinen Gruppen erkennbar                       | Zusicherung eingeschränkt, Abschnitt 6                                         |
| "Audit-Log ohne Personendaten" zu stark                        | Umformuliert: pseudonym, nicht anonym                                          |
| HTMX-Begründung zu pauschal                                    | Begründung ersetzt: gemeinsamer Zustand, Teamkompetenz                         |
| Same-Origin, CSRF, Cache                                       | Festgelegt, Abschnitt 11                                                       |
| 2.000 Konten belegen keine Kapazität                           | Lastannahmen und Lasttest, Abschnitt 15                                        |
| Pilot: gleiche Beobachtungszeiten                              | Kohortenregel, Abschnitt 18                                                    |
| "Aktiv" über Handlung statt Login                              | `last_activity_at`, Abschnitt 11 und 18                                        |
| Gelöschte Anfragen und Gespräche in den Quoten                 | `daily_stats` zählt am Entstehungstag, Löschungen ändern Nenner nicht          |

## 18. Pilot und Erfolgskriterien

- **Eine Pilotstadt**, 100.000 bis 300.000 Einwohner, hoher Zuzug,
  z. B. eine Hochschulstadt. Einladung über Hochschulen,
  Neubürgerveranstaltungen, Vereine, mit Einladungscodes.
- **Definitionen**:
  - *Aktives Konto*: wirksamer Zustand aktiv oder stummgeschaltet und
    `last_activity_at` in den letzten 30 Tagen (Umkreis geöffnet, Anfrage
    gesendet oder beantwortet, Nachricht geschrieben).
  - *Wiederkehrendes Gespräch*: beide Seiten haben an mindestens 3
    verschiedenen Tagen innerhalb von 14 Tagen nach Beginn geschrieben.
- **Vorphase**: höchstens 4 Monate ab Freigabe, um 200 aktive Konten zu
  erreichen. Sonst einmalige Verlängerung um 2 Monate oder Abbruch mit
  Ursachenanalyse.
- **Messphase**: 3 Monate ab Erreichen von 200 aktiven Konten, plus
  **14 Tage Nachbeobachtung**.
- **Kohortenregel**: In die Quoten gehen nur Anfragen und Gespräche ein,
  die mindestens 14 Tage vor Ende der Nachbeobachtung entstanden sind.
  Damit hatte jedes gezählte Objekt dieselbe Zeit, das Ziel zu erfüllen.
- **Zählung**: `daily_stats` erfasst jedes Objekt am Entstehungstag und
  sein Ergebnis am Tag des Eintritts. Spätere Löschungen verändern die
  Nenner nicht; so können Löschungen die Quoten nicht verzerren. Es werden
  nur Zahlen gespeichert, keine IDs, keine Texte.
- **Messgrößen**:

| Kennzahl                                                       | Nenner                                               | Ziel        |
|----------------------------------------------------------------|------------------------------------------------------|-------------|
| Nutzer, die mindestens eine Person aus demselben Landkreis im Umkreis sehen | alle aktiven Konten am Ende der Messphase | über 50 %   |
| Angenommene Kontaktanfragen                                    | Anfragen der Kohorte                                 | über 40 %   |
| Wiederkehrende Gespräche                                       | Konversationen der Kohorte                           | über 25 %   |
| Meldungen "Dating/Anmache"                                     | pro 100 aktive Konten und Monat                      | unter 3     |
| Moderationszeit                                                | Stunden pro Woche, alle Bearbeiter zusammen          | unter 4     |

- **Gegenprüfung**: Wenige Meldungen können auch geringe Nutzung oder
  einen schwer auffindbaren Meldeweg bedeuten. Deshalb am Ende der
  Messphase eine kurze Befragung aller aktiven Konten (3 Fragen, freiwillig).
- **Ergebnis**: Werden die Ziele verfehlt, wird nicht ausgebaut, sondern
  die Ursache gesucht.
- "So einen Dienst gibt es nicht" bleibt bis dahin Hypothese.

## 19. Roadmap

**Reihenfolge vor v0.1** (aus der dritten Stellungnahme übernommen):
1. Datenmodell und Abläufe aus den Abschnitten 6, 7 und 12 als Migrationen
   und Dienste umsetzen, mit parallelen Tests und Wiederherstellungstest.
2. Parallel dazu: Entwürfe und Netz-Prototyp mit künstlichen Daten.
3. Senkrechter Durchstich: Registrierung → Herkunftsnetz → Kontaktanfrage →
   Blockierung → Meldung → Löschung. Daran den Pilotaufwand schätzen.

**v0.1 – Pilotfähig** (alles, was vor dem ersten fremden Nutzer da sein muss)
- Registrierung mit getrennten Freigaben, Geburtsdatum-Prüfung, Heimatort,
  Wohnort, Vorschau-Seite
- Abgestuftes IP-Limit, Freigabe-Warteschlange, Einladungscodes,
  Wegwerf-Mail-Sperre, Proof-of-Work, Login-Regeln
- Nickname-Generator
- Designsystem (Tokens, Komponenten, hell/dunkel), abgenommene Entwürfe,
  geprüfter Netz-Prototyp
- Umkreiskarte mit Wohnort-Knoten, Miniatur-Netzen und Sammelknoten;
  Herkunftsnetz mit drei Stufen, Stabilitätsregel und Listenansicht mit
  Zustandserhalt; Filterung vor Aggregation
- Kontaktanfragen mit Zuständen, Versuchszähler, partiellem Index und
  Sperrstrategie; Konversationen; Blockieren; Melden mit Schnappschuss
- Zustands-Middleware, Stummschaltung mit Zeitstempel, Einspruch
- Löschdienst mit Löschjournal, sofortige Unsichtbarkeit, Nachlauf bei
  Wiederherstellung
- Admin: Nutzer, Ortsänderungen, Anträge, Freigabe-Warteschlange,
  Einladungscodes, 2FA
- Passwort-Reset, Aufräum-Jobs, `daily_stats`
- Backup mit getestetem Wiederherstellungsablauf inkl. Journal-Nachlauf
- Lasttest, CSRF-Test, manueller Barrierefreiheits-Durchgang
- Datenschutzerklärung, Impressum, Nutzungsbedingungen
- Tests für: Radiusgrenze, fremder Nachrichtenzugriff, Blockierung in beide
  Richtungen inkl. Zähler, Anfrage-Zustände inkl. Ablauf, Gegenseitigkeit
  und Versuchszähler, **parallele** Anfragen und Annahmen, vollständiger
  Löschablauf inkl. Wiederherstellung, IP-Limit, Zustandsmatrix

**v0.2 – Nach dem Pilot**
- E-Mail-Benachrichtigung bei neuer Anfrage oder Nachricht (abschaltbar)
- PWA-Installation
- Verbesserungen aus den Pilot-Messungen

**v0.3 – Gemeinschaft** (nur wenn der Pilot wiederkehrende Kontakte zeigt)
- Regionsgruppen ("Alle aus dem Oberallgäu in Hamburg"), rein textbasiert
- Treffpunkt-Vorschläge, vom Admin freigegeben

**Später**
- Weitere Länder (Abschnitt 15), Mehrsprachigkeit
- Stadtteile als Unterebene für Großstädte
- Kontenübergreifender Blockierschutz, falls sinnvoll lösbar
- Föderation, damit Städte eigene Instanzen betreiben können

## 20. Gibt es das schon?

Nach bisheriger (kurzer) Prüfung kein Dienst mit genau diesem Zuschnitt.
Verwandte Angebote:

- **InterNations**: Expats finden Landsleute im Ausland, nach Nationalität.
  Kommerziell, mit Fotos, auf Ausländer ausgerichtet.
- **Facebook-Gruppen** wie "Schwaben in Berlin": ohne Umkreis, ohne
  Ortsstufen, mit Fotos und Klarnamen.
- **nebenan.de**: Nachbarschaft, kein Heimatbezug.
- **Meetup**, **Bumble BFF**, **Link**, **Pingwheel**: Freundschafts-Apps
  ohne Herkunftsbezug, meist mit Fotos.
- **Integreat**: Orientierungs-App für Zugewanderte, ohne Vernetzung
  untereinander.

Die Lücke: genauer Heimatort als Merkmal, Umkreis, stufenweises
Hineinzoomen in die Herkunft als Netz, bewusst reduziertes Profil.

## 21. Namensvorschläge

| Name              | Gedanke                                                   |
|-------------------|-----------------------------------------------------------|
| **Heimatnah**     | Heimat in der Nähe finden, klingt warm, nicht nach Dating |
| **Landsleute**    | Das klassische Wort dafür, sofort verständlich            |
| **Zugezogen**     | Nüchtern, beschreibt genau die Zielgruppe                 |
| **Neudaheim**     | Neues Zuhause, Wortspiel                                  |
| **Wurzelwerk**    | Wurzeln finden am neuen Ort                               |
| **Mitgezogen**    | Andere, die den gleichen Weg gegangen sind                |
| **Fremdvertraut** | Fremde Stadt, vertraute Leute                             |

Empfehlung: **Heimatnah** oder **Landsleute**. Vor der Entscheidung Domain
und Markenregister (DPMA) prüfen.
