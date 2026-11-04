"""Desktop UI messages: Korean, English, Japanese, zh-CN, zh-TW, French, Spanish, Russian, German."""
DATA = '''
홈|Home|ホーム|主页|首頁|Accueil|Inicio|Главная|Start
입력 언어|Input languages|入力言語|输入语言|輸入語言|Langues de saisie|Idiomas de entrada|Языки ввода|Eingabesprachen
언어 전환|Switch input language|入力言語の切り替え|切换输入语言|切換輸入語言|Changer de langue de saisie|Cambiar idioma de entrada|Сменить язык ввода|Eingabesprache wechseln
한일 변환|Korean to Japanese|韓国語から日本語|韩语转日语|韓語轉日語|Coréen vers japonais|Coreano a japonés|Корейский → японский|Koreanisch → Japanisch
한중 변환|Korean to Chinese|韓国語から中国語|韩语转中文|韓語轉中文|Coréen vers chinois|Coreano a chino|Корейский → китайский|Koreanisch → Chinesisch
번체 / 주음부호|Traditional / Zhuyin|繁体字 / 注音|繁体 / 注音|繁體 / 注音|Chinois traditionnel / zhuyin|Chino tradicional / zhuyin|Традиционный китайский / чжуинь|Traditionelles Chinesisch / Zhuyin
병음 성조|Pinyin tones|ピンイン声調|拼音声调|拼音聲調|Tons du pinyin|Tonos del pinyin|Тоны пиньинь|Pinyin-Töne
Caps Lock 상태 알림|Caps Lock indicator|Caps Lock 状態表示|Caps Lock 状态提示|Caps Lock 狀態提示|Indicateur Verr. Maj|Indicador de Bloq Mayús|Индикатор Caps Lock|Feststelltasten-Anzeige
Lexift 사용|Enable Lexift|Lexift を有効にする|启用 Lexift|啟用 Lexift|Activer Lexift|Activar Lexift|Включить Lexift|Lexift aktivieren
Lexift를 종료할까요?|Quit Lexift?|Lexift を終了しますか？|退出 Lexift？|結束 Lexift？|Quitter Lexift ?|¿Cerrar Lexift?|Выйти из Lexift?|Lexift beenden?
Windows 입력기를 등록하고 표시 순서를 정하세요.|Add Windows input methods and arrange their order.|Windows の入力方式を追加し、表示順を設定します。|添加 Windows 输入法并调整顺序。|新增 Windows 輸入法並調整順序。|Ajoutez vos méthodes de saisie Windows et classez-les.|Añade los métodos de entrada de Windows y ordénalos.|Добавьте методы ввода Windows и задайте их порядок.|Windows-Eingabemethoden hinzufügen und anordnen.
개발 후원|Support Lexift|開発を支援|支持开发|支持開發|Soutenir Lexift|Apoyar Lexift|Поддержать Lexift|Lexift unterstützen
고마운 분|Credits|クレジット|鸣谢|致謝|Remerciements|Créditos|Благодарности|Mitwirkende
기능|Features|機能|功能|功能|Fonctions|Funciones|Функции|Funktionen
기능별 사용 여부와 키 조합을 설정하세요.|Choose which features to use and set their shortcuts.|機能の有効・無効とショートカットを設定します。|启用所需功能并设置快捷键。|啟用所需功能並設定快捷鍵。|Activez les fonctions et définissez leurs raccourcis.|Activa las funciones y configura sus atajos.|Выберите функции и назначьте сочетания клавиш.|Funktionen aktivieren und Tastenkürzel festlegen.
기본값으로 되돌릴까요?|Restore defaults?|初期設定に戻しますか？|恢复默认设置？|還原預設值？|Rétablir les valeurs par défaut ?|¿Restaurar los valores predeterminados?|Восстановить настройки по умолчанию?|Standardeinstellungen wiederherstellen?
다시 연결|Reconnect|再接続|重新连接|重新連線|Reconnecter|Reconectar|Подключить снова|Neu verbinden
단어 삭제|Remove word|単語を削除|删除词条|刪除詞條|Supprimer le mot|Eliminar palabra|Удалить слово|Wort entfernen
단어 추가|Add word|単語を追加|添加词条|新增詞條|Ajouter un mot|Añadir palabra|Добавить слово|Wort hinzufügen
단축키 설정|Edit shortcuts|ショートカット設定|设置快捷键|設定快捷鍵|Raccourcis|Editar atajos|Настроить сочетания|Tastenkürzel bearbeiten
단축키, 입력 언어와 사전을 초기화합니다.|This resets shortcuts, input languages and your dictionary.|ショートカット、入力言語、ユーザー辞書を初期化します。|将重置快捷键、输入语言和用户词典。|將重設快捷鍵、輸入語言及使用者字典。|Les raccourcis, les langues et le dictionnaire seront réinitialisés.|Se restablecerán los atajos, los idiomas y el diccionario.|Сочетания, языки ввода и словарь будут сброшены.|Tastenkürzel, Eingabesprachen und Wörterbuch werden zurückgesetzt.
메뉴|Navigation|メニュー|菜单|選單|Navigation|Navegación|Меню|Navigation
모든 변경사항이 저장되었습니다.|All changes saved.|すべて保存済みです。|所有更改已保存。|所有變更已儲存。|Toutes les modifications sont enregistrées.|Todos los cambios están guardados.|Все изменения сохранены.|Alle Änderungen gespeichert.
미리보기|Preview|プレビュー|预览|預覽|Aperçu|Vista previa|Предпросмотр|Vorschau
미리보기에서는 실제 설정을 변경하지 않습니다.|Preview only. Your settings are unchanged.|プレビューです。実際の設定は変更されません。|仅供预览，不会更改实际设置。|僅供預覽，不會變更實際設定。|Aperçu uniquement. Vos réglages restent inchangés.|Solo vista previa. No se modifican tus ajustes.|Только предпросмотр. Настройки не меняются.|Nur Vorschau. Ihre Einstellungen bleiben unverändert.
발음 변환은 한국어 입력 기준입니다. 다른 키보드 환경에서는 지원하지 않을 수 있습니다.|Phonetic conversion is designed for Korean input. Other keyboard layouts may not be supported.|発音変換は韓国語入力向けの機能です。他のキーボード配列では利用できない場合があります。|发音转换以韩语输入为基础，可能不支持其他键盘布局。|發音轉換以韓語輸入為基礎，可能不支援其他鍵盤配置。|La conversion phonétique est conçue pour la saisie coréenne. Les autres dispositions peuvent ne pas être prises en charge.|La conversión fonética está diseñada para la entrada en coreano. Otras distribuciones pueden no ser compatibles.|Преобразование произношения рассчитано на корейский ввод. Другие раскладки могут не поддерживаться.|Die Lautumwandlung ist für koreanische Eingaben ausgelegt. Andere Tastaturlayouts werden möglicherweise nicht unterstützt.
발음과 표기를 한 번 등록하면 다음 입력부터 후보에 표시됩니다.|Save a pronunciation and its spelling to include it in future suggestions.|読み方と表記を登録すると、次回から変換候補に表示されます。|保存读音和对应文字，下次输入时即可显示为候选。|儲存讀音及對應文字，下次輸入時即可顯示為候選。|Enregistrez une prononciation et son écriture pour la retrouver parmi les suggestions.|Guarda una pronunciación y su escritura para verla entre las sugerencias.|Сохраните произношение и написание, чтобы видеть его среди вариантов.|Aussprache und Schreibweise speichern, um sie künftig als Vorschlag zu erhalten.
변경|Change|変更|更改|變更|Modifier|Cambiar|Изменить|Ändern
병음 입력 후 Caps + 1~4로 성조 지정, Caps + 0으로 해제.|After typing pinyin, press Caps + 1–4 to add a tone or Caps + 0 to remove it.|ピンイン入力後、Caps + 1〜4 で声調を付け、Caps + 0 で解除します。|输入拼音后，按 Caps + 1–4 添加声调，Caps + 0 清除。|輸入拼音後，按 Caps + 1–4 加上聲調，Caps + 0 清除。|Après le pinyin, Caps + 1–4 ajoute un ton ; Caps + 0 le retire.|Tras escribir pinyin, Caps + 1–4 añade un tono y Caps + 0 lo elimina.|После ввода пиньинь Caps + 1–4 добавляет тон, Caps + 0 убирает его.|Nach der Pinyin-Eingabe fügt Caps + 1–4 einen Ton hinzu; Caps + 0 entfernt ihn.
사용 준비 완료|Ready|使用できます|已就绪|已就緒|Prêt|Listo|Готово|Bereit
사용설명서|User guide|使い方|使用指南|使用指南|Guide d’utilisation|Guía de uso|Руководство|Anleitung
사용할 입력 언어를 먼저 등록하세요.|Add an input language to get started.|まず使用する入力言語を追加してください。|请先添加要使用的输入语言。|請先新增要使用的輸入語言。|Ajoutez une langue de saisie pour commencer.|Añade un idioma de entrada para empezar.|Сначала добавьте язык ввода.|Fügen Sie zuerst eine Eingabesprache hinzu.
선택|Select|選択|选择|選取|Choisir|Seleccionar|Выбрать|Auswählen
선택 메뉴를 표시하지 못했습니다. 다시 시도하세요.|Could not show the language switcher. Try again.|言語切替メニューを表示できませんでした。もう一度お試しください。|无法显示语言切换菜单，请重试。|無法顯示語言切換選單，請再試一次。|Impossible d’afficher le sélecteur. Réessayez.|No se pudo mostrar el selector. Inténtalo de nuevo.|Не удалось открыть меню выбора. Повторите попытку.|Die Sprachauswahl konnte nicht angezeigt werden. Erneut versuchen.
아래로|Move down|下へ|下移|下移|Descendre|Bajar|Вниз|Nach unten
아직 등록된 단어가 없습니다.|Your dictionary is empty.|登録された単語はありません。|暂无词条。|尚無詞條。|Votre dictionnaire est vide.|Tu diccionario está vacío.|Словарь пока пуст.|Ihr Wörterbuch ist noch leer.
알림|Notifications|通知|通知|通知|Notifications|Notificaciones|Уведомления|Benachrichtigungen
알림 닫기|Dismiss notification|通知を閉じる|关闭通知|關閉通知|Fermer la notification|Cerrar notificación|Закрыть уведомление|Benachrichtigung schließen
알림 영역으로 닫기|Close to tray|通知領域に格納|最小化到托盘|縮小至系統匣|Réduire dans la zone de notification|Cerrar a la bandeja|Свернуть в трей|In den Infobereich schließen
언어 전환부터 발음 변환까지, 키보드 하나로.|Switch languages and convert pronunciations, all from your keyboard.|言語の切り替えも発音変換も、キーボードひとつで。|切换语言、转换发音，一个键盘就够。|切換語言、轉換發音，一個鍵盤就夠。|Changez de langue et convertissez les prononciations depuis votre clavier.|Cambia de idioma y convierte pronunciaciones desde tu teclado.|Переключайте языки и преобразуйте произношение с клавиатуры.|Sprachen wechseln und Laute umwandeln – direkt per Tastatur.
연결 오류|Connection error|接続エラー|连接错误|連線錯誤|Erreur de connexion|Error de conexión|Ошибка подключения|Verbindungsfehler
연결 중|Connecting|接続中|正在连接|正在連線|Connexion en cours|Conectando|Подключение|Verbindung wird hergestellt
예시|Example|例|示例|範例|Exemple|Ejemplo|Пример|Beispiel
위로|Move up|上へ|上移|上移|Monter|Subir|Вверх|Nach oben
입력은 그대로.|Same keyboard.|入力はそのまま。|照常输入。|照常輸入。|Le même clavier.|El mismo teclado.|Та же клавиатура.|Dieselbe Tastatur.
일시 정지|Paused|一時停止中|已暂停|已暫停|En pause|En pausa|Приостановлено|Pausiert
입력 기능 중지|Input features stopped|入力機能停止中|输入功能已停止|輸入功能已停止|Fonctions de saisie arrêtées|Funciones de entrada detenidas|Функции ввода остановлены|Eingabefunktionen angehalten
입력 모드|Input mode|入力モード|输入模式|輸入模式|Mode de saisie|Modo de entrada|Режим ввода|Eingabemodus
입력 언어 등록 필요|Add an input language|入力言語を追加してください|请添加输入语言|請新增輸入語言|Ajoutez une langue de saisie|Añade un idioma de entrada|Добавьте язык ввода|Eingabesprache hinzufügen
입력 환경 준비 중|Preparing your input tools|入力環境を準備中|正在准备输入环境|正在準備輸入環境|Préparation de la saisie|Preparando la entrada|Подготовка ввода|Eingabe wird vorbereitet
입력기 전환과 발음 변환이 중지됩니다.|Language switching and phonetic conversion will stop.|言語切替と発音変換を停止します。|语言切换和发音转换将停止。|語言切換及發音轉換將停止。|Le changement de langue et la conversion phonétique seront arrêtés.|Se detendrán el cambio de idioma y la conversión fonética.|Переключение языков и преобразование произношения прекратятся.|Sprachwechsel und Lautumwandlung werden angehalten.
입력기 추가|Add input method|入力方式を追加|添加输入法|新增輸入法|Ajouter une méthode de saisie|Añadir método de entrada|Добавить метод ввода|Eingabemethode hinzufügen
자주 쓰는 이름이나 표현을 원하는 표기로 등록하세요.|Save names and phrases with the spelling you prefer.|よく使う名前や表現を、好みの表記で登録できます。|为常用名称或表达保存指定写法。|為常用名稱或詞句儲存指定寫法。|Enregistrez vos noms et expressions avec l’écriture de votre choix.|Guarda nombres y expresiones con la escritura que prefieras.|Сохраняйте имена и выражения с нужным написанием.|Namen und Ausdrücke in der gewünschten Schreibweise speichern.
저장|Save|保存|保存|儲存|Enregistrer|Guardar|Сохранить|Speichern
저장하지 않은 변경사항이 있습니다.|You have unsaved changes.|未保存の変更があります。|有未保存的更改。|有尚未儲存的變更。|Des modifications ne sont pas enregistrées.|Hay cambios sin guardar.|Есть несохранённые изменения.|Es gibt ungespeicherte Änderungen.
저장했습니다.|Saved.|保存しました。|已保存。|已儲存。|Enregistré.|Guardado.|Сохранено.|Gespeichert.
표시 언어를 {language}로 바꿀까요?|Switch the display language to {language}?|表示言語を{language}に変更しますか？|要将界面语言切换为{language}吗？|要將介面語言切換為{language}嗎？|Passer l’interface en {language} ?|¿Cambiar el idioma de la interfaz a {language}?|Переключить интерфейс на {language}?|Die Anzeigesprache auf {language} umstellen?
조합|Modifiers|修飾キー|组合键|組合鍵|Modificateurs|Modificadores|Модификаторы|Modifikatortasten
중국어 간체|Simplified Chinese|中国語（簡体字）|简体中文|簡體中文|Chinois simplifié|Chino simplificado|Китайский (упрощённый)|Chinesisch (vereinfacht)
중국어 번체|Traditional Chinese|中国語（繁体字）|繁体中文|繁體中文|Chinois traditionnel|Chino tradicional|Китайский (традиционный)|Chinesisch (traditionell)
진단 모드|Diagnostic mode|診断モード|诊断模式|診斷模式|Mode diagnostic|Modo de diagnóstico|Режим диагностики|Diagnosemodus
최대화|Maximize|最大化|最大化|最大化|Agrandir|Maximizar|Развернуть|Maximieren
최소화|Minimize|最小化|最小化|最小化|Réduire|Minimizar|Свернуть|Minimieren
최신 버전: {version}|Latest release: {version}|最新バージョン: {version}|最新版本：{version}|最新版本：{version}|Dernière version : {version}|Última versión: {version}|Последняя версия: {version}|Neueste Version: {version}
키|Key|キー|按键|按鍵|Touche|Tecla|Клавиша|Taste
표시 언어 변경|Change display language|表示言語を変更|更改显示语言|變更顯示語言|Changer la langue d’affichage|Cambiar idioma de la interfaz|Изменение языка интерфейса|Anzeigesprache ändern
한글 발음|Korean pronunciation|ハングルの読み|韩文读音|韓文讀音|Prononciation coréenne|Pronunciación en coreano|Произношение на хангыле|Koreanische Aussprache
설정 값을 확인하세요.|Check the setting values.|設定値を確認してください。|请检查设置值。|請檢查設定值。|Vérifiez les valeurs des réglages.|Revisa los valores de los ajustes.|Проверьте значения настроек.|Prüfen Sie die Einstellungswerte.
지원하지 않는 요청입니다.|This operation is not supported.|この操作には対応していません。|不支持此操作。|不支援此操作。|Cette opération n’est pas prise en charge.|Esta operación no es compatible.|Эта операция не поддерживается.|Dieser Vorgang wird nicht unterstützt.
입력기는 1개에서 15개까지 등록할 수 있습니다.|Add between 1 and 15 input methods.|入力方式は 1〜15 件登録できます。|可添加 1 至 15 个输入法。|可新增 1 至 15 個輸入法。|Ajoutez entre 1 et 15 méthodes de saisie.|Añade entre 1 y 15 métodos de entrada.|Можно добавить от 1 до 15 методов ввода.|Fügen Sie 1 bis 15 Eingabemethoden hinzu.
기존 Lexift가 실행 중입니다. 알림 영역에서 종료한 뒤 다시 실행하세요.|Lexift is already running. Quit it from the system tray first.|Lexift は起動済みです。通知領域から終了してから起動してください。|Lexift 已在运行，请先从系统托盘退出。|Lexift 已在執行，請先從系統匣結束。|Lexift est déjà actif. Quittez-le d’abord depuis la zone de notification.|Lexift ya está en ejecución. Ciérralo primero desde la bandeja.|Lexift уже запущен. Сначала закройте его через системный трей.|Lexift läuft bereits. Beenden Sie es zuerst im Infobereich.
입력 엔진 연결이 종료되었습니다.|The input engine disconnected.|入力エンジンとの接続が切れました。|输入引擎连接已断开。|輸入引擎連線已中斷。|Le moteur de saisie est déconnecté.|El motor de entrada se ha desconectado.|Связь с движком ввода прервана.|Die Verbindung zur Eingabe-Engine wurde getrennt.
입력 엔진의 응답이 지연되고 있습니다.|The input engine is taking too long to respond.|入力エンジンの応答が遅れています。|输入引擎响应超时。|輸入引擎回應逾時。|Le moteur de saisie met trop de temps à répondre.|El motor de entrada tarda demasiado en responder.|Движок ввода слишком долго не отвечает.|Die Eingabe-Engine antwortet nicht rechtzeitig.
입력 엔진 파일을 찾을 수 없습니다. 배포 폴더를 확인하세요.|The input engine is missing. Check the app folder.|入力エンジンが見つかりません。アプリのフォルダーを確認してください。|找不到输入引擎，请检查程序文件夹。|找不到輸入引擎，請檢查程式資料夾。|Moteur de saisie introuvable. Vérifiez le dossier de l’application.|No se encuentra el motor de entrada. Revisa la carpeta de la aplicación.|Движок ввода не найден. Проверьте папку приложения.|Die Eingabe-Engine fehlt. Prüfen Sie den Programmordner.
입력기 이름을 입력하세요.|Enter an input name.|入力方式の名前を入力してください。|请输入输入法名称。|請輸入輸入法名稱。|Saisissez un nom.|Introduce un nombre de entrada.|Введите название метода ввода.|Geben Sie einen Namen ein.
키워드는 한글과 -로 64자 이내로 입력하세요.|Use Hangul and hyphens, up to 64 characters.|キーワードはハングルと - で 64 文字以内にしてください。|关键词仅限韩文和 -，最多 64 个字符。|關鍵字僅限韓文和 -，最多 64 個字元。|Utilisez le hangeul et les traits d’union, 64 caractères maximum.|Usa hangul y guiones, hasta 64 caracteres.|Используйте хангыль и дефисы, не более 64 символов.|Verwenden Sie Hangul und Bindestriche, höchstens 64 Zeichen.
대치할 텍스트와 언어를 확인하세요.|Check the replacement text and language.|置換する文字と対象言語を確認してください。|请检查替换文本和语言。|請檢查取代文字及語言。|Vérifiez le texte de remplacement et la langue.|Revisa el texto de reemplazo y el idioma.|Проверьте текст замены и язык.|Prüfen Sie Ersetzungstext und Sprache.
'''
ROWS = {}
for line in DATA.strip().splitlines():
    cells=line.split('|')
    assert len(cells)==9, cells[0]
    ROWS[cells[0]]=tuple(cells[1:])
for key in ('잘못된 요청 번호입니다.','잘못된 요청입니다.','단축키 기능을 확인하세요.','입력기 정보를 확인하세요.','Windows에 설치된 입력기와 모드를 선택하세요.'):
    ROWS[key]=ROWS['설정 값을 확인하세요.']
for key in ('지원하지 않는 기능입니다.','지원하지 않는 설정입니다.','지원하지 않는 언어입니다.','진단 모드에서만 사용할 수 있습니다.','확인이 필요한 작업입니다.','기본값 복원을 확인하세요.'):
    ROWS[key]=ROWS['지원하지 않는 요청입니다.']
