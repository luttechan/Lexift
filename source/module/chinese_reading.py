"""Offline Korean pronunciation -> ambiguous Mandarin readings -> Chinese.

The dictionary is separate, replaceable Apache-2.0 Rime pinyin_simp data.
This is phonetic input, not Korean-to-Chinese semantic translation.
"""
from collections import defaultdict
from pathlib import Path
import math
import unicodedata

from pinyin_phonetics import korean_forms, korean_variants, classify


class ChineseEngine:
    def __init__(self, dictionary=None):
        self.words = defaultdict(list)
        syllables = set()
        path = dictionary or Path(__file__).with_name('chinese_data')/'pinyin_simp.dict.yaml'
        for line in Path(path).read_text(encoding='utf-8').splitlines():
            parts = line.split('\t')
            if len(parts) < 3:
                continue
            text, reading, weight = parts[:3]
            tokens = tuple(reading.split())
            if not tokens or any(not t.isascii() or not t.isalpha() for t in tokens):
                continue
            try:
                score = int(weight)
            except ValueError:
                continue
            self.words[tokens].append((text, score))
            syllables.update(tokens)
        for rows in self.words.values():
            rows.sort(key=lambda row: -row[1])
        self.forms = defaultdict(list)
        for syllable in sorted(syllables):
            for form in korean_variants(syllable):
                self.forms[form.text].append((syllable, form.penalty))
        self.max_form = max(map(len, self.forms))
        self.word_lengths = sorted({len(k) for k in self.words}, reverse=True)
        self.syllables = tuple(sorted(syllables))
        # A phonetic beam alone can discard a real dictionary word before
        # frequency ranking sees it. Share short reading prefixes rather than
        # expanding every Korean alias combination for all dictionary words.
        self.word_prefixes = {tokens[:size] for tokens in self.words
                              for size in range(1,len(tokens)+1)}
        self.max_word_chars = max(self.word_lengths)*self.max_form

    def _dictionary_readings(self, text):
        if len(text)>self.max_word_chars:
            return []
        paths=[{} for _ in range(len(text)+1)]
        paths[0][()]=0.0
        for pos in range(len(text)):
            # Dictionary prefixes constrain branching; retain an explicit
            # work limit for unusual replacement dictionaries as well.
            active=sorted(paths[pos].items(),key=lambda item:item[1])[:4096]
            for size in range(1,min(self.max_form,len(text)-pos)+1):
                forms=self.forms.get(text[pos:pos+size],())
                for tokens,cost in active:
                    for syllable,penalty in forms:
                        prefix=tokens+(syllable,)
                        if prefix not in self.word_prefixes:
                            continue
                        score=cost+penalty+.06
                        old=paths[pos+size].get(prefix)
                        if old is None or score<old:
                            paths[pos+size][prefix]=score
        found=[(cost,tokens) for tokens,cost in paths[-1].items() if tokens in self.words]
        found.sort(key=lambda row:row[0]-math.log1p(self.words[row[1]][0][1]))
        return found[:96]

    def readings(self, source):
        text = unicodedata.normalize('NFC', source)
        if not text or len(text)>64 or any(not ('가'<=c<='힣') for c in text):
            return []
        # Bounded lattice: preserve syllable boundaries and pronunciation
        # alternatives without an exponential Cartesian-product expansion.
        paths = [[] for _ in range(len(text)+1)]
        paths[0] = [(0.0, ())]
        truncated=False
        for pos in range(len(text)):
            if len(set(paths[pos]))>32:
                truncated=True
            paths[pos] = sorted(set(paths[pos]))[:32]
            for size in range(1, min(self.max_form, len(text)-pos)+1):
                for syllable, penalty in self.forms.get(text[pos:pos+size], ()):
                    for cost, tokens in paths[pos]:
                        paths[pos+size].append((cost+penalty+.06, tokens+(syllable,)))
                if len(paths[pos+size])>256:
                    truncated=True
                    paths[pos+size]=sorted(set(paths[pos+size]))[:64]
        truncated=truncated or len(set(paths[-1]))>32
        result=sorted(set(paths[-1]))[:32]
        if truncated:
            # Preserve the ordinary sentence beam and recover complete real
            # words independently. At most 32+96 paths reach candidate ranking.
            cheapest={tokens:cost for cost,tokens in result}
            for cost,tokens in self._dictionary_readings(text):
                cheapest[tokens]=min(cost,cheapest.get(tokens,cost))
            result=sorted((cost,tokens) for tokens,cost in cheapest.items())
        return result

    def query(self, source):
        ranked = []
        reading_best = set()
        readings = self.readings(source)
        for cost, tokens in readings:
            # Whole words get priority. Otherwise compose dictionary words in
            # a bounded beam; arbitrary sentences need no phrase hard-coding.
            rows = self.words.get(tokens, ())[:20]
            if rows:
                reading_best.add(rows[0][0])
            for text, weight in rows:
                ranked.append((100+math.log1p(weight)-cost, text, tokens))
            paths = [[] for _ in range(len(tokens)+1)]
            paths[0] = [(0.0, '')]
            for pos in range(len(tokens)):
                paths[pos] = sorted(paths[pos], reverse=True)[:8]
                for size in self.word_lengths:
                    if pos+size>len(tokens):
                        continue
                    rows=self.words.get(tokens[pos:pos+size], ())[:5]
                    for text, weight in rows:
                        for score, prefix in paths[pos]:
                            paths[pos+size].append((score+math.log1p(weight)*.15-3, prefix+text))
                    if len(paths[pos+size])>128:
                        paths[pos+size]=sorted(paths[pos+size], reverse=True)[:16]
            ranked.extend((score-cost, text, tokens) for score,text in paths[-1])
        ranked.sort(key=lambda row:-row[0])
        unique = {}
        reading_alternatives=defaultdict(list)
        for score, text, tokens in ranked:
            spelling=' '.join(tokens)
            unique.setdefault(text,spelling)
            if spelling not in reading_alternatives[text] and len(reading_alternatives[text])<8:
                reading_alternatives[text].append(spelling)
        # Homophonous b/p/f etc. can otherwise fill all 20 slots with frequent
        # characters from one reading. Reserve its best character for each
        # recognized complete dictionary reading, retaining frequency order and the
        # shared-character deduplication (e.g. 谁 for shei/shui).
        required=set([text for text in unique if text in reading_best][:20])
        remaining=20-len(required)
        selected={}
        for text,reading in unique.items():
            if text in required:
                selected[text]=reading
            elif remaining:
                selected[text]=reading;remaining-=1
        return {'source':source, 'kana':next(iter(selected.values()), ''),
                'candidates':list(selected), 'readings':list(selected.values()), 'language':'zh',
                'reading_alternatives':{text:reading_alternatives[text] for text in selected},
                'backend':'offline-pinyin'}
