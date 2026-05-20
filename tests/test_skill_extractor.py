"""测试 skill_extractor.py — Skill 沉淀闭环"""

import json
from pathlib import Path

from src.core.skill_extractor import (
    SkillProposal,
    _find_proposal,
    _generalize_step,
    _generate_description,
    _generate_steps,
    _generate_title,
    _generate_trigger,
    _is_worth_extracting,
    accept_proposal,
    extract_skill_from_task,
    list_proposals,
    reject_proposal,
    save_proposal,
)

# ===== SkillProposal =====


class TestSkillProposal:
    def test_defaults(self):
        p = SkillProposal(id="x", title="T", description="D", trigger="trig", steps=["s1"], source_task="task", created_at="2026-01-01")
        assert p.status == "pending"

    def test_custom_status(self):
        p = SkillProposal(id="x", title="T", description="D", trigger="trig", steps=[], source_task="task", created_at="2026-01-01", status="accepted")
        assert p.status == "accepted"


# ===== _is_worth_extracting =====


class TestIsWorthExtracting:
    def test_too_few_steps(self):
        assert not _is_worth_extracting("创建项目", ["step1", "step2"], [])

    def test_no_generic_keyword(self):
        assert not _is_worth_extracting("random stuff", ["s1", "s2", "s3"], ["成功"])

    def test_no_positive_reflection(self):
        assert not _is_worth_extracting("创建项目", ["s1", "s2", "s3"], ["失败", "不好"])

    def test_worth_extracting(self):
        assert _is_worth_extracting("创建配置文件", ["s1", "s2", "s3"], ["成功完成", "✅"])

    def test_enough_steps_with_generic_and_positive(self):
        assert _is_worth_extracting("修复bug", ["a", "b", "c", "d"], ["顺利解决"])


# ===== _generate_title =====


class TestGenerateTitle:
    def test_verb_pattern(self):
        title = _generate_title("创建用户认证模块")
        assert "用户认证" in title or "认证模块" in title

    def test_of_pattern(self):
        title = _generate_title("用户认证的实现")
        assert "用户认证" in title

    def test_short_description(self):
        title = _generate_title("short task")
        assert title == "short task"

    def test_long_description_no_pattern(self):
        title = _generate_title("this is a very long description without any action keywords in it at all")
        assert "..." in title

    def test_dash_separator(self):
        title = _generate_title("配置环境 - dev setup")
        assert "环境" in title or len(title) <= 50


# ===== _generate_trigger =====


class TestGenerateTrigger:
    def test_with_keyword(self):
        trigger = _generate_trigger("创建和配置项目")
        assert "创建" in trigger
        assert "配置" in trigger

    def test_no_keyword(self):
        trigger = _generate_trigger("random task")
        assert "类似需求" in trigger

    def test_multiple_keywords(self):
        trigger = _generate_trigger("创建生成配置设置部署")
        # Only top 3 keywords
        assert "/" in trigger


# ===== _generate_steps =====


class TestGenerateSteps:
    def test_basic(self):
        steps = _generate_steps(["step1", "step2", "step3"], [])
        assert len(steps) >= 3

    def test_dedup(self):
        steps = _generate_steps(["same", "same", "different"], [])
        assert len(steps) <= 2  # deduplicated

    def test_with_reflections(self):
        steps = _generate_steps(["a", "b"], ["建议改进流程", "下次注意"])
        assert any("💡" in s for s in steps)

    def test_max_10(self):
        steps = _generate_steps([f"step{i}" for i in range(15)], [])
        assert len(steps) <= 10

    def test_reflection_without_tip_keywords(self):
        steps = _generate_steps(["a"], ["普通反思内容"])
        # Should not add tip for reflections without keywords
        tip_steps = [s for s in steps if "💡" in s]
        assert len(tip_steps) == 0


# ===== _generalize_step =====


class TestGeneralizeStep:
    def test_remove_path(self):
        result = _generalize_step("edit /Users/test/file.py")
        assert "<路径>" in result

    def test_remove_filename(self):
        result = _generalize_step("修改 config.yaml 文件")
        assert "<文件>" in result

    def test_remove_date(self):
        result = _generalize_step("commit 2026-01-01 10:00")
        assert "<时间>" in result

    def test_remove_commit_hash(self):
        result = _generalize_step("push abc123def456")
        assert "<commit>" in result

    def test_clean_text(self):
        result = _generalize_step("simple step")
        assert result == "simple step"


# ===== _generate_description =====


class TestGenerateDescription:
    def test_basic(self):
        desc = _generate_description("Test Skill", ["a", "b"])
        assert "Test Skill" in desc
        assert "2" in desc


# ===== extract_skill_from_task =====


