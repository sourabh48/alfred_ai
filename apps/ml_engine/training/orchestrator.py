from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import timedelta
from importlib import import_module
from statistics import mean
from time import monotonic

from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from apps.behavioral.models import BehavioralSignal
from apps.expenses.models import Expense
from apps.mobility.models import BikeServiceRecord
from apps.ml_engine.core.alfred_registry import model_registry
from apps.ml_engine.models import AdaptiveModelState, AdaptiveTrainingRun, DocumentParserLearningMemory
from apps.relationship.models import RelationshipProfile
from apps.users.models import User


@dataclass(frozen=True)
class TrainingSpec:
    key: str
    label: str
    refresh_hours: int
    minimum_samples: int
    fallback_mode: str
    sample_counter: callable
    trainer_path: str
    description: str


TRAINING_SPECS = [
    TrainingSpec(
        key="salary_predictor",
        label="Salary predictor",
        refresh_hours=24,
        minimum_samples=8,
        fallback_mode="career salary projection uses rule-based growth when the trained artifact is absent or stale",
        sample_counter=lambda: User.objects.filter(monthly_income__gt=0).count(),
        trainer_path="apps.ml_engine.training.train_salary.train_salary_model",
        description="Learns salary patterns from stored user profile signals without leaking the target back into features.",
    ),
    TrainingSpec(
        key="expense_forecaster",
        label="Expense forecaster",
        refresh_hours=12,
        minimum_samples=28,
        fallback_mode="expense forecasts fall back to recent average and trend heuristics",
        sample_counter=lambda: Expense.objects.count(),
        trainer_path="apps.ml_engine.training.train_expense_lstm.train_expense_lstm",
        description="Learns rolling cash-flow sequences from imported and manual expense history.",
    ),
    TrainingSpec(
        key="burnout_rf",
        label="Burnout estimator",
        refresh_hours=12,
        minimum_samples=12,
        fallback_mode="burnout and stress views fall back to behavioral score heuristics",
        sample_counter=lambda: BehavioralSignal.objects.count(),
        trainer_path="apps.ml_engine.training.train_burnout_rf.train_burnout_model",
        description="Learns stress and workload patterns from behavioral snapshots.",
    ),
    TrainingSpec(
        key="risk_classifier",
        label="Behavioral risk classifier",
        refresh_hours=12,
        minimum_samples=12,
        fallback_mode="risk views fall back to stress, sleep, and work-hour rules",
        sample_counter=lambda: BehavioralSignal.objects.count(),
        trainer_path="apps.ml_engine.training.train_risk_classifier.train_risk_classifier",
        description="Learns behavior-linked risk flags from stress, sleep, and work-hour patterns.",
    ),
    TrainingSpec(
        key="parser_confidence_calibrator",
        label="Parser confidence calibrator",
        refresh_hours=12,
        minimum_samples=12,
        fallback_mode="document parsers use bounded extractor confidence and review queues",
        sample_counter=lambda: DocumentParserLearningMemory.objects.count(),
        trainer_path="apps.ml_engine.training.train_parser_confidence.train_parser_confidence_model",
        description="Calibrates parser confidence from accepted corrections, retries, and stored parser outcome memory.",
    ),
    TrainingSpec(
        key="relationship_model",
        label="Relationship model",
        refresh_hours=24,
        minimum_samples=8,
        fallback_mode="relationship alignment uses bounded compatibility heuristics with evidence notes",
        sample_counter=lambda: RelationshipProfile.objects.filter(compatibility_score__gt=0).count(),
        trainer_path="apps.ml_engine.training.train_relationship.train_relationship_model",
        description="Learns bounded relationship-alignment calibration from stored scored partner profiles when enough reviewed examples exist.",
    ),
    TrainingSpec(
        key="service_cost_predictor",
        label="Service-cost predictor",
        refresh_hours=24,
        minimum_samples=10,
        fallback_mode="vehicle service cost uses catalog and recent-service heuristics",
        sample_counter=lambda: BikeServiceRecord.objects.filter(cost__gt=0).count(),
        trainer_path="apps.ml_engine.training.train_service_cost.train_service_cost_model",
        description="Learns a bounded service-cost baseline from stored vehicle service records, item counts, and vehicle metadata.",
    ),
    TrainingSpec(
        key="rl_agent",
        label="RL agent",
        refresh_hours=24,
        minimum_samples=0,
        fallback_mode="future policy learner is excluded; product flows use deterministic guardrails",
        sample_counter=lambda: 0,
        trainer_path="apps.ml_engine.training.train_rl_agent.train_rl_agent",
        description="Reserved for future reinforcement-learning policies.",
    ),
]

