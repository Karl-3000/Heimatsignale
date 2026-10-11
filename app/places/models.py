import re
import unicodedata

from django.db import models

from .states import state_name

_FOLD = str.maketrans({"ä": "a", "ö": "o", "ü": "u", "ß": "ss"})


def normalize(text: str) -> str:
    """Suchform eines Ortsnamens: klein, nur Buchstaben und Ziffern.

    Umlaute und ihre Umschrift fallen zusammen, damit "Münster", "Muenster"
    und "Munster" dasselbe finden.
    """
    text = text.strip().lower().translate(_FOLD)
    for pair, single in (("ae", "a"), ("oe", "o"), ("ue", "u")):
        text = text.replace(pair, single)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


class Place(models.Model):
    """Gemeinde aus dem Gemeindeverzeichnis (DESTATIS), fester Gebietsstand.

    Die Spalte ``center geography(Point, 4326)`` wird in der Migration als
    generierte Spalte aus ``lat``/``lon`` angelegt und trägt den GIST-Index.
    Django schreibt nur ``lat`` und ``lon``; gerechnet wird immer auf ``center``.
    """

    ags = models.CharField("AGS", max_length=8, primary_key=True)
    name = models.CharField(max_length=120)
    search_name = models.CharField(max_length=120, db_index=True)
    district_ags = models.CharField(max_length=5, db_index=True)
    district_name = models.CharField(max_length=120)
    state_code = models.CharField(max_length=2, db_index=True)
    lat = models.FloatField()
    lon = models.FloatField()

    class Meta:
        db_table = "places"
        verbose_name = "Ort"
        verbose_name_plural = "Orte"
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.district_name}, {self.state_name})"

    @property
    def state_name(self) -> str:
        return state_name(self.state_code)

    def save(self, *args, **kwargs):
        self.search_name = normalize(self.name)
        super().save(*args, **kwargs)


class PlaceMerge(models.Model):
    """Gemeindefusion: alter AGS wird auf die neue Gemeinde abgebildet."""

    old_ags = models.CharField(max_length=8, primary_key=True)
    new_ags = models.CharField(max_length=8)
    valid_from = models.DateField()

    class Meta:
        db_table = "place_merges"
        verbose_name = "Gemeindefusion"
        verbose_name_plural = "Gemeindefusionen"

    def __str__(self) -> str:
        return f"{self.old_ags} → {self.new_ags}"
