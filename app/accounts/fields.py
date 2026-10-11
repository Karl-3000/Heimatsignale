from django.db import models


class CIEmailField(models.EmailField):
    """E-Mail-Feld auf dem PostgreSQL-Typ ``citext`` (Vergleich ohne Groß-/Kleinschreibung)."""

    def db_type(self, connection):
        return "citext"
