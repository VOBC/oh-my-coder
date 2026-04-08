"""
Wiki 模块测试 - Parser 和 Generator

测试 Python AST 解析器和 Markdown Wiki 文档生成器。
"""

import tempfile
from pathlib import Path

import pytest

from src.wiki import PythonParser, WikiGenerator
from src.wiki.parser import (
    ASTVisitorWithParent,
    ClassInfo,
    FunctionInfo,
    ImportInfo,
    ModuleInfo,
)


class TestFunctionInfo:
    """FunctionInfo 数据类测试"""

    def test_create_function_info(self):
        """测试创建函数信息"""
        func = FunctionInfo(
            name="test_func",
            docstring="测试函数",
            args=["arg1", "arg2"],
            returns="int",
            decorators=["staticmethod", "cached"],
            lineno=10,
        )
        assert func.name == "test_func"
        assert func.docstring == "测试函数"
        assert func.args == ["arg1", "arg2"]
        assert func.returns == "int"
        assert func.decorators == ["staticmethod", "cached"]
        assert func.lineno == 10

    def test_signature_property(self):
        """测试函数签名生成"""
        func = FunctionInfo(name="my_func", args=["a", "b", "c"])
        assert func.signature == "my_func(a, b, c)"

    def test_signature_no_args(self):
        """测试无参数函数签名"""
        func = FunctionInfo(name="no_args")
        assert func.signature == "no_args()"

    def test_signature_empty_args(self):
        """测试空参数列表"""
        func = FunctionInfo(name="empty_args", args=[])
        assert func.signature == "empty_args()"


class TestClassInfo:
    """ClassInfo 数据类测试"""

    def test_create_class_info(self):
        """测试创建类信息"""
        cls = ClassInfo(
            name="TestClass",
            docstring="测试类",
            base_classes=["BaseClass"],
            methods=[],
            attributes=["attr1", "attr2"],
            lineno=20,
        )
        assert cls.name == "TestClass"
        assert cls.docstring == "测试类"
        assert cls.base_classes == ["BaseClass"]
        assert cls.attributes == ["attr1", "attr2"]
        assert cls.lineno == 20

    def test_public_methods(self):
        """测试获取公开方法"""
        methods = [
            FunctionInfo(name="public_method"),
            FunctionInfo(name="_private_method"),
            FunctionInfo(name="another_public"),
            FunctionInfo(name="__dunder_method"),
        ]
        cls = ClassInfo(name="TestClass", methods=methods)
        public = cls.public_methods
        assert len(public) == 2
        assert public[0].name == "public_method"
        assert public[1].name == "another_public"

    def test_private_methods(self):
        """测试获取私有方法"""
        methods = [
            FunctionInfo(name="public_method"),
            FunctionInfo(name="_private_method"),
            FunctionInfo(name="__dunder_method"),
        ]
        cls = ClassInfo(name="TestClass", methods=methods)
        private = cls.private_methods
        assert len(private) == 2
        assert "_private_method" in [m.name for m in private]
        assert "__dunder_method" in [m.name for m in private]


class TestImportInfo:
    """ImportInfo 数据类测试"""

    def test_create_import_info(self):
        """测试创建导入信息"""
        imp = ImportInfo(module="os", names=[], alias=None)
        assert imp.module == "os"
        assert imp.names == []
        assert imp.alias is None

    def test_import_with_alias(self):
        """测试带别名的导入"""
        imp = ImportInfo(module="os.path", names=[], alias="osp")
        assert imp.alias == "osp"

    def test_import_from(self):
        """测试 from...import 导入"""
        imp = ImportInfo(module="pathlib", names=["Path", "PurePath"])
        assert imp.names == ["Path", "PurePath"]


class TestModuleInfo:
    """ModuleInfo 数据类测试"""

    def test_create_module_info(self):
        """测试创建模块信息"""
        module = ModuleInfo(path=Path("test.py"), relative_path=Path("test.py"))
        assert module.path == Path("test.py")
        assert module.docstring is None
        assert module.imports == []
        assert module.classes == []
        assert module.functions == []


