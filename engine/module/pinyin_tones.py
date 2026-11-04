"""Apply a chosen tone to the last complete, explicitly separated pinyin syllable."""
import unicodedata

TONES={'a':'āáǎà','e':'ēéěè','i':'īíǐì','o':'ōóǒò','u':'ūúǔù','ü':'ǖǘǚǜ'}
MARKS=set('\u0304\u0301\u030c\u0300')

def plain(text):
    return unicodedata.normalize('NFC',''.join(c for c in unicodedata.normalize('NFD',text) if c not in MARKS))

def apply_tone(text,tone):
    if tone not in range(5):raise ValueError('Tone must be 0 through 4')
    # Space, apostrophe and hyphen are unambiguous syllable boundaries. For
    # joined spelling, use the last vowel group (nihao -> hao, zhongguo -> guo).
    # A vowel group ending in -ng/-n belongs to that syllable, not the next one.
    import re
    match=re.search(r"[A-Za-z\u00c0-\u024f\u1e00-\u1eff\u0300-\u036f:]+$",text)
    if not match:return text
    word=plain(match.group()).replace('u:','ü').replace('U:','Ü').replace('v','ü').replace('V','Ü')
    if word.lower() in ('m','n','ng','hm'):
        at=1 if word.lower()=='hm' else 0
        mark=('', '\u0304','\u0301','\u030c','\u0300')[tone]
        return text[:match.start()]+unicodedata.normalize('NFC',word[:at+1]+mark+word[at+1:])
    groups=list(re.finditer('[aeiouüAEIOUÜ]+',word))
    if not groups:return text
    # iu/ui are contracted finals; iao/uai/ian etc. retain a single vowel group.
    group=groups[-1];start=group.start();syllable=word[start:]
    lowered=syllable.lower()
    if 'a' in lowered:at=lowered.index('a')
    elif 'e' in lowered:at=lowered.index('e')
    elif 'ou' in lowered:at=lowered.index('ou')
    else:at=max(i for i,c in enumerate(lowered) if c in TONES)
    if tone:
        old=syllable[at];marked=TONES[old.lower()][tone-1]
        if old.isupper():marked=marked.upper()
        syllable=syllable[:at]+marked+syllable[at+1:]
    # Only remove the preceding tone within the target vowel group. Earlier
    # syllables retain their marks when the user types a joined word.
    original=unicodedata.normalize('NFC',match.group());original_plain=plain(original)
    if len(original_plain.replace('u:','ü').replace('U:','Ü'))==len(word):
        prefix=original[:start]
    else:prefix=word[:start]
    return text[:match.start()]+prefix+syllable
