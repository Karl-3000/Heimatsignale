from django.db import connection

from .models import Place, normalize


def search(query: str, limit: int = 8) -> list[Place]:
    """Ortssuche für das Suchfeld: erst Namensanfang, dann Wortanfang."""
    q = normalize(query)
    if len(q) < 2:
        return []
    starts = list(Place.objects.filter(search_name__startswith=q).order_by("search_name", "ags")[:limit])
    # Exakte Treffer zuerst ("Marl" vor "Marlow").
    starts.sort(key=lambda p: (p.search_name != q, len(p.search_name), p.search_name))
    if len(starts) >= limit:
        return starts
    seen = {p.ags for p in starts}
    more = Place.objects.filter(search_name__contains=f" {q}").exclude(ags__in=seen).order_by("search_name")[: limit - len(starts)]
    return starts + list(more)


def nearest(lat: float, lon: float) -> Place | None:
    """Nächstgelegene Gemeinde. Die Koordinaten werden nicht gespeichert."""
    with connection.cursor() as cur:
        cur.execute(
            "SELECT ags FROM places ORDER BY center <-> ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography LIMIT 1",
            [lon, lat],
        )
        row = cur.fetchone()
    return Place.objects.get(pk=row[0]) if row else None


def within_radius(ags_a: str, ags_b: str, meters: int) -> bool:
    """Liegen zwei Gemeindemittelpunkte höchstens ``meters`` auseinander?"""
    with connection.cursor() as cur:
        cur.execute(
            "SELECT ST_DWithin(a.center, b.center, %s) FROM places a, places b WHERE a.ags = %s AND b.ags = %s",
            [meters, ags_a, ags_b],
        )
        row = cur.fetchone()
    return bool(row and row[0])


def place_json(place: Place | None, with_point: bool = False) -> dict | None:
    if place is None:
        return None
    data = {
        "ags": place.ags,
        "name": place.name,
        "district_ags": place.district_ags,
        "district_name": place.district_name,
        "state_code": place.state_code,
        "state_name": place.state_name,
    }
    if with_point:
        data["lat"] = place.lat
        data["lon"] = place.lon
    return data
