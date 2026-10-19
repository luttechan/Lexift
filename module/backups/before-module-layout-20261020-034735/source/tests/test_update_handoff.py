import json
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import Mock, patch

from test_updates import payload
import update_apply as apply
from update_core import UpdateError


class HandoffTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.base=Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)
        self.cache=self.base/'cache';self.cache.mkdir()
        self.job=self.cache/uuid.uuid4().hex;self.job.mkdir()
        self.target=payload(self.base/'installed','0.7.7',b'old')
        self.new=payload(self.job/'unpacked'/'KanaShift','0.7.8')
        self.data=dict(product='KanaShift',nonce=self.job.name,target=str(self.target),
                       payload=str(self.new),version='0.7.8',parent_pid=123)
        self.path=self.job/'job.json';self.path.write_text(json.dumps(self.data))
        self.cache_patch=patch.object(apply,'cache_root',return_value=self.cache)
        self.cache_patch.start();self.addCleanup(self.cache_patch.stop)
        self.kernel=Mock();self.kernel.WaitForSingleObject.return_value=0

    def test_job_validation_accepts_only_scoped_staging(self):
        self.assertEqual(apply.load_job(self.path)['version'],'0.7.8')
        outside=self.base/'job.json';outside.write_text(json.dumps(self.data))
        with self.assertRaises(UpdateError): apply.load_job(outside)

    def test_wrong_embedded_app_version_cannot_acknowledge(self):
        with patch.object(apply.sys,'frozen',True,create=True), \
             patch.object(apply.sys,'executable',str(self.target/'KanaShift.exe')), \
             patch.object(apply.sys,'argv',['KanaShift.exe','--update-job',str(self.path)]):
            apply.mark_ready('0.7.7')
            self.assertFalse((self.job/'ready').exists())
            apply.mark_ready('0.7.8')
        self.assertEqual((self.job/'ready').read_text(),self.job.name)

    def test_parent_timeout_leaves_runtime_untouched(self):
        self.kernel.WaitForSingleObject.return_value=258
        with patch.object(apply,'parent_handle',return_value=(self.kernel,1)), \
             patch.object(apply.subprocess,'Popen') as spawn:
            with self.assertRaises(UpdateError): apply.run_job(self.path)
        spawn.assert_not_called()
        self.assertEqual((self.target/'KanaShift.exe').read_bytes(),b'MZold')

    def test_external_handoff_wait_replace_ack_and_cleanup(self):
        child=Mock();child.poll.return_value=None
        def spawn(args,**kwargs):
            self.assertIn('--update-job',args)
            self.assertEqual((self.target/'KanaShift.exe').read_bytes(),b'MZnew')
            (self.job/'ready').write_text(self.job.name)
            return child
        with patch.object(apply,'parent_handle',return_value=(self.kernel,1)), \
             patch.object(apply.subprocess,'Popen',side_effect=spawn):
            apply.run_job(self.path)
        self.kernel.WaitForSingleObject.assert_called_once_with(1,60000)
        self.assertTrue((self.job/'completed').exists())
        self.assertFalse((self.job/'unpacked').exists())
        self.assertEqual((self.target/'KanaShift.exe').read_bytes(),b'MZnew')

    def test_failed_new_process_restores_and_restarts_old_app(self):
        child=Mock();child.poll.return_value=7
        with patch.object(apply,'parent_handle',return_value=(self.kernel,1)), \
             patch.object(apply.subprocess,'Popen',return_value=child) as spawn:
            with self.assertRaises(UpdateError): apply.run_job(self.path)
        self.assertEqual(spawn.call_count,2)
        self.assertNotIn('--update-job',spawn.call_args.args[0])
        self.assertEqual((self.target/'KanaShift.exe').read_bytes(),b'MZold')
        self.assertFalse((self.job/'completed').exists())

