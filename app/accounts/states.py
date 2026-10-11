"""Wirksamer Kontozustand und Berechtigungstabelle (PROJEKT.md, Abschnitt 6).

Der Zustand wird bei jedem Zugriff aus den Merkmalen am Konto und der
aktuellen Zeit berechnet, nie aus einem Tagesjob.
"""

from dataclasses import dataclass
from datetime import datetime

from django.utils import timezone

UNVERIFIED = "unverified"                # unbestätigt
AWAITING_APPROVAL = "awaiting_approval"  # wartet auf Freigabe
ACTIVE = "active"                        # aktiv
MUTED = "muted"                          # stummgeschaltet
SUSPENDED = "suspended"                  # gesperrt
DELETED = "deleted"                      # gelöscht


@dataclass(frozen=True)
class Permissions:
    login: bool                 # darf sich anmelden
    status_page_only: bool      # sieht nur die Statusseite
    visible: bool               # sichtbar für andere
    counted: bool               # zählt in Gruppen
    conversations: bool         # bestehende Gespräche nutzbar
    send_requests: bool         # neue Anfragen senden
    receive_requests: bool      # Anfragen empfangen
    appeal: bool                # Einspruch möglich


MATRIX: dict[str, Permissions] = {
    UNVERIFIED: Permissions(False, False, False, False, False, False, False, False),
    AWAITING_APPROVAL: Permissions(True, True, False, False, False, False, False, False),
    ACTIVE: Permissions(True, False, True, True, True, True, True, False),
    MUTED: Permissions(True, False, True, True, True, False, True, True),
    SUSPENDED: Permissions(False, False, False, False, False, False, False, True),
    DELETED: Permissions(False, False, False, False, False, False, False, False),
}


def effective_state(user, now: datetime | None = None) -> str:
    now = now or timezone.now()
    if user.status == "deleted":
        return DELETED
    if user.status == "suspended":
        return SUSPENDED
    if user.status == "pending":
        return UNVERIFIED if user.email_verified_at is None else AWAITING_APPROVAL
    if user.muted_until is not None and user.muted_until > now:
        return MUTED
    return ACTIVE


def permissions(user, now: datetime | None = None) -> Permissions:
    return MATRIX[effective_state(user, now)]


def apply_activation(user) -> bool:
    """Schaltet ein Konto aktiv, sobald alle nötigen Freigaben vorliegen."""
    if user.status != "pending" or user.email_verified_at is None:
        return False
    if user.approval_required and user.approved_at is None:
        return False
    user.status = "active"
    return True


def activated_at(user) -> datetime | None:
    """Zeitpunkt, seit dem das Konto aktiv ist (für die 7-Tage-Regel beim Melden)."""
    if user.status != "active" or user.email_verified_at is None:
        return None
    if user.approval_required and user.approved_at is not None:
        return max(user.email_verified_at, user.approved_at)
    return user.email_verified_at
