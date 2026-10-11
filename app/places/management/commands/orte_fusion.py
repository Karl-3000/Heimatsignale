"""Bildet eine aufgelöste Gemeinde auf ihre Nachfolgerin ab (Gemeindefusion)."""

from datetime import date

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts import mail
from accounts.models import PlaceChangeRequest, User
from places.models import Place, PlaceMerge


class Command(BaseCommand):
    help = "Trägt eine Gemeindefusion ein, stellt betroffene Nutzer um und informiert sie."

    def add_arguments(self, parser):
        parser.add_argument("alter_ags")
        parser.add_argument("neuer_ags")
        parser.add_argument("--gueltig-ab", default=None, help="JJJJ-MM-TT, Standard: heute")

    @transaction.atomic
    def handle(self, *args, alter_ags: str, neuer_ags: str, gueltig_ab: str | None, **options):
        new = Place.objects.filter(pk=neuer_ags).first()
        if new is None:
            raise CommandError(f"Neue Gemeinde {neuer_ags} ist nicht in der Ortsliste.")
        valid_from = date.fromisoformat(gueltig_ab) if gueltig_ab else date.today()
        PlaceMerge.objects.update_or_create(old_ags=alter_ags, defaults={"new_ags": neuer_ags, "valid_from": valid_from})
        affected = list(User.objects.filter(home_id=alter_ags) | User.objects.filter(residence_id=alter_ags))
        User.objects.filter(home_id=alter_ags).update(home_id=neuer_ags)
        User.objects.filter(residence_id=alter_ags).update(residence_id=neuer_ags)
        PlaceChangeRequest.objects.filter(new_place_id=alter_ags).update(new_place_id=neuer_ags)
        PlaceChangeRequest.objects.filter(old_place_id=alter_ags).update(old_place_id=neuer_ags)
        Place.objects.filter(pk=alter_ags).delete()
        for user in affected:
            if user.email:
                mail.send(user.email, "place_merged", {"new_place": new})
        self.stdout.write(self.style.SUCCESS(f"{alter_ags} → {neuer_ags}: {len(affected)} Konten umgestellt."))
