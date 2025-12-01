# --- 1. 導入系統與路徑管理工具 ---

# 導入（import）Python 系統（sys）工具，用於跟作業系統互動。
import sys
# 導入（import）路徑處理（pathlib）中的 Path 工具，方便處理檔案路徑。
from pathlib import Path
# 導入（import）類型提示（typing）中的 cast, List, Dict, Any。
from typing import cast, List, Dict, Any 

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
    QInputDialog,  # (用來跳出輸入框)
    QListWidgetItem,  # (用來在列表中顯示單一項目)
    QListWidget,  # (用來顯示列表的元件)
    QDialogButtonBox,  # (用來顯示對話框按鈕列)
    QDialog,  # (用來顯示對話框)
    QCheckBox,
)

# 導入 PySide6 的圖形介面（QtGui）中的 QIcon（圖標）、QAction（動作）和 QColor（顏色）等。
from PySide6.QtGui import QIcon, QAction, QColor, QPalette

# --- 3. 導入自定義模組 ---

# 再次導入（import）路徑處理（pathlib）中的 Path 工具。（雖然上面有，但這裡保留）
from pathlib import Path

# 從「src/backend」這個資料夾中，導入（import）我們的資料庫處理工具（adapter）。
from src.backend import adapter 

class IgnoreSettingsDialog(QDialog):
    """
    忽略清單設定視窗：
    - 顯示候選名單 (Adapter 提供)
    - 允許勾選/取消
    - 允許手動新增
    """
    def __init__(self, parent=None, project_name=""):
        super().__init__(parent)
        self.setWindowTitle(f"編輯忽略規則 - {project_name}")
        self.resize(500, 600)
        
        layout = QVBoxLayout(self)

        # 1. 說明文字
        layout.addWidget(QLabel("勾選要忽略的檔案或資料夾（變更將觸發哨兵重啟）："))

        # 2. 列表區 (含複選框)
        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)

        # 3. 手動新增區
        input_layout = QHBoxLayout()
        self.new_pattern_edit = QLineEdit()
        self.new_pattern_edit.setPlaceholderText("手動輸入規則 (例: *.tmp)")
        btn_add = QPushButton("新增")
        btn_add.clicked.connect(self._on_add_pattern)
        
        input_layout.addWidget(self.new_pattern_edit)
        input_layout.addWidget(btn_add)
        layout.addLayout(input_layout)

        # 4. 底部按鈕 (確定/取消)
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

    def load_patterns(self, candidates: list[str], current: set[str]):
        """載入資料並設定勾選狀態"""
        self.list_widget.clear()
        
        # 先把 current 裡有的，但不在 candidates 裡的 (手動加的) 也補進去顯示
        all_items = sorted(set(candidates) | current)
        
        for name in all_items:
            item = QListWidgetItem(name)
            # 設定為可複選
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            
            # 設定勾選狀態
            if name in current:
                item.setCheckState(Qt.CheckState.Checked)
            else:
                item.setCheckState(Qt.CheckState.Unchecked)
            
            self.list_widget.addItem(item)

    def get_result(self) -> list[str]:
        """收集所有被勾選的項目"""
        results = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                results.append(item.text())
        return results

    def _on_add_pattern(self):
        """手動新增規則"""
        text = self.new_pattern_edit.text().strip()
        if not text:
            return
            
        # 檢查是否重複
        existing = [self.list_widget.item(i).text() for i in range(self.list_widget.count())]
        if text in existing:
            QMessageBox.warning(self, "重複", f"規則 '{text}' 已存在。")
            return

        # 加入列表並預設勾選
        item = QListWidgetItem(text)
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        item.setCheckState(Qt.CheckState.Checked)
        self.list_widget.addItem(item)
        self.list_widget.scrollToBottom()
        self.new_pattern_edit.clear()

# tray_app.py (在 IgnoreSettingsDialog 類別下方)

