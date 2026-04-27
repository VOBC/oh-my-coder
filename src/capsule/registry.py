from __future__ import annotations

"""
GEPRegistry - 能力注册表

register / discover / resolve / export_event
"""

from .capsule import Capsule
from .gene import Gene


class GEPRegistry:
    """
    GEP 能力注册表

    本地内存注册表，支持注册、发现、解析和事件导出。
    """

    def __init__(self) -> None:
        self._store: dict[str, Capsule] = {}  # gene_id -> Capsule

    # --- 核心 API ---

    def register(self, capsule: Capsule) -> str:
        """
        注册一个 Capsule，返回 Gene ID。

        如果 gene.id 已存在则覆盖。
        """
        gene_id = capsule.gene.id
        self._store[gene_id] = capsule
        return gene_id

    def discover(self, query: str) -> list[Gene]:
        """
        按关键词发现能力。

        搜索范围：name / description / tags / capabilities。
        匹配规则：大小写不敏感，支持空格分隔的多个关键词（AND 逻辑）。
        """
        keywords = [k.lower() for k in query.strip().split() if k]
        if not keywords:
            return []

        results: list[Gene] = []
        for capsule in self._store.values():
            gene = capsule.gene
            searchable = " ".join(
                [
                    gene.name,
                    gene.description,
                    gene.category,
                    " ".join(gene.tags),
                    " ".join(gene.capabilities),
                ]
            ).lower()

            if all(kw in searchable for kw in keywords):
                results.append(gene)

        return results

    def resolve(self, gene_id: str) -> Capsule | None:
        """根据 Gene ID 获取 Capsule，不存在返回 None"""
        return self._store.get(gene_id)

    def export_event(self, gene_id: str) -> dict | None:
        """
        导出 GEP Event 格式。

        {
            "type": "GEP/Register",
            "version": "1.0",
            "payload": {"gene": {...}, "manifest": {...}, ...}
        }
        """
        capsule = self._store.get(gene_id)
        if capsule is None:
            return None

        return {
            "type": "GEP/Register",
            "version": "1.0",
            "payload": capsule.to_dict(),
        }

    # --- 辅助 ---

    def list_all(self) -> list[Gene]:
        """列出所有已注册的 Gene"""
        return [c.gene for c in self._store.values()]

    def unregister(self, gene_id: str) -> bool:
        """移除注册，返回是否成功"""
        if gene_id in self._store:
            del self._store[gene_id]
            return True
        return False

    def count(self) -> int:
        return len(self._store)
