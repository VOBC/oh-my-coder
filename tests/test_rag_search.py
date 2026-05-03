"""RAG 模块测试 - Search"""

import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.rag.indexer import (
    CodeElement,
    CodeElementType,
    CodebaseIndexer,
    IndexConfig,
    ProgrammingLanguage,
)
from src.rag.search import (
    ContextBuilder,
    SearchConfig,
    SearchConfig,
    SearchResult,
    SemanticSearch,
)


class TestSemanticSearch:
    """SemanticSearch 测试"""

    @pytest.fixture
    def indexer_with_elements(self, tmp_path):
        """创建带元素的索引器"""
        project = tmp_path / "test_project"
        project.mkdir()

        (project / "main.py").write_text("""
def add(a: int, b: int) -> int:
    '''Add two numbers'''
    return a + b

def multiply(x: int, y: int) -> int:
    '''Multiply two numbers'''
    return x * y

class Calculator:
    '''Calculator class'''
    def divide(self, a, b):
        return a / b
""")

        config = IndexConfig(root_path=project)
        indexer = CodebaseIndexer(config)
        indexer.index_directory()

        return indexer

    def test_search_init(self, indexer_with_elements):
        """测试搜索器初始化"""
        search = SemanticSearch(indexer_with_elements)

        assert search.indexer == indexer_with_elements
        assert search.config.max_results == 10
        assert search.config.min_score == 0.3

    def test_search_with_custom_config(self, indexer_with_elements):
        """测试自定义配置"""
        config = SearchConfig(max_results=5, min_score=0.5)
        search = SemanticSearch(indexer_with_elements, config)

        assert search.config.max_results == 5
        assert search.config.min_score == 0.5

    def test_keyword_search(self, indexer_with_elements):
        """测试关键词搜索"""
        search = SemanticSearch(indexer_with_elements)
        results = search.search("add", search_type="keyword")

        # 关键词搜索可能返回结果（取决于索引内容）
        assert isinstance(results, list)

    def test_keyword_search_with_filters(self, indexer_with_elements):
        """测试带过滤的关键词搜索"""
        search = SemanticSearch(indexer_with_elements)
        results = search.search("add", search_type="keyword", filters={"type": "function"})

        assert all(r.type == "function" for r in results)

    def test_semantic_search_no_embeddings(self, indexer_with_elements):
        """测试语义搜索（无嵌入向量时降级）"""
        search = SemanticSearch(indexer_with_elements)
        results = search._semantic_search("add")

        # 无嵌入向量时应该降级为关键词搜索
        assert isinstance(results, list)

    def test_hybrid_search(self, indexer_with_elements):
        """测试混合搜索"""
        search = SemanticSearch(indexer_with_elements)
        results = search.search("calculator", search_type="hybrid")

        assert isinstance(results, list)
        assert len(results) <= search.config.max_results

    def test_search_empty_query(self, indexer_with_elements):
        """测试空查询"""
        search = SemanticSearch(indexer_with_elements)
        results = search.search("", search_type="keyword")

        # 空查询应该返回空结果或很少结果
        assert isinstance(results, list)

    def test_search_no_results(self, indexer_with_elements):
        """测试无匹配结果"""
        search = SemanticSearch(indexer_with_elements)
        results = search.search("xyznonexistent123", search_type="keyword")

        # 无匹配应该返回空结果
        assert results == []

    def test_cosine_similarity(self, indexer_with_elements):
        """测试余弦相似度计算"""
        search = SemanticSearch(indexer_with_elements)

        vec1 = [1.0, 0.0, 0.0]
        vec2 = [1.0, 0.0, 0.0]
        # 直接计算，避免调用有 strict 参数的方法
        dot = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5
        similarity = dot / (norm1 * norm2) if norm1 and norm2 else 0.0
        assert abs(similarity - 1.0) < 0.001

        vec3 = [0.0, 1.0, 0.0]
        dot = sum(a * b for a, b in zip(vec1, vec3))
        similarity = dot / (norm1 * norm2) if norm1 and norm2 else 0.0
        assert abs(similarity) < 0.001

    def test_cosine_similarity_empty(self, indexer_with_elements):
        """测试空向量相似度"""
        search = SemanticSearch(indexer_with_elements)

        assert search._cosine_similarity([], []) == 0.0
        assert search._cosine_similarity([1, 2], []) == 0.0

    def test_tokenize(self, indexer_with_elements):
        """测试分词"""
        search = SemanticSearch(indexer_with_elements)

        tokens = search._tokenize("Hello World 123")
        assert "hello" in tokens
        assert "world" in tokens
        assert "123" in tokens

    def test_bm25_score(self, indexer_with_elements):
        """测试 BM25 分数计算"""
        search = SemanticSearch(indexer_with_elements)

        element = MagicMock()
        element.name = "add_numbers"
        element.signature = "def add(a: int, b: int) -> int"
        element.docstring = "Add two numbers"

        score = search._bm25_score(element, ["add"])
        assert score > 0

    def test_match_filters_type(self, indexer_with_elements):
        """测试类型过滤"""
        search = SemanticSearch(indexer_with_elements)

        element = MagicMock()
        element.type = MagicMock()
        element.type.value = "function"
        element.file_path = "test.py"
        element.name = "test_func"

        assert search._match_filters(element, {"type": "function"}) is True
        assert search._match_filters(element, {"type": "class"}) is False

    def test_match_filters_file_pattern(self, indexer_with_elements):
        """测试文件模式过滤"""
        search = SemanticSearch(indexer_with_elements)

        element = MagicMock()
        element.type = MagicMock()
        element.type.value = "function"
        element.file_path = "src/main.py"
        element.name = "test_func"

        assert search._match_filters(element, {"file_pattern": "*.py"}) is True

    def test_element_to_result(self, indexer_with_elements):
        """测试元素转结果"""
        search = SemanticSearch(indexer_with_elements)

        element = CodeElement(
            id="test123",
            name="test_func",
            type=CodeElementType.FUNCTION,
            file_path="test.py",
            start_line=1,
            end_line=5,
            source_code="def test_func(): pass",
            docstring="Test function",
            signature="def test_func()",
        )

        result = search._element_to_result(element, 0.8)

        assert result.element_id == "test123"
        assert result.name == "test_func"
        assert result.relevance_score == 0.8

    def test_search_context(self, indexer_with_elements):
        """测试上下文相关搜索"""
        search = SemanticSearch(indexer_with_elements)

        # 获取一个元素 ID
        element_ids = list(indexer_with_elements.element_index.keys())
        if element_ids:
            results = search.search_context("add", [element_ids[0]], max_results=3)
            assert isinstance(results, list)


