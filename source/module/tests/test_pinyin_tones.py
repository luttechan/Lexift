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
    @patch('ime_windows.target_is_foreground',return_value=True)
    @patch('ime_windows._root',return_value=42)
    def test_one_shot_uses_verified_snapshot_and_quits_after_reply(self,*_):
        from pinyin_tone_input import ToneInput
        from ime_query_client import encode_text
        mode=ToneInput();process=Mock();mode.process=process;mode.target=42;mode.tone=3
        process.readAllStandardOutput.return_value=(json.dumps(dict(event='input',hwnd=42,source='hao',serial=7))+'\n').encode()
        mode._read(process);process.write.assert_called_once_with(f'REPLACE 7 {encode_text("hǎo")}\n'.encode())
        process.readAllStandardOutput.return_value=b'{"event":"replace","success":true}\n'
        mode._read(process);self.assertIsNone(mode.process)
        self.assertEqual(process.write.call_args.args,(b'QUIT\n',))
        mode.deleteLater()
    @patch('ime_windows.target_is_foreground',return_value=True)
    @patch('ime_windows._root',return_value=42)
    def test_focus_change_cannot_replace_another_field(self,*_):
        from pinyin_tone_input import ToneInput
        mode=ToneInput();process=Mock();mode.process=process;mode.target=42;mode.tone=2
        process.readAllStandardOutput.return_value=b'{"event":"input","hwnd":43,"source":"hao","serial":1}\n'
        mode._read(process);process.write.assert_called_once_with(b'QUIT\n');mode.deleteLater()

    def test_focused_child_can_use_its_owner_snapshot_without_switching_ime(self):
        from pinyin_tone_input import ToneInput
        from ime_query_client import encode_text
        for tone,expected in enumerate(('ke','kē','ké','kě','kè')):
            mode=ToneInput();process=Mock();mode.process=process;mode.target=420;mode.tone=tone
            source='kè' if tone==0 else 'ke'
            process.readAllStandardOutput.return_value=(json.dumps(dict(event='input',hwnd=42,source=source,serial=7))+'\n').encode()
            with patch('ime_windows._root',return_value=42),patch('ime_windows.target_is_foreground',return_value=True),patch('ime_windows.request_language') as switch,patch('ime_windows.ime_set_native') as native:
                mode._read(process)
                process.write.assert_called_once_with(f'REPLACE 7 {encode_text(expected)}\n'.encode())
                switch.assert_not_called();native.assert_not_called()
            mode.cancel();mode.deleteLater()

    def test_focus_moves_to_sibling_in_same_window_rejects_snapshot(self):
        from pinyin_tone_input import ToneInput
        mode=ToneInput();process=Mock();mode.process=process;mode.target=420;mode.tone=2
        process.readAllStandardOutput.return_value=b'{"event":"input","hwnd":42,"source":"ke","serial":1}\n'
        with patch('ime_windows._root',return_value=42),patch('ime_windows.target_is_foreground',return_value=False):
            mode._read(process)
        process.write.assert_called_once_with(b'QUIT\n');mode.deleteLater()

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
    def test_keypad_tones_numlock_on_off_and_dedicated_arrows(self):
        from native_hooks import library
        class State(ctypes.Structure):
            _fields_=[(name,wintypes.DWORD) for name in ('trigger','held','used','suppressed','chord')]
        step=library().ks_caps_tone_event_step
        step.argtypes=[ctypes.POINTER(State),ctypes.POINTER(ctypes.c_ubyte),wintypes.DWORD,wintypes.DWORD,wintypes.BOOL,wintypes.BOOL,wintypes.BOOL,wintypes.DWORD]
        step.restype=wintypes.DWORD
        scan=(0x52,0x4f,0x50,0x51,0x4b);nav=(0x2d,0x23,0x28,0x22,0x25)
        for tone in range(5):
            for vk in (0x60+tone,nav[tone]):
                held=(ctypes.c_ubyte*10)();state=State(81,1,0,0,0)
                call=lambda key,ext,down,enabled:step(ctypes.byref(state),held,key,scan[tone],ext,down,enabled,0)
                self.assertEqual(call(vk,False,True,True),1|((tone+1)<<8))
                self.assertEqual(call(vk,False,True,True),1)
                state.held=0
                # Num Lock can change while the physical key is held.
                self.assertEqual(call(nav[tone],False,False,False),1)
                self.assertFalse(any(held))
                state.held=1
                self.assertEqual(call(nav[tone],True,True,True),0)
                self.assertEqual(call(vk,False,True,False),0)
                self.assertEqual(call(vk,False,False,False),0)
                state.held=0
                self.assertEqual(call(vk,False,True,True),0)

    def test_top_row_and_keypad_hold_independently(self):
        from native_hooks import library
        class State(ctypes.Structure):
            _fields_=[(name,wintypes.DWORD) for name in ('trigger','held','used','suppressed','chord')]
        step=library().ks_caps_tone_event_step
        step.argtypes=[ctypes.POINTER(State),ctypes.POINTER(ctypes.c_ubyte),wintypes.DWORD,wintypes.DWORD,wintypes.BOOL,wintypes.BOOL,wintypes.BOOL,wintypes.DWORD]
        step.restype=wintypes.DWORD
        held=(ctypes.c_ubyte*10)();state=State(81,1,0,0,0)
        call=lambda vk,down:step(ctypes.byref(state),held,vk,0,False,down,True,0)
        self.assertEqual(call(ord('3'),True),1|(4<<8))
        self.assertEqual(call(0x63,True),1|(4<<8))
        self.assertEqual(call(ord('3'),False),1)
        self.assertEqual(call(0x63,True),1)
        self.assertEqual(call(0x63,False),1)
        self.assertFalse(any(held))

    def test_popup_numbers_take_priority_over_tones_while_caps_is_held(self):
        from native_hooks import library
        class State(ctypes.Structure):
            _fields_=[(name,wintypes.DWORD) for name in ('trigger','held','used','suppressed','chord')]
        dll=library();step=dll.ks_caps_tone_event_step
        step.argtypes=[ctypes.POINTER(State),ctypes.POINTER(ctypes.c_ubyte),wintypes.DWORD,wintypes.DWORD,wintypes.BOOL,wintypes.BOOL,wintypes.BOOL,wintypes.DWORD]
        step.restype=wintypes.DWORD
        nav=dll.ks_navigation_event_step
        nav.argtypes=[ctypes.POINTER(ctypes.c_ubyte),wintypes.DWORD,wintypes.DWORD,wintypes.BOOL,wintypes.DWORD,wintypes.BOOL,wintypes.BOOL,wintypes.BOOL]
        nav.restype=wintypes.DWORD
        for mode in (1,2,3):
            state=State(81,1,0,0,1);held=(ctypes.c_ubyte*10)()
            self.assertEqual(step(ctypes.byref(state),held,0x63,0x51,False,True,True,mode),0)
            if mode<3:
                navigation=(ctypes.c_ubyte*256)()
                action=nav(navigation,0x63,0x51,True,mode,True,False,False)
                self.assertEqual(action,3)  # SWALLOW | FIRE; VK travels separately.
            self.assertEqual(step(ctypes.byref(state),held,0x63,0x51,False,True,True,0),1|(4<<8))
            self.assertEqual(step(ctypes.byref(state),held,0x63,0x51,False,False,True,mode),1)
            self.assertFalse(any(held))

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
