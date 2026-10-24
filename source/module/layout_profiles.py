from __future__ import annotations

from dataclasses import dataclass
import ctypes
import locale
import sys
from functools import lru_cache
from ctypes import wintypes
from i18n import tr

LANG_KO = 0x0412
MAX_SLOTS = 15
LANG_JA = 0x0411
SIMPLIFIED_CHINESE = frozenset({0x0804, 0x1004})  # zh-CN, zh-SG
TRADITIONAL_CHINESE = frozenset({0x0404, 0x0C04, 0x1404})  # TW, HK, MO


@dataclass(frozen=True)
class LayoutInfo:
    hkl: str
    langid: int
    name: str
    tag: str
    family: str
    symbol: str
    is_ime: bool = False

    @property
    def display(self) -> str:
        return f"{localized_name(self)}  ·  {self.tag}  ({self.hkl[-8:]})"


def localized_name(layout: LayoutInfo) -> str:
    key = {0x12:'한국어', 0x11:'일본어', 0x04:'중국어', 0x09:'영어',
           0x19:'러시아어', 0x0A:'스페인어', 0x0C:'프랑스어', 0x07:'독일어'}.get(layout.langid & 0x03FF)
    return tr(key) if key else layout.name


def hkl_string(value: int) -> str:
    """Round-trip 32/64 bit pointer-valued HKLs without losing high bits."""
    return f"{int(value) & ((1 << (ctypes.sizeof(ctypes.c_void_p) * 8)) - 1):0{ctypes.sizeof(ctypes.c_void_p) * 2}X}"


def hkl_number(value: str) -> int:
    return int(value, 16)


def classify(langid: int) -> tuple[str, str]:
    if langid == LANG_KO:
        return "korean", "한"
    if langid == LANG_JA:
        return "japanese", "あ"
    if langid in SIMPLIFIED_CHINESE:
        return "chinese_simple", "简"
    if langid in TRADITIONAL_CHINESE:
        return "chinese_traditional", "繁"
    if langid & 0x03FF == 0x0004:  # Other Chinese LCID: don't promise specific script
        return "chinese_other", "中"
    special = {
        0x09: ("standard", "EN"), 0x19: ("standard", "Я"),
        0x0A: ("standard", "ES"), 0x0C: ("standard", "FR"),
        0x07: ("standard", "DE"), 0x16: ("standard", "PT"),
        0x01: ("standard", "ع"), 0x1F: ("standard", "TR"),
    }
    return special.get(langid & 0x03FF, ("standard", "⌨"))


def mode_options(layout: str | LayoutInfo) -> list[tuple[str, str]]:
    family = layout.family if isinstance(layout, LayoutInfo) else layout
    is_ime = layout.is_ime if isinstance(layout, LayoutInfo) else family.startswith("chinese")
    if family == "korean":
        return [("ko_hangul", "한국어"), ("ko_latin", "영어"), ("default", "현재 설정 유지")]
    if family == "japanese":
        return [("ja_hiragana", "일본어 · 히라가나"),
                ("ja_katakana_full", "가타카나 · 전각"),
                ("ja_katakana_half", "가타카나 · 반각"),
                ("ja_katakana_ask", "가타카나 · 매번 선택"),
                ("ime_latin", "영어"),
                ("default", "현재 설정 유지")]
    if is_ime:
        return [("ime_native", "중국어" if family.startswith("chinese") else localized_name(layout)),
                ("ime_latin", "영어"), ("default", "현재 설정 유지")]
    return [("default", "키보드 / 입력기 전환")]


def preferred_mode(layout: LayoutInfo) -> str:
    return {"korean": "ko_hangul", "japanese": "ja_hiragana"}.get(
        layout.family, "ime_native" if layout.is_ime else "default")


def default_name(layout: LayoutInfo, mode: str) -> str:
    names = {"ko_hangul": "한국어", "ko_latin": "English", "ime_latin": "English",
             "ja_hiragana": "日本語", "ja_katakana_full": "カタカナ · 全角",
             "ja_katakana_half": "ｶﾀｶﾅ · 半角", "ja_katakana_ask": "カタカナ"}
    return names.get(mode, localized_name(layout))


@lru_cache(maxsize=256)
def _locale_info(langid: int) -> tuple[str, str]:
    tag = locale.windows_locale.get(langid, f"0x{langid:04X}").replace("_", "-")
    fallback = {0x0412:"한국어",0x0411:"日本語",0x0804:"중국어 (간체)",
                0x0404:"중국어 (번체·대만)",0x0c04:"중국어 (번체·홍콩)",
                0x0419:"러시아어",0x040a:"스페인어",0x040c:"프랑스어",0x0409:"English"}
    name = fallback.get(langid, tag)
    if sys.platform == "win32":
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.GetLocaleInfoW.argtypes = [wintypes.DWORD, wintypes.DWORD,
                                            wintypes.LPWSTR, ctypes.c_int]
        kernel32.GetLocaleInfoW.restype = ctypes.c_int
        # LOCALE_SLOCALIZEDDISPLAYNAME: OS display language's name of locale.
        for constant in (0x00000002,):  # LOCALE_SLANGUAGE
            buf = ctypes.create_unicode_buffer(160)
            if kernel32.GetLocaleInfoW(langid, constant, buf, len(buf)) > 0 and buf.value:
                name = buf.value
                break
    return name, tag


