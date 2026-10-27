"""Trip references to existing owner-encrypted uploads; no second file/text copy."""
from pathlib import Path
import sqlite3

from cryptography.fernet import InvalidToken

from django.conf import settings
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework.exceptions import APIException, ValidationError

from apps.ml_engine.services.document_corpus import DocumentCorpus
from apps.ml_engine.services.memory_key import MemoryStorageUnavailable
from apps.ml_engine.services.memory_sync import valid_id
from apps.ml_engine.services.persistent_memory import MemoryConflict, MemoryStore
from ..travel_discovery import fact, value
from .editor import EditConflict


class DocumentsUnavailable(APIException):
    status_code = 503
    default_detail = "Private document copies are unavailable. Existing trip links and originals are retained; retry later."


def catalog(user):
    try:
        records = DocumentCorpus(MemoryStore(Path(settings.ALFRED_MEMORY_DIR))).list(user)["documents"]
    except (MemoryStorageUnavailable, MemoryConflict, OSError, ValueError, sqlite3.Error, InvalidToken, RuntimeError):
        raise DocumentsUnavailable() from None
    current = {}
    for row in records:
        if row.get("kind") != "upload" or not valid_id(row.get("id")) or not valid_id(row.get("source_fingerprint"), 64):
            continue
        try:
            expiry = parse_datetime(row.get("expires_at") or "")
        except (ValueError, TypeError, OverflowError):
            expiry = None
        if expiry and timezone.is_aware(expiry) and expiry > timezone.now():
            current[row["id"]] = {"id": row["id"], "name": row["document_name"],
                "fingerprint": row["source_fingerprint"], "expires_at": row["expires_at"],
                "original_path": f'/api/ai/document-corpus/{row["id"]}/original/'}
    return current


def document_links(session):
    links = value(session.state, "_itinerary_documents", [])
    if not links:
        return []
    try:
        current = catalog(session.user)
    except DocumentsUnavailable:
        current = {}
    return [{**current[row["id"]], "status": "available"}
        if row["id"] in current and current[row["id"]]["fingerprint"] == row["fingerprint"] else
        {"id": row["id"], "status": "unavailable", "name": "Linked document unavailable, changed or expired"}
        for row in links]


def update_documents(session, data):
    if set(data) - {"action", "operation", "revision", "document_id", "fingerprint"}:
        raise ValidationError("Choose a listed private document without extra fields.")
    operation = data.get("operation")
    if operation == "list":
        return list(catalog(session.user).values())
    identity = data.get("document_id")
    if operation not in {"link", "unlink"} or not valid_id(identity):
        raise ValidationError("Choose a private upload to link or unlink.")
    links = list(value(session.state, "_itinerary_documents", []))
    if operation == "link":
        source = catalog(session.user).get(identity)
        if not source or source["fingerprint"] != data.get("fingerprint"):
            raise EditConflict("That private copy changed, expired or is not yours. Refresh the document list.")
        entry = {"id": identity, "fingerprint": source["fingerprint"]}
        if entry in links:
            return None
    elif not any(row["id"] == identity for row in links):
        return None
    if type(data.get("revision")) is not int or data["revision"] != session.revision:
        raise EditConflict()
    links = [row for row in links if row["id"] != identity]
    if operation == "link":
        if len(links) >= 10:
            raise ValidationError("A trip supports at most10 private document references.")
        links.append(entry)
    session.state["_itinerary_documents"] = fact(links, "owner_selected_documents")
    updated = type(session).objects.filter(pk=session.pk, user=session.user, revision=session.revision).update(
        state=session.state, revision=session.revision+1, updated_at=timezone.now())
    if not updated:
        raise EditConflict()
    session.refresh_from_db()
    return None
