"""Career email from each person's own sign-in address (owner decision 2026-11-19).

Each person ticks one of the email addresses they sign in with. ALFRED then asks that address's mail service, Google
(Gmail) or Microsoft (Outlook), for permission to send mail and, when ticked on its screen, to read the inbox for reply
watch. Nobody types an address or a password: only the provider's refresh token is kept, encrypted, in one private file
per person. GitHub has no mailbox, so a GitHub address sends only when it is a Gmail or Outlook address.
Every email still needs its own review and Send (application_send); reply watch only reads.
"""
from __future__ import annotations

import base64
import json
import os
import re
from datetime import datetime, timedelta, timezone as dt_timezone
from pathlib import Path

from django.conf import settings
from django.utils import timezone

from alfred_ai.services import public_http
from alfred_ai.services.public_http import PublicHTTPError

SEND = {"google": "https://www.googleapis.com/auth/gmail.send", "microsoft": "https://graph.microsoft.com/Mail.Send"}
READ = {"google": "https://www.googleapis.com/auth/gmail.readonly", "microsoft": "https://graph.microsoft.com/Mail.Read"}
LABEL = {"google": "Google", "github": "GitHub", "microsoft": "Microsoft"}
GMAIL, GRAPH = "https://gmail.googleapis.com", "https://graph.microsoft.com/v1.0/me"
# shortcut: Graph takes a whole request of 4 MB, so an Outlook email carries a CV up to 3 MB; use an upload session if CVs grow.
OUTLOOK_MAX_BYTES = 3 * 1024 * 1024
# The provider answered and refused, so it did not take the email; anything else mid-send may have delivered it.
REFUSED = ("unsafe_url", "authorization_failed", "api_error", "quota_exhausted", "redirect_blocked")
MAX_MESSAGES, BODY_CHARS = 200, 4000


class MailError(Exception):
    """A message safe to show the person."""


def scope(provider) -> str:
    return f"{SEND[provider]} {READ[provider]}" + (" offline_access" if provider == "microsoft" else "")


def _service(email: str) -> str:
    domain = email.rsplit("@", 1)[-1]
    if domain in ("gmail.com", "googlemail.com"):
        return "google"
    return "microsoft" if domain.split(".")[0] in ("outlook", "hotmail", "live", "msn") else ""


def _folder() -> Path:
    return Path(os.environ.get("ALFRED_DATA_DIR") or settings.BASE_DIR) / "artifacts" / "career-mail"


def _path(user) -> Path:
    return _folder() / f"user-{int(user.pk)}.json"


