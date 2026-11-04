import ast,json,re,runpy,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'engine/module'))
base=runpy.run_path(str(root/'engine/module/i18n.py'))['_ROWS']
extra_file=root/'engine/module/desktop_messages.py'
if extra_file.exists():base.update(runpy.run_path(str(extra_file))['ROWS'])
keys=set()
for path in (root/'src').glob('*.tsx'):
    source='\n'.join(line for line in path.read_text(encoding='utf-8').splitlines()
                     if not line.rstrip().endswith('// i18n-sample'))
    # Include static labels inside arrays/conditional expressions as well as t().
    for literal in re.findall(r"'([^'\n]*[가-힣][^'\n]*)'",source):
        if not re.search(r'[<>;=]',literal):keys.add(literal)
keys.update(['선택 메뉴를 표시하지 못했습니다. 다시 시도하세요.'])
for path in (root/'engine/bridge.py',root/'src-tauri/src/main.rs'):
    backend_keys=re.findall(r'''["']([^"'\n]*[가-힣][^"'\n]*)["']''',path.read_text(encoding='utf-8'))
    keys.update(key for key in backend_keys if key in base)
missing=sorted(keys-base.keys())
if missing:
    print(json.dumps(missing,ensure_ascii=False,indent=2));sys.exit(1)
languages=['en','ja','zh_CN','zh_TW','fr','es','ru','de']
catalog={'ko':{key:key for key in keys}}
for index,code in enumerate(languages):
    catalog[code]={key:base[key][index] for key in keys}
    assert all(catalog[code].values()),code
    for key in keys:assert set(re.findall(r'\{\w+\}',key))==set(re.findall(r'\{\w+\}',catalog[code][key])),(code,key)
(root/'src/locales.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf-8')
print(f'{len(keys)} messages, {len(catalog)} languages; no missing translations or placeholder mismatches')
