"""
Edge-case tests for src/agents/evolution.py covering exception handlers.
"""
from __future__ import annotations

import json
from pathlib import Path

from src.agents.evolution import (
    DecisionMemory,
    EvolutionRecord,
    EvolutionStore,
)

# ── save_evolution_record edge cases ────────────────────────────────────


class TestSaveEvolutionRecordEdges:
    def test_save_with_corrupt_existing_history(self, tmp_path: Path):
        """Cover lines 120-121: JSONDecodeError when reading existing history."""
        store = EvolutionStore(tmp_path)
        agent_dir = store._agent_dir("test-agent")
        agent_dir.mkdir(parents=True, exist_ok=True)
        history_file = agent_dir / "evolution_history.json"
        history_file.write_text("this is not json {{{", encoding="utf-8")

        record = EvolutionRecord(
            id="evo-1",
            agent_type="test-agent",
            generation=1,
            trigger="manual",
            before_state="v1",
            after_state="v2",
            changes=["change1"],
        )
        store.save_evolution_record(record)
        # Should not raise, should overwrite
        data = json.loads(history_file.read_text(encoding="utf-8"))
        assert len(data["records"]) >= 1

    def test_save_with_100_existing_records(self, tmp_path: Path):
        """Cover line 140: truncation when exceeding max_records."""
        store = EvolutionStore(tmp_path)
        agent_dir = store._agent_dir("test-agent")
        agent_dir.mkdir(parents=True, exist_ok=True)
        history_file = agent_dir / "evolution_history.json"
        # Create 100 existing records
        existing_records = [
            {"id": f"evo-{i}", "agent_type": "test-agent"}
            for i in range(100)
        ]
        history_file.write_text(
            json.dumps({"records": existing_records}, ensure_ascii=False)
        )

        record = EvolutionRecord(
            id="evo-new",
            agent_type="test-agent",
            generation=1,
            trigger="manual",
        )
        store.save_evolution_record(record)
        data = json.loads(history_file.read_text(encoding="utf-8"))
        records = data["records"]
        # Should be 100 (truncated to max)
        assert len(records) == 100
        # Newest record should be last
        assert records[-1]["id"] == "evo-new"

    def test_save_with_101_records_truncates_to_100(self, tmp_path: Path):
        """When 101 records exist, saving truncates to 100 (covers line 140)."""
        store = EvolutionStore(tmp_path)
        agent_dir = store._agent_dir("test-agent")
        agent_dir.mkdir(parents=True, exist_ok=True)
        history_file = agent_dir / "evolution_history.json"
        existing_records = [
            {"id": f"evo-{i}", "agent_type": "test-agent"}
            for i in range(101)
        ]
        history_file.write_text(
            json.dumps({"records": existing_records}, ensure_ascii=False)
        )

        record = EvolutionRecord(
            id="evo-new2",
            agent_type="test-agent",
            generation=2,
            trigger="auto",
        )
        store.save_evolution_record(record)
        data = json.loads(history_file.read_text(encoding="utf-8"))
        assert len(data["records"]) == 100
        assert data["records"][-1]["id"] == "evo-new2"


# ── save_evolution_record: except KeyError ──────────────────────────────


class TestEvolutionRecordKeyError:
    def test_save_record_json_without_records_key(self, tmp_path: Path):
        """Cover except KeyError in save_evolution_record."""
        store = EvolutionStore(tmp_path)
        agent_dir = store._agent_dir("test-agent")
        agent_dir.mkdir(parents=True, exist_ok=True)
        history_file = agent_dir / "evolution_history.json"
        # Valid JSON but without "records" key
        history_file.write_text(
            json.dumps({"other": "data"}),
            encoding="utf-8",
        )

        record = EvolutionRecord(
            id="evo-keyerr",
            agent_type="test-agent",
            generation=1,
            trigger="manual",
        )
        store.save_evolution_record(record)
        data = json.loads(history_file.read_text(encoding="utf-8"))
        assert len(data["records"]) == 1
        assert data["records"][0]["id"] == "evo-keyerr"


# ── add_success_pattern edge cases ──────────────────────────────────────


class TestAddSuccessPatternEdges:
    def test_with_corrupt_patterns_file(self, tmp_path: Path):
        """Cover lines 188-189: JSONDecodeError when reading patterns."""
        store = EvolutionStore(tmp_path)
        agent_dir = store._agent_dir("test-agent")
        agent_dir.mkdir(parents=True, exist_ok=True)
        patterns_file = agent_dir / "success_patterns.json"
        patterns_file.write_text("not json !!!", encoding="utf-8")

        store.add_success_pattern(
            agent_name="test-agent",
            pattern_type="fix",
            description="test pattern",
        )
        data = json.loads(patterns_file.read_text(encoding="utf-8"))
        assert len(data.get("patterns", [])) == 1

    def test_add_pattern_key_error(self, tmp_path: Path):
        """Cover KeyError in add_success_pattern."""
        store = EvolutionStore(tmp_path)
        agent_dir = store._agent_dir("test-agent")
        agent_dir.mkdir(parents=True, exist_ok=True)
        patterns_file = agent_dir / "success_patterns.json"
        patterns_file.write_text(json.dumps({"wrong_key": []}))

        store.add_success_pattern(
            agent_name="test-agent",
            pattern_type="workflow",
            description="key error test",
        )
        data = json.loads(patterns_file.read_text(encoding="utf-8"))
        assert len(data.get("patterns", [])) >= 1


# ── load_success_patterns edge cases ───────────────────────────────────


class TestLoadSuccessPatternsEdges:
    def test_with_corrupt_file(self, tmp_path: Path):
        """Cover lines 232-236: error reading patterns file."""
        store = EvolutionStore(tmp_path)
        agent_dir = store._agent_dir("test-agent")
        agent_dir.mkdir(parents=True, exist_ok=True)
        (agent_dir / "success_patterns.json").write_text(
            "broken json {{", encoding="utf-8"
        )

        patterns = store.load_success_patterns("test-agent")
        assert patterns == []

    def test_load_patterns_key_error(self, tmp_path: Path):
        """Cover KeyError in load_success_patterns."""
        store = EvolutionStore(tmp_path)
        agent_dir = store._agent_dir("test-agent")
        agent_dir.mkdir(parents=True, exist_ok=True)
        (agent_dir / "success_patterns.json").write_text(
            json.dumps({"other": "stuff"}),
        )

        patterns = store.load_success_patterns("test-agent")
        assert patterns == []  # defaults to empty


# ── DecisionMemory: list_decisions and _parse_source_file ───────────────


class TestDecisionMemoryEdges:
    def test_list_decisions_with_corrupt_file(self, tmp_path: Path):
        """Cover lines 801-804: exception in list_decisions."""
        dm = DecisionMemory(tmp_path)
        # Create a decision file that will cause parsing error
        dec_dir = tmp_path / "decisions"
        dec_dir.mkdir(parents=True, exist_ok=True)
        (dec_dir / "bad.json").write_text("not json", encoding="utf-8")

        results = dm.list_decisions(category="test")
        # Should not crash
        assert isinstance(results, list)


class TestDecisionMemoryParseError:
    def test_parse_bad_content(self, tmp_path: Path):
        """Cover _parse_source_file error path (line 671-672)."""
        dm = DecisionMemory(tmp_path)
        # Create decision directory with a file that will fail to parse
        dec_dir = tmp_path / "decisions"
        dec_dir.mkdir(parents=True, exist_ok=True)
        (dec_dir / "broken.md").write_text("not a decision format", encoding="utf-8")

        # list_decisions should skip bad files
        results = dm.list_decisions()
        assert isinstance(results, list)
