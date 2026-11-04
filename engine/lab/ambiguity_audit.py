"""Dictionary-wide ambiguity audit; no keystrokes or external app automation."""
import json
from pathlib import Path
import sys
import time

root=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(root/'module'))
from chinese_reading import ChineseEngine
from pinyin_phonetics import korean_variants

engine=ChineseEngine()
started=time.perf_counter()
strategies={
    'preferred':{s:korean_variants(s)[0].text for s in engine.syllables},
    'most_ambiguous':{s:max(korean_variants(s),key=lambda f:(len(engine.forms[f.text]),f.penalty,len(f.text))).text
                      for s in engine.syllables},
    'expanded':{s:max(korean_variants(s),key=lambda f:(len(f.text),len(engine.forms[f.text]),f.penalty)).text
                for s in engine.syllables},
}
report={'syllables':len(engine.syllables),'strategies':{},'candidate_limit':20}
for strategy,forms in strategies.items():
    missing=[];candidate_missing=[];maximum_paths=0;maximum_queries_ms=0.0;polyphonic=0
    for tokens in engine.words:
        source=''.join(forms[s] for s in tokens)
        readings=engine.readings(source)
        maximum_paths=max(maximum_paths,len(readings))
        if tokens not in {t for _,t in readings}:
            missing.append({'source':source,'reading':' '.join(tokens)})
        if strategy=='most_ambiguous':
            before=time.perf_counter();answer=engine.query(source)
            maximum_queries_ms=max(maximum_queries_ms,(time.perf_counter()-before)*1000)
            target=' '.join(tokens)
            displayed={reading for forms in answer['reading_alternatives'].values() for reading in forms}
            if target not in answer['readings'] and target in displayed:
                polyphonic+=1
            if target not in displayed:
                candidate_missing.append({'source':source,'reading':target,'word':engine.words[tokens][0][0],
                                          'displayed_readings':sorted(set(answer['readings']))})
            assert len(answer['candidates'])<=20
            assert len(answer['candidates'])==len(set(answer['candidates']))==len(answer['readings'])
    report['strategies'][strategy]={'checked':len(engine.words),'unreachable':missing,
        'maximum_paths':maximum_paths,'not_displayed_in_top20':candidate_missing,
        'polyphonic_shared_candidates':polyphonic,
        'query_max_ms':round(maximum_queries_ms,2)}
report['passed']=all(not result['unreachable'] for result in report['strategies'].values())
report['elapsed_ms']=round((time.perf_counter()-started)*1000,2)
(root/'test-results/ambiguity-audit-1.0.1.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({key:{'checked':value['checked'],'unreachable':len(value['unreachable']),
    'not_displayed_in_top20':len(value['not_displayed_in_top20']),'maximum_paths':value['maximum_paths'],
    'query_max_ms':value['query_max_ms']} for key,value in report['strategies'].items()},indent=2))
raise SystemExit(0 if report['passed'] else 1)
