from __future__ import annotations

LANGUAGES = (
    ('ko', '한국어'), ('en', 'English'), ('ja', '日本語'),
    ('zh_CN', '简体中文'), ('zh_TW', '繁體中文'),
    ('fr', 'Français'), ('es', 'Español'), ('ru', 'Русский'), ('de', 'Deutsch'),
)
SUPPORTED = {code for code, _ in LANGUAGES}
_current = 'ko'
_current_index = -1

# Stable Korean source keys. Languages per row: English, Japanese, Chinese simplified,
# Chinese traditional, French, Spanish, Russian, German.
_ROWS = {
'로그를 저장하려면 일반 권한으로 실행하세요.': ('Run without administrator privileges to save logs.','ログを保存するには通常の権限で起動してください。','请以普通权限运行以保存日志。','請以一般權限執行以儲存記錄。','Exécutez sans droits administrateur pour enregistrer les journaux.','Ejecute sin permisos de administrador para guardar los registros.','Для сохранения журнала запустите без прав администратора.','Zum Speichern von Protokollen ohne Administratorrechte starten.'),
'개발자 커피 사주기... ㅎㅎ': ('Buy the developer a coffee... :)','開発者にコーヒーを... ☺','请开发者喝杯咖啡... 哈哈','請開發者喝杯咖啡... 哈哈','Offrir un café au développeur... :)','Invitar al desarrollador a un café... :)','Угостить разработчика кофе... :)','Dem Entwickler einen Kaffee spendieren... :)'),
'깃허브 둘러보기': ('Explore my GitHub','GitHubを見てみる','逛逛我的 GitHub','逛逛我的 GitHub','Découvrir mon GitHub','Explorar mi GitHub','Посмотреть мой GitHub','Mein GitHub entdecken'),
'한국어': ('Korean','韓国語','韩语','韓語','Coréen','Coreano','Корейский','Koreanisch'),
'영어': ('English','英語','英语','英語','Anglais','Inglés','Английский','Englisch'),
'중국어': ('Chinese','中国語','中文','中文','Chinois','Chino','Китайский','Chinesisch'),
'일본어 / 히라가나': ('Japanese / Hiragana','日本語 / ひらがな','日语 / 平假名','日語 / 平假名','Japonais / Hiragana','Japonés / Hiragana','Японский / Хирагана','Japanisch / Hiragana'),
'업데이트 확인': ('Check for updates','アップデートを確認','检查更新','檢查更新','Rechercher des mises à jour','Buscar actualizaciones','Проверить обновления','Nach Updates suchen'),
'취소': ('Cancel','キャンセル','取消','取消','Annuler','Cancelar','Отмена','Abbrechen'),
'업데이트를 확인하는 중...': ('Checking for updates...','更新を確認中...','正在检查更新...','正在檢查更新...','Recherche de mises à jour...','Buscando actualizaciones...','Проверка обновлений...','Updates werden gesucht...'),
'새 업데이트가 없습니다.': ('No new update is available.','新しい更新はありません。','暂无新更新。','暫無新更新。','Aucune nouvelle mise à jour.','No hay nuevas actualizaciones.','Новых обновлений нет.','Keine neuen Updates verfügbar.'),
'새 버전이 있습니다.': ('A new version is available.','新しいバージョンがあります。','有新版本可用。','有新版本可用。','Une nouvelle version est disponible.','Hay una nueva versión disponible.','Доступна новая версия.','Eine neue Version ist verfügbar.'),
'다운로드 후 설치하고 다시 시작할까요?': ('Download, install and restart?','ダウンロードして更新・再起動しますか？','下载、安装并重启？','下載、安裝並重新啟動？','Télécharger, installer et redémarrer ?','¿Descargar, instalar y reiniciar?','Скачать, установить и перезапустить?','Herunterladen, installieren und neu starten?'),
'다운로드 페이지를 열까요?': ('Open the download page?','ダウンロードページを開きますか？','打开下载页面？','開啟下載頁面？','Ouvrir la page de téléchargement ?','¿Abrir la página de descarga?','Открыть страницу загрузки?','Downloadseite öffnen?'),
'다운로드 및 파일 확인 중...': ('Downloading and verifying files...','ダウンロードとファイル検証中...','正在下载并校验文件...','正在下載並驗證檔案...','Téléchargement et vérification...','Descargando y verificando archivos...','Загрузка и проверка файлов...','Download und Dateiprüfung...'),
'파일 교체를 준비하는 중...': ('Preparing to replace files...','ファイルの更新を準備中...','正在准备替换文件...','正在準備更換檔案...','Préparation de la mise à jour...','Preparando la actualización...','Подготовка замены файлов...','Dateiaustausch wird vorbereitet...'),
'업데이트 실패': ('Update failed','更新に失敗しました','更新失败','更新失敗','Échec de la mise à jour','Error de actualización','Ошибка обновления','Update fehlgeschlagen'),
'Input switcher': ('Input switcher','入力切替','输入法切换','輸入法切換','Sélecteur de saisie','Selector de entrada','Переключение ввода','Eingabe wechseln'),
'대시보드': ('Dashboard','ダッシュボード','主页','主頁','Accueil','Inicio','Главная','Übersicht'),
'입력기 슬롯': ('Input slots','入力スロット','输入法槽位','輸入法欄位','Emplacements','Perfiles','Слоты ввода','Eingabeplätze'),
'일반 설정': ('Settings','一般設定','设置','設定','Paramètres','Ajustes','Настройки','Einstellungen'),
'프로그램 정보': ('About','アプリ情報','关于','關於','À propos','Acerca de','О программе','Info'),
'종료': ('Quit','終了','退出','結束','Quitter','Salir','Выход','Beenden'),
'정말로 종료하시겠습니까?': ('Are you sure you want to quit?','本当に終了しますか？','确定要退出吗？','確定要結束嗎？','Voulez-vous vraiment quitter ?','¿Seguro que quieres salir?','Вы действительно хотите выйти?','Möchten Sie wirklich beenden?'),
'입력기 선택': ('Choose input','入力方式を選択','选择输入法','選擇輸入法','Choisir une saisie','Elegir entrada','Выбор ввода','Eingabe wählen'),
'숫자키 또는 방향키로 선택': ('Number or arrow keys','数字キーまたは矢印キー','数字键或方向键','數字鍵或方向鍵','Chiffres ou flèches','Números o flechas','Цифры или стрелки','Ziffern oder Pfeile'),
'Enter 선택    /    Esc 닫기': ('Enter select / Esc close','Enter 選択 / Esc 閉じる','Enter 确认 / Esc 关闭','Enter 確認 / Esc 關閉','Entrée valider / Échap fermer','Intro elegir / Esc cerrar','Enter — выбрать / Esc — закрыть','Enter wählen / Esc schließen'),
'가타카나 문자 폭': ('Katakana width','カタカナの文字幅','片假名字符宽度','片假名字元寬度','Largeur katakana','Anchura de katakana','Ширина катаканы','Katakana-Breite'),
'전각 또는 반각을 선택하세요': ('Choose full- or half-width','全角または半角を選択','选择全角或半角','選擇全形或半形','Choisir pleine ou demi-chasse','Elige ancho completo o medio','Полная или половинная ширина','Voll- oder Halbbreite wählen'),
'전각 가타카나': ('Full-width Katakana','全角カタカナ','全角片假名','全形片假名','Katakana pleine chasse','Katakana de ancho completo','Полноширинная катакана','Katakana in Vollbreite'),
'반각 가타카나': ('Half-width Katakana','半角カタカナ','半角片假名','半形片假名','Katakana demi-chasse','Katakana de medio ancho','Полуширинная катакана','Katakana in Halbbreite'),
'설정에서 입력기를 다시 선택하세요': ('Select another input in Settings','設定で入力方式を選び直してください','请在设置中重新选择输入法','請在設定中重新選擇輸入法','Choisissez une autre saisie','Elige otra entrada en Ajustes','Выберите другую раскладку','Eingabe in Einstellungen neu wählen'),
'사용할 수 없는 입력기': ('Unavailable input','利用できない入力方式','不可用输入法','無法使用的輸入法','Saisie indisponible','Entrada no disponible','Недоступный ввод','Eingabe nicht verfügbar'),
'목록 새로고침': ('Refresh list','一覧を更新','刷新列表','重新整理清單','Actualiser','Actualizar','Обновить','Liste aktualisieren'),
'Windows에서 사용할 수 있는 입력기': ('Installed Windows inputs','Windows に登録された入力方式','Windows 已安装的输入法','Windows 已安裝的輸入法','Saisies installées sur Windows','Entradas instaladas en Windows','Раскладки Windows','Installierte Windows-Eingaben'),
'+ 슬롯 추가': ('+ Add slot','+ スロットを追加','+ 添加槽位','+ 新增欄位','+ Ajouter','+ Añadir','+ Добавить','+ Platz hinzufügen'),
'변경사항 저장': ('Save changes','変更を保存','保存更改','儲存變更','Enregistrer','Guardar cambios','Сохранить','Änderungen speichern'),
'이 슬롯에서 사용할 Windows 입력기': ('Windows input for this slot','このスロットの入力方式','此槽位的输入法','此欄位的輸入法','Saisie pour cet emplacement','Entrada de este perfil','Раскладка для слота','Eingabe für diesen Platz'),
'사용할 수 없는 입력기 — 다시 선택': ('Unavailable — choose another','利用不可 — 再選択','不可用 — 请重选','無法使用 — 請重選','Indisponible — rechoisir','No disponible — vuelve a elegir','Недоступно — выберите заново','Nicht verfügbar — neu wählen'),
'표시 이름': ('Display name','表示名','显示名称','顯示名稱','Nom affiché','Nombre visible','Название','Anzeigename'),
'삭제': ('Remove','削除','删除','刪除','Supprimer','Eliminar','Удалить','Entfernen'),
'입력기 없음': ('No input available','入力方式がありません','无可用输入法','無可用輸入法','Aucune saisie','Sin entrada','Нет раскладки','Keine Eingabe'),
'입력기를 하나 이상 선택하세요.': ('Choose at least one input.','入力方式を1つ以上選択してください。','请至少选择一种输入法。','請至少選擇一種輸入法。','Choisissez au moins une saisie.','Elige al menos una entrada.','Выберите хотя бы одну раскладку.','Mindestens eine Eingabe wählen.'),
'사용할 수 없는 입력기가 있습니다. 다시 선택하거나 삭제하세요.': ('An input is unavailable. Change or remove it.','利用できない入力方式があります。変更または削除してください。','部分输入法不可用，请更换或删除。','部分輸入法無法使用，請更換或刪除。','Saisie indisponible : modifiez-la ou supprimez-la.','Una entrada no está disponible: cámbiala o elimínala.','Недоступная раскладка: замените или удалите.','Nicht verfügbare Eingabe ändern oder entfernen.'),
'입력 모드 오류': ('Input mode error','入力モードエラー','输入模式错误','輸入模式錯誤','Erreur de mode','Error de modo','Ошибка режима','Eingabemodusfehler'),
'설치된 입력기에 맞는 입력 모드를 선택하세요.': ('Choose a mode supported by this input.','入力方式に対応するモードを選択してください。','请选择当前输入法支持的模式。','請選擇目前輸入法支援的模式。','Choisissez un mode pris en charge.','Elige un modo compatible.','Выберите поддерживаемый режим.','Unterstützten Modus wählen.'),
'최대 6개까지 등록할 수 있습니다.': ('Up to 6 slots.','最大6個まで設定できます。','最多可设置6个槽位。','最多可設定6個欄位。','6 emplacements maximum.','Hasta 6 perfiles.','До 6 слотов.','Bis zu 6 Plätze.'),
'빠른 전환': ('Quick switch','クイック切替','快速切换','快速切換','Accès rapide','Cambio rápido','Быстрое переключение','Schnellwechsel'),
'단축키 대기 중': ('Shortcut ready','ショートカット待機中','快捷键已就绪','快捷鍵已就緒','Raccourci prêt','Atajo listo','Горячая клавиша готова','Tastenkürzel bereit'),
'등록된 입력기': ('Configured inputs','登録した入力方式','已配置输入法','已設定輸入法','Saisies configurées','Entradas configuradas','Настроенные раскладки','Konfigurierte Eingaben'),
'편집': ('Edit','編集','编辑','編輯','Modifier','Editar','Изменить','Bearbeiten'),
'시작 옵션과 단축키': ('Startup and shortcut','起動とショートカット','启动与快捷键','啟動與快捷鍵','Démarrage et raccourci','Inicio y atajo','Запуск и горячая клавиша','Start und Tastenkürzel'),
'실행': ('Startup','起動','启动','啟動','Démarrage','Inicio','Запуск','Start'),
'실행할 때 메인 창 표시': ('Show main window on launch','起動時にメイン画面を表示','启动时显示主窗口','啟動時顯示主視窗','Afficher la fenêtre au démarrage','Mostrar ventana al iniciar','Показывать окно при запуске','Hauptfenster beim Start anzeigen'),
'시작 알림 표시': ('Show startup notification','起動通知を表示','显示启动通知','顯示啟動通知','Notification au démarrage','Aviso al iniciar','Уведомление при запуске','Startbenachrichtigung anzeigen'),
'Windows 로그인 시 자동 실행': ('Run at Windows sign-in','Windows ログイン時に起動','登录 Windows 时启动','登入 Windows 時啟動','Lancer avec Windows','Iniciar con Windows','Запускать с Windows','Mit Windows starten'),
'창을 닫으면 Lexift가 종료됩니다.': ('Closing the window quits Lexift.','ウィンドウを閉じると終了します。','关闭窗口将退出 Lexift。','關閉視窗將結束 Lexift。','Fermer la fenêtre quitte Lexift.','Cerrar la ventana sale de Lexift.','Закрытие окна завершает Lexift.','Das Schließen beendet Lexift.'),
'단축키': ('Shortcut','ショートカット','快捷键','快捷鍵','Raccourci','Atajo','Горячая клавиша','Tastenkürzel'),
'적용': ('Apply','適用','应用','套用','Appliquer','Aplicar','Применить','Übernehmen'),
'CapsLock 단독 입력은 원래 기능을 유지합니다.': ('CapsLock alone still works normally.','CapsLock 単独では通常どおり動作します。','单独按 CapsLock 仍可正常使用。','單獨按 CapsLock 仍可正常使用。','CapsLock seul conserve sa fonction.','CapsLock solo funciona normalmente.','Отдельный CapsLock работает как обычно.','CapsLock allein funktioniert weiterhin normal.'),
'단축키 확인': ('Confirm shortcut','ショートカット確認','确认快捷键','確認快捷鍵','Confirmer le raccourci','Confirmar atajo','Подтвердить сочетание','Tastenkürzel bestätigen'),
'Ctrl + Alt 조합은 일부 키보드에서 AltGr 입력과 겹칠 수 있습니다. 적용할까요?': ('Ctrl + Alt may conflict with AltGr. Apply anyway?','Ctrl + Alt は AltGr と競合する場合があります。適用しますか？','Ctrl + Alt 可能与 AltGr 冲突。仍要应用吗？','Ctrl + Alt 可能與 AltGr 衝突。仍要套用嗎？','Ctrl + Alt peut gêner AltGr. Continuer ?','Ctrl + Alt puede interferir con AltGr. ¿Aplicar?','Ctrl + Alt может конфликтовать с AltGr. Применить?','Ctrl + Alt kann AltGr stören. Trotzdem übernehmen?'),
'자동 실행 설정': ('Auto-start','自動起動','自动启动','自動啟動','Démarrage automatique','Inicio automático','Автозапуск','Autostart'),
'Windows 자동 실행 설정을 변경하지 못했습니다.': ('Could not change Windows startup settings.','Windows の自動起動設定を変更できませんでした。','无法更改 Windows 启动设置。','無法變更 Windows 啟動設定。','Impossible de modifier le démarrage Windows.','No se pudo cambiar el inicio con Windows.','Не удалось изменить автозапуск Windows.','Windows-Autostart konnte nicht geändert werden.'),
'이 프로그램은 MIT 라이선스로 배포됩니다.': ('Released under the MIT License.','MIT ライセンスで公開されています。','根据 MIT 许可证发布。','依 MIT 授權條款發布。','Distribué sous licence MIT.','Publicado bajo licencia MIT.','Распространяется по лицензии MIT.','Veröffentlicht unter der MIT-Lizenz.'),
'소스코드와 라이선스 전문은 배포 폴더에서 확인할 수 있습니다.': ('See LICENSE in the project folder.','ライセンス全文は LICENSE を参照。','完整条款请参阅 LICENSE。','完整條款請參閱 LICENSE。','Voir le fichier LICENSE.','Consulta el archivo LICENSE.','Полный текст — в файле LICENSE.','Vollständiger Text in LICENSE.'),
'오류 로그 열기': ('Open log','ログを開く','打开日志','開啟記錄','Ouvrir le journal','Abrir registro','Открыть журнал','Protokoll öffnen'),
'아직 생성된 로그가 없습니다.': ('No log file yet.','ログはまだありません。','尚无日志文件。','尚無記錄檔。','Aucun journal disponible.','Aún no hay registro.','Файла журнала пока нет.','Noch keine Protokolldatei.'),
'오류 로그': ('Log','ログ','日志','記錄','Journal','Registro','Журнал','Protokoll'),
'검수자 정보가 없습니다.': ('No reviewers listed.','検収者は未登録です。','暂无语言校对人员。','目前沒有語言校對人員。','Aucun relecteur indiqué.','Sin revisores indicados.','Рецензенты не указаны.','Keine Prüfer angegeben.'),
'메인 창': ('Main window','メイン画面','主窗口','主視窗','Fenêtre principale','Ventana principal','Главное окно','Hauptfenster'),
'설정': ('Settings','設定','设置','設定','Paramètres','Ajustes','Настройки','Einstellungen'),
'오버레이 키보드': ('Overlay keyboard','オーバーレイ操作','悬浮界面键盘','浮動視窗鍵盤','Clavier du sélecteur','Teclado superpuesto','Клавиатура меню','Overlay-Tastatur'),
'전역 방향키 연결에 실패했습니다.': ('Could not register overlay navigation.','選択画面のキー操作を登録できませんでした。','无法注册方向键控制。','無法註冊方向鍵控制。','Impossible d’activer les touches de navigation.','No se pudo activar la navegación.','Не удалось включить навигацию.','Overlay-Steuerung konnte nicht aktiviert werden.'),
'알림 영역에서 계속 실행됩니다.': ('Lexift is still running in the system tray.','通知領域で引き続き実行します。','Lexift 将继续在系统托盘中运行。','Lexift 將繼續在系統匣中執行。','Lexift reste actif dans la zone de notification.','Lexift sigue activo en la bandeja del sistema.','Lexift продолжает работать в области уведомлений.','Lexift läuft im Infobereich weiter.'),
'Lexift 실행 중': ('Lexift is running','Lexift 実行中','Lexift 正在运行','Lexift 執行中','Lexift est actif','Lexift en ejecución','Lexift запущен','Lexift läuft'),
'단축키 연결 실패': ('Shortcut unavailable','ショートカットを登録できません','快捷键不可用','快捷鍵無法使用','Raccourci indisponible','Atajo no disponible','Сочетание недоступно','Tastenkürzel nicht verfügbar'),
'단축키 오류': ('Shortcut error','ショートカットエラー','快捷键错误','快捷鍵錯誤','Erreur de raccourci','Error de atajo','Ошибка сочетания','Tastenkürzelfehler'),
'단축키 변경 실패': ('Could not change shortcut','ショートカットを変更できません','无法更改快捷键','無法變更快捷鍵','Impossible de changer le raccourci','No se pudo cambiar el atajo','Не удалось изменить сочетание','Tastenkürzel konnte nicht geändert werden'),
'입력기 설정을 저장했습니다.': ('Input slots saved.','入力方式を保存しました。','已保存输入法设置。','已儲存輸入法設定。','Emplacements enregistrés.','Perfiles guardados.','Раскладки сохранены.','Eingaben gespeichert.'),
'입력기 전환': ('Switch input','入力を切り替える','切换输入法','切換輸入法','Changer de saisie','Cambiar entrada','Сменить раскладку','Eingabe wechseln'),
'입력할 창으로 돌아가': ('Return to the app you want to type in and press','入力先の画面に戻り、押してください：','请回到输入窗口并按','請返回輸入視窗並按','Revenez à l’application cible et appuyez sur','Vuelve a la aplicación y pulsa','Вернитесь в нужное окно и нажмите','Zum Eingabefenster wechseln und drücken:'),
'현재 Windows에서 사용할 수 있는 입력기가 없습니다.': ('No Windows input methods are available.','利用可能な Windows 入力方式がありません。','未找到可用的 Windows 输入法。','找不到可用的 Windows 輸入法。','Aucune méthode de saisie Windows disponible.','No hay métodos de entrada disponibles.','Нет доступных раскладок Windows.','Keine Windows-Eingaben verfügbar.'),
'Lexift 시작 오류': ('Lexift startup error','Lexift 起動エラー','Lexift 启动错误','Lexift 啟動錯誤','Erreur de démarrage Lexift','Error al iniciar Lexift','Ошибка запуска Lexift','Lexift-Startfehler'),
'언어': ('Language','言語','语言','語言','Langue','Idioma','Язык','Sprache'),
'표시 언어': ('Display language','表示言語','界面语言','介面語言','Langue de l’interface','Idioma de la interfaz','Язык интерфейса','Anzeigesprache'),
'시작': ('Start','開始','开始','開始','Continuer','Continuar','Продолжить','Weiter'),
'언어를 선택하세요': ('Choose a language','言語を選択','选择语言','選擇語言','Choisissez une langue','Elige un idioma','Выберите язык','Sprache auswählen'),
'나중에 설정에서 바꿀 수 있습니다.': ('You can change it later in Settings.','後から設定で変更できます。','稍后可在设置中更改。','稍後可在設定中變更。','Modifiable plus tard dans les paramètres.','Puedes cambiarlo en Ajustes.','Позже можно изменить в настройках.','Später in den Einstellungen änderbar.'),
'입력기': ('Input method','入力方式','输入法','輸入法','Méthode de saisie','Método de entrada','Метод ввода','Eingabemethode'),
'한글': ('Hangul','ハングル','韩文','韓文','Hangul','Hangul','Хангыль','Hangul'),
'영문 (한/영)': ('Latin (Korean IME)','英字（韓国語 IME）','英文（韩语输入法）','英文（韓語輸入法）','Latin (IME coréen)','Latino (IME coreano)','Латиница (корейский IME)','Lateinisch (koreanische IME)'),
'현재 설정 유지': ('Keep current mode','現在のモードを維持','保持当前模式','維持目前模式','Conserver le mode','Mantener modo actual','Оставить режим','Aktuellen Modus behalten'),
'히라가나 / 전각': ('Hiragana / full-width','ひらがな・全角','平假名 / 全角','平假名 / 全形','Hiragana / pleine chasse','Hiragana / ancho completo','Хирагана / полная ширина','Hiragana / Vollbreite'),
'가타카나 / 전각': ('Katakana / full-width','カタカナ・全角','片假名 / 全角','片假名 / 全形','Katakana / pleine chasse','Katakana / ancho completo','Катакана / полная ширина','Katakana / Vollbreite'),
'가타카나 / 반각': ('Katakana / half-width','カタカナ・半角','片假名 / 半角','片假名 / 半形','Katakana / demi-chasse','Katakana / medio ancho','Катакана / половинная ширина','Katakana / Halbbreite'),
'가타카나 / 매번 선택': ('Katakana / ask every time','カタカナ・毎回選択','片假名 / 每次询问','片假名 / 每次詢問','Katakana / demander','Katakana / preguntar','Катакана / спрашивать','Katakana / jedes Mal fragen'),
'키보드 / 입력기 전환': ('Switch keyboard / IME','キーボード切替','切换键盘 / 输入法','切換鍵盤 / 輸入法','Changer clavier / IME','Cambiar teclado / IME','Сменить раскладку / IME','Tastatur / IME wechseln'),
'CapsLock': ('CapsLock','CapsLock','CapsLock','CapsLock','Verr. Maj','Bloq Mayús','CapsLock','Feststelltaste'),
'Ctrl + Shift': ('Ctrl + Shift','Ctrl + Shift','Ctrl + Shift','Ctrl + Shift','Ctrl + Maj','Ctrl + Mayús','Ctrl + Shift','Strg + Umschalt'),
'Ctrl + Alt': ('Ctrl + Alt','Ctrl + Alt','Ctrl + Alt','Ctrl + Alt','Ctrl + Alt','Ctrl + Alt','Ctrl + Alt','Strg + Alt'),
}
_ROWS.update({
'중국어 (중/영)': ('Chinese (Chinese/English)','中国語（中／英）','中文（中/英）','中文（中/英）','Chinois (chinois/anglais)','Chino (chino/inglés)','Китайский (китайский/английский)','Chinesisch (Chinesisch/Englisch)'),
'원어 (IME)': ('Native input (IME)','母語入力（IME）','本地语言（输入法）','原語輸入（輸入法）','Saisie native (IME)','Entrada nativa (IME)','Родной язык (IME)','Landessprache (IME)'),
'영문 (IME)': ('English (IME)','英字（IME）','英文（输入法）','英文（輸入法）','Anglais (IME)','Inglés (IME)','Английский (IME)','Englisch (IME)'),
'IME 입력 모드를 확인하지 못했습니다. 입력기 설정을 확인하세요.': ('Could not verify the IME input mode. Check your IME settings.','IME 入力モードを確認できませんでした。設定を確認してください。','无法确认输入法模式，请检查输入法设置。','無法確認輸入法模式，請檢查輸入法設定。','Impossible de vérifier le mode IME. Vérifiez ses paramètres.','No se pudo verificar el modo IME. Revisa su configuración.','Не удалось проверить режим IME. Проверьте настройки.','IME-Modus konnte nicht bestätigt werden. Einstellungen prüfen.'),
'Lexift 작동 중': ('Lexift is active','Lexift 動作中','Lexift 运行中','Lexift 執行中','Lexift actif','Lexift activo','Lexift работает','Lexift aktiv'),
'Lexift 비활성화': ('Lexift is disabled','Lexift 無効','Lexift 已停用','Lexift 已停用','Lexift désactivé','Lexift desactivado','Lexift отключён','Lexift deaktiviert'),
'Lexift 작동 중\n(단축키 : {shortcut})': ('Lexift is active\n(shortcut: {shortcut})','Lexift 動作中\n（ショートカット：{shortcut}）','Lexift 运行中\n（快捷键：{shortcut}）','Lexift 執行中\n（快捷鍵：{shortcut}）','Lexift actif\n(raccourci : {shortcut})','Lexift activo\n(atajo: {shortcut})','Lexift работает\n(сочетание: {shortcut})','Lexift aktiv\n(Tastenkürzel: {shortcut})'),
'최대 15개까지 등록할 수 있습니다.': ('Up to 15 slots.','最大15個まで設定できます。','最多可设置15个槽位。','最多可設定15個欄位。','15 emplacements maximum.','Hasta 15 perfiles.','До 15 слотов.','Bis zu 15 Plätze.'),
'1–9, 0, A–E 또는 방향키로 선택': ('Select with 1–9, 0, A–E or arrow keys','1–9、0、A–E または矢印キーで選択','使用1–9、0、A–E或方向键选择','使用1–9、0、A–E或方向鍵選擇','Sélection : 1–9, 0, A–E ou flèches','Seleccionar: 1–9, 0, A–E o flechas','Выбор: 1–9, 0, A–E или стрелки','Auswahl: 1–9, 0, A–E oder Pfeiltasten'),
'현재 버전': ('Current version','現在のバージョン','当前版本','目前版本','Version actuelle','Versión actual','Текущая версия','Aktuelle Version'),
'배포 버전': ('Released version','配布バージョン','发布版本','發布版本','Version publiée','Versión publicada','Опубликованная версия','Veröffentlichte Version'),
'최신 버전입니다.': ('You are up to date.','最新バージョンです。','已是最新版本。','已是最新版本。','Vous êtes à jour.','Tienes la última versión.','Установлена последняя версия.','Die Version ist aktuell.'),
'업데이트가 필요합니다.': ('An update is available.','アップデートが必要です。','需要更新。','需要更新。','Une mise à jour est disponible.','Hay una actualización disponible.','Доступно обновление.','Ein Update ist verfügbar.'),
'당신은 개발자입니다.': ('You are a developer.','あなたは開発者です。','你是开发者。','你是開發者。','Vous êtes développeur.','Eres desarrollador.','Вы разработчик.','Du bist Entwickler.'),
'다운로드 및 설치': ('Download and install','ダウンロードしてインストール','下载并安装','下載並安裝','Télécharger et installer','Descargar e instalar','Скачать и установить','Herunterladen und installieren'),
'다운로드 페이지 열기': ('Open download page','ダウンロードページを開く','打开下载页面','開啟下載頁面','Ouvrir la page de téléchargement','Abrir página de descarga','Открыть страницу загрузки','Downloadseite öffnen'),
'닫기': ('Close','閉じる','关闭','關閉','Fermer','Cerrar','Закрыть','Schließen'),
})
_ROWS.update({
'개발자 커피 사주기': ('Buy the developer a coffee','開発者にコーヒーをごちそうする','请开发者喝杯咖啡','請開發者喝杯咖啡','Offrir un café au développeur','Invitar al desarrollador a un café','Угостить разработчика кофе','Dem Entwickler einen Kaffee spendieren'),
'Github.io': ('Github.io','Github.io','Github.io','Github.io','Github.io','Github.io','Github.io','Github.io'),
'불러오는 중...': ('Loading...','読み込み中...','正在加载...','載入中...','Chargement...','Cargando...','Загрузка...','Wird geladen...'),
'버전 {version}': ('Version {version}','バージョン {version}','版本 {version}','版本 {version}','Version {version}','Versión {version}','Версия {version}','Version {version}'),
'개발: {name}': ('Developed by {name}','開発: {name}','开发者：{name}','開發者：{name}','Développé par {name}','Desarrollado por {name}','Разработчик: {name}','Entwickelt von {name}'),
'저작권 © {year} {name}': ('Copyright © {year} {name}','著作権 © {year} {name}','版权所有 © {year} {name}','著作權 © {year} {name}','Droits d’auteur © {year} {name}','Derechos de autor © {year} {name}','Авторские права © {year} {name}','Urheberrecht © {year} {name}'),
'MIT 라이선스': ('MIT License','MIT ライセンス','MIT 许可证','MIT 授權條款','Licence MIT','Licencia MIT','Лицензия MIT','MIT-Lizenz'),
'감사한 분들': ('Special Thanks','ご協力いただいた皆様','特别感谢','特別感謝','Remerciements','Agradecimientos','Особая благодарность','Besonderer Dank'),
'위로 이동': ('Move up','上へ移動','上移','上移','Monter','Subir','Переместить вверх','Nach oben'),
'아래로 이동': ('Move down','下へ移動','下移','下移','Descendre','Bajar','Переместить вниз','Nach unten'),
'확인': ('OK','OK','确定','確定','OK','Aceptar','ОК','OK'),
'예': ('Yes','はい','是','是','Oui','Sí','Да','Ja'),
'아니요': ('No','いいえ','否','否','Non','No','Нет','Nein'),
'일본어': ('Japanese','日本語','日语','日語','Japonais','Japonés','Японский','Japanisch'),
'러시아어': ('Russian','ロシア語','俄语','俄語','Russe','Ruso','Русский','Russisch'),
'스페인어': ('Spanish','スペイン語','西班牙语','西班牙語','Espagnol','Español','Испанский','Spanisch'),
'프랑스어': ('French','フランス語','法语','法語','Français','Francés','Французский','Französisch'),
'독일어': ('German','ドイツ語','德语','德語','Allemand','Alemán','Немецкий','Deutsch'),
'오류 로그: {path}': ('Error log: {path}','エラーログ: {path}','错误日志：{path}','錯誤記錄：{path}','Journal d’erreurs : {path}','Registro de errores: {path}','Журнал ошибок: {path}','Fehlerprotokoll: {path}'),
'자세한 오류는 로그를 확인하세요.': ('See the log for details.','詳細はログをご確認ください。','详细信息请查看日志。','詳細資訊請查看記錄。','Consultez le journal pour plus de détails.','Consulta el registro para más detalles.','Подробности — в журнале ошибок.','Einzelheiten stehen im Fehlerprotokoll.'),
'프로그램을 시작하지 못했습니다. debug.bat으로 오류를 확인하세요.': ('Could not start Lexift. Run debug.bat for details.','Lexift を起動できません。debug.bat で詳細をご確認ください。','无法启动 Lexift。请运行 debug.bat 查看详情。','無法啟動 Lexift。請執行 debug.bat 查看詳情。','Impossible de démarrer Lexift. Lancez debug.bat pour les détails.','No se pudo iniciar Lexift. Ejecuta debug.bat para ver los detalles.','Не удалось запустить Lexift. Запустите debug.bat для диагностики.','Lexift konnte nicht gestartet werden. Für Details debug.bat ausführen.'),
'업데이트를 완료하지 못했습니다. 다시 시도하거나 배포 페이지에서 다운로드하세요.': ('Could not complete the update. Try again or download it from the release page.','更新を完了できません。再試行するか、リリースページからダウンロードしてください。','无法完成更新。请重试或从发布页面下载。','無法完成更新。請重試或從發布頁面下載。','Mise à jour impossible. Réessayez ou téléchargez-la depuis la page de publication.','No se pudo completar la actualización. Reintenta o descárgala desde la página de versiones.','Не удалось завершить обновление. Повторите попытку или скачайте его со страницы релиза.','Update fehlgeschlagen. Erneut versuchen oder von der Release-Seite herunterladen.'),
'업데이트 파일을 확인하지 못했습니다. 공식 배포 파일인지 확인하세요.': ('Could not verify the update. Use the official release package.','更新ファイルを検証できません。公式の配布ファイルをご利用ください。','无法验证更新文件。请使用官方发布包。','無法驗證更新檔案。請使用官方發布套件。','Vérification impossible. Utilisez le paquet officiel.','No se pudo verificar la actualización. Usa el paquete oficial.','Не удалось проверить обновление. Используйте официальный архив.','Update konnte nicht geprüft werden. Das offizielle Release-Paket verwenden.'),
'업데이트 서버에 연결하지 못했습니다. 인터넷 연결을 확인하세요.': ('Could not reach the update server. Check your internet connection.','更新サーバーに接続できません。インターネット接続をご確認ください。','无法连接更新服务器。请检查网络连接。','無法連線至更新伺服器。請檢查網路連線。','Serveur de mise à jour inaccessible. Vérifiez votre connexion internet.','No se pudo conectar al servidor. Comprueba tu conexión a internet.','Нет связи с сервером обновлений. Проверьте подключение к интернету.','Update-Server nicht erreichbar. Internetverbindung prüfen.'),
'파일을 변경할 권한이 없습니다. 폴더 권한과 실행 중인 프로그램을 확인하세요.': ('Cannot change the files. Check folder permissions and running applications.','ファイルを変更できません。フォルダーの権限と実行中のアプリをご確認ください。','无法修改文件。请检查文件夹权限及正在运行的程序。','無法修改檔案。請檢查資料夾權限及執行中的程式。','Modification impossible. Vérifiez les droits du dossier et les applications ouvertes.','No se pueden modificar los archivos. Revisa los permisos y las aplicaciones abiertas.','Не удалось изменить файлы. Проверьте права доступа и запущенные приложения.','Dateien können nicht geändert werden. Ordnerrechte und laufende Programme prüfen.'),
'단축키를 연결하지 못했습니다. 다른 프로그램의 단축키와 겹치는지 확인하세요.': ('Could not register the shortcut. Check for conflicts with other applications.','ショートカットを登録できません。他のアプリとの競合をご確認ください。','无法注册快捷键。请检查是否与其他程序冲突。','無法註冊快捷鍵。請檢查是否與其他程式衝突。','Raccourci indisponible. Vérifiez les conflits avec les autres applications.','No se pudo registrar el atajo. Comprueba si otra aplicación lo está usando.','Не удалось зарегистрировать сочетание. Проверьте конфликты с другими программами.','Tastenkürzel konnte nicht registriert werden. Konflikte mit anderen Programmen prüfen.'),
'입력기를 전환하지 못했습니다. Windows 입력기 설정과 대상 창을 확인하세요.': ('Could not switch input. Check Windows input settings and the target window.','入力を切り替えられません。Windows の入力設定と入力先の画面をご確認ください。','无法切换输入法。请检查 Windows 输入设置及目标窗口。','無法切換輸入法。請檢查 Windows 輸入設定及目標視窗。','Changement de saisie impossible. Vérifiez les paramètres Windows et la fenêtre cible.','No se pudo cambiar la entrada. Revisa la configuración de Windows y la ventana de destino.','Не удалось сменить раскладку. Проверьте настройки Windows и нужное окно.','Eingabewechsel fehlgeschlagen. Windows-Eingabeeinstellungen und Zielfenster prüfen.'),
'업데이트와 복구에 실패했습니다. 다음 백업 폴더를 보존하세요:\n{path}': ('Update and recovery failed. Keep this backup folder:\n{path}','更新と復元に失敗しました。このバックアップを保管してください:\n{path}','更新和恢复失败。请保留此备份文件夹：\n{path}','更新與復原失敗。請保留此備份資料夾：\n{path}','Échec de la mise à jour et de la restauration. Conservez cette sauvegarde :\n{path}','Fallaron la actualización y la recuperación. Conserva esta copia:\n{path}','Обновление и восстановление не удались. Сохраните резервную копию:\n{path}','Update und Wiederherstellung fehlgeschlagen. Diesen Sicherungsordner aufbewahren:\n{path}'),
})
_ROWS.update({
'실행 정보': ('Runtime information','動作情報','运行信息','執行資訊','Informations d’exécution','Información de ejecución','Сведения о работе','Laufzeitinformationen'),
'RAM / 본체': ('RAM / application','RAM・本体','RAM / 主程序','RAM / 主程式','RAM / application','RAM / aplicación','ОЗУ / приложение','RAM / Anwendung'),
'RAM / 단축키 보조': ('RAM / shortcut worker','RAM・ショートカット補助','RAM / 快捷键辅助','RAM / 快捷鍵輔助','RAM / raccourcis','RAM / proceso de atajos','ОЗУ / процесс сочетаний','RAM / Tastenkürzelprozess'),
'전용 메모리 / 본체': ('Private memory / application','プライベートメモリ・本体','专用内存 / 主程序','私人記憶體 / 主程式','Mémoire privée / application','Memoria privada / aplicación','Частная память / приложение','Privater Speicher / Anwendung'),
'가동 시간': ('Uptime','稼働時間','运行时间','執行時間','Durée d’exécution','Tiempo en ejecución','Время работы','Laufzeit'),
'실행 환경': ('Environment','実行環境','运行环境','執行環境','Environnement','Entorno','Среда','Umgebung'),
'런타임': ('Runtime','ランタイム','运行时','執行階段','Moteur d’exécution','Entorno de ejecución','Среда выполнения','Laufzeitumgebung'),
'EXE 배포본': ('Packaged EXE','EXE 配布版','EXE 发行版','EXE 發行版','Version EXE','Versión EXE','Версия EXE','EXE-Version'),
'Python 소스': ('Python source','Python ソース','Python 源码','Python 原始碼','Sources Python','Código Python','Исходный код Python','Python-Quellcode'),
'2초 간격 / 화면에 보일 때만 갱신': ('Every 2 seconds / only while visible','2秒間隔・画面に表示中のみ更新','每2秒刷新 / 仅在可见时更新','每2秒更新 / 僅在可見時更新','Toutes les 2 secondes / uniquement à l’écran','Cada 2 segundos / solo mientras se ve','Раз в 2 секунды / только на экране','Alle 2 Sekunden / nur im sichtbaren Bereich'),
'현재 물리 메모리 사용량입니다. 공유 메모리가 포함됩니다.': ('Current resident memory, including shared pages.','現在の物理メモリ使用量です。共有メモリを含みます。','当前物理内存使用量，包含共享内存。','目前實體記憶體使用量，包含共用記憶體。','Mémoire physique utilisée, pages partagées comprises.','Memoria física actual, incluidas las páginas compartidas.','Текущая физическая память, включая общие страницы.','Aktuell belegter physischer Speicher einschließlich gemeinsam genutzter Seiten.'),
'단축키 보조 프로세스만 표시합니다. 실행 중이 아니면 —로 표시됩니다.': ('Shortcut worker only. A dash means it is not running.','ショートカット補助プロセスのみ表示します。未実行時は — になります。','仅显示快捷键辅助进程。未运行时显示 —。','僅顯示快捷鍵輔助處理程序。未執行時顯示 —。','Processus des raccourcis uniquement. Un tiret indique qu’il est arrêté.','Solo el proceso de atajos. Un guion indica que no está activo.','Только процесс сочетаний. Прочерк означает, что он не запущен.','Nur der Tastenkürzelprozess. Ein Strich bedeutet, dass er nicht läuft.'),
'프로세스 전용 커밋 메모리입니다. 물리 RAM 사용량과 다를 수 있습니다.': ('Private committed memory. This may differ from resident RAM.','プロセス専用のコミットメモリです。物理RAM使用量とは異なる場合があります。','进程专用提交内存，可能与物理RAM使用量不同。','處理程序的私人認可記憶體，可能與實體RAM使用量不同。','Mémoire privée engagée, distincte de la RAM physique.','Memoria privada comprometida; puede diferir de la RAM física.','Частная выделенная память; может отличаться от физической ОЗУ.','Privater zugesicherter Speicher; kann vom physischen RAM-Verbrauch abweichen.'),
})
_ROWS.update({
'등록된 입력기 {n}개 / {shortcut}': ('{n} inputs / {shortcut}','入力方式 {n} 件 / {shortcut}','{n} 个输入法 / {shortcut}','{n} 個輸入法 / {shortcut}','{n} saisies / {shortcut}','{n} entradas / {shortcut}','{n} раскладок / {shortcut}','{n} Eingaben / {shortcut}'),
'등록된 입력기 1개 / {shortcut}': ('1 input / {shortcut}','入力方式 1 件 / {shortcut}','1 个输入法 / {shortcut}','1 個輸入法 / {shortcut}','1 saisie / {shortcut}','1 entrada / {shortcut}','1 раскладка / {shortcut}','1 Eingabe / {shortcut}'),
'입력할 창으로 돌아가 {shortcut}를 누르세요.': ('Return to the target app and press {shortcut}.','入力先のアプリに戻り {shortcut} を押してください。','返回输入窗口并按 {shortcut}。','返回輸入視窗並按 {shortcut}。','Revenez à l’application cible et appuyez sur {shortcut}.','Vuelve a la aplicación y pulsa {shortcut}.','Вернитесь в нужное окно и нажмите {shortcut}.','Zum Eingabefenster wechseln und {shortcut} drücken.'),
'{shortcut}로 입력기를 전환하세요.': ('Press {shortcut} to switch inputs.','{shortcut} で入力方式を切り替えます。','按 {shortcut} 切换输入法。','按 {shortcut} 切換輸入法。','Appuyez sur {shortcut} pour changer de saisie.','Pulsa {shortcut} para cambiar la entrada.','Нажмите {shortcut}, чтобы сменить раскладку.','Mit {shortcut} die Eingabe wechseln.'),
})
from feature_i18n import ROWS as FEATURE_ROWS, KOREAN_COPY
_ROWS.update(FEATURE_ROWS)
CODES = ('en','ja','zh_CN','zh_TW','fr','es','ru','de')


