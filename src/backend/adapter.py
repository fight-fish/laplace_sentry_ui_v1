# src/backend/adapter.py

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, List, Dict, Optional

import json


# ============================
#  型別定義（給 tray_app 使用）
# ============================

ProjectStatus = Literal["monitoring", "stopped"]
ProjectMode = Literal["silent", "interactive"]


@dataclass
class ProjectInfo:
    """
    給 UI 用的專案資訊：
    - name / status / mode：tray_app 目前已經在使用
    - path / output_files / target_files：從 projects.json 讀出的真實欄位
    """

    name: str
    status: ProjectStatus
    mode: ProjectMode
    path: str = ""
    output_files: List[str] = field(default_factory=list)
    target_files: List[str] = field(default_factory=list)


@dataclass
class IgnoreSettings:
    sentry_ignore_patterns: List[str]
    tree_depth_limit: int


# ============================
#  內部用模型（真實 projects.json）
# ============================

@dataclass
class _RawProject:
    uuid: str
    name: str
    path: str
    output_files: List[str]
    target_files: List[str]


@dataclass
class _RuntimeState:
    status: ProjectStatus = "monitoring"
    mode: ProjectMode = "silent"


# ============================
#  Adapter 本體（封裝真實資料）
# ============================


class BackendAdapter:
    """
    Adapter v0.9.2

    - 讀取真實 projects.json（Laplace Sentry Control）
    - 內部使用 _RawProject + _RuntimeState
    - 對外提供 ProjectInfo / list_projects / toggle_project_status / get_ignore_settings
    """

    def __init__(self, json_path: str | Path) -> None:
        self.json_path = Path(json_path)

        # 真實的 projects.json → _RawProject
        self._projects: List[_RawProject] = []

        # 虛擬 runtime 狀態（uuid -> 狀態）
        self._runtime: Dict[str, _RuntimeState] = {}

        # 暫時寫死（之後可改成可編輯）
        self._ignore_settings = IgnoreSettings(
            sentry_ignore_patterns=["*.tmp", "*.log"],
            tree_depth_limit=3,
        )

        self._load_projects_json()

    # ---------------------------------------------------------
    # 讀取 projects.json
    # ---------------------------------------------------------

    def _load_projects_json(self) -> None:
        """從 json 檔載入專案列表，填入 _projects 與 _runtime。"""
        text = self.json_path.read_text(encoding="utf-8")
        raw_items = json.loads(text)

        self._projects.clear()

        if not isinstance(raw_items, list):
            return

        for item in raw_items:
            if not isinstance(item, dict):
                continue

            uuid = str(item.get("uuid") or "")
            name = str(item.get("name") or "")
            path = str(item.get("path") or "")

            output_files = item.get("output_file") or []
            target_files = item.get("target_files") or []

            if not uuid or not name:
                continue

            if not isinstance(output_files, list):
                output_files = []
            if not isinstance(target_files, list):
                target_files = []

            proj = _RawProject(
                uuid=uuid,
                name=name,
                path=path,
                output_files=list(map(str, output_files)),
                target_files=list(map(str, target_files)),
            )
            self._projects.append(proj)

            # 給新專案預設 runtime 狀態
            if uuid not in self._runtime:
                self._runtime[uuid] = _RuntimeState()

    # ---------------------------------------------------------
    # 內部：把 _RawProject + _RuntimeState → ProjectInfo
    # ---------------------------------------------------------

    def _to_project_info(self, raw: _RawProject) -> ProjectInfo:
        state = self._runtime.get(raw.uuid) or _RuntimeState()
        return ProjectInfo(
            name=raw.name,
            status=state.status,
            mode=state.mode,
            path=raw.path,
            output_files=list(raw.output_files),
            target_files=list(raw.target_files),
        )

    # ---------------------------------------------------------
    # 給 UI 用的介面（instance 版本）
    # ---------------------------------------------------------

    def list_projects(self) -> List[ProjectInfo]:
        """回傳目前所有專案的 UI 資訊。"""
        return [self._to_project_info(p) for p in self._projects]

    def toggle_project_status(self, project_name: str) -> Optional[ProjectInfo]:
        """
        依照專案名稱切換監控狀態：
        - 若找到：切換 monitoring/stopped，回傳更新後的 ProjectInfo
        - 若沒找到：回傳 None
        """
        target_raw: Optional[_RawProject] = None

        for raw in self._projects:
            if raw.name == project_name:
                target_raw = raw
                break

        if target_raw is None:
            return None

        state = self._runtime.get(target_raw.uuid)
        if state is None:
            state = _RuntimeState()
            self._runtime[target_raw.uuid] = state

        state.status = "stopped" if state.status == "monitoring" else "monitoring"
        return self._to_project_info(target_raw)

    def get_ignore_settings(self) -> IgnoreSettings:
        return self._ignore_settings


# ============================
#  模組層：給 tray_app 使用的單例介面
# ============================

# 單例 adapter（懶載入）
_adapter_singleton: Optional[BackendAdapter] = None


def _ensure_adapter() -> BackendAdapter:
    global _adapter_singleton
    if _adapter_singleton is not None:
        return _adapter_singleton

    # ⚠ 這條路徑依照你目前 WSL / 專案路徑寫死
    json_path = Path(
        r"\\wsl.localhost\Ubuntu\home\serpal\My_Python_Projects\laplace_sentry_control_v2\data\projects.json"
    )

    _adapter_singleton = BackendAdapter(json_path)
    return _adapter_singleton


def list_projects() -> List[ProjectInfo]:
    """
    tray_app 期待的介面：
    - 回傳 List[ProjectInfo]
    - ProjectInfo 內含 name/status/mode/path/output_files/target_files
    """
    adapter = _ensure_adapter()
    return adapter.list_projects()


def toggle_project_status(project_name: str) -> Optional[ProjectInfo]:
    """
    tray_app 期待的介面：
    - 以 name 為 key 切換監控狀態
    """
    adapter = _ensure_adapter()
    return adapter.toggle_project_status(project_name)


def get_ignore_settings() -> IgnoreSettings:
    """
    tray_app 期待的介面：
    - 回傳 IgnoreSettings（sentry_ignore_patterns, tree_depth_limit）
    """
    adapter = _ensure_adapter()
    return adapter.get_ignore_settings()


# ============================
# Demo（可直接 python -m src.backend.adapter）
# ============================

def _demo() -> None:
    adp = _ensure_adapter()

    print("\n=== backend_adapter demo ===")
    print("目前專案列表：")
    for proj in adp.list_projects():
        print(
            f"- {proj.name:28s} | status={proj.status:10s} | mode={proj.mode:11s}"
        )

    if adp.list_projects():
        name = adp.list_projects()[0].name
        print(f"\n切換 {name} 狀態...")
        updated = adp.toggle_project_status(name)
        print("切換後：", updated)

    print("\n忽略設定：", adp.get_ignore_settings())


if __name__ == "__main__":
    _demo()
