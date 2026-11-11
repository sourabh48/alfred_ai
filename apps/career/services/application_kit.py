"""Career Ops application workflows, rewritten in Python for ALFRED.

Adapted from career-ops (https://github.com/career-ops-hq/career-ops, commit 775861b, MIT License,
Copyright (c) 2026 Santiago Fernandez de Valderrama): modes triage, text/ats, cover, email, offer-prep
and patterns. No upstream code is copied. Everything here is deterministic and read-only apart from the
saved triage result: no model, no network, and nothing is ever sent, submitted or applied for.
Every CV, letter and email line comes from the owner's own CV and the saved job match; gaps stay placeholders.
"""
import re
from collections import Counter
from datetime import date
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

SALARY_ANNUAL_MULTIPLIERS = {"year": 1, "month": 12, "week": 52, "day": 260, "hour": 2080}

# triage.md: role (archetype) 35 %, pay 25 %, location 25 %, CV match 15 %; unknown terms drop out and the
# rest are rescaled; -0.5 per soft red flag; a hard disqualifier caps the score at 2.5.
TRIAGE_WEIGHTS = {"role": Decimal("0.35"), "pay": Decimal("0.25"), "location": Decimal("0.25"), "cv_match": Decimal("0.15")}
TRIAGE_PASS_MIN, TRIAGE_MAYBE_FLOOR, HARD_DQ_CAP, RED_FLAG_PENALTY = Decimal("3.5"), Decimal("3.0"), Decimal("2.5"), Decimal("0.5")
ROLE_FILLER = {"senior", "junior", "lead", "staff", "principal", "sr", "jr", "head", "of", "and", "the", "i", "ii", "iii", "iv", "-", "/", "&"}
BRIEF_LISTS = ("target_roles", "locations", "hard_dq", "red_flags", "priority_companies")


def _text(value, limit=80) -> str:
    return " ".join(str(value).split())[:limit] if isinstance(value, str) else ""


def clean_brief(raw) -> dict:
    """Validate the owner's triage brief (career-ops _brief.md): short phrase lists, a pay floor and remote choice."""
    if not isinstance(raw, dict):
        raise ValueError("Send a triage brief.")
    brief = {}
    for key in BRIEF_LISTS:
        items = raw.get(key) or []
        if isinstance(items, str):
            items = items.split(",")
        if not isinstance(items, list) or len(items) > 20:
            raise ValueError(f"{key.replace('_', ' ').capitalize()} must be a list of up to 20 phrases.")
        brief[key] = list(dict.fromkeys(item for item in (_text(entry) for entry in items) if item))
    floor = raw.get("pay_floor")
    brief["pay_floor"], brief["pay_currency"] = "", ""
    if floor not in (None, ""):
        try:
            amount = Decimal(str(floor).replace(",", ""))
        except InvalidOperation:
            raise ValueError("Pay floor must be a number.")
        if not amount.is_finite() or amount <= 0 or amount >= Decimal("1e12"):
            raise ValueError("Pay floor must be a positive yearly amount.")
        currency = _text(raw.get("pay_currency"), 3).upper()
        if not re.fullmatch(r"[A-Z]{3}", currency):
            raise ValueError("Choose the pay floor's three-letter currency, such as INR.")
        brief["pay_floor"], brief["pay_currency"] = str(amount.quantize(Decimal("0.01"))), currency
    if not isinstance(raw.get("remote_ok", False), bool):
        raise ValueError("Remote choice must be true or false.")
    brief["remote_ok"] = raw.get("remote_ok", False)
    return brief


def _payload(analysis) -> dict:
    return analysis.extracted_payload if isinstance(analysis.extracted_payload, dict) else {}


def _role_tokens(value: str) -> set[str]:
    return {token for token in re.split(r"[^a-z0-9+#]+", value.casefold()) if token and token not in ROLE_FILLER}


