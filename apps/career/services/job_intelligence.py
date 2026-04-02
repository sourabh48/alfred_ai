from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from statistics import median
from urllib.parse import quote_plus, urlparse

import requests
from bs4 import BeautifulSoup

from alfred_ai.services import extract_document_text
from alfred_ai.services.url_safety import validate_public_http_url
from apps.integrations.services import verified_intelligence

JOB_SKILLS = {
    "python", "sql", "excel", "power bi", "tableau", "django", "react", "node", "aws", "azure", "gcp",
    "docker", "kubernetes", "machine learning", "data analysis", "statistics", "forecasting", "finance",
    "risk", "operations", "analytics", "etl", "airflow", "product management", "strategy", "communication",
    "java", "javascript", "typescript", "spark", "pandas", "scikit-learn", "fastapi", "postgresql",
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
ROLE_HINTS = [
    "software engineer", "backend engineer", "frontend engineer", "full stack developer",
    "data analyst", "business analyst", "financial analyst", "data scientist",
    "machine learning engineer", "product manager", "program manager", "finance manager",
]
LINK_RE = re.compile(r"https?://[^\s<>\"]+", re.IGNORECASE)
CITY_TO_STATE_COUNTRY = {
    "bengaluru": ("Karnataka", "India"),
    "bangalore": ("Karnataka", "India"),
    "mumbai": ("Maharashtra", "India"),
    "pune": ("Maharashtra", "India"),
    "hyderabad": ("Telangana", "India"),
    "chennai": ("Tamil Nadu", "India"),
    "delhi": ("Delhi", "India"),
    "gurugram": ("Haryana", "India"),
    "gurgaon": ("Haryana", "India"),
    "noida": ("Uttar Pradesh", "India"),
    "kolkata": ("West Bengal", "India"),
    "san francisco": ("California", "United States"),
    "new york": ("New York", "United States"),
    "austin": ("Texas", "United States"),
}
STATE_TO_COUNTRY = {
    "karnataka": "India",
    "maharashtra": "India",
    "telangana": "India",
    "tamil nadu": "India",
    "delhi": "India",
    "haryana": "India",
    "uttar pradesh": "India",
    "west bengal": "India",
    "california": "United States",
    "new york": "United States",
    "texas": "United States",
}
COUNTRY_ALIASES = {
    "india": "India",
    "usa": "United States",
    "us": "United States",
    "united states": "United States",
    "united kingdom": "United Kingdom",
    "uk": "United Kingdom",
    "canada": "Canada",
    "australia": "Australia",
    "remote": "Remote",
    "worldwide": "Remote",
    "global": "Remote",
}
SALARY_BLOCK_RE = re.compile(
    r"(?P<currency>INR|Rs\.?|₹|USD|\$)?\s*"
    r"(?P<first>\d[\d,]*(?:\.\d+)?)\s*(?P<first_unit>k|lpa|lakh|lakhs|crore|cr|million|m)?"
    r"(?:\s*(?:-|to|–)\s*(?P<second>\d[\d,]*(?:\.\d+)?)\s*(?P<second_unit>k|lpa|lakh|lakhs|crore|cr|million|m)?)?"
    r"\s*(?P<period>per\s+annum|per\s+year|/year|yearly|annual|annum|lpa|per\s+month|/month|monthly|month|pm|per\s+hour|/hour|hourly)?",
    re.IGNORECASE,
)


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
    employment_type: str = ""
    salary_min: float = 0.0
    salary_max: float = 0.0
    salary_currency: str = ""
    salary_period: str = ""
    source_kind: str = "job_page"


class JobIntelligenceService:
    USER_AGENT = "AlfredAI/1.0 (career-intelligence)"

    def parse_job_page(self, job_url: str) -> JobPostingSnapshot:
        job_url = validate_public_http_url(job_url)
        response = requests.get(job_url, headers={"User-Agent": self.USER_AGENT}, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        ld_json = self._extract_job_posting_json_ld(soup)
        domain = urlparse(job_url).netloc.replace("www.", "")
        if "greenhouse.io" in domain:
            raw = self._parse_greenhouse_page(soup, job_url, domain, ld_json)
        elif "lever.co" in domain:
            raw = self._parse_lever_page(soup, job_url, domain, ld_json)
        elif "workdayjobs.com" in domain or "myworkdayjobs.com" in domain:
            raw = self._parse_workday_page(soup, job_url, domain, ld_json)
        elif "ashbyhq.com" in domain:
            raw = self._parse_ashby_page(soup, job_url, domain, ld_json)
        else:
            raw = self._parse_generic_page(soup, job_url, domain, ld_json)
        description = " ".join((raw.description or "").split())[:12000]
        salary_min, salary_max, salary_currency, salary_period = self._extract_salary(ld_json, description or soup.get_text(" ", strip=True))
        return JobPostingSnapshot(
            source_name=raw.source_name,
            job_url=job_url,
            apply_url=raw.apply_url or job_url,
            company=(raw.company or domain.split(".")[0].replace("-", " ").title())[:180],
            title=(raw.title or "")[:180],
            location=(raw.location or "")[:180],
            description=description,
            required_skills=self._extract_skills(description),
            experience_years=self._extract_experience(description),
            employment_type=self._extract_employment_type(ld_json, description),
            salary_min=salary_min,
            salary_max=salary_max,
            salary_currency=salary_currency,
            salary_period=salary_period,
            source_kind="job_page",
        )

    def parse_recruiter_message(self, message_text: str, *, attachment=None, filename: str = "") -> JobPostingSnapshot:
        attachment_text = ""
        if attachment is not None:
            raw_bytes = self._read_upload_bytes(attachment)
            attachment_text = extract_document_text(raw_bytes, filename or getattr(attachment, "name", "attachment")).text
        combined = "\n".join(part for part in [message_text or "", attachment_text or ""] if part).strip()
        salary_min, salary_max, salary_currency, salary_period = self._extract_salary({}, combined)
        return JobPostingSnapshot(
            source_name="Recruiter Mail Intake",
            job_url=self._synthetic_intake_url(combined),
            apply_url=(LINK_RE.findall(combined) or [self._synthetic_intake_url(combined)])[0],
            company=self._extract_company_from_recruiter_text(combined)[:180],
            title=self._extract_role_from_text(combined)[:180],
            location=self._extract_location_from_text(combined)[:180],
            description=" ".join(combined.split())[:12000],
            required_skills=self._extract_skills(combined),
            experience_years=self._extract_experience(combined),
            employment_type=self._extract_employment_type({}, combined),
            salary_min=salary_min,
            salary_max=salary_max,
            salary_currency=salary_currency,
            salary_period=salary_period,
            source_kind="recruiter_message",
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
        strengths, gaps = [], []
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
        if job.salary_min or job.salary_max:
            strengths.append("The role exposes a pay range, so Alfred can compare it against your current compensation more concretely.")
        if not strengths:
            strengths.append("General title alignment exists, but the fit signal is weak without stronger skill overlap.")
        if not gaps:
            gaps.append("No major gap is obvious from the extracted description, but manual review is still required.")
        return {
            "fit_score": fit_score,
            "matched_skills": matched,
            "missing_skills": missing,
            "strengths": strengths[:5],
            "gaps": gaps[:4],
        }

    def market_outlook(self, role: str, company: str = "", macro: dict | None = None) -> dict:
        macro = macro or verified_intelligence.macro_context()
        layoff_news = self._news_search(f'("{role}" OR technology) layoffs India OR "job cuts"')
        company_clause = f' OR "{company}" jobs' if company else ""
        job_market_news = self._news_search(f'("{role}" hiring India OR "{role}" jobs India{company_clause})')
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

    def suggest_openings(self, role: str, skills: list[str], *, country: str = "", state: str = "") -> dict:
        search_terms = [
            " ".join([role, *skills[:2]]).strip(),
            role.strip(),
            skills[0] if skills else "",
            "developer" if "engineer" in role.lower() else "",
            "analyst" if "analyst" in role.lower() else "",
            "python",
        ]
        seen_urls, jobs, evidence_records, used_terms = set(), [], [], []
        for term in [item for item in search_terms if item]:
            result = verified_intelligence.remotive_jobs(term)
            evidence_records.append(result.evidence)
            used_terms.append(term)
            for item in result.payload.get("jobs", []):
                url = item.get("url", "")
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)
                jobs.append(self._normalize_opening(item, role=role, skills=skills, evidence=result.evidence))
        evidence = self._combine_evidence(
            evidence_records,
            title="Live opening suggestions",
            source_name="Remotive Jobs API",
            source_url="https://remotive.com/api/remote-jobs",
            summary=f"Merged {len(jobs)} opening(s) across {len(used_terms)} search variant(s).",
        )
        filtered_jobs = [
            item for item in jobs
            if self._opening_matches_location(item, country=country, state=state)
        ]
        filtered_jobs.sort(
            key=lambda item: (
                float(item.get("relevance_score") or 0),
                1 if item.get("salary") else 0,
                item.get("publication_date", ""),
            ),
            reverse=True,
        )
        return {
            "openings": filtered_jobs[:8],
            "evidence": evidence,
            "filters": self._opening_filter_metadata(jobs),
            "active_filters": {
                "country": country,
                "state": state,
            },
            "total_candidates": len(jobs),
            "filtered_candidates": len(filtered_jobs),
        }

    def _normalize_opening(self, item: dict, *, role: str, skills: list[str], evidence: dict) -> dict:
        company = item.get("company") or item.get("company_name") or ""
        location = item.get("location", "") or "Remote"
        location_meta = self._location_hierarchy(location)
        relevance = self._opening_relevance(role, skills, item)
        return {
            "title": item.get("title", ""),
            "company": company,
            "location": location,
            "country": location_meta["country"],
            "state": location_meta["state"],
            "city": location_meta["city"],
            "is_remote": location_meta["is_remote"],
            "category": item.get("category", ""),
            "url": item.get("url", ""),
            "publication_date": item.get("publication_date", ""),
            "salary": item.get("salary", ""),
            "tags": item.get("tags", [])[:8],
            "portal_name": evidence.get("source_name", "Verified opening source") or "Verified opening source",
            "portal_url": evidence.get("source_url", ""),
            "portal_family": self._portal_family(item.get("url", "")),
            "portal_host": urlparse(item.get("url", "")).netloc.replace("www.", ""),
            "aggregator_name": evidence.get("source_name", "Verified opening source") or "Verified opening source",
            "verified_source": evidence.get("status", "fresh") in {"fresh", "stale"},
            "source_status": evidence.get("status", ""),
            "verified_at": evidence.get("verified_at", ""),
            "relevance_score": relevance["score"],
            "match_reasons": relevance["reasons"],
        }

    def _opening_relevance(self, role: str, skills: list[str], opening: dict) -> dict:
        title = str(opening.get("title", "") or "").lower()
        category = str(opening.get("category", "") or "").lower()
        tags = {str(item).lower() for item in (opening.get("tags") or []) if item}
        score = 25.0
        reasons = []
        normalized_role = str(role or "").strip().lower()
        if normalized_role and normalized_role in title:
            score += 38
            reasons.append("Job title directly matches your tracked role.")
        elif normalized_role and any(token in title for token in normalized_role.split() if len(token) > 2):
            score += 22
            reasons.append("Job title overlaps with your tracked role.")
        skill_hits = [skill for skill in skills if str(skill or "").lower() in tags or str(skill or "").lower() in title or str(skill or "").lower() in category]
        if skill_hits:
            score += min(len(skill_hits) * 9, 27)
            reasons.append(f"Role tags align with {', '.join(skill_hits[:3])}.")
        if "remote" in str(opening.get("location", "") or "").lower():
            score += 4
            reasons.append("Remote eligibility is explicitly mentioned.")
        return {"score": round(min(score, 99), 1), "reasons": reasons[:3]}

    def _opening_matches_location(self, opening: dict, *, country: str = "", state: str = "") -> bool:
        normalized_country = self._normalize_country(country)
        normalized_state = str(state or "").strip().lower()
        if normalized_country and normalized_country != "Remote":
            if opening.get("is_remote") and not normalized_state:
                return True
            if self._normalize_country(opening.get("country", "")) != normalized_country:
                return False
        if normalized_country == "Remote":
            return bool(opening.get("is_remote"))
        if normalized_state:
            opening_state = str(opening.get("state", "") or "").strip().lower()
            return opening_state == normalized_state
        return True

    def _opening_filter_metadata(self, openings: list[dict]) -> dict:
        countries = sorted({item.get("country", "") for item in openings if item.get("country")})
        states_by_country: dict[str, list[str]] = {}
        for country in countries:
            states = sorted({item.get("state", "") for item in openings if item.get("country") == country and item.get("state")})
            if states:
                states_by_country[country] = states
        return {
            "countries": countries,
            "states_by_country": states_by_country,
        }

    def _location_hierarchy(self, value: str) -> dict:
        raw = str(value or "").strip()
        normalized = raw.lower()
        if not raw:
            return {"country": "", "state": "", "city": "", "is_remote": False}
        if any(token in normalized for token in ("remote", "worldwide", "global", "anywhere")):
            return {"country": "Remote", "state": "", "city": "", "is_remote": True}
        parts = [item.strip() for item in re.split(r"[,/|]", raw) if item.strip()]
        city = ""
        state = ""
        country = ""
        for part in parts:
            lowered = part.lower()
            if lowered in COUNTRY_ALIASES:
                country = COUNTRY_ALIASES[lowered]
                continue
            if lowered in STATE_TO_COUNTRY:
                state = part.title()
                country = country or STATE_TO_COUNTRY[lowered]
                continue
            if lowered in CITY_TO_STATE_COUNTRY:
                city = part.title()
                mapped_state, mapped_country = CITY_TO_STATE_COUNTRY[lowered]
                state = state or mapped_state
                country = country or mapped_country
        if not city:
            for city_name, (mapped_state, mapped_country) in CITY_TO_STATE_COUNTRY.items():
                if city_name in normalized:
                    city = city_name.title()
                    state = state or mapped_state
                    country = country or mapped_country
                    break
        return {"country": country, "state": state, "city": city, "is_remote": False}

    def _normalize_country(self, value: str) -> str:
        lowered = str(value or "").strip().lower()
        return COUNTRY_ALIASES.get(lowered, str(value or "").strip())

    def compensation_benchmark(
        self,
        *,
        role: str,
        location: str = "",
        openings: list[dict] | None = None,
        job_snapshot: JobPostingSnapshot | None = None,
        openings_evidence: dict | None = None,
        current_income_annual: float = 0.0,
    ) -> dict:
        observations, evidence = [], []
        if openings_evidence:
            evidence.append(openings_evidence)
        if job_snapshot and (job_snapshot.salary_min or job_snapshot.salary_max):
            annual_min, annual_max = self._annualize_salary_range(job_snapshot.salary_min, job_snapshot.salary_max, job_snapshot.salary_period)
            observations.append(
                {
                    "source": job_snapshot.source_name,
                    "location": job_snapshot.location,
                    "salary_min_annual": annual_min,
                    "salary_max_annual": annual_max,
                    "currency": job_snapshot.salary_currency or "INR",
                    "url": job_snapshot.job_url,
                }
            )
            evidence.append(
                {
                    "title": "Direct role compensation signal",
                    "source_name": job_snapshot.source_name,
                    "source_url": job_snapshot.job_url,
                    "summary": f"Salary signal extracted from the current {job_snapshot.source_kind.replace('_', ' ')}.",
                    "status": "fresh",
                    "fetched_at": "",
                    "verified_at": "",
                    "stale_after": "",
                    "query": role,
                    "notes": "Compensation was read directly from the active role text or JSON-LD when the page exposed it.",
                }
            )
        for opening in openings or []:
            salary = self._parse_salary_text(opening.get("salary", ""))
            if not salary:
                continue
            annual_min, annual_max = self._annualize_salary_range(salary["salary_min"], salary["salary_max"], salary["period"])
            observations.append(
                {
                    "source": opening.get("company") or "Opening",
                    "location": opening.get("location", ""),
                    "salary_min_annual": annual_min,
                    "salary_max_annual": annual_max,
                    "currency": salary["currency"],
                    "url": opening.get("url", ""),
                }
            )
        if not observations:
            return {
                "available": False,
                "summary": "No salary-bearing evidence is available from the current parsed role or configured job feeds.",
                "sample_count": 0,
                "evidence": evidence,
                "location_scope": location or "Global / Remote",
            }
        filtered = [
            item for item in observations
            if not location
            or location.lower() in (item.get("location", "") or "").lower()
            or "remote" in (item.get("location", "") or "").lower()
        ]
        selected = filtered or observations
        mins = [item["salary_min_annual"] for item in selected if item["salary_min_annual"]]
        maxes = [item["salary_max_annual"] for item in selected if item["salary_max_annual"]]
        benchmark_min = round(median(mins), 2) if mins else 0.0
        benchmark_max = round(median(maxes), 2) if maxes else benchmark_min
        benchmark_mid = round((benchmark_min + benchmark_max) / 2, 2) if benchmark_max else benchmark_min
        comparison = None
        if current_income_annual:
            if current_income_annual < benchmark_min:
                comparison = "below_benchmark"
            elif benchmark_max and current_income_annual > benchmark_max:
                comparison = "above_benchmark"
            else:
                comparison = "within_benchmark"
        summary = f"Compensation benchmark is evidence-backed from {len(selected)} salary-bearing opening signal(s)."
        if comparison == "below_benchmark":
            summary += " Your current annualized income sits below the current benchmark band."
        elif comparison == "above_benchmark":
            summary += " Your current annualized income is above the current benchmark band."
        elif comparison == "within_benchmark":
            summary += " Your current annualized income sits inside the current benchmark band."
        return {
            "available": True,
            "summary": summary,
            "sample_count": len(selected),
            "market_min_annual": benchmark_min,
            "market_max_annual": benchmark_max,
            "market_mid_annual": benchmark_mid,
            "currency": next((item["currency"] for item in selected if item.get("currency")), "INR"),
            "location_scope": location or "Global / Remote",
            "comparison": comparison,
            "current_income_annual": round(current_income_annual or 0, 2),
            "evidence": evidence[:4],
        }

    def build_study_recommendations(self, profile, resume_payload: dict, latest_analysis=None, openings: list[dict] | None = None) -> dict:
        openings = openings or []
        role = (resume_payload.get("role") or getattr(profile, "role", "") or "").lower()
        experience_years = float(resume_payload.get("experience_years") or getattr(profile, "experience_years", 0) or 0)
        user_skills = {item.strip().lower() for item in (resume_payload.get("skills") or []) if item and item.strip()}
        fit_payload = ((getattr(latest_analysis, "extracted_payload", {}) or {}).get("fit", {}) if latest_analysis else {}) or {}
        missing_skills = [item.strip().lower() for item in (fit_payload.get("missing_skills") or []) if item and item.strip()]
        market_skill_counts: dict[str, int] = {}
        for opening in openings:
            combined = " ".join(str(item) for item in [*(opening.get("tags") or []), opening.get("title", ""), opening.get("category", "")] if item)
            for skill in self._extract_skills(combined):
                market_skill_counts[skill.lower()] = market_skill_counts.get(skill.lower(), 0) + 1
        study_queue: list[tuple[str, str, list[str]]] = []
        for skill in missing_skills[:4]:
            study_queue.append((skill, "Latest job-match analysis marked this as a gap.", ["latest_job_analysis", "user_resume"]))
        for skill in self._role_study_defaults(role):
            if skill not in user_skills and all(existing[0] != skill for existing in study_queue):
                study_queue.append((skill, "This is part of the normal capability ladder for your current role family and experience stage.", ["experience_stage", "role_family"]))
        for skill, count in sorted(market_skill_counts.items(), key=lambda item: (-item[1], item[0])):
            if skill in user_skills or any(existing[0] == skill for existing in study_queue):
                continue
            study_queue.append((skill, f"This appeared in {count} live opening tag or title signal(s) from the configured job feed.", ["live_openings"]))
            if len(study_queue) >= 6:
                break
        tracks = [
            {
                "skill": skill.title(),
                "priority": self._study_priority(skill, missing_skills, experience_years),
                "reason": reason,
                "grounded_in": grounded_in,
            }
            for skill, reason, grounded_in in study_queue[:5]
        ]
        if experience_years < 1.5:
            stage, stage_note = "Foundation", "Focus on fundamentals, visible portfolio work, and one strong execution stack."
        elif experience_years < 4:
            stage, stage_note = "Growth", "Close visible skill gaps, improve delivery depth, and make role-switch readiness concrete."
        elif experience_years < 8:
            stage, stage_note = "Leverage", "Deepen domain depth, architecture, automation, and communication so growth compounds."
        else:
            stage, stage_note = "Leadership", "Prioritize strategy, leadership leverage, mentoring, and selective deep-specialization."
        signals = [f"Experience stage: {stage.lower()} at about {experience_years:.1f} years.", f"Current tracked skill count: {len(user_skills)}."]
        if missing_skills:
            signals.append(f"Latest job analysis exposed {len(missing_skills)} explicit skill gap(s).")
        elif openings:
            signals.append("No explicit skill gap is stored, so live opening signals are driving the next-study list.")
        else:
            signals.append("No recent opening or job-match signal is stored, so the list falls back to role-stage guidance.")
        return {"experience_stage": stage, "focus_window": "Next 6 to 8 weeks", "stage_note": stage_note, "signals": signals, "tracks": tracks}

    def _parse_generic_page(self, soup: BeautifulSoup, job_url: str, domain: str, ld_json: dict) -> JobPostingSnapshot:
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
        return JobPostingSnapshot(source_name=domain, job_url=job_url, apply_url=apply_url or job_url, company=company, title=title, location=location, description=description, required_skills=[], experience_years=0.0)

    def _parse_greenhouse_page(self, soup: BeautifulSoup, job_url: str, domain: str, ld_json: dict) -> JobPostingSnapshot:
        generic = self._parse_generic_page(soup, job_url, domain, ld_json)
        title_node = soup.select_one("h1") or soup.select_one(".app-title")
        location_node = soup.select_one(".location") or soup.select_one(".location-name")
        apply_link = soup.find("a", href=True, string=re.compile(r"apply", re.IGNORECASE))
        description = generic.description or " ".join(node.get_text(" ", strip=True) for node in soup.select(".content, #content, main, section")[:8])
        return JobPostingSnapshot(
            source_name="Greenhouse",
            job_url=job_url,
            apply_url=apply_link.get("href") if apply_link else generic.apply_url,
            company=generic.company,
            title=title_node.get_text(" ", strip=True) if title_node else generic.title,
            location=location_node.get_text(" ", strip=True) if location_node else generic.location,
            description=description,
            required_skills=[],
            experience_years=0.0,
        )

    def _parse_lever_page(self, soup: BeautifulSoup, job_url: str, domain: str, ld_json: dict) -> JobPostingSnapshot:
        generic = self._parse_generic_page(soup, job_url, domain, ld_json)
        title_node = soup.select_one(".posting-headline h2") or soup.select_one("h2")
        location_node = soup.select_one(".posting-categories .sort-by-location") or soup.select_one(".location")
        description = generic.description or " ".join(node.get_text(" ", strip=True) for node in soup.select(".section-wrapper, .content, main")[:8])
        company = generic.company or urlparse(job_url).path.strip("/").split("/")[0].replace("-", " ").title()
        return JobPostingSnapshot(source_name="Lever", job_url=job_url, apply_url=generic.apply_url, company=company, title=title_node.get_text(" ", strip=True) if title_node else generic.title, location=location_node.get_text(" ", strip=True) if location_node else generic.location, description=description, required_skills=[], experience_years=0.0)

    def _parse_workday_page(self, soup: BeautifulSoup, job_url: str, domain: str, ld_json: dict) -> JobPostingSnapshot:
        generic = self._parse_generic_page(soup, job_url, domain, ld_json)
        title_node = (
            soup.select_one('[data-automation-id="jobPostingHeader"] h1')
            or soup.select_one('[data-automation-id="jobPostingHeader"]')
            or soup.select_one("h1")
        )
        location_node = (
            soup.select_one('[data-automation-id="locations"]')
            or soup.select_one('[data-automation-id="primaryLocation"]')
            or soup.select_one('[data-automation-id="location"]')
        )
        description_node = soup.select_one('[data-automation-id="jobPostingDescription"]')
        apply_link = soup.find("a", href=True, string=re.compile(r"apply", re.IGNORECASE))
        company = generic.company or domain.split(".")[0].replace("-", " ").title()
        description_bits = []
        if description_node:
            description_bits.append(description_node.get_text(" ", strip=True))
        if generic.description:
            description_bits.append(generic.description)
        description = " ".join(part for part in description_bits if part).strip()
        return JobPostingSnapshot(
            source_name="Workday",
            job_url=job_url,
            apply_url=apply_link.get("href") if apply_link else generic.apply_url,
            company=company,
            title=title_node.get_text(" ", strip=True) if title_node else generic.title,
            location=location_node.get_text(" ", strip=True) if location_node else generic.location,
            description=description,
            required_skills=[],
            experience_years=0.0,
        )

    def _parse_ashby_page(self, soup: BeautifulSoup, job_url: str, domain: str, ld_json: dict) -> JobPostingSnapshot:
        generic = self._parse_generic_page(soup, job_url, domain, ld_json)
        title_node = soup.select_one("h1") or soup.select_one('[data-testid="job-title"]')
        location_node = soup.find(string=re.compile(r"\bLocation\b", re.IGNORECASE))
        description = generic.description or " ".join(
            node.get_text(" ", strip=True)
            for node in soup.select('[data-testid="job-posting-description"], main, article, section')[:8]
        )
        location = generic.location
        if hasattr(location_node, "parent") and location_node.parent:
            location_container = location_node.parent.parent if getattr(location_node.parent, "parent", None) else location_node.parent
            location = location_container.get_text(" ", strip=True).replace("Location", "").strip(" :-") or location
        company = generic.company or urlparse(job_url).path.strip("/").split("/")[0].replace("-", " ").title()
        return JobPostingSnapshot(
            source_name="Ashby",
            job_url=job_url,
            apply_url=generic.apply_url,
            company=company,
            title=title_node.get_text(" ", strip=True) if title_node else generic.title,
            location=location,
            description=description,
            required_skills=[],
            experience_years=0.0,
        )

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
            for item in parsed if isinstance(parsed, list) else [parsed]:
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
        for tag_name, attrs, field in [("meta", {"property": "og:site_name"}, "content"), ("meta", {"name": "application-name"}, "content")]:
            tag = soup.find(tag_name, attrs=attrs)
            if tag and tag.get(field) and tag.get(field) not in {"Job Boards", "Lever"}:
                return tag.get(field)
        match = re.search(r"\bat\s+([A-Z][A-Za-z0-9&.,' -]{2,80})", f"{title} {description[:300]}")
        if match:
            return match.group(1).split(" - ", 1)[0].strip(" -")
        return domain.split(".")[0].replace("-", " ").title()

    def _extract_company_from_recruiter_text(self, text: str) -> str:
        for pattern in [r"(?i)\b(?:company|client|organization)\s*[:\-]\s*([A-Z][A-Za-z0-9&.,' -]{2,80})", r"(?i)\bat\s+([A-Z][A-Za-z0-9&.,' -]{2,80})"]:
            match = re.search(pattern, text[:2000])
            if match:
                return match.group(1).strip(" -")
        return ""

    def _extract_role_from_text(self, text: str) -> str:
        lowered = text.lower()
        for role in ROLE_HINTS:
            if role in lowered:
                return role.title()
        for pattern in [r"(?i)\b(?:role|position|opening|opportunity|job title)\s*[:\-]\s*([A-Za-z/&,\- ]{3,100})", r"(?i)\bwe are hiring\s+(?:for\s+)?([A-Za-z/&,\- ]{3,100})"]:
            match = re.search(pattern, text[:2500])
            if match:
                return match.group(1).strip(" -").title()
        return ""

    def _extract_page_description(self, soup: BeautifulSoup) -> str:
        description_tag = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
        meta_description = description_tag.get("content", "") if description_tag and description_tag.get("content") else ""
        body_text = ""
        for selector in ["div[data-testid='job-post-content']", "div.content", "div#content", "section", "article", "main"]:
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

    def _extract_employment_type(self, ld_json: dict, text: str) -> str:
        raw = ld_json.get("employmentType")
        raw = raw[0] if isinstance(raw, list) and raw else raw
        if raw:
            return str(raw)
        lowered = text.lower()
        for token in ("full time", "part time", "contract", "internship", "freelance", "temporary"):
            if token in lowered:
                return token.title()
        return ""

    def _extract_salary(self, ld_json: dict, text: str) -> tuple[float, float, str, str]:
        salary = self._extract_salary_from_json_ld(ld_json)
        if salary:
            return salary["salary_min"], salary["salary_max"], salary["currency"], salary["period"]
        salary = self._parse_salary_text(text)
        if salary:
            return salary["salary_min"], salary["salary_max"], salary["currency"], salary["period"]
        return 0.0, 0.0, "", ""

    def _extract_salary_from_json_ld(self, ld_json: dict) -> dict | None:
        if not isinstance(ld_json, dict):
            return None
        base_salary = ld_json.get("baseSalary")
        if not isinstance(base_salary, dict):
            return None
        currency = base_salary.get("currency", "INR")
        value = base_salary.get("value")
        period = "year"
        salary_min = 0.0
        salary_max = 0.0
        if isinstance(value, dict):
            period = str(value.get("unitText") or "year").lower()
            salary_min = float(value.get("minValue") or value.get("value") or 0)
            salary_max = float(value.get("maxValue") or salary_min or 0)
        elif isinstance(value, (int, float)):
            salary_min = float(value)
            salary_max = float(value)
        if not salary_min and not salary_max:
            return None
        return {"salary_min": salary_min, "salary_max": salary_max or salary_min, "currency": currency.upper(), "period": self._normalize_salary_period(period)}

    def _parse_salary_text(self, text: str) -> dict | None:
        match = SALARY_BLOCK_RE.search(text or "")
        if not match:
            return None
        fallback_unit = self._salary_unit_hint(match.group("period") or "")
        shared_unit = match.group("first_unit") or match.group("second_unit") or fallback_unit
        first_value = self._salary_value(match.group("first"), match.group("first_unit") or shared_unit)
        second_value = self._salary_value(match.group("second"), match.group("second_unit") or shared_unit) if match.group("second") else first_value
        if not first_value and not second_value:
            return None
        currency_raw = match.group("currency") or ""
        currency = "USD" if "$" in currency_raw or "usd" in currency_raw.lower() else "INR"
        period = self._normalize_salary_period(match.group("period") or match.group("first_unit") or "")
        salary_min = min(first_value, second_value) if second_value else first_value
        salary_max = max(first_value, second_value) if second_value else first_value
        return {"salary_min": salary_min, "salary_max": salary_max, "currency": currency, "period": period}

    def _salary_value(self, raw_value: str | None, unit: str | None) -> float:
        if not raw_value:
            return 0.0
        value = float(str(raw_value).replace(",", ""))
        normalized = (unit or "").lower()
        if normalized == "k":
            return value * 1_000
        if normalized in {"lpa", "lakh", "lakhs"}:
            return value * 100_000
        if normalized in {"crore", "cr"}:
            return value * 10_000_000
        if normalized in {"million", "m"}:
            return value * 1_000_000
        return value

    def _salary_unit_hint(self, value: str) -> str:
        normalized = str(value or "").lower()
        if "lpa" in normalized:
            return "lpa"
        if "lakh" in normalized:
            return "lakh"
        if "crore" in normalized or re.search(r"\bcr\b", normalized):
            return "crore"
        if "million" in normalized:
            return "million"
        return ""

    def _normalize_salary_period(self, value: str) -> str:
        normalized = str(value or "").lower()
        if any(token in normalized for token in ("month", "/month", "monthly", "pm")):
            return "month"
        if any(token in normalized for token in ("hour", "/hour", "hourly")):
            return "hour"
        return "year"

    def _annualize_salary_range(self, salary_min: float, salary_max: float, period: str) -> tuple[float, float]:
        multiplier = 12 if (period or "year").lower() == "month" else (2080 if (period or "year").lower() == "hour" else 1)
        return round((salary_min or 0) * multiplier, 2), round((salary_max or salary_min or 0) * multiplier, 2)

    def _combine_evidence(self, items: list[dict], *, title: str, source_name: str, source_url: str, summary: str) -> dict:
        normalized_items = [item for item in items if item]
        first = normalized_items[0] if normalized_items else {}
        notes = " | ".join(item.get("notes", "") for item in normalized_items if item.get("notes"))[:600]
        return {
            "title": title,
            "source_name": source_name,
            "source_url": source_url,
            "summary": summary,
            "status": first.get("status", "fresh"),
            "fetched_at": first.get("fetched_at", ""),
            "verified_at": first.get("verified_at", ""),
            "stale_after": first.get("stale_after", ""),
            "query": ", ".join(filter(None, [item.get("query", "") for item in normalized_items][:3])),
            "notes": notes,
        }

    def _portal_family(self, url: str) -> str:
        domain = urlparse(url or "").netloc.replace("www.", "").lower()
        if "greenhouse.io" in domain:
            return "Greenhouse"
        if "lever.co" in domain:
            return "Lever"
        if "workdayjobs.com" in domain or "myworkdayjobs.com" in domain:
            return "Workday"
        if "ashbyhq.com" in domain:
            return "Ashby"
        return domain.title() if domain else ""

    def _synthetic_intake_url(self, text: str) -> str:
        return f"https://alfred.local/recruiter-intake/{hashlib.sha256((text or 'recruiter').encode('utf-8')).hexdigest()[:16]}"

    def _read_upload_bytes(self, upload) -> bytes:
        current = upload.tell() if hasattr(upload, "tell") else None
        if hasattr(upload, "seek"):
            upload.seek(0)
        raw = upload.read()
        if current is not None and hasattr(upload, "seek"):
            upload.seek(current)
        return raw

    def _role_study_defaults(self, role: str) -> list[str]:
        normalized_role = (role or "").lower()
        for token, defaults in ROLE_STUDY_TRACKS.items():
            if token in normalized_role:
                return defaults
        return ["communication", "analytics", "strategy"]

    def _study_priority(self, skill: str, missing_skills: list[str], experience_years: float) -> str:
        if skill in missing_skills or experience_years < 3:
            return "high"
        return "medium"


job_intelligence = JobIntelligenceService()
