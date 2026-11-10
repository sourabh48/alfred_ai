"""Owner-set application stages, follow-up timing and stale-match checks for saved job analyses.

Stage names and follow-up timing follow career-ops (MIT, pin 4df3d052: templates/states.yml, modes/followup.md),
independently written here. ALFRED never sends anything: a follow-up counts only when the owner says it was sent.
"""
from __future__ import annotations

import math
from datetime import date, timedelta

STAGES = ("evaluated", "applied", "responded", "assessment", "interview", "offer", "rejected", "discarded", "hired")
CLOSED_STAGES = {"offer", "rejected", "discarded", "hired"}
# stage: (days after entering the stage, days between follow-ups, most follow-ups before the lead goes cold)
FOLLOW_UP_CADENCE = {"applied": (7, 7, 2), "responded": (1, 3, None), "assessment": (1, 3, None), "interview": (1, 3, None)}
MAX_HISTORY = 60
HISTORY_REVIEW = 'Unavailable: review missing, malformed or conflicting application history. Saved records have not been changed.'


def _day(value, *, today: date, floor: date | None = None) -> date:
    if value in (None, ""):
        chosen = today
    else:
        try:
            chosen = date.fromisoformat(str(value))
        except ValueError:
            raise ValueError("Use a date in YYYY-MM-DD form.") from None
    if chosen > today:
        raise ValueError("The date cannot be in the future.")
    if floor and chosen < floor:
        raise ValueError(f"The date cannot be before the last recorded step ({floor.isoformat()}).")
    return chosen


def _clean(application) -> dict:
    application = application if isinstance(application, dict) else {}
    def steps(key):
        items = application.get(key)
        if not isinstance(items, list):
            return []
        return [{**item, 'stage': item.get('stage') if item.get('stage') in STAGES else '',
                 'on': item.get('on') if isinstance(item.get('on'), str) else ''}
                for item in items[-MAX_HISTORY:] if isinstance(item, dict)]
    return {"stage": application.get("stage") if application.get("stage") in STAGES else "",
            "history": steps('history'), "follow_ups": steps('follow_ups')}


def _validated(application, *, today):
    application = {} if application is None else application
    try:
        if not isinstance(application, dict) or application.get('stage') not in (None, '', *STAGES):
            raise ValueError()
        for key in ('history', 'follow_ups'):
            items = application.get(key, [])
            if not isinstance(items, list) or len(items) > MAX_HISTORY:
                raise ValueError()
            days = []
            for item in items:
                if (not isinstance(item, dict) or item.get('stage') not in STAGES
                        or not isinstance(item.get('on'), str)):
                    raise ValueError()
                day = date.fromisoformat(item['on'])
                if day > today:
                    raise ValueError()
                days.append(day)
            if days != sorted(days):
                raise ValueError()
        record = _clean(application)
        if not record['stage'] and (record['history'] or record['follow_ups']):
            raise ValueError()
        if record['history'] and record['history'][-1]['stage'] != record['stage']:
            raise ValueError()
        if record['stage'] in FOLLOW_UP_CADENCE and not record['history']:
            raise ValueError()
        return record
    except (ValueError, TypeError, OverflowError):
        raise ValueError(HISTORY_REVIEW) from None


def _last_day(application) -> date | None:
    days = [item.get("on") for item in application["history"] + application["follow_ups"] if item.get("on")]
    return max(date.fromisoformat(value) for value in days) if days else None


def apply_change(application, payload: dict, *, today: date) -> dict:
    """Return a new application record after one owner change: a stage or a confirmed sent follow-up."""
    if not isinstance(payload, dict):
        raise ValueError("Send a stage or a sent follow-up.")
    original = application if isinstance(application, dict) else {}
    application = _validated(application, today=today)
    wants_stage, wants_follow_up = "stage" in payload, payload.get("follow_up_sent") is True
    if wants_stage == wants_follow_up:
        raise ValueError("Send either a new stage or follow_up_sent: true, not both.")
    on = _day(payload.get("on"), today=today, floor=_last_day(application))
    if wants_stage:
        stage = str(payload.get("stage") or "").strip().lower()
        if stage not in STAGES:
            raise ValueError("Choose a stage: " + ", ".join(STAGES) + ".")
        if stage == application["stage"]:
            raise ValueError("The opportunity is already at that stage.")
        application["stage"] = stage
        application["history"] = (application["history"] + [{"stage": stage, "on": on.isoformat()}])[-MAX_HISTORY:]
    else:
        if application["stage"] not in FOLLOW_UP_CADENCE:
            raise ValueError("Follow-ups are tracked only while applied, responded, in an assessment or interviewing.")
        application["follow_ups"] = (application["follow_ups"] + [{"stage": application["stage"], "on": on.isoformat()}])[-MAX_HISTORY:]
    return {**original, **application}


