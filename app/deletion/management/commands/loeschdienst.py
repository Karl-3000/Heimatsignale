from django.core.management.base import BaseCommand

from deletion.services import purge_deleted_accounts


class Command(BaseCommand):
    help = "Bereinigt alles, was noch an gelöschten Konten hängt (Schritt 2 der Kontolöschung)."

    def handle(self, *args, **options):
        counts = purge_deleted_accounts()
        self.stdout.write("Löschdienst: " + ", ".join(f"{k}={v}" for k, v in counts.items()))
