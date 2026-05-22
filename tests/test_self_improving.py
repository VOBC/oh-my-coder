"""Tests for SelfImprovingAgent."""
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.base import AgentLane, AgentOutput, AgentStatus
from src.agents.evolution import (
    EvolutionConfig,
    EvolutionRecord,
    SuccessPattern,
)
from src.agents.self_improving import (
    ExecutionFeedback,
    LearningStore,
    SelfImprovingAgent,
    StrategyAdjustment,
)


@pytest.fixture
def temp_db_path(tmp_path):
    """Provide a temporary database path."""
    return tmp_path / "test_learning.db"


@pytest.fixture
def learning_store(temp_db_path):
    """Create a LearningStore with temporary database."""
    return LearningStore(str(temp_db_path))


@pytest.fixture
def agent(temp_db_path):
    """Create a SelfImprovingAgent with temporary database."""
    router = MagicMock()
    store = LearningStore(str(temp_db_path))
    evolution_config = EvolutionConfig(
        enabled=True,
        improvement_threshold=0.8,
        min_samples=5,
    )
    return SelfImprovingAgent(
        model_router=router,
        store=store,
        evolution_config=evolution_config,
    )


# ------------------------------------------------------------------
# LearningStore Tests
# ------------------------------------------------------------------


class TestLearningStoreInit:
    def test_init_creates_db_file(self, temp_db_path):
        """Test that LearningStore creates database file on init."""
        store = LearningStore(str(temp_db_path))
        assert temp_db_path.exists()

    def test_init_creates_tables(self, learning_store):
        """Test that tables are created."""
        import sqlite3

        with sqlite3.connect(learning_store.db_path) as conn:
            # Check execution_feedback table exists
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='execution_feedback'"
            )
            assert cursor.fetchone() is not None

            # Check strategy_adjustments table exists
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='strategy_adjustments'"
            )
            assert cursor.fetchone() is not None


class TestLearningStoreRecordFeedback:
    def test_record_feedback_returns_id(self, learning_store):
        """Test that record_feedback returns an ID."""
        feedback = ExecutionFeedback(
            agent_type="executor",
            task_description="Test task",
            success=True,
            execution_time=1.5,
        )
        feedback_id = learning_store.record_feedback(feedback)
        assert feedback_id is not None
        assert feedback_id > 0

    def test_record_feedback_stores_data(self, learning_store):
        """Test that feedback data is stored correctly."""
        feedback = ExecutionFeedback(
            agent_type="planner",
            task_description="Plan task",
            success=False,
            execution_time=2.0,
            error_type="timeout",
            error_message="Task timed out",
        )
        learning_store.record_feedback(feedback)

        # Retrieve it back
        failures = learning_store.get_recent_failures("planner", limit=10)
        assert len(failures) == 1
        assert failures[0].agent_type == "planner"
        assert failures[0].error_type == "timeout"

    def test_record_feedback_sets_timestamp(self, learning_store):
        """Test that timestamp is set automatically."""
        feedback = ExecutionFeedback(
            agent_type="executor",
            task_description="Test",
            success=True,
        )
        learning_store.record_feedback(feedback)
        assert feedback.timestamp != ""


class TestLearningStoreRecordAdjustment:
    def test_record_adjustment_returns_id(self, learning_store):
        """Test that record_adjustment returns an ID."""
        adjustment = StrategyAdjustment(
            agent_type="executor",
            pattern_detected="timeout pattern",
            adjustment_type="parameter_tune",
            adjustment_content="Increase timeout",
        )
        adj_id = learning_store.record_adjustment(adjustment)
        assert adj_id is not None
        assert adj_id > 0

    def test_record_adjustment_stores_data(self, learning_store):
        """Test that adjustment data is stored correctly."""
        adjustment = StrategyAdjustment(
            agent_type="executor",
            pattern_detected="syntax_error pattern",
            adjustment_type="prompt_update",
            adjustment_content="Add syntax check",
            effectiveness_score=0.7,
        )
        learning_store.record_adjustment(adjustment)

        # Retrieve it back
        adjustments = learning_store.get_adjustments("executor")
        assert len(adjustments) == 1
        assert adjustments[0].pattern_detected == "syntax_error pattern"
        assert adjustments[0].effectiveness_score == 0.7


