# KanaShift 0.7.7 — Final QA

2026-10-20 · Windows · x64

## Checks

- Python 3.12 / PySide6 6.12: 244 regression tests passed
- Python 3.14.6 / PySide6 6.12: 244 regression tests passed from the deployed G: source folder
- Pixel scrolling across partial rows; wheel over selectors preserves input choice
- Source and portable module layouts; legacy migration and rollback
- About links: local SVG rendering and exact browser destinations
- Nine display languages · Four pages · Fifteen slots
- Unsaved edits · Slot order · New-slot scrolling · Selector reuse
- Exit confirmation · Cancel / reopen · Keyboard input during confirmation
- Ten OFF/ON cycles · Shortcut replacement · Worker crash recovery
- Korean / English · Japanese Hiragana / full-width Katakana / half-width Katakana
- Native / English round trips for all three locally installed IMEs
- Update checks · UI responsiveness · Cancellation · Version comparisons
- Native updater: parent exit, runtime replacement, restart acknowledgement, cleanup
- Rollback, invalid archives, path validation and hash mismatch: regression tests
- Live GitHub check: stable tag `v0.7.6`

## Local timings

Built application code and its actual Windows keyboard worker. Temporary settings.

| Action | Measurement |
| --- | ---: |
| Menu first display, maximum across nine languages | 54 ms |
| Cached menu display, maximum | 11 ms |
| Cached fifteen-slot selector rebuild, maximum | 1 ms |
| Display-language change, maximum | 624 ms |
| Exit confirmation first paint | 4 ms |
| OFF response, maximum across ten cycles | 2 ms |
| Keyboard worker exit after confirmed quit | 15 ms |

Update checks continued processing GUI timer events while awaiting a result.

## Remaining limits

- First main-window preparation: 335 ms in this build QA run. Earlier cold runs took 2.7–3.9 seconds; initial Qt font/layout preparation varies. These are not end-to-end launch timings.
- IME checks used a private native text field. No physical keystrokes or text entered into user applications. Every Windows language, third-party IME and application has not been tested.
- Native updater checks used an isolated test installation. The user's active installation was not updated through the installer during QA.
- Timings are local measurements, not guarantees for every PC.

## Build fingerprints

- EXE SHA-256: `83aebcd8a6148efccb94b3609b3aca913074ae744d13488fab88102f2cf2246b`
- ZIP SHA-256: `da547fb5310565d950b817ab47b766b00edba45a70a17450e6f6708f6a6facd6`
