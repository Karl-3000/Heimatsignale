"""Die JSON-API (Django Ninja). Vertrag: docs/API.md."""

from uuid import UUID

from django.conf import settings
from django.contrib.auth import logout as django_logout
from django.http import Http404, JsonResponse
from django.middleware.csrf import get_token, rotate_token
from ninja import NinjaAPI
from ninja.errors import AuthenticationError, ValidationError

from accounts import pow, services as accounts
from accounts import states
from accounts.net import client_ip, hit, ip_hash, seconds_to_window_end
from contacts import services as contacts
from deletion.services import delete_account
from heimatsignale.errors import ApiError, validation
from moderation import services as moderation
from nearby import services as nearby
from places import services as places

from . import schemas

api = NinjaAPI(title="Heimatsignale", docs_url=None, openapi_url=None)


# -- Fehlerbehandlung ---------------------------------------------------------
@api.exception_handler(ApiError)
def _api_error(request, exc: ApiError):
    return JsonResponse(exc.body(), status=exc.status)


@api.exception_handler(ValidationError)
def _validation_error(request, exc: ValidationError):
    fields = {}
    for error in exc.errors:
        loc = [str(p) for p in error.get("loc", []) if p not in ("body", "query", "path", "data", "payload")]
        fields[".".join(loc) or "_"] = "Ungültige Angabe."
    return JsonResponse({"code": "validation", "message": "Bitte prüfe deine Eingaben.", "fields": fields}, status=422)


@api.exception_handler(AuthenticationError)
def _auth_error(request, exc):
    return JsonResponse({"code": "not_authenticated", "message": "Bitte melde dich an."}, status=401)


@api.exception_handler(Http404)
def _http_404(request, exc):
    return JsonResponse({"code": "not_found", "message": "Das gibt es nicht oder es ist für dich nicht sichtbar."}, status=404)


# -- Anmeldung für Endpunkte --------------------------------------------------
def member(request):
    """Angemeldet und wirksam aktiv oder stummgeschaltet."""
    if request.user.is_authenticated and request.effective_state in (states.ACTIVE, states.MUTED):
        return request.user
    return None


def signed_in(request):
    """Angemeldet, auch in der Freigabe-Warteschlange (nur Statusseite)."""
    return request.user if request.user.is_authenticated else None


def _limit(key: str, limit: int) -> None:
    if not hit(key, limit):
        raise ApiError(429, "rate_limited", "Das waren sehr viele Aufrufe. Bitte warte etwas.",
                       retry_after=seconds_to_window_end())


def _session_json(request) -> dict:
    user = request.user if request.user.is_authenticated else None
    return {
        "authenticated": user is not None,
        "csrf_token": get_token(request),
        "state": request.effective_state if user else None,
        "user": accounts.me_json(user) if user else None,
        "site": {
            "name": settings.SITE_NAME,
            "radius_km": settings.RADIUS_DEFAULT_KM,
            "radius_options": list(settings.RADIUS_OPTIONS_KM),
            "request_body_max": settings.REQUEST_BODY_MAX,
            "message_body_max": settings.MESSAGE_BODY_MAX,
            "poll_seconds": settings.POLL_SECONDS,
            "admin_path": f"/{settings.ADMIN_PATH}/",
        },
    }


def _fresh_session(request, user) -> dict:
    request.effective_state = states.effective_state(user)
    rotate_token(request)
    return _session_json(request)


# -- Sitzung und Konto ----------------------------------------------------------
@api.get("/session")
def session(request):
    return _session_json(request)


@api.get("/auth/challenge")
def challenge(request, purpose: str = "register"):
    _limit(f"challenge:{ip_hash(client_ip(request))}", 120)
    hard = purpose == "register" and accounts.ip_over_limit(client_ip(request))
    return pow.create_challenge(hard=hard)


@api.post("/auth/register", response={202: dict})
def register(request, data: schemas.RegisterIn):
    _limit(f"register:{ip_hash(client_ip(request))}", 30)
    accounts.register(
        request, email=data.email, password=data.password, birth_date=data.birth_date, home_ags=data.home_ags,
        residence_ags=data.residence_ags, invite_code=data.invite_code, accept_terms=data.accept_terms,
        pow_payload=data.pow,
    )
    return 202, {"ok": True}


