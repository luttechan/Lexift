from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication
import app


class LocalFontTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qt = QApplication.instance() or QApplication([])

    def test_loads_local_true_type_font_and_reuses_registration(self):
        self.qt.setProperty('kanashiftLocalFontPath', None)
        with patch.object(QFontDatabase, 'addApplicationFont', wraps=QFontDatabase.addApplicationFont) as load:
            app.choose_font(self.qt)
            app.choose_font(self.qt)
        load.assert_called_once_with(str(app.local_font_path()))
        font_id = self.qt.property('kanashiftLocalFontId')
        self.assertGreaterEqual(font_id, 0)
        self.assertIn('Malgun Gothic', QFontDatabase.applicationFontFamilies(font_id))

    def test_missing_local_font_keeps_windows_font_available(self):
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(app, 'local_font_path', return_value=Path(directory)/'missing.ttf'), \
             patch.object(QFontDatabase, 'addApplicationFont') as load:
            app.choose_font(self.qt)
        load.assert_not_called()
        self.assertEqual(self.qt.font().family(), 'Malgun Gothic')

    def test_packaged_font_uses_bundle_directory(self):
        with patch.object(app.sys, '_MEIPASS', 'C:/example/_internal', create=True):
            self.assertEqual(app.local_font_path(), Path('C:/example/_internal/Style/malgun.ttf'))
