"""
Agent 编排器 - 智能体调度和编排引擎

核心功能：
1. Agent 工作流编排
2. 任务分解和分配
3. 状态追踪和持久化
4. 并行执行支持

设计思路：
原项目通过 Skills 系统编排多个 Agent 协作。
我们实现一个轻量级的编排引擎，支持：
- 顺序执行：explore → analyst → planner → executor
- 并行执行：多个 Agent 同时工作
- 条件执行：根据前序结果决定后续步骤
"""

import asyncio
import json
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..agents.health_check import HealthChecker


def _get_trace_context_cls():
    try:
        from ..agents.transparency import TraceContext

        return TraceContext
    except ImportError:
        return None


class WorkflowStatus(Enum):
    """工作流状态"""

    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class ExecutionMode(Enum):
    """执行模式"""

    SEQUENTIAL = "sequential"  # 顺序执行
    PARALLEL = "parallel"  # 并行执行
    CONDITIONAL = "conditional"  # 条件执行


@dataclass
class WorkflowStep:
    """工作流步骤"""

    agent_name: str
    description: str
    dependencies: list[str] = field(default_factory=list)  # 依赖的前序步骤
    condition: Callable[[dict], bool] | None = None  # 执行条件
    retry_count: int = 0
    timeout: float = 300.0  # 5分钟默认超时
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowResult:
    """工作流执行结果"""

    workflow_id: str
    status: WorkflowStatus
    steps_completed: list[str]
    steps_failed: list[str]
    outputs: dict[str, Any]  # agent_name -> output
    total_tokens: int
    total_cost: float
    execution_time: float
    error: str | None = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    agent_names: list[str] = field(
        default_factory=list
    )  # 此工作流涉及的 Agent 名称列表


# 预定义的工作流模板
WORKFLOW_TEMPLATES = {
    "build": [
        WorkflowStep("explore", "探索代码库"),
        WorkflowStep("analyst", "分析需求", dependencies=["explore"]),
        WorkflowStep("planner", "制定计划", dependencies=["analyst"]),
        WorkflowStep("architect", "设计架构", dependencies=["planner"]),
        WorkflowStep("executor", "实现代码", dependencies=["architect"]),
        WorkflowStep("verifier", "验证完成", dependencies=["executor"]),
    ],
    "review": [
        WorkflowStep("explore", "探索代码库"),
        WorkflowStep("code-reviewer", "代码审查", dependencies=["explore"]),
        WorkflowStep("security-reviewer", "安全审查", dependencies=["explore"]),
    ],
    "debug": [
        WorkflowStep("explore", "探索代码库"),
        WorkflowStep("debugger", "调试问题", dependencies=["explore"]),
        WorkflowStep("verifier", "验证修复", dependencies=["debugger"]),
    ],
    "test": [
        WorkflowStep("explore", "探索代码库"),
        WorkflowStep("test-engineer", "设计测试", dependencies=["explore"]),
        WorkflowStep("executor", "实现测试", dependencies=["test-engineer"]),
        WorkflowStep("verifier", "运行测试", dependencies=["executor"]),
    ],
    # ---- 新增工作流（2026-04-11）----
    # 全自动路由：根据任务描述自动识别类型，选择最合适的工作流
    "autopilot": [
        WorkflowStep("analyst", "任务类型识别 + 选择最合适工作流"),
    ],
    # ---- 文档生成模式（2026-04-12）----
    # 架构师 → 写手 → 文档专家，三阶段流水线，专注长篇结构化文档
    "doc": [
        WorkflowStep("architect", "架构设计与文档框架", dependencies=[]),
        WorkflowStep("writer", "内容初稿撰写", dependencies=["architect"]),
        WorkflowStep("document", "长篇文档精修与格式化", dependencies=["writer"]),
        WorkflowStep("verifier", "文档完整性校验", dependencies=["document"]),
    ],
    # ---- 顺序执行编排（2026-04-12）----
    # 通用顺序执行：用户定义各 Agent，按顺序依次执行，每步产出作为下一步输入
    "sequential": [
        WorkflowStep("explore", "探索代码库结构", dependencies=[]),
        WorkflowStep("analyst", "深度分析需求与现状", dependencies=["explore"]),
        WorkflowStep("planner", "制定详细执行计划", dependencies=["analyst"]),
        WorkflowStep("executor", "执行实现", dependencies=["planner"]),
        WorkflowStep("verifier", "验证结果正确性", dependencies=["executor"]),
    ],
    # 结对编程：实时对话式 Code Review，Explorer + Critic 交替协作
    "pair": [
        WorkflowStep("explore", "探索代码库"),
        WorkflowStep("critic", "代码审查（结对）", dependencies=["explore"]),
        WorkflowStep("explorer", "问题澄清（探索者）", dependencies=["critic"]),
        WorkflowStep("critic", "确认修复（评审者）", dependencies=["explorer"]),
    ],
    # 重构模式：分析热点 → 制定重构计划 → 执行 → 验证
    "refactor": [
        WorkflowStep("analyst", "分析代码热点和坏味道"),
        WorkflowStep("planner", "制定重构计划", dependencies=["analyst"]),
        WorkflowStep("code-simplifier", "执行重构", dependencies=["planner"]),
        WorkflowStep("verifier", "验证重构正确性", dependencies=["code-simplifier"]),
        WorkflowStep("test-engineer", "运行测试确保无回归", dependencies=["verifier"]),
    ],
}