PLANNED_MODEL_KEYS = {"rl_agent"}


def seed_model_states() -> list[AdaptiveModelState]:
    states = []
    for spec in TRAINING_SPECS:
        state, _ = AdaptiveModelState.objects.get_or_create(
            model_key=spec.key,
            defaults={
                "display_name": spec.label,
                "status": "idle",
                "notes": spec.description,
                "freshness_hours": spec.refresh_hours,
            },
        )
        changed = False
        if state.display_name != spec.label:
            state.display_name = spec.label
            changed = True
        if state.freshness_hours != spec.refresh_hours:
            state.freshness_hours = spec.refresh_hours
            changed = True
        if not state.notes:
            state.notes = spec.description
            changed = True
        if changed:
            state.save(update_fields=["display_name", "freshness_hours", "notes", "updated_at"])
        states.append(state)
    return states


def run_training_cycle(*, trigger: str = "manual", force: bool = False, model_keys: list[str] | None = None) -> dict:
    seed_model_states()
    lock_key = "alfred:ml-training:global-lock"
    if not cache.add(lock_key, trigger, timeout=60 * 60):
        return {
            "status": "busy",
            "detail": "A previous ALFRED training cycle is still running.",
            "results": [],
        }

    try:
        now = timezone.now()
        allowed_keys = set(model_keys or [spec.key for spec in TRAINING_SPECS])
        results = []
        for spec in TRAINING_SPECS:
            if spec.key not in allowed_keys:
                continue
            results.append(_run_training_spec(spec, trigger=trigger, force=force, now=now))

        ready_count = sum(1 for item in results if item["status"] == "ready")
        skipped_count = sum(1 for item in results if item["status"] == "skipped")
        failed_count = sum(1 for item in results if item["status"] == "failed")
        avg_confidence = round(mean([item["confidence_estimate"] for item in results]) if results else 0.0, 2)
        return {
            "status": "completed",
            "detail": f"ALFRED training cycle finished: {ready_count} ready, {skipped_count} skipped, {failed_count} failed.",
            "ready_count": ready_count,
            "skipped_count": skipped_count,
            "failed_count": failed_count,
            "average_confidence": avg_confidence,
            "results": results,
        }
    finally:
        cache.delete(lock_key)


def training_health_snapshot() -> dict:
    seed_model_states()
    states = list(AdaptiveModelState.objects.order_by("display_name", "model_key"))
    spec_by_key = {spec.key: spec for spec in TRAINING_SPECS}
    total = len(states)
    ready = [item for item in states if item.status == "ready"]
    fresh = [item for item in ready if item.is_fresh]
    skipped = [item for item in states if item.status == "skipped"]
    failed = [item for item in states if item.status == "failed"]
    training = [item for item in states if item.status == "training"]
    trainable = [item for item in states if item.model_key not in PLANNED_MODEL_KEYS]
    ready_trainable = [item for item in trainable if item.status == "ready"]
    fresh_trainable = [item for item in ready_trainable if item.is_fresh]
    skipped_trainable = [item for item in trainable if item.status == "skipped"]
    planned = [item for item in states if item.model_key in PLANNED_MODEL_KEYS]
    average_confidence = round(mean([item.confidence_estimate for item in states]) if states else 0.0, 2)
    maturity_items = [_model_maturity_payload(item, spec_by_key.get(item.model_key)) for item in states]
    maturity_counts = Counter(item["maturity_level"] for item in maturity_items)

    ready_ratio = (len(ready) / total) * 100 if total else 0.0
    freshness_ratio = (len(fresh) / total) * 100 if total else 0.0
    overall_progress = round(min(96.0, (ready_ratio * 0.4) + (freshness_ratio * 0.2) + (average_confidence * 0.4)), 1)
    supervised_training_progress = round(
        (((len(ready_trainable) / len(trainable)) * 50.0) + ((len(fresh_trainable) / len(trainable)) * 50.0))
        if trainable
        else 100.0,
        1,
    )
    summary = (
        f"{len(fresh)}/{total} model states are fresh and ready; "
        f"{len(skipped_trainable)} trainable model state(s) are waiting on data or environment gates, "
        f"{len(planned)} planned future model(s) are excluded from supervised coverage, and {len(failed)} failed recently."
        if total
        else "No model training states have been initialized yet."
    )

    return {
        "overall_progress": overall_progress,
        "summary": summary,
        "total_models": total,
        "ready_models": len(ready),
        "fresh_models": len(fresh),
        "skipped_models": len(skipped),
        "failed_models": len(failed),
        "training_models": len(training),
        "trainable_models": len(trainable),
        "supervised_ready_models": len(ready_trainable),
        "supervised_fresh_models": len(fresh_trainable),
        "supervised_skipped_models": len(skipped_trainable),
        "planned_models": len(planned),
        "supervised_training_progress": supervised_training_progress,
        "average_confidence": average_confidence,
        "maturity": {
            "trained_models": maturity_counts.get("trained", 0),
            "low_confidence_models": maturity_counts.get("trained_low_confidence", 0),
            "stale_models": maturity_counts.get("trained_stale", 0),
            "data_limited_models": maturity_counts.get("data_limited", 0),
            "heuristic_fallback_models": maturity_counts.get("heuristic_fallback", 0),
            "planned_models": maturity_counts.get("planned", 0),
            "blocked_models": maturity_counts.get("blocked", 0),
            "active_heuristic_fallbacks": sum(1 for item in maturity_items if item["uses_fallback"]),
            "data_gap_count": sum(1 for item in maturity_items if item["data_gap"] > 0),
        },
        "models": maturity_items,
    }