class _CatalogView:
    """Read-only column of the shared table, without copying a language dict."""
    __slots__ = ('_index',)

    def __init__(self, index):
        self._index = index

    def __getitem__(self, key):
        return _ROWS[key][self._index]

    def __contains__(self, key):
        return key in _ROWS

    def __iter__(self):
        return iter(_ROWS)

    def __len__(self):
        return len(_ROWS)

    def get(self, key, default=None):
        row = _ROWS.get(key)
        return row[self._index] if row is not None else default

    def keys(self):
        return _ROWS.keys()

    def values(self):
        return (row[self._index] for row in _ROWS.values())

    def items(self):
        return ((key, row[self._index]) for key, row in _ROWS.items())


CATALOG = {code: _CatalogView(index) for index, code in enumerate(CODES)}
# Developer credit data is part of the application package, not a user-editable config.
def set_language(code: str) -> str:
    global _current, _current_index
    if code not in SUPPORTED:
        raise ValueError(f'Unsupported UI language: {code}')
    _current = code
    _current_index = CODES.index(code) if code != 'ko' else -1
    return code

def language() -> str:
    return _current


def load_saved_language() -> str:
    """Read the existing Qt preference without importing Qt or changing settings."""
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r'Software\LuteTools\Lexift\general') as key:
            code = winreg.QueryValueEx(key, 'ui_language')[0]
        if code in SUPPORTED:
            return set_language(code)
    except (OSError, ImportError):
        pass
    return language()


