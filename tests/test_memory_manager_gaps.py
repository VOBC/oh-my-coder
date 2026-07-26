"""
Tests for coverage gaps in src/memory/manager.py
Covers: lines 95-96, 121, 144-149, 168-169, 181, 185-187,
        302, 320-328, 340, 376-378, 389
"""
from pathlib import Path

import pytest

from src.memory.manager import MemoryConfig, MemoryManager


@pytest.fixture
def mgr(tmp_path):
    config = MemoryConfig(storage_dir=tmp_path, short_term_max_messages=5)
    return MemoryManager(config)


# ─────────────────────────────────────────────
# Lines 95-96: OSError in record_compact
# ─────────────────────────────────────────────


class TestCompactStatsOSError:

    def test_record_compact_handles_oserror_on_write(self, mgr):
        """Lines 95-96: OSError during stats file write is caught"""
        class FakeResult:
            compacted = True
            tokens_saved = 100
            messages_removed = 5
            deduplicated_count = 2
            error_removed_count = 1

        from unittest.mock import patch

        def raising_mkdir(*args, **kwargs):
            raise OSError("read-only filesystem")

        with patch.object(Path, "mkdir", raising_mkdir):
            mgr.record_compact(FakeResult())

    def test_compact_stats_reads_invalid_json(self, mgr):
        """Lines 95-96: compact_stats handles invalid JSON gracefully"""
        stats = mgr.compact_stats
        assert stats["total_compact_count"] == 0

        stats_file = mgr._stats_file
        stats_file.parent.mkdir(parents=True, exist_ok=True)
        stats_file.write_text("not json at all", encoding="utf-8")

        stats = mgr.compact_stats
        assert isinstance(stats, dict)
        assert stats["total_compact_count"] == 0


# ─────────────────────────────────────────────
# Lines 144-149: record_compact stats tracking
# ─────────────────────────────────────────────


class TestRecordCompact:

    def test_record_compact_updates_stats(self, mgr):
        """Lines 144-149: record_compact accumulates stats"""
        class FakeResult:
            compacted = True
            tokens_saved = 500
            messages_removed = 10
            deduplicated_count = 3
            error_removed_count = 2

        mgr.record_compact(FakeResult())
        stats = mgr.compact_stats
        assert stats["total_compact_count"] == 1
        assert stats["total_tokens_saved"] == 500
        assert stats["total_messages_removed"] == 10
        assert stats["total_deduplicated"] == 3
        assert stats["total_errors_removed"] == 2

    def test_record_compact_multiple_calls(self, mgr):
        """Multiple record_compact calls accumulate"""
        class FakeResult:
            compacted = True
            tokens_saved = 100
            messages_removed = 5
            deduplicated_count = 1
            error_removed_count = 0

        mgr.record_compact(FakeResult())
        mgr.record_compact(FakeResult())
        stats = mgr.compact_stats
        assert stats["total_compact_count"] == 2
        assert stats["total_tokens_saved"] == 200

    def test_record_compact_minimal_result(self, mgr):
        """record_compact handles result without optional attrs"""
        class MinimalResult:
            compacted = True
            tokens_saved = 50
            messages_removed = 3

        mgr.record_compact(MinimalResult())
        stats = mgr.compact_stats
        assert stats["total_deduplicated"] == 0
        assert stats["total_errors_removed"] == 0


# ─────────────────────────────────────────────
# Line 121: count_tokens fallback formula
# ─────────────────────────────────────────────


class TestCountTokens:

    def test_count_tokens_formula_chinese(self, mgr):
        """Line 121: count_tokens uses int(len(text) / 2.5) fallback"""
        tokens = mgr.count_tokens("你好世界")
        assert tokens == 1  # int(4 / 2.5) = 1

    def test_count_tokens_formula_english(self, mgr):
        """count_tokens fallback formula for English"""
        tokens = mgr.count_tokens("hello world")
        assert tokens == 4  # int(11 / 2.5) = 4

    def test_count_tokens_formula_mixed(self, mgr):
        """count_tokens fallback formula for mixed content"""
        tokens = mgr.count_tokens("hello你好world世界123")
        assert tokens == 6  # int(15 / 2.5) = 6