@api.post("/auth/verify-email")
def verify_email(request, data: schemas.TokenIn):
    user = accounts.verify_email(request, data.token)
    return _fresh_session(request, user)


@api.post("/auth/resend-verification", response={202: dict})
def resend_verification(request, data: schemas.EmailPowIn):
    accounts.resend_verification(data.email, data.pow)
    return 202, {"ok": True}


@api.post("/auth/login")
def login(request, data: schemas.LoginIn):
    user = accounts.login(request, data.email, data.password, data.pow)
    return _fresh_session(request, user)


@api.post("/auth/logout", response={204: None})
def logout(request):
    django_logout(request)
    return 204, None


@api.post("/auth/password-reset", response={202: dict})
def password_reset(request, data: schemas.EmailPowIn):
    accounts.request_password_reset(data.email, data.pow)
    return 202, {"ok": True}


@api.post("/auth/password-reset/confirm", response={204: None})
def password_reset_confirm(request, data: schemas.ResetConfirmIn):
    accounts.confirm_password_reset(data.uid, data.token, data.password)
    return 204, None


@api.post("/me/nickname/reroll", auth=signed_in)
def nickname_reroll(request):
    user = accounts.reroll_nickname(request.user)
    return {"nickname": user.nickname, "nickname_rerolls_left": user.nickname_rerolls_left}


@api.post("/me/nickname/confirm", auth=signed_in, response={204: None})
def nickname_confirm(request):
    accounts.confirm_nickname(request.user)
    return 204, None


@api.post("/me/password", auth=signed_in, response={204: None})
def change_password(request, data: schemas.PasswordChangeIn):
    accounts.change_password(request, request.user, data.current_password, data.new_password)
    return 204, None


@api.post("/me/delete", auth=signed_in, response={204: None})
def delete_me(request, data: schemas.PasswordIn):
    user = request.user
    if not user.check_password(data.password or ""):
        raise validation({"password": "Das Passwort stimmt nicht."})
    delete_account(user.id)
    django_logout(request)
    return 204, None


@api.get("/me/place-changes", auth=member)
def place_changes(request):
    rows = request.user.place_change_requests.select_related("new_place").order_by("-created_at")[:20]
    return {"items": [accounts.place_change_json(r) for r in rows]}


@api.post("/me/place-changes", auth=member, response={201: dict})
def create_place_change(request, data: schemas.PlaceChangeIn):
    return 201, accounts.place_change_json(accounts.create_place_change(request.user, data.field, data.new_ags))


@api.post("/appeals", auth=member, response={201: dict})
def appeal(request, data: schemas.TextIn):
    moderation.appeal_as_muted(request.user, data.text)
    return 201, {"ok": True}


@api.post("/appeals/by-token", response={201: dict})
def appeal_by_token(request, data: schemas.TokenTextIn):
    _limit(f"appeal:{ip_hash(client_ip(request))}", 20)
    moderation.appeal_by_token(data.token, data.text)
    return 201, {"ok": True}


# -- Orte -------------------------------------------------------------------------
@api.get("/places/search")
def place_search(request, q: str = ""):
    _limit(f"places:{ip_hash(client_ip(request))}", settings.PLACE_SEARCH_PER_HOUR)
    return {"items": [places.place_json(p) for p in places.search(q[:80])]}


@api.post("/places/nearest")
def place_nearest(request, data: schemas.NearestIn):
    _limit(f"places:{ip_hash(client_ip(request))}", settings.PLACE_SEARCH_PER_HOUR)
    if not (47.0 <= data.lat <= 55.2 and 5.5 <= data.lon <= 15.3):
        raise ApiError(400, "outside_germany", "Dieser Standort liegt nicht in Deutschland.")
    # Die Koordinaten werden nur für diese eine Abfrage verwendet und nirgends gespeichert.
    return {"place": places.place_json(places.nearest(round(data.lat, 2), round(data.lon, 2)))}


# -- Umkreis und Herkunft ---------------------------------------------------------
def _nearby_guard(request) -> None:
    user = request.user
    if user.residence_id is None or user.home_id is None:
        raise ApiError(400, "no_places", "In deinem Konto fehlen Heimatort oder Wohnort.")
    _limit(f"nearby:{user.id}", settings.NEARBY_QUERIES_PER_HOUR)
    _fix_nickname(user)