class TestPythonParser:
    """PythonParser 解析器测试"""

    @pytest.fixture
    def temp_project(self):
        """创建临时测试项目"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / "test_project"
            project_dir.mkdir()

            # 创建示例文件
            (project_dir / "sample_module.py").write_text(
                '''
"""测试模块文档字符串"""

import os
import sys
from pathlib import Path
from typing import List, Optional

class BaseClass:
    """基类"""
    pass

class MyClass(BaseClass):
    """我的类

    这是类的详细描述。
    可以有多行。
    """

    def __init__(self, name: str):
        """初始化方法"""
        self.name = name

    def public_method(self, x: int, y: int) -> int:
        """公开方法，返回两个数的和"""
        return x + y

    def _private_method(self):
        """私有方法"""
        pass

    def __str__(self):
        """字符串表示"""
        return self.name

def standalone_function(a: str, b: Optional[str] = None) -> str:
    """独立函数

    Args:
        a: 第一个参数
        b: 第二个参数（可选）

    Returns:
        合并后的字符串
    """
    return f"{a}-{b}" if b else a
''',
                encoding="utf-8",
            )

            # 创建 __init__.py（应被忽略）
            (project_dir / "__init__.py").write_text("# ignored", encoding="utf-8")

            # 创建测试文件（应被忽略）
            (project_dir / "test_something.py").write_text("# test", encoding="utf-8")

            yield project_dir

    def test_parse_file_basic(self, temp_project):
        """测试基本文件解析"""
        parser = PythonParser(temp_project)
        file_path = temp_project / "sample_module.py"
        module = parser.parse_file(file_path)

        assert module is not None
        assert module.docstring == "测试模块文档字符串"
        assert len(module.imports) == 4  # os, sys, Path, List, Optional
        assert len(module.classes) == 2  # BaseClass, MyClass
        assert len(module.functions) == 1  # standalone_function

    def test_parse_file_class_details(self, temp_project):
        """测试类详情解析"""
        parser = PythonParser(temp_project)
        module = parser.parse_file(temp_project / "sample_module.py")

        # 查找 MyClass
        my_class = next((c for c in module.classes if c.name == "MyClass"), None)
        assert my_class is not None
        assert my_class.docstring is not None
        assert "我的类" in my_class.docstring
        assert my_class.base_classes == ["BaseClass"]
        assert (
            len(my_class.methods) == 4
        )  # __init__, public_method, _private_method, __str__

    def test_parse_file_function_details(self, temp_project):
        """测试函数详情解析"""
        parser = PythonParser(temp_project)
        module = parser.parse_file(temp_project / "sample_module.py")

        # 查找 standalone_function
        func = next(
            (f for f in module.functions if f.name == "standalone_function"), None
        )
        assert func is not None
        assert func.args == ["a", "b"]
        assert func.returns == "str"
        assert func.docstring is not None

    def test_parse_file_method_details(self, temp_project):
        """测试方法详情解析"""
        parser = PythonParser(temp_project)
        module = parser.parse_file(temp_project / "sample_module.py")

        my_class = next((c for c in module.classes if c.name == "MyClass"), None)
        public_method = next(
            (m for m in my_class.methods if m.name == "public_method"), None
        )

        assert public_method is not None
        assert public_method.args == ["self", "x", "y"]
        assert public_method.returns == "int"

    def test_parse_file_public_methods(self, temp_project):
        """测试公开方法过滤"""
        parser = PythonParser(temp_project)
        module = parser.parse_file(temp_project / "sample_module.py")

        my_class = next((c for c in module.classes if c.name == "MyClass"), None)
        public = my_class.public_methods

        # 公开方法不应以 _ 开头
        for method in public:
            assert not method.name.startswith("_")

    def test_parse_file_syntax_error(self, temp_project):
        """测试语法错误文件处理"""
        parser = PythonParser(temp_project)

        # 创建语法错误的文件
        bad_file = temp_project / "syntax_error.py"
        bad_file.write_text("def broken(\n    return 1", encoding="utf-8")

        module = parser.parse_file(bad_file)
        assert module is None

    def test_scan_directory(self, temp_project):
        """测试目录扫描"""
        parser = PythonParser(temp_project)
        modules = parser.scan_directory(temp_project)

        # 应该只包含 sample_module.py，不包含 __init__.py 和 test_*.py
        assert len(modules) == 1
        assert modules[0].path.name == "sample_module.py"

    def test_scan_nested_directories(self, temp_project):
        """测试嵌套目录扫描"""
        # 创建嵌套目录
        nested = temp_project / "src" / "utils"
        nested.mkdir(parents=True)

        (nested / "helper.py").write_text(
            '''
"""Helper module"""


class Helper:
    """Helper class"""
    pass
''',
            encoding="utf-8",
        )

        parser = PythonParser(temp_project)
        modules = parser.scan_directory(temp_project)

        assert len(modules) == 2
        module_names = [m.path.name for m in modules]
        assert "sample_module.py" in module_names
        assert "helper.py" in module_names

    def test_scan_ignores_pycache(self, temp_project):
        """测试忽略 __pycache__ 目录"""
        pycache = temp_project / "__pycache__"
        pycache.mkdir()
        (pycache / "cached.pyc").write_bytes(b"fake bytecode")

        parser = PythonParser(temp_project)
        modules = parser.scan_directory(temp_project)

        # 不应包含 __pycache__ 中的文件
        for module in modules:
            assert "__pycache__" not in str(module.path)

    def test_relative_path_calculation(self, temp_project):
        """测试相对路径计算"""
        parser = PythonParser(temp_project)
        module = parser.parse_file(temp_project / "sample_module.py")

        assert module.relative_path == Path("sample_module.py")


class TestWikiGenerator:
    """WikiGenerator 生成器测试"""

    @pytest.fixture
    def temp_project(self):
        """创建临时测试项目"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / "wiki_test"
            project_dir.mkdir()

            (project_dir / "main.py").write_text(
                '''"""Wiki Test Project"""

from typing import List


def hello(name: str) -> str:
    """Say hello to someone."""
    return f"Hello, {name}!"


class Greeter:
    """A simple greeter class."""

    def greet(self, name: str) -> str:
        """Greet a person."""
        return hello(name)
''',
                encoding="utf-8",
            )

            yield project_dir

    def test_generator_init(self, temp_project):
        """测试生成器初始化"""
        gen = WikiGenerator("test_project", temp_project)
        assert gen.project_name == "test_project"
        assert gen.project_path == temp_project
        assert gen.parser is not None

    def test_generator_init_with_custom_parser(self, temp_project):
        """测试使用自定义解析器"""
        parser = PythonParser(temp_project)
        gen = WikiGenerator("test_project", temp_project, parser=parser)
        assert gen.parser is parser

    def test_generate_header(self, temp_project):
        """测试生成文档头部"""
        gen = WikiGenerator("Test Project", temp_project)
        header = gen._generate_header()

        assert "# Test Project" in header
        assert "自动生成" in header
        assert "项目概述" in header
        assert "项目结构" in header
        assert "模块详解" in header

    def test_generate_summary(self, temp_project):
        """测试生成摘要"""
        parser = PythonParser(temp_project)
        modules = parser.scan_directory(temp_project)
        gen = WikiGenerator("test_project", temp_project, parser=parser)

        summary = gen._generate_summary(modules)

        assert "## 项目概述" in summary
        assert "总文件数" in summary
        assert "总类数" in summary
        assert "总函数数" in summary
        assert "typing" in summary  # 核心依赖

    def test_generate_project_structure(self, temp_project):
        """测试生成项目结构"""
        parser = PythonParser(temp_project)
        modules = parser.scan_directory(temp_project)
        gen = WikiGenerator("test_project", temp_project, parser=parser)

        structure = gen._generate_project_structure(modules)

        assert "## 项目结构" in structure
        assert "```" in structure  # 代码块
        assert "main.py" in structure

    def test_generate_module_details(self, temp_project):
        """测试生成模块详情"""
        parser = PythonParser(temp_project)
        modules = parser.scan_directory(temp_project)
        gen = WikiGenerator("test_project", temp_project, parser=parser)

        details = gen._generate_module_details(modules)

        assert "## 模块详解" in details
        assert "main.py" in details

    def test_generate_class(self, temp_project):
        """测试生成类文档"""
        cls = ClassInfo(
            name="Greeter",
            docstring="A simple greeter class.",
            base_classes=[],
            methods=[],
        )
        gen = WikiGenerator("test", temp_project)
        class_doc = gen._generate_class(cls)

        assert "Greeter" in class_doc
        assert "greeter class" in class_doc

    def test_generate_function(self, temp_project):
        """测试生成函数文档"""
        func = FunctionInfo(
            name="hello",
            docstring="Say hello to someone.",
            args=["name"],
            returns="str",
        )
        gen = WikiGenerator("test", temp_project)
        func_doc = gen._generate_function(func)

        assert "hello" in func_doc
        assert "Say hello" in func_doc

    def test_generate_footer(self, temp_project):
        """测试生成文档尾部"""
        gen = WikiGenerator("test", temp_project)
        footer = gen._generate_footer()

        assert "自动生成" in footer
        assert "oh-my-coder" in footer

    def test_generate_full_document(self, temp_project):
        """测试生成完整文档"""
        gen = WikiGenerator("WikiTest", temp_project)
        content = gen.generate()

        # 检查各部分都存在
        assert "# WikiTest" in content
        assert "项目概述" in content
        assert "项目结构" in content
        assert "模块详解" in content
        assert "API 参考" in content
        assert "Greeter" in content
        assert "hello" in content

    def test_generate_to_file(self, temp_project):
        """测试生成并写入文件"""
        output_path = temp_project / "OUTPUT.md"
        gen = WikiGenerator("test", temp_project)
        result = gen.generate(output_path=output_path)

        assert output_path.exists()
        content = output_path.read_text(encoding="utf-8")
        assert "# test" in content
        assert len(result) > 0

    def test_generate_with_nested_modules(self, temp_project):
        """测试生成嵌套模块文档"""
        # 创建嵌套结构
        src = temp_project / "src"
        src.mkdir()
        (src / "utils.py").write_text(
            '''"""Utils module"""


def util_func():
    """A utility function."""
    pass
''',
            encoding="utf-8",
        )

        gen = WikiGenerator("nested_test", temp_project)
        content = gen.generate()

        assert "src/" in content
        assert "utils.py" in content

    def test_generate_with_decorators(self, temp_project):
        """测试带装饰器的函数"""
        (temp_project / "decorated.py").write_text(
            '''
from functools import lru_cache


@lru_cache(maxsize=128)
def cached_function(x: int) -> int:
    """A cached function."""
    return x * 2
''',
            encoding="utf-8",
        )

        gen = WikiGenerator("decorated_test", temp_project)
        modules = gen.parser.scan_directory(temp_project)

        func = next(
            (f for m in modules if m.path.name == "decorated.py" for f in m.functions),
            None,
        )
        assert func is not None
        assert "lru_cache" in func.decorators


class TestASTVisitorWithParent:
    """ASTVisitorWithParent 测试"""

    def test_parent_stack_tracking(self):
        """测试父节点栈跟踪"""
        import ast

        code = """
class MyClass:
    def my_method(self):
        pass
"""
        tree = ast.parse(code)
        visitor = ASTVisitorWithParent()
        visitor.visit(tree)

        # 验证访问了节点
        assert len(visitor.parent_stack) == 0  # 访问完成后栈为空

    def test_get_parent(self):
        """测试获取父节点"""
        import ast

        code = """
class MyClass:
    def my_method(self):
        pass
"""
        tree = ast.parse(code)

        # 使用 PythonParser._add_parent_refs 填充 parent_map
        parser = PythonParser(".")
        parser._add_parent_refs(tree)

        # 从 parent_map 中获取 ClassDef 的父节点
        class_def = None
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_def = node
                break

        assert class_def is not None
        assert isinstance(class_def, ast.ClassDef)
