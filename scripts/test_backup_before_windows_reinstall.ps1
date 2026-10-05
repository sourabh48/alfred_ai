# Synthetic backup checks only: never open or copy operator data.
[CmdletBinding()]
param([string]$PythonExecutable)
$ErrorActionPreference = 'Stop'
if (-not $PythonExecutable) { $PythonExecutable = Join-Path $PSScriptRoot '..\.venv\Scripts\python.exe' }
$env:ALFRED_BACKUP_TEST_SCRIPT = Join-Path $PSScriptRoot 'backup_before_windows_reinstall.ps1'
$env:ALFRED_BACKUP_TEST_POWERSHELL = (Get-Command powershell.exe -ErrorAction Stop).Source
try {
@'
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from contextlib import ExitStack, closing

with tempfile.TemporaryDirectory(prefix='alfred-private-backup-test-') as temporary, ExitStack() as connections:
    base = Path(temporary)
    repo = base / 'synthetic-repo'
    (repo / 'scripts').mkdir(parents=True)
    script = repo / 'scripts/backup_before_windows_reinstall.ps1'
    shutil.copyfile(os.environ['ALFRED_BACKUP_TEST_SCRIPT'], script)
    for name in ('config', 'media/uploads', 'ml_models/alfred/model_registry', 'artifacts/native/cache'):
        (repo / name).mkdir(parents=True)
    (repo / 'config/native.env').write_text('DJANGO_SECRET_KEY=synthetic-test-only\n')
    (repo / 'config/local.env').write_text('SYNTHETIC_PRIVATE_LINE_THAT_MUST_NOT_APPEAR\n')
    (repo / 'config/local.env.example').write_text('DJANGO_SECRET_KEY=placeholder\n')
    (repo / 'media/uploads/sample.pdf').write_bytes(b'synthetic private upload')
    (repo / 'ml_models/alfred/model_registry/registry.json').write_text('{}')
    (repo / 'artifacts/native/cache/disposable').write_text('exclude me')
    (repo / 'artifacts/native/server.log').write_text('exclude me')
    (repo / 'artifacts/native/runtime.json').write_text(json.dumps({'status': 'stopped'}))
    source = connections.enter_context(closing(sqlite3.connect(repo / 'db.sqlite3')))
    source.execute('PRAGMA journal_mode=WAL')
    source.execute('CREATE TABLE evidence (id INTEGER PRIMARY KEY, value TEXT)')
    source.execute("INSERT INTO evidence(value) VALUES ('committed WAL row')")
    source.commit()  # keep connection open so committed data remains in WAL
    with closing(sqlite3.connect(repo / 'artifacts/native/jobs.sqlite3')) as queue:
        with queue:
            queue.execute('CREATE TABLE pending (id INTEGER PRIMARY KEY)')
            queue.execute('INSERT INTO pending VALUES (7)')
    extra = base / 'reviewed-private-disk.vhdx'
    extra.write_bytes(b'synthetic historical disk')
    env = dict(os.environ, LOCALAPPDATA=str(base / 'synthetic-localappdata'))
    for name in ('ALFRED_DATA_DIR', 'DB_ENGINE', 'DB_NAME', 'DATABASE_URL', 'ALFRED_REGISTRY_PATH', 'ALFRED_PERSONALITY_PATH'):
        env.pop(name, None)

    def run(destination, *arguments):
        return subprocess.run([os.environ['ALFRED_BACKUP_TEST_POWERSHELL'], '-NoProfile', '-ExecutionPolicy', 'Bypass',
                               '-File', str(script), '-Destination', str(destination), '-PythonExecutable', sys.executable,
                               *arguments], capture_output=True, text=True, env=env)

    destination = base / 'synthetic-backups'
    result = run(destination, '-Quiesced', '-AdditionalPrivatePath', str(extra))
    assert result.returncode == 0, 'Synthetic backup did not complete.'
    # First-ever native start must also be blocked while backing up retained data.
    for name in ('instance.lock', 'worker.lock'):
        assert (repo / 'artifacts/native' / name).read_bytes() == b'0'
    assert 'SYNTHETIC_PRIVATE_LINE_THAT_MUST_NOT_APPEAR' not in result.stdout + result.stderr
    backups = list(destination.iterdir())
    assert len(backups) == 1
    backup = backups[0]
    manifest = json.loads((backup / 'manifest.json').read_text())
    assert manifest['complete'] is True and manifest['file_count'] == 7
    for entry in manifest['files']:
        with (backup / entry['backup_path']).open('rb') as stream:
            assert hashlib.file_digest(stream, 'sha256').hexdigest() == entry['sha256']
    with closing(sqlite3.connect(backup / 'repository-runtime/db.sqlite3')) as restored:
        assert restored.execute('SELECT value FROM evidence').fetchone() == ('committed WAL row',)
    with closing(sqlite3.connect(backup / 'repository-runtime/artifacts/native/jobs.sqlite3')) as restored:
        assert restored.execute('SELECT id FROM pending').fetchone() == (7,)
    assert not (backup / 'repository-runtime/artifacts/native/cache').exists()
    assert not (backup / 'repository-runtime/config/local.env.example').exists()
    assert run(repo / 'unsafe-backups', '-Quiesced').returncode != 0
    assert not (repo / 'unsafe-backups').exists()
    assert run(base / 'not-quiesced').returncode != 0
    assert not (base / 'not-quiesced').exists()
    (repo / 'artifacts/native/runtime.json').write_text(json.dumps({'status': 'running', 'pid': os.getpid()}))
    assert run(base / 'active-writer', '-Quiesced').returncode != 0
    assert not (base / 'active-writer').exists()
    (repo / 'artifacts/native/runtime.json').write_text(json.dumps({'status': 'stopped'}))
    if os.name == 'nt':
        import msvcrt
        with (repo / 'artifacts/native/worker.lock').open('r+b') as lock:
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
            assert run(base / 'held-native-lock', '-Quiesced').returncode != 0
            assert not (base / 'held-native-lock').exists()
    (repo / 'config/local.env').write_text('DB_ENGINE=django.db.backends.postgresql\n')
    assert run(base / 'wrong-engine', '-Quiesced', '-Runtime', 'Source').returncode != 0
    assert not (base / 'wrong-engine').exists()
    source.close()
    print(json.dumps({'passed': True, 'checks': ['committed WAL snapshot', 'durable queue', 'config/media/model/external file hashes',
          'generated exclusions', 'missing native lock creation', 'held native lock refusal',
          'repository destination refusal', 'quiescence required', 'active writer refusal', 'non-SQLite refusal'],
          'operator_data_accessed': False}))
'@ | & $PythonExecutable -
if ($LASTEXITCODE -ne 0) { throw 'Synthetic backup checks failed.' }
} finally {
    Remove-Item Env:ALFRED_BACKUP_TEST_SCRIPT,Env:ALFRED_BACKUP_TEST_POWERSHELL -ErrorAction SilentlyContinue
}
