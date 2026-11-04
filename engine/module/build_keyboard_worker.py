import hashlib,json,os,shutil,subprocess
from pathlib import Path

def build():
    root=Path(__file__).resolve().parent
    digest=lambda p:hashlib.sha256(p.read_bytes().replace(b'\r\n',b'\n')).hexdigest()
    expected={name:digest(root/name) for name in ('keyboard_worker.c','native_hooks.c')}
    target=root/'lexift_keyboard.exe';manifest=root/'keyboard_worker_build.json'
    if target.exists() and manifest.exists():
        saved=json.loads(manifest.read_text(encoding='utf-8'))
        if saved.get('cpu')=='baseline' and saved.get('sources')==expected and saved.get('binary_sha256')==hashlib.sha256(target.read_bytes()).hexdigest():
            print('Native keyboard worker verified');return
    compiler=os.environ.get('KANASHIFT_ZIG') or shutil.which('zig')
    if not compiler:raise RuntimeError('Set KANASHIFT_ZIG to zig.exe')
    subprocess.run([compiler,'cc',str(root/'keyboard_worker.c'),'-target','x86_64-windows-gnu','-mcpu=baseline','-Os','-s','-municode','-Wl,--subsystem,windows','-lws2_32','-luser32','-lshell32','-o',str(target)],check=True)
    manifest.write_text(json.dumps(dict(cpu='baseline',sources=expected,binary_sha256=hashlib.sha256(target.read_bytes()).hexdigest()),indent=2)+'\n',encoding='utf-8')
    print('Native keyboard worker built')
if __name__=='__main__':build()
