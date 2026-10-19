"""Keep TLS, downloads and ZIP processing outside the keyboard-hook process."""
from __future__ import annotations

from dataclasses import asdict
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import threading
import time
import uuid

from update_core import Release, UpdateError, UpdateCancelled


def write_json(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value), encoding='utf-8')
    temporary.replace(path)


def worker_command(request):
    if getattr(sys, 'frozen', False):
        # The onedir app is one process; a onefile helper would create a second
        # bootloader process and complicate immediate cancellation.
        return [sys.executable, '--network-job', str(request)]
    return [sys.executable, '-E', '-s', str(Path(__file__).resolve()), '--network-job', str(request)]


def isolated_request(job_dir, operation, cancel, progress=lambda value: None, release=None):
    request = job_dir / 'network.json'
    write_json(request, dict(operation=operation, release=asdict(release) if release else None))
    environment = os.environ.copy()
    environment['PYINSTALLER_RESET_ENVIRONMENT'] = '1'
    child = subprocess.Popen(worker_command(request), cwd=job_dir, env=environment,
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    deadline = time.monotonic() + (60 if operation == 'check' else 1800)
    last_progress = -1
    try:
        while child.poll() is None:
            if cancel.wait(.05):
                raise UpdateCancelled('Cancelled')
            if time.monotonic() > deadline:
                raise UpdateError('Update request timed out')
            try:
                value = int((job_dir / 'progress').read_text(encoding='ascii'))
                if value != last_progress and 0 <= value <= 100:
                    progress(value)
                    last_progress = value
            except (OSError, ValueError):
                pass
        if cancel.is_set():
            raise UpdateCancelled('Cancelled')
        result_path = job_dir / 'result.json'
        if not result_path.is_file() or result_path.stat().st_size > 32768:
            raise UpdateError('Update worker did not return a result')
        result = json.loads(result_path.read_text(encoding='utf-8'))
        if child.returncode or 'error' in result:
            raise UpdateError(result.get('error', 'Update worker failed'))
        return result
    finally:
        if child.poll() is None:
            child.terminate()
            child.wait(timeout=10)


def isolated_check(cancel):
    from update_apply import cache_root, plain_tree
    base = cache_root()
    base.mkdir(parents=True, exist_ok=True)
    job_dir = base / uuid.uuid4().hex
    job_dir.mkdir()
    try:
        plain_tree(job_dir)
        return Release(**isolated_request(job_dir, 'check', cancel)['release'])
    finally:
        shutil.rmtree(job_dir, ignore_errors=True)


def isolated_download(release, job_dir, cancel, progress):
    isolated_request(job_dir, 'download', cancel, progress, release)
    return job_dir / 'unpacked' / 'KanaShift'


def run_network_job(request):
    from update_apply import cache_root, plain_tree
    from update_core import latest_release, download, extract_package
    request = Path(request).absolute()
    if (request.name != 'network.json' or request.parent.parent != cache_root().absolute()
            or len(request.parent.name) != 32):
        raise UpdateError('Invalid network job location')
    int(request.parent.name, 16)
    plain_tree(request.parent)
    if request.stat().st_size > 32768:
        raise UpdateError('Network job is too large')
    try:
        job = json.loads(request.read_text(encoding='utf-8'))
        if job['operation'] == 'check':
            result = {'release': asdict(latest_release())}
        elif job['operation'] == 'download':
            release = Release(**job['release'])
            cancel = threading.Event()
            previous = -1

            def report(value):
                nonlocal previous
                if value != previous:
                    temporary = request.parent / 'progress.tmp'
                    temporary.write_text(str(value), encoding='ascii')
                    temporary.replace(request.parent / 'progress')
                    previous = value

            archive = request.parent / 'download.zip'
            download(release, archive, cancel, report)
            extract_package(archive, request.parent / 'unpacked', release.version, cancel)
            result = {'prepared': True}
        else:
            raise UpdateError('Unsupported network operation')
        write_json(request.parent / 'result.json', result)
        return 0
    except Exception as error:
        write_json(request.parent / 'result.json', {'error': str(error)[:8000]})
        return 1


if __name__ == '__main__':
    if len(sys.argv) != 3 or sys.argv[1] != '--network-job':
        raise SystemExit(2)
    raise SystemExit(run_network_job(sys.argv[2]))
