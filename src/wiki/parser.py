from __future__ import annotations
"""
Wiki Parser - Python AST 解析器

使用 Python ast 模块解析代码结构，提取：
- 模块文档字符串
- 导入语句
- 类定义（名称、文档、方法）
- 函数定义（名称、文档、参数）
"""

import ast
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class FunctionInfo:
    """函数信息"""

    name: str
    docstring: str | None = None
    args: list[str] = field(default_factory=list)
    returns: str | None = None
    decorators: list[str] = field(default_factory=list)
    lineno: int = 0

    @property
    def signature(self) -> str:
        """生成函数签名"""
        params = ", ".join(self.args)
        return f"{self.name}({params})"


@dataclass
class ClassInfo:
    """类信息"""

    name: str
    docstring: str | None = None
    base_classes: list[str] = field(default_factory=list)
    methods: list[FunctionInfo] = field(default_factory=list)
    attributes: list[str] = field(default_factory=list)
    lineno: int = 0

    @property
    def public_methods(self) -> list[FunctionInfo]:
        """获取公开方法（不以 _ 开头）"""
        return [m for m in self.methods if not m.name.startswith("_")]

    @property
    def private_methods(self) -> list[FunctionInfo]:
        """获取私有方法（以 _ 开头）"""
        return [m for m in self.methods if m.name.startswith("_")]


@dataclass
class ImportInfo:
    """导入信息"""

    module: str
    names: list[str] = field(default_factory=list)
    alias: str | None = None


@dataclass
class ModuleInfo:
    """模块信息"""

    path: Path
    relative_path: Path
    docstring: str | None = None
    imports: list[ImportInfo] = field(default_factory=list)
    classes: list[ClassInfo] = field(default_factory=list)
    functions: list[FunctionInfo] = field(default_factory=list)


class ASTVisitorWithParent(ast.NodeVisitor):
    """带父节点引用的 AST 访问器"""

    def __init__(self):
        self.parent_stack: list[ast.AST] = []

    def visit(self, node: ast.AST) -> None:
        # 先将当前节点作为父节点压栈
        self.parent_stack.append(node)
        super().visit(node)
        self.parent_stack.pop()

    def get_parent(self, node: ast.AST) -> ast.AST | None:
        """获取父节点"""
        if len(self.parent_stack) > 1:
            return self.parent_stack[-2]
        return None