def text_font_family(text: str) -> str:
    """Use known Windows script fonts before Qt searches unrelated families."""
    if any(0x3100 <= ord(char) <= 0x312F or 0x31A0 <= ord(char) <= 0x31BF for char in text):
        return "Microsoft JhengHei UI"
    if any(0x3040 <= ord(char) <= 0x30FF for char in text):
        return "Yu Gothic UI"
    if not any(0xAC00 <= ord(char) <= 0xD7AF for char in text) and any(
            0x3400 <= ord(char) <= 0x9FFF for char in text):
        return {"zh_CN": "Microsoft YaHei UI", "zh_TW": "Microsoft JhengHei UI"}.get(_current, "Yu Gothic UI")
    return "Malgun Gothic"

def tr(key: str) -> str:
    if _current_index < 0:
        return KOREAN_COPY.get(key,key).replace("·", " / ")
    row = _ROWS.get(key)
    return (row[_current_index] if row is not None else key).replace("·", " / ")


def source_key(text: str) -> str:
    if text in _ROWS:
        return text
    # This infrequent dialog lookup intentionally has no growing reverse cache.
    for index in range(len(CODES)):
        for key, row in _ROWS.items():
            if row[index] == text:
                return key
    return text

def tr_mode(mode_label: str) -> str:
    return tr(mode_label)