def _model_maturity_payload(state: AdaptiveModelState, spec: TrainingSpec | None) -> dict:
    minimum_samples = int(getattr(spec, "minimum_samples", 0) or 0)
    data_gap = max(minimum_samples - int(state.sample_count or 0), 0)
    if state.model_key in PLANNED_MODEL_KEYS:
        maturity_level = "planned"
    elif state.status == "failed":
        maturity_level = "blocked"
    elif state.status == "ready" and not state.is_fresh:
        maturity_level = "trained_stale"
    elif state.status == "ready" and state.confidence_estimate < 55:
        maturity_level = "trained_low_confidence"
    elif state.status == "ready":
        maturity_level = "trained"
    elif data_gap > 0:
        maturity_level = "data_limited"
    else:
        maturity_level = "heuristic_fallback"

    blockers = []
    if data_gap > 0:
        blockers.append(f"Needs {data_gap} more sample(s) to reach the minimum training threshold.")
    if state.status == "failed":
        blockers.append("Last training attempt failed; inspect notes before trusting this model.")
    if state.status == "skipped" and data_gap == 0:
        blockers.append("Training was skipped because the data spread, environment, or implementation is not ready.")
    if state.status == "ready" and not state.is_fresh:
        blockers.append("Model artifact exists but its freshness window has elapsed.")

    return {
        "model_key": state.model_key,
        "display_name": state.display_name,
        "status": state.status,
        "sample_count": state.sample_count,
        "minimum_samples": minimum_samples,
        "data_gap": data_gap,
        "maturity_level": maturity_level,
        "uses_fallback": maturity_level in {"data_limited", "heuristic_fallback", "planned", "blocked", "trained_stale"},
        "fallback_mode": getattr(spec, "fallback_mode", ""),
        "quality_score": round(state.quality_score, 2),
        "confidence_estimate": round(state.confidence_estimate, 2),
        "notes": state.notes,
        "artifact_path": state.artifact_path,
        "next_refresh_due_at": state.next_refresh_due_at.isoformat() if state.next_refresh_due_at else None,
        "last_finished_at": state.last_finished_at.isoformat() if state.last_finished_at else None,
        "is_fresh": state.is_fresh,
        "training_blockers": blockers,
        "description": getattr(spec, "description", ""),
    }


def _load_trainer(spec: TrainingSpec):
    module_path, function_name = spec.trainer_path.rsplit(".", 1)
    module = import_module(module_path)
    return getattr(module, function_name)


