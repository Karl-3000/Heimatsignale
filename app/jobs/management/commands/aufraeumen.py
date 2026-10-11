from django.core.management.base import BaseCommand

from jobs import cleanup


class Command(BaseCommand):
    help = "Tagesjob: räumt auf und schreibt die Kennzahl der aktiven Konten."

    def handle(self, *args, **options):
        result = cleanup.run()
        active = cleanup.snapshot_active_accounts()
        self.stdout.write("Aufräumen: " + ", ".join(f"{k}={v}" for k, v in result.items()) + f", aktive_konten={active}")
