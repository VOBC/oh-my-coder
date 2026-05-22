"""
Tests for src/agents/evolution.py

Covers:
- EvolutionRecord dataclass
- SuccessPattern dataclass
- EvolutionConfig dataclass
- EvolutionStore (load/save evolution history, success patterns)
- DecisionRecord dataclass
- DecisionMemory (record_decision / retrieve / list_decisions)
"""

import re
from pathlib import Path
from typing import Any

from src.agents.evolution import (
    DecisionMemory,
    DecisionRecord,
    EvolutionConfig,
    EvolutionRecord,
    EvolutionStore,
    SuccessPattern,
)

# =============================================================================
# Fixtures
# =============================================================================

def _make_evolution_record(**overrides: Any) -> EvolutionRecord:
    defaults: dict[str, Any] = dict(
        id="evo-1700000000",
        timestamp="2024-01-01T10:00:00",
        agent_type="coder",
        generation=2,
        trigger="success_rate_low",
        before_state={"success_rate": 0.6},
        after_state={"success_rate": 0.85},
        changes=["Added retry logic", "Improved prompt"],
        effectiveness=0.85,
    )
    defaults.update(overrides)
    return EvolutionRecord(**defaults)


def _make_success_pattern(**overrides: Any) -> SuccessPattern:
    defaults: dict[str, Any] = dict(
        id="coder-fastapi-retry",
        pattern_type="strategy",
        description="Use tenacity for API retry",
        context="API calling with transient failures",
        effectiveness_score=0.9,
        occurrences=5,
        last_seen="2024-01-01T10:00:00",
        examples=["omc/core/retry.py"],
    )
    defaults.update(overrides)
    return SuccessPattern(**defaults)


def _make_decision_record(**overrides: Any) -> DecisionRecord:
    defaults: dict[str, Any] = dict(
        id="2024-01-01-use-fastapi",
        title="Use FastAPI for API layer",
        timestamp="2024-01-01T10:00:00",
        agent_type="architect",
        category="solution_choice",
        problem="Need a web framework",
        context="Web API for omc CLI",
        chosen_solution="Use FastAPI with async endpoints",
        rejected_alternatives=["flask", "django"],
        result="success",
        outcome="2x performance improvement",
        reusable_for="Any Python web API project",
        keywords=["fastapi", "async", "web"],
        related_files=["src/web/app.py"],
        version_tag="v1.0.0",
    )
    defaults.update(overrides)
    return DecisionRecord(**defaults)


# =============================================================================
# EvolutionRecord Tests
# =============================================================================

class TestEvolutionRecord:
    def test_basic_creation(self) -> None:
        r = _make_evolution_record()
        assert r.id == "evo-1700000000"
        assert r.agent_type == "coder"
        assert r.generation == 2
        assert r.effectiveness == 0.85

    def test_defaults(self) -> None:
        r = EvolutionRecord()
        assert r.id == ""
        assert r.agent_type == ""
        assert r.generation == 1
        assert r.trigger == ""
        assert r.before_state == {}
        assert r.after_state == {}
        assert r.changes == []
        assert r.effectiveness is None


# =============================================================================
# SuccessPattern Tests
# =============================================================================

class TestSuccessPattern:
    def test_basic_creation(self) -> None:
        p = _make_success_pattern()
        assert p.id == "coder-fastapi-retry"
        assert p.pattern_type == "strategy"
        assert p.effectiveness_score == 0.9
        assert p.occurrences == 5

    def test_defaults(self) -> None:
        p = SuccessPattern()
        assert p.id == ""
        assert p.pattern_type == ""
        assert p.effectiveness_score == 0.0
        assert p.occurrences == 0
        assert p.examples == []


# =============================================================================
# EvolutionConfig Tests
# =============================================================================

class TestEvolutionConfig:
    def test_defaults(self) -> None:
        c = EvolutionConfig()
        assert c.enabled is True
        assert c.improvement_threshold == 0.8
        assert c.min_samples == 5
        assert c.max_evolution_history == 100
        assert c.pattern_confidence_threshold == 0.7
        assert c.evolution_cooldown_hours == 24

    def test_custom_values(self) -> None:
        c = EvolutionConfig(
            enabled=False,
            improvement_threshold=0.7,
            min_samples=10,
        )
        assert c.enabled is False
        assert c.improvement_threshold == 0.7
        assert c.min_samples == 10


# =============================================================================
# EvolutionStore Tests
# =============================================================================

