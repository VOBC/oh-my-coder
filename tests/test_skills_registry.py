"""
Tests for src/skills/registry.py - Skill Registry

Tests cover:
- Skill and SkillResult dataclasses
- Built-in skill functions (_review_skill, _test_skill, _doc_skill)
- SkillRegistry class (registration, loading, execution)
- Global singleton get_registry()
"""

from __future__ import annotations

import pytest

from src.skills.registry import (
    Skill,
    SkillRegistry,
    SkillResult,
    get_registry,
)

# ── Fixtures ────────────────────────────────────────────────────────────

@pytest.fixture
def registry():
    """Create a fresh SkillRegistry instance"""
    return SkillRegistry()


@pytest.fixture
def sample_skill():
    """Create a sample custom skill function"""
    def custom_skill(code: str, context: dict) -> SkillResult:
        return SkillResult(success=True, output="Custom output")
    return custom_skill


@pytest.fixture
def temp_skills_dir(tmp_path):
    """Create a temporary directory for custom skills"""
    skills_dir = tmp_path / ".omc" / "skills"
    skills_dir.mkdir(parents=True)
    return skills_dir


# ── Skill Dataclass Tests ───────────────────────────────────────────────

class TestSkillDataclass:
    """Tests for Skill dataclass"""

    def test_skill_creation_minimal(self, sample_skill):
        """Test basic Skill creation"""
        skill = Skill(name="test", description="Test skill", func=sample_skill)
        assert skill.name == "test"
        assert skill.description == "Test skill"
        assert skill.source == "builtin"
        assert skill.file_path is None

    def test_skill_creation_with_all_fields(self, sample_skill, tmp_path):
        """Test Skill creation with all fields"""
        skill = Skill(
            name="custom",
            description="Custom skill",
            func=sample_skill,
            source="custom",
            file_path=tmp_path / "skill.py",
        )
        assert skill.name == "custom"
        assert skill.source == "custom"
        assert skill.file_path == tmp_path / "skill.py"

    def test_skill_post_init_with_docstring(self, sample_skill):
        """Test __post_init__ extracts description from docstring"""
        sample_skill.__doc__ = "This is a test skill\nWith details"
        skill = Skill(name="test", description="", func=sample_skill)
        assert skill.description == "This is a test skill"

    def test_skill_post_init_without_docstring(self, sample_skill):
        """Test __post_init__ with no docstring"""
        sample_skill.__doc__ = None
        skill = Skill(name="test", description="Existing desc", func=sample_skill)
        assert skill.description == "Existing desc"

    def test_skill_post_init_description_preserved(self, sample_skill):
        """Test __post_init__ preserves existing description"""
        skill = Skill(name="test", description="Predefined", func=sample_skill)
        assert skill.description == "Predefined"


# ── SkillResult Dataclass Tests ─────────────────────────────────────────

class TestSkillResultDataclass:
    """Tests for SkillResult dataclass"""

    def test_skill_result_creation_defaults(self):
        """Test SkillResult with default values"""
        result = SkillResult(success=True)
        assert result.success is True
        assert result.output == ""
        assert result.error == ""
        assert result.metadata == {}
        assert result.duration_ms == 0.0

    def test_skill_result_creation_with_all_fields(self):
        """Test SkillResult with all fields"""
        result = SkillResult(
            success=False,
            output="Some output",
            error="Some error",
            metadata={"key": "value"},
            duration_ms=123.45,
        )
        assert result.success is False
        assert result.output == "Some output"
        assert result.error == "Some error"
        assert result.metadata == {"key": "value"}
        assert result.duration_ms == 123.45

    def test_skill_result_as_dict(self):
        """Test as_dict() method"""
        result = SkillResult(
            success=True,
            output="Output",
            error="",
            metadata={"issues": ["issue1"]},
            duration_ms=50.0,
        )
        d = result.as_dict()
        assert isinstance(d, dict)
        assert d["success"] is True
        assert d["output"] == "Output"
        assert d["error"] == ""
        assert d["metadata"] == {"issues": ["issue1"]}
        assert d["duration_ms"] == 50.0


# ── Built-in Skill Function Tests ───────────────────────────────────────

