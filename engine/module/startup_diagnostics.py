"""Measure our own Windows UI without hooks, external input, or user settings writes."""
import json,sys,tempfile,time
from pathlib import Path


def verify(output,language='ko'):
    started=getattr(sys,'_lexift_started_at',time.perf_counter());rows=[]
    def mark(name):rows.append(dict(stage=name,elapsed_ms=round((time.perf_counter()-started)*1000,2)))
    import app
    from i18n import set_language
    from PySide6.QtCore import QSettings,QEventLoop
    from PySide6.QtGui import QRawFont
    from PySide6.QtWidgets import QLabel
    mark('imports');qt=app.QApplication([]);qt.setQuitOnLastWindowClosed(False)
    set_language(language);mark('application');app.choose_font(qt);qt.setStyleSheet(app.QSS);mark('fonts')
    with tempfile.TemporaryDirectory(prefix='lexift-startup-') as folder:
        store=QSettings(str(Path(folder)/'settings.ini'),QSettings.Format.IniFormat)
        original=app.QSettings;app.QSettings=lambda *args:store
        controller=None
        try:
            controller=app.LexiftController(qt);controller.caps_indicator.stop();controller.tray.hide();mark('controller')
            controller._create_window();mark('window_created')
            controller.window.show();qt.processEvents(QEventLoop.ProcessEventsFlag.ExcludeUserInputEvents);mark('first_paint')
            frame=controller.window.grab();frame.save(str(Path(output).with_suffix('.png')))
            example=next(w for w in controller.window.findChildren(QLabel) if w.text()=='ke → kě (Caps + 3)')
            font=QRawFont.fromFont(example.font());checks=dict(pinyin_glyph=font.supportsCharacter(ord('ě')),all_pages_ready=controller.window._ready_pages=={0,1,2,3,4},frame_rendered=not frame.isNull())
            menus=[]
            for page in (2,3,4,1,0):
                then=time.perf_counter();controller.window.navigate(page);qt.processEvents(QEventLoop.ProcessEventsFlag.ExcludeUserInputEvents)
                menus.append(dict(page=page,elapsed_ms=round((time.perf_counter()-then)*1000,2)))
            report=dict(passed=all(checks.values()),version=app.VERSION,language=language,platform=qt.platformName(),stages=rows,menus=menus,checks=checks,external_input_sent=False,keyboard_hooks_started=False)
            Path(output).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        finally:
            app.QSettings=original
            if controller:
                controller.tray.hide();controller.caps_indicator.stop()
                if controller._window:controller._window.hide()
                controller._shutdown_keyboard()
    return 0 if report['passed'] else 1
