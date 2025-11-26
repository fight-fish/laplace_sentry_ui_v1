# --- 1. 導入系統與路徑管理工具 ---

# 導入（import）Python 系統（sys）工具，用於跟作業系統互動。
import sys
# 導入（import）路徑處理（pathlib）中的 Path 工具，方便處理檔案路徑。
from pathlib import Path
# 導入（import）類型提示（typing）中的 cast，用於幫助程式碼更清晰。
from typing import cast


# --- 2. 導入 PySide6 介面相關模組 ---

# 導入 PySide6 的 Qt 核心（QtCore）中的 Qt，裡面包含各種常數設定。
from PySide6.QtCore import Qt
# 導入 PySide6 的視窗元件（QtWidgets），這是所有介面組件的來源。
from PySide6.QtWidgets import (
    # 這是應用程式（Application）的主入口。
    QApplication,
    # 這是所有介面元件的基礎元件（Widget）。
    QWidget,
    # 垂直佈局（Vertical Box Layout），把東西從上往下排。
    QVBoxLayout,
    # 水平佈局（Horizontal Box Layout），把東西從左往右排。
    QHBoxLayout,
    # 用來顯示文字的標籤（Label）。
    QLabel,
    # 這是系統托盤圖標（System Tray Icon），就是右下角的小圖標。
    QSystemTrayIcon,
    # 這是右鍵點擊會彈出來的選單（Menu）。
    QMenu,
    # 這是用於獲取標準外觀樣式（Style）的工具。
    QStyle,
    # 用來顯示表格（Table）的元件。
    QTableWidget,
    # 表格中的單一個項目（Item）。
    QTableWidgetItem,
    # 可以拖拉調整大小的分隔器（Splitter）。
    QSplitter,
    # 邊框或分隔線（Frame）元件。
    QFrame,
    # 按鈕（Button）元件。
    QPushButton,
    # 這是表格或列表的選取模式（Abstract Item View），例如只選一行。
    QAbstractItemView,
    # 單行文字輸入框（Line Edit）。
    QLineEdit,
    # 用來彈出檔案選取對話框（File Dialog）的工具。
    QFileDialog,
    # 用來彈出標準訊息框（Message Box），例如警告或確認。
    QMessageBox,
)
# 導入 PySide6 的圖形介面（QtGui）中的 QIcon（圖標）、QAction（動作）和 QColor（顏色）等。
from PySide6.QtGui import QIcon, QAction, QColor, QPalette

# --- 3. 導入自定義模組 ---

# 再次導入（import）路徑處理（pathlib）中的 Path 工具。（雖然上面有，但這裡保留）
from pathlib import Path

# 從「src/backend」這個資料夾中，導入（import）我們的資料庫處理工具（adapter）。
from src.backend import adapter 

class SentryConsoleWindow(QWidget):
    """
    Sentry 控制台主視窗（接 backend_adapter 的雛型）

    - 左側：專案列表（來自 adapter.list_projects）
    - 右側：顯示目前選取專案的詳細狀態
    - 下方：忽略設定區（目前只顯示 stub 資料）
    """

# 這裡，我們用「def」來 定義（define）一個物件被建立時會自動執行的函式（__init__）。
    def __init__(self) -> None:
        # 我們必須先呼叫（super().__init__()）基礎類別 QWidget 的初始化方法。
        super().__init__()
        # 設定視窗的標題（Window Title）。
        self.setWindowTitle("Sentry 控制台 v1（雛型）")
        # 設定視窗的初始大小（resize），寬 900 像素，高 600 像素。
        self.resize(900, 600)

        # # TODO: 這裡的註解將使用通俗比喻來解釋資料結構。
        # 準備一個叫「current_projects」的空籃子（[]），
        # 專門用來存放從後端讀取的專案資訊（adapter.ProjectInfo）。
        self.current_projects: list[adapter.ProjectInfo] = []

        # 呼叫（call）_build_ui 函式，開始建立所有的介面元件。
        self._build_ui()
        # 呼叫（call）_reload_projects_from_backend 函式，從後端資料庫載入專案列表。
        self._reload_projects_from_backend()
        # 呼叫（call）_load_ignore_settings 函式，載入程式的忽略設定。
        self._load_ignore_settings()

    # ---------------------------
    # UI 建構
    # ---------------------------

# 這裡，我們用「def」來定義（define）建立介面（UI）的函式。
    def _build_ui(self) -> None:
        # 建立主佈局（main_layout），採用垂直佈局（QVBoxLayout），東西將從上往下排。
        main_layout = QVBoxLayout(self)

        # 建立一個分割器（QSplitter），它可以讓使用者拖拉調整左右兩側的大小。
        # Qt.Orientation.Horizontal 表示它是水平分割的。
        splitter = QSplitter(Qt.Orientation.Horizontal, self)

        # --- 1. 左側：專案列表 ---
        # 呼叫（call）另一個函式來建立專案表格（project_table）。
        self.project_table = self._build_project_table()
        # 把表格元件（project_table）加入（addWidget）到分割器的左邊。
        splitter.addWidget(self.project_table)

        # --- 2. 右側：專案詳情 ---
        # 呼叫（call）另一個函式來建立專案詳情面板（detail_panel）。
        self.detail_panel = self._build_detail_panel()
        # 把詳情面板（detail_panel）加入（addWidget）到分割器的右邊。
        splitter.addWidget(self.detail_panel)

        # 設定分割器的拉伸比例（setStretchFactor）。
        # 0（左側）設定為 3 的比例。
        splitter.setStretchFactor(0, 3)
        # 1（右側）設定為 4 的比例，讓右側大一點。
        splitter.setStretchFactor(1, 4)

        # --- 3. 下方：忽略設定區 ---
        # 呼叫（call）另一個函式來建立底部的忽略設定區（bottom_panel）。
        bottom_panel = self._build_bottom_panel()

        # --- 4. 底部狀態訊息列 ---
        # 建立一個標籤（QLabel），用來顯示狀態訊息（status_label）。
        self.status_label = QLabel("")
        # 設定標籤的文字在超過寬度時可以自動換行（setWordWrap）。
        self.status_label.setWordWrap(True)

        # --- 5. 組合所有佈局 ---
        # 把分割器（splitter）加入到主佈局（main_layout）的上半部分。
        main_layout.addWidget(splitter)
        # 把底部面板（bottom_panel）加入到主佈局的中間部分。
        main_layout.addWidget(bottom_panel)
        # 把狀態標籤（status_label）加入到主佈局的最下方。
        main_layout.addWidget(self.status_label)

        # --- 6. 事件連結 (Signal/Slot) ---
        # 當表格的選擇改變時（itemSelectionChanged），連結（connect）到處理函式。
        self.project_table.itemSelectionChanged.connect(
            self._on_project_selection_changed
        )
        # 當表格的項目被雙擊時（itemDoubleClicked），連結（connect）到處理函式。
        self.project_table.itemDoubleClicked.connect(
            self._on_project_double_clicked
        )