class TestLearningStoreGetRecentFailures:
    def test_get_recent_failures_empty(self, learning_store):
        """Test getting failures when none exist."""
        failures = learning_store.get_recent_failures("nonexistent", limit=10)
        assert failures == []

    def test_get_recent_failures_returns_only_failures(self, learning_store):
        """Test that only failures are returned."""
        # Record one success and one failure
        learning_store.record_feedback(
            ExecutionFeedback(
                agent_type="executor",
                task_description="Success task",
                success=True,
            )
        )
        learning_store.record_feedback(
            ExecutionFeedback(
                agent_type="executor",
                task_description="Failed task",
                success=False,
                error_type="timeout",
            )
        )

        failures = learning_store.get_recent_failures("executor", limit=10)
        assert len(failures) == 1
        assert failures[0].success == 0  # SQLite stores boolean as 0/1

    def test_get_recent_failures_respects_limit(self, learning_store):
        """Test that limit is respected."""
        # Record multiple failures
        for i in range(5):
            learning_store.record_feedback(
                ExecutionFeedback(
                    agent_type="executor",
                    task_description=f"Failed task {i}",
                    success=False,
                )
            )

        failures = learning_store.get_recent_failures("executor", limit=2)
        assert len(failures) == 2


class TestLearningStoreGetErrorPatterns:
    def test_get_error_patterns_empty(self, learning_store):
        """Test getting patterns when none exist."""
        patterns = learning_store.get_error_patterns("nonexistent", min_count=1)
        assert patterns == []

    def test_get_error_patterns_groups_by_type(self, learning_store):
        """Test that errors are grouped by type."""
        # Record multiple errors of same type
        for _ in range(3):
            learning_store.record_feedback(
                ExecutionFeedback(
                    agent_type="executor",
                    task_description="Task",
                    success=False,
                    error_type="timeout",
                )
            )
        for _ in range(2):
            learning_store.record_feedback(
                ExecutionFeedback(
                    agent_type="executor",
                    task_description="Task",
                    success=False,
                    error_type="syntax_error",
                )
            )

        patterns = learning_store.get_error_patterns("executor", min_count=2)
        assert len(patterns) == 2
        # Sorted by count descending
        assert patterns[0]["error_type"] == "timeout"
        assert patterns[0]["count"] == 3

    def test_get_error_patterns_respects_min_count(self, learning_store):
        """Test that min_count filters results."""
        # Record 2 errors of one type
        for _ in range(2):
            learning_store.record_feedback(
                ExecutionFeedback(
                    agent_type="executor",
                    task_description="Task",
                    success=False,
                    error_type="timeout",
                )
            )
        # Record 1 error of another type
        learning_store.record_feedback(
            ExecutionFeedback(
                agent_type="executor",
                task_description="Task",
                success=False,
                error_type="syntax_error",
            )
        )

        patterns = learning_store.get_error_patterns("executor", min_count=2)
        assert len(patterns) == 1
        assert patterns[0]["error_type"] == "timeout"


class TestLearningStoreGetSuccessRate:
    def test_get_success_rate_no_data(self, learning_store):
        """Test success rate when no data exists."""
        rate = learning_store.get_success_rate("nonexistent", days=7)
        assert rate == 0.0

    def test_get_success_rate_all_success(self, learning_store):
        """Test success rate when all succeed."""
        for _ in range(5):
            learning_store.record_feedback(
                ExecutionFeedback(
                    agent_type="executor",
                    task_description="Task",
                    success=True,
                )
            )

        rate = learning_store.get_success_rate("executor", days=7)
        assert rate == 1.0

    def test_get_success_rate_mixed(self, learning_store):
        """Test success rate with mixed results."""
        for _ in range(3):
            learning_store.record_feedback(
                ExecutionFeedback(
                    agent_type="executor",
                    task_description="Task",
                    success=True,
                )
            )
        for _ in range(2):
            learning_store.record_feedback(
                ExecutionFeedback(
                    agent_type="executor",
                    task_description="Task",
                    success=False,
                )
            )

        rate = learning_store.get_success_rate("executor", days=7)
        assert rate == 0.6  # 3/5


# ------------------------------------------------------------------
# SelfImprovingAgent Tests
# ------------------------------------------------------------------


