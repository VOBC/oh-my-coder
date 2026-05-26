"""Tests for cli_skill commands."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from src.commands.cli_skill import app
from src.skills import Skill, SkillResult

runner = CliRunner()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_skill(name="test_skill", description="A test skill", source="builtin", file_path=None):
    def _func(code: str, ctx: dict):
        return SkillResult(success=True, output="ok", duration_ms=10.0)

    return Skill(name=name, description=description, func=_func, source=source, file_path=file_path)


def _mock_registry(skills=None, skill_by_name=None):
    """Return a mock SkillRegistry."""
    reg = MagicMock()
    reg.list_all.return_value = skills or []
    reg.list_builtin.return_value = [s for s in (skills or []) if s.source == "builtin"]
    reg.list_custom.return_value = [s for s in (skills or []) if s.source == "custom"]
    reg.get.return_value = skill_by_name
    reg.display_list.return_value = None

    if skill_by_name:
        reg.run.return_value = SkillResult(success=True, output="result code", duration_ms=42.0, metadata={"k": "v"})
    else:
        reg.run.return_value = SkillResult(success=False, error="not found", duration_ms=0)

    return reg


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------


class TestListSkills:
    @patch("src.commands.cli_skill.get_registry")
    def test_list_no_skills(self, mock_get):
        mock_get.return_value = _mock_registry(skills=[])
        result = runner.invoke(app, ["list"])
        assert result.exit_code == 0
        assert "No skills found" in result.output

    @patch("src.commands.cli_skill.get_registry")
    def test_list_all(self, mock_get):
        skills = [_make_skill("s1"), _make_skill("s2", source="custom")]
        mock_get.return_value = _mock_registry(skills=skills)
        result = runner.invoke(app, ["list"])
        assert result.exit_code == 0
        mock_get.return_value.display_list.assert_called_once()

    @patch("src.commands.cli_skill.get_registry")
    def test_list_builtin_only(self, mock_get):
        skills = [_make_skill("s1"), _make_skill("s2", source="custom")]
        mock_get.return_value = _mock_registry(skills=skills)
        result = runner.invoke(app, ["list", "--builtin"])
        assert result.exit_code == 0
        mock_get.return_value.list_builtin.assert_called_once()

    @patch("src.commands.cli_skill.get_registry")
    def test_list_custom_only(self, mock_get):
        skills = [_make_skill("s1"), _make_skill("s2", source="custom")]
        mock_get.return_value = _mock_registry(skills=skills)
        result = runner.invoke(app, ["list", "--custom"])
        assert result.exit_code == 0
        mock_get.return_value.list_custom.assert_called_once()


# ---------------------------------------------------------------------------
# info
# ---------------------------------------------------------------------------


class TestSkillInfo:
    @patch("src.commands.cli_skill.get_registry")
    def test_info_found(self, mock_get):
        skill = _make_skill(name="my_skill", description="Does things", file_path=Path("/tmp/s.py"))
        mock_get.return_value = _mock_registry(skill_by_name=skill)
        result = runner.invoke(app, ["info", "my_skill"])
        assert result.exit_code == 0
        assert "my_skill" in result.output
        assert "Does things" in result.output

    @patch("src.commands.cli_skill.get_registry")
    def test_info_not_found(self, mock_get):
        mock_get.return_value = _mock_registry(skill_by_name=None)
        result = runner.invoke(app, ["info", "missing"])
        assert result.exit_code == 1
        assert "not found" in result.output


# ---------------------------------------------------------------------------
# run
# ---------------------------------------------------------------------------


class TestRunSkill:
    @patch("src.commands.cli_skill.get_registry")
    def test_run_with_code_file(self, mock_get, tmp_path):
        code_file = tmp_path / "test.py"
        code_file.write_text("print('hi')")
        skill = _make_skill()
        mock_get.return_value = _mock_registry(skill_by_name=skill)
        result = runner.invoke(app, ["run", "my_skill", "--code", str(code_file)])
        assert result.exit_code == 0
        assert "executed" in result.output

    @patch("src.commands.cli_skill.get_registry")
    def test_run_code_file_not_found(self, mock_get, tmp_path):
        mock_get.return_value = _mock_registry(skill_by_name=_make_skill())
        result = runner.invoke(app, ["run", "my_skill", "--code", "/nonexistent/file.py"])
        assert result.exit_code == 1
        assert "File not found" in result.output

    @patch("src.commands.cli_skill.get_registry")
    def test_run_with_output_file(self, mock_get, tmp_path):
        code_file = tmp_path / "test.py"
        code_file.write_text("x=1")
        out_file = tmp_path / "out.py"
        skill = _make_skill()
        mock_get.return_value = _mock_registry(skill_by_name=skill)
        result = runner.invoke(app, ["run", "my_skill", "--code", str(code_file), "--output", str(out_file)])
        assert result.exit_code == 0
        assert out_file.exists()
        assert "result code" in out_file.read_text()

    @patch("src.commands.cli_skill.get_registry")
    def test_run_skill_failure(self, mock_get, tmp_path):
        code_file = tmp_path / "test.py"
        code_file.write_text("bad code")
        reg = _mock_registry(skill_by_name=_make_skill())
        reg.run.return_value = SkillResult(success=False, error="boom", duration_ms=5)
        mock_get.return_value = reg
        result = runner.invoke(app, ["run", "my_skill", "--code", str(code_file)])
        assert result.exit_code == 1
        assert "failed" in result.output

    @patch("src.commands.cli_skill.get_registry")
    def test_run_no_code_provided(self, mock_get):
        # When stdin is empty (no --code, no pipe), should warn
        mock_get.return_value = _mock_registry(skill_by_name=_make_skill())
        result = runner.invoke(app, ["run", "my_skill"], input="")
        assert result.exit_code == 1
        assert "No code provided" in result.output

    @patch("src.commands.cli_skill.get_registry")
    def test_run_stdin_code(self, mock_get):
        skill = _make_skill()
        mock_get.return_value = _mock_registry(skill_by_name=skill)
        result = runner.invoke(app, ["run", "my_skill"], input="print('hello')\n")
        assert result.exit_code == 0
        assert "executed" in result.output

    @patch("src.commands.cli_skill.get_registry")
    def test_run_with_metadata(self, mock_get, tmp_path):
        code_file = tmp_path / "test.py"
        code_file.write_text("x=1")
        reg = _mock_registry(skill_by_name=_make_skill())
        reg.run.return_value = SkillResult(
            success=True, output="out", duration_ms=10.0, metadata={"lines": 1}
        )
        mock_get.return_value = reg
        result = runner.invoke(app, ["run", "my_skill", "--code", str(code_file)])
        assert result.exit_code == 0
        assert "Metadata" in result.output


# ---------------------------------------------------------------------------
# init
# ---------------------------------------------------------------------------


class TestInitCustomSkills:
    @patch("src.commands.cli_skill.Path.home")
    def test_init_creates_dir_and_example(self, mock_home, tmp_path):
        mock_home.return_value = tmp_path
        result = runner.invoke(app, ["init"])
        assert result.exit_code == 0
        skill_dir = tmp_path / ".omc" / "skills"
        assert skill_dir.is_dir()
        example = skill_dir / "example_skill.py"
        assert example.exists()
        assert "Created example skill" in result.output

    @patch("src.commands.cli_skill.Path.home")
    def test_init_already_exists(self, mock_home, tmp_path):
        skill_dir = tmp_path / ".omc" / "skills"
        skill_dir.mkdir(parents=True)
        (skill_dir / "example_skill.py").write_text("old")
        mock_home.return_value = tmp_path
        result = runner.invoke(app, ["init"])
        assert result.exit_code == 0
        assert "already exists" in result.output


# ---------------------------------------------------------------------------
# propose
# ---------------------------------------------------------------------------


class TestProposeSkill:
    @patch("src.core.skill_extractor.save_proposal")
    @patch("src.core.skill_extractor.extract_skill_from_task")
    def test_propose_success(self, mock_extract, mock_save):
        from src.core.skill_extractor import SkillProposal

        proposal = SkillProposal(
            id="p1", title="My Skill", description="desc", trigger="when X",
            steps=["step1", "step2"], source_task="do something",
            created_at="2026-01-01", status="pending",
        )
        mock_extract.return_value = proposal
        mock_save.return_value = Path("/tmp/p1.json")

        result = runner.invoke(app, ["propose", "do something", "--steps", "a,b"])
        assert result.exit_code == 0
        assert "Skill 提议已生成" in result.output
        assert "My Skill" in result.output

    @patch("src.core.skill_extractor.extract_skill_from_task")
    def test_propose_not_worth(self, mock_extract):
        mock_extract.return_value = None
        result = runner.invoke(app, ["propose", "trivial task"])
        assert result.exit_code == 0
        assert "不值得提取" in result.output

    @patch("src.core.skill_extractor.save_proposal")
    @patch("src.core.skill_extractor.extract_skill_from_task")
    def test_propose_with_reflections(self, mock_extract, mock_save):
        from src.core.skill_extractor import SkillProposal

        proposal = SkillProposal(
            id="p2", title="Ref Skill", description="d", trigger="when Y",
            steps=["s1"], source_task="task", created_at="2026-01-01",
        )
        mock_extract.return_value = proposal
        mock_save.return_value = Path("/tmp/p2.json")

        result = runner.invoke(app, ["propose", "task", "--reflections", "r1,r2"])
        assert result.exit_code == 0
        # Verify reflections were passed
        call_args = mock_extract.call_args
        assert call_args[0][2] == ["r1", "r2"]


# ---------------------------------------------------------------------------
# review
# ---------------------------------------------------------------------------


class TestReviewProposals:
    @patch("src.core.skill_extractor.list_proposals")
    def test_review_no_pending(self, mock_list):
        mock_list.return_value = []
        result = runner.invoke(app, ["review"])
        assert result.exit_code == 0
        assert "没有待处理" in result.output

    @patch("src.core.skill_extractor.list_proposals")
    def test_review_with_pending(self, mock_list):
        from src.core.skill_extractor import SkillProposal

        p = SkillProposal(
            id="p1", title="T", description="d", trigger="x",
            steps=["s1"], source_task="a" * 100,
            created_at="2026-01-01", status="pending",
        )
        mock_list.return_value = [p]
        result = runner.invoke(app, ["review"])
        assert result.exit_code == 0
        assert "待处理的 Skill 提议" in result.output
        assert "accept" in result.output

    @patch("src.core.skill_extractor.list_proposals")
    def test_review_filters_non_pending(self, mock_list):
        from src.core.skill_extractor import SkillProposal

        p = SkillProposal(
            id="p1", title="T", description="d", trigger="x",
            steps=["s1"], source_task="a",
            created_at="2026-01-01", status="accepted",
        )
        mock_list.return_value = [p]
        result = runner.invoke(app, ["review"])
        assert result.exit_code == 0
        assert "没有待处理" in result.output


# ---------------------------------------------------------------------------
# accept / reject
# ---------------------------------------------------------------------------


class TestAcceptReject:
    @patch("src.core.skill_extractor.accept_proposal")
    def test_accept_success(self, mock_accept):
        mock_accept.return_value = Path("/tmp/SKILL.md")
        result = runner.invoke(app, ["accept", "p1"])
        assert result.exit_code == 0
        assert "已接受" in result.output

    @patch("src.core.skill_extractor.accept_proposal")
    def test_accept_not_found(self, mock_accept):
        mock_accept.return_value = None
        result = runner.invoke(app, ["accept", "missing"])
        assert result.exit_code == 1
        assert "未找到" in result.output

    @patch("src.core.skill_extractor.reject_proposal")
    def test_reject_success(self, mock_reject):
        mock_reject.return_value = True
        result = runner.invoke(app, ["reject", "p1"])
        assert result.exit_code == 0
        assert "已拒绝" in result.output

    @patch("src.core.skill_extractor.reject_proposal")
    def test_reject_not_found(self, mock_reject):
        mock_reject.return_value = False
        result = runner.invoke(app, ["reject", "missing"])
        assert result.exit_code == 1
        assert "未找到" in result.output