# 我們用「class」來定義（define）編輯專案設定視窗類別。
class EditProjectDialog(QDialog):
    """
    修改專案設定視窗：
    - 顯示專案名稱、路徑、目標檔等現有資訊。
    - 允許編輯名稱、專案路徑、主寫入檔。
    """
    # 我們用「def」來定義（define）初始化函式。
    def __init__(self, parent=None, project_data: adapter.ProjectInfo | None = None):
        # 我們用「super().__init__(parent)」來呼叫（call）父類別初始化函式。
        super().__init__(parent)
        # 我們用「self.setWindowTitle("修改專案設定 - {project_data.name}")」來設定（set）視窗標題。
        self.setWindowTitle(f"修改專案設定 - {project_data.name}" if project_data else "修改專案設定")
        # 我們用「self.resize(600, 300)」來設定（set）視窗大小。
        self.resize(600, 300)
        # 我們用「self.uuid = project_data.uuid」來儲存（store）UUID。
        self.uuid = project_data.uuid if project_data else ""
        # 我們用「self._build_ui(project_data)」來建立（build）介面。
        self._build_ui(project_data)

    # 我們用「def」來定義（define）建立介面函式。
    def _build_ui(self, data: adapter.ProjectInfo | None):
        # 我們用「main_layout = QVBoxLayout(self)」來建立（create）主垂直佈局。
        main_layout = QVBoxLayout(self)

        # 1. 專案名稱
        # 我們用「self.name_edit = QLineEdit(data.name)」來建立（create）名稱輸入框。
        self.name_edit = QLineEdit(data.name if data else "")
        # 我們用「main_layout.addWidget(QLabel("專案名稱 (Alias)："))」來新增（add）標籤。
        main_layout.addWidget(QLabel("專案名稱 (Alias)："))
        # 我們用「main_layout.addWidget(self.name_edit)」來新增（add）輸入框。
        main_layout.addWidget(self.name_edit)

        # 2. 專案路徑
        # 我們用「path_layout = QHBoxLayout()」來建立（create）水平佈局。
        path_layout = QHBoxLayout()
        # 我們用「self.path_edit = QLineEdit(data.path)」來建立（create）路徑輸入框。
        self.path_edit = QLineEdit(data.path if data else "")
        # 我們用「path_layout.addWidget(QLabel("專案資料夾路徑 (Path)："))」來新增（add）標籤。
        path_layout.addWidget(QLabel("專案資料夾路徑 (Path)："))
        # 我們用「path_layout.addWidget(self.path_edit)」來新增（add）輸入框。
        path_layout.addWidget(self.path_edit)
        # 我們用「main_layout.addLayout(path_layout)」來新增（add）水平佈局。
        main_layout.addLayout(path_layout)
        # 我們用「main_layout.addWidget(QLabel("提示：修改路徑可能導致哨兵重啟！"))」來新增（add）提示。
        main_layout.addWidget(QLabel("提示：修改路徑可能導致哨兵重啟！"))

        # 我們用「main_layout.addSpacing(10)」來新增（add）間距。
        main_layout.addSpacing(10)

        # 3. 主寫入檔
        # 我們用「output_path = data.output_file[0] if data and data.output_file else ""」來獲取（get）輸出路徑。
        output_path = data.output_file[0] if data and data.output_file else ""
        # 我們用「output_layout = QHBoxLayout()」來建立（create）水平佈局。
        output_layout = QHBoxLayout()
        # 我們用「self.output_edit = QLineEdit(output_path)」來建立（create）輸出輸入框。
        self.output_edit = QLineEdit(output_path)
        # 我們用「output_layout.addWidget(QLabel("主寫入檔路徑 (Output File)："))」來新增（add）標籤。
        output_layout.addWidget(QLabel("主寫入檔路徑 (Output File)："))
        # 我們用「output_layout.addWidget(self.output_edit)」來新增（add）輸入框。
        output_layout.addWidget(self.output_edit)
        # 我們用「main_layout.addLayout(output_layout)」來新增（add）水平佈局。
        main_layout.addLayout(output_layout)

        # 4. 按鈕區
        # 我們用「self.button_box = QDialogButtonBox(...)」來建立（create）按鈕盒。
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        # 我們用「self.button_box.accepted.connect(self.accept)」來連線（connect）接受訊號。
        self.button_box.accepted.connect(self.accept)
        # 我們用「self.button_box.rejected.connect(self.reject)」來連線（connect）拒絕訊號。
        self.button_box.rejected.connect(self.reject)
        # 我們用「main_layout.addWidget(self.button_box)」來新增（add）按鈕盒。
        main_layout.addWidget(self.button_box)
    
    # 我們用「def」來定義（define）獲取變更函式。
    def get_changes(self) -> Dict[str, str]:
        """回傳所有被修改的欄位及其新值"""
        # 我們用「changes = {}」來初始化（init）變更字典。
        changes = {}
        # 這裡需要對所有欄位進行 trim() 處理
        # 我們用「if self.name_edit.text().strip():」來檢查（check）名稱是否有值。
        if self.name_edit.text().strip():
            # 我們用「changes['name'] = self.name_edit.text().strip()」來儲存（store）名稱。
            changes['name'] = self.name_edit.text().strip()
        # 我們用「if self.path_edit.text().strip():」來檢查（check）路徑是否有值。
        if self.path_edit.text().strip():
            # 我們用「changes['path'] = self.path_edit.text().strip()」來儲存（store）路徑。
            changes['path'] = self.path_edit.text().strip()
        # 我們用「if self.output_edit.text().strip():」來檢查（check）輸出是否有值。
        if self.output_edit.text().strip():
            # 我們用「changes['output_file'] = self.output_edit.text().strip()」來儲存（store）輸出。
            changes['output_file'] = self.output_edit.text().strip()
            
        # 我們用「return changes」來回傳（return）變更。
        return changes
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
        # 啟用（setAcceptDrops）主視窗的拖曳接收功能（True），這是 PySide6 處理拖曳事件的第一步。
        self.setAcceptDrops(True)

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

        # 設定（set）選單策略為 CustomContextMenu，這樣才能自訂選單。
        table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        # 綁定（connect）請求選單訊號到我們的處理函式。
        table.customContextMenuRequested.connect(self._on_table_context_menu)
                
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

