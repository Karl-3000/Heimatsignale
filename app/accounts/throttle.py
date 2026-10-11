"""Login-Regeln (PROJEKT.md, Abschnitt 8).

* pro Konto und IP: nach 5 Fehlversuchen 15 Minuten Sperre
* pro Konto über alle IPs: nach 20 Fehlversuchen in einer Stunde zusätzlicher
  Proof-of-Work, keine harte Sperre
* pro IP: nach 50 Fehlversuchen in einer Stunde eine Stunde Sperre
"""

from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from .models import LoginFailure
from .net import account_hash, ip_hash


class LoginLocked(Exception):
    def __init__(self, retry_after: int):
        super().__init__("login_locked")
        self.retry_after = max(1, retry_after)


def _retry_after(queryset, needed: int, window: timedelta) -> int | None:
    """Sekunden bis zum Ende der Sperre oder ``None``, wenn keine Sperre besteht."""
    now = timezone.now()
    stamps = list(queryset.filter(created_at__gt=now - window).order_by("-created_at").values_list("created_at", flat=True)[:needed])
    if len(stamps) < needed:
        return None
    return int((stamps[-1] + window - now).total_seconds()) + 1


def check(email: str, ip: str) -> bool:
    """Wirft ``LoginLocked`` bei Sperre. Rückgabe: Ist zusätzlich ein Proof-of-Work nötig?"""
    acct, iph = account_hash(email), ip_hash(ip)
    wait = _retry_after(LoginFailure.objects.filter(ip_hash=iph), settings.LOGIN_IP_FAILURES, timedelta(hours=1))
    if wait:
        raise LoginLocked(wait)
    wait = _retry_after(
        LoginFailure.objects.filter(account_hash=acct, ip_hash=iph),
        settings.LOGIN_PAIR_FAILURES,
        timedelta(minutes=settings.LOGIN_PAIR_LOCK_MINUTES),
    )
    if wait:
        raise LoginLocked(wait)
    recent = LoginFailure.objects.filter(account_hash=acct, created_at__gt=timezone.now() - timedelta(hours=1)).count()
    return recent >= settings.LOGIN_ACCOUNT_FAILURES


def record_failure(email: str, ip: str) -> None:
    LoginFailure.objects.create(account_hash=account_hash(email), ip_hash=ip_hash(ip))


def clear(email: str, ip: str) -> None:
    LoginFailure.objects.filter(account_hash=account_hash(email), ip_hash=ip_hash(ip)).delete()
