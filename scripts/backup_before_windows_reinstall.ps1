<#
Back up ALFRED's private native data before reinstalling Windows.
Close ALFRED and its workers first. Keep the destination on a disk you will retain.
Example: .\scripts\backup_before_windows_reinstall.ps1 -Destination 'E:\ALFRED_PRIVATE_BACKUP' -Quiesced
The manifest contains private file paths; keep the whole backup private.
Source/Compose PostgreSQL installations use scripts/local_stack_ops.py backup instead.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$Destination,
    [switch]$Quiesced,
    [ValidateSet('Native', 'Source')][string]$Runtime = 'Native',
    [string[]]$AdditionalDataDirectory = @(),
    [string[]]$AdditionalPrivatePath = @(),
    [string]$PythonExecutable
)

$ErrorActionPreference = 'Stop'
$repoRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
if (-not $Quiesced) { throw 'Close ALFRED, workers, and training jobs, then explicitly pass -Quiesced.' }
if (-not $PythonExecutable) { $PythonExecutable = Join-Path $repoRoot '.venv\Scripts\python.exe' }
if (-not (Test-Path -LiteralPath $PythonExecutable -PathType Leaf)) { throw 'Project Python is missing. Pass -PythonExecutable with the existing project interpreter.' }

$env:ALFRED_REINSTALL_BACKUP_REPO = $repoRoot
$env:ALFRED_REINSTALL_BACKUP_DESTINATION = $Destination
$env:ALFRED_REINSTALL_BACKUP_RUNTIME = $Runtime
$env:ALFRED_REINSTALL_BACKUP_EXTRA = ConvertTo-Json -InputObject @($AdditionalDataDirectory) -Compress
$env:ALFRED_REINSTALL_BACKUP_PRIVATE = ConvertTo-Json -InputObject @($AdditionalPrivatePath) -Compress
try {
    @'
import ctypes
from datetime import datetime, timezone
import hashlib
import json
import logging
import os
from pathlib import Path
import shutil
import sqlite3
import sys
import uuid
from contextlib import ExitStack, closing

import environ

# django-environ can log an invalid line verbatim; local files can contain secrets.
logging.disable(logging.CRITICAL)


def inside(path, parent):
    return path == parent or parent in path.parents


def sha256(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def process_running(pid):
    if not isinstance(pid, int) or pid <= 0:
        return False
    if os.name == 'nt':
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.OpenProcess.argtypes = (ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong)
        kernel.OpenProcess.restype = ctypes.c_void_p
        kernel.WaitForSingleObject.argtypes = (ctypes.c_void_p, ctypes.c_ulong)
        kernel.CloseHandle.argtypes = (ctypes.c_void_p,)
        handle = kernel.OpenProcess(0x00100000, False, pid)
        if not handle:
            if ctypes.get_last_error() == 5:
                raise RuntimeError('Cannot establish whether a native writer has stopped.')
            return False
        try:
            return kernel.WaitForSingleObject(handle, 0) == 258
        finally:
            kernel.CloseHandle(handle)
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False


def local_environment(root):
    original = dict(os.environ)
    try:
        for path in (root / 'config/local.env', root / '.env'):
            if path.is_file():
                environ.Env.read_env(path, overwrite=False)
        return dict(os.environ)
    finally:
        os.environ.clear()
        os.environ.update(original)


def files_under(path):
    if not path.exists():
        return
    if path.is_symlink() or path.is_junction():
        raise RuntimeError('A data path is a link or junction; review it explicitly before backup.')
    if path.is_file():
        yield path
        return
    excluded = {'__pycache__', '.venv', 'venv', 'build', 'dist', '.pytest_cache',
                '.idea', '.vscode', '.cache', 'cache', 'diskcache', 'staticfiles',
                'screenshots', 'downloads', 'test-output', 'ocr_tmp', 'tmp', 'temp'}
    for current, folders, names in os.walk(path):
        current = Path(current)
        for name in folders[:]:
            child = current / name
            if child.is_symlink() or child.is_junction():
                raise RuntimeError('A data directory contains a link or junction; review it before backup.')
            if name.lower() in excluded:
                folders.remove(name)
        for name in names:
            source = current / name
            if source.is_symlink():
                raise RuntimeError('A data file is a symbolic link; review it before backup.')
            if source.suffix.lower() not in {'.pyc', '.pyo', '.tmp', '.temp', '.log'}:
                yield source


repo = Path(os.environ['ALFRED_REINSTALL_BACKUP_REPO']).resolve()
destination = Path(os.environ['ALFRED_REINSTALL_BACKUP_DESTINATION']).expanduser()
runtime = os.environ['ALFRED_REINSTALL_BACKUP_RUNTIME']
backup = None
locks = ExitStack()
manifest = {'version': 1, 'kind': 'pre_windows_private_backup', 'complete': False,
            'runtime': runtime.lower(), 'generated_at_utc': datetime.now(timezone.utc).isoformat(),
            'sources': [], 'files': [], 'excluded': ['virtual environments', 'build/dist',
            'browser and IDE caches', 'logs', 'temporary OCR files', 'native cache/static/locks/control files']}
try:
    if not destination.is_absolute():
        raise RuntimeError('Backup destination must be an explicit absolute path outside the repository.')
    destination = destination.resolve()
    if inside(destination, repo):
        raise RuntimeError('Backup destination cannot be the repository or any repository descendant.')
    roots = [repo]
    configured = os.environ.get('ALFRED_DATA_DIR')
    if configured:
        roots.append(Path(configured).expanduser().resolve())
    if os.environ.get('LOCALAPPDATA'):
        packaged = Path(os.environ['LOCALAPPDATA']) / 'ALFRED'
        if packaged.exists():
            roots.append(packaged.resolve())
    roots.extend(Path(p).expanduser().resolve() for p in json.loads(os.environ['ALFRED_REINSTALL_BACKUP_EXTRA']))
    roots = list(dict.fromkeys(roots))
    selected = []
    seen = set()
    for index, root in enumerate(roots):
        if inside(destination, root):
            raise RuntimeError('Backup destination cannot be inside a source data directory.')
        if not root.is_dir():
            raise RuntimeError('An explicitly selected data directory is missing.')
        state_path = root / 'artifacts/native/runtime.json'
        if state_path.exists():
            state = json.loads(state_path.read_text(encoding='utf-8-sig'))
            if state.get('status') != 'stopped' and any(process_running(state.get(k)) for k in ('pid', 'worker_pid')):
                raise RuntimeError('A native supervisor or worker is still running; stop ALFRED before backup.')
        # Reuse the native launcher's OS lock convention, including absent locks.
        lock_directory = root / 'artifacts/native'
        for path in (root / 'artifacts', lock_directory):
            if path.is_symlink() or path.is_junction():
                raise RuntimeError('A native lock directory is a link or junction; review it before backup.')
        lock_directory.mkdir(parents=True, exist_ok=True)
        for lock_name in ('instance.lock', 'worker.lock'):
            lock_path = lock_directory / lock_name
            if lock_path.is_symlink() or lock_path.is_junction():
                raise RuntimeError('A native lock file is a link or junction; review it before backup.')
            stream = locks.enter_context(lock_path.open('a+b'))
            stream.seek(0)
            if not stream.read(1):
                stream.write(b'0')
                stream.flush()
            stream.seek(0)
            if os.name == 'nt':
                import msvcrt
                try:
                    msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                except OSError:
                    raise RuntimeError('A native runtime lock is held; close ALFRED and its worker.')
            else:
                import fcntl
                try:
                    fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                except OSError:
                    raise RuntimeError('A native runtime lock is held; close ALFRED and its worker.')
        values = local_environment(root)
        engine = values.get('DB_ENGINE', 'django.db.backends.sqlite3')
        database = root / 'db.sqlite3'
        if runtime == 'Source':
            if values.get('DATABASE_URL'):
                engine = environ.Env.db_url_config(values['DATABASE_URL'])['ENGINE']
                database = Path(environ.Env.db_url_config(values['DATABASE_URL'])['NAME'])
            else:
                database = Path(values.get('DB_NAME', str(repo / 'db.sqlite3')))
            if 'sqlite' not in engine:
                raise RuntimeError('Source runtime uses a non-SQLite database. Use the existing local_stack_ops.py backup for Compose; no partial backup is accepted.')
            if str(database) == ':memory:':
                raise RuntimeError('An in-memory database cannot preserve operator data.')
            database = database if database.is_absolute() else repo / database
        label = 'repository-runtime' if root == repo else f'external-runtime-{index:02d}'
        manifest['sources'].append({'label': label, 'original_root': str(root),
                                    'database_engine': 'sqlite3', 'configured_source_engine': engine})
        candidates = [(database, Path('db.sqlite3'), True),
                      (root / 'artifacts/native/jobs.sqlite3', Path('artifacts/native/jobs.sqlite3'), True)]
        # Uploaded media can be irreplaceable; preserve it conservatively.
        for group in ('media', 'config', 'ml_models', 'backups', 'artifacts/backups'):
            for source in files_under(root / group):
                if group == 'config' and ('example' in source.name.lower() or source.suffix == '.pyc'):
                    continue
                candidates.append((source, source.relative_to(root), False))
        for source in root.glob('.env*'):
            if source.is_file() and 'example' not in source.name.lower():
                candidates.append((source, Path(source.name), False))
        for source in root.glob('gmail_token_*.json'):
            candidates.append((source, Path(source.name), False))
        for key, fallback in (('ALFRED_REGISTRY_PATH', 'ml_models/alfred/model_registry'),
                              ('ALFRED_PERSONALITY_PATH', 'ml_models/alfred/personality')):
            extra = Path(values.get(key, str(root / fallback))).expanduser()
            extra = extra if extra.is_absolute() else root / extra
            extra = extra.resolve()
            if inside(destination, extra):
                raise RuntimeError('Backup destination is inside a configured model/state directory.')
            if not inside(extra, root):
                for source in files_under(extra):
                    candidates.append((source, Path('configured-state') / key / source.relative_to(extra), False))
        for source, relative, is_database in candidates:
            if not source.exists():
                continue
            if source.is_symlink() or source.is_junction():
                raise RuntimeError('Backup source is a link or junction; review it explicitly.')
            source = source.resolve()
            if source in seen:
                continue
            if source.is_symlink() or not source.is_file():
                raise RuntimeError('Backup source is not a regular file.')
            seen.add(source)
            selected.append((source, Path(label) / relative, is_database))
    # Explicitly reviewed external items, e.g. an inactive Docker data disk or Git access key.
    for index, value in enumerate(json.loads(os.environ['ALFRED_REINSTALL_BACKUP_PRIVATE'])):
        private_path = Path(value).expanduser().resolve()
        if not private_path.exists():
            raise RuntimeError('An explicitly selected private path is missing.')
        if inside(destination, private_path):
            raise RuntimeError('Backup destination is inside an additional private source.')
        for source in files_under(private_path):
            if source.resolve() in seen:
                continue
            relative = source.relative_to(private_path) if private_path.is_dir() else Path(source.name)
            seen.add(source.resolve())
            selected.append((source.resolve(), Path(f'additional-private-{index:02d}') / relative, False))
    if not selected:
        raise RuntimeError('No valuable private data was detected; review the actual data directory.')
    destination.mkdir(parents=True, exist_ok=True)
    backup = destination / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8])
    backup.mkdir(exist_ok=False)
    for source, relative, is_database in selected:
        target = backup / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        before = (source.stat().st_size, source.stat().st_mtime_ns, sha256(source))
        if is_database:
            # SQLite's backup API includes committed WAL data, unlike a raw database copy.
            target.touch(exist_ok=False)
            with closing(sqlite3.connect(source.as_uri() + '?mode=ro', uri=True, timeout=30)) as src:
                with closing(sqlite3.connect(target)) as dst:
                    src.backup(dst)
                    if dst.execute('PRAGMA integrity_check').fetchone() != ('ok',):
                        raise RuntimeError('SQLite backup failed its integrity check.')
        else:
            with source.open('rb') as incoming, target.open('xb') as outgoing:
                shutil.copyfileobj(incoming, outgoing)
            shutil.copystat(source, target)
        after = (source.stat().st_size, source.stat().st_mtime_ns, sha256(source))
        if before != after:
            raise RuntimeError('A source file changed during backup; keep writers closed and rerun.')
        checksum = sha256(target)
        if not is_database and checksum != before[2]:
            raise RuntimeError('Copied file checksum differs from the source.')
        manifest['files'].append({'original_path': str(source), 'backup_path': relative.as_posix(),
                                  'bytes': target.stat().st_size, 'sha256': checksum,
                                  'sqlite_snapshot': is_database})
    # Re-read every copied file before declaring completion.
    for record in manifest['files']:
        if sha256(backup / record['backup_path']) != record['sha256']:
            raise RuntimeError('Final backup SHA256 verification failed.')
    manifest['complete'] = True
    manifest['verified_at_utc'] = datetime.now(timezone.utc).isoformat()
    manifest['file_count'] = len(manifest['files'])
    manifest['total_bytes'] = sum(r['bytes'] for r in manifest['files'])
    (backup / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'complete': True, 'backup_directory': str(backup), 'file_count': manifest['file_count'],
                      'total_bytes': manifest['total_bytes'], 'sha256_verified': True}))
except Exception as exc:
    if backup is not None:
        manifest['complete'] = False
        (backup / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    # Exception text from a parser/driver may contain credentials; print only our safe errors.
    print(json.dumps({'complete': False, 'error': str(exc) if isinstance(exc, RuntimeError) else type(exc).__name__,
                      'backup_directory': str(backup) if backup else None}))
    sys.exit(1)
finally:
    locks.close()
'@ | & $PythonExecutable -
    if ($LASTEXITCODE -ne 0) { throw 'Private backup failed. Any partial timestamp directory is marked incomplete; do not use it for recovery.' }
} finally {
    Remove-Item Env:ALFRED_REINSTALL_BACKUP_REPO,Env:ALFRED_REINSTALL_BACKUP_DESTINATION,Env:ALFRED_REINSTALL_BACKUP_RUNTIME,Env:ALFRED_REINSTALL_BACKUP_EXTRA,Env:ALFRED_REINSTALL_BACKUP_PRIVATE -ErrorAction SilentlyContinue
}
