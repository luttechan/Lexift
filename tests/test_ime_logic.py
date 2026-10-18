from __future__ import annotations
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ime_windows as w


class IMELogicTests(unittest.TestCase):
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
