"""Apply the Caps+Q hotfix to the authorized local 1.1 folder, with rollback."""
from datetime import datetime
import hashlib,json,shutil
from pathlib import Path

source=Path(__file__).resolve().parents[1]
target=Path('G:/Development/Lexift (Formerly KanaShift)/Lexift v1.1')
manifest_path=target/'local-manifest.json'
previous=json.loads(manifest_path.read_text(encoding='utf-8'))
if previous['version']!='1.1.0':raise SystemExit('Unexpected local version')
relative=[Path(name) for name in ('src-tauri/src/main.rs','engine/bridge.py','tests/native.mjs','scripts/patch-capsq-local.py','verification/native-debug.json','verification/engine-frozen.json','verification/portable.json')]
relative.extend(path.relative_to(source) for path in (source/'portable/Lexift').rglob('*') if path.is_file())
digest=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
changes=[]
for name in relative:
    origin=source/name;destination=target/name
    if not destination.resolve().is_relative_to(target.resolve()):raise SystemExit('Invalid destination')
    if not origin.is_file():raise SystemExit(f'Missing source: {name}')
    if destination.is_file():
        current=digest(destination)
        if current==digest(origin):continue
        expected=previous['files'].get(name.as_posix())
        if current!=expected:raise SystemExit(f'Local edits found; preserved: {name}')
    changes.append(name)
backup=target.parent/'.lexift-backups'/('v1.1-capsq-'+datetime.now().strftime('%Y%m%d-%H%M%S'))
backup.mkdir(parents=True,exist_ok=False)
shutil.copy2(manifest_path,backup/'local-manifest.json')
for name in changes:
    if (target/name).is_file():
        (backup/name).parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(target/name,backup/name)
applied=[]
try:
    for name in changes:
        (target/name).parent.mkdir(parents=True,exist_ok=True)
        applied.append(name);shutil.copy2(source/name,target/name)
        assert digest(target/name)==digest(source/name),name
    files={path.relative_to(target).as_posix():digest(path) for path in sorted(target.rglob('*')) if path.is_file() and path!=manifest_path}
    manifest_path.write_text(json.dumps(dict(version='1.1.0',hotfix='caps-q-native-window-hide',files=files),ensure_ascii=False,indent=2),encoding='utf-8')
except Exception:
    for name in reversed(applied):
        if (backup/name).is_file():shutil.copy2(backup/name,target/name)
        else:(target/name).unlink()
    shutil.copy2(backup/'local-manifest.json',manifest_path)
    raise
print(json.dumps(dict(path=str(target),backup=str(backup),changedFiles=len(changes),verified=True),ensure_ascii=False))
