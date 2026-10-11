#!/usr/bin/env bash
# Wiederherstellung nach docs/WIEDERHERSTELLUNG.md:
# Datenbank einspielen -> Journal-Nachlauf -> Tagesjob -> erst dann freigeben.
# Aufruf: ops/restore.sh backups/db-2026-10-05T01-15-00Z.dump
set -euo pipefail
cd "$(dirname "$0")/.."
DUMP="${1:?Bitte die Dump-Datei angeben}"
ZEITDATEI="${DUMP%.dump}.zeitpunkt"
[ -f "$DUMP" ] || { echo "Dump nicht gefunden: $DUMP"; exit 1; }
[ -f "$ZEITDATEI" ] || { echo "Zeitpunkt-Datei fehlt: $ZEITDATEI"; exit 1; }
ZEITPUNKT="$(cat "$ZEITDATEI")"

echo "Der Dienst wird angehalten und die Datenbank durch den Stand von $ZEITPUNKT ersetzt."
read -r -p "Fortfahren? (ja/nein) " ANTWORT
[ "$ANTWORT" = "ja" ] || exit 1

docker compose stop web app jobs
docker compose exec -T db sh -c 'dropdb -U "$POSTGRES_USER" --if-exists "$POSTGRES_DB" && createdb -U "$POSTGRES_USER" "$POSTGRES_DB"'
docker compose exec -T db sh -c 'pg_restore --no-owner -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < "$DUMP"

# Das Löschjournal liegt auf einem eigenen Volume und wurde NICHT zurückgesetzt.
docker compose run --rm --no-deps app python manage.py migrate --no-input
docker compose run --rm --no-deps app python manage.py wiederherstellung_nachlauf --backup-zeitpunkt "$ZEITPUNKT"
docker compose run --rm --no-deps app python manage.py aufraeumen

echo
echo "Bitte die Ausgabe prüfen (insbesondere 'Nicht bestätigt'). Erst danach freigeben mit:"
echo "  docker compose up -d"
