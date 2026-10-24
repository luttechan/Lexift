"""Exercise real worker lifecycle and GUI dispatch without injected keystrokes."""
import json
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / 'module'))
from isolated_hotkeys import CapsQHook
from hotkeys_windows import HotkeyBinding

results = {'context': 'Lexift & ANV', 'version': '1.0.0-experimental', 'worker_registration': []}
for mode, key in [('caps', 'Q'), ('ctrl_shift', 'F12')]:
    hook = CapsQHook(lambda hwnd: None, HotkeyBinding(mode, key), on_ime=lambda hwnd: None)
    try:
        hook.start()
        results['worker_registration'].append({'mode': mode, 'key': key, 'ime_enabled': True, 'started': True})
    finally:
        hook.stop()

from PySide6.QtCore import QSettings, QTimer
from PySide6.QtWidgets import QApplication
from app import Dispatcher
from ime_panel import candidate_panel

qt = QApplication([])
dispatch = Dispatcher()
dispatch.ime_requested.connect(lambda hwnd: candidate_panel().open())
dispatch.ime_requested.emit(0)

def finish():
    panel = candidate_panel()
    results['gui_dispatch'] = {'launched': panel.process is not None and panel.process.poll() is None,
                               'owned_window_found': bool(panel._window())}
    panel.close()
    qt.quit()

QTimer.singleShot(2200, finish)
qt.exec()
panel = candidate_panel()
if panel.process:
    panel.process.wait(timeout=5)
    results['gui_dispatch']['graceful_exit'] = panel.process.returncode == 0
results['physical_shortcut_tested'] = False
path = root / 'test-results' / 'shortcut-smoke.json'
path.write_text(json.dumps(results, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps(results, ensure_ascii=False, indent=2))
assert results['gui_dispatch']['launched'] and results['gui_dispatch']['owned_window_found'] and results['gui_dispatch']['graceful_exit']
