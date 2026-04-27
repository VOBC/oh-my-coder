from __future__ import annotations
"""
代码库索引器

功能：
1. 扫描项目文件
2. 解析代码结构
3. 生成嵌入向量
4. 构建向量索引
"""

import ast
import asyncio
import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any


class CodeElementType(str, Enum):
    """代码元素类型"""

    MODULE = "module"
    CLASS = "class"
    FUNCTION = "function"
    METHOD = "method"
    VARIABLE = "variable"
    IMPORT = "import"
    CONSTANT = "constant"
    OTHER = "other"


class ProgrammingLanguage(str, Enum):
    """编程语言"""

    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    JAVA = "java"
    GO = "go"
    RUST = "rust"
    CPP = "cpp"
    C = "c"
    UNKNOWN = "unknown"


@dataclass
class CodeElement:
    """代码元素"""

    id: str
    name: str
    type: CodeElementType
    file_path: str
    start_line: int
    end_line: int
    source_code: str
    docstring: str | None = None
    signature: str | None = None
    parent: str | None = None  # 父元素 ID
    children: list[str] = field(default_factory=list)
    embedding: list[float] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class FileIndex:
    """文件索引"""

    file_path: str
    language: ProgrammingLanguage
    elements: list[CodeElement]
    imports: list[str]
    exports: list[str]
    dependencies: list[str]
    hash: str
    last_modified: datetime
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class IndexConfig:
    """索引配置"""

    root_path: Path
    exclude_patterns: list[str] = field(
        default_factory=lambda: [
            "node_modules",
            ".git",
            "__pycache__",
            ".venv",
            "venv",
            "*.pyc",
            "*.pyo",
            "*.so",
            "*.dylib",
            "*.dll",
            "dist",
            "build",
            ".eggs",
            "*.egg-info",
            ".pytest_cache",
            ".ruff_cache",
            ".mypy_cache",
        ]
    )
    include_patterns: list[str] = field(
        default_factory=lambda: [
            "*.py",
            "*.js",
            "*.ts",
            "*.java",
            "*.go",
            "*.rs",
            "*.cpp",
            "*.c",
            "*.h",
            "*.hpp",
            "*.json",
            "*.yaml",
            "*.yml",
            "*.toml",
            "*.md",
        ]
    )
    max_file_size: int = 100 * 1024  # 100KB
    max_elements: int = 10000
    embedding_model: str = "text-embedding-3-small"
    chunk_size: int = 500
    chunk_overlap: int = 50


class PythonParser:
    """Python 代码解析器"""

    def parse(self, source: str, file_path: str) -> list[CodeElement]:
        """解析 Python 源码"""
        elements = []

        try:
            tree = ast.parse(source)
        except SyntaxError:
            return elements

        source_lines = source.split("\n")

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                element = self._parse_function(node, source_lines, file_path)
                if element:
                    elements.append(element)

            elif isinstance(node, ast.ClassDef):
                element = self._parse_class(node, source_lines, file_path)
                if element:
                    elements.append(element)

        return elements

    def _parse_function(
        self, node: ast.FunctionDef, source_lines: list[str], file_path: str
    ) -> CodeElement | None:
        """解析函数定义"""
        start_line = node.lineno
        end_line = node.end_lineno or start_line
        source_code = "\n".join(source_lines[start_line - 1 : end_line])

        # 构建签名
        args = []
        for arg in node.args.args:
            arg_str = arg.arg
            if arg.annotation:
                arg_str += f": {ast.unparse(arg.annotation)}"
            args.append(arg_str)

        returns = ""
        if node.returns:
            returns = f" -> {ast.unparse(node.returns)}"

        signature = f"def {node.name}({', '.join(args)}){returns}"

        # 提取 docstring
        docstring = ast.get_docstring(node)

        return CodeElement(
            id=self._generate_id(file_path, node.name, start_line),
            name=node.name,
            type=CodeElementType.FUNCTION,
            file_path=file_path,
            start_line=start_line,
            end_line=end_line,
            source_code=source_code,
            docstring=docstring,
            signature=signature,
        )

    def _parse_class(
        self, node: ast.ClassDef, source_lines: list[str], file_path: str
    ) -> CodeElement | None:
        """解析类定义"""
        start_line = node.lineno
        end_line = node.end_lineno or start_line
        source_code = "\n".join(source_lines[start_line - 1 : end_line])

        # 构建签名
        bases = [ast.unparse(base) for base in node.bases]
        signature = f"class {node.name}"
        if bases:
            signature += f"({', '.join(bases)})"

        # 提取 docstring
        docstring = ast.get_docstring(node)

        return CodeElement(
            id=self._generate_id(file_path, node.name, start_line),
            name=node.name,
            type=CodeElementType.CLASS,
            file_path=file_path,
            start_line=start_line,
            end_line=end_line,
            source_code=source_code,
            docstring=docstring,
            signature=signature,
        )

    def _generate_id(self, file_path: str, name: str, line: int) -> str:
        """生成元素 ID（非密码用途）"""
        hash_input = f"{file_path}:{name}:{line}"
        return hashlib.sha256(hash_input.encode()).hexdigest()[:12]


