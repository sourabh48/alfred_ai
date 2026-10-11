"""Verified, atomic OAuth token rotation; no secret values in reports/errors."""
from hmac import compare_digest

from cryptography.fernet import InvalidToken
from django.db import transaction

from apps.integrations.models import EmailConnection, TOKEN_PREFIX, _email_token_cipher


def reencrypt_email_tokens(*, apply=False):
    primary = _email_token_cipher(include_fallbacks=False)
    readable = _email_token_cipher()
    report = dict(connections=0, primary=0, fallback=0, legacy=0, empty=0, invalid=0, verified=0)
    with transaction.atomic():
        for row in EmailConnection.objects.select_for_update().order_by('pk').iterator(chunk_size=200):
            report['connections'] += 1
            changes, expected = {}, {}
            for field in ('access_token', 'refresh_token'):
                value = getattr(row, field)
                if not value:
                    report['empty'] += 1
                    continue
                if value.startswith(TOKEN_PREFIX):
                    encrypted = value[len(TOKEN_PREFIX):].encode('utf-8')
                    try:
                        expected[field] = primary.decrypt(encrypted)
                        report['primary'] += 1
                        continue
                    except InvalidToken:
                        try:
                            expected[field] = readable.decrypt(encrypted)
                            changes[field] = TOKEN_PREFIX + readable.rotate(encrypted).decode('ascii')
                            report['fallback'] += 1
                        except InvalidToken:
                            report['invalid'] += 1
                            if apply:
                                raise InvalidToken() from None
                            continue
                else:
                    expected[field] = value.encode('utf-8')
                    changes[field] = TOKEN_PREFIX + primary.encrypt(expected[field]).decode('ascii')
                    report['legacy'] += 1
                if not compare_digest(primary.decrypt(changes[field][len(TOKEN_PREFIX):].encode('ascii')), expected[field]):
                    raise InvalidToken()
            if apply:
                if changes:
                    # Conditional update also detects concurrent writers on SQLite.
                    changed = EmailConnection.objects.filter(pk=row.pk,
                        access_token=row.access_token, refresh_token=row.refresh_token).update(**changes)
                    if changed != 1:
                        raise RuntimeError('Token rotation conflict')
                saved = EmailConnection.objects.values('access_token', 'refresh_token').get(pk=row.pk)
                for field, plaintext in expected.items():
                    encrypted = saved[field][len(TOKEN_PREFIX):].encode('utf-8')
                    if not compare_digest(primary.decrypt(encrypted), plaintext):
                        raise InvalidToken()
                    report['verified'] += 1
    return report
