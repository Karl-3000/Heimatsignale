import secrets
import uuid

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.crypto import salted_hmac

from places.models import Place

from .fields import CIEmailField
from .nicknames import NICKNAME_REGEX


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email: str, password: str | None = None, **extra):
        user = self.model(email=self.normalize_email(email).lower(), **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user


class User(AbstractBaseUser):
    """Konto. Nach der Löschung bleibt nur ein Grabstein: id, status, deleted_at."""

    class Status(models.TextChoices):
        PENDING = "pending", "ausstehend"
        ACTIVE = "active", "aktiv"
        SUSPENDED = "suspended", "gesperrt"
        DELETED = "deleted", "gelöscht"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = CIEmailField("E-Mail", unique=True, null=True, blank=True)
    password = models.CharField("Passwort-Hash", max_length=255, null=True, blank=True, db_column="password_hash")
    last_login = None  # kein Anmeldeverlauf
    nickname = models.CharField(max_length=60, unique=True, null=True, blank=True)
    birth_year = models.SmallIntegerField("Geburtsjahr", null=True, blank=True)
    adult_self_declared_at = models.DateField("Volljährigkeit selbst erklärt am", null=True, blank=True)
    home = models.ForeignKey(
        Place, verbose_name="Heimatort", null=True, blank=True, on_delete=models.PROTECT,
        db_column="home_ags", related_name="+",
    )
    residence = models.ForeignKey(
        Place, verbose_name="Wohnort", null=True, blank=True, on_delete=models.PROTECT,
        db_column="residence_ags", related_name="+",
    )
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    email_verified_at = models.DateTimeField("E-Mail bestätigt", null=True, blank=True)
    approval_required = models.BooleanField("Admin-Freigabe nötig", default=False)
    approved_at = models.DateTimeField("Freigegeben", null=True, blank=True)
    approval_notice_sent_at = models.DateTimeField(null=True, blank=True)
    muted_until = models.DateTimeField("Stummgeschaltet bis", null=True, blank=True)
    last_activity_at = models.DateTimeField("Letzte Aktivität", null=True, blank=True)
    nickname_rerolls_left = models.SmallIntegerField(default=1)
    session_epoch = models.IntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    class Meta:
        db_table = "users"
        verbose_name = "Konto"
        verbose_name_plural = "Konten"
        constraints = [
            models.CheckConstraint(
                condition=Q(status__in=["pending", "active", "suspended", "deleted"]), name="users_status_valid"
            ),
            models.CheckConstraint(
                condition=Q(nickname__isnull=True) | Q(nickname__regex=NICKNAME_REGEX), name="users_nickname_format"
            ),
            # Grabstein: ein gelöschtes Konto trägt keine Kontodaten mehr.
            models.CheckConstraint(
                condition=~Q(status="deleted")
                | Q(
                    email__isnull=True, password__isnull=True, nickname__isnull=True, birth_year__isnull=True,
                    home__isnull=True, residence__isnull=True, deleted_at__isnull=False,
                ),
                name="users_tombstone_empty",
            ),
        ]
        indexes = [
            models.Index(fields=["residence"], condition=Q(status="active"), name="users_visible_residence"),
            models.Index(fields=["status", "created_at"], name="users_status_created"),
        ]

    def __str__(self) -> str:
        return self.nickname or f"Konto {str(self.id)[:8]}"

    # -- Anbindung an Django-Auth und den Admin -----------------------------
    @property
    def is_active(self) -> bool:
        return self.status == self.Status.ACTIVE

    @property
    def moderator_role(self) -> str | None:
        if not hasattr(self, "_moderator_role"):
            row = Moderator.objects.filter(user_id=self.pk).values_list("role", flat=True).first()
            self._moderator_role = row
        return self._moderator_role

    @property
    def is_staff(self) -> bool:
        return self.moderator_role is not None

    @property
    def is_superuser(self) -> bool:
        return self.moderator_role == Moderator.Role.ADMIN

    def has_perm(self, perm: str, obj=None) -> bool:
        if not self.is_active:
            return False
        if self.is_superuser:
            return True
        if self.moderator_role == Moderator.Role.MODERATOR:
            app = perm.split(".", 1)[0]
            return app == "moderation" or perm in {"accounts.view_user", "adminpanel.view_auditlog"}
        return False

    def has_perms(self, perm_list, obj=None) -> bool:
        return all(self.has_perm(p, obj) for p in perm_list)

    def has_module_perms(self, app_label: str) -> bool:
        if not self.is_active:
            return False
        if self.is_superuser:
            return True
        return self.moderator_role == Moderator.Role.MODERATOR and app_label in {"moderation", "accounts", "adminpanel"}

    def get_session_auth_hash(self) -> str:
        # Passwortwechsel, Sperre und Löschung erhöhen session_epoch oder
        # leeren das Passwort und machen damit alle Sitzungen ungültig.
        return salted_hmac(
            "accounts.User.session", f"{self.password or ''}|{self.session_epoch}", algorithm="sha256"
        ).hexdigest()

    def get_session_auth_fallback_hash(self):
        return iter(())


class Moderator(models.Model):
    """Benannte Bearbeiter. Nur Konten mit einem Eintrag hier kommen in den Admin-Bereich."""

    class Role(models.TextChoices):
        MODERATOR = "moderator", "Moderation"
        ADMIN = "admin", "Administration"

    user = models.OneToOneField(User, primary_key=True, on_delete=models.CASCADE, related_name="moderator")
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.MODERATOR)
    deputy_of = models.ForeignKey(
        "self", verbose_name="Vertretung für", null=True, blank=True, on_delete=models.SET_NULL, related_name="deputies"
    )

    class Meta:
        db_table = "moderators"
        verbose_name = "Bearbeiter"
        verbose_name_plural = "Bearbeiter"

    def __str__(self) -> str:
        return f"{self.user} ({self.get_role_display()})"


