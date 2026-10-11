from django.db import models


class DailyStat(models.Model):
    """Aggregierte Pilot-Kennzahlen pro Tag. Nur Zahlen, keine IDs, keine Texte.

    Jedes Objekt wird am Entstehungstag gezählt, sein Ergebnis am Tag des
    Eintritts. Die ``*_cohort``-Spalten schreiben das Ergebnis zusätzlich dem
    Entstehungstag zu, damit die Kohortenregel aus Abschnitt 18 ausgewertet
    werden kann. Spätere Löschungen verändern nichts.
    """

    day = models.DateField(primary_key=True)
    registrations = models.IntegerField(default=0)
    active_accounts = models.IntegerField(default=0)
    requests_sent = models.IntegerField(default=0)
    requests_accepted = models.IntegerField(default=0)
    requests_accepted_cohort = models.IntegerField(default=0)
    conversations_started = models.IntegerField(default=0)
    conversations_recurring = models.IntegerField(default=0)
    conversations_recurring_cohort = models.IntegerField(default=0)
    reports_dating = models.IntegerField(default=0)
    deletions = models.IntegerField(default=0)

    class Meta:
        db_table = "daily_stats"
        verbose_name = "Tageskennzahl"
        verbose_name_plural = "Tageskennzahlen"
        ordering = ["-day"]

    def __str__(self) -> str:
        return str(self.day)