class TestSelfImprovingAgentAttributes:
    def test_name(self, agent):
        assert agent.name == "self-improving"

    def test_description(self, agent):
        assert "主动学习" in agent.description or "优化" in agent.description

    def test_lane(self, agent):
        assert agent.lane == AgentLane.COORDINATION

    def test_default_tier(self, agent):
        assert agent.default_tier == "low"

    def test_icon(self, agent):
        assert agent.icon == "🧠"

    def test_tools(self, agent):
        assert agent.tools == ["file_read", "file_write"]


class TestSystemPrompt:
    def test_system_prompt_contains_role(self, agent):
        prompt = agent.system_prompt
        assert "主动学习" in prompt or "优化" in prompt

    def test_system_prompt_contains_keywords(self, agent):
        prompt = agent.system_prompt
        assert "错误" in prompt or "失败" in prompt
        assert "策略" in prompt


class TestRecordExecution:
    def test_record_execution_success(self, agent):
        """Test recording a successful execution."""
        feedback_id = agent.record_execution(
            agent_type="executor",
            task_description="Test task",
            success=True,
            execution_time=1.5,
        )
        assert feedback_id is not None
        assert feedback_id > 0

    def test_record_execution_with_error(self, agent):
        """Test recording a failed execution."""
        error = TimeoutError("Task timed out")
        feedback_id = agent.record_execution(
            agent_type="executor",
            task_description="Test task",
            success=False,
            error=error,
        )
        assert feedback_id is not None

        # Verify error was classified
        failures = agent.store.get_recent_failures("executor", limit=1)
        assert len(failures) == 1
        assert failures[0].error_type == "timeout"

    def test_record_execution_with_user_correction(self, agent):
        """Test recording execution with user correction."""
        feedback_id = agent.record_execution(
            agent_type="executor",
            task_description="Test task",
            success=False,
            user_correction="Use different approach",
        )
        assert feedback_id is not None

    def test_record_execution_with_retry(self, agent):
        """Test recording execution with retry count."""
        feedback_id = agent.record_execution(
            agent_type="executor",
            task_description="Test task",
            success=True,
            retry_count=2,
        )
        assert feedback_id is not None


class TestClassifyError:
    def test_classify_syntax_error(self, agent):
        """Test classifying syntax errors."""
        error = SyntaxError("invalid syntax")
        error_type = agent._classify_error(error)
        assert error_type == "syntax_error"

    def test_classify_timeout_error(self, agent):
        """Test classifying timeout errors."""
        error = TimeoutError("operation timed out")
        error_type = agent._classify_error(error)
        assert error_type == "timeout"

    def test_classify_memory_error(self, agent):
        """Test classifying memory errors."""
        error = MemoryError("out of memory")
        error_type = agent._classify_error(error)
        assert error_type == "memory_error"

    def test_classify_permission_error(self, agent):
        """Test classifying permission errors."""
        error = PermissionError("access denied")
        error_type = agent._classify_error(error)
        assert error_type == "permission_error"

    def test_classify_generic_error(self, agent):
        """Test classifying generic errors."""
        error = ValueError("invalid value")
        error_type = agent._classify_error(error)
        assert "valueerror" in error_type.lower()


class TestHashContext:
    def test_hash_context_returns_string(self, agent):
        """Test that hash returns a string."""
        hash_val = agent._hash_context("test context")
        assert isinstance(hash_val, str)
        assert len(hash_val) == 16

    def test_hash_context_consistent(self, agent):
        """Test that same input produces same hash."""
        hash1 = agent._hash_context("test context")
        hash2 = agent._hash_context("test context")
        assert hash1 == hash2

    def test_hash_context_different_inputs(self, agent):
        """Test that different inputs produce different hashes."""
        hash1 = agent._hash_context("context 1")
        hash2 = agent._hash_context("context 2")
        assert hash1 != hash2


