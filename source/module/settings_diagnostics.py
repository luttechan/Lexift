"""Exercise owned settings widgets with temporary preferences in the EXE too."""
import json
from pathlib import Path
import tempfile
import time

from PySide6.QtCore import QCoreApplication, QEvent, QSettings, Qt
from PySide6.QtWidgets import QApplication, QLabel, QFrame
import app
from custom_dictionary import CustomDictionary
from i18n import LANGUAGES, set_language, tr


def verify(output):
    qt = QApplication.instance() or QApplication([])
    qt.setQuitOnLastWindowClosed(False)
    app.choose_font(qt)
    qt.setStyleSheet(app.QSS)
    result = dict(version=app.VERSION, passed=False, languages=[], checks={})
    try:
        with tempfile.TemporaryDirectory() as directory:
            for code, _ in LANGUAGES:
                set_language(code)
                store = QSettings(str(Path(directory)/(code+'.ini')), QSettings.Format.IniFormat)
                for key, value in (('general/show_dashboard',False), ('general/start_notice',True),
                                   ('general/sound',False), ('features/ja',False), ('features/zh',True)):
                    store.setValue(key,value)
                dictionary = CustomDictionary(store)
                dictionary.replace([dict(keyword='스미네',text='澄音',language='ja'),
                                    dict(keyword='니하오',text='你好呀',language='zh')])
                before = {key:store.value(key) for key in store.allKeys()}
                window = app.MainWindow(store, [], False)
                window.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
                window.show()
                qt.processEvents()
                window._preferences_timer.stop()
                first=time.perf_counter();window.nav_buttons[2].click();window.grab()
                first_visit_ms=round((time.perf_counter()-first)*1000,3)
                window.navigate(0)
                started = time.perf_counter()
                for _ in range(3):
                    window._prepare_next_page()
                window._preferences_timer.stop()
                prepared_ms = round((time.perf_counter()-started)*1000,3)
                checks = {}
                checks['preparation_keeps_settings'] = before == {key:store.value(key) for key in store.allKeys()}
                checks['preparation_keeps_selection'] = window.pages.currentIndex()==0
                checks['no_background_statistics'] = not window.runtime_stats._sampling and window.runtime_stats._sampler.thread is None
                checks['all_pages_ready'] = window._ready_pages=={0,1,2,3,4}
                marks=[w for w in window.findChildren(QFrame) if w.objectName()=='brandMark']
                checks['three_packaged_logos'] = len(marks)==3 and all(not w.findChild(QLabel).pixmap().isNull() for w in marks)
                timings = []
                for index in (2,1,3,4,0,2):
                    started = time.perf_counter()
                    window.nav_buttons[index].click()
                    qt.processEvents()
                    window.grab()
                    timings.append(dict(page=index, ms=round((time.perf_counter()-started)*1000,3)))
                checks['conversion_heading'] = any(w.text()==tr('한글 환경 언어 변환') for w in window.findChildren(QLabel))
                checks['translated_heading'] = code=='ko' or tr('한글 환경 언어 변환')!='한글 환경 언어 변환'
                checks['saved_preferences_loaded'] = not window.show_at_start.isChecked() and window.start_notice.isChecked() and not window.sound_notice.isChecked()
                for control,key in ((window.show_at_start,'general/show_dashboard'),
                                    (window.start_notice,'general/start_notice'),(window.sound_notice,'general/sound')):
                    control.toggle()
                    checks['save_'+key] = store.value(key,type=bool)==control.isChecked()
                    control.toggle()
                checks['feature_flags_loaded'] = not window.feature_checks['ja'].isChecked() and window.feature_checks['zh'].isChecked()
                signals=[]
                window.feature_requested.connect(lambda name,value:signals.append((name,value)))
                window.feature_checks['ja'].toggle()
                checks['feature_change_signal'] = signals==[('ja',True)]
                window.feature_checks['ja'].toggle()
                window.shortcut_key.setCurrentIndex(window.shortcut_key.findData('A'))
                checks['duplicate_shortcuts_blocked'] = not any(w.isEnabled() for w in (window.selector_apply,window.ime_apply,window.chinese_apply))
                window.shortcut_key.setCurrentIndex(window.shortcut_key.findData('Q'))
                checks['valid_shortcuts_allowed'] = all(w.isEnabled() for w in (window.selector_apply,window.ime_apply,window.chinese_apply))
                checks['all_display_languages'] = {window.language_combo.itemData(n) for n in range(window.language_combo.count())}=={c for c,_ in LANGUAGES}
                checks['dictionary_loaded'] = window.dictionary_editor.model.rowCount()==2
                window.dictionary_editor.model.setData(window.dictionary_editor.model.index(0,1),'澄音さん')
                window.dictionary_saved.connect(dictionary.replace)
                window.dictionary_editor.save()
                checks['dictionary_saved'] = CustomDictionary(store).lookup('ja','스미네')=='澄音さん'
                scroll=window.pages.widget(2)
                scroll.verticalScrollBar().setValue(scroll.verticalScrollBar().maximum())
                qt.processEvents()
                window.grab().save(str(Path(output).with_name('settings-'+code+'.png')))
                result['languages'].append(dict(language=code,checks=checks,first_visit_ms=first_visit_ms,prepare_ms=prepared_ms,navigation=timings))
                window._preferences_timer.stop()
                window.hide()
                window.deleteLater()
                QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete)
                qt.processEvents()
        result['checks']['settings_matrix'] = all(all(row['checks'].values()) for row in result['languages'])
        result['checks']['nine_languages'] = len(result['languages'])==len(LANGUAGES)
        result['passed'] = all(result['checks'].values())
    except Exception as error:
        import traceback
        result['error'] = traceback.format_exc()
    finally:
        set_language('ko')
        Path(output).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return 0 if result['passed'] else 1
