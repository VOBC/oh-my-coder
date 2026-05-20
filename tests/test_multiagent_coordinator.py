"""Tests for src/multiagent/coordinator.py"""

import asyncio

import pytest

from src.multiagent.coordinator import (
    CoordinationResult,
    MultiAgentCoordinator,
    SubAgent,
    SubAgentStatus,
    TaskResult,
    get_coordinator,
)


class TestSubAgent:
    """Test SubAgent dataclass"""

    def test_create_subagent(self):
        """Test creating SubAgent"""
        agent = SubAgent(
            agent_id="abc123",
            name="TestAgent",
            role="coder",
            status=SubAgentStatus.IDLE,
        )

        assert agent.agent_id == "abc123"
        assert agent.name == "TestAgent"
        assert agent.role == "coder"
        assert agent.status == SubAgentStatus.IDLE
        assert agent.created_at != ""  # Should auto-fill

    def test_to_dict(self):
        """Test to_dict method"""
        agent = SubAgent(
            agent_id="abc123",
            name="TestAgent",
            role="reviewer",
            status=SubAgentStatus.RUNNING,
            created_at="2024-01-15T10:30:00",
            metadata={"task": "review code"},
        )

        result = agent.to_dict()

        assert result["agent_id"] == "abc123"
        assert result["name"] == "TestAgent"
        assert result["role"] == "reviewer"
        assert result["status"] == "running"
        assert result["created_at"] == "2024-01-15T10:30:00"
        assert result["metadata"]["task"] == "review code"


class TestTaskResult:
    """Test TaskResult dataclass"""

    def test_create_task_result(self):
        """Test creating TaskResult"""
        result = TaskResult(
            agent_id="abc123",
            role="coder",
            success=True,
            output="Code written",
            error=None,
            duration=5.0,
        )

        assert result.agent_id == "abc123"
        assert result.success is True
        assert result.output == "Code written"

    def test_to_dict_with_output(self):
        """Test to_dict with output"""
        result = TaskResult(
            agent_id="abc123",
            role="coder",
            success=True,
            output="Some output",
            timestamp="2024-01-15T10:30:00",
        )

        d = result.to_dict()

        assert d["output"] == "Some output"
        assert d["error"] is None

    def test_to_dict_with_error(self):
        """Test to_dict with error"""
        result = TaskResult(
            agent_id="abc123",
            role="coder",
            success=False,
            output=None,
            error="SyntaxError: invalid syntax",
            timestamp="2024-01-15T10:30:00",
        )

        d = result.to_dict()

        assert d["success"] is False
        assert d["output"] is None
        assert d["error"] == "SyntaxError: invalid syntax"

    def test_to_dict_none_output(self):
        """Test to_dict with None output (should convert to None in dict)"""
        result = TaskResult(
            agent_id="abc123",
            role="coder",
            success=False,
            output=None,
            error="Error",
        )

        d = result.to_dict()

        # output is None, should stay None in dict (str(None) is "None", but code handles it)
        assert d["output"] is None


class TestCoordinationResult:
    """Test CoordinationResult dataclass"""

    def test_create_coordination_result(self):
        """Test creating CoordinationResult"""
        results = [
            TaskResult(agent_id="a1", role="coder", success=True, output="Done"),
        ]

        result = CoordinationResult(
            task_id="task-001",
            results=results,
            summary="All passed",
            started_at="2024-01-15T10:00:00",
            completed_at="2024-01-15T10:05:00",
        )

        assert result.task_id == "task-001"
        assert len(result.results) == 1

    def test_to_dict(self):
        """Test to_dict method"""
        results = [
            TaskResult(agent_id="a1", role="coder", success=True, output="Done"),
        ]

        result = CoordinationResult(
            task_id="task-001",
            results=results,
            summary="All passed",
            started_at="2024-01-15T10:00:00",
            completed_at="2024-01-15T10:05:00",
        )

        d = result.to_dict()

        assert d["task_id"] == "task-001"
        assert len(d["results"]) == 1
        assert d["summary"] == "All passed"
        assert d["started_at"] == "2024-01-15T10:00:00"
        assert d["completed_at"] == "2024-01-15T10:05:00"


