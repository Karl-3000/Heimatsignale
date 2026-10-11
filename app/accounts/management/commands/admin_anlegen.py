"""Legt ein Admin-Konto mit Zwei-Faktor-Authentifizierung (TOTP) an.

Interaktiv:        manage.py admin_anlegen
Ohne Rückfragen:   ADMIN_EMAIL=... ADMIN_PASSWORD=... manage.py admin_anlegen --ohne-rueckfragen
"""

import getpass
import os

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from django_otp.plugins.otp_static.models import StaticDevice, StaticToken
from django_otp.plugins.otp_totp.models import TOTPDevice

from accounts import nicknames
from accounts.models import Moderator, User


class Command(BaseCommand):
    help = "Legt ein Admin-Konto an und richtet die Zwei-Faktor-Authentifizierung ein."

    def add_arguments(self, parser):
        parser.add_argument("--email", default=os.environ.get("ADMIN_EMAIL"))
        parser.add_argument("--rolle", choices=["admin", "moderator"], default="admin")
        parser.add_argument("--ohne-rueckfragen", action="store_true", help="Passwort aus ADMIN_PASSWORD lesen")

    def handle(self, *args, email, rolle, ohne_rueckfragen, **options):
        if not email:
            if ohne_rueckfragen:
                raise CommandError("ADMIN_EMAIL oder --email fehlt.")
            email = input("E-Mail-Adresse: ").strip()
        email = email.strip().lower()
        if User.objects.filter(email=email).exists():
            raise CommandError("Mit dieser E-Mail-Adresse gibt es bereits ein Konto.")

        if ohne_rueckfragen:
            password = os.environ.get("ADMIN_PASSWORD")
            if not password:
                raise CommandError("ADMIN_PASSWORD fehlt.")
        else:
            password = getpass.getpass("Passwort (mindestens 12 Zeichen): ")
            if password != getpass.getpass("Passwort wiederholen: "):
                raise CommandError("Die Passwörter stimmen nicht überein.")
        try:
            validate_password(password, user=User(email=email))
        except ValidationError as exc:
            raise CommandError(" ".join(exc.messages)) from None

        with transaction.atomic():
            now = timezone.now()
            user = User.objects.create_user(
                email=email, password=password, status=User.Status.ACTIVE, email_verified_at=now,
                nickname=nicknames.generate_unique(lambda n: User.objects.filter(nickname=n).exists()),
                nickname_rerolls_left=0,
            )
            Moderator.objects.create(user=user, role=rolle)
            device = TOTPDevice.objects.create(user=user, name="Authenticator", confirmed=True)
            backup = StaticDevice.objects.create(user=user, name="Notfallcodes", confirmed=True)
            codes = [StaticToken.random_token() for _ in range(8)]
            StaticToken.objects.bulk_create([StaticToken(device=backup, token=c) for c in codes])

        out = self.stdout.write
        out(self.style.SUCCESS(f"\nAdmin-Konto angelegt: {email} (Rolle: {rolle})"))
        out(f"Anmeldung: {settings.SITE_URL}/{settings.ADMIN_PATH}/\n")
        out("Zwei-Faktor-Authentifizierung: Scanne den Code mit einer Authenticator-App")
        out("(z. B. Aegis, FreeOTP, 2FAS) oder trage den Schlüssel von Hand ein.\n")
        try:
            import qrcode

            qr = qrcode.QRCode(border=1)
            qr.add_data(device.config_url)
            qr.print_ascii(out=self.stdout, invert=True)
        except Exception:  # ohne qrcode-Paket bleibt die Adresse zum Kopieren
            pass
        out(f"Einrichtungsadresse: {device.config_url}\n")
        out("Notfallcodes (jeder gilt einmal, bitte sicher verwahren):")
        for code in codes:
            out(f"  {code}")
        out("\nDiese Ausgabe erscheint nur jetzt. Schlüssel und Notfallcodes werden nicht noch einmal angezeigt.")
