from dataclasses import replace
import unittest
from unittest.mock import patch, Mock

import ime_windows as w
import app
from layout_profiles import create_layout, mode_options, installed_slots, sanitized_slots, preferred_mode


class IMEModeChoiceTests(unittest.TestCase):
    def test_choices_name_the_language_and_english(self):
        for locale, mode, name in ((0x0412,'ko_hangul','한국어'),
                                   (0x0411,'ja_hiragana','일본어 · 히라가나'),
                                   (0x0804,'ime_native','중국어'),
                                   (0x0404,'ime_native','중국어'),
                                   (0x0439,'ime_native',None)):
            layout = replace(create_layout(locale), is_ime=True)
            choices = dict(mode_options(layout))
            self.assertEqual(choices[mode], name or layout.name)
            self.assertEqual(choices['ko_latin' if locale == 0x0412 else 'ime_latin'], '영어')

    def test_capable_ime_gets_native_latin_and_keep_modes_in_any_language(self):
        for locale in (0x0804,0x0404,0x0C04,0x0439,0x041E):
            layout = replace(create_layout(locale),is_ime=True)
            self.assertEqual([key for key,_ in mode_options(layout)],['ime_native','ime_latin','default'])
            self.assertEqual(preferred_mode(layout),'ime_native')

    def test_ordinary_keyboards_never_get_fake_ime_toggle(self):
        layout = replace(create_layout(0x040C),is_ime=False)
        self.assertEqual(mode_options(layout),[('default','키보드 / 입력기 전환')])

    def test_japanese_includes_english_and_keeps_existing_modes(self):
        keys = dict(mode_options('japanese'))
        self.assertIn('ime_latin',keys)
        self.assertIn('ja_katakana_ask',keys)

    def test_new_modes_survive_save_and_reload_without_migrating_keep_mode(self):
        layout=replace(create_layout(0x0804),is_ime=True)
        slots=[dict(hkl=layout.hkl,mode=mode,name=mode) for mode in ('ime_native','ime_latin','default')]
        self.assertEqual(installed_slots(sanitized_slots(slots),[layout]),slots)
        self.assertEqual(app.short_code(slots[1],layout),'EN')


class GenericNativeModeTests(unittest.TestCase):
    def setUp(self):
        self.patches=[patch.object(w,'target_is_foreground',return_value=True),
                      patch.object(w,'current_hkl',return_value=0x08040804),
                      patch.object(w,'ime_capabilities',return_value=(True,True))]
        for item in self.patches:item.start()

    def tearDown(self):
        for item in reversed(self.patches):item.stop()

    def test_native_and_latin_preserve_unrelated_conversion_bits(self):
        flags=w.IME_CMODE_FULLSHAPE|w.IME_CMODE_ROMAN|0x400
        for desired in (True,False):
            before=flags if desired else flags|w.IME_CMODE_NATIVE
            after=flags|w.IME_CMODE_NATIVE if desired else flags
            with patch.object(w,'_mode',side_effect=[(before,True),(after,desired)]), \
                 patch.object(w,'_ime_cmd',return_value=(True,0)) as command:
                self.assertTrue(w.ime_set_native(101,desired))
            writes=[call.args for call in command.call_args_list]
            self.assertIn((101,w.IMC_SETCONVERSIONMODE,after),writes)
            self.assertIn((101,w.IMC_SETOPENSTATUS,int(desired)),writes)

    def test_already_correct_mode_does_not_write_or_toggle(self):
        with patch.object(w,'_mode',return_value=(1,True)),patch.object(w,'_ime_cmd') as write:
            self.assertTrue(w.ime_set_native(101,True))
        write.assert_not_called()

    def test_unknown_state_does_not_claim_native_or_write_unknown_flags(self):
        with patch.object(w,'_mode',return_value=(None,None)),patch.object(w,'_ime_cmd') as write:
            self.assertIsNone(w.ime_native_status(101))
            self.assertFalse(w.ime_set_native(101,True))
        write.assert_not_called()

    def test_open_status_alone_cannot_override_known_alphanumeric_mode(self):
        with patch.object(w,'_mode',return_value=(0,True)):
            self.assertIs(w.ime_native_status(101),False)

    def test_successful_command_is_not_enough_without_readback(self):
        with patch.object(w,'_mode',return_value=(1,True)),patch.object(w,'_ime_cmd',return_value=(True,0)):
            self.assertFalse(w.ime_set_native(101,False))

    def test_open_only_ime_does_not_send_conversion_commands(self):
        opened=[True]
        def command(hwnd,command,value=0,**kwargs):
            if command==w.IMC_GETOPENSTATUS:return True,int(opened[0])
            self.assertEqual(command,w.IMC_SETOPENSTATUS)
            opened[0]=bool(value)
            return True,0
        with patch.object(w,'ime_capabilities',return_value=(True,False)),patch.object(w,'_ime_cmd',side_effect=command):
            self.assertTrue(w.ime_set_native(101,False))
            self.assertFalse(opened[0])

    def test_no_commands_when_target_focus_is_lost(self):
        with patch.object(w,'target_is_foreground',return_value=False),patch.object(w,'_ime_cmd') as command:
            self.assertFalse(w.ime_set_native(101,True))
        command.assert_not_called()

    def test_windows_toggle_is_language_specific_and_never_blind(self):
        for locale,identifier in ((0x0804,0x10),(0x1004,0x10),(0x0404,0x70),(0x0C04,0x70),(0x0411,0x30)):
            with patch.object(w,'current_hkl',return_value=locale), \
                 patch.object(w,'ime_native_status',return_value=False), \
                 patch.object(w.imm32,'ImmSimulateHotKey',return_value=True) as toggle:
                self.assertTrue(w.ime_toggle_native(101,True))
            toggle.assert_called_once_with(101,identifier)
        for state in (None,True):
            with patch.object(w,'ime_native_status',return_value=state), \
                 patch.object(w.imm32,'ImmSimulateHotKey') as toggle:
                self.assertFalse(w.ime_toggle_native(101,True))
            toggle.assert_not_called()


