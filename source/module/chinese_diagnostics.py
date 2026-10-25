"""Exercise the frozen Chinese dictionary, async client and three shortcuts."""
import json
from pathlib import Path
import time
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from chinese_query_client import ChineseQueryClient


def verify(output):
    qt=QApplication.instance() or QApplication([])
    qt.setQuitOnLastWindowClosed(False)
    result={'version':'1.0.3','backend':'offline-pinyin','passed':False,'queries':[]}
    words=[('니하오','你好'),('셰셰','谢谢'),('씨에씨에','谢谢'),('워아이니','我爱你'),
           ('중궈','中国'),('베이징','北京'),('짜이젠','再见'),('니하오마','你好吗'),
           ('메이관시','没关系'),('진티엔','今天'),('펑요우','朋友')]
    first_choice_cases=len(words)
    words.extend([('췐','全'),('췐부','全部'),('취엔부','全部'),('안췐','安全'),
                  ('웬췐','温泉'),('쉔저','选择'),('쉬엔저','选择'),('줸콴','捐款'),
                  ('위엔','元'),('숑마오','熊猫'),('시옹마오','熊猫'),('슈에셩','学生'),
                  ('퍄오','覅'),('피아오','覅'),
                  ('치','吃'),('치','次'),('츠','吃'),('츠','次'),
                  ('지','字'),('시','四'),('치판','吃饭'),('츠판','吃饭'),
                  ('치둥시','吃东西'),('치처','汽车'),('치위','词语'),('시거','四个'),
                  ('파오파오','宝宝'),('피아오파이','表白'),('타이피아오','代表'),
                  ('쿠앙피아오','光标'),('시안','西安'),('뤼','吕'),('뉘','女')])
    client=ChineseQueryClient()
    started=time.perf_counter();request_started=started
    heartbeat=[0]
    pulse=QTimer();pulse.timeout.connect(lambda:heartbeat.__setitem__(0,heartbeat[0]+1));pulse.start(10)
    def save():
        Path(output).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    def failed(message):
        result['error']=message;qt.quit()
    def receive(serial,data):
        nonlocal request_started
        text,expected=words[len(result['queries'])]
        values=data.get('candidates',[])
        require_first=len(result['queries'])<first_choice_cases
        matched=bool(values) and (values[0]==expected if require_first else expected in values)
        result['queries'].append({'source':text,'reading':data.get('kana'),
            'elapsed_ms':round((time.perf_counter()-request_started)*1000,2),'candidates':values,
            'expected':expected,'require_first':require_first,
            'matched_reading':data.get('readings',[])[values.index(expected)] if expected in values else None,
            'passed':data.get('source')==text and matched})
        save()
        if len(result['queries'])==len(words):
            result['passed']=all(row['passed'] for row in result['queries'])
            client.stop();QTimer.singleShot(200,qt.quit)
        else:
            request_started=time.perf_counter();client.request(words[len(result['queries'])][0])
    client.result.connect(receive);client.failed.connect(failed)
    save()
    # Requests submitted before worker readiness must emit only the newest.
    client.request('버릴입력');client.request('잘못된입력');client.request(words[0][0])
    client.start()
    timer=QTimer();timer.setSingleShot(True);timer.timeout.connect(lambda:failed('Chinese diagnostic timeout'));timer.start(15000)
    qt.exec();client.stop()
    try:
        client.thread.wait(3000)
    except RuntimeError:
        pass  # finished -> deleteLater already released the QThread
    result['gui_heartbeats']=heartbeat[0]
    result['elapsed_ms']=round((time.perf_counter()-started)*1000)
    try:
        from isolated_hotkeys import CapsQHook
        hook=CapsQHook(lambda _:None,on_ime=lambda _:None,on_chinese=lambda _:None)
        try:
            hook.start();result['three_shortcuts_registered']=True
        finally:
            hook.stop()
    except Exception as error:
        result['three_shortcuts_registered']=False;result['shortcut_error']=str(error)
    result['passed']=result['passed'] and result['three_shortcuts_registered'] and heartbeat[0]>0
    save()
    return 0 if result['passed'] else 1
