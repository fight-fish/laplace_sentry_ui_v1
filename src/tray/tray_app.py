import sys
from pathlib import Path
from typing import cast


from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QSystemTrayIcon,
    QMenu,
    QStyle,
    QTableWidget,
    QTableWidgetItem,
    QSplitter,
    QFrame,
    QPushButton,
    QAbstractItemView,
)
from PySide6.QtGui import QIcon, QAction, QColor, QPalette

from pathlib import Path

from src.backend import adapter   



class SentryConsoleWindow(QWidget):
    """
    Sentry 控制台主視窗（接 backend_adapter 的雛型）

    - 左側：專案列表（來自 adapter.list_projects）
    - 右側：顯示目前選取專案的詳細狀態
    - 下方：忽略設定區（目前只顯示 stub 資料）
    """

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Sentry 控制台 v1（雛型）")
        self.resize(900, 600)

        # 目前載入的專案列表（adapter.ProjectInfo）
        self.current_projects: list[adapter.ProjectInfo] = []

        self._build_ui()
        self._reload_projects_from_backend()
        self._load_ignore_settings()

    # ---------------------------
    # UI 建構
    # ---------------------------

    def _build_ui(self) -> None:
        main_layout = QVBoxLayout(self)

        splitter = QSplitter(Qt.Orientation.Horizontal, self)


        # 左側：專案列表
        self.project_table = self._build_project_table()
        splitter.addWidget(self.project_table)

        # 右側：專案詳情
        self.detail_panel = self._build_detail_panel()
        splitter.addWidget(self.detail_panel)

        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 4)

        # 下方：忽略設定區
        bottom_panel = self._build_bottom_panel()

        main_layout.addWidget(splitter)
        main_layout.addWidget(bottom_panel)

        # 事件連結
        self.project_table.itemSelectionChanged.connect(
            self._on_project_selection_changed
        )
        self.project_table.itemDoubleClicked.connect(
            self._on_project_double_clicked
        )

    def _build_project_table(self) -> QTableWidget:
        table = QTableWidget(self)
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels(["專案名稱", "監控狀態", "模式"])

        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.verticalHeader().setVisible(False)
        table.setAlternatingRowColors(True)
        table.setSortingEnabled(False)

        header = table.horizontalHeader()
        header.setStretchLastSection(True)

        # ---- 顏色調整：降低藍底對比，改成柔和選取色 ----
        palette: QPalette = table.palette()

        # 選取底色：很淡的灰藍（你之後可以自己調整）
        palette.setColor(QPalette.ColorRole.Highlight, QColor(210, 225, 245))
        # 選取文字顏色：維持黑色，閱讀比較舒服
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(0, 0, 0))

        table.setPalette(palette)

        return table


    def _build_detail_panel(self) -> QFrame:
        frame = QFrame(self)
        frame.setFrameShape(QFrame.Shape.StyledPanel)



        layout = QVBoxLayout(frame)
        self.detail_label = QLabel(
            "專案詳情區：\n"
            "選取左側某個專案後，會在這裡顯示其狀態與模式。\n"
            "雙擊列可以切換【監控中／已停止】（目前為假後端 stub）。"
        )
        self.detail_label.setWordWrap(True)

        layout.addWidget(self.detail_label)
        layout.addStretch(1)
        return frame

    def _build_bottom_panel(self) -> QFrame:
        frame = QFrame(self)
        frame.setFrameShape(QFrame.Shape.StyledPanel)  # ★ 修正 StyledPanel

        layout = QHBoxLayout(frame)
        self.ignore_info_label = QLabel("忽略設定區（暫時版）：尚未載入設定。")
        self.ignore_info_label.setWordWrap(True)

        button_panel = QVBoxLayout()
        btn_sentry_ignore = QPushButton("編輯哨兵忽略清單…")
        btn_tree_ignore = QPushButton("編輯目錄樹忽略規則…")

        btn_sentry_ignore.setEnabled(False)
        btn_tree_ignore.setEnabled(False)

        button_panel.addWidget(btn_sentry_ignore)
        button_panel.addWidget(btn_tree_ignore)
        button_panel.addStretch(1)

        layout.addWidget(self.ignore_info_label, stretch=3)
        layout.addLayout(button_panel, stretch=2)

        return frame


    # ---------------------------
    # 從 backend_adapter 載入資料
    # ---------------------------

    def _reload_projects_from_backend(self) -> None:
        """呼叫 adapter.list_projects()，並刷新表格內容。"""
        self.current_projects = adapter.list_projects()

        self.project_table.setRowCount(len(self.current_projects))
        for row, proj in enumerate(self.current_projects):
            self.project_table.setItem(row, 0, QTableWidgetItem(proj.name))
            self.project_table.setItem(
                row, 1, QTableWidgetItem(self._status_to_label(proj.status))
            )
            self.project_table.setItem(
                row, 2, QTableWidgetItem(self._mode_to_label(proj.mode))
            )

        if self.current_projects:
            self.project_table.selectRow(0)
            self._update_detail_panel(self.current_projects[0])

    def _load_ignore_settings(self) -> None:
        """從 adapter 取得忽略設定，顯示在底部文字區。"""
        settings = adapter.get_ignore_settings()
        text_lines = [
            "忽略設定區（暫時版）：",
            "",
            f"- 哨兵忽略樣式：{', '.join(settings.sentry_ignore_patterns) or '(無)'}",
            f"- 目錄樹深度限制：{settings.tree_depth_limit}",
        ]
        self.ignore_info_label.setText("\n".join(text_lines))

    # ---------------------------
    # 事件處理：選取、雙擊
    # ---------------------------

    def _on_project_selection_changed(self) -> None:
        row = self.project_table.currentRow()
        if row < 0 or row >= len(self.current_projects):
            self._update_detail_panel(None)
            return

        proj = self.current_projects[row]
        self._update_detail_panel(proj)

    def _on_project_double_clicked(self) -> None:
        """雙擊列 → 切換監控狀態（只改 stub 狀態，不呼叫真後端）。"""
        row = self.project_table.currentRow()
        if row < 0 or row >= len(self.current_projects):
            return

        proj = self.current_projects[row]
        updated = adapter.toggle_project_status(proj.name)
        if updated is None:
            return

        # 更新本地快取
        self.current_projects[row] = updated

        # 更新表格上的狀態欄位
        status_item = self.project_table.item(row, 1)
        if status_item is not None:
            status_item.setText(self._status_to_label(updated.status))

        # 同步詳情區
        self._update_detail_panel(updated)

    # ---------------------------
    # 詳情區更新
    # ---------------------------

    def _update_detail_panel(
        self,
        proj: adapter.ProjectInfo | None,
    ) -> None:
        if proj is None:
            self.detail_label.setText("尚未選取任何專案。")
            return

        status_label = self._status_to_label(proj.status)
        mode_label = self._mode_to_label(proj.mode)

        text_lines = [
            f"專案名稱：{proj.name}",
            f"監控狀態：{status_label}",
            f"模式：{mode_label}",
            "",
            "（目前為假後端 stub：之後會改成顯示真實的寫入檔路徑、日誌入口等）",
            "雙擊左側列表可在【監控中／已停止】之間切換（僅影響 stub 狀態）。",
        ]
        self.detail_label.setText("\n".join(text_lines))

    # ---------------------------
    # 標籤轉換（之後可以抽成 i18n）
    # ---------------------------

    @staticmethod
    def _status_to_label(status: str) -> str:
        return "監控中" if status == "monitoring" else "已停止"

    @staticmethod
    def _mode_to_label(mode: str) -> str:
        return "靜默" if mode == "silent" else "互動"





