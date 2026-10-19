from __future__ import annotations

import ctypes
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path

if not getattr(sys, 'frozen', False):
    sys.path.insert(0, str(Path(__file__).resolve().parent / 'module'))


def _report_startup_error(details: str) -> None:
    folder = Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "KanaShift"
    log_path = folder / "startup-error.log"
    try:
        folder.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as stream:
            stream.write(f"\n[{datetime.now().isoformat(timespec='seconds')}]\n{details}\n")
    except Exception:
        pass
    summary = details.strip().splitlines()[-1] if details.strip() else "알 수 없는 오류"
    message = ("KanaShift를 시작할 수 없습니다.\n\n"
               f"{summary[:500]}\n\n오류 로그: {log_path}\n"
               "debug.bat을 실행하면 자세한 오류를 볼 수 있습니다.")
    try:
        ctypes.windll.user32.MessageBoxW(None, message, "KanaShift 실행 오류", 0x10)
    except Exception:
        print(message, file=sys.stderr)


def main() -> int:
    try:
        if len(sys.argv) == 4 and sys.argv[1] == '--hook-worker':
            from isolated_hotkeys import run_worker
            return run_worker(sys.argv[2], sys.argv[3])
        if len(sys.argv) == 3 and sys.argv[1] == '--network-job':
            from update_network import run_network_job
            return run_network_job(sys.argv[2])
        from app import main as app_main
        return app_main()
    except BaseException:
        if ((len(sys.argv) == 4 and sys.argv[1] == '--hook-worker') or
                (len(sys.argv) == 3 and sys.argv[1] == '--network-job')):
            # The parent owns error reporting and cancellation. A hidden child
            # must not wait forever for its own modal startup-error dialog.
            return 1
        _report_startup_error(traceback.format_exc())
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
