"""Löschdienst. Löschungen werden ausdrücklich ausgeführt, nicht über Kaskaden erhofft."""

import logging

from django.contrib.sessions.models import Session
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from accounts.models import PlaceChangeRequest, User
from contacts.models import Block, ContactRequest, Conversation, Message, RequestAttempt
from jobs import stats
from moderation.models import Appeal, Report

from . import journal

log = logging.getLogger(__name__)


def _tombstone(user_id) -> bool:
    """Schritt 1, eine Transaktion: Das Konto wird zum Grabstein und ist sofort unsichtbar."""
    with transaction.atomic():
        user = User.objects.select_for_update().filter(pk=user_id).first()
        if user is None or user.status == User.Status.DELETED:
            return False
        user.status = User.Status.DELETED
        user.deleted_at = timezone.now()
        user.email = None
        user.password = None
        user.nickname = None
        user.birth_year = None
        user.adult_self_declared_at = None
        user.home = None
        user.residence = None
        user.email_verified_at = None
        user.approval_required = False
        user.approved_at = None
        user.approval_notice_sent_at = None
        user.muted_until = None
        user.last_activity_at = None
        user.session_epoch += 1  # macht alle Sitzungen ungültig
        user.save()
        stats.bump("deletions")
    return True


def delete_account(user_id) -> None:
    """Kontolöschung: erst Journal, dann Grabstein, dann Bereinigung."""
    journal.record("account", user_id)
    _tombstone(user_id)
    journal.confirm("account", user_id)
    try:
        purge_deleted_accounts([user_id])
    except Exception:  # Die Bereinigung holt der Löschdienst spätestens binnen 24 Stunden nach.
        log.exception("Bereinigung nach Kontolöschung wird nachgeholt.")


def purge_deleted_accounts(user_ids=None) -> dict:
    """Schritt 2: entfernt alles, was an gelöschten Konten hängt. Beliebig oft wiederholbar."""
    deleted = User.objects.filter(status=User.Status.DELETED)
    if user_ids is not None:
        deleted = deleted.filter(pk__in=user_ids)
    ids = list(deleted.values_list("id", flat=True))
    counts = dict.fromkeys(("conversations", "messages", "requests", "attempts", "blocks", "place_changes", "appeals", "reports_closed"), 0)
    if not ids:
        return counts
    with transaction.atomic():
        convs = Conversation.objects.filter(Q(user_a_id__in=ids) | Q(user_b_id__in=ids))
        conv_ids = list(convs.values_list("id", flat=True))
        for conv_id in conv_ids:
            journal.record("conversation", conv_id)
        counts["messages"] = Message.objects.filter(conversation_id__in=conv_ids).delete()[0]
        counts["conversations"] = convs.delete()[0]
        counts["requests"] = ContactRequest.objects.filter(Q(from_user_id__in=ids) | Q(to_user_id__in=ids)).delete()[0]
        counts["attempts"] = RequestAttempt.objects.filter(Q(from_user_id__in=ids) | Q(to_user_id__in=ids)).delete()[0]
        counts["blocks"] = Block.objects.filter(Q(blocker_id__in=ids) | Q(blocked_id__in=ids)).delete()[0]
        counts["place_changes"] = PlaceChangeRequest.objects.filter(user_id__in=ids).delete()[0]
        counts["appeals"] = Appeal.objects.filter(user_id__in=ids).delete()[0]
        Report.objects.filter(reporter_id__in=ids).update(reporter=None)
        counts["reports_closed"] = Report.objects.filter(reported_user_id__in=ids, resolved_at__isnull=True).update(
            resolved_at=timezone.now(), outcome=Report.Outcome.ACCOUNT_DELETED
        )
    for conv_id in conv_ids:
        journal.confirm("conversation", conv_id)
    _drop_sessions(ids)
    return counts


def _drop_sessions(user_ids) -> None:
    """Räumt Sitzungsdatensätze gelöschter Konten ab (ungültig sind sie bereits)."""
    wanted = {str(i) for i in user_ids}
    for session in Session.objects.filter(expire_date__gt=timezone.now()).iterator():
        if session.get_decoded().get("_auth_user_id") in wanted:
            session.delete()


def replay(entry: dict) -> str:
    """Führt einen Journal-Eintrag erneut aus (nach dem Einspielen eines Backups)."""
    object_type, object_id = entry["object_type"], entry["object_id"]
    if object_type == "account":
        changed = _tombstone(object_id)
        purge_deleted_accounts([object_id])
        return "Konto gelöscht" if changed else "Konto war bereits gelöscht oder fehlt"
    if object_type == "message":
        n = Message.objects.filter(pk=object_id).delete()[0]
        return "Nachricht gelöscht" if n else "Nachricht fehlte bereits"
    if object_type == "conversation":
        n = Conversation.objects.filter(pk=object_id).delete()[0]
        return "Konversation gelöscht" if n else "Konversation fehlte bereits"
    if object_type == "request":
        n = ContactRequest.objects.filter(pk=object_id, status__in=("open", "declined")).update(
            status="withdrawn", decided_at=timezone.now()
        )
        return "Anfrage zurückgezogen" if n else "Anfrage war bereits erledigt oder fehlt"
    return "unbekannte Objektart"
