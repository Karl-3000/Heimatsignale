"""Einstellungen für Heimatsignale. Alles Betriebliche kommt aus der Umgebung."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def env(name: str, default: str | None = None) -> str:
    value = os.environ.get(name, default)
    if value is None:
        raise RuntimeError(f"Umgebungsvariable {name} fehlt.")
    return value


def env_bool(name: str, default: bool = False) -> bool:
    return os.environ.get(name, str(default)).strip().lower() in {"1", "true", "yes", "ja"}


DEBUG = env_bool("DEBUG", False)
SECRET_KEY = env("SECRET_KEY", "unsicher-nur-fuer-entwicklung" if DEBUG else None)
ALLOWED_HOSTS = [h.strip() for h in env("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h.strip()]

# Anzeigename und öffentliche Adresse (für Links in E-Mails).
SITE_NAME = env("SITE_NAME", "Heimatsignale")
SITE_URL = env("SITE_URL", "http://localhost:5173").rstrip("/")
CSRF_TRUSTED_ORIGINS = [SITE_URL] if SITE_URL.startswith("http") else []

# Der Admin-Bereich liegt unter einem eigenen Pfad (PROJEKT.md, Abschnitt 13).
ADMIN_PATH = env("ADMIN_PATH", "verwaltung").strip("/")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
    "django_otp",
    "django_otp.plugins.otp_totp",
    "django_otp.plugins.otp_static",
    "places",
    "accounts",
    "nearby",
    "contacts",
    "moderation",
    "deletion",
    "adminpanel",
    "jobs",
    "api",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django_otp.middleware.OTPMiddleware",
    # Berechnet den wirksamen Kontozustand und erzwingt die Berechtigungstabelle.
    "heimatsignale.middleware.AccountStateMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "heimatsignale.urls"
WSGI_APPLICATION = "heimatsignale.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("DB_NAME", "heimat"),
        "USER": env("DB_USER", "heimat"),
        "PASSWORD": env("DB_PASSWORD", "heimat"),
        "HOST": env("DB_HOST", "127.0.0.1"),
        "PORT": env("DB_PORT", "5432"),
        "CONN_MAX_AGE": 60,
        "CONN_HEALTH_CHECKS": True,
    }
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_USER_MODEL = "accounts.User"
AUTHENTICATION_BACKENDS = ["accounts.backends.ThrottledBackend"]
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 12}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator", "OPTIONS": {"user_attributes": ("email",)}},
]
PASSWORD_RESET_TIMEOUT = 60 * 60 * 2

LANGUAGE_CODE = "de"
TIME_ZONE = "Europe/Berlin"
USE_I18N = True
USE_TZ = True

STATIC_URL = f"/{ADMIN_PATH}/static/"
STATIC_ROOT = Path(env("STATIC_ROOT", str(BASE_DIR / "staticfiles")))

# Sitzungen und CSRF (PROJEKT.md, Abschnitt 11): gleiche Origin, Cookies
# SameSite=Lax, Secure, HttpOnly. Den CSRF-Token liefert /api/session im
# JSON, deshalb darf auch das CSRF-Cookie HttpOnly sein.
SECURE_COOKIES = env_bool("SECURE_COOKIES", not DEBUG)
SESSION_ENGINE = "django.contrib.sessions.backends.db"
SESSION_COOKIE_NAME = "sitzung"
SESSION_COOKIE_AGE = 60 * 60 * 24 * 30
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = SECURE_COOKIES
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = SECURE_COOKIES
CSRF_FAILURE_VIEW = "heimatsignale.middleware.csrf_failure"
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https") if env_bool("BEHIND_PROXY", not DEBUG) else None
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
if not DEBUG:
    SECURE_HSTS_SECONDS = int(env("HSTS_SECONDS", "31536000"))

# Anzahl vertrauenswürdiger Reverse-Proxys vor Django. 0 = direkte Verbindung.
TRUSTED_PROXY_COUNT = int(env("TRUSTED_PROXY_COUNT", "0" if DEBUG else "1"))

EMAIL_BACKEND = env(
    "EMAIL_BACKEND",
    "django.core.mail.backends.console.EmailBackend" if DEBUG else "django.core.mail.backends.smtp.EmailBackend",
)
EMAIL_FILE_PATH = env("EMAIL_FILE_PATH", "/tmp/heimatsignale-mails")  # nur für das filebased-Backend
EMAIL_HOST = env("EMAIL_HOST", "localhost")
EMAIL_PORT = int(env("EMAIL_PORT", "587"))
EMAIL_HOST_USER = env("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", True)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", f"{SITE_NAME} <noreply@localhost>")
MODERATION_EMAIL = env("MODERATION_EMAIL", "moderation@localhost")

# Löschjournal: bewusst außerhalb der Datenbank, auf einem eigenen Volume
# mit eigenem Backup (PROJEKT.md, Abschnitt 12).
DELETION_JOURNAL_PATH = env("DELETION_JOURNAL_PATH", str(BASE_DIR.parent / "var" / "journal" / "loeschjournal.sqlite3"))

# ---------------------------------------------------------------------------
# Fachliche Festlegungen aus PROJEKT.md. Bewusst an einer Stelle.
# ---------------------------------------------------------------------------
RADIUS_METERS = 20_000
MINIMUM_AGE = 18
UNVERIFIED_TTL_HOURS = 48
APPROVAL_NOTICE_DAYS = 14

REQUEST_BODY_MAX = 500
REQUEST_TTL_DAYS = 30
REQUEST_DAILY_MAX = 5
REQUEST_ACTIVE_MAX = 20
REQUEST_ATTEMPTS_MAX = 2
EXPIRED_REQUEST_KEEP_DAYS = 7

MESSAGE_BODY_MAX = 2000
MESSAGES_PER_HOUR = 60
LINKS_AFTER_MESSAGES = 10
PAGE_SIZE = 50
POLL_SECONDS = 30

NEARBY_QUERIES_PER_HOUR = 120
PLACE_SEARCH_PER_HOUR = 600

REGISTRATION_IP_MAX_24H = 3
REGISTRATION_IP_MAX_7D = 10
REGISTRATION_IP_KEEP_DAYS = 7

LOGIN_PAIR_FAILURES = 5          # pro Konto und IP
LOGIN_PAIR_LOCK_MINUTES = 15
LOGIN_ACCOUNT_FAILURES = 20      # pro Konto über alle IPs in einer Stunde -> Proof-of-Work
LOGIN_IP_FAILURES = 50           # pro IP in einer Stunde -> eine Stunde Sperre

POW_MAXNUMBER = int(env("POW_MAXNUMBER", "50000"))
POW_MAXNUMBER_HARD = int(env("POW_MAXNUMBER_HARD", "1000000"))
POW_TTL_SECONDS = 600

MUTE_REPORTERS = 3
MUTE_WINDOW_HOURS = 24
MUTE_REPORTER_MIN_ACTIVE_DAYS = 7
MUTE_HOURS = 48
INCIDENT_WINDOW_DAYS = 7
REPORT_SNAPSHOT_CONTEXT = 10
REPORT_KEEP_MONTHS = 12
AUDIT_KEEP_MONTHS = 24
TOMBSTONE_MAX_MONTHS = 24
PLACE_CHANGE_KEEP_DAYS = 30
JOURNAL_KEEP_DAYS = 60

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", "INFO")},
}
