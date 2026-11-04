"""Export the desktop project without dependency caches or build outputs."""
import hashlib
import json
import shutil
import zipfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]
destination = root.parent / 'output' / (root.name + ' Source')
archive = destination.with_suffix('.zip')
if destination.exists() or archive.exists():
    raise SystemExit('Source export already exists; keep it intact and choose a new export name.')
destination.mkdir(parents=True)
files = ['package.json', 'pnpm-lock.yaml', 'tsconfig.json', 'vite.config.ts',
         'index.html', 'build.ps1', 'LICENSE', '.gitignore']
for name in files:
    shutil.copy2(root / name, destination / name)
ignored = shutil.ignore_patterns('target', 'node_modules', '__pycache__', '*.pyc', '*.pdb', '*.obj', '*.log')
for name in ('src', 'src-tauri', 'public', 'engine', 'scripts', 'tests'):
    shutil.copytree(root / name, destination / name, ignore=ignored)
readme = (root / 'README.md').read_text(encoding='utf-8')
readme = readme.replace('## 실행\n',
    '## 소스 구성\n\n'
    '- `src/App.tsx`: 메인 React UI와 로딩창\n'
    '- `src/styles.css`: 밝은 모드 및 다크모드\n'
    '- `src-tauri/src/main.rs`: Tauri 호스트와 엔진 연결\n'
    '- `engine/bridge.py`: 기존 입력 엔진 연결\n'
    '- `engine/module/`, `engine/lab/`: 입력 엔진과 네이티브 모듈\n\n'
    '소스 보관본에는 빌드 결과와 의존성 캐시를 포함하지 않습니다. '
    '의존성 설치 후 `build.ps1 -RebuildEngine`으로 빌드합니다.\n\n## 실행\n')
(destination / 'README.md').write_text(readme, encoding='utf-8')
manifest = {}
for path in sorted(destination.rglob('*')):
    if path.is_file():
        relative = path.relative_to(destination)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if relative.name != 'README.md':
            assert digest == hashlib.sha256((root / relative).read_bytes()).hexdigest(), relative
        manifest[relative.as_posix()] = digest
(destination / 'source-manifest.json').write_text(
    json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as bundle:
    for path in sorted(destination.rglob('*')):
        if path.is_file():bundle.write(path, path.relative_to(destination.parent))
with zipfile.ZipFile(archive) as bundle:
    assert bundle.testzip() is None
print(json.dumps({'folder':str(destination),'zip':str(archive),'files':len(manifest),
                  'archiveBytes':archive.stat().st_size,'verified':True},ensure_ascii=False))