def _detect_workflow_for_autopilot(task: str) -> str:
    """
    根据任务描述自动识别应使用的工作流
    Keyword → Workflow 映射
    """
    task_lower = task.lower()
    if any(
        k in task_lower for k in ["bug", "崩溃", "报错", "fix", "修复", "错误", "crash"]
    ):
        return "debug"
    if any(k in task_lower for k in ["test", "测试", "用例", "coverage"]):
        return "test"
    if any(k in task_lower for k in ["refactor", "重构", "优化", "简化", "cleanup"]):
        return "refactor"
    if any(k in task_lower for k in ["review", "审查", "cr", "review"]):
        return "review"
    return "build"  # 默认走 build 流程


class Orchestrator:
    """
    Agent 编排器

    核心方法：
    - execute_workflow(): 执行完整工作流
    - execute_step(): 执行单个步骤
    - save_state(): 保存状态
    - load_state(): 加载状态

    Tier 0 自动注入（2026-04-12）：
    - 每次工作流完成后，自动读取 .omc/skills/index.json
    - 将所有 Skill 的名字+描述追加到系统 Prompt 底部
    - 让 Agent 知道有哪些经验可用

    自动沉淀（2026-04-12）：
    - 工作流完成后调用 evaluate_skill_worthy 判断是否值得沉淀
    - 满足条件时自动创建 SKILL.md
    """

    def __init__(
        self,
        model_router,
        state_dir: Path | None = None,
        skills_dir: Path | None = None,
        project_path: Path | None = None,
    ):
        """
        Args:
            model_router: 模型路由器
            state_dir: 状态持久化目录
            skills_dir: Skill 文件根目录（默认 .omc/skills）
            project_path: 项目路径（用于分层记忆注入）
        """
        self.model_router = model_router
        self.state_dir = state_dir or Path(".omc/state")
        self.state_dir.mkdir(parents=True, exist_ok=True)

        # Skill 自进化管理器
        from ..memory.skill_manager import SkillManager

        self.skills_dir = skills_dir or self.state_dir.parent / "skills"
        self._skill_manager: SkillManager | None = None

        # Checkpoint 管理器（懒加载）
        self._checkpoint_manager = None  # type: ignore

        # HealthChecker 管理器（懒加载）
        self._health_checker: HealthChecker | None = None

        # Agent 实例缓存
        self._agents: dict[str, Any] = {}

        # 工作流状态
        self._active_workflows: dict[str, WorkflowResult] = {}

        # 分层记忆管理器（懒加载）
        self._memory_manager = None  # type: ignore
        self._project_path = project_path

    # ------------------------------------------------------------------
    # Skill 自进化（Tier 0 自动注入）
    # ------------------------------------------------------------------

    @property
    def skill_manager(self):
        """懒加载 SkillManager"""
        if self._skill_manager is None:
            from ..memory.skill_manager import SkillManager

            self._skill_manager = SkillManager(skills_dir=self.skills_dir)
        return self._skill_manager

    @property
    def checkpoint_manager(self):
        """懒加载 CheckpointManager"""
        if self._checkpoint_manager is None:
            from .checkpoint import CheckpointManager

            self._checkpoint_manager = CheckpointManager(
                project_path=self.state_dir.parent
            )
        return self._checkpoint_manager

    @property
    def memory_manager(self):
        """懒加载 MemoryManager（分层有限记忆）"""
        if self._memory_manager is None:
            from ..memory.manager import MemoryManager

            base = self._project_path or self.state_dir.parent
            self._memory_manager = MemoryManager.from_project(base)
        return self._memory_manager

    @property
    def health_checker(self) -> "HealthChecker":
        """懒加载 HealthChecker"""
        if self._health_checker is None:
            from ..agents.health_check import HealthChecker

            self._health_checker = HealthChecker(
                orchestrator=self,
                check_interval=60.0,
                stale_threshold=300.0,
                max_retries=3,
                state_dir=self.state_dir.parent.parent / "health",
            )
        return self._health_checker

    def inject_memory_context(self) -> str:
        """
        获取 Tier 0 核心记忆注入文本。

        追加到 AgentContext.skill_context，放在 Skill 经验之后。
        """
        tier0 = self.memory_manager.get_tier0_summary()
        if not tier0 or not tier0.strip():
            return ""
        return (
            f"\n\n{'=' * 50}\n" f"## 🧠 核心记忆（Tier 0）\n" f"{tier0}\n" f"{'=' * 50}"
        )

    def get_skill_inventory(self, max_tokens: int = 500) -> str:
        """
        获取所有 Skill 的名字+一句话描述。
        供 Tier 0 注入到 Agent 系统 Prompt 底部。
        """
        return self.skill_manager.get_skill_inventory(max_tokens=max_tokens)

    def inject_skill_context(self, agent_class: str, max_tokens: int = 500) -> str:
        """
        为指定 Agent 生成 Skill 上下文注入文本。

        追加到 agent.system_prompt 底部，实现 Tier 0 自动注入。
        """
        inventory = self.get_skill_inventory(max_tokens=max_tokens)
        if not inventory or "(none)" in inventory:
            return ""
        return (
            f"\n\n{'=' * 50}\n"
            f"## 📚 可用经验（来自历史沉淀）\n"
            f"{inventory}\n"
            f"如当前任务与上述经验相关，请优先参考或调用 skill-manage 工具。\n"
            f"{'=' * 50}"
        )

    # ------------------------------------------------------------------
    # 自动沉淀
    # ------------------------------------------------------------------

    async def _maybe_learn_from_workflow(
        self,
        workflow_name: str,
        context: dict[str, Any],
        result: WorkflowResult,
    ) -> None:
        """
        工作流完成后评估是否值得沉淀为 Skill。

        满足以下任一条件时自动创建 SKILL.md：
        1. 工具调用 ≥5 次且成功
        2. 错误 → 解决
        3. 用户纠正
        4. 非平凡工作流（≥3 步骤）

        结果写入 .omc/skills/<category>/<name>/SKILL.md。
        """
        from ..memory.skill_manager import SkillManager

        # 统计工具调用次数（从 outputs 估算）
        tool_call_count = sum(
            len(getattr(o, "artifacts", {}).get("tool_calls", []))
            for o in result.outputs.values()
        )
        # 如果无法精确统计，至少按步骤数估算
        if tool_call_count == 0:
            tool_call_count = len(result.steps_completed)

        had_error = result.status == WorkflowStatus.FAILED
        had_fix = context.get("_had_fix", False)
        had_user_correction = context.get("_had_user_correction", False)
        is_nontrivial = len(result.steps_completed) >= 3

        if not SkillManager.evaluate_skill_worthy(
            tool_call_count=tool_call_count,
            had_error=had_error,
            had_fix=had_fix,
            had_user_correction=had_user_correction,
            is_nontrivial_workflow=is_nontrivial,
        ):
            return

        # 生成 Skill 草稿
        final_result = ""
        if result.outputs:
            last = list(result.outputs.values())[-1]
            final_result = getattr(last, "result", "")[:300] or str(last)[:300]

        # 构建 task_context 供 auto_create_skill 使用
        task_context = {
            "agent_name": (
                result.steps_completed[-1] if result.steps_completed else "orchestrator"
            ),
            "task": context.get("task", ""),
            "workflow": workflow_name,
            "result": final_result,
            "steps": result.steps_completed,
            "error": str(result.error) if result.error else None,
            "had_fix": context.get("_had_fix", False),
            "had_user_correction": context.get("_had_user_correction", False),
            "tool_call_count": tool_call_count,
            "judgments": context.get("_judgments", []),
            "gotchas": context.get("_gotchas", []),
        }

        # 通过 SelfImprovingAgent.auto_create_skill 完成沉淀
        from ..agents.self_improving import SelfImprovingAgent

        try:
            sia = SelfImprovingAgent(skill_manager=self.skill_manager)
            sia.auto_create_skill(task_context)
        except Exception:
            pass  # 静默，不阻塞工作流

    async def _maybe_evolve_agents(
        self,
        result: WorkflowResult,
    ) -> None:
        """
        工作流完成后触发 Agent 自进化。

        对参与工作流的所有 Agent 执行进化分析：
        1. 分析执行日志
        2. 提取成功/失败模式
        3. 更新 system prompt（如需要）

        仅当启用自进化且样本数足够时执行。
        """
        from ..agents.self_improving import EvolutionConfig, SelfImprovingAgent

        config = EvolutionConfig()
        if not config.enabled:
            return

        try:
            sia = SelfImprovingAgent(evolution_config=config)

            # 对每个参与的 Agent 执行进化
            for agent_name in result.steps_completed:
                try:
                    record = sia.evolve(
                        agent_type=agent_name,
                        trigger="workflow_completion",
                    )
                    if record:
                        # 进化成功，记录到上下文
                        result.outputs[f"_evolution_{agent_name}"] = {
                            "evolution_id": record.id,
                            "generation": record.generation,
                            "changes": record.changes,
                        }
                except Exception:
                    pass  # 单个 Agent 进化失败不影响其他
        except Exception:
            pass  # 静默，不阻塞工作流

    # ------------------------------------------------------------------
    # 上下文构建
    # ------------------------------------------------------------------

    def _build_agent_context(
        self,
        agent_name: str,
        context: dict[str, Any],
    ):
        """构建统一的 AgentContext（含 Skill 注入 + Tier 0 记忆注入）"""
        from ..agents.base import AgentContext

        skill_ctx = self.inject_skill_context(agent_name)
        memory_ctx = self.inject_memory_context()

        return AgentContext(
            project_path=Path(context.get("project_path", ".")),
            task_description=context.get("task", ""),
            previous_outputs=context.get("_result_outputs", {}),
            skill_context=skill_ctx + memory_ctx,
        )

    # ------------------------------------------------------------------
    # Agent 注册与获取
    # ------------------------------------------------------------------

    def register_agent(self, agent):
        """注册 Agent 实例"""
        self._agents[agent.name] = agent

    def get_agent(self, name: str):
        """获取 Agent 实例"""
        if name not in self._agents:
            # 动态加载
            from ..agents.base import get_agent

            agent_class = get_agent(name)
            if agent_class:
                agent = agent_class(self.model_router)
                self._agents[name] = agent
            else:
                raise ValueError(f"未知的 Agent: {name}")

        return self._agents[name]

    async def execute_workflow(
        self,
        workflow_name: str,
        context: dict[str, Any],
        mode: ExecutionMode = ExecutionMode.SEQUENTIAL,
        skip_checkpoint: bool = False,
    ) -> WorkflowResult:
        """
        执行工作流

        Args:
            workflow_name: 工作流名称或步骤列表
            context: 执行上下文
            mode: 执行模式

        Returns:
            WorkflowResult: 执行结果
        """
        import time
        import uuid

        workflow_id = str(uuid.uuid4())[:8]
        start_time = time.time()

        # 获取工作流模板
        if isinstance(workflow_name, str):
            # autopilot 特殊处理：自动检测任务类型并路由
            if workflow_name == "autopilot":
                actual = _detect_workflow_for_autopilot(context.get("task", ""))
                steps = WORKFLOW_TEMPLATES.get(actual, [])
                # 记录路由日志（写入 context 供后续使用）
                context["_autopilot_routed_to"] = actual
            else:
                steps = WORKFLOW_TEMPLATES.get(workflow_name, [])
        else:
            steps = workflow_name

        if not steps:
            raise ValueError(f"无效的工作流: {workflow_name}")

        # 初始化结果
        result = WorkflowResult(
            workflow_id=workflow_id,
            status=WorkflowStatus.RUNNING,
            steps_completed=[],
            steps_failed=[],
            outputs={},
            total_tokens=0,
            total_cost=0.0,
            execution_time=0.0,
            agent_names=[s.agent_name for s in steps],
        )

        self._active_workflows[workflow_id] = result

        # ---- 自动快照：任务开始前记录 checkpoint ----
        if not skip_checkpoint:
            try:
                task_id = context.get("task", "unknown").replace(" ", "-")[:30]
                task_desc = context.get("task", "")
                cp_id = self.checkpoint_manager.create(
                    task_id=task_id,
                    description=f"Workflow 开始: {workflow_name} | {task_desc}",
                )
                context["_checkpoint_id"] = cp_id
            except Exception:
                pass  # 静默，不阻塞工作流

        try:
            # 根据模式执行
            if mode == ExecutionMode.SEQUENTIAL:
                await self._execute_sequential(steps, context, result)
            elif mode == ExecutionMode.PARALLEL:
                await self._execute_parallel(steps, context, result)
            else:
                await self._execute_conditional(steps, context, result)

            result.status = WorkflowStatus.COMPLETED

        except Exception as e:
            result.status = WorkflowStatus.FAILED
            result.error = f"{type(e).__name__}: [执行异常，请查看工作流日志]"  # 不输出原始错误，防止泄露

        finally:
            result.execution_time = time.time() - start_time
            self._save_workflow_result(result)

        # ---- 自动沉淀：评估是否值得生成 Skill（Tier 0）----
        try:
            await self._maybe_learn_from_workflow(workflow_name, context, result)
        except Exception:
            pass  # 静默，不阻塞工作流

        # ---- 自进化：分析执行日志，优化 Agent prompt----
        try:
            await self._maybe_evolve_agents(result)
        except Exception:
            pass  # 静默，不阻塞工作流

        return result

    async def _execute_sequential(
        self,
        steps: list[WorkflowStep],
        context: dict[str, Any],
        result: WorkflowResult,
    ):
        """顺序执行步骤（集成健康检查与自动重试）"""

        for step in steps:
            # 检查依赖
            for dep in step.dependencies:
                if dep not in result.steps_completed:
                    raise ValueError(f"步骤 {step.agent_name} 的依赖 {dep} 未完成")

            agent_name = step.agent_name
            retry_count = 0
            max_retries = getattr(self, "_health_checker", None)
            max_retries = max_retries.max_retries if max_retries else 3

            while True:
                # ---- 注册健康检查：Agent 开始执行 ----
                hc = self.health_checker
                hc.register_agent(
                    agent_name=agent_name,
                    task_id=f"wf_{result.workflow_id}_step_{step.agent_name}",
                    workflow_id=result.workflow_id,
                    step_index=steps.index(step),
                )

                try:
                    agent = self.get_agent(agent_name)
                    agent_context = self._build_agent_context(agent_name, context)

                    output = await asyncio.wait_for(
                        agent.execute(agent_context),
                        timeout=step.timeout,
                    )

                    # ---- 心跳注册：执行成功，取消注册 ----
                    hc.unregister_agent(agent_name)

                    if output.status.value == "completed":
                        result.steps_completed.append(agent_name)
                        result.outputs[agent_name] = output
                        result.total_tokens += output.usage.get("total_tokens", 0)
                        break  # 进入下一步
                    else:
                        raise Exception(f"Agent {agent_name} 执行失败: {output.error}")

                except asyncio.TimeoutError:
                    error = f"Agent {agent_name} 执行超时（>{step.timeout}s）"
                    hc.unregister_agent(agent_name)

                    if hc.record_failure(agent_name, error):
                        # 超过重试上限
                        result.steps_failed.append(agent_name)
                        raise Exception(error)

                    # 仍可重试 → 找空闲 Agent 重分配
                    retry_count += 1
                    new_agent = hc.reassign_task(
                        agent_name=agent_name,
                        workflow_id=result.workflow_id,
                        step=step,
                    )
                    if new_agent:
                        agent_name = new_agent
                        hc.register_agent(agent_name, workflow_id=result.workflow_id)
                    else:
                        result.steps_failed.append(agent_name)
                        raise Exception(f"无法重分配任务：{error}")
                    # 重试

                except Exception as step_err:
                    hc.unregister_agent(agent_name)
                    error_msg = str(step_err)

                    if hc.record_failure(agent_name, error_msg):
                        result.steps_failed.append(agent_name)
                        raise

                    retry_count += 1
                    new_agent = hc.reassign_task(
                        agent_name=agent_name,
                        workflow_id=result.workflow_id,
                        step=step,
                    )
                    if new_agent:
                        agent_name = new_agent
                        hc.register_agent(agent_name, workflow_id=result.workflow_id)
                    else:
                        result.steps_failed.append(agent_name)
                        raise
                    # 重试

    async def _execute_parallel(
        self,
        steps: list[WorkflowStep],
        context: dict[str, Any],
        result: WorkflowResult,
    ):
        """
        并行执行步骤

        实现思路：
        1. 对步骤按依赖拓扑分层
        2. 同一层的所有步骤并发执行（asyncio.gather）
        3. 等待整层完成后再进入下一层
        这样 review 工作流的 code-reviewer + security-reviewer 可以同时跑，
        比顺序执行快约一倍。
        """

        # 建立步骤字典
        step_map: dict[str, WorkflowStep] = {s.agent_name: s for s in steps}

        # 拓扑分层
        levels: list[list[WorkflowStep]] = []
        remaining = set(step_map.keys())

        while remaining:
            # 找到所有依赖都已完成的步骤（作为当前层）
            current_level = [
                step_map[name]
                for name in remaining
                if all(
                    dep in result.steps_completed for dep in step_map[name].dependencies
                )
            ]
            if not current_level:
                # 有循环依赖或无效依赖
                break

            levels.append(current_level)
            for step in current_level:
                remaining.remove(step.agent_name)

        # 按层执行：同层并行，层间顺序
        for level in levels:
            tasks = []
            for step in level:
                agent = self.get_agent(step.agent_name)
                agent_context = self._build_agent_context(step.agent_name, context)
                tasks.append(
                    asyncio.wait_for(
                        agent.execute(agent_context),
                        timeout=step.timeout,
                    )
                )

            results = await asyncio.gather(*tasks, return_exceptions=True)

            for step, task_result in zip(level, results):
                if isinstance(task_result, Exception):
                    result.steps_failed.append(step.agent_name)
                    raise Exception(
                        f"Agent {step.agent_name} 并行执行失败: {task_result}"
                    )

                output = task_result
                if output.status.value == "completed":
                    result.steps_completed.append(step.agent_name)
                    result.outputs[step.agent_name] = output
                    result.total_tokens += output.usage.get("total_tokens", 0)
                else:
                    result.steps_failed.append(step.agent_name)
                    raise Exception(f"Agent {step.agent_name} 执行失败: {output.error}")

    async def _execute_conditional(
        self,
        steps: list[WorkflowStep],
        context: dict[str, Any],
        result: WorkflowResult,
    ):
        """
        条件执行步骤

        实现思路：
        - 对每个步骤，执行前检查 step.condition(result.outputs)
        - condition 为 None → 总是执行
        - condition 返回 True → 执行
        - condition 返回 False → 跳过（不计入 completed，但也不报错）
        - condition 抛异常 → 标记失败
        """

        for step in steps:
            # 检查依赖
            for dep in step.dependencies:
                if dep not in result.steps_completed:
                    raise ValueError(f"步骤 {step.agent_name} 的依赖 {dep} 未完成")

            # 执行条件检查
            if step.condition is not None:
                try:
                    should_run = step.condition(result.outputs)
                except Exception as cond_err:
                    result.steps_failed.append(step.agent_name)
                    raise Exception(f"步骤 {step.agent_name} 条件执行异常: {cond_err}")
                if not should_run:
                    # 条件不满足，跳过此步骤
                    continue

            try:
                agent = self.get_agent(step.agent_name)
                agent_context = self._build_agent_context(step.agent_name, context)

                output = await asyncio.wait_for(
                    agent.execute(agent_context),
                    timeout=step.timeout,
                )

                if output.status.value == "completed":
                    result.steps_completed.append(step.agent_name)
                    result.outputs[step.agent_name] = output
                    result.total_tokens += output.usage.get("total_tokens", 0)
                else:
                    result.steps_failed.append(step.agent_name)
                    raise Exception(f"Agent {step.agent_name} 执行失败: {output.error}")

            except asyncio.TimeoutError:
                result.steps_failed.append(step.agent_name)
                raise Exception(f"Agent {step.agent_name} 执行超时")

    async def execute_single_agent(
        self,
        agent_name: str,
        context: dict[str, Any],
        session_id: str = "",
    ):
        """
        执行单个 Agent

        Args:
            agent_name: Agent 名称
            context: 执行上下文
            session_id: Trace session ID（由调用方传入）

        Returns:
            AgentOutput: 执行结果
        """
        TraceContext = _get_trace_context_cls()
        trace_ctx = None
        if TraceContext is not None:
            trace_ctx = TraceContext(
                agent_name=agent_name,
                session_id=session_id or "default",
                workflow_id="",
            )
            trace_ctx.start()

        try:
            agent = self.get_agent(agent_name)
            agent_context = self._build_agent_context(agent_name, context)
            output = await agent.execute(agent_context)
            if trace_ctx is not None:
                summary = ""
                if hasattr(output, "output"):
                    summary = str(output.output)[:200]
                trace_ctx.stop(
                    status="completed",
                    output_summary=summary,
                )
            return output
        except Exception as e:
            if trace_ctx is not None:
                error_name = type(e).__name__
                trace_ctx.log_error(error_name)
                trace_ctx.stop(status="failed", error=error_name)
            raise

    def _save_workflow_result(self, result: WorkflowResult):
        """保存工作流结果"""
        result_file = self.state_dir / f"workflow_{result.workflow_id}.json"

        with open(result_file, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "workflow_id": result.workflow_id,
                    "status": result.status.value,
                    "steps_completed": result.steps_completed,
                    "steps_failed": result.steps_failed,
                    "total_tokens": result.total_tokens,
                    "total_cost": result.total_cost,
                    "execution_time": result.execution_time,
                    "error": result.error,
                    "timestamp": result.timestamp,
                },
                f,
                ensure_ascii=False,
                indent=2,
            )

    def load_workflow_result(self, workflow_id: str) -> WorkflowResult | None:
        """加载工作流结果"""
        result_file = self.state_dir / f"workflow_{workflow_id}.json"

        if not result_file.exists():
            return None

        with open(result_file, encoding="utf-8") as f:
            data = json.load(f)

        return WorkflowResult(
            workflow_id=data["workflow_id"],
            status=WorkflowStatus(data["status"]),
            steps_completed=data["steps_completed"],
            steps_failed=data["steps_failed"],
            outputs={},
            total_tokens=data["total_tokens"],
            total_cost=data["total_cost"],
            execution_time=data["execution_time"],
            error=data.get("error"),
            timestamp=data["timestamp"],
        )

    def list_active_workflows(self) -> list[str]:
        """列出活跃的工作流"""
        return list(self._active_workflows.keys())

    def get_workflow_status(self, workflow_id: str) -> WorkflowResult | None:
        """获取工作流状态"""
        return self._active_workflows.get(workflow_id)

    def get_current_state(self) -> dict[str, Any]:
        """获取当前所有 Agent 的协作状态"""
        active_agents = []
        completed_agents = []
        pending_agents = []

        # 遍历所有活跃工作流
        for workflow_id, workflow_result in self._active_workflows.items():
            if workflow_result.status == WorkflowStatus.RUNNING:
                # 活跃：agent_names 中尚未 completed 的
                completed_set = set(workflow_result.steps_completed)
                for agent_name in workflow_result.agent_names:
                    if agent_name not in completed_set:
                        active_agents.append(
                            {
                                "name": agent_name,
                                "status": "working",
                                "task": f"执行工作流: {workflow_id}",
                                "started_at": workflow_result.timestamp,
                            }
                        )
                # 已完成
                for agent_name in workflow_result.steps_completed:
                    completed_agents.append(
                        {
                            "name": agent_name,
                            "status": "done",
                            "task": f"完成工作流: {workflow_id}",
                            "duration": (
                                f"{workflow_result.execution_time:.0f}s"
                                if workflow_result.execution_time > 0
                                else "N/A"
                            ),
                        }
                    )

            elif workflow_result.status == WorkflowStatus.COMPLETED:
                # 全量标记为已完成
                for agent_name in workflow_result.steps_completed:
                    completed_agents.append(
                        {
                            "name": agent_name,
                            "status": "done",
                            "task": f"完成工作流: {workflow_id}",
                            "duration": (
                                f"{workflow_result.execution_time:.0f}s"
                                if workflow_result.execution_time > 0
                                else "N/A"
                            ),
                        }
                    )
            elif workflow_result.status == WorkflowStatus.FAILED:
                # 失败的
                for agent_name in workflow_result.steps_failed:
                    pending_agents.append(agent_name)

        # 待执行 = agent_names 中不在 active/completed/failed 的
        all_workflow_names: set = set()
        for wf in self._active_workflows.values():
            all_workflow_names.update(wf.agent_names)

        active_names = {a["name"] for a in active_agents}
        completed_names = {a["name"] for a in completed_agents}
        failed_names = set(pending_agents)

        for name in all_workflow_names:
            if (
                name not in active_names
                and name not in completed_names
                and name not in failed_names
            ):
                pending_agents.append(name)

        # 去重
        completed_names_unique = {}
        for c in completed_agents:
            completed_names_unique[c["name"]] = c
        completed_agents = list(completed_names_unique.values())

        active_names_unique = {}
        for a in active_agents:
            active_names_unique[a["name"]] = a
        active_agents = list(active_names_unique.values())

        total = len(all_workflow_names) if all_workflow_names else 0
        done_count = len(completed_agents)
        total_progress = f"{done_count}/{total}" if total > 0 else "0/0"

        current_workflow = ""
        if self._active_workflows:
            wf = list(self._active_workflows.values())[0]
            current_workflow = wf.agent_names[0] if wf.agent_names else "unknown"

        return {
            "active_agents": active_agents,
            "completed_agents": completed_agents,
            "pending_agents": pending_agents,
            "total_progress": total_progress,
            "workflow": current_workflow,
            "timestamp": datetime.now().isoformat(),
        }
