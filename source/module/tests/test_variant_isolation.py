import socket,unittest
from unittest.mock import Mock,patch
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QCoreApplication,QEvent
from ime_inline import InlineMode
from hotkeys_windows import HotkeyBinding,HotkeyGroup
import isolated_hotkeys as hooks

class VariantIsolationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.qt=QApplication.instance() or QApplication([])
    def tearDown(self):QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete);self.qt.processEvents()
    def test_same_client_cannot_deliver_an_old_output_profile_into_new_cache(self):
        mode=InlineMode();mode.enabled=True;mode.language='zh_tw';mode.cache=mode.caches['zh_tw'];mode.query=object()
        mode.snapshot={'source':'니하오','hwnd':1}
        raw=dict(source='니하오',kana='ni hao',candidates=['你好'],readings=['ni hao'])
        with patch.object(mode,'_show') as show:
            mode._queried(mode.query,raw);show.assert_not_called()
            tw=dict(raw,output_mode='zh_tw');mode._queried(mode.query,tw)
            show.assert_called_once_with(tw);self.assertEqual(mode.caches['zh_tw']['니하오'],tw)
            self.assertEqual(mode.caches['zh'],{})
            show.reset_mock();mode.language='zh_bopomofo';mode.cache=mode.caches['zh_bopomofo']
            mode._queried(mode.query,tw);show.assert_not_called();self.assertEqual(mode.cache,{})
        mode.query=None;mode.deleteLater()
    def test_traditional_and_bopomofo_prepare_only_one_dictionary_worker(self):
        mode=InlineMode();mode.overlay=Mock()
        with patch('chinese_query_client.ChineseQueryClient') as constructor:
            mode.prepare('zh_tw');mode.prepare('zh_bopomofo');mode.prepare('zh')
            constructor.assert_called_once_with(mode)
            constructor.return_value.start.assert_called_once()
        mode.query=None;mode.engines.clear();mode.overlay=None;mode.deleteLater()
    def test_fourth_ipc_event_and_cycle_key_survive_disabling_other_features(self):
        callback=Mock();worker=hooks.HookService();first,second=socket.socketpair()
        worker.connection=second;worker.caps=hooks.CapsQHook(None,on_traditional=callback)
        try:
            first.sendall(b'{"event":"traditional","hwnd":123}\n');first.shutdown(socket.SHUT_WR)
            worker._read(second);callback.assert_called_once_with(123)
        finally:worker.connection=None;first.close();second.close();worker.close()
        for keys in ('T','AT','QCT','QACT'):
            with patch('hotkeys_windows.CapsQHook') as native:
                group=HotkeyGroup([(HotkeyBinding('caps',key),Mock()) for key in keys],cycle_binding=HotkeyBinding('caps','T'))
                self.assertEqual(len(group.hooks),1);self.assertEqual(native.call_args.kwargs['cycle_key'],'T')