def _band(percent) -> int:
    return 5 if percent >= 80 else 4 if percent >= 65 else 3 if percent >= 50 else 2 if percent >= 35 else 1


def annual_posted_pay(snapshot: dict):
    """Posted range as yearly Decimals, or None when the posting states no pay."""
    try:
        low, high = Decimal(str(snapshot.get("salary_min") or 0)), Decimal(str(snapshot.get("salary_max") or 0))
    except InvalidOperation:
        return None
    if not (low.is_finite() and high.is_finite()) or (low <= 0 and high <= 0):
        return None
    multiplier = SALARY_ANNUAL_MULTIPLIERS.get((snapshot.get("salary_period") or "year").lower(), 1)
    low, high = (low or high) * multiplier, (high or low) * multiplier
    return {"min": low, "max": high, "currency": (snapshot.get("salary_currency") or "").upper()}


def triage(analysis, brief: dict, *, profile_role: str = "", today: date) -> dict:
    payload = _payload(analysis)
    snapshot = payload.get("job_snapshot") if isinstance(payload.get("job_snapshot"), dict) else {}
    fit = payload.get("fit") if isinstance(payload.get("fit"), dict) else {}
    jd = " ".join(str(analysis.extracted_text or "").split()).casefold()
    title = (analysis.job_title or snapshot.get("title") or "").strip()
    dims = []

    targets = brief["target_roles"] or ([profile_role] if profile_role and profile_role.casefold() != "profile pending" else [])
    if not targets or not title:
        dims.append(("role", None, "No target role or job title to compare."))
    elif any(target.casefold() in title.casefold() for target in targets):
        dims.append(("role", 5, f"Title matches a target role ({title})."))
    elif any(_role_tokens(target) & _role_tokens(title) for target in targets):
        dims.append(("role", 3, f"Title is adjacent to a target role ({title})."))
    else:
        dims.append(("role", 1, f"Title does not match a target role ({title})."))

    posted = annual_posted_pay(snapshot)
    if not brief["pay_floor"]:
        dims.append(("pay", None, "No pay floor set, so pay is left out."))
    elif posted is None:
        dims.append(("pay", None, "The posting states no pay, so pay is left out; nothing was estimated."))
    elif posted["currency"] != brief["pay_currency"]:
        dims.append(("pay", None, f"Posted pay is in {posted['currency'] or 'an unstated currency'}, not {brief['pay_currency']}; no conversion is used, so pay is left out."))
    else:
        floor = Decimal(brief["pay_floor"])
        score = 5 if posted["min"] >= floor else 3 if posted["max"] >= floor else 1
        dims.append(("pay", score, f"Posted {posted['currency']} {posted['min']:,.0f}-{posted['max']:,.0f} a year against your floor {floor:,.0f}."))

    location = (analysis.location or snapshot.get("location") or "").strip()
    remote = bool(re.search(r"\bremote\b", f"{location} {jd}", re.I))
    if not location and not remote:
        dims.append(("location", None, "The posting states no location, so location is left out."))
    elif any(place.casefold() in location.casefold() for place in brief["locations"]):
        dims.append(("location", 5, f"Location {location} is one you accept."))
    elif remote and brief["remote_ok"]:
        dims.append(("location", 4, "Remote is mentioned; check that your country is eligible before applying."))
    elif not brief["locations"] and not brief["remote_ok"]:
        dims.append(("location", None, "No accepted locations set, so location is left out."))
    else:
        dims.append(("location", 1, f"Location {location or 'remote'} is not one you accept."))

    matched, missing = fit.get("matched_skills") or [], fit.get("missing_skills") or []
    if isinstance(fit.get("fit_score"), (int, float)):
        dims.append(("cv_match", _band(fit["fit_score"]), f"Saved job match fit {fit['fit_score']:.0f}%."))
    elif matched or missing:
        share = 100 * len(matched) / (len(matched) + len(missing))
        dims.append(("cv_match", _band(share), f"{len(matched)} of {len(matched) + len(missing)} listed terms are on your CV (overall fit unavailable)."))
    else:
        dims.append(("cv_match", None, "No saved job match terms, so CV match is left out."))

    hard = [phrase for phrase in brief["hard_dq"] if phrase.casefold() in jd]
    flags = [phrase for phrase in brief["red_flags"] if phrase.casefold() in jd]
    priority = bool(analysis.company) and any(name.casefold() == analysis.company.casefold() for name in brief["priority_companies"])
    known = [(key, Decimal(score)) for key, score, _ in dims if score is not None]
    result = {
        "dimensions": [{"key": key, "score": score, "weight": float(TRIAGE_WEIGHTS[key]), "reason": reason} for key, score, reason in dims],
        "hard_dq": hard, "red_flags": flags, "priority": priority, "brief": brief, "scored_on": today.isoformat(),
        "basis": "Career Ops triage formula on your brief and the saved job match. A filter for your time, not a hiring prediction.",
    }
    if not known:
        return {**result, "score": None, "verdict": "UNAVAILABLE", "reason": "No dimension could be scored; set a brief and run a job match."}
    weight = sum(TRIAGE_WEIGHTS[key] for key, _ in known)
    score = sum(TRIAGE_WEIGHTS[key] * value for key, value in known) / weight - RED_FLAG_PENALTY * len(flags)
    score = max(Decimal(0), min(Decimal(5), score))
    if hard:
        score = min(score, HARD_DQ_CAP)
    score = score.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    verdict = "PASS" if priority or score >= TRIAGE_PASS_MIN else "MARGINAL" if score >= TRIAGE_MAYBE_FLOOR else "FAIL"
    reason = ("Priority company." if priority else "") + (f" Hard disqualifier: {', '.join(hard)}." if hard else "") + \
        (f" Red flags: {', '.join(flags)}." if flags else "")
    return {**result, "score": float(score), "verdict": verdict, "reason": reason.strip() or "Scored from the dimensions below."}


