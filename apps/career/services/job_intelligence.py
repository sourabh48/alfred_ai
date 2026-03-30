from __future__ import annotations

from dataclasses import dataclass
import json
import re
from urllib.parse import quote_plus, urlparse

import feedparser
import requests
from bs4 import BeautifulSoup

from apps.integrations.services import verified_intelligence


JOB_SKILLS = {
    "python", "sql", "excel", "power bi", "tableau", "django", "react", "node", "aws", "azure", "gcp",
    "docker", "kubernetes", "machine learning", "data analysis", "statistics", "forecasting", "finance",
    "risk", "operations", "analytics", "etl", "airflow", "product management", "strategy", "communication",
}
EXPERIENCE_RE = re.compile(r"(\d+(?:\.\d+)?)\+?\s+(?:years?|yrs?)", re.IGNORECASE)
ROLE_STUDY_TRACKS = {
    "analyst": ["sql", "statistics", "power bi", "tableau", "python"],
    "data": ["python", "sql", "statistics", "machine learning", "pandas"],
    "engineer": ["python", "docker", "aws", "system design", "kubernetes"],
    "developer": ["python", "django", "react", "docker", "aws"],
    "product": ["product management", "strategy", "analytics", "communication"],
    "finance": ["finance", "excel", "risk", "forecasting", "sql"],
}


@dataclass
class JobPostingSnapshot:
    source_name: str
    job_url: str
    apply_url: str
    company: str
    title: str
    location: str
    description: str
    required_skills: list[str]
    experience_years: float


