# src/backend/adapter.py

# 這裡，我們用「from __future__ import annotations」來確保所有的型別提示（annotations）
# 都以字串的形式處理，這是一個為了未來 Python 版本相容性的預備動作。
from __future__ import annotations

# 導入（import）dataclass 工具，方便建立只有資料的類別（不需要寫 __init__）。
from dataclasses import dataclass, field
# 導入（import）路徑處理（pathlib）中的 Path 工具。
from pathlib import Path
# 導入（import）類型提示（typing）中的 Literal（字面量）、List（列表）、Dict（字典）和 Optional（可選的）。
from typing import Literal, List, Dict, Optional

# 導入（import）json 模組，用於讀取和寫入 JSON 格式的設定檔。
import json


# ============================
#  型別定義（給 tray_app 使用）
# ============================

# 這裡，我們用 Literal 來定義（define）專案狀態（ProjectStatus）的類型，
# 它只能是 "monitoring"（監控中）或 "stopped"（已停止）其中之一。
ProjectStatus = Literal["monitoring", "stopped"]
# 定義（define）專案模式（ProjectMode）的類型，它只能是 "silent"（靜默）或 "interactive"（互動）其中之一。
ProjectMode = Literal["silent", "interactive"]

# ============================
#  例外型別（給 tray_app 使用）
# ============================

# 這裡，我們用「class」來定義（define）一個新的錯誤類型（BackendError），
# 讓它可以繼承（Exception）Python 內建的例外處理機制。
class BackendError(Exception):
    # 這個註釋（"""..."""）是說明文件，解釋這個錯誤類型的作用。
    """
    UI 專用的後端錯誤封裝。

    - 目前 stub 版本只用來在 adapter / tray_app 之間傳遞錯誤訊息。
    - 未來若接上真正的 Laplace Sentry daemon，可以在這裡加上
    error_code / kind 等欄位，統一映射 daemon 傳回的錯誤。
    """
    # 這裡用 pass 意思是不需要為這個錯誤類型添加額外的程式碼。
    pass


# 這裡，我們用「@dataclass」標記（mark）這是一個資料類別（只有數據）。
@dataclass
class ProjectInfo:
    """
    給 UI 用的專案資訊：
    - name / status / mode：tray_app 目前已經在使用
    - path / output_file / target_files：從 projects.json 讀出的真實欄位
    """
    # 這是專案的唯一識別碼（uuid），型別是字串（str）。
    uuid: str
    # 專案名稱（name），型別是字串（str）。
    name: str
    # 專案狀態（status），型別是我們上面定義的 ProjectStatus。
    status: ProjectStatus
    # 專案模式（mode），型別是我們上面定義的 ProjectMode。
    mode: ProjectMode
    # 專案的路徑（path），預設（= ""）是空字串。
    path: str = ""
    # 輸出檔案的路徑列表（output_file），預設是空的列表（用 default_factory=list）。
    # 我們這裡用「列表（List）」來指代「空籃子」。
    output_file: List[str] = field(default_factory=list)
    # 目標監控檔案的路徑列表（target_files），預設是空的列表（用 default_factory=list）。
    target_files: List[str] = field(default_factory=list)


# 這裡，我們用「@dataclass」標記（mark）這是忽略設定的資料類別。
@dataclass
class IgnoreSettings:
    # 哨兵忽略的樣式列表（List[str]）。
    sentry_ignore_patterns: List[str]
    # 目錄樹的深度限制（int），型別是整數。
    tree_depth_limit: int

# ============================
#  內部用模型（真實 projects.json）
# ============================
# 這裡，我們用「@dataclass」標記（mark）這是一個資料類別，
# 用於內部（前面帶 _），代表從 projects.json 讀出來的**原始專案資料**。
@dataclass
class _RawProject:
    # 這是專案的唯一識別碼（uuid）。
    uuid: str
    # 專案名稱。
    name: str
    # 專案路徑。
    path: str
    # 輸出檔案的路徑列表（List[str]）。
    output_file: List[str]
    # 目標監控檔案的列表。
    target_files: List[str]