# --- 下半部：新增專案區 ---
        # 建立一個水平佈局，用來放標題和模式開關
        title_layout = QHBoxLayout()
        
        # 標題
        title_label = QLabel("新增專案")
        # 設定標題字體加粗，讓它明顯一點
        font = title_label.font()
        font.setBold(True)
        title_label.setFont(font)
        
        # 模式開關 (預設不勾選)
        self.mode_checkbox = QCheckBox("自訂別名 (自由模式)")
        # 綁定事件：當勾選狀態改變時，呼叫切換函式 (稍後實作)
        self.mode_checkbox.toggled.connect(self._toggle_input_mode)

        # 組合
        title_layout.addWidget(title_label)
        title_layout.addStretch(1) # 中間塞彈簧，把開關推到右邊
        title_layout.addWidget(self.mode_checkbox)

        # 把這個水平佈局加入主垂直佈局
        layout.addLayout(title_layout)

        # 這是專門用來放「專案資料夾」和「寫入檔路徑」輸入框的垂直佈局
        self.new_project_input_layout = QVBoxLayout()
        # 把這個垂直佈局（new_project_input_layout）加入到主垂直佈局中。
        layout.addLayout(self.new_project_input_layout)

        # 呼叫（call）專門負責建立這些輸入框的函式
        self._build_input_fields()


        # 送出按鈕（目前 stub）
        self.new_project_submit_button = QPushButton("確認新增")
        # 預設禁用（setEnabled(False)）送出按鈕。
        self.new_project_submit_button.setEnabled(False)
        # 把按鈕加入（addWidget）到垂直佈局中。
        layout.addWidget(self.new_project_submit_button)
        # 綁定送出按鈕的點擊事件（clicked）到處理函式（Stub）。
        self.new_project_submit_button.clicked.connect(self._on_submit_new_project)
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

        # --- [Task I] 1. 建立別名輸入列 (預設隱藏) ---
        # 我們用一個 Widget 把整列包起來，方便之後直接控制整列的顯示/隱藏
        self.alias_container = QWidget()
        alias_layout = QHBoxLayout(self.alias_container)
        # 設定邊距為 0，讓它看起來像原生佈局的一部分
        alias_layout.setContentsMargins(0, 0, 0, 0)
        
        alias_label = QLabel("專案別名：")
        self.alias_edit = QLineEdit()
        self.alias_edit.setPlaceholderText("可選：自訂顯示名稱 (若留空則使用資料夾名)")
        
        alias_layout.addWidget(alias_label)
        alias_layout.addWidget(self.alias_edit)
        
        # 加入到主垂直佈局的最上方
        self.new_project_input_layout.addWidget(self.alias_container)
        
        # 預設隱藏
        self.alias_container.setVisible(False)
        
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

    def _toggle_input_mode(self, checked: bool) -> None:
        """切換輸入模式：控制別名欄位的顯隱"""
        # 控制容器的顯示/隱藏
        self.alias_container.setVisible(checked)
        
        # 如果切換回一般模式 (unchecked)，我們主動清空別名欄位，避免殘留舊資料
        if not checked:
            self.alias_edit.clear()

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

        # 建立第二個按鈕：編輯目錄樹忽略規則 ---
        # 改成 self.btn_tree_ignore，讓它變成全域可存取的物件
        self.btn_tree_ignore = QPushButton("編輯目錄樹忽略規則…")
        # 綁定點擊事件到我們即將實作的 _open_ignore_settings_dialog 函式
        self.btn_tree_ignore.clicked.connect(self._open_ignore_settings_dialog)

        # 預設禁用這兩個按鈕（setEnabled(False)）。
        btn_sentry_ignore.setEnabled(False)
        self.btn_tree_ignore.setEnabled(False) 

        # 把按鈕依序加入（addWidget）到右側垂直佈局。
        button_panel.addWidget(btn_sentry_ignore)
        button_panel.addWidget(self.btn_tree_ignore)       
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

    def _open_ignore_settings_dialog(self) -> None:
        """打開忽略規則設定視窗"""
        # 1. 獲取當前選中的專案
        row = self.project_table.currentRow()
        if row < 0 or row >= len(self.current_projects):
            return
        
        proj = self.current_projects[row]
        
        self._set_status_message(f"正在讀取專案 '{proj.name}' 的忽略設定...", level="info")
        # 強制刷新 UI，避免卡頓感
        QApplication.processEvents()

        try:
            # 2. 從後端讀取兩份資料：候選名單 & 當前設定
            candidates = adapter.get_ignore_candidates(proj.uuid)
            current_patterns = set(adapter.get_current_ignore_patterns(proj.uuid))
            
            # 3. 建立並顯示對話框
            dialog = IgnoreSettingsDialog(self, proj.name)
            
            # 將資料載入對話框，讓它正確顯示勾選狀態
            dialog.load_patterns(candidates, current=current_patterns)
            
            # 4. 等待使用者操作
            if dialog.exec() == QDialog.DialogCode.Accepted:
                # 使用者按了儲存，獲取最新的勾選結果
                new_patterns = dialog.get_result()
                
                self._set_status_message(f"正在儲存設定並重啟哨兵...", level="info")
                QApplication.processEvents()
                
                # 5. 呼叫後端寫入
                adapter.update_ignore_patterns(proj.uuid, new_patterns)
                
                self._set_status_message(f"✓ 專案 '{proj.name}' 忽略規則已更新。", level="success")
                QMessageBox.information(self, "更新成功", "忽略規則已更新，哨兵已自動重啟以套用新設定。")
            else:
                # 使用者按取消
                self._set_status_message("已取消編輯忽略規則。", level="info")

        except Exception as e:
            self._set_status_message(f"讀取/儲存設定失敗：{e}", level="error")
            QMessageBox.critical(self, "錯誤", str(e))

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
            self.btn_tree_ignore.setEnabled(False)
            # 用「return」結束這個函式。
            return

        # 從「專案籃子」（self.current_projects）中，根據行號（row）取出選取的專案（proj）。
        proj = self.current_projects[row]
        # 呼叫（call）_update_detail_panel 函式，顯示這個專案的詳細資訊。
        self._update_detail_panel(proj)

        # 有選到專案，啟用按鈕
        self.btn_tree_ignore.setEnabled(True) 

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

    # 這裡，我們用「def」來定義（define）處理表格右鍵選單的函式。
    def _on_table_context_menu(self, position) -> None:
        """顯示右鍵選單：手動更新 / 刪除專案。"""
        # 獲取（get）滑鼠點擊位置對應的索引（index）。
        index = self.project_table.indexAt(position)
        # 如果（if）點擊位置無效（沒點到行），就直接結束。
        if not index.isValid():
            return

        # 獲取行號。
        row = index.row()
        
        # 獲取該列的 UUID（第 0 欄）和名稱（第 1 欄）。
        uuid_item = self.project_table.item(row, 0)
        name_item = self.project_table.item(row, 1)
        
        # 防呆：如果拿不到資料，就結束。
        if not uuid_item or not name_item:
            return
            
        project_uuid = uuid_item.text()
        project_name = name_item.text()

        # 建立（create）一個選單物件。
        menu = QMenu(self.project_table)

        # [選項 A] 手動觸發更新
        action_update = QAction("🔄 立即手動更新 (Manual Update)", menu)
        # 綁定事件：使用 lambda 傳遞參數給處理函式。
        action_update.triggered.connect(
            lambda checked: self._perform_manual_update(project_uuid, project_name)
        )
        menu.addAction(action_update)

        menu.addAction(action_update)

        # 加入分隔線。
        # 我們用「menu.addSeparator()」來新增（add）分隔線。
        menu.addSeparator() 

        # [選項 C] 修改專案
        # 我們用「action_edit = QAction("📝 修改專案...", menu)」來建立（create）動作。
        action_edit = QAction("📝 修改專案...", menu)
        # 我們用「action_edit.triggered.connect(...)」來連線（connect）觸發訊號。
        action_edit.triggered.connect(
            lambda checked: self._perform_edit_project(project_uuid, project_name)
        )
        # 我們用「menu.addAction(action_edit)」來新增（add）動作。
        menu.addAction(action_edit)
        
        # 加入分隔線。
        # 我們用「menu.addSeparator()」來新增（add）分隔線。
        menu.addSeparator()

        # [選項 B] 刪除專案 (紅字警告風格)
        action_delete = QAction("🗑️ 刪除此專案...", menu)
        # 綁定事件。
        action_delete.triggered.connect(
            lambda checked: self._perform_delete_project(project_uuid, project_name)
        )
        menu.addAction(action_delete)

        # 在滑鼠位置顯示（exec）選單。
        menu.exec(self.project_table.viewport().mapToGlobal(position))

    # 這裡，我們用「def」來定義（define）執行手動更新的動作函式。
    def _perform_manual_update(self, uuid: str, name: str) -> None:
        # 先顯示一個「請稍候」的狀態訊息。
        self._set_status_message(f"正在更新專案 '{name}'，請稍候...", level="info")
        
        # 強制刷新（processEvents）UI，避免看起來卡死。
        QApplication.processEvents()

        try:
            # 呼叫（call）後端執行更新。
            adapter.trigger_manual_update(uuid)
            # 成功後顯示綠字訊息。
            self._set_status_message(f"✓ 專案 '{name}' 手動更新成功！", level="success")
            # 彈出成功對話框。
            QMessageBox.information(self, "更新成功", f"專案 '{name}' 的目錄結構已更新至 Markdown。")
        except Exception as e:
            # 失敗顯示紅字訊息。
            self._set_status_message(f"更新失敗：{e}", level="error")
            # 彈出錯誤警告框。
            QMessageBox.critical(self, "更新失敗", str(e))

    # 這裡，我們用「def」來定義（define）執行刪除專案的動作函式。
    def _perform_delete_project(self, uuid: str, name: str) -> None:
        # 1. 彈出確認視窗 (防呆)
        reply = QMessageBox.question(
            self,
            "確認刪除",
            f"您確定要刪除專案「{name}」嗎？\n\n"
            "這將會：\n"
            "1. 停止該專案的哨兵 (若在運行)\n"
            "2. 從設定檔移除專案\n"
            "3. 清除相關日誌與暫存檔\n\n"
            "(不會刪除您的原始檔案)",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        # 如果使用者沒有按 Yes，就結束。
        if reply != QMessageBox.StandardButton.Yes:
            return

        # 2. 執行刪除
        try:
            # 呼叫後端刪除。
            adapter.delete_project(uuid)
            self._set_status_message(f"✓ 專案 '{name}' 已刪除。", level="success")
            
            # 3. 刪除後重整列表（重要！這樣 UI 才會消失）。
            self._reload_projects_from_backend()
            # 清空右側詳情區。
            self._update_detail_panel(None)
            
        except Exception as e:
            self._set_status_message(f"刪除失敗：{e}", level="error")
            QMessageBox.critical(self, "刪除失敗", str(e))

            # tray_app.py (在 _perform_delete_project 函式下方)

# 我們用「def」來定義（define）執行編輯專案函式。
    def _perform_edit_project(self, uuid: str, name: str) -> None:
        """打開編輯視窗，並呼叫後端修改專案。"""
        # 1. 找到專案的完整資料
        target_proj = next((p for p in self.current_projects if p.uuid == uuid), None)
        if not target_proj:
            QMessageBox.critical(self, "錯誤", f"找不到 UUID 為 {uuid} 的專案資料。")
            return

        # 2. 建立並開啟編輯對話框
        dialog = EditProjectDialog(self, target_proj)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            # 3. 獲取所有變動
            changes = dialog.get_changes()
            
            if not changes:
                self._set_status_message("沒有任何變更，已取消操作。", level="info")
                return
            
            # 4. 逐一呼叫後端 API 進行修改
            all_success = True
            error_details = []
            
            for field, new_value in changes.items():
                try:
                    if field in ['name', 'path', 'output_file']:
                        self._set_status_message(f"正在修改 '{name}' 的 {field}...", level="info")
                        QApplication.processEvents()
                        
                        # 【修正】這裡改為呼叫 adapter.edit_project(uuid, field, new_value)
                        # 這符合我們剛剛在 adapter.py 定義的接口 (3 個參數)
                        adapter.edit_project(uuid, field, new_value) 
                        
                except Exception as e:
                    all_success = False
                    error_details.append(f"欄位 {field} 失敗：{e}")
                    
            # 5. 根據結果更新 UI
            if all_success:
                self._set_status_message(f"✓ 專案 '{name}' 已成功更新！", level="success")
                self._reload_projects_from_backend() # 重繪列表
            else:
                final_error = "\n".join(error_details)
                self._set_status_message(f"更新失敗！詳情請見彈出視窗。", level="error")
                QMessageBox.critical(self, "部分更新失敗", f"專案 '{name}' 的部分欄位未能更新。\n\n錯誤詳情:\n{final_error}")

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


    def _on_submit_new_project(self) -> None:
        """
        按下「確認新增」時呼叫：
        - 處理輸入資料 (支援自訂別名)
        - 呼叫後端 (含重名自動重試邏輯)
        - 更新 UI
        """
        # --- 1. 獲取所有路徑 ---
        folder = self.new_input_fields[0].text().strip()
        primary_output_file = self.new_input_fields[1].text().strip()

        # # DEFENSE: 防呆檢查
        if not folder or not primary_output_file:
            return

        from pathlib import Path
        
        # --- 決定專案名稱 (Task I 核心邏輯) ---
        # 1. 先計算預設名稱 (資料夾名)
        default_name = Path(folder).name or folder
        
        # 2. 檢查是否啟用自由模式且有輸入別名
        alias_input = self.alias_edit.text().strip()
        use_alias = self.mode_checkbox.isChecked() and bool(alias_input)
        
        # 3. 設定初始嘗試的名字
        if use_alias:
            current_name = alias_input
        else:
            current_name = default_name

        # 獲取額外目標 (目前僅用於顯示資訊，尚未寫入)
        extra_targets = [
            self.new_input_fields[i].text().strip()
            for i in range(2, 4) if self.new_input_fields[i].text().strip()
        ]
        
        # 準備顯示用的資訊
        primary_output_filename = Path(primary_output_file).name
        extra_count = len(extra_targets)
        targets_msg = f"（額外目標：{extra_count} 個）"

        # --- 核心 UX 優化：重名自動重試迴圈 ---
        while True:            
            try:
                # 嘗試呼叫後端新增
                adapter.add_project(name=current_name, path=folder, output_file=primary_output_file)
                
                # --- 如果程式跑到這裡，代表成功了！ ---
                
                # 1. 準備成功訊息
                ux_message = (
                    f"✓ 專案新增成功！\n\n"
                    f"專案名稱: {current_name}\n"
                    f"主目標檔: {primary_output_filename}\n"
                    f"額外目標: {extra_count} 個\n\n"
                    "後端已更新設定，您可以立即啟動監控。"
                )

                # 2. 彈出成功視窗
                QMessageBox.information(self, "新增成功", ux_message)
                
                # 3. 更新底部狀態列
                self._set_status_message(
                    f"✓ 專案 '{current_name}' 新增成功。{targets_msg}",
                    level="success",
                )

                # 4. 清空欄位 + 重繪列表
                for edit in self.new_input_fields:
                    edit.clear()

                self._update_new_project_submit_state()
                self._reload_projects_from_backend()
                self._update_detail_panel(None)
                
                # 成功，跳出迴圈
                break 

            except adapter.BackendError as e:
                error_msg = str(e)
                # 【關鍵判定】檢查是否為重名錯誤
                # (對應 daemon 拋出的: "專案別名 'xxx' 已被佔用")
                if "已被佔用" in error_msg:
                    # 彈出輸入框讓使用者改名
                    new_name, ok = QInputDialog.getText(
                        self, 
                        "專案名稱衝突", 
                        f"名稱 '{current_name}' 已存在。\n請輸入新的專案別名：",
                        text=current_name + "_new"
                    )
                    
                    if ok and new_name:
                        # 如果使用者輸入新名字並按 OK，更新名字，重跑迴圈 (continue)
                        current_name = new_name.strip()
                        continue
                    else:
                        # 如果使用者按取消，視為放棄操作
                        self._set_status_message(f"新增取消：名稱衝突", level="error")
                        return
                
                # 如果是其他錯誤 (如路徑不存在)，直接報錯並結束
                self._set_status_message(f"新增專案失敗：{error_msg}", level="error")
                return

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
            f"專案路徑：{proj.path}",
            f"主寫入檔：{proj.output_file[0] if proj.output_file else '(未設定)'}",
            "",
            "提示：雙擊左側列表可【啟動／停止】監控。",
        ]
        # 用換行符號（\n）連接（join）文字籃子，並設定（setText）到詳情標籤上。
        self.detail_label.setText("\n".join(text_lines))

    def dragEnterEvent(self, event) -> None:
        """
        處理拖曳進入事件：設定視窗為可接受拖曳。
        """
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event) -> None:
        """
        處理放下事件 (最終版)：
        1. 多檔智能路由。
        2. 類型白名單過濾。
        3. [新增] 防止重複路徑填入。
        """
        from pathlib import Path
        from PySide6.QtWidgets import QLineEdit
        
        # DEFENSE: 檢查事件中是否有路徑（URL）資訊。
        if not event.mimeData().hasUrls():
            event.ignore()
            return
            
        # 獲取所有拖曳的路徑列表。
        urls = event.mimeData().urls()
        
        # 定義允許的寫入檔副檔名（白名單）。
        VALID_EXTENSIONS = {'.md', '.markdown', '.txt', '.log'}
        
        filled_count = 0
        
        # 迴圈處理每一個拖曳進來的路徑。
        for url in urls:
            path_str = url.toLocalFile()
            path_obj = Path(path_str)
            
            # [新增] 防呆檢查：檢查路徑是否已經存在於任何一個輸入框中
            # 我們建立一個集合，包含所有目前輸入框內的文字（去除空格）
            current_values = {f.text().strip() for f in self.new_input_fields}
            
            if path_str in current_values:
                # 如果已經存在，就直接跳過，不處理這個檔案
                continue

            # 1. 處理資料夾 -> 嘗試填入專案資料夾 (索引 0)
            if path_obj.is_dir():
                folder_input = self.new_input_fields[0]
                if not folder_input.text().strip():
                    folder_input.setText(path_str)
                    filled_count += 1
            
            # 2. 處理檔案 -> 先檢查副檔名，再嘗試填入寫入檔
            elif path_obj.is_file():
                if path_obj.suffix.lower() in VALID_EXTENSIONS:
                    for i in range(1, 4):
                        file_input = self.new_input_fields[i]
                        if not file_input.text().strip():
                            file_input.setText(path_str)
                            filled_count += 1
                            break 

        # --- 總結處理結果 ---
        if filled_count > 0:
            event.acceptProposedAction()
            self._update_new_project_submit_state()
            msg = f"批量拖曳成功：已填入 {filled_count} 個欄位。"
            self._set_status_message(msg, level="success")
        else:
            # 可能是欄位滿了、類型不對、或者是重複的路徑
            self._set_status_message("拖曳無效：沒有填入任何欄位 (重複、格式不符或欄位已滿)。", level="error")
            event.ignore()

        # --- 總結處理結果 ---
        if filled_count > 0:
            event.acceptProposedAction()
            self._update_new_project_submit_state()
            
            # 簡化後的成功訊息。
            msg = f"批量拖曳成功：已填入 {filled_count} 個欄位。"
            self._set_status_message(msg, level="success")
        else:
            # 如果一個都沒填進去（可能是欄位滿了，或是所有檔案都被過濾了）。
            self._set_status_message("拖曳無效：沒有可填入的欄位，或檔案格式不支援。", level="error")
            event.ignore()

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