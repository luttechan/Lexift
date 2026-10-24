import json,queue,subprocess,threading
from pathlib import Path
root=Path(__file__).resolve().parents[1]
p=subprocess.Popen([str(root/'lab/ime_candidate_host.exe'),'--query-server'],stdin=subprocess.PIPE,stdout=subprocess.PIPE)
lines=queue.Queue()
def read():
    for line in p.stdout:lines.put(json.loads(line.decode('utf-8')))
threading.Thread(target=read,daemon=True).start();lines.get(timeout=10)
words=['고','고치','고치소','고치소-','고치소-사','고치소-사마','고치소-사마데시타','모요-데스','와타시와가쿠세이데스','쿄-와이-텐키데스']
rows=[]
try:
    for i,word in enumerate(words,1):
        hexed=''.join(f'{ord(c):04x}' for c in word)
        p.stdin.write(f'QUERY {i} {hexed}\n'.encode());p.stdin.flush()
        while True:
            row=lines.get(timeout=8)
            if not row.get('partial'):
                rows.append(row);break
finally:
    p.stdin.write(b'QUIT\n');p.stdin.flush();p.wait(timeout=5)
(root/'test-results/phrase-probe.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf8')
for r in rows:print(json.dumps(r,ensure_ascii=True))