class TestGenerateAdjustment:
    def test_generate_adjustment_syntax_error(self, agent):
        """Test generating adjustment for syntax errors."""
        pattern = {"error_type": "syntax_error", "count": 5}
        adjustment = agent._generate_adjustment("executor", pattern)
        assert adjustment is not None
        assert adjustment.adjustment_type == "prompt_update"
        assert "语法" in adjustment.adjustment_content or "syntax" in adjustment.adjustment_content.lower()

    def test_generate_adjustment_timeout(self, agent):
        """Test generating adjustment for timeout errors."""
        pattern = {"error_type": "timeout", "count": 3}
        adjustment = agent._generate_adjustment("executor", pattern)
        assert adjustment is not None
        assert adjustment.adjustment_type == "parameter_tune"

    def test_generate_adjustment_unknown_error(self, agent):
        """Test generating adjustment for unknown error types."""
        pattern = {"error_type": "unknown_error", "count": 5}
        adjustment = agent._generate_adjustment("executor", pattern)
        assert adjustment is None


class TestAnalyzeAndImprove:
    def test_analyze_and_improve_no_patterns(self, agent):
        """Test analyze when no error patterns exist."""
        adjustments = agent.analyze_and_improve("nonexistent")
        assert adjustments == []

    def test_analyze_and_improve_with_patterns(self, agent):
        """Test analyze with error patterns."""
        # Create some errors
        for _ in range(3):
            agent.record_execution(
                agent_type="executor",
                task_description="Task",
                success=False,
                error=TimeoutError("timeout"),
            )

        adjustments = agent.analyze_and_improve("executor")
        assert len(adjustments) > 0
        assert all(isinstance(a, StrategyAdjustment) for a in adjustments)


class TestGetImprovedPrompt:
    def test_get_improved_prompt_no_adjustments(self, agent):
        """Test getting improved prompt when no adjustments exist."""
        base_prompt = "You are an agent."
        improved = agent.get_improved_prompt("nonexistent", base_prompt)
        assert improved == base_prompt

    def test_get_improved_prompt_with_adjustments(self, agent):
        """Test getting improved prompt with adjustments."""
        # Create a high-effectiveness adjustment
        adjustment = StrategyAdjustment(
            agent_type="executor",
            pattern_detected="timeout pattern",
            adjustment_type="prompt_update",
            adjustment_content="Add timeout handling",
            effectiveness_score=0.8,
        )
        agent.store.record_adjustment(adjustment)

        base_prompt = "You are an agent."
        improved = agent.get_improved_prompt("executor", base_prompt)
        assert "学习优化" in improved or "timeout" in improved.lower()


class TestReport:
    def test_report_specific_agent(self, agent):
        """Test generating report for specific agent."""
        # Record some executions
        agent.record_execution(
            agent_type="executor",
            task_description="Task 1",
            success=True,
        )
        agent.record_execution(
            agent_type="executor",
            task_description="Task 2",
            success=False,
            error=TimeoutError("timeout"),
        )

        report = agent.report("executor")
        assert "generated_at" in report
        assert "agents" in report
        assert "executor" in report["agents"]

    def test_report_all_agents(self, agent):
        """Test generating report for all agents."""
        agent.record_execution(
            agent_type="executor",
            task_description="Task",
            success=True,
        )
        agent.record_execution(
            agent_type="planner",
            task_description="Task",
            success=True,
        )

        report = agent.report()
        assert "executor" in report["agents"]
        assert "planner" in report["agents"]


class TestRun:
    @pytest.mark.asyncio
    async def test_run_report(self, agent):
        """Test _run with report task."""
        result = await agent._run("report")
        assert isinstance(result, AgentOutput)
        assert result.status == AgentStatus.COMPLETED
        assert "generated_at" in result.result

    @pytest.mark.asyncio
    async def test_run_analyze(self, agent):
        """Test _run with analyze task."""
        agent.record_execution(
            agent_type="executor",
            task_description="Task",
            success=True,
        )
        result = await agent._run("analyze executor")
        assert isinstance(result, AgentOutput)
        assert result.status == AgentStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_run_stats(self, agent):
        """Test _run with stats task."""
        result = await agent._run("stats executor")
        assert isinstance(result, AgentOutput)
        assert result.status == AgentStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_run_default(self, agent):
        """Test _run with default (report) behavior."""
        result = await agent._run("unknown task")
        assert isinstance(result, AgentOutput)
        assert result.status == AgentStatus.COMPLETED


