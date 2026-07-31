from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.utils import timezone

from .income_intelligence import build_employment_income_signals
from apps.ml_engine.inference_adapters.salary_predictor import MODEL_PATH, salary_predictor
from apps.ml_engine.models import AdaptiveModelState


CITY_TIER_SCORES = {
    "mumbai": 1.0,
    "bangalore": 0.95,
    "bengaluru": 0.95,
    "delhi": 0.92,
    "gurgaon": 0.9,
    "noida": 0.88,
    "pune": 0.86,
    "hyderabad": 0.83,
    "chennai": 0.82,
    "kolkata": 0.78,
}


def build_salary_projection(user, profile, *, macro: dict, latest_resume=None, overrides: dict | None = None, income_signals: dict | None = None) -> dict:
    inputs = build_projection_inputs(
        user,
        profile,
        latest_resume=latest_resume,
        overrides=overrides,
        income_signals=income_signals,
    )
    model_runtime = resolve_salary_model_runtime(user, inputs)
    growth_context = build_growth_context(macro=macro, inputs=inputs)

    base_income = (
        model_runtime["predicted_monthly_income"]
        if model_runtime["available"]
        else inputs["current_income"]
    )
    yearly_multiplier = 1 + growth_context["annual_growth"]
    projections = []
    for year in range(1, 6):
        if model_runtime["available"]:
            projected_income = base_income * (yearly_multiplier ** year)
        else:
            projected_income = inputs["current_income"] * (yearly_multiplier ** year)
        inflation = growth_context["inflation"]
        projections.append(
            {
                "year": year,
                "projected_income": round(projected_income, 2),
                "real_income_estimate": round(projected_income / ((1 + (inflation / 100)) ** year), 2) if inflation else round(projected_income, 2),
            }
        )

    projection_mode = "hybrid_model_backed" if model_runtime["available"] else "heuristic"
    projection_method = (
        "Year 1 and the outer-year path are anchored to the trained salary predictor baseline, while growth still extends through the transparent heuristic rule."
        if model_runtime["available"]
        else "No trained salary predictor is active in the live path, so the projection is fully heuristic."
    )
    insights = [
        (
            f"Projection is using a model-backed salary anchor of INR {round(model_runtime['predicted_monthly_income'], 2):,.2f} "
            "before applying the transparent outer-year growth rule."
            if model_runtime["available"]
            else f"Projection uses a heuristic annual growth rate of {growth_context['annual_growth'] * 100:.1f}% because no live salary model anchor is available."
        ),
        f"Latest tracked India unemployment signal is {growth_context['unemployment']} and inflation is {growth_context['inflation']}.",
        "Resume and job-match data can sharpen the heuristic growth inputs even when the salary-model anchor is unavailable.",
    ]
    if growth_context["market_return"] < -5:
        insights.append("Recent market weakness can tighten hiring budgets. Keep a stronger interview and savings buffer.")
    elif growth_context["market_return"] > 5:
        insights.append("Risk appetite in the market looks better than average, which can support role-switch timing.")
    reasoning = build_projection_reasoning(
        model_runtime=model_runtime,
        inputs=inputs,
        growth_context=growth_context,
        macro=macro,
    )

    return {
        "current_income": inputs["current_income"],
        "projections": projections,
        "projection_mode": projection_mode,
        "projection_method": projection_method,
        "projection_basis": {
            "annual_growth_rate": round(growth_context["annual_growth"] * 100, 2),
            "skills_count": len(inputs["skills"]),
            "experience_years": inputs["experience_years"],
            "macro_drag": round(growth_context["macro_drag"] * 100, 2),
            "baseline_source": "salary_predictor_model" if model_runtime["available"] else "reported_income",
            "baseline_monthly_income": round(base_income, 2),
            "reported_current_income": round(inputs["current_income"], 2),
            "reported_income_mode": inputs["income_signals"]["reported_income"]["mode"],
            "annualized_compensation": round(inputs["income_signals"]["annualized_compensation"], 2),
            "current_employer": inputs["income_signals"]["current_employer"],
            "model_predicted_income": round(model_runtime["predicted_monthly_income"], 2) if model_runtime["available"] else None,
        },
        "macro_context": macro["payload"],
        "evidence": macro["evidence"],
        "income_signals": inputs["income_signals"],
        "insights": insights[:5],
        "reasoning": reasoning,
        "explainability_note": "Each reason below is tied to either the live salary-model baseline, explicit profile inputs, or verified macro evidence. It is not a confidence interval.",
        "projection_confidence": build_projection_confidence(
            model_runtime=model_runtime,
            inputs=inputs,
            macro=macro,
        ),
    }


