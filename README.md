# Lexift 1.2

한글 발음으로 일본어와 중국어를 입력하는 Windows 도구입니다.

[Windows 설치기](https://github.com/luttechan/Lexift/releases/latest) · [공식 사이트 및 사용 설명서](https://luttechan.github.io/lexift/)

- 일본어 입력 중 후보창이 사라지는 경로 개선
- 단축키 등록 실패 알림 추가
- IME 엔진 재빌드 누락 수정

언어 선택 메뉴, 한일·한중 후보창, 상태 알림은 React와 Tauri로 표시합니다. 트레이는 Tauri의 Windows 메뉴를 사용합니다. 입력 엔진은 네이티브 모듈로 발음과 확정 키를 처리하며, PySide6로 타이머와 자식 프로세스를 관리합니다.

## 소스

- `src/App.tsx`: 메인 UI
- `src/Selector.tsx`: Caps 선택 메뉴
- `src/styles.css`: 공통 디자인과 시스템 테마
- `src/locales.json`: 표시 문구
- `engine/module/desktop_messages.py`: 새 번역 원본
- `src-tauri/src/main.rs`: Windows 호스트와 엔진 연결
- `engine/bridge.py`: Python 엔진 어댑터
- `engine/desktop_selector.py`: 선택 메뉴 상태 및 키 처리

## 빌드

Zig 0.14.1을 PATH에 추가하거나 KANASHIFT_ZIG에 실행 파일 경로를 지정합니다.

Node.js 22.12 이상, pnpm, Rust MSVC, Visual Studio C++ 빌드 도구가 필요합니다. 엔진 빌드에는 Python 3.12.16 이상, `engine/module/requirements.txt`, PyInstaller 6.22.3 이상이 필요합니다.

```powershell
pnpm install --frozen-lockfile
python scripts/build_locales.py
.\build.ps1 -RebuildEngine -Installer
```

일반 실행에는 Node.js와 Python 설치가 필요하지 않습니다. Windows 10/11 x64 및 WebView2 Runtime이 필요합니다. 네이티브 모듈은 범용 x86-64 기준을 유지합니다.

`--diagnostic`은 임시 설정을 사용하며 전역 키보드 후크를 설치하지 않습니다. `verification/`에 검사 결과를 보관합니다. 다른 프로그램에 직접 입력하는 호환성 검사는 이 결과에 포함하지 않습니다.

MIT. Translation (JP) & QA: 루노.
