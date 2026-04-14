"""
Capsule - 完整能力包结构

由 Gene（元数据）+ manifest（配置）+ dependencies + checksum 组成。
"""

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

from .gene import Gene


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@dataclass
class Capsule:
    """
    GEP Capsule — 完整能力包

    Gene + manifest + dependencies + checksum。
    """

    gene: Gene  # 元数据
    manifest: Dict[str, Any] = field(default_factory=dict)  # tools/agents/prompts 配置
    dependencies: List[str] = field(default_factory=list)  # 依赖的其他 Capsule ID
    checksum: str = ""  # SHA256 校验

    def __post_init__(self) -> None:
        if not self.checksum:
            self.checksum = self.compute_checksum()

    # --- 校验和 ---

    def compute_checksum(self) -> str:
        """基于 gene + manifest + dependencies 计算 SHA256"""
        payload = json.dumps(
            {
                "gene": self.gene.to_dict(),
                "manifest": self.manifest,
                "dependencies": sorted(self.dependencies),
            },
            sort_keys=True,
            ensure_ascii=False,
        )
        return _sha256_hex(payload.encode("utf-8"))

    def verify_checksum(self) -> bool:
        return self.checksum == self.compute_checksum()

    # --- 序列化 ---

    def to_dict(self) -> Dict[str, Any]:
        return {
            "gene": self.gene.to_dict(),
            "manifest": self.manifest,
            "dependencies": self.dependencies,
            "checksum": self.checksum,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Capsule":
        gene = Gene.from_dict(data["gene"])
        return cls(
            gene=gene,
            manifest=data.get("manifest", {}),
            dependencies=data.get("dependencies", []),
            checksum=data.get("checksum", ""),
        )

    @classmethod
    def from_json(cls, text: str) -> "Capsule":
        return cls.from_dict(json.loads(text))

    # --- 向后兼容 .omcp ---

    @classmethod
    def from_omcp(cls, data: Dict[str, Any], file_name: str = "") -> "Capsule":
        """
        从旧 .omcp 格式升级为 Capsule。

        旧格式顶部可能没有 gene 字段，自动生成虚拟 Gene（基于文件名推断）。
        """
        gene_data = data.get("gene")
        if gene_data:
            gene = Gene.from_dict(gene_data)
        else:
            # 从文件名推断虚拟 Gene
            name = data.get("name", file_name.replace(".omcp", ""))
            category = _infer_category(data)
            tags = data.get("tags", [])
            gene = Gene(
                name=name,
                category=category,
                tags=tags,
                description=data.get("description", ""),
                version=data.get("version", "0.1.0"),
                author=data.get("author", "anonymous"),
            )

        # manifest 保留原始非 gene 字段
        manifest = {k: v for k, v in data.items() if k != "gene"}

        return cls(gene=gene, manifest=manifest)

    # --- 持久化 ---

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json(), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "Capsule":
        return cls.from_json(path.read_text(encoding="utf-8"))


def _infer_category(data: Dict[str, Any]) -> str:
    """从 .omcp 内容推断能力分类"""
    name = data.get("name", "").lower()
    desc = data.get("description", "").lower()
    tools = str(data.get("tools", [])).lower()
    combined = f"{name} {desc} {tools}"

    if "review" in combined:
        return "review"
    if "debug" in combined or "fix" in combined:
        return "debug"
    if "doc" in combined or "readme" in combined:
        return "docs"
    if "test" in combined:
        return "test"
    return "coding"
