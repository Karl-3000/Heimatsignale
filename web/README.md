# Heimatsignale: Oberfläche

SvelteKit 2 mit Svelte 5 (Runes), TypeScript, Tailwind CSS 4, D3 (d3-force, d3-hierarchy) und MapLibre GL.
Die Oberfläche ist eine reine SPA (`ssr = false`, `adapter-static` mit `fallback: 'index.html'`), weil alle Daten
hinter dem Login liegen. Ein Reverse-Proxy liefert `build/` aus und leitet `/api/` und den Admin-Pfad an Django
weiter (gleiche Origin). Der API-Vertrag steht in `../docs/API.md`.

## Befehle

| Befehl              | Zweck                                                                 |
|---------------------|-----------------------------------------------------------------------|
| `npm run dev`       | Entwicklungsserver; `/api` und `/verwaltung` gehen an `127.0.0.1:8000` |
| `npm run check`     | `svelte-kit sync` und `svelte-check`                                  |
| `npm run test:unit` | Vitest für die frameworkfreie Logik (`src/**/*.test.ts`)              |
| `npm run build`     | Statischer Build nach `build/`                                        |
| `npm run preview`   | Build lokal ansehen                                                   |

Umgebungsvariablen: siehe `.env.example`. Ohne `PUBLIC_TILES_URL` zeigt die Karte nur Hintergrund, Umkreis-Kreis
und Knoten und stellt keine einzige Anfrage nach außen. Ortsnamen auf der Grundkarte gibt es nur mit
`PUBLIC_GLYPHS_URL`; der Stil erwartet dort den Schriftschnitt „Noto Sans Regular“.

## Aufbau

```
src/
├── app.css, app.html          Tailwind-Einstieg, HTML-Rahmen (lang="de")
├── lib/
│   ├── tokens/tokens.css      Design-Tokens, hell und dunkel
│   ├── ui/                    Button, Field, TextArea, Dialog, Card, Badge, Tabs, Toaster, Notice,
│   │                          PlaceSearch (Combobox), ReportDialog, ConfirmDialog, ThemeToggle, Icon ...
│   ├── api/                   client.ts (ein fetch-Client), endpoints.ts, types.ts, guard.ts (Routenschutz),
│   │                          session.svelte.ts, inbox.svelte.ts (Polling, Lesestatus nur lokal)
│   ├── pow/                   Proof-of-Work (Altcha): solver.ts, pow.worker.ts, solve.ts, run.svelte.ts
│   ├── network/               Herkunftsnetz: layout.ts, labels.ts, model.ts, scene.ts, core.ts,
│   │                          view.svelte.ts, umkreis.svelte.ts, OriginNetwork, OriginTree, synthetic.ts
│   ├── map/                   Karte: style.ts, cluster.ts, miniature.ts, geo.ts, UmkreisMap, Miniature
│   └── util/                  Formate, Speicher, Farbschema
└── routes/                    Seiten mit deutschen Pfaden; /dev/netz ist der Prototyp ohne Backend
static/                        manifest.webmanifest, icon.svg, theme.js
```

Alle Module ohne `.svelte` im Namen sind frei von Framework-Code und haben Tests daneben.

## Design-Tokens

`src/lib/tokens/tokens.css` ist die einzige Quelle für Farben, Typografie, Abstände, Radien, Schatten und
Bewegung. `app.css` bildet sie über `@theme inline` in Tailwind ab (`bg-surface`, `text-ink-muted` ...);
Komponenten greifen direkt auf `var(--hs-...)` zu.

- Grundsystem aus warmem Grau, kein reines Weiß oder Schwarz.
- `--hs-accent` (Petrol): Interaktion. `--hs-origin` (Bernstein): nur die eigene Herkunft im Netz.
  Bundesländer haben keine eigenen Farben.
- Dunkles Thema per Systemeinstellung oder Wahl (`data-theme` am `<html>`, gespeichert unter `hs:theme`).
  `static/theme.js` setzt es vor dem ersten Zeichnen; als Datei, weil die CSP Inline-Skripte verbietet.
- Inter Variable mit zwei Gewichten, Tabellenziffern über `.hs-num`.
- Bewegung 150 bis 300 ms; bei `prefers-reduced-motion` sind alle Dauern 0.
- Icons: Lucide, immer über `ui/Icon.svelte` (eine Strichstärke).

## Stabilitätsregel des Netzes

Umgesetzt in `lib/network/layout.ts` (`NetworkLayout.sync`), aufgerufen aus `core.ts` (`recompute`):

1. Jede Änderung (Aufklappen, Zuklappen, Sortierung) ist ein Methodenaufruf. Danach wird die d3-force-Simulation
   **synchron** in einer Schleife gerechnet, bis `alpha < alphaMin`. Es gibt keinen Timer und kein
   `requestAnimationFrame`; die Oberfläche sieht nur das fertige Ergebnis.
