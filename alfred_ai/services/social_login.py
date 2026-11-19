"""Sign in with Google, GitHub or Microsoft (Outlook), which also proves the person's email address.

The owner adds each provider's client id and secret in Settings > Online services; a provider without both is not shown.
Standard OAuth 2.0 authorization-code flow with PKCE and a one-time state kept in the session. The code is exchanged
directly with the provider over TLS, and only the account id and a verified email are read back; no token is stored.
"""
from __future__ import annotations

import base64
import hashlib
import os
import re
import secrets
from urllib.parse import urlencode

from django.contrib.auth import get_user_model
from django.db import transaction

from alfred_ai.services import public_http
from alfred_ai.services.public_http import PublicHTTPError

# name: (label, authorize url, token url, scope)
PROVIDERS = {
    "google": ("Google", "https://accounts.google.com/o/oauth2/v2/auth", "https://oauth2.googleapis.com/token", "openid email"),
    "github": ("GitHub", "https://github.com/login/oauth/authorize", "https://github.com/login/oauth/access_token", "read:user user:email"),
    # Personal Microsoft accounts (Outlook.com, Hotmail, Live) only: their email is verified, a work account's may not be.
    "microsoft": ("Microsoft (Outlook)", "https://login.microsoftonline.com/consumers/oauth2/v2.0/authorize",
                  "https://login.microsoftonline.com/consumers/oauth2/v2.0/token", "openid email"),
}
SESSION_KEY = "alfred_social_login"
# Azure lists each client secret with a Secret ID (a GUID) beside its Value; only the Value signs in.
GUID = re.compile(r"[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}")
SECRET_ID_MESSAGE = ("That is the Microsoft secret's ID, not the secret. In the Azure portal open the app, then Certificates & secrets, and copy the Value column (shown only when the secret is created; make a new one if it is hidden).")


class SignInError(Exception):
    """A message safe to show the person."""


def _client(provider):
    prefix = f"ALFRED_{provider.upper()}"
    return os.environ.get(f"{prefix}_CLIENT_ID", ""), os.environ.get(f"{prefix}_CLIENT_SECRET", "")


def configured() -> list[dict]:
    return [{"id": p, "label": label} for p, (label, *_rest) in PROVIDERS.items() if all(_client(p))]


def callback_path(provider) -> str:
    return f"/auth/{provider}/callback/"


def start(session, provider, redirect_uri, next_url="/", connect=False, purpose="", hint="") -> str:
    """The provider's sign-in page; the state and PKCE verifier stay in this browser's session.

    purpose="sync" (Google only) also asks for the phone-sync permissions and lasting (offline) access; see google_sync.
    purpose="mail" (Google or Microsoft) asks to send, and read for reply watch, as the address in hint; see career_mail.
    purpose="backupkey" (Google only) asks for ALFRED's hidden Drive app folder once, to save ("save" in hint) or fetch
    ("fetch") the passphrase-locked backup key; see backup_key. No lasting access is kept.
    """
    if provider not in PROVIDERS or not all(_client(provider)):
        raise SignInError("That sign-in is not set up. Add its client id and secret in Settings first.")
    if purpose == "sync" and provider != "google":
        raise SignInError("Phone sync works with Google only.")
    if purpose == "mail" and provider not in ("google", "microsoft"):
        raise SignInError("Career email is sent through Google or Microsoft only.")
    if purpose == "backupkey" and (provider != "google" or hint not in ("save", "fetch")):
        raise SignInError("The backup key copy is kept in Google Drive only.")
    if purpose not in ("", "sync", "mail", "backupkey"):
        raise SignInError("That permission is not available.")
    state, verifier = secrets.token_urlsafe(32), secrets.token_urlsafe(64)
    session[SESSION_KEY] = {"provider": provider, "state": state, "verifier": verifier, "next": next_url,
                            "connect": connect, "redirect_uri": redirect_uri, "purpose": purpose, "hint": hint}
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    _label, authorize, _token, scope = PROVIDERS[provider]
    query = {"client_id": _client(provider)[0], "redirect_uri": redirect_uri, "response_type": "code", "scope": scope,
             "state": state, "code_challenge": challenge, "code_challenge_method": "S256"}
    if provider == "google":
        query["prompt"] = "select_account"
    if purpose == "sync":
        from .google_sync import SCOPES
        query.update(scope=f"{scope} {SCOPES}", access_type="offline", prompt="consent select_account")
    if purpose == "mail":
        from apps.career.services.career_mail import scope as mail_scope
        query.update(scope=f"{scope} {mail_scope(provider)}", login_hint=hint)
        if provider == "google":
            query.update(access_type="offline", prompt="consent")
    if purpose == "backupkey":
        from .backup_key import SCOPE as drive_scope
        query["scope"] = f"{scope} {drive_scope}"
    return f"{authorize}?{urlencode(query)}"


