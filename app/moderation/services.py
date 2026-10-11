"""Melden, automatische Stummschaltung, Sperre und Einspruch (PROJEKT.md, Abschnitt 8)."""

import uuid
from datetime import timedelta

from django.conf import settings
from django.core import signing
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone

from accounts import mail, states
from accounts.models import User
from adminpanel import audit
from contacts.models import Block, ContactRequest, Conversation, Message
from heimatsignale.errors import ApiError, not_found, validation
from jobs import stats
from nearby.visibility import is_visible

from .models import Appeal, Report

DELETED_NOTE = "Inhalt vom Absender gelöscht"


def _may_report_profile(reporter: User, target: User) -> bool:
    if is_visible(reporter, target.id):
        return True
    if Block.objects.filter(blocker_id=reporter.id, blocked_id=target.id).exists():
        return True  # Melden ist auch nach dem Blockieren möglich (aus der Blockliste)
    if Conversation.objects.filter(
        Q(user_a=reporter, user_b=target) | Q(user_a=target, user_b=reporter)
    ).exists():
        return True
    return ContactRequest.objects.filter(from_user=target, to_user=reporter).exists()


def _message_snapshot(reporter: User, conv: Conversation, message: Message | None) -> dict:
    if message is None:
        return {"kind": "message", "deleted": True, "text": DELETED_NOTE}
    before = list(
        conv.messages.filter(created_at__lt=message.created_at).order_by("-created_at")[: settings.REPORT_SNAPSHOT_CONTEXT]
    )
    return {
        "kind": "message",
        "text": message.body,
        "created_at": message.created_at.isoformat(),
        "context": [
            {
                "from": "meldende Person" if m.sender_id == reporter.id else "gemeldete Person",
                "text": m.body,
                "created_at": m.created_at.isoformat(),
            }
            for m in reversed(before)
        ],
    }


def create_report(reporter: User, *, target_type: str, target_id, conversation_id, reason: str, note: str) -> None:
    if reason not in Report.Reason.values:
        raise validation({"reason": "Bitte wähle einen Grund."})
    note = (note or "").strip()
    if len(note) > 1000:
        raise validation({"note": "Die Beschreibung darf höchstens 1000 Zeichen lang sein."})
    now = timezone.now()

    if target_type == "profile":
        target = User.objects.filter(pk=target_id).exclude(status__in=["deleted", "pending"]).first()
        if target is None or target.id == reporter.id or not _may_report_profile(reporter, target):
            raise not_found()
        reported, snapshot = target, {"kind": "profile", "nickname": target.nickname}
    elif target_type == "request":
        req = ContactRequest.objects.filter(pk=target_id, to_user=reporter).select_related("from_user").first()
        if req is None:
            raise not_found()
        reported = req.from_user
        snapshot = {"kind": "request", "text": req.body, "created_at": req.created_at.isoformat()}
    elif target_type == "message":
        conv = Conversation.objects.filter(Q(user_a=reporter) | Q(user_b=reporter), pk=conversation_id).first()
        if conv is None:
            raise not_found()
        reported = User.objects.filter(pk=conv.partner_id(reporter.id)).first()
        if reported is None:
            raise not_found()
        message = conv.messages.filter(pk=target_id).first()
        if message is not None and message.sender_id == reporter.id:
            raise not_found()
        # Der Schnappschuss sichert nur, was beim Melden noch existiert.
        snapshot = _message_snapshot(reporter, conv, message)
    else:
        raise validation({"target_type": "Unbekanntes Ziel."})

    with transaction.atomic():
        User.objects.select_for_update().filter(pk=reported.pk).first()
        window = now - timedelta(days=settings.INCIDENT_WINDOW_DAYS)
        same_target = Report.objects.filter(
            reported_user=reported, target_type=target_type, target_id=target_id, created_at__gt=window
        )
        if same_target.filter(reporter=reporter).exists():
            return  # dieselbe Meldung noch einmal: stillschweigend zusammengeführt
        key = same_target.order_by("created_at").values_list("incident_key", flat=True).first() or uuid.uuid4().hex
        Report.objects.create(
            reporter=reporter, reported_user=reported, target_type=target_type, target_id=target_id,
            snapshot=snapshot, reason=reason, severity=Report.SEVERITY[reason], note=note, incident_key=key,
            created_at=now,
        )
        if reason == Report.Reason.DATING:
            stats.bump("reports_dating")
        _auto_mute(reported, now)


def _auto_mute(reported: User, now) -> bool:
    """Drei verschiedene Konten in 24 Stunden, jedes seit mindestens 7 Tagen aktiv: 48 Stunden stumm."""
    since = now - timedelta(hours=settings.MUTE_WINDOW_HOURS)
    reporter_ids = (
        Report.objects.filter(reported_user=reported, created_at__gt=since, reporter__isnull=False)
        .values_list("reporter_id", flat=True).distinct()
    )
    min_age = timedelta(days=settings.MUTE_REPORTER_MIN_ACTIVE_DAYS)
    qualified = 0
    for reporter in User.objects.filter(pk__in=list(reporter_ids)):
        since_active = states.activated_at(reporter)
        if since_active is not None and since_active <= now - min_age:
            qualified += 1
    if qualified < settings.MUTE_REPORTERS:
        return False
    updated = User.objects.filter(pk=reported.pk, status="active").filter(
        Q(muted_until__isnull=True) | Q(muted_until__lte=now)
    ).update(muted_until=now + timedelta(hours=settings.MUTE_HOURS))
    return bool(updated)


