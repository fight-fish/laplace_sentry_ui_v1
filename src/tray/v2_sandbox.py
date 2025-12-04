# ==========================================
#   Sentry v2.0 Sandbox - Import Section
# ==========================================

# --- 1. 系統與基礎工具 ---
import sys
from typing import List, Dict, Any
import math
from pathlib import Path

# --- 2. PySide6 核心與介面元件 ---
from PySide6.QtCore import (
    Qt, 
    QPoint, 
    QSize, 
    QTimer,            # (心跳計時器)
    QPropertyAnimation,# (動畫工具，預留給之後用)
    QEasingCurve
)

from PySide6.QtGui import (
    QIcon, 
    QAction, 
    QPainter,          # (畫筆)
    QPen, 
    QColor, 
    QBrush, 
    QRadialGradient,   # (漸層)
    QCursor,
    QPalette,
    QPainterPath        # (貝茲曲線工具
)

from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSystemTrayIcon,
    QMenu,
    QStyle,
    QStackedWidget,
    QMessageBox,
    QInputDialog,
    QSpacerItem,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QSplitter,
    QFrame,
    QAbstractItemView,
    QLineEdit,
    QFileDialog,
    QListWidgetItem,
    QListWidget,
    QDialogButtonBox,
    QDialog,
    QCheckBox,
)

# --- 3. 專案內部模組 ---
from src.backend import adapter

# ==========================================
#   [New] 直覺引導氣泡 (Status Bubble)
# ==========================================
class StatusBubble(QWidget):
    """
    懸浮在眼睛下方的對話氣泡。
    - 支援淡入淡出
    - 支援自動消失
    - 視覺風格：半透明黑底 + 白字
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        # 設定為子視窗，但無邊框
        self.setWindowFlags(Qt.WindowType.SubWindow | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # 預設隱藏
        self.hide()
        
        # --- 介面佈局 ---
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        
        self.label = QLabel("提示訊息")
        self.label.setStyleSheet("""
            color: #FFFFFF;
            font-weight: bold;
            font-size: 11px;
        """)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label)
        
        # --- 自動消失計時器 ---
        self.fade_timer = QTimer(self)
        self.fade_timer.setSingleShot(True)
        self.fade_timer.timeout.connect(self.hide_bubble)

    def show_message(self, text: str, duration: int = 3000):
        """顯示訊息，並在 duration (毫秒) 後自動消失"""
        self.label.setText(text)
        self.adjustSize() # 自動調整大小以適應文字
        self.show()
        
        # 如果有設定時間，就啟動倒數
        if duration > 0:
            self.fade_timer.start(duration)

    def hide_bubble(self):
        self.hide()

    def paintEvent(self, event):
        """繪製圓角半透明背景"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = self.rect()
        
        # 半透明黑底
        brush_color = QColor(0, 0, 0, 180)
        painter.setBrush(QBrush(brush_color))
        painter.setPen(Qt.PenStyle.NoPen)
        
        # 畫圓角矩形
        painter.drawRoundedRect(rect, 10, 10)
        
        # (選配) 畫一個小三角形指向上面 (對話框的尾巴)
        # 這裡先保持簡單圓角，以免計算太複雜

