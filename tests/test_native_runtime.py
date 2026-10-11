"""Boundary checks that do not require the long-running native integration drill."""
import os
import json
import socket
import threading
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings
from alfred_ai.services.ocr_process import ocr_command
from apps.integrations.models import _encrypt_token, _decrypt_token
from alfred_native import InstanceLock, data_directory, parent_is_running, write_json
from alfred_ai.services.native_web import create_native_server


class NativeRuntimeBoundaryTests(SimpleTestCase):
    def test_runtime_status_write_survives_a_brief_windows_reader_lock(self):
        with TemporaryDirectory(prefix='alfred-status-synthetic-') as directory:
            path=Path(directory)/'runtime.json'; path.write_text('{"status":"stopping"}',encoding='utf-8')
            reader=path.open('r',encoding='utf-8')
            release=threading.Timer(0.1,reader.close); release.start()
            try: write_json(path,{'status':'stopped'})
            finally: release.join(); reader.close()
            self.assertEqual(json.loads(path.read_text()),{'status':'stopped'})

    def test_persistent_status_permission_failure_is_bounded_and_preserves_previous_state(self):
        with TemporaryDirectory(prefix='alfred-status-synthetic-') as directory:
            path=Path(directory)/'runtime.json'; path.write_text('{"status":"stopping"}',encoding='utf-8')
            with patch('alfred_native.os.replace',side_effect=PermissionError('synthetic denied')) as replace,patch('alfred_native.time.sleep') as pause:
                with self.assertRaises(PermissionError): write_json(path,{'status':'stopped'})
            self.assertLessEqual(replace.call_count,10)
            self.assertLessEqual(sum(call.args[0] for call in pause.call_args_list),2)
            self.assertEqual(json.loads(path.read_text()),{'status':'stopping'})
            self.assertEqual(len(list(Path(directory).glob('*.tmp'))),1)

    def test_unexpected_status_write_failure_is_not_retried_or_hidden(self):
        with TemporaryDirectory(prefix='alfred-status-synthetic-') as directory:
            with patch('alfred_native.os.replace',side_effect=OSError('synthetic disk failure')),patch('alfred_native.time.sleep') as pause:
                with self.assertRaises(OSError): write_json(Path(directory)/'runtime.json',{'status':'stopped'})
                pause.assert_not_called()

    def test_listener_refuses_an_occupied_port(self):
        with socket.socket() as occupied:
            occupied.bind(("127.0.0.1", 0))
            occupied.listen(1)
            with self.assertRaises(OSError):
                create_native_server(lambda *_: [], occupied.getsockname()[1])

    def test_process_monitor_recognizes_its_own_process(self):
        self.assertTrue(parent_is_running(os.getpid()))
        self.assertFalse(parent_is_running(2147483647))

    def test_singleton_lock_releases_after_exit(self):
        with TemporaryDirectory() as directory:
            data = Path(directory)
            with InstanceLock(data):
                with self.assertRaises(OSError):
                    with InstanceLock(data):
                        self.fail("A second supervisor acquired the same data folder")
            with InstanceLock(data):
                pass

    def test_explicit_data_folder_wins_over_environment(self):
        with patch.dict(os.environ, {"ALFRED_DATA_DIR": "wrong-folder"}):
            self.assertEqual(data_directory("chosen-folder"), Path("chosen-folder").resolve())

    def test_packaged_ocr_uses_worker_entry_point(self):
        with patch("sys.frozen", True, create=True):
            result = ocr_command("document", "do not execute arbitrary source", "sample.pdf", 2)
        self.assertEqual(result[1:], ["--ocr-worker", "document", "sample.pdf", "2"])

    def test_email_tokens_survive_native_secret_rotation(self):
        with override_settings(SECRET_KEY="previous-key", SECRET_KEY_FALLBACKS=[]):
            token = _encrypt_token("synthetic-email-token")
        with override_settings(SECRET_KEY="new-native-key", SECRET_KEY_FALLBACKS=["previous-key"]):
            self.assertEqual(_decrypt_token(token), "synthetic-email-token")
            new_token = _encrypt_token("new-token")
        with override_settings(SECRET_KEY="new-native-key", SECRET_KEY_FALLBACKS=[]):
            self.assertEqual(_decrypt_token(new_token), "new-token")
