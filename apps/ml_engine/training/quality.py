"""Conservative deployment gates; fitting a small dataset is not validation."""

import math
from pathlib import Path

from django.conf import settings


# These are lower bounds for evidence, not a claim that meeting them validates
# generalization. Minimum training thresholds remain useful for isolated pilots.
MINIMUM_VALIDATION_SAMPLES = {
    "salary_predictor": 40,
    "expense_forecaster": 60,
    "burnout_rf": 60,
    "risk_classifier": 60,
    "parser_confidence_calibrator": 60,
    "relationship_model": 40,
    "service_cost_predictor": 50,
}

PROXY_TARGET_NOTES = {
    "burnout_rf": "The target is computed from stress and work-hour inputs; its score measures rule imitation, not observed burnout outcomes.",
    "risk_classifier": "The target is a work-hours threshold; its score does not validate layoff or illness risk.",
    "parser_confidence_calibrator": "The target is derived from the same cumulative outcome counts used as features; new-document outcome validation is still required.",
}


def resolve_artifact_path(raw_path):
    candidate = Path(raw_path)
    return candidate if candidate.is_absolute() else Path(settings.BASE_DIR) / candidate


def validation_blockers(model_key, sample_count, quality_score, confidence_estimate):
    blockers = []
    minimum = MINIMUM_VALIDATION_SAMPLES.get(model_key, 40)
    if int(sample_count or 0) < minimum:
        blockers.append(f"Needs at least {minimum} samples for validation; a small pilot fit is not inference readiness.")
    if not math.isfinite(float(quality_score or 0)) or float(quality_score or 0) < 50:
        blockers.append("Holdout quality must reach 50/100 before inference is ready.")
    if not math.isfinite(float(confidence_estimate or 0)) or float(confidence_estimate or 0) < 55:
        blockers.append("Confidence must reach 55/100 before inference is ready.")
    if model_key in PROXY_TARGET_NOTES:
        blockers.append(PROXY_TARGET_NOTES[model_key])
    return blockers
