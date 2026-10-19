import json
import tempfile
import time
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import Mock, patch

from PySide6.QtCore import QEvent, QObject, QSettings, QTimer
from PySide6.QtWidgets import QApplication, QMessageBox, QPushButton
import app
from i18n import set_language
from layout_profiles import create_layout


class PaintProbe(QObject):
    def __init__(self):
        super().__init__()
        self.first_paint = None

    def eventFilter(self, watched, event):
        if event.type() == QEvent.Type.Paint and self.first_paint is None:
            self.first_paint = time.perf_counter()
        return False


class QuitDisplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qt = QApplication.instance() or QApplication([])
        cls.qt.setQuitOnLastWindowClosed(False)

    def setUp(self):
        set_language('ko')
        self.stack = ExitStack()
        self.directory = self.stack.enter_context(tempfile.TemporaryDirectory())
        store = QSettings(str(Path(self.directory) / 'prefs.ini'), QSettings.Format.IniFormat)
        layout = create_layout(0x0412)
        store.setValue('profiles/slots_json', json.dumps([dict(hkl=layout.hkl, mode='ko_hangul', name='Korean')]))
        self.stack.enter_context(patch.object(app, 'QSettings', return_value=store))
        self.stack.enter_context(patch.object(app, 'available_layouts', return_value=[layout]))
        self.controller = app.KanaShiftController(self.qt)
        self.controller._create_window()
        self.controller.stop = Mock()
        self.controller.window.show()
        self.qt.processEvents()
        self.dialog = self.controller._quit_dialog
        self.exit_button = next(button for button in self.controller.window.findChildren(QPushButton)
                                if button.text() == '종료' and button.parent() is not self.dialog)

    def tearDown(self):
        self.controller._quit_dialog.reject()
        self.controller.window.hide()
        self.controller.tray.hide()
        self.controller.window.deleteLater()
        self.controller.overlay.deleteLater()
        self.controller.cursor_indicator.deleteLater()
        self.qt.processEvents()
        self.stack.close()
        set_language('ko')

    def test_real_sidebar_click_paints_confirmation_and_keeps_event_loop_alive(self):
        probe = PaintProbe()
        self.dialog.installEventFilter(probe)
        heartbeat = []
        with patch.object(app.ctypes.windll.user32, 'MessageBoxW', side_effect=AssertionError('blocking native dialog')), \
             patch.object(QMessageBox, 'question', side_effect=AssertionError('nested Qt dialog')), \
             patch.object(app, 'QuitConfirmation', side_effect=AssertionError('dialog created during click')):
            started = time.perf_counter()
            self.exit_button.click()
            click_seconds = time.perf_counter() - started
            QTimer.singleShot(0, lambda: heartbeat.append(True))
            deadline = time.perf_counter() + 1
            while (probe.first_paint is None or not heartbeat) and time.perf_counter() < deadline:
                self.qt.processEvents()
        self.assertTrue(self.dialog.isVisible())
        self.assertTrue(self.controller._confirming_quit)
        self.assertLess(click_seconds, .3)
        self.assertIsNotNone(probe.first_paint)
        self.assertLess(probe.first_paint - started, .5)
        self.assertTrue(heartbeat)
        self.controller.stop.assert_not_called()

    def test_cancel_and_reopen_reuses_dialog_and_confirmation_still_required(self):
        self.exit_button.click()
        self.controller.request_quit()  # Duplicate requests cannot nest.
        self.dialog.cancel_button.click()
        self.assertFalse(self.controller._confirming_quit)
        self.assertFalse(self.dialog.isVisible())
        self.controller.stop.assert_not_called()
        self.exit_button.click()
        self.assertIs(self.controller._quit_dialog, self.dialog)
        self.dialog.quit_button.click()
        self.controller.stop.assert_called_once()

    def test_language_change_rebuilds_confirmation_before_next_click(self):
        self.controller.change_language('en')
        replacement = self.controller._quit_dialog
        self.assertIsNot(replacement, self.dialog)
        self.assertEqual(replacement.windowTitle(), 'Quit')
        self.controller.request_quit()
        self.assertTrue(replacement.isVisible())
        replacement.reject()
        self.controller.stop.assert_not_called()

    def test_hotkey_cannot_open_selector_while_confirmation_is_visible(self):
        self.exit_button.click()
        with patch.object(self.controller.overlay, 'open') as open_selector:
            self.controller._hotkey(12345)
            self.controller.show_overlay()
        open_selector.assert_not_called()
        self.assertTrue(self.dialog.isVisible())

    def test_language_change_preserves_unsaved_slots_with_one_editor_build(self):
        saved = [dict(slot) for slot in self.controller.slots]
        edits = [{**saved[0], 'mode':'ko_latin', 'name':'My English'},
                 {**saved[0], 'name':'수정 중인 이름'}]
        self.controller.window.slot_editor.set_slots(edits)
        rebuild = app.SlotEditor.rebuild
        with patch.object(app.SlotEditor,'rebuild',autospec=True,side_effect=rebuild) as builds:
            self.controller.change_language('en')
        self.assertEqual(builds.call_count,1)
        self.assertEqual(self.controller.window.slot_editor.slots,edits)
        self.assertEqual(self.controller.slots,saved)
