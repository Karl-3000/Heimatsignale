from .models import AuditLog


def log(admin, action: str, target_user=None, reason: str = "") -> None:
    """Schreibt einen Audit-Eintrag. ``reason`` darf keine Ortswerte, E-Mails oder Nutzertexte enthalten."""
    AuditLog.objects.create(
        admin_id=getattr(admin, "pk", None), action=action, target_user_id=getattr(target_user, "pk", target_user),
        reason=reason,
    )
