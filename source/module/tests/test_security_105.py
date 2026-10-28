import dataclasses,hashlib,io,json,os,shutil,socket,tempfile,unittest,uuid
from pathlib import Path
from unittest.mock import Mock,patch
import update_core as core
import update_apply as apply
import update_network as network
import isolated_hotkeys as hooks
from .test_updates import payload

def release(data=b'verified archive'):
 name='Lexift-1.0.5-Windows-x64.zip';root='https://github.com/luttechan/Lexift/releases/'
 return core.Release('1.0.5',root+'tag/v1.0.5',root+'download/v1.0.5/'+name,name,len(data),'sha256:'+hashlib.sha256(data).hexdigest())

class UpdateSecurity105Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
 def test_download_metadata_cannot_choose_another_repository_or_filename(self):
  for fields in ({'asset_url':'https://github.com/attacker/Lexift/releases/download/v1.0.5/payload.zip'}, {'page':'https://github.com/attacker/Lexift/releases/tag/v1.0.5'}, {'asset_name':'other.zip'}, {'size':True},{'digest':'sha256:bad'},{'build':123}):
   with self.subTest(fields=fields),patch.object(core,'open_url') as opened:
    with self.assertRaises(core.UpdateError):core.download(dataclasses.replace(release(),**fields),self.root/'download.zip',Mock())
    opened.assert_not_called()
 def test_failed_exclusive_download_does_not_delete_an_existing_file(self):
  path=self.root/'download.zip';path.write_bytes(b'keep this file')
  with patch.object(core,'open_url',return_value=io.BytesIO(b'verified archive')):
   with self.assertRaises(FileExistsError):core.download(release(),path,Mock())
  self.assertEqual(path.read_bytes(),b'keep this file')
 def test_invalid_url_forms_are_rejected_consistently(self):
  for value in (' https://github.com/a','https://github.com:bad/a','https://github.com/a\nb','https://github.com\\@evil.invalid/a','https://github.com/a\x7f'):
   with self.subTest(value=value),self.assertRaises(core.UpdateError):core.safe_url(value)
 def test_windows_aliases_and_control_characters_cannot_enter_a_package(self):
  for name in ('module/a?b','module/a*b','module/a|b','module/a<b','module/a\x01b','module/COM¹.txt','module/LPT².dll'):
   with self.subTest(name=name),self.assertRaises(core.UpdateError):core.safe_relative(name)
  self.assertEqual(str(core.safe_relative('module/日本語-data.json')),'module/日本語-data.json')
 def test_ambiguous_and_nonstandard_json_is_not_a_security_decision(self):
  for value in ('{"version":1,"version":2}','{"nested":{"a":1,"a":2}}','{"size":NaN}','{"size":Infinity}'):
   with self.subTest(value=value),self.assertRaises(core.UpdateError):core.strict_json(value)
 def test_payload_manifest_cannot_change_during_transaction_copy(self):
  new=payload(self.root/'new','1.0.5');old=payload(self.root/'old','1.0.4',b'old');copy=shutil.copytree
  def changed(src,dst,*args,**kwargs):
   result=copy(src,dst,*args,**kwargs)
   if Path(src)==new:
    (Path(dst)/'Lexift.exe').write_bytes(b'MZtampered');core.make_manifest(Path(dst),'1.0.5')
   return result
  with patch.object(apply.shutil,'copytree',side_effect=changed):
   with self.assertRaisesRegex(core.UpdateError,'changed during copy'):apply.replace_runtime(new,old,'1.0.5')
  self.assertEqual((old/'Lexift.exe').read_bytes(),b'MZold')
 def test_download_build_is_pinned_before_installing(self):
  new=payload(self.root/'new','1.0.5');old=payload(self.root/'old','1.0.4',b'old')
  with self.assertRaisesRegex(core.UpdateError,'changed after validation'):apply.replace_runtime(new,old,'1.0.5',expected_build='0'*64)
  self.assertEqual((old/'Lexift.exe').read_bytes(),b'MZold')
 def test_elevated_updater_stops_before_reading_a_user_writable_job(self):
  with patch.object(apply,'is_elevated',return_value=True),patch.object(apply,'load_job') as load:
   with self.assertRaises(core.UpdateError):apply.run_job(self.root/'job.json')
   load.assert_not_called()
 def test_elevated_app_does_not_create_user_controlled_log_files(self):
  import app
  root=Mock(handlers=[])
  with patch.object(apply,'is_elevated',return_value=True),patch.object(app.logging,'getLogger',return_value=root),patch.object(app,'RotatingFileHandler') as opened,patch.object(Path,'mkdir') as mkdir:
   app.setup_logging();opened.assert_not_called();mkdir.assert_not_called()
 def test_elevated_startup_failure_does_not_append_to_a_user_controlled_path(self):
  from .test_bootstrap import get_launcher
  bootstrap=get_launcher()
  with patch.object(apply,'is_elevated',return_value=True),patch.dict(os.environ,{'LOCALAPPDATA':str(self.root)}):
   bootstrap._report_startup_error('error',show_dialog=False)
  self.assertFalse((self.root/'Lexift').exists())
 @unittest.skipUnless(os.name=='nt','Windows process identity')
 def test_parent_identity_matches_the_actual_running_image(self):
  import sys
  kernel,handle=apply.parent_handle(os.getpid(),Path(sys.executable))
  kernel.CloseHandle(handle)
 @unittest.skipUnless(os.name=='nt','Windows process identity')
 def test_parent_identity_rejects_an_unrelated_running_image(self):
  with self.assertRaises(core.UpdateError):apply.parent_handle(os.getpid(),self.root/'Lexift.exe')
 @unittest.skipUnless(os.name=='nt','Windows filesystem security')
 def test_unc_and_device_paths_are_rejected_without_a_network_probe(self):
  for value in (r'\\attacker.invalid\share\runtime',r'\\?\C:\runtime',r'\\.\C:\runtime'):
   with self.subTest(path=value),self.assertRaises(core.UpdateError):core.plain_path(Path(value))
 def test_atomic_status_write_does_not_follow_a_predictable_temporary_file(self):
  trap=self.root/'result.tmp';trap.write_text('keep');network.write_json(self.root/'result.json',dict(prepared=True))
  self.assertEqual(trap.read_text(),'keep');self.assertTrue(json.loads((self.root/'result.json').read_text())['prepared'])
 def update_job(self):
  cache=self.root/'cache';job=cache/uuid.uuid4().hex;job.mkdir(parents=True)
  target=payload(self.root/'installed','1.0.4',b'old');new=payload(job/'unpacked/Lexift','1.0.5')
  data=dict(product='Lexift',nonce=job.name,target=str(target),payload=str(new),version='1.0.5',parent_pid=123,
            security_format=2,expected_build=core.payload_build(core.validate_payload(new,'1.0.5')['files']))
  path=job/'job.json';path.write_text(json.dumps(data));return cache,path,data
 def test_legacy_job_is_readable_only_for_an_old_updaters_startup_acknowledgement(self):
  cache,path,data=self.update_job();data.pop('security_format');data.pop('expected_build');path.write_text(json.dumps(data))
  with patch.object(apply,'cache_root',return_value=cache):
   with self.assertRaises(core.UpdateError):apply.load_job(path)
   self.assertEqual(apply.load_job(path,allow_legacy=True)['version'],'1.0.5')
 def test_rehashed_payload_cannot_replace_the_job_pinned_build(self):
  cache,path,data=self.update_job();new=Path(data['payload']);(new/'Lexift.exe').write_bytes(b'MZchanged');core.make_manifest(new,'1.0.5')
  with patch.object(apply,'cache_root',return_value=cache),self.assertRaisesRegex(core.UpdateError,'changed after download'):apply.load_job(path)
 def test_job_parent_must_be_a_positive_integer(self):
  cache,path,data=self.update_job();data['parent_pid']=True;path.write_text(json.dumps(data))
  with patch.object(apply,'cache_root',return_value=cache),self.assertRaises(core.UpdateError):apply.load_job(path)
 @unittest.skipUnless(os.name=='nt','Windows reparse point security')
 def test_junction_runtime_is_rejected_before_reading_its_manifest(self):
  new=payload(self.root/'payload','1.0.5');link=self.root/'linked'
  import subprocess
  subprocess.run(['cmd','/c','mklink','/J',str(link),str(new)],check=True,capture_output=True)
  try:
   with self.assertRaises(core.UpdateError):core.validate_payload(link,'1.0.5')
  finally:
   self.assertTrue(link.absolute().is_relative_to(self.root.absolute()));os.rmdir(link)
 def test_case_aliases_between_archive_files_and_directories_are_rejected(self):
  import zipfile,threading
  archive=self.root/'bad.zip'
  with zipfile.ZipFile(archive,'w') as target:
   target.writestr('Lexift/module',b'file');target.writestr('Lexift/MODULE/file.dll',b'outside')
  with self.assertRaises(core.UpdateError):core.extract_package(archive,self.root/'unpacked','1.0.5',threading.Event())
  self.assertFalse((self.root/'unpacked').exists())

