"""Tests for quest/spec_generator.py."""
import textwrap
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.quest.models import Quest, QuestSpec
from src.quest.spec_generator import SYSTEM_PROMPT, SpecGenerator

# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────


def make_quest(title="Test Quest", description="Test description", project_path="."):
    import uuid

    return Quest(id=str(uuid.uuid4()), title=title, description=description, project_path=project_path)


# ─────────────────────────────────────────────────────────────
# SpecGenerator.__init__
# ─────────────────────────────────────────────────────────────


class TestInit:
    def test_init_with_project_path(self):
        mock_router = MagicMock()
        sg = SpecGenerator(model_router=mock_router, project_path="/tmp/project")
        assert sg.model_router == mock_router
        assert str(sg.project_path) == "/tmp/project"

    def test_init_without_project_path(self):
        mock_router = MagicMock()
        sg = SpecGenerator(model_router=mock_router)
        assert sg.project_path == Path(".")


# ─────────────────────────────────────────────────────────────
# _parse_spec
# ─────────────────────────────────────────────────────────────


class TestParseSpec:
    def setup_method(self):
        self.sg = SpecGenerator(model_router=MagicMock())

    def test_basic_parse(self):
        content = textwrap.dedent("""\
# 测试任务

## 概述
这是一个测试任务

## 动机
测试动机

## 包含范围
- 功能1
- 功能2

## 不包含范围
- 功能3

## 验收标准
- [ ] **[AC1]** 标准1
- [ ] **[AC2]** 标准2

## 风险提示
- 风险1

## 技术方案
使用 TDD
""")
        spec = self.sg._parse_spec(content, "Fallback Title")
        assert spec.title == "测试任务"
        assert spec.overview == "这是一个测试任务"
        assert spec.motivation == "测试动机"
        assert len(spec.acceptance_criteria) == 2
        assert spec.acceptance_criteria[0].id == "AC1"
        assert spec.acceptance_criteria[0].description == "标准1"

    def test_no_title_uses_fallback(self):
        content = "## 概述\n无标题测试\n\n## 验收标准\n- [ ] **[AC1]** 测试\n"
        spec = self.sg._parse_spec(content, "Fallback")
        assert spec.title == "Fallback"

    def test_empty_acceptance_criteria_generates_default(self):
        content = "## 概述\n无验收标准\n\n## 技术方案\n随便\n"
        spec = self.sg._parse_spec(content, "Test")
        assert len(spec.acceptance_criteria) == 2
        assert spec.acceptance_criteria[0].id == "AC1"

    def test_scope_parsing(self):
        content = textwrap.dedent("""\
# Scope Test

## 包含范围
- 功能A
- 功能B

## 不包含范围
- 功能C
- 功能D

## 验收标准
- [ ] **[AC1]** 测试
""")
        spec = self.sg._parse_spec(content, "Test")
        assert "功能A" in spec.scope
        assert "功能B" in spec.scope
        assert "功能C" in spec.out_of_scope
        assert "功能D" in spec.out_of_scope

    def test_risks_parsing(self):
        content = textwrap.dedent("""\
# Risk Test

## 风险提示
- 风险1
- 风险2

## 验收标准
- [ ] **[AC1]** 测试
""")
        spec = self.sg._parse_spec(content, "Test")
        assert len(spec.risks) == 2
        assert "风险1" in spec.risks[0]

    def test_estimated_time_parsing(self):
        content = textwrap.dedent("""\
# Time Test

## 预估耗时
2h

## 验收标准
- [ ] **[AC1]** 测试
""")
        spec = self.sg._parse_spec(content, "Test")
        assert spec.estimated_time == "2h"

    def test_sections_excluded(self):
        """Sections like 概述, 动机 should not appear in sections list."""
        content = textwrap.dedent("""\
# Section Test

## 概述
概述内容

## 动机
动机内容

## 技术方案
技术内容

## 验收标准
- [ ] **[AC1]** 测试
""")
        spec = self.sg._parse_spec(content, "Test")
        section_titles = {s.title for s in spec.sections}
        assert "概述" not in section_titles
        assert "动机" not in section_titles
        assert "验收标准" not in section_titles
        assert "技术方案" in section_titles

    def test_acceptance_criteria_with_brackets(self):
        """Test [ ] and [x] parsing."""
        content = textwrap.dedent("""\
# AC Test

## 验收标准
- [ ] **[AC1]** 未完成
- [x] **[AC2]** 已完成

## 概述
测试
""")
        spec = self.sg._parse_spec(content, "Test")
        assert len(spec.acceptance_criteria) == 2

    def test_content_with_special_chars(self):
        content = textwrap.dedent("""\
# 特殊字符测试

## 概述
包含 中文、标点！@# ¥%

## 验收标准
- [ ] **[AC1]** 测试特殊字符：ωβψ
""")
        spec = self.sg._parse_spec(content, "Test")
        assert "ωβψ" in spec.acceptance_criteria[0].description

    def test_multiple_sections(self):
        content = textwrap.dedent("""\
# Multi Section

## 概述
概述

## 技术方案
技术1

## 文件规划
文件1

## 验收标准
- [ ] **[AC1]** 测试
""")
        spec = self.sg._parse_spec(content, "Test")
        # 技术方案 and 文件规划 should be in sections
        assert len(spec.sections) >= 2


