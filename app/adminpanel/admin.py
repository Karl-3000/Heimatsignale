"""Admin-Bereich (PROJEKT.md, Abschnitt 13). Jede Aktion schreibt einen Audit-Eintrag."""

import json

from django import forms
from django.contrib import admin, messages
from django.contrib.admin.helpers import ActionForm
from django.db import transaction
from django.db.models import Count, F, OuterRef, Subquery
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html
from django_otp.plugins.otp_static.models import StaticDevice
from django_otp.plugins.otp_totp.admin import TOTPDeviceAdmin
from django_otp.plugins.otp_totp.models import TOTPDevice

from accounts import mail, states
from accounts.models import InviteCode, Moderator, PlaceChangeRequest, User
from deletion.services import delete_account
from jobs.models import DailyStat
from moderation import services as moderation
from moderation.models import Appeal, Report
from places.models import Place, PlaceMerge, normalize

from . import audit
from .models import AuditLog
from .site import admin_site

STATE_LABELS = {
    states.UNVERIFIED: "unbestätigt", states.AWAITING_APPROVAL: "wartet auf Freigabe", states.ACTIVE: "aktiv",
    states.MUTED: "stummgeschaltet", states.SUSPENDED: "gesperrt", states.DELETED: "gelöscht",
}


class ReasonActionForm(ActionForm):
    reason = forms.CharField(label="Begründung", required=False, widget=forms.TextInput(attrs={"size": 50}))


class ReadOnlyAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


def _reason(request) -> str:
    return (request.POST.get("reason") or "").strip()


def _need_reason(modeladmin, request) -> str | None:
    reason = _reason(request)
    if not reason:
        modeladmin.message_user(request, "Bitte gib eine Begründung an.", messages.ERROR)
        return None
    return reason


# -- Konten ---------------------------------------------------------------------
class QueueFilter(admin.SimpleListFilter):
    title = "Zustand"
    parameter_name = "zustand"

    def lookups(self, request, model_admin):
        return [("freigabe", "wartet auf Freigabe"), ("stumm", "stummgeschaltet"), ("gesperrt", "gesperrt"),
                ("aktiv", "aktiv"), ("unbestaetigt", "unbestätigt"), ("geloescht", "gelöscht")]

    def queryset(self, request, queryset):
        now = timezone.now()
        value = self.value()
        if value == "freigabe":
            return queryset.filter(status="pending", email_verified_at__isnull=False, approval_required=True,
                                   approved_at__isnull=True).order_by("created_at")
        if value == "stumm":
            return queryset.filter(status="active", muted_until__gt=now)
        if value == "gesperrt":
            return queryset.filter(status="suspended")
        if value == "aktiv":
            return queryset.filter(status="active")
        if value == "unbestaetigt":
            return queryset.filter(status="pending", email_verified_at__isnull=True)
        if value == "geloescht":
            return queryset.filter(status="deleted")
        return queryset


class PlaceChangeForm(forms.Form):
    field = forms.ChoiceField(label="Feld", choices=PlaceChangeRequest.Field.choices)
    place = forms.CharField(label="Neuer Ort (AGS oder genauer Name)")
    reason = forms.CharField(label="Begründung", widget=forms.Textarea(attrs={"rows": 3}))

    def clean_place(self):
        value = self.cleaned_data["place"].strip()
        found = list(Place.objects.filter(pk=value)) or list(Place.objects.filter(search_name=normalize(value))[:6])
        if not found:
            raise forms.ValidationError("Kein Ort gefunden.")
        if len(found) > 1:
            raise forms.ValidationError("Mehrdeutig, bitte den AGS angeben: " + "; ".join(f"{p.ags} {p}" for p in found))
        return found[0]