# ---------- CV-grounded writing ----------
ACTION_VERBS = ("led", "built", "designed", "delivered", "launched", "reduced", "increased", "improved", "managed",
                "created", "developed", "automated", "migrated", "owned", "shipped", "implemented", "scaled", "cut",
                "grew", "drove", "mentored", "negotiated", "established", "optimised", "optimized", "saved")
SECTION_HEADINGS = {
    "experience": ("experience", "work experience", "professional experience", "employment", "employment history", "work history"),
    "projects": ("projects", "key projects", "selected projects"),
    "education": ("education", "academic background", "qualifications"),
    "certifications": ("certifications", "certificates", "licenses", "licences"),
}
ATS_REPLACEMENTS = {"—": "-", "–": "-", "‘": "'", "’": "'", "“": '"', "”": '"', "•": "-",
                    "▪": "-", "●": "-", " ": " ", "…": "..."}
BULLET_RE = re.compile(r"^[\-\*•▪●‣⁃>·]+\s*")


def ats_text(value: str) -> str:
    for old, new in ATS_REPLACEMENTS.items():
        value = value.replace(old, new)
    return value


def _cv_lines(text: str) -> list[str]:
    return [" ".join(line.split()) for line in (text or "").splitlines() if line.strip()]


def achievement_lines(text: str) -> list[str]:
    """Verbatim CV lines that state a result: a number, or an action verb at the start."""
    found = []
    for line in _cv_lines(text):
        body = BULLET_RE.sub("", line)
        if not 25 <= len(body) <= 300 or "@" in body:
            continue
        first = body.split(" ", 1)[0].casefold().rstrip(",.")
        # Years and month/year dates mark role headers, not results.
        numbers = re.sub(r"\b(?:19|20)\d{2}\b|\b\d{1,2}/\d{2,4}\b", "", body)
        if re.search(r"\d", numbers) or first in ACTION_VERBS:
            found.append(ats_text(body))
    return list(dict.fromkeys(found))


