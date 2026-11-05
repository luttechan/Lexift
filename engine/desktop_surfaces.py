"""Send UI state to the desktop host without creating Qt widgets."""
from PySide6.QtCore import QObject, QTimer, Signal
from caps_lock_indicator import CapsLockIndicator
from notification_sound import notify_event


class Notices(QObject):
    def __init__(self,publish):
        super().__init__()
        self.publish=publish
        self.kind=None
        self.revision=0
        self.timer=QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.hide)

    def show(self,text,kind,placement,duration,title=''):
        duration=max(500,min(int(duration),10000))
        self.timer.stop()
        self.revision+=1
        self.kind=kind
        self.publish('notice-popup',dict(visible=True,revision=self.revision,text=str(text),
                                        title=str(title),placement=placement,kind=kind,duration=duration))
        self.timer.start(duration)

    def hide(self,kind=None):
        if self.kind is None or (kind is not None and self.kind!=kind):
            return
        self.timer.stop()
        self.kind=None
        self.revision+=1
        self.publish('notice-popup',dict(visible=False,revision=self.revision))


class CapsIndicator(CapsLockIndicator):
    def __init__(self,notices,parent=None):
        self.notices=notices
        super().__init__(parent)

    def show_state(self,enabled):
        self.notices.show('Caps Lock  '+('ON' if enabled else 'OFF'),'caps','center',1000)

    def hide(self):
        self.notices.hide('caps')


class CursorIndicator:
    def __init__(self,notices):
        self.notices=notices

    def show_language(self,text):
        self.notices.show(text,'cursor','cursor',1000)

    def dismiss(self):
        self.notices.hide('cursor')


class TrayAdapter(QObject):
    activated=Signal(object)
    messageClicked=Signal()

    def __init__(self,notices,parent=None):
        super().__init__(parent)
        self.notices=notices
        self.visible=False

    def setToolTip(self,text):
        pass

    def setContextMenu(self,menu):
        pass

    def show(self):
        self.visible=True

    def hide(self):
        self.visible=False
        self.hide_notification()

    def isVisible(self):
        return self.visible

    def showMessage(self,title,message,icon=None,msecs=10000):
        self.notices.show(message,'notification','corner',msecs,title)
        notify_event()

    def hide_notification(self):
        self.notices.hide('notification')
