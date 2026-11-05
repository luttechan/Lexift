"""Assemble only runtime files. Never remove or modify the original Lexift install."""
from pathlib import Path
import hashlib, json, shutil, os

root = Path(__file__).resolve().parents[1]
release = Path(os.environ.get('CARGO_TARGET_DIR',root/'src-tauri/target')) / 'x86_64-pc-windows-msvc/release'
output = root / 'portable/Lexift'
exe = release / 'lexift-desktop.exe'
engine = root / 'engine-dist'
if not exe.is_file() or not (engine / 'LexiftEngine.exe').is_file():
    raise SystemExit('Build the optimized Tauri application and engine first.')
if output.exists():
    if output.resolve().parent != (root / 'portable').resolve():
        raise SystemExit('Unexpected output path')
    shutil.rmtree(output)
output.mkdir(parents=True)
shutil.copy2(exe, output / 'Lexift.exe')
shutil.copytree(engine, output / 'engine')
shutil.copy2(root / 'LICENSE', output / 'LICENSE.txt')
(output / 'README.txt').write_text(
    'Lexift Desktop - React + Tauri 개발본\n\n'
    '기존 Lexift를 트레이에서 종료한 뒤 Lexift.exe를 실행하세요.\n'
    'engine 폴더를 함께 유지하세요. 기존 설정과 사전을 사용합니다.\n'
    'Windows 10/11 x64, Microsoft Edge WebView2 Runtime 필요.\n'
    '메인 UI 이전본이며 후보창과 입력 엔진은 기존 구현을 유지합니다.\n'
    'Lexift 1.2.0 로컬 개발본입니다.\n', encoding='utf-8')
licenses = output / 'licenses'
licenses.mkdir()
for pattern in ('*-OFL.txt', '*-LICENSE.txt'):
    for path in (root / 'public/fonts').glob(pattern):
        shutil.copy2(path, licenses / path.name)
# Include license files from installed wheel distributions when available.
deps = root.parent / '.builddeps'
for name in ('pyside6_essentials', 'shiboken6'):
    for info in deps.glob(name + '-*.dist-info'):
        for folder in ('licenses', 'LICENSES'):
            if (info / folder).is_dir():shutil.copytree(info / folder, licenses / name, dirs_exist_ok=True)
for name in ('react','react-dom','lucide-react','@tauri-apps/api'):
    folder = root / 'node_modules' / name
    for path in folder.glob('LICENSE*'):
        if path.is_file():shutil.copy2(path, licenses / (name.replace('/','-').replace('@','') + '-' + path.name))
manifest = {'application':'Lexift Desktop development build','platform':'Windows x64',
            'files':{str(path.relative_to(output)).replace('\\','/'):hashlib.sha256(path.read_bytes()).hexdigest()
                     for path in sorted(output.rglob('*')) if path.is_file()}}
(output / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
print(output)
