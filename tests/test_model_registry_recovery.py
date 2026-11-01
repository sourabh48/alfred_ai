"""Registry receipts survive failed writes; no real training or model access."""
from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import time
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
        self.assertEqual(sorted(p.name for p in self.root.iterdir()), [".registry.lock", "registry.json"])

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

    def run_python(self, code):
        project = Path(__file__).resolve().parents[1]
        return subprocess.Popen([sys.executable, "-B", "-c", code], cwd=project, stderr=subprocess.PIPE,
                                env={**os.environ, "ALFRED_REGISTRY_PATH": str(self.root), "PYTHONPATH": str(project)})

    def test_separate_processes_keep_every_receipt_and_the_existing_one(self):
        before = self.registry.get("expense")
        # Released together: without a cross-process lock this loses most receipts, which staggered starts can hide.
        gate = self.root / "synthetic-start-gate"
        ready = [self.root / f"synthetic-ready-{index}" for index in range(3)]
        writer = ("import os, time\nfrom apps.ml_engine.core.alfred_registry import model_registry as r\n"
                  "open(ready, 'x').close()\nwhile not os.path.exists(gate): time.sleep(0.001)\n"
                  "for n in range(40): r.update(f'synthetic-process-{index}-{n}', 'synthetic-v2')\n")
        workers = [self.run_python(f"index, ready, gate = {index}, {str(ready[index])!r}, {str(gate)!r}\n" + writer) for index in range(3)]
        deadline = time.monotonic() + 60
        while not all(path.exists() for path in ready) and time.monotonic() < deadline:
            time.sleep(0.01)
        gate.touch()
        for worker in workers:
            _, errors = worker.communicate(timeout=120)
            self.assertEqual(worker.returncode, 0, errors.decode()[-400:])
        saved = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(len(saved), 121)
        self.assertEqual(saved["expense"], before)

    def test_writer_that_dies_holding_the_lock_does_not_block_the_next_one(self):
        worker = self.run_python("import os\nfrom apps.ml_engine.core.alfred_registry import _exclusive, model_registry\n"
                                 "lock = _exclusive(os.environ['ALFRED_REGISTRY_PATH'])\nlock.__enter__()\nos._exit(9)\n")
        worker.communicate(timeout=60)
        self.assertEqual(worker.returncode, 9)
        self.registry.update("salary", "synthetic-v2")
        self.assertEqual(json.loads(self.path.read_text(encoding="utf-8"))["salary"]["version"], "synthetic-v2")
