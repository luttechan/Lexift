# -*- mode: python ; coding: utf-8 -*-


from pathlib import Path
import os
import importlib.util
from PyInstaller.utils.hooks import collect_all
opencc_datas,opencc_binaries,opencc_hidden=collect_all('opencc')
opencc_libs=Path(importlib.util.find_spec('opencc').origin).parent.parent/'opencc.libs'
if opencc_libs.is_dir():
    opencc_binaries.extend((str(path),'opencc.libs') for path in opencc_libs.glob('*.dll'))
# Resolve Windows' ICU from System32 before unrelated tools on PATH (Poppler,
# for example, ships an incompatible DLL with the same name).
windows_folder = Path(os.environ.get('SystemRoot', 'C:/Windows'))
ssl_folder=Path(importlib.util.find_spec('_ssl').origin).parent
ssl_binaries=[(str(path),'.') for pattern in ('libssl*.dll','libcrypto*.dll') for path in ssl_folder.glob(pattern)]
ssl_data=Path(importlib.util.find_spec('ssl').origin).with_name('codex-rejected-cas.pem')
tls_datas=[(str(ssl_data),'.')] if ssl_data.is_file() else []
os.environ['PATH'] = os.pathsep.join([str(ssl_folder), str(windows_folder / 'System32'), str(windows_folder), os.environ.get('PATH', '')])
module_folder = Path(SPECPATH)
project_folder = module_folder.parent
import runpy
runpy.run_path(str(module_folder / 'build_security.py'))['verify']()
runpy.run_path(str(module_folder / 'native_baseline.py'))['verify'](project_folder)

a = Analysis(
    [str(project_folder / 'launch.pyw')],
    pathex=[str(module_folder)],
    binaries=[(str(module_folder / 'kanashift_hooks.dll'), '.'),
              (str(module_folder / 'lexift_keyboard.exe'), '.'),
              (str(project_folder / 'lab' / 'ime_candidate_host.exe'), 'lab'),*ssl_binaries,*opencc_binaries],
    datas=[(str(module_folder / 'Style'), 'Style'), (str(project_folder / 'LICENSE'), '.'),
           (str(module_folder / 'chinese_data'), 'chinese_data'),
           (str(module_folder / 'IAccessible2-LICENSE.txt'), '.'),*tls_datas,*opencc_datas,
           (str(module_folder / 'OpenCC-LICENSE.txt'),'.')],
    hiddenimports=opencc_hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Lexift',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=[str(module_folder / 'lexift.ico')],
    contents_directory='module',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='Lexift',
)
