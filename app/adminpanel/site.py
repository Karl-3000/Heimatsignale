from django.conf import settings
from django_otp.admin import OTPAdminSite


class AdminSite(OTPAdminSite):
    """Admin-Bereich unter eigenem Pfad, Anmeldung nur mit Zwei-Faktor-Authentifizierung."""

    site_header = f"{settings.SITE_NAME} Verwaltung"
    site_title = f"{settings.SITE_NAME} Verwaltung"
    index_title = "Übersicht"
    site_url = None


admin_site = AdminSite(name="verwaltung")
