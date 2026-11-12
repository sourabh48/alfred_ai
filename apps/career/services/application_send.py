"""Career emails the owner approves one at a time (CAREER2-002), sent from the owner's own mailbox.

The owner approved sending on 2026-11-12 on one condition: ALFRED shows the exact recipient, subject, body
and attachment, and sends only when the owner confirms that one email. So a send needs a signed review of
exactly that content, made within the last 15 minutes. Any change, including a new or changed CV file, makes
the review stale and is refused. A retry of an email already sent never sends it again.
"""
import hashlib
import re

from django.conf import settings
from django.core import signing
from django.core.exceptions import ValidationError
from django.core.mail import EmailMessage, get_connection
from django.core.validators import validate_email
from django.utils import timezone

REVIEW_SECONDS = 15 * 60
MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024
PLACEHOLDER_RE = re.compile(r"\[[^\]\n]{1,80}\]")
SALT = "career-send-review"


class SendRefused(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def mail_configured() -> bool:
    return bool(settings.ALFRED_SMTP_HOST and settings.ALFRED_SMTP_USER and settings.ALFRED_SMTP_PASSWORD)


def _attachment(resume):
    """The stored original CV, read once so its hash is what gets reviewed and what gets sent."""
    if resume is None:
        return None, "Upload your CV to attach it."
    field = resume.uploaded_file
    try:
        if not field or not field.storage.exists(field.name):
            return None, "ALFRED no longer keeps your original CV file. Upload it again to attach it."
        if field.size > MAX_ATTACHMENT_BYTES:
            return None, "Your CV file is larger than 10 MB."
        field.open("rb")
        try:
            content = field.read(MAX_ATTACHMENT_BYTES + 1)
        finally:
            field.close()
    except OSError:
        return None, "Your CV file could not be read. Upload it again."
    return {"resume_id": resume.pk, "name": resume.file_name, "bytes": len(content),
            "sha256": hashlib.sha256(content).hexdigest(), "content": content}, None


def _digest(user, analysis, to, subject, body, attachment) -> str:
    parts = [str(user.pk), str(analysis.pk), to.casefold(), subject, body,
             f"{attachment['resume_id']}:{attachment['sha256']}" if attachment else "no-attachment"]
    return hashlib.sha256("\x1f".join(parts).encode()).hexdigest()


def _payload(analysis) -> dict:
    return analysis.extracted_payload if isinstance(analysis.extracted_payload, dict) else {}


def _sent_log(analysis) -> list:
    return [item for item in _payload(analysis).get("sent_messages") or [] if isinstance(item, dict)]


def review(user, analysis, resume, *, to, subject, body, attach_cv) -> dict:
    """The attachment manifest and checklist; a signed token only when nothing blocks the send."""
    to = to.strip() if isinstance(to, str) else ""
    subject = " ".join(subject.split()) if isinstance(subject, str) else ""
    body = body.replace("\r\n", "\n").strip() if isinstance(body, str) else ""
    if len(subject) > 200 or len(body) > 10000 or len(to) > 254:
        raise SendRefused("Keep the subject under 200 characters and the email under 10,000.")
    blockers, warnings = [], []
    try:
        validate_email(to)
    except ValidationError:
        blockers.append("Enter one valid recipient email address.")
    if not subject:
        blockers.append("Add a subject.")
    if not body:
        blockers.append("Write the email.")
    leftover = sorted(set(PLACEHOLDER_RE.findall(f"{subject}\n{body}")))
    if leftover:
        blockers.append(f"Fill or remove the bracketed parts: {', '.join(leftover[:5])}.")
    attachment, problem = _attachment(resume) if attach_cv else (None, None)
    if problem:
        blockers.append(problem)
    if attach_cv and resume is not None and resume.parser_status != "parsed":
        warnings.append("Your CV extraction still needs review; check the file you are attaching.")
    if not mail_configured():
        blockers.append("Sending is off: add your mailbox (ALFRED_SMTP_HOST, ALFRED_SMTP_USER, ALFRED_SMTP_PASSWORD) "
                        "to config/local.env and restart ALFRED.")
    triage = _payload(analysis).get("triage")
    if isinstance(triage, dict) and isinstance(triage.get("score"), (int, float)) and triage["score"] < 4.0:
        warnings.append(f"Triage score {triage['score']}/5 is below 4.0, where Career Ops advises against applying.")
    digest = _digest(user, analysis, to, subject, body, attachment)
    if any(item.get("digest") == digest and item.get("status") == "sent" for item in _sent_log(analysis)):
        blockers.append("You already sent this exact email for this job.")
    previous = [item for item in _sent_log(analysis) if item.get("status") == "sent" and item.get("to", "").casefold() == to.casefold()]
    if previous and not blockers:
        warnings.append(f"You emailed {to} about this job on {previous[-1].get('sent_at', '')[:10]}.")
    sender = settings.ALFRED_SMTP_FROM or settings.ALFRED_SMTP_USER
    return {
        "to": to, "from": sender, "subject": subject, "body": body,
        "attachments": [{key: attachment[key] for key in ("name", "bytes", "sha256")}] if attachment else [],
        "blockers": blockers, "warnings": warnings, "ready": not blockers,
        "confirmation": signing.TimestampSigner(salt=SALT).sign(digest) if not blockers else "",
        "note": "Nothing is sent until you press Send for this email. Any change needs a new review.",
    }


def send(user, analysis, resume, *, to, subject, body, attach_cv, confirmation):
    """Send exactly what was reviewed. Returns (result, created): created is False when it was already sent."""
    from apps.career.models import CareerJobAnalysis
    try:
        reviewed = signing.TimestampSigner(salt=SALT).unsign(confirmation if isinstance(confirmation, str) else "", max_age=REVIEW_SECONDS)
    except signing.SignatureExpired:
        raise SendRefused("This review is older than 15 minutes. Review the email again before sending.", 409)
    except signing.BadSignature:
        raise SendRefused("Review the email before sending it.", 409)
    current = review(user, analysis, resume, to=to, subject=subject, body=body, attach_cv=attach_cv)
    attachment = _attachment(resume)[0] if attach_cv else None
    digest = _digest(user, analysis, current["to"], current["subject"], current["body"], attachment)
    already = next((item for item in _sent_log(analysis) if item.get("digest") == digest and item.get("status") == "sent"), None)
    if already:
        return already, False
    if digest != reviewed:
        raise SendRefused("The email, recipient or CV file changed since you reviewed it. Review it again before sending.", 409)
    if current["blockers"]:
        raise SendRefused(" ".join(current["blockers"]))
    record = {"digest": digest, "to": current["to"], "subject": current["subject"],
              "attachment": attachment["name"] if attachment else "", "status": "sending", "sent_at": ""}
    log = [item for item in _sent_log(analysis) if item.get("digest") != digest]
    claimed = CareerJobAnalysis.objects.filter(pk=analysis.pk, user=user, updated_at=analysis.updated_at).update(
        extracted_payload={**_payload(analysis), "sent_messages": [*log, record]}, updated_at=timezone.now())
    if not claimed:
        raise SendRefused("This job changed or another send is in progress. Reload it and review again.", 409)
    message = EmailMessage(current["subject"], current["body"], current["from"], [current["to"]])
    if attachment:
        message.attach(attachment["name"], attachment["content"])
    try:
        connection = get_connection(settings.ALFRED_SMTP_BACKEND, host=settings.ALFRED_SMTP_HOST, port=settings.ALFRED_SMTP_PORT,
                                    username=settings.ALFRED_SMTP_USER, password=settings.ALFRED_SMTP_PASSWORD,
                                    use_tls=not settings.ALFRED_SMTP_SSL, use_ssl=settings.ALFRED_SMTP_SSL, timeout=30)
        sent = connection.send_messages([message]) == 1
    except Exception:  # SMTP and socket errors; the record must not stay "sending"
        sent = False
    record = {**record, "status": "sent" if sent else "failed", "sent_at": timezone.now().isoformat() if sent else ""}
    analysis.refresh_from_db()
    log = [item for item in _sent_log(analysis) if item.get("digest") != digest]
    CareerJobAnalysis.objects.filter(pk=analysis.pk, user=user).update(
        extracted_payload={**_payload(analysis), "sent_messages": [*log, record]}, updated_at=timezone.now())
    if not sent:
        raise SendRefused("Your mail server did not accept the email. Nothing was sent; check the mailbox settings and try again.", 502)
    return record, True
