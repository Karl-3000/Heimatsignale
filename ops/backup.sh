#!/usr/bin/env bash
# Tägliches Backup. Auf dem Server per Cron aufrufen, z. B.:  15 3 * * *  /srv/heimatsignale/ops/backup.sh
# Datenbank: 30 Tage. Löschjournal: eigenes Backup, 60 Tage (länger als die Datenbank-Backups).
set -euo pipefail
cd "$(dirname "$0")/.."
ZIEL="${BACKUP_DIR:-./backups}"
JOURNAL_ZIEL="${JOURNAL_BACKUP_DIR:-./backups-journal}"
mkdir -p "$ZIEL" "$JOURNAL_ZIEL"
STEMPEL="$(date -u +%Y-%m-%dT%H-%M-%SZ)"
ZEITPUNKT="$(date -u +%Y-%m-%dT%H:%M:%S+00:00)"

docker compose exec -T db sh -c 'pg_dump -Fc -U "$POSTGRES_USER" "$POSTGRES_DB"' > "$ZIEL/db-$STEMPEL.dump"
# Der Zeitpunkt gehört zum Backup: Der Nachlauf nach einer Wiederherstellung braucht ihn.
echo "$ZEITPUNKT" > "$ZIEL/db-$STEMPEL.zeitpunkt"

docker compose exec -T app python - > "$JOURNAL_ZIEL/journal-$STEMPEL.sqlite3" <<'PY'
import os, sqlite3, sys, tempfile
src = sqlite3.connect(os.environ["DELETION_JOURNAL_PATH"])
tmp = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False).name
dst = sqlite3.connect(tmp)
src.backup(dst)
dst.close()
sys.stdout.buffer.write(open(tmp, "rb").read())
os.unlink(tmp)
PY

find "$ZIEL" -name 'db-*' -mtime +30 -delete
find "$JOURNAL_ZIEL" -name 'journal-*' -mtime +60 -delete
echo "Backup $STEMPEL geschrieben."
