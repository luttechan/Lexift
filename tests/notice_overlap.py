import os,sys,json
from pathlib import Path
root=Path(__file__).resolve().parents[1];sys.path[:0]=[str(root/'engine'),str(root/'engine/module'),str(root.parent/'.builddeps')]
from PySide6.QtCore import QCoreApplication,QTimer
from desktop_surfaces import Notices
app=QCoreApplication([]);frames=[];checks=[];n=Notices(lambda label,frame:frames.append((label,frame)))
n.show('Caps Lock ON','caps','center',500)
QTimer.singleShot(300,lambda:n.show('message','notification','corner',800))
QTimer.singleShot(400,lambda:n.hide('caps'))
def check_middle():
 checks.append(n.kind=='notification' and frames[-1][1]['visible'])
QTimer.singleShot(650,check_middle)
def finish():
 assert n.kind is None and frames[-1][1]['visible']==False
 assert len(frames)==3,frames
 assert frames[0][1]['duration']==500 and frames[1][1]['duration']==800
 print(json.dumps({'passed':True,'checks':['replaced caps timer does not close new notification','kind-specific hide does not close replacement','notification expires after overlap','duration included for native expiry']}));app.quit()
QTimer.singleShot(1400,finish);QTimer.singleShot(4000,app.quit);app.exec()
assert checks==[True] and n.kind is None and len(frames)==3 and not frames[-1][1]['visible']
