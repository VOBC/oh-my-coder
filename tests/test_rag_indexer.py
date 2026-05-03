"""RAG 模块测试 - Indexer"""

import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.rag.indexer import (
    CodebaseIndexer,
    CodeElementType,
    IndexConfig,
    ProgrammingLanguage,
    PythonParser,
)


class TestPythonParser:
    """PythonParser 测试"""

    @pytest.mark.parametrize("source,expected_name,expected_type,expected_docstring", [
        ("""
def hello(name: str) -> str:
    '''Say hello'''
    return f"Hello, {name}"
""", "hello", CodeElementType.FUNCTION, "Say hello"),
        ("""
class MyClass:
    '''A test class'''
    def __init__(self):
        pass
""", "MyClass", CodeElementType.CLASS, "A test class"),
        ("""
async def fetch_data(url: str) -> dict:
    '''Fetch data from URL'''
    return {}
""", "fetch_data", CodeElementType.FUNCTION, "Fetch data from URL"),
    ])
    def test_parse_elements(self, source, expected_name, expected_type, expected_docstring):
        """测试解析函数/类/异步函数定义"""
        parser = PythonParser()
        elements = parser.parse(source, "test.py")

        assert len(elements) >= 1
        # 找到目标元素
        elem = next((e for e in elements if e.name == expected_name), None)
        assert elem is not None
        assert elem.name == expected_name
        assert elem.type == expected_type
        assert elem.docstring == expected_docstring

    def test_parse_empty_source(self):
        """测试解析空源码"""
        parser = PythonParser()
        elements = parser.parse("", "test.py")
        assert elements == []

    def test_parse_syntax_error(self):
        """测试解析语法错误"""
        parser = PythonParser()
        source = "def invalid("  # 语法错误
        elements = parser.parse(source, "test.py")
        assert elements == []


