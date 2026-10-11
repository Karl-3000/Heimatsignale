"""Nachlauf nach dem Einspielen eines Backups (PROJEKT.md, Abschnitt 12).

Ablauf: Datenbank einspielen → diesen Befehl mit dem Zeitpunkt des Backups
ausführen → ``aufraeumen`` laufen lassen → erst dann freigeben.
"""

from datetime import datetime, timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from deletion import journal
from deletion.services import replay


class Command(BaseCommand):
    help = "Führt alle Löschaufträge aus dem Löschjournal erneut aus, die jünger sind als das Backup."

    def add_arguments(self, parser):
        parser.add_argument("--backup-zeitpunkt", required=True, help="ISO-Zeitstempel des eingespielten Backups")
        parser.add_argument(
            "--auch-unbestaetigte", action="store_true",
            help="Auch Aufträge ausführen, deren Ausführung im Journal nicht bestätigt ist",
        )

    def handle(self, *args, backup_zeitpunkt: str, auch_unbestaetigte: bool, **options):
        try:
            since = datetime.fromisoformat(backup_zeitpunkt)
        except ValueError:
            raise CommandError("Zeitpunkt bitte als ISO-Zeitstempel angeben, z. B. 2026-10-05T03:00:00+02:00.") from None
        if timezone.is_naive(since):
            since = timezone.make_aware(since)
        # Kleiner Sicherheitsabstand: lieber einen Auftrag doppelt ausführen als einen auslassen.
        entries = journal.entries_since(since - timedelta(minutes=10))
        done = skipped = 0
        for entry in entries:
            if not entry["confirmed"] and not auch_unbestaetigte:
                skipped += 1
                self.stderr.write(
                    f"Nicht bestätigt, bitte prüfen: {entry['object_type']} {entry['object_id']} ({entry['requested_at']})"
                )
                continue
            result = replay(entry)
            done += 1
            self.stdout.write(f"{entry['object_type']} {entry['object_id']}: {result}")
        self.stdout.write(self.style.SUCCESS(f"Nachlauf beendet: {done} ausgeführt, {skipped} unbestätigt übersprungen."))
