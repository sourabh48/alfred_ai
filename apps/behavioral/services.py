from __future__ import annotations

from collections import Counter
from datetime import timedelta
from statistics import mean

from django.utils import timezone

from apps.expenses.models import Expense
from apps.expenses.services.financial_intelligence import DISCRETIONARY_CATEGORIES, build_financial_intelligence
from apps.integrations.services import verified_intelligence
from apps.integrations.services.verified_intelligence import freshness_snapshot

from .models import BehavioralSignal


def build_behavioral_fingerprint(user) -> dict:
    linked = _build_linked_behavior_data(user)
    manual_series = linked["manual_series"]
    intelligence = linked["intelligence"]
    summary = intelligence["summary"]
    behavior = intelligence["behavior"]
    planning_context = verified_intelligence.household_planning_context()

    if not linked["has_behavior_data"]:
        return {
            "fingerprint": "No data",
            "stress_level": 0,
            "spending_pattern": "Pattern unavailable",
            "decision_style": "Style unavailable",
            "message": "Not enough behavioral data. Continue using Alfred to build your profile.",
            "insights": ["Capture a few days of stress, sleep, and work data or import a statement to build your behavioral fingerprint."],
            "pattern_flags": [],
            "stress_drivers": [],
            "minute_details": [],
            "strategy": "Import transaction history or log behavioral signals to activate the fingerprint engine.",
            "coach_tone": "energetic",
            "linked_data": linked["linked_data"],
            "pressure_map": [],
            "grounding": _behavioral_grounding(
                linked["linked_data"],
                planning_context=planning_context,
                notes=[
                    "Behavioral fingerprinting has no user-owned pattern data yet; verified household context is attached only as a planning-pressure baseline.",
                    "External evidence contextualizes affordability pressure while Alfred waits for personal behavioral signals.",
                ],
            ),
        }

    stress_level = round(_blend_current_stress(manual_series, linked["derived_pressure_scores"], summary["stress_score"]), 2)
    fingerprint = _derive_fingerprint(summary=summary, behavior=behavior, stress_level=stress_level, linked=linked)
    spending_pattern = _derive_spending_pattern(summary=summary, linked=linked)
    decision_style = _derive_decision_style(summary=summary, behavior=behavior, stress_level=stress_level)
    insights = _dedupe_items(
        behavior.get("ai_insights", []),
        behavior.get("pattern_flags", []),
        behavior.get("stress_drivers", []),
        behavior.get("minute_details", []),
    )[:7]

    transactions = linked["linked_data"]["transactions"]
    manual_signal_count = linked["linked_data"]["manual_signal_count"]
    reference_month = linked["linked_data"]["reference_month"]
    message_parts = []
    if transactions:
        message_parts.append(f"Linked {transactions} transaction{'s' if transactions != 1 else ''} through {reference_month}.")
    if manual_signal_count:
        message_parts.append(
            f"Blended {manual_signal_count} manual behavioral log{'s' if manual_signal_count != 1 else ''} into the current pressure view."
        )
    if behavior.get("strategy"):
        message_parts.append(behavior["strategy"])

    return {
        "fingerprint": fingerprint,
        "stress_level": stress_level,
        "spending_pattern": spending_pattern,
        "decision_style": decision_style,
        "message": " ".join(message_parts).strip() or "ALFRED linked your financial activity to the behavioral layer.",
        "insights": insights,
        "pattern_flags": behavior.get("pattern_flags", []),
        "stress_drivers": behavior.get("stress_drivers", []),
        "minute_details": behavior.get("minute_details", []),
        "strategy": behavior.get("strategy", ""),
        "coach_tone": behavior.get("coach_tone", "energetic"),
        "linked_data": linked["linked_data"],
        "pressure_map": linked["pressure_map"],
        "grounding": _behavioral_grounding(
            linked["linked_data"],
            planning_context=planning_context,
            notes=[
                "Behavioral fingerprinting is grounded in linked transaction patterns, recurring commitments, spike days, and manual signals.",
                "Verified household-planning evidence contextualizes affordability and decision pressure; it does not infer intent.",
            ],
        ),
    }


