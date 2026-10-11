"""Kontaktanfragen, Konversationen, Nachrichten und Blockierungen.

Sperrstrategie (PROJEKT.md, Abschnitt 7): Alles, was zwei Konten betrifft,
sperrt zuerst beide Nutzerdatensätze in ID-Reihenfolge (``FOR UPDATE``).
Damit sind Anfrage, Annahme und Blockieren gegeneinander serialisiert und
können sich nicht gegenseitig verklemmen. Nachrichten sperren den
Konversationsdatensatz; Blockieren sperrt denselben Datensatz.
"""

from datetime import datetime, time, timedelta

from django.conf import settings
from django.db import IntegrityError, connection, transaction
from django.db.models import Count, Max, OuterRef, Q, Subquery
from django.utils import timezone

from accounts import states
from accounts.models import User
from accounts.services import contains_link, public_user_json, touch_activity
from deletion import journal
from heimatsignale.errors import ApiError, not_found, validation
from jobs import stats
from accounts.net import hit
from nearby.visibility import is_blocked_between, is_visible, visible_ids

from .models import Block, ContactRequest, Conversation, Message, RequestAttempt

OPEN, ACCEPTED, DECLINED, WITHDRAWN, EXPIRED = "open", "accepted", "declined", "withdrawn", "expired"
ACTIVE = (OPEN, DECLINED)


# -- Hilfen -------------------------------------------------------------------
def lock_users(*ids) -> dict:
    """Sperrt Nutzerdatensätze in ID-Reihenfolge und liefert sie frisch gelesen."""
    # FOR NO KEY UPDATE: verträgt sich mit den Fremdschlüsselprüfungen anderer
    # Transaktionen (etwa beim Einfügen einer Nachricht) und verklemmt sich nicht mit ihnen.
    rows = User.objects.select_for_update(no_key=True).filter(pk__in=set(ids)).order_by("id")
    return {u.id: u for u in rows}


def _pair(a_id, b_id) -> tuple:
    return (a_id, b_id) if str(a_id) < str(b_id) else (b_id, a_id)


def _start_of_today() -> datetime:
    return timezone.make_aware(datetime.combine(timezone.localdate(), time.min))


def quota(user: User, now: datetime | None = None) -> dict:
    now = now or timezone.now()
    today = ContactRequest.objects.filter(from_user=user, created_at__gte=_start_of_today()).count()
    active = ContactRequest.objects.filter(from_user=user, status__in=ACTIVE, expires_at__gt=now).count()
    return {
        "today_used": today, "today_max": settings.REQUEST_DAILY_MAX,
        "active_used": active, "active_max": settings.REQUEST_ACTIVE_MAX,
    }


def _take_attempt(from_id, to_id) -> bool:
    """Atomarer Versuchszähler: höchstens zwei Versuche pro Richtung."""
    with connection.cursor() as cur:
        cur.execute(
            """
            INSERT INTO request_attempts (from_user, to_user, count) VALUES (%s, %s, 1)
            ON CONFLICT (from_user, to_user) DO UPDATE SET count = request_attempts.count + 1
            WHERE request_attempts.count < %s
            RETURNING count
            """,
            [from_id, to_id, settings.REQUEST_ATTEMPTS_MAX],
        )
        return cur.fetchone() is not None


def _clean_body(body: str, maximum: int, field: str = "body") -> str:
    body = (body or "").strip()
    if not body:
        raise validation({field: "Bitte schreibe einen Text."})
    if len(body) > maximum:
        raise validation({field: f"Der Text darf höchstens {maximum} Zeichen lang sein."})
    return body


