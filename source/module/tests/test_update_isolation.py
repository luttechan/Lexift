import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from PySide6.QtCore import QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from update_core import UpdateCancelled, UpdateError
from update_network import isolated_request, run_network_job, worker_command


class IsolationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qt = QApplication.instance() or QApplication([])

    def fixture_command(self, request):
        script = (
            'import time,json,os;from pathlib import Path;'
            'end=time.monotonic()+.4;'
            '\nwhile time.monotonic()<end: pass\n'
            f'Path({str(request.parent / "result.json")!r}).write_text(json.dumps({{"pid":os.getpid()}}))'
        )
        return [sys.executable, '-c', script]

    def test_busy_child_keeps_qt_timer_running_and_is_a_different_process(self):
        with tempfile.TemporaryDirectory() as directory:
            values, failures, beats = [], [], []
            timer = QTimer()
            timer.timeout.connect(lambda: beats.append(time.monotonic()))
            timer.start(10)
            def work():
                try:
                    values.append(isolated_request(Path(directory), 'check', threading.Event()))
                except Exception as error:
                    failures.append(error)
            with patch('update_network.worker_command', side_effect=self.fixture_command):
                thread = threading.Thread(target=work)
                thread.start()
                while thread.is_alive():
                    QTest.qWait(10)
                thread.join()
            timer.stop()
            self.assertFalse(failures)
            self.assertNotEqual(values[0]['pid'], os.getpid())
            self.assertGreater(len(beats), 10)

    def test_cancel_terminates_worker_before_returning(self):
        with tempfile.TemporaryDirectory() as directory:
            cancellation = threading.Event()
            timer = threading.Timer(.15, cancellation.set)
            start = time.monotonic()
            with patch('update_network.worker_command', return_value=[sys.executable, '-c', 'import time;time.sleep(30)']):
                timer.start()
                try:
                    with self.assertRaises(UpdateCancelled):
                        isolated_request(Path(directory), 'check', cancellation)
                finally:
                    timer.cancel()
            self.assertLess(time.monotonic()-start, 3)

    def test_network_mode_cannot_use_arbitrary_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            request = Path(directory)/'network.json'
            request.write_text('{}')
            with self.assertRaises(UpdateError):
                run_network_job(request)

    def test_packaged_worker_uses_single_process_app_entry(self):
        with patch.object(sys, 'frozen', True, create=True):
            self.assertEqual(worker_command(Path('network.json')),
                             [sys.executable, '--network-job', 'network.json'])