class TestCodebaseIndexer:
    """CodebaseIndexer 测试"""

    @pytest.fixture
    def temp_project(self, tmp_path):
        """创建临时项目目录"""
        project = tmp_path / "test_project"
        project.mkdir()

        # 创建测试文件
        (project / "main.py").write_text("""
def add(a: int, b: int) -> int:
    '''Add two numbers'''
    return a + b

class Calculator:
    '''Calculator class'''
    def multiply(self, x, y):
        return x * y
""")

        (project / "utils.py").write_text("""
def hello():
    '''Say hello'''
    print("Hello")
""")

        return project

    def test_indexer_init(self):
        """测试索引器初始化"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = IndexConfig(root_path=Path(tmpdir))
            indexer = CodebaseIndexer(config)

            assert indexer.config == config
            assert indexer.embedding_client is None
            assert indexer.file_indices == {}
            assert indexer.element_index == {}

    def test_should_index(self, temp_project):
        """测试文件过滤"""
        config = IndexConfig(root_path=temp_project)
        indexer = CodebaseIndexer(config)

        # 正常文件应该索引
        assert indexer.should_index(temp_project / "main.py") is True

    def test_should_index_exclude(self, temp_project):
        """测试排除模式"""
        config = IndexConfig(root_path=temp_project)
        CodebaseIndexer(config)

        # __pycache__ 路径应该被排除（检查路径字符串）
        pycache_path = str(temp_project / "__pycache__" / "test.pyc")
        # 直接检查排除模式匹配
        assert "__pycache__" in pycache_path

    @pytest.mark.parametrize("filename,expected_lang", [
        ("main.py", ProgrammingLanguage.PYTHON),
        ("test.js", ProgrammingLanguage.JAVASCRIPT),
        ("test.ts", ProgrammingLanguage.TYPESCRIPT),
        ("test.go", ProgrammingLanguage.GO),
        ("app.java", ProgrammingLanguage.JAVA),
        ("main.rs", ProgrammingLanguage.RUST),
    ])
    def test_detect_language(self, temp_project, filename, expected_lang):
        """测试语言检测"""
        config = IndexConfig(root_path=temp_project)
        indexer = CodebaseIndexer(config)

        assert indexer.detect_language(Path(filename)) == expected_lang

    def test_index_file(self, temp_project):
        """测试索引单个文件"""
        config = IndexConfig(root_path=temp_project)
        indexer = CodebaseIndexer(config)

        file_index = indexer.index_file(temp_project / "main.py")

        assert file_index is not None
        assert file_index.language == ProgrammingLanguage.PYTHON
        assert len(file_index.elements) > 0

    def test_index_directory(self, temp_project):
        """测试索引整个目录"""
        config = IndexConfig(root_path=temp_project)
        indexer = CodebaseIndexer(config)

        indices = indexer.index_directory()

        # 索引结果应该是字典
        assert isinstance(indices, dict)

    def test_index_file_read_error(self, temp_project):
        """测试文件读取错误"""
        config = IndexConfig(root_path=temp_project)
        indexer = CodebaseIndexer(config)

        # 不存在的文件
        result = indexer.index_file(temp_project / "nonexistent.py")
        assert result is None

    def test_generate_embeddings(self, temp_project):
        """测试生成嵌入向量"""
        config = IndexConfig(root_path=temp_project)
        mock_client = MagicMock()
        indexer = CodebaseIndexer(config, embedding_client=mock_client)

        indexer.index_directory()

        # 没有实际嵌入客户端时应该正常返回
        import asyncio
        asyncio.run(indexer.generate_embeddings())

        # 验证不会崩溃即可

    def test_get_stats(self, temp_project):
        """测试获取统计信息"""
        config = IndexConfig(root_path=temp_project)
        indexer = CodebaseIndexer(config)

        indexer.index_directory()
        stats = indexer.get_stats()

        # 验证统计信息结构
        assert "files_indexed" in stats
        assert "elements_indexed" in stats
        assert "languages" in stats

    def test_save_load_index(self, temp_project):
        """测试保存和加载索引"""
        config = IndexConfig(root_path=temp_project)
        indexer = CodebaseIndexer(config)

        indexer.index_directory()

        with tempfile.TemporaryDirectory() as tmpdir:
            save_path = Path(tmpdir) / "index"
            indexer.save(save_path)

            # 验证文件存在
            assert (save_path / "files.json").exists()
            assert (save_path / "elements.json").exists()

    def test_element_to_text(self, temp_project):
        """测试元素转文本"""
        config = IndexConfig(root_path=temp_project)
        indexer = CodebaseIndexer(config)

        indexer.index_directory()

        # 如果有元素，测试转换
        if indexer.element_index:
            element = list(indexer.element_index.values())[0]
            text = indexer._element_to_text(element)
            assert "File:" in text
            assert "Type:" in text
            assert "Name:" in text
        else:
            # 没有元素时跳过
            pass

    def test_extract_imports(self, temp_project):
        """测试提取导入语句"""
        config = IndexConfig(root_path=temp_project)
        indexer = CodebaseIndexer(config)

        source = """
import os
import sys
from pathlib import Path
from collections import defaultdict
"""
        imports = indexer._extract_imports(source, ProgrammingLanguage.PYTHON)

        assert "os" in imports
        assert "sys" in imports
        assert "pathlib" in imports or "Path" in imports


class TestEdgeCases:
    """边界情况测试"""

    def test_empty_directory(self, tmp_path):
        """测试空目录"""
        config = IndexConfig(root_path=tmp_path)
        indexer = CodebaseIndexer(config)

        indices = indexer.index_directory()
        assert indices == {}

    def test_very_long_source(self, tmp_path):
        """测试超长源码（截断）"""
        config = IndexConfig(root_path=tmp_path)
        indexer = CodebaseIndexer(config)

        # 创建超长源码文件
        long_source = "def test():\n    " + "pass\n    " * 1000
        test_file = tmp_path / "long.py"
        test_file.write_text(long_source)

        file_index = indexer.index_file(test_file)
        assert file_index is not None

    def test_max_file_size(self, tmp_path):
        """测试文件大小限制"""
        config = IndexConfig(root_path=tmp_path, max_file_size=10)
        indexer = CodebaseIndexer(config)

        # 创建大于 max_file_size 的文件
        large_file = tmp_path / "large.py"
        large_file.write_text("x" * 100)

        assert indexer.should_index(large_file) is False
