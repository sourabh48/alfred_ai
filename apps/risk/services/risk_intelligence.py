from __future__ import annotations

from statistics import mean

from django.db.models import Sum

from apps.behavioral.models import BehavioralSignal
from apps.career.models import CareerJobAnalysis, CareerProfile
from apps.career.services import job_intelligence
from apps.expenses.models import BankAccount
from apps.family.models import Dependent
from apps.integrations.services import verified_intelligence
from apps.integrations.services.verified_intelligence import freshness_snapshot
from apps.loans.models import Loan
from apps.mobility.services import bike_service_intelligence
from apps.risk.models import RiskSignal

RISK_NEWS_QUERIES = {
    "financial": "India inflation fuel prices EMI interest rates cost of living",
    "health": "India workplace stress burnout health news",
    "relocation": "India rent prices relocation cost of living cities",
    "mobility": "India two wheeler recall road safety fuel prices maintenance",
}


def _clamp(value: float, lower: float = 0.0, upper: float = 100.0) -> float:
    return max(lower, min(upper, value))


def _level(score: float) -> str:
    if score >= 75:
        return "critical"
    if score >= 55:
        return "high"
    if score >= 35:
        return "guarded"
    return "low"


def _trend(values: list[float]) -> str:
    if len(values) < 4:
        return "stable"
    midpoint = len(values) // 2
    recent = mean(values[:midpoint])
    older = mean(values[midpoint:])
    delta = recent - older
    if delta >= 5:
        return "rising"
    if delta <= -5:
        return "falling"
    return "stable"


def _dedupe_evidence(items: list[dict]) -> list[dict]:
    seen = set()
    result = []
    for item in items:
        if not item:
            continue
        key = (item.get("source_url", ""), item.get("verified_at", ""), item.get("title", ""))
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