@admin.register(User, site=admin_site)
class UserAdmin(ReadOnlyAdmin):
    list_display = ("nickname", "zustand", "home", "residence", "created_at", "wartet_seit", "rolle")
    list_filter = (QueueFilter,)
    search_fields = ("nickname", "email")
    list_select_related = ("home", "residence")
    ordering = ("-created_at",)
    action_form = ReasonActionForm
    actions = ["approve", "mute_48h", "unmute", "suspend", "unsuspend", "delete_accounts"]
    fields = ("id", "nickname", "email", "zustand", "status", "birth_year", "adult_self_declared_at", "home",
              "residence", "email_verified_at", "approval_required", "approved_at", "muted_until",
              "last_activity_at", "created_at", "deleted_at", "ort_aendern")
    readonly_fields = fields

    def get_ordering(self, request):
        # Die Freigabe-Warteschlange zeigt die ältesten Registrierungen zuerst.
        return ("created_at",) if request.GET.get("zustand") == "freigabe" else self.ordering

    def get_fields(self, request, obj=None):
        # Die Moderation braucht weder E-Mail-Adresse noch Geburtsjahr.
        hidden = () if request.user.is_superuser else ("email", "birth_year", "adult_self_declared_at", "ort_aendern")
        return [f for f in self.fields if f not in hidden]

    def get_search_fields(self, request):
        return self.search_fields if request.user.is_superuser else ("nickname",)

    @admin.display(description="Wirksamer Zustand")
    def zustand(self, obj):
        return STATE_LABELS[states.effective_state(obj)]

    @admin.display(description="Rolle")
    def rolle(self, obj):
        return obj.moderator_role or ""

    @admin.display(description="Wartet seit (Tagen)")
    def wartet_seit(self, obj):
        if states.effective_state(obj) != states.AWAITING_APPROVAL:
            return ""
        return (timezone.now() - obj.created_at).days

    @admin.display(description="Orte")
    def ort_aendern(self, obj):
        if obj is None or obj.status == "deleted":
            return ""
        url = reverse(f"{admin_site.name}:accounts_user_place", args=[obj.pk])
        return format_html('<a class="button" href="{}">Heimatort oder Wohnort ändern</a>', url)

    def get_actions(self, request):
        actions = super().get_actions(request)
        if not request.user.is_superuser:
            actions = {k: v for k, v in actions.items() if k in {"mute_48h", "unmute"}}
        return actions

    @admin.action(description="Freigeben (Warteschlange)")
    def approve(self, request, queryset):
        n = 0
        for candidate in queryset.filter(status="pending", approval_required=True, approved_at__isnull=True):
            with transaction.atomic():
                # Frisch und gesperrt lesen: Die E-Mail-Bestätigung kann gleichzeitig laufen.
                user = User.objects.select_for_update(no_key=True).get(pk=candidate.pk)
                if user.status != "pending" or user.approved_at is not None:
                    continue
                user.approved_at = timezone.now()
                states.apply_activation(user)
                user.save(update_fields=["approved_at", "status"])
                audit.log(request.user, "approve", user, _reason(request))
                if user.email and user.status == "active":
                    mail.send(user.email, "approved")
            n += 1
        self.message_user(request, f"{n} Konten freigegeben.")

    @admin.action(description="Stummschalten für 48 Stunden (Begründung nötig)")
    def mute_48h(self, request, queryset):
        if (reason := _need_reason(self, request)) is None:
            return
        for user in queryset.filter(status="active"):
            moderation.mute(request.user, user, 48, reason)
        self.message_user(request, "Stummschaltung gesetzt.")

    @admin.action(description="Stummschaltung aufheben")
    def unmute(self, request, queryset):
        for user in queryset:
            moderation.unmute(request.user, user, _reason(request))
        self.message_user(request, "Stummschaltung aufgehoben.")

    @admin.action(description="Sperren (Begründung nötig)")
    def suspend(self, request, queryset):
        if (reason := _need_reason(self, request)) is None:
            return
        for user in queryset.filter(status="active"):
            moderation.suspend(request.user, user, reason)
        self.message_user(request, "Konten gesperrt.")

    @admin.action(description="Entsperren")
    def unsuspend(self, request, queryset):
        for user in queryset.filter(status="suspended"):
            moderation.unsuspend(request.user, user, _reason(request))
        self.message_user(request, "Konten entsperrt.")

    @admin.action(description="Konto löschen (Begründung nötig, nicht umkehrbar)")
    def delete_accounts(self, request, queryset):
        if (reason := _need_reason(self, request)) is None:
            return
        n = 0
        for user in queryset.exclude(status="deleted"):
            if user.pk == request.user.pk:
                continue
            audit.log(request.user, "delete_account", user, reason)
            delete_account(user.pk)
            n += 1
        self.message_user(request, f"{n} Konten gelöscht.")

    def get_urls(self):
        return [
            path("<uuid:user_id>/ort/", self.admin_site.admin_view(self.change_place), name="accounts_user_place"),
        ] + super().get_urls()

    def change_place(self, request, user_id):
        """Heimatort oder Wohnort ändern: Pflichtfeld Begründung, Audit-Eintrag ohne Ortswerte."""
        if not request.user.is_superuser:
            return redirect(f"{admin_site.name}:index")
        user = get_object_or_404(User.objects.exclude(status="deleted"), pk=user_id)
        form = PlaceChangeForm(request.POST or None)
        if request.method == "POST" and form.is_valid():
            field, place = form.cleaned_data["field"], form.cleaned_data["place"]
            with transaction.atomic():
                setattr(user, field, place)
                user.save(update_fields=[field])
                audit.log(request.user, f"change_{field}", user, form.cleaned_data["reason"])
            self.message_user(request, "Ort geändert.")
            return redirect(f"{admin_site.name}:accounts_user_change", user.pk)
        context = {**self.admin_site.each_context(request), "form": form, "account": user, "title": "Ort ändern",
                   "opts": self.model._meta}
        return render(request, "admin/place_change.html", context)


