"""Private-backup checks use only disposable synthetic state."""
import importlib.util
import json
from pathlib import Path
import sqlite3
import shutil
from tempfile import TemporaryDirectory
import unittest
from contextlib import closing

spec = importlib.util.spec_from_file_location('recovery_verifier', Path(__file__).parents[1] / 'scripts/verify_private_recovery.py')
recovery = importlib.util.module_from_spec(spec)
spec.loader.exec_module(recovery)


class PrivateRecoveryVerifierTests(unittest.TestCase):
    def make_backup(self, root):
        database = root / 'repository-runtime/db.sqlite3'
        database.parent.mkdir()
        with closing(sqlite3.connect(database)) as connection, connection:
            connection.execute('CREATE TABLE proof (value TEXT)')
            connection.execute("INSERT INTO proof VALUES ('synthetic')")
        record = {'backup_path': 'repository-runtime/db.sqlite3', 'original_path': str(database),
                  'bytes': database.stat().st_size, 'sha256': recovery.checksum(database), 'sqlite_snapshot': True}
        manifest = {'complete': True, 'file_count': 1, 'total_bytes': record['bytes'], 'files': [record]}
        (root / 'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
        return manifest

    def test_hash_sqlite_and_private_internal_metadata(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_backup(root)
            result = recovery.verify(root, check_originals=True, source_head='a' * 40)
            self.assertEqual(result['sqlite_quick_check'], 'PASS')
            self.assertEqual(result['database_count'], 1)
            self.assertNotIn('original_path', json.dumps(result))
            internal = json.loads((root / 'backup-manifest.json').read_text())
            self.assertIn('original_sha256', internal['files'][0])
            self.assertTrue(recovery.verify(root, expected_source_head='a' * 40)['complete'])
            with self.assertRaises(ValueError):
                recovery.verify(root, expected_source_head='b' * 40)

    def test_corrupt_file_and_incomplete_manifest_refused(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = self.make_backup(root)
            (root / 'repository-runtime/db.sqlite3').write_bytes(b'changed')
            with self.assertRaises(ValueError):
                recovery.verify(root)
            manifest['complete'] = False
            (root / 'manifest.json').write_text(json.dumps(manifest))
            with self.assertRaises(ValueError):
                recovery.verify(root)

    def test_escaping_or_duplicate_manifest_path_refused(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = self.make_backup(root)
            manifest['files'][0]['backup_path'] = '../outside.sqlite3'
            (root / 'manifest.json').write_text(json.dumps(manifest))
            with self.assertRaises(ValueError):
                recovery.verify(root)
            manifest['files'][0]['backup_path'] = 'repository-runtime/db.sqlite3'
            manifest['files'].append(dict(manifest['files'][0]))
            manifest['file_count'] = 2
            (root / 'manifest.json').write_text(json.dumps(manifest))
            with self.assertRaises(ValueError):
                recovery.verify(root)

    def test_historical_wal_database_checked_without_changing_retained_bytes(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            original = root / 'original' / 'history.sqlite3'
            original.parent.mkdir()
            # Keep a writer open so committed data remains in its WAL.
            with closing(sqlite3.connect(original)) as connection:
                connection.execute('PRAGMA journal_mode=WAL')
                connection.execute('CREATE TABLE proof (value TEXT)')
                connection.execute("INSERT INTO proof VALUES ('synthetic')")
                connection.commit()
                backup = root / 'additional-private-01'
                backup.mkdir()
                originals = [original, Path(str(original) + '-wal'), Path(str(original) + '-shm')]
                records = []
                for path in originals:
                    target = backup / path.name
                    shutil.copyfile(path, target)
                    records.append({'backup_path': target.relative_to(root).as_posix(),
                                    'original_path': str(path), 'bytes': target.stat().st_size,
                                    'sha256': recovery.checksum(target), 'sqlite_snapshot': False})
                manifest = {'complete': True, 'file_count': len(records),
                            'total_bytes': sum(r['bytes'] for r in records), 'files': records}
                manifest_path = root / 'manifest.json'
                manifest_path.write_text(json.dumps(manifest))
                retained = originals + [backup / path.name for path in originals]
                before = {path: path.read_bytes() for path in retained}
                self.assertEqual(recovery.verify(root, check_originals=True)['database_count'], 1)
                self.assertEqual(before, {path: path.read_bytes() for path in retained})
                # Backup-API snapshots merge WAL data; their source WAL stays private.
                snapshot = root / 'snapshot.sqlite3'
                with closing(sqlite3.connect(snapshot)) as target:
                    connection.backup(target)
                snapshot_record = {'backup_path': snapshot.name, 'original_path': str(original),
                                   'bytes': snapshot.stat().st_size, 'sha256': recovery.checksum(snapshot),
                                   'sqlite_snapshot': True}
                snapshot_manifest = {'complete': True, 'file_count': 1,
                                     'total_bytes': snapshot_record['bytes'], 'files': [snapshot_record]}
                manifest_path.write_text(json.dumps(snapshot_manifest))
                empty_wal = Path(str(snapshot) + '-wal')
                empty_wal.write_bytes(b'')
                snapshot_before = {path: path.read_bytes() for path in retained + [snapshot, empty_wal]}
                recovery.verify(root, check_originals=True, source_head='a' * 40)
                internal = json.loads((root / 'backup-manifest.json').read_text())
                self.assertEqual(internal['files'][0]['original_wal_sha256'], recovery.checksum(originals[1]))
                self.assertEqual(snapshot_before, {path: path.read_bytes() for path in snapshot_before})
                snapshot_record['original_path'] = str(snapshot)
                manifest_path.write_text(json.dumps(snapshot_manifest))
                self.assertTrue(recovery.verify(root, check_originals=True)['complete'])
                # A WAL on disk must not be silently used outside the manifest.
                missing_wal = dict(manifest, files=[r for r in records if not r['backup_path'].endswith('-wal')])
                missing_wal['file_count'] = len(missing_wal['files'])
                missing_wal['total_bytes'] = sum(r['bytes'] for r in missing_wal['files'])
                manifest_path.write_text(json.dumps(missing_wal))
                with self.assertRaises(ValueError):
                    recovery.verify(root)
                manifest_path.write_text(json.dumps(manifest))
                # Even a hash-valid historical DB must pass the SQLite check.
                invalid = backup / original.name
                Path(str(invalid) + '-wal').unlink()
                invalid.write_bytes(b'not a sqlite database')
                records[0].update(bytes=invalid.stat().st_size, sha256=recovery.checksum(invalid))
                manifest.update(files=[records[0]], file_count=1, total_bytes=records[0]['bytes'])
                manifest_path.write_text(json.dumps(manifest))
                with self.assertRaises(sqlite3.DatabaseError):
                    recovery.verify(root)