# 這裡，我們用「@dataclass」標記（mark）這是一個資料類別，
# 用於內部（前面帶 _），代表專案**目前執行的狀態**（例如：有沒有在監控）。
@dataclass
class _RuntimeState:
    # 預設狀態（status）是「monitoring」（監控中）。
    status: ProjectStatus = "monitoring"
    # 預設模式（mode）是「silent」（靜默）。
    mode: ProjectMode = "silent"


# ============================
#  Adapter 本體（封裝真實資料）
# ============================


# 這裡，我們用「class」來定義（define）Adapter 類別，它負責所有後端資料的溝通。
class BackendAdapter:
    # 這個註釋（"""..."""）是說明文件，解釋這個類別的作用。
    """
    Adapter v0.9.2

    - 讀取真實 projects.json（Laplace Sentry Control）
    - 內部使用 _RawProject + _RuntimeState
    - 對外提供 ProjectInfo / list_projects / toggle_project_status / get_ignore_settings
    """

    # 這裡，我們用「def」來定義（define）Adapter 物件被建立時會自動執行的函式（__init__）。
    def __init__(self, json_path: str | Path) -> None:
        # 將設定檔的路徑（json_path）存入實例變數。
        self.json_path = Path(json_path)

        # 真實的 projects.json → _RawProject
        # 建立一個叫 _projects 的「空籃子」（List[_RawProject]），用來存放所有原始專案資料。
        self._projects: List[_RawProject] = []

        # 虛擬 runtime 狀態（uuid -> 狀態）
        # 建立一個叫 _runtime 的「有標籤的盒子」（Dict），用來存放專案的執行狀態。
        # 標籤（key）是 uuid，盒子裡面的內容（value）是 _RuntimeState 物件。
        self._runtime: Dict[str, _RuntimeState] = {}

        # 暫時寫死（之後可改成可編輯）
        # # TODO: 這裡之後要改成可編輯的設定。
        # 建立一個忽略設定（IgnoreSettings）物件，並暫時給定寫死的預設值。
        self._ignore_settings = IgnoreSettings(
            sentry_ignore_patterns=["*.tmp", "*.log"],
            tree_depth_limit=3,
        )

        # 呼叫（call）_load_projects_json 函式，開始從 JSON 檔案中載入資料。
        self._load_projects_json()

    # ---------------------------------------------------------
    # 讀取 projects.json
    # ---------------------------------------------------------

    # 這裡，我們用「def」來定義（define）載入 JSON 專案列表的函式。
    def _load_projects_json(self) -> None:
        """從 json 檔載入專案列表，填入 _projects 與 _runtime。"""
        # 讀取（read_text）JSON 檔案的全部內容，並指定編碼（encoding="utf-8"）。
        text = self.json_path.read_text(encoding="utf-8")
        # 呼叫（call）json.loads 函式，把 JSON 格式的文字轉換成 Python 的列表或字典（raw_items）。
        raw_items = json.loads(text)

        # 清空（clear）舊有的專案列表「空籃子」（_projects）。
        self._projects.clear()

        # # DEFENSE: 這裡用 DEFENSE 標籤標註，這是防呆檢查。
        # 用「if」來判斷：如果（if）讀進來的不是一個列表（list）...
        if not isinstance(raw_items, list):
            # 就用「return」結束這個載入函式。
            return

        # 我們用「for...in...」這個結構，來一個一個地（for）處理 JSON 列表中的每一個項目（item）。
        for item in raw_items:
            # # DEFENSE: 這裡再次防呆，檢查項目是不是一個字典（dict）。
            # 用「if」來判斷：如果（if）項目不是字典...
            if not isinstance(item, dict):
                # 就用「continue」跳過這一個項目，處理下一個。
                continue

            # 從字典（item）中獲取（get）uuid 欄位的值，如果沒有就用空字串，並強制轉成字串。
            uuid = str(item.get("uuid") or "")
            # 獲取 name 欄位的值。
            name = str(item.get("name") or "")
            # 獲取 path 欄位的值。
            path = str(item.get("path") or "")

            # 獲取 output_file 欄位的值，如果沒有就用空列表（[]）。
            output_file = item.get("output_file") or []
            # 獲取 target_files 欄位的值。
            target_files = item.get("target_files") or []

            # # DEFENSE: 檢查必要的欄位 uuid 和 name 是否為空。
            # 用「if」來判斷：如果（if）uuid 或 name 是空的...
            if not uuid or not name:
                # 就用「continue」跳過這一個專案。
                continue

            # # DEFENSE: 確保 output_file 是列表，不是的話就給它一個空列表。
            if not isinstance(output_file, list):
                output_file = []
            # # DEFENSE: 確保 target_files 是列表，不是的話就給它一個空列表。
            if not isinstance(target_files, list):
                target_files = []

            # 建立（instantiate）一個 _RawProject 物件，把讀到的所有資料傳入。
            # list(map(str, ...)) 是為了確保列表裡面的每個元素都是字串。
            proj = _RawProject(
                uuid=uuid,
                name=name,
                path=path,
                output_file=list(map(str, output_file)),
                target_files=list(map(str, target_files)),
            )
            # 把新的 _RawProject 物件加入（append）到 _projects 列表（空籃子）中。
            self._projects.append(proj)

            # 給新專案預設 runtime 狀態
            # 用「if」來判斷：如果（if）這個專案的 uuid 不在 runtime 盒子（_runtime）裡面...
            if uuid not in self._runtime:
                # 就建立一個預設的 _RuntimeState() 物件，並用 uuid 作為標籤（key）放進盒子。
                self._runtime[uuid] = _RuntimeState()