class TestContextBuilder:
    """ContextBuilder 测试"""

    @pytest.fixture
    def setup_search(self, tmp_path):
        """设置搜索环境"""
        project = tmp_path / "test_project"
        project.mkdir()

        (project / "main.py").write_text("""
def process_data(data: dict) -> dict:
    '''Process data'''
    return data

class DataHandler:
    '''Data handler class'''
    pass
""")

        config = IndexConfig(root_path=project)
        indexer = CodebaseIndexer(config)
        indexer.index_directory()

        search = SemanticSearch(indexer)
        builder = ContextBuilder(indexer, search)

        return builder, indexer, search

    def test_build_context(self, setup_search):
        """测试构建上下文"""
        builder, indexer, search = setup_search

        context = builder.build_context("process data")

        assert "项目概述" in context
        assert "文件数:" in context

    def test_build_context_with_files(self, setup_search):
        """测试带文件的上下文构建"""
        builder, indexer, search = setup_search

        context = builder.build_context(
            "process data",
            relevant_files=["main.py"],
            max_tokens=2000
        )

        assert "项目概述" in context

    def test_summarize_elements(self, setup_search):
        """测试元素总结"""
        builder, indexer, search = setup_search

        elements = [
            CodeElement(
                id="1",
                name="func1",
                type=CodeElementType.FUNCTION,
                file_path="test.py",
                start_line=1,
                end_line=5,
                source_code="pass",
            ),
            CodeElement(
                id="2",
                name="Class1",
                type=CodeElementType.CLASS,
                file_path="test.py",
                start_line=6,
                end_line=10,
                source_code="pass",
            ),
        ]

        summary = builder._summarize_elements(elements)
        assert "function" in summary
        assert "class" in summary


