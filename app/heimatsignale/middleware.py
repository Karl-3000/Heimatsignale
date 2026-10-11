"""Zustands-Middleware (PROJEKT.md, Abschnitt 6 und 11).

Django kennt die Kontozustände nicht von selbst. Diese Middleware berechnet
bei jedem Zugriff den wirksamen Zustand aus den Merkmalen am Konto und der
aktuellen Zeit und erzwingt die Berechtigungstabelle. Außerdem prüft sie für
die gesamte API den CSRF-Token und setzt die Cache-Header.
"""

import json
from urllib.parse import unquote

from django.conf import settings
from django.contrib.auth import logout
from django.http import JsonResponse
from ninja.utils import check_csrf

from accounts import states

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
# Was ein Konto in der Freigabe-Warteschlange aufrufen darf: nur die Statusseite.
AWAITING_ALLOWED = {"/api/session", "/api/auth/logout", "/api/me/delete"}
STAFF_ALLOWED = {"/api/session", "/api/auth/logout"}


def _error(status: int, code: str, message: str) -> JsonResponse:
    response = JsonResponse({"code": code, "message": message}, status=status)
    response["Cache-Control"] = "private, no-store"
    return response


def _input_ok(request) -> bool:
    """Weist NUL-Zeichen, kaputte Kodierung und ungültiges JSON ab, bevor sie die Datenbank erreichen."""
    try:
        if "\x00" in unquote(request.META.get("QUERY_STRING", ""), errors="strict") or "\x00" in request.path:
            return False
        body = request.body
        if not body or not body.strip():
            return True
        if len(body) > 64 * 1024:
            return False
        text = json.dumps(json.loads(body.decode("utf-8")), ensure_ascii=False)
        text.encode("utf-8")  # einzelne Surrogate lassen sich nicht kodieren
        return "\\u0000" not in text  # json.dumps schreibt NUL immer als \\u0000
    except (ValueError, UnicodeError):
        return False


def csrf_failure(request, reason=""):
    if request.path.startswith("/api/"):
        return _error(403, "csrf_failed", "Die Sitzung konnte nicht geprüft werden. Bitte lade die Seite neu.")
    from django.views.csrf import csrf_failure as default

    return default(request, reason=reason)


class AccountStateMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.effective_state = None
        is_api = request.path.startswith("/api/")
        user = request.user

        if user.is_authenticated:
            state = states.effective_state(user)
            if not states.MATRIX[state].login:
                # unbestätigt, gesperrt, gelöscht: keine Sitzung
                logout(request)
                user = request.user
            else:
                request.effective_state = state

        if is_api:
            if not _input_ok(request):
                return _error(400, "bad_request", "Die Anfrage enthält unzulässige Zeichen oder ist kein gültiges JSON.")
            if request.method not in SAFE_METHODS and check_csrf(request) is not None:
                return _error(403, "csrf_failed", "Die Sitzung konnte nicht geprüft werden. Bitte lade die Seite neu.")
            path = request.path.rstrip("/")
            if user.is_authenticated:
                if user.is_staff and path not in STAFF_ALLOWED:
                    return _error(403, "staff_only_admin", f"Dieses Konto arbeitet im Admin-Bereich unter /{settings.ADMIN_PATH}/.")
                if request.effective_state == states.AWAITING_APPROVAL and path not in AWAITING_ALLOWED:
                    return _error(403, "awaiting_approval", "Dein Konto wartet noch auf die Freigabe.")

        response = self.get_response(request)
        if is_api:
            response["Cache-Control"] = "private, no-store"
        return response
