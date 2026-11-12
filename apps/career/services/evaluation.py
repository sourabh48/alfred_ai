"""Full A-G job evaluation report, the Career Ops `job` mode, rewritten deterministically for ALFRED.

Adapted from career-ops (https://github.com/career-ops-hq/career-ops, commit 775861b, MIT License,
Copyright (c) 2026 Santiago Fernandez de Valderrama): modes/oferta.md blocks A-G, the two-pass
requirement table, importance bands with evidence tiers and the gate that keeps a guess from ever being
critical or high. No upstream code is copied. ALFRED uses no model and no network here: every row comes
from the saved posting, the owner's CV and the saved triage. Market research the upstream mode does with
web search is not done; the report says so instead of estimating.
"""
import re
from datetime import date

from .application_kit import (INJECTION_RE, _evidence, _facts, _payload, annual_posted_pay, ranked_achievements)

BANDS = ("critical", "high", "meaningful", "preferred", "low_signal")
ROW_BUDGET = 12
STATED_RE = re.compile(r"\b(must|required|requirement|essential|mandatory|need to have|minimum)\b", re.I)
PREFERRED_RE = re.compile(r"\b(preferred|nice to have|nice-to-have|bonus|a plus|desirable|advantage)\b", re.I)
SENIORITY = (("intern", "Intern", 0), ("graduate", "Entry", 0), ("junior", "Junior", 1), ("associate", "Junior", 1),
             ("principal", "Principal", 5), ("staff", "Staff", 4), ("director", "Director", 5), ("head", "Head", 5),
             ("lead", "Lead", 3), ("senior", "Senior", 3), ("sr", "Senior", 3), ("manager", "Manager", 3))
FEE_RE = re.compile(r"\b(registration fee|training fee|security deposit|pay (a|the) fee|processing fee|refundable deposit)\b", re.I)
API_SOURCES = ("Greenhouse", "Lever", "Ashby")


def _sentences(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"(?<=[.;!?])\s+|\s[•·▪]\s|\n+", text or "") if part.strip()]


def _quote(sentence: str, limit=160) -> str:
    return sentence if len(sentence) <= limit else sentence[: limit - 1].rstrip() + "…"


def requirement_rows(title: str, jd: str, wanted: list[str]) -> list[dict]:
    """Pass 1: importance from the posting text alone, before the CV is read."""
    sentences = _sentences(jd)
    folded = jd.casefold()
    rows = []
    for term in wanted:
        key = term.casefold()
        if not key:
            continue
        pattern = re.compile(rf"(?<![a-z0-9]){re.escape(key)}(?![a-z0-9])")
        hits = [s for s in sentences if pattern.search(s.casefold())]
        stated = next((s for s in hits if STATED_RE.search(s) and not PREFERRED_RE.search(s)), None)
        preferred = next((s for s in hits if PREFERRED_RE.search(s)), None)
        if pattern.search(title.casefold()):
            band, tier, signal = "critical", "stated", f'Job title: "{title}"'
        elif stated:
            band, tier, signal = "critical", "stated", f'"{_quote(stated)}"'
        elif preferred and not stated:
            band, tier, signal = "preferred", "stated", f'"{_quote(preferred)}"'
        elif len(pattern.findall(folded)) >= 2:
            band, tier, signal = "high", "structural", f"Mentioned {len(pattern.findall(folded))} times in the posting"
        elif hits:
            band, tier, signal = "meaningful", "structural", f'"{_quote(hits[0])}"'
        else:
            # Listed by the parser but not quotable from the text: a guess, so the gate caps it below high.
            band, tier, signal = "meaningful", "inferred", "—"
        rows.append({"requirement": term, "band": band, "tier": tier, "jd_signal": signal})
    return rows


def _match(rows, facts, cv_text):
    """Pass 2: the CV. Importance is never revised here."""
    have = {skill.casefold() for skill in facts["skills"]}
    lines = [line.strip() for line in (cv_text or "").splitlines() if line.strip()]
    for row in rows:
        key = row["requirement"].casefold()
        pattern = re.compile(rf"(?<![a-z0-9]){re.escape(key)}(?![a-z0-9])")
        line = next((item for item in lines if pattern.search(item.casefold()) and len(item) > len(key) + 3), None)
        if key in have and line:
            row["match"], row["evidence"] = "strong", f'CV: "{_quote(line)}"'
        elif key in have:
            row["match"], row["evidence"] = "partial", "Listed in your skills, but no CV line shows it in use."
        elif line:
            row["match"], row["evidence"] = "partial", f'Mentioned on your CV, not in your skills list: "{_quote(line)}"'
        else:
            row["match"], row["evidence"] = "missing", "Not on your CV."
    return rows


def _budget(rows):
    order = {band: index for index, band in enumerate(BANDS)}
    met = {"missing": 0, "partial": 1, "strong": 2}
    rows.sort(key=lambda row: (order[row["band"]], met[row["match"]]))
    kept = [row for row in rows if row["band"] in ("critical", "high")]
    kept += [row for row in rows if row["band"] not in ("critical", "high")][: max(0, ROW_BUDGET - len(kept))]
    return kept, len(rows) - len(kept)


