# API-Vertrag

Stand: v0.1. Dieser Vertrag ist die gemeinsame Grundlage von Backend
(`app/api/`) und Frontend (`web/src/lib/api/`). Oberfläche und API liegen
unter derselben Origin; alle Pfade beginnen mit `/api/`.

## Grundregeln

- Format: JSON, UTF-8. Zeitstempel ISO 8601 mit Zeitzone (UTC).
- Anmeldung: Session-Cookie (`HttpOnly`, `Secure`, `SameSite=Lax`).
- CSRF: Jeder zustandsändernde Aufruf (`POST`, `DELETE`) trägt den Header
  `X-CSRFToken`. Den Wert liefert `GET /api/session` im Feld `csrf_token`.
  Nach Login, Logout und E-Mail-Bestätigung wird er neu geholt.
- Jede Antwort trägt `Cache-Control: private, no-store`.
- IDs von Nutzern, Anfragen, Konversationen, Nachrichten sind UUIDs.
- Orte werden über den AGS (8 Ziffern, Text) angesprochen, Landkreise über
  die ersten 5 Ziffern, Bundesländer über die ersten 2 Ziffern.
- Der Client übergibt nie eine Suchmitte und nie einen Radius.

### Fehler

Fehler haben einen HTTP-Status und diesen Körper:

```json
{ "code": "quota_daily", "message": "Du hast heute bereits 5 Anfragen gesendet.", "fields": { "body": "..." } }
```

`fields` ist optional und ordnet Meldungen einzelnen Eingabefeldern zu.
`message` ist ein fertiger deutscher Satz und darf angezeigt werden.

| Status | Bedeutung                                                               |
|--------|-------------------------------------------------------------------------|
| 400    | Anfrage fachlich nicht möglich (`code` nennt den Grund); `bad_request` bei ungültigem JSON oder unzulässigen Zeichen |
| 401    | `not_authenticated`: nicht angemeldet oder Sitzung beendet              |
| 403    | `csrf_failed`, `state_forbidden`, `awaiting_approval`, `muted`, `staff_only_admin` |
| 404    | `not_found`: existiert nicht **oder ist für dich nicht sichtbar**       |
| 409    | Konflikt mit dem aktuellen Zustand (z. B. `already_requested`)          |
| 422    | `validation`: Eingaben ungültig, Details in `fields`                    |
| 429    | `rate_limited` oder `login_locked`, mit `retry_after` (Sekunden)        |

## Gemeinsame Objekte

```ts
type Place = { ags: string; name: string; district_ags: string; district_name: string;
               state_code: string; state_name: string };
type PlacePoint = Place & { lat: number; lon: number };   // Gemeindemittelpunkt

// So erscheint ein anderer Nutzer überall. Mehr Felder gibt es nicht.
type PublicUser = { id: string; nickname: string; age_range: string /* "25–34" */;
                    home: Place; residence: { ags: string; name: string };
                    member_since: string /* "2026-10" */ };

type EffectiveState = "active" | "muted" | "awaiting_approval";

type Me = { id: string; nickname: string; age_range: string; home: PlacePoint | null;
            residence: PlacePoint | null; member_since: string;
            muted_until: string | null; nickname_rerolls_left: number; is_staff: boolean };
```

`age_range` ist eine der Spannen `18–24`, `25–34`, `35–44`, `45–54`,
`55–64`, `65+` und wird in der Oberfläche immer mit "etwa" beschriftet.

## Sitzung und Konto

### `GET /api/session`
Immer 200. Setzt das CSRF-Cookie.

```json
{ "authenticated": true, "csrf_token": "…", "state": "active", "user": { /* Me */ },
  "site": { "name": "Heimatsignale", "radius_km": 20, "radius_options": [20, 100], "request_body_max": 500,
            "message_body_max": 2000, "poll_seconds": 30, "admin_path": "/verwaltung/" } }
```
Nicht angemeldet: `authenticated: false`, `state: null`, `user: null`.

### `GET /api/auth/challenge?purpose=register|login|password_reset|resend`
Proof-of-Work-Aufgabe (Altcha-Protokoll, SHA-256).

```json
{ "algorithm": "SHA-256", "challenge": "<hex>", "salt": "<text>", "signature": "<hex>", "maxnumber": 100000 }
```
Der Client sucht die Zahl `n` in `0..maxnumber` mit
`sha256(salt + n) == challenge` und sendet als `pow` die
Base64-Kodierung von
`{"algorithm","challenge","number":n,"salt","signature"}` (JSON).
Über dem IP-Limit ist `maxnumber` größer.

### `POST /api/auth/register`
```json
{ "email": "…", "password": "…", "birth_date": "1994-03-17", "home_ags": "09780139",
  "residence_ags": "05562024", "invite_code": null, "accept_terms": true, "pow": "…" }
```
Antwort 202 `{ "ok": true }`, auch wenn die E-Mail bereits registriert ist.
Fehler 422 mit `fields` (`email`: ungültig oder Wegwerf-Domain; `password`:
zu kurz oder zu häufig; `birth_date`: unter 18; `home_ags`,
`residence_ags`: unbekannt; `invite_code`: ungültig oder verbraucht;
`accept_terms`). 400 `pow_invalid`, 400 `pow_harder_required` (neue Aufgabe
holen und erneut senden).

