import tempfile
from pathlib import Path
import unittest
from unittest.mock import Mock, patch
from PySide6.QtCore import QSettings
from PySide6.QtGui import QInputMethodEvent
from PySide6.QtWidgets import QApplication
from ime_panel import CandidatePanel, PronunciationEdit
from hotkeys_windows import HotkeyBinding
from layout_profiles import create_layout
import app


class LiveCandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qt = QApplication.instance() or QApplication([])
        cls.qt.setQuitOnLastWindowClosed(False)

    def test_last_korean_syllable_is_searched_before_commit(self):
        search = PronunciationEdit()
        search.setText('와타')
        search.setCursorPosition(2)
        QApplication.sendEvent(search, QInputMethodEvent('시', []))
        self.assertEqual(search.effective_text(), '와타시')
        event = QInputMethodEvent()
        event.setCommitString('시')
        QApplication.sendEvent(search, event)
        self.assertEqual(search.effective_text(), '와타시')
        search.deleteLater()

    def test_stale_results_cannot_be_committed_after_editing(self):
        panel = CandidatePanel()
        panel._build()
        panel.search.setText('와타시')
        panel.displayed = '와타시'
        panel.candidates.addItem('私'); panel.candidates.setCurrentRow(0)
        self.assertEqual(panel._selection(), '私')
        panel.search.setText('니혼고')
        self.assertEqual(panel._selection(), '')
        self.assertEqual(panel.candidates.count(), 0)
        panel.close(); panel.window.deleteLater()

    def test_conflicting_settings_disable_both_apply_buttons(self):
        with tempfile.TemporaryDirectory() as directory:
            store = QSettings(str(Path(directory)/'prefs.ini'), QSettings.Format.IniFormat)
            window = app.MainWindow(store, [dict(hkl=create_layout(0x0412).hkl, mode='ko_hangul', name='Korean')], False)
            window.navigate(2)
            self.assertEqual(window.ime_key.currentData(), 'A')
            window.ime_key.setCurrentIndex(window.ime_key.findData('Q'))
            self.assertFalse(window.ime_apply.isEnabled())
            self.assertFalse(window.selector_apply.isEnabled())
            with patch.object(app.QMessageBox, 'warning') as warning:
                window._apply_ime_shortcut()
                warning.assert_called_once()
            window.ime_key.setCurrentIndex(window.ime_key.findData('J'))
            self.assertTrue(window.ime_apply.isEnabled())
            window.deleteLater()

    def test_controller_rejects_collision_without_replacing_running_hook(self):
        controller = app.LexiftController.__new__(app.LexiftController)
        controller.binding = HotkeyBinding('caps', 'Q')
        controller.ime_binding = HotkeyBinding('caps', 'A')
        controller.window = Mock()
        controller.hook = Mock()
        with patch.object(app.QMessageBox, 'warning'):
            controller.change_ime_shortcut(HotkeyBinding('caps', 'q'))
            controller.change_shortcut(HotkeyBinding('caps', 'a'))
        controller.hook.stop.assert_not_called()
        self.assertEqual(controller.ime_binding, HotkeyBinding('caps', 'A'))

    def test_failed_registration_restores_old_binding_and_settings(self):
        controller = app.LexiftController.__new__(app.LexiftController)
        controller.binding = HotkeyBinding()
        controller.ime_binding = HotkeyBinding('caps', 'A')
        controller.window = Mock(); controller.store = Mock()
        controller.hook = Mock(); controller._running = True
        failed, restored = Mock(), Mock()
        failed.start.side_effect = RuntimeError('Already registered')
        controller._make_keyboard_hook = Mock(side_effect=[failed, restored])
        with patch.object(app.QMessageBox, 'warning'):
            controller.change_ime_shortcut(HotkeyBinding('ctrl_shift', 'F12'))
        self.assertEqual(controller.ime_binding, HotkeyBinding('caps', 'A'))
        self.assertTrue(controller._running)
        restored.start.assert_called_once()
        controller.store.setValue.assert_not_called()