def build_behavioral_stress(user) -> dict:
    linked = _build_linked_behavior_data(user)
    intelligence = linked["intelligence"]
    summary = intelligence["summary"]
    behavior = intelligence["behavior"]
    planning_context = verified_intelligence.household_planning_context()

    if not linked["has_behavior_data"]:
        return {
            "current_stress": 0,
            "average_stress": 0,
            "trend": "Unknown",
            "weekly_data": [],
            "message": "No stress data available",
            "recommendations": ["Log a few behavioral snapshots or import spending data to activate the stress advisor."],
            "pressure_map": [],
            "linked_transactions": 0,
            "manual_signal_count": 0,
            "grounding": _behavioral_grounding(
                linked["linked_data"],
                planning_context=planning_context,
                notes=[
                    "Stress guidance has no user-owned behavioral pattern data yet; verified household context is attached only as a planning-pressure baseline.",
                    "External evidence contextualizes affordability pressure while Alfred waits for personal stress or spending signals.",
                ],
            ),
        }

    combined_series = _build_combined_stress_series(
        manual_series=linked["manual_series"],
        derived_scores=linked["derived_pressure_scores"],
        fallback_stress=summary["stress_score"],
    )
    trend = _series_trend(combined_series)
    recommendations = _dedupe_items(
        behavior.get("stress_drivers", []),
        behavior.get("ai_insights", []),
        _stress_recommendations_from_manual(linked["manual_signal_objects"]),
    )[:6]
    transactions = linked["linked_data"]["transactions"]
    manual_signal_count = linked["linked_data"]["manual_signal_count"]

    if transactions and manual_signal_count:
        message = (
            f"Derived from {transactions} linked transactions and {manual_signal_count} manual behavioral logs. "
            f"Current financial pressure state is {summary['risk_level'].lower()}."
        )
    elif transactions:
        message = (
            f"Derived from {transactions} linked transactions. "
            f"Current financial pressure state is {summary['risk_level'].lower()}."
        )
    else:
        message = "Derived from manual behavioral logs."

    return {
        "current_stress": round(combined_series[0] if combined_series else 0, 2),
        "average_stress": round(mean(combined_series), 2) if combined_series else 0,
        "trend": trend,
        "weekly_data": combined_series[:7],
        "message": message,
        "recommendations": recommendations,
        "pressure_map": linked["pressure_map"],
        "linked_transactions": transactions,
        "manual_signal_count": manual_signal_count,
        "grounding": _behavioral_grounding(
            linked["linked_data"],
            planning_context=planning_context,
            notes=[
                "Stress guidance is grounded in linked spending windows, recurring commitments, spike days, and manual behavioral logs.",
                "Verified household-planning evidence contextualizes affordability and decision pressure; it does not override user-owned stress signals.",
            ],
        ),
    }


def _behavioral_grounding(linked_data: dict, *, notes: list[str], planning_context: dict | None = None) -> dict:
    planning_context = planning_context or verified_intelligence.household_planning_context()
    evidence = [item for item in planning_context.get("evidence", []) if item]
    freshness = planning_context.get("freshness") or freshness_snapshot(evidence)
    return {
        "history": {
            "transactions": int(linked_data.get("transactions") or 0),
            "manual_signal_count": int(linked_data.get("manual_signal_count") or 0),
            "recurring_commitments": int(linked_data.get("recurring_commitments") or 0),
            "spike_days": int(linked_data.get("spike_days") or 0),
            "reference_month": linked_data.get("reference_month") or "",
            "peak_day": linked_data.get("peak_day") or "",
            "top_recurring": linked_data.get("top_recurring") or "",
            "top_categories": linked_data.get("top_categories") or [],
        },
        "evidence": evidence,
        "freshness": freshness,
        "external_context": planning_context.get("payload", {}),
        "proof_contract": _behavioral_proof_contract(freshness),
        "notes": [*notes, *planning_context.get("notes", [])],
    }


