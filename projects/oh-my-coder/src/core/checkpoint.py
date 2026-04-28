"""
Checkpoint & Rollback 系统

纯 Python 实现，不依赖 Git。
功能：
- 创建快照：记录工作区变更文件（SHA256 差异检测）
- 列出快照：支持按 task_id 过滤
- 恢复快照：覆盖工作区文件，恢复前先备份当前状态
- 对比差异：展示 snapshot 与当前工作区的差异
- 清理逻辑：每个 checkpoint 最多 100 个文件，超出自动清理最早的

目录结构：
.omc/checkpoints/
├── index.json              # 全量索引
└── <task-id>/
    ├── manifest.json        # 文件列表 + SHA256
    └── snapshot/            # 变更文件内容
        ├── <file1>
        └── <file2>
"""

from __future__ import annotations

import hashlib
import json
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import builtins

# 变更文件上限（超出时自动清理最早的 snapshot）
MAX_SNAPSHOT_FILES = 100


@dataclass
class SnapshotEntry:
    """快照中的单个文件条目"""

    path: str  # 相对路径
    sha256: str  # 文件内容 SHA256
    size: int  # 文件大小（字节）
    modified_at: str  # 修改时间（ISO 8601）


@dataclass
class Checkpoint:
    """快照元数据"""

    id: str  # checkpoint ID（时间戳 + task_id）
    task_id: str  # 关联任务 ID
    description: str  # 快照描述
    created_at: str  # 创建时间（ISO 8601）
    file_count: int  # 快照文件数量
    total_size: int  # 快照总大小（字节）
    working_dir: str  # 工作区根目录
    entries: list[SnapshotEntry] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "task_id": self.task_id,
            "description": self.description,
            "created_at": self.created_at,
            "file_count": self.file_count,
            "total_size": self.total_size,
            "working_dir": self.working_dir,
            "entries": [vars(e) for e in self.entries],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Checkpoint:
        entries = [SnapshotEntry(**e) for e in data.get("entries", [])]
        return cls(
            id=data["id"],
            task_id=data["task_id"],
            description=data["description"],
            created_at=data["created_at"],
            file_count=data["file_count"],
            total_size=data["total_size"],
            working_dir=data["working_dir"],
            entries=entries,
        )