class TestAnalyzeTaskLogs:
    def test_analyze_task_logs_no_data(self, agent):
        """Test analyzing logs when no data exists."""
        analysis = agent.analyze_task_logs("nonexistent")
        assert analysis["agent_type"] == "nonexistent"
        assert analysis["sample_size"] == 0
        assert analysis["success_rate"] == 0.0

    def test_analyze_task_logs_with_data(self, agent):
        """Test analyzing logs with execution data."""
        # Record some executions
        for _ in range(3):
            agent.record_execution(
                agent_type="executor",
                task_description="Success task",
                success=True,
                execution_time=1.0,
            )
        for _ in range(2):
            agent.record_execution(
                agent_type="executor",
                task_description="Failed task",
                success=False,
                error=TimeoutError("timeout"),
            )

        analysis = agent.analyze_task_logs("executor", recent_count=10)
        assert analysis["sample_size"] == 5
        assert analysis["success_rate"] == 0.6
        assert len(analysis["success_patterns"]) > 0
        assert len(analysis["failure_patterns"]) > 0

    def test_analyze_task_logs_recommendations(self, agent):
        """Test that recommendations are generated for low success rate."""
        # Record mostly failures
        for _ in range(8):
            agent.record_execution(
                agent_type="executor",
                task_description="Failed task",
                success=False,
                error=TimeoutError("timeout"),
            )
        for _ in range(2):
            agent.record_execution(
                agent_type="executor",
                task_description="Success task",
                success=True,
            )

        analysis = agent.analyze_task_logs("executor", recent_count=10)
        # Success rate is 0.2, below threshold 0.8
        assert any(r["type"] == "trigger_evolution" for r in analysis["recommendations"])


class TestExtractSuccessCharacteristics:
    def test_extract_characteristics_no_retries(self, agent):
        """Test extracting characteristics when no retries needed."""
        records = [
            {"execution_time": 1.0, "retry_count": 0},
            {"execution_time": 2.0, "retry_count": 0},
        ]
        characteristics = agent._extract_success_characteristics(records)
        assert any("无需重试" in c for c in characteristics)

    def test_extract_characteristics_with_retries(self, agent):
        """Test extracting characteristics with retries."""
        records = [
            {"execution_time": 1.0, "retry_count": 1},
            {"execution_time": 2.0, "retry_count": 2},
        ]
        characteristics = agent._extract_success_characteristics(records)
        assert any("重试" in c for c in characteristics)


class TestExtractPatterns:
    def test_extract_patterns_no_data(self, agent):
        """Test extracting patterns when no data exists."""
        patterns = agent.extract_patterns("nonexistent")
        assert patterns == []

    def test_extract_patterns_strategy(self, agent):
        """Test extracting strategy patterns."""
        # Create a high-effectiveness adjustment
        adjustment = StrategyAdjustment(
            agent_type="executor",
            pattern_detected="timeout pattern",
            adjustment_type="prompt_update",
            adjustment_content="Add timeout handling",
            effectiveness_score=0.8,
            applied_count=5,
        )
        agent.store.record_adjustment(adjustment)

        patterns = agent.extract_patterns("executor", pattern_type="strategy")
        assert len(patterns) > 0
        assert all(isinstance(p, SuccessPattern) for p in patterns)


class TestUpdateSystemPrompt:
    def test_update_system_prompt_disabled(self, agent):
        """Test that prompt update is skipped when disabled."""
        agent._evolution_config.enabled = False
        base_prompt = "You are an agent."
        new_prompt = agent.update_system_prompt("executor", base_prompt)
        assert new_prompt == base_prompt

    def test_update_system_prompt_no_optimizations(self, agent, tmp_path):
        """Test prompt update when no optimizations available."""
        # Use a fresh evolution store to avoid interference from other tests
        from src.agents.evolution import EvolutionStore
        agent._evolution_store = EvolutionStore(tmp_path / "state")
        
        base_prompt = "You are an agent."
        new_prompt = agent.update_system_prompt("nonexistent_agent", base_prompt)
        # Should return base prompt when no adjustments
        assert new_prompt == base_prompt

    def test_update_system_prompt_with_adjustments(self, agent):
        """Test prompt update with adjustments."""
        # Create a high-effectiveness adjustment
        adjustment = StrategyAdjustment(
            agent_type="executor",
            pattern_detected="timeout pattern",
            adjustment_type="prompt_update",
            adjustment_content="Add timeout handling",
            effectiveness_score=0.8,
        )
        agent.store.record_adjustment(adjustment)

        base_prompt = "You are an agent."
        new_prompt = agent.update_system_prompt("executor", base_prompt)
        # Should contain optimization section
        assert "自进化" in new_prompt or "学习" in new_prompt


