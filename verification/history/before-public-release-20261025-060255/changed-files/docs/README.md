# Lexift 1.0

Windows language switching, plus Korean pronunciation input for Japanese and Chinese. Formerly KanaShift.

[Releases](https://github.com/luttechan/Lexift/releases)

- Caps Lock + Q: choose an installed input method.
- Caps Lock + A: Korean pronunciation → Japanese candidates.
- Caps Lock + C: Korean pronunciation → simplified Chinese candidates.
- Enable each feature independently next to its shortcut in Settings.
- Conversion can only be enabled when the Korean IME is in Hangul mode.
- Custom dictionary: register a Hangul keyword, replacement text and conversion language. For example, `스미네 / 澄音 / Korean–Japanese`.
- The supplied `notify.wav` is used for application notifications.

Run `dist/Lexift/Lexift.exe`, or use `install.bat` and `run.bat` for the source version. Existing KanaShift preferences are imported once into a new Lexift configuration.

## 한국어

Windows 입력기 선택과 한글 발음으로 일본어·중국어를 입력하는 프로그램입니다. KanaShift의 새 이름은 Lexift입니다.

일반 설정에서 **언어 스위칭**과 **한–일·한–중 변환**을 별도 박스로 구분합니다. 단축키 옆의 **사용** 체크박스로 세 기능의 사용 여부를 각각 저장할 수 있습니다. 단축키 중복은 저장할 수 없습니다.

한–일·한–중 기능은 한국어 IME의 **한글** 상태에서만 켜집니다. 원래 프로그램의 입력란에 한글 발음을 입력한 뒤 커서 근처의 후보를 Space·Enter·숫자 또는 클릭으로 확정하세요.

**사용자 사전**은 후보에 없는 이름·단어를 등록할 때 사용합니다. `스미네 / 澄音 / 한–일 변환`처럼 등록하면 해당 키워드를 입력할 때 첫 후보로 표시됩니다. 등록 항목을 자동 확정하지 않으며 기존 후보도 유지합니다.

자세한 내용은 [한국어 사용 안내](README_1.0.ko.md), [중국어 입력 규칙](CHINESE_INPUT.ko.md), [호환성](COMPATIBILITY.ko.md)을 확인하세요. 모든 입력 프로그램에서 동일한 접근성·IME 동작을 보장하지는 않습니다.
