"""Registrierung, Anmeldung, Passwort, Nickname und Ortsanträge."""

import re
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path

from django.conf import settings
from django.contrib.auth import login as django_login
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core import signing
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import IntegrityError, connection, transaction
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

from heimatsignale.errors import ApiError, validation
from jobs import stats
from places.models import Place
from places.services import place_json

from . import mail, nicknames, pow, states, throttle
from .models import InviteCode, PlaceChangeRequest, RegistrationIP, User
from .net import client_ip, ip_hash

AGE_BRACKETS = [(18, 24), (25, 34), (35, 44), (45, 54), (55, 64)]


# -- Darstellung ----------------------------------------------------------------
def age_range(birth_year: int | None, today: date | None = None) -> str:
    """Ungefähre Altersspanne aus dem Kalenderjahr; wird nie gespeichert."""
    if birth_year is None:
        return ""
    age = (today or timezone.localdate()).year - birth_year
    for low, high in AGE_BRACKETS:
        if age <= high:
            return f"{low}–{high}"
    return "65+"


def _member_since(user: User) -> str:
    return timezone.localtime(user.created_at).strftime("%Y-%m") if user.created_at else ""


def public_user_json(user: User) -> dict:
    """Alles, was andere von einem Nutzer sehen. Mehr Felder gibt es nicht."""
    return {
        "id": str(user.id),
        "nickname": user.nickname,
        "age_range": age_range(user.birth_year),
        "home": place_json(user.home),
        "residence": {"ags": user.residence.ags, "name": user.residence.name} if user.residence else None,
        "member_since": _member_since(user),
    }


def me_json(user: User) -> dict:
    return {
        "id": str(user.id),
        "nickname": user.nickname,
        "age_range": age_range(user.birth_year),
        "home": place_json(user.home, with_point=True),
        "residence": place_json(user.residence, with_point=True),
        "member_since": _member_since(user),
        "muted_until": user.muted_until if states.effective_state(user) == states.MUTED else None,
        "nickname_rerolls_left": user.nickname_rerolls_left,
        "is_staff": user.is_staff,
    }


# -- Registrierung --------------------------------------------------------------
@lru_cache(maxsize=1)
def _disposable_domains() -> frozenset[str]:
    path = Path(__file__).parent / "data" / "disposable_domains.txt"
    lines = path.read_text(encoding="utf-8").splitlines()
    return frozenset(line.strip().lower() for line in lines if line.strip() and not line.startswith("#"))


def is_disposable(email: str) -> bool:
    domain = email.rsplit("@", 1)[-1].lower()
    parts = domain.split(".")
    blocked = _disposable_domains()
    return any(".".join(parts[i:]) in blocked for i in range(len(parts) - 1))


def is_adult(birth_date: date, today: date | None = None) -> bool:
    today = today or timezone.localdate()
    years = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    return years >= settings.MINIMUM_AGE


def ip_over_limit(ip: str) -> bool:
    """Abgestuftes IP-Limit: 3 Registrierungen in 24 Stunden, 10 in 7 Tagen."""
    now = timezone.now()
    rows = RegistrationIP.objects.filter(ip_hash=ip_hash(ip), invite_code__isnull=True)
    if rows.filter(created_at__gt=now - timedelta(hours=24)).count() >= settings.REGISTRATION_IP_MAX_24H:
        return True
    return rows.filter(created_at__gt=now - timedelta(days=7)).count() >= settings.REGISTRATION_IP_MAX_7D


def consume_invite(code_id: int) -> bool:
    """Atomarer Verbrauch eines Einladungscodes (PROJEKT.md, Abschnitt 7)."""
    with connection.cursor() as cur:
        cur.execute(
            "UPDATE invite_codes SET used_count = used_count + 1 "
            "WHERE id = %s AND used_count < max_uses AND valid_until > now() RETURNING id",
            [code_id],
        )
        return cur.fetchone() is not None


def _new_nickname() -> str:
    return nicknames.generate_unique(lambda n: User.objects.filter(nickname=n).exists())


def _verify_link(user: User) -> str:
    token = signing.dumps({"u": str(user.id)}, salt="verify-email")
    return f"{settings.SITE_URL}/bestaetigen?token={token}"


def _reset_link(user: User) -> str:
    uid = urlsafe_base64_encode(force_bytes(str(user.id)))
    return f"{settings.SITE_URL}/passwort-neu?uid={uid}&token={default_token_generator.make_token(user)}"