def _seniority(title: str):
    tokens = set(re.split(r"[^a-z]+", title.casefold()))
    return next(((label, rank) for word, label, rank in SENIORITY if word in tokens), (None, None))


def _candidate_rank(years):
    if years is None:
        return None
    return 1 if years < 2 else 2 if years < 5 else 3 if years < 9 else 4


def evaluation_report(analysis, resume, profile, *, today: date) -> dict:
    payload, cv_text, source = _evidence(resume, profile)
    data = _payload(analysis)
    snapshot = data.get("job_snapshot") if isinstance(data.get("job_snapshot"), dict) else {}
    if not snapshot and not analysis.extracted_text:
        return {"available": False, "reason": "Run a job match first so ALFRED has the posting to evaluate."}
    jd = analysis.extracted_text or snapshot.get("description") or ""
    facts = _facts(analysis, payload or {})
    title = facts["title"]
    wanted = [item for item in snapshot.get("required_skills") or [] if isinstance(item, str)] or facts["matched"] + facts["missing"]
    rows = requirement_rows(title, jd, list(dict.fromkeys(wanted)))
    if payload is not None:
        rows = _match(rows, facts, cv_text)
    else:
        for row in rows:
            row["match"], row["evidence"] = "missing", "No CV or profile saved, so nothing could be matched."
    rows, dropped = _budget(rows)
    triage = data.get("triage") if isinstance(data.get("triage"), dict) else None
    remote = "Remote" if re.search(r"\bremote\b", f"{facts['location']} {jd}", re.I) else \
        "Hybrid" if re.search(r"\bhybrid\b", jd, re.I) else ("On-site" if facts["location"] else "Not stated")
    level, level_rank = _seniority(title)
    candidate_rank = _candidate_rank(facts["years"])

    block_a = {"Role": title, "Company": facts["company"] or "Not stated", "Location": facts["location"] or "Not stated",
               "Work arrangement": remote, "Seniority in the title": level or "Not stated",
               "Employment type": snapshot.get("employment_type") or "Not stated",
               "Years asked": f"{snapshot['experience_years']:g}+" if isinstance(snapshot.get("experience_years"), (int, float))
               and snapshot["experience_years"] > 0 else "Not stated"}

    gaps = []
    for row in rows:
        if row["band"] in ("critical", "high") and row["match"] != "strong":
            gaps.append({
                "requirement": row["requirement"], "blocker": row["band"] == "critical",
                "risk": f"Interviewers are likely to ask about {row['requirement']} because the posting "
                        + ("names it as required." if row["tier"] == "stated" else "returns to it more than once."),
                "mitigation": ("Your CV mentions it; add a bullet that shows the result you got with it." if row["match"] == "partial"
                               else f"If you have used {row['requirement']}, add where and with what result. If not, say so plainly "
                                    "and name the closest work on your CV; do not claim it."),
            })

    if level_rank is None or candidate_rank is None:
        level_note = "Not enough information to compare levels: " + (
            "the title names no level." if level_rank is None else "your CV or profile gives no years of experience.")
    elif candidate_rank >= level_rank:
        level_note = f"The title reads {level}; your {facts['years']:g} years fit that level or above it."
    else:
        level_note = f"The title reads {level}; your {facts['years']:g} years are below what that level usually needs."
    block_c = {"detected": level or "Not stated", "your_years": facts["years"], "assessment": level_note,
               "plan": ["Lead with results that have numbers from your CV; they argue for the level better than titles.",
                        "If they offer a lower level, ask for the pay band, a written review date (for example 6 months) and the promotion criteria."]}

    posted = annual_posted_pay(snapshot)
    brief = (triage or {}).get("brief") or {}
    pay_lines = []
    if posted:
        pay_lines.append(f"Posted: {posted['currency'] or '?'} {posted['min']:,.0f}-{posted['max']:,.0f} a year.")
    else:
        pay_lines.append("The posting states no pay. ALFRED did not estimate one.")
    if brief.get("pay_floor"):
        pay_lines.append(f"Your floor: {brief['pay_currency']} {float(brief['pay_floor']):,.0f} a year.")
    pay_lines.append("Market pay was not researched: ALFRED does not read salary sites. Check Glassdoor, AmbitionBox or "
                     "Levels.fyi yourself if you need it.")

    wins = ranked_achievements(cv_text, facts["terms"], 3)
    block_e = {"lead_with": facts["matched"][:6], "achievements": wins,
               "add_only_if_true": facts["missing"][:8],
               "steps": ["Move the matching skills to the top of your skills line.",
                         "Put the achievements listed here first under your current role.",
                         "Use the job's own words for skills you really have, so applicant tracking systems find them."]}

    stories = []
    for row in [row for row in rows if row["band"] in ("critical", "high")][:5]:
        seed = row.get("evidence", "") if row["match"] != "missing" else ""
        stories.append({"requirement": row["requirement"],
                        "prompt": f"Tell me about a time you used {row['requirement']}.",
                        "seed": seed or "No CV line yet; pick a real example before the interview.",
                        "star": ["Situation", "Task", "Action", "Result (with a number)"]})

    signals, concerns = [], []
    source_name = getattr(analysis, "source_name", "") or snapshot.get("source_name") or ""
    if any(name.casefold() in source_name.casefold() for name in API_SOURCES):
        signals.append(f"Read from the employer's own {source_name} job board.")
    if getattr(analysis, "apply_url", "") or snapshot.get("apply_url"):
        signals.append("The posting has an application link.")
    if posted:
        signals.append("Pay is stated.")
    if len(jd) < 400:
        concerns.append("The description is very short, so the role may be vague or a placeholder.")
    if FEE_RE.search(jd):
        concerns.append(f'Asks for money: "{_quote(FEE_RE.search(jd).group(0))}". Real employers do not charge applicants.')
    injected = INJECTION_RE.search(jd)
    if injected:
        concerns.append(f'Contains text aimed at automated tools ("{injected.group(0)}"). ALFRED ignored it.')
    legitimacy = "caution" if concerns else "no concerns found" if signals else "not enough information"

    verdict = ({"score": triage.get("score"), "verdict": triage.get("verdict"), "reason": triage.get("reason")}
               if triage else {"score": None, "verdict": "NOT_SCORED", "reason": "Run triage with your brief to get a score."})
    report = {
        "available": True, "generated_on": today.isoformat(), "source": source,
        "verdict": verdict,
        "A": {"title": "Role summary", "rows": block_a},
        "B": {"title": "Match with your CV", "rows": rows, "dropped": dropped, "gaps": gaps},
        "C": {"title": "Level and strategy", **block_c},
        "D": {"title": "Pay", "lines": pay_lines},
        "E": {"title": "CV changes for this job", **block_e},
        "F": {"title": "Interview plan", "stories": stories},
        "G": {"title": "Posting legitimacy", "assessment": legitimacy, "signals": signals, "concerns": concerns},
        "basis": "Career Ops A-G evaluation, built from the saved posting, your CV and your triage. No AI wrote it; "
                 "nothing was looked up online. Importance comes from the posting alone, before your CV is read.",
    }
    report["markdown"] = to_markdown(report)
    return report


