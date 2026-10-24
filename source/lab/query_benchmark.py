"""Measure cold startup separately from a sequence of uncached real IME queries."""
import json
from pathlib import Path
import queue
import subprocess
import threading
import time
root=Path(__file__).resolve().parents[1]
start=time.perf_counter()
process=subprocess.Popen([str(root/'lab/ime_candidate_host.exe'),'--query-server'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
lines=queue.Queue()
def read():
    for line in process.stdout:
        lines.put(json.loads(line.decode('utf-8')))
threading.Thread(target=read,daemon=True).start()
ready=lines.get(timeout=8);assert ready.get('event')=='ready',ready
results={'startup_ms':round((time.perf_counter()-start)*1000),'queries':[]}
def encoded(text):
    data=text.encode('utf-16-le')
    return ''.join(f'{int.from_bytes(data[i:i+2],"little"):04x}' for i in range(0,len(data),2))
try:
    for i,(text,expected) in enumerate([('와타시','私')]*3+[('니혼고','日本語'),('갓코우','学校'),('쿄우','今日'),('코-히-','コーヒー'),('코-죠-','工場'),('모요-데스','模様です')]*2,1):
        start=time.perf_counter()
        process.stdin.write(f'QUERY {i} {encoded(text)}\n'.encode());process.stdin.flush()
        first=None
        while True:
            data=lines.get(timeout=6)
            if first is None:first=round((time.perf_counter()-start)*1000)
            if not data.get('partial'):break
        row={'source':text,'first_ms':first,'elapsed_ms':round((time.perf_counter()-start)*1000),'count':len(data.get('candidates',[])),'passed':expected in data.get('candidates',[])}
        results['queries'].append(row)
        assert data['id']==i and row['passed'],data
finally:
    process.stdin.write(b'QUIT\n');process.stdin.flush();process.wait(timeout=5)
results['exit_code']=process.returncode
(root/'test-results/query-benchmark.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(results,ensure_ascii=True,indent=2))
