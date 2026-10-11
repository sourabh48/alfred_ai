"""Verify a private backup without displaying its filenames or contents."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
from contextlib import closing
from tempfile import TemporaryDirectory


def checksum(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def check_sqlite(path, verified_paths):
    wal = Path(str(path) + '-wal')
    nonempty_wal = wal.exists() and wal.stat().st_size > 0
    if nonempty_wal and wal.resolve() not in verified_paths:
        raise ValueError('SQLite WAL is absent from the verified manifest.')
    # SQLite may rewrite shared-memory state even on a read-only connection.
    # Rebuild it in a disposable directory, preserving every retained byte.
    with TemporaryDirectory(prefix='alfred-sqlite-check-') as temporary:
        shadow = Path(temporary) / 'database.sqlite3'
        shutil.copyfile(path, shadow)
        if nonempty_wal:
            shutil.copyfile(wal, Path(str(shadow) + '-wal'))
        with closing(sqlite3.connect(shadow.as_uri() + '?mode=ro', uri=True)) as database:
            if database.execute('PRAGMA quick_check').fetchall() != [('ok',)]:
                raise ValueError('Private database integrity check failed.')


def verify(directory, check_originals=False, source_head=None, expected_source_head=None):
    root = Path(directory).resolve()
    manifest = json.loads((root / 'manifest.json').read_text(encoding='utf-8-sig'))
    records = manifest.get('files', [])
    if not manifest.get('complete') or not records or len(records) != manifest.get('file_count'):
        raise ValueError('Incomplete private manifest.')
    names = set()
    verified_paths = set()
    original_paths = set()
    total = databases = 0
    for record in records:
        relative = record['backup_path']
        target = (root / relative).resolve()
        if not target.is_relative_to(root) or target == root or relative in names:
            raise ValueError('Unsafe or duplicate manifest path.')
        names.add(relative)
        if not target.is_file() or target.stat().st_size != record['bytes'] or checksum(target) != record['sha256']:
            raise ValueError('Private backup hash or size mismatch.')
        verified_paths.add(target)
        total += record['bytes']
        if check_originals:
            original = Path(record['original_path']).resolve()
            record['original_sha256'] = checksum(original)
            record['original_modified_utc_ns'] = original.stat().st_mtime_ns
            original_paths.add(original)
            if record.get('sqlite_snapshot'):
                wal = Path(str(original) + '-wal')
                if wal.is_file() and wal.stat().st_size > 0:
                    # SQLite's backup API already merged this original WAL.
                    # Keep its verification evidence inside the private record.
                    record['original_wal_sha256'] = checksum(wal)
                    record['original_wal_modified_utc_ns'] = wal.stat().st_mtime_ns
                    original_paths.add(wal.resolve())
            if not record.get('sqlite_snapshot') and record['original_sha256'] != record['sha256']:
                raise ValueError('Original private file changed after backup.')
    if total != manifest.get('total_bytes'):
        raise ValueError('Private manifest total differs.')
    # Validate all sidecar hashes before SQLite sees any historical database.
    for record in records:
        target = (root / record['backup_path']).resolve()
        if record.get('sqlite_snapshot') or target.suffix.lower() in {'.sqlite3', '.sqlite', '.db'}:
            check_sqlite(target, verified_paths)
            databases += 1
            if check_originals:
                check_sqlite(Path(record['original_path']).resolve(), original_paths)
    if expected_source_head:
        internal = json.loads((root / 'backup-manifest.json').read_text(encoding='utf-8-sig'))
        if internal.get('source_git_head') != expected_source_head:
            raise ValueError('Encrypted source checkpoint differs from public metadata.')
    included = {
        'source_runtime': any(n.startswith('repository-runtime/') for n in names),
        'frozen_runtime': any(n.startswith('external-runtime-01/') for n in names),
        'database': {'repository-runtime/db.sqlite3', 'external-runtime-01/db.sqlite3'} <= names,
        'media': any(n.startswith('repository-runtime/media/') for n in names),
        'config': {'repository-runtime/config/local.env', 'repository-runtime/config/native.env',
                   'external-runtime-01/config/native.env'} <= names,
        'native_queue': {'repository-runtime/artifacts/native/jobs.sqlite3',
                         'external-runtime-01/artifacts/native/jobs.sqlite3'} <= names,
        'ml_state': any('/ml_models/' in n for n in names),
        'docker_vhdx': 'additional-private-00/ext4.vhdx' in names,
    }
    if source_head:
        if len(source_head) != 40 or any(c not in '0123456789abcdef' for c in source_head):
            raise ValueError('Invalid source commit.')
        # Detailed filenames and original locations remain INSIDE the encrypted archive.
        manifest['source_git_head'] = source_head
        (root / 'backup-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    return {'complete': True, 'sha256_verified': True, 'sqlite_quick_check': 'PASS',
            'file_count': len(records), 'total_bytes': total, 'database_count': databases,
            'included': included}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--backup-directory', required=True)
    parser.add_argument('--check-originals', action='store_true')
    parser.add_argument('--source-head')
    parser.add_argument('--expected-source-head')
    args = parser.parse_args()
    try:
        print(json.dumps(verify(args.backup_directory, args.check_originals, args.source_head, args.expected_source_head)))
    except Exception:
        # Driver/parser exceptions can include private values and paths.
        print(json.dumps({'complete': False, 'error': 'Private manifest, hash or database validation failed.'}))
        raise SystemExit(1)
