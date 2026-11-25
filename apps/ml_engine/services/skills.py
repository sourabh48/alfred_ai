"""Skills: short how-to instructions a person approves, which ALFRED adds to a matching question (owner 2026-11-25).

Inspired by OpenJarvis skills and its GitHub skill sources (Apache-2.0, 86f75ef), built independently. A skill here is
text only: nothing is run and no script, tool or dependency is installed. A skill may guide money and document
questions too (owner 2026-11-25), but it only goes to the local model on this PC, never to a cloud model, Telegram or
another agent, and it never overrides ALFRED's money rules. A skill imported from GitHub is shown in full first and is saved only when the person
approves that exact text; changed text needs a new approval. Each person's skills are their own.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import threading
from pathlib import Path
from urllib.parse import urlsplit

from django.conf import settings
from django.utils import timezone

from .prompt_injection import finding

SCOPES = ("general", "travel", "career", "finance", "documents")
# Answer scopes that share a skill group: bank and record questions use Money skills, document questions Document skills.
GROUPS = {"bank_statements": "finance", "financial_records": "finance", "financial_document": "documents"}
LIMITS = {"name": 80, "description": 300, "text": 4000}
STOP = {"what", "when", "where", "which", "with", "your", "this", "that", "from", "have", "about", "into", "should", "would",
        "could", "there", "their", "them", "then", "than", "make", "help", "please", "skill", "guide", "for", "and", "the"}
_lock = threading.Lock()


class SkillError(ValueError):
    pass


def _path() -> Path:
    return Path(os.environ.get("ALFRED_DATA_DIR") or settings.BASE_DIR) / "config" / "skills.json"


def _load() -> dict:
    try:
        data = json.loads(_path().read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _save(data) -> None:
    path = _path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    temporary.replace(path)


def _digest(skill) -> str:
    return hashlib.sha256(json.dumps([skill["name"], skill["description"], skill["scope"], skill["text"]]).encode()).hexdigest()


def clean(fields) -> dict:
    """The skill's fields, checked; raises SkillError before anything is saved."""
    if not isinstance(fields, dict):
        raise SkillError("Send the skill as JSON.")
    skill = {key: " ".join(str(fields.get(key) or "").split()) if key != "text" else str(fields.get(key) or "").strip()
             for key in ("name", "description", "text")}
    skill["scope"] = fields.get("scope") if fields.get("scope") in SCOPES else None
    if not skill["name"] or not skill["scope"] or len(skill["text"]) < 20:
        raise SkillError("Give the skill a name, choose what it is used for, and write at least 20 characters of instructions.")
    for key, limit in LIMITS.items():
        if len(skill[key]) > limit:
            raise SkillError(f"Keep the {key} within {limit} characters.")
    attack = finding(skill["name"], skill["description"], skill["text"])
    if attack:
        raise SkillError(f"This text tries to override ALFRED's rules ({attack.replace('_', ' ')}), so it cannot be saved.")
    return skill


def save(user, fields, *, source="") -> dict:
    """Saving is the person's approval of exactly this text."""
    skill = clean(fields)
    skill.update(id=secrets.token_hex(6), source=source if source.startswith("https://") else "",
                 approved_at=timezone.now().isoformat())
    skill["sha"] = _digest(skill)
    with _lock:
        data = _load()
        mine = data.setdefault(str(user.pk), [])
        if len(mine) >= 50:
            raise SkillError("You have 50 skills; delete one first.")
        mine.append(skill)
        _save(data)
    return skill


def listed(user) -> list:
    return [skill for skill in _load().get(str(user.pk), []) if isinstance(skill, dict) and skill.get("sha") == _digest_safe(skill)]


def _digest_safe(skill):
    try:
        return _digest(skill)
    except (KeyError, TypeError):
        return None


def delete(user, skill_id) -> bool:
    with _lock:
        data = _load()
        mine = data.get(str(user.pk), [])
        kept = [skill for skill in mine if skill.get("id") != skill_id]
        data[str(user.pk)] = kept
        _save(data)
    return len(kept) != len(mine)


def raw_link(url) -> str:
    """A GitHub file link as its raw-text address; anything else is refused."""
    parts = urlsplit(str(url or "").strip())
    path = parts.path.strip("/").split("/")
    if parts.scheme == "https" and parts.netloc == "raw.githubusercontent.com" and len(path) >= 4:
        return f"https://raw.githubusercontent.com/{'/'.join(path)}"
    if parts.scheme == "https" and parts.netloc == "github.com" and len(path) >= 5 and path[2] == "blob":
        return f"https://raw.githubusercontent.com/{path[0]}/{path[1]}/{'/'.join(path[3:])}"
    raise SkillError("Paste a link to one skill file on GitHub, such as a SKILL.md.")


def import_draft(url) -> dict:
    """Read a public SKILL.md or similar text file for the person to review; nothing is saved or run."""
    from alfred_ai.services import public_http
    link = raw_link(url)
    if not re.search(r"\.(md|txt|markdown)$", link, re.I):
        raise SkillError("Only text skill files (.md or .txt) can be imported; scripts are never imported.")
    try:
        text = public_http.request("GET", link, content_types=("text/plain", "text/markdown"), max_bytes=60_000).content.decode("utf-8")
    except (public_http.PublicHTTPError, UnicodeDecodeError, OSError) as exc:
        raise SkillError("That file could not be read.") from exc
    name = description = ""
    front = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.S)
    if front:
        for line in front.group(1).splitlines():
            key, _, value = line.partition(":")
            if key.strip() == "name": name = value.strip().strip("'\"")
            if key.strip() == "description": description = value.strip().strip("'\"")
        text = text[front.end():]
    name = name or Path(urlsplit(link).path).parent.name or "Imported skill"
    return {"name": name[:80], "description": description[:300], "text": text.strip()[:LIMITS["text"]], "source": link,
            "cut": len(text.strip()) > LIMITS["text"]}


def _words(text):
    return {word for word in re.findall(r"[a-z]{4,}", str(text).casefold()) if word not in STOP}


def pick(user, query, scope):
    """The approved skill whose name and description share the most words with the question, for its own scope only."""
    scope = GROUPS.get(scope, scope)
    if scope not in SCOPES or user is None or not getattr(user, "pk", None):
        return None
    asked = _words(query)
    scored = [(len(asked & _words(skill["name"] + " " + skill["description"])), skill) for skill in listed(user) if skill["scope"] == scope]
    scored = [item for item in scored if item[0] >= 1]
    return max(scored, key=lambda item: item[0])[1] if scored else None
