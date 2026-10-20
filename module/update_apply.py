"""External updater: no Qt, shell commands, administrator rights or user settings."""
from __future__ import annotations

import ctypes
import json
import os
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path

from update_core import MANAGED, UpdateError, validate_payload, runtime_entries
from i18n import tr, set_language, SUPPORTED, load_saved_language, error_text


class RecoveryError(UpdateError):
    pass


def cache_root() -> Path:
    return Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "KanaShift" / "updates"


def plain_tree(root: Path):
    for path in (root, *root.parents):
        if path.is_symlink() or getattr(path, "is_junction", lambda: False)():
            raise UpdateError("Update path contains a reparse point")
    if root.exists():
        for path in root.rglob("*"):
            if path.is_symlink() or getattr(path, "is_junction", lambda: False)():
                raise UpdateError("Runtime contains a reparse point")


def load_job(path: Path) -> dict:
    path = path.absolute()
    base = cache_root().absolute()
    if path.name != "job.json" or path.parent.parent != base or len(path.parent.name) != 32:
        raise UpdateError("Invalid update job location")
    int(path.parent.name, 16)
    plain_tree(path.parent)
    if path.stat().st_size > 32768:
        raise UpdateError("Update job is too large")
    job = json.loads(path.read_text(encoding="utf-8"))
    if job.get("product") != "KanaShift" or job.get("nonce") != path.parent.name:
        raise UpdateError("Invalid update job")
    target = Path(job["target"])
    payload = Path(job["payload"])
    if (not target.is_absolute() or target == target.parent
            or payload != path.parent / "unpacked" / "KanaShift"
            or not (target / "KanaShift.exe").is_file()
            or not any((target / name).is_dir() for name in ("_internal", "module"))):
        raise UpdateError("Invalid installed runtime or staging directory")
    plain_tree(target / "_internal")
    plain_tree(target / "module")
    for name in MANAGED:
        candidate = target / name
        if candidate.is_symlink() or getattr(candidate, "is_junction", lambda: False)():
            raise UpdateError("Managed runtime path is a reparse point")
    validate_payload(payload, job["version"])
    return job


def parent_handle(pid: int):
    if sys.platform != "win32":
        raise UpdateError("Windows only")
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong]
    kernel.OpenProcess.restype = ctypes.c_void_p
    kernel.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
    kernel.WaitForSingleObject.restype = ctypes.c_ulong
    kernel.CloseHandle.argtypes = [ctypes.c_void_p]
    handle = kernel.OpenProcess(0x00100000, False, pid)  # SYNCHRONIZE, no terminate access.
    if not handle:
        raise UpdateError("Cannot wait for the running KanaShift process")
    return kernel, handle


def remove_entry(path: Path):
    # Call only for a known MANAGED name within our transaction directory.
    plain_tree(path)
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink(missing_ok=True)


def replace_runtime(payload: Path, target: Path, version: str, verify_start=lambda: None):
    """Swap complete managed entries. Restore every old entry on any failure."""
    validate_payload(payload, version)
    plain_tree(payload)
    plain_tree(target / "_internal")
    plain_tree(target / "module")
    transaction = target / (".kanashift-update-" + uuid.uuid4().hex)
    incoming, backup = transaction / "incoming", transaction / "backup"
    if transaction.exists():
        raise UpdateError("Transaction already exists")
    transaction.mkdir()
    moved, installed = [], []
    try:
        shutil.copytree(payload, incoming)
        validate_payload(incoming, version)
        backup.mkdir()
        for name in MANAGED:
            if (target / name).exists():
                os.replace(target / name, backup / name)
                moved.append(name)
        for name in runtime_entries(incoming):
            os.replace(incoming / name, target / name)
            installed.append(name)
        verify_start()
    except Exception as error:
        # If restoration itself fails, retain transaction/backup for recovery.
        try:
            for name in reversed(installed):
                remove_entry(target / name)
            for name in reversed(moved):
                os.replace(backup / name, target / name)
        except Exception as recovery:
            failure = RecoveryError(f"Update and restoration failed. Retained backup: {backup}\n{error}\n{recovery}")
            failure.backup = backup
            raise failure from recovery
        plain_tree(transaction)
        shutil.rmtree(transaction)
        raise
    else:
        try:
            plain_tree(transaction)
            shutil.rmtree(transaction)
        except OSError:
            pass  # Successful update; leftover backup can be removed later.


