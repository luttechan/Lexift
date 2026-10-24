import unittest
from unittest.mock import Mock,patch
from PySide6.QtCore import QPoint,QRect
from ime_inline import caret_point,popup_coordinates

class CandidatePositionTests(unittest.TestCase):
    def test_popup_below_caret(self):
        self.assertEqual(popup_coordinates(QPoint(400,350),QRect(0,0,1920,1040),330,300),(400,350))

    def test_popup_above_caret_at_bottom_edge(self):
        x,y=popup_coordinates(QPoint(1800,1000),QRect(0,0,1920,1040),330,300,32)
        self.assertEqual((x,y),(1590,656))

    def test_negative_monitor_origin_and_top_edge(self):
        bounds=QRect(-1280,-200,1280,1024)
        for point in (QPoint(-1400,-300),QPoint(-2,820)):
            x,y=popup_coordinates(point,bounds,330,300)
            self.assertGreaterEqual(x,bounds.left());self.assertGreaterEqual(y,bounds.top())
            self.assertLessEqual(x+330,bounds.right()+1);self.assertLessEqual(y+300,bounds.bottom()+1)

    def test_physical_coordinates_map_to_carets_own_monitor(self):
        screen=Mock();screen.name.return_value='DISPLAY2'
        screen.geometry.return_value=QRect(-1280,0,1280,720);screen.devicePixelRatio.return_value=1.5
        def info(_monitor,pointer):
            obj=pointer._obj;obj.monitor.left=-1920;obj.monitor.top=0
            obj.device='\\\\.\\DISPLAY2';return True
        api=Mock();api.MonitorFromPoint.return_value=2;api.GetMonitorInfoW.side_effect=info
        with patch('ime_windows.user32',api),patch('ime_inline.QApplication.primaryScreen',return_value=screen),patch('ime_inline.QApplication.screens',return_value=[screen]):
            point,chosen=caret_point({'x':-960,'y':150})
        self.assertIs(chosen,screen);self.assertEqual(point,QPoint(-640,106))