# -- Einspruch ----------------------------------------------------------------
def appeal_link(user: User) -> str:
    token = signing.dumps({"u": str(user.id)}, salt="appeal")
    return f"{settings.SITE_URL}/einspruch?token={token}"


def _create_appeal(user: User, text: str, report: Report | None) -> Appeal:
    text = (text or "").strip()
    if not text:
        raise validation({"text": "Bitte beschreibe kurz, warum du Einspruch einlegst."})
    if len(text) > 2000:
        raise validation({"text": "Der Text darf höchstens 2000 Zeichen lang sein."})
    exists = ApiError(409, "appeal_exists", "Zu diesem Vorfall liegt bereits ein Einspruch vor.")
    if report is not None and Appeal.objects.filter(user=user, report__incident_key=report.incident_key).exists():
        raise exists
    try:
        with transaction.atomic():
            return Appeal.objects.create(user=user, report=report, text=text)
    except IntegrityError:
        raise exists from None


def appeal_as_muted(user: User, text: str) -> Appeal:
    if states.effective_state(user) != states.MUTED:
        raise ApiError(400, "not_muted", "Einspruch ist nur während einer Stummschaltung möglich.")
    report = Report.objects.filter(reported_user=user).order_by("-created_at").first()
    return _create_appeal(user, text, report)


def appeal_by_token(token: str, text: str) -> Appeal:
    invalid = ApiError(400, "token_invalid", "Der Link ist ungültig oder abgelaufen.")
    try:
        data = signing.loads(token or "", salt="appeal", max_age=60 * 60 * 24 * 30)
    except signing.BadSignature:
        raise invalid from None
    user = User.objects.filter(pk=data.get("u"), status="suspended").first()
    if user is None:
        raise invalid
    report = Report.objects.filter(reported_user=user, outcome=Report.Outcome.CONFIRMED).order_by("-resolved_at").first()
    return _create_appeal(user, text, report)


# -- Entscheidungen im Admin-Bereich ---------------------------------------------
def resolve_incident(admin: User, incident_key: str, confirmed: bool, reason: str = "") -> int:
    """Schließt alle offenen Meldungen eines Vorfalls. Bestätigt bedeutet: Konto wird gesperrt."""
    now = timezone.now()
    with transaction.atomic():
        reports = list(Report.objects.select_for_update().filter(incident_key=incident_key, resolved_at__isnull=True))
        if not reports:
            return 0
        outcome = Report.Outcome.CONFIRMED if confirmed else Report.Outcome.DISMISSED
        Report.objects.filter(pk__in=[r.pk for r in reports]).update(resolved_at=now, resolved_by=admin, outcome=outcome)
        target = reports[0].reported_user
        if confirmed:
            suspend(admin, target, reason or "Vorfall bestätigt")
        else:
            audit.log(admin, "incident_dismissed", target, reason)
        return len(reports)


def suspend(admin: User, target: User, reason: str) -> None:
    updated = User.objects.filter(pk=target.pk, status="active").update(
        status="suspended", session_epoch=target.session_epoch + 1
    )
    if updated:
        audit.log(admin, "suspend", target, reason)
        if target.email:
            mail.send(target.email, "suspended", {"link": appeal_link(target)})


def unsuspend(admin: User, target: User, reason: str) -> None:
    if User.objects.filter(pk=target.pk, status="suspended").update(status="active"):
        audit.log(admin, "unsuspend", target, reason)


def mute(admin: User, target: User, hours: int, reason: str) -> None:
    User.objects.filter(pk=target.pk, status="active").update(muted_until=timezone.now() + timedelta(hours=hours))
    audit.log(admin, "mute", target, reason)


def unmute(admin: User, target: User, reason: str) -> None:
    User.objects.filter(pk=target.pk).update(muted_until=None)
    audit.log(admin, "unmute", target, reason)


def decide_appeal(admin: User, appeal: Appeal, overturned: bool, reason: str = "") -> None:
    """Über den Einspruch entscheidet eine andere Person als die Erstentscheidung."""
    if appeal.decided_at is not None:
        raise ValueError("Über diesen Einspruch wurde bereits entschieden.")
    if appeal.report is not None and appeal.report.resolved_by_id == admin.pk:
        raise PermissionError("Den Einspruch muss eine andere Person entscheiden als die Erstentscheidung.")
    with transaction.atomic():
        appeal.decided_at = timezone.now()
        appeal.decided_by = admin
        appeal.outcome = Appeal.Outcome.OVERTURNED if overturned else Appeal.Outcome.UPHELD
        appeal.save(update_fields=["decided_at", "decided_by", "outcome"])
        user = appeal.user
        if overturned:
            if user.status == "suspended":
                unsuspend(admin, user, "Einspruch erfolgreich")
            User.objects.filter(pk=user.pk).update(muted_until=None)
        audit.log(admin, "appeal_overturned" if overturned else "appeal_upheld", user, reason)
        if user.email:
            mail.send(user.email, "appeal_decided", {"outcome": appeal.get_outcome_display()})