class TestEvolutionStore:
    def test_init_creates_dirs(self, tmp_path: Path) -> None:
        state_dir = tmp_path / "state"
        store = EvolutionStore(state_dir=state_dir)
        assert store.state_dir == state_dir
        assert store.agents_dir == state_dir / "agents"

    def test_save_and_load_evolution_history(self, tmp_path: Path) -> None:
        store = EvolutionStore(state_dir=tmp_path)
        record = _make_evolution_record()
        store.save_evolution_record(record)

        history = store.load_evolution_history(record.agent_type)
        assert len(history) == 1
        assert history[0].id == record.id
        assert history[0].agent_type == record.agent_type

    def test_load_evolution_history_empty(self, tmp_path: Path) -> None:
        store = EvolutionStore(state_dir=tmp_path)
        history = store.load_evolution_history("nonexistent")
        assert history == []

    def test_get_current_generation(self, tmp_path: Path) -> None:
        store = EvolutionStore(state_dir=tmp_path)
        # No history yet
        assert store.get_current_generation("coder") == 1

        # Add a record
        record = _make_evolution_record(agent_type="coder", generation=3)
        store.save_evolution_record(record)
        assert store.get_current_generation("coder") == 4

    def test_save_and_load_success_patterns(self, tmp_path: Path) -> None:
        store = EvolutionStore(state_dir=tmp_path)
        pattern = _make_success_pattern()
        store.save_success_pattern(pattern)

        patterns = store.load_success_patterns(pattern.id.split("-")[0])
        assert len(patterns) >= 1
        assert any(p.id == pattern.id for p in patterns)

    def test_add_success_pattern(self, tmp_path: Path) -> None:
        store = EvolutionStore(state_dir=tmp_path)
        pid = store.add_success_pattern(
            agent_name="coder",
            pattern_type="prompt_technique",
            description="Chain-of-thought for debugging",
            context="Debugging complex errors",
            example="omc/agents/debugger.py",
        )
        assert pid != ""
        patterns = store.load_success_patterns("coder")
        assert len(patterns) == 1
        assert patterns[0].pattern_type == "prompt_technique"

    def test_load_optimized_prompt_none(self, tmp_path: Path) -> None:
        store = EvolutionStore(state_dir=tmp_path)
        result = store.load_optimized_prompt("coder")
        assert result is None

    def test_save_evolution_record_creates_agent_dir(self, tmp_path: Path) -> None:
        store = EvolutionStore(state_dir=tmp_path)
        record = _make_evolution_record(agent_type="new_agent")
        store.save_evolution_record(record)
        agent_dir = tmp_path / "agents" / "new_agent"
        assert agent_dir.exists()

    def test_multiple_records(self, tmp_path: Path) -> None:
        store = EvolutionStore(state_dir=tmp_path)
        for i in range(3):
            record = _make_evolution_record(
                id=f"evo-{i}", agent_type="coder"
            )
            store.save_evolution_record(record)
        history = store.load_evolution_history("coder")
        assert len(history) == 3

    def test_corrupted_evolution_history(self, tmp_path: Path) -> None:
        agent_dir = tmp_path / "agents" / "coder"
        agent_dir.mkdir(parents=True)
        (agent_dir / "evolution_history.json").write_text("{invalid json}")
        store = EvolutionStore(state_dir=tmp_path)
        history = store.load_evolution_history("coder")
        assert history == []


# =============================================================================
# DecisionRecord Tests
# =============================================================================

class TestDecisionRecord:
    def test_basic_creation(self) -> None:
        r = _make_decision_record()
        assert r.id == "2024-01-01-use-fastapi"
        assert r.title == "Use FastAPI for API layer"
        assert r.category == "solution_choice"
        assert r.result == "success"

    def test_defaults(self) -> None:
        r = DecisionRecord()
        assert r.id == ""
        assert r.title == ""
        assert r.category == ""
        assert r.problem == ""
        assert r.chosen_solution == ""
        assert r.rejected_alternatives == []
        assert r.keywords == []
        assert r.related_files == []

    def test_keywords_list(self) -> None:
        r = _make_decision_record(keywords=["python", "testing", "pytest"])
        assert "pytest" in r.keywords
        assert len(r.keywords) == 3


# =============================================================================
# DecisionMemory Tests
# =============================================================================

