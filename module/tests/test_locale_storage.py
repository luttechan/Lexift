"""Keep locale switching offline, bounded, and reversible."""
import unittest
from unittest.mock import patch
import i18n


class LocaleStorageTests(unittest.TestCase):
    def tearDown(self):
        i18n.set_language('ko')

    def test_all_language_columns_include_input_errors(self):
        key = 'Windows 입력기 전환 명령을 실행하지 못했습니다.'
        for code in i18n.CODES:
            i18n.set_language(code)
            self.assertEqual(i18n.tr(key), i18n.CATALOG[code][key])
            self.assertEqual(i18n.source_key(i18n.tr(key)), key)
            self.assertIn(key, i18n.CATALOG[code])

    def test_unknown_text_and_unknown_language_leave_current_language_safe(self):
        i18n.set_language('en')
        self.assertEqual(i18n.tr('Custom user name'), 'Custom user name')
        self.assertEqual(i18n.source_key('Custom user name'), 'Custom user name')
        with self.assertRaises(ValueError):
            i18n.set_language('../../unknown')
        self.assertEqual(i18n.tr('대시보드'), 'Dashboard')

    def test_repeated_switches_do_not_read_files_or_grow_catalogs(self):
        views = tuple(id(view) for view in i18n.CATALOG.values())
        rows = tuple((key, id(row)) for key, row in i18n._ROWS.items())
        with patch('builtins.open', side_effect=AssertionError('locale disk access')):
            for index in range(10000):
                i18n.set_language(i18n.LANGUAGES[index % 9][0])
                i18n.tr('대시보드')
                i18n.tr_count(index % 15 + 1, 'CapsLock + Q')
                i18n.tr_hint('CapsLock + Q')
                i18n.tr_notify('CapsLock + Q')
        self.assertEqual(tuple(id(view) for view in i18n.CATALOG.values()), views)
        self.assertEqual(tuple((key, id(row)) for key, row in i18n._ROWS.items()), rows)

    def test_catalogs_cannot_mutate_shared_translation_data(self):
        with self.assertRaises(TypeError):
            i18n.CATALOG['en']['대시보드'] = 'bad'
        i18n.set_language('en')
        self.assertEqual(i18n.tr('대시보드'), 'Dashboard')
