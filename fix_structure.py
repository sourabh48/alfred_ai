import os
import shutil
import datetime

LOGFILE = "fixer_log.txt"
log_entries = []

def log(msg):
    print(msg)
    log_entries.append(msg)

# ----------------------------------------------------------
# EXPECTED STRUCTURE DEFINITION
# ----------------------------------------------------------

EXPECTED = {
    "alfred_ai": {
        "files": {"__init__.py", "settings.py", "urls.py", "wsgi.py", "asgi.py", "celery.py"},
        "folders": {}
    },
    "apps": {
        "files": set(),
        "folders": {
            app: {
                "files": {"__init__.py", "models.py", "views.py", "serializers.py", "admin.py", "urls.py"},
                "folders": {}
            }
            for app in [
                "users","expenses","budgets","loans","investments",
                "family","career","behavioral","relationship","risk","reports","ml_engine"
            ]
        }
    },
    "ml_engine": {
        "files": {"__init__.py"},
        "folders": {
            "api": {"files": {"__init__.py", "urls.py", "views.py"}, "folders": {}},
            "core": {"files": {
                "__init__.py","alfred_router.py","alfred_inference.py",
                "alfred_personality.py","alfred_safetylayer.py",
                "alfred_preprocessor.py","alfred_registry.py"
            }, "folders": {}},
            "loaders": {"files": {"__init__.py", "model_loader.py", "s3_loader.py"}, "folders": {}},
            "continual": {"files": {"__init__.py","learning_scheduler.py","drift_monitor.py","trust_scoring.py"}, "folders": {}},
            "preprocessing": {"files": {"__init__.py","cleaner.py","validators.py"}, "folders": {}},
        }
    },
    "ml_models": {
        "files": set(),
        "folders": {
            "alfred": {
                "files": set(),
                "folders": {
                    "personality": {"files": {"traits.json", "adaptive_traits.json"}, "folders": {}},
                    "memory": {"files": set(), "folders": {"embeddings_store": {"files": set(), "folders": {}}}},
                    "model_registry": {"files": {"registry.json"}, "folders": {}},
                    "salary_model": {"files": set(), "folders": {}},
                    "expense_lstm": {"files": set(), "folders": {}},
                    "emotional_bert": {"files": set(), "folders": {}},
                    "burnout_rf": {"files": set(), "folders": {}},
                    "relationship_siamese": {"files": set(), "folders": {}},
                    "risk_classifier": {"files": set(), "folders": {}},
                    "rl_agent": {"files": set(), "folders": {}},
                }
            }
        }
    },
    "templates": {
        "files": {"base.html","navbar.html","dashboard.html"},
        "folders": {
            "expenses": {"files": set(),"folders": {}},
            "budgets": {"files": set(),"folders": {}},
            "loans": {"files": set(),"folders": {}},
            "investments": {"files": set(),"folders": {}},
            "family": {"files": set(),"folders": {}},
            "career": {"files": set(),"folders": {}},
            "behavioral": {"files": set(),"folders": {}},
            "relationship": {"files": set(),"folders": {}},
            "risk": {"files": set(),"folders": {}},
            "reports": {"files": set(),"folders": {}},
        }
    },
    "static": {
        "files": set(),
        "folders": {
            "css": {"files": {"style.css"}, "folders": {}},
            "js": {"files": set(), "folders": {}},
            "vendor": {
                "files": set(),
                "folders": {
                    "bootstrap": {"files": set(),"folders": {}},
                    "chartjs": {"files": set(),"folders": {}},
                    "jquery": {"files": set(),"folders": {}},
                    "icons": {"files": set(),"folders": {}},
                }
            }
        }
    },
    "scripts": {
        "files": {"update_external_data.py","cron_jobs.py"},
        "folders": {
            "training_scripts": {
                "files": {
                    "train_salary_model.py","train_lstm_expense.py","train_emotional_bert.py",
                    "train_burnout_model.py","train_relationship_model.py","train_risk_model.py",
                    "train_rl_agent.py"
                },
                "folders": {}
            }
        }
    }
}

# ----------------------------------------------------------
# SAFE QUARANTINE SYSTEM (Prevents recursive errors)
# ----------------------------------------------------------

def quarantine(path, base):
    name = os.path.basename(path)

    # Do NOT quarantine quarantine folder itself
    if name == "__QUARANTINE__":
        log(f"[SKIP] Ignoring quarantine folder: {path}")
        return

    quarantine_dir = os.path.join(base, "__QUARANTINE__")
    os.makedirs(quarantine_dir, exist_ok=True)

    dest = os.path.join(quarantine_dir, name)

    # Prevent moving into itself
    if os.path.abspath(path) == os.path.abspath(dest):
        log(f"[SKIP] Cannot move {path} into itself")
        return

    shutil.move(path, dest)
    log(f"[QUARANTINED] {path} → {dest}")


# ----------------------------------------------------------
# FIX STRUCTURE RECURSIVELY (Safe + Correct)
# ----------------------------------------------------------

def fix_folder(folder_path, structure):

    expected_files = structure.get("files", set())
    expected_folders = structure.get("folders", {})

    # Ensure folders exist
    for folder in expected_folders:
        sub = os.path.join(folder_path, folder)
        if not os.path.exists(sub):
            os.makedirs(sub)
            log(f"[CREATED FOLDER] {sub}")
        fix_folder(sub, expected_folders[folder])

    # Ensure files exist
    for file in expected_files:
        target_file = os.path.join(folder_path, file)
        if not os.path.exists(target_file):
            with open(target_file, "w") as f:
                f.write("")
            log(f"[CREATED FILE] {target_file}")

    # Handle unexpected items
    for item in os.listdir(folder_path):
        if item == "__QUARANTINE__":
            continue  # ignore quarantine folder safely

        full_item = os.path.join(folder_path, item)
        if item not in expected_files and item not in expected_folders:
            quarantine(full_item, folder_path)


# ----------------------------------------------------------
# MAIN RUNNER
# ----------------------------------------------------------

def run_fixer():
    base = os.getcwd()
    log(f"--- ALFRED PROJECT STRUCTURE FIXER STARTED ---")
    log(f"Base directory: {base}")

    for root in EXPECTED:
        target = os.path.join(base, root)
        if not os.path.exists(target):
            os.makedirs(target)
            log(f"[CREATED ROOT FOLDER] {target}")
        fix_folder(target, EXPECTED[root])

    with open(LOGFILE, "w", encoding="utf-8") as f:
        f.write("\n".join(log_entries))

    log("--- STRUCTURE FIX COMPLETE ---")
    log(f"Log written to {LOGFILE}")


if __name__ == "__main__":
    run_fixer()