# 這裡，我們用「def」來定義（define）建立專案表格的函式。
    def _build_project_table(self) -> QTableWidget:
        # 建立一個表格元件（QTableWidget）。
        table = QTableWidget(self)
        
        # 設定表格的欄位數量（setColumnCount）為 4 個。
        table.setColumnCount(4)
        # 設定水平表頭的標籤（setHorizontalHeaderLabels），依序是欄位名稱。
        table.setHorizontalHeaderLabels(["UUID","專案名稱", "監控狀態", "模式"])

        # 設定選取行為（setSelectionBehavior）：點擊任何一個格子時，會選取（SelectRows）整行。
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        # 設定選取模式（setSelectionMode）：一次只能單獨選取（SingleSelection）一行。
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        # 設定編輯觸發（setEditTriggers）：關閉所有編輯功能（NoEditTriggers），讓表格只顯示資料。
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        # 隱藏垂直表頭（verticalHeader），也就是左側的行號。
        table.verticalHeader().setVisible(False)
        # 開啟交替行顏色（setAlternatingRowColors），讓表格更清晰。
        table.setAlternatingRowColors(True)
        # 關閉表格的排序功能（setSortingEnabled）。
        table.setSortingEnabled(False)
        # 隱藏第 0 欄（UUID），它只用於內部資料處理，不用給使用者看。
        table.setColumnHidden(0, True)

        # 獲取（get）表格的水平表頭（horizontalHeader）元件。
        header = table.horizontalHeader()
        # 設定表頭：讓最後一欄自動拉伸（setStretchLastSection）填滿剩餘空間。
        header.setStretchLastSection(True)

        # ---- 顏色調整：降低藍底對比，改成柔和選取色 ----
        # # HACK: 這裡用 HACK 標籤標註，這是為了處理 Qt 預設的藍色選取背景在 Windows 上對比太高問題。
        # 獲取（get）表格目前的調色盤（palette）。
        palette: QPalette = table.palette()

        # 選取底色：很淡的灰藍（你之後可以自己調整）
        # 設定調色盤的顏色（setColor），指定 Highlight（選取底色）為這個淡藍色。
        palette.setColor(QPalette.ColorRole.Highlight, QColor(210, 225, 245))
        # 選取文字顏色：維持黑色，閱讀比較舒服
        # 設定 HighlightedText（選取後的文字顏色）為黑色。
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(0, 0, 0))

        # 將調整後的調色盤設定（setPalette）回表格。
        table.setPalette(palette)

        # 回傳（return）設定好的表格元件。
        return table


