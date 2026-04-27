"""测试 Skill 注册中心"""

import tempfile
from pathlib import Path
from typing import Any

from src.skills import Skill, SkillRegistry, SkillResult


class TestSkillResult:
    """SkillResult 数据结构测试"""

    def test_success_result(self):
        result = SkillResult(success=True, output="done", duration_ms=42.0)
        assert result.success is True
        assert result.output == "done"
        assert result.duration_ms == 42.0

    def test_error_result(self):
        result = SkillResult(success=False, error="not found")
        assert result.success is False
        assert result.error == "not found"

    def test_as_dict(self):
        result = SkillResult(success=True, output="x", metadata={"k": "v"})
        d = result.as_dict()
        assert d["success"] is True
        assert d["output"] == "x"
        assert d["metadata"] == {"k": "v"}


class TestSkill:
    """Skill 数据结构测试"""

    def test_basic_skill(self):
        def dummy(code: str, ctx: dict[str, Any]) -> SkillResult:
            return SkillResult(success=True, output="ok")

        skill = Skill(name="dummy", description="A test skill", func=dummy)
        assert skill.name == "dummy"
        assert skill.source == "builtin"

    def test_auto_description_from_docstring(self):
        """描述为空时，自动从函数 docstring 提取"""

        def my_skill(code: str, ctx: dict[str, Any]) -> SkillResult:
            """This is the auto description."""
            return SkillResult(success=True)

        skill = Skill(name="auto", description="", func=my_skill)
        assert skill.description == "This is the auto description."


class TestSkillRegistryBuiltins:
    """内置 Skill 测试"""

    def setup_method(self):
        self.registry = SkillRegistry()

    def test_builtin_skills_registered(self):
        """三个内置 Skill 都已注册"""
        names = [s.name for s in self.registry.list_all()]
        assert "review" in names
        assert "test" in names
        assert "doc" in names

    def test_list_builtin_only(self):
        skills = self.registry.list_builtin()
        assert all(s.source == "builtin" for s in skills)
        assert len(skills) == 3

    def test_get_skill(self):
        skill = self.registry.get("review")
        assert skill is not None
        assert skill.name == "review"

    def test_get_nonexistent(self):
        assert self.registry.get("nonexistent") is None

    def test_unregister_builtin(self):
        assert self.registry.unregister("review") is True
        assert self.registry.get("review") is None
        # 注销后剩余 2 个内置 Skill（test 和 doc）
        assert len(self.registry.list_builtin()) == 2

    def test_register_custom_skill(self):
        def my_func(code: str, ctx: dict[str, Any]) -> SkillResult:
            return SkillResult(success=True, output="custom")

        custom = Skill(
            name="mine", description="my skill", func=my_func, source="custom"
        )
        self.registry.register(custom)
        assert self.registry.get("mine") is not None


class TestReviewSkill:
    """内置 /review Skill 测试"""

    def setup_method(self):
        self.registry = SkillRegistry()

    def test_review_clean_code(self):
        code = "def hello():\n    print('hi')\n"
        result = self.registry.run("review", code)
        assert result.success is True
        assert "问题" in result.output or "0" in result.output

    def test_review_detects_long_lines(self):
        # 行长度超过 120 字符应被检测
        code = "x = " + '"'.join(["a"] * 200) + '"' + chr(10)
        result = self.registry.run("review", code)
        assert result.success is True
        assert len(result.metadata.get("issues", [])) >= 1

    def test_review_detects_eval(self):
        code = "result = eval('1 + 1')\n"
        result = self.registry.run("review", code)
        assert result.success is True
        issues = result.metadata.get("issues", [])
        assert any("eval" in issue for issue in issues)

    def test_review_detects_shell_true(self):
        code = "subprocess.run('ls', shell=True)\n"
        result = self.registry.run("review", code)
        assert result.success is True
        issues = result.metadata.get("issues", [])
        assert any("shell=True" in issue for issue in issues)


