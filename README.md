# KanaShift

A keyboard input switcher for Windows.

## How to Use

1. On first launch, choose a display language and set up 1–15 input modes from the keyboards installed on your PC.
2. Press **CapsLock + Q** to open the input selector. You can change this shortcut in **Settings**.
3. Use the **arrow keys** or **1–9, 0, A–E** to select an input mode. Press **Enter** to switch or **Esc** to close.

**ON/OFF:** Dashboard or tray menu. Default: ON.

**To run from source:** Install Python 3.10 or later, run `install.bat` once, then launch with `run.bat`.

## Compatibility

- **Operating systems:** Windows 10 and Windows 11
- **Input methods:** Windows keyboard layouts and IMEs installed on your PC
- **Source version:** Python 3.10+ (dependencies installed by `install.bat`)
- **Packaged Windows application:** Does not require Python to be installed

---

# 한국어 설명

Windows용 키보드 입력 언어 전환 프로그램입니다.

## 사용 방법

1. PC에 설치된 키보드 입력기 중에서 1-15개의 입력 모드를 설정합니다.
2. **CapsLock + Q**를 눌러 입력 모드 선택 창을 엽니다. 단축키는 설정에서 변경할 수 있습니다.
3. **방향키** 또는 **1–9, 0, A–E**으로 원하는 입력 모드를 선택합니다. **Enter**를 누르면 입력 모드가 전환되며, **Esc**를 누르면 선택 창이 닫힙니다.

**ON/OFF:** 대시보드·트레이 메뉴. 실행 시 기본 ON.

Python 3.10 이상을 설치한 후 `install.bat`을 한 번 실행하여 필요한 패키지를 설치합니다. 이후 `run.bat`을 실행하면 프로그램이 시작됩니다.

## 호환성

- **지원 운영체제:** Windows 10 및 Windows 11
- **지원 입력 방식:** PC에 설치된 Windows 키보드 레이아웃 및 IME(입력기)
- **소스 코드 실행:** Python 3.10 이상 필요
- **Windows 패키지 버전:** Python을 별도로 설치하지 않아도 실행 가능

---

## Version History

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
- Windows build: `KanaShift.exe`, `module/`
- `module/`: code, fonts, icons, tests, build tools

## Credits

**Developed by Lutté**

This project was developed with the assistance of **OpenAI's ChatGPT, powered by the GPT-6 Astra model**, which was utilized throughout the development process for code generation, debugging, optimization, and technical consultation.
