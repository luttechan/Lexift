from __future__ import annotations

import ctypes
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path


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
        from app import main as app_main
        return app_main()
    except BaseException:
        _report_startup_error(traceback.format_exc())
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
