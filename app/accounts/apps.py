from django.apps import AppConfig


class AccountsConfig(AppConfig):
    name = "accounts"
    verbose_name = "Konten"

    def ready(self):
        # Es gibt bewusst kein "last_login": Das Datenmodell führt keinen
        # Anmeldeverlauf. Djangos Standard-Empfänger würde das Feld schreiben.
        from django.contrib.auth.models import update_last_login
        from django.contrib.auth.signals import user_logged_in

        user_logged_in.disconnect(update_last_login, dispatch_uid="update_last_login")
