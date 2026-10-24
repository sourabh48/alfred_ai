# Local email token rotation

**Operation boundary — 2026-10-15:** Verified fallback re-encryption tooling is present; live token re-encryption/old-key removal was not performed or authorized. Keep both decryptable key paths until separately approved backup/atomic apply/re-read verification. The unrouted legacy Gmail helper writes plaintext token JSON and must not be used for onboarding. [Provider register](ALFRED_EXTERNAL_INTEGRATIONS.md).

EmailConnection OAuth access and refresh tokens are encrypted at rest with the
primary DJANGO_SECRET_KEY; DJANGO_SECRET_KEY_FALLBACKS permit temporary old-key
reads. Signing-key rotation alone does not rewrite existing encrypted tokens.

Do not run these commands on a private/live database without explicit operator
authorization. No live rotation was performed during M14 development.

1. Stop token writers and take a verified protected database/config backup.
2. Establish the new primary and keep old keys as temporary fallbacks in the
   untracked local environment. Never print or commit keys/token values.
3. Rehearse on a disposable copy using `manage.py reencrypt_email_tokens`.
   This defaults to dry-run and emits counts only. Any invalid token blocks key
   retirement; obtain the missing recovery key or separately reconcile that row.
4. With authorization, run `manage.py reencrypt_email_tokens --apply`.
   The transaction rotates fallback-encrypted values, encrypts legacy plaintext,
   verifies primary-only decryption after re-reading every non-empty value, and
   rolls back the entire run on invalid data, conflicts or verification failure.
5. Re-run dry-run: fallback, legacy and invalid counts must all be zero.
   Retain fallback keys in the protected recovery backup. Remove runtime
   fallbacks only after successful verification and confirming other signing-key
   consumers are covered; re-run primary-only dry-run and restart acceptance.

Current-primary ciphertext and empty/null fields remain unchanged. A repeated
apply is idempotent. No schema migration is needed. Existing timestamps, expiry,
provider/account ownership and connection status remain unchanged. Rotation
preserves the original Fernet issuance timestamp, following the existing
[MultiFernet rotation API](https://cryptography.io/en/latest/fernet/#cryptography.fernet.MultiFernet.rotate).

Rollback: keep writers stopped; restore the protected pre-rotation database and
its compatible key set if necessary. Never remove the only decryptable original
or overwrite newer accepted token writes. The command never removes keys.
