import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone

USER = settings.AUTH_USER_MODEL


class Report(models.Model):
    """Meldung mit Schnappschuss. Moderatoren sehen nie das ganze Postfach."""

    class Target(models.TextChoices):
        PROFILE = "profile", "Profil"
        REQUEST = "request", "Kontaktanfrage"
        MESSAGE = "message", "Nachricht"

    class Reason(models.TextChoices):
        DATING = "dating", "Dating/Anmache"
        HARASSMENT = "harassment", "Belästigung"
        SPAM = "spam", "Spam"
        FALSE_INFO = "false_info", "Falsche Angaben"
        OTHER = "other", "Sonstiges"

    class Outcome(models.TextChoices):
        DISMISSED = "dismissed", "kein Verstoß"
        CONFIRMED = "confirmed", "bestätigt, Konto gesperrt"
        ACCOUNT_DELETED = "account_deleted", "Konto gelöscht"

    SEVERITY = {"harassment": 4, "dating": 3, "spam": 2, "false_info": 1, "other": 0}

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reporter = models.ForeignKey(USER, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    reported_user = models.ForeignKey(USER, on_delete=models.CASCADE, related_name="reports_against")
    target_type = models.CharField("Ziel", max_length=10, choices=Target.choices)
    target_id = models.UUIDField(null=True, blank=True)
    snapshot = models.JSONField("Schnappschuss", default=dict)
    reason = models.CharField("Grund", max_length=12, choices=Reason.choices)
    severity = models.SmallIntegerField(default=0)
    note = models.TextField("Beschreibung", blank=True, max_length=1000)
    incident_key = models.CharField("Vorfall", max_length=32, db_index=True)
    created_at = models.DateTimeField(default=timezone.now)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(USER, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    outcome = models.CharField("Ergebnis", max_length=16, choices=Outcome.choices, null=True, blank=True)

    class Meta:
        db_table = "reports"
        verbose_name = "Meldung"
        verbose_name_plural = "Meldungen"
        constraints = [
            models.CheckConstraint(condition=Q(target_type__in=["profile", "request", "message"]), name="reports_target_valid"),
            models.CheckConstraint(
                condition=Q(reason__in=["dating", "harassment", "spam", "false_info", "other"]), name="reports_reason_valid"
            ),
        ]
        indexes = [models.Index(fields=["reported_user", "created_at"]), models.Index(fields=["resolved_at"])]

    def __str__(self) -> str:
        return f"{self.get_reason_display()} ({self.get_target_type_display()})"


class Appeal(models.Model):
    """Einspruch gegen Stummschaltung oder Sperre. Entscheidet eine andere Person."""

    class Outcome(models.TextChoices):
        UPHELD = "upheld", "Entscheidung bleibt"
        OVERTURNED = "overturned", "Entscheidung aufgehoben"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    report = models.ForeignKey(Report, null=True, blank=True, on_delete=models.CASCADE, related_name="appeals")
    user = models.ForeignKey(USER, on_delete=models.CASCADE, related_name="appeals")
    text = models.TextField(max_length=2000)
    created_at = models.DateTimeField(default=timezone.now)
    decided_at = models.DateTimeField(null=True, blank=True)
    decided_by = models.ForeignKey(USER, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    outcome = models.CharField("Ergebnis", max_length=12, choices=Outcome.choices, null=True, blank=True)

    class Meta:
        db_table = "appeals"
        verbose_name = "Einspruch"
        verbose_name_plural = "Einsprüche"
        constraints = [
            models.UniqueConstraint(fields=["user"], condition=Q(decided_at__isnull=True), name="appeals_one_open"),
        ]

    def __str__(self) -> str:
        return f"Einspruch von {self.user}"
