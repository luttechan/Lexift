import json,os,queue,subprocess,sys,threading,time,winreg
from pathlib import Path
R=Path(__file__).resolve().parents[1];W=R.parent
frozen='--frozen' in sys.argv
python=W/'.security-python/cpython-3.12.16-windows-x86_64-none/python.exe'
args=[str(R/'engine-dist/LexiftEngine.exe')] if frozen else [str(python),str(R/'engine/bridge.py')]
env=dict(os.environ,PYTHONPATH=str(W/'.builddeps'),PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1')
def startup_value():
 try:
  with winreg.OpenKey(winreg.HKEY_CURRENT_USER,r'Software\Microsoft\Windows\CurrentVersion\Run') as key:return winreg.QueryValueEx(key,'Lexift')
 except FileNotFoundError:return None
before=startup_value()
p=subprocess.Popen([*args,'--host-exe',str(python),'--diagnostic'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env,creationflags=subprocess.CREATE_NO_WINDOW)
messages=queue.Queue();events=[];checks=[];sequence=0
def read():
 for line in p.stdout:
  try:messages.put(json.loads(line))
  except Exception:messages.put(dict(invalid=line.decode('utf-8','replace')[:300]))
threading.Thread(target=read,daemon=True).start()
def request(action,payload=None,ok=True):
 global sequence
 sequence+=1;identifier=sequence
 p.stdin.write((json.dumps(dict(id=identifier,action=action,payload=payload or {}),ensure_ascii=False)+'\n').encode());p.stdin.flush()
 until=time.monotonic()+20
 while time.monotonic()<until:
  item=messages.get(timeout=max(.01,until-time.monotonic()))
  assert 'invalid' not in item,item
  if item.get('id')==identifier:
   assert item['ok']==ok,item
   checks.append(dict(action=action,rejected=not ok));return item.get('data',item.get('error'))
  events.append(item)
 raise AssertionError('Engine response timed out')
try:
 state=request('get_state');assert state['diagnostic'] and not state['running'] and state['layouts']
 state=request('set_feature',dict(name='ja',enabled=False));assert not state['features']['ja']
 request('set_feature',dict(name='ja',enabled='false'),False)
 request('set_shortcut',dict(name='ja',mode='caps',key='Q'),False)
 state=request('set_shortcut',dict(name='ja',mode='ctrl_alt',key='F9'));assert state['shortcuts']['ja']['key']=='F9'
 state=request('set_feature',dict(name='tone',enabled=True));assert state['features']['tone']
 request('set_shortcut',dict(name='selector',mode='caps',key='1'),False)
 entries=[dict(keyword='도쿄',text='東京',language='ja'),dict(keyword='니하오',text='你好',language='zh')]
 state=request('save_dictionary',dict(entries=entries));assert state['dictionary']==entries
 state=request('save_dictionary',dict(entries=entries[:1]));assert state['dictionary']==entries[:1]
 request('save_dictionary',dict(entries=[entries[0],entries[0]]),False)
 assert request('get_state')['dictionary']==entries[:1]
 layout=state['layouts'][0];slots=[dict(hkl=layout['hkl'],mode=layout['modes'][0]['value'],name='검증 입력기')]
 state=request('save_slots',dict(slots=slots));assert state['slots']==slots and not state['firstRun']
 assert state['version']=='1.2.1' and state['selectorRenderer']=='tauri'
 state=request('set_general',dict(capsNotice=False));assert state['general']['capsNotice'] is False
 state=request('set_enabled',dict(enabled=False))
 state=request('set_enabled',dict(enabled=True));assert state['general']['capsNotice'] is False
 frame=request('diagnostic_selector',dict(open=True));assert frame['visible'] and frame['items'][0]['slot']==slots[0]
 request('selector_present',dict(revision=frame['revision']))
 stale=request('selector_pick',dict(index=0,revision=frame['revision']-1));assert stale['visible']
 frame=request('selector_pick',dict(index=0,revision=frame['revision']));assert not frame['visible']
 time.sleep(.1);assert request('get_state')['lastSelection']==slots[0]
 frame=request('diagnostic_selector',dict(open=True));request('selector_present',dict(revision=frame['revision']))
 frame=request('diagnostic_selector',dict(key=27));assert not frame['visible']
 request('diagnostic_selector',dict(open=True));time.sleep(2.3)
 assert not request('diagnostic_selector')['visible'],'Missing renderer must release captured navigation keys'
 many=[dict(slots[0],name=f'검증 {n+1}') for n in range(15)]
 request('save_slots',dict(slots=many))
 frame=request('diagnostic_selector',dict(open=True));request('selector_present',dict(revision=frame['revision']))
 request('diagnostic_selector',dict(key=ord('E')));time.sleep(.1)
 assert request('get_state')['lastSelection']['name']=='검증 15','Letter key must select row 15'
 frame=request('diagnostic_selector',dict(open=True));request('selector_present',dict(revision=frame['revision']))
 request('diagnostic_selector',dict(key=0x60));time.sleep(.1)
 assert request('get_state')['lastSelection']['name']=='검증 10','Numpad zero must select row 10'
 japanese=next((item for item in state['layouts'] if any(mode['value']=='ja_katakana_ask' for mode in item['modes'])),None)
 if japanese:
  request('save_slots',dict(slots=[dict(hkl=japanese['hkl'],mode='ja_katakana_ask',name='カタカナ')]))
  frame=request('diagnostic_selector',dict(open=True));request('selector_present',dict(revision=frame['revision']))
  frame=request('diagnostic_selector',dict(key=0x31));assert frame['page']=='width' and len(frame['items'])==2
  request('selector_present',dict(revision=frame['revision']))
  frame=request('diagnostic_selector',dict(key=27));assert frame['page']=='slots' and frame['visible']
  frame=request('diagnostic_selector',dict(key=0x31));request('selector_present',dict(revision=frame['revision']))
  request('diagnostic_selector',dict(key=0x32));time.sleep(.1)
  assert request('get_state')['lastSelection']['mode']=='ja_katakana_half'
 request('save_slots',dict(slots=slots))
 request('save_slots',dict(slots=[]),False)
 state=request('set_enabled',dict(enabled=False));assert not state['enabled']
 state=request('set_enabled',dict(enabled=True));assert state['enabled'] and not state['running']
 state=request('set_general',dict(sound=False,autoStart=True));assert not state['general']['sound'] and state['general']['autoStart']
 request('set_general',dict(sound=True,autoStart='invalid'),False)
 assert request('get_state')['general']['sound'] is False
 state=request('set_general',dict(language='ja'));assert state['language']=='ja'
 request('reset_defaults',dict(confirmed=False),False)
 state=request('reset_defaults',dict(confirmed=True));assert not state['dictionary'] and state['language']=='ko'
 assert state['general']['capsNotice'] is True
 request('execute',dict(command='do not execute'),False)
 assert startup_value()==before,'Real startup registry changed'
 p.stdin.close();p.wait(timeout=10);assert p.returncode==0,p.stderr.read().decode('utf-8','replace')[-2000:]
 report=dict(passed=True,frozen=frozen,checks=checks,real_startup_unchanged=True,external_input_sent=False,graceful_parent_pipe_close=True)
 (R/'verification'/('engine-frozen.json' if frozen else 'engine-source.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2))
 print(json.dumps(dict(passed=True,frozen=frozen,checks=len(checks))))
finally:
 if p.poll() is None:p.kill();p.wait()