def _fix_nickname(user) -> None:
    """Wer im Umkreis unterwegs ist, behält seinen Nickname: Das Neuwürfeln verfällt."""
    if user.nickname_rerolls_left > 0:
        accounts.confirm_nickname(user)
        user.nickname_rerolls_left = 0


@api.get("/nearby/overview", auth=member)
def nearby_overview(request, radius_km: int = settings.RADIUS_DEFAULT_KM):
    _nearby_guard(request)
    user = request.user
    accounts.touch_activity(user)
    return nearby.overview(user, radius_km)


@api.get("/nearby/origins", auth=member)
def nearby_origins(request, residence: str = "all", level: str = "state", parent: str | None = None,
                   radius_km: int = settings.RADIUS_DEFAULT_KM):
    _nearby_guard(request)
    return nearby.origins(request.user, residence, level, parent, radius_km)


@api.get("/nearby/people", auth=member)
def nearby_people(request, home: str, residence: str = "all", page: int = 1,
                  radius_km: int = settings.RADIUS_DEFAULT_KM):
    _nearby_guard(request)
    return nearby.people(request.user, residence, home, page, radius_km)


@api.get("/users/{user_id}", auth=member)
def user_profile(request, user_id: UUID):
    _limit(f"profile:{request.user.id}", 600)
    _fix_nickname(request.user)
    return contacts.profile(request.user, user_id)


# -- Kontaktanfragen ----------------------------------------------------------------
@api.get("/requests", auth=member)
def requests_list(request):
    return contacts.list_requests(request.user)


@api.post("/requests", auth=member, response={201: dict})
def requests_create(request, data: schemas.RequestIn):
    _fix_nickname(request.user)
    return 201, contacts.send_request(request.user, data.to_user_id, data.body)


@api.post("/requests/{request_id}/accept", auth=member)
def requests_accept(request, request_id: UUID):
    return {"conversation_id": str(contacts.accept_request(request.user, request_id).id)}


@api.post("/requests/{request_id}/decline", auth=member, response={204: None})
def requests_decline(request, request_id: UUID):
    contacts.decline_request(request.user, request_id)
    return 204, None


@api.post("/requests/{request_id}/withdraw", auth=member, response={204: None})
def requests_withdraw(request, request_id: UUID):
    contacts.withdraw_request(request.user, request_id)
    return 204, None


# -- Konversationen -----------------------------------------------------------------
@api.get("/conversations", auth=member)
def conversations(request):
    return {"items": contacts.list_conversations(request.user)}


@api.get("/conversations/{conversation_id}/messages", auth=member)
def messages(request, conversation_id: UUID, before: UUID | None = None):
    return contacts.list_messages(request.user, conversation_id, before)


@api.post("/conversations/{conversation_id}/messages", auth=member, response={201: dict})
def messages_create(request, conversation_id: UUID, data: schemas.BodyIn):
    return 201, contacts.send_message(request.user, conversation_id, data.body)


@api.delete("/messages/{message_id}", auth=member, response={204: None})
def messages_delete(request, message_id: UUID):
    contacts.delete_message(request.user, message_id)
    return 204, None


@api.get("/inbox/summary", auth=member)
def inbox_summary(request):
    return contacts.inbox_summary(request.user)


# -- Blockieren und Melden ------------------------------------------------------------
@api.get("/blocks", auth=member)
def blocks(request):
    return {"items": contacts.list_blocks(request.user)}


@api.post("/blocks", auth=member, response={204: None})
def blocks_create(request, data: schemas.BlockIn):
    contacts.block(request.user, data.user_id)
    return 204, None


@api.delete("/blocks/{user_id}", auth=member, response={204: None})
def blocks_delete(request, user_id: UUID):
    contacts.unblock(request.user, user_id)
    return 204, None


@api.post("/reports", auth=member, response={201: dict})
def reports_create(request, data: schemas.ReportIn):
    _limit(f"reports:{request.user.id}", 30)
    moderation.create_report(
        request.user, target_type=data.target_type, target_id=data.target_id,
        conversation_id=data.conversation_id, reason=data.reason, note=data.note,
    )
    return 201, {"ok": True}