# -- Anfragen -----------------------------------------------------------------
def _accept_locked(req: ContactRequest, now: datetime) -> Conversation:
    """Nimmt eine Anfrage an. Beide Nutzerdatensätze müssen bereits gesperrt sein."""
    a, b = _pair(req.from_user_id, req.to_user_id)
    conv, created = Conversation.objects.get_or_create(user_a_id=a, user_b_id=b)
    if not created and conv.blocked:
        conv.blocked = False
        conv.save(update_fields=["blocked"])
    Message.objects.create(conversation=conv, sender_id=req.from_user_id, body=req.body, created_at=now)
    created_day = timezone.localtime(req.created_at).date()
    req.status, req.decided_at = ACCEPTED, now
    req.save(update_fields=["status", "decided_at"])
    # Eine noch offene Anfrage in Gegenrichtung ist damit erledigt.
    ContactRequest.objects.filter(
        from_user_id=req.to_user_id, to_user_id=req.from_user_id, status__in=ACTIVE
    ).update(status=WITHDRAWN, decided_at=now)
    stats.bump("requests_accepted")
    stats.bump("requests_accepted_cohort", day=created_day)
    if created:
        stats.bump("conversations_started")
    return conv


def send_request(sender: User, to_user_id, body: str) -> dict:
    body = _clean_body(body, settings.REQUEST_BODY_MAX)
    if contains_link(body):
        raise validation({"body": "Anfragen dürfen keine Links enthalten."})
    if str(to_user_id) == str(sender.id):
        raise not_found()
    now = timezone.now()
    try:
        with transaction.atomic():
            users = lock_users(sender.id, to_user_id)
            me, other = users.get(sender.id), users.get(to_user_id)
            if me is None or other is None:
                raise not_found()
            state = states.effective_state(me, now)
            if state == states.MUTED:
                raise ApiError(403, "muted", "Du kannst gerade keine neuen Anfragen senden.")
            if not states.MATRIX[state].send_requests:
                raise ApiError(403, "state_forbidden", "Das ist mit deinem Konto gerade nicht möglich.")
            if not states.permissions(other, now).receive_requests or not is_visible(me, other.id):
                raise not_found()

            a, b = _pair(me.id, other.id)
            if Conversation.objects.filter(user_a_id=a, user_b_id=b, blocked=False).exists():
                raise ApiError(409, "connected", "Ihr seid bereits im Gespräch.")

            # Abgelaufene Anfragen werden bei Zugriff aus dem Zeitstempel erkannt.
            ContactRequest.objects.filter(
                Q(from_user=me, to_user=other) | Q(from_user=other, to_user=me), status__in=ACTIVE, expires_at__lte=now
            ).update(status=EXPIRED)

            # Gegenseitige Anfragen gelten beide als angenommen.
            # Das gilt auch, wenn die frühere Anfrage abgelehnt war: Für die Gegenseite war sie
            # die ganze Zeit "offen", und so verrät eine spätere Gegenanfrage die Ablehnung nicht.
            reverse = ContactRequest.objects.select_for_update().filter(from_user=other, to_user=me, status__in=ACTIVE).first()
            if reverse is not None:
                conv = _accept_locked(reverse, now)
                touch_activity(me)
                return {"request_id": None, "conversation_id": str(conv.id)}

            if ContactRequest.objects.filter(from_user=me, to_user=other, status__in=ACTIVE).exists():
                raise ApiError(409, "already_requested", "Du hast diese Person bereits angefragt.")

            q = quota(me, now)
            if q["today_used"] >= q["today_max"]:
                raise ApiError(400, "quota_daily", f"Du hast heute bereits {q['today_max']} Anfragen gesendet.")
            if q["active_used"] >= q["active_max"]:
                raise ApiError(400, "quota_active", f"Du hast bereits {q['active_max']} offene Anfragen.")

            if not _take_attempt(me.id, other.id):
                raise ApiError(409, "attempts_exhausted", "Du kannst diese Person nicht noch einmal anfragen.")

            req = ContactRequest.objects.create(
                from_user=me, to_user=other, body=body, created_at=now,
                expires_at=now + timedelta(days=settings.REQUEST_TTL_DAYS),
            )
            stats.bump("requests_sent")
            touch_activity(me)
            return {"request_id": str(req.id), "conversation_id": None}
    except IntegrityError:
        # Der partielle Unique-Index hat eine doppelte Anfrage abgefangen.
        raise ApiError(409, "already_requested", "Du hast diese Person bereits angefragt.") from None


