#!/usr/bin/env bash
# Wiederherstellungstest (PROJEKT.md, Abschnitt 12) mit echtem pg_dump und pg_restore:
# Backup -> Löschungen -> Backup einspielen -> Journal-Nachlauf -> Tagesjob -> Prüfung.
# Läuft gegen eine eigene Wegwerf-Datenbank und ein eigenes Wegwerf-Journal.
set -euo pipefail

cd "$(dirname "$0")/../app"
export DEBUG=1
export DB_HOST="${DB_HOST:-127.0.0.1}" DB_PORT="${DB_PORT:-5432}" DB_USER="${DB_USER:-heimat}"
export DB_NAME="heimat_wiederherstellungstest"
export PGHOST="$DB_HOST" PGPORT="$DB_PORT" PGUSER="$DB_USER" PGPASSWORD="${PGPASSWORD:-${DB_PASSWORD:-heimat}}"
export DB_PASSWORD="$PGPASSWORD"
WORK="$(mktemp -d)"
export DELETION_JOURNAL_PATH="$WORK/journal/loeschjournal.sqlite3"
export EMAIL_BACKEND="django.core.mail.backends.dummy.EmailBackend"
PY="${PYTHON:-python3}"
trap 'dropdb --if-exists "$DB_NAME" >/dev/null 2>&1 || true; rm -rf "$WORK"' EXIT

echo "1. Ausgangslage"
dropdb --if-exists "$DB_NAME"; createdb "$DB_NAME"
$PY manage.py migrate --no-input >/dev/null
$PY manage.py wiederherstellungstest_schritt vorbereiten --datei "$WORK/zustand.json"

echo "2. Backup (\"Montag\")"
BACKUP_ZEIT="$(date -u +%Y-%m-%dT%H:%M:%S+00:00)"
pg_dump -Fc -f "$WORK/backup.dump" "$DB_NAME"
sleep 2

echo "3. Löschungen nach dem Backup (\"Dienstag\")"
$PY manage.py wiederherstellungstest_schritt loeschen --datei "$WORK/zustand.json"

echo "4. Backup einspielen (\"Mittwoch\")"
dropdb "$DB_NAME"; createdb "$DB_NAME"
pg_restore --no-owner -d "$DB_NAME" "$WORK/backup.dump"

echo "5. Journal-Nachlauf und Tagesjob"
$PY manage.py wiederherstellung_nachlauf --backup-zeitpunkt "$BACKUP_ZEIT"
$PY manage.py aufraeumen

echo "6. Prüfung"
$PY manage.py wiederherstellungstest_schritt pruefen --datei "$WORK/zustand.json"