class TestDecisionMemory:
    def test_init_creates_dir(self, tmp_path: Path) -> None:
        dm = DecisionMemory(state_dir=tmp_path)
        assert dm.decisions_dir.exists()

    def test_record_and_retrieve(self, tmp_path: Path) -> None:
        dm = DecisionMemory(state_dir=tmp_path)
        content = dm.record_decision(
            title="Use FastAPI",
            problem="Need web framework",
            chosen_solution="FastAPI",
            agent_type="architect",
            category="solution_choice",
            result="success",
            outcome="Good",
            keywords=["fastapi", "web"],
        )
        assert content != ""

        # Retrieve
        results = dm.retrieve("fastapi")
        assert len(results) >= 1
        assert any("FastAPI" in r.title for r in results)

    def test_record_decision_with_rejected(self, tmp_path: Path) -> None:
        dm = DecisionMemory(state_dir=tmp_path)
        dm.record_decision(
            title="Use Rust",
            problem="Need performance",
            chosen_solution="Rust",
            rejected_alternatives=["Python", "C++"],
            keywords=["rust", "performance"],
        )
        decisions = dm.list_decisions()
        assert len(decisions) == 1
        assert decisions[0].rejected_alternatives == ["Python", "C++"]

    def test_retrieve_no_match(self, tmp_path: Path) -> None:
        dm = DecisionMemory(state_dir=tmp_path)
        results = dm.retrieve("nonexistent_keyword_xyz")
        assert results == []

    def test_retrieve_empty_query(self, tmp_path: Path) -> None:
        dm = DecisionMemory(state_dir=tmp_path)
        # Record a decision first
        dm.record_decision(
            title="Test",
            problem="p",
            chosen_solution="s",
            keywords=["test"],
        )
        # Empty query should return all or empty
        results = dm.retrieve("")
        assert isinstance(results, list)

    def test_list_decisions(self, tmp_path: Path) -> None:
        dm = DecisionMemory(state_dir=tmp_path)
        for i in range(3):
            dm.record_decision(
                title=f"Decision {i}",
                problem=f"problem {i}",
                chosen_solution=f"solution {i}",
                keywords=[f"kw{i}"],
            )
        decisions = dm.list_decisions()
        assert len(decisions) == 3

    def test_list_decisions_with_category(self, tmp_path: Path) -> None:
        dm = DecisionMemory(state_dir=tmp_path)
        dm.record_decision(
            title="Decision 1",
            problem="p",
            chosen_solution="s",
            category="bug_fix",
            keywords=["k"],
        )
        dm.record_decision(
            title="Decision 2",
            problem="p",
            chosen_solution="s",
            category="solution_choice",
            keywords=["k"],
        )
        results = dm.list_decisions(category="bug_fix")
        assert len(results) == 1

    def test_record_decision_persistence(self, tmp_path: Path) -> None:
        dm1 = DecisionMemory(state_dir=tmp_path)
        dm1.record_decision(
            title="Persistent",
            problem="p",
            chosen_solution="s",
            keywords=["persist"],
        )

        dm2 = DecisionMemory(state_dir=tmp_path)
        results = dm2.retrieve("persist")
        assert len(results) >= 1

    def test_record_decision_id_format(self, tmp_path: Path) -> None:
        dm = DecisionMemory(state_dir=tmp_path)
        dm.record_decision(
            title="My Awesome Decision!",
            problem="p",
            chosen_solution="s",
        )
        # Check that a .md file was created
        md_files = list((tmp_path / "decisions").glob("*.md"))
        assert len(md_files) == 1
        assert "my-awesome-decision" in md_files[0].name

    def test_record_decision_with_related_files(self, tmp_path: Path) -> None:
        dm = DecisionMemory(state_dir=tmp_path)
        dm.record_decision(
            title="Test",
            problem="p",
            chosen_solution="s",
            related_files=["src/main.py", "tests/test_main.py"],
            keywords=["test"],
        )
        decisions = dm.list_decisions()
        assert len(decisions[0].related_files) == 2

    def test_retrieve_by_title(self, tmp_path: Path) -> None:
        dm = DecisionMemory(state_dir=tmp_path)
        dm.record_decision(
            title="Use FastAPI for API",
            problem="Need API framework",
            chosen_solution="FastAPI",
            keywords=["fastapi"],
        )
        results = dm.retrieve("FastAPI")
        assert len(results) >= 1

    def test_save_and_load_optimized_prompt(self, tmp_path: Path) -> None:
        store = EvolutionStore(state_dir=tmp_path)
        agent_name = "coder"

        # 先没有 prompt
        assert store.load_optimized_prompt(agent_name) is None

        # 保存 prompt
        store.save_optimized_prompt(agent_name, "You are a helpful coder.\nversion: 3")

        # 读取 prompt
        result = store.load_optimized_prompt(agent_name)
        assert result is not None
        assert "helpful coder" in result

    def test_get_prompt_version(self, tmp_path: Path) -> None:
        store = EvolutionStore(state_dir=tmp_path)
        agent_name = "coder"

        # 没有文件时返回 0
        assert store.get_prompt_version(agent_name) == 0

        # 写入带 version 的 prompt
        store.save_optimized_prompt(agent_name, "# version: 5\nYou are a coder.")
        assert store.get_prompt_version(agent_name) == 5

    def test_get_prompt_version_no_version_line(self, tmp_path: Path) -> None:
        store = EvolutionStore(state_dir=tmp_path)
        agent_name = "coder"

        # 写入不含 version 的 prompt
        store.save_optimized_prompt(agent_name, "You are a coder.")
        assert store.get_prompt_version(agent_name) == 1

    def test_get_evolution_stats(self, tmp_path: Path) -> None:
        store = EvolutionStore(state_dir=tmp_path)
        agent_name = "coder"

        # 空历史
        stats = store.get_evolution_stats(agent_name)
        assert stats["total_evolutions"] == 0
        assert stats["current_generation"] == 1
        assert stats["total_patterns"] == 0

        # 加记录
        record = _make_evolution_record(agent_type=agent_name, generation=2, effectiveness=0.9)
        store.save_evolution_record(record)

        stats = store.get_evolution_stats(agent_name)
        assert stats["total_evolutions"] == 1
        assert stats["current_generation"] == 3

    def test_get_evolution_stats_with_patterns(self, tmp_path: Path) -> None:
        store = EvolutionStore(state_dir=tmp_path)
        agent_name = "coder"

        # 加 pattern
        store.add_success_pattern(
            agent_name=agent_name,
            pattern_type="strategy",
            description="Use tenacity",
            context="API",
        )

        stats = store.get_evolution_stats(agent_name)
        assert stats["total_patterns"] >= 1