def accept_request(user: User, request_id) -> Conversation:
    now = timezone.now()
    with transaction.atomic():
        peek = ContactRequest.objects.filter(pk=request_id, to_user=user).values("from_user_id").first()
        if peek is None:
            raise not_found()
        users = lock_users(user.id, peek["from_user_id"])
        me, other = users.get(user.id), users.get(peek["from_user_id"])
        req = ContactRequest.objects.select_for_update().filter(pk=request_id, to_user=user).first()
        if req is None or me is None or other is None or req.status != OPEN or req.expires_at <= now:
            raise not_found()
        if not states.permissions(me, now).receive_requests:
            raise ApiError(403, "state_forbidden", "Das ist mit deinem Konto gerade nicht möglich.")
        if not states.permissions(other, now).visible or is_blocked_between(me.id, other.id):
            raise not_found()
        conv = _accept_locked(req, now)
        touch_activity(me)
        return conv


def decline_request(user: User, request_id) -> None:
    now = timezone.now()
    changed = ContactRequest.objects.filter(
        pk=request_id, to_user=user, status=OPEN, expires_at__gt=now
    ).update(status=DECLINED, decided_at=now)
    if not changed:
        raise not_found()
    touch_activity(user)


def withdraw_request(user: User, request_id) -> None:
    now = timezone.now()
    mine = ContactRequest.objects.filter(pk=request_id, from_user=user, status__in=ACTIVE, expires_at__gt=now)
    if not mine.exists():
        raise not_found()
    journal.record("request", request_id)
    changed = mine.update(
        status=WITHDRAWN, decided_at=timezone.now()
    )
    if not changed:
        raise not_found()
    journal.confirm("request", request_id)


def list_requests(user: User) -> dict:
    now = timezone.now()
    blocked_ids = set(Block.objects.filter(blocker=user).values_list("blocked_id", flat=True)) | set(
        Block.objects.filter(blocked=user).values_list("blocker_id", flat=True)
    )
    incoming = (
        ContactRequest.objects.filter(to_user=user, status=OPEN, expires_at__gt=now, from_user__status="active")
        .exclude(from_user_id__in=blocked_ids)
        .select_related("from_user__home", "from_user__residence")
        .order_by("-created_at")[:100]
    )
    # Für den Absender sind "offen" und "abgelehnt" gleichermaßen "offen".
    outgoing = (
        ContactRequest.objects.filter(from_user=user, to_user__status="active")
        .filter(Q(status__in=ACTIVE) | Q(status=EXPIRED))
        .exclude(to_user_id__in=blocked_ids)
        .select_related("to_user__home", "to_user__residence")
        .order_by("-created_at")[:100]
    )
    # Wer inzwischen außerhalb des Umkreises wohnt, erscheint auch hier nicht mehr.
    incoming, outgoing = list(incoming), list(outgoing)
    visible = visible_ids(user, [r.from_user_id for r in incoming] + [r.to_user_id for r in outgoing])
    incoming = [r for r in incoming if r.from_user_id in visible]
    outgoing = [r for r in outgoing if r.to_user_id in visible]
    return {
        "incoming": [
            {"id": str(r.id), "from": public_user_json(r.from_user), "body": r.body,
             "created_at": r.created_at, "expires_at": r.expires_at}
            for r in incoming
        ],
        "outgoing": [
            {"id": str(r.id), "to": public_user_json(r.to_user), "body": r.body, "created_at": r.created_at,
             "expires_at": r.expires_at,
             "state": "open" if r.status in ACTIVE and r.expires_at > now else "expired"}
            for r in outgoing
        ],
        "quota": quota(user, now),
    }


