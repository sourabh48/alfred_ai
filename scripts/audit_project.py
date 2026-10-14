"""Read-only source/Markdown inventory and documentation checks; never imports application code."""
from __future__ import annotations

import argparse
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
LINK = re.compile(r"(?<!!)\[[^\]\n]*\]\((<[^>]+>|[^\s)]+)(?:\s+[^)]*)?\)")
MONEY = re.compile(r"income|salary|rent|emi|amount|balance|cost|price|budget|premium|principal|value|sip|deduction|expense|savings|wealth", re.I)
MEASURE = re.compile(r"rate|ratio|score|confidence|percent|mileage|odometer|km|latitude|longitude|probability", re.I)


def tracked(repo=ROOT):
    result = subprocess.run(["git", "--no-optional-locks", "-C", str(repo), "ls-files", "--cached", "--others",
                             "--exclude-standard", "-z"], capture_output=True, check=True)
    return sorted(set(result.stdout.decode().split("\0")) - {""})


def classification(path):
    if (path.startswith((".codex/skills/graphify/", ".claude/skills/graphify/", "static/vendor/"))
            or path.startswith(".agents/skills/") and not path.startswith(".agents/skills/alfred-")):
        return "VENDOR"
    if path.startswith(("docs/releases/", "artifacts/reinstall/")):
        return "HISTORICAL"
    if path.startswith(("docs/ALFRED_", "artifacts/audit/ALFRED_WHOLE_PROJECT_AUDIT_",
                        "artifacts/audit/ALFRED_DOCUMENTATION_RECONCILIATION_",
                        "artifacts/audit/ALFRED_MASTER_COMPLETION_")):
        return "CURRENT"
    if (re.search(r"(?:VERIFICATION|ACCEPTANCE|REPORT|RESEARCH|_20\d{6}|_2026-\d\d-\d\d)", path)
            and path not in ("docs/MANUAL_ACCEPTANCE.md", "docs/USER_DATA_ACCEPTANCE.md",
                             "docs/WINDOWS_ACCEPTANCE.md", "docs/COMPLETION_AUDIT.md",
                             "docs/M15_RECOVERY_ACCEPTANCE.md")):
        return "HISTORICAL"
    if path == "artifacts/audit/M15_RELEASE_READINESS.md":
        return "CURRENT"
    if path.startswith("artifacts/audit/") and "BACKLOG" not in path and "CONTINUATION" not in path:
        return "HISTORICAL"
    return "CURRENT"


def link_target(repo, source, target):
    target = unquote(target.strip("<>"))
    if target.startswith(("#", "//")) or urlsplit(target).scheme:
        return None
    relative = target.split("#", 1)[0].split("?", 1)[0]
    if not relative:
        return None
    resolved = (repo / relative.lstrip("/")) if relative.startswith("/") else (repo / source).parent / relative
    return resolved.resolve()


def markdown_inventory(repo, paths):
    records = []
    for name in (path for path in paths if path.lower().endswith(".md")):
        path = repo / name
        if path.is_symlink() or not path.is_file():
            raise ValueError("unsafe_documentation_path")
        text = path.read_text(encoding="utf-8-sig")
        missing = []
        for match in LINK.finditer(text):
            target = link_target(repo, name, match[1])
            if target is not None and not target.exists():
                missing.append(match[1])
        records.append({"path": name, "classification": classification(name),
            "review_method": "full_content_inventory_and_link_scan", "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "lines": len(text.splitlines()), "headings": re.findall(r"^#{1,4}\s+(.+)$", text, re.M),
            "missing_links": missing, "dated_status_claims": bool(re.search(r"undeployed|development only|no live.*deploy|not promoted", text, re.I))})
    return records


