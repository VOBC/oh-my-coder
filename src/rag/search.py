"""
语义搜索模块

功能：
1. 向量相似度搜索
2. 混合搜索（关键词 + 语义）
3. 上下文相关搜索
"""

import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class SearchResult:
    """搜索结果"""

    element_id: str
    file_path: str
    name: str
    type: str
    relevance_score: float
    source_code: str
    start_line: int
    end_line: int
    docstring: str | None = None
    signature: str | None = None
    highlights: list[str] = field(default_factory=list)
    context: str = ""


@dataclass
class SearchConfig:
    """搜索配置"""

    max_results: int = 10
    min_score: float = 0.3
    hybrid_alpha: float = 0.5  # 语义搜索权重（0-1），剩余为关键词权重
    context_lines: int = 3  # 上下文行数


class SemanticSearch:
    """
    语义搜索

    支持：
    1. 纯语义搜索（向量相似度）
    2. 纯关键词搜索（BM25）
    3. 混合搜索（语义 + 关键词）
    """

    def __init__(self, indexer, config: SearchConfig | None = None):
        """
        Args:
            indexer: CodebaseIndexer 实例
            config: 搜索配置
        """
        self.indexer = indexer
        self.config = config or SearchConfig()

    def search(
        self,
        query: str,
        search_type: str = "hybrid",
        filters: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        """
        执行搜索

        Args:
            query: 搜索查询
            search_type: 搜索类型（semantic/keyword/hybrid）
            filters: 过滤条件

        Returns:
            搜索结果列表
        """
        if search_type == "semantic":
            return self._semantic_search(query, filters)
        if search_type == "keyword":
            return self._keyword_search(query, filters)
        return self._hybrid_search(query, filters)

    def _semantic_search(
        self,
        query: str,
        filters: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        """语义搜索（向量相似度）"""
        results = []

        # 获取查询嵌入
        query_embedding = self._get_embedding(query)

        if not query_embedding:
            # 没有嵌入，降级为关键词搜索
            return self._keyword_search(query, filters)

        # 计算与所有元素的相似度
        similarities = []
        for element in self.indexer.element_index.values():
            if not element.embedding:
                continue

            # 应用过滤
            if filters and not self._match_filters(element, filters):
                continue

            similarity = self._cosine_similarity(query_embedding, element.embedding)
            similarities.append((element, similarity))

        # 排序并返回 top-k
        similarities.sort(key=lambda x: x[1], reverse=True)

        for element, score in similarities[: self.config.max_results]:
            if score < self.config.min_score:
                continue

            results.append(self._element_to_result(element, score))

        return results

    def _keyword_search(
        self,
        query: str,
        filters: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        """关键词搜索（BM25 风格）"""
        results = []

        # 分词
        query_terms = self._tokenize(query)

        # 计算每个元素的 BM25 分数
        scores = []
        for element in self.indexer.element_index.values():
            if filters and not self._match_filters(element, filters):
                continue

            score = self._bm25_score(element, query_terms)
            if score > 0:
                scores.append((element, score))

        # 排序并返回 top-k
        scores.sort(key=lambda x: x[1], reverse=True)

        for element, score in scores[: self.config.max_results]:
            results.append(self._element_to_result(element, score))

        return results

    def _hybrid_search(
        self,
        query: str,
        filters: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        """混合搜索（语义 + 关键词）"""
        semantic_results = self._semantic_search(query, filters)
        keyword_results = self._keyword_search(query, filters)

        # 合并结果
        combined = {}

        # 语义搜索结果
        for result in semantic_results:
            combined[result.element_id] = result
            result.relevance_score *= self.config.hybrid_alpha

        # 关键词搜索结果
        for result in keyword_results:
            if result.element_id in combined:
                # 合并分数
                combined[result.element_id].relevance_score += (
                    result.relevance_score * (1 - self.config.hybrid_alpha)
                )
            else:
                result.relevance_score *= 1 - self.config.hybrid_alpha
                combined[result.element_id] = result

        # 排序
        results = sorted(
            combined.values(),
            key=lambda x: x.relevance_score,
            reverse=True,
        )

        return results[: self.config.max_results]

    def search_context(
        self,
        query: str,
        context_elements: list[str],
        max_results: int = 5,
    ) -> list[SearchResult]:
        """
        上下文相关搜索

        根据当前上下文（如正在编辑的代码）搜索相关元素

        Args:
            query: 搜索查询
            context_elements: 上下文元素 ID 列表
            max_results: 最大结果数

        Returns:
            与上下文相关的搜索结果
        """
        # 获取上下文元素的嵌入
        context_embeddings = []
        for eid in context_elements:
            element = self.indexer.element_index.get(eid)
            if element and element.embedding:
                context_embeddings.append(element.embedding)

        if not context_embeddings:
            return self.search(query)

        # 计算上下文平均嵌入
        avg_embedding = self._average_embeddings(context_embeddings)

        # 获取查询嵌入
        query_embedding = self._get_embedding(query)

        if not query_embedding:
            return self._keyword_search(query)

        # 结合查询嵌入和上下文嵌入
        combined_embedding = [
            (q + c) / 2 for q, c in zip(query_embedding, avg_embedding)
        ]

        # 搜索
        results = []
        for element in self.indexer.element_index.values():
            if not element.embedding:
                continue

            if element.id in context_elements:
                continue  # 排除已在上下文中的元素

            similarity = self._cosine_similarity(combined_embedding, element.embedding)

            if similarity >= self.config.min_score:
                results.append((element, similarity))

        # 排序并返回
        results.sort(key=lambda x: x[1], reverse=True)

        return [self._element_to_result(e, s) for e, s in results[:max_results]]

    def _get_embedding(self, text: str) -> list[float] | None:
        """获取文本嵌入"""
        # TODO: 调用嵌入 API
        return None

    def _cosine_similarity(
        self,
        vec1: list[float],
        vec2: list[float],
    ) -> float:
        """计算余弦相似度"""
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    def _average_embeddings(
        self,
        embeddings: list[list[float]],
    ) -> list[float]:
        """计算平均嵌入"""
        if not embeddings:
            return []

        n = len(embeddings)
        dim = len(embeddings[0])

        return [sum(e[i] for e in embeddings) / n for i in range(dim)]

    def _tokenize(self, text: str) -> list[str]:
        """分词"""
        # 简单分词：小写化 + 按非字母数字分割
        text = text.lower()
        return re.findall(r"[a-z0-9_]+", text)

    def _bm25_score(
        self,
        element,
        query_terms: list[str],
        k1: float = 1.5,
        b: float = 0.75,
    ) -> float:
        """计算 BM25 分数"""
        # 获取元素文本
        text = f"{element.name} {element.signature or ''} {element.docstring or ''}"
        text = text.lower()

        # 分词
        element_terms = self._tokenize(text)
        if not element_terms:
            return 0.0

        # 计算词频
        term_freq = {}
        for term in element_terms:
            term_freq[term] = term_freq.get(term, 0) + 1

        # 计算文档长度
        doc_length = len(element_terms)
        avg_doc_length = 50  # 简化假设

        # 计算分数
        score = 0.0
        for term in query_terms:
            if term not in term_freq:
                continue

            tf = term_freq[term]
            idf = 1.0  # 简化，没有文档频率

            numerator = tf * (k1 + 1)
            denominator = tf + k1 * (1 - b + b * doc_length / avg_doc_length)

            score += idf * numerator / denominator

        return score

    def _match_filters(
        self,
        element,
        filters: dict[str, Any],
    ) -> bool:
        """检查元素是否匹配过滤条件"""
        for key, value in filters.items():
            if key == "type":
                if element.type.value != value:
                    return False
            elif key == "file_pattern":
                if not Path(element.file_path).match(value):
                    return False
            elif key == "name_pattern":
                if not re.search(value, element.name):
                    return False

        return True

    def _element_to_result(
        self,
        element,
        score: float,
    ) -> SearchResult:
        """将元素转换为搜索结果"""
        # 提取高亮
        highlights = []
        if element.docstring:
            highlights.append(element.docstring[:100])

        return SearchResult(
            element_id=element.id,
            file_path=element.file_path,
            name=element.name,
            type=element.type.value,
            relevance_score=score,
            source_code=element.source_code,
            start_line=element.start_line,
            end_line=element.end_line,
            docstring=element.docstring,
            signature=element.signature,
            highlights=highlights,
        )


class ContextBuilder:
    """
    上下文构建器

    为 Agent 构建项目上下文
    """

    def __init__(self, indexer, search: SemanticSearch):
        self.indexer = indexer
        self.search = search

    def build_context(
        self,
        task: str,
        relevant_files: list[str] | None = None,
        max_tokens: int = 4000,
    ) -> str:
        """
        构建项目上下文

        Args:
            task: 任务描述
            relevant_files: 相关文件列表
            max_tokens: 最大 token 数

        Returns:
            格式化的上下文字符串
        """
        parts = []

        # 1. 项目概述
        stats = self.indexer.get_stats()
        parts.append(
            f"""## 项目概述
- 文件数: {stats["files_indexed"]}
- 代码元素: {stats["elements_indexed"]}
- 语言分布: {stats["languages"]}
"""
        )

        # 2. 相关代码搜索
        search_results = self.search.search(task, search_type="hybrid")

        if search_results:
            parts.append("## 相关代码\n")
            for result in search_results[:5]:
                parts.append(
                    f"""### {result.name} ({result.type})
文件: {result.file_path}:{result.start_line}-{result.end_line}
```python
{result.source_code[:500]}{"..." if len(result.source_code) > 500 else ""}
```
"""
                )

        # 3. 相关文件结构
        if relevant_files:
            parts.append("## 文件结构\n")
            for file_path in relevant_files[:10]:
                file_index = self.indexer.file_indices.get(file_path)
                if file_index:
                    elements_summary = self._summarize_elements(file_index.elements)
                    parts.append(f"- {file_path}\n  {elements_summary}\n")

        return "\n".join(parts)

    def _summarize_elements(self, elements) -> str:
        """总结元素"""
        counts = {}
        for e in elements:
            type_name = e.type.value
            counts[type_name] = counts.get(type_name, 0) + 1

        return ", ".join(f"{count} {type_name}" for type_name, count in counts.items())