def _relevance(line: str, terms: list[str]) -> int:
    lowered = line.casefold()
    return sum(1 for term in terms if term and re.search(rf"(?<![a-z0-9]){re.escape(term.casefold())}(?![a-z0-9])", lowered))


def ranked_achievements(text: str, terms: list[str], limit: int) -> list[str]:
    lines = achievement_lines(text)
    ranked = sorted(enumerate(lines), key=lambda pair: (-_relevance(pair[1], terms), pair[0]))
    return [line for _, line in ranked[:limit]]


def cv_sections(text: str) -> dict:
    """Standard sections copied verbatim from the CV text, keyed by heading family."""
    sections, current = {}, None
    for line in _cv_lines(text):
        heading = line.casefold().rstrip(":").strip()
        family = next((key for key, names in SECTION_HEADINGS.items() if heading in names), None)
        if family:
            current = family
            sections.setdefault(current, [])
            continue
        if current and re.fullmatch(r"[A-Za-z &/]{3,40}:?", line) and line.isupper():
            current = None  # an unrecognised upper-case heading ends the copied section
            continue
        if current:
            sections[current].append(ats_text(line))
    return {key: lines for key, lines in sections.items() if lines}


def _evidence(resume, profile):
    """The CV a draft is built from: latest upload, else the manual profile (no CV text then)."""
    if resume is not None:
        payload = resume.extracted_payload if isinstance(resume.extracted_payload, dict) else {}
        return payload, resume.extracted_text or "", {"kind": "resume_upload", "record_id": resume.pk, "label": resume.file_name,
                                                      "parser_status": resume.parser_status}
    if profile is not None:
        payload = {"role": profile.role, "experience_years": profile.experience_years,
                   "skills": [item.strip() for item in (profile.skills or "").split(",") if item.strip()]}
        return payload, "", {"kind": "manual_profile", "record_id": profile.pk, "label": "Manual career profile", "parser_status": "user_declared"}
    return None, "", None


def _facts(analysis, payload: dict) -> dict:
    snapshot = _payload(analysis).get("job_snapshot") or {}
    fit = _payload(analysis).get("fit") or {}
    skills = [item for item in payload.get("skills") or [] if isinstance(item, str) and item.strip()]
    wanted = [item for item in snapshot.get("required_skills") or [] if isinstance(item, str)]
    have = {skill.casefold() for skill in skills}
    matched = [term for term in wanted if term.casefold() in have] or [item for item in fit.get("matched_skills") or [] if isinstance(item, str)]
    missing = [term for term in wanted if term.casefold() not in have] or [item for item in fit.get("missing_skills") or [] if isinstance(item, str)]
    try:
        years = float(payload.get("experience_years"))
        years = years if years > 0 else None
    except (TypeError, ValueError):
        years = None
    role = (payload.get("role") or "").strip()
    return {
        "title": analysis.job_title or snapshot.get("title") or "this role",
        "company": analysis.company or snapshot.get("company") or "",
        "location": analysis.location or snapshot.get("location") or "",
        "role": "" if role.casefold() == "profile pending" else role,
        "years": years, "current_company": (payload.get("current_company") or "").strip(),
        "skills": skills, "matched": matched, "missing": missing,
        "contact": " | ".join(item for item in [payload.get("email") or "", payload.get("phone") or "", *(payload.get("links") or [])[:3]] if item),
        "terms": list(dict.fromkeys([*wanted, *matched, *_role_tokens(analysis.job_title or "")])),
    }


def _years(facts) -> str:
    return f"{facts['years']:g} years" if facts["years"] else "[years of experience]"