class WorkerSecurity105Tests(unittest.TestCase):
 @unittest.skipUnless(os.name=='nt','Windows exclusive socket binding')
 def test_another_local_listener_cannot_take_over_the_worker_port(self):
  worker=hooks.HookService();spawn=hooks.subprocess.Popen
  def intercepted(args,**kwargs):
   with socket.socket() as rogue:
    rogue.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
    with self.assertRaises(OSError):rogue.bind(('127.0.0.1',int(args[1])))
   return spawn(args,**kwargs)
  try:
   with patch.object(hooks.subprocess,'Popen',side_effect=intercepted):worker.ensure_started()
   worker.command('active',active=0)
  finally:worker.close()
 def test_each_valid_frame_is_bounded_separately(self):
  raw=(json.dumps(dict(value='x'*14000))+'\n').encode()*2
  class Stream:
   def recv(self,size):
    nonlocal raw
    result,raw=raw[:size],raw[size:];return result
  self.assertEqual(len(list(hooks.messages(Stream()))),2)
 def test_oversized_incoming_frame_is_rejected(self):
  stream=Mock();stream.recv.side_effect=[b'x'*16385,b'']
  with self.assertRaises(ValueError):list(hooks.messages(stream))
 def test_outgoing_frame_limit_is_applied_before_socket_write(self):
  stream=Mock()
  with self.assertRaises(ValueError):hooks.send(stream,dict(value='x'*20000))
  stream.sendall.assert_not_called()
 def test_worker_authentication_rejects_short_or_nonhex_tokens(self):
  for value in (b'a'*63,b'z'*64,b'a'*65):
   with patch.object(hooks.sys,'stdin',Mock(buffer=io.BytesIO(value))),self.assertRaises(ValueError):hooks.read_worker_token()
 @unittest.skipUnless(os.name=='nt','Native keyboard worker')
 def test_native_worker_authenticates_without_a_command_line_secret(self):
  worker=hooks.HookService()
  try:
   worker.ensure_started();self.assertEqual(len(worker.process.args),2);self.assertTrue(worker.process.stdin.closed)
   worker.command('active',active=0)
  finally:worker.close()
 @unittest.skipUnless(os.name=='nt','Native keyboard worker')
 def test_unauthenticated_oversized_client_cannot_abort_worker_startup(self):
  worker=hooks.HookService();spawn=hooks.subprocess.Popen
  def intercepted(args,**kwargs):
   with socket.create_connection(('127.0.0.1',int(args[1])),timeout=2) as rogue:rogue.sendall(b'x'*20000+b'\n')
   return spawn(args,**kwargs)
  try:
   with patch.object(hooks.subprocess,'Popen',side_effect=intercepted):worker.ensure_started()
   worker.command('active',active=0)
  finally:worker.close()
