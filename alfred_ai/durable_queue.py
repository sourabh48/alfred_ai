"""SQLite acknowledgements for the native, single-consumer Huey runtime.

Claims and queue/schedule transfers are atomic. Replay is deliberately limited
to repeatable maintenance tasks; interrupted imports and training are retained
for review because their application writes cannot share the queue transaction.
"""
import datetime
import json
import time
import uuid

from huey import SqliteHuey
from huey.api import Result
from huey.storage import SqliteStorage


REPLAY_SAFE = frozenset({
    "alfred_ai.tasks.production_probe_task",
    "alfred_ai.tasks.production_beat_heartbeat",
    "alfred_ai.native_tasks.native_scheduler_heartbeat",
    "alfred_ai.native_tasks.native_runtime_probe",
    "alfred_ai.native_tasks.native_intelligence_refresh",
    "alfred_ai.native_tasks.native_intelligence_cleanup",
    "apps.integrations.tasks.refresh_verified_external_intelligence",
    "apps.integrations.tasks.cleanup_verified_external_intelligence",
})


def task_name(task):
    module, name = type(task).__module__, type(task).__name__
    # The Celery-compatible wrapper historically supplied a fully qualified
    # name to Huey, which also prefixes the module. Preserve wire compatibility.
    return name if name.startswith(module + ".") else f"{module}.{name}"


def safe_summary(value):
    """Persist operational counts, never task arguments, documents or results."""
    if not isinstance(value, dict):
        return {}
    keys = {"status", "processed", "refreshed", "failed", "skipped", "trained",
            "fitted_models", "skipped_models", "failed_models", "retention_days",
            "ready_count", "fitted_count", "skipped_count", "failed_count"}
    return {key: item for key, item in value.items() if key in keys
            and isinstance(item, (str, int, float, bool, type(None)))}


class AcknowledgedSqliteStorage(SqliteStorage):
    ddl = SqliteStorage.ddl + [
        "CREATE TABLE IF NOT EXISTS native_claim (token TEXT PRIMARY KEY, queue TEXT NOT NULL, "
        "data BLOB NOT NULL, priority REAL NOT NULL, claimed REAL NOT NULL, state TEXT NOT NULL)",
        "CREATE INDEX IF NOT EXISTS native_claim_queue ON native_claim(queue, state)",
        "CREATE TABLE IF NOT EXISTS native_history (id INTEGER PRIMARY KEY, queue TEXT NOT NULL, "
        "task_id TEXT, name TEXT, started REAL, finished REAL, outcome TEXT, summary TEXT)",
        "CREATE TABLE IF NOT EXISTS native_recovery (queue TEXT, task_id TEXT, attempts INTEGER, "
        "PRIMARY KEY(queue, task_id))",
    ]

    def claim(self):
        with self.db(commit=True) as cursor:
            cursor.execute("SELECT id, data, priority FROM task WHERE queue=? "
                           "ORDER BY priority DESC, id LIMIT 1", (self.name,))
            row = cursor.fetchone()
            if row is None:
                return None
            row_id, data, priority = row
            token = uuid.uuid4().hex
            cursor.execute("INSERT INTO native_claim VALUES (?, ?, ?, ?, ?, 'active')",
                           (token, self.name, data, priority, time.time()))
            cursor.execute("DELETE FROM task WHERE id=?", (row_id,))
            return token, data

    def finish(self, token, task, outcome, summary=None, *, data=None, eta=None):
        """Acknowledge, or transfer a retry to queue/schedule, in one commit."""
        with self.db(commit=True) as cursor:
            cursor.execute("SELECT claimed FROM native_claim WHERE token=? AND queue=?",
                           (token, self.name))
            row = cursor.fetchone()
            if row is None:
                raise RuntimeError("Native task acknowledgement has no matching claim")
            if data is not None:
                if eta is None:
                    cursor.execute("INSERT INTO task(queue, data, priority) VALUES (?, ?, ?)",
                                   (self.name, self.to_blob(data), task.priority or 0))
                else:
                    cursor.execute("INSERT INTO schedule(queue, data, timestamp) VALUES (?, ?, ?)",
                                   (self.name, self.to_blob(data), eta.timestamp()))
            cursor.execute("INSERT INTO native_history(queue, task_id, name, started, finished, outcome, summary) "
                           "VALUES (?, ?, ?, ?, ?, ?, ?)",
                           (self.name, task.id, task_name(task), row[0], time.time(), outcome,
                            json.dumps(summary or {})))
            cursor.execute("DELETE FROM native_claim WHERE token=?", (token,))
            # Keep 30 days of metadata. Never expire unfinished claims.
            cursor.execute("DELETE FROM native_history WHERE queue=? AND finished<?",
                           (self.name, time.time() - 30 * 86400))
            if data is None:
                cursor.execute("DELETE FROM native_recovery WHERE queue=? AND task_id=?",
                               (self.name, task.id))

    def promote_schedule(self, timestamp, deserialize):
        """Avoid the destructive read_schedule -> enqueue crash window."""
        with self.db(commit=True) as cursor:
            cursor.execute("SELECT id, data FROM schedule WHERE queue=? AND timestamp<=? "
                           "ORDER BY timestamp, id", (self.name, timestamp.timestamp()))
            for row_id, data in cursor.fetchall():
                try:
                    priority = deserialize(data).priority or 0
                except Exception:
                    # Retain unknown payloads for inspection instead of dropping them.
                    cursor.execute("INSERT INTO native_claim VALUES (?, ?, ?, 0, ?, 'review')",
                                   (uuid.uuid4().hex, self.name, data, time.time()))
                else:
                    cursor.execute("INSERT INTO task(queue, data, priority) VALUES (?, ?, ?)",
                                   (self.name, data, priority))
                cursor.execute("DELETE FROM schedule WHERE id=?", (row_id,))

    def recover(self, deserialize):
        """Only call while holding the exclusive native worker OS lock."""
        recovered, review = 0, 0
        with self.db(commit=True) as cursor:
            cursor.execute("SELECT token, data, priority, claimed FROM native_claim "
                           "WHERE queue=? AND state='active'", (self.name,))
            for token, data, priority, claimed in cursor.fetchall():
                try:
                    task = deserialize(data)
                    name, identity = task_name(task), task.id
                except Exception:
                    name, identity = "unregistered task", token
                cursor.execute("SELECT attempts FROM native_recovery WHERE queue=? AND task_id=?",
                               (self.name, identity))
                attempts = (cursor.fetchone() or (0,))[0]
                if name in REPLAY_SAFE and attempts < 3:
                    cursor.execute("INSERT INTO task(queue, data, priority) VALUES (?, ?, ?)",
                                   (self.name, data, priority))
                    cursor.execute("DELETE FROM native_claim WHERE token=?", (token,))
                    cursor.execute("INSERT OR REPLACE INTO native_recovery VALUES (?, ?, ?)",
                                   (self.name, identity, attempts + 1))
                    outcome = "recovered"
                    recovered += 1
                else:
                    cursor.execute("UPDATE native_claim SET state='review' WHERE token=?", (token,))
                    outcome = "interrupted_needs_review"
                    review += 1
                cursor.execute("INSERT INTO native_history(queue, task_id, name, started, finished, outcome, summary) "
                               "VALUES (?, ?, ?, ?, ?, ?, '{}')",
                               (self.name, identity, name, claimed, time.time(), outcome))
        return {"requeued": recovered, "needs_review": review}

    def review_jobs(self, deserialize):
        jobs = []
        for token, data, claimed in self.sql(
                "SELECT token, data, claimed FROM native_claim WHERE queue=? AND state='review'",
                (self.name,), results=True):
            try:
                name = task_name(deserialize(data))
            except Exception:
                name = "unregistered task"
            jobs.append({"job_id": token, "task": name, "interrupted_at": claimed,
                         "status": "Review partial changes before retrying"})
        return jobs

    def retry_review(self, token, deserialize):
        with self.db(commit=True) as cursor:
            cursor.execute("SELECT data, priority FROM native_claim WHERE queue=? AND token=? AND state='review'",
                           (self.name, token))
            row = cursor.fetchone()
            if row is None:
                raise ValueError("No interrupted job with that ID is awaiting review")
            task = deserialize(row[0])  # Do not release an unregistered task.
            cursor.execute("INSERT INTO task(queue, data, priority) VALUES (?, ?, ?)", (self.name, *row))
            cursor.execute("DELETE FROM native_claim WHERE token=?", (token,))
            cursor.execute("DELETE FROM native_recovery WHERE queue=? AND task_id=?", (self.name, task.id))


