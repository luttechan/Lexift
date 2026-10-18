# KanaShift
A keyboard input switcher for Windows.

## How to Use

1. On first launch, choose a display language and set up 1–6 input modes from the keyboards installed on your PC.
2. Press **CapsLock + Q** to open the input selector. You can change this shortcut in **Settings**.
3. Use the **arrow keys** or **1–6** to select an input mode. Press **Enter** to switch or **Esc** to close.
4. Closing the main window keeps KanaShift running in the system tray. Use the tray icon to reopen it or select **Quit** to exit.
5. To change the interface language, go to **Settings → Display language**. Changes apply immediately.

**To run from source:** Install Python 3.10 or later, run `install.bat` once, then launch with `run.bat`.

## Compatibility

- **Operating systems:** Windows 10 and Windows 11
- **Input methods:** Windows keyboard layouts and IMEs installed on your PC
- **Source version:** Python 3.10+ (dependencies installed by `install.bat`)
- **Packaged Windows application:** Does not require Python to be installed

## Version History

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