# ---------------------------------------------------------
    # 內部：把 _RawProject + _RuntimeState → ProjectInfo
    # ---------------------------------------------------------

    # 這裡，我們用「def」來定義（define）內部轉換函式，把兩種內部資料結構成為 UI 用的 ProjectInfo。
    def _to_project_info(self, raw: _RawProject) -> ProjectInfo:
        # 從 runtime 盒子（_runtime）中，用 uuid 標籤（raw.uuid）取出狀態。
        # 如果沒找到（get() 的結果是 None），就給它一個預設的 _RuntimeState()。
        state = self._runtime.get(raw.uuid) or _RuntimeState()
        # 建立（return）並回傳（return）一個 ProjectInfo 物件。
        return ProjectInfo(
            # uuid 和 name 直接從原始資料（raw）中複製。
            uuid=raw.uuid,
            name=raw.name,
            # status 和 mode 從狀態資料（state）中獲取。
            status=state.status,
            mode=state.mode,
            # 其餘欄位也從原始資料（raw）中複製。
            path=raw.path,
            output_file=list(raw.output_file),
            target_files=list(raw.target_files),
        )

    # ---------------------------------------------------------
    # 給 UI 用的介面（instance 版本）
    # ---------------------------------------------------------

    # 這裡，我們用「def」來定義（define）對外提供的專案列表獲取函式。
    def list_projects(self) -> List[ProjectInfo]:
        """回傳目前所有專案的 UI 資訊。"""
        # 使用列表生成式（list comprehension）
        # 循環（for）_projects 籃子中的每一個原始專案（p），
        # 然後呼叫（call）_to_project_info 函式進行轉換，
        # 最後回傳（return）由 ProjectInfo 物件組成的列表。
        return [self._to_project_info(p) for p in self._projects]

    # 這裡，我們用「def」來定義（define）切換專案狀態的函式。
    def toggle_project_status(self, project_name: str) -> Optional[ProjectInfo]:
        """
        依照專案名稱切換監控狀態：
        - 若找到：切換 monitoring/stopped，回傳更新後的 ProjectInfo
        - 若沒找到：回傳 None
        """
        # 預設目標原始專案（target_raw）是空的（None）。
        target_raw: Optional[_RawProject] = None

        # 我們用「for...in...」這個結構，來一個一個地（for）檢查 _projects 籃子中的專案。
        for raw in self._projects:
            # 用「if」來判斷：如果（if）原始專案的名稱（raw.name）等於（==）傳入的名稱...
            if raw.name == project_name:
                # 找到目標了，把這個原始專案物件存到 target_raw。
                target_raw = raw
                # 用「break」跳出（exit）這個 for 循環。
                break

        # 用「if」來判斷：如果（if）target_raw 還是空的（None）...
        if target_raw is None:
            # 就回傳（return） None，表示找不到專案。
            return None

        # 從 runtime 盒子（_runtime）中獲取（get）目標專案的狀態。
        state = self._runtime.get(target_raw.uuid)
        # 用「if」來判斷：如果（if）狀態是空的（None）（理論上不該發生）...
        if state is None:
            # 就建立一個預設狀態。
            state = _RuntimeState()
            # 並把這個新狀態用 uuid 標籤放回 runtime 盒子中。
            self._runtime[target_raw.uuid] = state

        # 核心切換邏輯：
        # 用「= ... if ... else ...」來判斷並賦值：
        # 如果（if）狀態是 "monitoring"，就設定為 "stopped"，否則（else）設定為 "monitoring"。
        state.status = "stopped" if state.status == "monitoring" else "monitoring"
        # 呼叫（call）_to_project_info 函式，把更新後的狀態轉成 ProjectInfo，並回傳（return）。
        return self._to_project_info(target_raw)

    # 這裡，我們用「def」來定義（define）獲取忽略設定的函式。
    def get_ignore_settings(self) -> IgnoreSettings:
        # 直接回傳（return）初始化時設定的忽略設定物件（_ignore_settings）。
        return self._ignore_settings
    

    def add_project(self, name: str, path: str, output_file: str) -> None:
        """
        【Stub 版本】

        - 目前僅負責記錄「新增專案請求」的參數，不會修改 projects.json。
        - 未來若要接上真正的 Laplace Sentry daemon，可以在這裡呼叫
        CLI / RPC，並根據結果決定是否拋出 BackendError。
        """
        name = (name or "").strip()
        path = (path or "").strip()
        output_file = (output_file or "").strip()

        # 最基本的防呆檢查（避免 UI 傳完全空白的東西進來）
        if not name:
            raise BackendError("【新增失敗】：專案名稱不得為空。")
        if not path:
            raise BackendError("【新增失敗】：專案資料夾路徑不得為空。")
        if not output_file:
            raise BackendError("【新增失敗】：寫入檔路徑不得為空。")

        # ✅ B-2 要求：「先 print，不寫檔」
        print(
            f"[backend_adapter stub] add_project("
            f"name={name!r}, path={path!r}, output_file={output_file!r})"
        )

        # ⚠ 目前不修改 self._projects / self._runtime，也不寫回 json 檔。
        #    真正的新增行為會在未來改為：
        #    - 呼叫 Laplace Sentry daemon 的 add_project 命令
        #    - 再重新載入 projects.json