def build_projection_inputs(user, profile, *, latest_resume=None, overrides: dict | None = None, income_signals: dict | None = None) -> dict:
    overrides = overrides or {}
    resume_payload = (latest_resume.extracted_payload or {}) if latest_resume and latest_resume.parser_status == "parsed" else {}
    profile_skills = [item.strip() for item in (profile.skills or "").split(",") if item.strip()]
    resume_skills = [str(item).strip() for item in (resume_payload.get("skills") or []) if str(item).strip()]
    skills = overrides.get("skills")
    if skills is None:
        skills = resume_skills or profile_skills

    resolved_income_signals = income_signals or build_employment_income_signals(
        user=user,
        latest_resume=latest_resume,
        profile=profile,
    )
    current_income = float(
        overrides.get(
            "monthly_income",
            resolved_income_signals.get("monthly_cash_income")
            or getattr(user, "monthly_income", 0)
            or profile.last_salary
            or 0,
        )
        or 0
    )
    variable_income = float(overrides.get("variable_income", getattr(user, "variable_income", 0) or 0) or 0)
    return {
        "current_income": current_income,
        "variable_income": variable_income,
        "rent_or_emi": float(overrides.get("rent_or_emi", getattr(user, "rent_or_emi", 0) or 0) or 0),
        "city": str(overrides.get("city", getattr(user, "city", "") or "") or ""),
        "experience_years": float(overrides.get("experience_years", profile.experience_years or 0) or 0),
        "skills": [str(item).strip() for item in skills if str(item).strip()],
        "account_age_days": max((timezone.now() - getattr(user, "created_at", timezone.now())).days, 0),
        "resume_used": bool(resume_skills and skills == resume_skills),
        "income_signals": resolved_income_signals,
    }


def build_growth_context(*, macro: dict, inputs: dict) -> dict:
    unemployment = float(macro["payload"]["unemployment"].get("latest_value") or 0)
    inflation = float(macro["payload"]["inflation"].get("latest_value") or 0)
    market_return = float(macro["payload"]["market"].get("one_month_return_pct") or 0)

    skills_score = min(len(inputs["skills"]) * 0.004, 0.02)
    experience_score = 0.012 if 2 <= inputs["experience_years"] <= 8 else (0.008 if inputs["experience_years"] > 8 else 0.004)
    macro_drag = max(unemployment - 5, 0) * 0.003 + max(inflation - 6, 0) * 0.002
    market_signal = 0.003 if market_return > 2 else (-0.003 if market_return < -5 else 0)
    annual_growth = min(max(0.07 + skills_score + experience_score + market_signal - macro_drag, 0.03), 0.16)

    return {
        "annual_growth": annual_growth,
        "skills_score": skills_score,
        "experience_score": experience_score,
        "macro_drag": macro_drag,
        "unemployment": unemployment,
        "inflation": inflation,
        "market_return": market_return,
    }


