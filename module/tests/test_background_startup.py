from contextlib import ExitStack
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication
import app
from layout_profiles import create_layout
import json


class BackgroundStartupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qt = QApplication.instance() or QApplication([])

    def test_manual_main_window_is_painted_before_worker_handshake(self):
        from PySide6.QtCore import QEventLoop
        controller=app.KanaShiftController.__new__(app.KanaShiftController)
        controller.first_run=False
        controller._update_timer_started=True
        controller.store=Mock()
        controller.qt=Mock()
        order=[]
        controller.show_window=Mock(side_effect=lambda *_:order.append('window'))
        controller.qt.processEvents.side_effect=lambda *_:order.append('paint')
        controller._start_hook=Mock(side_effect=lambda:order.append('hooks'))
        controller.start(show_main=True)
        self.assertEqual(order,['window','paint','hooks'])
        controller.qt.processEvents.assert_called_once_with(QEventLoop.ProcessEventsFlag.ExcludeUserInputEvents)

    def test_ui_uses_existing_malgun_regular_and_bold_faces(self):
        import re
        self.assertEqual(set(re.findall(r'font-weight:(\d+)',app.QSS)),{'400','700'})

    def test_login_startup_does_not_construct_main_window_or_settings(self):
        with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
            layout = create_layout(0x0412)
            store = QSettings(str(Path(directory)/'prefs.ini'), QSettings.Format.IniFormat)
            store.setValue('profiles/slots_json', json.dumps([
                dict(hkl=layout.hkl, mode='ko_hangul', name='Korean')]))
            stack.enter_context(patch.object(app, 'QSettings', return_value=store))
            stack.enter_context(patch.object(app, 'available_layouts', return_value=[layout]))
            stack.enter_context(patch.object(app, 'CapsQHook'))
            stack.enter_context(patch.object(app, 'OverlayNavigationHook'))
            stack.enter_context(patch.object(app.QTimer, 'singleShot'))
            main = stack.enter_context(patch.object(app, 'MainWindow', side_effect=AssertionError('eager GUI')))
            controller = app.KanaShiftController(self.qt)
            controller.start(background=True)
            self.assertTrue(controller._running)
            self.assertIsNone(controller._window)
            main.assert_not_called()
            controller.hook.stop()
            controller.navigation_hook.stop()
            controller.tray.hide()
            controller.overlay.deleteLater()
            controller.cursor_indicator.deleteLater()
            controller.deleteLater()

    def test_startup_command_quotes_python_and_script_and_uses_background_mode(self):
        registry = Mock()
        registry.__enter__ = Mock(return_value=registry)
        registry.__exit__ = Mock(return_value=False)
        with patch.object(app.winreg, 'OpenKey', return_value=registry), \
             patch.object(app.winreg, 'SetValueEx') as save, \
             patch.object(app.sys, 'frozen', False, create=True):
            app.set_startup_enabled(True)
        command = save.call_args.args[-1]
        self.assertTrue(command.startswith('"'))
        self.assertIn('" "', command)
        self.assertTrue(command.endswith('" --background'))
