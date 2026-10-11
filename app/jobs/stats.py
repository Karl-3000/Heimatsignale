from datetime import date

from django.db import connection
from django.utils import timezone

FIELDS = {
    "registrations", "active_accounts", "requests_sent", "requests_accepted", "requests_accepted_cohort",
    "conversations_started", "conversations_recurring", "conversations_recurring_cohort", "reports_dating",
    "deletions",
}


def bump(field: str, day: date | None = None, amount: int = 1) -> None:
    """Erhöht eine Tageskennzahl atomar."""
    if field not in FIELDS:
        raise ValueError(field)
    with connection.cursor() as cur:
        cur.execute(
            f"INSERT INTO daily_stats (day, registrations, active_accounts, requests_sent, requests_accepted, "
            f"requests_accepted_cohort, conversations_started, conversations_recurring, "
            f"conversations_recurring_cohort, reports_dating, deletions) "
            f"VALUES (%s, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0) ON CONFLICT (day) DO NOTHING",
            [day or timezone.localdate()],
        )
        cur.execute(f"UPDATE daily_stats SET {field} = {field} + %s WHERE day = %s", [amount, day or timezone.localdate()])


def set_value(field: str, value: int, day: date | None = None) -> None:
    if field not in FIELDS:
        raise ValueError(field)
    bump(field, day, 0)
    with connection.cursor() as cur:
        cur.execute(f"UPDATE daily_stats SET {field} = %s WHERE day = %s", [value, day or timezone.localdate()])