# =============================================================================
# DecisionMemory.get_stats Tests
# =============================================================================

class TestDecisionMemoryGetStats:
    def test_get_stats_empty(self, tmp_path: Path) -> None:
        dm = DecisionMemory(state_dir=tmp_path)
        stats = dm.get_stats()
        assert stats["total_decisions"] == 0
        assert stats["by_category"] == {}

    def test_get_stats_with_decisions(self, tmp_path: Path) -> None:
        dm = DecisionMemory(state_dir=tmp_path)
        dm.record_decision(
            title="Decision 1",
            problem="p",
            chosen_solution="s",
            category="bug_fix",
            keywords=["k"],
        )
        dm.record_decision(
            title="Decision 2",
            problem="p",
            chosen_solution="s",
            category="solution_choice",
            keywords=["k"],
        )

        stats = dm.get_stats()
        assert stats["total_decisions"] == 2
        assert stats["by_category"]["bug_fix"] == 1
        assert stats["by_category"]["solution_choice"] == 1

    def test_get_stats_counts_keywords(self, tmp_path: Path) -> None:
        dm = DecisionMemory(state_dir=tmp_path)
        dm.record_decision(
            title="D",
            problem="p",
            chosen_solution="s",
            keywords=["python", "testing"],
        )
        stats = dm.get_stats()
        assert stats["total_decisions"] >= 1


# =============================================================================
# Additional Edge Case Tests
# =============================================================================

class TestEvolutionStoreEdgeCases:
    def test_save_evolution_record_return_value(self, tmp_path: Path) -> None:
        store = EvolutionStore(state_dir=tmp_path)
        record = _make_evolution_record()
        result = store.save_evolution_record(record)
        assert result == record.id

    def test_load_success_patterns_empty(self, tmp_path: Path) -> None:
        store = EvolutionStore(state_dir=tmp_path)
        patterns = store.load_success_patterns("nonexistent")
        assert patterns == []

    def test_add_success_pattern_return_value(self, tmp_path: Path) -> None:
        store = EvolutionStore(state_dir=tmp_path)
        pid = store.add_success_pattern(
            agent_name="coder",
            pattern_type="prompt_technique",
            description="Chain-of-thought",
            context="Debug",
        )
        assert pid != ""
        assert "coder" in pid

    def test_corrupted_patterns_file(self, tmp_path: Path) -> None:
        agent_dir = tmp_path / "agents" / "coder"
        agent_dir.mkdir(parents=True)
        (agent_dir / "success_patterns.json").write_text("{invalid}")
        store = EvolutionStore(state_dir=tmp_path)
        patterns = store.load_success_patterns("coder")
        assert patterns == []

    def test_pattern_update_existing(self, tmp_path: Path) -> None:
        store = EvolutionStore(state_dir=tmp_path)
        # 添加一个 pattern
        pid = store.add_success_pattern(
            agent_name="coder",
            pattern_type="strategy",
            description="Original",
            context="Test",
        )
        # 手动修改并重新保存（模拟更新）
        pattern = _make_success_pattern(id=pid, description="Updated")
        store.save_success_pattern(pattern)

        patterns = store.load_success_patterns("coder")
        assert len(patterns) == 1
        assert patterns[0].description == "Updated"


