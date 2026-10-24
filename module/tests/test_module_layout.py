import tempfile
import threading
import unittest
import zipfile
from pathlib import Path
import update_core as core
from update_apply import replace_runtime
from package_release import package
from .test_updates import payload


def modern_payload(root, version='0.7.8'):
    (root/'module').mkdir(parents=True)
    (root/'Lexift.exe').write_bytes(b'MZmodern')
    (root/'module'/'LexiftUpdater.exe').write_bytes(b'MZhelper')
    (root/'module'/'python.dll').write_bytes(b'runtime')
    core.make_manifest(root,version)
    return root


class ModuleLayoutTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_portable_root_contains_only_main_exe_and_module(self):
        source = modern_payload(self.root/'source')
        self.assertEqual({p.name for p in source.iterdir()},{'Lexift.exe','module'})
        archive = package(source,self.root/'release','0.7.8')
        with zipfile.ZipFile(archive) as zipped:
            self.assertIn('Lexift/module/update-manifest.json',zipped.namelist())
            self.assertNotIn('Lexift/update-manifest.json',zipped.namelist())
        result = core.extract_package(archive,self.root/'unpacked','0.7.8',threading.Event())
        core.validate_payload(result,'0.7.8')
        self.assertEqual(core.updater_path(result),result/'module'/'LexiftUpdater.exe')

    def test_legacy_installation_migrates_without_obsolete_runtime_entries(self):
        target = payload(self.root/'target','0.7.7',b'old')
        (target/'preferences.ini').write_text('keep')
        source = modern_payload(self.root/'source')
        replace_runtime(source,target,'0.7.8')
        self.assertFalse((target/'_internal').exists())
        self.assertFalse((target/'LexiftUpdater.exe').exists())
        self.assertFalse((target/'update-manifest.json').exists())
        self.assertEqual((target/'preferences.ini').read_text(),'keep')
        self.assertEqual(core.runtime_entries(target),core.MODULE_ENTRIES)

    def test_failed_migration_restores_entire_legacy_installation(self):
        target = payload(self.root/'target','0.7.7',b'old')
        source = modern_payload(self.root/'source')
        def reject_start():
            self.assertTrue((target/'module').is_dir())
            raise RuntimeError('new app did not start')
        with self.assertRaisesRegex(RuntimeError,'did not start'):
            replace_runtime(source,target,'0.7.8',reject_start)
        self.assertEqual((target/'Lexift.exe').read_bytes(),b'MZold')
        self.assertFalse((target/'module').exists())
        core.validate_payload(target,'0.7.7')

    def test_legacy_update_packages_remain_supported(self):
        target = modern_payload(self.root/'target','0.7.7')
        source = payload(self.root/'source')
        replace_runtime(source,target,'0.7.8')
        self.assertFalse((target/'module').exists())
        core.validate_payload(target,'0.7.8')

    def test_mixed_runtime_layouts_are_rejected(self):
        source = modern_payload(self.root/'source')
        (source/'_internal').mkdir()
        (source/'_internal'/'extra.dll').write_bytes(b'extra')
        with self.assertRaises(core.UpdateError):
            core.make_manifest(source,'0.7.8')
