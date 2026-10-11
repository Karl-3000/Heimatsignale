from django.contrib.auth.backends import ModelBackend

from heimatsignale.errors import ApiError


class ThrottledBackend(ModelBackend):
    """Anmeldung über Djangos ``authenticate`` (Admin-Bereich) unter denselben Login-Regeln wie die API."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        from .services import check_credentials

        if request is None or username is None or password is None:
            return None
        try:
            user = check_credentials(request, username, password, pow_exempt=True)
        except ApiError:
            return None
        return user if user.is_active else None

    def user_can_authenticate(self, user):
        # Den wirksamen Zustand erzwingt die Zustands-Middleware bei jedem Zugriff.
        return True