def _behavioral_proof_contract(freshness: dict) -> dict:
    return {
        "complete": bool(freshness.get("proof_complete")),
        "required_sources": ["World Bank", "Yahoo Finance"],
        "tracked_records": freshness.get("tracked_records", 0),
        "stale_or_due_records": freshness.get("stale_or_due_records", 0),
        "missing_source_records": freshness.get("missing_source_records", 0),
        "missing_freshness_records": freshness.get("missing_freshness_records", 0),
    }


def _build_linked_behavior_data(user) -> dict:
    intelligence = build_financial_intelligence(user)
    manual_signal_objects = list(BehavioralSignal.objects.filter(user=user).order_by("-timestamp", "-id")[:7])
    manual_series = [float(item.stress_score or 0) for item in manual_signal_objects]
    derived_pressure = _build_derived_pressure_series(user)
    linked_transactions = int(intelligence["summary"].get("transactions") or 0)
    recurring_commitments = intelligence.get("recurring_commitments", []) or []
    spike_days = intelligence.get("spike_days", []) or []
    category_distribution = intelligence.get("charts", {}).get("category_labels", []) or []
    has_behavior_data = bool(manual_series or linked_transactions or intelligence["loan_portfolio"]["active_loans"])

    return {
        "intelligence": intelligence,
        "manual_signal_objects": manual_signal_objects,
        "manual_series": manual_series,
        "derived_pressure_scores": [item["score"] for item in derived_pressure],
        "derived_pressure": derived_pressure,
        "pressure_map": _build_pressure_map(intelligence, derived_pressure),
        "linked_data": {
            "transactions": linked_transactions,
            "manual_signal_count": len(manual_signal_objects),
            "recurring_commitments": len(recurring_commitments),
            "spike_days": len(spike_days),
            "top_categories": category_distribution[:3],
            "reference_month": intelligence["summary"].get("reference_month", timezone.localdate().strftime("%B %Y")),
            "peak_day": spike_days[0]["date"] if spike_days else "",
            "top_recurring": recurring_commitments[0]["merchant"] if recurring_commitments else "",
        },
        "has_behavior_data": has_behavior_data,
    }


def _build_derived_pressure_series(user, *, windows: int = 7) -> list[dict]:
    today = timezone.localdate()
    expenses = list(
        Expense.objects.filter(
            user=user,
            direction="debit",
            transaction_date__gte=today - timedelta(days=(windows * 7) + 6),
        )
        .only("amount", "classification", "category", "merchant", "is_emotional", "transaction_date")
        .order_by("-transaction_date", "-id")
    )
    if not expenses:
        return []

    window_payloads = []
    for index in range(windows):
        window_end = today - timedelta(days=index * 7)
        window_start = window_end - timedelta(days=6)
        window_items = [
            item
            for item in expenses
            if window_start <= item.transaction_date <= window_end
        ]
        if not window_items:
            window_payloads.append(
                {
                    "label": f"{window_start.strftime('%d %b')} - {window_end.strftime('%d %b')}",
                    "score": 0.0,
                    "driver": "No debit activity captured in this window.",
                }
            )
            continue

        outflow_total = sum(float(item.amount or 0) for item in window_items)
        loan_total = sum(float(item.amount or 0) for item in window_items if item.classification == "loan")
        discretionary_total = sum(float(item.amount or 0) for item in window_items if item.category in DISCRETIONARY_CATEGORIES)
        emotional_count = sum(1 for item in window_items if item.is_emotional)
        merchant_counter = Counter(
            (item.merchant or item.category or "Unspecified").strip()
            for item in window_items
            if item.merchant or item.category
        )
        window_payloads.append(
            {
                "label": f"{window_start.strftime('%d %b')} - {window_end.strftime('%d %b')}",
                "outflow_total": outflow_total,
                "loan_ratio": _safe_ratio(loan_total, outflow_total),
                "discretionary_ratio": _safe_ratio(discretionary_total, outflow_total),
                "emotional_count": emotional_count,
                "top_merchant": merchant_counter.most_common(1)[0][0] if merchant_counter else "Unspecified",
            }
        )

    average_outflow = mean(item["outflow_total"] for item in window_payloads if item.get("outflow_total")) if any(
        item.get("outflow_total") for item in window_payloads
    ) else 0.0

    results = []
    for item in window_payloads:
        outflow_total = float(item.get("outflow_total") or 0)
        spend_intensity = _safe_ratio(outflow_total, average_outflow or outflow_total or 1)
        loan_ratio = float(item.get("loan_ratio") or 0)
        discretionary_ratio = float(item.get("discretionary_ratio") or 0)
        emotional_count = int(item.get("emotional_count") or 0)
        score = min(
            10.0,
            max(0.0, (max(spend_intensity - 0.75, 0) * 3.4))
            + (loan_ratio * 3.2)
            + (discretionary_ratio * 1.7)
            + min(emotional_count * 0.45, 1.35),
        )
        driver = _pressure_driver(
            loan_ratio=loan_ratio,
            discretionary_ratio=discretionary_ratio,
            emotional_count=emotional_count,
            spend_intensity=spend_intensity,
            top_merchant=item.get("top_merchant", "Unspecified"),
        )
        results.append(
            {
                "label": item["label"],
                "score": round(score, 2),
                "driver": driver,
                "outflow_total": round(outflow_total, 2),
            }
        )

    return results


