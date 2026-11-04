"""Verify the shipped runtime and private helper authentication, without typing."""
import json,ssl,struct,sys
from pathlib import Path

def verify(output):
    from app import VERSION
    from PySide6.QtCore import qVersion
    from isolated_hotkeys import HookService
    root=Path(__file__).resolve().parent
    checks=dict(python=sys.version_info[:3]>=(3,12,16),openssl=ssl.OPENSSL_VERSION_INFO[:4]>=(3,5,0,9),
                qt=tuple(map(int,qVersion().split('.')))>=(6,12,0))
    worker=HookService()
    try:
        worker.ensure_started();worker.command('active',active=0)
        checks['private_worker_authentication']=len(worker.process.args)==2 and worker.process.stdin.closed
    finally:worker.close()
    headers=[]
    files=[root/'lab/ime_candidate_host.exe',root/'lexift_keyboard.exe',root/'kanashift_hooks.dll']
    if getattr(sys,'frozen',False):files.extend((Path(sys.executable),root/'LexiftUpdater.exe'))
    else:files[0]=root.parent/'lab/ime_candidate_host.exe'
    for path in files:
        with path.open('rb') as stream:
            dos=stream.read(64);offset=struct.unpack_from('<I',dos,60)[0]
            if dos[:2]!=b'MZ' or offset>1024*1024:raise ValueError('Invalid PE header')
            stream.seek(offset);header=stream.read(96)
        if header[:4]!=b'PE\x00\x00':raise ValueError('Invalid PE signature')
        machine=struct.unpack_from('<H',header,4)[0];flags=struct.unpack_from('<H',header,94)[0]
        headers.append(dict(file=path.name,x64=machine==0x8664,aslr=bool(flags&0x40),dep=bool(flags&0x100)))
    checks['native_hardening']=all(row['x64'] and row['aslr'] and row['dep'] for row in headers)
    result=dict(version=VERSION,python=sys.version.split()[0],openssl=ssl.OPENSSL_VERSION,qt=qVersion(),
                checks=checks,pe_headers=headers,passed=all(checks.values()))
    Path(output).write_text(json.dumps(result,indent=2),encoding='utf-8')
    return 0 if result['passed'] else 1
