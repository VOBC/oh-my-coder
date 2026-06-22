"""
Round 2 edge-case tests for evolution.py — covering remaining uncovered paths.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from src.agents.evolution import EvolutionStore, DecisionRecord, DecisionMemory


class TestPatternsFileError:
    """Cover lines 188-189: JSONDecodeError/KeyError when loading patterns."""

    def test_corrupt_patterns_file(self, tmp_path: Path):
        """Corrupt success_patterns.json falls back to empty list."""
        store = EvolutionStore(tmp_path)
        agent_dir = tmp_path / "agents" / "test_agent"
        agent_dir.mkdir(parents=True)
        (agent_dir / "success_patterns.json").write_text("not json {{{", encoding="utf-8")
        result = store.load_success_patterns("test_agent")
        assert result == []

    def test_missing_patterns_key(self, tmp_path: Path):
        """success_patterns.json without 'patterns' key returns empty."""
        store = EvolutionStore(tmp_path)
        agent_dir = tmp_path / "agents" / "test_agent"
        agent_dir.mkdir(parents=True)
        (agent_dir / "success_patterns.json").write_text('{"other": "data"}', encoding="utf-8")
        result = store.load_success_patterns("test_agent")
        assert result == []


class TestParseVersion:
    """Cover lines 287-288: ValueError in _parse_version."""

    def test_version_value_error_fallback(self, tmp_path: Path):
        """Non-integer version returns default 1."""
        store = EvolutionStore(tmp_path)
        agent_dir = tmp_path / "agents" / "test_agent"
        agent_dir.mkdir(parents=True)
        (agent_dir / "optimized_prompt.md").write_text(
            "version: not_a_number\n\nsome content"
        )
        result = store.get_prompt_version("test_agent")
        assert result == 1


class TestSlugifyLength:
    """Cover line 385: slug truncation when > 40 chars."""

    def test_very_long_name_truncates(self, tmp_path: Path):
        """Long names are truncated to 40 chars."""
        dm = DecisionMemory(tmp_path)
        long_name = "a" * 80 + "-with-dashes-and-special--chars"
        result = dm._slugify(long_name)
        assert len(result) <= 40
        assert not result.endswith("-")


class TestDecisionRetrieval:
    """Cover decision retrieval edge paths."""

    def test_corrupt_decision_file_skipped(self, tmp_path: Path):
        """Cover line 665: corrupt decision file triggers except Exception."""
        dm = DecisionMemory(tmp_path)
        # Create a corrupt decision file
        (dm.decisions_dir / "corrupt_decision.md").write_text(
            "not markdown {{{}\nsome invalid content", encoding="utf-8"
        )
        result = dm.retrieve("test query", limit=5)
        assert isinstance(result, list)

    def test_keyword_matching_in_relevance(self, tmp_path: Path):
        """Cover lines 671-672: keywords contribute to relevance score."""
        dm = DecisionMemory(tmp_path)
        record = DecisionRecord(
            id="test-1",
            timestamp="2024-01-01",
            problem="Database connection timeout",
            chosen_solution="Increase timeout",
            category="debugging",
            keywords=["database", "timeout"],
        )
        score = dm._calculate_relevance({"timeout"}, record)
        # Keywords matching contributes 2 points per keyword match
        # Problem match contributes 3 points
        assert score >= 3

    def test_reusable_for_matching(self, tmp_path: Path):
        """Cover lines 801-804: reusable_for contributes to relevance."""
        dm = DecisionMemory(tmp_path)
        record = DecisionRecord(
            id="test-2",
            timestamp="2024-01-01",
            problem="Some problem",
            chosen_solution="Some solution",
            category="debugging",
            reusable_for="FastAPI and Django web apps",
        )
        score = dm._calculate_relevance({"fastapi"}, record)
        assert score > 0

    def test_title_matching(self, tmp_path: Path):
        """Cover line 791: title matching in relevance (5 points)."""
        dm = DecisionMemory(tmp_path)
        record = DecisionRecord(
            id="test-3",
            title="Debugging Python import errors",
            timestamp="2024-01-01",
            problem="",
            chosen_solution="",
            category="debugging",
        )
        score = dm._calculate_relevance({"import", "errors"}, record)
        assert score >= 5

    def test_list_by_category(self, tmp_path: Path):
        """Cover lines 841-842: category filtering in list_decisions."""
        dm = DecisionMemory(tmp_path)
        # Create a properly-formatted decision file
        content = """# 2024-01-01 Database timeout fix
**Agent**: planner
**类别**: debugging
**结果**: success
## 问题背景
Database connection timeout
## 选择的方案
Increased timeout to 60s
## 关键词
database, timeout
"""
        (dm.decisions_dir / "2024-01-01-cat-test.md").write_text(content, encoding="utf-8")
        results = dm.list_decisions(category="debugging")
        assert len(results) >= 1
        assert results[0].category == "debugging"
        all_results = dm.list_decisions(category=None)
        assert len(all_results) >= 1


class TestSavePatternInternalError:
    """Cover lines 188-189: corrupt patterns file in _save_pattern_internal."""

    def test_save_pattern_with_corrupt_existing_file(self, tmp_path: Path):
        """_save_pattern_internal handles corrupt existing patterns file."""
        from src.agents.evolution import SuccessPattern
        store = EvolutionStore(tmp_path)
        agent_dir = tmp_path / "agents" / "default"
        agent_dir.mkdir(parents=True)
        (agent_dir / "success_patterns.json").write_text("not json [[{", encoding="utf-8")
        pattern = SuccessPattern(
            id="default-test1",
            pattern_type="test",
            description="test pattern",
        )
        result = store.save_success_pattern(pattern)
        assert result == "default-test1"


class TestRetrieveException:
    """Cover lines 665, 671-672: except Exception in retrieve loop."""

    def test_retrieve_with_unreadable_decision_file(self, tmp_path: Path):
        """retrieve skips files that raise exceptions."""
        dm = DecisionMemory(tmp_path)
        # Create a valid decision first so glob finds files
        content = """# 2024-01-01 Valid decision
**类别**: debugging
## 问题背景
test
## 选择的方案
test
"""
        (dm.decisions_dir / "valid_decision.md").write_text(content, encoding="utf-8")
        # Mock _parse_decision_file to raise exception for one file
        original_parse = dm._parse_decision_file
        call_count = [0]
        def raising_parse(fp, c):
            call_count[0] += 1
            if call_count[0] == 1:
                raise RuntimeError("simulated parse failure")
            return original_parse(fp, c)
        dm._parse_decision_file = raising_parse
        result = dm.retrieve("test", limit=5)
        assert isinstance(result, list)
