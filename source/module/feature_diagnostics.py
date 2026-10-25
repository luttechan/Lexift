"""Verify packaged settings, dictionary and branding without external UI control."""
import hashlib,json,tempfile,time,threading
from pathlib import Path
from PySide6.QtCore import QSettings,QTimer
from PySide6.QtWidgets import QApplication
import app
from custom_dictionary import CustomDictionary
from i18n import set_language,tr,LANGUAGES
from notification_sound import NotificationSound,sound_path
from preferences import migrate_preferences
import update_core

def verify(output):
    qt=QApplication.instance() or QApplication([]);qt.setQuitOnLastWindowClosed(False)
    app.choose_font(qt);qt.setStyleSheet(app.QSS)
    result={'version':app.VERSION,'product':app.PRODUCT,'passed':False,'checks':{}}
    checks=result['checks']
    from isolated_hotkeys import HookService
    worker=HookService();errors=[]
    def start_worker():
        try:worker.ensure_started()
        except Exception as error:errors.append(str(error))
    thread=threading.Thread(target=start_worker)
    started=time.perf_counter();thread.start();heartbeats=0
    while thread.is_alive() and time.perf_counter()-started<12:
        qt.processEvents();heartbeats+=1;time.sleep(.005)
    result['keyboard_start_ms']=round((time.perf_counter()-started)*1000,2)
    result['startup_heartbeats']=heartbeats
    checks['nonblocking_keyboard_start']=not thread.is_alive() and not errors and worker.connection is not None and heartbeats>0
    worker.close();thread.join(2)
    with tempfile.TemporaryDirectory() as directory:
        store=QSettings(str(Path(directory)/'new.ini'),QSettings.Format.IniFormat)
        old=QSettings(str(Path(directory)/'old.ini'),QSettings.Format.IniFormat)
        old.setValue('general/ui_language','en');old.setValue('features/ja',False)
        CustomDictionary(old).replace([dict(keyword='스미네',text='澄音',language='ja'),dict(keyword='니하오',text='你好呀',language='zh')])
        checks['legacy_migration']=migrate_preferences(store,old) and not store.value('features/ja',type=bool)
        dictionary=CustomDictionary(store)
        checks['custom_japanese']=dictionary.merge('ja','스미네',{'kana':'すみね','candidates':['私']})['candidates'][0]=='澄音'
        checks['custom_chinese']=dictionary.merge('zh','니하오',{'kana':'ni hao','candidates':['你好']})['candidates'][0]=='你好呀'
        checks['language_scoping']=dictionary.lookup('zh','스미네') is None
        checks['branding']=app.PRODUCT=='Lexift' and app.VERSION=='1.0.2' and update_core.REPOSITORY=='luttechan/Lexift'
        started=time.perf_counter();window=app.MainWindow(store,[],False)
        window.navigate(2)
        checks['separate_panels']=window.shortcut_modifier.parent() is not window.ime_modifier.parent()
        checks['persisted_checkbox']=not window.feature_checks['ja'].isChecked() and window.feature_checks['zh'].isChecked()
        window.navigate(4)
        checks['dictionary_page']=window.dictionary_editor.model.rowCount()==2
        from PySide6.QtWidgets import QLabel
        checks['japanese_translation_qa_credit']=any(w.text()=='Translation (JP) & QA :' for w in window.special_host.findChildren(QLabel)) and any(w.text()=='루노' for w in window.special_host.findChildren(QLabel))
        result['construct_all_pages_ms']=round((time.perf_counter()-started)*1000,2)
        for code,_ in LANGUAGES:
            set_language(code)
            if code!='ko':
                checks['translation_'+code]=all(tr(key)!=key for key in ('한–일 변환','한–중 변환','사용자 사전','언어 스위칭'))
        checks['notify_asset']=hashlib.sha256(sound_path().read_bytes()).hexdigest()=='e134873ca4fd9140e5a90ed5d57814115b2f283dacde68de138b25a5c80ec264'
        done=threading.Event();paths=[]
        sound=NotificationSound(lambda path:(paths.append(str(path)),done.set()))
        sound.play();checks['async_notify_path']=done.wait(2) and paths==[str(sound_path())]
        sound.close();sound.thread.join(2)
        checks['sound_thread_stopped']=not sound.thread.is_alive()
        window._preferences_timer.stop();window.deleteLater();qt.processEvents()
    result['passed']=all(checks.values())
    Path(output).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
    return 0 if result['passed'] else 1
