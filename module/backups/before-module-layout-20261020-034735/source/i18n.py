from __future__ import annotations

LANGUAGES = (
    ('ko', '한국어'), ('en', 'English'), ('ja', '日本語'),
    ('zh_CN', '简体中文'), ('zh_TW', '繁體中文'),
    ('fr', 'Français'), ('es', 'Español'), ('ru', 'Русский'), ('de', 'Deutsch'),
)
SUPPORTED = {code for code, _ in LANGUAGES}
_current = 'ko'

# Stable Korean source keys. Languages per row: English, Japanese, Chinese simplified,
# Chinese traditional, French, Spanish, Russian, German.
_ROWS = {
'한국어': ('Korean','韓国語','韩语','韓語','Coréen','Coreano','Корейский','Koreanisch'),
'영어': ('English','英語','英语','英語','Anglais','Inglés','Английский','Englisch'),
'중국어': ('Chinese','中国語','中文','中文','Chinois','Chino','Китайский','Chinesisch'),
'일본어 · 히라가나': ('Japanese · Hiragana','日本語 · ひらがな','日语 · 平假名','日語 · 平假名','Japonais · Hiragana','Japonés · Hiragana','Японский · Хирагана','Japanisch · Hiragana'),
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
'Enter 선택    ·    Esc 닫기': ('Enter select · Esc close','Enter 選択 · Esc 閉じる','Enter 确认 · Esc 关闭','Enter 確認 · Esc 關閉','Entrée valider · Échap fermer','Intro elegir · Esc cerrar','Enter — выбрать · Esc — закрыть','Enter wählen · Esc schließen'),
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
'창을 닫으면 KanaShift가 종료됩니다.': ('Closing the window quits KanaShift.','ウィンドウを閉じると終了します。','关闭窗口将退出 KanaShift。','關閉視窗將結束 KanaShift。','Fermer la fenêtre quitte KanaShift.','Cerrar la ventana sale de KanaShift.','Закрытие окна завершает KanaShift.','Das Schließen beendet KanaShift.'),
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
'알림 영역에서 계속 실행됩니다.': ('KanaShift is still running in the system tray.','通知領域で引き続き実行します。','KanaShift 将继续在系统托盘中运行。','KanaShift 將繼續在系統匣中執行。','KanaShift reste actif dans la zone de notification.','KanaShift sigue activo en la bandeja del sistema.','KanaShift продолжает работать в области уведомлений.','KanaShift läuft im Infobereich weiter.'),
'KanaShift 실행 중': ('KanaShift is running','KanaShift 実行中','KanaShift 正在运行','KanaShift 執行中','KanaShift est actif','KanaShift en ejecución','KanaShift запущен','KanaShift läuft'),
'단축키 연결 실패': ('Shortcut unavailable','ショートカットを登録できません','快捷键不可用','快捷鍵無法使用','Raccourci indisponible','Atajo no disponible','Сочетание недоступно','Tastenkürzel nicht verfügbar'),
'단축키 오류': ('Shortcut error','ショートカットエラー','快捷键错误','快捷鍵錯誤','Erreur de raccourci','Error de atajo','Ошибка сочетания','Tastenkürzelfehler'),
'단축키 변경 실패': ('Could not change shortcut','ショートカットを変更できません','无法更改快捷键','無法變更快捷鍵','Impossible de changer le raccourci','No se pudo cambiar el atajo','Не удалось изменить сочетание','Tastenkürzel konnte nicht geändert werden'),
'입력기 설정을 저장했습니다.': ('Input slots saved.','入力方式を保存しました。','已保存输入法设置。','已儲存輸入法設定。','Emplacements enregistrés.','Perfiles guardados.','Раскладки сохранены.','Eingaben gespeichert.'),
'입력기 전환': ('Switch input','入力を切り替える','切换输入法','切換輸入法','Changer de saisie','Cambiar entrada','Сменить раскладку','Eingabe wechseln'),
'입력할 창으로 돌아가': ('Return to the app you want to type in and press','入力先の画面に戻り、押してください：','请回到输入窗口并按','請返回輸入視窗並按','Revenez à l’application cible et appuyez sur','Vuelve a la aplicación y pulsa','Вернитесь в нужное окно и нажмите','Zum Eingabefenster wechseln und drücken:'),
'현재 Windows에서 사용할 수 있는 입력기가 없습니다.': ('No Windows input methods are available.','利用可能な Windows 入力方式がありません。','未找到可用的 Windows 输入法。','找不到可用的 Windows 輸入法。','Aucune méthode de saisie Windows disponible.','No hay métodos de entrada disponibles.','Нет доступных раскладок Windows.','Keine Windows-Eingaben verfügbar.'),
'KanaShift 시작 오류': ('KanaShift startup error','KanaShift 起動エラー','KanaShift 启动错误','KanaShift 啟動錯誤','Erreur de démarrage KanaShift','Error al iniciar KanaShift','Ошибка запуска KanaShift','KanaShift-Startfehler'),
'언어': ('Language','言語','语言','語言','Langue','Idioma','Язык','Sprache'),
'표시 언어': ('Display language','表示言語','界面语言','介面語言','Langue de l’interface','Idioma de la interfaz','Язык интерфейса','Anzeigesprache'),
'시작': ('Start','開始','开始','開始','Continuer','Continuar','Продолжить','Weiter'),
'언어를 선택하세요': ('Choose a language','言語を選択','选择语言','選擇語言','Choisissez une langue','Elige un idioma','Выберите язык','Sprache auswählen'),
'나중에 설정에서 바꿀 수 있습니다.': ('You can change it later in Settings.','後から設定で変更できます。','稍后可在设置中更改。','稍後可在設定中變更。','Modifiable plus tard dans les paramètres.','Puedes cambiarlo en Ajustes.','Позже можно изменить в настройках.','Später in den Einstellungen änderbar.'),
'입력기': ('Input method','入力方式','输入法','輸入法','Méthode de saisie','Método de entrada','Метод ввода','Eingabemethode'),
'한글': ('Hangul','ハングル','韩文','韓文','Hangul','Hangul','Хангыль','Hangul'),
'영문 (한/영)': ('Latin (Korean IME)','英字（韓国語 IME）','英文（韩语输入法）','英文（韓語輸入法）','Latin (IME coréen)','Latino (IME coreano)','Латиница (корейский IME)','Lateinisch (koreanische IME)'),
'현재 설정 유지': ('Keep current mode','現在のモードを維持','保持当前模式','維持目前模式','Conserver le mode','Mantener modo actual','Оставить режим','Aktuellen Modus behalten'),
'히라가나 · 전각': ('Hiragana · full-width','ひらがな・全角','平假名 · 全角','平假名 · 全形','Hiragana · pleine chasse','Hiragana · ancho completo','Хирагана · полная ширина','Hiragana · Vollbreite'),
'가타카나 · 전각': ('Katakana · full-width','カタカナ・全角','片假名 · 全角','片假名 · 全形','Katakana · pleine chasse','Katakana · ancho completo','Катакана · полная ширина','Katakana · Vollbreite'),
'가타카나 · 반각': ('Katakana · half-width','カタカナ・半角','片假名 · 半角','片假名 · 半形','Katakana · demi-chasse','Katakana · medio ancho','Катакана · половинная ширина','Katakana · Halbbreite'),
'가타카나 · 매번 선택': ('Katakana · ask every time','カタカナ・毎回選択','片假名 · 每次询问','片假名 · 每次詢問','Katakana · demander','Katakana · preguntar','Катакана · спрашивать','Katakana · jedes Mal fragen'),
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
'KanaShift 작동 중': ('KanaShift is active','KanaShift 動作中','KanaShift 运行中','KanaShift 執行中','KanaShift actif','KanaShift activo','KanaShift работает','KanaShift aktiv'),
'KanaShift 비활성화': ('KanaShift is disabled','KanaShift 無効','KanaShift 已停用','KanaShift 已停用','KanaShift désactivé','KanaShift desactivado','KanaShift отключён','KanaShift deaktiviert'),
'KanaShift 작동 중\n(단축키 : {shortcut})': ('KanaShift is active\n(shortcut: {shortcut})','KanaShift 動作中\n（ショートカット：{shortcut}）','KanaShift 运行中\n（快捷键：{shortcut}）','KanaShift 執行中\n（快捷鍵：{shortcut}）','KanaShift actif\n(raccourci : {shortcut})','KanaShift activo\n(atajo: {shortcut})','KanaShift работает\n(сочетание: {shortcut})','KanaShift aktiv\n(Tastenkürzel: {shortcut})'),
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
CODES = ('en','ja','zh_CN','zh_TW','fr','es','ru','de')
CATALOG = {code: {k: row[i] for k, row in _ROWS.items()} for i, code in enumerate(CODES)}
# Developer credit data is part of the application package, not a user-editable config.
def set_language(code: str) -> str:
    global _current
    if code not in SUPPORTED:
        raise ValueError(f'Unsupported UI language: {code}')
    _current = code
    return code

def language() -> str:
    return _current


def text_font_family(text: str) -> str:
    """Use known Windows script fonts before Qt searches unrelated families."""
    if any(0x3040 <= ord(char) <= 0x30FF for char in text):
        return "Yu Gothic UI"
    if not any(0xAC00 <= ord(char) <= 0xD7AF for char in text) and any(
            0x3400 <= ord(char) <= 0x9FFF for char in text):
        return {"zh_CN": "Microsoft YaHei UI", "zh_TW": "Microsoft JhengHei UI"}.get(_current, "Yu Gothic UI")
    return "Malgun Gothic"

def tr(key: str) -> str:
    if _current == 'ko':
        return key
    return CATALOG.get(_current, {}).get(key, CATALOG['en'].get(key, key))

def tr_mode(mode_label: str) -> str:
    return tr(mode_label)

def tr_count(n: int, shortcut: str) -> str:
    templates = {
        'ko':'등록된 입력기 {n}개 · {shortcut}',
        'en':'{n} inputs · {shortcut}', 'ja':'入力方式 {n} 件 · {shortcut}',
        'zh_CN':'{n} 个输入法 · {shortcut}', 'zh_TW':'{n} 個輸入法 · {shortcut}',
        'fr':'{n} saisies · {shortcut}', 'es':'{n} entradas · {shortcut}',
        'ru':'{n} раскладок · {shortcut}', 'de':'{n} Eingaben · {shortcut}',
    }
    return templates[_current].format(n=n, shortcut=shortcut)

def tr_hint(shortcut: str) -> str:
    templates = {
        'ko':'입력할 창으로 돌아가 {shortcut}를 누르세요.',
        'en':'Return to the target app and press {shortcut}.',
        'ja':'入力先のアプリに戻り {shortcut} を押してください。',
        'zh_CN':'返回输入窗口并按 {shortcut}。', 'zh_TW':'返回輸入視窗並按 {shortcut}。',
        'fr':'Revenez à l’application cible et appuyez sur {shortcut}.',
        'es':'Vuelve a la aplicación y pulsa {shortcut}.',
        'ru':'Вернитесь в нужное окно и нажмите {shortcut}.',
        'de':'Zum Eingabefenster wechseln und {shortcut} drücken.',
    }
    return templates[_current].format(shortcut=shortcut)

def tr_notify(shortcut: str) -> str:
    templates = {
        'ko':'{shortcut}로 입력기를 전환하세요.', 'en':'Press {shortcut} to switch inputs.',
        'ja':'{shortcut} で入力方式を切り替えます。',
        'zh_CN':'按 {shortcut} 切换输入法。', 'zh_TW':'按 {shortcut} 切換輸入法。',
        'fr':'Appuyez sur {shortcut} pour changer de saisie.',
        'es':'Pulsa {shortcut} para cambiar la entrada.',
        'ru':'Нажмите {shortcut}, чтобы сменить раскладку.',
        'de':'Mit {shortcut} die Eingabe wechseln.',
    }
    return templates[_current].format(shortcut=shortcut)

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
'KanaShift가 이미 실행 중입니다.\n작업표시줄 알림 영역의 K 아이콘을 확인하세요.':
('KanaShift is already running.\nCheck the K icon in the system tray.','KanaShift はすでに実行中です。\n通知領域の K アイコンをご確認ください。','KanaShift 已在运行。\n请查看系统托盘中的 K 图标。','KanaShift 已在執行。\n請查看系統匣中的 K 圖示。','KanaShift est déjà actif.\nCherchez l’icône K dans la zone de notification.','KanaShift ya está activo.\nBusca el icono K en la bandeja del sistema.','KanaShift уже запущен.\nНайдите значок K в области уведомлений.','KanaShift läuft bereits.\nPrüfen Sie das K-Symbol im Infobereich.'),
}
for _i, _code in enumerate(CODES):
    CATALOG[_code].update({key: row[_i] for key, row in _EXTRA_ROWS.items()})
