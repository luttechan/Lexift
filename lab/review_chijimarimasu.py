"""Headless diagnostic using the existing private-desktop query host."""
import json
import queue
import subprocess
import threading
from pathlib import Path

root = Path(__file__).resolve().parents[1]
words = ['\uce58\uc9c0\ub9c8\ub9ac\ub9c8\uc2a4', '\uce58\uc9c0\ub9c8\ub9ac\ub9c8\uc2dc\ud0c0', '\uc624-\ud0a4\uc774', '\uc624\ub124-\uc0c1', '\uc640\ud0c0\uc2dc\uc640\uac00\ucfe0\uc138\uc774\ub370\uc2a4', '\uc4d4\ud0a4', '\uace0\uce58\uc18c-\uc0ac\ub9c8', '\ucf54-\uc8e0-']
rows = []
# A separate host per input avoids attributing a previous candidate list to it.
for word in words:
    p = subprocess.Popen([str(root/'lab/ime_candidate_host.exe'), '--query-server'],
                         stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    lines = queue.Queue()
    def read(process=p, output=lines):
        for line in process.stdout:
            output.put(json.loads(line.decode('utf8')))
    threading.Thread(target=read, daemon=True).start()
    try:
        assert lines.get(timeout=10).get('event') == 'ready'
        encoded = ''.join(f'{ord(c):04x}' for c in word)
        p.stdin.write(f'QUERY 1 {encoded}\n'.encode()); p.stdin.flush()
        while True:
            row=lines.get(timeout=10)
            if not row.get('partial'):
                rows.append(row);break
    finally:
        p.stdin.write(b'QUIT\n'); p.stdin.flush(); p.wait(timeout=5)
(root/'test-results/chijimarimasu-review.json').write_text(
    json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf8')
for row in rows:
    print(json.dumps(row, ensure_ascii=True))