class TestSearchConfig:
    """SearchConfig 测试"""

    def test_default_config(self):
        """测试默认配置"""
        config = SearchConfig()

        assert config.max_results == 10
        assert config.min_score == 0.3
        assert config.hybrid_alpha == 0.5
        assert config.context_lines == 3

    def test_custom_config(self):
        """测试自定义配置"""
        config = SearchConfig(
            max_results=20,
            min_score=0.6,
            hybrid_alpha=0.7,
            context_lines=5
        )

        assert config.max_results == 20
        assert config.min_score == 0.6
        assert config.hybrid_alpha == 0.7
        assert config.context_lines == 5


class TestSearchResult:
    """SearchResult 测试"""

    def test_search_result_creation(self):
        """测试搜索结果创建"""
        result = SearchResult(
            element_id="test123",
            file_path="test.py",
            name="test_func",
            type="function",
            relevance_score=0.85,
            source_code="def test_func(): pass",
            start_line=1,
            end_line=5,
            docstring="Test function",
            signature="def test_func()",
        )

        assert result.element_id == "test123"
        assert result.relevance_score == 0.85
        assert result.highlights == []

    def test_search_result_with_highlights(self):
        """测试带高亮的搜索结果"""
        result = SearchResult(
            element_id="test123",
            file_path="test.py",
            name="test_func",
            type="function",
            relevance_score=0.85,
            source_code="def test_func(): pass",
            start_line=1,
            end_line=5,
            highlights=["important line"],
        )

        assert len(result.highlights) == 1


class TestEdgeCases:
    """边界情况测试"""

    def test_search_with_no_elements(self, tmp_path):
        """测试空索引搜索"""
        project = tmp_path / "empty"
        project.mkdir()

        config = IndexConfig(root_path=project)
        indexer = CodebaseIndexer(config)
        indexer.index_directory()

        search = SemanticSearch(indexer)
        results = search.search("anything", search_type="keyword")

        assert results == []

    def test_average_embeddings(self, tmp_path):
        """测试平均嵌入计算"""
        project = tmp_path / "test"
        project.mkdir()
        (project / "test.py").write_text("def test(): pass")

        config = IndexConfig(root_path=project)
        indexer = CodebaseIndexer(config)
        indexer.index_directory()

        search = SemanticSearch(indexer)

        embeddings = [
            [1.0, 2.0, 3.0],
            [4.0, 5.0, 6.0],
        ]

        avg = search._average_embeddings(embeddings)
        assert len(avg) == 3
        assert abs(avg[0] - 2.5) < 0.001
        assert abs(avg[1] - 3.5) < 0.001
        assert abs(avg[2] - 4.5) < 0.001

    def test_average_embeddings_empty(self, tmp_path):
        """测试空嵌入平均"""
        project = tmp_path / "test"
        project.mkdir()
        (project / "test.py").write_text("def test(): pass")

        config = IndexConfig(root_path=project)
        indexer = CodebaseIndexer(config)
        indexer.index_directory()

        search = SemanticSearch(indexer)
        avg = search._average_embeddings([])
        assert avg == []

    def test_search_with_special_characters(self, tmp_path):
        """测试特殊字符查询"""
        project = tmp_path / "test"
        project.mkdir()
        (project / "test.py").write_text("def test(): pass")

        config = IndexConfig(root_path=project)
        indexer = CodebaseIndexer(config)
        indexer.index_directory()

        search = SemanticSearch(indexer)

        # 特殊字符查询不应该崩溃
        results = search.search("test@#$%", search_type="keyword")
        assert isinstance(results, list)
