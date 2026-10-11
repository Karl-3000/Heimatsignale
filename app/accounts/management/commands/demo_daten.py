"""Künstliche Konten für Entwicklung, Netz-Prototyp und Browser-Tests. Nie im Pilotbetrieb verwenden."""

import random

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.utils import timezone

from accounts import nicknames
from accounts.models import User
from places.models import Place


class Command(BaseCommand):
    help = "Legt künstliche Konten rund um einen Wohnort an (nur mit DEBUG=1)."

    def add_arguments(self, parser):
        parser.add_argument("--wohnort", default="05562024", help="AGS der Mitte, Standard: Marl")
        parser.add_argument("--heimat", default="09780139", help="AGS des Heimatorts der Demo-Person, Standard: Sonthofen")
        parser.add_argument("--anzahl", type=int, default=60)
        parser.add_argument("--passwort", default="demo-passwort-123")
        parser.add_argument("--seed", type=int, default=7)

    def handle(self, *args, wohnort, heimat, anzahl, passwort, seed, **options):
        if not settings.DEBUG:
            raise CommandError("Demo-Daten gibt es nur mit DEBUG=1.")
        rng = random.Random(seed)
        centre, home = Place.objects.filter(pk=wohnort).first(), Place.objects.filter(pk=heimat).first()
        if centre is None or home is None:
            raise CommandError("Ort nicht gefunden. Wurde die Ortsliste importiert?")
        with connection.cursor() as cur:
            cur.execute(
                "SELECT b.ags FROM places a, places b WHERE a.ags = %s AND ST_DWithin(a.center, b.center, %s)",
                [wohnort, settings.RADIUS_DEFAULT_KM * 1000],
            )
            residences = [row[0] for row in cur.fetchall()]
        same_district = list(Place.objects.filter(district_ags=home.district_ags).values_list("ags", flat=True))
        same_state = list(Place.objects.filter(state_code=home.state_code).values_list("ags", flat=True)[:400])
        everywhere = list(Place.objects.order_by("?").values_list("ags", flat=True)[:300])
        now = timezone.now()

        def create(email, home_ags, residence_ags):
            if User.objects.filter(email=email).exists():
                return
            User.objects.create_user(
                email=email, password=passwort, birth_year=rng.randint(1958, 2006), adult_self_declared_at=now.date(),
                nickname=nicknames.generate_unique(lambda n: User.objects.filter(nickname=n).exists()),
                home_id=home_ags, residence_id=residence_ags, status="active", email_verified_at=now,
                nickname_rerolls_left=0,
            )

        create("demo@example.org", heimat, wohnort)
        create("demo2@example.org", heimat, rng.choice(residences))
        for i in range(anzahl):
            pool = rng.choices([[heimat], same_district, same_state, everywhere], weights=[1, 2, 4, 9])[0]
            create(f"kunst{i}@example.org", rng.choice(pool), wohnort if rng.random() < 0.45 else rng.choice(residences))
        # Einige Konten im weiteren Umland, damit die 100-km-Ansicht mehr zeigt als die 20-km-Ansicht.
        with connection.cursor() as cur:
            cur.execute(
                "SELECT b.ags FROM places a, places b WHERE a.ags = %s AND ST_DWithin(a.center, b.center, %s) "
                "AND NOT ST_DWithin(a.center, b.center, %s) ORDER BY b.ags",
                [wohnort, settings.RADIUS_METERS, settings.RADIUS_DEFAULT_KM * 1000],
            )
            outer = [row[0] for row in cur.fetchall()]
        for i in range(anzahl // 3 if outer else 0):
            pool = rng.choices([[heimat], same_district, same_state, everywhere], weights=[1, 2, 4, 9])[0]
            create(f"umland{i}@example.org", rng.choice(pool), rng.choice(outer))
        self.stdout.write(self.style.SUCCESS(
            f"Demo-Konten angelegt. Anmeldung: demo@example.org oder demo2@example.org, Passwort: {passwort}"
        ))
