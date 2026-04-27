"""
Planner Agent - 任务规划智能体（增强版）

增强功能：
1. 结构化任务分解 - 使用 Pydantic 模型
2. COT 推理链 - 多步推理能力
3. 依赖图分析 - 自动拓扑排序
4. 自适应调整 - 根据执行反馈优化计划
5. 上下文理解 - 利用项目探索结果

参考：
- Windsurf Cascade 的深度推理
- LangGraph 的状态机编排
"""

import re
from dataclasses import dataclass
from enum import Enum

from pydantic import BaseModel, Field

from ..core.router import TaskType
from .base import (
    AgentContext,
    AgentLane,
    AgentOutput,
    AgentStatus,
    BaseAgent,
    register_agent,
)

# ============================================================
# 结构化任务模型
# ============================================================


class TaskPriority(str, Enum):
    """任务优先级"""

    CRITICAL = "critical"  # 阻塞其他任务
    HIGH = "high"  # 重要任务
    MEDIUM = "medium"  # 常规任务
    LOW = "low"  # 可延后任务


class TaskStatus(str, Enum):
    """任务状态"""

    PENDING = "pending"
    READY = "ready"  # 依赖已满足
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class TaskComplexity(str, Enum):
    """任务复杂度"""

    SIMPLE = "simple"  # 单文件修改
    MODERATE = "moderate"  # 多文件修改
    COMPLEX = "complex"  # 架构级别改动


class SubTask(BaseModel):
    """子任务"""

    id: str = Field(..., description="任务ID，格式 T1, T2, T3...")
    title: str = Field(..., description="任务标题")
    description: str = Field(..., description="任务描述")
    agent: str = Field(..., description="推荐的执行 Agent")
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM)
    complexity: TaskComplexity = Field(default=TaskComplexity.MODERATE)
    dependencies: list[str] = Field(
        default_factory=list, description="依赖的任务ID列表"
    )
    estimated_time: str = Field(default="5m", description="预估耗时")
    files_to_modify: list[str] = Field(
        default_factory=list, description="需要修改的文件"
    )
    acceptance_criteria: list[str] = Field(default_factory=list, description="验收标准")
    risks: list[str] = Field(default_factory=list, description="潜在风险")


class TaskPhase(BaseModel):
    """任务阶段"""

    name: str = Field(..., description="阶段名称")
    description: str = Field(..., description="阶段描述")
    tasks: list[SubTask] = Field(default_factory=list)
    parallel: bool = Field(default=False, description="是否可并行执行")


class ExecutionPlan(BaseModel):
    """执行计划"""

    title: str = Field(..., description="计划标题")
    summary: str = Field(..., description="计划摘要")
    phases: list[TaskPhase] = Field(default_factory=list)
    total_tasks: int = Field(default=0)
    estimated_time: str = Field(default="1h")
    critical_path: list[str] = Field(default_factory=list, description="关键路径")
    milestones: list[str] = Field(default_factory=list, description="里程碑")


# ============================================================
# COT 推理链
# ============================================================


@dataclass
class ReasoningStep:
    """推理步骤"""

    step: int
    thought: str
    action: str | None = None
    observation: str | None = None
    conclusion: str | None = None


class ChainOfThought:
    """思维链推理"""

    def __init__(self):
        self.steps: list[ReasoningStep] = []
        self.current_step = 0

    def add_step(
        self,
        thought: str,
        action: str | None = None,
        observation: str | None = None,
        conclusion: str | None = None,
    ) -> ReasoningStep:
        """添加推理步骤"""
        self.current_step += 1
        step = ReasoningStep(
            step=self.current_step,
            thought=thought,
            action=action,
            observation=observation,
            conclusion=conclusion,
        )
        self.steps.append(step)
        return step

    def to_prompt(self) -> str:
        """转换为 Prompt 格式"""
        lines = ["## 思维链推理过程\n"]
        for step in self.steps:
            lines.append(f"### 步骤 {step.step}")
            lines.append(f"**思考**: {step.thought}")
            if step.action:
                lines.append(f"**行动**: {step.action}")
            if step.observation:
                lines.append(f"**观察**: {step.observation}")
            if step.conclusion:
                lines.append(f"**结论**: {step.conclusion}")
            lines.append("")
        return "\n".join(lines)


