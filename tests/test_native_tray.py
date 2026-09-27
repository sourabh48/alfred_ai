"""Tray actions must follow the selected runtime and preserve graceful shutdown."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

from alfred_tray import NativeTray, start_tray


class NativeTrayTests(unittest.TestCase):
    def setUp(self):
        self.folder = TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        self.stop = Mock()
        self.record = Mock()
        self.tray = NativeTray(self.root, "test-instance", 8013, self.root, self.stop, self.record)

    def test_open_uses_actual_selected_port(self):
        with patch("alfred_tray.threading.Thread") as thread:
            self.tray.open_workspace()
            self.assertEqual(thread.call_args.kwargs["args"], ("http://127.0.0.1:8013/",))
            thread.return_value.start.assert_called_once()

    def test_stop_requests_graceful_shutdown_once_and_keeps_icon_until_complete(self):
        self.tray.icon = Mock(visible=True)
        self.tray.request_stop()
        self.tray.request_stop()
        self.stop.assert_called_once()
        self.tray.icon.stop.assert_not_called()
        self.assertTrue(self.tray.stopping)
        self.assertEqual(self.record.call_args.args[0]["status"], "stopping")
        with patch("alfred_tray.threading.Thread") as thread:
            self.tray.open_workspace()
            thread.assert_not_called()

    def test_guide_opens_bundled_local_html(self):
        guide = self.root / "guide" / "index.html"
        guide.parent.mkdir()
        guide.write_text("installation instructions")
        with patch("alfred_tray.webbrowser.open") as browser:
            self.tray.open_guide()
        browser.assert_called_once_with(guide.as_uri())

    def test_data_folder_action_preserves_spaces(self):
        with patch("alfred_tray.os.startfile", create=True) as open_folder:
            self.tray.open_data()
        open_folder.assert_called_once_with(str(self.root))

    def test_shutdown_ui_failure_does_not_prevent_application_shutdown(self):
        self.tray.icon = Mock(visible=True)
        self.tray.icon.update_menu.side_effect = OSError("shell unavailable")
        self.tray.icon.stop.side_effect = OSError("shell unavailable")
        self.tray.ready.set()
        with self.assertLogs(level="ERROR"):
            self.tray.request_stop()
            self.tray.close()
        self.stop.assert_called_once()
        self.assertEqual(self.record.call_args.args[0]["status"], "stopped")

    def test_no_tray_mode_does_not_launch_a_desktop_thread(self):
        with patch.dict("alfred_tray.os.environ", {"ALFRED_NO_TRAY": "1"}), \
             patch("alfred_tray.NativeTray") as tray_class:
            self.assertIsNone(start_tray(self.root, {}, self.root, self.stop, self.record))
        tray_class.assert_not_called()

    def test_close_during_startup_never_leaves_an_icon(self):
        icon = Mock()
        self.tray.closing.set()
        self.tray._setup(icon)
        icon.stop.assert_called_once()
        self.record.assert_not_called()
        self.assertTrue(self.tray.ready.is_set())
