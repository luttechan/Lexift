import ctypes
from ctypes import wintypes
import itertools
import tempfile
import time
from pathlib import Path
import unittest
from unittest.mock import Mock, patch
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication
from chinese_reading import ChineseEngine
from pinyin_phonetics import classify, korean_forms, korean_variants
from hotkeys_windows import HotkeyBinding, HotkeyGroup
from native_hooks import library
from tests.test_native_hooks import CapsState
import app


class ChineseReadingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine=ChineseEngine()

    def test_common_words_and_composed_phrases(self):
        examples={'니하오':'你好','셰셰':'谢谢','씨에씨에':'谢谢','워아이니':'我爱你',
                  '중궈':'中国','종궈':'中国','베이징':'北京','짜이젠':'再见',
                  '니하오마':'你好吗','메이관시':'没关系','진티엔':'今天','펑요우':'朋友'}
        for source,expected in examples.items():
            with self.subTest(source=source):
                result=self.engine.query(source)
                self.assertEqual(result['candidates'][0],expected)
                self.assertEqual(len(result['candidates']),len(result['readings']))
                self.assertEqual(len(result['candidates']),len(set(result['candidates'])))

    def test_ambiguity_keeps_multiple_hanzi(self):
        result=self.engine.query('스')
        self.assertIn('是',result['candidates'])
        self.assertGreater(len(result['candidates']),1)

    def test_invalid_and_unfinished_inputs_are_rejected(self):
        for source in ('','ㄴ','니ㅎ','nihao','你好','니 하오','니하오!','아'*65):
            with self.subTest(source=source):
                self.assertEqual(self.engine.query(source)['candidates'],[])

    def test_nfd_normalization(self):
        import unicodedata
        self.assertEqual(self.engine.query(unicodedata.normalize('NFD','니하오'))['candidates'][0],'你好')

    def test_long_ambiguous_input_is_bounded(self):
        start=time.monotonic()
        result=self.engine.query('시아'*24)
        self.assertLess(time.monotonic()-start,3)
        self.assertLessEqual(len(result['candidates']),20)

    def test_all_dictionary_syllables_have_phonetic_forms(self):
        for spelling in self.engine.syllables:
            with self.subTest(spelling=spelling):
                self.assertTrue(korean_forms(spelling))

    def test_every_generated_alias_reaches_its_dictionary_syllable(self):
        # A nonempty alias list alone misses aliases discarded by beam pruning
        # or a broken inverse index. Exercise the production reading lattice.
        for spelling in self.engine.syllables:
            for form in korean_forms(spelling):
                with self.subTest(spelling=spelling,form=form):
                    self.assertIn((spelling,),[tokens for _,tokens in self.engine.readings(form)])

    def test_each_dictionary_syllable_keeps_a_character_in_the_candidate_limit(self):
        for spelling in self.engine.syllables:
            characters={text for text,_ in self.engine.words.get((spelling,),())}
            if not characters:
                continue
            for form in korean_forms(spelling):
                with self.subTest(spelling=spelling,form=form):
                    answer=self.engine.query(form)
                    self.assertTrue(characters.intersection(answer['candidates']))
                    self.assertLessEqual(len(answer['candidates']),20)
                    self.assertEqual(len(answer['candidates']),len(set(answer['candidates'])))

    def test_front_rounded_finals_accept_compact_and_explicit_spellings(self):
        examples={'juan':('줸','쥐엔','쥐앤','쥐안','쥬엔'),
                  'quan':('췐','쵄','취엔','취앤','취안','츄엔'),
                  'xuan':('쉔','쇈','쉬엔','쉬앤','쉬안','슈엔'),
                  'yuan':('웬','왠','위엔','위앤','위안','유엔'),
                  'jue':('줴','쥐에','쥬에'),'que':('췌','취에','츄에'),
                  'xue':('쉐','쉬에','슈에'),'yue':('웨','위에','유에'),
                  'jun':('쥔','쥰'),'qun':('췬','츈'),
                  'xun':('쉰','슌'),'yun':('윈','윤')}
        for spelling,forms in examples.items():
            for form in forms:
                with self.subTest(spelling=spelling,form=form):
                    self.assertIn((spelling,),[tokens for _,tokens in self.engine.readings(form)])

    def test_other_medial_aliases_keep_contracted_and_expanded_forms(self):
        examples={'xiong':('슝','숑','시웅','시옹'),
                  'qiong':('충','춍','치웅','치옹'),
                  'jiong':('중','죵','지웅','지옹'),
                  'yong':('융','용','이웅','이옹'),
                  'qian':('첸','챈','치엔','치앤'),
                  'lian':('롄','리엔','리앤'),
                  'wen':('원','웬','우언','우엔')}
        for spelling,forms in examples.items():
            for form in forms:
                with self.subTest(spelling=spelling,form=form):
                    self.assertIn((spelling,),[tokens for _,tokens in self.engine.readings(form)])

    def test_new_pronunciations_produce_real_dictionary_candidates(self):
        examples={'췐':'全','췐부':'全部','취엔부':'全部','안췐':'安全',
                  '웬췐':'温泉','쉔저':'选择','쉬엔저':'选择','줸콴':'捐款',
                  '위엔':'元','숑마오':'熊猫','시옹마오':'熊猫','슈에셩':'学生'}
        for source,expected in examples.items():
            with self.subTest(source=source):
                answer=self.engine.query(source)
                self.assertIn(expected,answer['candidates'])
                self.assertLessEqual(len(answer['candidates']),20)
                self.assertEqual(len(answer['candidates']),len(answer['readings']))

    def test_aliases_preserve_nasal_and_rounded_vowel_distinctions(self):
        for source,spelling,excluded in (('췐','quan','qun'),('췬','qun','quan'),
                                         ('쉔','xuan','xun'),('숑','xiong','xian'),
                                         ('쥐','ju','zhu'),('주','zhu','ju')):
            readings={tokens for _,tokens in self.engine.readings(source)}
            with self.subTest(source=source):
                self.assertIn((spelling,),readings)
                self.assertNotIn((excluded,),readings)

    def test_umlaut_and_back_u_stay_separate(self):
        for spelling in ('ju','qu','xu','yu'):
            self.assertEqual(classify(spelling).final,'v')
        self.assertEqual(classify('zhu').final,'u')
        self.assertIn('쥐',korean_forms('ju'))
        self.assertNotIn('주',korean_forms('ju'))
        self.assertIn('주',korean_forms('zhu'))
        self.assertEqual(classify('nue').final,'ve')
        self.assertEqual(classify('lüe').final,'ve')

    def test_apical_i_is_not_ordinary_i(self):
        self.assertEqual(classify('zhi').final_group,'apical-retroflex')
        self.assertEqual(classify('zi').final_group,'apical-alveolar')
        self.assertEqual(classify('ji').final,'i')
        self.assertIn('즈',korean_forms('zhi'))
        self.assertIn('쓰',korean_forms('si'))
        forms={form.text:form for form in korean_variants('si')}
        self.assertEqual(forms['시'].kind,'approximate-syllabic-i')
        self.assertGreater(forms['시'].penalty,forms['쓰'].penalty)

    def test_apical_input_conveniences_preserve_all_ambiguous_readings(self):
        examples={'치':('qi','chi','ci'),'지':('ji','zhi','zi'),
                  '시':('xi','shi','si'),'츠':('chi','ci')}
        for source,spellings in examples.items():
            with self.subTest(source=source):
                readings={tokens for _,tokens in self.engine.readings(source)}
                answer=self.engine.query(source)
                for spelling in spellings:
                    self.assertIn((spelling,),readings)
                    # Test displayed candidates, not just an internal alias.
                    self.assertIn(spelling,answer['readings'])
        self.assertNotIn('치',korean_forms('che'))
        self.assertNotIn('시',korean_forms('shu'))
        self.assertNotIn('지',korean_forms('ju'))

    def test_chi_and_qi_are_both_usable_in_words(self):
        for source,expected,reading in (
                ('치판','吃饭','chi fan'),('츠판','吃饭','chi fan'),
                ('치둥시','吃东西','chi dong xi'),('츠둥시','吃东西','chi dong xi'),
                ('치처','汽车','qi che'),('츠위','词语','ci yu'),
                ('치위','词语','ci yu'),('시거','四个','si ge')):
            with self.subTest(source=source):
                answer=self.engine.query(source)
                self.assertIn(expected,answer['candidates'])
                self.assertEqual(answer['readings'][answer['candidates'].index(expected)],reading)

    def test_dictionary_words_recover_readings_dropped_by_phonetic_beam(self):
        for source,reading,expected in (
                ('파오파오',('bao','bao'),'宝宝'),
                ('피아오파이',('biao','bai'),'表白'),
                ('타이피아오',('dai','biao'),'代表'),
                ('쿠앙피아오',('guang','biao'),'光标')):
            with self.subTest(source=source):
                paths=self.engine.readings(source)
                self.assertIn(reading,{tokens for _,tokens in paths})
                self.assertLessEqual(len(paths),128)
                self.assertIn(expected,self.engine.query(source)['candidates'])

    def test_syllable_boundaries_and_rounded_vowels_remain_distinct(self):
        self.assertIn('西安',self.engine.query('시안')['candidates'])
        self.assertNotIn(('xian',),{tokens for _,tokens in self.engine.readings('시안')})
        for source,reading,excluded in (('뤼','lv','lu'),('뉘','nv','nu'),
                                        ('쥐','ju','zhu'),('췬','qun','quan')):
            paths={tokens for _,tokens in self.engine.readings(source)}
            self.assertIn((reading,),paths)
            self.assertNotIn((excluded,),paths)

    def test_polyphonic_candidates_keep_all_recognized_readings_without_duplicate_rows(self):
        for source,word,expected in (('쉐이','谁',{'shei','shui'}),
                                     ('쉐이터','谁的',{'shei de','shui de'}),
                                     ('티아오페이','调配',{'diao pei','tiao pei'})):
            answer=self.engine.query(source)
            with self.subTest(source=source):
                self.assertEqual(answer['candidates'].count(word),1)
                self.assertLessEqual(len(answer['candidates']),20)
                self.assertTrue(expected.issubset(answer['reading_alternatives'][word]))

    def test_contracted_and_zero_initial_finals(self):
        for word,final in (('liu','iou'),('gui','uei'),('dun','uen'),('you','iou'),
                           ('wei','uei'),('wen','uen'),('jun','vn'),('yuan','van')):
            with self.subTest(word=word):self.assertEqual(classify(word).final,final)

    def test_palatal_glides_and_korean_tense_variants(self):
        for word,form in (('jia','자'),('qia','차'),('xiao','샤오'),('jie','제'),
                          ('qie','체'),('xie','셰'),('bei','뻬이'),('da','따'),('gao','까오')):
            with self.subTest(word=word):self.assertIn(form,korean_forms(word))

    def test_nasal_n_and_ng_do_not_merge(self):
        self.assertEqual(classify('an').final_group,'nasal-n')
        self.assertEqual(classify('ang').final_group,'nasal-ng')
        self.assertIn('안',korean_forms('an'));self.assertNotIn('앙',korean_forms('an'))
        self.assertIn('앙',korean_forms('ang'));self.assertNotIn('안',korean_forms('ang'))