def resolve_salary_model_runtime(user, inputs: dict) -> dict:
    state = AdaptiveModelState.objects.filter(model_key="salary_predictor").first()
    state_payload = {
        "available": False,
        "status": "missing",
        "is_fresh": False,
        "quality_score": 0.0,
        "confidence_estimate": 0.0,
        "sample_count": 0,
        "artifact_path": "",
        "last_finished_at": None,
        "next_refresh_due_at": None,
        "inference_ready": False,
        "inference_reason": "no_model_state",
    }
    if state is None:
        return {"available": False, "predicted_monthly_income": None, "state": state_payload}

    artifact_path = resolve_artifact_path(state.artifact_path or MODEL_PATH)
    state_payload = {
        "available": state.status == "ready",
        "status": state.status,
        "is_fresh": state.is_fresh,
        "quality_score": round(float(state.quality_score or 0), 2),
        "confidence_estimate": round(float(state.confidence_estimate or 0), 2),
        "sample_count": int(state.sample_count or 0),
        "artifact_path": str(artifact_path),
        "last_finished_at": state.last_finished_at.isoformat() if state.last_finished_at else None,
        "next_refresh_due_at": state.next_refresh_due_at.isoformat() if state.next_refresh_due_at else None,
        "inference_ready": False,
        "inference_reason": "state_not_ready",
    }
    if state.status != "ready":
        return {"available": False, "predicted_monthly_income": None, "state": state_payload}
    if not artifact_path.exists():
        state_payload["inference_reason"] = "artifact_missing"
        return {"available": False, "predicted_monthly_income": None, "state": state_payload}

    feature_vector = {
        "variable_income": inputs["variable_income"],
        "rent_or_emi": inputs["rent_or_emi"],
        "city_tier_score": CITY_TIER_SCORES.get(inputs["city"].lower(), 0.75),
        "income_variability_ratio": inputs["variable_income"] / max(inputs["current_income"], 1),
        "account_age_days": inputs["account_age_days"],
    }
    try:
        prediction = salary_predictor.predict(
            feature_vector,
            model_path=str(artifact_path),
            force_reload=getattr(salary_predictor, "_loaded_from", None) != str(artifact_path),
        )
    except Exception:
        state_payload["inference_reason"] = "load_or_predict_failed"
        return {"available": False, "predicted_monthly_income": None, "state": state_payload}

    if prediction <= 0:
        state_payload["inference_reason"] = "invalid_prediction"
        return {"available": False, "predicted_monthly_income": None, "state": state_payload}

    state_payload["inference_ready"] = True
    state_payload["inference_reason"] = "ok"
    return {
        "available": True,
        "predicted_monthly_income": round(float(prediction), 2),
        "state": state_payload,
    }


def build_projection_confidence(*, model_runtime: dict, inputs: dict, macro: dict) -> dict:
    support = {
        "income_present": bool(inputs["current_income"] > 0),
        "skills_count": len(inputs["skills"]),
        "resume_used": bool(inputs["resume_used"]),
        "macro_evidence_count": len(macro.get("evidence") or []),
    }
    model_payload = model_runtime["state"]
    if model_runtime["available"]:
        freshness_note = "fresh" if model_payload["is_fresh"] else "stale"
        return {
            "status": "model_backed_baseline",
            "score": round(float(model_payload["confidence_estimate"] or 0), 1),
            "label": "Model-backed baseline confidence",
            "summary": (
                f"Confidence applies only to the trained salary-model baseline used to anchor the projection start point "
                f"({freshness_note}, {model_payload['sample_count']} samples)."
            ),
            "method": "This score comes from the stored salary predictor training state. It is not a confidence interval for the full five-year trajectory.",
            "model": model_payload,
            "support": support,
        }

    reason = model_payload.get("inference_reason") or model_payload.get("status") or "unavailable"
    return {
        "status": "unavailable",
        "score": None,
        "label": "Heuristic projection",
        "summary": f"Projection remains heuristic because no live salary-model baseline is available ({reason}).",
        "method": "No prediction confidence score is attached because the current five-year path is heuristic.",
        "model": model_payload,
        "support": support,
    }


