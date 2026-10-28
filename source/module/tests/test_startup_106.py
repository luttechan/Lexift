import threading
import unittest
from unittest.mock import patch
import update_apply as apply
from i18n import text_font_family


class Startup106Tests(unittest.TestCase):
    def setUp(self):
        self.argv=patch.object(apply.sys,'argv',['Lexift.exe','--update-job','job.json']);self.argv.start();self.addCleanup(self.argv.stop)
        self.frozen=patch.object(apply.sys,'frozen',True,create=True);self.frozen.start();self.addCleanup(self.frozen.stop)
        apply._ready_pending=False;apply._ready_done=None

    def test_slow_validation_does_not_block_caller_or_run_twice(self):
        started=threading.Event();release=threading.Event()
        def slow(version):
            started.set();release.wait(5);return True
        with patch.object(apply,'mark_ready',side_effect=slow) as mark:
            worker=apply.schedule_ready('1.0.6')
            try:
                self.assertTrue(started.wait(2))
                self.assertTrue(worker.is_alive())
                self.assertIsNone(apply.schedule_ready('1.0.6'))
            finally:release.set();worker.join(3)
            self.assertFalse(worker.is_alive());self.assertEqual(mark.call_count,1)
            self.assertIsNone(apply.schedule_ready('1.0.6'));self.assertEqual(mark.call_count,1)

    def test_failed_validation_does_not_cache_success(self):
        with patch.object(apply,'mark_ready',return_value=False) as mark:
            apply.schedule_ready('1.0.6').join(3)
            apply.schedule_ready('1.0.6').join(3)
        self.assertEqual(mark.call_count,2);self.assertIsNone(apply._ready_done)

    def test_normal_start_does_not_create_a_validation_thread(self):
        with patch.object(apply.sys,'argv',['Lexift.exe']),patch.object(apply.threading,'Thread') as worker:
            self.assertIsNone(apply.schedule_ready('1.0.6'));worker.assert_not_called()

    def test_worker_creation_failure_can_be_retried(self):
        with patch.object(apply.threading.Thread,'start',side_effect=RuntimeError('failed')):
            with self.assertRaises(RuntimeError):apply.schedule_ready('1.0.6')
        self.assertFalse(apply._ready_pending)

    def test_pinyin_uses_a_font_with_extended_latin_glyphs(self):
        self.assertEqual(text_font_family('ke → kě'), 'Segoe UI')
        self.assertEqual(text_font_family('nǚ lǜ'), 'Segoe UI')
        self.assertEqual(text_font_family('한국어'), 'Malgun Gothic')
        self.assertEqual(text_font_family('わたし'), 'Yu Gothic UI')

    def test_korean_profile_name_does_not_inherit_japanese_ui_font(self):
        import app
        from i18n import language,set_language
        from PySide6.QtWidgets import QApplication,QLabel
        qt=QApplication.instance() or QApplication([])
        previous=language();set_language('ja')
        try:
            widget=QLabel('한국어');app.apply_text_font(widget,widget.text())
            self.assertIn('Malgun Gothic',widget.styleSheet())
            widget.deleteLater()
        finally:set_language(previous)