# -- Blockieren ---------------------------------------------------------------
def block(user: User, target_id) -> None:
    if str(target_id) == str(user.id):
        raise not_found()
    now = timezone.now()
    with transaction.atomic():
        users = lock_users(user.id, target_id)
        target = users.get(target_id)
        if user.id not in users or target is None or target.status != "active":
            raise not_found()
        a, b = _pair(user.id, target.id)
        # Blockieren kann man nur, wen man kennt: im Umkreis sichtbar, im Gespräch
        # oder über eine Anfrage. Sonst wäre das Blockieren ein Weg, fremde Konten abzufragen.
        known = (
            is_visible(user, target.id)
            or Block.objects.filter(blocker_id=user.id, blocked_id=target.id).exists()
            or Conversation.objects.filter(user_a_id=a, user_b_id=b).exists()
            or ContactRequest.objects.filter(
                Q(from_user_id=user.id, to_user_id=target.id) | Q(from_user_id=target.id, to_user_id=user.id)
            ).exists()
        )
        if not known:
            raise not_found()
        # Derselbe Datensatz, den auch das Senden einer Nachricht sperrt.
        conv = Conversation.objects.select_for_update().filter(user_a_id=a, user_b_id=b).first()
        Block.objects.get_or_create(blocker_id=user.id, blocked_id=target.id)
        ContactRequest.objects.filter(
            Q(from_user_id=user.id, to_user_id=target.id) | Q(from_user_id=target.id, to_user_id=user.id),
            status__in=ACTIVE,
        ).update(status=WITHDRAWN, decided_at=now)
        if conv is not None and not conv.blocked:
            conv.blocked = True
            conv.save(update_fields=["blocked"])


def unblock(user: User, target_id) -> None:
    Block.objects.filter(blocker_id=user.id, blocked_id=target_id).delete()


def list_blocks(user: User) -> list[dict]:
    rows = Block.objects.filter(blocker=user).select_related("blocked").order_by("-created_at")
    return [{"user_id": str(r.blocked_id), "nickname": r.blocked.nickname, "created_at": r.created_at} for r in rows]


# -- Konversationen -----------------------------------------------------------
def _conversation_for(user: User, conversation_id, lock: bool = False) -> Conversation:
    qs = Conversation.objects.select_for_update() if lock else Conversation.objects
    conv = qs.filter(Q(user_a=user) | Q(user_b=user), pk=conversation_id).first()
    if conv is None:
        raise not_found()
    return conv


def _available(conv: Conversation, user: User, partner: User | None, now: datetime) -> bool:
    """Ist das Gespräch für ``user`` nutzbar? Sonst: "Gespräch nicht mehr verfügbar"."""
    if conv.blocked or partner is None:
        return False
    if not states.permissions(user, now).conversations or not states.permissions(partner, now).conversations:
        return False
    return not is_blocked_between(user.id, partner.id)


def list_conversations(user: User) -> list[dict]:
    now = timezone.now()
    convs = list(
        Conversation.objects.filter(Q(user_a=user) | Q(user_b=user))
        .annotate(last_at=Max("messages__created_at"))
        .order_by("-last_at", "-created_at")[:200]
    )
    partners = User.objects.select_related("home", "residence").in_bulk([c.partner_id(user.id) for c in convs])
    items = []
    for conv in convs:
        partner = partners.get(conv.partner_id(user.id))
        available = _available(conv, user, partner, now)
        last = None
        if available:
            msg = conv.messages.order_by("-created_at").first()
            if msg is not None:
                preview = msg.body if len(msg.body) <= 80 else msg.body[:79].rstrip() + "…"
                last = {"preview": preview, "created_at": msg.created_at, "mine": msg.sender_id == user.id}
        items.append({
            "id": str(conv.id),
            "partner": public_user_json(partner) if available else None,
            "available": available,
            "last_message": last,
            "created_at": conv.created_at,
        })
    return items


def _message_json(msg: Message, user: User) -> dict:
    return {"id": str(msg.id), "mine": msg.sender_id == user.id, "body": msg.body, "created_at": msg.created_at}


