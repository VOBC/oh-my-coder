"""
SkillManager 单元测试
"""

import tempfile
from pathlib import Path

import pytest

from src.memory.skill_manager import SkillManager


@pytest.fixture
def tmp_skill_dir():
    """临时 .omc/skills 目录"""
    with tempfile.TemporaryDirectory() as td:
        yield Path(td) / ".omc" / "skills"


@pytest.fixture
def sm(tmp_skill_dir):
    return SkillManager(skills_dir=tmp_skill_dir)


class TestSlugify:
    def test_basic(self, sm):
        assert sm._slugify("Hello World") == "hello-world"
        assert sm._slugify("SQL Query Fix") == "sql-query-fix"

    def test_special_chars(self, sm):
        assert sm._slugify("Fix: 慢查询!") == "fix-慢查询"
        assert sm._slugify("Test (v1)") == "test-v1"

    def test_long_name(self, sm):
        long_name = "a" * 100
        result = sm._slugify(long_name)
        assert len(result) <= 48


class TestCreate:
    def test_create_basic(self, sm):
        result = sm.create(
            name="SQL 慢查询修复",
            body="# SQL 慢查询修复\n\n当发现查询慢时...",
            category="debugging",
            tags=["sql", "performance"],
            triggers=["查询慢", "timeout"],
            description="修复 SQL 慢查询的步骤",
        )
        assert "skill_id" in result
        assert result["category"] == "debugging"
        assert result["name"] == "SQL 慢查询修复"

        # 文件存在
        skill_path = sm._find_skill_path(result["skill_id"])
        assert skill_path is not None
        assert skill_path.name == "SKILL.md"

        # 内容正确
        content = skill_path.read_text(encoding="utf-8")
        assert "sql-慢查询修复" in result["skill_id"]
        assert "sql" in content
        assert "---" in content  # frontmatter

    def test_create_auto_description(self, sm):
        result = sm.create(
            name="Test Skill",
            body="## 标题\n\n这是第一行描述",
            category="workflow",
        )
        assert result["description"] == "这是第一行描述"

    def test_create_invalid_category(self, sm):
        with pytest.raises(ValueError, match="无效 category"):
            sm.create(name="x", body="body", category="invalid")

    def test_create_duplicate_raises(self, sm):
        sm.create(name="Test", body="# Test\n\nbody", category="workflow")
        with pytest.raises(FileExistsError, match="已存在"):
            sm.create(name="Test", body="# Test\n\nbody", category="workflow")


class TestPatch:
    def test_patch_body_only(self, sm):
        original = sm.create(
            name="Test Patch",
            body="# Old Body",
            category="workflow",
            tags=["tag1"],
            description="old desc",
        )
        updated = sm.patch(
            skill_id=original["skill_id"], body="# New Body\n\nnew content"
        )

        assert updated["skill_id"] == original["skill_id"]
        skill = sm.get_skill(original["skill_id"], include_body=True)
        assert "New Body" in skill["body"]
        assert skill["tags"] == ["tag1"]  # 未更新的字段保留

    def test_patch_description(self, sm):
        original = sm.create(
            name="Test", body="# Test", category="workflow", description="old"
        )
        updated = sm.patch(skill_id=original["skill_id"], description="new description")

        assert updated["description"] == "new description"
        # updated_at 变化
        assert updated["updated_at"] == original["updated_at"]  # 无 body 就不变

    def test_patch_nonexistent_creates(self, sm):
        """patch 一个不存在的 skill_id，如果有 body 则自动 create"""
        result = sm.patch(
            skill_id="auto-created-skill",
            body="# Auto Created\n\nbody",
            category="workflow",
            description="autocreated",
        )
        assert result["skill_id"] == "auto-created-skill"
        assert sm.get_skill("auto-created-skill") is not None

    def test_patch_nonexistent_without_body_raises(self, sm):
        with pytest.raises(ValueError, match="未提供 body"):
            sm.patch(skill_id="no-such-skill")


