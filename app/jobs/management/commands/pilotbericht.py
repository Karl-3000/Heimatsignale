"""Pilot-Kennzahlen nach PROJEKT.md, Abschnitt 18. Gibt nur aggregierte Zahlen aus."""

from datetime import date, timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection
from django.db.models import Sum
from django.utils import timezone

from jobs.models import DailyStat


class Command(BaseCommand):
    help = "Wertet die Pilot-Kennzahlen aus (Kohortenregel: 14 Tage vor Ende der Nachbeobachtung)."

    def add_arguments(self, parser):
        parser.add_argument("--von", required=True, help="Beginn der Messphase, JJJJ-MM-TT")
        parser.add_argument("--bis", required=True, help="Ende der Nachbeobachtung, JJJJ-MM-TT")

    def handle(self, *args, von: str, bis: str, **options):
        start, end = date.fromisoformat(von), date.fromisoformat(bis)
        cohort_end = end - timedelta(days=14)
        cohort = DailyStat.objects.filter(day__gte=start, day__lte=cohort_end).aggregate(
            sent=Sum("requests_sent"), accepted=Sum("requests_accepted_cohort"),
            started=Sum("conversations_started"), recurring=Sum("conversations_recurring_cohort"),
        )
        period = DailyStat.objects.filter(day__gte=start, day__lte=end).aggregate(dating=Sum("reports_dating"))

        with connection.cursor() as cur:
            cur.execute(
                """
                WITH active AS (
                    SELECT u.id, u.residence_ags, hp.district_ags FROM users u JOIN places hp ON hp.ags = u.home_ags
                    WHERE u.status = 'active' AND u.last_activity_at >= %s
                )
                SELECT COUNT(*), COUNT(*) FILTER (WHERE EXISTS (
                    SELECT 1 FROM active o
                    JOIN places op ON op.ags = o.residence_ags
                    JOIN places mp ON mp.ags = a.residence_ags
                    WHERE o.id <> a.id AND o.district_ags = a.district_ags
                      AND ST_DWithin(mp.center, op.center, %s)
                      AND NOT EXISTS (
                          SELECT 1 FROM blocks b WHERE (b.blocker_id = a.id AND b.blocked_id = o.id)
                                                    OR (b.blocker_id = o.id AND b.blocked_id = a.id))
                ))
                FROM active a
                """,
                [timezone.now() - timedelta(days=30), settings.RADIUS_DEFAULT_KM * 1000],
            )
            active, with_match = cur.fetchone()

        def pct(a, b):
            return f"{100 * (a or 0) / b:.1f} %" if b else "keine Daten"

        months = max((end - start).days / 30.44, 0.01)
        dating_rate = (period["dating"] or 0) / (active / 100) / months if active else None
        self.stdout.write(f"Messzeitraum {start} bis {end}, Kohorte bis {cohort_end}")
        self.stdout.write(f"Aktive Konten: {active}")
        self.stdout.write(f"Sehen jemanden aus demselben Landkreis: {pct(with_match, active)} (Ziel über 50 %)")
        self.stdout.write(f"Angenommene Anfragen: {pct(cohort['accepted'], cohort['sent'])} (Ziel über 40 %)")
        self.stdout.write(f"Wiederkehrende Gespräche: {pct(cohort['recurring'], cohort['started'])} (Ziel über 25 %)")
        self.stdout.write(
            "Meldungen Dating/Anmache pro 100 aktive Konten und Monat: "
            + (f"{dating_rate:.2f}" if dating_rate is not None else "keine Daten") + " (Ziel unter 3)"
        )