def tailored_cv(analysis, resume, profile) -> dict:
    payload, text, source = _evidence(resume, profile)
    if payload is None:
        return {"available": False, "reason": "Upload your CV or save a career profile first."}
    facts = _facts(analysis, payload)
    ordered = [skill for skill in facts["skills"] if skill.casefold() in {term.casefold() for term in facts["matched"]}]
    ordered += [skill for skill in facts["skills"] if skill not in ordered]
    lines = ["[Your name]"] + ([facts["contact"]] if facts["contact"] else ["[email | phone | city]"])
    summary = f"{facts['role'] or '[Your current role]'} with {_years(facts)} of experience"
    summary += f", most recently at {facts['current_company']}." if facts["current_company"] else "."
    if facts["matched"]:
        summary += f" Skills relevant to this role: {', '.join(facts['matched'][:5])}."
    lines += ["", "PROFESSIONAL SUMMARY", summary, "", "SKILLS", ", ".join(ordered) or "[Your skills]"]
    wins = ranked_achievements(text, facts["terms"], 6)
    lines += ["", "SELECTED ACHIEVEMENTS"] + ([f"- {line}" for line in wins] or ["- [Add an achievement with a number from your CV]"])
    sections = cv_sections(text)
    for key, heading in (("experience", "PROFESSIONAL EXPERIENCE"), ("projects", "PROJECTS"), ("education", "EDUCATION"),
                         ("certifications", "CERTIFICATIONS")):
        if key in sections:
            lines += ["", heading, *sections[key]]
        elif key in ("experience", "education"):
            lines += ["", heading, f"[Copy your {heading.lower()} from your CV]"]
    notes = ["Every line comes from your CV; bracketed lines are for you to fill in.",
             "Experience, projects and education are copied unchanged; reorder bullets yourself if you want."]
    if facts["missing"]:
        notes.append(f"The job lists {', '.join(facts['missing'][:8])}, which your CV does not show. Add them only if true.")
    if source["parser_status"] not in ("parsed", "user_declared"):
        notes.append("Your CV extraction still needs review, so check every line against the original.")
    return {"available": True, "text": ats_text("\n".join(lines)), "notes": notes, "source": source,
            "basis": "Plain single-column text with standard headings, so applicant tracking systems can read it."}


def cover_letter(analysis, resume, profile, *, today: date) -> dict:
    payload, text, source = _evidence(resume, profile)
    if payload is None:
        return {"available": False, "reason": "Upload your CV or save a career profile first."}
    facts = _facts(analysis, payload)
    at = f" at {facts['company']}" if facts["company"] else ""
    skills = ", ".join(facts["matched"][:3]) or "[the main skills this role asks for]"
    wins = ranked_achievements(text, facts["terms"], 5)
    while len(wins) < 3:
        wins.append("[Add a specific achievement with a number from your CV]")
    body = [
        "[Your name]", facts["contact"] or "[email | phone | city]", "",
        f"Cover Letter: {facts['title']}",
        f"{facts['company'] or '[Company]'}{', ' + facts['location'] if facts['location'] else ''}    {today.strftime('%d %B %Y')}", "",
        f"I am applying for the {facts['title']} role{at}. My work as {facts['role'] or '[your current role]'} covers {skills}, which this role asks for.", "",
        f"I have {_years(facts)} of experience as {facts['role'] or '[your current role]'}"
        + (f", most recently at {facts['current_company']}." if facts["current_company"] else "."), "",
        "From my CV:", *[f"- {line}" for line in wins], "",
        "[Two or three sentences on a problem this company has that you can solve. ALFRED did not research the company; "
        "use what you know from their site or people there.]", "",
        "I would welcome a conversation about the role.", "", "[Your name]",
    ]
    notes = ["Read every sentence and replace each bracketed part. You send it yourself; ALFRED sends nothing."]
    if facts["missing"]:
        notes.append(f"Not on your CV: {', '.join(facts['missing'][:6])}. Mention them only if true.")
    return {"available": True, "text": ats_text("\n".join(body)), "notes": notes, "source": source}


