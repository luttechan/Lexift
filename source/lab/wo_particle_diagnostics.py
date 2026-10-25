"""Exercise long object-particle readings through the actual native IME host."""
import argparse
import json
from pathlib import Path
import sys
import time

root=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(root/'module'))
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from ime_query_client import QueryClient

CASES=[
 ('와타시와키노-토쇼칸데카리타아타라시이혼오토모다치니와타시마시타',
  'わたしはきのうとしょかんでかりたあたらしいほんをともだちにわたしました'),
 ('와타시와오오사카데카리타아오이혼오요미나가라온가쿠오키키마스',
  'わたしはおおさかでかりたあおいほんをよみながらおんがくをききます'),
 ('아오이카미오오오키나하코니이레마스','あおいかみをおおきなはこにいれます'),
 ('오모이데오오모이다시마스','おもいでをおもいだします'),
 ('호-코쿠쇼오테-슈츠시마스','ほうこくしょをていしゅつします'),
 ('혼오니혼니오쿠리마스','ほんをにほんにおくります'),
]

def verify(host,output):
    qt=QApplication.instance() or QApplication([])
    qt.setQuitOnLastWindowClosed(False)
    client=QueryClient(host)
    report={'passed':False,'queries':[],'host':str(host)}
    started=time.perf_counter();query_started=started;first=None
    def save():output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    def failed(message):report['error']=message;qt.quit()
    def received(serial,data):
        nonlocal query_started,first
        if first is None:first=round((time.perf_counter()-query_started)*1000,2)
        if data.get('partial'):return
        source,expected=CASES[len(report['queries'])]
        pairs=list(zip(data.get('candidates',[]),data.get('readings',[])))
        matches=[word for word,reading in pairs if reading==expected and 'を' in word and
                 any('\u4e00'<=letter<='\u9fff' for letter in word)]
        report['queries'].append({'source':source,'expected_reading':expected,
            'first_result_ms':first,'final_ms':round((time.perf_counter()-query_started)*1000,2),
            'queried_readings':data.get('queried_readings'),'matched_candidates':matches[:5],
            'passed':data.get('source')==source and expected in data.get('kana_variants',[]) and bool(matches)})
        save()
        if len(report['queries'])==len(CASES):
            report['passed']=all(row['passed'] for row in report['queries'])
            client.stop();QTimer.singleShot(200,qt.quit)
        else:
            query_started=time.perf_counter();first=None
            client.request(CASES[len(report['queries'])][0])
    client.result.connect(received);client.failed.connect(failed)
    save();client.start();client.request(CASES[0][0])
    timer=QTimer();timer.setSingleShot(True);timer.timeout.connect(lambda:failed('Particle diagnostic timeout'))
    timer.start(60000);qt.exec();client.stop()
    report['elapsed_ms']=round((time.perf_counter()-started)*1000,2);save()
    print(json.dumps(report,ensure_ascii=True,indent=2))
    return 0 if report['passed'] else 1

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--host',type=Path,default=root/'lab/ime_candidate_host.exe')
    parser.add_argument('--output',type=Path,default=root/'test-results/wo-particle-ime.json')
    args=parser.parse_args()
    raise SystemExit(verify(args.host,args.output))
