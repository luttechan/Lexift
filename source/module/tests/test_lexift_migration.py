from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock,patch
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication
import app
from preferences import migrate_preferences
from custom_dictionary import CustomDictionary
import update_core as updates

class MigrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.qt=QApplication.instance() or QApplication([])
    def test_legacy_settings_dictionary_and_flags_are_copied_once(self):
        with tempfile.TemporaryDirectory() as folder:
            old=QSettings(str(Path(folder)/'old.ini'),QSettings.Format.IniFormat)
            new=QSettings(str(Path(folder)/'new.ini'),QSettings.Format.IniFormat)
            old.setValue('general/ui_language','en');old.setValue('features/ja',False)
            old.setValue('profiles/slots_json','[{"name":"Custom"}]')
            dictionary=CustomDictionary(old);dictionary.replace([dict(keyword='스미네',text='澄音',language='ja')])
            self.assertTrue(migrate_preferences(new,old))
            self.assertEqual(new.value('general/ui_language'),'en')
            self.assertFalse(new.value('features/ja',type=bool))
            self.assertEqual(CustomDictionary(new).lookup('ja','스미네'),'澄音')
            new.setValue('general/ui_language','ja');old.setValue('general/ui_language','ko')
            self.assertFalse(migrate_preferences(new,old))
            self.assertEqual(new.value('general/ui_language'),'ja');self.assertEqual(old.value('general/ui_language'),'ko')
    def test_new_release_namespace_and_executable_are_consistent(self):
        self.assertEqual(app.PRODUCT,'Lexift');self.assertEqual(app.VERSION,'1.0.4b')
        self.assertEqual(updates.REPOSITORY,'luttechan/Lexift')
        self.assertEqual(updates.API_URL,'https://api.github.com/repos/luttechan/Lexift/releases/latest')
        self.assertEqual(updates.MODULE_ENTRIES,('Lexift.exe','module'))
        manifest={'format':1,'product':'KanaShift','version':'1.0.2','architecture':'x64','files':{}}
        with tempfile.TemporaryDirectory() as folder:
            import json
            root=Path(folder);(root/'update-manifest.json').write_text(json.dumps(manifest))
            with self.assertRaises(updates.UpdateError):updates.validate_payload(root,'1.0.2')
    def test_shortcut_controls_live_in_separate_panels(self):
        with tempfile.TemporaryDirectory() as folder:
            store=QSettings(str(Path(folder)/'prefs.ini'),QSettings.Format.IniFormat)
            window=app.MainWindow(store,[],False);window.navigate(2)
            self.assertIsNot(window.shortcut_modifier.parent(),window.ime_modifier.parent())
            self.assertIs(window.ime_modifier.parent(),window.chinese_modifier.parent())
            self.assertIs(window.feature_checks['selector'].parent(),window.shortcut_modifier.parent())
            window.deleteLater()
