"""Per-user startup entry for the desktop host, including legacy cleanup."""
import winreg

RUN_KEY=r'Software\Microsoft\Windows\CurrentVersion\Run'

def set_startup(host,enabled,registry=winreg):
    with registry.CreateKey(registry.HKEY_CURRENT_USER,RUN_KEY) as key:
        if enabled:
            registry.SetValueEx(key,'Lexift',0,registry.REG_SZ,f'"{host}" --background')
        for name in (('KanaShift',) if enabled else ('Lexift','KanaShift')):
            try:registry.DeleteValue(key,name)
            except FileNotFoundError:pass