# 這裡，我們用「def」來定義（define）建立右側詳情面板的函式。
    def _build_detail_panel(self) -> QFrame:
        # 建立一個框架（QFrame），作為右側面板的容器。
        frame = QFrame(self)
        # 設定框架的外觀形狀（setFrameShape）為帶有樣式（StyledPanel）的面板。
        frame.setFrameShape(QFrame.Shape.StyledPanel)

        # 建立一個垂直佈局（QVBoxLayout），把元件從上往下排。
        layout = QVBoxLayout(frame)

        # --- 上半部：專案詳情（保留你的原始文字） ---
        # 建立一個標籤（QLabel），用於顯示專案詳情，並將其存入 self.detail_label 以便後續更新。
        self.detail_label = QLabel(
            "專案詳情區：\n"
            "選取左側某個專案後，會在這裡顯示其狀態與模式。\n"
            "雙擊列可以切換【監控中／已停止】（目前為假後端 stub）。"
        )
        # 設定標籤的文字在超過寬度時可以自動換行（setWordWrap）。
        self.detail_label.setWordWrap(True)
        # 把詳情標籤加入（addWidget）到垂直佈局中。
        layout.addWidget(self.detail_label)

        # 加入一個 16 像素的空白間距（addSpacing），將詳情和新增區隔開。
        layout.addSpacing(16)

        # --- 下半部：新增專案（Stub）區 ---
        # 建立新增專案區塊的標題。
        title_label = QLabel("新增專案（Stub｜目前只顯示 UI，不寫入檔案）")
        # 把標題加入（addWidget）到垂直佈局中。
        layout.addWidget(title_label)

        # 這是專門用來放「專案資料夾」和「寫入檔路徑」輸入框的垂直佈局
        self.new_project_input_layout = QVBoxLayout()
        # 把這個垂直佈局（new_project_input_layout）加入到主垂直佈局中。
        layout.addLayout(self.new_project_input_layout)

        # 呼叫（call）專門負責建立這些輸入框的函式
        self._build_input_fields()


        # 送出按鈕（目前 stub）
        self.new_project_submit_button = QPushButton("送出新增請求（Stub）")
        # 預設禁用（setEnabled(False)）送出按鈕。
        self.new_project_submit_button.setEnabled(False)
        # 把按鈕加入（addWidget）到垂直佈局中。
        layout.addWidget(self.new_project_submit_button)
        # 綁定送出按鈕的點擊事件（clicked）到處理函式（Stub）。
        self.new_project_submit_button.clicked.connect(self._on_submit_new_project_stub)
        # 空白推底：加入一個拉伸因子（addStretch(1)），把上面所有東西推到頂部。
        layout.addStretch(1)

        # 回傳（return）設定好的框架元件。
        return frame
    
    def _build_input_fields(self) -> None:
        """
        建立並設定新增專案的輸入欄位（支援 1 個專案資料夾 + 3 個寫入檔）。
        這些元件將被加入到 self.new_project_input_layout 中。
        """
        # 建立一個叫 new_input_fields 的「空籃子」（List），用來存放所有輸入框物件。
        self.new_input_fields: list[QLineEdit] = []
        # 建立一個叫 new_browse_buttons 的「空籃子」（List），用來存放所有瀏覽按鈕物件。
        self.new_browse_buttons: list[QPushButton] = []
        
        # 專案資料夾列 (索引 0)
        # 建立水平佈局（folder_row）
        folder_row = QHBoxLayout()
        # 建立標籤。
        folder_label = QLabel("專案資料夾：")
        # 建立輸入框（QLineEdit）。
        self.new_project_folder_edit = QLineEdit()
        self.new_project_folder_edit.setPlaceholderText("例如：/home/user/my_project")
        # 建立瀏覽按鈕。
        self.new_project_folder_button = QPushButton("瀏覽…")

        # 加入元件到 folder_row
        folder_row.addWidget(folder_label)
        folder_row.addWidget(self.new_project_folder_edit, stretch=1)
        folder_row.addWidget(self.new_project_folder_button)
        
        # 把這個水平佈局加入到 new_project_input_layout 垂直佈局中。
        self.new_project_input_layout.addLayout(folder_row)
        
        # 把輸入框和按鈕儲存到籃子中（未來用索引 0 存取）
        self.new_input_fields.append(self.new_project_folder_edit)
        self.new_browse_buttons.append(self.new_project_folder_button)
        
        # 寫入檔路徑列 (索引 1, 2, 3 - 最多 3 個)
        # 我們用 for...in... 這個結構，來循環（loop）3 次，建立 3 個寫入檔輸入欄位。
        for i in range(1, 4):
            # 建立水平佈局（output_row）
            output_row = QHBoxLayout()
            # 建立標籤（用 i 來區分是第幾個寫入檔）
            output_label = QLabel(f"寫入檔 {i}：")
            # 建立輸入框（QLineEdit）。
            output_edit = QLineEdit()
            output_edit.setPlaceholderText(f"目標 Markdown 文件 {i}")
            # 建立瀏覽按鈕。
            output_button = QPushButton("瀏覽…")
            
            # 將元件加入到 output_row
            output_row.addWidget(output_label)
            output_row.addWidget(output_edit, stretch=1)
            output_row.addWidget(output_button)

            # 把這個水平佈局加入到 new_project_input_layout 垂直佈局中。
            self.new_project_input_layout.addLayout(output_row)

            # 把輸入框和按鈕儲存到籃子中（未來用索引 i 存取）
            self.new_input_fields.append(output_edit)
            self.new_browse_buttons.append(output_button)

            # 讓第 2 和第 3 個寫入檔預設隱藏
            if i >= 2:
                output_row.setContentsMargins(0, 0, 0, 0) # 移除內邊距，讓它完全隱藏
                output_edit.setVisible(False)
                output_label.setVisible(False)
                output_button.setVisible(False)


        # --- 事件連結 (Signal/Slot) ---
        # 綁定「瀏覽…」按鈕的點擊事件到處理函式。
        # 因為我們現在有多個按鈕，我們使用 QWidget.findChildren 來找到它們。
        for btn in self.new_browse_buttons:
            # 這裡我們用 lambda 函式來傳遞按鈕本身，以便在 _on_select_new_path 中知道是哪個按鈕被點擊。
            btn.clicked.connect(lambda checked, b=btn: self._on_select_new_path(b))

        # 當使用者手動改文字時（textChanged），也綁定到檢查函式。
        for edit in self.new_input_fields:
            edit.textChanged.connect(self._update_new_project_submit_state)

        # 建立一個拉伸因子，確保這塊輸入區的內容可以推開。
        self.new_project_input_layout.addStretch(1)