2. Das Ergebnis liegt eingefroren in einer Map. `view.svelte.ts` spiegelt es als `$state.raw`; die Komponenten
   zeichnen nur und simulieren nie.
3. Beim Aufklappen nehmen bestehende Knoten nur als feste Hindernisse teil (`fx`/`fy` gesetzt). Bewegt werden
   ausschließlich die neuen Knoten: Startposition im Fächer um den Winkel des Elternknotens, radiale Bindung an
   den Ring ihrer Stufe, Kollision gegen alle Klickflächen. Reicht der Bogen nicht, entstehen versetzte Reihen.
4. Die Zeichenfläche hat eine feste Größe (`HALF_EXTENT`), damit beim Wachsen nichts springt.
5. Die 300-ms-Animation ist reine Darstellung: Neue Knoten starten an der Position des Elternknotens und laufen
   per CSS-Transition zu ihrem festen Ziel. Bei reduzierter Bewegung entfällt sie.

Die Tests in `layout.test.ts` klappen die Testdaten aus dem Projektplan Schritt für Schritt auf und prüfen nach
jedem Schritt, dass kein bestehender Knoten seine Position geändert hat, dass sich keine Klickflächen
überlappen und dass keine Beschriftungen übereinander liegen.

Netz und Liste teilen sich dieselbe `NetworkView` (Auswahl, aufgeklappte Stufen, Fokus). `umkreis.svelte.ts`
hält sie außerhalb der Seite, damit nach einem Profilbesuch alles wie zuvor ist.

## Karte

Jede Wohnort-Gemeinde ist ein HTML-Knoten über der Karte. Die Positionen kommen bei jeder Kartenbewegung aus
`map.project`; aus den Pixelabständen bildet `cluster.ts` Sammelknoten (unter 48 px) und begrenzt die Größe der
Miniaturen so, dass sich nie zwei überdecken. Der kleinste Zoom ist der, bei dem der Kreis des gewählten Umkreises
gerade in die Fläche passt; außerhalb des Kreises deckt eine Maske die Karte ab. Kann MapLibre nicht starten (kein WebGL),
erscheint eine schematische Ersatzdarstellung mit denselben Knoten.

## Umkreis 20 km oder 100 km

Die Auswahl kommt aus `site.radius_options`, der Standard aus `site.radius_km`. Der gewählte Wert liegt in
`network/umkreis.svelte.ts` (`radius`, `setRadius`) und wird im Browser unter `hs:umkreis` gemerkt; ein
gespeicherter Wert gilt nur, wenn der Server ihn anbietet (`util/radius.ts`). Übersicht, Herkunft und Personen
werden immer mit demselben `radius_km` abgefragt (`createApiSource(radius)`). Ein Wechsel lädt die Übersicht neu
und verwirft alle Netze; Darstellung und Sortierung bleiben. Karte, Texte und leerer Zustand richten sich nach
dem angewandten Wert `overview.radius_km`. `datasetWeit()` (100 km, 60 Wohnorte) prüft Sammelknoten und
Überdeckungsfreiheit; die Paarsuche in `cluster.ts` arbeitet dafür mit einem Gitter.

## Sicherheit und Datenschutz

- Keine Anfragen an fremde Hosts, kein Tracking. Die CSP kommt aus `svelte.config.js` (`kit.csp`, Modus `hash`).
- Koordinaten verlassen das Gerät nur gerundet (zwei Nachkommastellen) an `/api/places/nearest`, nach einem
  ausdrücklichen Klick, und werden nicht gespeichert.
- localStorage enthält nur `hs:theme` (Farbschema), `hs:umkreis` (gewählter Umkreis) und `hs:gelesen` (bis wann
  ein Gespräch gelesen ist).

## Test-IDs

Stabile `data-testid`-Attribute für die Ende-zu-Ende-Tests, nach Bereich:

- Rahmen: `brand`, `nav-umkreis`, `nav-anfragen`, `nav-gespraeche`, `nav-einstellungen` (mobil mit Endung `-mobil`),
  `nav-anmelden`, `nav-registrieren`, `logout`, `muted-banner`, `session-error`, `toaster`, `toast`,
  `theme-toggle`, `theme-system`, `theme-light`, `theme-dark`
- Start und Vorschau: `landing-register`, `landing-preview`, `preview-card`, `preview-radius`, `preview-levels`, `preview-risk`,
  `preview-register`
- Registrierung: `register-form` (Attribut `data-step`), `register-progress`, `register-step-title`,
  `register-email`, `register-password`, `register-day`, `register-month`, `register-year`, `register-home`,
  `register-residence` (jeweils mit `-input`, `-option`, `-selected`, `-change`), `register-locate`,
  `register-suggestion`, `register-suggestion-accept`, `register-summary`, `register-places-note`,
  `register-invite`, `register-terms`, `register-back`, `register-next`, `register-error`, `register-sent`,
  `register-resend`, `register-resent`, `pow-status`