class TestDelete:
    def test_delete_exists(self, sm):
        created = sm.create(name="To Delete", body="# To Delete", category="workflow")
        assert sm.delete(created["skill_id"]) is True
        assert sm.get_skill(created["skill_id"]) is None

    def test_delete_not_exists(self, sm):
        assert sm.delete("nonexistent") is False


class TestListAndGet:
    def test_list_all(self, sm):
        sm.create(name="a", body="# a", category="debugging", tags=["t1"])
        sm.create(name="b", body="# b", category="workflow", tags=["t2"])
        sm.create(name="c", body="# c", category="debugging", tags=["t1"])

        all_list = sm.list_skills()
        assert len(all_list) == 3

    def test_list_filter_category(self, sm):
        sm.create(name="a", body="# a", category="debugging")
        sm.create(name="b", body="# b", category="workflow")
        sm.create(name="c", body="# c", category="workflow")

        assert len(sm.list_skills(category="debugging")) == 1
        assert len(sm.list_skills(category="workflow")) == 2

    def test_list_filter_tag(self, sm):
        sm.create(name="a", body="# a", category="debugging", tags=["python"])
        sm.create(name="b", body="# b", category="workflow", tags=["python", "fastapi"])
        sm.create(name="c", body="# c", category="debugging", tags=["go"])

        assert len(sm.list_skills(tag="python")) == 2
        assert len(sm.list_skills(tag="go")) == 1

    def test_get_with_body(self, sm):
        created = sm.create(
            name="Get Test",
            body="# Get Test\n\n## Section\n\ncontent here",
            category="workflow",
        )
        skill = sm.get_skill(created["skill_id"], include_body=True)
        assert skill is not None
        assert "Get Test" in skill["body"]
        assert "Section" in skill["body"]

    def test_get_not_exists(self, sm):
        assert sm.get_skill("nonexistent") is None


class TestSearch:
    def setup_method(self):
        self.sm = SkillManager(skills_dir=Path(tempfile.mkdtemp()) / ".omc" / "skills")
        self.sm.create(
            name="SQL 慢查询优化",
            body="# SQL 慢查询优化",
            category="debugging",
            tags=["sql", "performance"],
            triggers=["查询慢"],
            description="优化 SQL 慢查询的步骤",
        )
        self.sm.create(
            name="Flask 项目重构",
            body="# Flask 项目重构",
            category="workflow",
            tags=["flask", "refactor"],
            triggers=["重构"],
            description="Flask 项目模块化重构",
        )
        self.sm.create(
            name="GitHub 推送失败",
            body="# GitHub 推送失败",
            category="debugging",
            tags=["git", "github"],
            triggers=["push", "超时"],
            description="GitHub 443 端口超时解决",
        )

    def test_search_single_term(self):
        results = self.sm.search("sql")
        assert len(results) >= 1
        assert any("sql" in r.get("tags", []) for r in results)

    def test_search_and_logic(self):
        """多词 AND"""
        results = self.sm.search("sql 慢查询")
        assert len(results) >= 1

    def test_search_no_match(self):
        results = self.sm.search("zzzz_not_exist")
        assert len(results) == 0

    def test_search_filter_category(self):
        results = self.sm.search("git", category="debugging")
        assert all(r["category"] == "debugging" for r in results)

    def test_search_triggers(self):
        results = self.sm.search("push")
        assert len(results) >= 1


