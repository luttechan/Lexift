import ctypes,json,unittest
from unittest.mock import Mock,patch
from ctypes import wintypes
from PySide6.QtCore import QSettings,Qt
from PySide6.QtWidgets import QApplication
from pinyin_tones import apply_tone

class ToneRulesTests(unittest.TestCase):
    def test_standard_vowel_priority_and_contracted_finals(self):
        for source,tone,expected in (('hao',3,'hǎo'),('liu',2,'liú'),('gui',3,'guǐ'),
          ('shui',4,'shuì'),('dou',1,'dōu'),('xue',3,'xuě'),('nu:',3,'nǚ'),
          ('lv',4,'lǜ'),('LÜ',2,'LǗ'),('nǐ hao',3,'nǐ hǎo'),('nihao',3,'nihǎo'),
          ('zhongguo',2,'zhongguó'),("xi'an",1,"xi'ān"),('nǐhǎo',4,'nǐhào')):
            with self.subTest(source=source):self.assertEqual(apply_tone(source,tone),expected)
    def test_tones_replace_and_remove_without_accumulating_marks(self):
        for tone,expected in enumerate(('ma','mā','má','mǎ','mà')):
            self.assertEqual(apply_tone('mǎ',tone),expected)
        self.assertEqual(apply_tone('nǐ hǎo',0),'nǐ hao')
        self.assertEqual(apply_tone('ni\u030c',4),'nì')
    def test_syllabic_nasals_allow_combining_marks_and_replacement(self):
        self.assertEqual(apply_tone('m',1),'m\u0304')
        self.assertEqual(apply_tone('m',2),'ḿ')
        self.assertEqual(apply_tone('ḿ',3),'m\u030c')
        self.assertEqual(apply_tone('ng',4),'ǹg')
        self.assertEqual(apply_tone('ńg',0),'ng')
    def test_uneditable_suffix_is_unchanged(self):
        for source in ('','123','你好','hao ','hao!'):
            self.assertEqual(apply_tone(source,2),source)
        with self.assertRaises(ValueError):apply_tone('ma',5)

class ToneInputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.qt=QApplication.instance() or QApplication([])
    def test_one_shot_uses_verified_snapshot_and_quits_after_reply(self):
        from pinyin_tone_input import ToneInput
        from ime_query_client import encode_text
        mode=ToneInput();process=Mock();mode.process=process;mode.target=42;mode.tone=3
        process.readAllStandardOutput.return_value=(json.dumps(dict(event='input',hwnd=42,source='hao',serial=7))+'\n').encode()
        mode._read(process);process.write.assert_called_once_with(f'REPLACE 7 {encode_text("hǎo")}\n'.encode())
        process.readAllStandardOutput.return_value=b'{"event":"replace","success":true}\n'
        mode._read(process);self.assertIsNone(mode.process)
        self.assertEqual(process.write.call_args.args,(b'QUIT\n',))
        mode.deleteLater()
    def test_focus_change_cannot_replace_another_field(self):
        from pinyin_tone_input import ToneInput
        mode=ToneInput();process=Mock();mode.process=process;mode.target=42;mode.tone=2
        process.readAllStandardOutput.return_value=b'{"event":"input","hwnd":43,"source":"hao","serial":1}\n'
        mode._read(process);process.write.assert_called_once_with(b'QUIT\n');mode.deleteLater()

    def test_enable_selects_chinese_ime_and_its_latin_mode(self):
        from pinyin_tone_input import ensure_chinese_latin
        with patch('ime_windows.target_is_foreground',return_value=True),patch('ime_windows.current_language',side_effect=[0x409,0x804]),patch('ime_windows.request_language') as request,patch('ime_windows.ime_set_native',return_value=True) as mode:
            self.assertTrue(ensure_chinese_latin(42,wait=lambda:None))
            request.assert_called_once_with(42,0x804);mode.assert_called_once_with(42,False)

    def test_existing_traditional_ime_is_preserved_and_set_to_latin(self):
        from pinyin_tone_input import ensure_chinese_latin
        with patch('ime_windows.target_is_foreground',return_value=True),patch('ime_windows.current_language',return_value=0x404),patch('ime_windows.request_language') as request,patch('ime_windows.ime_set_native',return_value=True) as mode:
            self.assertTrue(ensure_chinese_latin(42,wait=lambda:None))
            request.assert_not_called();mode.assert_called_once_with(42,False)

    def test_cancelled_or_unfocused_activation_never_changes_ime(self):
        from pinyin_tone_input import ensure_chinese_latin
        with patch('ime_windows.target_is_foreground',return_value=False),patch('ime_windows.request_language') as request:
            self.assertFalse(ensure_chinese_latin(42));request.assert_not_called()

class ToneSettingsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.qt=QApplication.instance() or QApplication([])
    def test_tone_shortcuts_cannot_collide_with_configurable_caps_chords(self):
        from hotkeys_windows import HotkeyGroup,HotkeyBinding
        with self.assertRaises(RuntimeError):HotkeyGroup([(HotkeyBinding('caps','1'),Mock())],on_tone=Mock())
        group=HotkeyGroup([(HotkeyBinding('ctrl_alt','1'),Mock())],on_tone=Mock())
        self.assertEqual(len(group.hooks),2)
    def test_tone_only_mode_still_has_a_native_caps_owner(self):
        from hotkeys_windows import HotkeyGroup
        callback=Mock();group=HotkeyGroup([],on_tone=callback)
        self.assertEqual(len(group.hooks),1);self.assertIs(group.hooks[0].on_tone,callback)
        self.assertIsNone(group.hooks[0].on_hotkey)


class NativeToneStateTests(unittest.TestCase):
    def test_caps_number_autorepeat_release_order_and_off(self):
        from native_hooks import library
        class State(ctypes.Structure):
            _fields_=[(name,wintypes.DWORD) for name in ('trigger','held','used','suppressed','chord')]
        dll=library();step=dll.ks_caps_tone_step
        step.argtypes=[ctypes.POINTER(State),ctypes.POINTER(ctypes.c_ubyte),wintypes.DWORD,wintypes.BOOL,wintypes.BOOL]
        step.restype=wintypes.DWORD
        held=(ctypes.c_ubyte*5)();state=State(81,1,0,0,0)
        self.assertEqual(step(ctypes.byref(state),held,ord('3'),True,True),1|(4<<8))
        self.assertEqual(step(ctypes.byref(state),held,ord('3'),True,True),1)
        state.held=0
        self.assertEqual(step(ctypes.byref(state),held,ord('3'),False,False),1)
        self.assertEqual(step(ctypes.byref(state),held,ord('3'),True,False),0)
        state.held=1
        self.assertEqual(step(ctypes.byref(state),held,ord('2'),True,True),1|(3<<8))
        self.assertEqual(step(ctypes.byref(state),held,ord('2'),False,True),1)
        self.assertEqual(step(ctypes.byref(state),held,ord('4'),True,True),1|(5<<8))
        self.assertEqual(step(ctypes.byref(state),held,ord('5'),True,True),0)
