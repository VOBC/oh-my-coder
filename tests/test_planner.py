"""
PlannerAgent 单元测试（纯逻辑，不调 API）
"""

from src.agents.planner import (
    ChainOfThought,
    DependencyGraph,
    ExecutionPlan,
    SubTask,
    TaskComplexity,
    TaskPhase,
    TaskPriority,
)

# ─────────────────────────────────────────────────────────────────
# DependencyGraph
# ─────────────────────────────────────────────────────────────────


class TestDependencyGraph:
    def test_add_task(self):
        graph = DependencyGraph()
        graph.add_task("T1", [])
        graph.add_task("T2", ["T1"])
        assert "T1" in graph.nodes
        assert "T2" in graph.nodes

    def test_topological_sort_no_deps(self):
        graph = DependencyGraph()
        for tid in ["T1", "T2", "T3"]:
            graph.add_task(tid, [])
        result, has_cycle = graph.topological_sort()
        assert has_cycle is False
        assert set(result) == {"T1", "T2", "T3"}

    def test_topological_sort_with_deps(self):
        graph = DependencyGraph()
        graph.add_task("T1", [])
        graph.add_task("T2", ["T1"])
        graph.add_task("T3", ["T2"])
        result, has_cycle = graph.topological_sort()
        assert has_cycle is False
        assert result.index("T1") < result.index("T2") < result.index("T3")

    def test_topological_sort_parallel(self):
        """T2、T3 都依赖 T1，可以并行"""
        graph = DependencyGraph()
        graph.add_task("T1", [])
        graph.add_task("T2", ["T1"])
        graph.add_task("T3", ["T1"])
        result, has_cycle = graph.topological_sort()
        assert has_cycle is False
        assert result.index("T1") < result.index("T2")
        assert result.index("T1") < result.index("T3")

    def test_topological_sort_cycle(self):
        """T1→T2→T3→T1 形成环"""
        graph = DependencyGraph()
        graph.add_task("T1", ["T3"])
        graph.add_task("T2", ["T1"])
        graph.add_task("T3", ["T2"])
        _result, has_cycle = graph.topological_sort()
        assert has_cycle is True

    def test_get_ready_tasks_empty(self):
        graph = DependencyGraph()
        graph.add_task("T1", [])
        graph.add_task("T2", ["T1"])
        ready = graph.get_ready_tasks(set())
        assert "T1" in ready
        assert "T2" not in ready

    def test_get_ready_tasks_partial(self):
        graph = DependencyGraph()
        graph.add_task("T1", [])
        graph.add_task("T2", ["T1"])
        graph.add_task("T3", ["T2"])
        ready = graph.get_ready_tasks({"T1"})
        assert "T2" in ready
        assert "T1" not in ready
        assert "T3" not in ready

    def test_get_ready_tasks_all_done(self):
        graph = DependencyGraph()
        graph.add_task("T1", [])
        graph.add_task("T2", ["T1"])
        ready = graph.get_ready_tasks({"T1", "T2"})
        assert len(ready) == 0


# ─────────────────────────────────────────────────────────────────
# ChainOfThought
# ─────────────────────────────────────────────────────────────────


class TestChainOfThought:
    def test_add_step(self):
        cot = ChainOfThought()
        step = cot.add_step(thought="test thought", conclusion="test conclusion")
        assert step.thought == "test thought"
        assert step.conclusion == "test conclusion"
        assert step.step == 1

    def test_multiple_steps(self):
        cot = ChainOfThought()
        cot.add_step(thought="step 1")
        cot.add_step(thought="step 2", action="do something")
        cot.add_step(thought="step 3", observation="saw result")
        assert len(cot.steps) == 3
        assert cot.steps[1].action == "do something"
        assert cot.steps[2].observation == "saw result"

    def test_to_prompt(self):
        cot = ChainOfThought()
        cot.add_step(thought="think", conclusion="done")
        prompt = cot.to_prompt()
        assert "think" in prompt
        assert "done" in prompt


# ─────────────────────────────────────────────────────────────────
# ExecutionPlan & SubTask
# ─────────────────────────────────────────────────────────────────