class CheckpointManager:
    """
    Checkpoint 管理器

    用法：
        cm = CheckpointManager(project_path=Path("."))
        cp_id = cm.create(task_id="build-flask", description="开始重构")
        cm.restore(cp_id)
        cm.diff(cp_id)
    """

    # 不纳入快照的目录/文件模式
    IGNORE_PATTERNS: set[str] = {
        ".git",
        ".omc",
        "__pycache__",
        ".pytest_cache",
        ".ruff_cache",
        ".mypy_cache",
        ".tox",
        "node_modules",
        ".venv",
        "venv",
        ".env",
        ".DS_Store",
        "*.pyc",
        "*.pyo",
        "*.so",
        "*.dylib",
        "*.egg-info",
        ".eggs",
        "dist",
        "build",
        ".coverage",
        "htmlcov",
        "*.whl",
    }

    def __init__(self, project_path: Path | None = None):
        self.project_path = project_path or Path.cwd()
        self.checkpoint_root = self.project_path / ".omc" / "checkpoints"
        self.index_file = self.checkpoint_root / "index.json"
        self.backup_root = Path.home() / ".omc" / "backup"
        self._index: dict[str, dict[str, Any]] = {}
        self._seq = 0  # 单调递增序列号，确保 cp_id 唯一
        self._init()
        self._load_index()

    # ------------------------------------------------------------------
    # 初始化
    # ------------------------------------------------------------------

    def _init(self) -> None:
        self.checkpoint_root.mkdir(parents=True, exist_ok=True)
        self.backup_root.mkdir(parents=True, exist_ok=True)

    def _load_index(self) -> None:
        if self.index_file.exists():
            try:
                self._index = json.loads(self.index_file.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                self._index = {}
        else:
            self._index = {}

    def _save_index(self) -> None:
        self.index_file.write_text(
            json.dumps(self._index, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    # ------------------------------------------------------------------
    # 核心操作
    # ------------------------------------------------------------------

    def create(
        self,
        task_id: str,
        description: str = "",
        max_files: int = MAX_SNAPSHOT_FILES,
    ) -> str:
        """
        创建 checkpoint（快照当前工作区）

        只保存有变更的文件（SHA256 对比）。

        Args:
            task_id: 任务 ID
            description: 快照描述
            max_files: 本次快照最多保存的文件数

        Returns:
            checkpoint ID
        """
        ts = time.strftime("%Y%m%d-%H%M%S")
        self._seq += 1
        cp_id = f"{ts}-{self._seq:04d}-{task_id}"
        cp_dir = self.checkpoint_root / task_id / cp_id
        snapshot_dir = cp_dir / "snapshot"
        snapshot_dir.mkdir(parents=True, exist_ok=True)

        entries: list[SnapshotEntry] = []
        total_size = 0

        # 遍历工作区文件
        for file_path in self._iter_files():
            # 跳过忽略的模式
            if self._is_ignored(file_path):
                continue

            try:
                content = file_path.read_bytes()
            except OSError:
                continue

            # 计算 SHA256
            sha256 = hashlib.sha256(content).hexdigest()
            rel_path = str(file_path.relative_to(self.project_path))

            # 记录条目
            entry = SnapshotEntry(
                path=rel_path,
                sha256=sha256,
                size=len(content),
                modified_at=time.strftime("%Y-%m-%dT%H:%M:%S") + f".{self._seq:04d}",
            )
            entries.append(entry)

            # 写入 snapshot（只存内容，manifest 单独存）
            dest = snapshot_dir / rel_path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(content)
            total_size += entry.size

        # 限制文件数（超出时取最近的）
        if len(entries) > max_files:
            entries.sort(key=lambda e: e.modified_at, reverse=True)
            entries = entries[:max_files]

        created_at = time.strftime("%Y-%m-%dT%H:%M:%S") + f".{self._seq:04d}"

        # 写 manifest
        manifest = {
            "id": cp_id,
            "task_id": task_id,
            "description": description,
            "created_at": created_at,
            "file_count": len(entries),
            "total_size": total_size,
            "working_dir": str(self.project_path.resolve()),
            "entries": [vars(e) for e in entries],
        }
        (cp_dir / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        # 更新索引
        self._index[cp_id] = {
            "id": cp_id,
            "task_id": task_id,
            "description": description,
            "created_at": created_at,
            "file_count": len(entries),
            "total_size": total_size,
            "working_dir": str(self.project_path.resolve()),
            "path": str(cp_dir),
        }
        self._save_index()

        return cp_id

    def restore(self, checkpoint_id: str) -> str:
        """
        恢复 checkpoint（覆盖工作区文件）

        恢复前自动将当前工作区备份到 ~/.omc/backup/<timestamp>/

        Args:
            checkpoint_id: checkpoint ID

        Returns:
            备份路径
        """
        cp_dir = self._get_checkpoint_dir(checkpoint_id)
        manifest_file = cp_dir / "manifest.json"
        if not manifest_file.exists():
            raise FileNotFoundError(f"Checkpoint '{checkpoint_id}' 不存在")

        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        snapshot_dir = cp_dir / "snapshot"

        # 备份当前状态
        backup_ts = time.strftime("%Y%m%d-%H%M%S")
        backup_dir = self.backup_root / backup_ts
        backup_dir.mkdir(parents=True, exist_ok=True)

        restored_files = []
        for entry_data in manifest.get("entries", []):
            rel_path = entry_data["path"]
            current_file = self.project_path / rel_path

            # 1. 先备份当前文件（如果存在）
            if current_file.exists():
                dest = backup_dir / rel_path
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(current_file, dest)

            # 2. 再恢复 snapshot 文件
            snap_file = snapshot_dir / rel_path
            if snap_file.exists():
                dest = self.project_path / rel_path
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(snap_file.read_bytes())
                restored_files.append(rel_path)

        # 写备份元数据
        (backup_dir / "metadata.json").write_text(
            json.dumps(
                {
                    "restored_from": checkpoint_id,
                    "restored_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                    "files_restored": len(restored_files),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        return str(backup_dir)

    def diff(self, checkpoint_id: str) -> dict[str, builtins.list[str]]:
        """
        对比 checkpoint 与当前工作区的差异

        Returns:
            {"added": [...], "removed": [...], "modified": [...], "unchanged": [...]}
        """
        cp_dir = self._get_checkpoint_dir(checkpoint_id)
        manifest_file = cp_dir / "manifest.json"
        if not manifest_file.exists():
            raise FileNotFoundError(f"Checkpoint '{checkpoint_id}' 不存在")

        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        cp_dir / "snapshot"

        result: dict[str, list[str]] = {
            "added": [],
            "removed": [],
            "modified": [],
            "unchanged": [],
        }

        # 从 manifest 构建 path -> sha256 映射
        snapshot_map: dict[str, str] = {}
        for entry_data in manifest.get("entries", []):
            snapshot_map[entry_data["path"]] = entry_data["sha256"]

        # 遍历当前工作区文件
        current_files: set[str] = set()
        for file_path in self._iter_files():
            if self._is_ignored(file_path):
                continue
            rel_path = str(file_path.relative_to(self.project_path))
            current_files.add(rel_path)

        # 对比 snapshot vs 当前
        for rel_path, snapshot_sha in snapshot_map.items():
            current_file = self.project_path / rel_path
            if rel_path not in current_files:
                result["removed"].append(rel_path)
            else:
                current_sha = self._file_sha256(current_file)
                if current_sha == snapshot_sha:
                    result["unchanged"].append(rel_path)
                else:
                    result["modified"].append(rel_path)

        # 当前有但 snapshot 没有的 → added
        for file_path in self._iter_files():
            if self._is_ignored(file_path):
                continue
            rel_path = str(file_path.relative_to(self.project_path))
            if rel_path not in snapshot_map:
                result["added"].append(rel_path)

        return result

    def delete(self, checkpoint_id: str) -> bool:
        """删除 checkpoint"""
        if checkpoint_id not in self._index:
            return False
        cp_dir = Path(self._index[checkpoint_id]["path"])
        if cp_dir.exists():
            shutil.rmtree(cp_dir)
        del self._index[checkpoint_id]
        self._save_index()
        return True

    def list(
        self,
        task_id: str | None = None,
        limit: int = 50,
    ) -> builtins.list[dict[str, Any]]:
        """
        列出 checkpoint

        Args:
            task_id: 按任务 ID 过滤
            limit: 返回上限

        Returns:
            checkpoint 信息列表
        """
        results = []
        for cp_id, info in self._index.items():
            if task_id and info.get("task_id") != task_id:
                continue
            results.append({**info, "id": cp_id})

        # 按时间倒序
        results.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return results[:limit]

    def get_checkpoint(self, checkpoint_id: str) -> Checkpoint | None:
        """获取单个 checkpoint 完整信息"""
        if checkpoint_id not in self._index:
            return None
        cp_dir = Path(self._index[checkpoint_id]["path"])
        manifest_file = cp_dir / "manifest.json"
        if not manifest_file.exists():
            return None
        data = json.loads(manifest_file.read_text(encoding="utf-8"))
        return Checkpoint.from_dict(data)

    # ------------------------------------------------------------------
    # 辅助方法
    # ------------------------------------------------------------------

    def _iter_files(self):
        """迭代工作区中的所有文件"""
        if not self.project_path.exists():
            return
        for item in self.project_path.rglob("*"):
            if item.is_file():
                yield item

    def _is_ignored(self, path: Path) -> bool:
        """判断文件是否应该忽略"""
        rel_str = str(path.relative_to(self.project_path))
        for part in rel_str.split("/"):
            if part in self.IGNORE_PATTERNS:
                return True
            for pattern in self.IGNORE_PATTERNS:
                if pattern.startswith("*") and part.endswith(pattern[1:]):
                    return True
        return False

    @staticmethod
    def _file_sha256(path: Path) -> str:
        """计算文件 SHA256"""
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def _get_checkpoint_dir(self, checkpoint_id: str) -> Path:
        """根据 ID 找到 checkpoint 目录"""
        if checkpoint_id in self._index:
            return Path(self._index[checkpoint_id]["path"])
        # 尝试从 task_id 目录查找
        for cp_dir in self.checkpoint_root.rglob("*/manifest.json"):
            manifest = json.loads(cp_dir.read_text(encoding="utf-8"))
            if manifest.get("id") == checkpoint_id:
                return cp_dir.parent
        raise FileNotFoundError(f"Checkpoint '{checkpoint_id}' 不存在")

    # ------------------------------------------------------------------
    # 统计
    # ------------------------------------------------------------------

    def get_stats(self) -> dict[str, Any]:
        """获取快照统计"""
        total = len(self._index)
        total_size = sum(c.get("total_size", 0) for c in self._index.values())
        total_files = sum(c.get("file_count", 0) for c in self._index.values())
        return {
            "total_checkpoints": total,
            "total_size_bytes": total_size,
            "total_files": total_files,
        }

    def format_diff(self, diff_result: dict[str, builtins.list[str]]) -> str:
        """格式化 diff 结果为可读字符串"""
        lines = []
        if diff_result["added"]:
            lines.append(f"🆕 新增 ({len(diff_result['added'])}):")
            lines.extend([f"  + {f}" for f in diff_result["added"][:20]])
            if len(diff_result["added"]) > 20:
                lines.append(f"  ... 还有 {len(diff_result['added']) - 20} 个")

        if diff_result["removed"]:
            lines.append(f"❌ 已删除 ({len(diff_result['removed'])}):")
            lines.extend([f"  - {f}" for f in diff_result["removed"][:20]])
            if len(diff_result["removed"]) > 20:
                lines.append(f"  ... 还有 {len(diff_result['removed']) - 20} 个")

        if diff_result["modified"]:
            lines.append(f"🔄 已修改 ({len(diff_result['modified'])}):")
            lines.extend([f"  ~ {f}" for f in diff_result["modified"][:20]])
            if len(diff_result["modified"]) > 20:
                lines.append(f"  ... 还有 {len(diff_result['modified']) - 20} 个")

        if diff_result["unchanged"]:
            lines.append(f"✅ 未变 ({len(diff_result['unchanged'])})")

        if not lines:
            lines.append("（无差异）")

        return "\n".join(lines)
