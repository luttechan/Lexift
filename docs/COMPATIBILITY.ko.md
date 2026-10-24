# Lexift 0.8: 다양한 프로그램의 입력 위치에서 변환

Lexift의 한–일·한–중 발음 변환은 다른 프로그램의 입력 위치에서 동작하도록 설계했습니다. 별도 검색창으로 옮겨 적을 필요가 없습니다. Caps + A 또는 Caps + C로 모드를 켜고, 사용하던 입력란에서 한글 발음을 입력한 다음 후보를 고릅니다.

특정 프로그램의 이름을 검사하는 방식 대신 입력 컨트롤이 제공하는 인터페이스를 선택합니다. 두 언어 모두 같은 감지·후보창·원문 치환 계층을 사용합니다.

## 추가한 호환 경로

| 경로 | 처리하는 입력창 | 이번 검증 |
|---|---|---|
| UI Automation TextPattern | 접근성 텍스트와 선택 범위를 제공하는 입력창 | 기존 메모장 본문 경로 유지, 실제 치환 재검증 |
| UI Automation TextPattern2 | 선택 범위 대신 활성 커서 범위를 제공하는 컨트롤 | API 경로 구현. 별도 실제 앱 사례는 아직 미검증 |
| 편집 가능한 사용자 정의 UIA 컨트롤 | 컨트롤 종류가 Edit/Document가 아니어도 TextPattern과 명시적 편집 가능 속성이 있는 경우 | 인터페이스 기반 허용. 프레임워크별 추가 검증 필요 |
| Windows Edit/RichEdit | UIA 정보를 얻을 수 없는 표준 Unicode Edit·RichEdit20W·RichEdit50W 입력창 | 실제 별도 프로세스의 Windows 컨트롤 검사 |
| Scintilla | UIA가 충분하지 않은 UTF-8 Scintilla 문서 | 설치된 실제 SciLexer 컨트롤을 별도 32비트 프로세스에 띄워 64비트 호스트에서 검사 |
| MSAA / IAccessible2 | Firefox 및 IA2 텍스트·편집 인터페이스를 제공하는 입력칸 | 텍스트·선택·글자 좌표·범위 치환 경로 추가. 자체 COM 제공자 21개 검사 통과. 실제 Firefox 종단 검증은 미실시 |

브라우저·Electron·Office·Qt 앱은 제품 이름만으로 호환을 단정하지 않습니다. 개별 입력창이 지원하는 접근성 인터페이스와 편집 상태에 따라 달라집니다. Scintilla 컨트롤 검증 역시 모든 Notepad++ 버전·플러그인 조합의 검증을 뜻하지 않습니다.

## 치환과 지연 처리

