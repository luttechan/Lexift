# NOW WE ARE LEXIFT.

**KanaShift, evolved. Switch languages. Type Hangul. Find your words in Japanese and Chinese.**

Lexift 1.0 keeps KanaShift's input switching and adds conversion from Korean pronunciation directly in supported text fields.

## What's new

- **CapsLock + Q:** Input language switching, with up to 15 input modes.
- **CapsLock + A / C:** Hangul → Japanese / Chinese candidates near the input field. Choose with Space, Enter, 1–9/0, or a click.
- **Custom dictionary:** Register a keyword, replacement text, and language; for example, `스미네 / 澄音 / Japanese`.
- **Independent feature switches and shortcuts:** Enable each feature separately and prevent duplicate shortcuts.
- **Faster settings navigation:** Reuse prepared pages, limit idle preparation to the viewport, and keep diagnostics inactive until requested.
- **Reliability:** Improve repeated Space confirmation, candidate numbering and scrolling, reading alternatives, caret placement, worker cleanup, and resource use.
- **New branding:** Original Lexift wordmark in the sidebar, dashboard, and About page, inverted for the dark interface while preserving transparency.
- **Migration and updates:** Import existing KanaShift preferences on first use and receive verified updates from `luttechan/Lexift`.

## 사용 방법

1. ZIP의 압축을 풀고 **Lexift/Lexift.exe**를 실행하세요. Python 설치가 필요하지 않습니다.
2. 첫 실행에서 표시 언어와 사용할 입력기 슬롯을 설정합니다.
3. **CapsLock + Q**로 입력 언어를 선택합니다. **CapsLock + A**는 한–일, **CapsLock + C**는 한–중 변환입니다.
4. 한국어 IME가 **한글 상태**일 때 변환 모드를 켜고 `와타시`, `니하오`처럼 입력합니다.
5. 일반 설정의 **언어 스위칭 / 한글 환경 언어 변환**에서 기능별 사용 여부와 단축키를 변경합니다.

## Requirements / 호환성

- Windows 10/11 x64.
- Japanese conversion requires Microsoft Japanese IME. Chinese conversion uses the bundled offline Pinyin dictionary and does not require a Chinese IME.
- Conversion is intended for Korean pronunciation input. Supported accessibility/edit-control paths include Edit/RichEdit, Scintilla, UI Automation, and IAccessible2. App-specific compatibility varies; protected/custom/elevated fields may be limited.
- 기존 버전을 종료한 뒤 실행하세요. 이 패키지는 기존 KanaShift 입력기 전환·설정·애셋을 계승합니다.

## Validation

- 398 regression tests passed.
- 51 native compatibility checks passed across Edit/RichEdit, IAccessible2 fixtures, and 32/64-bit Scintilla.
- 162 settings checks passed across nine interface languages in the packaged EXE.
- Packaged runtime, Japanese/Chinese candidate engines, feature settings, notification asset, and update package manifest verified.
- Repeated 60-window and 20-engine lifecycle checks passed; no GDI/user-handle growth or remaining engine threads in that test.

Actual Firefox end-to-end compatibility and every third-party app were not exercised in this release check. Settings navigation timings exclude the initial Qt application/font initialization.

**Files:** `Lexift-1.0.0-Windows-x64.zip` and its `.sha256` checksum.
