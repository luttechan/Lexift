import unittest
from unittest.mock import Mock,patch
from PySide6.QtCore import Qt,QRect
from PySide6.QtWidgets import QApplication,QLabel
from caps_lock_indicator import CapsLockIndicator

class CapsLockIndicatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.qt=QApplication.instance() or QApplication([])
    def setUp(self):
        self.read=Mock(return_value=False)
        self.screen=Mock();self.screen.geometry.return_value=QRect(-1920,120,1920,1080)
        def hidden_label():
            label=QLabel();label.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen);return label
        self.patch=patch('caps_lock_indicator.QLabel',side_effect=hidden_label);self.patch.start()
        self.indicator=CapsLockIndicator(read_state=self.read,get_screen=lambda:self.screen)
        self.events=[];self.indicator.changed.connect(self.events.append)
    def tearDown(self):
        self.indicator.stop()
        if self.indicator.toast:self.indicator.toast.deleteLater()
        self.indicator.deleteLater();self.patch.stop()
    def test_startup_and_unchanged_state_do_not_notify(self):
        for _ in range(4):self.indicator.poll()
        self.assertEqual(self.events,[]);self.assertIsNone(self.indicator.toast)
    def test_actual_on_and_off_reuse_one_centered_nonactivating_window(self):
        widget=None
        for state,text in ((True,'Caps Lock  ON'),(False,'Caps Lock  OFF')):
            self.read.return_value=state;self.indicator.poll()
            toast=self.indicator.toast
            if widget:self.assertIs(toast,widget)
            widget=toast;self.assertEqual(toast.text(),text)
            self.assertEqual(toast.geometry().center(),self.screen.geometry().center())
            self.assertTrue(toast.windowFlags()&Qt.WindowType.WindowDoesNotAcceptFocus)
            self.assertTrue(toast.windowFlags()&Qt.WindowType.WindowTransparentForInput)
            self.assertTrue(self.indicator.hide_timer.isActive())
        self.assertEqual(self.events,[True,False])
    def test_disabled_indicator_ignores_changes_and_reenable_sets_a_silent_baseline(self):
        self.indicator.stop();self.read.return_value=True;self.indicator.poll()
        self.assertEqual(self.events,[]);self.assertIsNone(self.indicator.toast)
        self.indicator.set_enabled(True);self.indicator.poll();self.assertEqual(self.events,[])
        self.read.return_value=False;self.indicator.poll();self.assertEqual(self.events,[False])
    def test_hide_ends_visibility_without_changing_caps_state(self):
        self.read.return_value=True;self.indicator.poll();calls=self.read.call_count
        self.indicator.hide();self.assertFalse(self.indicator.toast.isVisible())
        self.assertEqual(self.read.call_count,calls);self.assertTrue(self.indicator.state)
    def test_monitor_queries_do_not_accumulate_ctypes_structure_types(self):
        import ctypes
        from types import SimpleNamespace
        from caps_lock_indicator import active_screen
        from ime_inline import caret_point
        fake=SimpleNamespace(GetForegroundWindow=Mock(return_value=1),MonitorFromWindow=Mock(return_value=0),
            MonitorFromPoint=Mock(return_value=0),GetMonitorInfoW=Mock(return_value=0))
        with patch('ime_windows.user32',fake):
            before=len(ctypes._pointer_type_cache)
            for _ in range(200):active_screen();caret_point(dict(x=0,y=0))
            self.assertLessEqual(len(ctypes._pointer_type_cache)-before,2)
