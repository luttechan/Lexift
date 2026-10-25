"""Output profiles share one phonetic dictionary; no invented tone information."""
from pinyin_phonetics import classify

TRADITIONAL='zh_tw'
BOPOMOFO='zh_bopomofo'
CHINESE_MODES=('zh',TRADITIONAL,BOPOMOFO)
INITIALS=dict(zip(('b','p','m','f','d','t','n','l','g','k','h','j','q','x','zh','ch','sh','r','z','c','s'),
                 'ㄅㄆㄇㄈㄉㄊㄋㄌㄍㄎㄏㄐㄑㄒㄓㄔㄕㄖㄗㄘㄙ'))
FINALS={'a':'ㄚ','o':'ㄛ','e':'ㄜ','ai':'ㄞ','ei':'ㄟ','ao':'ㄠ','ou':'ㄡ',
        'an':'ㄢ','en':'ㄣ','ang':'ㄤ','eng':'ㄥ','er':'ㄦ',
        'i':'ㄧ','ia':'ㄧㄚ','io':'ㄧㄛ','ie':'ㄧㄝ','iao':'ㄧㄠ','iou':'ㄧㄡ',
        'ian':'ㄧㄢ','in':'ㄧㄣ','iang':'ㄧㄤ','ing':'ㄧㄥ','iong':'ㄩㄥ',
        'u':'ㄨ','ua':'ㄨㄚ','uo':'ㄨㄛ','uai':'ㄨㄞ','uei':'ㄨㄟ',
        'uan':'ㄨㄢ','uen':'ㄨㄣ','uang':'ㄨㄤ','ueng':'ㄨㄥ','ong':'ㄨㄥ',
        'v':'ㄩ','ve':'ㄩㄝ','van':'ㄩㄢ','vn':'ㄩㄣ',
        'apical-retroflex':'','apical-alveolar':'',
        'm':'ㄇ','n':'ㄋ','ng':'ㄫ','hm':'ㄏㄇ'}

def zhuyin_syllable(spelling):
    syllable=classify(spelling)
    if syllable.final not in FINALS:raise ValueError('Unsupported Mandarin syllable: '+spelling)
    return INITIALS.get(syllable.initial,'')+FINALS[syllable.final]

def zhuyin_reading(reading):
    return ' '.join(zhuyin_syllable(token) for token in reading.split())

class OutputProfiles:
    def __init__(self):self.converter=None
    def transform(self,data,mode='zh'):
        if mode not in CHINESE_MODES:raise ValueError('Unsupported Chinese output mode')
        if mode=='zh':return data
        if mode==TRADITIONAL:
            if self.converter is None:
                from opencc import OpenCC
                # Orthography only: s2twp would change words AND their readings.
                self.converter=OpenCC('s2tw')
            values=[];readings=[];alternatives={}
            for index,text in enumerate(data.get('candidates',[])):
                converted=self.converter.convert(text)
                reading=data['readings'][index]
                if converted not in alternatives:values.append(converted);readings.append(reading);alternatives[converted]=[]
                for form in data.get('reading_alternatives',{}).get(text,[reading]):
                    if form not in alternatives[converted]:alternatives[converted].append(form)
            return dict(data,candidates=values,readings=readings,reading_alternatives=alternatives,
                        language=mode,backend='offline-pinyin-opencc-s2tw',output_mode=mode)
        # The input has no tones. Preserve all distinct dictionary readings,
        # rather than guessing a tone or choosing a polyphonic character's sound.
        values=[];readings=[];alternatives={}
        for index,text in enumerate(data.get('candidates',[])):
            reading=data['readings'][index]
            for form in data.get('reading_alternatives',{}).get(text,[reading]):
                converted=zhuyin_reading(form)
                if converted not in alternatives:values.append(converted);readings.append(form);alternatives[converted]=[]
                if form not in alternatives[converted]:alternatives[converted].append(form)
                if len(values)>=20:break
            if len(values)>=20:break
        return dict(data,candidates=values,readings=readings,reading_alternatives=alternatives,
                    language=mode,backend='offline-pinyin-bopomofo',output_mode=mode,tones=False)
