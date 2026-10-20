import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from PySide6.QtCore import QCoreApplication, QEvent, QSettings
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
import app
import isolated_hotkeys
import runtime_stats as stats
from layout_profiles import create_layout


class FakeEvents:
    def __init__(self):
        self.sampled = Mock()


class SamplerTests(unittest.TestCase):
    def test_no_thread_or_reader_until_visible_and_single_worker_reused(self):
        events = FakeEvents()
        reader = Mock()
        reader.read.return_value = (1, 2, 3, 4)
        factory = Mock(return_value=reader)
        sampler = stats.Sampler(events, interval=.01, reader_factory=factory)
        self.assertIsNone(sampler.thread)
        factory.assert_not_called()
        try:
            sampler.set_active(True)
            deadline = time.monotonic() + 1
            while not reader.read.called and time.monotonic() < deadline:
                time.sleep(.002)
            self.assertTrue(reader.read.called)
            worker = sampler.thread
            sampler.set_active(False)
            time.sleep(.02)
            count = reader.read.call_count
            time.sleep(.04)
            self.assertEqual(reader.read.call_count, count)
            sampler.set_active(True)
            self.assertIs(sampler.thread, worker)
            self.assertEqual(factory.call_count, 1)
        finally:
            sampler.close()
            sampler.thread.join(1)
        self.assertFalse(sampler.thread.is_alive())

    def test_only_latest_snapshot_and_one_notification_while_gui_is_busy(self):
        events = FakeEvents()
        counter = []
        def sample():
            counter.append(1)
            return (len(counter), 2, 3, 4)
        sampler = stats.Sampler(events, interval=.001,
                                reader_factory=lambda: Mock(read=sample))
        generation = sampler.set_active(True)
        try:
            deadline = time.monotonic() + 1
            while len(counter) < 25 and time.monotonic() < deadline:
                time.sleep(.002)
            self.assertGreaterEqual(len(counter), 25)
            self.assertEqual(events.sampled.emit.call_count, 1)
            sampler.set_active(False)
            self.assertIsNone(sampler.latest)
            self.assertIsNone(sampler.take(generation))
        finally:
            sampler.close()
            sampler.thread.join(1)

    def test_pausing_or_closing_never_waits_for_a_busy_reader(self):
        events = FakeEvents()
        entered, release = threading.Event(), threading.Event()
        def sample():
            entered.set()
            release.wait(1)
            return 1, 2, 3, 4
        sampler = stats.Sampler(events, reader_factory=lambda: Mock(read=sample))
        sampler.set_active(True)
        try:
            self.assertTrue(entered.wait(1))
            start = time.perf_counter()
            sampler.set_active(False)
            sampler.close()
            self.assertLess(time.perf_counter()-start, .05)
        finally:
            release.set()
            sampler.thread.join(1)
        events.sampled.emit.assert_not_called()

    def test_reader_never_starts_a_keyboard_worker(self):
        with patch.object(isolated_hotkeys, '_shared', None), \
             patch.object(isolated_hotkeys, 'HookService', side_effect=AssertionError('unexpected worker')):
            reader = stats.NativeReader()
            memory, private, worker, uptime = reader.read()
        self.assertGreater(memory, 0)
        self.assertGreater(private, 0)
        self.assertIsNone(worker)
        self.assertGreaterEqual(uptime, 0)


class PanelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qt = QApplication.instance() or QApplication([])
        cls.qt.setQuitOnLastWindowClosed(False)

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        store = QSettings(str(Path(self.directory.name)/'test.ini'), QSettings.Format.IniFormat)
        layout = create_layout(0x0412)
        with patch.object(app, 'available_layouts', return_value=[layout]):
            self.window = app.MainWindow(store, [dict(hkl=layout.hkl, mode='ko_hangul', name='custom')], False)
        self.assertFalse(hasattr(self.window, 'runtime_stats'))
        self.window.resize(1020, 560)
        self.window.navigate(3)
        self.panel = self.window.runtime_stats
        self.assertFalse(self.panel.toggle.isChecked())
        self.assertIsNone(self.panel.details)
        self.sampler = self.panel._sampler
        self.reader = Mock()
        self.reader.read.return_value = (50*1048576, 30*1048576, None, 3661)
        self.sampler.reader_factory = Mock(return_value=self.reader)
        self.sampler.interval = .02
        self.scroll = self.window.pages.widget(3)
        self.panel.toggle.setChecked(True)

    def tearDown(self):
        if self.window is not None:
            self.window.hide()
            self.window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self.sampler.close()
        if self.sampler.thread is not None:
            self.sampler.thread.join(1)
        self.qt.processEvents()
        self.directory.cleanup()

    def bottom(self):
        self.scroll.verticalScrollBar().setValue(self.scroll.verticalScrollBar().maximum())
        for _ in range(15):
            self.qt.processEvents()
            time.sleep(.01)

    def test_samples_only_when_scrolled_into_view_and_stops_on_other_page(self):
        self.window.show()
        QTest.qWait(40)
        self.assertIsNone(self.sampler.thread)
        self.reader.read.assert_not_called()
        self.bottom()
        self.assertTrue(self.sampler.active)
        self.assertEqual(self.panel.values[0].text(), '50.0 MB')
        self.assertEqual(self.panel.values[1].text(), '—')
        self.assertEqual(self.panel.values[3].text(), '01:01:01')
        self.scroll.verticalScrollBar().setValue(0)
        QTest.qWait(30)
        self.assertFalse(self.sampler.active)
        count = self.reader.read.call_count
        QTest.qWait(60)
        self.assertEqual(self.reader.read.call_count, count)
        self.bottom()
        self.window.navigate(0)
        QTest.qWait(30)
        self.assertFalse(self.sampler.active)
        self.assertIsNone(self.panel._watched_window)

    def test_hide_minimize_and_destroy_stop_sampling(self):
        self.window.show()
        self.qt.processEvents()
        self.bottom()
        self.assertTrue(self.sampler.active)
        self.window.showMinimized()
        QTest.qWait(30)
        self.assertFalse(self.sampler.active)
        self.window.showNormal()
        QTest.qWait(40)
        self.window.hide()
        QTest.qWait(20)
        self.assertFalse(self.sampler.active)
        self.window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self.window = None
        self.sampler.thread.join(1)
        self.assertTrue(self.sampler.closed)
        self.assertFalse(self.sampler.thread.is_alive())

    def test_stale_or_hidden_samples_never_change_labels(self):
        before = [value.text() for value in self.panel.values]
        self.panel._on_sample(999, None)
        self.assertEqual([value.text() for value in self.panel.values], before)

    def test_collapse_stops_queries_and_releases_details_until_expanded(self):
        self.window.show()
        self.bottom()
        self.assertTrue(self.sampler.active)
        self.panel.toggle.setChecked(False)
        self.assertFalse(self.sampler.active)
        self.assertIsNone(self.panel.details)
        self.assertEqual(self.panel.values, [])
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        count = self.reader.read.call_count
        time.sleep(.06)
        self.qt.processEvents()
        self.assertEqual(self.reader.read.call_count, count)
        self.panel.toggle.setChecked(True)
        self.bottom()
        self.assertEqual(self.panel.values[0].text(), '50.0 MB')
