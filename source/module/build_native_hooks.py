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
    # Git checkouts/source ZIPs can use different line endings. The compiler
    # input is identical; verify canonical source bytes and exact DLL bytes.
    source_digest = hashlib.sha256(source.read_bytes().replace(b'\r\n',b'\n')).hexdigest()
    if target.exists() and manifest.exists():
        recorded = json.loads(manifest.read_text(encoding='utf-8'))
        if recorded.get('source_sha256') in (source_digest,digest(source)) and recorded.get('dll_sha256') == digest(target):
            if recorded['source_sha256'] != source_digest:
                recorded['source_sha256'] = source_digest
                manifest.write_text(json.dumps(recorded,indent=2)+'\n',encoding='utf-8')
            print('Native keyboard module verified')
            return
    compiler = os.environ.get('KANASHIFT_ZIG') or shutil.which('zig')
    if not compiler:
        raise RuntimeError('Native module needs rebuilding. Set KANASHIFT_ZIG to zig.exe.')
    subprocess.run([compiler, 'cc', '-target', 'x86_64-windows-gnu', '-shared', '-Os', '-s',
        str(source), '-o', str(target), '-luser32', '-lkernel32'], check=True)
    source.with_suffix('.lib').unlink(missing_ok=True)  # Not used by the Python loader.
    target.with_suffix('.lib').unlink(missing_ok=True)
    manifest.write_text(json.dumps({'abi': 6, 'target': 'x86_64-windows-gnu',
        'source_sha256': source_digest, 'dll_sha256': digest(target)}, indent=2) + '\n', encoding='utf-8')
    print('Native keyboard module built')

if __name__ == '__main__':
    build()