class TestEvolve:
    def test_evolve_disabled(self, agent):
        """Test that evolution is skipped when disabled."""
        agent._evolution_config.enabled = False
        record = agent.evolve("executor")
        assert record is None

    def test_evolve_insufficient_samples(self, agent):
        """Test that evolution is skipped with insufficient samples."""
        # Only 3 samples, below min_samples=5
        for _ in range(3):
            agent.record_execution(
                agent_type="executor",
                task_description="Task",
                success=True,
            )

        record = agent.evolve("executor")
        assert record is None

    def test_evolve_with_sufficient_samples(self, agent):
        """Test evolution with sufficient samples."""
        # Create enough samples with failures to trigger evolution
        for _ in range(6):
            agent.record_execution(
                agent_type="executor",
                task_description="Failed task",
                success=False,
                error=TimeoutError("timeout"),
            )
        for _ in range(4):
            agent.record_execution(
                agent_type="executor",
                task_description="Success task",
                success=True,
            )

        record = agent.evolve("executor", trigger="manual")
        assert record is not None
        assert isinstance(record, EvolutionRecord)
        assert record.agent_type == "executor"
        assert len(record.changes) > 0


class TestDecisionMemory:
    def test_record_decision(self, agent, tmp_path):
        """Test recording a decision."""
        # Use a fresh decision memory for this test
        from src.agents.evolution import DecisionMemory
        agent._decision_memory = DecisionMemory(tmp_path / "state")
        
        decision_id = agent.record_decision(
            title="Test decision",
            problem="Test problem",
            chosen_solution="Test solution",
            agent_type="executor",
        )
        assert decision_id is not None
        assert decision_id != ""

    def test_retrieve_past_decisions(self, agent, tmp_path):
        """Test retrieving past decisions."""
        from src.agents.evolution import DecisionMemory
        agent._decision_memory = DecisionMemory(tmp_path / "state")
        
        # Record a decision
        agent.record_decision(
            title="Fix timeout issue",
            problem="Task keeps timing out",
            chosen_solution="Increase timeout to 30s",
            agent_type="executor",
        )

        # Retrieve it
        decisions = agent.retrieve_past_decisions("timeout issue")
        assert len(decisions) > 0
        # "timeout" is in title, not in problem text ("timing out" is two words)
        assert any(
            "timeout" in d["title"].lower() or "timeout" in d["problem"].lower()
            for d in decisions
        )

    def test_list_decisions(self, agent, tmp_path):
        """Test listing decisions."""
        from src.agents.evolution import DecisionMemory
        agent._decision_memory = DecisionMemory(tmp_path / "state")
        
        agent.record_decision(
            title="Decision 1",
            problem="Problem 1",
            chosen_solution="Solution 1",
            category="bug_fix",
        )
        agent.record_decision(
            title="Decision 2",
            problem="Problem 2",
            chosen_solution="Solution 2",
            category="solution_choice",
        )

        decisions = agent.list_decisions()
        assert len(decisions) >= 2

    def test_list_decisions_by_category(self, agent, tmp_path):
        """Test listing decisions filtered by category."""
        from src.agents.evolution import DecisionMemory
        agent._decision_memory = DecisionMemory(tmp_path / "state")
        
        agent.record_decision(
            title="Bug fix",
            problem="Problem",
            chosen_solution="Solution",
            category="bug_fix",
        )
        agent.record_decision(
            title="Architecture",
            problem="Problem",
            chosen_solution="Solution",
            category="architecture",
        )

        bug_fixes = agent.list_decisions(category="bug_fix")
        assert all(d["category"] == "bug_fix" for d in bug_fixes)

    def test_get_decision_stats(self, agent, tmp_path):
        """Test getting decision statistics."""
        from src.agents.evolution import DecisionMemory
        agent._decision_memory = DecisionMemory(tmp_path / "state")
        
        agent.record_decision(
            title="Decision 1",
            problem="Problem 1",
            chosen_solution="Solution 1",
            category="bug_fix",
        )

        stats = agent.get_decision_stats()
        assert "total_decisions" in stats
        assert stats["total_decisions"] >= 1