class TestTestSkill:
    """内置 /test Skill 测试"""

    def setup_method(self):
        self.registry = SkillRegistry()

    def test_test_generates_content(self):
        code = "def add(a, b):\n    return a + b\n"
        result = self.registry.run("test", code)
        assert result.success is True
        assert "def test_" in result.output or "add" in result.output

    def test_test_metadata(self):
        code = "def foo():\n    pass\ndef bar():\n    pass\n"
        result = self.registry.run("test", code)
        assert result.metadata.get("functions_found", 0) >= 2


class TestDocSkill:
    """内置 /doc Skill 测试"""

    def setup_method(self):
        self.registry = SkillRegistry()

    def test_doc_generates_markdown(self):
        code = '"""Module docstring."""\n\ndef public_api(x):\n    """Public API."""\n    pass\n'
        result = self.registry.run("doc", code, {"file_path": "mymodule.py"})
        assert result.success is True
        assert "#" in result.output  # Markdown heading
        assert "public_api" in result.output


class TestSkillRegistryExecution:
    """Skill 执行测试"""

    def setup_method(self):
        self.registry = SkillRegistry()

    def test_run_nonexistent(self):
        result = self.registry.run("does_not_exist", "code")
        assert result.success is False
        assert "not found" in result.error

    def test_run_with_context(self):
        result = self.registry.run(
            "doc",
            "def foo():\n    pass\n",
            {"file_path": "test.py", "module_name": "test"},
        )
        assert result.success is True
        assert "foo" in result.output

    def test_run_interactive(self):
        """run_interactive 支持 /name 语法"""
        result = self.registry.run_interactive("/review", "x = 1\n")
        assert result.success is True
        result2 = self.registry.run_interactive("review", "x = 1\n")
        assert result2.success is True


class TestCustomSkillsLoading:
    """自定义 Skill 加载测试"""

    def setup_method(self):
        self.registry = SkillRegistry()
        self.tmpdir = tempfile.TemporaryDirectory()
        self.tmppath = Path(self.tmpdir.name)

    def teardown_method(self):
        self.tmpdir.cleanup()

    def test_load_skill_function_pattern(self):
        """加载 skill_xxx 函数"""
        skill_file = self.tmppath / "my_skills.py"
        skill_file.write_text(
            """
def skill_lint(code: str, ctx: dict):
    '''Lints code.'''
    from src.skills import SkillResult
    lines = code.splitlines()
    return SkillResult(success=True, output=f'Checked {len(lines)} lines')

def unrelated():
    pass
"""
        )
        self.registry.set_custom_dir(self.tmppath)
        count = self.registry.load_custom_skills()
        assert count >= 1
        skill = self.registry.get("lint")
        assert skill is not None
        assert skill.source == "custom"

    def test_load_skill_constant_pattern(self):
        """加载 SKILL 常量"""
        skill_file = self.tmppath / "static_skill.py"
        skill_file.write_text(
            """
from src.skills import Skill, SkillResult

def stats(code: str, ctx: dict):
    return SkillResult(success=True, output=str(len(code)))

SKILL = Skill(name='stats', description='Count chars', func=stats)
"""
        )
        self.registry.set_custom_dir(self.tmppath)
        self.registry.load_custom_skills()
        skill = self.registry.get("stats")
        assert skill is not None
        assert skill.source == "custom"

    def test_nonexistent_dir_returns_zero(self):
        """自定义目录不存在时返回 0"""
        self.registry.set_custom_dir(Path("/nonexistent/path"))
        count = self.registry.load_custom_skills()
        assert count == 0

    def test_reload_resets_flag(self):
        """重设目录后重新加载"""
        self.registry.set_custom_dir(self.tmppath)
        self.registry._loaded_custom = True  # 模拟已加载
        self.registry.set_custom_dir(Path("/tmp"))  # 重新设置
        assert self.registry._loaded_custom is False


class TestDisplayList:
    """display_list 测试（无异常即通过）"""

    def setup_method(self):
        self.registry = SkillRegistry()

    def test_display_no_crash(self):
        self.registry.display_list()  # 纯 UI，捕获即可