class TestDecisionMemoryEdgeCases:
    def test_record_decision_no_keywords_auto_extract(self, tmp_path: Path) -> None:
        dm = DecisionMemory(state_dir=tmp_path)
        dm.record_decision(
            title="Use FastAPI for API",
            problem="Need a web framework for REST API",
            chosen_solution="Use FastAPI with async support",
        )
        # 应该自动提取关键词
        results = dm.retrieve("fastapi")
        assert len(results) >= 1

    def test_record_decision_custom_timestamp(self, tmp_path: Path) -> None:
        dm = DecisionMemory(state_dir=tmp_path)
        content = dm.record_decision(
            title="Test",
            problem="p",
            chosen_solution="s",
        )
        # ID 应该包含日期
        assert re.match(r"\d{4}-\d{2}-\d{2}-test", content)

    def test_retrieve_case_insensitive(self, tmp_path: Path) -> None:
        dm = DecisionMemory(state_dir=tmp_path)
        dm.record_decision(
            title="FastAPI Decision",
            problem="p",
            chosen_solution="s",
            keywords=["FastAPI"],
        )
        # 小写查询应该匹配大写关键词
        results = dm.retrieve("fastapi")
        assert len(results) >= 1

    def test_list_decisions_limit(self, tmp_path: Path) -> None:
        dm = DecisionMemory(state_dir=tmp_path)
        for i in range(5):
            dm.record_decision(
                title=f"Decision {i}",
                problem="p",
                chosen_solution="s",
                keywords=["k"],
            )
        decisions = dm.list_decisions(limit=3)
        assert len(decisions) == 3

    def test_list_decisions_empty(self, tmp_path: Path) -> None:
        dm = DecisionMemory(state_dir=tmp_path)
        decisions = dm.list_decisions()
        assert decisions == []

    def test_slugify_special_chars(self, tmp_path: Path) -> None:
        dm = DecisionMemory(state_dir=tmp_path)
        content = dm.record_decision(
            title="Special!@#$%Characters",
            problem="p",
            chosen_solution="s",
        )
        # slug 应该只包含字母数字和短横线
        assert "!" not in content
        assert "@" not in content

    def test_decision_record_round_trip(self, tmp_path: Path) -> None:
        dm = DecisionMemory(state_dir=tmp_path)
        dm.record_decision(
            title="Round Trip Test",
            problem="Test problem",
            chosen_solution="Test solution",
            agent_type="tester",
            category="architecture",
            rejected_alternatives=["alt1", "alt2"],
            result="success",
            outcome="Good",
            reusable_for="Testing",
            keywords=["test", "roundtrip"],
            related_files=["tests/test.py"],
            version_tag="v1.0.0",
        )

        # 读取回来
        decisions = dm.list_decisions()
        assert len(decisions) == 1
        d = decisions[0]
        assert d.title == "Round Trip Test"
        assert d.agent_type == "tester"
        assert d.category == "architecture"
        assert d.rejected_alternatives == ["alt1", "alt2"]
        assert d.related_files == ["tests/test.py"]
        assert d.version_tag == "v1.0.0"


# =============================================================================
# ImportError fallback test (if src.agents.evolution is broken)
# =============================================================================

class TestEvolutionImport:
    def test_all_exports_importable(self) -> None:
        from src.agents.evolution import (
            DecisionMemory,
            DecisionRecord,
            EvolutionConfig,
            EvolutionRecord,
            EvolutionStore,
            SuccessPattern,
        )
        assert DecisionRecord is not None
        assert SuccessPattern is not None
        assert EvolutionConfig is not None
        assert EvolutionStore is not None
        assert DecisionMemory is not None
        assert EvolutionRecord is not None

