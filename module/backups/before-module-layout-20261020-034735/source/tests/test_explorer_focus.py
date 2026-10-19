"""Keep Explorer's transient editor alive while using the input selector."""
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
import app
from layout_profiles import hkl_string


class ExplorerFocusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qt = QApplication.instance() or QApplication([])
        cls.qt.setQuitOnLastWindowClosed(False)

    def setUp(self):
        self.overlay = app.Overlay()
        self.slot = dict(hkl=hkl_string(0x0411), mode='ja_hiragana', name='Japanese')

    def tearDown(self):
        self.overlay.hide()
        self.overlay.close()

    def test_hook_backed_selector_never_requests_target_focus(self):
        self.overlay.set_preserve_target_focus(True)
        with patch.object(self.overlay, 'activateWindow') as activate, \
             patch.object(self.overlay, 'setFocus') as focus:
            self.overlay.open([self.slot], 101)
        activate.assert_not_called()
        focus.assert_not_called()
        self.assertTrue(self.overlay.testAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating))
        self.assertTrue(self.overlay.windowFlags() & Qt.WindowType.WindowDoesNotAcceptFocus)
        self.assertFalse(self.overlay.windowFlags() & Qt.WindowType.WindowTransparentForInput)
        self.assertFalse(self.overlay.testAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents))

    def test_no_hook_retains_focused_keyboard_fallback(self):
        self.overlay.set_preserve_target_focus(True)
        self.overlay.set_preserve_target_focus(False)
        with patch.object(self.overlay, 'activateWindow') as activate, \
             patch.object(self.overlay, 'setFocus') as focus:
            self.overlay.open([self.slot], 101)
        activate.assert_called_once()
        focus.assert_called_once()
        self.assertFalse(self.overlay.windowFlags() & Qt.WindowType.WindowDoesNotAcceptFocus)

    def test_passive_selector_still_selects_with_navigation_hook(self):
        self.overlay.set_preserve_target_focus(True)
        with patch.object(self.overlay, 'activateWindow'):
            self.overlay.open([self.slot], 101)
        self.overlay.navigate_virtual_key(0x0D)
        self.assertFalse(self.overlay.isVisible())
        self.assertEqual(self.overlay.target_hwnd, 101)

    def test_katakana_width_prompt_keeps_original_editor(self):
        self.overlay.set_preserve_target_focus(True)
        slot = {**self.slot, 'mode': 'ja_katakana_ask'}
        with patch.object(self.overlay, 'activateWindow') as activate:
            self.overlay.open([slot], 101)
            self.overlay._activate(slot)
        activate.assert_not_called()
        self.assertEqual(self.overlay.page, 'width')
        self.assertEqual(self.overlay.target_hwnd, 101)
        self.assertTrue(self.overlay.windowFlags() & Qt.WindowType.WindowDoesNotAcceptFocus)

    def controller(self):
        controller = app.KanaShiftController.__new__(app.KanaShiftController)
        controller._running = False
        controller._navigation_started = False
        controller.overlay = self.overlay
        controller.navigation_hook = Mock()
        controller.hook = Mock()
        controller.store = Mock()
        controller.store.value.return_value = False
        controller.window = Mock()
        return controller

    def test_successful_hook_enables_focus_preservation(self):
        controller = self.controller()
        controller._start_hook()
        self.assertTrue(self.overlay._preserve_target_focus)

    def test_failed_hook_keeps_keyboard_fallback(self):
        controller = self.controller()
        controller.navigation_hook.start.side_effect = RuntimeError('hook unavailable')
        with patch.object(app.QMessageBox, 'warning'), patch.object(app.logging, 'exception'):
            controller._start_hook()
        self.assertFalse(self.overlay._preserve_target_focus)

    @unittest.skipUnless(sys.platform == 'win32', 'Windows native style')
    def test_native_selector_disallows_activation_but_accepts_mouse(self):
        import ctypes
        self.overlay.set_preserve_target_focus(True)
        get_style = ctypes.windll.user32.GetWindowLongW
        get_style.argtypes = [ctypes.c_void_p, ctypes.c_int]
        style = get_style(int(self.overlay.winId()), -20)
        self.assertTrue(style & 0x08000000)  # WS_EX_NOACTIVATE
        self.assertFalse(style & 0x20)  # NOT WS_EX_TRANSPARENT
