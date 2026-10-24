"""Classify Hanyu Pinyin by sound before generating Korean input aliases.

References and the scope of Korean approximations: CHINESE_INPUT.ko.md.
This module does not claim that Hangul can encode Mandarin sounds or tones
losslessly. The dictionary, not a Cartesian product, supplies legal syllables.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Syllable:
    spelling: str
    initial: str
    final: str
    initial_group: str
    final_group: str
    rules: tuple


@dataclass(frozen=True)
class KoreanForm:
    text: str
    penalty: float
    kind: str


GROUPS={'labial':('b','p','m','f'),'alveolar':('d','t','n','l'),
        'velar':('g','k','h'),'palatal':('j','q','x'),
        'retroflex':('zh','ch','sh','r'),'sibilant':('z','c','s')}
INITIALS={'b':(7,8,17),'p':(17,),'m':(6,),'f':(17,),
          'd':(3,4,16),'t':(16,),'n':(2,),'l':(5,),
          'g':(0,1,15),'k':(15,),'h':(18,),
          'j':(12,13),'q':(14,),'x':(9,10),
          'zh':(12,13),'ch':(14,),'sh':(9,10),'r':(5,),
          'z':(12,13),'c':(14,),'s':(9,10)}
ZERO={'yi':'i','ya':'ia','yan':'ian','yang':'iang','yao':'iao','ye':'ie',
      'yin':'in','ying':'ing','yong':'iong','you':'iou','yo':'io',
      'yu':'v','yue':'ve','yuan':'van','yun':'vn',
      'wu':'u','wa':'ua','wai':'uai','wan':'uan','wang':'uang',
      'wei':'uei','wen':'uen','weng':'ueng','wo':'uo'}
FINALS={'a':'아','ai':'아이','an':'안','ang':'앙','ao':'아오',
        'e':'어','ei':'에이','en':'언','eng':'엉','er':'얼','o':'오',
        'ong':'웅 옹','ou':'오우 어우','i':'이','ia':'야 이아','io':'요',
        'ian':'옌 이엔 얜 이앤','iang':'양 이앙','iao':'야오 이아오','ie':'예 이에',
        'in':'인','ing':'잉','iong':'융 이웅 용 이옹','iou':'유 이오우 이우',
        'u':'우','ua':'와 우아','uai':'와이 우아이','uan':'완 우안',
        'uang':'왕 우앙','ue':'웨 우에','uei':'웨이 우에이 우이 위',
        'uen':'원 우언 운 웬 우엔','ueng':'웡','uo':'워 우어 오',
        # üan has a front main vowel: both the familiar 위안 spelling and
        # contracted 웬/왠 or explicit 위엔/위앤 must reach the same syllable.
        # Keep 위/유 glide approximations consistent across the ü family.
        'v':'위 유','ve':'웨 위에 유에',
        'van':'위안 웬 위엔 위앤 왠 유엔 유앤 유안','vn':'윈 윤'}
APICAL={'zhi':'즈 쯔 지','chi':'츠 치','shi':'스 시 쓰','ri':'르 리',
        'zi':'쯔 즈','ci':'츠','si':'쓰 스'}
# Korean spellings often omit the already-palatalised glide after j/q.
PALATAL_JQ={'ia':'아 야 이아','iao':'아오 야오 이아오','ian':'엔 옌 이엔 앤 얜 이앤',
            'iang':'앙 양 이앙','ie':'에 예 이에','iong':'웅 용 융 이웅 이옹',
            'iou':'우 유 이우 이오우'}
# Optional colloquial spellings, after the phonological rules have run.
ALIASES={'xie':'셰 씨에 시에 쉐','xian':'셴 시엔 씨엔',
         'zhong':'중 종 쫑 쭝','guo':'궈 구어 고',
         'jing':'징 찡','qing':'칭','xing':'싱 씽',
         'jian':'젠 지엔 찌엔','qian':'첸 치엔','xue':'쉐 쉬에 슈에',
         'shi':'스 시 쓰','zhi':'즈 쯔 지','zi':'쯔 즈',
         'you':'요우 유','yong':'융 용','yuan':'위안 웬',
         'yu':'위 유','yan':'옌 얜','wo':'워','ri':'르 리',
         'sha':'샤','shai':'샤이','shan':'샨','shang':'샹','shao':'샤오',
         'she':'셔','shei':'셰이 쉐이','shen':'션','sheng':'셩',
         'shou':'쇼우','shu':'슈','shuo':'숴 슈어',
         'shui':'수이','chui':'추이','zhui':'주이',
         'm':'음','n':'은','ng':'응','hm':'흠'}


def classify(spelling):
    value=spelling.lower().replace('u:','v').replace('ü','v')
    rules=[]
    if value in ('m','n','ng','hm'):
        return Syllable(value,'',value,'zero','syllabic-consonant',('interjection',))
    if value in ZERO:
        initial='';final=ZERO[value];rules.append('zero-initial-y-w')
    else:
        initial=next((i for i in ('zh','ch','sh',*INITIALS) if value.startswith(i)), '')
        final=value[len(initial):]
    group=next((g for g,items in GROUPS.items() if initial in items),'zero')
    if value in APICAL:
        final='apical-retroflex' if group=='retroflex' else 'apical-alveolar'
        rules.append('syllabic-i')
    elif initial in ('j','q','x') and final.startswith('u'):
        final={'u':'v','ue':'ve','uan':'van','un':'vn'}.get(final,final)
        rules.append('umlaut-dots-omitted')
    elif initial in ('n','l') and final=='ue':
        # The bundled dictionary spells nüe/lüe as nue/lue.
        final='ve';rules.append('dictionary-umlaut-spelling')
    if final in ('iu','ui','un'):
        final={'iu':'iou','ui':'uei','un':'uen'}[final]
        rules.append('contracted-final')
    if final.startswith('apical'):
        family=final
    elif final.startswith('v'):
        family='rounded-front'
    elif final.endswith('ng'):
        family='nasal-ng'
    elif final.endswith('n'):
        family='nasal-n'
    elif final in ('er',):
        family='rhotic'
    elif final.startswith('i'):
        family='i-medial'
    elif final.startswith('u'):
        family='u-medial'
    else:
        family='simple-or-compound'
    return Syllable(value,initial,final,group,family,tuple(rules))


def korean_variants(spelling):
    syllable=classify(spelling)
    forms={}
    def add(text,penalty,kind):
        old=forms.get(text)
        if old is None or penalty<old.penalty:
            forms[text]=KoreanForm(text,penalty,kind)
    if syllable.spelling in APICAL:
        # Never generate an ordinary /i/ merely because the spelling ends i.
        for index,text in enumerate(APICAL[syllable.spelling].split()):
            add(text,index*.2,'syllabic-i')
    else:
        bases=FINALS.get(syllable.final,'').split()
        if syllable.initial in ('j','q'):
            bases=PALATAL_JQ.get(syllable.final,' '.join(bases)).split()
        for rank,base in enumerate(bases):
            if not syllable.initial:
                add(base,rank*.18,'phonetic')
            else:
                for consonant_rank,consonant in enumerate(INITIALS[syllable.initial]):
                    first=ord(base[0])-0xac00
                    text=chr(0xac00+consonant*588+first%588)+base[1:]
                    add(text,rank*.18+consonant_rank*.2,'phonetic' if not consonant_rank else 'korean-initial-variant')
    for rank,text in enumerate(ALIASES.get(syllable.spelling,'').split()):
        add(text,.12+rank*.12,'common-spelling')
    return tuple(sorted(forms.values(),key=lambda item:(item.penalty,item.text)))


def korean_forms(spelling):
    return tuple(form.text for form in korean_variants(spelling))
