"""Löschjournal: liegt bewusst außerhalb der Datenbank (PROJEKT.md, Abschnitt 12).

Eine kleine SQLite-Datei auf einem eigenen Volume mit eigenem Backup. Sie ist
nur anfügbar: Trigger verbieten Änderungen, gelöscht werden dürfen nur
Einträge, die älter als 60 Tage sind. Gespeichert werden ausschließlich
Objektart, Objekt-ID und Zeitstempel.

Jeder Löschauftrag wird zuerst als ``request`` eingetragen, dann ausgeführt
und danach als ``confirm`` bestätigt. Nach dem Einspielen eines Backups
werden alle bestätigten Aufträge, die jünger sind als das Backup, erneut
ausgeführt (``manage.py wiederherstellung_nachlauf``).
"""

import sqlite3
from contextlib import closing
from datetime import datetime, timedelta, timezone as dt_timezone
from pathlib import Path

from django.conf import settings

OBJECT_TYPES = ("account", "message", "conversation", "request")

_SCHEMA = f"""
CREATE TABLE IF NOT EXISTS deletion_journal (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT NOT NULL CHECK (kind IN ('request', 'confirm')),
    object_type TEXT NOT NULL CHECK (object_type IN {OBJECT_TYPES!r}),
    object_id TEXT NOT NULL,
    requested_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS deletion_journal_at ON deletion_journal (requested_at);
CREATE TRIGGER IF NOT EXISTS deletion_journal_no_update BEFORE UPDATE ON deletion_journal
BEGIN SELECT RAISE(ABORT, 'Das Löschjournal ist nur anfügbar.'); END;
CREATE TRIGGER IF NOT EXISTS deletion_journal_no_early_delete BEFORE DELETE ON deletion_journal
WHEN OLD.requested_at > strftime('%Y-%m-%dT%H:%M:%fZ', 'now', '-{settings.JOURNAL_KEEP_DAYS} days')
BEGIN SELECT RAISE(ABORT, 'Einträge dürfen erst nach Ablauf der Aufbewahrung entfernt werden.'); END;
"""


def _now() -> str:
    return datetime.now(dt_timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _connect() -> sqlite3.Connection:
    path = Path(settings.DELETION_JOURNAL_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=30, isolation_level=None)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=FULL")
    conn.executescript(_SCHEMA)
    return conn


def _append(kind: str, object_type: str, object_id) -> None:
    if object_type not in OBJECT_TYPES:
        raise ValueError(object_type)
    with closing(_connect()) as conn:
        conn.execute(
            "INSERT INTO deletion_journal (kind, object_type, object_id, requested_at) VALUES (?, ?, ?, ?)",
            (kind, object_type, str(object_id), _now()),
        )


def record(object_type: str, object_id) -> None:
    """Trägt einen Löschauftrag ein, bevor er ausgeführt wird."""
    _append("request", object_type, object_id)


def confirm(object_type: str, object_id) -> None:
    """Bestätigt, dass der Auftrag in der Datenbank ausgeführt und festgeschrieben wurde."""
    _append("confirm", object_type, object_id)


def entries_since(since: datetime) -> list[dict]:
    """Alle Aufträge seit ``since`` mit dem Vermerk, ob sie bestätigt wurden."""
    stamp = since.astimezone(dt_timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    with closing(_connect()) as conn:
        rows = conn.execute(
            "SELECT kind, object_type, object_id, requested_at FROM deletion_journal WHERE requested_at >= ? ORDER BY seq",
            (stamp,),
        ).fetchall()
    confirmed = {(t, i) for kind, t, i, _ in rows if kind == "confirm"}
    seen: set = set()
    result = []
    for kind, object_type, object_id, at in rows:
        if kind != "request" or (object_type, object_id) in seen:
            continue
        seen.add((object_type, object_id))
        result.append({
            "object_type": object_type, "object_id": object_id, "requested_at": at,
            "confirmed": (object_type, object_id) in confirmed,
        })
    return result


def purge() -> int:
    """Entfernt Einträge nach Ablauf der Aufbewahrung (60 Tage)."""
    limit = (datetime.now(dt_timezone.utc) - timedelta(days=settings.JOURNAL_KEEP_DAYS)).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    with closing(_connect()) as conn:
        return conn.execute("DELETE FROM deletion_journal WHERE requested_at < ?", (limit,)).rowcount
