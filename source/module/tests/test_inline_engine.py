import json
from pathlib import Path
import time
import unittest
from unittest.mock import Mock, patch
from PySide6.QtCore import QProcess
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from ime_query_client import QueryClient, encode_text
from ime_inline import InlineMode, host_path


def wait_until(condition, seconds=7):
    end=time.monotonic()+seconds
    while time.monotonic()<end:
        QApplication.processEvents()
        if condition(): return True
        QTest.qWait(10)
    return False


class InlineEngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qt=QApplication.instance() or QApplication([])
        cls.qt.setQuitOnLastWindowClosed(False)

    def test_utf16_protocol_preserves_hangul_and_surrogates(self):
        value='와타시 ☕ 🏫'
        encoded=encode_text(value)
        restored=b''.join(int(encoded[i:i+4],16).to_bytes(2,'little') for i in range(0,len(encoded),4)).decode('utf-16-le')
        self.assertEqual(restored,value)

    def test_real_engine_keeps_only_latest_request_and_reuses_process(self):
        client=QueryClient(host_path())
        responses=[];failures=[]
        client.result.connect(lambda serial,data:responses.append((serial,data)) if not data.get('partial') else None)
        client.failed.connect(failures.append)
        client.start()
        # Submit before warmup, then change input while the old query is live.
        client.request('와타시')
        self.assertTrue(wait_until(lambda:client.ready))
        pid=client.process.processId()
        QTest.qWait(20)
        final=client.request('갓코우')
        self.assertTrue(wait_until(lambda:responses or failures))
        self.assertFalse(failures)
        self.assertEqual([item[0] for item in responses],[final])
        self.assertIn('学校',responses[-1][1]['candidates'])
        final=client.request('니혼고')
        self.assertTrue(wait_until(lambda:len(responses)==2))
        self.assertEqual(client.process.processId(),pid)
        self.assertIn('日本語',responses[-1][1]['candidates'])
        client.stop()
        self.assertTrue(wait_until(lambda:client.closed,1))
        QTest.qWait(200)

    def test_inline_suppresses_results_for_changed_input(self):
        mode=InlineMode();mode.enabled=True
        mode.query=Mock();mode.snapshot={'source':'니혼고','serial':4}
        with patch.object(mode,'_show') as show:
            mode._queried(mode.query,{'source':'와타시','kana':'わたし','candidates':['私']})
            show.assert_not_called()
            mode._queried(mode.query,{'source':'니혼고','kana':'にほんご','candidates':['日本語']})
            show.assert_called_once()
        mode.close()

    def test_partial_query_keeps_request_pending_until_final_response(self):
        client=QueryClient(host_path());client.ready=True;client.serial=7;client.pending=(7,'치지마리마스')
        received=[];client.result.connect(lambda serial,data:received.append(data))
        partial={'id':7,'source':'치지마리마스','partial':True,'candidates':['縮まります']}
        with patch.object(client.process,'readAllStandardOutput',return_value=(json.dumps(partial)+'\n').encode()):
            client._read()
        self.assertEqual(client.pending,(7,'치지마리마스'))
        self.assertTrue(client.timer.isActive())
        final=dict(partial,partial=False)
        with patch.object(client.process,'readAllStandardOutput',return_value=(json.dumps(final)+'\n').encode()):client._read()
        self.assertIsNone(client.pending);self.assertFalse(client.timer.isActive())
        self.assertEqual(len(received),2);client.stop()

    def test_partial_candidates_are_shown_but_never_cached_as_complete(self):
        mode=InlineMode();mode.enabled=True;mode.query=Mock()
        mode.snapshot={'source':'치지마리마스','serial':4}
        partial={'source':'치지마리마스','kana':'ちじまります','candidates':['縮まります'],'partial':True}
        with patch.object(mode,'_show') as show:
            mode._queried(mode.query,partial);show.assert_called_once()
            self.assertNotIn('치지마리마스',mode.cache)
            mode._queried(mode.query,dict(partial,partial=False))
            self.assertIn('치지마리마스',mode.cache)
        mode.close()

    def test_real_ime_queries_alternate_spellings_and_preserves_sentence_suffix(self):
        client=QueryClient(host_path());responses=[];failures=[]
        client.result.connect(lambda serial,data:responses.append(data))
        client.failed.connect(failures.append);client.start()
        cases={'치지마리마스':'縮まります','치지마리마시타':'縮まりました',
               '오-키이':'大きい','오네-상':'お姉さん','쯔키':'月',
               '와타시와가쿠세이데스':'私は学生です','코-죠-':'工場',
               '고치소-사마':'ご馳走様','니혼고오벤쿄-시마스':'日本語を勉強します',
               '도쿄에이키마스':'東京へ行きます','미카즈키':'三日月'}
        try:
            for source,expected in cases.items():
                with self.subTest(source=source):
                    responses.clear();client.request(source)
                    self.assertTrue(wait_until(lambda:failures or any(not r.get('partial') for r in responses),12))
                    self.assertFalse(failures)
                    final=responses[-1];self.assertIn(expected,final['candidates'])
                    self.assertEqual(final['queried_readings'],len(final['kana_variants']))
                    self.assertEqual(len(final['candidates']),len(final['readings']))
                    self.assertTrue(all(reading in final['kana_variants'] for reading in final['readings']))
                    if source=='치지마리마스':
                        self.assertFalse(any('まり' in s and s.count('まり')>1 for s in final['candidates']))
                    if source=='와타시와가쿠세이데스':
                        self.assertNotIn('私',final['candidates'])
        finally:
            client.stop();QTest.qWait(200)

    def test_escaped_candidates_do_not_reappear_from_late_reply(self):
        mode=InlineMode();mode.enabled=True;mode._build()
        mode.snapshot={'source':'와타시','serial':4,'hwnd':100}
        mode.dismissed=4
        with patch('ime_windows.user32.GetForegroundWindow',return_value=100):
            mode._show({'kana':'わたし','candidates':['私']})
        self.assertFalse(mode.visible())
        mode.close();mode.overlay.deleteLater()

    def test_focus_change_hides_popup_and_refuses_replacement(self):
        mode=InlineMode();mode.enabled=True;mode._build()
        mode.snapshot={'source':'와타시','serial':4,'hwnd':100}
        mode.watcher=Mock()
        mode.list.addItem('私');mode.list.setCurrentRow(0)
        mode.overlay.show()
        with patch('ime_windows.user32.GetForegroundWindow',return_value=200):
            mode.commit()
        mode.watcher.write.assert_not_called()
        self.assertFalse(mode.visible())
        mode.watcher=None;mode.close();mode.overlay.deleteLater()

    def test_old_watcher_finish_cannot_turn_off_reenabled_mode(self):
        mode=InlineMode();mode.enabled=True
        old=Mock();current=Mock();mode.watcher=current
        mode._watcher_stopped(old)
        self.assertTrue(mode.enabled)
        self.assertIs(mode.watcher,current)
        mode.watcher=None;mode.close()

    def test_stale_watcher_data_is_not_consumed(self):
        mode=InlineMode();current=Mock();old=Mock();mode.watcher=current
        mode._read(old)
        old.readAllStandardOutput.assert_not_called()
        mode.watcher=None;mode.close()

    def test_long_sentence_selection_survives_geometry_refresh_and_space(self):
        mode=InlineMode();mode.enabled=True;mode._build();mode.watcher=Mock()
        mode.snapshot={'source':'모요-데스','serial':7,'hwnd':100,'x':50,'y':50}
        data={'kana':'もようです','candidates':['もようです','模様です']}
        with patch('ime_windows.user32.GetForegroundWindow',return_value=100):
            mode._show(data);mode.list.setCurrentRow(1)
            mode.snapshot=dict(mode.snapshot,serial=8,x=60)
            mode._show(data)
            self.assertEqual(mode.list.currentItem().text(),'模様です')
            mode.navigate(0x20)
        mode.watcher.write.assert_called_once_with(f'REPLACE 8 {encode_text("模様です")}\n'.encode())
        mode.watcher=None;mode.close();mode.overlay.deleteLater()

    def test_changed_source_does_not_inherit_previous_sentence_selection(self):
        mode=InlineMode();mode.enabled=True;mode._build()
        mode.snapshot={'source':'모요-데스','serial':7,'hwnd':100,'x':50,'y':50}
        data={'kana':'もようです','candidates':['もようです','模様です']}
        with patch('ime_windows.user32.GetForegroundWindow',return_value=100):
            mode._show(data);mode.list.setCurrentRow(1)
            mode.snapshot=dict(mode.snapshot,source='모요-',serial=8)
            mode._show(data)
            self.assertEqual(mode.list.currentRow(),0)
        mode.close();mode.overlay.deleteLater()

    def test_space_commits_selected_candidate_without_inserting_space(self):
        mode=InlineMode();mode.enabled=True;mode._build();mode.watcher=Mock()
        mode.snapshot={'source':'와타시','serial':9,'hwnd':100}
        mode.list.addItems(['わたし','私']);mode.list.setCurrentRow(1);mode.overlay.show()
        with patch('ime_windows.user32.GetForegroundWindow',return_value=100):mode.navigate(0x20)
        mode.watcher.write.assert_called_once_with(b'REPLACE 9 79c1\n')
        self.assertFalse(mode.visible());self.assertEqual(mode.dismissed,9)
        mode.watcher=None;mode.close();mode.overlay.deleteLater()

    def test_number_keys_commit_matching_row_without_number_prefix(self):
        for key,row in ((0x31,0),(0x32,1),(0x39,8),(0x30,9),(0x61,0),(0x69,8),(0x60,9)):
            with self.subTest(key=key):
                mode=InlineMode();mode.enabled=True;mode._build();mode.watcher=Mock()
                mode.snapshot={'source':'와타시','serial':9,'hwnd':100}
                words=['私','渡し','わたし','ワタシ','亘','渡','綿','和足','和多志','私達']
                mode.list.addItems(words);mode.overlay.show()
                with patch('ime_windows.user32.GetForegroundWindow',return_value=100):mode.navigate(key)
                expected=encode_text(words[row])
                mode.watcher.write.assert_called_once_with(f'REPLACE 9 {expected}\n'.encode())
                self.assertFalse(mode.visible())
                mode.watcher=None;mode.close();mode.overlay.deleteLater()

    def test_missing_number_row_and_hidden_popup_do_not_commit(self):
        mode=InlineMode();mode.enabled=True;mode._build();mode.watcher=Mock()
        mode.snapshot={'source':'와타시','serial':9,'hwnd':100}
        mode.list.addItem('私');mode.list.setCurrentRow(0);mode.overlay.show()
        with patch('ime_windows.user32.GetForegroundWindow',return_value=100):
            mode.navigate(0x39);mode.watcher.write.assert_not_called()
            self.assertEqual(mode.list.currentRow(),0)
            mode._hide();mode.navigate(0x31);mode.watcher.write.assert_not_called()
        mode.watcher=None;mode.close();mode.overlay.deleteLater()

    def test_input_burst_renders_and_queries_only_latest_snapshot(self):
        mode=InlineMode();mode.enabled=True;mode.watcher=process=Mock();mode.query=Mock()
        rows=[{'event':'input','source':text,'serial':i,'kana':'わ','kana_variants':['わ']} for i,text in enumerate(['와','와타','와타시'])]
        process.readAllStandardOutput.return_value=('\n'.join(map(json.dumps,rows))+'\n').encode()
        with patch.object(mode,'_show') as show:
            mode._read(process);show.assert_called_once()
            self.assertEqual(mode.snapshot['source'],'와타시')
            mode._search();mode.query.request.assert_called_once_with('와타시')
        mode.watcher=None;mode.close()

    def test_cached_reply_survives_mode_off_and_language_caches_are_separate(self):
        mode=InlineMode();mode.cache['와타시']={'candidates':['私']}
        mode.close()
        self.assertIn('와타시',mode.caches['ja']);self.assertNotIn('와타시',mode.caches['zh'])
        mode.shutdown();self.assertFalse(mode.caches['ja'])

    def test_native_reading_preview_is_shown_before_async_ime_request(self):
        mode=InlineMode();mode.enabled=True;mode.query=Mock()
        mode.watcher=process=Mock()
        data={'event':'input','source':'모노즈쿠리','kana':'ものづくり',
              'kana_variants':['ものづくり','ものずくり'],'serial':7}
        process.readAllStandardOutput.return_value=(json.dumps(data)+'\n').encode()
        with patch.object(mode,'_show') as show:
            mode._read(process)
            self.assertTrue(show.call_args.args[0]['preview'])
            self.assertEqual(show.call_args.args[0]['candidates'],data['kana_variants'])
            mode.query.request.assert_not_called()
            mode._search()
            mode.query.request.assert_called_once_with('모노즈쿠리')
        mode.watcher=None;mode.close()
