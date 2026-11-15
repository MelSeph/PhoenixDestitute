"""Serve the existing backend against a temporary database for UI integration tests."""
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "django"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "phoenixdestitute.settings")

import django
from django.conf import settings
from django.core.management import call_command

with TemporaryDirectory(prefix="phoenix-react-test-") as directory:
    settings.DATABASES["default"]["NAME"] = str(Path(directory) / "test.sqlite3")
    django.setup()
    call_command("migrate", verbosity=0)
    call_command("runserver", "127.0.0.1:8000", use_reloader=False)
