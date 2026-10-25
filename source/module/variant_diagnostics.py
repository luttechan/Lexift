"""Frozen-build checks for traditional, Bopomofo, one worker and four shortcuts."""
import json,tempfile,time
from pathlib import Path
from PySide6.QtCore import QSettings,QEvent,QCoreApplication,Qt
from PySide6.QtWidgets import QApplication
import app
from chinese_reading import ChineseEngine
from chinese_variants import OutputProfiles,zhuyin_syllable
from chinese_query_client import ChineseQueryClient,_running_threads
from custom_dictionary import CustomDictionary
from i18n import LANGUAGES,set_language,tr

def verify(output):
    qt=QApplication.instance() or QApplication([]);qt.setQuitOnLastWindowClosed(False)
    app.choose_font(qt);qt.setStyleSheet(app.QSS)
    report=dict(version=app.VERSION,passed=False,checks={},queries=[])
    checks=report['checks'];client=None
    try:
        engine=ChineseEngine();profiles=OutputProfiles()
        checks['all_415_syllables']=len(engine.syllables)==415 and all(zhuyin_syllable(s) for s in engine.syllables)
        for source,tw,bo in (('니하오','你好','ㄋㄧ ㄏㄠ'),('중궈','中國','ㄓㄨㄥ ㄍㄨㄛ'),
                             ('터우파','頭髮','ㄊㄡ ㄈㄚ'),('황허우','皇后','ㄏㄨㄤ ㄏㄡ'),('췐','權','ㄑㄩㄢ')):
            started=time.perf_counter();raw=engine.query(source)
            traditional=profiles.transform(raw,'zh_tw');bopomofo=profiles.transform(raw,'zh_bopomofo')
            report['queries'].append(dict(source=source,traditional=traditional['candidates'],bopomofo=bopomofo['candidates'],
                passed=tw in traditional['candidates'] and bo in bopomofo['candidates'],elapsed_ms=round((time.perf_counter()-started)*1000,3)))
        checks['real_dictionary_outputs']=all(row['passed'] for row in report['queries'])
        from candidate_delegate import CandidateDelegate
        renderer=CandidateDelegate()
        characters=set(''.join(zhuyin_syllable(s) for s in engine.syllables))
        checks['bopomofo_font_coverage']=all(renderer.raw[renderer.font_index(c)].supportsCharacter(ord(c)) for c in characters)
        client=ChineseQueryClient();thread=client.thread;received=[];errors=[]
        client.result.connect(lambda serial,data:received.append((serial,data)))
        client.failed.connect(errors.append);client.start()
        async_times=[];heartbeats=0
        for index,mode in enumerate(('zh','zh_tw','zh_bopomofo','zh')):
            started=time.perf_counter();serial=client.request('중궈',mode)
            while not any(n==serial for n,_ in received) and not errors and time.perf_counter()-started<8:
                qt.processEvents();heartbeats+=1;time.sleep(.001)
            data=next((data for n,data in received if n==serial),{})
            expected={'zh':'中国','zh_tw':'中國','zh_bopomofo':'ㄓㄨㄥ ㄍㄨㄛ'}[mode]
            checks['async_'+str(index)+'_'+mode]=expected in data.get('candidates',[]) and client.thread is thread
            async_times.append(dict(mode=mode,ms=round((time.perf_counter()-started)*1000,3)))
        report['async_queries']=async_times;checks['gui_responsive']=heartbeats>0 and not errors
        client.stop();deadline=time.monotonic()+3
        while _running_threads and time.monotonic()<deadline:qt.processEvents();time.sleep(.001)
        checks['worker_released']=not _running_threads;client=None
        with tempfile.TemporaryDirectory() as directory:
            for code,_ in LANGUAGES:
                set_language(code)
                store=QSettings(str(Path(directory)/(code+'.ini')),QSettings.Format.IniFormat)
                dictionary=CustomDictionary(store)
                rows=[dict(keyword='니하오',text=text,language=name) for name,text in
                      (('ja','例'),('zh','你好'),('zh_tw','妳好'),('zh_bopomofo','ㄋㄧ ㄏㄠ'))]
                dictionary.replace(rows);checks['dictionary_'+code]=CustomDictionary(store).entries==rows
                window=app.MainWindow(store,[],False);window.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
                window._preferences_timer.stop();window.navigate(2)
                checks['four_bindings_'+code]=len(window.feature_checks)==5 and window.traditional_key.currentData()=='T'
                window.traditional_key.setCurrentIndex(window.traditional_key.findData('A'))
                checks['four_way_conflict_'+code]=not any(b.isEnabled() for b in (window.selector_apply,window.ime_apply,window.chinese_apply,window.traditional_apply))
                window.traditional_key.setCurrentIndex(window.traditional_key.findData('T'))
                checks['valid_four_bindings_'+code]=all(b.isEnabled() for b in (window.selector_apply,window.ime_apply,window.chinese_apply,window.traditional_apply))
                if code!='ko':checks['translations_'+code]=all(tr(k)!=k for k in ('한–중 번체','주음부호','한–중 번체·주음'))
                window.hide();window.deleteLater()
                QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete);qt.processEvents()
        from native_hooks import library
        checks['four_shortcut_native_abi']=library().ks_abi_version()==6
        report['passed']=all(checks.values())
    except Exception:
        import traceback
        report['error']=traceback.format_exc()
    finally:
        if client:client.stop()
        set_language('ko')
        Path(output).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return 0 if report['passed'] else 1
