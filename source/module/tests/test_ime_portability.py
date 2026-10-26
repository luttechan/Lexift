import ctypes,json,subprocess,time,unittest
from pathlib import Path
from unittest.mock import patch
from PySide6.QtCore import QProcess
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from ime_query_client import QueryClient,encode_text
from ime_inline import host_path

def wait_for(predicate,seconds=12):
    until=time.monotonic()+seconds
    while time.monotonic()<until:
        if predicate():return True
        QTest.qWait(10)
    return bool(predicate())

class IMEPortabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.qt=QApplication.instance() or QApplication([])

    def test_startup_desktop_failure_retries_on_hidden_shared_desktop(self):
        client=QueryClient(host_path());client.request('야마토');errors=[];client.failed.connect(errors.append)
        client._finished(7,QProcess.ExitStatus.NormalExit)
        self.assertFalse(client.closed);self.assertTrue(client.restart_timer.isActive())
        self.assertIn('--shared-desktop',client.process.arguments())
        self.assertEqual(client.pending[1],'야마토');self.assertFalse(errors);client.stop()

    def test_repeated_engine_failure_has_a_bounded_retry_and_logged_exit_code(self):
        client=QueryClient(host_path());errors=[];client.failed.connect(errors.append)
        with self.assertLogs(level='WARNING') as records:
            for _ in range(3):client._finished(-1073741819,QProcess.ExitStatus.CrashExit)
        self.assertEqual(len(errors),1);self.assertIn('C0000005',errors[0])
        self.assertTrue(client.closed);self.assertFalse(client.restart_timer.isActive())
        self.assertIn('code=0xC0000005',' '.join(records.output))

    def test_explicit_off_cancels_a_queued_engine_restart(self):
        client=QueryClient(host_path());client._finished(7);client.stop()
        with patch.object(client.process,'start') as start:client._restart();start.assert_not_called()

    def test_private_profile_miss_gets_one_shared_desktop_attempt(self):
        client=QueryClient(host_path());errors=[];client.failed.connect(errors.append)
        client._finished(3);self.assertTrue(client.shared_desktop);self.assertFalse(errors)
        client._finished(3);self.assertEqual(len(errors),1);self.assertTrue(client.closed)

    def test_actual_killed_helper_recovers_latest_word_without_a_failure_notice(self):
        client=QueryClient(host_path());responses=[];errors=[]
        client.result.connect(lambda serial,data:responses.append(data));client.failed.connect(errors.append)
        client.start();self.assertTrue(wait_for(lambda:client.ready))
        first=client.process.processId();client.request('와타시');client.process.kill()
        client.request('야마토')
        self.assertTrue(wait_for(lambda:errors or any('大和' in d.get('candidates',[]) for d in responses)))
        self.assertFalse(errors);self.assertNotEqual(first,client.process.processId());client.stop();QTest.qWait(200)

    def test_loaded_hkl_cache_is_not_required_and_shared_host_keeps_user_focus(self):
        user32=ctypes.windll.user32;user32.GetForegroundWindow.restype=ctypes.c_void_p
        user32.GetKeyboardLayout.restype=ctypes.c_void_p
        before=user32.GetForegroundWindow();thread=user32.GetWindowThreadProcessId(ctypes.c_void_p(before),None)
        layout=user32.GetKeyboardLayout(thread)
        client=QueryClient(host_path());client.process.setArguments(['--query-server','--shared-desktop','--diagnostic-ignore-layout-cache'])
        data=[];errors=[];client.result.connect(lambda serial,value:data.append(value));client.failed.connect(errors.append)
        try:
            client.start();client.request('야마토')
            self.assertTrue(wait_for(lambda:errors or any('大和' in d.get('candidates',[]) for d in data)))
            self.assertFalse(errors);self.assertEqual(user32.GetForegroundWindow(),before)
            self.assertEqual(user32.GetKeyboardLayout(thread),layout)
        finally:client.stop();QTest.qWait(200)

    def test_maximum_unicode_frame_returns_error_without_terminating_the_engine(self):
        client=QueryClient(host_path());data=[];errors=[]
        client.result.connect(lambda serial,value:data.append(value));client.failed.connect(errors.append)
        client.start();client.request('🙂'*4096)
        try:
            self.assertTrue(wait_for(lambda:data or errors));self.assertFalse(errors)
            self.assertIn('error',data[-1]);data.clear();client.request('야마토')
            self.assertTrue(wait_for(lambda:errors or any('大和' in d.get('candidates',[]) for d in data)))
            self.assertFalse(errors);self.assertEqual(client.recoveries,0)
        finally:client.stop();QTest.qWait(200)

    def test_private_host_also_starts_without_the_loaded_layout_cache(self):
        client=QueryClient(host_path());client.process.setArguments(['--query-server','--diagnostic-ignore-layout-cache'])
        data=[];errors=[];client.result.connect(lambda serial,value:data.append(value));client.failed.connect(errors.append)
        try:
            client.start();client.request('야마토')
            self.assertTrue(wait_for(lambda:errors or any('大和' in d.get('candidates',[]) for d in data)))
            self.assertFalse(errors)
        finally:client.stop();QTest.qWait(200)
