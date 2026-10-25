"""Check the packaged Qt/IME pipeline without sending input to another app."""
import json
from pathlib import Path
import time
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from ime_inline import host_path
from ime_query_client import QueryClient


def verify(output):
    Path(output).write_text('{"stage":"initializing Qt","passed":false}',encoding='utf-8')
    qt=QApplication.instance() or QApplication([])
    qt.setQuitOnLastWindowClosed(False)
    client=QueryClient(host_path())
    words=[('와타시','私'),('와타시','私'),('니혼고','日本語'),('갓코우','学校'),
           ('쿄우','今日'),('코-히-','コーヒー'),('모노즈쿠리','ものづくり'),
           ('치지마리마스','縮まります'),('오-키이','大きい'),
           ('와타시와가쿠세이데스','私は学生です'),('미카즈키','三日月'),
           ('아리가토-','ありがとう'),('오하요-','おはよう'),
           ('주-스','ジュース'),('파이루','ファイル'),
           ('바이올린','バイオリン'),('듀엣토','デュエット'),
           ('쓰나미','津波'),('마쓰모토','松本'),('지바','千葉')]
    results={'version':'1.0.2','queries':[],'passed':False}
    Path(output).write_text(json.dumps(results),encoding='utf-8')
    started=time.perf_counter();request_started=started
    def receive(serial,data):
        nonlocal request_started
        if data.get('partial'):
            return
        text,expected=words[len(results['queries'])]
        values=data.get('candidates',[])
        results['queries'].append({'source':text,'reading':data.get('kana'),'elapsed_ms':round((time.perf_counter()-request_started)*1000),
                                  'candidate_count':len(values),'passed':data.get('source')==text and expected in values})
        Path(output).write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
        if len(results['queries'])==len(words):
            results['passed']=all(row['passed'] for row in results['queries'])
            client.stop();QTimer.singleShot(200,qt.quit)
        else:
            request_started=time.perf_counter();client.request(words[len(results['queries'])][0])
    def failed(message):
        results['error']=message;qt.quit()
    client.result.connect(receive);client.failed.connect(failed)
    client.start();client.request(words[0][0])
    timer=QTimer();timer.setSingleShot(True);timer.timeout.connect(lambda:failed('Diagnostic timeout'))
    timer.start(30000);qt.exec();client.stop()
    results['elapsed_ms']=round((time.perf_counter()-started)*1000)
    Path(output).write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
    return 0 if results['passed'] else 1
