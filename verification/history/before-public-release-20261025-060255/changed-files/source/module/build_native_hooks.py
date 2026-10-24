"""Build with Zig, or verify the checked-in native module when Zig is absent."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

def build():
    folder = Path(__file__).resolve().parent
    source = folder / 'native_hooks.c'
    target = folder / 'kanashift_hooks.dll'
    manifest = folder / 'native_hooks_build.json'
    digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    if target.exists() and manifest.exists():
        recorded = json.loads(manifest.read_text(encoding='utf-8'))
        if recorded.get('source_sha256') == digest(source) and recorded.get('dll_sha256') == digest(target):
            print('Native keyboard module verified')
            return
    compiler = os.environ.get('KANASHIFT_ZIG') or shutil.which('zig')
    if not compiler:
        raise RuntimeError('Native module needs rebuilding. Set KANASHIFT_ZIG to zig.exe.')
    subprocess.run([compiler, 'cc', '-target', 'x86_64-windows-gnu', '-shared', '-Os', '-s',
        str(source), '-o', str(target), '-luser32', '-lkernel32'], check=True)
    source.with_suffix('.lib').unlink(missing_ok=True)  # Not used by the Python loader.
    target.with_suffix('.lib').unlink(missing_ok=True)
    manifest.write_text(json.dumps({'abi': 4, 'target': 'x86_64-windows-gnu',
        'source_sha256': digest(source), 'dll_sha256': digest(target)}, indent=2) + '\n', encoding='utf-8')
    print('Native keyboard module built')

if __name__ == '__main__':
    build()
