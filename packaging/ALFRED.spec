# Build from the repository root: python -m PyInstaller packaging/ALFRED.spec --noconfirm
import os
from pathlib import Path
from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_submodules, copy_metadata

root = Path(SPECPATH).parent
os.environ["ALFRED_LOCAL_RUNTIME"] = "true"
os.environ["ALFRED_AUTO_TRAIN_ON_STARTUP"] = "false"
os.environ["ALFRED_TASK_BACKEND"] = "huey"
os.environ["DJANGO_SETTINGS_MODULE"] = "alfred_ai.settings"
datas = [(str(root / "templates"), "templates"), (str(root / "static"), "static")]
binaries = []
hiddenimports = ["alfred_ai.native_settings", "diskcache.djangocache", "huey.contrib.djhuey",
                 "django.db.backends.sqlite3", "django.contrib.sessions.backends.db",
                 "django.template.backends.django", "django.contrib.auth.backends",
                 "corsheaders", "rest_framework", "rest_framework.authtoken"]
for package in ("corsheaders", "whitenoise", "rest_framework"):
    hiddenimports += collect_submodules(package, on_error="ignore")
for package in ("apps", "alfred_ai"):
    for file in (root / package).rglob("*.py"):
        if "__pycache__" in file.parts:
            continue
        relative = file.relative_to(root)
        module = ".".join(relative.with_suffix("").parts)
        hiddenimports.append(module.removesuffix(".__init__"))
        if "migrations" in relative.parts:
            datas.append((str(file), str(relative.parent)))
# These engines are imported dynamically or by the isolated OCR worker.
for package in ("rapidocr_onnxruntime", "onnxruntime"):
    package_data, package_binaries, package_imports = collect_all(package)
    datas += package_data
    binaries += package_binaries
    hiddenimports += package_imports
for package in ("huey", "diskcache", "waitress", "django", "djangorestframework"):
    datas += copy_metadata(package)
datas += collect_data_files("rest_framework")

analysis = Analysis(
    [str(root / "alfred_native.py")], pathex=[str(root)],
    binaries=binaries, datas=datas, hiddenimports=hiddenimports,
    hookspath=[str(root / "packaging" / "hooks")],
    excludes=["pytest", "IPython", "jupyter", "notebook", "selenium", "tensorboard"],
    noarchive=False,
)
pyz = PYZ(analysis.pure)
exe = EXE(pyz, analysis.scripts, [], exclude_binaries=True, name="ALFRED",
          console=True, disable_windowed_traceback=False, upx=False)
coll = COLLECT(exe, analysis.binaries, analysis.datas, strip=False, upx=False, name="ALFRED")
