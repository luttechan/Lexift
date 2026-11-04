"""Security minimums for the distributable's interpreter and bootloader."""
import importlib.metadata,ssl,sys

def verify():
    python_min={(3,12):16,(3,13):18,(3,14):10,(3,15):2}
    if sys.version_info[:2] not in python_min or sys.version_info[2]<python_min[sys.version_info[:2]]:
        raise RuntimeError('Use a Python security release from 2026-10-26 or later')
    if ssl.OPENSSL_VERSION_INFO[:4]<(3,5,0,9):raise RuntimeError('OpenSSL 3.5.9 or later is required')
    for name,minimum in (('PyInstaller',(6,22,3)),('PySide6-Essentials',(6,12,0))):
        version=tuple(int(value) for value in importlib.metadata.version(name).split('.')[:3])
        if version<minimum:raise RuntimeError(name+' must be updated before packaging')
    return dict(python=sys.version.split()[0],openssl=ssl.OPENSSL_VERSION,pyinstaller=importlib.metadata.version('PyInstaller'),pyside=importlib.metadata.version('PySide6-Essentials'))