class ModeVerificationTests(unittest.TestCase):
    def setUp(self):
        self.c=app.LexiftController.__new__(app.LexiftController)
        self.c._job=7;self.c._stopping=False;self.c._enabled=True
        self.c.overlay=Mock();self.c.overlay.isVisible.return_value=False
        self.c.cursor_indicator=Mock();self.c.tray=Mock()
        layout=replace(create_layout(0x0804),is_ime=True)
        self.slot=dict(hkl=layout.hkl,mode='ime_native',name='Chinese')
        self.patches=[patch.object(app,'current_hkl',return_value=int(layout.hkl,16)),
            patch.object(app,'target_is_foreground',return_value=True),
            patch.object(app,'available_layouts',return_value=[layout]),
            patch.object(app.QTimer,'singleShot')]
        for item in self.patches:item.start()

    def tearDown(self):
        for item in reversed(self.patches):item.stop()

    def test_success_indicator_requires_verified_mode(self):
        with patch.object(app,'ime_native_status',return_value=True):
            self.c._verify_ime_mode(7,101,self.slot,True,0)
        self.c.cursor_indicator.show_language.assert_called_once()

    def test_unknown_mode_fails_after_bounded_retries(self):
        with patch.object(app,'ime_native_status',return_value=None):
            self.c._verify_ime_mode(7,101,self.slot,True,2)
        self.c.cursor_indicator.show_language.assert_not_called()
        self.c.tray.showMessage.assert_called_once()

    def test_fallback_toggle_only_once_then_direct_set(self):
        with patch.object(app,'ime_native_status',return_value=False), \
             patch.object(app,'ime_toggle_native') as toggle,patch.object(app,'ime_set_native') as direct:
            self.c._verify_ime_mode(7,101,self.slot,True,0)
            self.c._verify_ime_mode(7,101,self.slot,True,1)
        toggle.assert_called_once();direct.assert_called_once()

    def test_user_layout_change_cancels_before_writing_mode(self):
        with patch.object(app,'current_hkl',return_value=0x0409),patch.object(app,'ime_native_status') as status:
            self.c._verify_ime_mode(7,101,self.slot,True,0)
        status.assert_not_called()
        self.assertNotEqual(self.c._job,7)