def _pressure_driver(*, loan_ratio: float, discretionary_ratio: float, emotional_count: int, spend_intensity: float, top_merchant: str) -> str:
    if loan_ratio >= 0.28:
        return "Debt-servicing outflows dominated this period."
    if discretionary_ratio >= 0.38:
        return f"Lifestyle-heavy spending concentrated around {top_merchant}."
    if emotional_count >= 2:
        return "Emotion-tagged spending clustered in this period."
    if spend_intensity >= 1.3:
        return "Outflow volume spiked above your normal weekly pace."
    return "Pressure stayed within your recent spending range."


def _build_pressure_map(intelligence: dict, derived_pressure: list[dict]) -> list[dict]:
    summary = intelligence["summary"]
    behavior = intelligence["behavior"]
    recurring_commitments = intelligence.get("recurring_commitments", []) or []
    spike_days = intelligence.get("spike_days", []) or []
    avg_pressure = round(mean(item["score"] for item in derived_pressure), 2) if derived_pressure else round(
        float(summary.get("stress_score") or 0) / 10,
        2,
    )

    return [
        {
            "label": "Cash-flow pressure",
            "score": round(float(summary.get("stress_score") or 0), 1),
            "detail": f"{summary.get('risk_level', 'Unknown')} state driven by current savings and debt-service ratios.",
        },
        {
            "label": "Lifestyle pressure",
            "score": round(float(summary.get("discretionary_ratio") or 0), 1),
            "detail": f"{len(recurring_commitments)} recurring commitment{'s' if len(recurring_commitments) != 1 else ''} and variable discretionary outflow.",
        },
        {
            "label": "Spike pressure",
            "score": min(round(len(spike_days) * 12.5, 1), 100.0),
            "detail": "Based on detected high-intensity spend days in the linked transaction history.",
        },
        {
            "label": "Behavior pressure",
            "score": round(avg_pressure * 10, 1),
            "detail": behavior.get("strategy", "ALFRED is still calibrating the right behavioral response."),
        },
    ]


def _build_combined_stress_series(*, manual_series: list[float], derived_scores: list[float], fallback_stress: float) -> list[float]:
    series_length = max(len(manual_series), len(derived_scores), 1)
    combined = []
    for index in range(series_length):
        manual_value = manual_series[index] if index < len(manual_series) else None
        derived_value = derived_scores[index] if index < len(derived_scores) else None
        if manual_value is not None and derived_value is not None:
            combined.append(round((manual_value * 0.65) + (derived_value * 0.35), 2))
        elif manual_value is not None:
            combined.append(round(manual_value, 2))
        elif derived_value is not None:
            combined.append(round(derived_value, 2))
        else:
            combined.append(round(float(fallback_stress or 0) / 10, 2))
    return combined