def list_messages(user: User, conversation_id, before=None) -> dict:
    now = timezone.now()
    conv = _conversation_for(user, conversation_id)
    partner = User.objects.select_related("home", "residence").filter(pk=conv.partner_id(user.id)).first()
    if not _available(conv, user, partner, now):
        return {"partner": None, "available": False, "links_allowed": False, "messages": [], "has_more": False}
    qs = conv.messages.order_by("-created_at", "-id")
    if before:
        anchor = conv.messages.filter(pk=before).values_list("created_at", flat=True).first()
        if anchor is not None:
            qs = qs.filter(created_at__lt=anchor)
    size = settings.PAGE_SIZE
    rows = list(qs[: size + 1])
    return {
        "partner": public_user_json(partner),
        "available": True,
        "links_allowed": _links_allowed(conv),
        "messages": [_message_json(m, user) for m in reversed(rows[:size])],
        "has_more": len(rows) > size,
    }


def _links_allowed(conv: Conversation) -> bool:
    """Links erst nach 10 ausgetauschten Nachrichten: beide Seiten müssen geschrieben haben."""
    per_sender = dict(conv.messages.values_list("sender_id").annotate(n=Count("id")))
    return sum(per_sender.values()) >= settings.LINKS_AFTER_MESSAGES and len(per_sender) >= 2


def _count_recurring(conv: Conversation, now: datetime) -> None:
    """Pilot-Kennzahl: beide Seiten an mindestens 3 Tagen innerhalb von 14 Tagen nach Beginn."""
    if conv.recurring_counted or now > conv.created_at + timedelta(days=14):
        return
    days: dict = {conv.user_a_id: set(), conv.user_b_id: set()}
    for sender_id, created_at in conv.messages.values_list("sender_id", "created_at"):
        days.setdefault(sender_id, set()).add(timezone.localtime(created_at).date())
    if all(len(d) >= 3 for d in days.values()):
        conv.recurring_counted = True
        conv.save(update_fields=["recurring_counted"])
        stats.bump("conversations_recurring")
        stats.bump("conversations_recurring_cohort", day=timezone.localtime(conv.created_at).date())


def send_message(user: User, conversation_id, body: str) -> dict:
    body = _clean_body(body, settings.MESSAGE_BODY_MAX)
    now = timezone.now()
    with transaction.atomic():
        conv = _conversation_for(user, conversation_id, lock=True)
        me = User.objects.get(pk=user.pk)
        partner = User.objects.filter(pk=conv.partner_id(user.id)).first()
        if not _available(conv, me, partner, now):
            raise ApiError(403, "unavailable", "Dieses Gespräch ist nicht mehr verfügbar.")
        if contains_link(body) and not _links_allowed(conv):
            raise validation({"body": f"Links sind erst nach {settings.LINKS_AFTER_MESSAGES} ausgetauschten Nachrichten möglich."})
        # Gezählt wird das Senden, nicht der Bestand: Löschen schafft keinen neuen Platz.
        if not hit(f"messages:{conv.id}", settings.MESSAGES_PER_HOUR):
            raise ApiError(429, "rate_limited", "Das sind sehr viele Nachrichten. Bitte warte etwas.", retry_after=600)
        msg = Message.objects.create(conversation=conv, sender=me, body=body, created_at=now)
        _count_recurring(conv, now)
    # Erst nach dem Commit: Innerhalb der Transaktion würde das Schreiben am
    # Nutzerdatensatz die Sperrreihenfolge gegenüber dem Blockieren umkehren.
    touch_activity(me)
    return _message_json(msg, user)


def delete_message(user: User, message_id) -> None:
    """Eigene Nachricht löschen: erst Journal, dann für beide Seiten entfernen."""
    if not Message.objects.filter(pk=message_id, sender=user).exists():
        raise not_found()
    journal.record("message", message_id)
    Message.objects.filter(pk=message_id, sender=user).delete()
    journal.confirm("message", message_id)