def register(request, *, email: str, password: str, birth_date: date, home_ags: str, residence_ags: str,
             invite_code: str | None, accept_terms: bool, pow_payload: str | None) -> None:
    email = (email or "").strip().lower()
    fields: dict[str, str] = {}

    try:
        validate_email(email)
        if is_disposable(email):
            fields["email"] = "Bitte verwende eine dauerhafte E-Mail-Adresse, keine Wegwerf-Adresse."
    except ValidationError:
        fields["email"] = "Bitte gib eine gültige E-Mail-Adresse ein."

    try:
        validate_password(password or "", user=User(email=email))
    except ValidationError as exc:
        fields["password"] = " ".join(exc.messages)

    today = timezone.localdate()
    if birth_date > today or birth_date.year < 1900:
        fields["birth_date"] = "Bitte gib dein Geburtsdatum ein."
    elif not is_adult(birth_date, today):
        fields["birth_date"] = "Du musst mindestens 18 Jahre alt sein."

    places = Place.objects.in_bulk([home_ags, residence_ags])
    if home_ags not in places:
        fields["home_ags"] = "Bitte wähle deinen Heimatort aus der Liste."
    if residence_ags not in places:
        fields["residence_ags"] = "Bitte wähle deinen Wohnort aus der Liste."
    if not accept_terms:
        fields["accept_terms"] = "Bitte stimme den Nutzungsbedingungen zu."

    invite = None
    if invite_code and invite_code.strip():
        invite = InviteCode.objects.filter(code__iexact=invite_code.strip()).first()
        if invite is None or invite.valid_until <= timezone.now() or invite.used_count >= invite.max_uses:
            fields["invite_code"] = "Dieser Einladungscode ist ungültig oder aufgebraucht."

    if fields:
        raise validation(fields)

    ip = client_ip(request)
    with transaction.atomic():
        # Registrierungen von derselben IP laufen nacheinander, damit das Limit
        # nicht durch gleichzeitige Aufrufe unterlaufen wird.
        with connection.cursor() as cur:
            cur.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", [f"register:{ip_hash(ip)}"])
        over_limit = invite is None and ip_over_limit(ip)
        try:
            pow.verify(pow_payload, require_hard=over_limit)
        except pow.PowError as exc:
            raise ApiError(400, exc.code, "Die Sicherheitsprüfung ist abgelaufen. Bitte versuche es noch einmal.") from None

        existing = User.objects.filter(email=email).first()
        if existing is not None and _verification_expired(existing):
            existing.delete()  # verfallene, nie bestätigte Registrierung
            existing = None
        if existing is not None:
            # Nach außen dieselbe Antwort und dieselbe Wirkung auf das IP-Limit;
            # die Person erfährt es per E-Mail.
            RegistrationIP.objects.create(ip_hash=ip_hash(ip))
            User().set_password(password)
            if states.effective_state(existing) == states.UNVERIFIED:
                mail.send(email, "verify", {"link": _verify_link(existing)})
            else:
                mail.send(email, "already_registered", {"reset_link": f"{settings.SITE_URL}/passwort-vergessen"})
            return

        if invite is not None and not consume_invite(invite.id):
            raise validation({"invite_code": "Dieser Einladungscode ist ungültig oder aufgebraucht."})

        RegistrationIP.objects.create(ip_hash=ip_hash(ip), invite_code=invite)
        user = None
        for _ in range(5):
            try:
                with transaction.atomic():
                    user = User.objects.create_user(
                        email=email, password=password, nickname=_new_nickname(), birth_year=birth_date.year,
                        adult_self_declared_at=today, home=places[home_ags], residence=places[residence_ags],
                        status=User.Status.PENDING, approval_required=over_limit,
                    )
                break
            except IntegrityError:
                if User.objects.filter(email=email).exists():
                    return  # gleichzeitige Registrierung derselben Adresse
        if user is None:
            raise ApiError(503, "try_again", "Das hat gerade nicht geklappt. Bitte versuche es noch einmal.")
        stats.bump("registrations")
        mail.send(email, "verify", {"link": _verify_link(user)})