# ============================
#  模組層：給 tray_app 使用的單例介面
# ============================

# 單例 adapter（懶載入）
# 建立一個叫 _adapter_singleton 的變數，預設是空的（Optional[BackendAdapter] = None）。
# 之後整個應用程式只會建立這一個 Adapter 物件。
_adapter_singleton: Optional[BackendAdapter] = None


# 這裡，我們用「def」來定義（define）確保 Adapter 物件已經被建立的函式。
def _ensure_adapter() -> BackendAdapter:
    # 宣告（global）我們要修改這個全域變數 _adapter_singleton。
    global _adapter_singleton
    # 用「if」來判斷：如果（if）它已經被建立了（不是 None）...
    if _adapter_singleton is not None:
        # 就直接回傳（return）現有的物件。
        return _adapter_singleton

    # ⚠ 這條路徑依照你目前 WSL / 專案路徑寫死
    # 這裡，我們用 Path 工具來定義（define）projects.json 的**絕對路徑**。
    # 這是基於您的個人化配置（WSL2）來寫死的路徑。
    json_path = Path(
        r"\\wsl.localhost\Ubuntu\home\serpal\My_Python_Projects\laplace_sentry_control_v2\data\projects.json"
    )

    # 建立（instantiate）BackendAdapter 物件，把路徑傳入。
    _adapter_singleton = BackendAdapter(json_path)
    # 回傳（return）這個新建立的物件。
    return _adapter_singleton


# 這裡，我們用「def」來定義（define）對外提供的獲取專案列表函式。
def list_projects() -> List[ProjectInfo]:
    """
    tray_app 期待的介面：
    - 回傳 List[ProjectInfo]
    - ProjectInfo 內含 name/status/mode/path/output_file/target_files
    """
    # 呼叫（call）_ensure_adapter 函式，獲取 Adapter 物件。
    adapter = _ensure_adapter()
    # 呼叫（call）Adapter 內部的 list_projects 函式並回傳結果。
    return adapter.list_projects()


