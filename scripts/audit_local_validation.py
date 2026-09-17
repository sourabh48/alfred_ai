"""Read-only aggregate data/model audit. No personal documents enter reports."""
import argparse
import datetime
import json
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/ops/real_data_validation.json")
    args = parser.parse_args()
    # Django configuration would run app hooks; raw read-only SQLite avoids them.
    database = args.data_dir.resolve() / "db.sqlite3"
    with sqlite3.connect(database.as_uri() + "?mode=ro", uri=True) as connection:
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        counts = {name: connection.execute(f'SELECT count(*) FROM "{name}"').fetchone()[0]
                  for name in tables if not name.startswith("sqlite_")}
        consent = connection.execute("SELECT ml_training_consent_granted, count(*) FROM users_user "
                                     "GROUP BY ml_training_consent_granted").fetchall()
        models = []
        for row in connection.execute("SELECT model_key, status, sample_count, quality_score, confidence_estimate, "
                                      "artifact_path, last_finished_at FROM ml_engine_adaptivemodelstate ORDER BY model_key"):
            key, status, samples, quality, confidence, path, finished = row
            # Importing this module has no DB writes; settings are not accessed here.
            from apps.ml_engine.training.quality import validation_blockers
            blockers = validation_blockers(key, samples, quality, confidence)
            if not path or not (args.data_dir / path).is_file():
                blockers.append("No model artifact is available at the recorded path.")
            models.append({"model": key, "training_status": status, "samples": samples,
                           "recorded_quality": quality, "recorded_confidence": confidence,
                           "last_finished": finished, "validation_blockers": blockers})
        documents = []
        for name in sorted(tables):
            columns = {row[1] for row in connection.execute(f'PRAGMA table_info("{name}")')}
            if "parser_status" in columns:
                statuses = dict(connection.execute(f'SELECT parser_status, count(*) FROM "{name}" GROUP BY parser_status'))
                documents.append({"family": name, "statuses": statuses, "count": counts[name]})
    payload = {
        "audited_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "read_only": True, "table_counts": dict(sorted(counts.items())),
        "training_consent_counts": {str(bool(key)): value for key, value in consent},
        "models": models, "documents": documents,
        "real_world_accuracy_verified": False,
        "limitation": "Stored scores and parser status are not independently checked ground truth. "
                      "Existing records may include demo/test data. No new accuracy percentage is justified by this audit.",
        "next_validation": "Supply anonymized documents with checked fields and independently observed target outcomes; "
                           "split evaluation by document/provider, user and time to avoid training/test overlap.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({"report": str(args.output), "models": len(models), "document_families": len(documents),
                      "real_world_accuracy_verified": False}))


if __name__ == "__main__":
    main()
