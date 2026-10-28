import unittest
from unittest.mock import patch
import build_security

class BuildSecurityTests(unittest.TestCase):
 def test_current_security_toolchain_is_accepted(self):
  self.assertEqual(build_security.verify()['pyinstaller'],'6.22.3')
 def test_vulnerable_onefile_bootloader_cannot_be_reintroduced(self):
  original=build_security.importlib.metadata.version
  with patch.object(build_security.importlib.metadata,'version',side_effect=lambda name:'6.22.0' if name=='PyInstaller' else original(name)):
   with self.assertRaisesRegex(RuntimeError,'PyInstaller'):build_security.verify()
 def test_older_python_is_rejected_before_packaging(self):
  with patch.object(build_security.sys,'version_info',(3,12,14)),self.assertRaisesRegex(RuntimeError,'Python'):build_security.verify()
 def test_older_openssl_is_rejected_before_packaging(self):
  with patch.object(build_security.ssl,'OPENSSL_VERSION_INFO',(3,5,0,8,0)),self.assertRaisesRegex(RuntimeError,'OpenSSL'):build_security.verify()