class TestReviewSkill:
    """Tests for _review_skill function"""

    def test_review_skill_basic(self):
        """Test basic code review"""
        from src.skills.registry import _review_skill
        code = "def hello():\n    print('world')\n"
        result = _review_skill(code, {})
        assert result.success is True
        assert "问题" in result.output or "issues" in result.output.lower()
        assert "metadata" in result.as_dict()
        assert "issues" in result.metadata
        assert "suggestions" in result.metadata

    def test_review_skill_with_long_line(self):
        """Test detection of long lines"""
        from src.skills.registry import _review_skill
        code = "x = " + "a" * 150  # Very long line
        result = _review_skill(code, {})
        assert result.success is True
        assert any("过长" in issue or "long" in issue.lower() for issue in result.metadata["issues"])

    def test_review_skill_with_eval(self):
        """Test detection of eval() usage"""
        from src.skills.registry import _review_skill
        code = "result = eval(user_input)\n"
        result = _review_skill(code, {})
        assert result.success is True
        assert any("eval" in issue.lower() for issue in result.metadata["issues"])

    def test_review_skill_with_shell_true(self):
        """Test detection of shell=True"""
        from src.skills.registry import _review_skill
        code = "subprocess.run('ls', shell=True)\n"
        result = _review_skill(code, {})
        assert result.success is True
        assert any("shell=True" in issue for issue in result.metadata["issues"])

    def test_review_skill_empty_code(self):
        """Test review with empty code"""
        from src.skills.registry import _review_skill
        result = _review_skill("", {})
        assert result.success is True
        assert result.duration_ms >= 0


class TestTestSkill:
    """Tests for _test_skill function"""

    def test_test_skill_basic(self):
        """Test basic test generation"""
        from src.skills.registry import _test_skill
        code = "def add(a, b):\n    return a + b\n"
        result = _test_skill(code, {})
        assert result.success is True
        assert "test_" in result.output
        assert result.metadata["functions_found"] >= 0
        assert result.metadata["test_cases_generated"] >= 0

    def test_test_skill_with_multiple_functions(self):
        """Test test generation for multiple functions"""
        from src.skills.registry import _test_skill
        code = """
def func1():
    pass

def func2():
    pass

def test_existing():
    pass
"""
        result = _test_skill(code, {})
        assert result.success is True
        assert "test_func1" in result.output
        assert "test_func2" in result.output

    def test_test_skill_empty_code(self):
        """Test test generation with empty code"""
        from src.skills.registry import _test_skill
        result = _test_skill("", {})
        assert result.success is True
        assert result.metadata["functions_found"] == 0


class TestDocSkill:
    """Tests for _doc_skill function"""

    def test_doc_skill_basic(self):
        """Test basic documentation generation"""
        from src.skills.registry import _doc_skill
        code = '''
"""Module docstring"""
def hello():
    """Say hello"""
    pass
'''
        result = _doc_skill(code, {"module_name": "test_module", "file_path": "test.py"})
        assert result.success is True
        assert "# test_module" in result.output or "# test" in result.output
        assert "hello" in result.output

    def test_doc_skill_with_docstring(self):
        """Test doc generation with module docstring"""
        from src.skills.registry import _doc_skill
        code = '"""This is a module"""\n\ndef func():\n    pass\n'
        result = _doc_skill(code, {})
        assert result.success is True
        assert "Module" in result.output or "模块" in result.output

    def test_doc_skill_empty_code(self):
        """Test doc generation with empty code"""
        from src.skills.registry import _doc_skill
        result = _doc_skill("", {})
        assert result.success is True
        assert result.duration_ms >= 0


# ── SkillRegistry Tests ──────────────────────────────────────────────────

class TestSkillRegistryInit:
    """Tests for SkillRegistry initialization"""

    def test_init_creates_registry(self, registry):
        """Test registry initialization"""
        assert registry is not None
        assert isinstance(registry, SkillRegistry)

    def test_init_registers_builtin_skills(self, registry):
        """Test that built-in skills are registered on init"""
        assert len(registry.list_all()) >= 3
        assert registry.get("review") is not None
        assert registry.get("test") is not None
        assert registry.get("doc") is not None

    def test_init_builtin_skill_sources(self, registry):
        """Test that built-in skills have correct source"""
        review_skill = registry.get("review")
        assert review_skill.source == "builtin"


