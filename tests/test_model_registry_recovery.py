"""Registry receipts survive failed writes; no real training or model access."""
from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.ml_engine.core.alfred_registry import AlfredModelRegistry


class ModelRegistryRecoveryTests(SimpleTestCase):
    def setUp(self):
        self.root = Path(self.enterContext(TemporaryDirectory(prefix="alfred-synthetic-registry-")))
        self.enterContext(patch.dict("os.environ", {"ALFRED_REGISTRY_PATH": str(self.root)}))
        self.registry = AlfredModelRegistry()
        self.path = self.root / "registry.json"
        self.registry.update("expense", "synthetic-v1", {"status": "skipped", "notes": "Synthetic evidence only"})

    def test_serialization_failure_preserves_disk_and_memory(self):
        before, memory = self.path.read_bytes(), deepcopy(self.registry.registry)
        for invalid in ({"payload": object()}, {"quality_score": float("nan")}, {"quality_score": float("inf")}):
            with self.subTest(invalid_type=type(next(iter(invalid.values()))).__name__):
                with self.assertRaises((TypeError, ValueError)):
                    self.registry.update("salary", "synthetic-v2", invalid)
                self.assertEqual(self.path.read_bytes(), before)
                self.assertEqual(self.registry.registry, memory)

    def test_failed_atomic_replace_preserves_prior_receipt_and_removes_temporary_file(self):
        before, memory = self.path.read_bytes(), deepcopy(self.registry.registry)
        with patch("apps.ml_engine.core.alfred_registry.os.replace", side_effect=OSError("Synthetic disk failure")):
            with self.assertRaises(OSError):
                self.registry.update("salary", "synthetic-v2")
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(self.registry.registry, memory)
        self.assertEqual(sorted(p.name for p in self.root.iterdir()), ["registry.json"])

    def test_independent_instances_merge_latest_receipts(self):
        other = AlfredModelRegistry()
        self.registry.update("parser", "synthetic-v2")
        other.update("salary", "synthetic-v3", {"notes": "Synthetic résumé receipt"})
        saved = AlfredModelRegistry()
        self.assertEqual(set(saved.registry), {"expense", "parser", "salary"})
        self.assertEqual(saved.get("salary")["metadata"]["notes"], "Synthetic résumé receipt")

    def test_corrupt_or_nonobject_registry_is_unavailable_without_overwriting_evidence(self):
        for source in ("{broken", "[]", "null", '"not an object"'):
            with self.subTest(source=source):
                self.path.write_text(source, encoding="utf-8")
                registry = AlfredModelRegistry()
                self.assertIsNone(registry.get("expense"))
                with self.assertRaises(ValueError):
                    registry.update("salary", "synthetic-v2")
                self.assertEqual(self.path.read_text(encoding="utf-8"), source)

    def test_successful_replace_exposes_a_complete_old_then_complete_new_snapshot(self):
        import os
        replace = os.replace
        before = self.path.read_bytes()
        def inspect(source, target):
            self.assertEqual(self.path.read_bytes(), before)
            self.assertEqual(set(json.loads(Path(source).read_text(encoding="utf-8"))), {"expense", "salary"})
            replace(source, target)
        with patch("apps.ml_engine.core.alfred_registry.os.replace", side_effect=inspect) as write:
            self.registry.update("salary", "synthetic-v2")
        write.assert_called_once()
        self.assertEqual(set(json.loads(self.path.read_text(encoding="utf-8"))), {"expense", "salary"})

    def test_simultaneous_threaded_instances_preserve_each_role(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        instances = [AlfredModelRegistry(), AlfredModelRegistry()]
        start = Barrier(2)
        def update(index):
            start.wait(timeout=10)
            for number in range(5):
                instances[index].update(f"synthetic-role-{index}-{number}", "synthetic-v2")
        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(update, range(2)))
        self.assertEqual(len(AlfredModelRegistry().registry), 11)
