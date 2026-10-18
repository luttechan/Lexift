import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from layout_profiles import (
    classify, create_layout, mode_options, initial_slots, sanitized_slots,
    hkl_string, hkl_number, default_name, installed_slots,
    first_run_slots, needs_first_run_setup,
)


class ProfileTests(unittest.TestCase):
    def test_windows_locale_families(self):
        self.assertEqual(classify(0x0412)[0], "korean")
        self.assertEqual(classify(0x0411)[0], "japanese")
        self.assertEqual(classify(0x0804)[0], "chinese_simple")
        self.assertEqual(classify(0x1004)[0], "chinese_simple")
        self.assertEqual(classify(0x0404)[0], "chinese_traditional")
        self.assertEqual(classify(0x0C04)[0], "chinese_traditional")
        self.assertEqual(classify(0x1404)[0], "chinese_traditional")
        self.assertEqual(classify(0x0419), ("standard", "Я"))
        self.assertEqual(classify(0x040C), ("standard", "FR"))
        self.assertEqual(classify(0x040A), ("standard", "ES"))

    def test_nonhardcoded_language_supported(self):
        self.assertEqual(classify(0x0422)[0], "standard")  # Ukrainian
        self.assertEqual(classify(0x041E)[0], "standard")  # Thai
        self.assertEqual(classify(0x0439)[0], "standard")  # Hindi

    def test_japanese_no_half_hiragana(self):
        ja = [mode for mode, _ in mode_options("japanese")]
        self.assertIn("ja_katakana_half", ja)
        self.assertNotIn("ja_hiragana_half", ja)
        self.assertIn("ja_katakana_ask", ja)

    def test_chinese_has_no_unverified_script_toggle(self):
        self.assertEqual(mode_options("chinese_simple"), [("default", "키보드 / 입력기 전환")])
        self.assertEqual(mode_options("chinese_traditional"), mode_options("chinese_simple"))

    def test_hkl_roundtrip(self):
        for hkl in (0x0412, 0xF0020411, 0x00000419):
            self.assertEqual(hkl_number(hkl_string(hkl)), hkl)

    def test_wizard_starts_with_one_slot_even_with_six_installed(self):
        layouts = [create_layout(0x00000409+i) for i in range(6)]
        slots = first_run_slots(layouts)
        self.assertEqual(len(slots), 1)
        self.assertEqual(slots[0]["hkl"], layouts[0].hkl)

    def test_initial_setup_not_repeated_for_existing_one_slot(self):
        layouts = [create_layout(0x00000412), create_layout(0x00000411)]
        saved = [{"hkl": layouts[1].hkl, "mode": "ja_hiragana", "name": "히라가나"}]
        self.assertFalse(needs_first_run_setup(saved, layouts))

    def test_initial_setup_repeated_if_saved_input_removed(self):
        layouts = [create_layout(0x00000419)]
        saved = [{"hkl": hkl_string(0x00000411), "mode": "ja_hiragana", "name": "Japan"}]
        self.assertTrue(needs_first_run_setup(saved, layouts))

    def test_initial_setup_when_no_profile(self):
        layouts = [create_layout(0x00000419)]
        self.assertTrue(needs_first_run_setup([], layouts))
        self.assertEqual(first_run_slots([]), [])

    def test_setup_one_or_two_modes_of_same_ime_remains_valid(self):
        layout = create_layout(0x00000411)
        saved = [{"hkl": layout.hkl, "mode":"ja_hiragana", "name":"ひらがな"},
                 {"hkl": layout.hkl, "mode":"ja_katakana_half", "name":"ｶﾀｶﾅ"}]
        self.assertEqual(installed_slots(saved, [layout]), saved)

    def test_initial_slots_use_actual_installed_list(self):
        layouts = [create_layout(0x00000412), create_layout(0x00000411),
                   create_layout(0x00000419), create_layout(0x0000040C)]
        slots = initial_slots(layouts)
        self.assertEqual(len(slots), 4)
        self.assertEqual([x["hkl"] for x in slots], [x.hkl for x in layouts])
        self.assertEqual([x["mode"] for x in slots], [
            "ko_hangul", "ja_hiragana", "default", "default"])

    def test_only_six_installed_layouts_on_first_run(self):
        layouts = [create_layout(0x00000409+i) for i in range(12)]
        self.assertEqual(len(initial_slots(layouts)), 6)

    def test_uninstalled_saved_layout_hidden(self):
        layouts = [create_layout(0x00000412), create_layout(0x00000419)]
        saved = [{"hkl": hkl_string(0x00000411), "mode":"ja_hiragana", "name":"Japanese"},
                 {"hkl": layouts[1].hkl, "mode":"default", "name":"Russian"}]
        self.assertEqual(installed_slots(saved, layouts), [saved[1]])

    def test_preserves_custom_modes_for_present_layouts(self):
        layout = create_layout(0x00000411)
        saved = [{"hkl": layout.hkl, "mode": "ja_katakana_half", "name": "My Katakana"}]
        self.assertEqual(installed_slots(saved, [layout]), saved)

    def test_invalid_mode_not_used_for_new_layout(self):
        layout = create_layout(0x00000419)
        saved = [{"hkl": layout.hkl, "mode": "ja_hiragana", "name": "bad"}]
        self.assertEqual(installed_slots(saved, [layout])[0]["mode"], "default")

    def test_missing_all_recovers_installed_layouts(self):
        layout = create_layout(0x0000040C)
        missing = [{"hkl": hkl_string(0x00000419), "mode":"default"}]
        self.assertEqual(installed_slots(missing, [layout]), initial_slots([layout]))

    def test_can_default_non_ime_language(self):
        layouts = [create_layout(0x00000419), create_layout(0x0000040A),
                   create_layout(0x0000040C)]
        slots = initial_slots(layouts)
        self.assertEqual(len(slots), 3)
        self.assertTrue(all(slot['mode'] == 'default' for slot in slots))

    def test_max_six_and_invalid_modes(self):
        raw = [{'hkl':hkl_string(0x0419+i), 'mode':'bogus','name':'X'*80}
               for i in range(10)]
        slots = sanitized_slots(raw)
        self.assertEqual(len(slots), 6)
        self.assertTrue(all(slot['mode']=='default' for slot in slots))
        self.assertTrue(all(len(slot['name']) == 32 for slot in slots))

    def test_invalid_format_ignored(self):
        self.assertEqual(sanitized_slots('junk'), [])
        self.assertEqual(sanitized_slots([{'hkl':'pizza'}]), [])
        self.assertEqual(sanitized_slots([{'hkl':'999999999999999999999'}]), [])


if __name__ == '__main__':
    unittest.main()