class TestSkillRegistryRegistration:
    """Tests for register/unregister methods"""

    def test_register_skill(self, registry, sample_skill):
        """Test registering a new skill"""
        skill = Skill(name="custom", description="Custom", func=sample_skill)
        registry.register(skill)
        assert registry.get("custom") is not None
        assert registry.get("custom").name == "custom"

    def test_register_multiple_skills(self, registry, sample_skill):
        """Test registering multiple skills"""
        for i in range(5):
            skill = Skill(name=f"skill{i}", description=f"Skill {i}", func=sample_skill)
            registry.register(skill)
        assert len(registry.list_all()) >= 5

    def test_unregister_existing_skill(self, registry):
        """Test unregistering an existing skill"""
        # Review skill exists by default
        assert registry.unregister("review") is True
        assert registry.get("review") is None

    def test_unregister_nonexistent_skill(self, registry):
        """Test unregistering a non-existent skill"""
        assert registry.unregister("nonexistent") is False

    def test_reregister_skill(self, registry, sample_skill):
        """Test re-registering a skill (overwrite)"""
        skill1 = Skill(name="test", description="Version 1", func=sample_skill)
        skill2 = Skill(name="test", description="Version 2", func=sample_skill)
        registry.register(skill1)
        registry.register(skill2)
        assert registry.get("test").description == "Version 2"


class TestSkillRegistryQuery:
    """Tests for get/list methods"""

    def test_get_existing_skill(self, registry):
        """Test getting an existing skill"""
        skill = registry.get("review")
        assert skill is not None
        assert skill.name == "review"

    def test_get_nonexistent_skill(self, registry):
        """Test getting a non-existent skill"""
        assert registry.get("nonexistent") is None

    def test_list_all_includes_builtins(self, registry):
        """Test list_all includes built-in skills"""
        all_skills = registry.list_all()
        names = [s.name for s in all_skills]
        assert "review" in names
        assert "test" in names
        assert "doc" in names

    def test_list_builtin(self, registry):
        """Test list_builtin returns only built-in skills"""
        builtin = registry.list_builtin()
        assert all(s.source == "builtin" for s in builtin)
        assert len(builtin) >= 3

    def test_list_custom_empty(self, registry):
        """Test list_custom returns empty when no custom skills"""
        assert registry.list_custom() == []


class TestSkillRegistryCustomSkills:
    """Tests for custom skill loading"""

    def test_set_custom_dir(self, registry, temp_skills_dir):
        """Test setting custom skills directory"""
        registry.set_custom_dir(temp_skills_dir)
        assert registry._custom_skills_dir == temp_skills_dir
        assert registry._loaded_custom is False

    def test_load_custom_skills_no_dir(self, registry):
        """Test loading when directory doesn't exist"""
        count = registry.load_custom_skills()
        assert count == 0

    def test_load_custom_skills_from_dir(self, registry, temp_skills_dir):
        """Test loading custom skills from directory"""
        # Create a custom skill file
        skill_file = temp_skills_dir / "my_skill.py"
        skill_file.write_text("""
from src.skills.registry import Skill, SkillResult

def skill_my_custom(code: str, context: dict) -> SkillResult:
    return SkillResult(success=True, output="Custom skill output")
""")
        registry.set_custom_dir(temp_skills_dir)
        count = registry.load_custom_skills()
        assert count >= 1
        assert registry.get("my_custom") is not None

    def test_load_custom_skills_with_skill_object(self, registry, temp_skills_dir):
        """Test loading custom skill with SKILL object"""
        skill_file = temp_skills_dir / "official_skill.py"
        skill_file.write_text("""
from src.skills.registry import Skill, SkillResult

SKILL = Skill(
    name="official",
    description="Official custom skill",
    func=lambda code, ctx: SkillResult(success=True, output="official"),
    source="custom",
)
""")
        registry.set_custom_dir(temp_skills_dir)
        count = registry.load_custom_skills()
        assert count >= 1
        skill = registry.get("official")
        assert skill is not None
        assert skill.source == "custom"

    def test_load_custom_skills_skips_init(self, registry, temp_skills_dir):
        """Test that __init__.py is skipped"""
        init_file = temp_skills_dir / "__init__.py"
        init_file.write_text("# init file")
        registry.set_custom_dir(temp_skills_dir)
        registry.load_custom_skills()
        # __init__.py should be skipped
        assert registry.get("init") is None