def _load(user) -> dict:
    try:
        data = json.loads(_path(user).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _store(user, data: dict) -> None:
    from alfred_private_storage import private_directory
    path = _path(user)
    private_directory(path.parent)
    temporary = path.with_suffix(".saving")
    temporary.write_text(json.dumps(data), encoding="utf-8")
    os.replace(temporary, path)


def choices(user) -> list:
    """The person's verified sign-in addresses, each with the mail service that can send from it (if any)."""
    from alfred_ai.services import social_login
    ready = {p["id"] for p in social_login.configured()}
    found = {}
    for identity in user.email_identities.order_by("pk"):
        email = identity.email.strip().lower()
        item = found.setdefault(email, {"email": email, "via": "", "signed_in_with": []})
        item["signed_in_with"].append(LABEL.get(identity.provider, identity.provider))
        item["via"] = item["via"] or (identity.provider if identity.provider in SEND else _service(email))
    for item in found.values():
        item["can_send"] = bool(item["via"]) and item["via"] in ready
        item["why"] = ("" if item["can_send"] else
                       f"{LABEL[item['via']]} sign-in is not set up on this PC." if item["via"] else
                       "GitHub has no mailbox, and this is not a Gmail or Outlook address, so ALFRED cannot send from it.")
    return list(found.values())


def status(user) -> dict:
    data = _load(user)
    return {"address": data.get("email", ""), "via": data.get("provider", ""), "ready": bool(data.get("refresh")),
            "reads_replies": bool(data.get("refresh") and data.get("read")), "choices": choices(user)}


def can_start(user, provider, email) -> bool:
    return any(c["email"] == str(email or "").strip().lower() and c["via"] == provider and c["can_send"] for c in choices(user))


def _granted(scopes: str, wanted: str) -> bool:
    # Google returns full scope URLs; Microsoft may return "Mail.Send" without its resource.
    return any(s == wanted or wanted.endswith("/" + s) for s in (scopes or "").split())


def connect(user, chosen: str, identity: dict, refresh_token: str | None, granted: str) -> None:
    from apps.integrations.models import _encrypt_token
    provider, chosen = identity["provider"], str(chosen or "").strip().lower()
    if identity["email"] != chosen:
        raise MailError(f"You signed in to {LABEL[provider]} as {identity['email']}, not {chosen}. Choose that address, or sign in as {chosen}.")
    if not can_start(user, provider, chosen):
        raise MailError("That address is not one you sign in with, so ALFRED cannot send from it.")
    if not refresh_token:
        raise MailError(f"{LABEL[provider]} did not give ALFRED lasting access. Remove ALFRED from your account's app permissions and try again.")
    if not _granted(granted, SEND[provider]):
        raise MailError(f"Tick \"send email\" on {LABEL[provider]}'s screen so ALFRED can send the emails you approve.")
    _store(user, {"email": chosen, "provider": provider, "refresh": _encrypt_token(refresh_token), "read": _granted(granted, READ[provider])})


def disconnect(user) -> dict:
    from apps.integrations.models import _decrypt_token
    data = _load(user)
    if data.get("provider") == "google" and data.get("refresh"):
        try:
            public_http.request("POST", "https://oauth2.googleapis.com/revoke", data={"token": _decrypt_token(data["refresh"])},
                                accepted_statuses=(200, 400))
        except PublicHTTPError:
            pass  # the local token is removed either way; the person can also remove ALFRED in their Google account
    _path(user).unlink(missing_ok=True)
    return status(user)


def _access(user, data: dict) -> str:
    from alfred_ai.services import social_login
    from apps.integrations.models import _decrypt_token, _encrypt_token
    provider = data["provider"]
    client_id, secret = social_login._client(provider)
    form = {"grant_type": "refresh_token", "refresh_token": _decrypt_token(data["refresh"]), "client_id": client_id, "client_secret": secret}
    if provider == "microsoft":
        form["scope"] = scope(provider)
    try:
        token = public_http.request("POST", social_login.PROVIDERS[provider][2], headers={"Accept": "application/json"}, data=form).json()
    except PublicHTTPError as exc:
        raise MailError(f"{LABEL[provider]} refused ALFRED's access; choose your address again in Settings." if exc.code in REFUSED
                        else f"Could not reach {LABEL[provider]}. Try again later.") from None
    if not isinstance(token, dict) or not token.get("access_token"):
        raise MailError(f"{LABEL[provider]} refused ALFRED's access; choose your address again in Settings.")
    if token.get("refresh_token"):  # Microsoft replaces the refresh token as it is used
        _store(user, {**data, "refresh": _encrypt_token(token["refresh_token"])})
    return token["access_token"]


def deliver(user, message) -> str:
    """'sent', 'failed' (the provider never took it) or 'unknown' (the connection broke once the email was handed over)."""
    data = _load(user)
    if not data.get("refresh"):
        return "failed"
    try:
        token = _access(user, data)
    except MailError:
        return "failed"
    mime = message.message()
    raw = mime.as_bytes(policy=mime.policy.clone(linesep="\r\n"))
    if data["provider"] == "google":  # the upload endpoint takes the whole email, CV included, as it is
        url, body, kind = f"{GMAIL}/upload/gmail/v1/users/me/messages/send?uploadType=media", raw, "message/rfc822"
    else:
        url, body, kind = f"{GRAPH}/sendMail", base64.b64encode(raw), "text/plain"
    try:
        public_http.request("POST", url, headers={"Authorization": f"Bearer {token}", "Content-Type": kind}, data=body,
                            accepted_statuses=(200, 202))
    except PublicHTTPError as exc:
        return "failed" if exc.code in REFUSED else "unknown"
    return "sent"


def _get(token, url, params=None, headers=None):
    return public_http.request("GET", url, params=params, headers={"Authorization": f"Bearer {token}", **(headers or {})}).json()


def _gmail_text(part) -> str:
    if part.get("mimeType") == "text/plain" and (part.get("body") or {}).get("data"):
        return base64.urlsafe_b64decode(part["body"]["data"] + "==").decode("utf-8", "replace")
    return next((text for child in part.get("parts") or [] if (text := _gmail_text(child))), "")


def _clip(text) -> str:
    return " ".join(str(text or "").split())[:BODY_CHARS]


def read_inbox(user, *, days: int) -> list:
    """Recent inbox messages (sender, subject, date, a plain-text excerpt); reading never marks anything read."""
    from email.utils import parseaddr
    data = _load(user)
    if not (data.get("refresh") and data.get("read")):
        raise MailError("Choose your Career email address in Settings and tick \"read email\" on its screen first.")
    token = _access(user, data)
    messages = []
    try:
        if data["provider"] == "google":
            listing = _get(token, f"{GMAIL}/gmail/v1/users/me/messages", {"q": f"in:inbox newer_than:{days}d", "maxResults": MAX_MESSAGES})
            for item in (listing.get("messages") or [])[:MAX_MESSAGES]:
                found = _get(token, f"{GMAIL}/gmail/v1/users/me/messages/{item['id']}", {"format": "full"})
                head = {h.get("name", "").lower(): h.get("value", "") for h in (found.get("payload") or {}).get("headers", [])}
                name, address = parseaddr(head.get("from", ""))
                on = datetime.fromtimestamp(int(found.get("internalDate") or 0) / 1000, dt_timezone.utc).date().isoformat()
                messages.append({"id": str(found.get("id") or item["id"]), "from_name": name[:120], "from": address[:200],
                                 "subject": _clip(head.get("subject"))[:300], "on": on, "body": _clip(_gmail_text(found.get("payload") or {})),
                                 "attachment": bool(_gmail_files(found.get("payload") or {}))})
        else:
            since = (timezone.now() - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
            url, params = f"{GRAPH}/mailFolders/inbox/messages", {"$filter": f"receivedDateTime ge {since}", "$top": 50,
                                                                    "$select": "id,from,subject,receivedDateTime,body,hasAttachments",
                                                                    "$orderby": "receivedDateTime desc"}
            while url and len(messages) < MAX_MESSAGES:
                page = _get(token, url, params, {"Prefer": 'outlook.body-content-type="text"'})
                for item in page.get("value") or []:
                    sender = (item.get("from") or {}).get("emailAddress") or {}
                    messages.append({"id": str(item.get("id") or ""), "from_name": str(sender.get("name") or "")[:120],
                                     "from": str(sender.get("address") or "")[:200], "subject": _clip(item.get("subject"))[:300],
                                     "on": str(item.get("receivedDateTime") or "")[:10], "body": _clip((item.get("body") or {}).get("content")),
                                     "attachment": item.get("hasAttachments") is True})
                url, params = page.get("@odata.nextLink"), None
    except PublicHTTPError:
        raise MailError(f"Could not read your inbox at {LABEL[data['provider']]} right now. Try again later.") from None
    return messages[:MAX_MESSAGES]


JOB_FILES, MAX_ATTACHMENT_BYTES = (".pdf", ".docx", ".txt"), 10 * 1024 * 1024
MAIL_ID = re.compile(r"[A-Za-z0-9_=+-]{1,512}")


def _gmail_files(part) -> list:
    """(filename, attachment id, size) of every attached job-description file in a Gmail payload."""
    body, name = part.get("body") or {}, str(part.get("filename") or "")
    found = [(name, body["attachmentId"], int(body.get("size") or 0))] if name.lower().endswith(JOB_FILES) and body.get("attachmentId") else []
    return found + [file for child in part.get("parts") or [] for file in _gmail_files(child)]


def read_message(user, mail_id) -> dict:
    """One inbox email the person chose, for the recruiter intake: its text and its first job-description file, if any.

    Read-only, like reply watch: nothing is marked read, moved or kept here; the intake stores what the person analyses.
    """
    from django.core.files.uploadedfile import SimpleUploadedFile
    from urllib.parse import quote
    if not isinstance(mail_id, str) or not MAIL_ID.fullmatch(mail_id):
        raise MailError("Choose an email from the reply watch list.")
    data = _load(user)
    if not (data.get("refresh") and data.get("read")):
        raise MailError("Choose your Career email address in Settings and tick \"read email\" on its screen first.")
    token, ident, file = _access(user, data), quote(mail_id, safe=""), None
    try:
        if data["provider"] == "google":
            found = _get(token, f"{GMAIL}/gmail/v1/users/me/messages/{ident}", {"format": "full"})
            head = {h.get("name", "").lower(): h.get("value", "") for h in (found.get("payload") or {}).get("headers", [])}
            text = f"{head.get('subject', '')}\n{_gmail_text(found.get('payload') or {})}"
            for name, attachment, size in _gmail_files(found.get("payload") or {}):
                if size <= MAX_ATTACHMENT_BYTES:
                    raw = _get(token, f"{GMAIL}/gmail/v1/users/me/messages/{ident}/attachments/{quote(attachment, safe='')}")
                    file = (name, base64.urlsafe_b64decode(str(raw.get("data") or "") + "=="))
                    break
        else:
            found = _get(token, f"{GRAPH}/messages/{ident}", {"$select": "subject,body"}, {"Prefer": 'outlook.body-content-type="text"'})
            text = f"{found.get('subject') or ''}\n{(found.get('body') or {}).get('content') or ''}"
            listing = _get(token, f"{GRAPH}/messages/{ident}/attachments", {"$select": "id,name,size"})
            for item in listing.get("value") or []:
                name = str(item.get("name") or "")
                if name.lower().endswith(JOB_FILES) and int(item.get("size") or 0) <= MAX_ATTACHMENT_BYTES:
                    raw = _get(token, f"{GRAPH}/messages/{ident}/attachments/{quote(str(item.get('id') or ''), safe='')}")
                    file = (name, base64.b64decode(str(raw.get("contentBytes") or "")))
                    break
    except PublicHTTPError:
        raise MailError(f"Could not read that email at {LABEL[data['provider']]} right now. Try again later.") from None
    except (ValueError, TypeError):
        raise MailError("That email's attachment could not be read. Save it and upload it instead.") from None
    return {"text": text.strip()[:20000], "attachment": SimpleUploadedFile(file[0][:180], file[1]) if file else None}