# ==========================================
#   View A: 哨兵之眼 (Sentry Eye) - 正式實作
# ==========================================
class SentryEyeWidget(QWidget):
    
    # 這是我們的靜態常數
    DEFAULT_OUTPUT_FILENAMES = ["README.md", "README.MD", "readme.md", "INDEX.md", "index.md"]

    # 這是我們的靜態方法 (可以直接呼叫 SentryEyeWidget._find_default_output_file)
    @staticmethod
    def _find_default_output_file(folder_path: Path) -> str | None:
        """[核心] 檢查資料夾內是否存在預設寫入檔，並返回第一個存在的路徑。"""
        # 我們用「for...in...」這個結構，來一個一個地處理「預設寫入檔名稱（filename）」。
        for filename in SentryEyeWidget.DEFAULT_OUTPUT_FILENAMES:
            target_path = folder_path / filename
            # 我們用「if」來判斷，如果（if）這個路徑是一個檔案（is_file）...
            if target_path.is_file():
                # 就回傳（return）這個路徑的字串。
                return str(target_path)
        # 如果迴圈結束都沒找到，就回傳（return）空值（None）。
        return None

    def __init__(self, switch_callback):
        super().__init__()
        # [新增] 告訴視窗：我願意接收拖曳進來的東西
        self.setAcceptDrops(True)
        # 設定背景透明
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # 用於視窗拖曳的變數
        self.old_pos = None

        # [新增] 狀態記憶體：用來暫存「還沒餵飽」的專案資料夾
        self.pending_folder = None

        # --- 動畫核心 ---
        # 我們建立（create）一個計時器，讓眼睛動起來。
        self.timer = QTimer(self)
        # 每 50 毫秒（ms）觸發一次更新，讓畫面重畫。
        self.timer.timeout.connect(self.update)
        # 啟動（start）計時器。
        self.timer.start(50)
        # 這是一個變數，用來記錄動畫目前的「呼吸進度」。
        self.phase = 0
        # [新增] 吞噬動畫計數器 (0 = 無動畫, >0 = 播放中)
        self.eating_frame = 0

        # [新增] 初始化引導氣泡
        # 我們把 self (眼睛) 傳進去當作 parent，這樣氣泡就會成為眼睛的子視窗
        self.bubble = StatusBubble(self)
        # 設定氣泡初始位置 (相對於眼睛左上角)
        # 這裡先暫定 (10, 140)，也就是眼睛下方一點點
        self.bubble.move(10, 140)

        # [新增] 瞳孔運動神經
        self.pupil_offset = QPoint(0, 0)       # 目前位置
        self.target_offset = QPoint(0, 0)      # 目標位置

        # [新增] 掃視計時器 (Saccade Timer)
        self.saccade_timer = QTimer(self)
        self.saccade_timer.timeout.connect(self._trigger_saccade)
        self.saccade_timer.start(3000) # 初始每 3 秒動一次

        # [新增] 眨眼計時器 (Blink Timer)
        # 我們建立（create）一個計時器，專門控制眨眼。
        self.blink_timer = QTimer(self)
        # 時間到時，連結（connect）到觸發眨眼的方法。
        self.blink_timer.timeout.connect(self._trigger_blink)
        # 啟動（start）計時器，初始設定 4000 毫秒（4秒）。
        self.blink_timer.start(4000)

        # [新增] 眨眼狀態變數
        # 這是一個旗標，標記目前是否正在（is）眨眼。
        self.is_blinking = False
        # 這是一個浮點數，記錄眼皮閉合的進度（0.0 全開 ~ 1.0 全閉）。
        self.blink_progress = 0.0
        self.blink_repeats = 0  # [新增] 剩餘眨眼次數

        # --- 佈局設計 (維持不變) ---
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.addStretch(1)
        
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch(1) 
        
        self.btn_dashboard = QPushButton("哨兵管理")
        self.btn_dashboard.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_dashboard.setStyleSheet("""
            QPushButton {
                background-color: rgba(0, 0, 0, 150);
                color: white;
                border: 1px solid rgba(255, 255, 255, 100);
                border-radius: 5px;
                padding: 5px 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(40, 40, 40, 200);
                border-color: white;
            }
        """)
        self.btn_dashboard.clicked.connect(switch_callback)
        
        bottom_layout.addWidget(self.btn_dashboard)
        layout.addLayout(bottom_layout)

    def _trigger_saccade(self): 
        """隨機產生眼球移動目標""" 
        import random 
        # 隨機決定下一次動的時間 (2~5秒) 
        self.saccade_timer.setInterval(random.randint(2000, 5000))
        # 隨機決定看的方向 (範圍限制在 +/- 15px 以內，避免脫窗)
        # 這裡使用整數簡化計算
        rx = random.randint(-15, 15)
        ry = random.randint(-10, 10) # 上下移動範圍小一點，比較自然
        self.target_offset = QPoint(rx, ry)

    def _trigger_blink(self):
        """觸發眨眼動畫 (設定雙連眨)"""
        import random
        if self.eating_frame > 0:
            return

        # --- [教學] 修改這裡的數字來控制頻率 ---
        # 4000 = 4秒, 8000 = 8秒
        # 這表示：每隔 4~8 秒之間，會觸發一次眨眼
        next_interval = random.randint(4000, 8000) 
        self.blink_timer.setInterval(next_interval)
        
        # 開始眨眼
        self.is_blinking = True
        self.blink_progress = 0.0
        
        # [設定] 設定為 1，表示這次眨完後，還要「再眨 1 次」(共 2 次)
        # 如果您想要單次眨眼，改成 0 即可
        self.blink_repeats = 1

    def resizeEvent(self, event):
        """當視窗大小改變時，調整氣泡位置"""
        super().resizeEvent(event)
        # 讓氣泡水平置中
        if hasattr(self, 'bubble'):
            bx = (self.width() - self.bubble.width()) // 2
            # 放在高度的 85% 處 (眼睛下方)
            by = int(self.height() * 0.85) 
            self.bubble.move(bx, by)
        
    def paintEvent(self, event):
        """繪製精細版哨兵之眼 (v2.1: 中空機械眼 + 雷射邊框)"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # --- 0. 動畫核心計算 ---
        self.phase += 0.1
        breath_factor = 0.85 + 0.15 * abs(math.sin(self.phase))
        # --- [新增] 瞳孔物理運動 (Ease-out 插值) ---
        # 讓目前位置追趕目標位置，係數 0.1 代表速度
        dx = self.target_offset.x() - self.pupil_offset.x()
        dy = self.target_offset.y() - self.pupil_offset.y()

        # 更新目前位置 (轉成整數以利繪圖)
        new_x = self.pupil_offset.x() + int(dx * 0.1)
        new_y = self.pupil_offset.y() + int(dy * 0.1)
        self.pupil_offset = QPoint(new_x, new_y)
        # 狀態判斷
        is_eating = self.eating_frame > 0
        if is_eating:
            self.eating_frame -= 1
            breath_factor = 1.2 
            
        # 判斷是否處於「飢渴狀態 (Hunting Mode)」
        is_hungry = self.pending_folder is not None

        rect = self.rect()
        center = rect.center()
        w = rect.width()
        h = rect.height()
        
        # [動態適配] 使用相對比例，而非固定數值
        eye_width = w * 0.8
        eye_height = h * 0.5

        # --- 定義色票 (Color Palette) ---
        if is_eating:
            # 吞噬中：綠色
            main_color = QColor(50, 255, 50)
            glow_color = QColor(0, 200, 0)
        elif is_hungry:
            # 飢渴中：橘紅色
            main_color = QColor(255, 140, 0) 
            glow_color = QColor(255, 69, 0)  
        else:
            # 正常：青色
            main_color = QColor(0, 255, 255)
            glow_color = QColor(0, 150, 255)

        # --- 1. 背景光暈 ---
        halo_radius = (eye_width / 2) * breath_factor * 1.2
        halo = QRadialGradient(center, halo_radius)
        
        # 設定透明度
        c1 = QColor(main_color)
        c1.setAlpha(100 if not is_eating else 180)
        c2 = QColor(glow_color)
        c2.setAlpha(40 if not is_eating else 50)
        
        halo.setColorAt(0.0, c1)
        halo.setColorAt(0.5, c2)
        halo.setColorAt(1.0, QColor(0, 0, 0, 0))
        
        painter.setBrush(QBrush(halo))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(center, halo_radius, halo_radius)
        
        # --- 2. 眼眶 (上下眼瞼) ---
        path = QPainterPath()
        left_pt = QPoint(int(center.x() - eye_width/2), int(center.y()))
        right_pt = QPoint(int(center.x() + eye_width/2), int(center.y()))
        top_ctrl = QPoint(int(center.x()), int(center.y() - eye_height))
        bottom_ctrl = QPoint(int(center.x()), int(center.y() + eye_height))
        
        path.moveTo(left_pt)
        path.quadTo(top_ctrl, right_pt)
        path.quadTo(bottom_ctrl, left_pt)
        
        # 外框顏色
        pen_color = QColor(main_color)
        pen_color.setAlpha(255)
        pen_glow = QPen(pen_color)
        # [視覺微調] 使用浮點數寬度，讓線條更細緻 (1.5px / 2.5px)
        pen_glow.setWidthF(2.5 if is_eating else 1.5)
        painter.setPen(pen_glow)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)

# --- 3. 瞳孔 (v2.1: 中空雷射環 + 物理運動) ---
        # [關鍵 1] 計算瞳孔的新中心點 (原本的中心 + 偏移量)
        pupil_center = center + self.pupil_offset

        # [關鍵 2] 根據狀態決定瞳孔大小 (維持 Task 9.2.1 的邏輯)
        if is_eating:
            pupil_scale = 0.2
        elif is_hungry:
            pupil_scale = 0.55 
        else:
            pupil_scale = 0.45 

        pupil_r = eye_height * pupil_scale
        
        # [關鍵 3] 繪製 (注意：這裡全部改成用 pupil_center！)
        
        # A. 虹膜 (透明 + 邊框)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        ring_pen = QPen(main_color)
        ring_pen.setWidthF(1.5) 
        painter.setPen(ring_pen)
        # 使用新的中心點繪製
        painter.drawEllipse(pupil_center, pupil_r, pupil_r)
        
        # B. 內圈瞳孔 (黑色實心)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(0, 0, 0, 220)))
        # 使用新的中心點繪製
        painter.drawEllipse(pupil_center, pupil_r * 0.6, pupil_r * 0.6)

        # --- 4. 眨眼動畫 (v2.2: 單向 + 雙連眨) ---
        if self.is_blinking:
            # 增加進度 (0.35 = 眨得更快一點，因為要眨兩下)
            self.blink_progress += 0.35

            # 計算閉合程度
            if self.blink_progress <= 1.0:
                lid_factor = self.blink_progress
            else:
                lid_factor = 2.0 - self.blink_progress

            # 動畫結束檢查
            if self.blink_progress >= 2.0:
                # [關鍵] 檢查是否需要連眨
                if self.blink_repeats > 0:
                    self.blink_repeats -= 1
                    self.blink_progress = 0.0 # 重置進度，馬上再眨一次
                    lid_factor = 0.0
                else:
                    # 真的結束了
                    self.is_blinking = False
                    self.blink_progress = 0.0
                    lid_factor = 0.0

            # 設定剪裁
            painter.save()
            painter.setClipPath(path)

            # 計算眼皮高度
            # 因為只從上面蓋下來，高度需要是原本的 2 倍才能蓋滿全眼
            lid_h = int(eye_height * 2 * lid_factor)
            
            lid_color = QColor(main_color)
            lid_color.setAlpha(200) 
            painter.setBrush(QBrush(lid_color))
            painter.setPen(Qt.PenStyle.NoPen)

            # 只畫上眼瞼 (從上往下蓋)
            # 起點 Y 是眼眶最高點 (center.y - eye_height)
            painter.drawRect(
                int(center.x() - eye_width/2), 
                int(center.y() - eye_height), 
                int(eye_width), 
                lid_h
            )
            
            painter.restore()

    # --- 實作無邊框視窗的拖曳功能 ---
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if self.old_pos:
            delta = event.globalPosition().toPoint() - self.old_pos
            # 注意：這裡是移動父容器 (SentryTrayAppV2.container)
            # 因為 SentryEyeWidget 只是 container 裡的一頁
            self.window().move(self.window().pos() + delta)
            self.old_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        self.old_pos = None

        # --- 拖曳事件處理 ---
    def dragEnterEvent(self, event):
        """當拖曳物進入視窗時觸發"""
        # 我們檢查（check）拖曳物是否包含檔案路徑（Urls）。
        if event.mimeData().hasUrls():
            # 如果有，我們就接受（accept）這個動作，游標會變。
            event.accept()
        else:
            # 否則，我們忽略（ignore），游標顯示禁止符號。
            event.ignore()

    def dropEvent(self, event):
        """處理放下事件：氣泡回饋版 (Status Bubble Integration)"""
        urls = event.mimeData().urls()
        if not urls:
            return
            
        path_str = urls[0].toLocalFile()
        path_obj = Path(path_str)
        
        # --- [Priority 0] 解除飢餓狀態 ---
        if self.pending_folder:
            if path_obj.is_file():
                folder = self.pending_folder
                target_file = path_str
                self.pending_folder = None
                self._execute_add_project(folder, target_file)
                event.accept()
            else:
                # [氣泡] 錯誤提示
                self.bubble.show_message("❌ 錯誤：請餵我「檔案」作為寫入目標！", 3000)
                event.ignore()
            return

        # --- [Layer 1] 舊雨判定 ---
        if path_obj.is_dir():
            match_proj = adapter.match_project_by_path(path_str)

            if match_proj:
                if match_proj.status == "monitoring":
                    adapter.trigger_manual_update(match_proj.uuid)
                    # [氣泡] 單次更新回饋
                    self.bubble.show_message(f"✨ 專案「{match_proj.name}」\n已觸發單次更新！", 3000)
                else:
                    adapter.toggle_project_status(match_proj.uuid)
                    # [氣泡] 啟動回饋
                    self.bubble.show_message(f"👁️ 歡迎回來，{match_proj.name}。\n哨兵已啟動！", 4000)
                
                event.accept()
                return

        # --- [Layer 2 & 3] 新專案處理 ---
        if path_obj.is_dir():
            # Layer 2: 智慧預設
            default_file = self._find_default_output_file(path_obj)
            
            if default_file:
                # [氣泡] 預設檔命中提示 (在彈出輸入框前先給個提示)
                self.bubble.show_message("✨ 已鎖定預設檔，準備啟動...", 2000)
                # 這裡稍微延遲一下再彈出輸入框，讓氣泡能被看到
                QTimer.singleShot(500, lambda: self._execute_add_project(str(path_obj), default_file))
            else:
                # Layer 3: 飢餓模式
                self.pending_folder = str(path_obj)
                self.update() 
                # [氣泡] 引導提示 (顯示久一點：8秒)
                self.bubble.show_message("🟠 收到資料夾！\n請再拖入「寫入檔」給我...", 8000)
            event.accept()
            
        elif path_obj.is_file():
            menu = QMenu(self)
            menu.setStyleSheet("QMenu { background-color: rgba(20, 20, 30, 240); color: white; border: 1px solid #00FFFF; }")
            action = QAction(f"⚡ 單次更新: {path_obj.name}", menu)
            action.triggered.connect(lambda: self.bubble.show_message("🚧 功能開發中...", 2000))
            menu.addAction(action)
            if not menu.isEmpty():
                menu.exec(QCursor.pos())
                event.accept()


    def _execute_add_project(self, folder, output_file):
        """[內部工具] 執行最終的新增動作"""
        path_obj = Path(folder)
        default_name = path_obj.name
        
        # 詢問別名
        name, ok = QInputDialog.getText(self, "新哨兵設定", "請輸入專案別名：", text=default_name)
        if not ok or not name:
            # 如果取消，記得把暫存清空，不然會卡在飢餓狀態
            self.pending_folder = None
            return

        try:
            adapter.add_project(name=name, path=folder, output_file=output_file)
            # [新增] 觸發吞噬動畫 (持續約 20 幀)
            self.eating_frame = 20
            # [修正] 延遲 600 毫秒再彈出視窗，讓使用者先欣賞「吞噬動畫」
            actual_filename = Path(output_file).name
            QTimer.singleShot(600, lambda: QMessageBox.information(self, "新增成功", f"已加入哨兵：{name}\n目標：{Path(output_file).name}"))
        except Exception as e:
            QMessageBox.critical(self, "新增失敗", str(e))
            self.pending_folder = None # 失敗也要重置

    def _real_add_project(self, path_obj):
        """[真實邏輯] 呼叫 Adapter 新增專案 (含智慧引導)"""
        folder_path = str(path_obj)
        default_name = path_obj.name
        
        # 1. 詢問別名
        name, ok = QInputDialog.getText(self, "新哨兵設定", "請輸入專案別名：", text=default_name)
        if not ok or not name:
            return

        # 2. 尋找第一個存在的寫入檔 (大小寫不敏感檢查)
        # HACK: 直接複製靜態常數到區域變數，避免 Pylance 在 f-string 內報錯
        DEFAULT_NAMES = SentryEyeWidget.DEFAULT_OUTPUT_FILENAMES 
        
        # 我們現在直接呼叫 SentryEyeWidget 類別內的靜態方法
        output_file = SentryEyeWidget._find_default_output_file(path_obj)

        # 舊有邏輯：如果一個預設寫入檔都找不到，就報錯。
        if output_file is None:
            # 提示（show warning）：未找到預設寫入檔，無法自動註冊。
            QMessageBox.warning(self, "Sentry 警告",
                                f"此資料夾未找到預設寫入檔：{DEFAULT_NAMES} 中的任何一個。\n" # 使用新的區域變數
                                "請先手動創建一個 Markdown 檔案，或使用控制台手動新增專案。",
                                QMessageBox.StandardButton.Ok)
            # 用「return」結束新增流程。
            return

        # 3. 呼叫後端 (使用找到的 output_file)
        try:
            # 嘗試快速新增
            adapter.add_project(name=name, path=folder_path, output_file=output_file)
            # R2 修正: 確保成功訊息顯示的是實際找到的檔名，而不是硬編碼的 README.md。
            actual_filename = Path(output_file).name 
            QMessageBox.information(self, "新增成功", f"已加入哨兵：{name}\n目標：{actual_filename}")
            
        except Exception as e:
            # --- 失敗後的智慧引導 ---
            error_msg = str(e)
            
            # 【關鍵優化】如果找不到預設檔案（R2 暫時解法）
            # 或者是後端報錯，我們直接引導使用者去控制台。
            if "不存在" in error_msg or "No such file" in error_msg or "已被佔用" in error_msg:
                QMessageBox.warning(
                    self, 
                    "新增失敗 - 需要手動修正", 
                    f"快速新增失敗：找不到預設寫入檔，或專案已被佔用。\n\n已為您切換至【控制台】，請在下方手動輸入路徑。",
                    QMessageBox.StandardButton.Ok
                )
                
                # 執行切換到 View B (控制台) 的動作
                self.btn_dashboard.click()
                
                # 這裡未來可以新增邏輯：自動填入 View B 的輸入框
                # 但目前 View B 的輸入框邏輯還沒完全移植，先只做到切換。
                
            else:
                # 其他錯誤（例如後端崩潰、Adapter 通訊失敗）直接報錯
                QMessageBox.critical(self, "新增失敗", error_msg)

    def mouseDoubleClickEvent(self, event):
        """雙擊隱藏視窗"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.window().hide()

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

