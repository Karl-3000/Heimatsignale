"""Sichtbarkeit: eine einzige Definition für Umkreis, Profile und Anfragen.

Grundmenge sind Nutzer mit ``status = 'active'`` (wirksam aktiv oder
stummgeschaltet) im Radius um den gespeicherten Wohnort des Betrachters,
abzüglich Blockierungen in beide Richtungen. Erst auf dieser Menge wird
gezählt (PROJEKT.md, Abschnitt 11).
"""

from django.conf import settings
from django.db import connection

# Erwartet die Parameter viewer_id und radius. ``u`` ist der sichtbare Nutzer.
VISIBLE_FROM = """
    FROM users u
    JOIN places rp ON rp.ags = u.residence_ags
    JOIN places hp ON hp.ags = u.home_ags
    JOIN users me ON me.id = %(viewer_id)s
    JOIN places mp ON mp.ags = me.residence_ags
    WHERE u.status = 'active'
      AND u.id <> me.id
      AND ST_DWithin(mp.center, rp.center, %(radius)s)
      AND NOT EXISTS (
          SELECT 1 FROM blocks b
          WHERE (b.blocker_id = me.id AND b.blocked_id = u.id)
             OR (b.blocker_id = u.id AND b.blocked_id = me.id)
      )
"""


def params(viewer, **extra) -> dict:
    return {"viewer_id": viewer.id, "radius": settings.RADIUS_METERS, **extra}


def is_visible(viewer, user_id) -> bool:
    """Darf ``viewer`` den Nutzer ``user_id`` im Umkreis sehen?"""
    with connection.cursor() as cur:
        cur.execute(f"SELECT 1 {VISIBLE_FROM} AND u.id = %(user_id)s", params(viewer, user_id=user_id))
        return cur.fetchone() is not None


def is_blocked_between(a_id, b_id) -> bool:
    with connection.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM blocks WHERE (blocker_id = %s AND blocked_id = %s) OR (blocker_id = %s AND blocked_id = %s)",
            [a_id, b_id, b_id, a_id],
        )
        return cur.fetchone() is not None