def finish(session, provider, params) -> tuple[dict, dict]:
    """(identity, pending) after checking the state once; identity is {provider, subject, email} with a verified email."""
    pending = session.pop(SESSION_KEY, None) or {}
    if params.get("error"):
        raise SignInError("Sign-in was cancelled.")
    if (pending.get("provider") != provider or not params.get("code")
            or not secrets.compare_digest(str(pending.get("state", "")), str(params.get("state", "")))):
        raise SignInError("That sign-in link expired. Please try again.")
    client_id, secret = _client(provider)
    try:
        token = public_http.request("POST", PROVIDERS[provider][2], headers={"Accept": "application/json"}, data={
            "grant_type": "authorization_code", "code": params["code"], "redirect_uri": pending["redirect_uri"],
            "client_id": client_id, "client_secret": secret, "code_verifier": pending["verifier"]}).json()
        access = token.get("access_token") if isinstance(token, dict) else None
        if not access:
            raise SignInError(f"{PROVIDERS[provider][0]} did not accept the sign-in. Check its client id and secret in Settings.")
        identity = _identity(provider, {"Authorization": f"Bearer {access}", "Accept": "application/json"})
        if pending.get("purpose") in ("sync", "mail"):  # handed to google_sync or career_mail, never kept in the session
            pending = {**pending, "refresh_token": token.get("refresh_token"), "granted": token.get("scope", "")}
        if pending.get("purpose") == "backupkey":  # used once by backup_key during this request, never stored
            pending = {**pending, "access_token": access, "granted": token.get("scope", "")}
    except PublicHTTPError as exc:
        if exc.code in ("authorization_failed", "api_error"):  # a wrong secret or an expired code
            if provider == "microsoft" and GUID.fullmatch(secret):
                raise SignInError(SECRET_ID_MESSAGE) from None
            raise SignInError(f"{PROVIDERS[provider][0]} did not accept the sign-in. Try again, or check its client id and secret in Settings.") from None
        raise SignInError(f"Could not reach {PROVIDERS[provider][0]}. Check the internet connection and try again.") from None
    return identity, pending


def _get(url, headers):
    return public_http.request("GET", url, headers=headers).json()


def _identity(provider, headers) -> dict:
    if provider == "github":
        account = _get("https://api.github.com/user", headers)
        emails = _get("https://api.github.com/user/emails", headers)
        email = next((e.get("email") for e in emails if isinstance(e, dict) and e.get("primary") and e.get("verified")), "")
        subject = account.get("id")
    else:
        info = _get("https://openidconnect.googleapis.com/v1/userinfo" if provider == "google"
                    else "https://graph.microsoft.com/oidc/userinfo", headers)
        # Google states it; a personal Microsoft account's sign-in email is always verified by Microsoft.
        verified = info.get("email_verified") is True if provider == "google" else True
        email, subject = (info.get("email") if verified else ""), info.get("sub")
    if not subject:
        raise SignInError(f"{PROVIDERS[provider][0]} did not say who signed in. Please try again.")
    if not email or "@" not in str(email):
        raise SignInError(f"Your {PROVIDERS[provider][0]} account has no verified email address, so ALFRED cannot use it.")
    return {"provider": provider, "subject": str(subject), "email": str(email).strip().lower()}


def user_for(identity, connect_to=None):
    """The person this identity signs in as: the linked account, else an account whose email another provider
    already verified, else a new account. With connect_to, links the identity to that signed-in person instead."""
    from apps.users.models import EmailIdentity
    users = get_user_model().objects
    with transaction.atomic():
        linked = EmailIdentity.objects.select_related("user").filter(provider=identity["provider"], subject=identity["subject"]).first()
        if connect_to is not None:
            if linked and linked.user_id != connect_to.pk:
                raise SignInError("That account is already used by another ALFRED person.")
            user = connect_to
        elif linked:
            user = linked.user
        else:
            verified = EmailIdentity.objects.select_related("user").filter(email__iexact=identity["email"]).first()
            # An account made with a password before sign-in became provider-only keeps its records (owner 2026-11-19).
            same_email = list(users.filter(email__iexact=identity["email"], is_active=True)[:2])
            user = verified.user if verified else same_email[0] if len(same_email) == 1 else _new_user(users, identity["email"])
        if not user.is_active:
            raise SignInError("This ALFRED account is switched off.")
        EmailIdentity.objects.update_or_create(provider=identity["provider"], subject=identity["subject"],
                                               defaults={"user": user, "email": identity["email"]})
        if not is_verified(user):  # the address the provider just proved becomes the account's email
            user.email = identity["email"]
            user.save(update_fields=["email"])
    return user


def _new_user(users, email):
    base = "".join(c for c in email.split("@", 1)[0] if c.isalnum() or c in "._-")[:120] or "user"
    name, n = base, 1
    while users.filter(username__iexact=name).exists():
        n += 1
        name = f"{base}{n}"
    user = users.create_user(username=name, email=email)
    user.set_unusable_password()  # signs in only through the provider until they choose a password
    user.save(update_fields=["password"])
    return user


def is_verified(user) -> bool:
    return bool(user.email) and user.email_identities.filter(email__iexact=user.email).exists()


def password_signup_open() -> bool:
    """Passwords work only on a copy with no sign-in provider at all (a source checkout or test run); owner 2026-11-19."""
    return not configured()
