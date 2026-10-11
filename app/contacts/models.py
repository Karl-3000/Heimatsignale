import uuid

from django.conf import settings
from django.db import models
from django.db.models import F, Q
from django.utils import timezone

USER = settings.AUTH_USER_MODEL


class ContactRequest(models.Model):
    """Kontaktanfrage. Zustände und Regeln: PROJEKT.md, Abschnitt 7."""

    class Status(models.TextChoices):
        OPEN = "open", "offen"
        ACCEPTED = "accepted", "angenommen"
        DECLINED = "declined", "abgelehnt"
        WITHDRAWN = "withdrawn", "zurückgezogen"
        EXPIRED = "expired", "abgelaufen"

    ACTIVE_STATES = ("open", "declined")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    from_user = models.ForeignKey(USER, on_delete=models.CASCADE, db_column="from_user", related_name="requests_sent")
    to_user = models.ForeignKey(USER, on_delete=models.CASCADE, db_column="to_user", related_name="requests_received")
    body = models.TextField(max_length=500)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN)
    created_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "contact_requests"
        constraints = [
            # Höchstens eine aktive Anfrage pro Richtung (partieller Unique-Index).
            models.UniqueConstraint(
                fields=["from_user", "to_user"], condition=Q(status__in=["open", "declined"]),
                name="contact_requests_one_active",
            ),
            models.CheckConstraint(condition=~Q(from_user=F("to_user")), name="contact_requests_not_self"),
            models.CheckConstraint(
                condition=Q(status__in=["open", "accepted", "declined", "withdrawn", "expired"]),
                name="contact_requests_status_valid",
            ),
        ]
        indexes = [
            models.Index(fields=["to_user", "status"]),
            models.Index(fields=["from_user", "created_at"]),
        ]


class RequestAttempt(models.Model):
    """Versuchszähler pro Richtung, ohne Text. Überlebt die Löschung der Anfragen."""

    pk = models.CompositePrimaryKey("from_user_id", "to_user_id")
    from_user = models.ForeignKey(USER, on_delete=models.CASCADE, db_column="from_user", related_name="+")
    to_user = models.ForeignKey(USER, on_delete=models.CASCADE, db_column="to_user", related_name="+")
    count = models.SmallIntegerField(default=0)

    class Meta:
        db_table = "request_attempts"


class Conversation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_a = models.ForeignKey(USER, on_delete=models.CASCADE, db_column="user_a", related_name="+")
    user_b = models.ForeignKey(USER, on_delete=models.CASCADE, db_column="user_b", related_name="+")
    created_at = models.DateTimeField(default=timezone.now)
    blocked = models.BooleanField(default=False)
    # Nur für die Pilot-Kennzahl "wiederkehrendes Gespräch": wurde es schon gezählt?
    recurring_counted = models.BooleanField(default=False)

    class Meta:
        db_table = "conversations"
        constraints = [
            models.UniqueConstraint(fields=["user_a", "user_b"], name="conversations_pair"),
            models.CheckConstraint(condition=Q(user_a__lt=F("user_b")), name="conversations_ordered"),
        ]

    def partner_id(self, user_id):
        return self.user_b_id if self.user_a_id == user_id else self.user_a_id


class Message(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(USER, on_delete=models.CASCADE, related_name="+")
    body = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "messages"
        indexes = [models.Index(fields=["conversation", "created_at"])]


class Block(models.Model):
    """Blockierung. Wirkt in beide Richtungen, vor jeder Zählung und Anzeige."""

    pk = models.CompositePrimaryKey("blocker_id", "blocked_id")
    blocker = models.ForeignKey(USER, on_delete=models.CASCADE, related_name="+")
    blocked = models.ForeignKey(USER, on_delete=models.CASCADE, related_name="+")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "blocks"
        indexes = [models.Index(fields=["blocked"])]