### `POST /api/auth/verify-email`
`{ "token": "…" }` → 200 wie `GET /api/session` (der Nutzer ist danach
angemeldet). 400 `token_invalid`.

### `POST /api/auth/resend-verification`
`{ "email": "…", "pow": "…" }` → 202 `{ "ok": true }`.

### `POST /api/auth/login`
`{ "email": "…", "password": "…", "pow": null }` → 200 wie `GET /api/session`.
Fehler: 401 `invalid_credentials`; 403 `unverified`; 403 `suspended`
(mit Hinweis auf den Einspruch per E-Mail); 403 `pow_required` (Aufgabe mit
`purpose=login` holen, lösen, erneut senden); 403 `staff_only_admin`;
429 `login_locked` mit `retry_after`.

### `POST /api/auth/logout` → 204

### `POST /api/auth/password-reset`
`{ "email": "…", "pow": "…" }` → 202 `{ "ok": true }` (immer).

### `POST /api/auth/password-reset/confirm`
`{ "uid": "…", "token": "…", "password": "…" }` → 204. 400 `token_invalid`,
422 `validation`.

### `POST /api/me/nickname/reroll`
Einmaliges Neuwürfeln direkt nach der Bestätigung.
→ 200 `{ "nickname": "…", "nickname_rerolls_left": 0 }`. 409 `reroll_used`.

### `POST /api/me/nickname/confirm` → 204
Legt den Nickname fest (verbraucht das Neuwürfeln).

### `POST /api/me/password`
`{ "current_password": "…", "new_password": "…" }` → 204.

### `POST /api/me/delete`
`{ "password": "…" }` → 204. Das Konto ist ab diesem Moment unsichtbar,
die Sitzung beendet.

### `GET /api/me/place-changes`
```json
{ "items": [ { "id": "…", "field": "residence", "new_place": { /* Place */ },
               "created_at": "…", "decided_at": null, "decision": null } ] }
```
`decision`: `null` (offen), `"approved"`, `"rejected"`.

### `POST /api/me/place-changes`
`{ "field": "home" | "residence", "new_ags": "…" }` → 201 (Objekt wie oben).
409 `change_pending`, wenn für das Feld schon ein offener Antrag besteht.

### `POST /api/appeals`
Einspruch eines stummgeschalteten Nutzers. `{ "text": "…" }` → 201.
409 `appeal_exists`.

### `POST /api/appeals/by-token`
Einspruch eines gesperrten Nutzers über den Link aus der E-Mail.
`{ "token": "…", "text": "…" }` → 201. 400 `token_invalid`, 409 `appeal_exists`.

## Orte

### `GET /api/places/search?q=sonth`
Öffentlich (für die Registrierung), höchstens 8 Treffer, mindestens 2
Zeichen. → `{ "items": [ Place, … ] }`

### `POST /api/places/nearest`
Nur zum Vorbelegen des Wohnort-Suchfelds. `{ "lat": 51.65, "lon": 7.09 }`
(vom Client auf zwei Nachkommastellen gerundet). → `{ "place": Place }`.
Die Koordinaten werden weder gespeichert noch protokolliert.

## Umkreis und Herkunft

Suchmitte ist immer der gespeicherte Wohnort. Die drei Aufrufe nehmen den
optionalen Parameter `radius_km` an. Erlaubt sind nur die Werte aus
`site.radius_options` (20 und 100), Standard ist `site.radius_km` (20);
jeder andere Wert ergibt 422. Grundmenge sind alle sichtbaren Nutzer im
gewählten Umkreis (ohne einen selbst), nach Abzug der Blockierungen in
beide Richtungen. Zusammen höchstens 120 Aufrufe pro Stunde (429
`rate_limited`).

Profile, Kontaktanfragen, Blockieren und Melden gelten unabhängig von der
gewählten Ansicht für alle im größten Umkreis (100 km).

### `GET /api/nearby/overview`
```json
{ "radius_km": 20,
  "me": { "residence": { /* PlacePoint */ }, "home": { /* PlacePoint */ } },
  "total": 22,
  "residences": [
    { "ags": "05562024", "name": "Marl", "lat": 51.65, "lon": 7.09, "total": 12,
      "states": [ { "state_code": "09", "count": 7, "distance_km": 480 }, … ] } ] }
```
`states` ist absteigend nach `count` sortiert und vollständig.

### `GET /api/nearby/origins`
Parameter: `residence` (AGS oder `all`), `level` (`state` | `district` |
`place`), `parent` (bei `district` ein `state_code`, bei `place` ein
`district_ags`; bei `state` entfällt er).

```json
{ "level": "district", "parent": "09",
  "items": [ { "key": "09780", "name": "Oberallgäu", "count": 4, "distance_km": 12 } ] }
```
`key` ist je nach Stufe `state_code`, `district_ags` oder `ags`.
`distance_km` ist die Entfernung vom eigenen Heimatort zum Schwerpunkt der
Gruppe (für die Sortierung "nach Nähe").