class AuditedAdmin(admin.ModelAdmin):
    """Schreibt Anlegen, Ändern und Löschen ins Audit-Log (ohne Inhalte)."""

    audit_name = ""

    def _target(self, obj):
        return getattr(obj, "user", None)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        audit.log(request.user, f"{self.audit_name}_{'changed' if change else 'created'}", self._target(obj))

    def delete_model(self, request, obj):
        audit.log(request.user, f"{self.audit_name}_deleted", self._target(obj))
        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        for obj in queryset:
            audit.log(request.user, f"{self.audit_name}_deleted", self._target(obj))
        super().delete_queryset(request, queryset)


class ModeratorForm(forms.ModelForm):
    class Meta:
        model = Moderator
        fields = ("user", "role", "deputy_of")

    def clean_user(self):
        user = self.cleaned_data["user"]
        if user.home_id or user.residence_id:
            raise forms.ValidationError(
                "Bearbeiter brauchen ein eigenes Konto ohne Orte. Bitte mit 'manage.py admin_anlegen' anlegen."
            )
        return user


@admin.register(Moderator, site=admin_site)
class ModeratorAdmin(AuditedAdmin):
    audit_name = "moderator"
    form = ModeratorForm
    list_display = ("user", "role", "deputy_of")
    raw_id_fields = ("user",)


@admin.register(PlaceChangeRequest, site=admin_site)
class PlaceChangeRequestAdmin(ReadOnlyAdmin):
    list_display = ("user", "field", "old_place", "new_place", "created_at", "decision", "decided_at")
    list_filter = ("decision", "field")
    list_select_related = ("user", "old_place", "new_place")
    ordering = (F("decided_at").asc(nulls_first=True), "created_at")
    action_form = ReasonActionForm
    actions = ["approve", "reject"]

    def _decide(self, request, queryset, approved: bool):
        n = 0
        for req in queryset.filter(decided_at__isnull=True).select_related("user", "new_place"):
            with transaction.atomic():
                user = User.objects.select_for_update(no_key=True).get(pk=req.user_id)
                if approved and user.status != "deleted":
                    setattr(user, req.field, req.new_place)
                    user.save(update_fields=[req.field])
                req.decided_at, req.decided_by = timezone.now(), request.user
                req.decision = "approved" if approved else "rejected"
                req.save(update_fields=["decided_at", "decided_by", "decision"])
                audit.log(request.user, f"place_change_{req.decision}", user, _reason(request))
                if user.email:
                    mail.send(user.email, "place_change_decided", {
                        "field": req.get_field_display(), "decision": "bestätigt" if approved else "abgelehnt",
                    })
            n += 1
        self.message_user(request, f"{n} Anträge entschieden.")

    @admin.action(description="Bestätigen")
    def approve(self, request, queryset):
        self._decide(request, queryset, True)

    @admin.action(description="Ablehnen")
    def reject(self, request, queryset):
        self._decide(request, queryset, False)


# -- Meldungen und Einsprüche -------------------------------------------------------
class OpenFilter(admin.SimpleListFilter):
    title = "Bearbeitung"
    parameter_name = "offen"

    def lookups(self, request, model_admin):
        return [("ja", "offen"), ("nein", "abgeschlossen")]

    def queryset(self, request, queryset):
        if self.value() == "ja":
            return queryset.filter(**{self.field: True})
        if self.value() == "nein":
            return queryset.filter(**{self.field: False})
        return queryset


class ReportOpenFilter(OpenFilter):
    field = "resolved_at__isnull"


class AppealOpenFilter(OpenFilter):
    field = "decided_at__isnull"