class TestSkillRegistryExecution:
    """Tests for run/run_interactive methods"""

    def test_run_existing_skill(self, registry):
        """Test running an existing skill"""
        result = registry.run("review", "def test(): pass")
        assert isinstance(result, SkillResult)
        assert result.success is True

    def test_run_nonexistent_skill(self, registry):
        """Test running a non-existent skill"""
        result = registry.run("nonexistent")
        assert result.success is False
        assert "not found" in result.error

    def test_run_with_context(self, registry):
        """Test running a skill with context"""
        context = {"module_name": "test", "file_path": "test.py"}
        result = registry.run("doc", "# comment", context)
        assert result.success is True

    def test_run_interactive_with_slash(self, registry):
        """Test run_interactive strips leading slash"""
        result = registry.run_interactive("/review", "def test(): pass")
        assert result.success is True

    def test_run_interactive_without_slash(self, registry):
        """Test run_interactive works without slash"""
        result = registry.run_interactive("review", "def test(): pass")
        assert result.success is True

    def test_run_skill_exception_handling(self, registry):
        """Test that skill exceptions are caught"""
        def failing_skill(code: str, context: dict) -> SkillResult:
            raise ValueError("Skill error")

        skill = Skill(name="failing", description="Fails", func=failing_skill)
        registry.register(skill)

        result = registry.run("failing")
        assert result.success is False
        assert "ValueError" in result.error


class TestSkillRegistryDisplay:
    """Tests for display_list method"""

    def test_display_list_no_error(self, registry):
        """Test display_list doesn't raise errors"""
        # Should not raise any exceptions
        registry.display_list()
        assert True


# ── Global Singleton Tests ──────────────────────────────────────────────

class TestGetRegistry:
    """Tests for get_registry() singleton"""

    def test_get_registry_returns_instance(self):
        """Test get_registry returns a SkillRegistry instance"""
        reg = get_registry()
        assert isinstance(reg, SkillRegistry)

    def test_get_registry_singleton(self):
        """Test get_registry returns same instance"""
        reg1 = get_registry()
        reg2 = get_registry()
        assert reg1 is reg2

    def test_get_registry_loads_custom(self):
        """Test get_registry loads custom skills"""
        reg = get_registry()
        # Should have loaded custom skills (if any exist)
        assert reg._loaded_custom is True


# ── Integration Tests ───────────────────────────────────────────────────

class TestIntegration:
    """Integration tests for SkillRegistry"""

    def test_full_workflow(self, registry, sample_skill):
        """Test complete workflow: register, list, run"""
        # Register a custom skill
        skill = Skill(name="integration", description="Integration test", func=sample_skill)
        registry.register(skill)

        # List all skills
        all_skills = registry.list_all()
        assert len(all_skills) >= 4  # 3 builtin + 1 custom

        # Run the custom skill
        result = registry.run("integration")
        assert result.success is True
        assert result.output == "Custom output"

        # Unregister
        assert registry.unregister("integration") is True
        assert registry.get("integration") is None

    def test_builtin_skills_execution(self, registry):
        """Test all built-in skills can be executed"""
        test_code = """
def add(a, b):
    return a + b

def subtract(a, b):
    return a - b
"""
        # Test review
        result = registry.run("review", test_code)
        assert result.success is True

        # Test test
        result = registry.run("test", test_code)
        assert result.success is True

        # Test doc
        result = registry.run("doc", test_code, {"module_name": "math_ops"})
        assert result.success is True

    def test_skill_result_metadata(self, registry):
        """Test that skill results contain useful metadata"""
        code = "def test():\n    eval('dangerous')\n"
        result = registry.run("review", code)

        assert "issues" in result.metadata
        assert "suggestions" in result.metadata
        assert len(result.metadata["issues"]) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
