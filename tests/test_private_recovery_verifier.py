"""Private-backup checks use only disposable synthetic state."""
import importlib.util
import json
from pathlib import Path
import sqlite3
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
