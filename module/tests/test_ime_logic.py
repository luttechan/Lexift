from __future__ import annotations
import sys
import unittest
import time
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ime_windows as w


class IMELogicTests(unittest.TestCase):
    def test_unresponsive_ime_queries_have_short_bounded_wait(self):
        def timeout(ime, message, command, value, flags, milliseconds, result):
            time.sleep(milliseconds / 1000)
            return 0
        with patch.object(w.imm32, 'ImmGetDefaultIMEWnd', return_value=123), \
             patch.object(w.user32, 'SendMessageTimeoutW', side_effect=timeout):
            started = time.perf_counter()
            self.assertEqual(w._mode(101), (None, None))
            self.assertLess(time.perf_counter()-started, .3)

    def test_focus_change_stops_korean_and_japanese_writes_mid_operation(self):
        for locale, name, args, status_name in ((w.LANG_KO,'korean_set',(True,),'korean_is_hangul'),
                                               (w.LANG_JA,'japanese_set',('hiragana',),'japanese_matches')):
            with patch.object(w,'current_language',return_value=locale), \
                 patch.object(w,'current_hkl',return_value=locale), \
                 patch.object(w,status_name,return_value=False), \
                 patch.object(w,'target_is_foreground',side_effect=[True,False]), \
                 patch.object(w,'_ime_cmd') as command:
                self.assertFalse(getattr(w,name)(101,*args))
            self.assertEqual(command.call_count,1)
            self.assertEqual(command.call_args.args[1],w.IMC_SETOPENSTATUS)

    def test_layout_change_during_query_cancels_writes(self):
        with patch.object(w,'current_language',return_value=w.LANG_KO), \
             patch.object(w,'current_hkl',side_effect=[w.LANG_KO,w.LANG_JA]), \
             patch.object(w,'korean_is_hangul',return_value=False), \
             patch.object(w,'target_is_foreground',return_value=True), \
             patch.object(w,'_ime_cmd') as command:
            self.assertFalse(w.korean_set(101,True))
        command.assert_not_called()

    def test_english_uses_korean_ime_not_us_keyboard(self):
        with patch.object(w, 'current_language', return_value=w.LANG_KO), \
             patch.object(w, 'korean_is_hangul', return_value=False):
            self.assertTrue(w.korean_set(101, False))

    def test_hiragana_flags_do_not_include_katakana(self):
        flags = w._JAPANESE_MODES['hiragana']
        self.assertFalse(flags & w.IME_CMODE_KATAKANA)
        self.assertTrue(flags & w.IME_CMODE_FULLSHAPE)

    def test_katakana_half_flags(self):
        flags = w._JAPANESE_MODES['katakana_half']
        self.assertTrue(flags & w.IME_CMODE_KATAKANA)
        self.assertFalse(flags & w.IME_CMODE_FULLSHAPE)

    def test_no_claim_of_success_when_language_incorrect(self):
        with patch.object(w, 'current_language', return_value=w.LANG_KO):
            self.assertFalse(w.japanese_set(101, 'hiragana'))

    def test_no_synthetic_hotkey_on_foreign_focus(self):
        with patch.object(w, 'current_language', return_value=w.LANG_JA), \
             patch.object(w, 'target_is_foreground', return_value=False):
            self.assertFalse(w.japanese_fallback_key(101, 'hiragana'))

    def test_openstatus_off_counts_as_latin(self):
        with patch.object(w, '_mode', return_value=(w.IME_CMODE_NATIVE, False)):
            self.assertEqual(w.korean_is_hangul(101), False)


if __name__ == '__main__':
    unittest.main()