def error_text(error: Exception, context: str = 'general') -> str:
    """Keep technical diagnostics in logs and localize the visible explanation."""
    import urllib.error
    message = str(error)
    if message in CATALOG['en'] or message in CATALOG.get(language(), {}).values():
        return tr(message)
    if isinstance(error, PermissionError):
        key = '파일을 변경할 권한이 없습니다. 폴더 권한과 실행 중인 프로그램을 확인하세요.'
    elif context == 'update':
        if isinstance(error, (ConnectionError, TimeoutError, urllib.error.URLError)) or any(
                word in message.lower() for word in ('offline', 'network', 'connection', 'http', 'urlopen', 'timed out', 'resolve')):
            key = '업데이트 서버에 연결하지 못했습니다. 인터넷 연결을 확인하세요.'
        elif any(word in message.lower() for word in ('hash', 'digest', 'manifest', 'archive', 'zip', 'package', 'reparse')):
            key = '업데이트 파일을 확인하지 못했습니다. 공식 배포 파일인지 확인하세요.'
        else:
            key = '업데이트를 완료하지 못했습니다. 다시 시도하거나 배포 페이지에서 다운로드하세요.'
    elif context == 'shortcut':
        key = '단축키를 연결하지 못했습니다. 다른 프로그램의 단축키와 겹치는지 확인하세요.'
    elif context == 'input':
        key = '입력기를 전환하지 못했습니다. Windows 입력기 설정과 대상 창을 확인하세요.'
    else:
        key = '프로그램을 시작하지 못했습니다. debug.bat으로 오류를 확인하세요.'
    return tr(key)