# ============================================================
# 依赖图分析
# ============================================================


class DependencyGraph:
    """依赖图"""

    def __init__(self):
        self.nodes: set[str] = set()
        self.edges: dict[str, set[str]] = {}  # task_id -> set of dependencies

    def add_task(self, task_id: str, dependencies: list[str] = None):
        """添加任务节点"""
        self.nodes.add(task_id)
        self.edges[task_id] = set(dependencies or [])

    def topological_sort(self) -> tuple[list[str], bool]:
        """拓扑排序，返回 (排序结果, 是否有环)"""
        in_degree = dict.fromkeys(self.nodes, 0)

        # 计算入度
        for node in self.nodes:
            for dep in self.edges.get(node, set()):
                if dep in in_degree:
                    in_degree[node] += 1

        # 找出入度为 0 的节点
        queue = [node for node in self.nodes if in_degree[node] == 0]
        result = []

        while queue:
            node = queue.pop(0)
            result.append(node)

            # 减少依赖此节点的其他节点的入度
            for other in self.nodes:
                if node in self.edges.get(other, set()):
                    in_degree[other] -= 1
                    if in_degree[other] == 0:
                        queue.append(other)

        has_cycle = len(result) != len(self.nodes)
        return result, has_cycle

    def find_critical_path(self) -> list[str]:
        """找到关键路径（最长路径）"""
        # 简化实现：返回拓扑排序中优先级最高的路径
        sorted_nodes, _ = self.topological_sort()

        # 按 CRITICAL > HIGH > MEDIUM > LOW 排序
        priority_order = {
            TaskPriority.CRITICAL: 0,
            TaskPriority.HIGH: 1,
            TaskPriority.MEDIUM: 2,
            TaskPriority.LOW: 3,
        }

        return sorted_nodes

    def get_ready_tasks(self, completed: set[str]) -> list[str]:
        """获取就绪任务（依赖已满足）"""
        ready = []
        for node in self.nodes:
            if node not in completed:
                deps = self.edges.get(node, set())
                if deps.issubset(completed):
                    ready.append(node)
        return ready


# ============================================================
# 增强 PlannerAgent
# ============================================================


