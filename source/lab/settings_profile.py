"""Measure the owned settings UI through layout and paint, with real styling."""
import argparse
import cProfile
import io
import json
from pathlib import Path
import pstats
import sys
import tempfile
import time

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / 'module'))
import app
from PySide6.QtCore import QCoreApplication, QEvent, QSettings, Qt
from PySide6.QtWidgets import QApplication
from i18n import set_language


def measure(output, language='ko', prepare=False):
    qt = QApplication.instance() or QApplication([])
    qt.setQuitOnLastWindowClosed(False)
    set_language(language)
    app.choose_font(qt)
    qt.setStyleSheet(app.QSS)
    rows = []
    profile = cProfile.Profile()
    profile.enable()
    with tempfile.TemporaryDirectory() as folder:
        store = QSettings(str(Path(folder) / 'settings.ini'), QSettings.Format.IniFormat)
        start = time.perf_counter()
        window = app.MainWindow(store, [], False)
        window._preferences_timer.stop()
        rows.append(dict(operation='construct', ms=round((time.perf_counter()-start)*1000, 3)))
        # Paint our own widgets without displaying or controlling another app.
        window.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
        start = time.perf_counter()
        window.show()
        qt.processEvents()
        window.grab()
        rows.append(dict(operation='dashboard_first_paint', ms=round((time.perf_counter()-start)*1000, 3)))
        if prepare:
            for _ in range(3):
                window._prepare_next_page()
            window._preferences_timer.stop()
        for index in (2, 3, 4, 1, 0, 2, 3, 4, 0, 2):
            start = time.perf_counter()
            window.nav_buttons[index].click()
            navigated = time.perf_counter()
            qt.processEvents()
            events = time.perf_counter()
            window.grab()
            painted = time.perf_counter()
            rows.append(dict(operation=f'page_{index}_paint', ms=round((painted-start)*1000, 3),
                             navigate_ms=round((navigated-start)*1000, 3),
                             events_ms=round((events-navigated)*1000, 3),
                             paint_ms=round((painted-events)*1000, 3)))
            if index == 2:
                window.grab().save(str(Path(output).with_suffix('.png')))
        window._preferences_timer.stop()
        window.hide()
        window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        qt.processEvents()
    profile.disable()
    stream = io.StringIO()
    pstats.Stats(profile, stream=stream).sort_stats('cumtime').print_stats(25)
    result = dict(language=language, prepared=prepare, rows=rows, profile=stream.getvalue())
    Path(output).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='profile'}, ensure_ascii=False))
    print(stream.getvalue())


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    parser.add_argument('--language', default='ko')
    parser.add_argument('--prepare', action='store_true')
    args = parser.parse_args()
    measure(args.output, args.language, args.prepare)
