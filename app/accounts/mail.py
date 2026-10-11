"""Transaktionale E-Mails. Schlicht, nur Text, konsequent Du."""

import logging

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction

log = logging.getLogger(__name__)

TEMPLATES: dict[str, tuple[str, str]] = {
    "verify": (
        "Bitte bestätige deine E-Mail-Adresse",
        "Hallo,\n\ndu hast dich bei {site} registriert. Bitte bestätige deine E-Mail-Adresse:\n\n{link}\n\n"
        "Der Link gilt 48 Stunden. Ohne Bestätigung wird das Konto danach gelöscht.\n\n"
        "Falls du dich nicht registriert hast, musst du nichts tun.\n",
    ),
    "already_registered": (
        "Du hast bereits ein Konto",
        "Hallo,\n\nmit dieser E-Mail-Adresse gibt es bereits ein Konto bei {site}. "
        "Du kannst dich hier anmelden:\n\n{login_link}\n\n"
        "Falls du dein Passwort nicht mehr weißt:\n\n{reset_link}\n\n"
        "Falls du das nicht warst, musst du nichts tun.\n",
    ),
    "password_reset": (
        "Neues Passwort festlegen",
        "Hallo,\n\nüber diesen Link legst du ein neues Passwort fest:\n\n{link}\n\n"
        "Der Link gilt zwei Stunden. Falls du das nicht angefordert hast, musst du nichts tun.\n",
    ),
    "approval_pending": (
        "Deine Registrierung wartet noch auf Freigabe",
        "Hallo,\n\ndeine Registrierung bei {site} wartet weiterhin auf die Freigabe durch unser Team. "
        "Das dauert länger als geplant, dafür bitten wir um Entschuldigung. "
        "Dein Konto bleibt in der Warteschlange, du musst nichts tun.\n",
    ),
    "approved": (
        "Dein Konto ist freigegeben",
        "Hallo,\n\ndein Konto bei {site} ist freigegeben. Du kannst dich jetzt anmelden:\n\n{login_link}\n",
    ),
    "suspended": (
        "Dein Konto wurde gesperrt",
        "Hallo,\n\ndein Konto bei {site} wurde nach Prüfung einer Meldung gesperrt.\n\n"
        "Du kannst einmal Einspruch einlegen. Den Einspruch prüft eine andere Person als die, "
        "die die Sperre entschieden hat:\n\n{link}\n",
    ),
    "appeal_decided": (
        "Entscheidung über deinen Einspruch",
        "Hallo,\n\nüber deinen Einspruch bei {site} wurde entschieden: {outcome}.\n",
    ),
    "place_change_decided": (
        "Entscheidung über deinen Ortsantrag",
        "Hallo,\n\ndein Antrag zur Änderung ({field}) bei {site} wurde {decision}.\n",
    ),
    "place_merged": (
        "Deine Gemeinde hat sich geändert",
        "Hallo,\n\neine Gemeinde, die in deinem Konto bei {site} steht, wurde durch eine Gebietsreform "
        "zusammengelegt. In deinem Profil steht jetzt: {new_place}.\n\n"
        "Falls das nicht stimmt, kannst du im Profil eine Korrektur beantragen.\n",
    ),
}


def send(to: str, template: str, context: dict | None = None) -> None:
    """Versendet nach dem Commit der laufenden Transaktion."""
    subject, body = TEMPLATES[template]
    values = {"site": settings.SITE_NAME, "login_link": f"{settings.SITE_URL}/anmelden", **(context or {})}
    text = body.format(**values)

    def _deliver():
        try:
            send_mail(f"{settings.SITE_NAME}: {subject}", text, settings.DEFAULT_FROM_EMAIL, [to])
        except Exception:  # Versandfehler dürfen keine Nutzeraktion zurückrollen
            log.exception("E-Mail-Versand fehlgeschlagen (Vorlage %s)", template)

    transaction.on_commit(_deliver)
