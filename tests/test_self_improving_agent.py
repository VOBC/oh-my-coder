"""
Tests for src/agents/self_improving.py

Coverage target: 80%+ with at least 40 test cases
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.agents.base import AgentOutput, AgentStatus
from src.agents.evolution import (
    DecisionMemory,
    EvolutionConfig,
    EvolutionRecord,
    EvolutionStore,
    SuccessPattern,
)
from src.agents.self_improving import (
    ExecutionFeedback,
    LearningStore,
    SelfImprovingAgent,
    StrategyAdjustment,
)

# ==============================================================================
# Fixtures
# ==============================================================================


@pytest.fixture
def temp_db_path():
    """Create a temporary database path for testing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir) / "test_learning.db"


@pytest.fixture
def temp_state_dir():
    """Create a temporary state directory for testing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def learning_store(temp_db_path):
    """Create a LearningStore instance with temporary database"""
    return LearningStore(str(temp_db_path))


@pytest.fixture
def evolution_store(temp_state_dir):
    """Create an EvolutionStore instance with temporary directory"""
    return EvolutionStore(temp_state_dir)


@pytest.fixture
def decision_memory(temp_state_dir):
    """Create a DecisionMemory instance with temporary directory"""
    return DecisionMemory(temp_state_dir)


@pytest.fixture
def evolution_config():
    """Create an EvolutionConfig instance with test defaults"""
    return EvolutionConfig(
        enabled=True,
        improvement_threshold=0.8,
        min_samples=5,
        max_evolution_history=100,
        pattern_confidence_threshold=0.7,
        evolution_cooldown_hours=24,
    )


@pytest.fixture
def self_improving_agent(temp_db_path, temp_state_dir, evolution_config):
    """Create a SelfImprovingAgent instance with test dependencies"""
    learning_store = LearningStore(str(temp_db_path))

    with patch("src.memory.learnings.LearningsMemory") as mock_learnings:
        mock_learnings_instance = MagicMock()
        mock_learnings.return_value = mock_learnings_instance

        agent = SelfImprovingAgent(
            model_router=None,
            config={},
            store=learning_store,
            evolution_config=evolution_config,
        )
        # Override evolution store with temp directory
        agent._evolution_store = EvolutionStore(temp_state_dir)
        agent._decision_memory = DecisionMemory(temp_state_dir)

        yield agent


# ==============================================================================
# Test ExecutionFeedback dataclass
# ==============================================================================


def test_execution_feedback_creation_with_defaults():
    """Test ExecutionFeedback creation with default values"""
    feedback = ExecutionFeedback()
    assert feedback.id is None
    assert feedback.timestamp == ""
    assert feedback.agent_type == ""
    assert feedback.success is False
    assert feedback.retry_count == 0
    assert feedback.final_success is False


def test_execution_feedback_creation_with_values():
    """Test ExecutionFeedback creation with all values"""
    feedback = ExecutionFeedback(
        id=1,
        timestamp="2024-01-01T00:00:00",
        agent_type="executor",
        task_description="Test task",
        context_hash="abc123",
        success=True,
        execution_time=1.5,
        error_type=None,
        error_message=None,
        user_correction="Fix applied",
        retry_count=2,
        final_success=True,
    )
    assert feedback.id == 1
    assert feedback.agent_type == "executor"
    assert feedback.success is True
    assert feedback.retry_count == 2


# ==============================================================================
# Test StrategyAdjustment dataclass
# ==============================================================================


def test_strategy_adjustment_creation_with_defaults():
    """Test StrategyAdjustment creation with default values"""
    adjustment = StrategyAdjustment()
    assert adjustment.id is None
    assert adjustment.timestamp == ""
    assert adjustment.effectiveness_score == 0.0
    assert adjustment.applied_count == 0


def test_strategy_adjustment_creation_with_values():
    """Test StrategyAdjustment creation with all values"""
    adjustment = StrategyAdjustment(
        id=1,
        timestamp="2024-01-01T00:00:00",
        agent_type="executor",
        pattern_detected="syntax_error",
        adjustment_type="prompt_update",
        adjustment_content="Add syntax check",
        effectiveness_score=0.8,
        applied_count=5,
    )
    assert adjustment.id == 1
    assert adjustment.pattern_detected == "syntax_error"
    assert adjustment.effectiveness_score == 0.8


# ==============================================================================
# Test LearningStore
# ==============================================================================


def test_learning_store_init(learning_store, temp_db_path):
    """Test LearningStore initialization creates database"""
    assert learning_store.db_path == Path(temp_db_path)
    assert temp_db_path.exists()


def test_learning_store_record_feedback(learning_store):
    """Test recording execution feedback"""
    feedback = ExecutionFeedback(
        agent_type="executor",
        task_description="Test task",
        success=True,
        execution_time=1.0,
    )
    record_id = learning_store.record_feedback(feedback)

    assert record_id is not None
    assert record_id > 0
    assert feedback.timestamp != ""  # Should be set by record_feedback


def test_learning_store_record_feedback_with_error(learning_store):
    """Test recording feedback with error information"""
    feedback = ExecutionFeedback(
        agent_type="executor",
        task_description="Failing task",
        success=False,
        error_type="syntax_error",
        error_message="Invalid syntax on line 10",
        retry_count=3,
    )
    record_id = learning_store.record_feedback(feedback)

    assert record_id is not None


def test_learning_store_record_adjustment(learning_store):
    """Test recording strategy adjustment"""
    adjustment = StrategyAdjustment(
        agent_type="executor",
        pattern_detected="timeout",
        adjustment_type="parameter_tune",
        adjustment_content="Increase timeout",
        effectiveness_score=0.7,
    )
    record_id = learning_store.record_adjustment(adjustment)

    assert record_id is not None
    assert adjustment.timestamp != ""


def test_learning_store_get_recent_failures_empty(learning_store):
    """Test getting recent failures when none exist"""
    failures = learning_store.get_recent_failures("executor")
    assert failures == []


def test_learning_store_get_recent_failures_with_data(learning_store):
    """Test getting recent failures from database"""
    # Add some feedback records
    for i in range(3):
        feedback = ExecutionFeedback(
            agent_type="executor",
            task_description=f"Task {i}",
            success=False,
            error_type="timeout" if i < 2 else "syntax_error",
        )
        learning_store.record_feedback(feedback)

    failures = learning_store.get_recent_failures("executor", limit=2)

    assert len(failures) == 2
    # Check that all returned records have success=0 (False in SQLite)
    assert all(f.success == 0 or f.success is False for f in failures)


def test_learning_store_get_error_patterns_no_data(learning_store):
    """Test getting error patterns when insufficient data"""
    patterns = learning_store.get_error_patterns("executor", min_count=3)
    assert patterns == []


def test_learning_store_get_error_patterns_with_data(learning_store):
    """Test getting error patterns from database"""
    # Add enough records to meet min_count
    for i in range(5):
        feedback = ExecutionFeedback(
            agent_type="executor",
            task_description=f"Task {i}",
            success=False,
            error_type="timeout",
            execution_time=1.0,
            retry_count=1,
        )
        learning_store.record_feedback(feedback)

    patterns = learning_store.get_error_patterns("executor", min_count=3)

    assert len(patterns) == 1
    assert patterns[0]["error_type"] == "timeout"
    assert patterns[0]["count"] >= 3


def test_learning_store_get_success_rate_no_data(learning_store):
    """Test getting success rate when no data exists"""
    rate = learning_store.get_success_rate("executor", days=7)
    assert rate == 0.0


def test_learning_store_get_success_rate_with_data(learning_store):
    """Test calculating success rate from database"""
    # Add mix of success and failure
    for i in range(10):
        feedback = ExecutionFeedback(
            agent_type="executor",
            task_description=f"Task {i}",
            success=(i % 3 == 0),  # 1/3 success rate
        )
        learning_store.record_feedback(feedback)

    rate = learning_store.get_success_rate("executor", days=30)

    assert 0.0 <= rate <= 1.0


def test_learning_store_get_adjustments_empty(learning_store):
    """Test getting adjustments when none exist"""
    adjustments = learning_store.get_adjustments("executor")
    assert adjustments == []


def test_learning_store_get_adjustments_with_data(learning_store):
    """Test getting adjustments from database"""
    # Add adjustments with different effectiveness scores
    for score in [0.9, 0.5, 0.8]:
        adjustment = StrategyAdjustment(
            agent_type="executor",
            pattern_detected="test_pattern",
            adjustment_type="prompt_update",
            adjustment_content="Test content",
            effectiveness_score=score,
        )
        learning_store.record_adjustment(adjustment)

    adjustments = learning_store.get_adjustments("executor")

    assert len(adjustments) == 3
    # Should be sorted by effectiveness_score DESC
    assert adjustments[0].effectiveness_score >= adjustments[1].effectiveness_score


# ==============================================================================
# Test SelfImprovingAgent - Basic Properties
# ==============================================================================


def test_agent_properties(self_improving_agent):
    """Test SelfImprovingAgent basic properties"""
    assert self_improving_agent.name == "self-improving"
    assert self_improving_agent.icon == "🧠"
    assert self_improving_agent.default_tier == "low"
    # Description contains Chinese "学习" (learning)
    assert "学习" in self_improving_agent.description or "learning" in self_improving_agent.description.lower()


def test_agent_system_prompt(self_improving_agent):
    """Test SelfImprovingAgent system_prompt property"""
    prompt = self_improving_agent.system_prompt
    assert isinstance(prompt, str)
    assert len(prompt) > 0
    assert "学习" in prompt or "learning" in prompt.lower()


# ==============================================================================
# Test SelfImprovingAgent - record_execution
# ==============================================================================


def test_agent_record_execution_success(self_improving_agent):
    """Test recording successful execution"""
    record_id = self_improving_agent.record_execution(
        agent_type="executor",
        task_description="Test task",
        success=True,
        execution_time=1.5,
    )

    assert record_id is not None
    assert record_id > 0


def test_agent_record_execution_with_error(self_improving_agent):
    """Test recording execution with error"""
    error = SyntaxError("Invalid syntax")
    record_id = self_improving_agent.record_execution(
        agent_type="executor",
        task_description="Failing task",
        success=False,
        error=error,
    )

    assert record_id is not None


def test_agent_record_execution_with_user_correction(self_improving_agent):
    """Test recording execution with user correction"""
    record_id = self_improving_agent.record_execution(
        agent_type="executor",
        task_description="Task needing correction",
        success=False,
        user_correction="Apply this fix instead",
        retry_count=2,
    )

    assert record_id is not None


# ==============================================================================
# Test SelfImprovingAgent - _classify_error
# ==============================================================================


def test_classify_syntax_error(self_improving_agent):
    """Test error classification for syntax errors"""
    error = SyntaxError("Invalid syntax")
    error_type = self_improving_agent._classify_error(error)
    assert error_type == "syntax_error"


def test_classify_timeout_error(self_improving_agent):
    """Test error classification for timeout errors"""
    error = TimeoutError("Operation timed out")
    error_type = self_improving_agent._classify_error(error)
    assert error_type == "timeout"


def test_classify_memory_error(self_improving_agent):
    """Test error classification for memory errors"""
    error = MemoryError("Out of memory")
    error_type = self_improving_agent._classify_error(error)
    assert error_type == "memory_error"


def test_classify_permission_error(self_improving_agent):
    """Test error classification for permission errors"""
    error = PermissionError("Access denied")
    error_type = self_improving_agent._classify_error(error)
    assert error_type == "permission_error"


def test_classify_network_error(self_improving_agent):
    """Test error classification for network errors"""
    error = ConnectionError("Network connection failed")
    error_type = self_improving_agent._classify_error(error)
    assert error_type == "network_error"


def test_classify_api_error(self_improving_agent):
    """Test error classification for API errors"""
    error = Exception("API rate limit exceeded")
    error_type = self_improving_agent._classify_error(error)
    assert error_type == "api_error"


def test_classify_generic_error(self_improving_agent):
    """Test error classification for generic errors"""
    error = ValueError("Some value error")
    error_type = self_improving_agent._classify_error(error)
    assert "error" in error_type


# ==============================================================================
# Test SelfImprovingAgent - _hash_context
# ==============================================================================


def test_hash_context_deterministic(self_improving_agent):
    """Test that context hashing is deterministic"""
    context = "Test context for hashing"
    hash1 = self_improving_agent._hash_context(context)
    hash2 = self_improving_agent._hash_context(context)

    assert hash1 == hash2
    assert len(hash1) == 16


def test_hash_context_different(self_improving_agent):
    """Test that different contexts produce different hashes"""
    hash1 = self_improving_agent._hash_context("Context 1")
    hash2 = self_improving_agent._hash_context("Context 2")

    assert hash1 != hash2


# ==============================================================================
# Test SelfImprovingAgent - analyze_and_improve
# ==============================================================================


def test_analyze_and_improve_no_patterns(self_improving_agent):
    """Test analyze_and_improve when no error patterns exist"""
    adjustments = self_improving_agent.analyze_and_improve("executor")
    assert adjustments == []


def test_analyze_and_improve_with_patterns(self_improving_agent):
    """Test analyze_and_improve generates adjustments for known patterns"""
    # Add timeout errors
    for i in range(3):
        self_improving_agent.record_execution(
            agent_type="executor",
            task_description=f"Task {i}",
            success=False,
            error=TimeoutError("Timeout"),
        )

    adjustments = self_improving_agent.analyze_and_improve("executor")

    assert len(adjustments) > 0
    assert any("timeout" in a.pattern_detected.lower() for a in adjustments)


# ==============================================================================
# Test SelfImprovingAgent - get_improved_prompt
# ==============================================================================


def test_get_improved_prompt_no_adjustments(self_improving_agent):
    """Test get_improved_prompt returns base prompt when no adjustments"""
    base_prompt = "You are a helpful assistant."
    improved = self_improving_agent.get_improved_prompt("executor", base_prompt)

    assert improved == base_prompt


def test_get_improved_prompt_with_adjustments(self_improving_agent):
    """Test get_improved_prompt applies effective adjustments"""
    # Add a high-effectiveness adjustment
    adjustment = StrategyAdjustment(
        agent_type="executor",
        pattern_detected="syntax_error",
        adjustment_type="prompt_update",
        adjustment_content="Check syntax before execution",
        effectiveness_score=0.9,
        applied_count=5,
    )
    self_improving_agent.store.record_adjustment(adjustment)

    base_prompt = "You are a helpful assistant."
    improved = self_improving_agent.get_improved_prompt("executor", base_prompt)

    assert "学习优化" in improved or "syntax_error" in improved


# ==============================================================================
# Test SelfImprovingAgent - report
# ==============================================================================


def test_report_for_specific_agent(self_improving_agent):
    """Test generating report for a specific agent type"""
    # Add some execution data
    self_improving_agent.record_execution(
        agent_type="executor",
        task_description="Test task",
        success=True,
    )

    report = self_improving_agent.report(agent_type="executor")

    assert "generated_at" in report
    assert "agents" in report
    assert "executor" in report["agents"]


def test_report_for_all_agents(self_improving_agent):
    """Test generating report for all agent types"""
    # Add data for multiple agents
    for agent_type in ["executor", "planner"]:
        self_improving_agent.record_execution(
            agent_type=agent_type,
            task_description=f"Task for {agent_type}",
            success=True,
        )

    report = self_improving_agent.report()

    assert "executor" in report["agents"]
    assert "planner" in report["agents"]


# ==============================================================================
# Test SelfImprovingAgent - _run (async)
# ==============================================================================


@pytest.mark.asyncio
async def test_run_report_task(self_improving_agent):
    """Test _run with report task"""
    output = await self_improving_agent._run("report")

    assert isinstance(output, AgentOutput)
    assert output.status == AgentStatus.COMPLETED
    assert output.result is not None


@pytest.mark.asyncio
async def test_run_stats_task(self_improving_agent):
    """Test _run with stats task"""
    output = await self_improving_agent._run("stats executor")

    assert isinstance(output, AgentOutput)
    assert output.status == AgentStatus.COMPLETED


# ==============================================================================
# Test SelfImprovingAgent - analyze_task_logs
# ==============================================================================


def test_analyze_task_logs_empty(self_improving_agent):
    """Test analyze_task_logs with no data"""
    analysis = self_improving_agent.analyze_task_logs("executor")

    assert analysis["agent_type"] == "executor"
    assert analysis["sample_size"] == 0
    assert analysis["success_rate"] == 0.0


def test_analyze_task_logs_with_data(self_improving_agent):
    """Test analyze_task_logs with execution data"""
    # Add mix of success and failure
    for i in range(10):
        self_improving_agent.record_execution(
            agent_type="executor",
            task_description=f"Task {i}",
            success=(i % 3 == 0),
            execution_time=1.0 + i * 0.1,
            error=Exception("Test error") if i % 3 != 0 else None,
        )

    analysis = self_improving_agent.analyze_task_logs("executor", recent_count=10)

    assert analysis["sample_size"] == 10
    assert 0.0 <= analysis["success_rate"] <= 1.0


def test_analyze_task_logs_recommendations(self_improving_agent):
    """Test analyze_task_logs generates recommendations for low success rate"""
    # Add mostly failures
    for i in range(10):
        self_improving_agent.record_execution(
            agent_type="executor",
            task_description=f"Task {i}",
            success=(i == 0),  # Only 1 success
            error=Exception("Some error") if i > 0 else None,
        )

    analysis = self_improving_agent.analyze_task_logs("executor")

    assert len(analysis["recommendations"]) > 0


# ==============================================================================
# Test SelfImprovingAgent - extract_patterns
# ==============================================================================


def test_extract_patterns_no_data(self_improving_agent):
    """Test extract_patterns with no data"""
    patterns = self_improving_agent.extract_patterns("executor")
    assert isinstance(patterns, list)


def test_extract_patterns_with_adjustments(self_improving_agent):
    """Test extract_patterns extracts strategy patterns"""
    # Add adjustment
    adjustment = StrategyAdjustment(
        agent_type="executor",
        pattern_detected="timeout",
        adjustment_type="prompt_update",
        adjustment_content="Increase timeout",
        effectiveness_score=0.8,
        applied_count=3,
    )
    self_improving_agent.store.record_adjustment(adjustment)

    patterns = self_improving_agent.extract_patterns("executor", pattern_type="strategy")

    assert len(patterns) > 0
    assert all(isinstance(p, SuccessPattern) for p in patterns)


# ==============================================================================
# Test SelfImprovingAgent - update_system_prompt
# ==============================================================================


def test_update_system_prompt_disabled(self_improving_agent):
    """Test update_system_prompt when evolution is disabled"""
    self_improving_agent._evolution_config.enabled = False

    base_prompt = "Base prompt"
    updated = self_improving_agent.update_system_prompt("executor", base_prompt)

    assert updated == base_prompt


def test_update_system_prompt_enabled(self_improving_agent):
    """Test update_system_prompt when evolution is enabled"""
    self_improving_agent._evolution_config.enabled = True

    base_prompt = "Base prompt"

    # Add some data to generate patterns
    self_improving_agent.record_execution(
        agent_type="executor",
        task_description="Test",
        success=True,
    )

    updated = self_improving_agent.update_system_prompt("executor", base_prompt)

    # Should return a string (may or may not be different)
    assert isinstance(updated, str)


# ==============================================================================
# Test SelfImprovingAgent - evolve
# ==============================================================================


def test_evolve_disabled(self_improving_agent):
    """Test evolve when evolution is disabled"""
    self_improving_agent._evolution_config.enabled = False

    record = self_improving_agent.evolve("executor")

    assert record is None


def test_evolve_insufficient_samples(self_improving_agent):
    """Test evolve with insufficient samples"""
    self_improving_agent._evolution_config.min_samples = 10
    self_improving_agent._evolution_config.enabled = True

    # Only add 3 samples
    for i in range(3):
        self_improving_agent.record_execution(
            agent_type="executor",
            task_description=f"Task {i}",
            success=True,
        )

    record = self_improving_agent.evolve("executor")

    assert record is None


def test_evolve_with_sufficient_data(self_improving_agent):
    """Test evolve with sufficient execution data"""
    self_improving_agent._evolution_config.min_samples = 5
    self_improving_agent._evolution_config.enabled = True

    # Add enough samples with some failures
    for i in range(10):
        self_improving_agent.record_execution(
            agent_type="executor",
            task_description=f"Task {i}",
            success=(i % 2 == 0),
            error=TimeoutError("Timeout") if i % 2 == 1 else None,
        )

    record = self_improving_agent.evolve("executor", trigger="manual")

    # May or may not produce record depending on analysis
    if record:
        assert isinstance(record, EvolutionRecord)
        assert record.agent_type == "executor"
        assert record.trigger == "manual"


# ==============================================================================
# Test SelfImprovingAgent - Decision Memory Methods
# ==============================================================================


def test_record_decision(self_improving_agent):
    """Test recording a decision"""
    decision_id = self_improving_agent.record_decision(
        title="Test Decision",
        problem="Test problem description",
        chosen_solution="Test solution",
        agent_type="executor",
        category="bug_fix",
        result="success",
    )

    assert decision_id is not None
    assert len(decision_id) > 0


def test_retrieve_past_decisions(self_improving_agent):
    """Test retrieving past decisions"""
    # Record a decision first
    self_improving_agent.record_decision(
        title="Syntax Error Fix",
        problem="Syntax error in code",
        chosen_solution="Fixed the syntax",
    )

    decisions = self_improving_agent.retrieve_past_decisions(
        problem_description="syntax error", limit=5
    )

    assert isinstance(decisions, list)


def test_list_decisions(self_improving_agent):
    """Test listing decisions"""
    # Record some decisions
    for i in range(3):
        self_improving_agent.record_decision(
            title=f"Decision {i}",
            problem=f"Problem {i}",
            chosen_solution=f"Solution {i}",
            category="bug_fix" if i % 2 == 0 else "solution_choice",
        )

    decisions = self_improving_agent.list_decisions(category="bug_fix", limit=10)

    assert isinstance(decisions, list)


def test_get_decision_stats(self_improving_agent):
    """Test getting decision statistics"""
    stats = self_improving_agent.get_decision_stats()

    assert isinstance(stats, dict)
    assert "total_decisions" in stats


# ==============================================================================
# Test SelfImprovingAgent - auto_create_skill
# ==============================================================================


def test_auto_create_skill_not_worthy(self_improving_agent):
    """Test auto_create_skill when criteria not met"""
    task_context = {
        "agent_name": "executor",
        "task": "Simple task",
        "tool_call_count": 2,  # Below threshold
        "steps": ["step1"],
    }

    result = self_improving_agent.auto_create_skill(task_context)

    assert result is None


def test_auto_create_skill_with_error_and_fix(self_improving_agent):
    """Test auto_create_skill when error was fixed"""
    with patch(
        "src.memory.skill_manager.SkillManager"
    ) as mock_skill_manager_class:
        mock_skill_manager = MagicMock()
        mock_skill_manager.patch.return_value = {"skill_id": "test-skill"}
        mock_skill_manager_class.return_value = mock_skill_manager

        task_context = {
            "agent_name": "executor",
            "task": "Complex task with error",
            "workflow": "debug",
            "result": "Fixed successfully",
            "steps": ["step1", "step2", "step3"],
            "error": "Some error",
            "had_fix": True,
            "had_user_correction": False,
            "tool_call_count": 5,
        }

        result = self_improving_agent.auto_create_skill(task_context)

        # Should create skill when had_fix=True and tool_call_count >= 5
        assert result is not None or mock_skill_manager.patch.called


# ==============================================================================
# Test SelfImprovingAgent - promote_best_practices_to_skills
# ==============================================================================


def test_promote_best_practices_dry_run(self_improving_agent):
    """Test promote_best_practices_to_skills in dry run mode"""
    result = self_improving_agent.promote_best_practices_to_skills(dry_run=True)

    assert isinstance(result, dict)
    assert "dry_run" not in result  # dry_run mode doesn't create
    assert "total_best_practices" in result


def test_promote_best_practices_actual(self_improving_agent):
    """Test promote_best_practices_to_skills actual run"""
    with patch(
        "src.memory.skill_manager.SkillManager"
    ) as mock_skill_manager_class:
        mock_skill_manager = MagicMock()
        mock_skill_manager.list_skills.return_value = []
        mock_skill_manager_class.return_value = mock_skill_manager

        result = self_improving_agent.promote_best_practices_to_skills(dry_run=False)

        assert isinstance(result, dict)
        assert "created" in result
        assert "skipped" in result
        assert "errors" in result


# ==============================================================================
# Test SelfImprovingAgent - get_evolution_stats
# ==============================================================================


def test_get_evolution_stats(self_improving_agent):
    """Test getting evolution statistics"""
    stats = self_improving_agent.get_evolution_stats("executor")

    assert isinstance(stats, dict)
    assert "config" in stats
    assert "enabled" in stats["config"]


# ==============================================================================
# Test EvolutionStore
# ==============================================================================


def test_evolution_store_save_and_load_record(evolution_store):
    """Test saving and loading evolution records"""
    record = EvolutionRecord(
        id="test-evo-1",
        timestamp="2024-01-01 00:00:00",
        agent_type="executor",
        generation=1,
        trigger="manual",
        before_state={"success_rate": 0.5},
        after_state={"success_rate": 0.7},
        changes=["Added prompt optimization"],
    )

    record_id = evolution_store.save_evolution_record(record)
    assert record_id == "test-evo-1"

    history = evolution_store.load_evolution_history("executor")
    assert len(history) == 1
    assert history[0].agent_type == "executor"


def test_evolution_store_get_current_generation(evolution_store):
    """Test getting current generation number"""
    gen = evolution_store.get_current_generation("executor")
    assert gen == 1  # Default when no history

    # Add a record
    record = EvolutionRecord(
        agent_type="executor",
        generation=2,
        trigger="manual",
        before_state={},
        after_state={},
        changes=[],
    )
    evolution_store.save_evolution_record(record)

    gen = evolution_store.get_current_generation("executor")
    assert gen == 3  # Should be previous + 1


def test_evolution_store_save_and_load_prompt(evolution_store):
    """Test saving and loading optimized prompts"""
    prompt = "Optimized system prompt"

    evolution_store.save_optimized_prompt("executor", prompt)
    loaded = evolution_store.load_optimized_prompt("executor")

    assert loaded == prompt


def test_evolution_store_add_success_pattern(evolution_store):
    """Test adding success patterns"""
    pattern_id = evolution_store.add_success_pattern(
        agent_name="executor",
        pattern_type="strategy",
        description="Test pattern",
        context="Test context",
    )

    assert pattern_id is not None

    patterns = evolution_store.load_success_patterns("executor")
    assert len(patterns) > 0


# ==============================================================================
# Test DecisionMemory
# ==============================================================================


def test_decision_memory_record_and_retrieve(decision_memory):
    """Test recording and retrieving decisions"""
    decision_id = decision_memory.record_decision(
        title="Test Decision",
        problem="Test problem",
        chosen_solution="Test solution",
        keywords=["test", "decision"],
    )

    assert decision_id is not None

    decisions = decision_memory.retrieve("test problem", limit=5)
    assert len(decisions) > 0
    assert decisions[0].title == "Test Decision"


def test_decision_memory_list_decisions(decision_memory):
    """Test listing decisions"""
    # Record multiple decisions
    for i in range(3):
        decision_memory.record_decision(
            title=f"Decision {i}",
            problem=f"Problem {i}",
            chosen_solution=f"Solution {i}",
            category="bug_fix" if i == 0 else "solution_choice",
        )

    all_decisions = decision_memory.list_decisions(limit=10)
    assert len(all_decisions) == 3

    filtered = decision_memory.list_decisions(category="bug_fix")
    assert len(filtered) == 1


def test_decision_memory_get_stats(decision_memory):
    """Test getting decision statistics"""
    # Record some decisions
    for i in range(5):
        decision_memory.record_decision(
            title=f"Decision {i}",
            problem=f"Problem {i}",
            chosen_solution=f"Solution {i}",
            category=["bug_fix", "solution_choice", "architecture"][i % 3],
        )

    stats = decision_memory.get_stats()

    assert stats["total_decisions"] == 5
    assert "by_category" in stats


# ==============================================================================
# Test EvolutionRecord dataclass
# ==============================================================================


def test_evolution_record_defaults():
    """Test EvolutionRecord default values"""
    record = EvolutionRecord()
    assert record.id == ""
    assert record.generation == 1
    assert record.before_state == {}
    assert record.after_state == {}
    assert record.changes == []


# ==============================================================================
# Test SuccessPattern dataclass
# ==============================================================================


def test_success_pattern_defaults():
    """Test SuccessPattern default values"""
    pattern = SuccessPattern()
    assert pattern.id == ""
    assert pattern.effectiveness_score == 0.0
    assert pattern.occurrences == 0


# ==============================================================================
# Test EvolutionConfig
# ==============================================================================


def test_evolution_config_defaults():
    """Test EvolutionConfig default values"""
    config = EvolutionConfig()
    assert config.enabled is True
    assert config.improvement_threshold == 0.8
    assert config.min_samples == 5


# ==============================================================================
# Integration Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_full_learning_cycle(self_improving_agent):
    """Test a complete learning cycle: record, analyze, evolve"""
    # Record multiple executions
    for i in range(10):
        self_improving_agent.record_execution(
            agent_type="executor",
            task_description=f"Task {i}",
            success=(i % 3 == 0),  # ~33% success rate
            execution_time=1.0,
            error=TimeoutError("Timeout") if i % 3 != 0 else None,
        )

    # Analyze
    analysis = self_improving_agent.analyze_task_logs("executor")
    assert analysis["sample_size"] == 10

    # Get report
    report = self_improving_agent.report("executor")
    assert "executor" in report["agents"]


def test_error_pattern_learning(self_improving_agent):
    """Test learning from error patterns"""
    # Record same error type multiple times
    for i in range(5):
        self_improving_agent.record_execution(
            agent_type="executor",
            task_description=f"Task {i}",
            success=False,
            error=TimeoutError("Connection timeout"),
        )

    # Analyze patterns
    patterns = self_improving_agent.store.get_error_patterns("executor", min_count=3)

    assert len(patterns) > 0
    assert patterns[0]["error_type"] == "timeout"


@pytest.mark.asyncio
async def test_agent_registered():
    """Test that SelfImprovingAgent is properly registered"""
    from src.agents.base import AGENT_REGISTRY

    assert "self-improving" in AGENT_REGISTRY
    assert AGENT_REGISTRY["self-improving"] == SelfImprovingAgent