EMAIL_KINDS = {
    "hr_application": "Application to HR or a recruiter",
    "referral_request": "Referral request",
    "cold_application": "Speculative application",
    "follow_up": "Follow-up on an application",
    "process_stuck": "Application process broke",
    "confirmed_time_noshow": "Missed confirmed call",
}


def email_draft(analysis, resume, profile, *, kind: str, triage_score=None) -> dict:
    if kind not in EMAIL_KINDS:
        raise ValueError("Choose a supported email type.")
    payload, text, source = _evidence(resume, profile)
    if payload is None:
        return {"available": False, "reason": "Upload your CV or save a career profile first."}
    facts = _facts(analysis, payload)
    role, company = facts["title"], facts["company"] or "[Company]"
    win = (ranked_achievements(text, facts["terms"], 1) or ["[one result with a number from your CV]"])[0]
    fit = ", ".join(facts["matched"][:3]) or "[skills the role asks for]"
    me = facts["role"] or "[your current role]"
    applied = next((step.get("on") for step in reversed((_payload(analysis).get("application") or {}).get("history") or [])
                    if isinstance(step, dict) and step.get("stage") == "applied"), None)
    drafts = {
        "hr_application": (f"Application: {role}",
            [f"Hello,", "", f"I would like to apply for the {role} role at {company}. I work as {me} with {_years(facts)} of experience in {fit}.",
             f"One example: {win}", "", "My CV is attached. I can talk at a time that suits you.", "", "Regards,", "[Your name]"]),
        "referral_request": (f"Would you refer me for {role} at {company}?",
            ["Hi [name],", "", f"{company} has an opening for {role}. It matches my work as {me}, mainly {fit}.",
             f"Recent example: {win}", "", "Would you be comfortable referring me? I can send a short summary you can forward. "
             "No problem at all if not.", "", "Thanks,", "[Your name]"]),
        "cold_application": (f"{me} interested in {company}",
            ["Hello [name],", "", f"I work as {me} with {_years(facts)} of experience in {fit}. {win}",
             "", f"If {company} is hiring for {role} or similar work, I would like to be considered. My CV is attached.",
             "", "Regards,", "[Your name]"]),
        "follow_up": (f"Following up: {role} application",
            ["Hello,", "", f"I applied for the {role} role at {company}" + (f" on {applied}" if applied else " [on date]")
             + " and wanted to check whether there is any update.", f"I am still interested; my work in {fit} fits what the role describes.",
             "", "Thank you for your time.", "", "Regards,", "[Your name]"]),
        "process_stuck": (f"{role} application: [what broke]",
            ["Hello,", "", f"I am applying for the {role} role at {company}. At [step], [what happened, with any error message].",
             "Could you tell me how to complete the application, or accept it by email? My CV is attached.", "", "Regards,", "[Your name]"]),
        "confirmed_time_noshow": (f"{role}: our call on [date and time]",
            ["Hello [name],", "", f"We confirmed a call for [date and time] about the {role} role. I was available at that time but we did not connect.",
             "Could we find another time? I am free [two or three options].", "", "Regards,", "[Your name]"]),
    }
    subject, body = drafts[kind]
    notes = ["A draft only. Check it, fill the brackets and send it yourself; ALFRED sends nothing."]
    if kind in ("hr_application", "referral_request", "cold_application") and triage_score is not None and triage_score < 4.0:
        notes.append(f"Triage score {triage_score}/5 is below 4.0, where Career Ops advises against applying; keep the email restrained.")
    return {"available": True, "kind": kind, "label": EMAIL_KINDS[kind], "subject": ats_text(subject),
            "text": ats_text("\n".join(body)), "notes": notes, "source": source}