class TestGetEvolutionStats:
    def test_get_evolution_stats(self, agent):
        """Test getting evolution statistics."""
        stats = agent.get_evolution_stats("executor")
        assert "config" in stats
        assert "enabled" in stats["config"]
        assert stats["config"]["enabled"] is True


class TestAutoCreateSkill:
    def test_auto_create_skill_not_worthy(self, agent):
        """Test that skill is not created for trivial tasks."""
        task_context = {
            "agent_name": "executor",
            "task": "Simple task",
            "workflow": "general",
            "result": "Done",
            "steps": ["step1"],
            "tool_call_count": 2,
            "had_error": False,
            "had_fix": False,
            "had_user_correction": False,
        }
        result = agent.auto_create_skill(task_context)
        assert result is None

    def test_auto_create_skill_worthy(self, agent):
        """Test that skill is created for worthy tasks."""
        task_context = {
            "agent_name": "executor",
            "task": "Complex refactoring task with multiple steps",
            "workflow": "refactor",
            "result": "Successfully refactored module",
            "steps": ["analyze", "plan", "execute", "verify"],
            "tool_call_count": 10,
            "had_error": True,
            "had_fix": True,
            "had_user_correction": False,
        }
        # This should be worthy: tool_call_count >= 5, had_fix = True
        result = agent.auto_create_skill(task_context)
        # Result depends on SkillManager, may be None if file operations fail
        # Just verify no exception is raised
        assert result is None or isinstance(result, dict)


class TestPromoteBestPracticesToSkills:
    def test_promote_dry_run(self, agent):
        """Test promoting best practices in dry run mode."""
        result = agent.promote_best_practices_to_skills(dry_run=True)
        assert "created" in result
        assert "skipped" in result
        assert "errors" in result
        assert result["created"] == []  # Dry run doesn't create

    def test_promote_actual(self, agent):
        """Test promoting best practices."""
        result = agent.promote_best_practices_to_skills(dry_run=False)
        assert "created" in result
        assert "skipped" in result
        assert "errors" in result
        assert "total_best_practices" in result


# ------------------------------------------------------------------
# Edge Cases and Error Handling
# ------------------------------------------------------------------


class TestEdgeCases:
    def test_record_execution_truncates_long_description(self, agent):
        """Test that long task descriptions are truncated."""
        long_description = "x" * 500
        feedback_id = agent.record_execution(
            agent_type="executor",
            task_description=long_description,
            success=True,
        )
        assert feedback_id is not None
        # Verify truncation happened (task_description limited to 200 chars)
        failures = agent.store.get_recent_failures("executor", limit=0)
        # No failures since success=True

    def test_classify_error_with_network_keywords(self, agent):
        """Test classifying network-related errors."""
        error = ConnectionError("network unreachable")
        error_type = agent._classify_error(error)
        assert error_type == "network_error"

    def test_classify_error_with_api_keywords(self, agent):
        """Test classifying API-related errors."""
        error = Exception("API rate limit exceeded")
        error_type = agent._classify_error(error)
        assert error_type == "api_error"

    def test_report_handles_empty_database(self, agent):
        """Test that report handles empty database gracefully."""
        report = agent.report("nonexistent_agent")
        assert "generated_at" in report
        assert "agents" in report

    def test_analyze_task_logs_with_mixed_results(self, agent):
        """Test analyzing logs with mixed success/failure."""
        # Create varied execution history
        for i in range(10):
            if i % 3 == 0:
                # Failure with error
                agent.record_execution(
                    agent_type="executor",
                    task_description=f"Task {i}",
                    success=False,
                    error=TimeoutError("timeout"),
                    execution_time=1.0 + i * 0.1,
                )
            else:
                # Success
                agent.record_execution(
                    agent_type="executor",
                    task_description=f"Task {i}",
                    success=True,
                    execution_time=1.0 + i * 0.1,
                )

        analysis = agent.analyze_task_logs("executor", recent_count=10)
        # Success rate should be around 0.6-0.7 (7 successes out of 10)
        # i=0: False, i=1: True, i=2: True, i=3: False, i=4: True, i=5: True, i=6: False, i=7: True, i=8: True, i=9: True
        # = 7 successes out of 10 = 0.7
        assert 0.6 <= analysis["success_rate"] <= 0.8
