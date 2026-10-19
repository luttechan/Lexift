"""Tests for launch diagnostics and distribution entrypoints (platform neutral)."""
import importlib.machinery
import importlib.util
import sys
import types
from pathlib import Path
from unittest import TestCase, mock

ROOT = Path(__file__).resolve().parent.parent


def get_launcher():
    loader = importlib.machinery.SourceFileLoader("kana_bootstrap_for_test", str(ROOT / "launch.pyw"))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


class StartupTests(TestCase):
    def test_worker_failures_exit_without_hidden_modal_error_dialogs(self):
        bootstrap = get_launcher()
        for args,module,name in ((['--hook-worker','1234','token'],'isolated_hotkeys','run_worker'),
                                 (['--network-job','network.json'],'update_network','run_network_job')):
            worker=types.SimpleNamespace(**{name:mock.Mock(side_effect=RuntimeError('worker failed'))})
            with mock.patch.object(sys,'argv',['KanaShift.exe',*args]), \
                 mock.patch.dict(sys.modules,{module:worker}), \
                 mock.patch.object(bootstrap,'_report_startup_error') as dialog:
                self.assertEqual(bootstrap.main(),1)
                dialog.assert_not_called()

    def test_hook_worker_bypasses_app_import_and_returns_worker_status(self):
        bootstrap = get_launcher()
        worker = mock.Mock(return_value=0)
        with mock.patch.object(sys, 'argv', ['KanaShift.exe', '--hook-worker', '1234', 'token']), \
             mock.patch.dict(sys.modules, {'app': None, 'isolated_hotkeys': types.SimpleNamespace(run_worker=worker)}), \
             mock.patch.object(bootstrap, '_report_startup_error') as report:
            self.assertEqual(bootstrap.main(), 0)
        worker.assert_called_once_with('1234', 'token')
        report.assert_not_called()

    def test_launcher_returns_app_status(self):
        bootstrap = get_launcher()
        fake = types.SimpleNamespace(main=lambda: 42)
        with mock.patch.dict(sys.modules, {"app": fake}):
            self.assertEqual(bootstrap.main(), 42)

    def test_launcher_reports_import_error(self):
        bootstrap = get_launcher()
        with mock.patch.dict(sys.modules, {"app": None}):
            with mock.patch.object(bootstrap, "_report_startup_error") as report:
                self.assertEqual(bootstrap.main(), 1)
                report.assert_called_once()
                self.assertIn("ModuleNotFoundError", report.call_args.args[0])

    def test_manual_launch_is_visible_and_diagnostic_entrypoint_exists(self):
        run = (ROOT / "run.bat").read_text(encoding="utf-8")
        debug = (ROOT / "debug.bat").read_text(encoding="utf-8")
        self.assertIn('"%~dp0launch.pyw" --show', run)
        self.assertIn('"%~dp0launch.pyw" --show', debug)
        self.assertIn("pause", debug)
        self.assertNotIn('pyw.exe "%~dp0app.py"', run)

    def test_build_uses_launcher(self):
        commands = (ROOT / "build_windows.bat").read_text(encoding="utf-8").splitlines()
        self.assertTrue(any('-m PyInstaller ' in line and line.endswith('launch.pyw')
                            and '--name KanaShift' in line for line in commands))

    def test_bat_files_windows_line_endings(self):
        for name in ("run.bat", "debug.bat", "build_windows.bat", "install.bat"):
            contents = (ROOT / name).read_bytes()
            self.assertEqual(contents.count(b"\n"), contents.count(b"\r\n"), name)

    def test_source_launch_supports_background(self):
        src = (ROOT / "app.py").read_text(encoding="utf-8")
        self.assertIn('"--background"', src)
        self.assertIn('"--show"', src)
        self.assertIn('이미 실행 중입니다', src)
