"""Create a new, versioned local folder; never overwrite another version."""
import hashlib,json,shutil,sys
from pathlib import Path

root=Path(__file__).resolve().parents[1]
destination=Path(sys.argv[1]) if len(sys.argv)>1 else Path('G:/Development/Lexift (Formerly KanaShift)/Lexift v1.1')
version=json.loads((root/'package.json').read_text(encoding='utf-8'))['version']
if version!='1.1.0':raise SystemExit('Unexpected source version')
if destination.exists():raise SystemExit('Destination already exists; existing files are preserved.')
if not (root/'portable/Lexift/Lexift.exe').is_file():raise SystemExit('Build portable first.')
destination.mkdir(parents=True)
ignore=shutil.ignore_patterns('target','node_modules','__pycache__','*.pyc','*.pdb','*.obj','*.log')
for name in ('src','src-tauri','public','engine','scripts','tests','portable'):
    shutil.copytree(root/name,destination/name,ignore=ignore)
for name in ('package.json','pnpm-lock.yaml','tsconfig.json','vite.config.ts','index.html','build.ps1','LICENSE','.gitignore','README.md'):
    shutil.copy2(root/name,destination/name)
reports=destination/'verification';reports.mkdir()
for name in ('ui.json','engine-source.json','engine-frozen.json','native-debug.json','portable.json','dependency-audit.json','home-light.png','home-dark.png','selector-light.png','selector-dark.png','native-selector.png'):
    path=root/'verification'/name
    if path.is_file():shutil.copy2(path,reports/name)
(destination/'실행.cmd').write_bytes(b'@echo off\r\nstart "" "%~dp0portable\\Lexift\\Lexift.exe"\r\n')
manifest={}
for path in sorted(destination.rglob('*')):
    if not path.is_file():continue
    relative=path.relative_to(destination)
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    source=root/relative
    if source.is_file():assert digest==hashlib.sha256(source.read_bytes()).hexdigest(),relative
    manifest[relative.as_posix()]=digest
(destination/'local-manifest.json').write_text(json.dumps(dict(version=version,files=manifest),ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(dict(path=str(destination),version=version,verifiedFiles=len(manifest)),ensure_ascii=False))
