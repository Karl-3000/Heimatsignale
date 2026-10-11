"""Gemeinsame Hilfen für die Tests."""

import itertools
import json
from datetime import timedelta

from django.test import Client, TestCase, TransactionTestCase
from django.utils import timezone

from accounts import pow
from accounts.models import Moderator, User
from places.models import Place, normalize

# Echte Gemeindemittelpunkte. Entfernungen zu Marl: Recklinghausen ca. 8 km,
# Dorsten ca. 10 km, Haltern ca. 11 km, Münster ca. 50 km.
PLACES = [
    ("05562024", "Marl", "Recklinghausen", 51.65821, 7.10181),
    ("05562032", "Recklinghausen", "Recklinghausen", 51.61379, 7.19738),
    ("05562012", "Dorsten", "Recklinghausen", 51.66008, 6.96514),
    ("05562016", "Haltern am See", "Recklinghausen", 51.74297, 7.18163),
    ("05515000", "Münster", "Münster", 51.96236, 7.62571),
    ("09780139", "Sonthofen", "Oberallgäu", 47.51239, 10.28120),
    ("09780124", "Immenstadt i.Allgäu", "Oberallgäu", 47.55996, 10.21394),
    ("09163000", "Rosenheim", "Rosenheim", 47.85637, 12.12247),
    ("14524120", "Hohenstein-Ernstthal", "Zwickau", 50.80088, 12.71315),
    ("14713000", "Leipzig", "Leipzig", 51.33962, 12.37129),
    ("15003000", "Magdeburg", "Magdeburg", 52.13160, 11.64030),
    # Künstliche Orte für die Radiusgrenze: genau nördlich von "Mitte".
    ("99000001", "Mitte", "Testkreis", 51.00000, 9.00000),
    ("99000002", "Knappdrin", "Testkreis", 51.17800, 9.00000),   # ca. 19,8 km
    ("99000003", "Knappdraussen", "Testkreis", 51.18200, 9.00000),  # ca. 20,2 km
    ("99000004", "Fasthundert", "Testkreis", 51.89400, 9.00000),    # ca. 99,5 km
    ("99000005", "Ueberhundert", "Testkreis", 51.90500, 9.00000),   # ca. 100,7 km
]

MARL, RECKLINGHAUSEN, DORSTEN, HALTERN, MUENSTER = "05562024", "05562032", "05562012", "05562016", "05515000"
SONTHOFEN, IMMENSTADT, ROSENHEIM, HOHENSTEIN, LEIPZIG, MAGDEBURG = (
    "09780139", "09780124", "09163000", "14524120", "14713000", "15003000",
)
MITTE, KNAPP_DRIN, KNAPP_DRAUSSEN = "99000001", "99000002", "99000003"
FAST_100, UEBER_100 = "99000004", "99000005"

PASSWORD = "ein-langes-testpasswort"
_counter = itertools.count(1)


def create_places() -> None:
    Place.objects.bulk_create(
        [
            Place(ags=ags, name=name, search_name=normalize(name), district_ags=ags[:5], district_name=district,
                  state_code=ags[:2], lat=lat, lon=lon)
            for ags, name, district, lat, lon in PLACES
        ],
        ignore_conflicts=True,
    )


def make_user(home=SONTHOFEN, residence=MARL, *, status="active", verified=True, active_days=30, **extra) -> User:
    n = next(_counter)
    now = timezone.now()
    defaults = dict(
        email=f"nutzer{n}@example.org", nickname=f"Stiller-Kranich-{100 + n}" if n < 800 else f"Heller-Otter-{n - 700}",
        birth_year=1990, adult_self_declared_at=now.date(), home_id=home, residence_id=residence, status=status,
        email_verified_at=now - timedelta(days=active_days) if verified else None,
        created_at=now - timedelta(days=active_days), nickname_rerolls_left=0,
    )
    defaults.update(extra)
    email = defaults.pop("email")
    return User.objects.create_user(email=email, password=PASSWORD, **defaults)


def make_admin(role="admin") -> User:
    user = make_user(home=None, residence=None)
    Moderator.objects.create(user=user, role=role)
    return user


class Api:
    """Dünner JSON-Client. ``login`` meldet über die Sitzung an, ohne die Login-Regeln zu berühren."""

    def __init__(self, user: User | None = None, enforce_csrf: bool = False):
        self.client = Client(enforce_csrf_checks=enforce_csrf)
        if user is not None:
            self.client.force_login(user, backend="accounts.backends.ThrottledBackend")

    def get(self, path, **params):
        return self._wrap(self.client.get(f"/api{path}", params))

    def post(self, path, data=None, **headers):
        return self._wrap(self.client.post(f"/api{path}", json.dumps(data or {}), content_type="application/json", **headers))

    def delete(self, path):
        return self._wrap(self.client.delete(f"/api{path}"))

    @staticmethod
    def _wrap(response):
        try:
            response.data = json.loads(response.content) if response.content else None
        except ValueError:
            response.data = None
        return response


def solved_pow(hard: bool = False) -> str:
    return pow.solve(pow.create_challenge(hard=hard))


class PlacesMixin:
    def setUp(self):
        super().setUp()
        create_places()


class BaseTest(PlacesMixin, TestCase):
    pass


class ParallelTest(PlacesMixin, TransactionTestCase):
    """Für Tests mit tatsächlich parallelen Transaktionen (eigene Verbindungen pro Thread)."""
