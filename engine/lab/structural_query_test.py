"""Real IME integration and latency checks, entirely on its private desktop."""
import json
from pathlib import Path
import queue
import subprocess
import threading
import time

root=Path(__file__).resolve().parents[1]
cases=[('와타시','私'),('치지마리마스','縮まります'),('치지마리마시타','縮まりました'),
       ('치지마라나이','縮まらない'),('치지맛타','縮まった'),('치지메마스','縮めます'),
       ('오-키이','大きい'),('오네-상','お姉さん'),('쯔키','月'),('미카즈키','三日月'),
       ('와타시와가쿠세이데스','私は学生です'),('니혼고오벤쿄-시마스','日本語を勉強します'),
       ('도쿄에이키마스','東京へ行きます'),('고치소-사마','ご馳走様'),('코-죠-','工場'),
       ('센세-데스','先生です'),('모요-데스','模様です'),('코-히-','コーヒー')]
p=subprocess.Popen([str(root/'lab/ime_candidate_host.exe'),'--query-server'],
                   stdin=subprocess.PIPE,stdout=subprocess.PIPE)
lines=queue.Queue()
def read():
    for line in p.stdout:lines.put(json.loads(line.decode('utf8')))
threading.Thread(target=read,daemon=True).start()
assert lines.get(timeout=10).get('event')=='ready'
rows=[]
try:
    for serial,(source,expected) in enumerate(cases,1):
        began=time.perf_counter();first=found=None;updates=0
        encoded=''.join(f'{ord(c):04x}' for c in source)
        p.stdin.write(f'QUERY {serial} {encoded}\n'.encode());p.stdin.flush()
        while True:
            data=lines.get(timeout=10);elapsed=round((time.perf_counter()-began)*1000)
            assert data['id']==serial,data
            updates+=1
            if first is None:first=elapsed
            if found is None and expected in data['candidates']:found=elapsed
            if not data.get('partial'):break
        passed=expected in data['candidates'] and data['queried_readings']==len(data['kana_variants'])
        if source=='와타시와가쿠세이데스':passed=passed and '私' not in data['candidates']
        if source=='치지마리마스':passed=passed and not any(s.count('まり')>1 for s in data['candidates'])
        rows.append({'source':source,'expected':expected,'first_ms':first,'expected_ms':found,
                     'complete_ms':elapsed,'updates':updates,'passed':passed,'result':data})
finally:
    p.stdin.write(b'QUIT\n');p.stdin.flush();p.wait(timeout=5)
report={'passed':all(row['passed'] for row in rows),'cases':rows,'computer_use':False}
(root/'test-results/structural-query-final.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({**report,'cases':[{k:v for k,v in row.items() if k!='result'} for row in rows]},ensure_ascii=True))
assert report['passed']