def verify_email(request, token: str) -> User:
    invalid = ApiError(400, "token_invalid", "Der Link ist ungültig, abgelaufen oder wurde schon verwendet.")
    try:
        data = signing.loads(token or "", salt="verify-email", max_age=settings.UNVERIFIED_TTL_HOURS * 3600)
    except signing.BadSignature:
        raise invalid from None
    with transaction.atomic():
        user = User.objects.select_for_update(no_key=True).filter(pk=data.get("u")).first()
        if user is None or user.status != User.Status.PENDING or user.email_verified_at is not None:
            raise invalid
        if _verification_expired(user):
            raise invalid
        user.email_verified_at = timezone.now()
        states.apply_activation(user)
        user.save(update_fields=["email_verified_at", "status"])
    django_login(request, user, backend="accounts.backends.ThrottledBackend")
    return user


def resend_verification(email: str, pow_payload: str | None) -> None:
    _require_pow(pow_payload)
    user = User.objects.filter(email=(email or "").strip().lower()).first()
    if user is not None and states.effective_state(user) == states.UNVERIFIED and not _verification_expired(user):
        mail.send(user.email, "verify", {"link": _verify_link(user)})


def _verification_expired(user: User) -> bool:
    """Unbestätigte Konten verfallen 48 Stunden nach der Registrierung, exakt nach Zeitstempel."""
    limit = timezone.now() - timedelta(hours=settings.UNVERIFIED_TTL_HOURS)
    return user.email_verified_at is None and user.created_at is not None and user.created_at <= limit


def _require_pow(pow_payload: str | None) -> None:
    try:
        pow.verify(pow_payload)
    except pow.PowError as exc:
        raise ApiError(400, exc.code, "Die Sicherheitsprüfung ist abgelaufen. Bitte versuche es noch einmal.") from None


# -- Anmeldung ------------------------------------------------------------------
def check_credentials(request, email: str, password: str, pow_payload: str | None = None, *,
                      pow_exempt: bool = False) -> User:
    """Prüft Zugangsdaten unter den Login-Regeln. Gemeinsam für App und Admin-Bereich.

    ``pow_exempt``: Der Admin-Bereich kann keinen Proof-of-Work liefern und ist durch den
    zweiten Faktor geschützt. Ohne die Ausnahme könnte jeder, der eine Admin-Adresse
    kennt, die Anmeldung dort mit 20 Fehlversuchen pro Stunde dauerhaft verhindern.
    """
    email = (email or "").strip().lower()
    ip = client_ip(request)
    error: ApiError | None = None
    user = None
    with transaction.atomic():
        throttle.serialize(email, ip)
        try:
            needs_pow = throttle.check(email, ip) and not pow_exempt
            if needs_pow:
                try:
                    pow.verify(pow_payload)
                except pow.PowError:
                    raise ApiError(403, "pow_required", "Bitte löse zuerst die Sicherheitsprüfung.") from None
            user = User.objects.filter(email=email).first() if email else None
            if user is None or not user.password:
                User().set_password(password)  # gleiche Rechenzeit wie bei einem echten Konto
                ok = False
            else:
                ok = user.check_password(password)
            if ok:
                throttle.clear(email, ip)
            else:
                throttle.record_failure(email, ip)
                raise ApiError(401, "invalid_credentials", "E-Mail-Adresse oder Passwort stimmen nicht.")
        except throttle.LoginLocked as exc:
            error = ApiError(429, "login_locked", "Zu viele Fehlversuche. Bitte warte einen Moment.",
                             retry_after=exc.retry_after)
        except ApiError as exc:
            error = exc  # erst nach dem Commit werfen, damit der Fehlversuch gezählt bleibt
    if error is not None:
        raise error
    return user


def login(request, email: str, password: str, pow_payload: str | None) -> User:
    user = check_credentials(request, email, password, pow_payload)
    state = states.effective_state(user)
    if state == states.UNVERIFIED and _verification_expired(user):
        raise ApiError(401, "invalid_credentials", "E-Mail-Adresse oder Passwort stimmen nicht.")
    if state == states.UNVERIFIED:
        raise ApiError(403, "unverified", "Bitte bestätige zuerst deine E-Mail-Adresse. Den Link haben wir dir geschickt.")
    if state == states.SUSPENDED:
        raise ApiError(
            403, "suspended",
            "Dieses Konto ist gesperrt. Einspruch ist über den Link in der E-Mail zur Sperre möglich.",
        )
    if not states.MATRIX[state].login:
        raise ApiError(401, "invalid_credentials", "E-Mail-Adresse oder Passwort stimmen nicht.")
    if user.is_staff:
        raise ApiError(403, "staff_only_admin", "Dieses Konto meldet sich im Admin-Bereich an.")
    django_login(request, user, backend="accounts.backends.ThrottledBackend")
    return user