# 這裡，我們用「def」來定義（define）對外提供的切換專案狀態函式。
def toggle_project_status(key: str) -> Optional[ProjectInfo]:
    """
    tray_app 期待的介面：
    - key 可以是 uuid 或 name（過渡期）
    """
    # 呼叫（call）_ensure_adapter 函式，獲取 Adapter 物件。
    adp = _ensure_adapter()

    # 先試 uuid
    # 我們用「for...in...」這個結構，來一個一個地（for）檢查 Adapter 內部（_projects）。
    for raw in adp._projects:
        # 用「if」來判斷：如果（if）原始專案的 uuid 等於（==）傳入的 key...
        if raw.uuid == key:
            # 就呼叫（call）Adapter 內部的 toggle_project_status，並回傳（return）結果。
            # 這裡傳入的是 name，因為 Adapter 內部是以 name 來判斷的（過渡期邏輯）。
            return adp.toggle_project_status(raw.name)

    # 否則 fallback 成舊行為（靠 name）
    # 如果上面 for 循環沒有找到 uuid，就回到原本的行為：直接用 key（name）去切換狀態。
    return adp.toggle_project_status(key)


# 這裡，我們用「def」來定義（define）對外提供的獲取忽略設定函式。
def get_ignore_settings() -> IgnoreSettings:
    """
    tray_app 期待的介面：
    - 回傳 IgnoreSettings（sentry_ignore_patterns, tree_depth_limit）
    """
    # 呼叫（call）_ensure_adapter 函式，獲取 Adapter 物件。
    adapter = _ensure_adapter()
    # 呼叫（call）Adapter 內部的 get_ignore_settings 函式並回傳結果。
    return adapter.get_ignore_settings()

# 這裡，我們用「def」來定義（define）對外提供的新增專案函式（目前是 stub）。
def add_project(name: str, path: str, output_file: str) -> None:
    """
    tray_app 期待的介面（stub 版本）：

    - 目前只會呼叫 BackendAdapter.add_project(...)
    - add_project 內部只會做參數檢查 + print，不會改變 projects.json
    """
    # 呼叫（call）_ensure_adapter 函式，獲取 Adapter 物件。
    adapter = _ensure_adapter()
    # 呼叫（call）Adapter 內部的 add_project 函式。
    return adapter.add_project(name, path, output_file)

# ============================
# Demo（可直接 python -m src.backend.adapter）
# ============================

# 這裡，我們用「def」來定義（define）一個用於測試的示範（demo）函式。
def _demo() -> None:
    # 呼叫（call）_ensure_adapter 函式，獲取 Adapter 物件。
    adp = _ensure_adapter()

    # 用「print」輸出（output）標題。
    print("\n=== backend_adapter demo ===")
    print("目前專案列表：")
    
    # 我們用「for...in...」這個結構，來一個一個地（for）處理所有專案。
    for proj in adp.list_projects():
        # 用「print」格式化輸出每個專案的名稱、狀態和模式。
        # {proj.name:28s} 是指用 28 個字元來顯示 name，並靠左對齊。
        print(
            f"- {proj.name:28s} | status={proj.status:10s} | mode={proj.mode:11s}"
        )

    # 用「if」來判斷：如果（if）專案列表裡面有東西（不是空的）...
    if adp.list_projects():
        # 獲取（get）第一個專案的名稱。
        name = adp.list_projects()[0].name
        print(f"\n切換 {name} 狀態...")
        
        # 呼叫（call）toggle_project_status 函式來切換狀態。
        updated = adp.toggle_project_status(name)
        # 輸出切換後的專案資訊。
        print("切換後：", updated)

    # 輸出（output）目前的忽略設定。
    print("\n忽略設定：", adp.get_ignore_settings())


# 這是 Python 標準的寫法：如果（if）這個檔案是直接執行的主程式...
if __name__ == "__main__":
    # 就呼叫（call）_demo 函式來執行測試。
    _demo()