@lru_cache(maxsize=256)
def ime_capabilities(hkl: int) -> tuple[bool, bool]:
    if sys.platform != "win32":
        return False, False
    imm = ctypes.WinDLL("imm32", use_last_error=True)
    imm.ImmIsIME.argtypes = [ctypes.c_void_p]
    imm.ImmIsIME.restype = wintypes.BOOL
    imm.ImmGetProperty.argtypes = [ctypes.c_void_p, wintypes.DWORD]
    imm.ImmGetProperty.restype = wintypes.DWORD
    native = bool(imm.ImmGetProperty(hkl, 8) & 1)  # IGP_CONVERSION / IME_CMODE_NATIVE
    return bool(imm.ImmIsIME(hkl)) or native, native


def create_layout(hkl: int, name: str | None = None) -> LayoutInfo:
    langid = int(hkl) & 0xFFFF
    family, symbol = classify(langid)
    system_name, tag = _locale_info(langid)
    return LayoutInfo(hkl_string(hkl), langid, name or system_name, tag, family, symbol,
                      ime_capabilities(hkl)[0])


def available_layouts() -> list[LayoutInfo]:
    if sys.platform != "win32":
        return []
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.GetKeyboardLayoutList.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_void_p)]
    user32.GetKeyboardLayoutList.restype = ctypes.c_int
    count = user32.GetKeyboardLayoutList(0, None)
    if not count:
        return []
    slots = (ctypes.c_void_p * count)()
    n = user32.GetKeyboardLayoutList(count, slots)
    unique: dict[str, LayoutInfo] = {}
    for ptr in slots[:n]:
        if ptr:
            layout = create_layout(int(ptr))
            unique[layout.hkl] = layout
    return list(unique.values())


def initial_slots(layouts: list[LayoutInfo]) -> list[dict[str, str]]:
    """Auto-fill from currently available Windows input locales, not preset languages.

    A layout gets one slot by default. Users can assign multiple modes of the
    same installed IME in Settings; up to fifteen slots are supported.
    """
    result: list[dict[str, str]] = []
    for layout in layouts[:MAX_SLOTS]:
        mode = preferred_mode(layout)
        result.append({"hkl": layout.hkl, "mode": mode,
                       "name": default_name(layout, mode)})
    return result


def first_run_slots(layouts: list[LayoutInfo]) -> list[dict[str, str]]:
    """Offer precisely one editable slot, never force all available layouts."""
    return initial_slots(layouts)[:1]


def needs_first_run_setup(raw: object, layouts: list[LayoutInfo]) -> bool:
    """Respect existing profiles; reconfigure if every saved input method vanished."""
    available = {layout.hkl for layout in layouts}
    return not any(slot["hkl"] in available for slot in sanitized_slots(raw))


def installed_slots(raw: object, layouts: list[LayoutInfo]) -> list[dict[str, str]]:
    """Only expose usable input locales while retaining matching custom choices.

    Do not silently turn a Japanese IME mode into a Korean mode after the OS
    list changes. If all saved entries disappeared, populate from installed HKLs.
    """
    valid = {layout.hkl: layout for layout in layouts}
    result: list[dict[str, str]] = []
    for slot in sanitized_slots(raw):
        layout = valid.get(slot["hkl"])
        if not layout:
            continue
        if slot["mode"] not in {mode for mode, _ in mode_options(layout)}:
            slot = {**slot, "mode": "default"}
        result.append(slot)
    return result or initial_slots(layouts)


def sanitized_slots(raw: object) -> list[dict[str,str]]:
    """Only accept well formed 1..15-slot profiles from settings."""
    if not isinstance(raw, list):
        return []
    result = []
    for slot in raw[:MAX_SLOTS]:
        if not isinstance(slot, dict):
            continue
        hkl = slot.get("hkl", "")
        if not isinstance(hkl, str) or not hkl or len(hkl)>16:
            continue
        try:
            int(hkl, 16)
        except ValueError:
            continue
        mode = str(slot.get("mode", "default"))[:32]
        if mode not in {"default","ko_hangul","ko_latin","ja_hiragana",
                        "ja_katakana_full","ja_katakana_half","ja_katakana_ask",
                        "ime_native", "ime_latin"}:
            mode = "default"
        name = str(slot.get("name", ""))[:32].strip()
        # Match the current pointer width; old 32-bit identifiers are accepted
        # and zero/sign-extended only when resolving Windows-provided profiles.
        result.append({"hkl":hkl.upper(), "mode":mode, "name":name})
    return result


def editable_slots(raw: object, layouts: list[LayoutInfo]) -> list[dict[str, str]]:
    """Keep the user's unsaved choices, including temporarily missing HKLs.

    Only the UI's combobox choices are constrained to currently loaded layouts.
    Missing entries remain visible until the user fixes or removes them; saving
    such an entry is rejected by the editor.
    """
    slots = sanitized_slots(raw)
    if slots:
        return slots
    return first_run_slots(layouts)