class TestIndexPersistence:
    def test_index_persists_after_reinit(self, tmp_skill_dir):
        sm1 = SkillManager(skills_dir=tmp_skill_dir)
        sm1.create(name="Persist Test", body="# Test", category="workflow")

        # 重新初始化
        sm2 = SkillManager(skills_dir=tmp_skill_dir)
        skill = sm2.get_skill(list(sm2._index.keys())[0])
        assert skill is not None
        assert skill["name"] == "Persist Test"

    def test_rebuild_index(self, tmp_skill_dir):
        sm = SkillManager(skills_dir=tmp_skill_dir)
        sm.create(name="Rebuild 1", body="# R1", category="debugging")
        sm.create(name="Rebuild 2", body="# R2", category="workflow")

        # 模拟索引损坏
        index_file = tmp_skill_dir / "index.json"
        index_file.write_text("{}", encoding="utf-8")

        sm2 = SkillManager(skills_dir=tmp_skill_dir)
        count = sm2.rebuild_index()
        assert count == 2
        assert len(sm2.list_skills()) == 2


class TestEvaluateSkillWorthy:
    def test_tool_call_threshold(self):
        assert (
            SkillManager.evaluate_skill_worthy(
                tool_call_count=5,
                had_error=False,
                had_fix=False,
                had_user_correction=False,
                is_nontrivial_workflow=False,
            )
            is True
        )
        assert (
            SkillManager.evaluate_skill_worthy(
                tool_call_count=4,
                had_error=False,
                had_fix=False,
                had_user_correction=False,
                is_nontrivial_workflow=False,
            )
            is False
        )

    def test_error_then_fix(self):
        assert (
            SkillManager.evaluate_skill_worthy(
                tool_call_count=0,
                had_error=True,
                had_fix=True,
                had_user_correction=False,
                is_nontrivial_workflow=False,
            )
            is True
        )

    def test_user_correction(self):
        assert (
            SkillManager.evaluate_skill_worthy(
                tool_call_count=0,
                had_error=False,
                had_fix=False,
                had_user_correction=True,
                is_nontrivial_workflow=False,
            )
            is True
        )

    def test_nontrivial_workflow(self):
        assert (
            SkillManager.evaluate_skill_worthy(
                tool_call_count=0,
                had_error=False,
                had_fix=False,
                had_user_correction=False,
                is_nontrivial_workflow=True,
            )
            is True
        )

    def test_all_false(self):
        assert (
            SkillManager.evaluate_skill_worthy(
                tool_call_count=2,
                had_error=False,
                had_fix=False,
                had_user_correction=False,
                is_nontrivial_workflow=False,
            )
            is False
        )


class TestBuildSkillFromExecution:
    def test_build_basic(self):
        draft = SkillManager.build_skill_from_execution(
            agent_name="executor",
            task_description="重构 Flask 单文件为多模块",
            workflow_name="refactor",
            final_result="成功重构为 5 个模块，测试全部通过",
            key_steps=["分析依赖", "拆分为模块", "修复导入", "写测试"],
        )
        assert draft["name"] == "refactor-executor"
        assert draft["category"] == "workflow"
        assert "Flask" in draft["body"]
        assert "分析依赖" in draft["body"]
        assert "flask" in draft["tags"] or "重构" in draft["body"].lower()

    def test_build_debugging_category(self):
        draft = SkillManager.build_skill_from_execution(
            agent_name="debugger",
            task_description="修复 SQL 语法错误",
            workflow_name="debug",
            final_result="修复成功",
            error_context="缺少引号",
        )
        assert draft["category"] == "debugging"


class TestGetSkillInventory:
    def test_empty(self, sm):
        inv = sm.get_skill_inventory()
        assert "0 Skills Available" in inv

    def test_with_skills(self, sm):
        sm.create(name="S1", body="# S1", category="debugging", description="desc1")
        sm.create(name="S2", body="# S2", category="workflow", description="desc2")
        inv = sm.get_skill_inventory()
        assert "2 Skills Available" in inv
        assert "s1" in inv or "S1" in inv
        assert "desc1" in inv

    def test_max_chars_truncation(self, sm):
        # 创建很多小 skill
        for i in range(20):
            sm.create(
                name=f"Skill {i}",
                body=f"# Skill {i}",
                category="workflow",
                description=f"description number {i}",
            )
        inv = sm.get_skill_inventory(max_chars=300)
        # 应该被截断
        assert len(inv) <= 400