class ThreeChordTests(unittest.TestCase):
    def test_native_chinese_repeats_and_release_order(self):
        dll=library()
        dll.ks_caps_three_step.argtypes=[ctypes.POINTER(CapsState),ctypes.POINTER(wintypes.DWORD),
            ctypes.POINTER(wintypes.DWORD),wintypes.DWORD,wintypes.BOOL,wintypes.DWORD,wintypes.DWORD]
        dll.ks_caps_three_step.restype=wintypes.DWORD
        for release_order in ((0x14,0x43),(0x43,0x14)):
            state=CapsState(0x51,0,0,0,0);second=wintypes.DWORD();third=wintypes.DWORD()
            def step(key,down):
                return dll.ks_caps_three_step(ctypes.byref(state),ctypes.byref(second),ctypes.byref(third),key,down,0x41,0x43)
            self.assertEqual(step(0x14,True),1)
            self.assertEqual(step(0x43,True),17)
            self.assertEqual(step(0x43,True),1)
            self.assertEqual(step(0x41,True),1)
            self.assertEqual(step(0x51,True),1)
            for key in release_order:
                self.assertEqual(step(key,False),1)
            self.assertEqual(step(0x41,False),1)
            self.assertEqual(step(0x51,False),1)
            self.assertEqual(step(0x43,True),0)

    def test_all_modifier_combinations_share_at_most_one_caps_hook(self):
        for modes in itertools.product(('caps','ctrl_shift','ctrl_alt'),repeat=3):
            with self.subTest(modes=modes):
                entries=[(HotkeyBinding(mode,key),Mock()) for mode,key in zip(modes,'QAC')]
                group=HotkeyGroup(entries)
                self.assertLessEqual(sum(h.binding.mode=='caps' for h in group.hooks),1)
                with patch('hotkeys_windows.CapsQHook.start'),patch('hotkeys_windows.CapsQHook.stop'):
                    group.start();group.stop()

    def test_group_registration_failure_rolls_back_every_hook(self):
        group=HotkeyGroup([(HotkeyBinding('ctrl_shift','Q'),Mock()),(HotkeyBinding('caps','A'),Mock())])
        group.hooks=[Mock(),Mock()]
        group.hooks[1].start.side_effect=RuntimeError('occupied')
        with self.assertRaises(RuntimeError):group.start()
        for hook in group.hooks:hook.stop.assert_called_once()

    def test_duplicate_bindings_rejected_before_registration(self):
        with self.assertRaises(RuntimeError):
            HotkeyGroup([(HotkeyBinding('caps','C'),Mock()),(HotkeyBinding('caps','C'),Mock())])


class ChineseSettingsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qt=QApplication.instance() or QApplication([])

    def test_any_pair_collision_disables_all_apply_buttons(self):
        with tempfile.TemporaryDirectory() as folder:
            store=QSettings(str(Path(folder)/'prefs.ini'),QSettings.Format.IniFormat)
            window=app.MainWindow(store,[dict(hkl=0x0412,mode='ko_hangul',name='Korean')],False)
            window.navigate(2)
            self.assertEqual(window.chinese_key.currentData(),'C')
            for key in ('Q','A'):
                window.chinese_key.setCurrentIndex(window.chinese_key.findData(key))
                for button in (window.selector_apply,window.ime_apply,window.chinese_apply):
                    self.assertFalse(button.isEnabled())
            window.chinese_key.setCurrentIndex(window.chinese_key.findData('C'))
            self.assertTrue(window.chinese_apply.isEnabled())
            window.deleteLater()

    def test_controller_rejects_chinese_collision_and_rolls_back_failure(self):
        c=app.LexiftController.__new__(app.LexiftController)
        c.binding=HotkeyBinding();c.ime_binding=HotkeyBinding('caps','A');c.chinese_binding=HotkeyBinding('caps','C')
        c.window=Mock();c.hook=Mock();c.store=Mock();c._running=True
        with patch.object(app.QMessageBox,'warning'):
            c.change_chinese_shortcut(c.ime_binding)
            c.hook.stop.assert_not_called()
            failed,restored=Mock(),Mock();failed.start.side_effect=RuntimeError('occupied')
            c._make_keyboard_hook=Mock(side_effect=[failed,restored])
            c.change_chinese_shortcut(HotkeyBinding('ctrl_shift','F12'))
        self.assertEqual(c.chinese_binding,HotkeyBinding('caps','C'))
        restored.start.assert_called_once();c.store.setValue.assert_not_called()

    def test_language_switch_cancels_old_requests_and_reuses_warm_engine(self):
        from ime_inline import InlineMode
        mode=InlineMode()
        japanese,chinese=Mock(),Mock()
        with patch('ime_inline.QProcess'),patch('ime_query_client.QueryClient',return_value=japanese), \
             patch('chinese_query_client.ChineseQueryClient',return_value=chinese):
            self.assertTrue(mode.toggle('ja'))
            mode.cache['니하오']={'candidates':['wrong-language']}
            self.assertTrue(mode.toggle('zh'))
            japanese.cancel.assert_called_once()
            japanese.stop.assert_not_called()
            self.assertEqual(mode.language,'zh');self.assertEqual(mode.cache,{})
            with patch.object(mode,'_show') as show:
                mode._queried(japanese,{'source':'니하오','candidates':['old-result']})
                show.assert_not_called()
            self.assertFalse(mode.toggle('zh'))
            chinese.cancel.assert_called_once()
            self.assertTrue(mode.toggle('ja'))
            japanese.start.assert_called_once()
            mode.shutdown()
            japanese.stop.assert_called_once();chinese.stop.assert_called_once()
        mode.overlay.deleteLater()
