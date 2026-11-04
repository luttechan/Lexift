"""Legacy startup migration, without reading or writing the real registry."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'engine/module'))
from desktop_startup import set_startup

class Registry:
    HKEY_CURRENT_USER=1;REG_SZ=1
    def __init__(self):self.values={'KanaShift':'old launcher','Lexift':'old Lexift'}
    def CreateKey(self,*unused):return self
    def __enter__(self):return self
    def __exit__(self,*unused):pass
    def SetValueEx(self,key,name,reserved,kind,value):self.values[name]=value
    def DeleteValue(self,key,name):
        if name not in self.values:raise FileNotFoundError(name)
        del self.values[name]

registry=Registry();set_startup('G:/Development/Lexift/Lexift.exe',False,registry)
assert not registry.values,'Turning startup off must also remove the KanaShift entry'
registry=Registry();set_startup('G:/Development/Lexift App/Lexift.exe',True,registry)
assert registry.values=={'Lexift':'"G:/Development/Lexift App/Lexift.exe" --background'}
print('Startup migration: 2 checks passed; real registry untouched')
