from __future__ import annotations

from collections import Counter
import os
import re

from apps.ml_engine.models import DocumentParserLearningMemory
from apps.ml_engine.inference_adapters.parser_confidence_calibrator import parser_confidence_calibrator


TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9]{2,}")
STOP_TOKENS = {
    "THE", "AND", "FOR", "WITH", "THIS", "FROM", "THAT", "YOUR", "DATE", "NAME", "AMOUNT",
    "TOTAL", "ACCOUNT", "NUMBER", "DOCUMENT", "REPORT", "SERVICE", "CUSTOMER", "PAGE",
}


def apply_parser_learning(*, user, scope: str, filename: str, detected_type: str, text: str, field_names: list[str], confidence: float) -> tuple[float, list[str]]:
    if user is None:
        return confidence, []

    extension, template_signature, field_signature, keywords = _build_learning_profile(filename, text, field_names)
    notes: list[str] = []
    adjusted = float(confidence or 0)

    exact_memory = (
        DocumentParserLearningMemory.objects.filter(
            user=user,
            scope=scope,
            file_extension=extension,
            detected_type=detected_type[:60],
            template_signature=template_signature,
            field_signature=field_signature,
        )
        .order_by("-last_seen_at", "-id")
        .first()
    )
    family_memories = list(
        DocumentParserLearningMemory.objects.filter(
            user=user,
            scope=scope,
            file_extension=extension,
            detected_type=detected_type[:60],
        ).order_by("-last_seen_at", "-id")[:20]
    )

    if exact_memory and exact_memory.successful_count >= 2 and text.strip():
        boost = min(0.12, 0.03 + (exact_memory.successful_count * 0.015))
        adjusted += boost
        notes.append(f"Adaptive parser memory boosted confidence from {scope} upload history for this document shape (+{boost:.2f}).")
    elif exact_memory and exact_memory.failed_count >= 2 and not text.strip():
        adjusted = min(adjusted, 0.22)
        notes.append(f"Adaptive parser memory recognized a previously weak {scope} document shape and kept confidence conservative.")
    if exact_memory and exact_memory.correction_count >= 1:
        correction_boost = min(0.08, 0.02 + (exact_memory.correction_count * 0.01))
        adjusted += correction_boost
        notes.append("Accepted user corrections exist for this document shape, so Alfred is weighting similar fields more confidently.")
    accepted_overlap = len(set(field_names) & set(exact_memory.accepted_field_hints or [])) if exact_memory else 0
    if exact_memory and exact_memory.retry_success_count >= 1 and text.strip():
        retry_boost = min(0.07, 0.02 + (exact_memory.retry_success_count * 0.01) + (accepted_overlap * 0.005))
        adjusted += retry_boost
        notes.append("Retry history shows Alfred has previously recovered this document shape after review, so confidence was lifted slightly.")
    elif exact_memory and exact_memory.retry_failure_count > exact_memory.retry_success_count and not text.strip():
        adjusted = min(adjusted, 0.2)
        notes.append("Retry history shows this document shape still fails often without better source text, so Alfred kept confidence conservative.")

    if family_memories:
        total_success = sum(item.successful_count for item in family_memories)
        total_review = sum(item.review_count for item in family_memories)
        total_failed = sum(item.failed_count for item in family_memories)
        total_retry_success = sum(item.retry_success_count for item in family_memories)
        total_retry_failure = sum(item.retry_failure_count for item in family_memories)
        observed = total_success + total_review + total_failed
        keyword_overlap = max(
            (
                len(set(keywords) & set(item.observed_keywords or []))
                for item in family_memories
            ),
            default=0,
        )
        field_overlap = max(
            (
                len(set(field_names) & set(item.observed_fields or []))
                for item in family_memories
            ),
            default=0,
        )
        accepted_field_overlap = max(
            (
                len(set(field_names) & set(item.accepted_field_hints or []))
                for item in family_memories
            ),
            default=0,
        )
        if observed >= 3 and text.strip():
            success_ratio = total_success / max(observed, 1)
            overlap_boost = min(0.07, (keyword_overlap * 0.01) + (field_overlap * 0.01) + (accepted_field_overlap * 0.008))
            ratio_boost = min(0.06, success_ratio * 0.05)
            retry_boost = min(0.04, max(total_retry_success - total_retry_failure, 0) * 0.008)
            adjusted += overlap_boost + ratio_boost + retry_boost
            if overlap_boost or ratio_boost or retry_boost:
                notes.append("Adaptive parser memory found similar uploaded documents and raised confidence accordingly.")
        elif observed >= 3 and not text.strip() and (total_failed + total_retry_failure) >= (total_success + total_retry_success):
            adjusted = min(adjusted, 0.18)
            notes.append("Adaptive parser memory marked this pattern as historically weak until cleaner files arrive.")

    calibrated = _calibrated_confidence(
        scope=scope,
        extension=extension,
        exact_memory=exact_memory,
        family_memories=family_memories,
        confidence=adjusted,
        field_names=field_names,
        has_text=bool(text.strip()),
    )
    if calibrated is not None:
        adjusted = (adjusted * 0.7) + (calibrated * 0.3)
        notes.append("A trained parser-confidence calibrator blended the final confidence using stored parser outcome history.")

    return round(min(max(adjusted, 0.0), 0.98), 2), notes[:3]