def _blend_current_stress(manual_series: list[float], derived_scores: list[float], fallback_stress: float) -> float:
    combined = _build_combined_stress_series(
        manual_series=manual_series,
        derived_scores=derived_scores,
        fallback_stress=fallback_stress,
    )
    return combined[0] if combined else 0.0


def _derive_fingerprint(*, summary: dict, behavior: dict, stress_level: float, linked: dict) -> str:
    if float(summary.get("debt_service_ratio") or 0) >= 28 or stress_level >= 7:
        return "Pressure-Weighted Planner"
    if float(summary.get("stability_score") or 0) >= 75 and float(summary.get("savings_rate") or 0) >= 18:
        return "Steady Builder"
    if linked["linked_data"]["transactions"] >= 8:
        return behavior.get("personality") or "Adaptive Balancer"
    return "Adaptive Balancer"


def _derive_spending_pattern(*, summary: dict, linked: dict) -> str:
    discretionary_ratio = float(summary.get("discretionary_ratio") or 0)
    loan_ratio = float(summary.get("loan_ratio") or 0)
    recurring_count = int(linked["linked_data"]["recurring_commitments"] or 0)

    if loan_ratio >= 22:
        return "Debt-weighted"
    if discretionary_ratio >= 35:
        return "Lifestyle-heavy"
    if recurring_count >= 3:
        return "Commitment-led"
    if float(summary.get("savings_rate") or 0) >= 20:
        return "Controlled"
    return "Mixed"


def _derive_decision_style(*, summary: dict, behavior: dict, stress_level: float) -> str:
    if stress_level >= 7 or str(summary.get("risk_level") or "").lower() == "high":
        return "Reactive"
    if float(summary.get("discipline_score") or 0) >= 70 and float(summary.get("stability_score") or 0) >= 70:
        return "Analytical"
    if behavior.get("coach_tone") == "gentle":
        return "Cautious"
    return "Balanced"


def _stress_recommendations_from_manual(signals: list[BehavioralSignal]) -> list[str]:
    if not signals:
        return []
    avg_sleep = mean(float(item.sleep_hours or 0) for item in signals)
    avg_work = mean(float(item.work_hours or 0) for item in signals)
    avg_stress = mean(float(item.stress_score or 0) for item in signals)
    recommendations = []
    if avg_stress > 6:
        recommendations.append("Manual stress logs are elevated. Delay non-essential spending while pressure is high.")
    if avg_sleep < 6:
        recommendations.append("Sleep recovery is low in recent logs. Decision fatigue is likely affecting financial choices.")
    if avg_work > 10:
        recommendations.append("Workload is elevated. Protect a lower-pressure window before making financial commitments.")
    return recommendations


def _series_trend(values: list[float]) -> str:
    if len(values) >= 4:
        midpoint = len(values) // 2
        recent_window = mean(values[:midpoint])
        older_window = mean(values[midpoint:])
        delta = recent_window - older_window
        if delta >= 0.6:
            return "Increasing"
        if delta <= -0.6:
            return "Decreasing"
        return "Stable"
    if len(values) >= 2:
        delta = values[0] - values[-1]
        if delta >= 0.5:
            return "Increasing"
        if delta <= -0.5:
            return "Decreasing"
    return "Stable"


def _dedupe_items(*groups: list[str]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for group in groups:
        for item in group or []:
            text = str(item or "").strip()
            if not text or text in seen:
                continue
            seen.add(text)
            ordered.append(text)
    return ordered


def _safe_ratio(value: float, base: float) -> float:
    if not base:
        return 0.0
    return float(value or 0) / float(base or 1)
