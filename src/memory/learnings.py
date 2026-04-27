from __future__ import annotations
"""
学习记忆 - 踩坑记录、最佳实践

存储：
- 错误模式（什么情况下会出错）
- 解决方案（如何修复）
- 最佳实践（推荐做法）
- 技术笔记

设计：
- Markdown 格式，便于阅读和版本控制
- 按类别组织（errors, solutions, best-practices, notes）
- 支持搜索
"""

import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class LearningEntry:
    """学习条目"""

    id: str
    category: str  # "error", "solution", "best-practice", "note"
    title: str
    content: str
    tags: list[str] = field(default_factory=list)
    context: str = ""  # 触发场景
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LearningEntry":
        return cls(**data)


class LearningsMemory:
    """学习记忆管理器"""

    CATEGORIES = ["error", "solution", "best-practice", "note"]

    def __init__(self, storage_dir: Path):
        """
        Args:
            storage_dir: 存储目录
        """
        self.storage_dir = storage_dir / "learnings"
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # 按类别分目录
        for cat in self.CATEGORIES:
            (self.storage_dir / cat).mkdir(exist_ok=True)

        self.index_file = self.storage_dir / "index.json"
        self._index: dict[str, LearningEntry] = {}
        self._load_index()

    def _load_index(self):
        """加载索引"""
        if self.index_file.exists():
            data = self._parse_markdown_index()
            self._index = {k: LearningEntry.from_dict(v) for k, v in data.items()}

    def _parse_markdown_index(self) -> dict[str, dict]:
        """从 Markdown 文件解析索引"""
        index = {}
        for cat in self.CATEGORIES:
            cat_dir = self.storage_dir / cat
            if not cat_dir.exists():
                continue
            for md_file in cat_dir.glob("*.md"):
                entry = self._parse_learning_file(md_file)
                if entry:
                    index[entry.id] = entry.to_dict()
        return index

    def _parse_learning_file(self, path: Path) -> LearningEntry | None:
        """解析单个 Markdown 文件"""
        try:
            content = path.read_text()
            # 简单解析：从标题提取
            lines = content.split("\n")
            title = lines[0].lstrip("# ").strip() if lines else path.stem

            # 提取 tags
            tags = []
            tag_match = re.search(r"\[tags?: ([^\]]+)\]", content)
            if tag_match:
                tags = [t.strip() for t in tag_match.group(1).split(",")]

            return LearningEntry(
                id=path.stem,
                category=path.parent.name,
                title=title,
                content=content,
                tags=tags,
            )
        except Exception:
            return None

    def _save_entry(self, entry: LearningEntry):
        """保存条目到 Markdown 文件"""
        cat_dir = self.storage_dir / entry.category
        cat_dir.mkdir(exist_ok=True)

        file_path = cat_dir / f"{entry.id}.md"
        content = f"# {entry.title}\n\n"
        if entry.tags:
            content += f"[tags: {', '.join(entry.tags)}]\n\n"
        if entry.context:
            content += f"**场景**: {entry.context}\n\n"
        content += entry.content

        file_path.write_text(content)

    def add(
        self,
        title: str,
        content: str,
        category: str = "note",
        tags: list[str] | None = None,
        context: str = "",
    ) -> LearningEntry:
        """添加学习条目"""
        # 生成 ID
        import uuid

        entry_id = f"{title.lower().replace(' ', '-')[:30]}-{uuid.uuid4().hex[:4]}"

        entry = LearningEntry(
            id=entry_id,
            category=category,
            title=title,
            content=content,
            tags=tags or [],
            context=context,
        )

        self._index[entry_id] = entry
        self._save_entry(entry)
        self._save_index()

        return entry

    def _save_index(self):
        """保存索引"""
        data = {k: v.to_dict() for k, v in self._index.items()}
        import json

        self.index_file.write_text(json.dumps(data, ensure_ascii=False, indent=2))

    def search(self, query: str, category: str | None = None) -> list[LearningEntry]:
        """搜索学习条目"""
        results = []
        query_lower = query.lower()

        for entry in self._index.values():
            if category and entry.category != category:
                continue

            # 搜索标题、内容、tags
            if (
                query_lower in entry.title.lower()
                or query_lower in entry.content.lower()
                or any(query_lower in tag.lower() for tag in entry.tags)
            ):
                results.append(entry)

        return results

    def get_by_category(self, category: str) -> list[LearningEntry]:
        """按类别获取"""
        return [e for e in self._index.values() if e.category == category]

    def get_recent(self, limit: int = 10) -> list[LearningEntry]:
        """获取最近添加的"""
        sorted_entries = sorted(
            self._index.values(), key=lambda e: e.created_at, reverse=True
        )
        return sorted_entries[:limit]

    def delete(self, entry_id: str) -> bool:
        """删除条目"""
        if entry_id not in self._index:
            return False

        entry = self._index[entry_id]
        file_path = self.storage_dir / entry.category / f"{entry_id}.md"
        if file_path.exists():
            file_path.unlink()

        del self._index[entry_id]
        self._save_index()
        return True