class SentryTrayApp:
    """系統托盤應用程式：負責托盤圖示與主控台視窗。"""

    def __init__(self, app: QApplication) -> None:
        self.app = app
        self.console = SentryConsoleWindow()

        # 載入托盤圖示
        icon = self._load_icon()

        self.tray_icon = QSystemTrayIcon(icon, self.app)
        self.tray_icon.setToolTip("Laplace Sentry 控制台")

        # 建立右鍵選單
        menu = QMenu()
        self._build_menu(menu)
        self.tray_icon.setContextMenu(menu)

        # 左鍵點擊托盤 → 打開控制台
        self.tray_icon.activated.connect(self._on_activated)

        # 顯示托盤
        self.tray_icon.show()

    def _load_icon(self) -> QIcon:
        """從 assets/icons/tray_icon.png 載入圖示；若失敗則使用系統預設圖示。"""
        root = Path(__file__).resolve().parents[2]
        icon_path = root / "assets" / "icons" / "tray_icon.png"

        if icon_path.is_file():
            icon = QIcon(str(icon_path))
            if not icon.isNull():
                return icon

        # 後備方案：使用系統內建圖示，避免 QSystemTrayIcon::setVisible: No Icon set
        app = QApplication.instance()
        if app is not None:
            # Pylance 把 instance() 視為 QCoreApplication，我們明確告訴它其實是 QApplication
            app_qt = cast(QApplication, app)
            style = app_qt.style()
            return style.standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)

        # 理論上不會跑到這裡；保底回傳一個空 icon
        return QIcon()



    def _build_menu(self, menu: QMenu) -> None:
        """建立托盤右鍵選單。"""

        open_console_action = QAction("開啟控制台", menu)
        open_console_action.triggered.connect(self.show_console)

        quit_action = QAction("退出", menu)
        quit_action.triggered.connect(self.app.quit)

        menu.addAction(open_console_action)
        menu.addSeparator()
        menu.addAction(quit_action)

    def show_console(self) -> None:
        """顯示控制台視窗並把它拉到前景。"""
        self.console.show()
        self.console.activateWindow()
        self.console.raise_()

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """托盤圖示被點擊時的行為：左鍵 → 打開控制台。"""
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.show_console()


def main() -> None:
    """應用程式進入點。"""
    app = QApplication(sys.argv)

    # 關閉最後一個視窗時不要自動退出，交給「退出」選單控制
    app.setQuitOnLastWindowClosed(False)

    tray_app = SentryTrayApp(app)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