def record_parser_learning(
    *,
    user,
    scope: str,
    filename: str,
    detected_type: str,
    text: str,
    field_names: list[str],
    parser_status: str,
    confidence: float,
    from_retry: bool = False,
    accepted_fields: list[str] | None = None,
    resolution: str = "",
):
    if user is None:
        return None

    extension, template_signature, field_signature, keywords = _build_learning_profile(filename, text, field_names)
    memory, _ = DocumentParserLearningMemory.objects.get_or_create(
        user=user,
        scope=scope,
        file_extension=extension,
        detected_type=(detected_type or "")[:60],
        template_signature=template_signature,
        field_signature=field_signature,
    )

    if parser_status == "parsed":
        memory.successful_count += 1
    elif parser_status == "needs_review":
        memory.review_count += 1
    else:
        memory.failed_count += 1
    if from_retry:
        if parser_status == "parsed":
            memory.retry_success_count += 1
        else:
            memory.retry_failure_count += 1

    total = memory.successful_count + memory.review_count + memory.failed_count
    previous_weight = max(total - 1, 0)
    memory.average_confidence = round(
        ((memory.average_confidence * previous_weight) + float(confidence or 0)) / max(total, 1),
        4,
    )
    memory.observed_fields = sorted({*(memory.observed_fields or []), *[field for field in field_names if field]})[:24]
    memory.observed_keywords = sorted({*(memory.observed_keywords or []), *keywords})[:24]
    memory.accepted_field_hints = sorted(
        {
            *(memory.accepted_field_hints or []),
            *[field for field in (accepted_fields or []) if field],
        }
    )[:24]
    if resolution:
        memory.last_resolution = resolution[:40]
    memory.save()
    return memory


def record_parser_correction(
    *,
    user,
    scope: str,
    filename: str,
    detected_type: str,
    text: str,
    field_names: list[str],
    confidence: float,
    resolution: str = "accepted_correction",
):
    if user is None:
        return None

    extension, template_signature, field_signature, keywords = _build_learning_profile(filename, text, field_names)
    memory, _ = DocumentParserLearningMemory.objects.get_or_create(
        user=user,
        scope=scope,
        file_extension=extension,
        detected_type=(detected_type or "")[:60],
        template_signature=template_signature,
        field_signature=field_signature,
    )
    memory.correction_count += 1
    memory.review_count += 1
    total = memory.successful_count + memory.review_count + memory.failed_count
    previous_weight = max(total - 1, 0)
    memory.average_confidence = round(
        ((memory.average_confidence * previous_weight) + float(confidence or 0)) / max(total, 1),
        4,
    )
    memory.observed_fields = sorted({*(memory.observed_fields or []), *[field for field in field_names if field]})[:24]
    memory.observed_keywords = sorted({*(memory.observed_keywords or []), *keywords})[:24]
    memory.accepted_field_hints = sorted({*(memory.accepted_field_hints or []), *[field for field in field_names if field]})[:24]
    memory.last_resolution = resolution[:40]
    memory.save()
    return memory


def _build_learning_profile(filename: str, text: str, field_names: list[str]) -> tuple[str, str, str, list[str]]:
    extension = os.path.splitext((filename or "").lower())[1] or "unknown"
    template_signature, keywords = _template_signature(text)
    field_signature = "|".join(sorted({field.strip().lower() for field in (field_names or []) if field and field.strip()})[:12])[:255]
    return extension, template_signature, field_signature, keywords


def _template_signature(text: str) -> tuple[str, list[str]]:
    tokens = [
        token.upper()
        for token in TOKEN_RE.findall((text or "")[:4000])
        if token.upper() not in STOP_TOKENS
    ]
    if not tokens:
        return "", []
    keywords = [token for token, _ in Counter(tokens).most_common(8)]
    return "|".join(sorted(keywords))[:255], keywords


def _calibrated_confidence(*, scope: str, extension: str, exact_memory, family_memories: list, confidence: float, field_names: list[str], has_text: bool) -> float | None:
    seed = exact_memory or (family_memories[0] if family_memories else None)
    if seed is None:
        return None
    features = {
        "successful_count": float(sum(item.successful_count for item in family_memories) if family_memories else seed.successful_count),
        "review_count": float(sum(item.review_count for item in family_memories) if family_memories else seed.review_count),
        "failed_count": float(sum(item.failed_count for item in family_memories) if family_memories else seed.failed_count),
        "correction_count": float(sum(item.correction_count for item in family_memories) if family_memories else seed.correction_count),
        "retry_success_count": float(sum(item.retry_success_count for item in family_memories) if family_memories else seed.retry_success_count),
        "retry_failure_count": float(sum(item.retry_failure_count for item in family_memories) if family_memories else seed.retry_failure_count),
        "average_confidence": float(confidence or seed.average_confidence or 0),
        "observed_fields_count": float(len(set(field_names) | set(seed.observed_fields or []))),
        "observed_keywords_count": float(len(seed.observed_keywords or [])) if has_text else 0.0,
        "accepted_field_hints_count": float(len(set(field_names) & set(seed.accepted_field_hints or []))),
        "scope_hash": float(sum(ord(char) for char in (scope or "")) % 997),
        "extension_hash": float(sum(ord(char) for char in (extension or "")) % 97),
    }
    prediction = parser_confidence_calibrator.predict_probability(features)
    if prediction is None:
        return None
    return round(min(max(prediction, 0.0), 0.98), 4)
