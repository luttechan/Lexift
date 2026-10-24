"""Audit dictionary-wide Hangul aliases through the actual reading lattice."""
import json
from pathlib import Path
import sys
import time

location=Path(__file__).resolve().parent
root=location.parent if location.name=='lab' else location/'Lexift v.0.8'
sys.path.insert(0,str(root/'module'))
from chinese_reading import ChineseEngine
from pinyin_phonetics import classify, korean_variants

engine=ChineseEngine()
started=time.perf_counter()
missing=[];rows=[];total=0;missing_candidates=[];candidate_checks=0
for spelling in engine.syllables:
    sound=classify(spelling)
    forms=korean_variants(spelling)
    for form in forms:
        total+=1
        if (spelling,) not in {tokens for _,tokens in engine.readings(form.text)}:
            missing.append({'spelling':spelling,'form':form.text})
        characters={text for text,_ in engine.words.get((spelling,),())}
        if characters:
            candidate_checks+=1
            if not characters.intersection(engine.query(form.text)['candidates']):
                missing_candidates.append({'spelling':spelling,'form':form.text})
    rows.append({'spelling':spelling,'initial':sound.initial,'final':sound.final,
                 'rules':sound.rules,'forms':[f.text for f in forms]})
examples={'췐':'quan','취엔':'quan','취앤':'quan','줸':'juan','쥐엔':'juan',
          '쉔':'xuan','쉬엔':'xuan','위엔':'yuan','위앤':'yuan',
          '숑':'xiong','시옹':'xiong','치웅':'qiong',
          '쉬에':'xue','췬':'qun','쥔':'jun','쉰':'xun','뉘':'nv','뤼':'lv'}
checks=[]
for source,spelling in examples.items():
    checks.append({'source':source,'expected':spelling,
                   'passed':(spelling,) in {tokens for _,tokens in engine.readings(source)}})
phrases={'췐':'全','췐부':'全部','취엔부':'全部','안췐':'安全',
         '웬췐':'温泉','쉔저':'选择','쉬엔저':'选择','줸콴':'捐款',
         '위엔':'元','숑마오':'熊猫','시옹마오':'熊猫','슈에셩':'学生'}
queries=[]
for source,expected in phrases.items():
    before=time.perf_counter();answer=engine.query(source)
    queries.append({'source':source,'expected':expected,'candidates':answer['candidates'],
                    'readings':answer['readings'],
                    'elapsed_ms':round((time.perf_counter()-before)*1000,2),
                    'passed':expected in answer['candidates']})
result={'syllables':len(rows),'forms':total,'unreachable_forms':missing,
        'candidate_checks':candidate_checks,'missing_candidates':missing_candidates,
        'examples':checks,'queries':queries,'elapsed_ms':round((time.perf_counter()-started)*1000,2),
        'passed':not missing and not missing_candidates and all(c['passed'] for c in checks+queries),'classification':rows}
output=root/'test-results'/('pinyin-coverage-baseline.json' if '--baseline' in sys.argv else 'pinyin-coverage-final.json')
output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
if '--baseline' not in sys.argv:
    (root/'test-results/pinyin-classification.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({k:v for k,v in result.items() if k!='classification'},ensure_ascii=True,indent=2))
