from __future__ import annotations

"""
Gene - 能力元数据结构

GEP 协议中的基本单元，描述一个能力的身份和属性。
"""

from dataclasses import asdict, dataclass, field
from typing import Any
from uuid import uuid4


@dataclass
class Gene:
    """
    能力元数据（GEP Gene）

    对应 GEP 协议中的能力基因，携带身份、分类和描述信息。
    """

    name: str  # 能力名称
    category: str  # coding / review / debug / docs / test
    tags: list[str] = field(default_factory=list)  # [python, pytest, bug-fix]
    description: str = ""  # 一句话描述
    capabilities: list[str] = field(default_factory=list)  # 具体能力列表
    version: str = "1.0.0"  # 版本号
    author: str = "anonymous"  # 作者
    created_at: str = ""  # ISO 格式时间
    signature: str | None = None  # 未来对接 zCloak
    id: str = ""  # UUID

    def __post_init__(self) -> None:
        if not self.id:
            self.id = str(uuid4())
        if not self.created_at:
            from datetime import datetime

            self.created_at = datetime.now().isoformat()

    # --- 序列化 ---

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        import json

        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Gene":
        # 只取 Gene 自身字段，忽略多余 key
        valid = {
            k: v
            for k, v in data.items()
            if k in cls.__dataclass_fields__  # type: ignore[attr-defined]
        }
        return cls(**valid)

    # --- 校验 ---

    def validate(self) -> list[str]:
        errors: list[str] = []
        valid_categories = {"coding", "review", "debug", "docs", "test"}
        if self.category and self.category not in valid_categories:
            errors.append(
                f"无效 category '{self.category}'，应为 {sorted(valid_categories)}"
            )
        if not self.name:
            errors.append("name 不能为空")
        return errors