class RiskIntelligenceService:
    def build_outlook(self, user) -> dict:
        history = list(
            RiskSignal.objects.filter(user=user)
            .only("id", "layoff_risk", "illness_risk", "relocation_risk", "timestamp")
            .order_by("-timestamp", "-id")[:12]
        )
        latest = history[0] if history else None
        profile = CareerProfile.objects.filter(user=user).only("role").first()
        latest_job_analysis = (
            CareerJobAnalysis.objects.filter(user=user)
            .only("fit_score", "company", "created_at")
            .order_by("-created_at", "-id")
            .first()
        )
        role = (profile.role if profile and profile.role and profile.role != "Profile pending" else "") or "analyst"
        career_market = job_intelligence.market_outlook(role, getattr(latest_job_analysis, "company", ""))
        macro = career_market["macro_context"]

        unemployment = macro["unemployment"].get("latest_value") or 0
        inflation = macro["inflation"].get("latest_value") or 0
        market = macro["market"]
        market_return = market.get("one_month_return_pct") or 0
        market_volatility = market.get("india_vix") or market.get("realized_volatility_pct") or 0

        manual_layoff = float(latest.layoff_risk) if latest else 0.0
        manual_illness = float(latest.illness_risk) if latest else 0.0
        manual_relocation = float(latest.relocation_risk) if latest else 0.0

        recent_behavior = list(BehavioralSignal.objects.filter(user=user).order_by("-timestamp").values_list("stress_score", "sleep_hours", "work_hours")[:7])
        avg_stress = mean(row[0] for row in recent_behavior) if recent_behavior else 0.0
        avg_sleep = mean(row[1] for row in recent_behavior) if recent_behavior else 0.0
        avg_work = mean(row[2] for row in recent_behavior) if recent_behavior else 0.0

        liquid_cash = (
            BankAccount.objects.filter(user=user, is_active=True)
            .exclude(account_type="credit")
            .aggregate(total=Sum("current_balance"))
            .get("total")
            or 0.0
        )
        monthly_emi = Loan.objects.filter(user=user, is_active=True).aggregate(total=Sum("emi")).get("total") or 0.0
        dependents = Dependent.objects.filter(user=user).count()
        monthly_income = getattr(user, "monthly_income", 0) or 0.0
        rent_or_emi = getattr(user, "rent_or_emi", 0) or 0.0
        debt_burden = ((monthly_emi + rent_or_emi) / monthly_income * 100) if monthly_income else 0.0
        emergency_months = (liquid_cash / max(monthly_emi + rent_or_emi, 1)) if (monthly_emi + rent_or_emi) else 0.0

        mobility = bike_service_intelligence.risk_snapshot(user)
        mobility_summary = mobility.get("summary", {})
        mobility_risk = _clamp(
            (mobility_summary.get("critical_faults", 0) * 18)
            + (mobility_summary.get("expired_documents", 0) * 18)
            + (mobility_summary.get("expiring_documents", 0) * 8)
            + max(0, 65 - (mobility_summary.get("latest_condition_score") or 0)) * 0.5
        )

        fit_gap = max(0.0, 100.0 - float(getattr(latest_job_analysis, "fit_score", 0) or 0)) if latest_job_analysis else 24.0

        career_score = _clamp(
            (manual_layoff * 0.35)
            + (career_market["risk_score"] * 0.45)
            + (fit_gap * 0.15)
            + (4 if market_return < -4 else 0)
        )
        health_score = _clamp(
            (manual_illness * 0.45)
            + (avg_stress * 5.5)
            + (max(0, 6 - avg_sleep) * 8)
            + (max(0, avg_work - 9) * 3)
            + (max(0, inflation - 6) * 1.8)
        )
        financial_score = _clamp(
            (debt_burden * 0.7)
            + (18 if emergency_months < 1 else (10 if emergency_months < 3 else 0))
            + (dependents * 3.5)
            + (max(0, unemployment - 5) * 2.8)
        )
        relocation_score = _clamp(
            (manual_relocation * 0.45)
            + (max(0, debt_burden - 35) * 0.6)
            + (6 if inflation >= 6 else 0)
            + (6 if market_volatility >= 20 else 0)
        )

        career_values = [float(item.layoff_risk) for item in history]
        health_values = [float(item.illness_risk) for item in history]
        relocation_values = [float(item.relocation_risk) for item in history]
        financial_values = [((float(item.layoff_risk) + float(item.relocation_risk)) / 2) for item in history]

        consolidated = [
            {
                "key": "career",
                "label": "Career / Layoff",
                "score": round(career_score, 1),
                "level": _level(career_score),
                "trend": _trend(career_values),
                "note": "Role-level job market, layoffs, and fit-gap pressure combined with your latest layoff snapshot.",
                "drivers": [
                    f"Manual layoff snapshot {manual_layoff:.0f}/100",
                    f"External market risk {career_market['risk_score']:.0f}/100",
                    f"Job-fit gap {fit_gap:.0f}/100" if latest_job_analysis else "No latest job-fit analysis yet",
                ],
            },
            {
                "key": "financial",
                "label": "Financial Pressure",
                "score": round(financial_score, 1),
                "level": _level(financial_score),
                "trend": _trend(financial_values),
                "note": "Debt burden, liquid runway, dependents, and macro labor pressure.",
                "drivers": [
                    f"Debt burden {debt_burden:.1f}% of income" if monthly_income else "Income not set",
                    f"Emergency runway {emergency_months:.1f} months",
                    f"Dependents {dependents}",
                ],
            },
            {
                "key": "health",
                "label": "Health / Burnout",
                "score": round(health_score, 1),
                "level": _level(health_score),
                "trend": _trend(health_values),
                "note": "Illness risk blended with behavioral stress, sleep, workload, and inflation pressure.",
                "drivers": [
                    f"Manual illness snapshot {manual_illness:.0f}/100",
                    f"Average stress {avg_stress:.1f}/10",
                    f"Average sleep {avg_sleep:.1f}h",
                ],
            },
            {
                "key": "relocation",
                "label": "Relocation / Cost Shift",
                "score": round(relocation_score, 1),
                "level": _level(relocation_score),
                "trend": _trend(relocation_values),
                "note": "Relocation pressure blended with rent burden, inflation, and market volatility.",
                "drivers": [
                    f"Manual relocation snapshot {manual_relocation:.0f}/100",
                    f"Rent plus EMI burden {debt_burden:.1f}%",
                    f"Inflation {inflation}",
                ],
            },
            {
                "key": "mobility",
                "label": "Mobility / Vehicle Readiness",
                "score": round(mobility_risk, 1),
                "level": _level(mobility_risk),
                "trend": "stable",
                "note": "Vehicle faults, expired documents, and condition score from the service dashboard.",
                "drivers": [
                    f"Critical faults {mobility_summary.get('critical_faults', 0)}",
                    f"Expired documents {mobility_summary.get('expired_documents', 0)}",
                    f"Condition score {mobility_summary.get('latest_condition_score', 0)}/100",
                ],
            },
        ]

        action_items = self._build_actions(consolidated, career_market, mobility, latest_job_analysis)
        related_news, extra_evidence = self._build_related_news(consolidated, career_market)
        evidence = _dedupe_evidence([*career_market["evidence"], *extra_evidence])

        top = max(consolidated, key=lambda item: item["score"]) if consolidated else None
        overall_average = round(mean(item["score"] for item in consolidated), 1) if consolidated else 0.0

        return {
            "history": history,
            "latest": latest,
            "outlook": {
                "layoff": round(career_score, 1),
                "illness": round(health_score, 1),
                "relocation": round(relocation_score, 1),
                "average": overall_average,
            },
            "summary": {
                "highest_label": top["label"] if top else "No data",
                "highest_score": top["score"] if top else 0,
                "overall_average": overall_average,
                "news_count": len(related_news),
                "action_count": len(action_items),
            },
            "macro_context": macro,
            "consolidated_risks": consolidated,
            "related_news": related_news,
            "action_items": action_items,
            "module_signals": {
                "career_market_risk": round(career_market["risk_score"], 1),
                "job_fit_score": round(float(getattr(latest_job_analysis, "fit_score", 0) or 0), 1) if latest_job_analysis else None,
                "debt_burden_pct": round(debt_burden, 1),
                "emergency_months": round(emergency_months, 1),
                "average_stress": round(avg_stress, 1),
                "average_sleep": round(avg_sleep, 1),
                "mobility_document_compliance": mobility_summary.get("document_compliance_score", 0),
                "mobility_condition_score": mobility_summary.get("latest_condition_score", 0),
            },
            "insights": self._build_insights(consolidated, career_market, monthly_income, liquid_cash),
            "evidence": evidence,
            "evidence_freshness": freshness_snapshot(evidence),
        }

    def _build_actions(self, consolidated: list[dict], career_market: dict, mobility: dict, latest_job_analysis) -> list[dict]:
        actions = []
        for item in sorted(consolidated, key=lambda value: value["score"], reverse=True):
            if item["key"] == "career" and item["score"] >= 55:
                actions.append(
                    {
                        "title": "Tighten career runway",
                        "priority": item["level"],
                        "note": "Refresh the resume, apply to active openings, and use the job-match view to close missing-skill gaps.",
                    }
                )
            if item["key"] == "financial" and item["score"] >= 55:
                actions.append(
                    {
                        "title": "Increase financial buffer",
                        "priority": item["level"],
                        "note": "Reduce optional spend and target at least 3 months of liquid runway against rent and EMI load.",
                    }
                )
            if item["key"] == "health" and item["score"] >= 55:
                actions.append(
                    {
                        "title": "Reduce burnout pressure",
                        "priority": item["level"],
                        "note": "Use lower-risk decision windows, protect sleep, and avoid large commitments during high-stress periods.",
                    }
                )
            if item["key"] == "mobility" and item["score"] >= 35:
                pending = mobility.get("pending_tasks", [])
                if pending:
                    actions.append(
                        {
                            "title": "Close vehicle readiness gaps",
                            "priority": item["level"],
                            "note": pending[0]["note"],
                        }
                    )
        if latest_job_analysis and getattr(latest_job_analysis, "fit_score", 0) < 70:
            actions.append(
                {
                    "title": "Close job-fit gaps",
                    "priority": "guarded",
                    "note": "The latest analyzed role is below a 70/100 fit. Address the missing skills before prioritizing that role.",
                }
            )
        return actions[:6]

    def _build_related_news(self, consolidated: list[dict], career_market: dict) -> tuple[list[dict], list[dict]]:
        news = []
        evidence = []
        for bucket, items in (("Layoff", career_market.get("layoff_news", [])), ("Hiring", career_market.get("job_market_news", []))):
            for item in items[:8]:
                news.append(
                    {
                        "bucket": bucket,
                        "title": item.get("title", ""),
                        "link": item.get("link", ""),
                        "published": item.get("published", ""),
                        "source": item.get("source", ""),
                    }
                )
        extra_categories = [
            item for item in sorted(consolidated, key=lambda value: value["score"], reverse=True)
            if item["key"] in RISK_NEWS_QUERIES and item["score"] >= 35
        ][:2]
        for item in extra_categories:
            result = verified_intelligence.google_news_search(RISK_NEWS_QUERIES[item["key"]])
            evidence.append(result.evidence)
            for article in result.payload.get("items", [])[:4]:
                news.append(
                    {
                        "bucket": item["label"],
                        "title": article.get("title", ""),
                        "link": article.get("link", ""),
                        "published": article.get("published", ""),
                        "source": article.get("source", ""),
                    }
                )

        deduped_news = []
        seen = set()
        for item in news:
            key = item.get("link", "") or f"{item.get('bucket', '')}:{item.get('title', '')}"
            if key in seen:
                continue
            seen.add(key)
            deduped_news.append(item)
        return deduped_news[:12], evidence

    def _build_insights(self, consolidated: list[dict], career_market: dict, monthly_income: float, liquid_cash: float) -> list[str]:
        insights = []
        top = max(consolidated, key=lambda item: item["score"]) if consolidated else None
        if top:
            insights.append(f"Highest consolidated risk is {top['label'].lower()} at {top['score']:.0f}/100.")
        if monthly_income and liquid_cash < monthly_income * 2:
            insights.append("Liquid cash is below roughly two months of income, which weakens your shock absorption.")
        insights.extend(career_market.get("insights", [])[:2])
        if not insights:
            insights.append("Risk signals are currently balanced, but keep logging snapshots so Alfred can adapt the baseline.")
        return insights[:6]


risk_intelligence = RiskIntelligenceService()
