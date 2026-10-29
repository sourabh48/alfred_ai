"""Boundary checks that do not require the long-running native integration drill."""
import os
import json
import socket
import threading
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from django.test import SimpleTestCase, override_settings
from alfred_ai.services.ocr_process import ocr_command
from apps.integrations.models import _encrypt_token, _decrypt_token
from alfred_native import InstanceLock, data_directory, parent_is_running, stop, write_json
from alfred_ai.services.native_web import create_native_server
from scripts.verify_native_runtime import runtime_dashboard


class NativeRuntimeBoundaryTests(SimpleTestCase):
    def test_native_travel_fence_rejects_external_dns_connect_and_local_ollama(self):
        import subprocess
        import sys
        from scripts.verify_native_travel import isolated_environment, allowed_address
        self.assertTrue(allowed_address('127.0.0.1', 8046))
        self.assertTrue(allowed_address('::1', 8046))
        for host, port in (('example.invalid', 443), ('203.0.113.1', 443),
                           ('127.0.0.1', 11434), ('localhost', 11434), (None, None)):
            self.assertFalse(allowed_address(host, port))
        with TemporaryDirectory() as temporary, patch.dict(os.environ,
                {'OPENAI_API_KEY': 'synthetic-private-key', 'ALFRED_DATA_DIR': 'synthetic-operator-data'}):
            env = isolated_environment(Path(temporary))
            self.assertNotIn('OPENAI_API_KEY', env)
            self.assertNotIn('synthetic-operator-data', json.dumps(env))
            code = '''import socket
socket.getaddrinfo('0.0.0.0', 8080, type=socket.SOCK_STREAM)
for action in (lambda:socket.getaddrinfo('example.invalid',443),
               lambda:socket.gethostbyname('example.invalid'),
               lambda:socket.socket().bind(('0.0.0.0',0)),
               lambda:socket.create_connection(('203.0.113.1',443),timeout=.1),
               lambda:socket.create_connection(('127.0.0.1',11434),timeout=.1)):
    try: action()
    except PermissionError: continue
    raise AssertionError('Unfenced network boundary')
print('fence_pass')'''
            result = subprocess.run([sys.executable, '-c', code], env=env, capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), 'fence_pass')

    def test_dashboard_waits_for_one_explicit_quota_retry_within_existing_deadline(self):
        summary = {'current_month_net': 33000}
        success = Mock(status_code=200)
        success.json.return_value = {'summary': summary}
        session = Mock()
        session.get.side_effect = [Mock(status_code=429, headers={'Retry-After': '2'}), success]
        with patch('scripts.verify_native_runtime.time.sleep') as sleep, \
                patch('scripts.verify_native_runtime.time.monotonic', side_effect=[100, 101, 103]):
            self.assertEqual(runtime_dashboard(session, 'http://synthetic.invalid'), summary)
        sleep.assert_called_once_with(2)
        self.assertEqual([call.kwargs['timeout'] for call in session.get.call_args_list], [90, 87])
        success.raise_for_status.assert_called_once()

    def test_dashboard_rejects_unbounded_or_invalid_quota_waits(self):
        for header in ('', '0', '-1', '61', '1.5', 'nan', 'tomorrow', '9' * 100):
            with self.subTest(header=header), patch('scripts.verify_native_runtime.time.sleep') as sleep:
                session = Mock()
                session.get.return_value = Mock(status_code=429, headers={'Retry-After': header})
                with self.assertRaises(AssertionError):
                    runtime_dashboard(session, 'http://synthetic.invalid')
                sleep.assert_not_called()
                session.get.assert_called_once()

    def test_dashboard_keeps_http_and_response_contract_failures_visible(self):
        from requests.exceptions import HTTPError
        for code in (403, 500, 503):
            with self.subTest(code=code), patch('scripts.verify_native_runtime.time.sleep') as sleep:
                session = Mock()
                response = session.get.return_value = Mock(status_code=code)
                response.raise_for_status.side_effect = HTTPError('synthetic HTTP failure')
                with self.assertRaises(HTTPError):
                    runtime_dashboard(session, 'http://synthetic.invalid')
                sleep.assert_not_called()
                response.json.assert_not_called()
        session = Mock()
        session.get.return_value.status_code = 200
        session.get.return_value.json.return_value = {'detail': 'unexpected response'}
        with self.assertRaises(AssertionError):
            runtime_dashboard(session, 'http://synthetic.invalid')

    def test_dashboard_does_not_hide_persistent_throttling_or_exhausted_deadline(self):
        from requests.exceptions import HTTPError
        session = Mock()
        limited = Mock(status_code=429, headers={'Retry-After': '1'})
        limited.raise_for_status.side_effect = HTTPError('synthetic repeated quota')
        session.get.return_value = limited
        with patch('scripts.verify_native_runtime.time.sleep'), self.assertRaises(HTTPError):
            runtime_dashboard(session, 'http://synthetic.invalid')
        self.assertEqual(session.get.call_count, 2)
        with patch('scripts.verify_native_runtime.time.monotonic', side_effect=[100, 190]), \
                patch('scripts.verify_native_runtime.time.sleep') as sleep, self.assertRaises(AssertionError):
            runtime_dashboard(session, 'http://synthetic.invalid')
        sleep.assert_not_called()
        session.reset_mock()
        with patch('scripts.verify_native_runtime.time.monotonic', side_effect=[100, 101, 191]), \
                patch('scripts.verify_native_runtime.time.sleep'), self.assertRaises(AssertionError):
            runtime_dashboard(session, 'http://synthetic.invalid')
        session.get.assert_called_once()

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

    def test_stop_waits_for_both_locks_after_stopped_status_is_published(self):
        for finishing_worker in (False, True):
            with self.subTest(worker=finishing_worker), TemporaryDirectory() as directory:
                data = Path(directory)
                supervisor = InstanceLock(data); supervisor.__enter__()
                worker = InstanceLock(data, "worker.lock") if finishing_worker else None
                if worker:
                    worker.__enter__()
                releases = []
                def finish(_):
                    releases.append(True)
                    if len(releases) == 1:
                        supervisor.__exit__()
                    elif worker:
                        worker.__exit__()
                states = [{"status": "running", "instance": "synthetic"}] + [{"status": "stopped"}] * 3
                try:
                    with patch("alfred_native.read_state", side_effect=states), \
                         patch("alfred_native.time.monotonic", side_effect=[0, 0, 1, 2, 121]), \
                         patch("alfred_native.time.sleep", side_effect=finish) as pause:
                        self.assertEqual(stop(data), 0)
                        self.assertEqual(pause.call_count, 2 if worker else 1)
                finally:
                    supervisor.__exit__()
                    if worker:
                        worker.__exit__()

    def test_stop_does_not_claim_success_when_stopped_state_still_has_a_writer(self):
        with TemporaryDirectory() as directory:
            data = Path(directory)
            with InstanceLock(data), \
                 patch("alfred_native.read_state", side_effect=[
                     {"status": "running", "instance": "synthetic"}, {"status": "stopped"}]), \
                 patch("alfred_native.time.monotonic", side_effect=[0, 0, 121]), \
                 patch("alfred_native.time.sleep"):
                self.assertEqual(stop(data), 1)

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