class DurableSqliteHuey(SqliteHuey):
    storage_class = AcknowledgedSqliteStorage

    def dequeue(self):
        claimed = self.storage.claim()
        if claimed is None:
            return None
        token, data = claimed
        try:
            task = self.deserialize_task(data)
        except Exception:
            self.storage.sql("UPDATE native_claim SET state='review' WHERE token=?", (token,), True)
            raise
        task._native_claim = token
        return task

    def _emit(self, signal, task, *args, **kwargs):
        if signal in {"complete", "error", "revoked", "expired", "canceled", "interrupted",
                      "timeout", "locked", "rate-limited"}:
            task._native_outcome = signal
        return super()._emit(signal, task, *args, **kwargs)

    def execute(self, task, timestamp=None):
        result = super().execute(task, timestamp)
        token = getattr(task, "_native_claim", None)
        if token and getattr(task, "_native_outcome", None) != "interrupted":
            self.storage.finish(token, task, getattr(task, "_native_outcome", "finished"), safe_summary(result))
            del task._native_claim
        return result

    def enqueue(self, task):
        token = getattr(task, "_native_claim", None)
        if token:
            if task.expires:
                task.resolve_expires(self.utc)
            self.storage.finish(token, task, "retry_queued", data=self.serialize_task(task))
            del task._native_claim
            self._emit("enqueued", task)
            return Result(self, task) if self.results else None
        return super().enqueue(task)

    def add_schedule(self, task):
        token = getattr(task, "_native_claim", None)
        if token:
            self.storage.finish(token, task, "scheduled", data=self.serialize_task(task),
                                eta=task.eta or datetime.datetime.fromtimestamp(0))
            del task._native_claim
            self._emit("scheduled", task)
        else:
            super().add_schedule(task)

    def read_schedule(self, timestamp=None):
        self.storage.promote_schedule(timestamp or self._get_timestamp(), self.deserialize_task)
        return []  # Already transferred atomically to the queue.
