import os,shutil,subprocess,sys
from pathlib import Path
R=Path(__file__).resolve().parents[1];W=R.parent;tools=W/'.lexift-tools'
env=dict(os.environ)
local_cargo=tools/'cargo/bin/cargo.exe'
if local_cargo.is_file():
    env.update(CARGO_HOME=str(tools/'cargo'),RUSTUP_HOME=str(tools/'rustup'))
node=Path.home()/'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin'
pnpm=Path.home()/'.cache/codex-runtimes/codex-primary-runtime/dependencies/bin/fallback'
env['PATH']=os.pathsep.join((str(tools/'cargo/bin'),str(node),str(pnpm),env['PATH']))
vc=Path('C:/Program Files/Microsoft Visual Studio/2022/Community/VC/Auxiliary/Build/vcvars64.bat')
if vc.is_file():
    p=subprocess.run(f'cmd.exe /d /s /c "chcp 65001 >nul && call "{vc}" >nul && set"',capture_output=True,text=True,encoding='utf-8',errors='replace')
    if p.returncode:raise RuntimeError(p.stderr[-800:])
    for line in p.stdout.splitlines():
        if '=' in line and not line.startswith('='):
            key,value=line.split('=',1)
            if key.upper() in ('PATH','INCLUDE','LIB','LIBPATH','WINDOWSSDKDIR','VCTOOLSINSTALLDIR'):env[key]=value if key.upper()!='PATH' else env['PATH']+os.pathsep+value
# Optional workspace-local SDK cache for hosts whose system SDK is incomplete.
# These are Microsoft.Windows.SDK.CPP.x64 import libraries, not runtime files.
sdk=tools/'windows-sdk/10.0.26100.4204/c'
for part in ('um/x64','ucrt/x64'):
    folder=sdk/part
    if folder.is_dir():env['LIB']=env.get('LIB','')+os.pathsep+str(folder)
for part in ('shared','um','ucrt','winrt','cppwinrt'):
    folder=sdk/'Include/10.0.26100.0'/part
    if folder.is_dir():env['INCLUDE']=env.get('INCLUDE','')+os.pathsep+str(folder)
resource_compiler=sdk/'bin/10.0.26100.0/x64/rc.exe'
if resource_compiler.is_file():
    env['RC']=str(resource_compiler)
    env['PATH']=str(resource_compiler.parent)+os.pathsep+env['PATH']
arguments=sys.argv[1:]
if arguments and arguments[0] in ('build','test') and '--features' not in arguments:
    arguments += ['--features','tauri/custom-protocol']
cargo=str(local_cargo) if local_cargo.is_file() else shutil.which('cargo',path=env['PATH'])
if not cargo:raise SystemExit('Rust MSVC toolchain is required.')
raise SystemExit(subprocess.call([cargo,*arguments],cwd=R/'src-tauri',env=env))
