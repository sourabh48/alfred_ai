"""Collect Django without the stock hook's automatic live-db.sqlite3 inclusion."""
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

hiddenimports = collect_submodules("django", on_error="ignore")
datas = collect_data_files("django")
datas += collect_data_files("django", include_py_files=True, includes=["**/migrations/*.py"])
