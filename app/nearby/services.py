"""Umkreis und Herkunftsgruppen. Gefiltert wird vor jeder Aggregation."""

from django.conf import settings
from django.db import connection

from accounts.models import User
from accounts.services import public_user_json
from heimatsignale.errors import ApiError, validation
from places.models import Place
from places.services import place_json
from places.states import STATES, state_name

from .visibility import VISIBLE_FROM, params

# Entfernung vom eigenen Heimatort zum Schwerpunkt der Herkunftsorte einer Gruppe.
_DISTANCE = """
    ROUND(ST_Distance(
        (SELECT center FROM places WHERE ags = me.home_ags),
        ST_Centroid(ST_Collect(hp.center::geometry))::geography
    ) / 1000)::int
"""


def _residence_filter(residence: str) -> tuple[str, dict]:
    if residence == "all":
        return "", {}
    if not (len(residence) == 8 and residence.isdigit()):
        raise validation({"residence": "Unbekannter Wohnort."})
    return " AND u.residence_ags = %(residence)s", {"residence": residence}


def check_radius(radius_km: int) -> int:
    """Der Client darf nur zwischen den festen Stufen wählen, nie einen freien Radius."""
    if radius_km not in settings.RADIUS_OPTIONS_KM:
        raise validation({"radius_km": "Diesen Umkreis gibt es nicht."})
    return radius_km


def overview(viewer: User, radius_km: int) -> dict:
    radius_km = check_radius(radius_km)
    with connection.cursor() as cur:
        cur.execute(
            f"""
            SELECT rp.ags, rp.name, rp.lat, rp.lon, hp.state_code, COUNT(*) AS n, {_DISTANCE} AS km
            {VISIBLE_FROM}
            GROUP BY rp.ags, rp.name, rp.lat, rp.lon, hp.state_code, me.home_ags
            ORDER BY rp.ags, n DESC, hp.state_code
            """,
            params(viewer, radius_km),
        )
        rows = cur.fetchall()
    residences: dict[str, dict] = {}
    for ags, name, lat, lon, state_code, count, km in rows:
        node = residences.setdefault(ags, {"ags": ags, "name": name, "lat": lat, "lon": lon, "total": 0, "states": []})
        node["total"] += count
        node["states"].append({"state_code": state_code, "count": count, "distance_km": km})
    items = sorted(residences.values(), key=lambda r: (-r["total"], r["name"]))
    return {
        "radius_km": radius_km,
        "me": {"residence": place_json(viewer.residence, with_point=True), "home": place_json(viewer.home, with_point=True)},
        "total": sum(r["total"] for r in items),
        "residences": items,
    }


def origins(viewer: User, residence: str, level: str, parent: str | None, radius_km: int) -> dict:
    radius_km = check_radius(radius_km)
    where, extra = _residence_filter(residence)
    if level == "state":
        key, name, parent = "hp.state_code", "hp.state_code", None
    elif level == "district":
        if parent not in STATES:
            raise validation({"parent": "Unbekanntes Bundesland."})
        key, name = "hp.district_ags", "hp.district_name"
        where += " AND hp.state_code = %(parent)s"
    elif level == "place":
        if not (parent and len(parent) == 5 and parent.isdigit()):
            raise validation({"parent": "Unbekannter Landkreis."})
        key, name = "hp.ags", "hp.name"
        where += " AND hp.district_ags = %(parent)s"
    else:
        raise validation({"level": "Unbekannte Stufe."})
    with connection.cursor() as cur:
        cur.execute(
            f"""
            SELECT {key} AS key, MIN({name}) AS name, COUNT(*) AS n, {_DISTANCE} AS km
            {VISIBLE_FROM} {where}
            GROUP BY {key}, me.home_ags
            ORDER BY n DESC, name
            """,
            params(viewer, radius_km, parent=parent, **extra),
        )
        rows = cur.fetchall()
    return {
        "level": level,
        "parent": parent,
        "items": [
            {"key": k, "name": state_name(n) if level == "state" else n, "count": c, "distance_km": km}
            for k, n, c, km in rows
        ],
    }


def people(viewer: User, residence: str, home: str, page: int, radius_km: int) -> dict:
    radius_km = check_radius(radius_km)
    where, extra = _residence_filter(residence)
    if not Place.objects.filter(pk=home).exists():
        raise validation({"home": "Unbekannter Ort."})
    if page < 1 or page > 1000:
        raise ApiError(400, "bad_page", "Diese Seite gibt es nicht.")
    size = settings.PAGE_SIZE
    with connection.cursor() as cur:
        cur.execute(
            f"""
            SELECT u.id {VISIBLE_FROM} {where} AND u.home_ags = %(home)s
            ORDER BY u.nickname LIMIT %(limit)s OFFSET %(offset)s
            """,
            params(viewer, radius_km, home=home, limit=size + 1, offset=(page - 1) * size, **extra),
        )
        ids = [row[0] for row in cur.fetchall()]
    has_more = len(ids) > size
    users = User.objects.select_related("home", "residence").in_bulk(ids[:size])
    return {"items": [public_user_json(users[i]) for i in ids[:size] if i in users], "page": page, "has_more": has_more}