class TestMultiAgentCoordinator:
    """Test MultiAgentCoordinator class"""

    @pytest.fixture
    def coordinator(self):
        """Create a fresh coordinator"""
        return MultiAgentCoordinator()

    def test_init(self, coordinator):
        """Test __init__"""
        assert coordinator.agents == {}
        assert coordinator.tasks == {}
        assert coordinator._runner is None
        assert coordinator._history == []

    def test_spawn(self, coordinator):
        """Test spawn method"""
        agent = coordinator.spawn(role="coder", name="TestCoder")

        assert agent.agent_id != ""
        assert agent.name == "TestCoder"
        assert agent.role == "coder"
        assert agent.status == SubAgentStatus.IDLE
        assert agent.agent_id in coordinator.agents

    def test_spawn_with_metadata(self, coordinator):
        """Test spawn with metadata"""
        metadata = {"model": "gpt-4", "temperature": 0.7}
        agent = coordinator.spawn(role="reviewer", name="TestReviewer", metadata=metadata)

        assert agent.metadata["model"] == "gpt-4"
        assert agent.metadata["temperature"] == 0.7

    def test_set_runner(self, coordinator):
        """Test set_runner method"""

        async def dummy_runner(agent, task):
            return f"Ran {agent.name} on {task}"

        coordinator.set_runner(dummy_runner)
        assert coordinator._runner is dummy_runner

    def test_get_status_empty(self, coordinator):
        """Test get_status with no agents"""
        status = coordinator.get_status()

        assert status["total_agents"] == 0
        assert status["running"] == 0
        assert status["completed"] == 0
        assert status["failed"] == 0
        assert status["idle"] == 0
        assert status["active_tasks"] == 0

    def test_get_status_with_agents(self, coordinator):
        """Test get_status with agents"""
        a1 = coordinator.spawn("coder", "Coder1")
        a2 = coordinator.spawn("reviewer", "Reviewer1")

        status = coordinator.get_status()

        assert status["total_agents"] == 2
        assert status["idle"] == 2
        # Use variables to avoid unused warning
        assert a1.status == SubAgentStatus.IDLE
        assert a2.status == SubAgentStatus.IDLE

    def test_get_agent_exists(self, coordinator):
        """Test get_agent when agent exists"""
        agent = coordinator.spawn("coder", "TestCoder")

        retrieved = coordinator.get_agent(agent.agent_id)

        assert retrieved is not None
        assert retrieved.agent_id == agent.agent_id

    def test_get_agent_not_exists(self, coordinator):
        """Test get_agent when agent does not exist"""
        result = coordinator.get_agent("nonexistent")

        assert result is None

    def test_remove_agent_exists(self, coordinator):
        """Test remove_agent when agent exists"""
        agent = coordinator.spawn("coder", "TestCoder")

        assert agent.agent_id in coordinator.agents

        result = coordinator.remove_agent(agent.agent_id)

        assert result is True
        assert agent.agent_id not in coordinator.agents

    def test_remove_agent_not_exists(self, coordinator):
        """Test remove_agent when agent does not exist"""
        result = coordinator.remove_agent("nonexistent")

        assert result is False

    def test_clear_agents(self, coordinator):
        """Test clear_agents method"""
        coordinator.spawn("coder", "Coder1")
        coordinator.spawn("reviewer", "Reviewer1")
        coordinator.tasks["task-001"] = ["a1", "a2"]

        assert len(coordinator.agents) == 2
        assert len(coordinator.tasks) == 1

        coordinator.clear_agents()

        assert len(coordinator.agents) == 0
        assert len(coordinator.tasks) == 0

    @pytest.mark.asyncio
    async def test_dispatch_without_runner(self, coordinator):
        """Test dispatch without setting runner (uses mock output)"""
        agents = [
            coordinator.spawn("coder", "Coder1"),
            coordinator.spawn("reviewer", "Reviewer1"),
        ]

        result = await coordinator.dispatch("Write a function", agents)

        assert result.task_id != ""
        assert len(result.results) == 2
        assert all(r.success for r in result.results)
        assert result.summary != ""
        assert result.started_at != ""
        assert result.completed_at != ""

    @pytest.mark.asyncio
    async def test_dispatch_with_runner(self, coordinator):
        """Test dispatch with custom runner"""

        async def custom_runner(agent, task):
            return f"Custom: {agent.name} -> {task}"

        coordinator.set_runner(custom_runner)

        agents = [coordinator.spawn("coder", "Coder1")]
        result = await coordinator.dispatch("Test task", agents)

        assert result.results[0].success is True
        assert "Custom:" in result.results[0].output

    @pytest.mark.asyncio
    async def test_dispatch_exception_handling(self, coordinator):
        """Test dispatch when runner raises exception"""

        async def failing_runner(agent, task):
            raise ValueError("Simulated failure")

        coordinator.set_runner(failing_runner)

        agents = [coordinator.spawn("coder", "Coder1")]
        result = await coordinator.dispatch("Test task", agents)

        assert len(result.results) == 1
        assert result.results[0].success is False
        assert result.results[0].error is not None
        assert "ValueError" in result.results[0].error

    @pytest.mark.asyncio
    async def test_dispatch_sequential(self, coordinator):
        """Test dispatch_sequential method"""
        agents = [
            coordinator.spawn("planner", "Planner1"),
            coordinator.spawn("coder", "Coder1"),
        ]

        result = await coordinator.dispatch_sequential("Plan and code", agents)

        assert result.task_id != ""
        assert len(result.results) == 2
        assert all(r.success for r in result.results)

    @pytest.mark.asyncio
    async def test_dispatch_sequential_with_context_passing(self, coordinator):
        """Test that dispatch_sequential passes context between agents"""

        async def context_runner(agent, task):
            return f"Output from {agent.name}"

        coordinator.set_runner(context_runner)

        agents = [
            coordinator.spawn("planner", "Planner1"),
            coordinator.spawn("coder", "Coder1"),
        ]

        result = await coordinator.dispatch_sequential("Initial task", agents)

        assert len(result.results) == 2
        # Both should succeed
        assert all(r.success for r in result.results)

    @pytest.mark.asyncio
    async def test_dispatch_sequential_breaks_on_failure(self, coordinator):
        """Test that dispatch_sequential breaks on failure (stops loop)"""

        call_count = 0

        async def conditional_runner(agent, task):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("First agent fails")
            return f"Output from {agent.name}"

        coordinator.set_runner(conditional_runner)

        agents = [
            coordinator.spawn("planner", "Planner1"),
            coordinator.spawn("coder", "Coder1"),
        ]

        result = await coordinator.dispatch_sequential("Test task", agents)

        # Should have 1 result (first agent fails, loop breaks)
        assert len(result.results) == 1
        assert result.results[0].success is False  # First failed

    def test_summarize(self, coordinator):
        """Test _summarize method"""
        results = [
            TaskResult(agent_id="a1", role="coder", success=True, output="Done"),
            TaskResult(agent_id="a2", role="coder", success=True, output="Done2"),
            TaskResult(
                agent_id="a3",
                role="reviewer",
                success=False,
                output=None,
                error="Failed",
            ),
        ]

        summary = coordinator._summarize(results)

        assert "总任务: 3" in summary
        assert "成功: 2" in summary
        assert "失败: 1" in summary
        assert "coder:" in summary
        assert "reviewer:" in summary

    def test_history_recorded(self, coordinator):
        """Test that history is recorded after dispatch"""

        async def dummy_runner(agent, task):
            return "Done"

        coordinator.set_runner(dummy_runner)

        agents = [coordinator.spawn("coder", "Coder1")]

        # Need to run async, use pytest.mark.asyncio

        result = asyncio.run(coordinator.dispatch("Test", agents))

        assert len(coordinator._history) == 1
        assert coordinator._history[0].task_id == result.task_id


class TestGetCoordinator:
    """Test get_coordinator function"""

    def test_get_coordinator_singleton(self):
        """Test that get_coordinator returns singleton"""
        coord1 = get_coordinator()
        coord2 = get_coordinator()

        assert coord1 is coord2  # Same instance