def build_projection_reasoning(*, model_runtime: dict, inputs: dict, growth_context: dict, macro: dict) -> list[dict]:
    model_payload = model_runtime["state"]
    reasoning = [
        {
            "label": "Baseline source",
            "detail": (
                f"Salary predictor baseline is active at INR {model_runtime['predicted_monthly_income']:,.2f} per month."
                if model_runtime["available"]
                else f"Reported monthly income of INR {inputs['current_income']:,.2f} is being used because no live salary-model baseline is available."
            ),
            "source": "salary_model" if model_runtime["available"] else "reported_income",
        },
        {
            "label": "Skills contribution",
            "detail": f"{len(inputs['skills'])} tracked skill(s) contribute about {growth_context['skills_score'] * 100:.1f} percentage points to annual growth.",
            "source": "profile_and_resume",
        },
        {
            "label": "Experience contribution",
            "detail": f"{inputs['experience_years']:.1f} years of experience contribute about {growth_context['experience_score'] * 100:.1f} percentage points to annual growth.",
            "source": "career_profile",
        },
        {
            "label": "Macro pressure",
            "detail": f"Verified macro drag is {growth_context['macro_drag'] * 100:.1f} points from unemployment {growth_context['unemployment']:.2f} and inflation {growth_context['inflation']:.2f}.",
            "source": "verified_macro_context",
        },
        {
            "label": "Market signal",
            "detail": f"Recent market return of {growth_context['market_return']:.2f}% adjusts the annual growth rule to {growth_context['annual_growth'] * 100:.2f}%.",
            "source": "verified_market_context",
        },
    ]
    if model_runtime["available"]:
        reasoning.append(
            {
                "label": "Model evidence",
                "detail": (
                    f"The stored salary model is {model_payload['status']} with confidence {model_payload['confidence_estimate']:.1f}/100, "
                    f"quality {model_payload['quality_score']:.1f}/100, and {model_payload['sample_count']} training samples."
                ),
                "source": "model_training_state",
            }
        )
    evidence_count = len(macro.get("evidence") or [])
    reasoning.append(
        {
            "label": "Evidence coverage",
            "detail": f"{evidence_count} verified evidence record(s) are attached to the current macro snapshot.",
            "source": "evidence_cache",
        }
    )
    return reasoning


def build_projection_simulation(*, user, profile, macro: dict, latest_resume=None, overrides: dict) -> dict:
    baseline = build_salary_projection(user, profile, macro=macro, latest_resume=latest_resume)
    scenario = build_salary_projection(user, profile, macro=macro, latest_resume=latest_resume, overrides=overrides)
    baseline_year_1 = baseline["projections"][0]["projected_income"] if baseline["projections"] else 0.0
    baseline_year_5 = baseline["projections"][-1]["projected_income"] if baseline["projections"] else 0.0
    scenario_year_1 = scenario["projections"][0]["projected_income"] if scenario["projections"] else 0.0
    scenario_year_5 = scenario["projections"][-1]["projected_income"] if scenario["projections"] else 0.0

    return {
        "baseline": baseline,
        "scenario": scenario,
        "delta": {
            "year_1_projected_income": round(scenario_year_1 - baseline_year_1, 2),
            "year_5_projected_income": round(scenario_year_5 - baseline_year_5, 2),
            "baseline_mode": baseline["projection_mode"],
            "scenario_mode": scenario["projection_mode"],
        },
        "assumptions": {
            "macro_context_locked": True,
            "macro_source": "Current verified macro snapshot",
            "overridden_fields": sorted(overrides.keys()),
            "baseline_method": baseline["projection_method"],
            "scenario_method": scenario["projection_method"],
            "explainability_note": "Baseline and scenario reasoning are returned separately so users can see exactly which inputs changed the outcome.",
        },
    }


def resolve_artifact_path(raw_path: str) -> Path:
    candidate = Path(raw_path or MODEL_PATH)
    if not candidate.is_absolute():
        candidate = Path(settings.BASE_DIR) / candidate
    return candidate
