import json
from pathlib import Path
from pinyin_tones import apply_tone
from native_hooks import library

def verify(output):
    from compact_dictionary import CompactDictionary
    from chinese_reading import ChineseEngine
    report=dict(version='1.0.5',passed=False,checks={})
    try:
        checks=report['checks']
        examples=(('hao',3,'hǎo'),('liu',2,'liú'),('gui',3,'guǐ'),('nǐhǎo',4,'nǐhào'),('lv',4,'lǜ'),('nü',0,'nü'))
        checks['tone_rules']=all(apply_tone(a,t)==b for a,t,b in examples)
        checks['ke_all_tones']=all(apply_tone('kè' if t==0 else 'ke',t)==word
                                  for t,word in enumerate(('ke','kē','ké','kě','kè')))
        checks['native_tone_abi']=library().ks_abi_version()==6
        checks['keypad_tone_handler_packaged']=bool(library().ks_caps_tone_event_step)
        checks['native_worker_packaged']=Path(__file__).with_name('lexift_keyboard.exe').is_file()
        engine=ChineseEngine();checks['indexed_dictionary']=isinstance(engine.words,CompactDictionary)
        checks['index_matches_source']=engine.query('췐')['candidates'] and '你好' in engine.query('니하오')['candidates'];engine.close()
        report['passed']=all(checks.values())
    except Exception:
        import traceback
        report['error']=traceback.format_exc()
    Path(output).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return 0 if report['passed'] else 1