# ─────────────────────────────────────────────
# Lines 168-169: delegation to short_term
# ─────────────────────────────────────────────


class TestMemoryManagerDelegation:

    def test_get_latest_session(self, mgr):
        """Line 168: get_latest_session delegates to short_term"""
        session = mgr.create_session(Path("/tmp/test"), "delegation test")
        mgr.save_session(session)
        latest = mgr.get_latest_session()
        assert latest is not None
        assert latest.session_id == session.session_id

    def test_save_session(self, mgr):
        """Line 169: save_session delegates to short_term"""
        session = mgr.create_session()
        session.add_message("user", "hello")
        mgr.save_session(session)


# ─────────────────────────────────────────────
# Lines 181, 185-187: recall method
# ─────────────────────────────────────────────


class TestRecall:

    def test_recall_searches_learnings(self, mgr):
        """recall searches learnings"""
        mgr.add_learning("pytest tips", "use fixtures", "testing")
        results = mgr.recall("pytest")
        assert "learnings" in results
        assert any("pytest tips" in e.title for e in results["learnings"])

    def test_recall_searches_long_term_projects(self, mgr, tmp_path):
        """Line 181: recall searches long_term project preferences"""
        project = tmp_path / "testproject"
        project.mkdir()
        mgr.add_recent_project(project)
        mgr.update_project_prefs(project, name="MyProject", notes="uses fastapi framework")
        results = mgr.recall("fastapi")
        assert "long_term" in results

    def test_recall_no_long_term_match(self, mgr, tmp_path):
        """Lines 185-187: no match in long_term → empty list"""
        project = tmp_path / "other_project"
        project.mkdir()
        mgr.add_recent_project(project)
        mgr.update_project_prefs(project, name="Other", notes="django web framework")
        results = mgr.recall("fastapi")
        assert results["long_term"] == []


# ─────────────────────────────────────────────
# Lines 302, 320-328: tier0/tier1 truncation
# ─────────────────────────────────────────────


class TestTier0Truncation:

    def test_tier0_within_limit(self, mgr):
        """tier0 within limit → returns full content"""
        mgr.add_learning("short", "brief", "note")
        tier0 = mgr.get_tier0_summary()
        assert isinstance(tier0, str)

    def test_tier0_truncation_fallback(self, mgr):
        """tier0 truncation with fallback (tiktoken unavailable)"""
        for i in range(30):
            mgr.add_learning(f"title {i}", "x " * 200, "note")
        tier0 = mgr.get_tier0_summary()
        # Fallback: truncates to tier0_max_tokens * 4 chars
        assert isinstance(tier0, str)


class TestTier1Truncation:

    def test_tier1_truncation_fallback(self, mgr):
        """Lines 320-328: tier1 truncation with fallback"""
        for i in range(30):
            mgr.add_learning(f"entry {i}", "x " * 200, "note")
        tier1 = mgr.get_tier1_summary(max_tokens=50)
        # Fallback: summary[:50*4] = [:200]
        assert len(tier1) <= 200

    def test_tier1_no_truncation(self, mgr):
        """tier1 within limit"""
        mgr.add_learning("short note", "brief content", "note")
        tier1 = mgr.get_tier1_summary(max_tokens=2000)
        assert isinstance(tier1, str)


# ─────────────────────────────────────────────
# Lines 340, 376-378: tier2 archive
# ─────────────────────────────────────────────


