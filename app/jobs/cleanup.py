"""Aufräumen. Fristen gelten exakt aus den Zeitstempeln; dieser Job räumt nur hinterher."""

from datetime import timedelta

from django.conf import settings
from django.contrib.admin.models import LogEntry
from django.contrib.sessions.models import Session
from django.db.models import Exists, OuterRef, Q
from django.utils import timezone

from accounts import mail
from accounts.models import LoginFailure, PlaceChangeRequest, PowChallenge, RegistrationIP, User
from accounts.net import purge_counters
from adminpanel.models import AuditLog
from contacts.models import ContactRequest
from deletion import journal
from deletion.services import purge_deleted_accounts
from moderation.models import Appeal, Report

from . import stats


def _months(n: int) -> timedelta:
    return timedelta(days=round(n * 30.44))


def run(now=None) -> dict:
    now = now or timezone.now()
    out: dict[str, int] = {}

    # Anfragen: abgelaufene nachträglich markieren, später löschen; zurückgezogene löschen.
    out["requests_expired"] = ContactRequest.objects.filter(
        status__in=("open", "declined"), expires_at__lte=now
    ).update(status="expired")
    out["requests_deleted"] = ContactRequest.objects.filter(
        Q(status="expired", expires_at__lte=now - timedelta(days=settings.EXPIRED_REQUEST_KEEP_DAYS))
        | Q(status="withdrawn", decided_at__lte=now - timedelta(days=1))
    ).delete()[0]

    # Unbestätigte Konten nach 48 Stunden. Die Freigabe-Warteschlange wird nie automatisch gelöscht.
    out["unverified_deleted"] = User.objects.filter(
        status="pending", email_verified_at__isnull=True,
        created_at__lte=now - timedelta(hours=settings.UNVERIFIED_TTL_HOURS),
    ).delete()[0]

    # Hinweis an Konten, die seit 14 Tagen auf Freigabe warten (einmalig).
    waiting = User.objects.filter(
        status="pending", email_verified_at__isnull=False, approval_required=True, approved_at__isnull=True,
        approval_notice_sent_at__isnull=True, created_at__lte=now - timedelta(days=settings.APPROVAL_NOTICE_DAYS),
    )
    out["approval_notices"] = 0
    for user in waiting:
        mail.send(user.email, "approval_pending")
        User.objects.filter(pk=user.pk).update(approval_notice_sent_at=now)
        out["approval_notices"] += 1

    out["place_changes_deleted"] = PlaceChangeRequest.objects.filter(
        decided_at__lte=now - timedelta(days=settings.PLACE_CHANGE_KEEP_DAYS)
    ).delete()[0]
    out["registration_ips_deleted"] = RegistrationIP.objects.filter(
        created_at__lte=now - timedelta(days=settings.REGISTRATION_IP_KEEP_DAYS)
    ).delete()[0]
    out["login_failures_deleted"] = LoginFailure.objects.filter(created_at__lte=now - timedelta(hours=24)).delete()[0]
    out["pow_deleted"] = PowChallenge.objects.filter(expires_at__lte=now).delete()[0]
    out["rate_counters_deleted"] = purge_counters()

    # Meldungen mit Schnappschuss 12 Monate nach Abschluss, Einsprüche zusammen mit der Meldung.
    old_reports = Report.objects.filter(resolved_at__lte=now - _months(settings.REPORT_KEEP_MONTHS))
    out["appeals_deleted"] = Appeal.objects.filter(report__in=old_reports).delete()[0]
    out["appeals_deleted"] += Appeal.objects.filter(
        report__isnull=True, decided_at__lte=now - _months(settings.REPORT_KEEP_MONTHS)
    ).delete()[0]
    out["reports_deleted"] = old_reports.delete()[0]
    audit_limit = now - _months(settings.AUDIT_KEEP_MONTHS)
    out["audit_deleted"] = AuditLog.objects.filter(created_at__lte=audit_limit).delete()[0]
    out["audit_deleted"] += LogEntry.objects.filter(action_time__lte=audit_limit).delete()[0]
    Session.objects.filter(expire_date__lte=now).delete()

    # Bereinigung nach Kontolöschungen nachholen, danach verwaiste Grabsteine entfernen.
    purge_deleted_accounts()
    tombstones = User.objects.filter(status="deleted")
    referenced = (
        Exists(Report.objects.filter(Q(reported_user_id=OuterRef("pk")) | Q(resolved_by_id=OuterRef("pk"))))
        | Exists(AuditLog.objects.filter(Q(admin_id=OuterRef("pk")) | Q(target_user_id=OuterRef("pk"))))
        | Exists(Appeal.objects.filter(decided_by_id=OuterRef("pk")))
    )
    orphaned = tombstones.exclude(referenced)
    too_old = tombstones.filter(deleted_at__lte=now - _months(settings.TOMBSTONE_MAX_MONTHS))
    out["tombstones_deleted"] = orphaned.delete()[0] + too_old.delete()[0]

    out["journal_purged"] = journal.purge()
    return out


def snapshot_active_accounts(now=None) -> int:
    """Aktive Konten: Zustand aktiv oder stummgeschaltet und Aktivität in den letzten 30 Tagen."""
    now = now or timezone.now()
    count = User.objects.filter(status="active", last_activity_at__gte=now - timedelta(days=30)).count()
    stats.set_value("active_accounts", count, timezone.localtime(now).date())
    return count
