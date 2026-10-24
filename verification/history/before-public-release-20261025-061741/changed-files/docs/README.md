# NOW WE ARE LEXIFT.

**KanaShift, evolved. Switch languages. Type Hangul. Find your words in Japanese and Chinese.**

Your familiar input switcher, with a new name and more ways to write.

[Download Lexift for Windows](https://github.com/luttechan/Lexift/releases/latest)

---

# Lexift

A keyboard input switcher for Windows, with Japanese and Chinese conversion from Hangul pronunciation.

## How to Use

1. On first launch, choose a display language and set up 1–15 input modes from the keyboards installed on your PC.
2. Press **CapsLock + Q** to open the input selector. You can change this shortcut in **Settings**.
3. Use the **arrow keys** or **1–9, 0, A–E** to select an input mode. Press **Enter** to switch or **Esc** to close.

**Hangul conversion:** Press **CapsLock + A** for Japanese or **CapsLock + C** for Chinese. In a supported text field, type a Korean pronunciation such as `와타시` or `니하오`, then choose a candidate with **Space**, **Enter**, **1–9 / 0**, or a click. Conversion can only be enabled while the Korean IME is in Hangul mode.

**ON/OFF:** Dashboard or tray menu. Default: ON. Enable each feature independently beside its shortcut in **Settings**.

**To run from source:** Install Python 3.10 or later, run `install.bat` once, then launch with `run.bat`.

## Compatibility

- **Operating systems:** Windows 10 and Windows 11
- **Input methods:** Windows keyboard layouts and IMEs installed on your PC
- **Source version:** Python 3.10+ (dependencies installed by `install.bat`)
- **Packaged Windows application:** Does not require Python to be installed
- **Japanese conversion:** Microsoft Japanese IME must be installed
- **Chinese conversion:** Bundled offline Pinyin dictionary; no Chinese IME required
- **Editable text fields:** Windows Edit/RichEdit, Scintilla, UI Automation, and IAccessible2 paths. Support depends on the application; protected fields, elevated apps, and custom editors may be limited.

---

# 한국어 설명

입력 언어 전환을 넘어, 한글 발음으로 일본어·중국어까지. **KanaShift는 이제 Lexift입니다.**

Windows용 키보드 입력 언어 전환 프로그램에 한글 발음 변환 기능을 더했습니다.

## 사용 방법

1. PC에 설치된 키보드 입력기 중에서 1-15개의 입력 모드를 설정합니다.
2. **CapsLock + Q**를 눌러 입력 모드 선택 창을 엽니다. 단축키는 설정에서 변경할 수 있습니다.
3. **방향키** 또는 **1–9, 0, A–E**으로 원하는 입력 모드를 선택합니다. **Enter**를 누르면 입력 모드가 전환되며, **Esc**를 누르면 선택 창이 닫힙니다.

**한글 환경 언어 변환:** **CapsLock + A**는 한–일, **CapsLock + C**는 한–중 변환입니다. 지원하는 프로그램의 입력란에 `와타시`, `니하오`처럼 입력하고 **Space·Enter·숫자 1~9/0·클릭**으로 후보를 확정합니다. 한국어 IME의 한글 상태에서만 켤 수 있습니다.

**ON/OFF:** 대시보드·트레이 메뉴. 실행 시 기본 ON. 일반 설정에서 각 단축키 옆의 **사용** 체크박스로 세 기능을 개별 설정합니다.

Python 3.10 이상을 설치한 후 `install.bat`을 한 번 실행하여 필요한 패키지를 설치합니다. 이후 `run.bat`을 실행하면 프로그램이 시작됩니다.

## 호환성

- **지원 운영체제:** Windows 10 및 Windows 11
- **지원 입력 방식:** PC에 설치된 Windows 키보드 레이아웃 및 IME(입력기)
- **소스 코드 실행:** Python 3.10 이상 필요
- **Windows 패키지 버전:** Python을 별도로 설치하지 않아도 실행 가능
- **일본어 변환:** Microsoft 일본어 IME 설치 필요
- **중국어 변환:** 내장 오프라인 병음 사전 사용, 중국어 IME 설치 불필요
- **입력란 호환성:** Windows Edit/RichEdit, Scintilla, UI Automation, IAccessible2 경로 지원. 앱별 지원 범위는 다르며 암호 입력란·관리자 권한 앱·일부 사용자 정의 편집기는 제한됩니다.

---

## Version History

### 1.0.0 — Lexift

- KanaShift is now Lexift
- Japanese and Chinese candidates from Hangul pronunciation
- Independent feature switches, custom shortcuts, and a custom dictionary
- Faster settings navigation and safer candidate confirmation
- New branding and Lexift release/update integration

### 0.7.8

- Faster startup
- Live RAM usage and runtime information
- Collapsible runtime information
- Lower translation overhead
- Complete interface translations
- Localized dialogs and error messages
- Lower font memory usage
- Layout cleanup and final QA

### 0.7.7

- ON/OFF toggle
- 15 input slots
- Faster input selector
- Language / English modes
- New-slot auto-scroll
- Faster exit confirmation and shutdown
- Faster ON/OFF response
- Faster language switching
- Fewer IME delays
- Keyboard worker recovery fixes
- Pixel-based slot scrolling
- Scroll-safe input selectors
- Organized module folder
- Check for updates
- Verified downloads and installation
- Automatic restart and recovery

### 0.7.6

- Input language indicator near cursor
- File Explorer language switching fix
- Exit confirmation dialog
- Faster startup
- Faster Settings and About pages
- Switch cancellation on focus change

### 0.7.5

- Tray notification after closing main window
- Arrow key navigation improvements

### 0.7.4

- Malgun Gothic font
- First-run language selection improvements

### 0.7.3

- Nine interface languages
- Instant interface language changes

---

## Files

- Source: `launch.pyw`, launch scripts, `module/`
- Windows build: `Lexift.exe`, `module/`
- `module/`: code, fonts, logos, notification sound, dictionaries, tests, build tools
- `lab/`: native Japanese IME host source/build tools and compatibility checks
- Portable download: [Lexift releases](https://github.com/luttechan/Lexift/releases)

## Credits

**Developed by Lutté**

This project was developed with the assistance of **OpenAI's ChatGPT, powered by the GPT-6 Astra model**, which was utilized throughout the development process for code generation, debugging, optimization, and technical consultation.

---

## What's New in Lexift

- **Hangul → Japanese / Chinese:** Candidates appear near the active text field. Japanese uses Microsoft Japanese IME; Chinese uses an offline dictionary.
- **Pronunciation alternatives:** Japanese long vowels with `-`, common spelling variants, and multiple Korean spellings for Pinyin, including `췐 → quan`.
- **Custom dictionary:** Register a keyword, replacement text, and language. Example: `스미네 / 澄音 / Japanese`.
- **Independent controls:** Enable input switching, Japanese conversion, and Chinese conversion separately. Change shortcuts and block duplicate combinations.
- **Settings:** Separate **Language switching** and **Language conversion from Hangul** sections, nine UI languages, and Korean-speaker guidance in English/Japanese.
- **Responsiveness and reliability:** Reused settings pages, bounded preparation of visible content, duplicate-confirmation protection, candidate numbering/scroll fixes, and worker/cache cleanup.
- **Branding and updates:** The Lexift logo, the supplied notification sound, one-time KanaShift preference migration, and verified updates from this repository.

## Lexift에서 추가된 기능

- **한글 → 일본어·중국어:** 원래 입력하던 칸 근처에 후보를 표시합니다. 일본어는 Microsoft 일본어 IME, 중국어는 오프라인 사전을 사용합니다.
- **발음 해석 확장:** `코-죠-` 같은 대시 장음, 일본어 관용 철자·복수 독음, `췐 → quan` 등 다양한 한글 병음 표기를 처리합니다.
- **사용자 사전:** 키워드·대치할 텍스트·언어를 등록합니다. 예: `스미네 / 澄音 / 한–일`.
- **기능별 작동 설정:** 언어 스위칭·한–일·한–중을 각각 켜고 끄며 단축키를 변경합니다. 겹치는 단축키는 적용할 수 없습니다.
- **설정 화면:** **언어 스위칭**과 **한글 환경 언어 변환**을 구분했습니다. 9개 UI 언어와 영어·일본어 사용 안내를 제공합니다.
- **반응성·안정성:** 설정 화면 재사용, 화면 크기로 제한한 사전 준비, 중복 확정 방지, 후보 번호·스크롤 및 작업자·캐시 정리를 개선했습니다.
- **새 이름과 업데이트:** Lexift 로고·지정 알림음, 기존 KanaShift 설정의 최초 가져오기, 이 저장소와 연결된 검증 업데이트를 적용했습니다.
