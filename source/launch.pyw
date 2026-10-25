from __future__ import annotations

import ctypes
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path

# Apply to diagnostics and helper entrypoints too, before QApplication exists.
if sys.platform == 'win32':
    os.environ.setdefault('QT_QPA_PLATFORM','windows:fontengine=gdi')
os.environ.setdefault('QT_LOGGING_RULES','qt.gui.icc.warning=false')

if not getattr(sys, 'frozen', False):
    sys.path.insert(0, str(Path(__file__).resolve().parent / 'module'))


def _report_startup_error(details: str, show_dialog: bool = True) -> None:
    folder = Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "Lexift"
    log_path = folder / "startup-error.log"
    try:
        folder.mkdir(parents=True, exist_ok=True)
        if log_path.exists() and log_path.stat().st_size>1024*1024:
            log_path.replace(log_path.with_suffix('.log.1'))
        with log_path.open("a", encoding="utf-8") as stream:
            stream.write(f"\n[{datetime.now().isoformat(timespec='seconds')}]\n{details}\n")
    except Exception:
        pass
    if not show_dialog:
        return
    try:
        from i18n import tr, load_saved_language
        load_saved_language()
        message = (tr('프로그램을 시작하지 못했습니다. debug.bat으로 오류를 확인하세요.')
                   + '\n\n' + tr('오류 로그: {path}').format(path=log_path))
        title = tr('Lexift 시작 오류')
    except Exception:
        message = f'Could not start Lexift. Run debug.bat for details.\n\nError log: {log_path}'
        title = 'Lexift startup error'
    try:
        ctypes.windll.user32.MessageBoxW(None, message, title, 0x10)
    except Exception:
        print(message, file=sys.stderr)


def main() -> int:
    try:
        if len(sys.argv)==3 and sys.argv[1]=='--verify-tones':
            from tone_diagnostics import verify
            return verify(sys.argv[2])
        if len(sys.argv)==3 and sys.argv[1]=='--verify-memory':
            from memory_diagnostics import verify
            return verify(sys.argv[2])
        if len(sys.argv)==3 and sys.argv[1]=='--verify-variants':
            from variant_diagnostics import verify
            return verify(sys.argv[2])
        if len(sys.argv)==3 and sys.argv[1]=='--verify-settings':
            from settings_diagnostics import verify
            return verify(sys.argv[2])
        if len(sys.argv)==3 and sys.argv[1]=='--verify-features':
            from feature_diagnostics import verify
            return verify(sys.argv[2])
        if len(sys.argv)==3 and sys.argv[1]=='--verify-chinese':
            from chinese_diagnostics import verify
            return verify(sys.argv[2])
        if len(sys.argv)==3 and sys.argv[1]=='--verify-ime':
            from ime_diagnostics import verify
            return verify(sys.argv[2])
        if len(sys.argv) >= 2 and sys.argv[1] == '--ime-lab':
            import subprocess
            host = Path(__file__).resolve().parent / 'lab' / 'ime_candidate_host.exe'
            if not host.is_file():
                raise RuntimeError('IME experimental host has not been built.')
            return subprocess.call([str(host), *sys.argv[2:]],
                                   creationflags=subprocess.CREATE_NO_WINDOW)
        if len(sys.argv) == 4 and sys.argv[1] == '--hook-worker':
            from isolated_hotkeys import run_worker
            return run_worker(sys.argv[2], sys.argv[3])
        if len(sys.argv) == 3 and sys.argv[1] == '--network-job':
            from update_network import run_network_job
            return run_network_job(sys.argv[2])
        if sys.argv[1:] == ['--verify-runtime']:
            from PySide6.QtWidgets import QApplication
            from app import choose_font
            qt = QApplication([sys.argv[0]])
            choose_font(qt)
            return 0
        from app import main as app_main
        return app_main()
    except BaseException:
        if len(sys.argv)>=2 and sys.argv[1] in ('--verify-ime','--verify-chinese','--verify-features','--verify-settings','--verify-variants'):
            _report_startup_error(traceback.format_exc(),show_dialog=False)
            return 1
        if sys.argv[1:] == ['--verify-runtime']:
            _report_startup_error(traceback.format_exc(), show_dialog=False)
            return 1
        if ((len(sys.argv) == 4 and sys.argv[1] == '--hook-worker') or
                (len(sys.argv) == 3 and sys.argv[1] == '--network-job') or
                sys.argv[1:] == ['--verify-runtime']):
            # The parent owns error reporting and cancellation. A hidden child
            # must not wait forever for its own modal startup-error dialog.
            return 1
        _report_startup_error(traceback.format_exc())
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
