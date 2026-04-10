"""
Quest 持久化存储

使用 JSON 文件存储 Quest 列表，每个 Quest 单独一个 JSON 文件。
存储在 <project_path>/.omc/quests/ 目录下。
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union

from .models import Quest, QuestSpec, QuestStatus


class QuestStore:
    """Quest 持久化存储"""

    def __init__(self, project_path: Union[Path, str]):
        project_path = Path(project_path)
        self.project_path = project_path
        self.quests_dir = project_path / ".omc" / "quests"
        self._quests_cache: Dict[str, Quest] = {}

    def _ensure_dir(self) -> None:
        """确保存储目录存在"""
        self.quests_dir.mkdir(parents=True, exist_ok=True)

    def _quest_file(self, quest_id: str) -> Path:
        """获取 Quest 文件路径"""
        return self.quests_dir / f"{quest_id}.json"

    # ============================================================
    # CRUD 操作
    # ============================================================

    def create(self, title: str, description: str, project_path: str) -> Quest:
        """创建新 Quest"""
        self._ensure_dir()
        quest = Quest(
            id=str(uuid.uuid4()),
            title=title,
            description=description,
            project_path=project_path,
        )
        self._save(quest)
        return quest

    def get(self, quest_id: str) -> Optional[Quest]:
        """获取 Quest"""
        if quest_id in self._quests_cache:
            return self._quests_cache[quest_id]

        path = self._quest_file(quest_id)
        if not path.exists():
            return None

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError):
            # 文件损坏，返回 None
            return None

        try:
            quest = Quest(**data)
            self._quests_cache[quest_id] = quest
            return quest
        except Exception:
            return None

    def save(self, quest: Quest) -> None:
        """保存 Quest"""
        quest.updated_at = datetime.now()
        self._save(quest)
        self._quests_cache[quest.id] = quest

    def delete(self, quest_id: str) -> bool:
        """删除 Quest"""
        path = self._quest_file(quest_id)
        if path.exists():
            path.unlink()
        self._quests_cache.pop(quest_id, None)
        return True

    def list(self, status_filter: Optional[QuestStatus] = None) -> List[Quest]:
        """列出所有 Quest"""
        self._ensure_dir()

        if not self.quests_dir.exists():
            return []

        quests = []
        for file in self.quests_dir.glob("*.json"):
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                quest = Quest(**data)
                if status_filter is None or quest.status == status_filter:
                    quests.append(quest)
            except Exception:
                continue

        # 按创建时间倒序
        quests.sort(key=lambda q: q.created_at, reverse=True)
        return quests

    def get_active(self) -> List[Quest]:
        """获取活跃的 Quest（未完成且未取消）"""
        active_statuses = {
            QuestStatus.PENDING,
            QuestStatus.SPEC_GENERATING,
            QuestStatus.SPEC_READY,
            QuestStatus.EXECUTING,
            QuestStatus.PAUSED,
        }
        return self.list(status_filter=None)

    # ============================================================
    # 便捷操作
    # ============================================================

    def update_status(self, quest_id: str, status: QuestStatus) -> Optional[Quest]:
        """更新 Quest 状态"""
        quest = self.get(quest_id)
        if quest is None:
            return None

        quest.status = status
        if status == QuestStatus.EXECUTING and quest.started_at is None:
            quest.started_at = datetime.now()
        if status in (QuestStatus.COMPLETED, QuestStatus.FAILED):
            quest.completed_at = datetime.now()

        self.save(quest)
        return quest

    def set_spec(self, quest_id: str, spec: QuestSpec) -> Optional[Quest]:
        """设置 SPEC"""
        quest = self.get(quest_id)
        if quest is None:
            return None

        quest.spec = spec
        # 保存到文件
        spec_path = self.quests_dir / f"{quest_id}_SPEC.md"
        spec_path.write_text(spec.to_markdown(), encoding="utf-8")
        quest.spec_path = str(spec_path)
        self.save(quest)
        return quest

    def _save(self, quest: Quest) -> None:
        """内部保存方法"""
        self._ensure_dir()
        path = self._quest_file(quest.id)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(
                quest.model_dump(mode="json"),
                f,
                ensure_ascii=False,
                indent=2,
            )
