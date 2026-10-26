import json,unittest
from unittest.mock import Mock,patch
from PySide6.QtWidgets import QApplication
from ime_inline import InlineMode
import update_core

class InputRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.qt=QApplication.instance() or QApplication([])
    def setUp(self):self.mode=InlineMode();self.mode.enabled=True
    def tearDown(self):
        self.mode.watcher=None;self.mode.query=None;self.mode.engines.clear();self.mode.close()
    def test_watcher_exit_keeps_on_and_schedules_recovery(self):
        process=Mock();self.mode.watcher=process;self.mode._watcher_stopped(process)
        self.assertTrue(self.mode.enabled);self.assertTrue(self.mode.watcher_retry.isActive())
    def test_query_failure_does_not_stop_input_detection(self):
        client=Mock();watcher=Mock();self.mode.watcher=watcher
        self.mode.query=client;self.mode.engines['ja']=client
        self.mode._client_failed('ja',client,'temporary')
        self.assertTrue(self.mode.enabled);self.assertIs(self.mode.watcher,watcher)
        self.assertTrue(self.mode.query_retry.isActive());watcher.kill.assert_not_called()
    def test_stale_query_failure_cannot_drop_new_engine(self):
        old=Mock();new=Mock();self.mode.engines['ja']=new;self.mode.query=new
        self.mode._client_failed('ja',old,'stale')
        self.assertIs(self.mode.query,new);self.assertIs(self.mode.engines['ja'],new)
    def test_commit_timeout_drops_work_without_replaying_or_turning_off(self):
        self.mode.watcher=Mock();self.mode.pending_commit={'serial':3}
        self.mode._commit_timeout()
        self.assertTrue(self.mode.enabled);self.assertIsNone(self.mode.pending_commit)
        self.assertIsNone(self.mode.watcher);self.assertTrue(self.mode.watcher_retry.isActive())
    def test_explicit_off_cancels_every_recovery_timer(self):
        self.mode.watcher_retry.start(500);self.mode.query_retry.start(500);self.mode.watcher_health.start()
        self.mode.close();self.assertFalse(self.mode.enabled)
        self.assertFalse(any(t.isActive() for t in (self.mode.watcher_retry,self.mode.query_retry,self.mode.watcher_health)))
        with patch.object(self.mode,'prepare') as prepare:self.mode._restore_query();prepare.assert_not_called()
    def test_heartbeat_preserves_current_snapshot(self):
        process=Mock();self.mode.watcher=process;self.mode.snapshot={'serial':4,'source':'니하오'}
        process.readAllStandardOutput.return_value=b'{"event":"heartbeat","uia":false}\n'
        self.mode._read(process)
        self.assertEqual(self.mode.snapshot['serial'],4);self.assertTrue(self.mode.watcher_health.isActive())
    def test_retry_backoff_is_bounded_and_warning_not_repeated(self):
        events=[];self.mode.failed.connect(events.append)
        for _ in range(50):self.mode._engine_failed('temporary')
        self.assertEqual(self.mode.watcher_retry.interval(),30000);self.assertEqual(events,['temporary'])
    def test_beta_version_is_preserved_and_stable_upgrade_remains_possible(self):
        self.assertEqual(update_core.version_text('v1.0.4b'),'1.0.4b')
        self.assertGreater(update_core.version_key('1.0.4b'),update_core.version_key('1.0.3'))
        self.assertGreater(update_core.version_key('1.0.4'),update_core.version_key('1.0.4b'))
