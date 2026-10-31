from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal, DecimalException
import hashlib
import json
import math
import re
from statistics import median
from urllib.parse import quote_plus, urlparse

from bs4 import BeautifulSoup
from django.utils import timezone

from alfred_ai.services import extract_document_text
from alfred_ai.services.currency import INR_TOKEN
from alfred_ai.services.upload_limits import document_source
from alfred_ai.services import public_http
from apps.integrations.services import verified_intelligence
from apps.integrations.services.verified_intelligence import InsightResult, freshness_snapshot
from apps.expenses.money import expense_money, money_float
from apps.users.money import profile_money
from .resume_intelligence import extract_skill_terms

JOB_SKILLS = {
    "python", "sql", "excel", "power bi", "tableau", "django", "react", "node", "azure", "gcp",
    "docker", "kubernetes", "machine learning", "data analysis", "statistics", "forecasting", "finance",
    "risk", "operations", "analytics", "etl", "airflow", "product management", "strategy", "communication",
    "java", "javascript", "typescript", "spark", "pandas", "scikit-learn", "fastapi", "postgresql",
}
EXPERIENCE_RE = re.compile(r"(\d+(?:\.\d+)?)\+?\s+(?:years?|yrs?)", re.IGNORECASE)
ROLE_STUDY_TRACKS = {
    "analyst": ["sql", "statistics", "power bi", "tableau", "python"],
    "data": ["python", "sql", "statistics", "machine learning", "pandas"],
    "engineer": ["python", "docker", "system design", "kubernetes", "linux"],
    "developer": ["python", "django", "react", "docker", "postgresql"],
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
SALARY_CURRENCY_PATTERN = rf"{INR_TOKEN}|USD\b|\$|EUR\b|\u20ac|GBP\b|\u00a3"
SALARY_BLOCK_RE = re.compile(
    rf"(?<![\w.])(?P<currency>{SALARY_CURRENCY_PATTERN})?\s*"
    r"(?P<first>\d[\d,]*(?:\.\d+)?)\s*(?P<first_unit>(?:k|lpa|lakhs?|crore|cr|million|m)(?![A-Za-z]))?"
    rf"(?:\s*(?:-|to|\u2013|\u2014)\s*(?P<second_currency>{SALARY_CURRENCY_PATTERN})?\s*(?P<second>\d[\d,]*(?:\.\d+)?)\s*(?P<second_unit>(?:k|lpa|lakhs?|crore|cr|million|m)(?![A-Za-z]))?)?"
    r"(?:\s*(?P<trailing_currency>(?:INR|USD|EUR|GBP|RUPEES?|RS)\b))?(?P<rupee_dash>\s*/-)?"
    r"\s*(?P<period>(?:per\s+annum|per\s+year|/year|/yr|a\s+year|yearly|annually|annual|annum|lpa"
    r"|per\s+month|/month|/mo|a\s+month|monthly|month|pm|per\s+hour|/hour|/hr|an\s+hour|hourly"
    r"|per\s+week|/week|/wk|a\s+week|weekly|per\s+day|/day|a\s+day|daily)(?![A-Za-z]))?",
    re.IGNORECASE,
)
# Whole-page text mentions funding, revenue and audience sizes; only pay wording may become salary evidence.
SALARY_CONTEXT_RE = re.compile(
    r"\b(?:salary|salaries|compensation|ctc|pay|paying|pays|package|stipend|remuneration|earnings?|wages?|ote)\b",
    re.IGNORECASE,
)
SALARY_CURRENCY_CODES = {"inr": "INR", "inr.": "INR", "rs": "INR", "rs.": "INR", "rs/-": "INR", "rupee": "INR", "rupees": "INR",
                         "\u20b9": "INR", "\u20a8": "INR", "\u00e2\u201a\u00b9": "INR", "usd": "USD", "$": "USD",
                         "eur": "EUR", "\u20ac": "EUR", "gbp": "GBP", "\u00a3": "GBP"}
SALARY_RUPEE_UNITS = {"lpa", "lakh", "lakhs", "crore", "cr"}
SALARY_VALUE_LIMIT = 10**12
SALARY_ANNUAL_MULTIPLIERS = {"year": 1, "month": 12, "week": 52, "day": 260, "hour": 2080}
SALARY_SCHEMA_PERIODS = {"year", "yearly", "annual", "annually", "month", "monthly", "week", "weekly",
                         "day", "daily", "hour", "hourly"}
OPPORTUNITY_OUTCOME_STATUSES = {"accepted", "rejected"}
OPPORTUNITY_OUTCOME_VALIDATION_CONTRACT = [
    "accepted_or_rejected_decision",
    "salary_range",
    "source_url",
    "location_match",
]
JOB_FEED_ADAPTERS = (
    {
        "name": "Remotive Jobs API",
        "method": "remotive_jobs",
        "source_url": "https://remotive.com/api/remote-jobs",
    },
    {
        "name": "Arbeitnow Job Board API",
        "method": "arbeitnow_jobs",
        "source_url": "https://www.arbeitnow.com/api/job-board-api",
    },
    {
        "name": "Remote OK API",
        "method": "remoteok_jobs",
        "source_url": "https://remoteok.com/api",
    },
)
JOB_PAGE_ADAPTERS = ("Generic JSON-LD", "Greenhouse", "Lever", "Workday", "Ashby")
SPECIALTY_SOURCE_CANDIDATES = (
    {
        "name": "Naukri",
        "source_url": "https://www.naukri.com/",
        "role_families": ["general", "data", "engineering", "finance", "product"],
        "countries": ["India"],
        "reason": "Broad India job-market coverage useful when configured feeds miss local role/geography samples.",
    },
    {
        "name": "Instahyre",
        "source_url": "https://www.instahyre.com/search-jobs/",
        "role_families": ["engineering", "data", "product", "finance"],
        "countries": ["India"],
        "reason": "India startup and MNC roles can expose salary-bearing tech and business openings by city.",
    },
    {
        "name": "Wellfound Jobs",
        "source_url": "https://wellfound.com/jobs",
        "role_families": ["engineering", "data", "product", "general"],
        "countries": ["Global", "Remote", "United States", "India"],
        "reason": "Startup roles often expose remote/local geography and salary or equity signals.",
    },
    {
        "name": "AI Jobs",
        "source_url": "https://aijobs.net/",
        "role_families": ["data", "engineering"],
        "countries": ["Global", "Remote"],
        "reason": "Specialized AI, ML, data-science, and big-data roles fill long-tail role-family gaps.",
    },
)


def career_source_coverage_summary() -> dict:
    return {
        "completion_status": "complete_current_scope",
        "configured_feed_count": len(JOB_FEED_ADAPTERS),
        "configured_feeds": [item["name"] for item in JOB_FEED_ADAPTERS],
        "minimum_feed_count": 3,
        "job_page_adapter_count": len(JOB_PAGE_ADAPTERS),
        "job_page_adapters": list(JOB_PAGE_ADAPTERS),
        "compensation_layers": [
            "direct role salary extraction",
            "salary-bearing live opening samples",
            "city/state/country salary-sample matching",
            "freshness-backed evidence contracts",
        ],
        "specialty_source_policy": "Specialty sources remain candidates only until a real user's role/geography request exposes a salary-bearing coverage gap.",
        "candidate_specialty_source_count": len(SPECIALTY_SOURCE_CANDIDATES),
        "candidate_specialty_sources": [
            {
                "name": item["name"],
                "source_url": item["source_url"],
                "role_families": item["role_families"],
                "countries": item["countries"],
                "reason": item["reason"],
            }
            for item in SPECIALTY_SOURCE_CANDIDATES
        ],
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
    employment_type: str = ""
    salary_min: float = 0.0
    salary_max: float = 0.0
    salary_currency: str = ""
    salary_period: str = ""
    source_kind: str = "job_page"


class JobIntelligenceService:
    USER_AGENT = "AlfredAI/1.0 (career-intelligence)"

    def parse_job_page(self, job_url: str) -> JobPostingSnapshot:
        response = public_http.request(
            "GET", job_url, headers={"User-Agent": self.USER_AGENT},
            content_types=("text/html", "application/xhtml+xml"), max_bytes=2_000_000,
        )
        job_url = public_http.normalized_link(job_url)
        soup = BeautifulSoup(response.content, "html.parser")
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

    def compare_resume_to_job(self, resume_payload: dict, job: JobPostingSnapshot, *, resume_source=None) -> dict:
        resume_skills = {item.strip().casefold() for item in (resume_payload.get("skills") or []) if isinstance(item, str) and item.strip()}
        required_skills = {item.strip().casefold() for item in job.required_skills if item.strip()}
        matched = sorted(skill.title() for skill in (resume_skills & required_skills))
        missing = sorted(skill.title() for skill in (required_skills - resume_skills))
        extra = sorted(skill.title() for skill in (resume_skills - required_skills))[:8]
        role = (resume_payload.get("role") or "").strip().lower()
        role_fit = 1.0 if role and role in job.title.lower() else (0.75 if role and any(token in job.title.lower() for token in role.split()) else 0.5)
        try:
            exp_years = float(resume_payload.get("experience_years"))
            experience_known = math.isfinite(exp_years) and exp_years >= 0
        except (TypeError, ValueError, OverflowError):
            exp_years, experience_known = 0, False
        if not experience_known:
            exp_years = 0
        exp_fit = 1.0 if not job.experience_years or exp_years >= job.experience_years else max(exp_years / max(job.experience_years, 1), 0)
        skill_fit = 0.55 if not required_skills else len(matched) / len(required_skills)
        fit_score = round(min(((skill_fit * 0.6) + (exp_fit * 0.25) + (role_fit * 0.15)) * 100, 99), 1)
        uncertainty = ["Rule-based overlap, not a hiring probability or independently verified proficiency.",
                       "Catalog extraction covers up to 20 listed terms, not all requirements.",
                       "Listed terms may be preferred or contextual; a missing term does not prove a missing skill."]
        available = bool(resume_skills and required_skills and role and role != "profile pending" and job.title and experience_known and math.isfinite(job.experience_years) and job.experience_years > 0)
        if not available:
            uncertainty.append("Role, skill or experience evidence is incomplete; overall fit is unavailable.")
        # shortcut: mixed/optional requirements need human review; do not infer their semantics.
        ambiguous = re.search(r"\b(?:not required|no experience|optional|preferred|nice.to.have)\b", job.description, re.I)
        conflicting = len({float(item.group(1)) for item in EXPERIENCE_RE.finditer(job.description)}) > 1
        if ambiguous or conflicting:
            available = False
            uncertainty.append("Optional, negated or conflicting requirements need review; overall fit is unavailable.")
        resume_source = resume_source or {"kind": "saved_fields", "label": "Saved resume/profile fields"}
        if resume_source.get("parser_status", "parsed") not in ("parsed", "user_declared"):
            available = False
            uncertainty.append("The selected resume extraction needs review; overall fit is unavailable.")
        if not available:
            fit_score = None
        strengths, gaps = [], []
        if matched:
            strengths.append(f"Matched skills: {', '.join(matched[:8])}.")
        if not (ambiguous or conflicting) and experience_known and job.experience_years > 0 and exp_fit >= 1:
            strengths.append("Experience level appears to meet or exceed the stated requirement.")
        elif not (ambiguous or conflicting) and experience_known and job.experience_years:
            gaps.append(f"Resume appears below the stated experience mark of {job.experience_years:.1f} years.")
        if missing:
            gaps.append(f"JD terms not listed in the saved resume/profile skills: {', '.join(missing[:8])}. Review whether they are requirements.")
        if extra:
            strengths.append(f"Other listed resume/profile skills: {', '.join(extra[:6])}.")
        if job.salary_min or job.salary_max:
            strengths.append("The role exposes a pay range, so Alfred can compare it against your current compensation more concretely.")
        if not strengths:
            strengths.append("No skill overlap established from the saved fields.")
        if not gaps:
            gaps.append("No additional listed-term gap extracted; manual review is still required." if available else "Insufficient evidence to assess overall gaps; review the saved sources.")
        return {
            "fit_score": fit_score,
            "score_status": "RULE_BASED" if available else "UNAVAILABLE",
            "uncertainty": uncertainty,
            "sources": [
                {**resume_source, "skills": sorted(item.title() for item in resume_skills), "role": role,
                 "experience_years": exp_years if experience_known else None},
                {"kind": job.source_kind, "label": job.title or job.source_name,
                 "skills": sorted(item.title() for item in required_skills), "experience_years": job.experience_years,
                 "excerpt": job.description[:4000]},
            ],
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
        unique_terms = []
        for term in [item.strip() for item in search_terms if item and item.strip()]:
            if term.lower() not in {existing.lower() for existing in unique_terms}:
                unique_terms.append(term)
        by_url, evidence_records, feed_queries = {}, [], []
        for term in unique_terms[:5]:
            for feed_result in self._live_job_feed_results(term):
                evidence_records.append(feed_result["evidence"])
                feed_queries.append({"term": term, "source_name": feed_result["source_name"]})
                for item in feed_result["payload"].get("jobs", []):
                    if not isinstance(item, dict) or not isinstance(item.get("title"), str) or not item["title"].strip():
                        continue
                    if any(item.get(key) is not None and not isinstance(item[key], str)
                           for key in ("company", "company_name", "location", "category", "salary", "publication_date")):
                        continue
                    url = public_http.normalized_link(item.get("url"))
                    if not url:
                        continue
                    url = urlparse(url)._replace(fragment="").geturl()
                    item = {**item, "_aggregator_name": feed_result["source_name"]}
                    item["url"] = url
                    tags = item.get("tags") or []
                    item["tags"] = [tag for tag in (tags if isinstance(tags, list) else [tags]) if isinstance(tag, str)][:8]
                    opening = self._normalize_opening(item, role=role, skills=skills, evidence=feed_result["evidence"])
                    if url not in by_url or (opening["verified_source"] and not by_url[url]["verified_source"]):
                        by_url[url] = opening
        jobs = list(by_url.values())
        evidence = self._combine_evidence(
            evidence_records,
            title="Multi-source live opening suggestions",
            source_name="Multiple verified job feeds",
            source_url=JOB_FEED_ADAPTERS[0]["source_url"],
            summary=f"Merged {len(jobs)} opening(s) across {len(unique_terms[:5])} search variant(s) and {len(JOB_FEED_ADAPTERS)} configured feed adapter(s).",
        )
        evidence["status"] = "fresh" if evidence["freshness"]["proof_complete"] else ("stale" if jobs else "failed")
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
            "source_evidence": evidence_records,
            "source_coverage": self._opening_source_coverage(
                jobs,
                filtered_jobs,
                unique_terms,
                evidence_records,
                feed_queries,
                role=role,
                country=country,
                state=state,
            ),
            "filters": self._opening_filter_metadata(jobs),
            "active_filters": {
                "country": country,
                "state": state,
            },
            "total_candidates": len(jobs),
            "filtered_candidates": len(filtered_jobs),
        }

    def _live_job_feed_results(self, term: str) -> list[dict]:
        results = []
        for adapter in JOB_FEED_ADAPTERS:
            method = getattr(verified_intelligence, adapter["method"])
            try:
                result = method(term)
            except (public_http.PublicHTTPError, ValueError, TypeError):
                result = InsightResult({}, {"status": "unavailable", "source_url": adapter["source_url"]}, False)
            payload = getattr(result, "payload", result if isinstance(result, dict) else {}) or {}
            evidence = getattr(result, "evidence", {}) or {}
            if not isinstance(evidence, dict):
                evidence = {}
            if not evidence:
                evidence = {
                    "title": f"{adapter['name']} job search for {term}",
                    "source_name": adapter["name"],
                    "source_url": adapter["source_url"],
                    "summary": "Feed returned payload without stored evidence metadata.",
                    "status": "unknown",
                    "fetched_at": "",
                    "verified_at": "",
                    "stale_after": "",
                    "query": term,
                }
            evidence = {**evidence, "source_name": adapter["name"],
                "source_url": public_http.normalized_link(evidence.get("source_url"))}
            if evidence["source_url"] != adapter["source_url"]:
                evidence.update(status="unknown", source_url="")
            evidence["status"] = self.opening_evidence_status(evidence)
            rows = payload.get("jobs", []) if isinstance(payload, dict) else []
            results.append({"source_name": adapter["name"], "payload": {"jobs": rows[:10] if isinstance(rows, list) else []}, "evidence": evidence})
        return results

    def opening_evidence_status(self, evidence: dict) -> str:
        if not isinstance(evidence, dict):
            return "unknown"
        if evidence.get("status") not in {"fresh", "stale"}:
            return "unavailable" if evidence.get("status") in {"failed", "unavailable"} else "unknown"
        try:
            verified = datetime.fromisoformat(evidence.get("verified_at", "").replace("Z", "+00:00"))
            expires = datetime.fromisoformat(evidence.get("stale_after", "").replace("Z", "+00:00"))
        except (ValueError, TypeError, AttributeError):
            return "unknown"
        if (timezone.is_naive(verified) or timezone.is_naive(expires) or verified > timezone.now()
                or expires <= verified or public_http.normalized_link(evidence.get("source_url")) not in {a["source_url"] for a in JOB_FEED_ADAPTERS}):
            return "unknown"
        return "fresh" if evidence["status"] == "fresh" and expires > timezone.now() else "stale"

    def _normalize_opening(self, item: dict, *, role: str, skills: list[str], evidence: dict) -> dict:
        company = item.get("company") or item.get("company_name") or ""
        location = str(item.get("location") or "")
        location_meta = self._location_hierarchy(location)
        relevance = self._opening_relevance(role, skills, item)
        salary_signal = self._salary_signal_payload(item.get("salary", ""))
        aggregator_name = item.get("_aggregator_name") or evidence.get("source_name", "Verified opening source") or "Verified opening source"
        tags = item.get("tags", []) or []
        if isinstance(tags, str):
            tags = [tags]
        source_status = self.opening_evidence_status(evidence)
        return {
            "title": item.get("title", ""),
            "company": company,
            "location": location,
            "country": location_meta["country"],
            "state": location_meta["state"],
            "city": location_meta["city"],
            "is_remote": location_meta["is_remote"],
            "is_worldwide": bool(re.fullmatch(r"(?:remote[\s,/-]*)?(?:worldwide|global|anywhere)(?:[\s,/-]*remote)?", location.strip(), re.IGNORECASE)),
            "category": item.get("category", ""),
            "url": item.get("url", ""),
            "publication_date": item.get("publication_date") or "",
            "salary": item.get("salary", ""),
            "salary_signal": salary_signal,
            "tags": tags[:8],
            "portal_name": aggregator_name,
            "portal_url": evidence.get("source_url", ""),
            "portal_family": self._portal_family(item.get("url", "")),
            "portal_host": urlparse(item.get("url", "")).netloc.replace("www.", ""),
            "aggregator_name": aggregator_name,
            "verified_source": source_status == "fresh",
            "source_status": source_status,
            "source_evidence": evidence,
            "verified_at": evidence.get("verified_at", ""),
            "relevance_score": relevance["score"],
            "match_reasons": relevance["reasons"],
        }

    def _salary_signal_payload(self, salary_text: str) -> dict:
        salary = self._parse_salary_text(salary_text)
        if not salary:
            return {"available": False}
        annual_min, annual_max = self._annualize_salary_range(salary["salary_min"], salary["salary_max"], salary["period"])
        return {
            "available": bool(annual_min or annual_max),
            "raw": salary_text,
            "salary_min_annual": annual_min,
            "salary_max_annual": annual_max,
            "currency": salary["currency"],
            "period": salary["period"],
            "period_stated": salary["period_stated"],
        }

    def _opening_source_coverage(
        self,
        openings: list[dict],
        filtered_jobs: list[dict],
        used_terms: list[str],
        evidence_records: list[dict],
        feed_queries: list[dict] | None = None,
        *,
        role: str = "",
        country: str = "",
        state: str = "",
    ) -> dict:
        statuses = sorted({str(item.get("status") or "") for item in evidence_records if isinstance(item, dict) and item.get("status")})
        portal_families = sorted({item.get("portal_family", "") for item in openings if item.get("portal_family")})
        countries = sorted({item.get("country", "") for item in openings if item.get("country")})
        salary_bearing = [item for item in openings if item.get("salary_signal", {}).get("available")]
        source_names = self._evidence_source_names(evidence_records)
        active_feed_names = sorted(
            {
                item.get("source_name", "")
                for item in evidence_records
                if isinstance(item, dict) and item.get("source_name") and item.get("status", "fresh") in {"fresh", "stale"}
            }
        )
        source_candidate_counts = {}
        source_salary_counts = {}
        for item in openings:
            source = item.get("aggregator_name") or item.get("portal_name") or "Unknown"
            source_candidate_counts[source] = source_candidate_counts.get(source, 0) + 1
            if item.get("salary_signal", {}).get("available"):
                source_salary_counts[source] = source_salary_counts.get(source, 0) + 1
        return {
            "configured_feeds": [item["name"] for item in JOB_FEED_ADAPTERS],
            "configured_feed_count": len(JOB_FEED_ADAPTERS),
            "live_feed_count": len(active_feed_names),
            "source_names": source_names,
            "query_variants": used_terms[:6],
            "feed_queries": (feed_queries or [])[:12],
            "source_statuses": statuses,
            "source_status_by_feed": {
                item.get("source_name", ""): item.get("status", "")
                for item in evidence_records
                if isinstance(item, dict) and item.get("source_name")
            },
            "portal_families": portal_families,
            "countries_seen": countries,
            "salary_bearing_candidates": len(salary_bearing),
            "filtered_salary_bearing_candidates": len([item for item in filtered_jobs if item.get("salary_signal", {}).get("available")]),
            "source_candidate_counts": source_candidate_counts,
            "source_salary_counts": source_salary_counts,
            "specialty_source_gap_policy": self._specialty_source_gap_policy(
                role,
                country,
                state,
                openings,
                filtered_jobs,
                used_terms,
                evidence_records,
            ),
            "coverage_complete": len(active_feed_names) >= len(JOB_FEED_ADAPTERS),
        }

    def _specialty_source_gap_policy(
        self,
        role: str,
        country: str,
        state: str,
        openings: list[dict],
        filtered_jobs: list[dict],
        used_terms: list[str],
        evidence_records: list[dict],
    ) -> dict:
        role_family = self._role_family(role)
        requested_country = self._normalize_country(country)
        requested_state = str(state or "").strip()
        salary_bearing = [item for item in openings if item.get("salary_signal", {}).get("available")]
        filtered_salary_bearing = [item for item in filtered_jobs if item.get("salary_signal", {}).get("available")]
        reasons = []
        if requested_country or requested_state:
            location_label = ", ".join(part for part in [requested_state, requested_country] if part)
            if not filtered_jobs:
                reasons.append(f"No live opening candidates matched {location_label or 'the requested geography'}.")
            elif not filtered_salary_bearing:
                reasons.append(f"No salary-bearing live opening matched {location_label or 'the requested geography'}.")
        elif not salary_bearing:
            reasons.append("No salary-bearing live opening appeared for the requested role family.")
        if evidence_records and not any(item.get("status", "fresh") in {"fresh", "stale"} for item in evidence_records if isinstance(item, dict)):
            reasons.append("Configured job-feed evidence did not return a usable freshness status.")

        gap_exposed = bool(reasons)
        recommended_sources = self._candidate_specialty_sources(role_family, requested_country) if gap_exposed else []
        return {
            "gap_exposed": gap_exposed,
            "policy": "candidate_only_until_connector_or_adapter_is_added" if gap_exposed else "core_feeds_sufficient_for_current_role_geography",
            "source_addition_allowed": gap_exposed,
            "requested_role": role,
            "role_family": role_family,
            "requested_country": requested_country,
            "requested_state": requested_state,
            "query_variants": used_terms[:6],
            "salary_bearing_candidates": len(salary_bearing),
            "filtered_salary_bearing_candidates": len(filtered_salary_bearing),
            "filtered_candidates": len(filtered_jobs),
            "gap_basis": reasons,
            "recommended_sources": recommended_sources,
        }

    def _candidate_specialty_sources(self, role_family: str, requested_country: str) -> list[dict]:
        candidates = []
        for item in SPECIALTY_SOURCE_CANDIDATES:
            family_match = role_family in item["role_families"] or "general" in item["role_families"]
            country_match = (
                not requested_country
                or requested_country in item["countries"]
                or "Global" in item["countries"]
                or (requested_country == "Remote" and "Remote" in item["countries"])
            )
            if family_match and country_match:
                candidates.append(
                    {
                        "name": item["name"],
                        "source_url": item["source_url"],
                        "role_families": item["role_families"],
                        "countries": item["countries"],
                        "reason": item["reason"],
                    }
                )
        return candidates[:4]

    def _role_family(self, role: str) -> str:
        normalized = str(role or "").lower()
        if any(token in normalized for token in ("data", "analyst", "analytics", "scientist", "machine learning", "ml", "ai", "bi")):
            return "data"
        if any(token in normalized for token in ("engineer", "developer", "frontend", "backend", "full stack", "software", "devops", "platform")):
            return "engineering"
        if "product" in normalized or "program manager" in normalized:
            return "product"
        if any(token in normalized for token in ("finance", "risk", "accounting", "fp&a", "financial")):
            return "finance"
        return "general"

    def _opening_relevance(self, role: str, skills: list[str], opening: dict) -> dict:
        title = str(opening.get("title", "") or "").lower()
        category = str(opening.get("category", "") or "").lower()
        raw_tags = opening.get("tags") or []
        if isinstance(raw_tags, str):
            raw_tags = [raw_tags]
        tags = {str(item).lower() for item in raw_tags if item}
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
        if self._location_hierarchy(opening.get("location", ""))["is_remote"]:
            score += 4
            reasons.append("Remote work is mentioned; check geographic eligibility.")
        return {"score": round(min(score, 99), 1), "reasons": reasons[:3]}

    def _opening_matches_location(self, opening: dict, *, country: str = "", state: str = "") -> bool:
        normalized_country = self._normalize_country(country)
        normalized_state = str(state or "").strip().lower()
        if normalized_country and normalized_country != "Remote":
            if not opening.get("is_worldwide") and self._normalize_country(opening.get("country", "")) != normalized_country:
                return False
        if normalized_country == "Remote":
            return bool(opening.get("is_remote"))
        if normalized_state:
            opening_state = str(opening.get("state", "") or "").strip().lower()
            return opening_state == normalized_state
        return True

    def _opening_filter_metadata(self, openings: list[dict]) -> dict:
        countries = sorted({item.get("country", "") for item in openings if item.get("country")})
        if any(item.get("is_remote") for item in openings) and "Remote" not in countries:
            countries.append("Remote")
            countries.sort()
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
        is_remote = bool(re.search(r"\b(remote|worldwide|global|anywhere)\b", normalized)) and not bool(re.search(r"\b(?:not|non|no)[ -]+remote\b", normalized))
        parts = [re.sub(r"\b(?:remote|only)\b", "", item, flags=re.IGNORECASE).strip()
                 for item in re.split(r"[,/|()·-]", raw) if item.strip()]
        city = ""
        state = ""
        country = ""
        countries = set()
        states = set()
        for part in parts:
            lowered = part.lower()
            if lowered in COUNTRY_ALIASES and COUNTRY_ALIASES[lowered] != "Remote":
                country = COUNTRY_ALIASES[lowered]
                countries.add(country)
                continue
            if lowered in STATE_TO_COUNTRY:
                state = part.title()
                states.add(state)
                country = country or STATE_TO_COUNTRY[lowered]
                countries.add(STATE_TO_COUNTRY[lowered])
                continue
            if lowered in CITY_TO_STATE_COUNTRY:
                city = part.title()
                mapped_state, mapped_country = CITY_TO_STATE_COUNTRY[lowered]
                states.add(mapped_state)
                state = state or mapped_state
                country = country or mapped_country
                countries.add(mapped_country)
        if not city:
            for city_name, (mapped_state, mapped_country) in CITY_TO_STATE_COUNTRY.items():
                if re.search(r"\b" + re.escape(city_name) + r"\b", normalized):
                    city = city_name.title()
                    states.add(mapped_state)
                    state = state or mapped_state
                    country = country or mapped_country
                    countries.add(mapped_country)
                    break
        # Composite/negative restrictions need review, not a guessed eligible country.
        if len(countries) > 1 or len(states) > 1 or re.search(r"\b(?:except|excluding|outside|not in)\b", normalized):
            country, state, city = "", "", ""
        elif not country and is_remote:
            country = "Remote"
        return {"country": country, "state": state, "city": city, "is_remote": is_remote}

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
        openings_evidence: dict | list[dict] | None = None,
        current_income_annual: float = 0.0,
    ) -> dict:
        observations = []
        evidence = self._normalize_evidence_collection(openings_evidence)
        if job_snapshot and (job_snapshot.salary_min or job_snapshot.salary_max):
            now = timezone.now()
            annual_min, annual_max = self._annualize_salary_range(job_snapshot.salary_min, job_snapshot.salary_max, job_snapshot.salary_period)
            location_meta = self._location_hierarchy(job_snapshot.location)
            observations.append(
                {
                    "source": job_snapshot.source_name,
                    "location": job_snapshot.location,
                    "country": location_meta["country"],
                    "state": location_meta["state"],
                    "city": location_meta["city"],
                    "is_remote": location_meta["is_remote"],
                    "salary_min_annual": annual_min,
                    "salary_max_annual": annual_max,
                    "currency": job_snapshot.salary_currency or "",
                    "period_stated": bool(job_snapshot.salary_period),
                    "url": job_snapshot.job_url,
                    "source_kind": job_snapshot.source_kind,
                    "feed_source": job_snapshot.source_name,
                }
            )
            evidence.append(
                {
                    "title": "Direct role compensation signal",
                    "source_name": job_snapshot.source_name,
                    "source_url": job_snapshot.job_url,
                    "summary": f"Salary signal extracted from the current {job_snapshot.source_kind.replace('_', ' ')}.",
                    "status": "fresh",
                    "fetched_at": now.isoformat(),
                    "verified_at": now.isoformat(),
                    "stale_after": (now + timedelta(hours=24)).isoformat(),
                    "query": role,
                    "notes": "Compensation was read directly from the active role text or JSON-LD when the page exposed it.",
                }
            )
        for opening in openings or []:
            salary = self._parse_salary_text(opening.get("salary", ""))
            if not salary:
                continue
            annual_min, annual_max = self._annualize_salary_range(salary["salary_min"], salary["salary_max"], salary["period"])
            location_meta = self._location_hierarchy(opening.get("location", ""))
            observations.append(
                {
                    "source": opening.get("company") or "Opening",
                    "location": opening.get("location", ""),
                    "country": opening.get("country") or location_meta["country"],
                    "state": opening.get("state") or location_meta["state"],
                    "city": opening.get("city") or location_meta["city"],
                    "is_remote": bool(opening.get("is_remote") or location_meta["is_remote"]),
                    "salary_min_annual": annual_min,
                    "salary_max_annual": annual_max,
                    "currency": salary["currency"],
                    "period_stated": salary["period_stated"],
                    "url": opening.get("url", ""),
                    "source_kind": "live_opening",
                    "feed_source": opening.get("aggregator_name") or opening.get("portal_name") or "Live opening",
                }
            )
        if not observations:
            geography_scope = self._salary_geography_scope(location, observations, [], fallback_to_global=False)
            evidence_contract = self._compensation_evidence_contract(observations, [], evidence, fallback_to_global=False, requested_location=location)
            return {
                "available": False,
                "summary": "No salary-bearing evidence is available from the current parsed role or configured job feeds.",
                "sample_count": 0,
                "evidence": evidence,
                "location_scope": location or "Global / Remote",
                "geography_scope": geography_scope,
                "salary_observations": [],
                "evidence_contract": evidence_contract,
            }
        filtered = [
            item for item in observations
            if self._salary_location_matches(item, location)
        ]
        located = filtered or observations
        fallback_to_global = bool(location and not filtered and observations)
        currency, selected = self._salary_currency_cohort(located)
        excluded_currency_count = len(located) - len(selected)
        if not selected:
            return {
                "available": False,
                "summary": "Salary evidence is split evenly across currencies; amounts are not converted, so no benchmark is shown.",
                "sample_count": 0,
                "evidence": evidence,
                "location_scope": location or "Global / Remote",
                "geography_scope": self._salary_geography_scope(location, observations, [], fallback_to_global=fallback_to_global),
                "salary_observations": [],
                "evidence_contract": self._compensation_evidence_contract(
                    observations, [], evidence, fallback_to_global=fallback_to_global,
                    requested_location=location, currency_scope=located),
            }
        mins = [item["salary_min_annual"] for item in selected if item["salary_min_annual"]]
        maxes = [item["salary_max_annual"] for item in selected if item["salary_max_annual"]]
        benchmark_min = round(median(mins), 2) if mins else 0.0
        benchmark_max = round(median(maxes), 2) if maxes else benchmark_min
        benchmark_mid = round((benchmark_min + benchmark_max) / 2, 2) if benchmark_max else benchmark_min
        comparison = None
        if current_income_annual and currency == "INR":
            if current_income_annual < benchmark_min:
                comparison = "below_benchmark"
            elif benchmark_max and current_income_annual > benchmark_max:
                comparison = "above_benchmark"
            else:
                comparison = "within_benchmark"
        evidence_contract = self._compensation_evidence_contract(observations, selected, evidence, fallback_to_global=fallback_to_global, requested_location=location, currency_scope=located)
        summary = (
            f"Compensation benchmark is evidence-backed from {len(selected)} salary-bearing opening signal(s) "
            f"across {evidence_contract['selected_source_count']} source(s)."
        )
        if comparison == "below_benchmark":
            summary += " Your current annualized income sits below the current benchmark band."
        elif comparison == "above_benchmark":
            summary += " Your current annualized income is above the current benchmark band."
        elif comparison == "within_benchmark":
            summary += " Your current annualized income sits inside the current benchmark band."
        elif current_income_annual:
            summary += " This benchmark is not in rupees, so your income was not compared with it."
        if excluded_currency_count:
            summary += f" {excluded_currency_count} signal(s) in another or unstated currency were excluded and not converted."
        if evidence_contract["assumed_period_count"]:
            summary += f" {evidence_contract['assumed_period_count']} signal(s) did not state a pay period and were treated as annual."
        return {
            "available": True,
            "summary": summary,
            "sample_count": len(selected),
            "market_min_annual": benchmark_min,
            "market_max_annual": benchmark_max,
            "market_mid_annual": benchmark_mid,
            "currency": currency,
            "location_scope": location or "Global / Remote",
            "comparison": comparison,
            "current_income_annual": round(current_income_annual or 0, 2),
            "geography_scope": self._salary_geography_scope(location, observations, selected, fallback_to_global=fallback_to_global),
            "salary_observations": [
                {
                    "source": item.get("source", ""),
                    "location": item.get("location", ""),
                    "salary_min_annual": item.get("salary_min_annual", 0),
                    "salary_max_annual": item.get("salary_max_annual", 0),
                    "currency": item.get("currency", ""),
                    "url": item.get("url", ""),
                    "source_kind": item.get("source_kind", ""),
                    "feed_source": item.get("feed_source", ""),
                    "country": item.get("country", ""),
                    "state": item.get("state", ""),
                    "city": item.get("city", ""),
                }
                for item in selected[:6]
            ],
            "evidence_contract": evidence_contract,
            "evidence": evidence[:6],
        }

    def normalize_opportunity_outcome(self, analysis, payload: dict) -> dict:
        if not isinstance(payload, dict):
            raise ValueError("Outcome payload must be an object.")
        outcome = str(payload.get("outcome") or payload.get("status") or "").strip().lower()
        if outcome not in OPPORTUNITY_OUTCOME_STATUSES:
            raise ValueError("Outcome must be accepted or rejected.")

        analysis_payload = getattr(analysis, "extracted_payload", {}) or {}
        snapshot = analysis_payload.get("job_snapshot", {}) if isinstance(analysis_payload, dict) else {}
        salary_text = str(payload.get("salary_text") or payload.get("salary") or "").strip()
        parsed_salary = self._parse_salary_text(salary_text) if salary_text else None
        if salary_text and not parsed_salary and not all(payload.get(key) not in (None,'') for key in ('salary_min','salary_max')):
            raise ValueError('Provide numeric salary evidence or leave salary text blank.')

        period = (
            payload.get("salary_period")
            or payload.get("period")
            or (parsed_salary or {}).get("period")
            or snapshot.get("salary_period")
            or "year"
        )
        if not isinstance(period,str) or period.strip().lower() not in {
                'year','yearly','annual','annually','per year','/year','month','monthly','per month','/month','pm',
                'hour','hourly','per hour','/hour','lpa'}:
            raise ValueError('Choose a supported salary period: year, month or hour.')
        salary_unit = payload.get("salary_unit") or payload.get("salary_scale") or self._salary_unit_hint(str(period))
        salary_min = self._outcome_salary_value(payload.get("salary_min"), salary_unit)
        salary_max = self._outcome_salary_value(payload.get("salary_max"), salary_unit)
        if parsed_salary and not salary_min:
            salary_min = float(parsed_salary.get("salary_min") or 0)
        if parsed_salary and not salary_max:
            salary_max = float(parsed_salary.get("salary_max") or 0)
        if not salary_min:
            salary_min = float(snapshot.get("salary_min") or 0)
        if not salary_max:
            salary_max = float(snapshot.get("salary_max") or salary_min or 0)
        if not salary_min and salary_max:
            salary_min = salary_max
        if not salary_max and salary_min:
            salary_max = salary_min
        salary_min,salary_max=(float(profile_money(value)) for value in (salary_min,salary_max))
        if salary_max < salary_min:
            raise ValueError('Salary maximum must not be below salary minimum.')

        normalized_period = self._normalize_salary_period(str(period))
        annual_min, annual_max = self._annualize_salary_range(salary_min, salary_max, normalized_period)
        annual_min,annual_max=(float(profile_money(value)) for value in (annual_min,annual_max))
        if not annual_min and not annual_max:
            raise ValueError("Accepted or rejected opportunities must include salary evidence before they count toward outcome learning.")

        source_url = str(
            payload.get("source_url")
            or snapshot.get("source_url")
            or snapshot.get("job_url")
            or getattr(analysis, "job_url", "")
            or ""
        ).strip()
        parsed_source_url = urlparse(source_url)
        if (parsed_source_url.scheme not in {"http", "https"} or not parsed_source_url.netloc
                or parsed_source_url.username or parsed_source_url.password):
            raise ValueError("Accepted or rejected opportunities must include a valid source URL before they count toward outcome learning.")

        now = timezone.now()
        decided_at=payload.get('decided_at')
        if decided_at is None or decided_at=='': decided_at=timezone.localdate(now).isoformat()
        try:
            valid_date=isinstance(decided_at,str) and date.fromisoformat(decided_at).isoformat()==decided_at
        except ValueError:
            valid_date=False
        if not valid_date:
            raise ValueError('Decision date must be a valid ISO date.')
        location = str(payload.get("location") or getattr(analysis, "location", "") or snapshot.get("location", "") or "").strip()
        if not location:
            location = ", ".join(
                part
                for part in [
                    str(payload.get("city") or snapshot.get("city") or "").strip(),
                    str(payload.get("state") or snapshot.get("state") or "").strip(),
                    str(payload.get("country") or snapshot.get("country") or "").strip(),
                ]
                if part
            )
        if not location:
            raise ValueError("Accepted or rejected opportunities must include a location before they count toward outcome learning.")
        location_meta = self._location_hierarchy(location)
        currency = (
            payload.get("salary_currency")
            or payload.get("currency")
            or (parsed_salary or {}).get("currency")
            or snapshot.get("salary_currency")
            or "INR"
        )
        return {
            "outcome": outcome,
            "salary_bearing": True,
            "salary_min": round(salary_min, 2),
            "salary_max": round(salary_max, 2),
            "salary_currency": str(currency).upper(),
            "salary_period": normalized_period,
            "salary_min_annual": annual_min,
            "salary_max_annual": annual_max,
            "salary_mid_annual": float(expense_money((Decimal(str(annual_min)) + Decimal(str(annual_max))) / 2)),
            "salary_text": salary_text,
            "decided_at": decided_at,
            "verification": "owner_reported",
            "recorded_at": now.isoformat(),
            "source_kind": str(payload.get("source_kind") or snapshot.get("source_kind") or "manual_outcome"),
            "source_url": source_url,
            "apply_url": str(payload.get("apply_url") or getattr(analysis, "apply_url", "") or ""),
            "company": str(payload.get("company") or getattr(analysis, "company", "") or snapshot.get("company", "") or ""),
            "job_title": str(payload.get("job_title") or payload.get("title") or getattr(analysis, "job_title", "") or snapshot.get("title", "") or ""),
            "location": location,
            "country": location_meta["country"],
            "state": location_meta["state"],
            "city": location_meta["city"],
            "notes": str(payload.get("notes") or "").strip()[:1200],
            "rejection_reason": str(payload.get("rejection_reason") or "").strip()[:600],
        }

    def opportunity_outcome_contract_status(self, item: dict | None) -> dict:
        item = item if isinstance(item, dict) else {}
        has_salary = bool(item.get("salary_bearing") and (item.get("salary_min_annual") or item.get("salary_max_annual")))
        has_decision = item.get("outcome") in OPPORTUNITY_OUTCOME_STATUSES
        has_source = bool(str(item.get("source_url") or "").strip())
        has_location = bool(
            str(item.get("location") or "").strip()
            or str(item.get("city") or "").strip()
            or str(item.get("state") or "").strip()
            or str(item.get("country") or "").strip()
        )
        fields = {
            "accepted_or_rejected_decision": has_decision,
            "salary_range": has_salary,
            "source_url": has_source,
            "location_match": has_location,
        }
        missing = [key for key in OPPORTUNITY_OUTCOME_VALIDATION_CONTRACT if not fields[key]]
        return {
            "valid": not missing,
            "fields": fields,
            "missing": missing,
        }

    def opportunity_outcome_learning_summary(self, analyses) -> dict:
        outcomes = []
        for analysis in analyses:
            payload = getattr(analysis, "extracted_payload", {}) or {}
            outcome = payload.get("opportunity_outcome") if isinstance(payload, dict) else None
            if isinstance(outcome, dict):
                outcomes.append(outcome)

        def has_valid_outcome_contract(item: dict) -> bool:
            return self.opportunity_outcome_contract_status(item)["valid"]

        salary_bearing = [item for item in outcomes if has_valid_outcome_contract(item)]
        accepted = [item for item in salary_bearing if item.get("outcome") == "accepted"]
        rejected = [item for item in salary_bearing if item.get("outcome") == "rejected"]
        source_urls = sorted({str(item.get("source_url") or "") for item in salary_bearing if item.get("source_url")})
        geography_counts = {}
        for item in salary_bearing:
            location_key = ", ".join(part for part in [item.get("city", ""), item.get("state", ""), item.get("country", "")] if part) or item.get("location") or "Unknown"
            geography_counts[location_key] = geography_counts.get(location_key, 0) + 1

        minimum_salary_bearing = 8
        minimum_accepted = 3
        minimum_rejected = 3
        remaining_salary_bearing = max(minimum_salary_bearing - len(salary_bearing), 0)
        remaining_accepted = max(minimum_accepted - len(accepted), 0)
        remaining_rejected = max(minimum_rejected - len(rejected), 0)
        maturity_ready = (
            remaining_salary_bearing == 0
            and remaining_accepted == 0
            and remaining_rejected == 0
        )
        if maturity_ready:
            maturity_status = "mature"
            blocker = "Accepted/rejected salary-bearing outcome coverage is mature for the current scope."
        elif salary_bearing:
            maturity_status = "collecting"
            blocker = (
                f"Need {remaining_salary_bearing} more salary-bearing outcome(s), "
                f"{remaining_accepted} more accepted outcome(s), and "
                f"{remaining_rejected} more rejected outcome(s)."
            )
        else:
            maturity_status = "not_started"
            blocker = "No accepted or rejected salary-bearing opportunity outcome has been recorded yet."

        return {
            "maturity_status": maturity_status,
            "outcome_count": len(outcomes),
            "salary_bearing_outcome_count": len(salary_bearing),
            "validated_outcome_count": len(salary_bearing),
            "unvalidated_outcome_count": max(len(outcomes) - len(salary_bearing), 0),
            "accepted_count": len(accepted),
            "rejected_count": len(rejected),
            "minimum_salary_bearing_outcomes": minimum_salary_bearing,
            "minimum_accepted_outcomes": minimum_accepted,
            "minimum_rejected_outcomes": minimum_rejected,
            "remaining_salary_bearing_outcomes": remaining_salary_bearing,
            "remaining_accepted_outcomes": remaining_accepted,
            "remaining_rejected_outcomes": remaining_rejected,
            "maturity_ready": maturity_ready,
            "accepted_salary_mid_median": self._median_salary_mid(accepted),
            "rejected_salary_mid_median": self._median_salary_mid(rejected),
            "source_count": len(source_urls),
            "source_urls": source_urls[:8],
            "geography_counts": dict(sorted(geography_counts.items())),
            "validation_contract": OPPORTUNITY_OUTCOME_VALIDATION_CONTRACT,
            "blocker": blocker,
            "summary": (
                f"{len(salary_bearing)} salary-bearing accepted/rejected outcome(s) recorded "
                f"across {len(source_urls)} source URL(s)."
            ),
        }

    def _normalize_evidence_collection(self, evidence: dict | list[dict] | None) -> list[dict]:
        if not evidence:
            return []
        if isinstance(evidence, dict):
            return [evidence]
        return [item for item in evidence if isinstance(item, dict)]

    def _compensation_evidence_contract(
        self,
        observations: list[dict],
        selected: list[dict],
        evidence: list[dict],
        *,
        fallback_to_global: bool,
        requested_location: str,
        currency_scope: list[dict] | None = None,
    ) -> dict:
        freshness = freshness_snapshot(evidence)
        currency_scope = selected if currency_scope is None else currency_scope
        selected_sources = sorted({item.get("feed_source") or item.get("source", "") for item in selected if item.get("feed_source") or item.get("source")})
        selected_locations = sorted({item.get("location", "") for item in selected if item.get("location")})[:8]
        source_names = self._evidence_source_names(evidence)
        source_urls = self._evidence_source_urls(evidence)
        return {
            "observed_salary_count": len(observations),
            "selected_salary_count": len(selected),
            "selected_source_count": len(selected_sources),
            "selected_sources": selected_sources,
            "selected_locations": selected_locations,
            "evidence_count": len(evidence),
            "source_names": source_names,
            "source_urls": source_urls,
            "fallback_to_global": fallback_to_global,
            "geo_match_level": self._salary_geo_match_level(requested_location, selected, fallback_to_global=fallback_to_global),
            "salary_evidence_density": self._salary_evidence_density(len(selected), len(selected_sources)),
            "currency_breakdown": self._salary_currency_breakdown(currency_scope),
            "mixed_currency": len(self._salary_currency_breakdown(currency_scope)) > 1,
            "excluded_currency_count": len(currency_scope) - len(selected),
            "assumed_period_count": sum(1 for item in selected if not item.get("period_stated")),
            "annualization_basis": "Monthly x12, weekly x52, daily x260 and hourly x2080; no currency conversion.",
            "freshness": freshness,
            "proof_complete": bool(selected and source_names and freshness.get("proof_complete")),
        }

    def _salary_geo_match_level(self, requested_location: str, selected: list[dict], *, fallback_to_global: bool) -> str:
        if not selected:
            return "missing"
        if fallback_to_global:
            return "global_fallback"
        requested = self._location_hierarchy(requested_location)
        if requested["city"] and any(item.get("city") == requested["city"] for item in selected):
            return "city"
        if requested["state"] and any(item.get("state") == requested["state"] for item in selected):
            return "state"
        if requested["country"] and any(item.get("country") == requested["country"] for item in selected):
            return "country"
        if any(item.get("is_remote") for item in selected):
            return "remote"
        return "global"

    def _salary_evidence_density(self, selected_count: int, source_count: int) -> str:
        if selected_count >= 5 and source_count >= 2:
            return "strong"
        if selected_count >= 2:
            return "usable"
        if selected_count == 1:
            return "thin"
        return "missing"

    def _salary_currency_breakdown(self, selected: list[dict]) -> dict:
        counts = {}
        for item in selected:
            currency = item.get("currency") or "Unknown"
            counts[currency] = counts.get(currency, 0) + 1
        return counts

    def _salary_currency_cohort(self, observations: list[dict]) -> tuple[str, list[dict]]:
        # Amounts are never converted: the band uses one currency, and an even split abstains.
        counts = self._salary_currency_breakdown([item for item in observations if item.get("currency")])
        if not counts:
            return "", observations
        ranked = sorted(counts.items(), key=lambda entry: entry[1], reverse=True)
        if len(ranked) > 1 and ranked[0][1] == ranked[1][1]:
            return "", []
        return ranked[0][0], [item for item in observations if item.get("currency") == ranked[0][0]]

    def _salary_location_matches(self, observation: dict, requested_location: str) -> bool:
        requested = str(requested_location or "").strip()
        if not requested:
            return True
        requested_meta = self._location_hierarchy(requested)
        observation_location = str(observation.get("location", "") or "").lower()
        if requested.lower() in observation_location or observation.get("is_remote"):
            return True
        if requested_meta["country"] and observation.get("country") == requested_meta["country"]:
            if not requested_meta["state"] or observation.get("state") == requested_meta["state"]:
                return True
        if requested_meta["state"] and observation.get("state") == requested_meta["state"]:
            return True
        if requested_meta["city"] and observation.get("city") == requested_meta["city"]:
            return True
        return False

    def _salary_geography_scope(self, requested_location: str, observations: list[dict], selected: list[dict], *, fallback_to_global: bool) -> dict:
        requested_meta = self._location_hierarchy(requested_location)
        return {
            "requested_location": requested_location or "Global / Remote",
            "requested_country": requested_meta["country"],
            "requested_state": requested_meta["state"],
            "requested_city": requested_meta["city"],
            "matched_sample_count": len(selected),
            "observed_locations": sorted({item.get("location", "") for item in observations if item.get("location")})[:8],
            "fallback_to_global": fallback_to_global,
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
        return extract_skill_terms(text, JOB_SKILLS)

    def _extract_experience(self, text: str) -> float:
        matches = [float(item.group(1)) for item in EXPERIENCE_RE.finditer(text)]
        return max((value for value in matches if math.isfinite(value)), default=0.0)

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
        salary = self._extract_salary_from_json_ld(ld_json) or self._parse_salary_text(text, require_context=True)
        if salary:
            return salary["salary_min"], salary["salary_max"], salary["currency"], salary["period"] if salary["period_stated"] else ""
        return 0.0, 0.0, "", ""

    def _extract_salary_from_json_ld(self, ld_json: dict) -> dict | None:
        if not isinstance(ld_json, dict):
            return None
        base_salary = ld_json.get("baseSalary")
        if not isinstance(base_salary, dict):
            return None
        raw_currency = base_salary.get("currency")
        currency = raw_currency.strip().upper() if isinstance(raw_currency, str) else ""
        if not re.fullmatch(r"[A-Z]{3}", currency):
            currency = ""
        value = base_salary.get("value")
        unit_text = ""
        if isinstance(value, dict):
            unit_text = str(value.get("unitText") or "").strip().lower()
            first = self._json_salary_number(value.get("minValue")) or self._json_salary_number(value.get("value"))
            second = self._json_salary_number(value.get("maxValue")) or first
        else:
            first = second = self._json_salary_number(value)
        if not first and not second:
            return None
        if unit_text and unit_text not in SALARY_SCHEMA_PERIODS:
            return None
        first = first or second
        return {"salary_min": min(first, second), "salary_max": max(first, second), "currency": currency,
                "period": self._normalize_salary_period(unit_text), "period_stated": bool(unit_text)}

    def _json_salary_number(self, raw_value) -> float:
        if isinstance(raw_value, bool) or not isinstance(raw_value, (int, float, str)):
            return 0.0
        try:
            value = Decimal(str(raw_value).replace(",", "").strip())
        except DecimalException:
            return 0.0
        return float(value) if value.is_finite() and 0 < value <= SALARY_VALUE_LIMIT else 0.0

    def _outcome_salary_value(self, raw_value, unit: str | None) -> float:
        if raw_value is None or raw_value == "":
            return 0.0
        try:
            if isinstance(raw_value,bool) or len(str(raw_value))>128 or (unit is not None and not isinstance(unit,str)):
                raise ValueError()
            value=profile_money(self._salary_value(str(raw_value),unit))
            if value<=0:
                raise ValueError()
            return float(value)
        except (TypeError, ValueError):
            raise ValueError('Provide finite positive salary evidence in cents within the supported range.') from None

    def _parse_salary_text(self, text: str, *, require_context: bool = False) -> dict | None:
        for match in SALARY_BLOCK_RE.finditer(text or ""):
            units = {(match.group(name) or "").lower() for name in ("first_unit", "second_unit")} - {""}
            currencies = {SALARY_CURRENCY_CODES[raw.strip().lower()]
                          for raw in (match.group(name) for name in ("currency", "second_currency", "trailing_currency")) if raw}
            rupee_dash = bool(match.group("rupee_dash"))
            if not currencies and not units and not rupee_dash:
                continue
            if len(currencies) > 1 or (require_context and not self._salary_match_has_context(text, match)):
                continue
            fallback_unit = self._salary_unit_hint(match.group("period") or "")
            shared_unit = match.group("first_unit") or match.group("second_unit") or fallback_unit
            first_value = self._salary_value(match.group("first"), match.group("first_unit") or shared_unit)
            second_value = self._salary_value(match.group("second"), match.group("second_unit") or shared_unit) if match.group("second") else first_value
            if not first_value and not second_value:
                continue
            if max(first_value, second_value) > SALARY_VALUE_LIMIT:
                continue
            currency = next(iter(currencies), "INR" if rupee_dash or units & SALARY_RUPEE_UNITS else "")
            period = self._normalize_salary_period(match.group("period") or match.group("first_unit") or "")
            salary_min = min(first_value, second_value) if second_value else first_value
            salary_max = max(first_value, second_value) if second_value else first_value
            return {"salary_min": salary_min, "salary_max": salary_max, "currency": currency, "period": period,
                    "period_stated": bool(match.group("period")) or "lpa" in units}
        return None

    def _salary_match_has_context(self, text: str, match) -> bool:
        units = {(match.group(name) or "").lower() for name in ("first_unit", "second_unit")}
        if match.group("period") or "lpa" in units:
            return True
        before = re.split(r"[.!?;\n]\s", text[max(0, match.start() - 60):match.start()])[-1]
        after = re.split(r"[.!?;\n]", text[match.end():match.end() + 24])[0]
        return bool(SALARY_CONTEXT_RE.search(before) or SALARY_CONTEXT_RE.search(after))

    def _salary_value(self, raw_value: str | None, unit: str | None) -> float:
        if not raw_value:
            return 0.0
        multipliers={'k':1000,'lpa':100000,'lakh':100000,'lakhs':100000,
                     'crore':10000000,'cr':10000000,'million':1000000,'m':1000000}
        normalized=(unit or '').lower()
        if normalized and normalized not in multipliers:
            raise ValueError('Choose a supported salary unit.')
        try:
            return float(Decimal(str(raw_value).replace(',','')) * multipliers.get(normalized,1))
        except DecimalException:
            raise ValueError('Invalid salary number.') from None

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
        if any(token in normalized for token in ("month", "/mo", "pm")):
            return "month"
        if any(token in normalized for token in ("hour", "/hr")):
            return "hour"
        if any(token in normalized for token in ("week", "/wk")):
            return "week"
        if any(token in normalized for token in ("day", "daily")):
            return "day"
        return "year"

    def _annualize_salary_range(self, salary_min: float, salary_max: float, period: str) -> tuple[float, float]:
        multiplier = SALARY_ANNUAL_MULTIPLIERS.get((period or "year").lower(), 1)
        return (money_float(Decimal(str(salary_min or 0))*multiplier),
                money_float(Decimal(str(salary_max or salary_min or 0))*multiplier))

    def _median_salary_mid(self, outcomes: list[dict]) -> float:
        # Reported outcomes are never converted, so a mixed-currency median is not meaningful.
        if len({item.get("salary_currency") or "" for item in outcomes}) > 1:
            return 0.0
        mids = [float(item.get("salary_mid_annual") or 0) for item in outcomes if item.get("salary_mid_annual")]
        return round(median(mids), 2) if mids else 0.0

    def _combine_evidence(self, items: list[dict], *, title: str, source_name: str, source_url: str, summary: str) -> dict:
        normalized_items = [item for item in items if item]
        first = normalized_items[0] if normalized_items else {}
        notes = " | ".join(item.get("notes", "") for item in normalized_items if item.get("notes"))[:600]
        source_names = self._evidence_source_names(normalized_items) or [source_name]
        source_urls = self._evidence_source_urls(normalized_items) or [source_url]
        return {
            "title": title,
            "source_name": source_name,
            "source_url": source_url,
            "source_names": source_names,
            "source_urls": source_urls,
            "source_count": len(source_names),
            "summary": summary,
            "status": first.get("status", "fresh"),
            "fetched_at": first.get("fetched_at", ""),
            "verified_at": first.get("verified_at", ""),
            "stale_after": first.get("stale_after", ""),
            "query": ", ".join(filter(None, [item.get("query", "") for item in normalized_items][:3])),
            "notes": notes,
            "freshness": freshness_snapshot(normalized_items),
        }

    def _evidence_source_names(self, evidence: list[dict]) -> list[str]:
        names = set()
        for item in evidence:
            if not isinstance(item, dict):
                continue
            for source_name in item.get("source_names", []) or []:
                if source_name:
                    names.add(str(source_name))
            if item.get("source_name"):
                names.add(str(item["source_name"]))
        return sorted(names)

    def _evidence_source_urls(self, evidence: list[dict]) -> list[str]:
        urls = set()
        for item in evidence:
            if not isinstance(item, dict):
                continue
            for source_url in item.get("source_urls", []) or []:
                if source_url:
                    urls.add(str(source_url))
            if item.get("source_url"):
                urls.add(str(item["source_url"]))
        return sorted(urls)

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
        raw = document_source(upload)
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


def career_opportunity_outcome_summary(analyses) -> dict:
    return job_intelligence.opportunity_outcome_learning_summary(analyses)
