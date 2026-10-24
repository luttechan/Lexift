import ctypes
import sys
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import Qt, QPoint
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
import app as a
import ime_windows as ime
from cursor_indicator import CursorIndicator
from layout_profiles import create_layout, hkl_string


class CursorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qt = QApplication.instance() or QApplication([])
        cls.qt.setQuitOnLastWindowClosed(False)

    def setUp(self):
        self.tip = CursorIndicator()

    def tearDown(self):
        self.tip.dismiss()
        self.tip.close()

    def test_passive_native_window_and_plain_text(self):
        self.tip.show_language('<img src="https://invalid.test/track">')
        self.qt.processEvents()
        self.assertEqual(self.tip.text.textFormat(), Qt.TextFormat.PlainText)
        self.assertTrue(self.tip.windowFlags() & Qt.WindowType.WindowTransparentForInput)
        self.assertTrue(self.tip.windowFlags() & Qt.WindowType.WindowDoesNotAcceptFocus)
        self.assertTrue(self.tip.testAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating))
        if sys.platform == 'win32':
            get_style = ctypes.windll.user32.GetWindowLongW
            get_style.argtypes = [ctypes.c_void_p, ctypes.c_int]
            style = get_style(int(self.tip.winId()), -20)
            self.assertTrue(style & 0x20)  # WS_EX_TRANSPARENT
            self.assertTrue(style & 0x08000000)  # WS_EX_NOACTIVATE

    def test_one_second_lifetime(self):
        self.tip.show_language('KO · 한국어')
        started = time.monotonic()
        QTest.qWait(800)
        self.assertTrue(self.tip.isVisible())
        while self.tip.isVisible() and time.monotonic() - started < 1.25:
            QTest.qWait(10)
        self.assertFalse(self.tip.isVisible())
        self.assertLess(time.monotonic() - started, 1.25)

    def test_timer_restarts_and_dismiss_cancels(self):
        self.tip.show_language('KO')
        QTest.qWait(600)
        self.tip.show_language('EN')
        QTest.qWait(500)
        self.assertTrue(self.tip.isVisible())
        self.tip.dismiss()
        self.assertFalse(self.tip.timer.isActive())

    def test_stays_inside_monitor_at_edges(self):
        screen = self.qt.primaryScreen()
        rect = screen.availableGeometry()
        for point in (rect.topLeft(), rect.bottomRight(),
                      QPoint(rect.left(), rect.bottom())):
            with patch('cursor_indicator.QCursor.pos', return_value=point):
                self.tip.show_language('JA · ' + '가' * 100)
                self.assertTrue(rect.contains(self.tip.geometry()))

    def test_profile_text_is_plain(self):
        widget = a.label('<img src="file:///private">')
        self.assertEqual(widget.textFormat(), Qt.TextFormat.PlainText)
        widget.close()


