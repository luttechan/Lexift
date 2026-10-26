import importlib.util,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import update_core as core

def compatibility_release():
    tag='v1.0.4';base='https://github.com/luttechan/Lexift/releases/download/'+tag+'/'
    files={'Lexift.exe':'a'*64,'module/helper.exe':'b'*64};build=core.payload_build(files)
    return dict(tag_name=tag,name='Lexift 1.0.4',draft=False,prerelease=False,
        html_url='https://github.com/luttechan/Lexift/releases/tag/'+tag,
        body='<!-- lexift-files-sha256:'+build+' -->',
        assets=[dict(name='Lexift-'+v+'-Windows-x64.zip',size=100,digest='sha256:'+'c'*64,
                     browser_download_url=base+'Lexift-'+v+'-Windows-x64.zip') for v in ('1.0.4','1.0.4b')])

class UpdateCompatibilityTests(unittest.TestCase):
    def test_current_client_selects_the_stable_payload(self):
        result=core.parse_release(compatibility_release())
        self.assertEqual(result.version,'1.0.4');self.assertIn('1.0.4-Windows',result.asset_name)
        self.assertIn('/v1.0.4/',result.asset_url);self.assertEqual(len(result.build),64)
        data=compatibility_release();data['body']=data['body'].replace('\n','\r\n')+'\r\n'
        self.assertEqual(core.parse_release(data).build,result.build)
    def test_stable_version_is_newer_than_the_existing_beta(self):
        self.assertGreater(core.version_key('1.0.4'),core.version_key('1.0.4b'))
    def test_transport_manifest_version_does_not_change_the_installed_build(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'module').mkdir();p=root/'module/update-manifest.json'
            files={'Lexift.exe':'a'*64};p.write_text(json.dumps(dict(version='1.0.4',files=files)))
            before=core.installed_build(root);p.write_text(json.dumps(dict(version='1.0.4b',files=files)))
            self.assertEqual(before,core.installed_build(root));self.assertEqual(len(before),64)
    def test_missing_or_corrupt_local_manifest_does_not_crash_update_check(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);self.assertEqual(core.installed_build(root),'')
            (root/'update-manifest.json').write_text('bad json')
            self.assertEqual(core.installed_build(root),'')
    def test_actual_103_parser_selects_numeric_transport_payload(self):
        path=Path(__file__).resolve().parents[3]/'Lexift v1.0.3/module/update_core.py'
        if not path.is_file():self.skipTest('Archived 1.0.3 source is not installed')
        import sys
        name='lexift_103_compat_test';spec=importlib.util.spec_from_file_location(name,path)
        old=importlib.util.module_from_spec(spec);sys.modules[name]=old
        try:
            spec.loader.exec_module(old);result=old.parse_release(compatibility_release())
            self.assertEqual(result.version,'1.0.4');self.assertIn('1.0.4-Windows',result.asset_name)
        finally:sys.modules.pop(name,None)
