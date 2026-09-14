from __future__ import annotations

import math
from collections import Counter
from numbers import Number


class DriftMonitor:
    """Detect population drift with a bounded population-stability index."""

    DEFAULT_BUCKETS = 10
    EPSILON = 1e-6

    def detect(self, old_distribution, new_data) -> float:
        """
        Return a population-stability index for numeric or categorical samples.

        Values below 0.1 are normally stable, 0.1-0.25 suggests moderate drift,
        and values above 0.25 indicate material drift that should be reviewed.
        """
        old_values = self._as_sequence(old_distribution)
        new_values = self._as_sequence(new_data)
        if not old_values or not new_values:
            return 0.0

        if self._looks_numeric(old_values) and self._looks_numeric(new_values):
            old_counts, new_counts = self._numeric_bucket_counts(old_values, new_values)
        else:
            old_counts, new_counts = self._categorical_counts(old_values, new_values)

        return round(self._population_stability_index(old_counts, new_counts), 6)

    def level(self, psi_score: float) -> str:
        score = max(float(psi_score or 0), 0.0)
        if score >= 0.25:
            return "material"
        if score >= 0.1:
            return "moderate"
        return "stable"

    def explain(self, old_distribution, new_data) -> dict:
        score = self.detect(old_distribution, new_data)
        return {
            "psi_score": score,
            "drift_level": self.level(score),
            "review_required": score >= 0.1,
        }

    def _as_sequence(self, values) -> list:
        if values is None:
            return []
        if isinstance(values, dict):
            if all(isinstance(value, Number) for value in values.values()):
                expanded = []
                for key, count in values.items():
                    expanded.extend([key] * max(int(count or 0), 0))
                return expanded
            return list(values.values())
        if isinstance(values, (str, bytes)):
            return [values]
        try:
            return list(values)
        except TypeError:
            return [values]

    def _looks_numeric(self, values: list) -> bool:
        if not values:
            return False
        for value in values:
            try:
                float(value)
            except (TypeError, ValueError):
                return False
        return True

    def _numeric_bucket_counts(self, old_values: list, new_values: list) -> tuple[list[int], list[int]]:
        old_numeric = [float(value) for value in old_values]
        new_numeric = [float(value) for value in new_values]
        combined = old_numeric + new_numeric
        low = min(combined)
        high = max(combined)
        if math.isclose(low, high):
            return [len(old_numeric)], [len(new_numeric)]

        bucket_count = min(
            self.DEFAULT_BUCKETS,
            max(2, int(math.sqrt(min(len(old_numeric), len(new_numeric))))),
        )
        width = (high - low) / bucket_count
        old_counts = [0] * bucket_count
        new_counts = [0] * bucket_count
        for target, values in ((old_counts, old_numeric), (new_counts, new_numeric)):
            for value in values:
                index = min(bucket_count - 1, max(0, int((value - low) / width)))
                target[index] += 1
        return old_counts, new_counts

    def _categorical_counts(self, old_values: list, new_values: list) -> tuple[list[int], list[int]]:
        old_counter = Counter(str(value) for value in old_values)
        new_counter = Counter(str(value) for value in new_values)
        keys = sorted(set(old_counter) | set(new_counter))
        return [old_counter[key] for key in keys], [new_counter[key] for key in keys]

    def _population_stability_index(self, old_counts: list[int], new_counts: list[int]) -> float:
        old_total = sum(old_counts)
        new_total = sum(new_counts)
        if old_total <= 0 or new_total <= 0:
            return 0.0

        smoothing = 1.0
        old_total += smoothing * len(old_counts)
        new_total += smoothing * len(new_counts)
        score = 0.0
        for old_count, new_count in zip(old_counts, new_counts):
            old_pct = max((old_count + smoothing) / old_total, self.EPSILON)
            new_pct = max((new_count + smoothing) / new_total, self.EPSILON)
            score += (new_pct - old_pct) * math.log(new_pct / old_pct)
        return max(score, 0.0)


drift_monitor = DriftMonitor()