class SwitchTests(unittest.TestCase):
    def setUp(self):
        self.controller = a.LexiftController.__new__(a.LexiftController)
        self.controller._job = 7
        self.controller._stopping = False
        self.controller.overlay = Mock()
        self.controller.overlay.isVisible.return_value = False
        self.controller.cursor_indicator = Mock()
        self.controller.tray = Mock()
        self.slot = dict(hkl=hkl_string(0x0412), mode='ko_hangul', name='custom')
        self.focus = patch.object(a, 'target_is_foreground', return_value=True)
        self.focus.start()
        self.hkl = patch.object(a, 'current_hkl', return_value=0x0412)
        self.hkl.start()
        self.layouts = patch.object(a, 'available_layouts', return_value=[create_layout(0x0412)])
        self.layouts.start()
        self.addCleanup(patch.stopall)

    def test_default_and_korean_success(self):
        for mode in ('default', 'ko_hangul', 'ko_latin'):
            self.controller._job = 7
            with patch.object(a, 'korean_set', return_value=True):
                self.controller._apply_mode(7, 101, {**self.slot, 'mode': mode})
        self.assertEqual(self.controller.cursor_indicator.show_language.call_count, 3)

    def test_same_layout_switch_skips_layout_activation_delay(self):
        self.controller.overlay.target_hwnd = 101
        scheduled = []
        with patch.object(a, 'foreground_target', return_value=True), \
             patch.object(a, 'request_hkl') as request, \
             patch.object(a, 'korean_set', return_value=True), \
             patch.object(a.QTimer, 'singleShot', side_effect=lambda ms, call: scheduled.append((ms, call))):
            self.controller.apply_slot(self.slot)
            request.assert_not_called()
            self.assertEqual(scheduled[0][0], 0)
            scheduled[0][1]()
        self.controller.cursor_indicator.show_language.assert_called_once()

    def test_legacy_short_hkl_never_cycles_an_already_selected_layout(self):
        slot = {**self.slot, 'hkl': '00000412'}
        with patch.object(self.controller, '_apply_mode') as apply, \
             patch.object(a, 'cycle_windows_language') as cycle:
            self.controller._cycle(7, 101, slot, 0)
        apply.assert_called_once_with(7, 101, slot)
        cycle.assert_not_called()

    def test_layout_change_cancels_delayed_japanese_fallback_without_keys(self):
        with patch.object(a, 'current_hkl', return_value=0x0409), \
             patch.object(a, 'japanese_fallback_key') as send:
            self.controller._japanese_fallback(7, 101, {**self.slot, 'hkl': hkl_string(0x0411)}, 'hiragana', 0)
        send.assert_not_called()
        self.assertGreater(self.controller._job, 7)

    def test_korean_unverified_does_not_show(self):
        with patch.object(a, 'korean_is_hangul', return_value=None):
            self.controller._verify_korean(7, 101, self.slot, True)
        self.controller.cursor_indicator.show_language.assert_not_called()

    def test_korean_fallback_verified(self):
        with patch.object(a, 'korean_is_hangul', return_value=True):
            self.controller._verify_korean(7, 101, self.slot, True)
        self.controller.cursor_indicator.show_language.assert_called_once()

    def test_japanese_immediate_and_fallback_success(self):
        with patch.object(a, 'current_hkl', return_value=0x0411), \
             patch.object(a, 'available_layouts', return_value=[create_layout(0x0411)]):
            for mode, kind in [('ja_hiragana', 'hiragana'),
                               ('ja_katakana_full', 'katakana_full'),
                               ('ja_katakana_half', 'katakana_half')]:
                slot = dict(hkl=hkl_string(0x0411), mode=mode, name='custom')
                self.controller._job = 7
                with patch.object(a, 'japanese_set', return_value=True):
                    self.controller._apply_mode(7, 101, slot)
                self.controller._job = 7
                with patch.object(a, 'japanese_matches', return_value=True):
                    self.controller._japanese_fallback(7, 101, slot, kind, 1)
        self.assertEqual(self.controller.cursor_indicator.show_language.call_count, 6)

    def test_new_selector_cancels_old_completion(self):
        self.controller._selector_visibility(True)
        self.controller._switch_succeeded(7, 101, self.slot)
        self.controller.cursor_indicator.dismiss.assert_called_once()
        self.controller.cursor_indicator.show_language.assert_not_called()

    def test_visible_selector_never_duplicates(self):
        self.controller.overlay.isVisible.return_value = True
        self.controller._switch_succeeded(7, 101, self.slot)
        self.controller.cursor_indicator.show_language.assert_not_called()

    def test_duplicate_completion_consumed(self):
        self.controller._switch_succeeded(7, 101, self.slot)
        self.controller._switch_succeeded(7, 101, self.slot)
        self.controller.cursor_indicator.show_language.assert_called_once()

    def test_changed_hkl_never_shows_old_language(self):
        with patch.object(a, 'current_hkl', return_value=0x0411):
            self.controller._switch_succeeded(7, 101, self.slot)
        self.controller.cursor_indicator.show_language.assert_not_called()

    def test_focus_loss_cancels_all_delayed_operations(self):
        with patch.object(a, 'target_is_foreground', return_value=False), \
             patch.object(a, 'foreground_target') as restore, \
             patch.object(a, 'cycle_windows_language') as inject:
            self.controller._cycle(7, 101, self.slot, 0)
            self.assertNotEqual(self.controller._job, 7)
            self.controller._apply_mode(7, 101, self.slot)
            restore.assert_not_called()
            inject.assert_not_called()
        self.controller.cursor_indicator.show_language.assert_not_called()


@unittest.skipUnless(sys.platform == 'win32', 'Windows focus policy')
class NativeSecurityTests(unittest.TestCase):
    def test_no_focus_restore_from_unrelated_app(self):
        with patch.object(ime, 'user32') as api, patch.object(ime, '_root', return_value=101):
            api.IsWindow.return_value = True
            api.GetForegroundWindow.return_value = 202
            api.GetWindowThreadProcessId.return_value = 303
            self.assertFalse(ime.foreground_target(101))
            api.SetForegroundWindow.assert_not_called()

    def test_foreground_child_must_match(self):
        with patch.object(ime, 'user32') as api, patch.object(ime, '_root', return_value=101), \
             patch.object(ime, 'get_target_window', return_value=104):
            api.IsWindow.return_value = True
            api.GetForegroundWindow.return_value = 101
            self.assertFalse(ime.target_is_foreground(103))

    def test_all_keyboard_fallbacks_require_existing_focus(self):
        with patch.object(ime, 'target_is_foreground', return_value=False), \
             patch.object(ime, 'current_language', return_value=ime.LANG_KO), \
             patch.object(ime, '_send_keys') as keys, patch.object(ime, 'foreground_target') as restore:
            self.assertFalse(ime.korean_toggle_key(101))
            self.assertFalse(ime.cycle_windows_language(101))
            with patch.object(ime, 'current_language', return_value=ime.LANG_JA):
                self.assertFalse(ime.japanese_fallback_key(101, 'hiragana'))
            keys.assert_not_called()
            restore.assert_not_called()