class CodebaseIndexer:
    """
    代码库索引器

    功能：
    1. 扫描项目文件
    2. 解析代码结构
    3. 生成嵌入向量
    4. 构建向量索引
    """

    LANGUAGE_EXTENSIONS = {
        ".py": ProgrammingLanguage.PYTHON,
        ".js": ProgrammingLanguage.JAVASCRIPT,
        ".ts": ProgrammingLanguage.TYPESCRIPT,
        ".java": ProgrammingLanguage.JAVA,
        ".go": ProgrammingLanguage.GO,
        ".rs": ProgrammingLanguage.RUST,
        ".cpp": ProgrammingLanguage.CPP,
        ".cxx": ProgrammingLanguage.CPP,
        ".cc": ProgrammingLanguage.CPP,
        ".c": ProgrammingLanguage.C,
        ".h": ProgrammingLanguage.C,
        ".hpp": ProgrammingLanguage.CPP,
    }

    def __init__(self, config: IndexConfig, embedding_client=None):
        """
        Args:
            config: 索引配置
            embedding_client: 嵌入向量客户端（可选）
        """
        self.config = config
        self.embedding_client = embedding_client
        self.file_indices: dict[str, FileIndex] = {}
        self.element_index: dict[str, CodeElement] = {}
        self._parsers = {
            ProgrammingLanguage.PYTHON: PythonParser(),
        }

    def should_index(self, file_path: Path) -> bool:
        """判断是否应该索引该文件"""
        # 检查文件大小
        if file_path.stat().st_size > self.config.max_file_size:
            return False

        # 检查排除模式
        for pattern in self.config.exclude_patterns:
            if pattern in str(file_path):
                return False

        # 检查包含模式
        return any(file_path.match(pattern) for pattern in self.config.include_patterns)

    def detect_language(self, file_path: Path) -> ProgrammingLanguage:
        """检测文件语言"""
        ext = file_path.suffix.lower()
        return self.LANGUAGE_EXTENSIONS.get(ext, ProgrammingLanguage.UNKNOWN)

    def index_file(self, file_path: Path) -> FileIndex | None:
        """索引单个文件"""
        try:
            source = file_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return None

        language = self.detect_language(file_path)
        file_hash = hashlib.sha256(source.encode()).hexdigest()  # 非密码用途
        relative_path = str(file_path.relative_to(self.config.root_path))

        # 解析代码元素
        elements = []
        parser = self._parsers.get(language)
        if parser:
            elements = parser.parse(source, relative_path)

        # 提取导入
        imports = self._extract_imports(source, language)

        # 更新元素索引
        for element in elements:
            self.element_index[element.id] = element

        file_index = FileIndex(
            file_path=relative_path,
            language=language,
            elements=elements,
            imports=imports,
            exports=[],  # TODO: 实现导出提取
            dependencies=[],
            hash=file_hash,
            last_modified=datetime.fromtimestamp(file_path.stat().st_mtime),
        )

        self.file_indices[relative_path] = file_index
        return file_index

    def index_directory(self, progress_callback=None) -> dict[str, FileIndex]:
        """索引整个目录"""
        root = self.config.root_path

        # 收集所有文件
        files = []
        for ext in self.config.include_patterns:
            files.extend(root.rglob(ext.lstrip("*.")))

        # 过滤文件
        valid_files = [f for f in files if self.should_index(f)]

        # 索引文件
        total = len(valid_files)
        for i, file_path in enumerate(valid_files):
            self.index_file(file_path)

            if progress_callback:
                progress_callback(i + 1, total, file_path)

        return self.file_indices

    async def generate_embeddings(self, batch_size: int = 100) -> None:
        """为所有元素生成嵌入向量"""
        if not self.embedding_client:
            return

        elements = list(self.element_index.values())

        for i in range(0, len(elements), batch_size):
            batch = elements[i : i + batch_size]
            texts = [self._element_to_text(e) for e in batch]

            # 批量生成嵌入
            embeddings = await self._batch_embed(texts)

            for j, element in enumerate(batch):
                element.embedding = embeddings[j]

            # 避免 API 限流
            await asyncio.sleep(0.1)

    def _element_to_text(self, element: CodeElement) -> str:
        """将元素转换为嵌入文本"""
        parts = [
            f"File: {element.file_path}",
            f"Type: {element.type.value}",
            f"Name: {element.name}",
        ]

        if element.signature:
            parts.append(f"Signature: {element.signature}")

        if element.docstring:
            parts.append(f"Docstring: {element.docstring}")

        # 添加源码（截断）
        source = element.source_code
        if len(source) > 500:
            source = source[:500] + "..."
        parts.append(f"Source:\n{source}")

        return "\n".join(parts)

    async def _batch_embed(self, texts: list[str]) -> list[list[float]]:
        """批量生成嵌入"""
        if not self.embedding_client:
            return [[] for _ in texts]

        # TODO: 调用实际嵌入 API
        return [[] for _ in texts]

    def _extract_imports(self, source: str, language: ProgrammingLanguage) -> list[str]:
        """提取导入语句"""
        imports = []

        if language == ProgrammingLanguage.PYTHON:
            # 提取 Python import
            pattern = r"^(?:from|import)\s+([^\s]+)"
            matches = re.findall(pattern, source, re.MULTILINE)
            imports.extend(matches)

        return imports

    def get_stats(self) -> dict[str, Any]:
        """获取索引统计"""
        return {
            "files_indexed": len(self.file_indices),
            "elements_indexed": len(self.element_index),
            "languages": self._count_by_language(),
            "element_types": self._count_by_type(),
        }

    def _count_by_language(self) -> dict[str, int]:
        """按语言统计"""
        counts = {}
        for file_index in self.file_indices.values():
            lang = file_index.language.value
            counts[lang] = counts.get(lang, 0) + 1
        return counts

    def _count_by_type(self) -> dict[str, int]:
        """按元素类型统计"""
        counts = {}
        for element in self.element_index.values():
            type_name = element.type.value
            counts[type_name] = counts.get(type_name, 0) + 1
        return counts

    def save(self, path: Path) -> None:
        """保存索引"""
        path.mkdir(parents=True, exist_ok=True)

        # 保存文件索引
        file_index_path = path / "files.json"
        with open(file_index_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    fp: {
                        "file_path": fi.file_path,
                        "language": fi.language.value,
                        "imports": fi.imports,
                        "hash": fi.hash,
                        "last_modified": fi.last_modified.isoformat(),
                    }
                    for fp, fi in self.file_indices.items()
                },
                f,
                indent=2,
                ensure_ascii=False,
            )

        # 保存元素索引
        element_index_path = path / "elements.json"
        with open(element_index_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    eid: {
                        "id": e.id,
                        "name": e.name,
                        "type": e.type.value,
                        "file_path": e.file_path,
                        "start_line": e.start_line,
                        "end_line": e.end_line,
                        "source_code": e.source_code,
                        "docstring": e.docstring,
                        "signature": e.signature,
                    }
                    for eid, e in self.element_index.items()
                },
                f,
                indent=2,
                ensure_ascii=False,
            )

    def load(self, path: Path) -> None:
        """加载索引"""
        file_index_path = path / "files.json"
        if file_index_path.exists():
            with open(file_index_path, encoding="utf-8") as f:
                json.load(f)  # TODO: 反序列化

        element_index_path = path / "elements.json"
        if element_index_path.exists():
            with open(element_index_path, encoding="utf-8") as f:
                json.load(f)  # TODO: 反序列化