- Bestätigung: `verify-pending`, `verify-invalid`, `verify-missing`, `nickname-card`, `nickname`,
  `nickname-reroll`, `nickname-confirm`, `nickname-error`
- Anmeldung und Passwort: `login-form`, `login-email`, `login-password`, `login-submit`, `login-error`,
  `login-resend`, `login-resent`, `login-forgot`, `reset-form`, `reset-email`, `reset-submit`, `reset-sent`,
  `reset-error`, `newpw-form`, `newpw-password`, `newpw-repeat`, `newpw-submit`, `newpw-done`, `newpw-error`,
  `newpw-invalid`
- Status und Einspruch: `status-awaiting`, `status-recheck`, `status-muted`, `status-muted-until`,
  `status-appeal-form`, `status-appeal-text`, `status-appeal-submit`, `status-appeal-done`,
  `status-appeal-exists`, `appeal-form`, `appeal-text`, `appeal-submit`, `appeal-done`, `appeal-exists`,
  `appeal-invalid`, `appeal-error`, `staff-page`, `staff-admin-link`
- Umkreis: `umkreis-page`, `umkreis-summary`, `radius-toggle`, `radius-20`, `radius-100` (je Wert aus
  `site.radius_options`), `radius-status`, `empty-wider`, `umkreis-refresh`, `umkreis-loading`, `umkreis-error`,
  `umkreis-empty`, `umkreis-map` (Attribut `data-ready`), `map-node` und `map-cluster` (Attribute `data-ags`,
  `data-mode`), `map-zoom-in`, `map-zoom-out`, `map-reset`, `radius-hint`, `residence-list`, `residence-all`,
  `residence-item` (Attribut `data-ags`), `network-title`
- Netz und Liste: `network-explorer` (Attribut `data-mode`), `view-toggle`, `view-toggle-netz`,
  `view-toggle-liste`, `sort-distance`, `sort-count`, `network`, `network-root`, `network-node` (Attribute
  `data-node-id`, `data-level`, `data-own`), `network-zoom-in`, `network-zoom-out`, `network-center`,
  `network-legend`, `network-announcement`, `network-error`, `people-panel`, `people-item`, `people-link`,
  `people-more`, `people-close`, `origin-tree`, `tree-item` (Attribute `data-row-id`, `data-level`, `data-own`),
  `tree-person`, `tree-more`
- Profil: `profile-page`, `profile-back`, `profile-card`, `profile-notfound`, `profile-error`,
  `profile-incoming`, `profile-outgoing`, `profile-withdraw`, `profile-open-conversation`, `request-form`,
  `request-body`, `request-submit`, `request-error`, `request-blocked`, `profile-block`, `profile-report`,
  `person-link`
- Anfragen: `requests-page`, `requests-tabs`, `requests-tabs-eingegangen`, `requests-tabs-gesendet`,
  `request-incoming`, `request-text`, `request-accept`, `request-decline`, `request-block`, `request-report`,
  `request-outgoing`, `request-withdraw`, `requests-quota`, `requests-incoming-empty`,
  `requests-outgoing-empty`, `requests-error`
- Gespräche: `conversations-page`, `conversation-item`, `conversations-empty`, `conversations-error`,
  `conversation-page`, `conversation-back`, `conversation-partner`, `conversation-block`,
  `conversation-unavailable`, `conversation-notfound`, `conversation-error`, `message-list`, `message`
  (Attribut `data-mine`), `message-delete`, `message-report`, `messages-older`, `message-form`,
  `message-input`, `message-send`, `message-error`, `links-hint`
- Dialoge: `block-dialog`, `block-ok`, `block-cancel`, `delete-message-dialog`, `delete-message-ok`,
  `delete-message-cancel`, `report-dialog`, `report-reason-dating` (ebenso `-harassment`, `-spam`,
  `-false_info`, `-other`), `report-note`, `report-submit`, `report-error`
- Einstellungen: `settings-page`, `settings-profile`, `change-residence`, `change-home`, `change-form`,
  `change-place` (mit `-input`, `-option`, `-selected`), `change-submit`, `change-list`, `change-item`,
  `block-list`, `block-item`, `block-remove`, `block-report`, `blocks-empty`, `blocks-error`, `password-form`,
  `password-current`, `password-new`, `password-repeat`, `password-submit`, `settings-logout`, `delete-open`,
  `delete-dialog`, `delete-password`, `delete-confirm`, `delete-cancel`
- Sonstiges: `legal-page`, `legal-draft`, `error-page`, `dev-netz`, `dev-dataset`, `dev-description`