# 這裡，我們用「def」來定義（define）建立底部面板的函式。
    def _build_bottom_panel(self) -> QFrame:
        # 建立一個框架（QFrame），作為底部面板的容器。
        frame = QFrame(self)
        # 設定框架的外觀形狀（setFrameShape）為帶有樣式（StyledPanel）的面板。
        frame.setFrameShape(QFrame.Shape.StyledPanel)

        # 建立主佈局，採用水平佈局（QHBoxLayout），把左右兩塊內容並排。
        layout = QHBoxLayout(frame)

        # 左側：忽略設定 + 狀態訊息（採用垂直佈局）
        left_panel = QVBoxLayout()

        # [1] 忽略設定說明
        # 建立一個標籤（QLabel）用於顯示忽略設定資訊。
        self.ignore_info_label = QLabel("忽略設定區（暫時版）：尚未載入設定。")
        # 設定文字自動換行（setWordWrap）。
        self.ignore_info_label.setWordWrap(True)
        # 把標籤加入（addWidget）到左側垂直佈局。
        left_panel.addWidget(self.ignore_info_label)

        # [2] 狀態訊息列
        # 建立另一個標籤（QLabel）用於顯示詳細的狀態訊息。
        self.status_message_label = QLabel("狀態訊息：目前沒有任何訊息。")
        self.status_message_label.setWordWrap(True)
        # 用比較淡的顏色（#666666）當預設，讓狀態訊息不要太突兀。
        self.status_message_label.setStyleSheet("color: #666666;")
        left_panel.addWidget(self.status_message_label)

        # 讓這兩行資訊貼上去，底下留空（addStretch(1)）。
        left_panel.addStretch(1)

        # 右側：按鈕群（採用垂直佈局）
        button_panel = QVBoxLayout()
        # 建立第一個按鈕：編輯哨兵忽略清單。
        btn_sentry_ignore = QPushButton("編輯哨兵忽略清單…")
        # 建立第二個按鈕：編輯目錄樹忽略規則。
        btn_tree_ignore = QPushButton("編輯目錄樹忽略規則…")

        # 預設禁用這兩個按鈕（setEnabled(False)）。
        btn_sentry_ignore.setEnabled(False)
        btn_tree_ignore.setEnabled(False)

        # 把按鈕依序加入（addWidget）到右側垂直佈局。
        button_panel.addWidget(btn_sentry_ignore)
        button_panel.addWidget(btn_tree_ignore)
        # 加入拉伸因子（addStretch(1)），把按鈕推到頂部。
        button_panel.addStretch(1)

        # --- 組合佈局 ---
        # 把左側面板加入（addLayout）到主水平佈局，佔 3 的比例。
        layout.addLayout(left_panel, stretch=3)
        # 把右側按鈕群加入，佔 2 的比例。
        layout.addLayout(button_panel, stretch=2)

        # 回傳（return）設定好的框架元件。
        return frame



    # ---------------------------
    # 從 backend_adapter 載入資料
    # ---------------------------

