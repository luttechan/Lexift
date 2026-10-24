"""Static safeguards for accidentally replacing the Lexift v0.6 design."""
from pathlib import Path
import unittest

APP = (Path(__file__).resolve().parents[1] / 'app.py').read_text(encoding='utf-8')


class OriginalDesignTests(unittest.TestCase):
    def test_original_sidebar(self):
        self.assertIn('sidebar.setFixedWidth(226)', APP)
        self.assertIn('for text in (tr("대시보드"), tr("입력기 슬롯"), tr("일반 설정"), tr("프로그램 정보"),tr(\'사용자 사전\'))', APP)

    def test_original_dashboard_and_cards(self):
        self.assertIn('def _make_dashboard(self)', APP)
        self.assertIn('self.preview.addWidget(card, i//3, i%3)', APP)
        self.assertIn('self.resize(1020, 690)', APP)
        self.assertIn('self.setMinimumSize(850, 560)', APP)

    def test_original_charcoal_theme(self):
        self.assertIn('QWidget#window { background:#0D0E11; }', APP)
        self.assertIn('QFrame#side { background:#111216;', APP)
        self.assertIn('QFrame#panel { background:#17191E;', APP)
        self.assertIn('QFrame#tile { background:#1C1F25;', APP)

    def test_features_added_without_removing_pages(self):
        self.assertIn('self.window.shortcut_changed.connect(self.change_shortcut)', APP)
        self.assertIn('self.dashboard_shortcut.setText(binding.title)', APP)
        self.assertIn('self.special_list', APP)
        self.assertIn('self.tray_menu.addAction(tr("설정"), lambda: self.show_window(2))', APP)


if __name__ == '__main__':
    unittest.main()