### `GET /api/nearby/people`
Parameter: `residence` (AGS oder `all`), `home` (AGS), `page` (ab 1).
Feste Seitengröße 50.
```json
{ "items": [ PublicUser, … ], "page": 1, "has_more": false }
```

### `GET /api/users/{id}`
```json
{ "user": { /* PublicUser */ },
  "relation": { "can_request": true, "request_blocked_reason": null,
                "outgoing_request": null, "incoming_request_id": null,
                "conversation_id": null, "blocked_by_me": false } }
```
`outgoing_request`: `null` oder `{ "id": "…", "state": "open" | "expired", "expires_at": "…" }`.
`request_blocked_reason`: `null`, `"muted"`, `"attempts_exhausted"`,
`"already_requested"`, `"connected"`, `"quota_daily"`, `"quota_active"`,
`"not_visible"` (außerhalb deines Umkreises oder von dir blockiert).
404, wenn der Nutzer nicht sichtbar ist. Das gilt auch bei einer
Blockierung in beliebiger Richtung; `blocked_by_me` ist deshalb immer
`false` und nur noch aus Kompatibilität vorhanden. Die Blockliste
(`GET /api/blocks`) nennt den Nickname.

## Kontaktanfragen

### `GET /api/requests`
```json
{ "incoming": [ { "id": "…", "from": PublicUser, "body": "…", "created_at": "…", "expires_at": "…" } ],
  "outgoing": [ { "id": "…", "to": PublicUser, "body": "…", "created_at": "…", "expires_at": "…",
                  "state": "open" | "expired" } ],
  "quota": { "today_used": 1, "today_max": 5, "active_used": 3, "active_max": 20 } }
```
Abgelehnte Anfragen erscheinen beim Absender als `open`.

### `POST /api/requests`
`{ "to_user_id": "…", "body": "…" }` → 201
`{ "request_id": "…" | null, "conversation_id": "…" | null }`
(`conversation_id` ist gesetzt, wenn eine Gegenanfrage offen war und beide
damit als angenommen gelten).
Fehler: 404 `not_found`; 403 `muted`; 409 `already_requested`,
`connected`, `attempts_exhausted`; 400 `quota_daily`, `quota_active`;
422 `validation` (`body`: leer, über 500 Zeichen, enthält Link).

### `POST /api/requests/{id}/accept` → 200 `{ "conversation_id": "…" }`
### `POST /api/requests/{id}/decline` → 204
### `POST /api/requests/{id}/withdraw` → 204
404, wenn die Anfrage nicht (mehr) existiert, abgelaufen ist oder dir nicht
gehört.

## Konversationen

### `GET /api/conversations`
```json
{ "items": [ { "id": "…", "partner": PublicUser | null, "available": true,
               "last_message": { "preview": "…", "created_at": "…", "mine": false } | null,
               "created_at": "…" } ] }
```
`available: false` bedeutet "Gespräch nicht mehr verfügbar" (blockiert,
Gegenseite gesperrt oder gelöscht); `partner` ist dann `null`.

### `GET /api/conversations/{id}/messages?before={message_id}`
Feste Seitengröße 50, neueste zuerst geladen, in der Antwort aufsteigend
sortiert.
```json
{ "partner": PublicUser | null, "available": true, "links_allowed": false,
  "messages": [ { "id": "…", "mine": true, "body": "…", "created_at": "…" } ],
  "has_more": false }
```

### `POST /api/conversations/{id}/messages`
`{ "body": "…" }` → 201 (Nachrichtenobjekt). Fehler: 403 `unavailable`;
422 `validation` (leer, über 2000 Zeichen, Link vor 10 Nachrichten);
429 `rate_limited`.

### `DELETE /api/messages/{id}` → 204 (nur eigene)

### `GET /api/inbox/summary`
Für das Polling alle 30 Sekunden.
```json
{ "incoming_requests": 2,
  "conversations": [ { "id": "…", "last_message_at": "…", "last_message_mine": false } ] }
```
Ob etwas "ungelesen" ist, entscheidet nur der Client (lokaler Speicher).

## Blockieren und Melden

### `GET /api/blocks`
`{ "items": [ { "user_id": "…", "nickname": "…" | null, "created_at": "…" } ] }`
### `POST /api/blocks` `{ "user_id": "…" }` → 204
404, wenn du das Konto nicht kennst (nicht im Umkreis sichtbar, kein
Gespräch, keine Anfrage zwischen euch).
### `DELETE /api/blocks/{user_id}` → 204

### `POST /api/reports`
```json
{ "target_type": "profile" | "request" | "message", "target_id": "…",
  "conversation_id": null, "reason": "dating" | "harassment" | "spam" | "false_info" | "other",
  "note": "…" }
```
`target_id` ist bei `profile` die Nutzer-ID. Bei `message` muss
`conversation_id` gesetzt sein. → 201 `{ "ok": true }`. 404, wenn das Ziel
für dich nicht zugänglich ist. Eine zweite Meldung desselben Ziels
innerhalb von 7 Tagen wird stillschweigend zusammengeführt.