class PythonParser:
    """Python 代码解析器"""

    # 需要忽略的目录
    IGNORE_DIRS = {
        "__pycache__",
        ".git",
        ".venv",
        "venv",
        "env",
        ".eggs",
        "*.egg-info",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "node_modules",
        ".tox",
        "build",
        "dist",
    }

    # 需要忽略的文件
    IGNORE_FILES = {
        "__init__.py",
        "__main__.py",
        "setup.py",
        "conftest.py",
    }

    def __init__(self, root_path: Path | str):
        """
        初始化解析器

        Args:
            root_path: 项目根目录
        """
        self.root_path = Path(root_path)

    def _add_parent_refs(self, tree: ast.AST) -> None:
        """为所有节点添加父节点引用"""

        class ParentAdder(ast.NodeVisitor):
            def __init__(self):
                self.parent_map: dict[ast.AST, ast.AST] = {}

            def visit(self, node: ast.AST) -> None:
                for child in ast.iter_child_nodes(node):
                    self.parent_map[child] = node
                    self.visit(child)

        visitor = ParentAdder()
        visitor.visit(tree)

    def parse_file(self, file_path: Path | str) -> ModuleInfo | None:
        """
        解析单个 Python 文件

        Args:
            file_path: Python 文件路径

        Returns:
            ModuleInfo 或 None（如果解析失败）
        """
        file_path = Path(file_path)

        try:
            with open(file_path, encoding="utf-8") as f:
                source = f.read()

            tree = ast.parse(source, filename=str(file_path))

            # 为所有节点添加父节点引用
            self._add_parent_refs(tree)

            # 计算相对路径
            try:
                rel_path = file_path.relative_to(self.root_path)
            except ValueError:
                rel_path = file_path

            module = ModuleInfo(
                path=file_path,
                relative_path=rel_path,
                docstring=ast.get_docstring(tree),
            )

            # 遍历顶层节点
            for node in tree.body:
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    self._visit_import(module, node)
                elif isinstance(node, ast.ClassDef):
                    class_info = self._visit_class(node)
                    if class_info:
                        module.classes.append(class_info)
                elif isinstance(node, ast.FunctionDef):
                    func_info = self._visit_function(node)
                    if func_info:
                        module.functions.append(func_info)

            return module

        except (SyntaxError, UnicodeDecodeError) as e:
            print(f"  ⚠️ 解析失败 {file_path}: {e}")
            return None

    def _visit_import(self, module: ModuleInfo, node: ast.Import | ast.ImportFrom):
        """访问导入语句"""
        if isinstance(node, ast.Import):
            for alias in node.names:
                module.imports.append(
                    ImportInfo(
                        module=alias.name,
                        alias=alias.asname,
                    )
                )
        elif isinstance(node, ast.ImportFrom):
            module_name = node.module or ""
            names = [alias.name for alias in node.names]
            module.imports.append(
                ImportInfo(
                    module=module_name,
                    names=names,
                )
            )

    def _visit_class(self, node: ast.ClassDef) -> ClassInfo | None:
        """访问类定义"""
        # 获取基类
        base_classes = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                base_classes.append(base.id)
            elif isinstance(base, ast.Attribute):
                base_classes.append(self._get_attr_name(base))

        # 获取方法
        methods = []
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                func_info = self._visit_function(item)
                if func_info:
                    methods.append(func_info)

        # 获取类属性（简单实现，只检测类级别的赋值）
        attributes = []
        for item in node.body:
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                attributes.append(item.target.id)

        return ClassInfo(
            name=node.name,
            docstring=ast.get_docstring(node),
            base_classes=base_classes,
            methods=methods,
            attributes=attributes,
            lineno=node.lineno or 0,
        )

    def _visit_function(self, node: ast.FunctionDef) -> FunctionInfo | None:
        """访问函数定义"""
        # 获取参数
        args = []
        args.extend([arg.arg for arg in node.args.args])

        # 获取装饰器
        decorators = []
        for dec in node.decorator_list:
            if isinstance(dec, ast.Name):
                decorators.append(dec.id)
            elif isinstance(dec, ast.Call) and isinstance(dec.func, ast.Name):
                decorators.append(dec.func.id)
            elif isinstance(dec, ast.Attribute):
                decorators.append(self._get_attr_name(dec))

        # 获取返回值注解
        returns = None
        if node.returns:
            if isinstance(node.returns, ast.Name):
                returns = node.returns.id
            elif isinstance(node.returns, ast.Constant):
                returns = str(node.returns.value)

        return FunctionInfo(
            name=node.name,
            docstring=ast.get_docstring(node),
            args=args,
            returns=returns,
            decorators=decorators,
            lineno=node.lineno or 0,
        )

    def _get_attr_name(self, node: ast.Attribute) -> str:
        """获取属性节点的名称"""
        parts = []
        current = node
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
        return ".".join(reversed(parts))

    def scan_directory(
        self,
        directory: Path | str,
        pattern: str = "**/*.py",
    ) -> list[ModuleInfo]:
        """
        扫描目录下的所有 Python 文件

        Args:
            directory: 目录路径
            pattern: 文件匹配模式

        Returns:
            ModuleInfo 列表
        """
        directory = Path(directory)
        modules = []

        for py_file in directory.glob(pattern):
            # 忽略测试文件
            if py_file.name.startswith("test_") or py_file.name.endswith("_test.py"):
                continue

            # 忽略指定文件
            if py_file.name in self.IGNORE_FILES:
                continue

            # 忽略指定目录
            should_ignore = False
            for part in py_file.parts:
                if part in self.IGNORE_DIRS:
                    should_ignore = True
                    break
            if should_ignore:
                continue

            # 解析文件
            module = self.parse_file(py_file)
            if module:
                modules.append(module)

        return modules
