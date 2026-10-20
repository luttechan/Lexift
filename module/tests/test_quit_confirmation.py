import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtGui import QCloseEvent
from localized_dialogs import QMessageBox
import app
from i18n import LANGUAGES, set_language, tr


class QuitConfirmationTests(unittest.TestCase):
    def setUp(self):
        platform = patch.object(app.sys, 'platform', 'linux')
        platform.start()
        self.addCleanup(platform.stop)
        self.controller = app.KanaShiftController.__new__(app.KanaShiftController)
        self.controller._stopping = False
        self.controller._confirming_quit = False
        self.controller._job = 3
        self.controller.overlay = Mock()
        self.controller.overlay._selection_revision = 2
        self.controller.cursor_indicator = Mock()
        self.controller.window = Mock()
        self.controller.window.isVisible.return_value = True
        self.controller.stop = Mock()
        set_language('ko')

    def tearDown(self):
        set_language('ko')

    def test_yes_quits_only_after_confirmation(self):
        with patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.Yes) as question:
            self.controller.request_quit()
        self.controller.stop.assert_called_once()
        args = question.call_args.args
        self.assertEqual(args[2], '정말로 종료하시겠습니까?')
        self.assertEqual(args[4], QMessageBox.StandardButton.No)

    def test_no_or_dismiss_keeps_app_running_and_allows_retry(self):
        for answer in (QMessageBox.StandardButton.No, QMessageBox.StandardButton.NoButton):
            with patch.object(QMessageBox, 'question', return_value=answer):
                self.controller.request_quit()
            self.controller.stop.assert_not_called()
            self.assertFalse(self.controller._confirming_quit)

    def test_tray_confirmation_has_visible_independent_dialog(self):
        self.controller.window.isVisible.return_value = False
        with patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.No) as question:
            self.controller.request_quit()
        self.assertIsNone(question.call_args.args[0])

    def test_cold_tray_quit_uses_native_confirmation_without_constructing_pages(self):
        self.controller._window = None
        with patch.object(app.sys, 'platform', 'win32'), \
             patch.object(app, 'MainWindow', side_effect=AssertionError('unnecessary pages')), \
             patch.object(app, 'confirm_quit', return_value=False) as native, \
             patch.object(QMessageBox, 'question') as qt_dialog:
            self.controller.request_quit()
        native.assert_called_once()
        self.assertIsNone(native.call_args.args[0])
        qt_dialog.assert_not_called()
        self.controller.stop.assert_not_called()
        self.assertIsNone(self.controller._window)

    def test_native_yes_confirms_quit(self):
        self.controller._window = None
        with patch.object(app.sys, 'platform', 'win32'), \
             patch.object(app, 'confirm_quit', return_value=True):
            self.controller.request_quit()
        self.controller.stop.assert_called_once()

    def test_warm_window_uses_owned_native_dialog_without_qt_font_work(self):
        self.controller.window.winId.return_value = 12345
        with patch.object(app.sys, 'platform', 'win32'), \
             patch.object(app, 'confirm_quit', return_value=False) as native, \
             patch.object(QMessageBox, 'question', side_effect=AssertionError('Qt dialog initialization')):
            self.controller.request_quit()
        self.assertEqual(native.call_args.args[0].value, 12345)
        self.controller.stop.assert_not_called()

    def test_exit_never_waits_for_per_hook_acknowledgements(self):
        controller = self.controller
        del controller.stop
        controller.hook = Mock()
        controller.navigation_hook = Mock()
        controller.qt = Mock()
        controller.tray = Mock()
        controller.store = Mock()
        controller.updater = Mock()
        with patch.object(app, 'keyboard_service') as service:
            controller.stop()
            controller.stop()
        service.return_value.close.assert_called_once_with(wait=False)
        controller.hook.stop.assert_not_called()
        controller.navigation_hook.stop.assert_not_called()
        controller.tray.hide.assert_called_once()
        controller.store.sync.assert_called_once()
        controller.qt.quit.assert_called_once()

    def test_repeated_quit_does_not_open_nested_dialogs(self):
        def answer(*args):
            self.controller.request_quit()
            return QMessageBox.StandardButton.No
        with patch.object(QMessageBox, 'question', side_effect=answer) as question:
            self.controller.request_quit()
        question.assert_called_once()

    def test_pending_switch_and_selection_cancelled_before_modal(self):
        def answer(*args):
            self.assertEqual(self.controller._job, 4)
            self.assertEqual(self.controller.overlay._selection_revision, 3)
            self.controller.overlay.hide.assert_called_once()
            self.controller.cursor_indicator.dismiss.assert_called_once()
            return QMessageBox.StandardButton.No
        with patch.object(QMessageBox, 'question', side_effect=answer):
            self.controller.request_quit()

    def test_no_tray_close_can_be_cancelled_without_hiding_main_window(self):
        window = Mock()
        event = QCloseEvent()
        with patch.object(app.QSystemTrayIcon, 'isSystemTrayAvailable', return_value=False):
            app.MainWindow.closeEvent(window, event)
        self.assertFalse(event.isAccepted())
        window.hide.assert_not_called()
        window.quit_requested.emit.assert_called_once()

    def test_confirmation_translated_in_every_supported_language(self):
        for code, _ in LANGUAGES:
            set_language(code)
            self.assertTrue(tr('정말로 종료하시겠습니까?'))
            if code != 'ko':
                self.assertNotEqual(tr('정말로 종료하시겠습니까?'), '정말로 종료하시겠습니까?')