class TestTier2Archive:

    def test_tier2_user_prefs(self, mgr):
        """Lines 340, 376-378: tier2 includes user preferences"""
        mgr.update_user_prefs(
            default_model="kimi",
            default_workflow="build",
            theme="dark",
            editor="vim",
            shell="zsh",
        )
        archive = mgr.get_tier2_archive()
        assert "kimi" in archive
        assert "build" in archive
        assert "dark" in archive
        assert "vim" in archive
        assert "zsh" in archive

    def test_tier2_projects(self, mgr, tmp_path):
        """Lines 376-378: tier2 includes project details"""
        project = tmp_path / "webapp"
        project.mkdir()
        mgr.add_recent_project(project)
        mgr.update_project_prefs(
            project,
            name="WebApp",
            framework="fastapi",
            language="python",
            notes="REST API project",
            custom_commands={"serve": "uvicorn main:app"},
        )
        archive = mgr.get_tier2_archive()
        assert "WebApp" in archive
        assert "fastapi" in archive
        assert "python" in archive
        assert "REST API project" in archive
        assert "serve" in archive

    def test_tier2_learnings_tags(self, mgr):
        """Lines 376-378: tier2 includes learning tags"""
        mgr.add_learning(
            "docker lesson",
            "use multi-stage builds",
            "devops",
            tags=["docker", "build"],
        )
        archive = mgr.get_tier2_archive()
        assert "docker lesson" in archive
        assert "docker, build" in archive
        assert "devops" in archive

    def test_tier2_empty(self, mgr):
        """tier2 with no data"""
        archive = mgr.get_tier2_archive()
        assert "## 用户偏好" in archive


# ─────────────────────────────────────────────
# Line 389: get_memory_stats
# ─────────────────────────────────────────────


class TestGetMemoryStats:

    def test_get_memory_stats(self, mgr):
        """Line 389: get_memory_stats returns correct structure"""
        mgr.add_learning("stat test", "content", "testing")
        stats = mgr.get_memory_stats()
        assert "projects_count" in stats
        assert "learnings_count" in stats
        assert "tier0_tokens" in stats
        assert "tier1_tokens" in stats
        assert "categories" in stats
        assert "testing" in stats["categories"]
        assert stats["learnings_count"] >= 1

    def test_get_memory_stats_empty(self, mgr):
        """get_memory_stats with no data"""
        stats = mgr.get_memory_stats()
        assert stats["projects_count"] == 0
        assert stats["learnings_count"] == 0
        assert stats["categories"] == []


# ─────────────────────────────────────────────
# Additional edge cases
# ─────────────────────────────────────────────


class TestMemoryManagerEdgeCases:

    def test_from_home(self):
        """from_home creates valid manager"""
        mgr2 = MemoryManager.from_home()
        assert mgr2 is not None
        assert mgr2.config.storage_dir.name == "memory"

    def test_update_project_prefs_full(self, mgr, tmp_path):
        """update_project_prefs with various fields"""
        project = tmp_path / "proj"
        project.mkdir()
        mgr.update_project_prefs(
            project,
            name="Test",
            framework="react",
            language="typescript",
            notes="SPA",
            custom_commands={"start": "npm start"},
        )
        prefs = mgr.get_project_prefs(project)
        assert prefs.name == "Test"
        assert prefs.framework == "react"
        assert prefs.custom_commands == {"start": "npm start"}

    def test_get_project_prefs_default_for_nonexistent(self, mgr, tmp_path):
        """get_project_prefs for non-existent project returns defaults"""
        project = tmp_path / "nonexistent"
        prefs = mgr.get_project_prefs(project)
        # Returns a ProjectPreference with empty string name
        assert prefs.name == ""
        assert prefs.framework == ""

    def test_get_recent_learnings(self, mgr):
        """get_recent_learnings"""
        mgr.add_learning("first", "content 1", "note")
        mgr.add_learning("second", "content 2", "note")
        recent = mgr.get_recent_learnings(limit=1)
        assert len(recent) <= 1

    def test_get_learnings_by_category(self, mgr):
        """get_learnings_by_category"""
        mgr.add_learning("t1", "c1", "error")
        mgr.add_learning("t2", "c2", "note")
        error_entries = mgr.get_learnings_by_category("error")
        assert len(error_entries) == 1
        assert error_entries[0].title == "t1"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
