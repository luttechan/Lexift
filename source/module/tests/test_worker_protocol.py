import json,subprocess,unittest
from pathlib import Path

class WorkerWireProtocolTests(unittest.TestCase):
    def test_actual_wire_messages_preserve_navigation_mode(self):
        fixture=Path(__file__).with_name('worker_protocol_fixture.exe')
        p=subprocess.run([str(fixture)],capture_output=True,text=True,timeout=10,
                         creationflags=subprocess.CREATE_NO_WINDOW)
        self.assertEqual(p.returncode,0,p.stdout+p.stderr)
        self.assertEqual(json.loads(p.stdout),dict(passed=15,failed=0))

    def test_navigation_packets_drive_a_nonfocus_selector_and_escape_closes_it(self):
        import socket
        from unittest.mock import patch
        from types import SimpleNamespace
        from PySide6.QtCore import Qt,QCoreApplication,QEvent
        from PySide6.QtWidgets import QApplication
        import app
        from isolated_hotkeys import HookService
        from layout_profiles import create_layout
        qt=QApplication.instance() or QApplication([])
        qt.setQuitOnLastWindowClosed(False)
        layout=create_layout(0x412)
        slots=[dict(hkl=layout.hkl,mode='ko_hangul',name=str(n)) for n in range(15)]
        overlay=app.Overlay();overlay.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
        overlay.set_preserve_target_focus(True)
        service=HookService();first,second=socket.socketpair();service.connection=second
        observed=[]
        def navigate(key):
            overlay.navigate_virtual_key(key);observed.append(overlay.index)
        service.navigation=SimpleNamespace(on_key=navigate)
        try:
            with patch.object(app,'available_layouts',return_value=[layout]):overlay.open(slots,0)
            keys=(0x27,0x28,0x25,0x26,0x1b)
            first.sendall(b''.join((json.dumps(dict(event='navigation',key=k))+'\n').encode() for k in keys))
            first.shutdown(socket.SHUT_WR);service._read(second)
            self.assertEqual(observed[:4],[1,1+overlay.columns,overlay.columns,0])
            self.assertFalse(overlay.isVisible())
        finally:
            service.connection=None;first.close();second.close();overlay.hide();overlay.deleteLater()
            QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete)
