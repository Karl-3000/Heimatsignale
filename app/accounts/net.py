"""Client-IP, IP-Hash und Rate-Limits in festen Zeitfenstern."""

import hashlib
import hmac
import ipaddress
from datetime import datetime, timedelta, timezone as dt_timezone

from django.conf import settings
from django.db import connection
from django.utils import timezone


def client_ip(request) -> str:
    """IP des Aufrufers. Hinter Reverse-Proxys zählt nur der vertrauenswürdige Teil von X-Forwarded-For."""
    hops = settings.TRUSTED_PROXY_COUNT
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if hops > 0 and forwarded:
        parts = [p.strip() for p in forwarded.split(",") if p.strip()]
        if len(parts) >= hops:
            return parts[-hops]
    return request.META.get("REMOTE_ADDR", "") or "0.0.0.0"


def _keyed(purpose: str, value: str) -> str:
    return hmac.new(f"{settings.SECRET_KEY}|{purpose}".encode(), value.encode(), hashlib.sha256).hexdigest()[:40]


def ip_hash(ip: str) -> str:
    """Schlüsselabhängiger Hash der IP. IPv6 wird auf das /64-Netz gekürzt."""
    try:
        addr = ipaddress.ip_address(ip)
        if addr.version == 6:
            ip = str(ipaddress.ip_network(f"{ip}/64", strict=False).network_address)
    except ValueError:
        pass
    return _keyed("ip", ip)


def account_hash(email: str) -> str:
    return _keyed("account", email.strip().lower())


def hit(key: str, limit: int, window_seconds: int = 3600) -> bool:
    """Zählt einen Zugriff im laufenden Fenster. ``False`` bedeutet: Limit überschritten."""
    now = timezone.now()
    start_ts = int(now.timestamp()) // window_seconds * window_seconds
    window_start = datetime.fromtimestamp(start_ts, tz=dt_timezone.utc)
    with connection.cursor() as cur:
        cur.execute(
            """
            INSERT INTO rate_counters (key, window_start, count) VALUES (%s, %s, 1)
            ON CONFLICT (key, window_start) DO UPDATE SET count = rate_counters.count + 1
            RETURNING count
            """,
            [key, window_start],
        )
        count = cur.fetchone()[0]
    return count <= limit


def seconds_to_window_end(window_seconds: int = 3600) -> int:
    now = int(timezone.now().timestamp())
    return window_seconds - now % window_seconds


def purge_counters(older_than: timedelta = timedelta(days=1)) -> int:
    from .models import RateCounter

    return RateCounter.objects.filter(window_start__lt=timezone.now() - older_than).delete()[0]
