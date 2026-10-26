import hashlib,json,tempfile,unittest
from pathlib import Path
from native_baseline import verify

class NativeBaselineTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        for folder,binary,manifest,key in [('lab','ime_candidate_host.exe','ime_candidate_host_build.json','binary_sha256'),('module','kanashift_hooks.dll','native_hooks_build.json','dll_sha256'),('module','lexift_keyboard.exe','keyboard_worker_build.json','binary_sha256')]:
            p=self.root/folder;p.mkdir(exist_ok=True);(p/binary).write_bytes(b'fixture')
            (p/manifest).write_text(json.dumps(dict(cpu='baseline',**{key:hashlib.sha256(b'fixture').hexdigest()})))
    def test_complete_baseline_package_is_accepted(self):self.assertTrue(verify(self.root))
    def test_native_cpu_build_cannot_be_packaged(self):
        p=self.root/'lab/ime_candidate_host_build.json';d=json.loads(p.read_text());d['cpu']='native';p.write_text(json.dumps(d))
        with self.assertRaisesRegex(ValueError,'baseline'):verify(self.root)
    def test_replacing_the_binary_invalidates_compatibility_evidence(self):
        (self.root/'lab/ime_candidate_host.exe').write_bytes(b'different CPU build')
        with self.assertRaisesRegex(ValueError,'does not match'):verify(self.root)
    def test_missing_build_evidence_cannot_be_packaged(self):
        (self.root/'module/keyboard_worker_build.json').unlink()
        with self.assertRaises(FileNotFoundError):verify(self.root)