def _run_training_spec(spec: TrainingSpec, *, trigger: str, force: bool, now) -> dict:
    state = AdaptiveModelState.objects.get(model_key=spec.key)
    sample_count = int(spec.sample_counter())
    if not force and state.status == "ready" and state.next_refresh_due_at and state.next_refresh_due_at > now:
        return _record_skip(
            spec=spec,
            state=state,
            trigger=trigger,
            sample_count=sample_count,
            note="Model is still fresh, so Alfred skipped unnecessary retraining.",
            now=now,
        )

    try:
        trainer = _load_trainer(spec)
    except Exception as exc:
        return _record_unavailable(
            spec=spec,
            state=state,
            trigger=trigger,
            sample_count=sample_count,
            note=f"{spec.label} training is unavailable in this environment: {exc}",
            now=now,
        )

    state.status = "training"
    state.last_trigger = trigger
    state.sample_count = sample_count
    state.last_started_at = now
    state.save(update_fields=["status", "last_trigger", "sample_count", "last_started_at", "updated_at"])

    run = AdaptiveTrainingRun.objects.create(
        model_key=spec.key,
        display_name=spec.label,
        trigger=trigger,
        status="training",
        sample_count=sample_count,
        started_at=now,
    )

    started = monotonic()
    try:
        result = trainer() or {}
    except Exception as exc:
        result = {
            "status": "failed",
            "sample_count": sample_count,
            "quality_score": 0.0,
            "confidence_estimate": 0.0,
            "artifact_path": "",
            "notes": f"{spec.label} training failed: {exc}",
        }

    finished = timezone.now()
    duration_ms = int((monotonic() - started) * 1000)
    status_value = result.get("status", "ready")
    quality_score = float(result.get("quality_score", 0) or 0)
    confidence_estimate = float(result.get("confidence_estimate", 0) or 0)
    state.sample_count = int(result.get("sample_count", sample_count) or 0)
    state.quality_score = quality_score
    state.confidence_estimate = confidence_estimate
    state.artifact_path = result.get("artifact_path", "") or ""
    state.notes = result.get("notes", spec.description)
    state.last_finished_at = finished
    state.last_trigger = trigger
    state.freshness_hours = spec.refresh_hours

    if status_value == "ready":
        state.status = "ready"
        state.success_count += 1
        state.next_refresh_due_at = finished + timedelta(hours=spec.refresh_hours)
    elif status_value == "failed":
        state.status = "failed"
        state.failure_count += 1
        state.next_refresh_due_at = finished + timedelta(hours=max(2, spec.refresh_hours // 2))
    else:
        state.status = "skipped"
        state.next_refresh_due_at = finished + timedelta(hours=max(6, spec.refresh_hours))

    model_registry.update(
        spec.key,
        version=finished.isoformat(),
        metadata={
            "status": state.status,
            "quality_score": round(quality_score, 2),
            "confidence_estimate": round(confidence_estimate, 2),
            "sample_count": state.sample_count,
            "artifact_path": state.artifact_path,
            "notes": state.notes,
        },
    )

    with transaction.atomic():
        state.save()
        run.status = state.status
        run.sample_count = state.sample_count
        run.quality_score = state.quality_score
        run.confidence_estimate = state.confidence_estimate
        run.duration_ms = duration_ms
        run.notes = state.notes
        run.finished_at = finished
        run.save()

    return {
        "model_key": spec.key,
        "display_name": spec.label,
        "status": state.status,
        "sample_count": state.sample_count,
        "quality_score": round(state.quality_score, 2),
        "confidence_estimate": round(state.confidence_estimate, 2),
        "notes": state.notes,
        "artifact_path": state.artifact_path,
    }


def _record_skip(*, spec: TrainingSpec, state: AdaptiveModelState, trigger: str, sample_count: int, note: str, now) -> dict:
    state.sample_count = sample_count
    state.last_trigger = trigger
    state.save(update_fields=["sample_count", "last_trigger", "updated_at"])
    AdaptiveTrainingRun.objects.create(
        model_key=spec.key,
        display_name=spec.label,
        trigger=trigger,
        status="skipped",
        sample_count=sample_count,
        quality_score=state.quality_score,
        confidence_estimate=state.confidence_estimate,
        duration_ms=0,
        notes=note,
        started_at=now,
        finished_at=now,
    )
    return {
        "model_key": spec.key,
        "display_name": spec.label,
        "status": "skipped",
        "sample_count": sample_count,
        "quality_score": round(state.quality_score, 2),
        "confidence_estimate": round(state.confidence_estimate, 2),
        "notes": note,
        "artifact_path": state.artifact_path,
    }


def _record_unavailable(*, spec: TrainingSpec, state: AdaptiveModelState, trigger: str, sample_count: int, note: str, now) -> dict:
    state.status = "skipped"
    state.sample_count = sample_count
    state.last_trigger = trigger
    state.notes = note
    state.last_started_at = now
    state.last_finished_at = now
    state.next_refresh_due_at = now + timedelta(hours=max(2, spec.refresh_hours // 2))
    state.save(
        update_fields=[
            "status",
            "sample_count",
            "last_trigger",
            "notes",
            "last_started_at",
            "last_finished_at",
            "next_refresh_due_at",
            "updated_at",
        ]
    )
    AdaptiveTrainingRun.objects.create(
        model_key=spec.key,
        display_name=spec.label,
        trigger=trigger,
        status="skipped",
        sample_count=sample_count,
        quality_score=state.quality_score,
        confidence_estimate=state.confidence_estimate,
        duration_ms=0,
        notes=note,
        started_at=now,
        finished_at=now,
    )
    return {
        "model_key": spec.key,
        "display_name": spec.label,
        "status": "skipped",
        "sample_count": sample_count,
        "quality_score": round(state.quality_score, 2),
        "confidence_estimate": round(state.confidence_estimate, 2),
        "notes": note,
        "artifact_path": state.artifact_path,
    }
