"""Automatische Nicknames: Adjektiv + Tier/Ding + Zahl, z. B. Stiller-Leuchtturm-412.

Die Wortlisten sind bewusst harmlos gehalten. Zusätzlich gibt es eine
Sperrliste für Zahlen und Wortteile; die Datenbank erzwingt Format und
Eindeutigkeit.
"""

import re
import secrets

NICKNAME_REGEX = r"^[A-ZÄÖÜ][a-zäöüß]+-[A-ZÄÖÜ][a-zäöüß]+-[1-9][0-9]{1,2}$"

# Stamm; Endungen: maskulin -er, feminin -e, neutrum -es
ADJECTIVES = [
    "Still", "Ruhig", "Leis", "Hell", "Klar", "Mild", "Sanft", "Wach", "Flink", "Munter", "Heiter", "Froh",
    "Klug", "Kühn", "Frisch", "Bunt", "Blau", "Grün", "Grau", "Gelb", "Golden", "Silbern", "Weit", "Fern",
    "Neu", "Schlicht", "Leicht", "Kühl", "Fein", "Rasch", "Treu", "Echt", "Sacht", "Emsig", "Fleißig",
    "Mutig", "Freundlich", "Höflich", "Friedlich", "Fröhlich", "Gemütlich", "Herzlich", "Redlich",
    "Nördlich", "Südlich", "Östlich", "Westlich", "Sonnig", "Windig", "Neblig", "Wolkig", "Luftig",
    "Sandig", "Steinig", "Moosig", "Geduldig", "Gelassen", "Besonnen", "Beherzt", "Bedächtig", "Wacker",
    "Rüstig", "Pfiffig", "Findig", "Achtsam", "Wachsam", "Sorgsam", "Behutsam", "Genügsam", "Standhaft",
]

MASCULINE = [
    "Leuchtturm", "Kranich", "Dachs", "Fuchs", "Igel", "Otter", "Biber", "Luchs", "Falke", "Reiher", "Storch",
    "Specht", "Fink", "Spatz", "Kauz", "Uhu", "Rabe", "Schwan", "Hirsch", "Hase", "Maulwurf", "Marder", "Lachs",
    "Hecht", "Karpfen", "Stieglitz", "Zaunkönig", "Kiebitz", "Bussard", "Milan", "Habicht", "Berg", "Hügel",
    "Bach", "Fluss", "See", "Teich", "Wald", "Hain", "Stein", "Fels", "Pfad", "Steg", "Hafen", "Anker",
    "Kompass", "Kahn", "Kutter", "Garten", "Baum", "Ahorn", "Holunder", "Wacholder", "Stern", "Mond", "Morgen",
    "Abend", "Wind", "Nebel", "Regen", "Giebel", "Brunnen", "Kirchturm", "Bahnhof", "Kiesel", "Eisvogel",
    "Seestern", "Wegweiser", "Feldweg", "Apfelbaum", "Birnbaum", "Marktplatz",
]

FEMININE = [
    "Eule", "Amsel", "Meise", "Lerche", "Möwe", "Schwalbe", "Drossel", "Elster", "Taube", "Ente", "Gans",
    "Robbe", "Forelle", "Libelle", "Hummel", "Biene", "Grille", "Linde", "Eiche", "Buche", "Birke", "Weide",
    "Tanne", "Kiefer", "Fichte", "Erle", "Ulme", "Kastanie", "Wiese", "Heide", "Düne", "Insel", "Küste",
    "Bucht", "Quelle", "Brücke", "Mühle", "Laterne", "Glocke", "Wolke", "Welle", "Brise", "Lichtung", "Hütte",
    "Scheune", "Gasse", "Fähre", "Kogge", "Boje", "Nachtigall", "Bachstelze", "Haselmaus", "Windmühle",
]

NEUTER = [
    "Ufer", "Tal", "Feld", "Moor", "Watt", "Riff", "Boot", "Floß", "Segel", "Ruder", "Tor", "Dach", "Fenster",
    "Licht", "Echo", "Blatt", "Moos", "Korn", "Reh", "Kitz", "Eichhörnchen", "Rotkehlchen", "Windrad",
    "Fachwerk", "Wasserrad", "Gipfelkreuz", "Dorf", "Gehöft", "Kleeblatt", "Schilfrohr", "Seepferdchen",
]

# Zahlen mit einschlägiger Bedeutung werden nie vergeben.
_BLOCKED_NUMBER_PARTS = ("18", "88", "69", "28", "74", "84")
_BLOCKED_NUMBERS = {13, 14, 33, 110, 112, 168, 187, 311, 420, 444, 666, 911}
# Wortteile, die in keinem Nickname vorkommen dürfen (Kleinschreibung).
BLOCKED_SUBSTRINGS = ("heil", "sieg", "reich", "führer", "nazi", "hitler", "sex", "porn", "date", "single", "flirt")


def _number_allowed(n: int) -> bool:
    text = str(n)
    return n not in _BLOCKED_NUMBERS and not any(part in text for part in _BLOCKED_NUMBER_PARTS)


def is_allowed(nickname: str) -> bool:
    if not re.match(NICKNAME_REGEX, nickname):
        return False
    lowered = nickname.lower()
    if any(part in lowered for part in BLOCKED_SUBSTRINGS):
        return False
    return _number_allowed(int(nickname.rsplit("-", 1)[1]))


def _inflect(stem: str, ending: str) -> str:
    # "Leis" + "er" = "Leiser", "Golden" + "er" = "Goldener"
    return stem + ending


def generate() -> str:
    """Erzeugt einen zulässigen Nickname (ohne Prüfung auf Eindeutigkeit)."""
    while True:
        ending, nouns = secrets.choice((("er", MASCULINE), ("e", FEMININE), ("es", NEUTER)))
        number = 10 + secrets.randbelow(990)
        candidate = f"{_inflect(secrets.choice(ADJECTIVES), ending)}-{secrets.choice(nouns)}-{number}"
        if is_allowed(candidate):
            return candidate


def generate_unique(exists) -> str:
    """``exists(nickname) -> bool`` prüft die Belegung. Die DB sichert zusätzlich ab."""
    for _ in range(50):
        candidate = generate()
        if not exists(candidate):
            return candidate
    raise RuntimeError("Kein freier Nickname gefunden.")
