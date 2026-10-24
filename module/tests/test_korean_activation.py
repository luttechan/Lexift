import unittest
from unittest.mock import patch
from korean_activation import ensure_korean


class KoreanActivationTests(unittest.TestCase):
    def setUp(self):
        self.patcher=patch('korean_activation.ime')
        self.ime=self.patcher.start();self.addCleanup(self.patcher.stop)
        self.ime.LANG_KO=0x412
        self.ime.target_is_foreground.return_value=True
        self.ime.current_language.return_value=0x412
        self.ime.korean_is_hangul.return_value=True
        self.ime.korean_set.return_value=False

    def test_english_layout_requests_korean_then_verifies_hangul(self):
        self.ime.current_language.side_effect=[0x409,0x409,0x412]
        self.assertTrue(ensure_korean(123,wait=lambda:None))
        self.ime.request_language.assert_called_once_with(123,0x412)
        self.ime.korean_toggle_key.assert_not_called()

    def test_existing_hangul_needs_no_toggle(self):
        self.assertTrue(ensure_korean(123))
        self.ime.korean_set.assert_not_called()
        self.ime.korean_toggle_key.assert_not_called()

    def test_known_latin_mode_uses_single_fallback_toggle(self):
        self.ime.korean_is_hangul.side_effect=[False,False,True]
        self.ime.korean_toggle_key.return_value=True
        self.assertTrue(ensure_korean(123,wait=lambda:None))
        self.ime.korean_toggle_key.assert_called_once_with(123)

    def test_unknown_mode_never_blindly_toggles(self):
        self.ime.korean_is_hangul.return_value=None
        self.assertFalse(ensure_korean(123,wait=lambda:None))
        self.ime.korean_toggle_key.assert_not_called()

    def test_cancelled_or_changed_focus_does_not_change_layout(self):
        self.assertFalse(ensure_korean(123,cancelled=lambda:True))
        self.ime.request_language.assert_not_called()
        self.ime.korean_set.assert_not_called()
        self.ime.target_is_foreground.return_value=False
        self.assertFalse(ensure_korean(123))
        self.ime.korean_set.assert_not_called()