@register_agent
class PlannerAgent(BaseAgent):
    """规划 Agent - 任务分解和执行计划（增强版）"""

    name = "planner"
    description = "规划智能体 - 任务分解和执行计划"
    lane = AgentLane.BUILD_ANALYSIS
    default_tier = "high"
    icon = "📋"
    tools = ["file_read", "search", "code_analyze"]

    @property
    def system_prompt(self) -> str:
        return """你是一个资深的项目架构师和规划师。

## 角色
你的职责是将复杂任务分解为可执行的小任务，并制定合理的执行计划。

## 核心能力

### 1. 结构化任务分解
- 使用 SMART 原则定义任务
- 每个任务独立、可测试、可验收
- 明确任务的输入、输出和验收标准

### 2. 依赖分析
- 识别任务间依赖关系
- 构建依赖图
- 计算最优执行顺序（拓扑排序）

### 3. 复杂度评估
- SIMPLE: 单文件修改，< 50 行代码
- MODERATE: 多文件修改，50-200 行代码
- COMPLEX: 架构级改动，> 200 行代码

### 4. 风险识别
- 技术风险：新技术、复杂算法
- 依赖风险：外部服务、第三方库
- 业务风险：需求不明确、边界情况

### 5. 自适应调整
- 根据执行反馈调整计划
- 处理任务失败和重试
- 动态添加新任务

## 思维链推理

请按以下步骤思考：

**步骤 1: 理解任务**
- 任务的核心目标是什么？
- 有哪些约束条件？
- 成功的标准是什么？

**步骤 2: 分析上下文**
- 项目的技术栈是什么？
- 现有代码结构如何？

**步骤 3: 风险评估**
- 有哪些潜在风险？
- 如何规避或缓解？

## 输出格式

请输出以下结构：

### 📋 执行计划摘要
- 任务总数: X
- 预计耗时: X
- 关键路径: T1 → T2 → T3

### 📊 阶段分解

#### 阶段 1: [阶段名]
| ID | 任务 | Agent | 优先级 | 复杂度 | 依赖 | 耗时 |
|----|------|-------|--------|--------|------|------|
| T1 | ... | explore | HIGH | SIMPLE | - | 5m |

#### 阶段 2: [阶段名]
...

### 🎯 验收标准
- [ ] 标准 1
- [ ] 标准 2

### ⚠️ 风险提示
- ⚠️ 风险 1: ...
- ⚠️ 风险 2: ...

### 📝 执行顺序
```
1. T1 (explore)
2. T2 (analyst) - 依赖 T1
3. T3, T4 并行 - 依赖 T2
...
```

### 🔄 自适应调整
- 如果 T3 失败，回退到 T2 重新分析
- 如果发现新需求，添加 T5
"""

    def _build_context_prompt(self, context: AgentContext) -> str:
        """构建上下文提示"""
        parts = []

        # 项目探索结果
        if context.previous_outputs.get("explore"):
            explore_result = context.previous_outputs["explore"]
            if isinstance(explore_result, dict):
                parts.append(
                    f"""## 项目探索结果
- 文件数量: {explore_result.get("files_count", "N/A")}
- 技术栈: {", ".join(explore_result.get("tech_stack", []))}
- 项目结构: {explore_result.get("structure", "N/A")}
"""
                )

        # 需求分析结果
        if context.previous_outputs.get("analyst"):
            analyst_result = context.previous_outputs["analyst"]
            if isinstance(analyst_result, dict):
                parts.append(
                    f"""## 需求分析结果
- 实体: {", ".join(analyst_result.get("entities", []))}
- 功能: {", ".join(analyst_result.get("features", []))}
- 约束: {", ".join(analyst_result.get("constraints", []))}
"""
                )

        # 相关文件
        if context.relevant_files:
            files_str = "\n".join(f"  - {f}" for f in context.relevant_files[:10])
            parts.append(
                f"""## 相关文件
{files_str}
"""
            )

        return "\n".join(parts) if parts else ""

    def _parse_structured_plan(self, result: str) -> ExecutionPlan:
        """解析结构化计划"""
        plan = ExecutionPlan(
            title="执行计划",
            summary="任务执行计划",
        )

        # 解析任务表格
        task_pattern = (
            r"\| (T\d+) \| (.+?) \| (\w+) \| (\w+) \| (\w+) \| (.+?) \| (\w+) \|"
        )
        matches = re.findall(task_pattern, result)

        current_phase = TaskPhase(name="默认阶段", description="执行阶段")

        for match in matches:
            task_id, title, agent, priority, complexity, deps, time = match

            # 解析依赖
            dependencies = [d.strip() for d in deps.split(",") if d.strip() != "-"]

            task = SubTask(
                id=task_id,
                title=title.strip(),
                description=title.strip(),
                agent=agent.strip(),
                priority=TaskPriority(priority.lower()),
                complexity=TaskComplexity(complexity.upper()),
                dependencies=dependencies,
                estimated_time=time.strip(),
            )
            current_phase.tasks.append(task)

        if current_phase.tasks:
            plan.phases.append(current_phase)

        plan.total_tasks = sum(len(p.tasks) for p in plan.phases)
        return plan

    @staticmethod
    def _build_dependency_graph(plan: ExecutionPlan) -> DependencyGraph:
        """构建依赖图"""
        graph = DependencyGraph()

        for phase in plan.phases:
            for task in phase.tasks:
                graph.add_task(task.id, task.dependencies)

        return graph

    async def _run(
        self, context: AgentContext, prompt: list[dict[str, str]], **kwargs
    ) -> str:
        """执行规划"""
        # 构建上下文
        context_prompt = self._build_context_prompt(context)

        # COT 推理
        cot = ChainOfThought()

        # 步骤 1: 理解任务
        cot.add_step(
            thought=f"分析任务: {context.task_description}",
            conclusion="需要将任务分解为可执行的子任务",
        )

        # 步骤 2: 分析上下文
        if context_prompt:
            cot.add_step(
                thought="分析项目上下文",
                observation=context_prompt[:500],
                conclusion="已获取项目结构和技术栈信息",
            )

        # 构建完整 prompt
        full_prompt = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": context_prompt},
            {"role": "user", "content": cot.to_prompt()},
            {
                "role": "user",
                "content": f"""
请为以下任务制定执行计划：

## 任务
{context.task_description}

请按照上述格式输出结构化的执行计划。
""",
            },
        ]

        # 调用模型
        from ..models.base import Message

        messages = [
            Message(role=msg["role"], content=msg["content"]) for msg in full_prompt
        ]

        response = await self.model_router.route_and_call(
            task_type=TaskType.PLANNING,
            messages=messages,
            complexity="high",
        )

        return response.content

    def _post_process(self, result: str, context: AgentContext) -> AgentOutput:
        """后处理 - 解析结构化输出"""
        # 解析计划
        plan = self._parse_structured_plan(result)

        # 构建依赖图
        graph = self._build_dependency_graph(plan)

        # 获取执行顺序
        execution_order, has_cycle = graph.topological_sort()

        # 构建推荐
        recommendations = [
            f"按拓扑顺序执行: {' → '.join(execution_order[:5])}",
            "关注关键路径上的任务",
            "每个任务完成后验证验收标准",
        ]

        if has_cycle:
            recommendations.append("⚠️ 检测到循环依赖，需要调整计划")

        return AgentOutput(
            agent_name=self.name,
            status=AgentStatus.COMPLETED,
            result=result,
            artifacts={
                "plan": plan.model_dump(),
                "execution_order": execution_order,
                "has_cycle": has_cycle,
            },
            recommendations=recommendations,
            next_agent="architect" if plan.phases else None,
        )

    @staticmethod
    def adjust_plan(
        plan: ExecutionPlan,
        completed_tasks: set[str],
        failed_tasks: set[str],
        new_requirements: list[str] | None = None,
    ) -> ExecutionPlan:
        """
        自适应调整计划

        Args:
            plan: 原计划
            completed_tasks: 已完成的任务ID
            failed_tasks: 失败的任务ID
            new_requirements: 新增需求

        Returns:
            调整后的计划
        """
        graph = PlannerAgent._build_dependency_graph(plan)

        # 获取就绪任务
        ready_tasks = graph.get_ready_tasks(completed_tasks)

        # 处理失败任务
        for failed_id in failed_tasks:
            # 找到失败任务
            for phase in plan.phases:
                for task in phase.tasks:
                    if task.id == failed_id:
                        # 添加重试任务
                        retry_task = SubTask(
                            id=f"{failed_id}_retry",
                            title=f"重试: {task.title}",
                            description=task.description,
                            agent=task.agent,
                            priority=TaskPriority.HIGH,
                            complexity=task.complexity,
                            dependencies=[],
                        )
                        phase.tasks.append(retry_task)

        # 添加新需求
        if new_requirements:
            new_phase = TaskPhase(
                name="新增需求",
                description="根据执行反馈新增的任务",
                tasks=[
                    SubTask(
                        id=f"N{i + 1}",
                        title=req,
                        description=req,
                        agent="executor",
                        priority=TaskPriority.HIGH,
                    )
                    for i, req in enumerate(new_requirements)
                ],
            )
            plan.phases.append(new_phase)

        return plan