class TestExtractSkillFromTask:
    def test_not_worth(self):
        result = extract_skill_from_task("random", ["a", "b"], ["bad"])
        assert result is None

    def test_worth(self):
        result = extract_skill_from_task(
            "创建项目配置",
            ["step1", "step2", "step3", "step4"],
            ["成功完成 ✅"],
        )
        assert result is not None
        assert result.title != ""
        assert len(result.steps) >= 1
        assert result.status == "pending"


# ===== save/list/accept/reject =====


class TestSaveAndList:
    def test_save_and_list(self, tmp_path, monkeypatch):
        monkeypatch.setattr("src.core.skill_extractor.SKILL_PROPOSALS_DIR", tmp_path)
        proposal = SkillProposal(
            id="proposal-test-001",
            title="Test",
            description="Desc",
            trigger="When needed",
            steps=["s1"],
            source_task="task",
            created_at="2026-01-01",
        )
        path = save_proposal(proposal)
        assert path.exists()

        proposals = list_proposals()
        assert len(proposals) == 1
        assert proposals[0].id == "proposal-test-001"

    def test_list_empty_dir(self, tmp_path, monkeypatch):
        monkeypatch.setattr("src.core.skill_extractor.SKILL_PROPOSALS_DIR", tmp_path)
        assert list_proposals() == []

    def test_list_nonexistent_dir(self, tmp_path, monkeypatch):
        monkeypatch.setattr("src.core.skill_extractor.SKILL_PROPOSALS_DIR", tmp_path / "nope")
        assert list_proposals() == []

    def test_list_skips_bad_json(self, tmp_path, monkeypatch):
        monkeypatch.setattr("src.core.skill_extractor.SKILL_PROPOSALS_DIR", tmp_path)
        bad = tmp_path / "proposal-bad.json"
        bad.write_text("not json", encoding="utf-8")
        good = tmp_path / "proposal-good.json"
        good.write_text(json.dumps({
            "id": "good", "title": "T", "description": "D",
            "trigger": "trig", "steps": [], "source_task": "task",
            "created_at": "2026-01-01", "status": "pending",
        }), encoding="utf-8")
        proposals = list_proposals()
        assert len(proposals) == 1

    def test_accept_proposal(self, tmp_path, monkeypatch):
        monkeypatch.setattr("src.core.skill_extractor.SKILL_PROPOSALS_DIR", tmp_path)
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)

        proposal = SkillProposal(
            id="proposal-accept-001",
            title="Accept Test",
            description="Desc",
            trigger="trig",
            steps=["step1", "step2"],
            source_task="task",
            created_at="2026-01-01",
        )
        save_proposal(proposal)

        result = accept_proposal("proposal-accept-001")
        assert result is not None
        assert result.exists()
        content = result.read_text(encoding="utf-8")
        assert "Accept Test" in content

        # Check status updated
        proposals = list_proposals()
        assert proposals[0].status == "accepted"

    def test_accept_nonexistent(self, tmp_path, monkeypatch):
        monkeypatch.setattr("src.core.skill_extractor.SKILL_PROPOSALS_DIR", tmp_path)
        result = accept_proposal("nonexistent")
        assert result is None

    def test_reject_proposal(self, tmp_path, monkeypatch):
        monkeypatch.setattr("src.core.skill_extractor.SKILL_PROPOSALS_DIR", tmp_path)
        proposal = SkillProposal(
            id="proposal-reject-001",
            title="Reject Test",
            description="D",
            trigger="t",
            steps=["s"],
            source_task="task",
            created_at="2026-01-01",
        )
        save_proposal(proposal)
        result = reject_proposal("proposal-reject-001")
        assert result is True

        proposals = list_proposals()
        assert proposals[0].status == "rejected"

    def test_reject_nonexistent(self, tmp_path, monkeypatch):
        monkeypatch.setattr("src.core.skill_extractor.SKILL_PROPOSALS_DIR", tmp_path)
        assert not reject_proposal("nonexistent")


# ===== _find_proposal =====


class TestFindProposal:
    def test_find_existing(self, tmp_path, monkeypatch):
        monkeypatch.setattr("src.core.skill_extractor.SKILL_PROPOSALS_DIR", tmp_path)
        proposal = SkillProposal(
            id="proposal-find-001",
            title="Find",
            description="D",
            trigger="t",
            steps=["s"],
            source_task="task",
            created_at="2026-01-01",
        )
        save_proposal(proposal)
        found = _find_proposal("proposal-find-001")
        assert found is not None
        assert found.title == "Find"

    def test_find_nonexistent(self, tmp_path, monkeypatch):
        monkeypatch.setattr("src.core.skill_extractor.SKILL_PROPOSALS_DIR", tmp_path)
        assert _find_proposal("nonexistent") is None

    def test_find_corrupted(self, tmp_path, monkeypatch):
        monkeypatch.setattr("src.core.skill_extractor.SKILL_PROPOSALS_DIR", tmp_path)
        bad = tmp_path / "proposal-bad.json"
        bad.write_text("{invalid", encoding="utf-8")
        assert _find_proposal("proposal-bad") is None
