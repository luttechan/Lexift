"""Latency changes must retain cancellation, privacy and page state."""
import unittest
from unittest.mock import Mock,patch
from PySide6.QtWidgets import QApplication
from ime_inline import InlineMode
from ime_query_client import QueryClient
from tests import test_startup_lazy_pages as startup_pages


class LatencyLifecycleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qt=QApplication.instance() or QApplication([])

    def test_prepare_warms_engines_without_input_watcher_or_popup(self):
        mode=InlineMode();japanese,chinese=Mock(),Mock()
        with patch('ime_query_client.QueryClient',return_value=japanese), \
             patch('chinese_query_client.ChineseQueryClient',return_value=chinese):
            mode.prepare();mode.prepare()
            self.assertIsNone(mode.watcher);self.assertFalse(mode.enabled);self.assertFalse(mode.visible())
            japanese.start.assert_called_once();chinese.start.assert_called_once()
            japanese.request.assert_called_once_with('와타시')
            mode.shutdown()
            japanese.stop.assert_called_once();chinese.stop.assert_called_once()
        mode.overlay.deleteLater()

    def test_cancel_invalidates_old_japanese_request_without_killing_engine(self):
        client=QueryClient('unused')
        client.ready=True;client.pending=(5,'니혼고');client.serial=5
        client.cancel()
        self.assertIsNone(client.pending);self.assertGreater(client.serial,5)
        self.assertFalse(client.closed);self.assertFalse(client.timer.isActive())
        client.stop();client.deleteLater()

    def test_same_pending_reading_does_not_restart_native_conversion(self):
        client=QueryClient('unused');client.ready=True
        with patch.object(client,'_send') as send:
            first=client.request('와타시');second=client.request('와타시')
            self.assertEqual(first,second);send.assert_called_once()
        client.stop();client.deleteLater()

    def test_inactive_warmup_result_never_shows_candidate(self):
        mode=InlineMode();mode.prepare=Mock()
        client=Mock();mode.engines['ja']=client
        with patch.object(mode,'_show') as show:
            mode._queried(client,{'source':'와타시','candidates':['私']})
            show.assert_not_called()
        mode.shutdown()

    def test_emoji_and_cjk_font_runs_disable_unbounded_font_fallback(self):
        from candidate_delegate import CandidateDelegate
        from PySide6.QtGui import QFont
        delegate=CandidateDelegate()
        text='学校🏫㈻'
        runs=delegate.formats(text)
        self.assertEqual(sum(run.length for run in runs),len(text.encode('utf-16-le'))//2)
        self.assertTrue(all(run.format.font().styleStrategy()&QFont.StyleStrategy.NoFontMerging for run in runs))
        emoji_index=delegate.font_index('🏫')
        self.assertTrue(delegate.raw[emoji_index].supportsCharacter(ord('🏫')))


class PreferencesWarmupTests(unittest.TestCase):
    setUp= startup_pages.StartupPageTests.setUp
    tearDown= startup_pages.StartupPageTests.tearDown

    @classmethod
    def setUpClass(cls):
        cls.qt=QApplication.instance() or QApplication([])
        cls.qt.setQuitOnLastWindowClosed(False)

    def test_prepare_does_not_change_page_or_saved_settings(self):
        before=dict((key,self.store.value(key)) for key in self.store.allKeys())
        self.window._prepare_preferences()
        self.assertEqual(self.window.pages.currentIndex(),0)
        self.assertEqual(before,dict((key,self.store.value(key)) for key in self.store.allKeys()))
        prepared=self.window.pages.widget(2)
        with patch.object(self.window,'_make_preferences',side_effect=AssertionError('rebuilt on click')):
            self.window.navigate(2)
        self.assertIs(prepared,self.window.pages.widget(2))

    def test_idle_page_preparation_does_not_rasterize_hidden_scroll_pages(self):
        self.window._ensure_page(2)
        with patch.object(self.window.pages.widget(2),'grab') as grab:
            self.window._prepare_preferences()
        grab.assert_not_called()
        self.window._prepare_next_page()
        self.assertIn(3,self.window._ready_pages)
