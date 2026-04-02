import base64
import hashlib

from cryptography.fernet import Fernet
from django.conf import settings
from django.db import migrations


TOKEN_PREFIX = "enc::"


def _cipher():
    digest = hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def _encrypt(value):
    if not value or value.startswith(TOKEN_PREFIX):
        return value
    encrypted = _cipher().encrypt(value.encode("utf-8")).decode("utf-8")
    return f"{TOKEN_PREFIX}{encrypted}"


def encrypt_email_tokens(apps, schema_editor):
    EmailConnection = apps.get_model("integrations", "EmailConnection")
    for connection in EmailConnection.objects.all():
        encrypted_access = _encrypt(connection.access_token)
        encrypted_refresh = _encrypt(connection.refresh_token)
        if encrypted_access != connection.access_token or encrypted_refresh != connection.refresh_token:
            connection.access_token = encrypted_access
            connection.refresh_token = encrypted_refresh
            connection.save(update_fields=["access_token", "refresh_token", "updated_at"])


class Migration(migrations.Migration):

    dependencies = [
        ("integrations", "0004_creditreportupload"),
    ]

    operations = [
        migrations.RunPython(encrypt_email_tokens, migrations.RunPython.noop),
    ]
