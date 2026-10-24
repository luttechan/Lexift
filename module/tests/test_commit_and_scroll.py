import json
import unittest
from unittest.mock import Mock,patch
from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QApplication
from ime_inline import InlineMode

class CommitAndScrollTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qt=QApplication.instance() or QApplication([])

    def setUp(self):
        self.mode=InlineMode();self.mode._build();self.mode.enabled=True
        self.mode.snapshot={'source':'와타시','serial':10,'hwnd':100,'x':100,'y':100}
        self.mode.watcher=Mock()
        self.focus=patch('ime_windows.user32.GetForegroundWindow',return_value=100);self.focus.start()

    def tearDown(self):
        self.mode.watcher=None;self.mode.close();self.mode.overlay.deleteLater();self.focus.stop()

    def feed(self,*rows):
        process=self.mode.watcher
        process.readAllStandardOutput.return_value=('\n'.join(json.dumps(row) for row in rows)+'\n').encode()
        self.mode._read(process)

    def test_double_space_and_duplicate_click_send_one_replace(self):
        self.mode._show({'kana':'わたし','candidates':['私']})
        self.mode.navigate(0x20);self.mode.commit();self.mode.navigate(0x20)
        self.mode.watcher.write.assert_called_once()
        self.assertIsNotNone(self.mode.pending_commit);self.assertFalse(self.mode.visible())

    def test_geometry_and_partial_results_cannot_reopen_pending_commit(self):
        self.mode._show({'kana':'わたし','candidates':['私']});self.mode.commit()
        self.feed(dict(self.mode.snapshot,event='input',serial=11,x=110))
        self.mode._show({'kana':'わたし','candidates':['私','渡し']})
        self.assertFalse(self.mode.visible());self.assertEqual(self.mode.pending_commit['serial'],10)
        self.feed({'event':'replace','serial':10,'success':True})
        self.assertIsNone(self.mode.pending_commit);self.assertFalse(self.mode.commit_timer.isActive())
        self.mode._show({'kana':'わたし','candidates':['私']})
        self.assertFalse(self.mode.visible())

    def test_obsolete_reply_does_not_discard_new_input(self):
        with patch.object(self.mode,'_show') as show:
            self.feed(dict(self.mode.snapshot,event='input',source='니혼고',kana='にほんご',serial=12),
                      {'event':'replace','serial':1,'success':False})
        self.assertEqual(self.mode.snapshot['source'],'니혼고');show.assert_called_once()

    def test_automatic_preview_selection_does_not_scroll_to_middle(self):
        self.mode._show({'kana':'わたし','candidates':['わたし'],'preview':True})
        values=['私','渡し','わたし']+[f'候補{i}' for i in range(30)]
        self.mode._show({'kana':'わたし','candidates':values})
        self.qt.processEvents()
        self.assertEqual(self.mode.list.currentRow(),0)
        self.assertEqual(self.mode.list.verticalScrollBar().value(),0)
        self.assertEqual(self.mode.list.row(self.mode.list.itemAt(QPoint(10,10))),0)

    def test_new_word_resets_previous_scroll_but_explicit_selection_survives_updates(self):
        values=[f'候補{i}' for i in range(30)]
        self.mode._show({'kana':'わたし','candidates':values})
        self.mode.list.setCurrentRow(20)
        self.mode._show({'kana':'わたし','candidates':['追加']+values})
        self.assertEqual(self.mode.list.currentItem().text(),'候補20')
        self.mode.snapshot=dict(self.mode.snapshot,source='니혼고',serial=11)
        self.mode._show({'kana':'にほんご','candidates':values})
        self.qt.processEvents()
        self.assertEqual(self.mode.list.currentRow(),0)
        self.assertEqual(self.mode.list.verticalScrollBar().value(),0)

    def test_unchanged_candidates_do_not_rebuild_the_list(self):
        data={'kana':'わたし','candidates':['私','渡し']};self.mode._show(data)
        with patch.object(self.mode.list,'clear') as clear:
            self.mode._show(data)
        clear.assert_not_called()

    def test_close_releases_pending_guard_and_timer(self):
        self.mode._show({'kana':'わたし','candidates':['私']});self.mode.commit()
        self.mode.close()
        self.assertIsNone(self.mode.pending_commit);self.assertFalse(self.mode.commit_timer.isActive())

    def test_pause_stops_text_polling_and_obsolete_candidate_search(self):
        self.mode.query=Mock()
        self.mode.set_paused(True)
        self.mode.watcher.write.assert_called_with(b'PAUSE 1\n')
        self.mode.query.cancel.assert_called_once()
        self.mode.set_paused(False)
        self.mode.watcher.write.assert_called_with(b'PAUSE 0\n')

    def test_worker_ipc_keeps_target_for_commit_guard(self):
        import isolated_hotkeys
        worker=Mock();proxy=isolated_hotkeys.OverlayNavigationHook(Mock());worker.navigation=proxy
        with patch.object(isolated_hotkeys,'service',return_value=worker):
            proxy.set_active(3,100)
        worker.command.assert_called_once_with('active',wait=False,active=3,target=100)
