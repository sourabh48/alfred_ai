from __future__ import annotations

from dataclasses import dataclass

from apps.expenses.services.financial_intelligence import resolve_canonical_financial_baseline
from apps.integrations.services import verified_intelligence
from apps.integrations.services.verified_intelligence import freshness_snapshot
from apps.ml_engine.inference_adapters.relationship_model import relationship_model_predictor
from apps.relationship.models import RelationshipProfile


@dataclass
class RelationshipAlignment:
    payload: dict


def build_relationship_alignment(user) -> RelationshipAlignment:
    baseline = resolve_canonical_financial_baseline(user)
    profile = RelationshipProfile.objects.filter(user=user).order_by("-id").first()
    if not profile:
        return RelationshipAlignment(
            {
                "alignment_score": 0,
                "compatibility": "Unknown",
                "message": "No relationship profile found. Create one to unlock alignment, planning pressure, and shared-finance guidance.",
                "insights": ["Add a partner profile so Alfred can compare household planning signals."],
                "factors": [],
                "financial_baseline": baseline,
                "grounding": {
                    "history": {
                        "monthly_income": float(baseline.get("monthly_income", 0) or 0),
                        "monthly_expenses": 0.0,
                        "savings_rate": 0.0,
                        "debt_pressure": 0.0,
                    },
                    "evidence": [],
                    "freshness": freshness_snapshot([]),
                    "proof_contract": {
                        "complete": False,
                        "required_sources": ["World Bank", "Yahoo Finance"],
                        "tracked_records": 0,
                        "stale_or_due_records": 0,
                        "missing_source_records": 0,
                        "missing_freshness_records": 0,
                    },
                    "notes": [
                        "Relationship guidance is unavailable until a partner profile exists.",
                    ],
                },
            }
        )

    monthly_income = float(baseline.get("monthly_income", 0) or 0)
    recent_expense_total = float(baseline.get("observed_average_monthly_variable_spend", 0) or 0)
    monthly_emi = float(baseline.get("recurring_emi_burden", 0) or 0)
    fixed_load = float(baseline.get("fixed_obligations", 0) or 0)
    savings_rate = max(0.0, min(100.0, float(baseline.get("savings_rate", 0) or 0)))
    debt_pressure = max(0.0, min(100.0, float(baseline.get("debt_burden_ratio", 0) or 0)))

    planning_context = verified_intelligence.household_planning_context()
    planning_payload = planning_context.get("payload", {})
    inflation_payload = planning_payload.get("inflation", {})
    market_payload = planning_payload.get("market", {})
    evidence_items = planning_context.get("evidence", [])
    evidence_freshness = planning_context.get("freshness") or freshness_snapshot(evidence_items)

    baseline_financial_score = round(max(25.0, min(95.0, (savings_rate * 0.55) + (100.0 - debt_pressure) * 0.45)), 2)
    user_habit_score = max(20.0, min(100.0, savings_rate))
    financial_alignment = max(20.0, 100.0 - abs(float(profile.partner_financial_score or 0) - baseline_financial_score))
    habit_alignment = max(20.0, 100.0 - abs(float((profile.partner_savings_habits or 0) * 20) - user_habit_score))
    shared_resilience = max(20.0, min(100.0, (float(profile.compatibility_score or 0) * 0.65) + ((100.0 - debt_pressure) * 0.35)))
    planning_pressure = max(
        15.0,
        min(
            100.0,
            100.0
            - (
                float(inflation_payload.get("latest_value") or 0) * 4.5
                + float(market_payload.get("india_vix") or 0) * 1.1
            ),
        ),
    )

    heuristic_score = round(
        (financial_alignment * 0.32)
        + (habit_alignment * 0.23)
        + (shared_resilience * 0.3)
        + (planning_pressure * 0.15),
        2,
    )
    ml_prediction = relationship_model_predictor.predict_score(
        {
            "partner_financial_score": float(profile.partner_financial_score or 0),
            "partner_savings_habits": float(profile.partner_savings_habits or 0),
            "user_savings_rate": float(savings_rate or 0),
            "user_debt_pressure": float(debt_pressure or 0),
            "monthly_income_band": min(12.0, float(monthly_income or 0) / 25000.0) if monthly_income else 0.0,
        }
    )
    if ml_prediction is not None:
        alignment_score = round((heuristic_score * 0.7) + (float(ml_prediction) * 0.3), 2)
        model_note = "A trained relationship-score regressor was available and used only as a bounded blend over the rule-based score."
    else:
        alignment_score = heuristic_score
        model_note = "No trained relationship model was available, so Alfred used only bounded household-planning heuristics."

    if alignment_score >= 80:
        compatibility = "Strong"
    elif alignment_score >= 65:
        compatibility = "Good"
    elif alignment_score >= 50:
        compatibility = "Watch"
    else:
        compatibility = "Fragile"

    insights = [
        f"Partner financial score is {profile.partner_financial_score:.0f} versus your current household baseline of {baseline_financial_score:.0f}.",
        f"Savings habit alignment is {habit_alignment:.0f}/100 after comparing partner habit score with your current savings rate.",
        f"Shared planning pressure is {100.0 - planning_pressure:.0f}/100 after considering inflation and market volatility context.",
    ]
    if debt_pressure >= 45:
        insights.append("Debt and fixed-load pressure are elevated, so large shared commitments should be staged more carefully.")
    elif savings_rate >= 25:
        insights.append("Savings buffer is relatively healthy, which supports medium-term shared goals more safely.")
    else:
        insights.append("Savings runway is thin, so short-term affordability discussions matter more than long-horizon goals right now.")

    return RelationshipAlignment(
        {
            "alignment_score": alignment_score,
            "compatibility": compatibility,
            "message": f"Alignment is {compatibility.lower()} based on partner inputs, current household cash-flow pressure, and shared planning context.",
            "insights": insights,
            "financial_baseline": baseline,
            "factors": [
                {"label": "Financial Alignment", "score": round(financial_alignment, 2), "detail": "Partner score vs your current financial baseline."},
                {"label": "Savings Habit Fit", "score": round(habit_alignment, 2), "detail": "Partner savings habit vs your observed savings capacity."},
                {"label": "Shared Resilience", "score": round(shared_resilience, 2), "detail": "Compatibility input blended with debt and fixed-load resilience."},
                {"label": "Planning Pressure", "score": round(planning_pressure, 2), "detail": "Lower inflation and volatility support easier shared planning."},
            ],
            "grounding": {
                "history": {
                    "monthly_income": round(monthly_income, 2),
                    "monthly_expenses": round(recent_expense_total, 2),
                    "monthly_emi": round(monthly_emi, 2),
                    "fixed_load": round(fixed_load, 2),
                    "savings_rate": round(savings_rate, 2),
                    "debt_pressure": round(debt_pressure, 2),
                },
                "evidence": evidence_items,
                "freshness": evidence_freshness,
                "external_context": planning_payload,
                "proof_contract": {
                    "complete": bool(evidence_freshness.get("proof_complete")),
                    "required_sources": ["World Bank", "Yahoo Finance"],
                    "tracked_records": evidence_freshness.get("tracked_records", 0),
                    "stale_or_due_records": evidence_freshness.get("stale_or_due_records", 0),
                    "missing_source_records": evidence_freshness.get("missing_source_records", 0),
                    "missing_freshness_records": evidence_freshness.get("missing_freshness_records", 0),
                },
                "notes": [
                    "Relationship output is grounded in user-owned household cash-flow signals plus verified external affordability context.",
                    "External evidence contextualizes planning pressure, not emotional compatibility.",
                    *planning_context.get("notes", []),
                    model_note,
                ],
            },
        }
    )