def mark_ready(version: str):
    """Acknowledge only a validated job targeting this packaged executable."""
    if "--update-job" not in sys.argv or not getattr(sys, "frozen", False):
        return
    index = sys.argv.index("--update-job")
    try:
        path = Path(sys.argv[index + 1])
        job = load_job(path)
        if Path(sys.executable).parent != Path(job["target"]) or job["version"] != version:
            return
        (path.parent / "ready").write_text(job["nonce"], encoding="ascii")
    except Exception:
        # No acknowledgment: the external updater will roll back.
        return


def run_job(path: Path):
    job = load_job(path)
    if job.get('ui_language') in SUPPORTED:
        set_language(job['ui_language'])
    kernel, handle = parent_handle(int(job["parent_pid"]))
    try:
        # Signal only after opening the exact parent process object, preventing
        # PID reuse from ever attaching this update to a different process.
        (path.parent / "helper-ready").write_text(job["nonce"], encoding="ascii")
        if kernel.WaitForSingleObject(handle, 60000) != 0:
            raise UpdateError("KanaShift did not exit; update cancelled")
    finally:
        kernel.CloseHandle(handle)
    target = Path(job["target"])
    child = None

    def restart_and_verify():
        nonlocal child
        try:
            child = subprocess.Popen([str(target / "KanaShift.exe"), "--show", "--update-job", str(path)], cwd=target)
            deadline = time.monotonic() + 60
            ready = path.parent / "ready"
            while time.monotonic() < deadline:
                if ready.exists() and ready.read_text(encoding="ascii") == job["nonce"]:
                    return
                if child.poll() is not None:
                    raise UpdateError("New version exited during startup")
                time.sleep(.1)
            raise UpdateError("New version did not confirm startup")
        except Exception:
            # Stop only our exact new child before rollback touches loaded DLLs.
            if child is not None and child.poll() is None:
                child.terminate()
                child.wait(timeout=15)
            raise

    try:
        replace_runtime(Path(job["payload"]), target, job["version"], restart_and_verify)
    except RecoveryError:
        raise
    except Exception:
        if child is not None and child.poll() is None:
            child.terminate()
            child.wait(timeout=15)
        subprocess.Popen([str(target / "KanaShift.exe"), "--show"], cwd=target)
        raise
    else:
        (path.parent / "completed").write_text(job["nonce"], encoding="ascii")
        # The copied helper executable stays until it exits. Large downloads do not.
        try:
            plain_tree(path.parent / "unpacked")
            shutil.rmtree(path.parent / "unpacked")
            (path.parent / "download.zip").unlink(missing_ok=True)
        except OSError:
            pass


def main() -> int:
    load_saved_language()
    try:
        if len(sys.argv) != 3 or sys.argv[1] != "--job":
            raise UpdateError("This program is started by KanaShift's update menu.")
        run_job(Path(sys.argv[2]).absolute())
        return 0
    except Exception as error:
        if len(sys.argv) == 3:
            try:
                path = Path(sys.argv[2]).absolute()
                if path.name == "job.json" and path.parent.parent == cache_root().absolute():
                    (path.parent / "error.log").write_text(str(error), encoding="utf-8")
            except OSError:
                pass
        if sys.platform == "win32":
            message = (tr('업데이트와 복구에 실패했습니다. 다음 백업 폴더를 보존하세요:\n{path}').format(path=error.backup)
                       if isinstance(error, RecoveryError) else error_text(error, 'update'))
            ctypes.windll.user32.MessageBoxW(None,
                tr('업데이트 실패') + '\n\n' + message,
                "KanaShift", 0x10)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