MATCH_LABEL = {"strong": "Strong", "partial": "Partial", "missing": "Missing"}


def _cell(value) -> str:
    return str(value).replace("|", "/").replace("\n", " ")


def to_markdown(report: dict) -> str:
    out = [f"# Evaluation: {report['A']['rows']['Role']} at {report['A']['rows']['Company']}", "",
           f"Generated {report['generated_on']}. {report['basis']}", ""]
    verdict = report["verdict"]
    out += [f"**Triage:** {verdict['verdict']}" + (f" ({verdict['score']}/5)" if verdict["score"] is not None else "")
            + f" - {verdict['reason']}", "", "## A) Role summary", "", "| Item | Value |", "|---|---|"]
    out += [f"| {key} | {_cell(value)} |" for key, value in report["A"]["rows"].items()]
    out += ["", "## B) Match with your CV", "", "| Requirement | Importance | Match | Posting says | Evidence / gap |", "|---|---|---|---|---|"]
    out += [f"| {_cell(r['requirement'])} | {r['band']} ({r['tier']}) | {MATCH_LABEL[r['match']]} | {_cell(r['jd_signal'])} | {_cell(r['evidence'])} |"
            for r in report["B"]["rows"]]
    if report["B"]["dropped"]:
        out.append(f"\n+{report['B']['dropped']} lower-importance requirements not listed.")
    if report["B"]["gaps"]:
        out += ["", "### Gaps"] + [f"- **{g['requirement']}**{' (blocker)' if g['blocker'] else ''}: {g['risk']} {g['mitigation']}"
                                   for g in report["B"]["gaps"]]
    c = report["C"]
    out += ["", "## C) Level and strategy", "", c["assessment"], ""] + [f"- {line}" for line in c["plan"]]
    out += ["", "## D) Pay", ""] + [f"- {line}" for line in report["D"]["lines"]]
    e = report["E"]
    out += ["", "## E) CV changes for this job", ""] + [f"- {line}" for line in e["steps"]]
    if e["lead_with"]:
        out.append(f"- Lead with: {', '.join(e['lead_with'])}")
    out += [f"- Achievement to put first: {line}" for line in e["achievements"]]
    if e["add_only_if_true"]:
        out.append(f"- Asked for but not on your CV (add only if true): {', '.join(e['add_only_if_true'])}")
    out += ["", "## F) Interview plan", ""]
    out += [f"- {s['prompt']} Start from: {s['seed']}" for s in report["F"]["stories"]] or ["- No critical or high requirement to prepare for."]
    g = report["G"]
    out += ["", "## G) Posting legitimacy", "", f"Assessment: {g['assessment']}."]
    out += [f"- {line}" for line in g["signals"]] + [f"- Concern: {line}" for line in g["concerns"]]
    return "\n".join(out) + "\n"