class TargetListWidget(QListWidget):
    """
    專門用於處理寫入檔列表的 QListWidget 子類別。
    它接收專案 UUID 和重載回調函式，直接執行拖曳新增邏輯。
    """
    def __init__(self, uuid, reload_callback, log_callback, parent=None):
        super().__init__(parent)
        # 儲存參數
        self.uuid = uuid 
        self.reload_data = reload_callback 
        self.log_callback = log_callback
        self.VALID_EXTENSIONS = {'.md', '.markdown', '.txt', '.log'}

        # --- 拖曳核心設定 ---
        # 告訴列表：接受拖曳進來的東西
        self.setAcceptDrops(True)
        # 設定模式：只接受「放下 (DropOnly)」，不允許把項目拖出去
        self.setDragDropMode(QAbstractItemView.DragDropMode.DropOnly)
        # 設定選取模式：允許「多選 (ExtendedSelection)」，方便一次刪除多個
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)

        # --- 視覺提示 ---
        # 設定樣式表：給它一個虛線框和提示文字背景，讓它看起來像個「接收區」
        self.setStyleSheet("""
            QListWidget {
                border: 2px dashed #AAAAAA;
                border-radius: 5px;
                background-color: #F9F9F9;
                padding: 5px;
            }
            QListWidget::item {
                background-color: white;
                border-bottom: 1px solid #EEEEEE;
                padding: 4px;
            }
            QListWidget::item:selected {
                background-color: #D2E1F5;
                color: black;
            }
        """)
        # 設定提示文字 (當列表為空時顯示，雖然 QListWidget 預設不支援直接顯示文字，但邊框已經足夠提示)
        self.setToolTip("💡 提示：您可以直接將多個 Markdown 檔案「拖曳」到此列表中加入")

    def dragEnterEvent(self, event):
        """當拖曳物進入列表時觸發"""
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    # [新增] 處理拖曳移動事件 (這是關鍵！很多時候是這裡拒絕了拖曳)
    def dragMoveEvent(self, event):
        """當拖曳物在列表中移動時觸發"""
        if event.mimeData().hasUrls():
            event.setDropAction(Qt.DropAction.CopyAction)
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        """處理放下事件：批次呼叫後端追加目標"""
        from pathlib import Path
        from PySide6.QtWidgets import QMessageBox

        urls = event.mimeData().urls()
        if not urls:
            return
            
        added_count = 0
        error_count = 0
        
        for url in urls:
            path_str = url.toLocalFile()
            path_obj = Path(path_str)
            
            # 只處理存在的檔案，且在白名單內
            if path_obj.is_file() and path_obj.suffix.lower() in self.VALID_EXTENSIONS:
                try:
                    # 呼叫後端追加 (複用既有的 adapter 接口)
                    adapter.add_target(self.uuid, path_str)
                    added_count += 1
                    self.log_callback(f"+ 拖曳新增: {Path(path_str).name}")
                except Exception:
                    # 如果後端拒絕 (例如：重複路徑、路徑無效)，我們計數但繼續處理下一個
                    error_count += 1
            
        # 根據結果更新介面與回饋
        if added_count > 0 or error_count > 0:
            self.reload_data() # 刷新列表
            msg = f"✓ 成功追加 {added_count} 個目標。"
            if error_count > 0:
                msg += f" (忽略 {error_count} 個重複/無效路徑)"
            QMessageBox.information(self, "批次追加結果", msg)
            event.accept()
        else:
            QMessageBox.warning(self, "警告", "拖曳無效：沒有可識別的 Markdown 檔案。")
            event.ignore()

