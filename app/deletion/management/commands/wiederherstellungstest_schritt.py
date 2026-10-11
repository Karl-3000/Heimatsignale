"""Einzelschritte für ``ops/wiederherstellungstest.sh`` (echter Ablauf mit pg_dump und pg_restore)."""

import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from accounts.models import User
from contacts import services as contacts
from contacts.models import ContactRequest, Conversation, Message
from deletion.services import delete_account
from places.models import Place, normalize


class Command(BaseCommand):
    help = "Schritte des Wiederherstellungstests: vorbereiten, loeschen, pruefen."

    def add_arguments(self, parser):
        parser.add_argument("schritt", choices=["vorbereiten", "loeschen", "pruefen"])
        parser.add_argument("--datei", type=Path, required=True)

    def handle(self, *args, schritt, datei: Path, **options):
        if not settings.DEBUG:
            raise CommandError("Nur in einer Testumgebung (DEBUG=1) ausführen.")
        getattr(self, schritt)(datei)

    def _user(self, n: int, residence: str) -> User:
        return User.objects.create_user(
            email=f"restore{n}@example.org", password="ein-langes-testpasswort", nickname=f"Stiller-Kranich-{200 + n}",
            birth_year=1990, home_id="09780139", residence_id=residence, status="active",
            email_verified_at=timezone.now(), nickname_rerolls_left=0,
        )

    def vorbereiten(self, datei: Path):
        for ags, name, lat, lon in (("05562024", "Marl", 51.65821, 7.10181), ("05562032", "Recklinghausen", 51.61379, 7.19738),
                                    ("09780139", "Sonthofen", 47.51239, 10.2812)):
            Place.objects.update_or_create(ags=ags, defaults=dict(
                name=name, search_name=normalize(name), district_ags=ags[:5], district_name=name, state_code=ags[:2], lat=lat, lon=lon))
        user, friend, third = self._user(1, "05562024"), self._user(2, "05562032"), self._user(3, "05562032")
        conv = contacts.accept_request(friend, contacts.send_request(user, friend.id, "Hallo")["request_id"])
        kept = contacts.send_message(friend, conv.id, "Antwort")
        other = contacts.accept_request(third, contacts.send_request(friend, third.id, "Hallo")["request_id"])
        doomed = contacts.send_message(friend, other.id, "Diese Nachricht wird nach dem Backup gelöscht")
        fourth = self._user(4, "05562032")
        request_id = contacts.send_request(friend, fourth.id, "Diese Anfrage wird nach dem Backup zurückgezogen")["request_id"]
        datei.write_text(json.dumps({
            "user": str(user.id), "friend": str(friend.id), "conversation": str(conv.id), "kept_message": kept["id"],
            "doomed_message": doomed["id"], "request": request_id,
        }))
        self.stdout.write("Ausgangslage angelegt.")

    def loeschen(self, datei: Path):
        state = json.loads(datei.read_text())
        friend = User.objects.get(pk=state["friend"])
        delete_account(state["user"])
        contacts.delete_message(friend, state["doomed_message"])
        contacts.withdraw_request(friend, state["request"])
        self.stdout.write("Nach dem Backup gelöscht: Konto, Nachricht, Anfrage.")

    def pruefen(self, datei: Path):
        state = json.loads(datei.read_text())
        problems = []
        user = User.objects.filter(pk=state["user"]).first()
        if user is not None and (user.status != "deleted" or user.email or user.nickname):
            problems.append("Das gelöschte Konto wurde wiederbelebt.")
        if Conversation.objects.filter(pk=state["conversation"]).exists():
            problems.append("Die Konversation des gelöschten Kontos existiert wieder.")
        if Message.objects.filter(pk__in=[state["kept_message"], state["doomed_message"]]).exists():
            problems.append("Gelöschte Nachrichten existieren wieder.")
        if ContactRequest.objects.filter(pk=state["request"], status__in=["open", "declined"]).exists():
            problems.append("Die zurückgezogene Anfrage ist wieder offen.")
        if User.objects.get(pk=state["friend"]).status != "active":
            problems.append("Ein unbeteiligtes Konto wurde verändert.")
        if problems:
            raise CommandError(" ".join(problems))
        self.stdout.write(self.style.SUCCESS("Wiederherstellungstest bestanden: Nach dem Nachlauf ist nichts Gelöschtes zurück."))
