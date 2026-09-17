"""Real SQLite and abrupt-process-exit tests for native queue acknowledgements."""
import datetime
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

from alfred_ai.durable_queue import DurableSqliteHuey, REPLAY_SAFE, safe_summary, task_name


def native_runtime_probe(value=7):
    return value


native_runtime_probe.__module__ = "alfred_ai.native_tasks"


class DurableQueueTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.filename = str(Path(self.directory.name) / "jobs.sqlite3")
        self.huey = DurableSqliteHuey("proof", filename=self.filename, fsync=True)
        self.task = self.huey.task()(native_runtime_probe)

    def tearDown(self):
        self.huey.storage.close()
        self.directory.cleanup()

    def rows(self, table):
        return self.huey.storage.sql(f"SELECT * FROM {table}", results=True)

    def test_completed_result_is_acknowledged_and_not_replayed(self):
        result = self.task(12)
        task = self.huey.dequeue()
        self.assertIn(task_name(task), REPLAY_SAFE)
        self.assertEqual(len(self.rows("native_claim")), 1)
        self.huey.execute(task)
        self.assertEqual(result(), 12)
        self.assertEqual(self.rows("native_claim"), [])
        self.assertEqual(self.huey.storage.recover(self.huey.deserialize_task)["requeued"], 0)
        self.assertEqual(self.rows("native_history")[0][-2], "complete")

    def test_worker_killed_after_dequeue_keeps_job_for_recovery(self):
        result = self.task(19)
        code = (
            "import os, sys; from tests.test_durable_queue import native_runtime_probe; "
            "from alfred_ai.durable_queue import DurableSqliteHuey; "
            "h=DurableSqliteHuey('proof', filename=sys.argv[1], fsync=True); "
            "h.task()(native_runtime_probe); assert h.dequeue() is not None; os._exit(77)"
        )
        process = subprocess.run([sys.executable, "-c", code, self.filename], capture_output=True)
        self.assertEqual(process.returncode, 77, process.stderr)
        self.assertEqual(self.huey.pending_count(), 0)
        self.assertEqual(self.huey.storage.recover(self.huey.deserialize_task)["requeued"], 1)
        self.huey.execute(self.huey.dequeue())
        self.assertEqual(result(), 19)

    def test_crash_inside_claim_transaction_rolls_back_deletion(self):
        self.task()
        code = (
            "import os, sqlite3, sys; c=sqlite3.connect(sys.argv[1]); "
            "c.execute('BEGIN IMMEDIATE'); c.execute('DELETE FROM task'); os._exit(78)"
        )
        process = subprocess.run([sys.executable, "-c", code, self.filename], capture_output=True)
        self.assertEqual(process.returncode, 78, process.stderr)
        self.assertEqual(self.huey.pending_count(), 1)

    def test_retry_handoff_has_one_scheduled_copy_and_no_claim(self):
        @self.huey.task(retries=1, retry_delay=1)
        def transient():
            raise ValueError("synthetic failure")
        transient()
        self.huey.execute(self.huey.dequeue())
        self.assertEqual(self.rows("native_claim"), [])
        self.assertEqual(self.huey.scheduled_count(), 1)
        future = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) + datetime.timedelta(seconds=5)
        self.huey.read_schedule(future)
        self.assertEqual(self.huey.scheduled_count(), 0)
        self.assertEqual(self.huey.pending_count(), 1)
        self.huey.execute(self.huey.dequeue(), timestamp=future)
        self.assertEqual(self.rows("native_claim"), [])
        self.assertEqual(self.rows("native_history")[-1][-2], "error")

    def test_repeated_crashes_stop_after_three_automatic_replays(self):
        self.task()
        for _ in range(3):
            self.huey.dequeue()
            self.assertEqual(self.huey.storage.recover(self.huey.deserialize_task)["requeued"], 1)
        self.huey.dequeue()
        self.assertEqual(self.huey.storage.recover(self.huey.deserialize_task)["needs_review"], 1)
        self.assertEqual(self.huey.pending_count(), 0)

    def test_import_is_retained_for_review_then_explicit_retry(self):
        @self.huey.task()
        def write_financial_data():
            return 1
        write_financial_data()
        self.huey.dequeue()
        self.assertEqual(self.huey.storage.recover(self.huey.deserialize_task)["needs_review"], 1)
        review = self.huey.storage.review_jobs(self.huey.deserialize_task)
        self.assertEqual(len(review), 1)
        token = review[0]["job_id"]
        self.huey.storage.retry_review(token, self.huey.deserialize_task)
        self.assertEqual(self.huey.pending_count(), 1)
        with self.assertRaises(ValueError):
            self.huey.storage.retry_review(token, self.huey.deserialize_task)

    def test_revoked_task_is_acknowledged_without_execution(self):
        result = self.task()
        result.revoke()
        self.huey.execute(self.huey.dequeue())
        self.assertEqual(self.rows("native_claim"), [])
        self.assertEqual(self.rows("native_history")[-1][-2], "revoked")

    def test_unknown_payload_is_retained(self):
        self.huey.storage.enqueue(b"invalid payload")
        with self.assertRaises(Exception):
            self.huey.dequeue()
        self.assertEqual(self.rows("native_claim")[0][-1], "review")

    def test_due_schedule_keeps_priority(self):
        task = self.task.s(5)
        task.priority = 10
        task.eta = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) - datetime.timedelta(seconds=1)
        self.huey.add_schedule(task)
        self.task(2)
        self.huey.read_schedule()
        self.assertEqual(self.huey.dequeue().id, task.id)

    def test_summary_excludes_personal_payloads(self):
        self.assertEqual(safe_summary({"status": "ok", "processed": 2,
                                       "results": [{"user_id": 5}], "email": "private"}),
                         {"status": "ok", "processed": 2})


if __name__ == "__main__":
    unittest.main()
