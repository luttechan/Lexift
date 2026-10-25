import copy,ctypes,unittest
from ctypes import wintypes
from unittest.mock import Mock,patch
from chinese_reading import ChineseEngine
from chinese_variants import OutputProfiles,zhuyin_syllable,zhuyin_reading
from hotkeys_windows import HotkeyBinding,HotkeyGroup
from native_hooks import library

class ChineseVariantTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.engine=ChineseEngine();cls.output=OutputProfiles()
    def test_every_dictionary_syllable_has_a_bopomofo_mapping(self):
        self.assertEqual(len(self.engine.syllables),415)
        for spelling in self.engine.syllables:
            value=zhuyin_syllable(spelling)
            self.assertTrue(value,spelling)
            self.assertTrue(all('\u3105'<=c<='\u312f' for c in value),(spelling,value))
    def test_dictionary_bopomofo_uses_an_explicit_supported_script_font(self):
        from i18n import text_font_family,set_language
        try:
            for code in ('ko','en','ja','zh_CN','zh_TW'):
                set_language(code)
                self.assertEqual(text_font_family('ㄋㄧ ㄏㄠ'),'Microsoft JhengHei UI')
        finally:set_language('ko')
    def test_apical_rounded_front_contracted_and_zero_initial_rules(self):
        rows={'zhi':'ㄓ','chi':'ㄔ','shi':'ㄕ','ri':'ㄖ','zi':'ㄗ','ci':'ㄘ','si':'ㄙ',
              'ji':'ㄐㄧ','qi':'ㄑㄧ','xi':'ㄒㄧ','ju':'ㄐㄩ','qu':'ㄑㄩ','xu':'ㄒㄩ',
              'juan':'ㄐㄩㄢ','quan':'ㄑㄩㄢ','xuan':'ㄒㄩㄢ','jun':'ㄐㄩㄣ','jiong':'ㄐㄩㄥ',
              'liu':'ㄌㄧㄡ','gui':'ㄍㄨㄟ','dun':'ㄉㄨㄣ','lü':'ㄌㄩ','nue':'ㄋㄩㄝ',
              'yi':'ㄧ','wu':'ㄨ','yu':'ㄩ','yue':'ㄩㄝ','yuan':'ㄩㄢ','yun':'ㄩㄣ','yong':'ㄩㄥ',
              'wen':'ㄨㄣ','weng':'ㄨㄥ','zhong':'ㄓㄨㄥ','er':'ㄦ','wo':'ㄨㄛ'}
        for pinyin,expected in rows.items():self.assertEqual(zhuyin_syllable(pinyin),expected,pinyin)
        self.assertEqual(zhuyin_reading('ni hao'),'ㄋㄧ ㄏㄠ')
        with self.assertRaises(ValueError):zhuyin_syllable('notasyllable')
    def test_traditional_word_context_and_reading_preservation(self):
        data=dict(source='예제',kana='tou fa',candidates=['头发','发展','皇后','以后','软件'],
                  readings=['tou fa','fa zhan','huang hou','yi hou','ruan jian'])
        result=self.output.transform(data,'zh_tw')
        self.assertEqual(result['candidates'],['頭髮','發展','皇后','以後','軟件'])
        self.assertEqual(result['readings'],data['readings'])
    def test_real_dictionary_profiles_do_not_modify_simplified_results(self):
        for source,traditional,bopomofo in (('니하오','你好','ㄋㄧ ㄏㄠ'),('중궈','中國','ㄓㄨㄥ ㄍㄨㄛ'),
                                           ('터우파','頭髮','ㄊㄡ ㄈㄚ'),('췐','權','ㄑㄩㄢ')):
            data=self.engine.query(source);before=copy.deepcopy(data)
            tw=self.output.transform(data,'zh_tw');bo=self.output.transform(data,'zh_bopomofo')
            self.assertIn(traditional,tw['candidates']);self.assertIn(bopomofo,bo['candidates'])
            self.assertEqual(data,before);self.assertIs(self.output.transform(data,'zh'),data)
            self.assertFalse(bo['tones']);self.assertLessEqual(len(bo['candidates']),20)
            self.assertEqual(len(bo['candidates']),len(set(bo['candidates'])))
    def test_polyphonic_readings_survive_candidate_deduplication(self):
        data=dict(source='셰이',kana='shei',candidates=['谁'],readings=['shei'],reading_alternatives={'谁':['shei','shui']})
        bo=self.output.transform(data,'zh_bopomofo')
        self.assertEqual(bo['candidates'],['ㄕㄟ','ㄕㄨㄟ'])
        self.assertEqual(self.output.transform(data,'zh_tw')['reading_alternatives']['誰'],['shei','shui'])
    def test_four_caps_bindings_use_one_native_hook_and_never_drop_the_fourth(self):
        callbacks=[Mock() for _ in range(4)]
        with patch('hotkeys_windows.CapsQHook') as hook:
            group=HotkeyGroup([(HotkeyBinding('caps',k),cb) for k,cb in zip('QACT',callbacks)])
            self.assertEqual(len(group.hooks),1)
            self.assertEqual(hook.call_args.kwargs['quaternary_key'],'T')
            self.assertIs(hook.call_args.kwargs['on_traditional'],callbacks[3])
        with self.assertRaises(ValueError):HotkeyGroup([(HotkeyBinding('caps',k),Mock()) for k in 'QACTB'])
    def test_fourth_chord_repeats_and_key_up_order_are_balanced(self):
        class State(ctypes.Structure):
            _fields_=[(name,wintypes.DWORD) for name in ('trigger','held','used','suppressed','chord')]
        dll=library();fn=dll.ks_caps_four_step
        fn.argtypes=[ctypes.POINTER(State),ctypes.POINTER(wintypes.DWORD),ctypes.POINTER(wintypes.DWORD),
                     ctypes.POINTER(wintypes.DWORD),wintypes.DWORD,wintypes.BOOL,wintypes.DWORD,wintypes.DWORD,wintypes.DWORD]
        fn.restype=wintypes.DWORD
        self.assertEqual(dll.ks_abi_version(),6)
        for caps_up_first in (True,False):
            state=State(0x51,0,0,0,0);held=[wintypes.DWORD() for _ in range(3)]
            def step(key,down):return fn(ctypes.byref(state),*[ctypes.byref(v) for v in held],key,down,0x41,0x43,0x54)
            for _ in range(100):
                self.assertEqual(step(0x14,True),1);self.assertEqual(step(0x54,True),33)
                self.assertEqual(step(0x54,True),1)
                for key in ((0x14,0x54) if caps_up_first else (0x54,0x14)):self.assertEqual(step(key,False),1)
                self.assertEqual(step(0x54,True),0);self.assertEqual(step(0x54,False),0)

    def test_cycle_binding_can_be_tapped_with_caps_held_in_every_native_slot(self):
        class State(ctypes.Structure):
            _fields_=[(name,wintypes.DWORD) for name in ('trigger','held','used','suppressed','chord')]
        fn=library().ks_caps_cycle_step
        fn.argtypes=[ctypes.POINTER(State),ctypes.POINTER(wintypes.DWORD),ctypes.POINTER(wintypes.DWORD),
                     ctypes.POINTER(wintypes.DWORD),wintypes.DWORD,wintypes.BOOL,wintypes.DWORD,wintypes.DWORD,wintypes.DWORD,wintypes.DWORD]
        fn.restype=wintypes.DWORD
        for key,action in ((0x51,3),(0x41,9),(0x43,17),(0x54,33)):
            state=State(0x51,0,0,0,0);held=[wintypes.DWORD() for _ in range(3)]
            def step(vk,down):return fn(ctypes.byref(state),*[ctypes.byref(v) for v in held],vk,down,0x41,0x43,0x54,key)
            self.assertEqual(step(0x14,True),1)
            for _ in range(3):
                self.assertEqual(step(key,True),action)
                self.assertEqual(step(key,True),1)
                self.assertEqual(step(key,False),1)
            self.assertEqual(step(0x14,False),1)
