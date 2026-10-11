from django.conf import settings
from django.db import models
from django.utils import timezone


class AuditLog(models.Model):
    """Nachvollziehbarkeit des Admin-Handelns.

    Enthält keine Ortswerte, keine E-Mails und keine Texte der Nutzer. Die
    Verweise auf Admin und Nutzer sind pseudonyme Personendaten.
    """

    admin = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    action = models.CharField("Aktion", max_length=40)
    target_user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    reason = models.TextField("Begründung", blank=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        db_table = "admin_audit_log"
        verbose_name = "Audit-Eintrag"
        verbose_name_plural = "Audit-Log"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.action} ({self.created_at:%d.%m.%Y %H:%M})"
