"""Source/debug storage protection with synthetic files and no live records."""
from contextlib import closing
import os
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
from unittest import TestCase, skipUnless
from unittest.mock import patch

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.test import override_settings

from alfred_ai.local_config import load_local_environment
from alfred_ai.services.upload_limits import PrivateTemporaryUploadHandler, UploadStorageUnavailable
from alfred_private_storage import (PrivateStorageUnavailable, acl_snapshot, current_sid,
    guard_sqlite_storage, private_directory, replace_acl, verify_private)


@skipUnless(os.name == "nt", "Windows source storage acceptance requires Windows")
class SourceStorageTests(TestCase):
    def test_source_startup_protects_media_before_preview_or_document_creation(self):
        from django.apps import apps
        with TemporaryDirectory() as directory,override_settings(MEDIA_ROOT=Path(directory)/'media'):
            apps.get_app_config('users').ready()
            self.assertTrue(verify_private(Path(settings.MEDIA_ROOT)))
            preview=Path(settings.MEDIA_ROOT)/'synthetic-preview.bin'
            preview.write_bytes(b'synthetic preview')
            self.assertTrue(verify_private(preview))

    def test_sqlite_and_test_directories_are_private_before_first_connection(self):
        with TemporaryDirectory() as directory:
            root=Path(directory)
            names=[root/'runtime/db.sqlite3',root/'browser-test/test.sqlite3']
            guard_sqlite_storage({'default':{'ENGINE':'django.db.backends.sqlite3','NAME':names[0],
                                            'TEST':{'NAME':names[1]}}})
            for path in names:
                self.assertTrue(verify_private(path.parent))
                self.assertFalse(path.exists())
                with closing(sqlite3.connect(path)) as db, db:
                    db.execute('CREATE TABLE synthetic(id INTEGER)')
                self.assertTrue(verify_private(path))
            guard_sqlite_storage({'default':{'ENGINE':'django.db.backends.sqlite3','NAME':names[0]}})

    def test_existing_public_sqlite_is_refused_without_acl_or_content_change(self):
        with TemporaryDirectory() as directory:
            root=private_directory(Path(directory))
            path=root/'synthetic.sqlite3';path.write_bytes(b'synthetic retained database')
            replace_acl(path,f'D:P(A;;FA;;;{current_sid()})(A;;FA;;;SY)(A;;FR;;;AU)')
            before=acl_snapshot(path)
            with self.assertRaises(PrivateStorageUnavailable):
                guard_sqlite_storage({'default':{'ENGINE':'django.db.backends.sqlite3','NAME':path}})
            self.assertEqual(acl_snapshot(path),before)
            self.assertEqual(path.read_bytes(),b'synthetic retained database')

    def test_memory_databases_skip_filesystem_and_disk_uri_cannot_bypass_guard(self):
        for name in (':memory:','file:memorydb_default?mode=memory&cache=shared'):
            with patch('alfred_private_storage.private_directory',side_effect=AssertionError('Memory has no disk path')):
                guard_sqlite_storage({'default':{'ENGINE':'django.db.backends.sqlite3','NAME':name}})
        with self.assertRaises(PrivateStorageUnavailable):
            guard_sqlite_storage({'default':{'ENGINE':'django.db.backends.sqlite3','NAME':'file:synthetic.db?mode=rw'}})

    def test_retained_media_uses_private_creation_and_preserves_path_contract(self):
        with TemporaryDirectory() as directory, override_settings(MEDIA_ROOT=Path(directory)/'media'):
            self.assertEqual(settings.STORAGES['default']['BACKEND'],'alfred_ai.storage.PrivateFileSystemStorage')
            name=default_storage.save('owned/synthetic.txt',ContentFile(b'synthetic private upload'))
            path=Path(default_storage.path(name))
            self.assertTrue(verify_private(path))
            self.assertEqual(default_storage.url(name),'/media/owned/synthetic.txt')
            self.assertEqual(path.read_bytes(),b'synthetic private upload')

    def test_existing_unsafe_media_is_refused_before_another_upload(self):
        with TemporaryDirectory() as directory, override_settings(MEDIA_ROOT=Path(directory)):
            root=Path(directory)
            replace_acl(root,f'D:P(A;OICI;FA;;;{current_sid()})(A;OICI;FA;;;SY)(A;OICI;FR;;;BU)')
            retained=root/'retained.fixture';retained.write_bytes(b'synthetic retained evidence')
            before=acl_snapshot(root)
            with self.assertRaises(PermissionError):
                default_storage.save('new.fixture',ContentFile(b'synthetic new evidence'))
            self.assertEqual(acl_snapshot(root),before)
            self.assertEqual(retained.read_bytes(),b'synthetic retained evidence')
            self.assertFalse((root/'new.fixture').exists())

    def test_streamed_temporary_upload_is_private_before_bytes_and_deleted_on_close(self):
        with TemporaryDirectory() as directory, override_settings(FILE_UPLOAD_TEMP_DIR=directory):
            handler=PrivateTemporaryUploadHandler()
            handler.new_file('upload','synthetic.txt','text/plain',9)
            path=Path(handler.file.temporary_file_path())
            self.assertTrue(verify_private(path))
            self.assertEqual(path.stat().st_size,0)
            handler.receive_data_chunk(b'synthetic',0)
            handler.file.flush()
            self.assertEqual(path.read_bytes(),b'synthetic')
            handler.file.close()
            self.assertFalse(path.exists())

    def test_unavailable_upload_permissions_fail_503_before_payload_write(self):
        with TemporaryDirectory() as directory, override_settings(FILE_UPLOAD_TEMP_DIR=directory):
            handler=PrivateTemporaryUploadHandler()
            with patch('alfred_ai.services.upload_limits.protect',side_effect=PrivateStorageUnavailable('synthetic denial')):
                with self.assertRaises(UploadStorageUnavailable) as failure:
                    handler.new_file('upload','synthetic.txt','text/plain',9)
            self.assertEqual(failure.exception.status_code,503)
            self.assertEqual(list(Path(directory).iterdir()),[])

    def test_config_read_requires_private_acl_without_printing_or_changing_values(self):
        with TemporaryDirectory() as directory:
            root=Path(directory);(root/'config').mkdir()
            path=root/'config/local.env';path.write_text('SYNTHETIC_ONLY=retained-fixture\n')
            replace_acl(path,f'D:P(A;;FA;;;{current_sid()})(A;;FA;;;SY)(A;;FR;;;AU)')
            before=acl_snapshot(path)
            with self.assertRaises(PermissionError):load_local_environment(root)
            self.assertEqual(acl_snapshot(path),before)
            self.assertEqual(path.read_text(),'SYNTHETIC_ONLY=retained-fixture\n')
