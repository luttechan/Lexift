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

    def readings(self, source):
        text = unicodedata.normalize('NFC', source)
        if not text or len(text)>64 or any(not ('가'<=c<='힣') for c in text):
            return []
        # Bounded lattice: preserve syllable boundaries and pronunciation
        # alternatives without an exponential Cartesian-product expansion.
        paths = [[] for _ in range(len(text)+1)]
        paths[0] = [(0.0, ())]
        for pos in range(len(text)):
            paths[pos] = sorted(set(paths[pos]))[:32]
            for size in range(1, min(self.max_form, len(text)-pos)+1):
                for syllable, penalty in self.forms.get(text[pos:pos+size], ()):
                    for cost, tokens in paths[pos]:
                        paths[pos+size].append((cost+penalty+.06, tokens+(syllable,)))
                if len(paths[pos+size])>256:
                    paths[pos+size]=sorted(set(paths[pos+size]))[:64]
        return sorted(set(paths[-1]))[:32]

    def query(self, source):
        ranked = []
        single_syllable_best = set()
        readings = self.readings(source)
        for cost, tokens in readings:
            # Whole words get priority. Otherwise compose dictionary words in
            # a bounded beam; arbitrary sentences need no phrase hard-coding.
            rows = self.words.get(tokens, ())[:20]
            if len(tokens)==1 and rows:
                single_syllable_best.add(rows[0][0])
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
        for score, text, tokens in ranked:
            unique.setdefault(text, ' '.join(tokens))
        # Homophonous b/p/f etc. can otherwise fill all 20 slots with frequent
        # characters from one reading. Reserve its best character for each
        # recognized whole-input syllable, retaining frequency order and the
        # shared-character deduplication (e.g. 谁 for shei/shui).
        required=set([text for text in unique if text in single_syllable_best][:20])
        remaining=20-len(required)
        selected={}
        for text,reading in unique.items():
            if text in required:
                selected[text]=reading
            elif remaining:
                selected[text]=reading;remaining-=1
        return {'source':source, 'kana':next(iter(selected.values()), ''),
                'candidates':list(selected), 'readings':list(selected.values()), 'language':'zh',
                'backend':'offline-pinyin'}