# 這裡，我們用「def」來定義（define）重新載入專案的函式。
    def _reload_projects_from_backend(self) -> None:
        # 這個註釋（"""..."""）是說明文件，解釋函式的作用：呼叫後端（adapter）工具並刷新表格。
        """呼叫 adapter.list_projects()，並刷新表格內容。"""
        
        # 呼叫（call）後端（adapter）的 list_projects 函式，獲取所有的專案列表。
        # 並將結果存回我們在 __init__ 準備的「空籃子」（self.current_projects）中。
        self.current_projects = adapter.list_projects()

        # 設定表格的行數（setRowCount），使其等於當前專案的數量（len）。
        self.project_table.setRowCount(len(self.current_projects))
        
        # 我們用「for...in...」這個結構，來一個一個地（enumerate）處理所有專案（self.current_projects）。
        # enumerate 會給我們行號（row）和專案物件（proj）。
        for row, proj in enumerate(self.current_projects):
            # --- 1. UUID（隱藏欄）---
            # 建立一個表格項目（QTableWidgetItem），內容是專案的 UUID。
            uuid_item = QTableWidgetItem(proj.uuid)
            # 設置標誌（setFlags）：使用位運算子（& ~）把「可編輯（ItemIsEditable）」的特性關掉。
            uuid_item.setFlags(uuid_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            # 把這個項目設定（setItem）到表格的指定行（row）、第 0 欄。
            self.project_table.setItem(row, 0, uuid_item)

            # --- 2. 名稱 ---
            # 建立名稱的表格項目，內容是專案名稱（proj.name）。
            name_item = QTableWidgetItem(proj.name)
            # 設置標誌：關閉編輯功能。
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            # 把這個項目設定到表格的指定行（row）、第 1 欄。
            self.project_table.setItem(row, 1, name_item)

            # --- 3. 監控狀態 ---
            # 建立狀態的表格項目，這裡呼叫（call）另一個函式把狀態（proj.status）轉換成中文標籤。
            status_item = QTableWidgetItem(self._status_to_label(proj.status))
            # 設置標誌：關閉編輯功能。
            status_item.setFlags(status_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            # 把這個項目設定到表格的指定行（row）、第 2 欄。
            self.project_table.setItem(row, 2, status_item)

            # --- 4. 模式 ---
            # 建立模式的表格項目，呼叫（call）另一個函式把模式（proj.mode）轉換成中文標籤。
            mode_item = QTableWidgetItem(self._mode_to_label(proj.mode))
            # 設置標誌：關閉編輯功能。
            mode_item.setFlags(mode_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            # 把這個項目設定到表格的指定行（row）、第 3 欄。
            self.project_table.setItem(row, 3, mode_item)

        # 用「if」來判斷，如果（if）專案列表（self.current_projects）裡面有東西...
        if self.current_projects:
            # 就預設選取（selectRow）第一行（0）。
            self.project_table.selectRow(0)
            # 並且呼叫（call）_update_detail_panel 函式，顯示第一行專案的詳細資訊。
            self._update_detail_panel(self.current_projects[0])

# 這裡，我們用「def」來定義（define）載入忽略設定的函式。
    def _load_ignore_settings(self) -> None:
        """從 adapter 取得忽略設定，顯示在底部文字區。"""
        # 呼叫（call）後端（adapter）的 get_ignore_settings 函式，獲取忽略設定物件。
        settings = adapter.get_ignore_settings()
        
        # 建立（[]）一個叫 text_lines 的「文字籃子」，準備好要顯示的每一行文字。
        text_lines = [
            "忽略設定區（暫時版）：",
            "",
            # 這是 f-string 的寫法，用於組裝文字。
            # .join(settings.sentry_ignore_patterns) 會把忽略樣式用逗號連接起來。
            f"- 哨兵忽略樣式：{', '.join(settings.sentry_ignore_patterns) or '(無)'}",
            # 顯示目錄樹的深度限制。
            f"- 目錄樹深度限制：{settings.tree_depth_limit}",
        ]
        # 用換行符號（\n）將「文字籃子」中的每一行文字連接（join）起來，
        # 然後設定（setText）到忽略資訊標籤（ignore_info_label）上。
        self.ignore_info_label.setText("\n".join(text_lines))


    # 這裡，我們用「def」來定義（define）更新底部狀態訊息的函式。
    def _set_status_message(self, text: str, level: str = "info") -> None:
        """
        更新底部狀態訊息列。
        
        level:
            - "info"    一般訊息（灰色）
            - "success" 成功訊息（綠色）
            - "error"   錯誤訊息（紅色）
        """
        # .strip() 是去除文字前後的空格。
        # 如果（or）輸入的 text 是空字串，就用預設文字「狀態訊息：」來代替。
        text = text.strip() or "狀態訊息："

        # 用「if」來判斷（if）：如果 level 是 "error"（錯誤）...
        if level == "error":
            # 顏色就設定為紅色（#aa0000）。
            color = "#aa0000"
        # 用「elif」來判斷（else if）：否則，如果 level 是 "success"（成功）...
        elif level == "success":
            # 顏色就設定為綠色（#006600）。
            color = "#006600"
        # 用「else」來判斷：都不是的話（預設是 "info"）...
        else:
            # 顏色就設定為灰色（#666666）。
            color = "#666666"

        # 設定（setText）狀態訊息標籤的文字。
        self.status_message_label.setText(text)
        # 設定（setStyleSheet）標籤的樣式，把前面判斷好的顏色放進去。
        self.status_message_label.setStyleSheet(f"color: {color};")


    # ---------------------------
    # 事件處理：選取、雙擊
    # ---------------------------

# 這裡，我們用「def」來定義（define）當專案列表的選取項目改變時（selection_changed）執行的函式。
    def _on_project_selection_changed(self) -> None:
        # 獲取（get）目前選取的行號（currentRow）。
        row = self.project_table.currentRow()
        
        # 用「if」來判斷：如果（if）行號小於 0（沒選到）或者超過了專案總數...
        if row < 0 or row >= len(self.current_projects):
            # 就呼叫（call）_update_detail_panel 函式，並傳入 None（代表清空詳情面板）。
            self._update_detail_panel(None)
            # 用「return」結束這個函式。
            return

        # 從「專案籃子」（self.current_projects）中，根據行號（row）取出選取的專案（proj）。
        proj = self.current_projects[row]
        # 呼叫（call）_update_detail_panel 函式，顯示這個專案的詳細資訊。
        self._update_detail_panel(proj)

    # 這裡，我們用「def」來定義（define）當專案列表被雙擊時（double_clicked）執行的函式。
    def _on_project_double_clicked(self) -> None:
        """雙擊列 → 切換監控狀態（只改 stub 狀態，不呼叫真後端）。"""

        # 1. 先確認有選到有效列
        # 獲取（get）目前選取的行號（currentRow）。
        row = self.project_table.currentRow()
        # 用「if」來判斷：如果（if）行號無效，就直接用「return」結束。
        if row < 0 or row >= len(self.current_projects):
            return

        # 2. 取得 UUID 欄位（第 0 欄是隱藏 uuid）
        # 獲取（get）表格中指定行（row）、第 0 欄的項目（item）。
        uuid_item = self.project_table.item(row, 0)
        # 用「if」來判斷：如果（if）這個項目是空的（None），就直接結束。
        if uuid_item is None:
            # 理論上不該發生，代表列表初始化有問題
            return

        # 獲取（get）表格項目的文字（text），並去除空格（strip）。
        project_key = uuid_item.text().strip()
        # 用「if」來判斷：如果（if）UUID 是空的，就直接結束。
        if not project_key:
            return

        # 3. 呼叫 backend_adapter 切換狀態
        # 呼叫（call）後端（adapter）的 toggle_project_status 函式，嘗試切換專案狀態。
        updated = adapter.toggle_project_status(project_key)
        # 用「if」來判斷：如果（if）回傳的結果是 None（代表切換失敗，找不到專案）...
        if updated is None:
            # D-2：失敗 → 用底部訊息列顯示錯誤（紅字）
            # 呼叫（call）_set_status_message，顯示錯誤訊息，並設定 level 為 "error"。
            self._set_status_message("切換監控狀態失敗：找不到指定專案。", level="error")
            # 用「return」結束。
            return

        # 4. 更新本地快取
        # 用新的更新後的專案物件（updated）替換掉「專案籃子」（self.current_projects）中原本位置的舊物件。
        self.current_projects[row] = updated

        # 5. 更新表格顯示（狀態 & 模式）
        # 獲取（get）表格中指定行（row）的狀態（第 2 欄）和模式（第 3 欄）項目。
        status_item = self.project_table.item(row, 2)
        mode_item = self.project_table.item(row, 3)

        # 用「if」來判斷：如果（if）狀態項目不是空的...
        if status_item is not None:
            # 就設定（setText）新的狀態文字（這裡呼叫 _status_to_label 轉換中文）。
            status_item.setText(self._status_to_label(updated.status))
        # 用「if」來判斷：如果（if）模式項目不是空的...
        if mode_item is not None:
            # 就設定（setText）新的模式文字（這裡呼叫 _mode_to_label 轉換中文）。
            mode_item.setText(self._mode_to_label(updated.mode))

            # 呼叫（call）_update_detail_panel 函式，用更新後的專案物件（updated）刷新右側詳情面板。
            self._update_detail_panel(updated)

        # 6. D-2：成功 → 同樣用底部訊息列顯示成功（綠字）
        # 呼叫（call）_set_status_message，顯示成功的提示訊息，並設定 level 為 "success"。
        self._set_status_message(
            f"切換監控狀態成功：{updated.name} 現在為 {self._status_to_label(updated.status)}。",
            level="success",
        )


    def _on_select_new_path(self, button: QPushButton) -> None:
        """
        【一對多】統一的路徑選擇器：
        - 根據點擊的按鈕是哪個欄位（Project Folder 或 Output File），呼叫不同的 QFileDialog。
        - 並將結果填入對應的 QLineEdit 輸入框。
        """
        # HACK: QFileDialog 需要 QtWidgets 中的 QPushButton，我們需要確保其類型正確。
        from PySide6.QtWidgets import QPushButton, QFileDialog

        # 找到被點擊按鈕在 self.new_browse_buttons 籃子中的位置（索引 i）。
        try:
            # DEFENSE: 這裡用 DEFENSE 標籤標註，這是一個防呆檢查。
            index = self.new_browse_buttons.index(button)
        except ValueError:
            # 這是極度不可能發生的狀況（除非有程式碼被亂動），直接結束。
            return

        # 獲取（get）對應索引的輸入框。
        target_edit = self.new_input_fields[index]

        # 用「if...else」來判斷：如果（if）索引是 0（專案資料夾）...
        if index == 0:
            # 呼叫（call）QFileDialog.getExistingDirectory，讓使用者選擇現有的**資料夾**。
            path = QFileDialog.getExistingDirectory(self, "選擇專案資料夾")
            # 如果（if）使用者有選擇（path 不是空字串）...
            if path:
                # 就把路徑設定（setText）到輸入框。
                target_edit.setText(path)
        else:
            # 否則（else），呼叫（call）QFileDialog.getOpenFileName，讓使用者選擇**檔案**。
            # NOTE: 我們將允許使用者建立新檔案，所以這裡使用 OpenFileName 只是為了獲得路徑。
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                f"選擇寫入檔路徑 {index}",
                "",
                "Markdown 文件 (*.md);;所有檔案 (*.*)", # 新增 .md 篩選
            )
            # 如果（if）使用者有選擇（file_path 不是空字串）...
            if file_path:
                # 就把路徑設定（setText）到輸入框。
                target_edit.setText(file_path)

        # 呼叫（call）_update_new_project_submit_state 函式，重新檢查一次是否可以送出。
        # NOTE: 此時 _update_new_project_submit_state 函式中的舊邏輯會報錯，下一輪處理。
        self._update_new_project_submit_state()


    def _on_submit_new_project_stub(self) -> None:
        """
        按下「送出新增請求（Stub）」時呼叫：
        - 處理一對多輸出檔的邏輯（只送出主輸出檔給 adapter）。
        """
        # --- 1. 獲取所有路徑 ---
        # 獲取（get）專案資料夾路徑，並去除空格（strip）。
        # new_input_fields[0] = Project Folder
        folder = self.new_input_fields[0].text().strip()
        # 獲取（get）主要輸出檔路徑（索引 1），並去除空格（strip）。
        # new_input_fields[1] = Primary Output File
        primary_output_file = self.new_input_fields[1].text().strip()

        # # DEFENSE: 這裡用 DEFENSE 標籤標註，這是一個防呆檢查。
        # 用「if」來判斷：如果（if）資料夾或主輸出檔案是空的...
        if not folder or not primary_output_file:
            # 用「return」結束。
            return

        # 為了從路徑中取出專案名稱，我們需要 導入（import）Path 工具。
        from pathlib import Path
        # 建立一個 Path 物件，並取出路徑的最後一層名字（name）。
        # 如果最後一層名字是空的，就用整個路徑（folder）代替。
        name = Path(folder).name or folder

        # 獲取所有額外的輸出檔路徑（索引 2 和 3）。
        extra_targets = [
            self.new_input_fields[i].text().strip()
            for i in range(2, 4) if self.new_input_fields[i].text().strip()
        ]

        # 嘗試（try）執行可能出錯的程式碼。
        try:
            # 呼叫（call）後端（adapter）的 add_project 函式，傳入名稱、資料夾和**主要輸出檔**。
            # 目前 Stub 版本不傳遞額外的 extra_targets。
            adapter.add_project(name=name, path=folder, output_file=primary_output_file)

            # 由於新增成功，我們在這裡可以 print 出多個 targets 的訊息，模擬後端接收。
            targets_msg = f"（額外目標：{', '.join(extra_targets) or '無'}）"

        # 如果在 try 區塊發生了 adapter.BackendError 錯誤...
        except adapter.BackendError as e:
            # D-2：失敗 → 用底部訊息列顯示錯誤（紅色）
            # 呼叫（call）_set_status_message，顯示錯誤訊息（e），並設定 level 為 "error"。
            self._set_status_message(f"新增專案失敗：{e}", level="error")
            return # 用「return」結束。

        # 如果 try 區塊成功，就顯示一個資訊對話框（QMessageBox.information）。
        QMessageBox.information(
            self,
            "新增專案（Stub）",
            f"✓ 已送出新增請求（Stub）。\n"
            f"主目標：{primary_output_file}\n"
            f"額外目標：{', '.join(extra_targets) or '無'}\n"
            "目前僅記錄請求，不會寫入檔案或更新列表。",
        )
        # 呼叫（call）_set_status_message，顯示成功提示，並設定 level 為 "success"。
        self._set_status_message(
            f"✓ 已送出新增請求（Stub）。{targets_msg}",
            level="success",
        )

        # --- 成功後清空欄位 + 重繪列表 ---
        # 這裡我們使用 for 循環，清空所有 new_input_fields 列表中的輸入框。
        for edit in self.new_input_fields:
            edit.clear()

        # 呼叫（call）_update_new_project_submit_state 函式，讓按鈕回到 disabled 狀態。
        self._update_new_project_submit_state()
        # 呼叫（call）_reload_projects_from_backend 函式，重新載入列表。
        self._reload_projects_from_backend()
        # 呼叫（call）_update_detail_panel 函式，清空右側詳情面板。
        self._update_detail_panel(None)

    # 這裡，我們用「def」來定義（define）更新新增專案按鈕狀態的函式。
    def _update_new_project_submit_state(self) -> None:
        """依據輸入籃子中的第一個（Folder）和第二個（Primary Output）欄位是否有內容，決定送出按鈕是否啟用。"""
        # 預先告知：由於 UI 啟動時 _build_input_fields 尚未完全完成，這裡可能會在極短時間內因 self.new_input_fields 尚未定義而崩潰，這是正常的。

        # # DEFENSE: 這裡用 DEFENSE 標籤標註，這是一個防呆檢查，確保 self.new_input_fields 已經被建立。
        # 我們只在 self.new_input_fields 已經被建立（且包含至少 2 個輸入框）時才執行檢查。
        if not hasattr(self, 'new_input_fields') or len(self.new_input_fields) < 2:
            return

        # 獲取（get）專案資料夾輸入框的文字，去除空格，並用 bool() 判斷是否有內容（folder_ok）。
        # new_input_fields[0] = Project Folder
        folder_ok = bool(self.new_input_fields[0].text().strip())
        
        # 獲取（get）主要輸出檔輸入框的文字，去除空格，並用 bool() 判斷是否有內容（primary_output_ok）。
        # new_input_fields[1] = Primary Output File
        primary_output_ok = bool(self.new_input_fields[1].text().strip())
        
        # 設定（setEnabled）送出按鈕的啟用狀態：只有當兩個條件（folder_ok 和 primary_output_ok）都成立（and）時才啟用。
        self.new_project_submit_button.setEnabled(folder_ok and primary_output_ok)

        # 同步詳情區：當輸入框有變動時，清空詳情區，避免誤導。
        self._update_detail_panel(None)

    # ---------------------------
    # 詳情區更新
    # ---------------------------

    # 這裡，我們用「def」來定義（define）更新右側詳情面板的函式。
    # 參數 proj 接受一個專案物件（ProjectInfo）或是 None（空值）。
    def _update_detail_panel(
        self,
        proj: adapter.ProjectInfo | None,
    ) -> None:
        # 用「if」來判斷：如果（if）傳入的 proj 是 None（沒有選取專案）...
        if proj is None:
            # 就設定（setText）標籤顯示「尚未選取任何專案。」
            self.detail_label.setText("尚未選取任何專案。")
            # 用「return」結束函式。
            return

        # 呼叫（call）_status_to_label 函式，把狀態代碼（proj.status）轉成中文標籤。
        status_label = self._status_to_label(proj.status)
        # 呼叫（call）_mode_to_label 函式，把模式代碼（proj.mode）轉成中文標籤。
        mode_label = self._mode_to_label(proj.mode)

        # 建立（[]）一個叫 text_lines 的「文字籃子」，用於顯示專案詳情。
        text_lines = [
            f"專案名稱：{proj.name}",
            f"監控狀態：{status_label}",
            f"模式：{mode_label}",
            "",
            "（目前為假後端 stub：之後會改成顯示真實的寫入檔路徑、日誌入口等）",
            "雙擊左側列表可在【監控中／已停止】之間切換（僅影響 stub 狀態）。",
        ]
        # 用換行符號（\n）連接（join）文字籃子，並設定（setText）到詳情標籤上。
        self.detail_label.setText("\n".join(text_lines))

    # ---------------------------
    # 標籤轉換（之後可以抽成 i18n）
    # ---------------------------

    # 這裡，我們用「@staticmethod」來標記（mark）這是一個不需要物件（self）就可以呼叫的函式。
    # 它負責把狀態代碼轉成中文標籤。
    @staticmethod
    def _status_to_label(status: str) -> str:
        # 用「return ... if ... else ...」來判斷並回傳（return）中文標籤。
        return "監控中" if status == "monitoring" else "已停止"

    # 這裡，我們用「@staticmethod」來標記（mark）這是一個不需要物件（self）就可以呼叫的函式。
    # 它負責把模式代碼轉成中文標籤。
    @staticmethod
    def _mode_to_label(mode: str) -> str:
        # 用「return ... if ... else ...」來判斷並回傳（return）中文標籤。
        return "靜默" if mode == "silent" else "互動"


class SentryTrayApp:
    # 這個註釋（"""..."""）是說明文件，解釋這個類別的作用。
    """系統托盤應用程式：負責托盤圖示與主控台視窗。"""

    # 這裡，我們用「def」來定義（define）物件被建立時會自動執行的函式（__init__）。
    def __init__(self, app: QApplication) -> None:
        # 將傳入的應用程式物件（app）儲存起來。
        self.app = app
        # 建立（instantiate）主控制台視窗（SentryConsoleWindow）物件。
        self.console = SentryConsoleWindow()

        # 載入托盤圖示
        # 呼叫（call）_load_icon 函式，獲取要顯示的圖標（icon）。
        icon = self._load_icon()

        # 建立系統托盤圖標（QSystemTrayIcon），並傳入圖標和應用程式物件。
        self.tray_icon = QSystemTrayIcon(icon, self.app)
        # 設定滑鼠懸停在圖標上時會顯示的提示文字（setToolTip）。
        self.tray_icon.setToolTip("Laplace Sentry 控制台")

        # 建立右鍵選單
        # 建立一個選單（QMenu）物件。
        menu = QMenu()
        # 呼叫（call）_build_menu 函式來填充選單內容（這個函式我們之後會寫）。
        self._build_menu(menu)
        # 把這個選單設定（setContextMenu）為托盤圖標的右鍵選單。
        self.tray_icon.setContextMenu(menu)

        # 左鍵點擊托盤 → 打開控制台
        # 綁定（connect）托盤圖標被激活（activated）的事件，到處理函式 _on_activated。
        self.tray_icon.activated.connect(self._on_activated)

        # 顯示托盤
        # 讓系統托盤圖標顯示出來（show()）。
        self.tray_icon.show()

    # 這裡，我們用「def」來定義（define）載入托盤圖標的函式。
    def _load_icon(self) -> QIcon:
        """從 assets/icons/tray_icon.png 載入圖示；若失敗則使用系統預設圖示。"""
        # 獲取（get）當前檔案的根路徑（Path(__file__).resolve().parents[2]）。
        root = Path(__file__).resolve().parents[2]
        # 拼接出（/）目標圖標檔案的完整路徑。
        icon_path = root / "assets" / "icons" / "tray_icon.png"

        # 用「if」來判斷：如果（if）圖標路徑是一個檔案（is_file）...
        if icon_path.is_file():
            # 就嘗試用這個路徑建立一個圖標（QIcon）。
            icon = QIcon(str(icon_path))
            # 再用「if」來判斷：如果（if）圖標不是空的（isNull）...
            if not icon.isNull():
                # 就回傳（return）這個圖標。
                return icon

        # 後備方案：使用系統內建圖示，避免 QSystemTrayIcon::setVisible: No Icon set
        # 獲取（get）當前應用程式的實例（instance）。
        app = QApplication.instance()
        # 用「if」來判斷：如果（if）應用程式實例不是空的...
        if app is not None:
            # 這是為了 Pylance 類型提示，強制轉換（cast）應用程式實例為 QApplication。
            app_qt = cast(QApplication, app)
            # 獲取（get）應用程式的樣式（style）物件。
            style = app_qt.style()
            # 回傳（return）系統標準圖標（StandardPixmap.SP_ComputerIcon）作為後備。
            return style.standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)

        # 理論上不會跑到這裡；保底回傳一個空 icon
        # 最後的防呆機制，回傳（return）一個空的圖標。
        return QIcon()



# 這裡，我們用「def」來定義（define）建立右鍵選單的函式。
    def _build_menu(self, menu: QMenu) -> None:
        """建立托盤右鍵選單。"""

        # 建立一個「動作」（QAction），它是選單中的一個選項。
        open_console_action = QAction("開啟控制台", menu)
        # 把這個動作的觸發事件（triggered）綁定（connect）到 show_console 函式。
        open_console_action.triggered.connect(self.show_console)

        # 建立另一個「動作」：退出應用程式。
        quit_action = QAction("退出", menu)
        # 把退出動作綁定（connect）到應用程式的退出函式（self.app.quit）。
        quit_action.triggered.connect(self.app.quit)

        # 把「開啟控制台」這個動作加入（addAction）到選單中。
        menu.addAction(open_console_action)
        # 加入一條分隔線（addSeparator），把控制台和退出選項分開。
        menu.addSeparator()
        # 把「退出」動作加入（addAction）到選單中。
        menu.addAction(quit_action)

    # 這裡，我們用「def」來定義（define）顯示主控制台視窗的函式。
    def show_console(self) -> None:
        """顯示控制台視窗並把它拉到前景。"""
        # 顯示（show）控制台視窗。
        self.console.show()
        # 將視窗拉到前景，以便使用者看到它。
        self.console.activateWindow()
        # 確保視窗堆疊順序正確（raise_()）。
        self.console.raise_()

    # 這裡，我們用「def」來定義（define）托盤圖示被激活時（activated）的處理函式。
    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """托盤圖示被點擊時的行為：左鍵 → 打開控制台。"""
        # 用「if」來判斷：如果（if）被激活的原因是滑鼠左鍵點擊（Trigger）...
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            # 就呼叫（call）show_console 函式來顯示控制台。
            self.show_console()


# 這裡，我們用「def」來定義（define）應用程式的主入口點（main）。
def main() -> None:
    """應用程式進入點。"""
    # 建立一個 QApplication 物件，這是所有 Qt 應用程式的核心。
    app = QApplication(sys.argv)

    # 關閉最後一個視窗時不要自動退出，交給「退出」選單控制
    # 設定（setQuitOnLastWindowClosed）為 False，這樣關閉主視窗時應用程式才不會結束。
    app.setQuitOnLastWindowClosed(False)

    # 建立（instantiate）我們剛剛寫好的 SentryTrayApp 物件。
    tray_app = SentryTrayApp(app)
    # 啟動（exec）應用程式的主事件迴圈，並把回傳的退出碼傳給系統（sys.exit）。
    sys.exit(app.exec())


# 這是 Python 標準的寫法：如果（if）這個檔案是直接執行的主程式...
if __name__ == "__main__":
    # 就呼叫（call）main 函式來啟動應用程式。
    main()

    # -----------執行指令----------------  
    # python -m src.tray.tray_app
    #  ----------------------------------

    # ============虛擬環境================
    # .\.venv\Scripts\Activate
    # ----------------------------------