def follow_up_status(application, *, today: date) -> dict:
    """When the next follow-up is due for the current stage, or why none is."""
    unavailable = dict(status='unavailable', due_on=None, sent_in_stage=None, detail=HISTORY_REVIEW)
    try:
        application = _validated(application, today=today)
    except ValueError:
        return unavailable
    stage = application["stage"]
    if not stage:
        return {"status": "no_stage", "due_on": None, "sent_in_stage": 0, "detail": "Set a stage to track follow-ups."}
    if stage not in FOLLOW_UP_CADENCE:
        detail = "No follow-ups once the opportunity is closed." if stage in CLOSED_STAGES else "Follow-ups start once you apply."
        return {"status": "not_tracked", "due_on": None, "sent_in_stage": 0, "detail": detail}
    entered = max(date.fromisoformat(item["on"]) for item in application["history"] if item.get("stage") == stage)
    sent = sorted(date.fromisoformat(item["on"]) for item in application["follow_ups"]
                  if item.get("stage") == stage and item.get("on") and date.fromisoformat(item["on"]) >= entered)
    first, every, most = FOLLOW_UP_CADENCE[stage]
    if most is not None and len(sent) >= most:
        return {"status": "cold", "due_on": None, "sent_in_stage": len(sent),
                "detail": f"{len(sent)} follow-ups sent with no reply recorded; treat this lead as cold."}
    try:
        due = (sent[-1] + timedelta(days=every)) if sent else (entered + timedelta(days=first))
    except OverflowError:
        return unavailable
    return {"status": "due" if due <= today else "upcoming", "due_on": due.isoformat(), "sent_in_stage": len(sent),
            "detail": f"Next follow-up {'due' if due <= today else 'from'} {due.isoformat()}."}


def resume_evidence(payload: dict, *, kind: str, record_id) -> dict:
    """The comparable resume evidence a match uses, normalized the same way compare_resume_to_job saves it."""
    skills = sorted({item.strip().casefold() for item in (payload.get("skills") or []) if isinstance(item, str) and item.strip()})
    try:
        years = float(payload.get("experience_years"))
        years = years if math.isfinite(years) and years >= 0 else None
    except (TypeError, ValueError, OverflowError):
        years = None
    return {"kind": kind, "record_id": record_id, "skills": skills,
            "role": str(payload.get("role") or "").strip().lower(), "experience_years": years}


def match_freshness(analysis_payload, current: dict | None) -> dict:
    """Whether the resume evidence behind a saved match still matches the current resume, with the exact change."""
    fit = (analysis_payload or {}).get("fit") if isinstance(analysis_payload, dict) else None
    sources = fit.get("sources") if isinstance(fit, dict) else None
    used = sources[0] if isinstance(sources, list) and sources and isinstance(sources[0], dict) else None
    if used is None or current is None:
        return {"status": "unknown", "reasons": ["The resume evidence behind this match was not saved."], "added_skills": [], "removed_skills": []}
    used = resume_evidence(used, kind=used.get("kind"), record_id=used.get("record_id"))
    reasons = []
    if (used["kind"], used["record_id"]) != (current["kind"], current["record_id"]):
        reasons.append("A different resume or profile is now your current one.")
    added = sorted(set(current["skills"]) - set(used["skills"]))
    removed = sorted(set(used["skills"]) - set(current["skills"]))
    if added or removed:
        reasons.append("Your listed skills changed.")
    if used["role"] != current["role"]:
        reasons.append("Your role changed.")
    if used["experience_years"] != current["experience_years"]:
        reasons.append("Your years of experience changed.")
    return {"status": "stale" if reasons else "current", "reasons": reasons,
            "added_skills": [item.title() for item in added], "removed_skills": [item.title() for item in removed]}


def compare_resumes(older: dict, newer: dict) -> dict:
    a, b = resume_evidence(older, kind="", record_id=None), resume_evidence(newer, kind="", record_id=None)
    return {"added_skills": [item.title() for item in sorted(set(b["skills"]) - set(a["skills"]))],
            "removed_skills": [item.title() for item in sorted(set(a["skills"]) - set(b["skills"]))],
            "kept_skills": [item.title() for item in sorted(set(a["skills"]) & set(b["skills"]))],
            "role": {"from": a["role"], "to": b["role"], "changed": a["role"] != b["role"]},
            "experience_years": {"from": a["experience_years"], "to": b["experience_years"],
                                 "changed": a["experience_years"] != b["experience_years"]}}


def current_resume_evidence(user) -> dict | None:
    """Evidence from the resume a new match would use now: the latest upload, else the manual profile."""
    from apps.career.models import CareerProfile, CareerResume

    latest = CareerResume.objects.filter(user=user).order_by("-created_at", "-id").first()
    if latest is not None:
        return resume_evidence(latest.extracted_payload or {}, kind="resume_upload", record_id=latest.pk)
    profile = CareerProfile.objects.filter(user=user).first()
    if profile is None:
        return None
    payload = {"role": profile.role, "experience_years": profile.experience_years,
               "skills": [item.strip() for item in (profile.skills or "").split(",") if item.strip()]}
    return resume_evidence(payload, kind="manual_profile", record_id=profile.pk)