@admin.register(Report, site=admin_site)
class ReportAdmin(ReadOnlyAdmin):
    """Warteschlange, sortiert nach Schwere und Häufung. Ein Vorfall bündelt Meldungen zum selben Ziel."""

    list_display = ("vorfall", "reason", "target_type", "reported_user", "haeufung", "created_at", "outcome")
    list_filter = (ReportOpenFilter, "reason", "target_type")
    search_fields = ("incident_key", "reported_user__nickname")
    action_form = ReasonActionForm
    actions = ["dismiss", "confirm"]
    fields = ("incident_key", "reason", "target_type", "reported_user", "note", "schnappschuss", "created_at",
              "resolved_at", "resolved_by", "outcome")
    readonly_fields = fields

    def get_queryset(self, request):
        size = (
            Report.objects.filter(incident_key=OuterRef("incident_key")).order_by().values("incident_key")
            .annotate(n=Count("id")).values("n")
        )
        return super().get_queryset(request).select_related("reported_user").annotate(
            incident_size=Subquery(size)
        ).order_by(F("resolved_at").asc(nulls_first=True), "-severity", "-incident_size", "created_at")

    @admin.display(description="Vorfall")
    def vorfall(self, obj):
        return obj.incident_key[:8]

    @admin.display(description="Meldungen im Vorfall")
    def haeufung(self, obj):
        return obj.incident_size

    @admin.display(description="Schnappschuss")
    def schnappschuss(self, obj):
        return format_html("<pre style='white-space:pre-wrap'>{}</pre>", json.dumps(obj.snapshot, ensure_ascii=False, indent=2))

    def _resolve(self, request, queryset, confirmed: bool, reason: str):
        keys = set(queryset.values_list("incident_key", flat=True))
        n = sum(moderation.resolve_incident(request.user, key, confirmed, reason) for key in keys)
        self.message_user(request, f"{len(keys)} Vorfälle mit {n} Meldungen abgeschlossen.")

    @admin.action(description="Vorfall schließen: kein Verstoß")
    def dismiss(self, request, queryset):
        self._resolve(request, queryset, False, _reason(request))

    @admin.action(description="Vorfall bestätigen und Konto sperren (Begründung nötig)")
    def confirm(self, request, queryset):
        if (reason := _need_reason(self, request)) is None:
            return
        self._resolve(request, queryset, True, reason)


@admin.register(Appeal, site=admin_site)
class AppealAdmin(ReadOnlyAdmin):
    list_display = ("user", "created_at", "erstentscheidung", "outcome", "decided_by", "decided_at")
    list_filter = (AppealOpenFilter,)
    list_select_related = ("user", "report__resolved_by", "decided_by")
    action_form = ReasonActionForm
    actions = ["uphold", "overturn"]
    fields = ("user", "text", "report", "erstentscheidung", "created_at", "decided_at", "decided_by", "outcome")
    readonly_fields = fields

    @admin.display(description="Erstentscheidung durch")
    def erstentscheidung(self, obj):
        return obj.report.resolved_by if obj.report and obj.report.resolved_by else "automatisch"

    def _decide(self, request, queryset, overturned: bool):
        for appeal in queryset.filter(decided_at__isnull=True).select_related("report", "user"):
            try:
                moderation.decide_appeal(request.user, appeal, overturned, _reason(request))
            except PermissionError as exc:
                self.message_user(request, str(exc), messages.ERROR)
        self.message_user(request, "Entscheidung gespeichert.")

    @admin.action(description="Einspruch ablehnen (Entscheidung bleibt)")
    def uphold(self, request, queryset):
        self._decide(request, queryset, False)

    @admin.action(description="Einspruch stattgeben (Entscheidung aufheben)")
    def overturn(self, request, queryset):
        self._decide(request, queryset, True)


# -- Einladungscodes, Kennzahlen, Audit, Orte ------------------------------------------
@admin.register(InviteCode, site=admin_site)
class InviteCodeAdmin(AuditedAdmin):
    audit_name = "invite_code"
    list_display = ("label", "code", "valid_until", "used_count", "max_uses", "created_by")
    readonly_fields = ("code", "used_count", "created_by", "created_at")
    fields = ("label", "valid_until", "max_uses", "code", "used_count", "created_by", "created_at")

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(DailyStat, site=admin_site)
class DailyStatAdmin(ReadOnlyAdmin):
    list_display = ("day", "registrations", "active_accounts", "requests_sent", "requests_accepted",
                    "conversations_started", "conversations_recurring", "reports_dating", "deletions")
    date_hierarchy = "day"


@admin.register(AuditLog, site=admin_site)
class AuditLogAdmin(ReadOnlyAdmin):
    list_display = ("created_at", "admin", "action", "target_user", "reason")
    list_filter = ("action",)
    date_hierarchy = "created_at"


@admin.register(Place, site=admin_site)
class PlaceAdmin(ReadOnlyAdmin):
    list_display = ("name", "ags", "district_name", "state_code")
    search_fields = ("search_name", "ags")
    list_filter = ("state_code",)


@admin.register(PlaceMerge, site=admin_site)
class PlaceMergeAdmin(ReadOnlyAdmin):
    list_display = ("old_ags", "new_ags", "valid_from")


class AuditedTOTPDeviceAdmin(AuditedAdmin, TOTPDeviceAdmin):
    audit_name = "totp_device"


class AuditedStaticDeviceAdmin(AuditedAdmin):
    audit_name = "backup_codes"
    raw_id_fields = ("user",)


admin_site.register(TOTPDevice, AuditedTOTPDeviceAdmin)
admin_site.register(StaticDevice, AuditedStaticDeviceAdmin)
