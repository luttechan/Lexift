"""Exercise actual separate-process native controls, rather than API mocks."""
import json
from pathlib import Path
import subprocess
import unittest

LAB=Path(__file__).resolve().parents[2]/'lab'


class CompatibilityAdapterTests(unittest.TestCase):
    def run_native(self,arguments):
        process=subprocess.run([str(arg) for arg in arguments],capture_output=True,timeout=20)
        self.assertEqual(process.returncode,0,process.stdout.decode('utf-8',errors='replace'))
        records=[json.loads(line) for line in process.stdout.decode('utf-8').splitlines() if line.strip()]
        self.assertEqual(records[-1]['failed'],0)
        self.assertTrue(records[-1]['cross_process'])
        return records[-1]

    @unittest.skipUnless((LAB/'native_edit_test.exe').is_file(),'build native compatibility tests first')
    def test_windows_edit_and_richedit_cross_process(self):
        result=self.run_native([LAB/'native_edit_test.exe'])
        self.assertGreaterEqual(result['passed'],17)

    @unittest.skipUnless((LAB/'scintilla_fixture32.exe').is_file() and Path('C:/Program Files (x86)/Notepad++/SciLexer.dll').is_file(),
                         'optional local 32-bit SciLexer fixture is unavailable')
    def test_actual_scintilla_cross_process_and_cross_bitness(self):
        result=self.run_native([LAB/'scintilla_test.exe',LAB/'scintilla_fixture32.exe'])
        self.assertGreaterEqual(result['passed'],10)
        self.assertTrue(result['cross_bitness'])