# -- Passwort -------------------------------------------------------------------
def request_password_reset(email: str, pow_payload: str | None) -> None:
    _require_pow(pow_payload)
    user = User.objects.filter(email=(email or "").strip().lower()).first()
    if user is not None and states.effective_state(user) in {states.ACTIVE, states.MUTED, states.AWAITING_APPROVAL}:
        mail.send(user.email, "password_reset", {"link": _reset_link(user)})


def confirm_password_reset(uid: str, token: str, password: str) -> None:
    invalid = ApiError(400, "token_invalid", "Der Link ist ungültig oder abgelaufen.")
    try:
        user = User.objects.filter(pk=force_str(urlsafe_base64_decode(uid or ""))).first()
    except (ValueError, ValidationError):
        user = None
    if user is None or not user.password or not default_token_generator.check_token(user, token):
        raise invalid
    _set_password(user, password)


def _set_password(user: User, password: str) -> None:
    try:
        validate_password(password or "", user=user)
    except ValidationError as exc:
        raise validation({"password": " ".join(exc.messages)}) from None
    user.set_password(password)
    user.session_epoch += 1
    user.save(update_fields=["password", "session_epoch"])


def change_password(request, user: User, current: str, new: str) -> None:
    if not user.check_password(current or ""):
        raise validation({"current_password": "Das aktuelle Passwort stimmt nicht."})
    _set_password(user, new)
    from django.contrib.auth import update_session_auth_hash

    update_session_auth_hash(request, user)


# -- Nickname -------------------------------------------------------------------
def reroll_nickname(user: User) -> User:
    """Einmaliges Neuwürfeln, danach ist der Nickname fest."""
    for _ in range(5):
        try:
            with transaction.atomic():
                locked = User.objects.select_for_update(no_key=True).get(pk=user.pk)
                if locked.nickname_rerolls_left <= 0:
                    raise ApiError(409, "reroll_used", "Du hast bereits neu gewürfelt. Der Nickname ist jetzt fest.")
                locked.nickname = _new_nickname()
                locked.nickname_rerolls_left = 0
                locked.save(update_fields=["nickname", "nickname_rerolls_left"])
                return locked
        except IntegrityError:
            continue
    raise ApiError(503, "try_again", "Das hat gerade nicht geklappt. Bitte versuche es noch einmal.")


def confirm_nickname(user: User) -> None:
    User.objects.filter(pk=user.pk).update(nickname_rerolls_left=0)


# -- Ortsanträge ----------------------------------------------------------------
def place_change_json(req: PlaceChangeRequest) -> dict:
    return {
        "id": str(req.id),
        "field": req.field,
        "new_place": place_json(req.new_place),
        "created_at": req.created_at,
        "decided_at": req.decided_at,
        "decision": req.decision,
    }


def create_place_change(user: User, field: str, new_ags: str) -> PlaceChangeRequest:
    if field not in PlaceChangeRequest.Field.values:
        raise validation({"field": "Unbekanntes Feld."})
    place = Place.objects.filter(pk=new_ags).first()
    if place is None:
        raise validation({"new_ags": "Bitte wähle einen Ort aus der Liste."})
    current = user.home_id if field == "home" else user.residence_id
    if current == place.ags:
        raise validation({"new_ags": "Das ist bereits dein eingetragener Ort."})
    try:
        with transaction.atomic():
            return PlaceChangeRequest.objects.create(user=user, field=field, new_place=place, old_place_id=current)
    except IntegrityError:
        raise ApiError(409, "change_pending", "Für dieses Feld läuft bereits ein Antrag.") from None


# -- Aktivität ------------------------------------------------------------------
def touch_activity(user: User) -> None:
    """Setzt ``last_activity_at``. Nur der letzte Zeitstempel, kein Verlauf."""
    now = timezone.now()
    if user.last_activity_at is None or now - user.last_activity_at > timedelta(minutes=5):
        User.objects.filter(pk=user.pk).update(last_activity_at=now)
        user.last_activity_at = now


LINK_RE = re.compile(
    r"(https?://|www\.|\b[a-z0-9-]+\.(de|com|net|org|io|me|app|info|eu|at|ch|ly|gg|to|co|tv|xyz|link|page)\b)",
    re.IGNORECASE,
)


def contains_link(text: str) -> bool:
    return bool(LINK_RE.search(text or ""))