# 我們用「class」來定義（define）編輯專案設定視窗類別。
class EditProjectDialog(QDialog):
    """
    修改專案設定視窗 (v2.0 - 多目標支援版)：
    - 名稱 (Name) / 路徑 (Path)：【延遲儲存】按下 Save 才寫入。
    - 寫入檔 (Targets)：【即時操作】按下新增/刪除按鈕立即生效。
    """
    def __init__(self, parent=None, project_data: adapter.ProjectInfo | None = None):

        super().__init__(parent)
        self.project_data = project_data # 保留參照以便重新讀取
        self.uuid = project_data.uuid if project_data else ""
        # [新增] 記錄即時操作的次數 (如增刪寫入檔)
        self.change_log = []
        self.setWindowTitle(f"修改專案設定 - {project_data.name if project_data else ''}")
        self.resize(600, 500) # 加高一點以容納列表
        
        self._build_ui(project_data)

    def _build_ui(self, data: adapter.ProjectInfo | None):
        main_layout = QVBoxLayout(self)

        # --- A. 基本資料區 (延遲儲存) ---
        group_basic = QFrame()
        group_basic.setFrameShape(QFrame.Shape.StyledPanel)
        layout_basic = QVBoxLayout(group_basic)
        
        layout_basic.addWidget(QLabel("<b>基本設定 (按下 Save 後生效)</b>"))
        
        # 1. 專案名稱
        self.name_edit = QLineEdit(data.name if data else "")
        layout_basic.addWidget(QLabel("專案名稱 (Alias)："))
        layout_basic.addWidget(self.name_edit)

        # 2. 專案路徑
        self.path_edit = QLineEdit(data.path if data else "")
        layout_basic.addWidget(QLabel("專案資料夾路徑 (Path)："))
        layout_basic.addWidget(self.path_edit)
        layout_basic.addWidget(QLabel("提示：修改路徑可能導致哨兵重啟！"))
        
        main_layout.addWidget(group_basic)
        main_layout.addSpacing(10)

        # --- B. 寫入檔管理區 (即時生效) ---
        group_targets = QFrame()
        group_targets.setFrameShape(QFrame.Shape.StyledPanel)
        layout_targets = QVBoxLayout(group_targets)
        
        layout_targets.addWidget(QLabel("<b>寫入檔管理 (即時生效)</b>"))
        
        # 目標列表
        # 我們替換為專門處理拖曳的 TargetListWidget
        # 傳入 uuid 和 刷新回調函式 (_reload_data)
        # [新增] 傳入 log_callback 以便記錄拖曳新增的日誌
        self.target_list = TargetListWidget(
            uuid=self.uuid, 
            reload_callback=self._reload_data,
            log_callback=self._append_log
        )
        # [新增] 啟用寫入檔列表的拖曳功能
        self.target_list.setAcceptDrops(True)
        self._refresh_target_list(data.output_file if data else [])
        layout_targets.addWidget(self.target_list)
        
        # 按鈕區
        btn_layout = QHBoxLayout()
        btn_add = QPushButton("➕ 追加寫入檔...")
        btn_remove = QPushButton("➖ 移除選中檔")
        
        btn_add.clicked.connect(self._on_add_target)
        btn_remove.clicked.connect(self._on_remove_target)
        
        btn_layout.addWidget(btn_add)
        btn_layout.addWidget(btn_remove)
        layout_targets.addLayout(btn_layout)
        
        main_layout.addWidget(group_targets)

        # --- C. 底部按鈕 ---
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)

    def _refresh_target_list(self, targets: List[str]):
        """刷新列表顯示"""
        self.target_list.clear()
        for t in targets:
            self.target_list.addItem(t)

    def _reload_data(self):
        """從後端重新讀取此專案的最新資料 (用於更新列表)"""

        all_projects = adapter.list_projects()
        current = next((p for p in all_projects if p.uuid == self.uuid), None)
        if current:
            self.project_data = current
            self._refresh_target_list(current.output_file)

    def _append_log(self, msg: str):
        self.change_log.append(msg)

    def _on_add_target(self):
        """處理追加寫入檔 (即時)"""
        # HACK: 避免循環引用
        from PySide6.QtWidgets import QFileDialog, QMessageBox
        
        file_path, _ = QFileDialog.getOpenFileName(
            self, "選擇要追加的 Markdown 檔案", "", "Markdown (*.md *.txt);;All Files (*.*)"
        )
        
        if not file_path:
            return

        try:
            # 呼叫後端追加
            adapter.add_target(self.uuid, file_path)
            self._append_log(f"+ 新增: {Path(file_path).name}") 
            # 刷新介面
            self._reload_data()
            QMessageBox.information(self, "成功", "已成功追加寫入目標。")
        except Exception as e:
            QMessageBox.critical(self, "追加失敗", str(e))

    def _on_remove_target(self):
        """處理移除寫入檔 (支援批次移除)"""
        selected_items = self.target_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "提示", "請先選擇要移除的路徑。")
            return
            
        count = len(selected_items)
        
        # 1. 構建確認訊息
        if count == 1:
            target_path = selected_items[0].text()
            msg = f"確定要移除此寫入目標嗎？\n{target_path}"
        else:
            msg = f"確定要移除這 {count} 個寫入目標嗎？"

        # 2. 二次確認
        reply = QMessageBox.question(
            self, "確認移除", msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # 3. 執行批次移除
            error_count = 0
            for item in selected_items:
                path_to_remove = item.text()
                try:
                    adapter.remove_target(self.uuid, path_to_remove)
                    self._append_log(f"- 移除: {Path(path_to_remove).name}")
                except Exception:
                    error_count += 1
            
            # 4. 刷新介面
            self._reload_data()
            
            if error_count > 0:
                QMessageBox.warning(self, "部分失敗", f"有 {error_count} 個檔案移除失敗。")

    def get_changes(self) -> Dict[str, Any]:
        """回傳基本資料的變更 (Name/Path) 以及寫入檔變更"""
        changes = {}
        
        # 1. 檢查名稱變更
        new_name = self.name_edit.text().strip()
        if self.project_data and new_name != self.project_data.name:
            if new_name:
                changes['name'] = new_name

        # 2. 檢查路徑變更
        new_path = self.path_edit.text().strip()
        if self.project_data and new_path != self.project_data.path:
            if new_path:
                changes['path'] = new_path
        
        # 3. [新增] 檢查寫入檔變更
        # 我們收集目前列表中的所有項目
        current_targets = []
        for i in range(self.target_list.count()):
            item = self.target_list.item(i)
            current_targets.append(item.text())
            
        # 與原始資料比對 (轉換成 set 比較內容，忽略順序)
        original_targets = self.project_data.output_file if self.project_data else []
        
        if set(current_targets) != set(original_targets):
            # 如果有變動，將新列表放入 changes
            changes['output_file'] = current_targets
            
        return changes  


class DashboardWidget(QWidget):
    """
    Sentry 控制台主視窗（接 backend_adapter 的雛型）
    """

    # 我們用「def」來 定義（define）初始化方法，並接收統計回調（on_stats_change）。
    def __init__(self, on_stats_change=None, switch_callback=None) -> None:
        # 我們 呼叫（call）父類別的初始化。
        super().__init__()
        # 設定視窗的標題（Window Title）。
        self.setWindowTitle("Sentry 控制台 v1 (UX 測試樣板)")
        # 設定視窗的初始大小（resize），寬 900 像素，高 600 像素。
        self.resize(900, 600)
        # 我們將切換回調函式 儲存（store）起來 
        self.switch_callback = switch_callback
        # [新增] 用於視窗拖曳的變數
        self.old_pos = None
        # 我們將回調函式 儲存（store）起來，供稍後使用。
        self.on_stats_change = on_stats_change


        # # TODO: 這裡的註解將使用通俗比喻來解釋資料結構。
        # 準備一個叫「current_projects」的空籃子（[]），
        # 專門用來存放從後端讀取的專案資訊（adapter.ProjectInfo）。
        self.current_projects: list[adapter.ProjectInfo] = []
        self.new_input_fields: list[QLineEdit] = [] 
        self.new_browse_buttons: list[QPushButton] = []
        # 呼叫各類函式來 建立介面 和 載入初始資料。        
        self._build_ui()
                
        # 載入資料
        self._load_ignore_settings()

    # --- [新增] 獨立的統計通知函式 ---
    # 我們用「def」來 定義（define）重新計算並通知上層的函式。
    def _notify_stats_update(self) -> None:
        """重新計算監控/靜默數量，並通知 Tray 更新 Tooltip"""
        # 如果沒有設定回調，就不做任何事。
        if not self.on_stats_change:
            return

        running_count = 0
        muting_count = 0
        
        # 我們用「for」來 遍歷（iterate）所有專案。
        for p in self.current_projects:
            if p.status == "monitoring":
                if p.mode == "silent":
                    muting_count += 1
                else:
                    running_count += 1
        
        # 我們 呼叫（call）回調函式，把數字傳出去。
        self.on_stats_change(running_count, muting_count)

    # ---------------------------
    # UI 建構
    # ---------------------------

    # 這裡，我們用「def」來定義（define）建立介面（UI）的函式。
    def _build_ui(self) -> None:
        # 建立主佈局（main_layout），採用垂直佈局（QVBoxLayout），東西將從上往下排。
        main_layout = QVBoxLayout(self)

        # --- 頂部導航區 (返回按鈕) ---
        nav_layout = QHBoxLayout()
        # 依照 UI_Strings_Reference_v2.md 定義的返回按鈕
        btn_back = QPushButton("↩ 返回哨兵之眼") 
        # 將按鈕連接到我們在 __init__ 中儲存的回調
        btn_back.clicked.connect(self.switch_callback) 

        # 標題
        title_label = QLabel("Sentry 控制台")
        title_label.setStyleSheet("font-weight: bold;")

        nav_layout.addWidget(btn_back)
        nav_layout.addWidget(title_label)
        nav_layout.addStretch(1) # 推到底
        main_layout.addLayout(nav_layout)
        # --- 導航區塊結束 ---

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


    def _build_input_fields(self) -> None:
        """
        [移植自 v1.8] 建立新增專案的輸入欄位（支援 1 個專案資料夾 + 3 個寫入檔）。
        """
        # 建立一個叫 new_input_fields 的「空籃子」（List），用來存放所有輸入框物件。
        self.new_input_fields: list[QLineEdit] = []
        self.new_browse_buttons: list[QPushButton] = [] # 瀏覽按鈕列表

        # --- 1. 建立別名輸入列 (預設隱藏) ---
        self.alias_container = QWidget()
        alias_layout = QHBoxLayout(self.alias_container)
        alias_layout.setContentsMargins(0, 0, 0, 0)
        
        alias_label = QLabel("專案別名：")
        self.alias_edit = QLineEdit()
        self.alias_edit.setPlaceholderText("可選：自訂顯示名稱")
        
        alias_layout.addWidget(alias_label)
        alias_layout.addWidget(self.alias_edit)
        self.new_project_input_layout.addWidget(self.alias_container)
        self.alias_container.setVisible(False)
        
        # 2. 專案資料夾列 (索引 0)
        folder_row = QHBoxLayout()
        folder_label = QLabel("專案資料夾：")
        self.new_project_folder_edit = QLineEdit()
        self.new_project_folder_edit.setPlaceholderText("例如：/home/user/my_project")
        self.new_project_folder_button = QPushButton("瀏覽…")

        folder_row.addWidget(folder_label)
        folder_row.addWidget(self.new_project_folder_edit, stretch=1)
        folder_row.addWidget(self.new_project_folder_button)
        self.new_project_input_layout.addLayout(folder_row)
        
        self.new_input_fields.append(self.new_project_folder_edit)
        self.new_browse_buttons.append(self.new_project_folder_button)
        
        # 3. 寫入檔路徑列 (索引 1, 2, 3 - 最多 3 個)
        for i in range(1, 4):
            output_row = QHBoxLayout()
            output_label = QLabel(f"寫入檔 {i}：")
            output_edit = QLineEdit()
            output_edit.setPlaceholderText(f"目標 Markdown 文件 {i}")
            output_button = QPushButton("瀏覽…")
            
            output_row.addWidget(output_label)
            output_row.addWidget(output_edit, stretch=1)
            output_row.addWidget(output_button)

            self.new_project_input_layout.addLayout(output_row)

            self.new_input_fields.append(output_edit)
            self.new_browse_buttons.append(output_button)

        # 4. 事件連結 (Signal/Slot)
        # 重新接上神經：綁定「瀏覽…」按鈕的點擊事件
        for btn in self.new_browse_buttons:
            # 使用 lambda 鎖定按鈕實例 b=btn
            btn.clicked.connect(lambda checked, b=btn: self._on_select_new_path(b))

        # 重新接上神經：綁定輸入框的文字變動事件
        for edit in self.new_input_fields:
            edit.textChanged.connect(self._update_new_project_submit_state)
        self.new_project_input_layout.addStretch(1)

    def _toggle_input_mode(self, checked: bool) -> None:
        """[移植自 v1.8] 切換輸入模式：控制別名欄位的顯隱"""
        self.alias_container.setVisible(checked)
        if not checked:
            self.alias_edit.clear()
            
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
        # 設定選取模式（ExtendedSelection）：支援一次可以選取批量檔案。
        table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
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


    def _build_detail_panel(self) -> QFrame:
        # 建立一個框架（QFrame），作為右側面板的容器。
        frame = QFrame(self)
        # 設定框架的外觀形狀（setFrameShape）為帶有樣式（StyledPanel）的面板。
        frame.setFrameShape(QFrame.Shape.StyledPanel)

        # 建立一個垂直佈局（QVBoxLayout），把元件從上往下排。
        layout = QVBoxLayout(frame)

        # --- 上半部：專案詳情 ---
        self.detail_label = QLabel(
            "專案詳情區：\n"
            "選取左側某個專案後，會在這裡顯示其狀態與模式。"
        )
        self.detail_label.setWordWrap(True)
        layout.addWidget(self.detail_label)

        # 加入分隔線
        layout.addSpacing(16)

        # --- 下半部：新增/調試專案區 (恢復入口，作為 View A 的後備基地) ---
        
        # 建立一個框架來容納新增區塊，使其與詳情區分隔
        group_new_container = QFrame()
        group_new_container.setFrameShape(QFrame.Shape.StyledPanel)
        group_layout = QVBoxLayout(group_new_container)
        
        # 建立一個水平佈局，用來放標題和模式開關
        title_layout = QHBoxLayout()
        title_label = QLabel("新增專案 / 自由更新 (後備入口)")
        font = title_label.font()
        font.setBold(True)
        title_label.setFont(font)
        
        # 模式開關 (預設不勾選)
        self.mode_checkbox = QCheckBox("自訂別名 (自由模式)")
        self.mode_checkbox.toggled.connect(self._toggle_input_mode)

        title_layout.addWidget(title_label)
        title_layout.addStretch(1) 
        title_layout.addWidget(self.mode_checkbox)
        group_layout.addLayout(title_layout)

        # 輸入框容器
        self.new_project_input_layout = QVBoxLayout()
        group_layout.addLayout(self.new_project_input_layout)
        
        # 呼叫專門負責建立這些輸入框的函式
        self._build_input_fields()

        # [新增] 拖曳提示區 (提示使用者主要拖曳應在 View A)
        self.drag_tip = QLabel("提示：主要拖曳新增功能在「哨兵之眼 (View A)」")
        self.drag_tip.setStyleSheet("color: gray; font-size: 10px;")
        group_layout.addWidget(self.drag_tip)


        # 送出按鈕
        self.new_project_submit_button = QPushButton("確認新增 / 執行更新")
        self.new_project_submit_button.setEnabled(False)
        # 注意：這裡我們需要綁定一個實際的提交函式，我們暫時複用 _on_submit_new_project 的名字
        self.new_project_submit_button.clicked.connect(self._on_submit_new_project)
        group_layout.addWidget(self.new_project_submit_button)
        
        layout.addWidget(group_new_container) # 將整個群組加入主佈局
        layout.addStretch(1) # 空白推底


        # 回傳（return）設定好的框架元件。
        return frame
    

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

    def _reload_projects_from_backend(self) -> None:
        """呼叫 adapter.list_projects()，並刷新表格內容 (訊號屏蔽版)。"""
        # 1. 獲取資料
        self.current_projects = adapter.list_projects()
        
        # 2. 更新統計與 Tooltip
        self._notify_stats_update()

        # [關鍵修正] 暫時切斷表格的訊號，避免更新過程觸發不必要的 selectionChanged
        self.project_table.blockSignals(True)
        
        try:
            self.project_table.setRowCount(len(self.current_projects))
            
            for row, proj in enumerate(self.current_projects):
                # 1. UUID (隱藏)
                uuid_item = QTableWidgetItem(proj.uuid)
                uuid_item.setFlags(uuid_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.project_table.setItem(row, 0, uuid_item)

                # 2. 名稱
                name_item = QTableWidgetItem(proj.name)
                name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.project_table.setItem(row, 1, name_item)

                # 3. 狀態
                status_item = QTableWidgetItem(self._status_to_label(proj.status))
                status_item.setFlags(status_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.project_table.setItem(row, 2, status_item)

                # 4. 模式
                mode_item = QTableWidgetItem(self._mode_to_label(proj.mode))
                mode_item.setFlags(mode_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.project_table.setItem(row, 3, mode_item)

            # [關鍵修正] 資料填完後，手動處理選取狀態
            if self.current_projects:
                # 預設選取第一行 (或者您可以改成保持之前的選取，但選第一行最穩)
                self.project_table.selectRow(0)
                
                # 手動更新詳情面板 (因為訊號被切斷了，必須手動呼叫)
                self._update_detail_panel(self.current_projects[0])
            else:
                self._update_detail_panel(None)
                
        finally:
            # [關鍵修正] 無論如何，最後一定要把訊號接回去，不然使用者就不能點擊了
            self.project_table.blockSignals(False)

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

        # DashboardWidget 類別內 (貼入)
    
    def _on_submit_new_project(self) -> None:
        """處理新增專案 / 自由更新"""
        # 1. 獲取路徑
        folder = self.new_input_fields[0].text().strip()
        primary_output = self.new_input_fields[1].text().strip()

        if not folder or not primary_output:
            return

        # 2. 決定名稱
        from pathlib import Path
        default_name = Path(folder).name or "New Project"
        
        alias_input = self.alias_edit.text().strip()
        use_alias = self.alias_container.isVisible() and bool(alias_input)
        name = alias_input if use_alias else default_name

        # 3. 呼叫後端 (自動重試邏輯)
        while True:
            try:
                adapter.add_project(name=name, path=folder, output_file=primary_output)
                
                # 成功
                QMessageBox.information(self, "成功", f"專案 '{name}' 已新增。")
                
                # 清空欄位並重整
                for edit in self.new_input_fields:
                    edit.clear()
                self.alias_edit.clear()
                self._update_new_project_submit_state()
                self._reload_projects_from_backend()
                break

            except Exception as e:
                error_msg = str(e)
                if "已被佔用" in error_msg:
                    # 重名處理
                    new_name, ok = QInputDialog.getText(
                        self, "名稱衝突", f"名稱 '{name}' 已存在，請輸入新名稱：", text=name + "_new"
                    )
                    if ok and new_name:
                        name = new_name.strip()
                        continue # 重試
                    else:
                        return # 取消
                else:
                    QMessageBox.critical(self, "失敗", error_msg)
                    return
        
    def _on_select_new_path(self, button: QPushButton) -> None:
        """處理瀏覽按鈕點擊"""
        try:
            index = self.new_browse_buttons.index(button)
        except ValueError:
            return

        target_edit = self.new_input_fields[index]

        if index == 0:
            # 索引 0 = 專案資料夾
            path = QFileDialog.getExistingDirectory(self, "選擇專案資料夾")
            if path:
                target_edit.setText(path)
        else:
            # 索引 > 0 = 寫入檔 (允許選擇不存在的檔案，因為這是手動模式)
            file_path, _ = QFileDialog.getSaveFileName(
                self, f"選擇寫入檔路徑 {index}", "", "Markdown (*.md);;All Files (*.*)"
            )
            if file_path:
                target_edit.setText(file_path)
        
        # 觸發狀態檢查
        self._update_new_project_submit_state()

    def _update_new_project_submit_state(self) -> None:
        """檢查必要欄位是否已填寫"""
        if not hasattr(self, 'new_input_fields') or len(self.new_input_fields) < 2:
            return

        folder_ok = bool(self.new_input_fields[0].text().strip())
        output_ok = bool(self.new_input_fields[1].text().strip())
        
        self.new_project_submit_button.setEnabled(folder_ok and output_ok)

    # 這裡，我們用「def」來定義（define）當專案列表被雙擊時（double_clicked）執行的函式。
    def _on_project_double_clicked(self) -> None:
        """雙擊列 → 切換監控狀態。"""

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

        # 【關鍵修復】狀態改變了，這裡一定要重新算一次人頭！
        self._notify_stats_update()

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

    def _on_table_context_menu(self, position) -> None:
        """顯示右鍵選單：支援批次刪除。"""
        # 獲取所有選取的列 (rows)
        selection = self.project_table.selectionModel().selectedRows()
        if not selection:
            return

        menu = QMenu(self.project_table)
        
        # 判斷選取數量
        count = len(selection)
        
        if count == 1:
            # 單選邏輯 (保持原有功能：更新、修改、刪除)
            row = selection[0].row()
            uuid_item = self.project_table.item(row, 0)
            name_item = self.project_table.item(row, 1)
            
            if not uuid_item or not name_item: return
            
            p_uuid = uuid_item.text()
            p_name = name_item.text()

            action_update = QAction("🔄 立即手動更新", menu)
            action_update.triggered.connect(lambda: self._perform_manual_update(p_uuid, p_name))
            menu.addAction(action_update)
            
            menu.addSeparator()
            
            action_edit = QAction("📝 修改專案...", menu)
            action_edit.triggered.connect(lambda: self._perform_edit_project(p_uuid, p_name))
            menu.addAction(action_edit)
            
            menu.addSeparator()
            
            action_delete = QAction("🗑️ 刪除此專案...", menu)
            action_delete.triggered.connect(lambda: self._perform_delete_project([(p_uuid, p_name)]))
            menu.addAction(action_delete)
            
        else:
            # 多選邏輯 (只允許批量刪除，避免邏輯複雜化)
            # 收集所有選取的 (uuid, name)
            targets = []
            for index in selection:
                row = index.row()
                # [修正] 防禦性寫法：先取出 item，檢查是否存在
                item_u = self.project_table.item(row, 0)
                item_n = self.project_table.item(row, 1)
                
                # 只有當兩個格子都有東西時，才取文字
                if item_u and item_n:
                    targets.append((item_u.text(), item_n.text()))
            
            label_text = f"🗑️ 批量刪除 ({count} 個專案)..."
            action_batch_delete = QAction(label_text, menu)
            # 傳遞列表給刪除函式
            action_batch_delete.triggered.connect(lambda: self._perform_delete_project(targets))
            menu.addAction(action_batch_delete)

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

    def _perform_delete_project(self, targets: list[tuple[str, str]]) -> None:
        """執行刪除專案 (支援單刪與批刪)"""
        count = len(targets)
        if count == 0: return

        # 1. 構建確認訊息
        if count == 1:
            uuid, name = targets[0]
            msg_title = "確認刪除"
            msg_body = f"您確定要刪除專案「{name}」嗎？"
        else:
            names = "\n".join([f"- {t[1]}" for t in targets[:5]]) # 最多顯示前5個名字
            if count > 5: names += "\n...等"
            msg_title = f"確認批量刪除 ({count} 個)"
            msg_body = f"您確定要刪除以下 {count} 個專案嗎？\n\n{names}"

        msg_body += "\n\n這將會停止哨兵並移除設定 (檔案保留)。"

        # 2. 彈出確認
        reply = QMessageBox.question(
            self, msg_title, msg_body,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        # 3. 執行刪除循環
        success_count = 0
        errors = []
        
        self._set_status_message(f"正在刪除 {count} 個專案...", level="info")
        QApplication.processEvents()

        for uuid, name in targets:
            try:
                adapter.delete_project(uuid)
                success_count += 1
            except Exception as e:
                errors.append(f"{name}: {str(e)}")

        # 4. 結果回饋與刷新
        self._reload_projects_from_backend()
        self._update_detail_panel(None) # 清空詳情避免殘留

        if len(errors) == 0:
            self._set_status_message(f"✓ 成功刪除 {success_count} 個專案。", level="success")
        else:
            err_msg = "\n".join(errors)
            QMessageBox.critical(self, "部分刪除失敗", f"成功: {success_count}\n失敗: {len(errors)}\n\n錯誤詳情:\n{err_msg}")
            self._set_status_message(f"刪除完成，但有 {len(errors)} 個失敗。", level="error")

# 我們用「def」來定義（define）執行編輯專案函式。
    def _perform_edit_project(self, uuid: str, name: str) -> None:
        """打開編輯視窗，並呼叫後端修改專案。"""

        # 在打開編輯視窗前，強制從後端讀取最新狀態，防止「殘影」
        self._reload_projects_from_backend()

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
            
            # 檢查即時變更日誌
            logs = dialog.change_log
            
            if not changes and not logs:
                self._set_status_message("沒有任何變更，已取消操作。", level="info")
                return
            
            # 準備成功訊息
            success_msg = "✓ 專案已更新"
            if logs:
                # 將日誌串接起來顯示 (最多顯示 3 筆，太多就省略)
                details = ", ".join(logs[:3])
                if len(logs) > 3: details += f" ...等 {len(logs)} 項"
                success_msg += f" ({details})"
            
            if not changes and logs:
                self._set_status_message(success_msg, level="success")
                self._reload_projects_from_backend()
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
    
    # --- 實作無邊框視窗的拖曳功能 ---
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if self.old_pos:
            delta = event.globalPosition().toPoint() - self.old_pos
            # 注意：這裡是移動父容器 (SentryTrayAppV2.container)
            # 因為 DashboardWidget 只是 container 裡的一頁
            self.window().move(self.window().pos() + delta)
            self.old_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        self.old_pos = None


# ==========================================
#   View B: 模擬「控制台」 (Dashboard)
# ==========================================
# 我們用「class」來 定義（define）一個模擬的視圖 B。
class MockViewB(QWidget):
    def __init__(self, switch_callback):
        super().__init__()
        # 設定（set）背景為白色，字體為黑色，模擬「控制台」的亮色風格。
        self.setStyleSheet("background-color: white; color: black;")
        
        layout = QVBoxLayout(self)
        
        # 顯示標題
        label = QLabel("View B: 控制台 (Legacy List)")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)
        
        # 測試按鈕：返回眼睛
        btn_back = QPushButton("↩ 返回哨兵之眼")
        # 當按鈕被點擊（clicked）時，執行切換回調。
        btn_back.clicked.connect(switch_callback)
        layout.addWidget(btn_back)

# ==========================================
#   主控制器：v2.0 托盤應用程式
# ==========================================
class SentryTrayAppV2:
    def update_tooltip(self, running: int, muting: int) -> None:
        """更新托盤圖示的 Tooltip 顯示狀態，並檢查循環依賴。"""
        # [DEFENSE] 檢查 self.tray_icon 是否已經被初始化，防止 Dashboard 在載入時提前呼叫導致 AttributeError。
        if not hasattr(self, 'tray_icon') or self.tray_icon is None:
            return

        # 我們用「if...else」判斷狀態並組合（concatenate）字串。
        if running == 0 and muting == 0:
            msg = "Sentry: 目前無監控"
        else:
            msg = f"Sentry: {running} 個監控中"
            if muting > 0:
                msg += f" / {muting} 個靜默中"
        
        self.tray_icon.setToolTip(msg)
    def __init__(self, app: QApplication):
        self.app = app
        
        # --- 1. 建立托盤圖示 ---
        self.tray_icon = QSystemTrayIcon(self._load_icon(), self.app)
        
        # 建立右鍵選單
        menu = QMenu()
        # 建立「顯示/隱藏」動作
        action_show = QAction("顯示/隱藏視窗", menu)
        action_show.triggered.connect(self.toggle_window)
        menu.addAction(action_show)
        
        # 建立「退出」動作
        action_quit = QAction("退出 Sandbox", menu)
        action_quit.triggered.connect(self.app.quit)
        
        menu.addAction(action_quit)
        self.tray_icon.setContextMenu(menu)
        
        # 左鍵點擊托盤也觸發切換
        self.tray_icon.activated.connect(self._on_tray_activated)
        
        self.tray_icon.show()

        # --- 2. 建立雙視圖容器 ---
        # 我們建立（create）一個堆疊容器，它可以像紙牌一樣切換頁面。
        self.container = QStackedWidget()
        self.container.setWindowTitle("Sentry v2.0 Sandbox")
        self.container.resize(900, 600)

        # 建立兩個視圖，並傳入「切換頁面」的函式作為參數。
        self.view_a = SentryEyeWidget(switch_callback=self.go_to_dashboard)        
        # 替換為我們剛剛貼入並改名的 DashboardWidget
        # 這裡我們傳入了 self.go_to_eye 函式作為返回按鈕的回調
        # type: ignore # 【技術鎮壓】忽略 Pylance 對 update_tooltip 的循環依賴警告
        self.view_b = DashboardWidget(on_stats_change=lambda r, m: self.update_tooltip(r, m), switch_callback=self.go_to_eye)
        # 把視圖加入（addWidget）容器中。
        # 索引 0 = View A
        self.container.addWidget(self.view_a)
        # 索引 1 = View B
        self.container.addWidget(self.view_b)

        # --- 改成呼叫 go_to_eye() 來初始化 ---
        # 這會同時設定頁面並將視窗縮小為 130x130
        self.go_to_eye()

        # 啟動時直接顯示視窗
        self.container.show()

        # 設定容器視窗屬性以支援透明背景
        self.container.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.container.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)

    def go_to_dashboard(self):
        """切換到 View B (展開)"""
        # 1. 命令 View B 重新去後端拉取最新資料
        self.view_b._reload_projects_from_backend()
        # 2. 切換頁面
        self.container.setCurrentIndex(1)
        # 3. [新增] 展開視窗為後台尺寸
        self.container.resize(900, 600)
    
    def go_to_eye(self):
        """切換到 View A (縮微)"""
        # 1. 切換頁面
        self.container.setCurrentIndex(0)
        # 2. [新增] 縮小視窗為眼球尺寸
        self.container.resize(130, 130)

    def toggle_window(self):
        """切換視窗顯示狀態"""
        if self.container.isVisible():
            self.container.hide()
        else:
            self.container.show()
            self.container.activateWindow()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.toggle_window()

    def _load_icon(self) -> QIcon:
        """從 assets/icons/tray_icon.png 載入圖示"""
        # 我們計算（calculate）專案根目錄位置 (往上找兩層：src -> root)
        root = Path(__file__).resolve().parents[2]
        icon_path = root / "assets" / "icons" / "tray_icon.png"

        # 我們用「if」檢查檔案是否存在
        if icon_path.is_file():
            return QIcon(str(icon_path))
        
        # 如果找不到，回傳系統預設圖示當作備案
        return self.app.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)

# --- 程式進入點 ---
def main():
    app = QApplication(sys.argv)
    # 這是為了確保關閉視窗時不會直接殺死程式 (因為有 Tray)。
    app.setQuitOnLastWindowClosed(False)
    
    # 啟動 v2 沙盒
    sandbox = SentryTrayAppV2(app)
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()

    #  啟動系統 python -m src.tray.v2_sandbox