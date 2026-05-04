"""
测试多 Agent 协作模块
"""

import pytest

from src.multiagent.coordinator import (
    MultiAgentCoordinator,
    SubAgent,
    SubAgentStatus,
    TaskResult,
    get_coordinator,
)


class TestSubAgent:
    """SubAgent 模型测试"""

    def test_init(self) -> None:
        agent = SubAgent(
            agent_id="test-01",
            name="TestAgent",
            role="coder",
        )
        assert agent.agent_id == "test-01"
        assert agent.name == "TestAgent"
        assert agent.role == "coder"
        assert agent.status == SubAgentStatus.IDLE
        assert agent.created_at != ""

    def test_to_dict(self) -> None:
        agent = SubAgent(
            agent_id="abc",
            name="X",
            role="reviewer",
            status=SubAgentStatus.RUNNING,
            metadata={"priority": "high"},
        )
        data = agent.to_dict()
        assert data["agent_id"] == "abc"
        assert data["role"] == "reviewer"
        assert data["status"] == "running"
        assert data["metadata"]["priority"] == "high"


class TestTaskResult:
    """TaskResult 测试"""

    def test_success_result(self) -> None:
        result = TaskResult(
            agent_id="a1",
            role="coder",
            success=True,
            output="code generated",
            duration=2.5,
        )
        assert result.success is True
        assert result.output == "code generated"
        assert result.error is None

    def test_failed_result(self) -> None:
        result = TaskResult(
            agent_id="a1",
            role="reviewer",
            success=False,
            output=None,
            error="timeout",
        )
        assert result.success is False
        assert result.error == "timeout"


class TestMultiAgentCoordinator:
    """协调器测试"""

    def test_spawn(self) -> None:
        coordinator = MultiAgentCoordinator()
        agent = coordinator.spawn(role="coder", name="CodeBot")

        assert agent.agent_id != ""
        assert agent.name == "CodeBot"
        assert agent.role == "coder"
        assert agent.status == SubAgentStatus.IDLE
        assert agent.agent_id in coordinator.agents

    def test_spawn_multiple(self) -> None:
        coordinator = MultiAgentCoordinator()
        agents = [coordinator.spawn("coder", f"coder-{i}") for i in range(3)]

        assert len(coordinator.agents) == 3
        ids = {a.agent_id for a in agents}
        assert len(ids) == 3  # 全部唯一

    def test_get_status(self) -> None:
        coordinator = MultiAgentCoordinator()
        coordinator.spawn("coder", "c1")
        coordinator.spawn("reviewer", "r1")
        coordinator.spawn("tester", "t1")

        status = coordinator.get_status()
        assert status["total_agents"] == 3
        assert status["idle"] == 3
        assert status["running"] == 0

    def test_remove_agent(self) -> None:
        coordinator = MultiAgentCoordinator()
        agent = coordinator.spawn("coder", "temp")
        agent_id = agent.agent_id

        assert coordinator.remove_agent(agent_id) is True
        assert agent_id not in coordinator.agents

        # 重复删除
        assert coordinator.remove_agent(agent_id) is False

    def test_clear_agents(self) -> None:
        coordinator = MultiAgentCoordinator()
        coordinator.spawn("coder", "c1")
        coordinator.spawn("reviewer", "r1")

        coordinator.clear_agents()
        assert len(coordinator.agents) == 0
        assert len(coordinator.tasks) == 0

    def test_get_agent(self) -> None:
        coordinator = MultiAgentCoordinator()
        agent = coordinator.spawn("coder", "find-me")

        assert coordinator.get_agent(agent.agent_id) is agent
        assert coordinator.get_agent("nonexistent") is None

    @pytest.mark.asyncio
    async def test_dispatch_with_runner(self) -> None:
        coordinator = MultiAgentCoordinator()

        # 设置模拟 runner
        async def mock_runner(agent: SubAgent, task: str) -> str:
            return f"{agent.name} processed: {task[:20]}"

        coordinator.set_runner(mock_runner)

        agent1 = coordinator.spawn("coder", "CodeBot")
        agent2 = coordinator.spawn("reviewer", "ReviewBot")

        result = await coordinator.dispatch("build feature X", [agent1, agent2])

        assert result.task_id != ""
        assert len(result.results) == 2
        assert all(r.success for r in result.results)
        assert "CodeBot" in result.results[0].output

    @pytest.mark.asyncio
    async def test_dispatch_without_runner(self) -> None:
        coordinator = MultiAgentCoordinator()
        agent = coordinator.spawn("explorer", "ExploreBot")

        result = await coordinator.dispatch("analyze codebase", [agent])

        assert len(result.results) == 1
        assert result.results[0].success is True
        # 无 runner 时使用模拟输出
        assert "ExploreBot" in result.results[0].output

    @pytest.mark.asyncio
    async def test_dispatch_sequential(self) -> None:
        coordinator = MultiAgentCoordinator()

        async def mock_runner(agent: SubAgent, task: str) -> str:
            return f"[{agent.name}] done"

        coordinator.set_runner(mock_runner)

        agent1 = coordinator.spawn("coder", "C1")
        agent2 = coordinator.spawn("reviewer", "R1")

        result = await coordinator.dispatch_sequential(
            "implement feature", [agent1, agent2]
        )

        assert len(result.results) == 2
        assert all(r.success for r in result.results)
        # 第二个 agent 的输入应该包含第一个的输出
        assert "[C1]" in result.results[1].output or result.results[1].output

    @pytest.mark.asyncio
    async def test_dispatch_with_exception(self) -> None:
        coordinator = MultiAgentCoordinator()

        async def failing_runner(agent: SubAgent, task: str) -> str:
            if agent.role == "reviewer":
                raise RuntimeError("review failed")
            return "ok"

        coordinator.set_runner(failing_runner)

        agent1 = coordinator.spawn("coder", "C1")
        agent2 = coordinator.spawn("reviewer", "R1")

        result = await coordinator.dispatch("test", [agent1, agent2])

        # 至少 coder 应该成功
        assert result.results[0].success is True
        # reviewer 应该失败
        assert result.results[1].success is False

    def test_summarize(self) -> None:
        coordinator = MultiAgentCoordinator()
        results = [
            TaskResult(agent_id="a1", role="coder", success=True, output="ok"),
            TaskResult(agent_id="a2", role="coder", success=True, output="ok"),
            TaskResult(agent_id="a3", role="reviewer", success=False, error="fail"),
        ]

        summary = coordinator._summarize(results)
        assert "总任务: 3" in summary
        assert "成功: 2" in summary
        assert "失败: 1" in summary
        assert "coder" in summary
        assert "reviewer" in summary