class JobIntelligenceService:
    USER_AGENT = "AlfredAI/1.0 (career-intelligence)"

    def parse_job_page(self, job_url: str) -> JobPostingSnapshot:
        response = requests.get(job_url, headers={"User-Agent": self.USER_AGENT}, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        ld_json = self._extract_job_posting_json_ld(soup)
        domain = urlparse(job_url).netloc.replace("www.", "")

        title = ""
        company = ""
        location = ""
        description = ""
        apply_url = job_url

        if ld_json:
            title = ld_json.get("title", "")
            company = ((ld_json.get("hiringOrganization") or {}).get("name", "")) if isinstance(ld_json.get("hiringOrganization"), dict) else ""
            description = BeautifulSoup(ld_json.get("description", "") or "", "html.parser").get_text(" ", strip=True)
            location = self._extract_location(ld_json.get("jobLocation"))
            identifier = ld_json.get("url") or ld_json.get("sameAs")
            if identifier:
                apply_url = identifier
        else:
            title = (soup.find("meta", attrs={"property": "og:title"}) or {}).get("content", "") or (soup.title.string.strip() if soup.title and soup.title.string else "")
            description = self._extract_page_description(soup)
            company = self._extract_company_from_page(soup, domain, title, description)
            location = self._extract_location_from_text(description or soup.get_text(" ", strip=True)[:5000])

        if not description:
            description = self._extract_page_description(soup)
        if not company:
            company = self._extract_company_from_page(soup, domain, title, description)
        if not location:
            location = self._extract_location_from_text(description)
        if not location:
            location_meta = soup.find("meta", attrs={"property": "og:description"})
            if location_meta and location_meta.get("content"):
                location = location_meta.get("content")

        description = " ".join((description or "").split())[:12000]
        skills = self._extract_skills(description)
        experience = self._extract_experience(description)

        return JobPostingSnapshot(
            source_name=domain,
            job_url=job_url,
            apply_url=apply_url or job_url,
            company=company[:180],
            title=title[:180],
            location=location[:180],
            description=description,
            required_skills=skills,
            experience_years=experience,
        )

    def compare_resume_to_job(self, resume_payload: dict, job: JobPostingSnapshot) -> dict:
        resume_skills = {item.lower() for item in (resume_payload.get("skills") or [])}
        required_skills = {item.lower() for item in job.required_skills}
        matched = sorted(skill.title() for skill in (resume_skills & required_skills))
        missing = sorted(skill.title() for skill in (required_skills - resume_skills))
        extra = sorted(skill.title() for skill in (resume_skills - required_skills))[:8]
        role = (resume_payload.get("role") or "").lower()
        role_fit = 1.0 if role and role in job.title.lower() else (0.75 if role and any(token in job.title.lower() for token in role.split()) else 0.5)
        exp_years = float(resume_payload.get("experience_years") or 0)
        exp_fit = 1.0 if not job.experience_years or exp_years >= job.experience_years else max(exp_years / max(job.experience_years, 1), 0)
        skill_fit = 0.55 if not required_skills else len(matched) / len(required_skills)
        fit_score = round(min(((skill_fit * 0.6) + (exp_fit * 0.25) + (role_fit * 0.15)) * 100, 99), 1)

        strengths = []
        gaps = []
        if matched:
            strengths.append(f"Matched skills: {', '.join(matched[:8])}.")
        if exp_fit >= 1:
            strengths.append("Experience level appears to meet or exceed the stated requirement.")
        elif job.experience_years:
            gaps.append(f"Resume appears below the stated experience mark of {job.experience_years:.1f} years.")
        if missing:
            gaps.append(f"Likely missing or weak skills: {', '.join(missing[:8])}.")
        if extra:
            strengths.append(f"Extra adjacent strengths detected: {', '.join(extra[:6])}.")
        if not strengths:
            strengths.append("General title alignment exists, but the fit signal is weak without stronger skill overlap.")
        if not gaps:
            gaps.append("No major gap is obvious from the extracted description, but manual review is still required.")

        return {
            "fit_score": fit_score,
            "matched_skills": matched,
            "missing_skills": missing,
            "strengths": strengths[:4],
            "gaps": gaps[:4],
        }

    def market_outlook(self, role: str, company: str = "", macro: dict | None = None) -> dict:
        macro = macro or verified_intelligence.macro_context()
        layoff_news = self._news_search(f'("{role}" OR technology) layoffs India OR "job cuts"')
        job_market_news = self._news_search(f'("{role}" hiring India OR "{role}" jobs India)')
        layoffs_count = len(layoff_news["items"])
        unemployment = macro["payload"]["unemployment"].get("latest_value") or 0
        market_return = macro["payload"]["market"].get("one_month_return_pct") or 0
        market_vix = macro["payload"]["market"].get("india_vix") or macro["payload"]["market"].get("realized_volatility_pct") or 0
        risk_score = round(min(100, (max(unemployment - 5, 0) * 8) + (layoffs_count * 6) + (6 if market_return < -4 else 0) + (8 if market_vix >= 22 else 0)), 1)

        insights = []
        if risk_score >= 55:
            insights.append("Layoff and volatility signals are elevated. Keep runway and application activity active.")
        if layoffs_count:
            insights.append(f"Recent layoff-related articles found for the role/sector: {layoffs_count}.")
        if market_return > 2:
            insights.append("Broader market sentiment is not weak, which can partially offset role-specific risk.")
        if not insights:
            insights.append("No strong external layoff spike was found in the current configured feeds.")

        evidence = [*macro["evidence"], layoff_news["evidence"], job_market_news["evidence"]]
        return {
            "risk_score": risk_score,
            "layoff_news": layoff_news["items"],
            "job_market_news": job_market_news["items"],
            "macro_context": macro["payload"],
            "insights": insights[:5],
            "evidence": evidence,
        }

    def suggest_openings(self, role: str, skills: list[str]) -> dict:
        search_terms = [
            " ".join([role, *skills[:2]]).strip(),
            role.strip(),
            skills[0] if skills else "",
            "developer" if "engineer" in role.lower() else "",
            "analyst" if "analyst" in role.lower() else "",
            "python",
        ]
        evidence = None
        jobs = []
        for term in [item for item in search_terms if item]:
            result = verified_intelligence.remotive_jobs(term)
            jobs = result.payload.get("jobs", [])[:8]
            evidence = result.evidence
            if jobs:
                break
        return {"openings": jobs, "evidence": evidence or {}}

    def build_study_recommendations(self, profile, resume_payload: dict, latest_analysis=None, openings: list[dict] | None = None) -> dict:
        openings = openings or []
        role = (resume_payload.get("role") or getattr(profile, "role", "") or "").lower()
        experience_years = float(resume_payload.get("experience_years") or getattr(profile, "experience_years", 0) or 0)
        user_skills = {item.strip().lower() for item in (resume_payload.get("skills") or []) if item and item.strip()}
        fit_payload = ((getattr(latest_analysis, "extracted_payload", {}) or {}).get("fit", {}) if latest_analysis else {}) or {}
        missing_skills = [item.strip().lower() for item in (fit_payload.get("missing_skills") or []) if item and item.strip()]

        market_skill_counts: dict[str, int] = {}
        for opening in openings:
            sources = [
                *(opening.get("tags") or []),
                opening.get("title", ""),
                opening.get("category", ""),
            ]
            combined = " ".join(str(item) for item in sources if item)
            for skill in self._extract_skills(combined):
                lowered = skill.lower()
                market_skill_counts[lowered] = market_skill_counts.get(lowered, 0) + 1

        study_queue: list[tuple[str, str, list[str]]] = []
        for skill in missing_skills[:4]:
            study_queue.append(
                (
                    skill,
                    "Latest job-match analysis marked this as a gap.",
                    ["latest_job_analysis", "user_resume"],
                )
            )

        role_defaults = self._role_study_defaults(role)
        for skill in role_defaults:
            if skill not in user_skills and all(existing[0] != skill for existing in study_queue):
                study_queue.append(
                    (
                        skill,
                        "This is part of the normal capability ladder for your current role family and experience stage.",
                        ["experience_stage", "role_family"],
                    )
                )

        for skill, count in sorted(market_skill_counts.items(), key=lambda item: (-item[1], item[0])):
            if skill in user_skills or any(existing[0] == skill for existing in study_queue):
                continue
            study_queue.append(
                (
                    skill,
                    f"This appeared in {count} live opening tag or title signal(s) from the configured job feed.",
                    ["live_openings"],
                )
            )
            if len(study_queue) >= 6:
                break

        tracks = []
        for skill, reason, grounded_in in study_queue[:5]:
            tracks.append(
                {
                    "skill": skill.title(),
                    "priority": self._study_priority(skill, missing_skills, experience_years),
                    "reason": reason,
                    "grounded_in": grounded_in,
                }
            )

        if experience_years < 1.5:
            stage = "Foundation"
            stage_note = "Focus on fundamentals, visible portfolio work, and one strong execution stack."
        elif experience_years < 4:
            stage = "Growth"
            stage_note = "Close visible skill gaps, improve delivery depth, and make role-switch readiness concrete."
        elif experience_years < 8:
            stage = "Leverage"
            stage_note = "Deepen domain depth, architecture, automation, and communication so growth compounds."
        else:
            stage = "Leadership"
            stage_note = "Prioritize strategy, leadership leverage, mentoring, and selective deep-specialization."

        signals = [
            f"Experience stage: {stage.lower()} at about {experience_years:.1f} years.",
            f"Current tracked skill count: {len(user_skills)}.",
        ]
        if missing_skills:
            signals.append(f"Latest job analysis exposed {len(missing_skills)} explicit skill gap(s).")
        elif openings:
            signals.append("No explicit skill gap is stored, so live opening signals are driving the next-study list.")
        else:
            signals.append("No recent opening or job-match signal is stored, so the list falls back to role-stage guidance.")

        return {
            "experience_stage": stage,
            "focus_window": "Next 6 to 8 weeks",
            "stage_note": stage_note,
            "signals": signals,
            "tracks": tracks,
        }

    def _news_search(self, query: str) -> dict:
        url = f"https://news.google.com/rss/search?q={quote_plus(query)}&hl=en-IN&gl=IN&ceid=IN:en"
        result = verified_intelligence.google_news_search(query)
        return {"items": result.payload.get("items", []), "evidence": result.evidence, "feed_url": url}

    def _extract_job_posting_json_ld(self, soup: BeautifulSoup) -> dict:
        for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
            raw = script.string or script.get_text()
            if not raw:
                continue
            try:
                parsed = json.loads(raw)
            except Exception:
                continue
            candidates = parsed if isinstance(parsed, list) else [parsed]
            for item in candidates:
                if isinstance(item, dict) and item.get("@type") == "JobPosting":
                    return item
        return {}

    def _extract_location(self, job_location) -> str:
        if isinstance(job_location, list) and job_location:
            job_location = job_location[0]
        if isinstance(job_location, dict):
            address = job_location.get("address", {})
            return ", ".join(filter(None, [address.get("addressLocality"), address.get("addressRegion"), address.get("addressCountry")]))
        return ""

    def _extract_company_from_page(self, soup: BeautifulSoup, domain: str, title: str, description: str) -> str:
        page_title = soup.title.string.strip() if soup.title and soup.title.string else ""
        for candidate in (page_title, title, description[:300]):
            match = re.search(r"Job Application for .*? at ([A-Z][A-Za-z0-9&.,' -]{2,80})", candidate)
            if match:
                return match.group(1).split(" - ", 1)[0].strip(" -")
        selectors = [
            ("meta", {"property": "og:site_name"}, "content"),
            ("meta", {"name": "application-name"}, "content"),
        ]
        for tag_name, attrs, field in selectors:
            tag = soup.find(tag_name, attrs=attrs)
            if tag and tag.get(field) and tag.get(field) not in {"Job Boards", "Lever"}:
                return tag.get(field)
        combined = f"{title} {description[:300]}"
        match = re.search(r"\bat\s+([A-Z][A-Za-z0-9&.,' -]{2,80})", combined)
        if match:
            return match.group(1).split(" - ", 1)[0].strip(" -")
        return domain.split(".")[0].replace("-", " ").title()

    def _extract_page_description(self, soup: BeautifulSoup) -> str:
        description_tag = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
        if description_tag and description_tag.get("content"):
            meta_description = description_tag.get("content", "")
        else:
            meta_description = ""

        selectors = [
            "div[data-testid='job-post-content']",
            "div.content",
            "div#content",
            "section",
            "article",
            "main",
        ]
        body_text = ""
        for selector in selectors:
            nodes = soup.select(selector)
            if not nodes:
                continue
            joined = " ".join(node.get_text(" ", strip=True) for node in nodes[:8])
            if len(joined) > len(body_text):
                body_text = joined
        return body_text[:8000] if len(body_text) > len(meta_description) else meta_description[:8000]

    def _extract_location_from_text(self, text: str) -> str:
        match = re.search(r"\b([A-Z][A-Za-z]+(?:,\s*[A-Z][A-Za-z]+)*(?:,\s*India|,\s*Remote)?)\b", text[:250])
        if match and any(city in match.group(1).lower() for city in ("bengaluru", "bangalore", "pune", "hyderabad", "chennai", "mumbai", "gurugram", "delhi", "remote", "india", "noida")):
            return match.group(1)
        match = re.search(r"\b(Bengaluru|Bangalore|Pune|Hyderabad|Chennai|Mumbai|Delhi|Gurgaon|Noida|Remote)\b", text, re.IGNORECASE)
        return match.group(1) if match else ""

    def _extract_skills(self, text: str) -> list[str]:
        lowered = text.lower()
        return [skill.title() for skill in sorted(JOB_SKILLS) if skill in lowered][:20]

    def _extract_experience(self, text: str) -> float:
        matches = [float(item.group(1)) for item in EXPERIENCE_RE.finditer(text)]
        return max(matches) if matches else 0.0

    def _role_study_defaults(self, role: str) -> list[str]:
        normalized_role = (role or "").lower()
        for token, defaults in ROLE_STUDY_TRACKS.items():
            if token in normalized_role:
                return defaults
        return ["communication", "analytics", "strategy"]

    def _study_priority(self, skill: str, missing_skills: list[str], experience_years: float) -> str:
        if skill in missing_skills:
            return "high"
        if experience_years < 3:
            return "high"
        if experience_years < 7:
            return "medium"
        return "medium"


job_intelligence = JobIntelligenceService()