def inbox_summary(user: User) -> dict:
    now = timezone.now()
    blocked_ids = set(Block.objects.filter(blocker=user).values_list("blocked_id", flat=True)) | set(
        Block.objects.filter(blocked=user).values_list("blocker_id", flat=True)
    )
    senders = list(
        ContactRequest.objects.filter(to_user=user, status=OPEN, expires_at__gt=now, from_user__status="active")
        .exclude(from_user_id__in=blocked_ids).values_list("from_user_id", flat=True)[:100]
    )
    incoming = len(visible_ids(user, senders))
    last = Message.objects.filter(conversation=OuterRef("pk")).order_by("-created_at")
    convs = (
        Conversation.objects.filter(Q(user_a=user) | Q(user_b=user), blocked=False)
        .filter(user_a__status="active", user_b__status="active")
        .exclude(Q(user_a_id__in=blocked_ids) | Q(user_b_id__in=blocked_ids))
        .annotate(last_at=Subquery(last.values("created_at")[:1]), last_sender=Subquery(last.values("sender_id")[:1]))
        .filter(last_at__isnull=False)[:200]
    )
    items = [
        {"id": str(conv.id), "last_message_at": conv.last_at, "last_message_mine": conv.last_sender == user.id}
        for conv in convs
    ]
    return {"incoming_requests": incoming, "conversations": items}


# -- Profil -------------------------------------------------------------------
def profile(viewer: User, user_id) -> dict:
    """Profil eines anderen Nutzers samt Beziehung. 404, wenn nicht sichtbar."""
    now = timezone.now()
    other = User.objects.select_related("home", "residence").filter(pk=user_id, status="active").first()
    if other is None or other.id == viewer.id:
        raise not_found()
    a, b = _pair(viewer.id, other.id)
    conv = Conversation.objects.filter(user_a_id=a, user_b_id=b, blocked=False).first()
    # Eine Blockierung, gleich in welche Richtung, macht das Profil unsichtbar.
    if is_blocked_between(viewer.id, other.id):
        raise not_found()
    blocked_by_me = False
    in_radius = is_visible(viewer, other.id)
    if not in_radius and conv is None:
        raise not_found()

    outgoing = ContactRequest.objects.filter(from_user=viewer, to_user=other).filter(
        Q(status__in=ACTIVE) | Q(status=EXPIRED)
    ).order_by("-created_at").first()
    outgoing_json = None
    outgoing_active = False
    if outgoing is not None:
        outgoing_active = outgoing.status in ACTIVE and outgoing.expires_at > now
        outgoing_json = {
            "id": str(outgoing.id), "state": "open" if outgoing_active else "expired", "expires_at": outgoing.expires_at,
        }
    incoming_id = ContactRequest.objects.filter(
        from_user=other, to_user=viewer, status=OPEN, expires_at__gt=now
    ).values_list("id", flat=True).first()

    reason = None
    q = quota(viewer, now)
    attempts = RequestAttempt.objects.filter(from_user_id=viewer.id, to_user_id=other.id).values_list("count", flat=True).first() or 0
    if not in_radius:
        reason = "not_visible"
    elif conv is not None:
        reason = "connected"
    elif states.effective_state(viewer, now) == states.MUTED:
        reason = "muted"
    elif outgoing_active:
        reason = "already_requested"
    elif incoming_id is None and attempts >= settings.REQUEST_ATTEMPTS_MAX:
        reason = "attempts_exhausted"
    elif incoming_id is None and q["today_used"] >= q["today_max"]:
        reason = "quota_daily"
    elif incoming_id is None and q["active_used"] >= q["active_max"]:
        reason = "quota_active"

    return {
        "user": public_user_json(other),
        "relation": {
            "can_request": reason is None,
            "request_blocked_reason": reason,
            "outgoing_request": outgoing_json,
            "incoming_request_id": str(incoming_id) if incoming_id else None,
            "conversation_id": str(conv.id) if conv else None,
            "blocked_by_me": blocked_by_me,
        },
    }