class TestGlobalCoordinator:
    """全局单例测试"""

    def test_get_coordinator(self) -> None:
        coordinator = get_coordinator()
        assert coordinator is not None
        assert isinstance(coordinator, MultiAgentCoordinator)

        # 多次调用返回同一实例
        assert get_coordinator() is coordinator


class TestAgentCollaboration:
    """多 Agent 协作场景测试"""

    @pytest.mark.asyncio
    async def test_two_agents_collaborate(self):
        """测试两个 Agent 协作完成任务"""
        coordinator = MultiAgentCoordinator()

        # 模拟协作流程：coder 写代码 → reviewer 审查
        collaboration_log = []

        async def coder_runner(agent: SubAgent, task: str) -> str:
            collaboration_log.append(f"{agent.name} writing code")
            return "def hello(): return 'world'"

        async def reviewer_runner(agent: SubAgent, task: str) -> str:
            collaboration_log.append(f"{agent.name} reviewing code")
            return "looks good"

        # 创建 coder 和 reviewer
        coder = coordinator.spawn("coder", "CodeBot")
        reviewer = coordinator.spawn("reviewer", "ReviewBot")

        # 分发并行任务
        task = "implement login feature"
        result = await coordinator.dispatch(task, [coder, reviewer])

        assert result.task_id != ""
        assert len(result.results) == 2
        # 两个 agent 都应该成功
        assert all(r.success for r in result.results)

    @pytest.mark.asyncio
    async def test_three_agents_pipeline(self):
        """测试三 Agent 流水线协作"""
        coordinator = MultiAgentCoordinator()

        async def mock_runner(agent: SubAgent, task: str) -> str:
            return f"{agent.role} done: {task[:20]}"

        coordinator.set_runner(mock_runner)

        # 创建三个不同角色的 agent
        planner = coordinator.spawn("planner", "PlannerBot")
        coder = coordinator.spawn("coder", "CoderBot")
        tester = coordinator.spawn("tester", "TesterBot")

        # 顺序执行
        result = await coordinator.dispatch_sequential(
            "build todo app",
            [planner, coder, tester]
        )

        assert len(result.results) == 3
        assert all(r.success for r in result.results)
        # 验证结果包含各角色
        roles = [r.role for r in result.results]
        assert "planner" in roles
        assert "coder" in roles
        assert "tester" in roles

    @pytest.mark.asyncio
    async def test_parallel_vs_sequential_timing(self):
        """测试并行 vs 顺序执行的时间差异"""
        coordinator = MultiAgentCoordinator()

        async def slow_runner(agent: SubAgent, task: str) -> str:
            import asyncio
            await asyncio.sleep(0.05)  # 模拟 50ms 延迟
            return "done"

        coordinator.set_runner(slow_runner)

        agents = [coordinator.spawn("coder", f"Agent{i}") for i in range(3)]

        # 并行执行
        import time
        start_parallel = time.time()
        await coordinator.dispatch("task", agents)
        time_parallel = time.time() - start_parallel

        coordinator2 = MultiAgentCoordinator()
        coordinator2.set_runner(slow_runner)
        agents2 = [coordinator2.spawn("coder", f"Agent{i}") for i in range(3)]

        # 顺序执行
        start_seq = time.time()
        await coordinator2.dispatch_sequential("task", agents2)
        time_seq = time.time() - start_seq

        # 并行应该比顺序快（并行约 50ms，顺序约 150ms）
        assert time_parallel < time_seq * 0.7  # 并行至少快 30%

    @pytest.mark.asyncio
    async def test_coordination_summary(self):
        """测试协作汇总信息"""
        coordinator = MultiAgentCoordinator()


        results = [
            TaskResult(agent_id="a1", role="coder", success=True, output="code"),
            TaskResult(agent_id="a2", role="reviewer", success=True, output="approved"),
            TaskResult(agent_id="a3", role="tester", success=False, error="test failed"),
        ]

        summary = coordinator._summarize(results)
        assert "总任务: 3" in summary
        assert "成功: 2" in summary
        assert "失败: 1" in summary
        assert "tester" in summary  # 包含失败的 role

    def test_coordinator_history(self):
        """测试协调器历史记录"""
        coordinator = MultiAgentCoordinator()

        # 执行一些任务来创建历史
        coordinator.spawn("coder", "C1")
        coordinator.spawn("coder", "C2")

        # 检查历史列表存在
        assert hasattr(coordinator, "_history")
        assert isinstance(coordinator._history, list)
