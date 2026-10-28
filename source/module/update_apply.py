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

from update_core import MANAGED, UpdateError, validate_payload, runtime_entries, strict_json, payload_build, plain_path
from i18n import tr, set_language, SUPPORTED, load_saved_language, error_text


class RecoveryError(UpdateError):
    pass


def cache_root() -> Path:
    return plain_path(Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "Lexift" / "updates")


def is_elevated():
    if sys.platform!='win32':return False
    from ctypes import wintypes
    kernel=ctypes.WinDLL('kernel32',use_last_error=True);advapi=ctypes.WinDLL('advapi32',use_last_error=True)
    kernel.GetCurrentProcess.restype=ctypes.c_void_p
    kernel.CloseHandle.argtypes=[ctypes.c_void_p]
    advapi.OpenProcessToken.argtypes=[ctypes.c_void_p,wintypes.DWORD,ctypes.POINTER(ctypes.c_void_p)]
    advapi.GetTokenInformation.argtypes=[ctypes.c_void_p,wintypes.DWORD,ctypes.c_void_p,wintypes.DWORD,ctypes.POINTER(wintypes.DWORD)]
    token=ctypes.c_void_p();value=wintypes.DWORD();size=wintypes.DWORD()
    if not advapi.OpenProcessToken(kernel.GetCurrentProcess(),0x0008,ctypes.byref(token)):
        raise UpdateError('Cannot verify update process privileges')
    try:
        if not advapi.GetTokenInformation(token,20,ctypes.byref(value),ctypes.sizeof(value),ctypes.byref(size)):
            raise UpdateError('Cannot verify update process privileges')
        return bool(value.value)
    finally:kernel.CloseHandle(token)


def plain_tree(root: Path):
    for path in (root, *root.parents):
        if path.is_symlink() or getattr(path, "is_junction", lambda: False)():
            raise UpdateError("Update path contains a reparse point")
    if root.exists():
        for path in root.rglob("*"):
            if path.is_symlink() or getattr(path, "is_junction", lambda: False)():
                raise UpdateError("Runtime contains a reparse point")


def load_job(path: Path, allow_legacy=False) -> dict:
    path = path.absolute()
    base = cache_root().absolute()
    if path.name != "job.json" or path.parent.parent != base or len(path.parent.name) != 32:
        raise UpdateError("Invalid update job location")
    int(path.parent.name, 16)
    plain_tree(path.parent)
    if path.stat().st_size > 32768:
        raise UpdateError("Update job is too large")
    job = strict_json(path.read_text(encoding="utf-8"))
    if not isinstance(job,dict) or job.get("product") != "Lexift" or job.get("nonce") != path.parent.name:
        raise UpdateError("Invalid update job")
    if any(not isinstance(job.get(name),str) for name in ('target','payload','version')):raise UpdateError('Invalid update job fields')
    target = Path(job["target"])
    payload = Path(job["payload"])
    plain_path(target)
    if (not target.is_absolute() or target == target.parent
            or payload != path.parent / "unpacked" / "Lexift"
            or not (target / "Lexift.exe").is_file()
            or not any((target / name).is_dir() for name in ("_internal", "module"))):
        raise UpdateError("Invalid installed runtime or staging directory")
    plain_tree(target / "_internal")
    plain_tree(target / "module")
    for name in MANAGED:
        candidate = target / name
        if candidate.is_symlink() or getattr(candidate, "is_junction", lambda: False)():
            raise UpdateError("Managed runtime path is a reparse point")
    manifest=validate_payload(payload, job["version"])
    if job.get('security_format')==2:
        if job.get('expected_build')!=payload_build(manifest['files']):raise UpdateError('Update payload changed after download')
    elif not (allow_legacy and 'security_format' not in job):raise UpdateError('Unverified legacy update job')
    if type(job.get('parent_pid')) is not int or job['parent_pid']<=0:raise UpdateError('Invalid update parent process')
    return job


def parent_handle(pid: int, expected_image=None):
    if sys.platform != "win32":
        raise UpdateError("Windows only")
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong]
    kernel.OpenProcess.restype = ctypes.c_void_p
    kernel.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
    kernel.WaitForSingleObject.restype = ctypes.c_ulong
    kernel.CloseHandle.argtypes = [ctypes.c_void_p]
    handle = kernel.OpenProcess(0x00101000, False, pid)  # SYNCHRONIZE + QUERY_LIMITED_INFORMATION.
    if not handle:
        raise UpdateError("Cannot wait for the running Lexift process")
    if expected_image is not None:
        kernel.QueryFullProcessImageNameW.argtypes=[ctypes.c_void_p,ctypes.c_ulong,ctypes.c_wchar_p,ctypes.POINTER(ctypes.c_ulong)]
        size=ctypes.c_ulong(32768);buffer=ctypes.create_unicode_buffer(size.value)
        if not kernel.QueryFullProcessImageNameW(handle,0,buffer,ctypes.byref(size)) or Path(buffer.value).resolve()!=Path(expected_image).resolve():
            kernel.CloseHandle(handle);raise UpdateError('Update parent is not the installed Lexift process')
    return kernel, handle


