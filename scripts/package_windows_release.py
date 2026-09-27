"""Create distributable Windows artifacts from a complete, verified frozen bundle."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import zipfile


ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write_acceptance_kit(bundle, output):
    import winreg

    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography",
                        access=winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as key:
        machine_guid = winreg.QueryValueEx(key, "MachineGuid")[0]
    for name in ("Verify fresh install.cmd", "Verify after reboot.cmd", "ACCEPTANCE.txt", "READ ME.txt"):
        shutil.copy2(ROOT / "packaging/windows" / name, output / name)
    shutil.copy2(ROOT / "scripts/verify_windows_acceptance.ps1", output / "verify_windows_acceptance.ps1")
    for name in ("MANUAL_ACCEPTANCE.md", "WINDOWS_ACCEPTANCE.md"):
        shutil.copy2(ROOT / "docs" / name, output / name)
    (output / "acceptance-manifest.json").write_text(json.dumps({
        "development_machine_fingerprint": hashlib.sha256(machine_guid.encode("utf-8")).hexdigest(),
        "executable_sha256": digest(bundle / "ALFRED.exe"),
    }, indent=2), encoding="utf-8")


def inspect_bundle(bundle):
    required = ("ALFRED.exe", "ALFRED Launcher.exe", "Start ALFRED.cmd", "Stop ALFRED.cmd",
                "READ ME.txt", "_internal/python312.dll", "_internal/base_library.zip",
                "_internal/static/alfred.ico", "_internal/guide/index.html",
                "_internal/guide/images/04-tray.svg",
                "_internal/static/vendor/bootstrap.min.css", "_internal/static/vendor/chart.umd.min.js",
                "_internal/templates/career/list.html", "_internal/templates/integrations/credit_score.html")
    missing = [name for name in required if not (bundle / name).is_file()]
    for pattern in ("_internal/rapidocr_onnxruntime/models/*.onnx", "_internal/onnxruntime/capi/*.dll",
                    "_internal/_tcl_data/init.tcl", "_internal/_tk_data/tk.tcl"):
        if not any(bundle.glob(pattern)):
            missing.append(pattern)
    if missing:
        raise RuntimeError(f"Incomplete standalone bundle: {missing}")
    files = []
    for path in sorted(bundle.rglob("*")):
        if path.is_symlink() or path.is_junction():
            raise RuntimeError(f"Unexpected link in the release: {path.relative_to(bundle)}")
        if not path.is_file():
            continue
        relative = path.relative_to(bundle)
        lowered = relative.as_posix().lower()
        public_ca_bundle = lowered in ("_internal/certifi/cacert.pem", "_internal/botocore/cacert.pem")
        if public_ca_bundle and "PRIVATE KEY" in path.read_text(encoding="ascii"):
            raise RuntimeError(f"Unexpected private key in certificate bundle: {relative}")
        if (path.suffix.lower() in (".sqlite3", ".env", ".key")
                or (path.suffix.lower() == ".pem" and not public_ca_bundle)
                or path.name.lower() == ".env"
                or any(part in {"media", "statement_uploads", "career_resumes", "credit_reports"} for part in relative.parts)
                or lowered.endswith("ml_models/alfred/model_registry/registry.json")):
            raise RuntimeError(f"Private runtime path found in release: {relative}")
        files.append(path)
    for name in ("career/list.html", "integrations/credit_score.html"):
        if digest(bundle / "_internal/templates" / name) != digest(ROOT / "templates" / name):
            raise RuntimeError(f"Bundled template is stale: {name}")
    if digest(bundle / "_internal/static/alfred.ico") != digest(ROOT / "static/alfred.ico"):
        raise RuntimeError("Bundled Windows icon is stale")
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--iscc", type=Path, required=True)
    args = parser.parse_args()
    bundle, output = args.bundle.resolve(), args.output.resolve()
    if bundle == output or bundle in output.parents:
        parser.error("output must be outside the bundle")
    files = inspect_bundle(bundle)
    output.mkdir(parents=True, exist_ok=True)
    archive = output / "ALFRED-Windows-x64.zip"
    installer = output / "ALFRED-Setup.exe"
    if archive.exists() or installer.exists():
        parser.error("release artifacts already exist; choose a new output folder")
    subprocess.run([str(args.iscc.resolve()), f"/DBundleDir={bundle}", f"/DReleaseDir={output}",
                    str(ROOT / "packaging/ALFRED.iss")], check=True)
    temporary = archive.with_suffix(".zip.partial")
    with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zipped:
        for path in files:
            zipped.write(path, "ALFRED/" + path.relative_to(bundle).as_posix())
    with zipfile.ZipFile(temporary) as zipped:
        bad = zipped.testzip()
        if bad:
            raise RuntimeError(f"ZIP verification failed: {bad}")
    temporary.replace(archive)
    write_acceptance_kit(bundle, output)
    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(), "platform": "Windows x64",
        "requires_system_python": False, "files_checked": len(files),
        "bundle_bytes": sum(path.stat().st_size for path in files),
        "data_directory": "%LOCALAPPDATA%/ALFRED", "private_runtime_paths_found": 0,
        "components": ["Python 3.12", "Django", "Waitress", "Huey", "SQLite", "diskcache",
                       "RapidOCR", "ONNX Runtime", "Tcl/Tk desktop launcher", "Windows tray icon",
                       "offline illustrated installation guide", "bundled web assets"],
        "artifacts": {path.name: {"bytes": path.stat().st_size, "sha256": digest(path)}
                      for path in (archive, installer, bundle / "ALFRED.exe", bundle / "ALFRED Launcher.exe")},
    }
    (output / "release-manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (output / "SHA256SUMS.txt").write_text("".join(
        f"{manifest['artifacts'][path.name]['sha256']}  {path.name}\n" for path in (archive, installer)), encoding="ascii")
    print(json.dumps({"output": str(output), "files_checked": len(files), "artifacts": manifest["artifacts"]}), flush=True)


if __name__ == "__main__":
    main()
