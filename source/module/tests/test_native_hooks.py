"""Native/Python behavior parity, without installing global keyboard hooks."""
import ctypes
from ctypes import wintypes
import random
import unittest

from hotkeys_windows import CapsQState, OverlayKeyState
from native_hooks import library


class CapsState(ctypes.Structure):
    _fields_ = [(name, wintypes.DWORD) for name in
                ('trigger', 'held', 'used', 'suppressed', 'chord')]


class NativeHookTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dll = library()
        cls.dll.ks_caps_step.argtypes = [ctypes.POINTER(CapsState), wintypes.DWORD, wintypes.BOOL]
        cls.dll.ks_caps_step.restype = wintypes.DWORD
        cls.dll.ks_navigation_step.argtypes = [ctypes.POINTER(ctypes.c_ubyte), wintypes.DWORD,
                                               wintypes.BOOL, wintypes.BOOL, wintypes.BOOL]
        cls.dll.ks_navigation_step.restype = wintypes.DWORD

    def test_caps_chords_repeats_and_releases_match_existing_behavior(self):
        randomizer = random.Random(786)
        for trigger in (0x51, 0x31, 0x7B):
            reference, native = CapsQState(trigger), CapsState(trigger, 0, 0, 0, 0)
            for _ in range(15000):
                vk = randomizer.choice((0x14, trigger, 0x41, 0x11, 0x12))
                down = randomizer.choice((False, True))
                expected = reference.handle(vk, down)
                action = self.dll.ks_caps_step(ctypes.byref(native), vk, down)
                self.assertEqual(tuple(bool(action & bit) for bit in (1, 2, 4)), expected)

    def test_selector_keys_balanced_across_visibility_and_modifier_changes(self):
        randomizer = random.Random(787)
        reference, held = OverlayKeyState(), (ctypes.c_ubyte * 256)()
        for _ in range(30000):
            vk = randomizer.randrange(256)
            down, active, modified = (randomizer.choice((False, True)) for _ in range(3))
            expected = reference.handle(vk, down, active, modified)
            action = self.dll.ks_navigation_step(held, vk, down, active, modified)
            self.assertEqual((bool(action & 1), bool(action & 2)), expected)

    def test_hidden_selector_and_unmodified_ordinary_typing_are_passed_through(self):
        held = (ctypes.c_ubyte * 256)()
        native = CapsState(0x51, 0, 0, 0, 0)
        for _ in range(100):
            for vk in range(0x20, 0x7C):
                for down in (True, False):
                    self.assertEqual(self.dll.ks_caps_step(ctypes.byref(native), vk, down), 0)
                    self.assertEqual(self.dll.ks_navigation_step(held, vk, down, False, False), 0)

    def test_native_module_rejects_invalid_hook_kind(self):
        self.assertFalse(self.dll.ks_start(-1, 0, 0))
        self.assertFalse(self.dll.ks_start(2, 0, 0))

    def nav_event(self,held,vk=0x20,scan=0x39,down=True,mode=2,foreground=True,modified=False,injected=False):
        fn=self.dll.ks_navigation_event_step
        fn.argtypes=[ctypes.POINTER(ctypes.c_ubyte),wintypes.DWORD,wintypes.DWORD,wintypes.BOOL,
                     wintypes.DWORD,wintypes.BOOL,wintypes.BOOL,wintypes.BOOL]
        fn.restype=wintypes.DWORD
        return fn(held,vk,scan,down,mode,foreground,modified,injected)

    def test_ime_process_space_releases_the_same_held_key(self):
        held=(ctypes.c_ubyte*256)()
        self.assertEqual(self.nav_event(held),3)
        self.assertEqual(self.nav_event(held,vk=0xe5,down=False,mode=0),1)
        self.assertEqual(held[0x20],0)
        self.assertEqual(self.nav_event(held,vk=0xe5),3)
        self.assertEqual(self.nav_event(held,down=False,mode=0),1)

    def test_lost_space_release_recovers_after_new_text_without_repeating(self):
        held=(ctypes.c_ubyte*256)()
        self.assertEqual(self.nav_event(held),3)
        for _ in range(20):self.assertEqual(self.nav_event(held),1)
        self.assertEqual(self.nav_event(held,vk=ord('R'),scan=0x13,mode=0),0)
        self.assertEqual(self.nav_event(held),3)
        self.assertEqual(self.nav_event(held,vk=0xe5,down=False,injected=True),0)
        self.assertEqual(held[0x20],0)
        self.assertEqual(self.nav_event(held,vk=0xe5,injected=True),0)
        self.assertEqual(self.nav_event(held),3)

    def test_process_key_other_scans_and_wrong_window_are_not_commands(self):
        held=(ctypes.c_ubyte*256)()
        self.assertEqual(self.nav_event(held,vk=0xe5,scan=0x1e),0)
        self.assertEqual(self.nav_event(held,foreground=False),0)
        self.assertEqual(self.nav_event(held,modified=True),0)

    def test_pending_commit_swallows_double_space_without_a_second_command(self):
        held=(ctypes.c_ubyte*256)()
        self.assertEqual(self.nav_event(held),3)
        self.assertEqual(self.nav_event(held,down=False,mode=3),1)
        self.assertEqual(self.nav_event(held,mode=3),1)
        self.assertEqual(self.nav_event(held,down=False,mode=3),1)
        self.assertEqual(self.nav_event(held,mode=0),0)
        self.assertEqual(self.nav_event(held,vk=ord('A'),mode=3),0)
        self.assertEqual(self.nav_event(held,mode=3,foreground=False),0)

    def test_inline_space_is_accepted_once_and_balances_release_after_hide(self):
        self.dll.ks_inline_key.argtypes=[wintypes.DWORD]
        self.dll.ks_inline_key.restype=wintypes.BOOL
        self.assertTrue(self.dll.ks_inline_key(0x20));self.assertFalse(self.dll.ks_inline_key(0x41))
        held=(ctypes.c_ubyte*256)()
        self.assertEqual(self.dll.ks_navigation_step(held,0x20,True,True,False),3)
        self.assertEqual(self.dll.ks_navigation_step(held,0x20,True,True,False),1)
        self.assertEqual(self.dll.ks_navigation_step(held,0x20,False,False,False),1)
        self.assertEqual(self.dll.ks_navigation_step(held,0x20,True,False,False),0)

    def test_inline_numbers_repeat_release_and_modified_passthrough(self):
        self.dll.ks_inline_key.argtypes=[wintypes.DWORD]
        self.dll.ks_inline_key.restype=wintypes.BOOL
        for vk in (*range(0x30,0x3a),*range(0x60,0x6a)):
            with self.subTest(vk=vk):
                self.assertTrue(self.dll.ks_inline_key(vk))
                held=(ctypes.c_ubyte*256)()
                self.assertEqual(self.dll.ks_navigation_step(held,vk,True,True,True),0)
                self.assertEqual(self.dll.ks_navigation_step(held,vk,True,True,False),3)
                self.assertEqual(self.dll.ks_navigation_step(held,vk,True,True,False),1)
                self.assertEqual(self.dll.ks_navigation_step(held,vk,False,False,False),1)
                self.assertEqual(self.dll.ks_navigation_step(held,vk,True,False,False),0)