def remove_entry(path: Path):
    # Call only for a known MANAGED name within our transaction directory.
    plain_tree(path)
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink(missing_ok=True)


def replace_runtime(payload: Path, target: Path, version: str, verify_start=lambda: None, expected_build=None):
    """Swap complete managed entries. Restore every old entry on any failure."""
    plain_path(target)
    before=validate_payload(payload, version)
    expected_build=expected_build or payload_build(before['files'])
    if payload_build(before['files'])!=expected_build:raise UpdateError('Update payload changed after validation')
    plain_tree(payload)
    plain_tree(target / "_internal")
    plain_tree(target / "module")
    transaction = target / (".kanashift-update-" + uuid.uuid4().hex)
    incoming, backup = transaction / "incoming", transaction / "backup"
    if transaction.exists():
        raise UpdateError("Transaction already exists")
    transaction.mkdir(mode=0o700)
    moved, installed = [], []
    try:
        shutil.copytree(payload, incoming)
        incoming_manifest=validate_payload(incoming, version)
        if payload_build(incoming_manifest['files'])!=expected_build:raise UpdateError('Update payload changed during copy')
        backup.mkdir(mode=0o700)
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
        job = load_job(path,allow_legacy=True)
        if Path(sys.executable).parent != Path(job["target"]) or job["version"] != version:
            return
        (path.parent / "ready").write_text(job["nonce"], encoding="ascii")
    except Exception:
        # No acknowledgment: the external updater will roll back.
        return


def run_job(path: Path):
    if is_elevated():raise UpdateError('Automatic installation is unavailable with administrator privileges')
    job = load_job(path)
    if job.get('ui_language') in SUPPORTED:
        set_language(job['ui_language'])
    kernel, handle = parent_handle(job["parent_pid"],Path(job['target'])/'Lexift.exe')
    try:
        # Signal only after opening the exact parent process object, preventing
        # PID reuse from ever attaching this update to a different process.
        (path.parent / "helper-ready").write_text(job["nonce"], encoding="ascii")
        if kernel.WaitForSingleObject(handle, 60000) != 0:
            raise UpdateError("Lexift did not exit; update cancelled")
    finally:
        kernel.CloseHandle(handle)
    target = Path(job["target"])
    child = None

    def restart_and_verify():
        nonlocal child
        try:
            child = subprocess.Popen([str(target / "Lexift.exe"), "--show", "--update-job", str(path)], cwd=target)
            deadline = time.monotonic() + 60
            ready = path.parent / "ready"
            while time.monotonic() < deadline:
                plain_path(ready)
                if ready.exists() and ready.stat().st_size<=64 and ready.read_text(encoding="ascii") == job["nonce"]:
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
        replace_runtime(Path(job["payload"]), target, job["version"], restart_and_verify,expected_build=job['expected_build'])
    except RecoveryError:
        raise
    except Exception:
        if child is not None and child.poll() is None:
            child.terminate()
            child.wait(timeout=15)
        subprocess.Popen([str(target / "Lexift.exe"), "--show"], cwd=target)
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
    elevated=True
    try:
        elevated=is_elevated()
        if elevated:raise UpdateError('Automatic installation is unavailable with administrator privileges')
        if len(sys.argv) != 3 or sys.argv[1] != "--job":
            raise UpdateError("This program is started by Lexift's update menu.")
        run_job(Path(sys.argv[2]).absolute())
        return 0
    except Exception as error:
        if len(sys.argv) == 3 and not elevated:
            try:
                path = Path(sys.argv[2]).absolute()
                if path.name == "job.json" and path.parent.parent == cache_root().absolute():
                    plain_tree(path.parent)
                    (path.parent / "error.log").write_text(str(error), encoding="utf-8")
            except (OSError,UpdateError):
                pass
        if sys.platform == "win32":
            message = (tr('업데이트와 복구에 실패했습니다. 다음 백업 폴더를 보존하세요:\n{path}').format(path=error.backup)
                       if isinstance(error, RecoveryError) else error_text(error, 'update'))
            ctypes.windll.user32.MessageBoxW(None,
                tr('업데이트 실패') + '\n\n' + message,
                "Lexift", 0x10)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
