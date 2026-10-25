import ctypes,gc,unittest
from native_language_dialog import _dialog_types


class NativeDialogResourcesTests(unittest.TestCase):
    def test_native_dialog_types_do_not_accumulate_pointer_cache_entries(self):
        first=_dialog_types()
        before=len(ctypes._pointer_type_cache)
        for _ in range(500):
            self.assertIs(_dialog_types(),first)
            ctypes.POINTER(_dialog_types()[1])
        gc.collect()
        # Config's pointer can be registered once, never once per dialog.
        self.assertLessEqual(len(ctypes._pointer_type_cache)-before,1)
