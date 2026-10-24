"""Pronunciation expectations and actual compiled normalizer, not canned IME data."""
import json
from pathlib import Path
import subprocess
import unittest
import unicodedata

HOST = Path(__file__).resolve().parents[2] / 'lab' / 'ime_candidate_host.exe'


@unittest.skipUnless(HOST.is_file(), 'Build the native IME host first')
class HangulReadingTests(unittest.TestCase):
    def convert(self, *inputs):
        completed = subprocess.run([str(HOST), '--normalize', *inputs], capture_output=True,
                                   encoding='utf-8', check=True, timeout=10)
        return [json.loads(line) for line in completed.stdout.splitlines()]

    def test_words_and_sentence_outside_spelling_dictionary(self):
        cases = {'와타시':'わたし', '니혼고':'にほんご', '센세이':'せんせい', '스시':'すし',
                 '가쿠세이':'がくせい', '와타시와가쿠세이데스':'わたしわがくせいです',
                 '간바레':'がんばれ', '감바레':'がんばれ', '하시':'はし', '키모치':'きもち'}
        results = self.convert(*cases)
        for (source, kana), result in zip(cases.items(), results):
            with self.subTest(source=source):
                self.assertEqual(result['error'], '')
                self.assertEqual(result['kana'], kana)

    def test_small_tsu_palatal_sounds_and_explicit_long_vowels(self):
        cases = {'갓코우':'がっこう','킷테':'きって','쿄우':'きょう','료코우':'りょこう',
                 '샤신':'しゃしん','쥬우':'じゅう','츄우':'ちゅう','츠키':'つき',
                 '코-히-':'こーひー','코오히이':'こおひい','슈쿠다이':'しゅくだい'}
        for source, result in zip(cases, self.convert(*cases)):
            with self.subTest(source=source):
                self.assertEqual(result['error'], '')
                self.assertEqual(result['kana'], cases[source])

    def test_pronunciation_dictionary_does_not_double_explicit_long_vowel(self):
        cases = {'아리가토':'ありがとう','아리가토우':'ありがとう',
                 '아리가또우':'ありがとう','아리가토 고자이마스':'ありがとうございます',
                 '곤니치와':'こんにちは','콘니치와':'こんにちは','도쿄':'とうきょう',
                 '오하요':'おはよう','오하요우':'おはよう'}
        for source, result in zip(cases, self.convert(*cases)):
            with self.subTest(source=source):
                self.assertEqual(result['kana'], cases[source])

    def test_decomposed_hangul_is_equivalent_to_composed(self):
        words = ['와타시', '니혼고', '갓코우', '센세이']
        results = self.convert(*words, *(unicodedata.normalize('NFD', s) for s in words))
        for first, second in zip(results[:4], results[4:]):
            self.assertEqual(first['kana'], second['kana'])
            self.assertEqual(first['romaji'], second['romaji'])

    def test_korean_dash_expands_long_vowels_without_changing_manual_kana(self):
        cases={'코-죠-':'こうじょう','도-쿄-':'とうきょう','토-쿄-':'とうきょう',
               '센세-':'せんせい','수-가쿠':'すうがく','오바-상':'おばあさん',
               '코-히-':'こーひー','こーじょー':'こーじょー'}
        for source,row in zip(cases,self.convert(*cases)):
            with self.subTest(source=source):self.assertEqual(row['kana'],cases[source])
        self.assertIn('こーじょー',self.convert('코-죠-')[0]['kana_variants'])

    def test_ji_zu_spelling_variants_keep_context_and_are_bounded(self):
        words=['모노즈쿠리','츠즈쿠','하나지','즈','지','ずじずじずじ','モノヅクリ']
        rows=self.convert(*words)
        for row,expected in zip(rows,['ものづくり','つづく','はなぢ','ず','じ','ずじずじずじ','ものづくり']):
            self.assertEqual(row['kana'],expected)
            self.assertEqual(row['kana_variants'][0],expected)
            self.assertLessEqual(len(row['kana_variants']),16)
        self.assertIn('ものずくり',rows[0]['kana_variants'])
        self.assertIn('づ',rows[3]['kana_variants'])
        self.assertIn('ぢ',rows[4]['kana_variants'])

    def test_bad_input_is_rejected_instead_of_silently_dropped(self):
        inputs = ['', ' ', 'ㅇ', 'ㄱㅏ', '私', 'watashi', '와타시🙂', '와타시1', '가'*257]
        for source, result in zip(inputs, self.convert(*inputs)):
            with self.subTest(source=source):
                self.assertTrue(result['error'])

    def test_orthographic_stems_cover_inflections_and_keep_literal_reading(self):
        cases={'치지마리마스':'ちぢまります','치지마리마시타':'ちぢまりました',
               '치지마라나이':'ちぢまらない','치지맛타':'ちぢまった',
               '치지메마스':'ちぢめます','오-키이':'おおきい','오네-상':'おねえさん'}
        for source,row in zip(cases,self.convert(*cases)):
            with self.subTest(source=source):
                self.assertEqual(row['kana_variants'][0],cases[source])
                self.assertIn(row['kana'],row['kana_variants'])

    def test_particle_boundaries_and_conventional_korean_spellings(self):
        cases={'쯔키':'つき','와타시와가쿠세이데스':'わたしはがくせいです',
               '와타시 와 가쿠세이데스':'わたしはがくせいです',
               '도쿄 에 이키마스':'とうきょうへいきます',
               '혼 오 요미마스':'ほんをよみます'}
        for source,row in zip(cases,self.convert(*cases)):
            with self.subTest(source=source):self.assertIn(cases[source],row['kana_variants'])

    def test_long_vowel_alternatives_are_vowel_specific_and_bounded(self):
        rows=self.convert('키-','수-','지지지지지지지지','코-죠-','지 와 '*8+'코-죠-')
        self.assertNotIn('きえ',rows[0]['kana_variants'])
        self.assertNotIn('すお',rows[1]['kana_variants'])
        for row in rows:
            self.assertEqual(len(row['kana_variants']),len(set(row['kana_variants'])))
            self.assertLessEqual(len(row['kana_variants']),16)
        self.assertIn('こうぢょう',rows[3]['kana_variants'])
        self.assertIn(rows[4]['kana'],rows[4]['kana_variants'])
        self.assertIn(rows[4]['kana'].replace('こうじょう','こーじょー'),rows[4]['kana_variants'])

    def test_manual_kana_correction_and_katakana(self):
        inputs = ['わたしはがくせいです','ワタシ','がっこう','きょう','にほんご']
        results = self.convert(*inputs)
        self.assertEqual(results[0]['kana'], inputs[0])
        self.assertEqual(results[1]['kana'], 'わたし')
        self.assertEqual(results[2]['romaji'], 'gaxtsukou')
        self.assertEqual(results[3]['romaji'], 'kixyou')
        self.assertEqual(results[4]['romaji'], "nihon'go")

    def test_all_modern_hangul_syllables_produce_bounded_supported_ime_keys(self):
        # Batch under Windows' command-line limit. Exercise all 11,172 syllables.
        allowed = set("abcdefghijklmnopqrstuvwxyz'-,.")
        for offset in range(0xac00, 0xd7a4, 400):
            words = [chr(c) for c in range(offset, min(offset+400, 0xd7a4))]
            for result in self.convert(*words):
                self.assertFalse(result['error'], result)
                self.assertTrue(result['romaji'])
                self.assertLessEqual(len(result['romaji']), 16)
                self.assertLessEqual(set(result['romaji']), allowed)