def new_invite_code() -> str:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "-".join("".join(secrets.choice(alphabet) for _ in range(4)) for _ in range(3))


class InviteCode(models.Model):
    code = models.CharField(max_length=40, unique=True, default=new_invite_code)
    label = models.CharField("Anlass", max_length=120)
    valid_until = models.DateTimeField("Gültig bis")
    max_uses = models.PositiveIntegerField("Kontingent")
    used_count = models.PositiveIntegerField("Verbraucht", default=0)
    created_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "invite_codes"
        verbose_name = "Einladungscode"
        verbose_name_plural = "Einladungscodes"
        constraints = [
            models.CheckConstraint(condition=Q(used_count__lte=models.F("max_uses")), name="invite_codes_not_overused"),
        ]

    def __str__(self) -> str:
        return f"{self.label} ({self.code})"


class RegistrationIP(models.Model):
    """Gehashte IP einer Registrierung, 7 Tage, ohne Nutzerzuordnung."""

    ip_hash = models.CharField(max_length=64, db_index=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    invite_code = models.ForeignKey(InviteCode, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")

    class Meta:
        db_table = "registration_ips"


class PlaceChangeRequest(models.Model):
    """Antrag "Ich bin umgezogen" oder "Mein Heimatort ist falsch"."""

    class Field(models.TextChoices):
        HOME = "home", "Heimatort"
        RESIDENCE = "residence", "Wohnort"

    class Decision(models.TextChoices):
        APPROVED = "approved", "bestätigt"
        REJECTED = "rejected", "abgelehnt"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="place_change_requests")
    field = models.CharField("Feld", max_length=10, choices=Field.choices)
    new_place = models.ForeignKey(Place, on_delete=models.PROTECT, db_column="new_ags", related_name="+")
    # Alter Wert nur zeitweise, bis 30 Tage nach der Entscheidung (Abschnitt 14).
    old_place = models.ForeignKey(Place, null=True, blank=True, on_delete=models.SET_NULL, db_column="old_ags", related_name="+")
    created_at = models.DateTimeField(default=timezone.now)
    decided_at = models.DateTimeField(null=True, blank=True)
    decided_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    decision = models.CharField(max_length=10, choices=Decision.choices, null=True, blank=True)

    class Meta:
        db_table = "place_change_requests"
        verbose_name = "Ortsänderungsantrag"
        verbose_name_plural = "Ortsänderungsanträge"
        constraints = [
            models.UniqueConstraint(fields=["user", "field"], condition=Q(decided_at__isnull=True), name="place_change_one_open"),
            models.CheckConstraint(condition=Q(field__in=["home", "residence"]), name="place_change_field_valid"),
        ]

    def __str__(self) -> str:
        return f"{self.get_field_display()} von {self.user}"


class LoginFailure(models.Model):
    """Fehlgeschlagene Anmeldung, nur als Hash von Konto und IP, höchstens 24 Stunden."""

    account_hash = models.CharField(max_length=64)
    ip_hash = models.CharField(max_length=64)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "login_failures"
        indexes = [
            models.Index(fields=["account_hash", "created_at"]),
            models.Index(fields=["ip_hash", "created_at"]),
        ]


class RateCounter(models.Model):
    """Zähler für Rate-Limits in festen Zeitfenstern."""

    key = models.CharField(max_length=120)
    window_start = models.DateTimeField()
    count = models.IntegerField(default=0)

    class Meta:
        db_table = "rate_counters"
        constraints = [models.UniqueConstraint(fields=["key", "window_start"], name="rate_counters_window")]


class PowChallenge(models.Model):
    """Bereits eingelöste Proof-of-Work-Aufgaben (Schutz vor Wiederverwendung)."""

    challenge = models.CharField(max_length=64, primary_key=True)
    expires_at = models.DateTimeField(db_index=True)

    class Meta:
        db_table = "pow_challenges"
