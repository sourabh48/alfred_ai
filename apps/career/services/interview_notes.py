"""Interview stories (STAR + reflection) and post-interview debriefs the owner writes for a saved job.

Adapted from career-ops (https://github.com/career-ops-hq/career-ops, commit 775861b, MIT License):
templates/story-bank.template.md, lib/story-bank.mjs and modes/interview/debrief.md. No upstream code is copied.
Everything here is the owner's own words, stored on that job's saved analysis; nothing is generated. A figure in a
story that the current CV does not contain is shown as not in your CV, never as a fact (story-provenance rule).
"""
from datetime import date

from .bullet_rewrite import _numbers

STORY_FIELDS = ("theme", "title", "situation", "task", "action", "result", "reflection", "best_for")
STORY_REQUIRED = ("title", "action")
ROUND_TYPES = ("screen", "hiring-manager", "technical", "system-design", "behavioral", "other")
ROUND_OUTCOMES = ("pending", "moved-forward", "rejected")
DEBRIEF_TEXT = ("interviewer", "questions", "went_well", "gaps", "next_steps")
MAX_ITEMS = 20
SHORT, LONG = 120, 1500


def _text(value, limit, label):
    if value in (None, ""):
        return ""
    if not isinstance(value, str):
        raise ValueError(f"{label} must be text.")
    value = value.strip()
    if len(value) > limit:
        raise ValueError(f"{label} is longer than {limit} characters.")
    return value


def _story(data) -> dict:
    story = {key: _text(data.get(key), SHORT if key in {"theme", "title", "best_for"} else LONG, key.replace("_", " ").capitalize())
             for key in STORY_FIELDS}
    missing = [key for key in STORY_REQUIRED if not story[key]]
    if missing:
        raise ValueError("A story needs a title and what you did.")
    return story


def _debrief(data, *, today: date) -> dict:
    try:
        on = date.fromisoformat(str(data.get("on") or today.isoformat()))
    except ValueError:
        raise ValueError("Use a date in YYYY-MM-DD form.") from None
    if on > today:
        raise ValueError("The interview date cannot be in the future.")
    round_type, outcome = data.get("round_type") or "other", data.get("outcome") or "pending"
    if round_type not in ROUND_TYPES or outcome not in ROUND_OUTCOMES:
        raise ValueError("Choose a listed round type and outcome.")
    debrief = {"on": on.isoformat(), "round_type": round_type, "outcome": outcome,
               **{key: _text(data.get(key), SHORT if key == "interviewer" else LONG, key.replace("_", " ").capitalize())
                  for key in DEBRIEF_TEXT}}
    if not (debrief["questions"] or debrief["went_well"] or debrief["gaps"]):
        raise ValueError("Write at least the questions asked, what went well or a gap.")
    return debrief


def clean(notes) -> dict:
    """Saved notes in a safe shape; a malformed item is not shown and is dropped at the owner's next change."""
    notes = notes if isinstance(notes, dict) else {}
    def items(key, check):
        values = notes.get(key) if isinstance(notes.get(key), list) else []
        kept = []
        for value in values[:MAX_ITEMS]:
            try:
                kept.append(check(value) if isinstance(value, dict) else None)
            except ValueError:
                kept.append(None)
        return [value for value in kept if value]
    return {"stories": items("stories", _story), "debriefs": items("debriefs", lambda value: _debrief(value, today=date.max))}


def apply_change(notes, change, *, today: date) -> dict:
    """Return new notes after one owner change: add or remove a story or a debrief."""
    if not isinstance(change, dict):
        raise ValueError("Send one change.")
    notes = clean(notes)
    action, kind = change.get("action"), change.get("kind")
    key = {"story": "stories", "debrief": "debriefs"}.get(kind)
    if key is None or action not in {"add", "remove"}:
        raise ValueError("Choose add or remove for a story or a debrief.")
    if action == "remove":
        index = change.get("index")
        if not isinstance(index, int) or isinstance(index, bool) or not 0 <= index < len(notes[key]):
            raise ValueError("That item is no longer there. Reload and try again.")
        notes[key] = notes[key][:index] + notes[key][index + 1:]
        return notes
    if len(notes[key]) >= MAX_ITEMS:
        raise ValueError(f"This job already has {MAX_ITEMS} {key}. Remove one first.")
    data = change.get("item") if isinstance(change.get("item"), dict) else {}
    notes[key] = notes[key] + [_story(data) if kind == "story" else _debrief(data, today=today)]
    if kind == "debrief":
        notes[key].sort(key=lambda item: item["on"])
    return notes


def unverified_figures(story: dict, cv_text: str) -> list[str]:
    """Numbers in the story that the CV does not contain; shown to the owner, never restated as fact."""
    text = " ".join(story.get(key, "") for key in ("situation", "task", "action", "result"))
    return sorted(_numbers(text) - _numbers(cv_text or ""))


def story_bank(analyses, cv_text: str) -> list[dict]:
    """Every story across the owner's saved jobs, with where it was written and figures the CV does not show."""
    bank = []
    for analysis in analyses:
        payload = analysis.extracted_payload if isinstance(analysis.extracted_payload, dict) else {}
        for index, story in enumerate(clean(payload.get("interview_notes"))["stories"]):
            bank.append({**story, "analysis_id": analysis.pk, "index": index,
                         "source": " - ".join(part for part in (analysis.company, analysis.job_title) if part) or f"Job {analysis.pk}",
                         "unverified_figures": unverified_figures(story, cv_text)})
    return bank
