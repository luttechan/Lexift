import hashlib
import io
import json
import os
import stat
import tempfile
import threading
import unittest
import zipfile
from pathlib import Path
from unittest.mock import Mock, patch

import update_core as core
from update_apply import replace_runtime
from package_release import package


def payload(root, version='0.7.8', marker=b'new'):
    root.mkdir(parents=True)
    (root/'KanaShift.exe').write_bytes(b'MZ'+marker)
    (root/'KanaShiftUpdater.exe').write_bytes(b'MZhelper'+marker)
    (root/'_internal').mkdir()
    (root/'_internal'/'new.dll').write_bytes(marker)
    core.make_manifest(root, version)
    return root


def release_data(tag='v0.7.8'):
    name='KanaShift-0.7.8-Windows-x64.zip'
    return dict(tag_name=tag, draft=False, prerelease=False,
                html_url=f'https://github.com/luttechan/KanaShift/releases/tag/{tag}',
                assets=[dict(name=name, size=100, digest='sha256:'+'a'*64,
                             browser_download_url=f'https://github.com/luttechan/KanaShift/releases/download/{tag}/{name}')])


class ReleaseTests(unittest.TestCase):
    def test_numeric_version_order(self):
        self.assertGreater(core.version_number('v0.7.10'),core.version_number('0.7.9'))
        self.assertGreater(core.version_number('v1.0.0'),core.version_number('v0.99.99'))

    def test_only_new_tag_convention(self):
        for tag in ('KanaShift_076','KanaShift_v076','0.7.8','v0.7.8-beta','v0.7'):
            with self.assertRaises(core.UpdateError): core.parse_release(release_data(tag))
        self.assertEqual(core.parse_release(release_data()).version,'0.7.8')

    def test_draft_and_prerelease_rejected(self):
        for field in ('draft','prerelease'):
            data=release_data();data[field]=True
            with self.assertRaises(core.UpdateError): core.parse_release(data)

    def test_source_archives_not_selected(self):
        data=release_data();data['assets'][0]['name']='Source.zip'
        self.assertFalse(core.parse_release(data).asset_url)

    def test_cross_repository_and_tag_assets_rejected(self):
        for value in ('https://github.com/other/KanaShift/releases/download/v0.7.8/a.zip',
                      'https://github.com/luttechan/KanaShift/releases/download/v0.7.9/KanaShift-0.7.8-Windows-x64.zip'):
            data=release_data();data['assets'][0]['browser_download_url']=value
            with self.assertRaises(core.UpdateError): core.parse_release(data)

    def test_untrusted_redirects_rejected(self):
        for url in ('http://github.com/a','https://github.com.evil.test/a',
                    'file:///C:/Windows/a','https://user:pass@github.com/a','https://github.com:444/a'):
            with self.assertRaises(core.UpdateError): core.safe_url(url)

    def test_redirect_to_github_asset_host_allowed(self):
        url='https://release-assets.githubusercontent.com/example?token=test'
        self.assertEqual(core.safe_url(url),url)


class PackageTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)

    def test_package_round_trip(self):
        source=payload(self.root/'source')
        archive=package(source,self.root/'release','0.7.8')
        result=core.extract_package(archive,self.root/'extract','0.7.8',threading.Event())
        self.assertEqual((result/'KanaShift.exe').read_bytes(),b'MZnew')
        self.assertTrue(archive.with_suffix('.zip.sha256').exists())

    def test_wrong_version_never_accepted(self):
        source=payload(self.root/'source')
        with self.assertRaises(core.UpdateError): core.validate_payload(source,'0.7.9')

    def test_modified_file_rejected(self):
        source=payload(self.root/'source');(source/'_internal'/'new.dll').write_bytes(b'tampered')
        with self.assertRaises(core.UpdateError): core.validate_payload(source,'0.7.8')

    def test_unlisted_extra_file_rejected(self):
        source=payload(self.root/'source');(source/'unexpected.exe').write_bytes(b'MZbad')
        with self.assertRaises(core.UpdateError): core.validate_payload(source,'0.7.8')

    def test_reserved_and_traversal_paths_rejected(self):
        for name in ('../outside','/absolute','C:/evil','_internal/../evil',
                     '_internal\\evil','_internal/a:stream','_internal/CON.txt','_internal/a.','_internal//a'):
            with self.assertRaises(core.UpdateError,msg=name): core.safe_relative(name)

    def test_hostile_zip_never_writes_outside_staging(self):
        archive=self.root/'bad.zip'
        with zipfile.ZipFile(archive,'w') as out: out.writestr('KanaShift/../../outside',b'evil')
        with self.assertRaises(core.UpdateError):
            core.extract_package(archive,self.root/'extract','0.7.8',threading.Event())
        self.assertFalse((self.root/'outside').exists())
        self.assertFalse((self.root/'extract').exists())

    def test_archive_symlink_rejected(self):
        archive=self.root/'bad.zip'
        info=zipfile.ZipInfo('KanaShift/_internal/link');info.external_attr=(stat.S_IFLNK|0o777)<<16
        with zipfile.ZipFile(archive,'w') as out: out.writestr(info,'../../outside')
        with self.assertRaises(core.UpdateError): core.extract_package(archive,self.root/'extract','0.7.8',threading.Event())

    def test_archive_limits(self):
        archive=self.root/'big.zip'
        with zipfile.ZipFile(archive,'w') as out: out.writestr('KanaShift/_internal/a',b'12345')
        with patch.object(core,'MAX_EXPANDED',4):
            with self.assertRaises(core.UpdateError): core.extract_package(archive,self.root/'extract','0.7.8',threading.Event())

    def test_cancelled_extraction_cleans_staging(self):
        source=payload(self.root/'source'); archive=package(source,self.root/'release','0.7.8')
        cancel=threading.Event();cancel.set()
        with self.assertRaises(core.UpdateCancelled): core.extract_package(archive,self.root/'extract','0.7.8',cancel)
        self.assertFalse((self.root/'extract').exists())

    def test_verified_download_and_checksum_failure(self):
        data=b'example zip'; digest=hashlib.sha256(data).hexdigest()
        release=core.Release('0.7.8','https://github.com/luttechan/KanaShift/releases/latest',
                             'https://github.com/luttechan/KanaShift/releases/download/v0.7.8/test.zip','test.zip',len(data),'sha256:'+digest)
        with patch.object(core,'open_url',return_value=io.BytesIO(data)):
            core.download(release,self.root/'good.zip',threading.Event())
        self.assertEqual((self.root/'good.zip').read_bytes(),data)
        with patch.object(core,'open_url',return_value=io.BytesIO(b'corrupt zip')):
            with self.assertRaises(core.UpdateError): core.download(release,self.root/'bad.zip',threading.Event())
        self.assertFalse((self.root/'bad.zip').exists())

    def test_missing_digest_refuses_automatic_install(self):
        release=core.Release('0.7.8','page','url','name',100,'')
        with self.assertRaises(core.UpdateError): core.download(release,self.root/'bad.zip',threading.Event())


class ReplacementTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)
        self.new=payload(self.root/'payload')
        self.target=payload(self.root/'installed','0.7.7',b'old')
        (self.target/'_internal'/'obsolete.dll').write_bytes(b'old library')
        (self.target/'personal-notes.txt').write_text('keep me')

    def test_complete_runtime_replaced_settings_and_other_files_retained(self):
        verified=Mock()
        replace_runtime(self.new,self.target,'0.7.8',verified)
        verified.assert_called_once()
        self.assertEqual((self.target/'KanaShift.exe').read_bytes(),b'MZnew')
        self.assertFalse((self.target/'_internal'/'obsolete.dll').exists())
        self.assertEqual((self.target/'personal-notes.txt').read_text(),'keep me')
        self.assertFalse(list(self.target.glob('.kanashift-update-*')))

    def test_startup_failure_restores_old_runtime(self):
        def fail(): raise RuntimeError('new startup failed')
        with self.assertRaises(RuntimeError): replace_runtime(self.new,self.target,'0.7.8',fail)
        self.assertEqual((self.target/'KanaShift.exe').read_bytes(),b'MZold')
        self.assertTrue((self.target/'_internal'/'obsolete.dll').exists())
        self.assertEqual((self.target/'personal-notes.txt').read_text(),'keep me')

    def test_partial_install_failure_rolls_back(self):
        original=os.replace
        def replace(src,dst):
            if Path(src).parent.name=='incoming' and Path(src).name=='_internal':
                raise OSError('simulated sharing violation')
            return original(src,dst)
        with patch('update_apply.os.replace',side_effect=replace):
            with self.assertRaises(OSError): replace_runtime(self.new,self.target,'0.7.8')
        self.assertEqual((self.target/'KanaShift.exe').read_bytes(),b'MZold')
        self.assertTrue((self.target/'_internal'/'obsolete.dll').exists())

    def test_verification_failure_never_changes_installed_files(self):
        (self.new/'KanaShift.exe').write_bytes(b'MZtampered')
        with self.assertRaises(core.UpdateError): replace_runtime(self.new,self.target,'0.7.8')
        self.assertEqual((self.target/'KanaShift.exe').read_bytes(),b'MZold')