def tr_count(n: int, shortcut: str) -> str:
    if _current == 'ru':
        ending = 'раскладка' if n % 10 == 1 and n % 100 != 11 else (
            'раскладки' if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14) else 'раскладок')
        return f'{n} {ending} / {shortcut}'
    if n == 1:
        return tr('등록된 입력기 1개 / {shortcut}').format(shortcut=shortcut)
    return tr('등록된 입력기 {n}개 / {shortcut}').format(n=n, shortcut=shortcut)

def tr_hint(shortcut: str) -> str:
    return tr('입력할 창으로 돌아가 {shortcut}를 누르세요.').format(shortcut=shortcut)

def tr_notify(shortcut: str) -> str:
    return tr('{shortcut}로 입력기를 전환하세요.').format(shortcut=shortcut)

_EXTRA_ROWS = {
'이전 입력 창으로 돌아갈 수 없습니다. 다시 단축키를 눌러주세요.':
('Cannot return to the target window. Try the shortcut again.','元の入力画面に戻れません。もう一度操作してください。','无法返回原输入窗口，请重试快捷键。','無法返回原輸入視窗，請重試快捷鍵。','Impossible de revenir à la fenêtre cible. Réessayez.','No se pudo volver a la ventana. Repite el atajo.','Не удалось вернуться в окно. Повторите сочетание.','Zum Zielfenster konnte nicht gewechselt werden. Erneut versuchen.'),
'입력기가 바뀌지 않았습니다. Windows 입력기 설정을 확인하세요.':
('Input did not change. Check Windows input settings.','入力方式を切り替えられません。Windows の設定をご確認ください。','输入法未切换。请检查 Windows 输入设置。','輸入法未切換。請檢查 Windows 輸入設定。','Saisie inchangée. Vérifiez les paramètres Windows.','La entrada no cambió. Revisa la configuración de Windows.','Раскладка не сменилась. Проверьте настройки Windows.','Eingabe nicht gewechselt. Windows-Einstellungen prüfen.'),
'Windows 입력기 전환 명령을 실행하지 못했습니다.':
('Windows input switching failed.','Windows の入力切替に失敗しました。','Windows 输入法切换失败。','Windows 輸入法切換失敗。','Échec du changement de saisie Windows.','Falló el cambio de entrada de Windows.','Не удалось переключить раскладку Windows.','Windows-Eingabewechsel fehlgeschlagen.'),
'한/영 전환을 완료하지 못했습니다.':
('Could not switch Hangul/Latin mode.','韓英入力を切り替えられませんでした。','无法切换韩文/英文模式。','無法切換韓文/英文模式。','Impossible de changer le mode coréen/latin.','No se pudo cambiar el modo coreano/latino.','Не удалось сменить корейский/латинский режим.','Hangul/Lateinisch-Wechsel fehlgeschlagen.'),
'한국어 입력 상태를 확인하지 못했습니다.':
('Could not verify Korean input mode.','韓国語入力モードを確認できません。','无法确认韩语输入模式。','無法確認韓語輸入模式。','Impossible de vérifier le mode coréen.','No se pudo verificar el modo coreano.','Не удалось проверить корейский режим.','Koreanischen Modus konnte nicht geprüft werden.'),
'일본어 IME 모드를 확인하지 못했습니다.':
('Could not verify Japanese IME mode.','日本語 IME モードを確認できません。','无法确认日语输入法模式。','無法確認日語輸入法模式。','Impossible de vérifier le mode IME japonais.','No se pudo verificar el modo IME japonés.','Не удалось проверить режим японского IME.','Japanischer IME-Modus nicht überprüfbar.'),
'일본어 IME 전환키를 전달하지 못했습니다.':
('Could not send Japanese IME shortcut.','日本語 IME の切替キーを送れません。','无法发送日语输入法快捷键。','無法傳送日語輸入法快速鍵。','Impossible d’envoyer la touche IME japonaise.','No se pudo enviar el atajo IME japonés.','Не удалось отправить команду японскому IME.','Japanischer IME-Befehl konnte nicht gesendet werden.'),
'Lexift가 이미 실행 중입니다.\n작업표시줄 알림 영역의 K 아이콘을 확인하세요.':
('Lexift is already running.\nCheck the K icon in the system tray.','Lexift はすでに実行中です。\n通知領域の K アイコンをご確認ください。','Lexift 已在运行。\n请查看系统托盘中的 K 图标。','Lexift 已在執行。\n請查看系統匣中的 K 圖示。','Lexift est déjà actif.\nCherchez l’icône K dans la zone de notification.','Lexift ya está activo.\nBusca el icono K en la bandeja del sistema.','Lexift уже запущен.\nНайдите значок K в области уведомлений.','Lexift läuft bereits.\nPrüfen Sie das K-Symbol im Infobereich.'),
}
_ROWS.update(_EXTRA_ROWS)
del _EXTRA_ROWS