# ---------- offer-prep: a reading aid, never a verdict ----------
OFFER_TAXONOMY = [
    ("compensation", "Compensation and bonus", r"\b(salary|ctc|compensation|bonus|commission|variable pay|incentive)\b", False),
    ("equity", "Equity", r"\b(esop|equity|stock options?|rsus?|vesting|vest|cliff)\b", False),
    ("termination", "Termination and notice", r"\b(notice period|terminat\w*|severance|probation|garden leave|in lieu of notice)\b", True),
    ("restrictive", "Non-compete and non-solicitation", r"\b(non-?compete|non-?solicit\w*|non-?dealing|restrictive covenant)\b", True),
    ("ip", "Intellectual property and confidentiality", r"\b(intellectual property|inventions?|assign\w* .{0,40}rights|confidential\w*|moral rights)\b", True),
    ("clawback", "Clawbacks and repayment", r"\b(claw ?back|repay\w*|bond|refund .{0,30}(bonus|relocation|training))\b", False),
    ("dispute", "Disputes and governing law", r"\b(arbitrat\w*|governing law|jurisdiction|courts? of|waive\w* .{0,20}(jury|class))\b", True),
    ("classification", "Employment status", r"\b(contractor|consultant|employee status|exempt|overtime|retainer)\b", True),
    ("working", "Working terms and benefits", r"\b(working hours|leave|holidays?|pto|benefits?|insurance|relocat\w*|work from|office)\b", False),
    ("integration", "Entire agreement and conditions", r"\b(entire agreement|supersedes?|background (check|verification)|subject to|contingent|offer (is )?valid|expire\w*)\b", False),
]
INJECTION_RE = re.compile(r"\b(ignore (all|any|previous) instructions|as an ai|language model|assistant[,:])", re.I)
MUST_MENTION = ("compensation", "termination", "working")


def offer_prep(analysis, *, offer_text: str, offered: dict | None, profile) -> dict:
    text = " ".join((offer_text or "").split())
    if len(text) < 40:
        raise ValueError("Paste the offer letter or contract text (at least a few sentences).")
    if len(text) > 30000:
        raise ValueError("Paste at most 30,000 characters of the offer.")
    sentences = [part.strip() for part in re.split(r"(?<=[.;])\s+", text) if part.strip()]
    walk, lawyer = [], []
    for key, label, pattern, legal in OFFER_TAXONOMY:
        quotes = [sentence[:300] for sentence in sentences if re.search(pattern, sentence, re.I)][:3]
        walk.append({"key": key, "label": label, "quotes": quotes})
        if quotes and legal:
            lawyer.append(f"{label}: how do these terms apply where you will work, and can they be enforced?")
    found = {item["key"] for item in walk if item["quotes"]}
    raise_items = [f"The offer does not mention {label.lower()}; ask for it in writing." for key, label, _, _ in OFFER_TAXONOMY
                   if key in MUST_MENTION and key not in found]
    if "integration" in found:
        raise_items.append("It has an entire-agreement or conditions clause: anything promised verbally must be written into the offer.")
    anomalies = [sentence[:300] for sentence in sentences if INJECTION_RE.search(sentence)]
    if anomalies:
        raise_items.append("The document contains text addressed to an AI or reviewer; ask the employer about it.")
    pay = _pay_consistency(analysis, offered, profile)
    return {"clause_walk": walk, "lawyer_questions": lawyer, "raise_with_employer": raise_items, "anomalies": anomalies, "pay": pay,
            "disclaimer": "A reading aid, not legal advice. ALFRED gives no verdict on the contract or any clause, did no research, "
                          "and did not store the offer text."}


