import unittest
from unittest.mock import patch
from PySide6.QtWidgets import QApplication
from chinese_query_client import ChineseQueryClient,SearchThread
from chinese_reading import ChineseEngine

class CandidateDeliveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.qt=QApplication.instance() or QApplication([])
    def test_identical_pending_requests_cannot_starve_the_result(self):
        client=ChineseQueryClient();results=[];client.result.connect(lambda serial,data:results.append(data))
        with patch.object(client.thread,'submit') as submit:
            serial=client.request('니츠판러마')
            for _ in range(1000):self.assertEqual(client.request('니츠판러마'),serial)
            submit.assert_called_once()
        client._result(serial,dict(source='니츠판러마',candidates=['你吃饭了吗']))
        self.assertEqual(results[0]['candidates'],['你吃饭了吗']);client.stop();client.deleteLater()
    def test_changed_text_and_output_mode_still_replace_pending_requests(self):
        client=ChineseQueryClient()
        with patch.object(client.thread,'submit') as submit:
            first=client.request('니츠판');second=client.request('니츠판러');third=client.request('니츠판러','zh_tw')
            self.assertLess(first,second);self.assertLess(second,third);self.assertEqual(submit.call_count,3)
        client.stop();client.deleteLater()
    def test_failed_word_does_not_turn_off_or_destroy_the_shared_engine(self):
        from ime_inline import InlineMode
        mode=InlineMode();mode.enabled=True;mode.language='zh';client=object();mode.query=client
        mode._queried(client,dict(source='니츠판러',output_mode='zh',error='temporary search error'))
        self.assertTrue(mode.enabled);self.assertIs(mode.query,client)
        mode.query=None;mode.close()
    def test_reported_phrase_prefixes_keep_hanzi(self):
        engine=ChineseEngine()
        try:
            for text,expected in [('니츠판','你吃饭'),('니츠판러','你吃饭了'),('니츠판러마','你吃饭了吗')]:
                self.assertIn(expected,engine.query(text)['candidates'])
        finally:engine.close()
    def test_geometry_refresh_does_not_replace_delivered_hanzi_with_kana_preview(self):
        import json
        from unittest.mock import Mock
        from ime_inline import InlineMode
        mode=InlineMode();mode.enabled=True;mode.query=Mock();watcher=Mock();mode.watcher=watcher
        mode.last_query={'data':dict(source='야마토',kana='やまと',candidates=['大和'],partial=True)}
        watcher.readAllStandardOutput.return_value=(json.dumps(dict(event='input',source='야마토',serial=3,hwnd=42,kana='やまと'))+'\n').encode()
        with patch.object(mode,'_show') as show:
            mode._read(watcher);self.assertEqual(show.call_args.args[0]['candidates'],['大和'])
        mode.watcher=None;mode.close()
    def test_one_bad_search_does_not_terminate_the_dictionary_thread(self):
        from unittest.mock import Mock
        from PySide6.QtCore import Qt
        engine=Mock();engine.query.side_effect=[ValueError('transient'),dict(source='니츠판러마',candidates=['你吃饭了吗'])]
        profiles=Mock();profiles.transform.side_effect=lambda data,mode:data
        thread=SearchThread();results=[]
        def receive(serial,data):
            results.append(data)
            if serial==1:thread.submit(2,'니츠판러마')
            else:thread.finish()
        thread.result.connect(receive,Qt.ConnectionType.DirectConnection);thread.submit(1,'니츠판러')
        with patch('chinese_reading.ChineseEngine',return_value=engine),patch('chinese_variants.OutputProfiles',return_value=profiles):thread.run()
        self.assertIn('error',results[0]);self.assertEqual(results[1]['candidates'],['你吃饭了吗'])
        engine.close.assert_called_once();thread.deleteLater()
