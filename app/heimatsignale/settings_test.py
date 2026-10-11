"""Einstellungen für die Tests: schnelle Hasher, kleines Proof-of-Work, eigenes Journal."""

import os
import tempfile

os.environ.setdefault("DEBUG", "1")

from .settings import *  # noqa: E402,F403

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
POW_MAXNUMBER = 200
POW_MAXNUMBER_HARD = 400
TRUSTED_PROXY_COUNT = 0
SITE_URL = "https://test.example"
DELETION_JOURNAL_PATH = os.path.join(tempfile.mkdtemp(prefix="journal-"), "loeschjournal.sqlite3")
LOGGING["loggers"] = {"django.request": {"level": "ERROR"}, "django.security.csrf": {"level": "ERROR"}}  # noqa: F405