def _pay_consistency(analysis, offered, profile) -> list[dict]:
    if not offered:
        return []
    try:
        amount = Decimal(str(offered.get("amount")).replace(",", ""))
    except (InvalidOperation, AttributeError):
        raise ValueError("Offered pay must be a number.")
    currency = _text(offered.get("currency"), 3).upper()
    period = (offered.get("period") or "year").lower()
    if not amount.is_finite() or amount <= 0 or period not in SALARY_ANNUAL_MULTIPLIERS or not re.fullmatch(r"[A-Z]{3}", currency):
        raise ValueError("Give the offered pay as a positive amount, a three-letter currency and a period.")
    yearly = amount * SALARY_ANNUAL_MULTIPLIERS[period]
    money = lambda value: str(Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    rows = [{"label": "Offered, yearly", "amount": money(yearly), "currency": currency}]
    posted = annual_posted_pay(_payload(analysis).get("job_snapshot") or {})
    if posted and posted["currency"] == currency:
        rows.append({"label": "Posted range, yearly", "amount": f"{money(posted['min'])}-{money(posted['max'])}", "currency": currency,
                     "gap": money(yearly - posted["max"]), "gap_label": "Offer minus top of posted range"})
    elif posted:
        rows.append({"label": "Posted range", "detail": f"Stated in {posted['currency'] or 'an unstated currency'}; not compared, no conversion."})
    last = getattr(profile, "last_salary", None)
    if last and getattr(profile, "salary_currency", None) == currency:
        rows.append({"label": "Your last salary, yearly", "amount": money(last), "currency": currency,
                     "gap": money(yearly - Decimal(last)), "gap_label": "Offer minus your last salary"})
    return rows


# ---------- patterns: outcomes the owner recorded ----------
POSITIVE, AWAITING, NEGATIVE, DISCARDED, PENDING = {"responded", "assessment", "interview", "offer", "hired"}, {"applied"}, {"rejected"}, {"discarded"}, {"evaluated"}
SENT = POSITIVE | AWAITING | NEGATIVE
PATTERN_MIN_SENT = 5


def _group(stage):
    for name, stages in (("positive", POSITIVE), ("awaiting", AWAITING), ("negative", NEGATIVE), ("discarded", DISCARDED), ("pending", PENDING)):
        if stage in stages:
            return name
    return None


def patterns(analyses) -> dict:
    rows = []
    for analysis in analyses:
        payload = _payload(analysis)
        stage = (payload.get("application") or {}).get("stage") if isinstance(payload.get("application"), dict) else None
        if stage:
            rows.append((stage, payload))
    sent = sum(1 for stage, _ in rows if stage in SENT)
    if sent < PATTERN_MIN_SENT:
        return {"available": False, "sent": sent, "minimum": PATTERN_MIN_SENT,
                "reason": f"Not enough data yet: {sent} of {PATTERN_MIN_SENT} applications have been sent. Come back when you have more outcomes."}
    funnel = Counter(stage for stage, _ in rows)
    scores = {}
    for stage, payload in rows:
        score = (payload.get("triage") or {}).get("score")
        if isinstance(score, (int, float)):
            scores.setdefault(_group(stage), []).append(score)
    positive = sum(1 for stage, _ in rows if stage in POSITIVE)
    decided = positive + sum(1 for stage, _ in rows if stage in NEGATIVE)
    gaps = Counter(skill for stage, payload in rows if stage in NEGATIVE | DISCARDED
                   for skill in ((payload.get("fit") or {}).get("missing_skills") or []) if isinstance(skill, str))
    positives = scores.get("positive", [])
    return {
        "available": True, "sent": sent, "total": len(rows),
        "funnel": [{"stage": stage, "count": funnel[stage], "percent": round(100 * funnel[stage] / len(rows))}
                   for stage in ("evaluated", "applied", "responded", "assessment", "interview", "offer", "hired", "rejected", "discarded") if funnel[stage]],
        "conversion_rate": round(100 * positive / sent),
        "decided_rate": round(100 * positive / decided) if decided else None,
        "decided": decided,
        "score_vs_outcome": [{"group": group, "count": len(values), "average": round(sum(values) / len(values), 1),
                              "min": min(values), "max": max(values)} for group, values in scores.items() if group],
        "top_gaps": [{"skill": skill, "count": count} for skill, count in gaps.most_common(8)],
        "lowest_positive_score": min(positives) if positives else None,
        "basis": "Counts from the stages you recorded. Awaiting replies are silence, not rejection; no rate is a prediction.",
    }
