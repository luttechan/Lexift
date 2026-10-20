"""The interactive process must not initialize the network transport at boot."""
import os, subprocess, sys, unittest
from pathlib import Path
from unittest.mock import Mock, patch
import urllib.request
import update_core


class StartupImportTests(unittest.TestCase):
    def test_app_boot_does_not_load_http_or_tls(self):
        environment=os.environ.copy()
        environment['PYTHONPATH']=str(Path(__file__).resolve().parents[1])
        # PySide itself imports zipfile; only the isolated HTTP/TLS stack is
        # expected to be absent from the interactive process at boot.
        code="import sys,app; assert not ({'urllib.request','ssl'} & sys.modules.keys())"
        result=subprocess.run([sys.executable,'-B','-c',code],env=environment,
                              capture_output=True,text=True,timeout=15)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_deferred_transport_still_rejects_untrusted_redirects(self):
        opened=Mock()
        with patch.object(urllib.request,'build_opener',return_value=opened) as builder:
            update_core.open_url(update_core.API_URL)
        handler=builder.call_args.args[0]
        with self.assertRaises(update_core.UpdateError):
            handler.redirect_request(None,None,302,'redirect',{},'https://untrusted.example/payload')
        with self.assertRaises(update_core.UpdateError):
            handler.redirect_request(None,None,302,'redirect',{},'http://github.com/payload')
        self.assertEqual(opened.open.call_count,1)
