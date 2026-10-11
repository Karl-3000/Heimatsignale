"""Proof-of-Work nach dem Altcha-Protokoll (SHA-256), selbst gehostet.

Aufgabe:   challenge = sha256(salt + number), signature = HMAC(challenge)
Lösung:    Base64(JSON{algorithm, challenge, number, salt, signature})

Der Schwierigkeitsgrad steht im Salt und ist damit von der Signatur
gedeckt. Eine gelöste Aufgabe gilt genau einmal.
"""

import base64
import hashlib
import hmac
import json
import secrets
import time
from datetime import datetime, timezone as dt_timezone
from urllib.parse import parse_qs

from django.conf import settings
from django.db import IntegrityError, transaction

from .models import PowChallenge

ALGORITHM = "SHA-256"


class PowError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _sign(challenge: str) -> str:
    key = f"{settings.SECRET_KEY}|pow".encode()
    return hmac.new(key, challenge.encode(), hashlib.sha256).hexdigest()


def create_challenge(hard: bool = False) -> dict:
    maxnumber = settings.POW_MAXNUMBER_HARD if hard else settings.POW_MAXNUMBER
    expires = int(time.time()) + settings.POW_TTL_SECONDS
    salt = f"{secrets.token_hex(12)}?expires={expires}&level={'hard' if hard else 'normal'}"
    number = secrets.randbelow(maxnumber + 1)
    challenge = hashlib.sha256(f"{salt}{number}".encode()).hexdigest()
    return {
        "algorithm": ALGORITHM,
        "challenge": challenge,
        "salt": salt,
        "signature": _sign(challenge),
        "maxnumber": maxnumber,
    }


def solve(challenge: dict) -> str:
    """Löst eine Aufgabe (für Tests und Werkzeuge) und liefert die Base64-Lösung."""
    for number in range(challenge["maxnumber"] + 1):
        if hashlib.sha256(f"{challenge['salt']}{number}".encode()).hexdigest() == challenge["challenge"]:
            payload = {k: challenge[k] for k in ("algorithm", "challenge", "salt", "signature")} | {"number": number}
            return base64.b64encode(json.dumps(payload).encode()).decode()
    raise PowError("pow_invalid")


def verify(payload_b64: str | None, require_hard: bool = False) -> None:
    """Prüft und entwertet eine Lösung. Wirft ``PowError`` mit einem API-Fehlercode."""
    if not payload_b64:
        raise PowError("pow_invalid")
    try:
        data = json.loads(base64.b64decode(payload_b64, validate=True))
        salt, challenge = str(data["salt"]), str(data["challenge"])
        number, signature = int(data["number"]), str(data["signature"])
        if data.get("algorithm") != ALGORITHM:
            raise ValueError
    except (ValueError, KeyError, TypeError):
        raise PowError("pow_invalid") from None

    expected = hashlib.sha256(f"{salt}{number}".encode()).hexdigest()
    if not hmac.compare_digest(expected, challenge) or not hmac.compare_digest(_sign(challenge), signature):
        raise PowError("pow_invalid")

    params = parse_qs(salt.partition("?")[2])
    try:
        expires = int(params["expires"][0])
    except (KeyError, ValueError, IndexError):
        raise PowError("pow_invalid") from None
    if expires < time.time():
        raise PowError("pow_invalid")
    if require_hard and params.get("level", [""])[0] != "hard":
        raise PowError("pow_harder_required")

    try:
        with transaction.atomic():
            PowChallenge.objects.create(
                challenge=challenge, expires_at=datetime.fromtimestamp(expires, tz=dt_timezone.utc)
            )
    except IntegrityError:
        raise PowError("pow_invalid") from None