# ─────────────────────────────────────────────────────────────
# generate (async)
# ─────────────────────────────────────────────────────────────


class TestGenerate:
    @pytest.mark.asyncio
    async def test_generate_calls_model_router(self):
        mock_router = MagicMock()
        mock_router.route_and_call = AsyncMock(return_value=MagicMock(content="# Test\n\n## 验收标准\n- [ ] **[AC1]** 测试"))
        sg = SpecGenerator(model_router=mock_router, project_path="/tmp")

        quest = make_quest()
        spec = await sg.generate(quest)

        mock_router.route_and_call.assert_called_once()
        assert isinstance(spec, QuestSpec)

    @pytest.mark.asyncio
    async def test_generate_builds_prompt(self):
        mock_router = MagicMock()
        mock_router.route_and_call = AsyncMock(return_value=MagicMock(content="# Test\n\n## 验收标准\n- [ ] **[AC1]** 测试"))
        sg = SpecGenerator(model_router=mock_router, project_path="/tmp")

        quest = make_quest(description="需要实现登录功能")
        await sg.generate(quest)

        call_args = mock_router.route_and_call.call_args
        messages = call_args[1]["messages"]
        user_msg = [m for m in messages if m.role == "user"][0]
        assert "登录功能" in user_msg.content
        assert "## 用户需求" in user_msg.content

    @pytest.mark.asyncio
    async def test_generate_task_type(self):
        mock_router = MagicMock()
        mock_router.route_and_call = AsyncMock(return_value=MagicMock(content="# Test\n\n## 验收标准\n- [ ] **[AC1]** 测试"))
        sg = SpecGenerator(model_router=mock_router, project_path="/tmp")

        quest = make_quest()
        await sg.generate(quest)

        call_args = mock_router.route_and_call.call_args
        assert call_args[1]["task_type"] == "planning"


# ─────────────────────────────────────────────────────────────
# _gather_context (async)
# ─────────────────────────────────────────────────────────────


class TestGatherContext:
    @pytest.mark.asyncio
    async def test_no_project_path(self):
        sg = SpecGenerator(model_router=MagicMock(), project_path="/nonexistent")
        quest = make_quest(project_path="/nonexistent")
        result = await sg._gather_context(quest)
        assert "项目路径" in result

    @pytest.mark.asyncio
    async def test_with_pyproject(self, tmp_path):
        sg = SpecGenerator(model_router=MagicMock(), project_path=str(tmp_path))
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "test"\n')
        quest = make_quest(project_path=str(tmp_path))
        result = await sg._gather_context(quest)
        assert "pyproject.toml" in result

    @pytest.mark.asyncio
    async def test_with_readme(self, tmp_path):
        sg = SpecGenerator(model_router=MagicMock(), project_path=str(tmp_path))
        (tmp_path / "README.md").write_text("# Test Project\n")
        quest = make_quest(project_path=str(tmp_path))
        result = await sg._gather_context(quest)
        assert "README.md" in result

    @pytest.mark.asyncio
    async def test_directory_listing(self, tmp_path):
        sg = SpecGenerator(model_router=MagicMock(), project_path=str(tmp_path))
        (tmp_path / "src").mkdir()
        (tmp_path / "tests").mkdir()
        (tmp_path / "README.md").write_text("# Test\n")
        quest = make_quest(project_path=str(tmp_path))
        result = await sg._gather_context(quest)
        assert "项目结构" in result


# ─────────────────────────────────────────────────────────────
# SYSTEM_PROMPT
# ─────────────────────────────────────────────────────────────


class TestSystemPrompt:
    def test_contains_required_sections(self):
        assert "概述" in SYSTEM_PROMPT
        assert "验收标准" in SYSTEM_PROMPT
        assert "动机" in SYSTEM_PROMPT
        assert "包含范围" in SYSTEM_PROMPT

    def test_contains_format_example(self):
        assert "AC1" in SYSTEM_PROMPT
        assert "[ ]" in SYSTEM_PROMPT
