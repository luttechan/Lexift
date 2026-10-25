import tempfile,unittest
from pathlib import Path
from chinese_reading import ChineseEngine
from pinyin_phonetics import korean_forms

class CompactDictionaryTests(unittest.TestCase):
    def test_index_preserves_ranked_results_for_dictionary_words_and_ambiguous_phrases(self):
        path=Path(__file__).parents[1]/'chinese_data/pinyin_simp.dict.yaml'
        old=ChineseEngine(path);new=ChineseEngine()
        samples={'니하오','췐','워아이니','진티엔','시아'*24,'중궈','터우파','황허우'}
        for tokens in list(old.words)[::397]:
            samples.add(''.join(korean_forms(s)[0] for s in tokens))
        try:
            for text in samples:
                with self.subTest(source=text):self.assertEqual(new.query(text),old.query(text))
            self.assertLessEqual(len(new.words.cache),256)
            self.assertLessEqual(len(new.word_prefixes.cache),2048)
        finally:new.close()

    def test_stale_index_falls_back_to_updated_text_dictionary(self):
        from unittest.mock import patch
        with patch('compact_dictionary.CompactDictionary',side_effect=ValueError('stale')):
            engine=ChineseEngine()
            self.assertEqual(engine.query('니하오')['candidates'][0],'你好')