class TestSubTask:
    def test_subtask_creation(self):
        task = SubTask(
            id="T1",
            title="测试任务",
            description="描述",
            agent="executor",
            priority=TaskPriority.HIGH,
            complexity=TaskComplexity.COMPLEX,
            dependencies=[],
            estimated_time="10m",
        )
        assert task.id == "T1"
        assert task.priority == TaskPriority.HIGH
        assert task.complexity == TaskComplexity.COMPLEX

    def test_subtask_with_deps(self):
        task = SubTask(
            id="T2",
            title="依赖任务",
            description="描述",
            agent="planner",
            dependencies=["T1", "T3"],
        )
        assert "T1" in task.dependencies
        assert "T3" in task.dependencies


class TestExecutionPlan:
    def test_plan_creation(self):
        plan = ExecutionPlan(
            title="测试计划",
            summary="摘要",
            total_tasks=3,
            estimated_time="30m",
        )
        assert plan.total_tasks == 3
        assert len(plan.phases) == 0

    def test_plan_with_phases(self):
        plan = ExecutionPlan(title="多阶段计划", summary="")
        phase = TaskPhase(
            name="分析阶段",
            description="需求分析",
            tasks=[
                SubTask(
                    id="T1",
                    title="探索代码",
                    description="探索",
                    agent="explore",
                ),
            ],
        )
        plan.phases.append(phase)
        assert len(plan.phases) == 1
        assert plan.phases[0].name == "分析阶段"


# ─────────────────────────────────────────────────────────────────
# adjust_plan
# ─────────────────────────────────────────────────────────────────


class TestAdjustPlan:
    """测试 adjust_plan 自适应调整逻辑"""

    def _make_plan(self):
        plan = ExecutionPlan(title="test", summary="")
        phase = TaskPhase(
            name="default",
            description="",
            tasks=[
                SubTask(
                    id="T1",
                    title="任务1",
                    description="desc1",
                    agent="explore",
                    priority=TaskPriority.MEDIUM,
                    complexity=TaskComplexity.MODERATE,
                    dependencies=[],
                ),
                SubTask(
                    id="T2",
                    title="任务2",
                    description="desc2",
                    agent="executor",
                    priority=TaskPriority.HIGH,
                    complexity=TaskComplexity.SIMPLE,
                    dependencies=["T1"],
                ),
                SubTask(
                    id="T3",
                    title="任务3",
                    description="desc3",
                    agent="verifier",
                    priority=TaskPriority.LOW,
                    complexity=TaskComplexity.SIMPLE,
                    dependencies=["T2"],
                ),
            ],
        )
        plan.phases.append(phase)
        return plan

    def test_adjust_add_retry_task(self):
        """失败任务后添加重试任务"""
        from src.agents.planner import PlannerAgent

        plan = self._make_plan()
        adjusted = PlannerAgent.adjust_plan(
            plan,
            completed_tasks=set(),
            failed_tasks={"T2"},
        )
        # 重试任务被添加到同一 phase
        all_ids = []
        for phase in adjusted.phases:
            all_ids.extend(t.id for t in phase.tasks)
        assert "T2_retry" in all_ids

    def test_adjust_add_new_requirements(self):
        """新增需求添加新阶段"""
        from src.agents.planner import PlannerAgent

        plan = self._make_plan()
        adjusted = PlannerAgent.adjust_plan(
            plan,
            completed_tasks={"T1", "T2"},
            failed_tasks=set(),
            new_requirements=["新需求A", "新需求B"],
        )
        phase_names = [p.name for p in adjusted.phases]
        assert "新增需求" in phase_names
        # 新任务在新增阶段
        new_phase = next(p for p in adjusted.phases if p.name == "新增需求")
        new_ids = [t.id for t in new_phase.tasks]
        assert "N1" in new_ids
        assert "N2" in new_ids

    def test_adjust_get_ready_tasks(self):
        """调整后获取就绪任务"""
        from src.agents.planner import PlannerAgent

        plan = self._make_plan()
        adjusted = PlannerAgent.adjust_plan(
            plan,
            completed_tasks={"T1"},
            failed_tasks=set(),
        )
        graph = PlannerAgent._build_dependency_graph(adjusted)
        ready = graph.get_ready_tasks({"T1"})
        assert "T2" in ready
        assert "T1" not in ready