def source_inventory(repo, paths):
    records = []
    for name in (path for path in paths if path.endswith(".py")):
        path = repo / name
        try:
            tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=name)
        except SyntaxError as exc:
            records.append({"path": name, "syntax_error_line": exc.lineno})
            continue
        symbols, fields, imports, routes, calls = [], [], set(), [], set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                symbols.append({"name": node.name, "kind": type(node).__name__, "line": node.lineno})
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.add("." * node.level + (node.module or ""))
            elif isinstance(node, ast.Call):
                function = ast.unparse(node.func)
                calls.add(function)
                if function in ("path", "re_path") and node.args and isinstance(node.args[0], ast.Constant):
                    routes.append({"path": str(node.args[0].value), "view": ast.unparse(node.args[1]) if len(node.args) > 1 else "", "line": node.lineno})
        for model in (node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)):
            for node in model.body:
                if (isinstance(node, ast.Assign) and isinstance(node.value, ast.Call)
                        and isinstance(node.value.func, ast.Attribute)
                        and (node.value.func.attr.endswith("Field") or node.value.func.attr in ("ForeignKey", "OneToOneField", "ManyToManyField"))):
                    field = ast.unparse(node.targets[0])
                    fields.append({"model": model.name, "field": field, "type": node.value.func.attr, "line": node.lineno,
                        "monetary_candidate": bool(MONEY.search(field) and not MEASURE.search(field)),
                        "relationships": ast.unparse(node.value.args[0]) if node.value.func.attr in ("ForeignKey", "OneToOneField", "ManyToManyField") and node.value.args else None})
        records.append({"path": name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                        "symbols": symbols, "model_fields": fields, "imports": sorted(imports), "routes": routes, "calls": sorted(calls)})
    return records


def validate_matrix(repo, path):
    rows = json.loads(path.read_text(encoding="utf-8"))
    statuses = {"COMPLETE_VERIFIED", "IMPLEMENTED_NOT_ACCEPTED", "PARTIALLY_IMPLEMENTED", "NOT_IMPLEMENTED",
                "BLOCKED_EXTERNAL", "BLOCKED_APPROVAL", "REQUIRES_RESEARCH", "UNKNOWN"}
    required = {"id", "module", "requirement", "status", "sources", "endpoints", "models", "tests", "test_result",
                "real_account_acceptance", "real_provider_acceptance", "production_status", "limitations", "dependencies", "priority", "next_action"}
    issues, seen = [], set()
    for row in rows:
        if not required <= row.keys() or row.get("status") not in statuses or row.get("id") in seen:
            issues.append({"id": row.get("id"), "code": "invalid_matrix_record"})
        seen.add(row.get("id"))
        for reference in row.get("sources", []) + row.get("tests", []):
            path = reference.split(":", 1)[0]
            if not (repo / path).is_file():
                issues.append({"id": row["id"], "code": "missing_source_reference", "path": path})
    return issues


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--matrix", type=Path)
    args = parser.parse_args()
    repo = args.repo.resolve()
    paths = tracked(repo)
    docs, source = markdown_inventory(repo, paths), source_inventory(repo, paths)
    args.output.mkdir(parents=True, exist_ok=True)
    for name, data in (("markdown-inventory.json", docs), ("source-inventory.json", source)):
        (args.output / name).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    issues = validate_matrix(repo, args.matrix) if args.matrix else []
    summary = {"source_commit": subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip(),
        "tracked_and_owned_files": len(paths), "markdown_files": len(docs), "python_files": len(source),
        "documentation_classes": dict(Counter(row["classification"] for row in docs)),
        "syntax_errors": sum("syntax_error_line" in row for row in source),
        "missing_link_count": sum(len(row["missing_links"]) for row in docs),
        "active_missing_links": [{"path": row["path"], "targets": row["missing_links"]}
                                 for row in docs if row["classification"] == "CURRENT" and row["missing_links"]],
        "matrix_issues": issues,
        "scope": "public_source_and_documentation_only_no_runtime_or_database_access"}
    (args.output / "inventory-summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary))
    return 1 if issues or summary["syntax_errors"] or summary["active_missing_links"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