- 창·입력 컨트롤·원문·커서 위치를 다시 확인한 뒤 원래 단어만 선택해 입력합니다. 선택 후에도 포커스가 같은 컨트롤인지 확인합니다.
- 암호·읽기 전용·사용 불가 입력창과 선택 영역이 있는 상태는 처리하지 않습니다.
- Windows 메시지에는 응답 제한을 둡니다. 대상 앱이 응답하지 않아도 Lexift 메인 창에서 기다리지 않습니다.
- Scintilla는 UTF-8 바이트 위치를 사용합니다. 원격 프로세스의 메모리를 할당하거나 DLL을 주입하지 않으며, 자체 메시지에는 정수 인수와 반환값만 사용합니다.
- Scintilla의 다중·직사각형 선택, 가상 공백, UTF-8 이외의 코드 페이지는 자동 치환하지 않습니다. 문서 전체를 읽지 않고 커서 앞의 발음만 제한된 범위에서 조회합니다.
- 표준 Edit의 대체 경로는 최대 60,000 UTF-16 단위 문서에 한정합니다. RichEdit의 줄바꿈 표현 때문에 위치가 불명확하면 UIA 경로를 사용합니다.
- 클립보드를 복사·덮어쓰지 않습니다. 일반 실행에서 입력 내용을 디스크에 기록하지 않습니다.
- 텍스트 조회와 커서 좌표 조회를 분리했습니다. UIA 범위·Windows 커서·MSAA 커서·IA2 글자 좌표와 표준 Edit의 EM_POSFROMCHAR를 사용합니다. 좌표가 부족한 네이티브 입력칸에서는 UIA도 확인하고, 정확한 좌표를 얻지 못하면 입력칸 위쪽에 대체 표시합니다. 창 전체 하단을 위치 기준으로 사용하지 않습니다. 모니터 좌표 0·음수도 정상 위치이며, 해당 모니터 배율로 변환하고 화면 밖으로 벗어나지 않도록 조정합니다.
- Firefox의 MozillaWindowClass에서는 IAccessible2를 우선 조회합니다. focused MSAA 객체에서 IAccessibleText·IAccessibleEditableText를 직접 또는 IServiceProvider로 찾고, contenteditable은 IA2의 편집 가능 상태도 확인합니다. 같은 입력 객체·커서·원문·주변 문맥을 재검증한 뒤 범위 치환 API를 호출합니다. 포커스 이벤트에 따라 객체 캐시를 무효화합니다.
- 후보가 열려 있고 원래 창에 포커스가 있을 때만 Space·Enter로 확정합니다. Space 키 반복은 한 번만 확정하고, 후보가 닫힌 뒤의 키 해제도 균형 있게 처리합니다.
- 확정 요청부터 응답까지 중복 Space·Enter를 같은 대상 창에서 차단합니다. 다른 프로세스의 HIMC를 직접 조작하는 대신 대상 앱에 Space를 전달해 조합을 완료하고, 원문에 한 공백만 추가됐는지 위치·문맥을 검증합니다. 그 범위를 한 번 치환하므로 완료용 공백이 결과에 남지 않습니다. 검증이 실패하면 원문을 선택하거나 강제 치환하지 않으며, 앱이 처리한 공백은 남을 수 있습니다. 자체 Edit 별도 프로세스에서는 공백 범위 검증과 치환 후 커서 위치를 검사했습니다. 실제 메모장 물리 키보드 연속 입력은 이번 수정에서 자동 조작하지 않았습니다.
- 원래 입력 감지 프로세스에 Lexift 본체 PID를 전달하여 자기 창의 접근성 조회를 막습니다. 선택창의 일시정지 상태도 보조 프로세스로 전달하며, 이때 후보 조회를 취소합니다.

## 지원의 경계

범용 입력을 목표로 호환 경로를 확장했지만, 모든 Windows 프로그램을 보장하지는 않습니다. 텍스트나 커서 접근을 제공하지 않는 게임·직접 그리는 편집기, 보안 입력 환경, 더 높은 권한으로 실행된 프로그램은 여전히 제한됩니다. 이를 해결하려면 Windows 텍스트 서비스 수준의 별도 구현과 검증이 필요합니다.

## 근거와 검사 자료

- Microsoft EM_GETSEL / EM_SETSEL: https://learn.microsoft.com/en-us/windows/win32/controls/em-getsel , https://learn.microsoft.com/en-us/windows/win32/controls/em-setsel
- Microsoft TextPattern2 GetCaretRange: https://learn.microsoft.com/en-us/windows/win32/api/uiautomationclient/nf-uiautomationclient-iuiautomationtextpattern2-getcaretrange
- Scintilla 공식 인터페이스: https://www.scintilla.org/ScintillaDoc.html
- `test-results/native-edit-compatibility.jsonl`: 표준 Windows 컨트롤·거부 조건·응답 제한 검사
- `test-results/scintilla-compatibility.jsonl`: 실제 Scintilla UTF-8·이모지·여러 줄·선택 상태·32/64비트 간 검사
- `test-results/compatibility-notepad.json`: 실제 메모장 후보 표시와 치환
- `test-results/latency-desktop.json`: 자체 Edit 창의 20회 표시 시간 및 DestroyCaret 후 후보 표시·Space 치환 검사
- `test-results/ia2-adapter-final.jsonl`: IA2 객체·포커스·보호 상태·범위·치환·좌표 검사. 브라우저 자동 조작 없이 자체 제공자로 검사
- `test-results/candidate-position-final.txt`: 배율·음수 모니터 원점·화면 경계·팝업 배치 검사

개발용 재검사: `lab/build_compat_tests.ps1`. Scintilla 검사는 로컬의 32비트 SciLexer.dll을 필요로 하며, 그 DLL은 배포하지 않습니다.
