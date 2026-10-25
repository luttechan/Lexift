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

    def test_long_vowels_are_local_and_not_duplicated_by_word_aliases(self):
        cases={'코-히-토코-차':'こーひーとこうちゃ','코-히-오노무':'こーひーおのむ',
               '아리가토-':'ありがとう','아리가토우':'ありがとう',
               '오하요-':'おはよう','오하요우':'おはよう',
               '도쿄우':'とうきょう','토쿄-':'とうきょう',
               '코-히-토오-키이':'こーひーとおうきい'}
        for source,row in zip(cases,self.convert(*cases)):
            with self.subTest(source=source):
                self.assertEqual(row['kana'],cases[source])
                self.assertIn(row['kana'],row['kana_variants'])
        row=self.convert('오-큐-')[0]
        self.assertEqual(row['kana_variants'][0],'おうきゅう')
        self.assertEqual(self.convert('오-키이')[0]['kana_variants'][0],'おおきい')

    def test_loan_sounds_and_korean_coda_liaison_keep_the_literal_option(self):
        cases={'파':'ふぁ','피':'ふぃ','푸':'ふ','페':'ふぇ','포':'ふぉ',
               '바':'ゔぁ','비':'ゔぃ','부':'ゔ','베':'ゔぇ','보':'ゔぉ',
               '자':'じゃ','주':'じゅ','조':'じょ','제':'じぇ',
               '듀':'でゅ','퓨':'ふゅ','뷰':'ゔゅ',
               '쉬':'し','쥐':'じ','바이올린':'ばいおりん'}
        for source,row in zip(cases,self.convert(*cases)):
            with self.subTest(source=source):
                self.assertIn(cases[source],row['kana_variants'])
                self.assertIn(row['kana'],row['kana_variants'])
                self.assertLessEqual(len(row['kana_variants']),16)
        self.assertEqual(self.convert('듀')[0]['kana'],'でゅ')
        self.assertIn('じゅ',self.convert('듀')[0]['kana_variants'])

    def test_consistent_ambiguity_families_survive_long_input_pruning(self):
        cases={'가가가가가가':'かかかかかか',
               '파피푸페포':'ふぁふぃふふぇふぉ',
               '바비부베보':'ゔぁゔぃゔゔぇゔぉ',
               '자주제조자주제조':'じゃじゅじぇじょじゃじゅじぇじょ',
               '알라알라알라알라':'あらあらあらあら'}
        for source,row in zip(cases,self.convert(*cases)):
            with self.subTest(source=source):
                self.assertIn(cases[source],row['kana_variants'])
                self.assertLessEqual(len(row['kana_variants']),16)
                self.assertEqual(len(row['kana_variants']),len(set(row['kana_variants'])))

    def test_korean_transcription_table_and_modern_loan_sound_inventory(self):
        # Standard Korean spellings merge word-initial k/g, t/d, ch/j and
        # s/ts. Check the intended reading remains reachable for every row.
        rows=(('아 이 우 에 오','あいうえお'),('가 기 구 게 고','かきくけこ'),
              ('사 시 쓰 세 소','さしすせそ'),('다 지 쓰 데 도','たちつてと'),
              ('나 니 누 네 노','なにぬねの'),('하 히 후 헤 호','はひふへほ'),
              ('마 미 무 메 모','まみむめも'),('라 리 루 레 로','らりるれろ'),
              ('가 기 구 게 고','がぎぐげご'),('자 지 즈 제 조','ざじずぜぞ'),
              ('다 지 즈 데 도','だぢづでど'),('바 비 부 베 보','ばびぶべぼ'),
              ('파 피 푸 페 포','ぱぴぷぺぽ'))
        cases=[(source,kana) for sources,kanas in rows for source,kana in zip(sources.split(),kanas)]
        for sources,stem in (('갸 규 교','き'),('갸 규 교','ぎ'),('샤 슈 쇼','し'),
                             ('자 주 조','じ'),('냐 뉴 뇨','に'),('자 주 조','ち'),
                             ('햐 휴 효','ひ'),('뱌 뷰 뵤','び'),('퍄 퓨 표','ぴ'),
                             ('먀 뮤 묘','み'),('랴 류 료','り')):
            cases.extend((source,stem+small) for source,small in zip(sources.split(),'ゃゅょ'))
        cases.extend([('위','うぃ'),('웨','うぇ'),('워','うぉ'),('티','てぃ'),('디','でぃ'),
                      ('투','とぅ'),('두','どぅ'),('튜','てゅ'),('듀','でゅ'),
                      ('셰','しぇ'),('제','じぇ'),('체','ちぇ'),('퓨','ふゅ'),('뷰','ゔゅ'),
                      ('쓰나미','つなみ'),('마쓰모토','まつもと'),('지바','ちば'),
                      ('보쿠와','ぼくは'),('보쿠 와','ぼくは'),('와','は'),('에','へ'),('오','を')])
        for (source,expected),row in zip(cases,self.convert(*(case[0] for case in cases))):
            with self.subTest(source=source,expected=expected):
                self.assertIn(expected,row['kana_variants'])
                self.assertIn(row['kana'],row['kana_variants'])

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

    def test_object_particle_paths_survive_long_sentences_and_unknown_noun_phrases(self):
        cases={
            '와타시와키노-토쇼칸데카리타아타라시이혼오토모다치니와타시마시타':
                'わたしはきのうとしょかんでかりたあたらしいほんをともだちにわたしました',
            '와타시와오오사카데카리타아오이혼오요미나가라온가쿠오키키마스':
                'わたしはおおさかでかりたあおいほんをよみながらおんがくをききます',
            '아오이카미오오오키나하코니이레마스':'あおいかみをおおきなはこにいれます',
            '오모이데오오모이다시마스':'おもいでをおもいだします',
            '호-코쿠쇼오테-슈츠시마스':'ほうこくしょをていしゅつします',
            '와타시 와 아타라시이 혼 오 토모다치 니 와타시마스':
                'わたしはあたらしいほんをともだちにわたします',
            '혼오니혼니오쿠리마스':'ほんをにほんにおくります',
            '혼오카시마스':'ほんをかします',
            '혼오욘다히토오미마시타':'ほんをよんだひとをみました',
        }
        for source,row in zip(cases,self.convert(*cases)):
            with self.subTest(source=source):
                self.assertIn(cases[source],row['kana_variants'])
                self.assertIn(row['kana'],row['kana_variants'])
                self.assertLessEqual(len(row['kana_variants']),16)
                self.assertEqual(len(row['kana_variants']),len(set(row['kana_variants'])))

    def test_object_inference_keeps_word_internal_o_and_explicit_japanese(self):
        for source,expected in (('아오이','あおい'),('오모이데','おもいで'),
                                ('카오리가시마스','かおりがします'),('오노미치','おのみち'),
                                ('오요미쿠다사이','およみください'),('아오이카미','あおいかみ')):
            row=self.convert(source)[0]
            with self.subTest(source=source):
                self.assertEqual(row['kana_variants'][0],expected)
        for source in ('ほんおよみます','あおいかみおおおきなはこにいれます'):
            row=self.convert(source)[0]
            self.assertEqual(row['kana_variants'][0],source)
        violin=self.convert('바이올린')[0]['kana_variants']
        wrong='ばいをるりん'
        if wrong in violin:self.assertLess(violin.index('ばいおりん'),violin.index(wrong))
        # Stress a long object ending after many distracting ordinary お.
        source='아오이카오리노오오키나오모이데노오미야게오요미마스'
        row=self.convert(source)[0]
        self.assertIn('あおいかおりのおおきなおもいでのおみやげをよみます',row['kana_variants'])
