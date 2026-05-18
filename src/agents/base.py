from __future__ import annotations

# mypy: disable-error-code="abstract, arg-type, assignment, attr-defined, call-arg, call-overload, dict-item, func-returns-value, import-untyped, index, misc, no-any-return, no-redef, operator, override, return, return-value, syntax, union-attr, var-annotated"


"""
Agent 基类 - 所有智能体的基类

设计原则：
1. 每个 Agent 职责单一、明确
2. 通过 Prompt 定义角色和行为
3. 自动记录工作过程和产出
4. 支持与其他 Agent 协作

Agent 生命周期：
1. 初始化（加载配置和 Prompt）
2. 接收任务
3. 执行（调用模型、使用工具）
4. 输出结果
"""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

from src.models.base import Message, ModelResponse

logger = logging.getLogger(__name__)

# 工具 Schema 定义（OpenAI function calling 格式）
WEB_FETCH_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "web_fetch",
        "description": "获取指定 URL 的网页文本内容，用于访问外部链接、查阅在线文档",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "要访问的 URL"}
            },
            "required": ["url"],
        },
    },
}

SUPPORTED_TOOLS = {"web_fetch": WEB_FETCH_TOOL_SCHEMA}

if TYPE_CHECKING:
    from src.models.router import ModelRouter


class AgentStatus(Enum):
    """Agent 状态"""

    IDLE = "idle"  # 空闲
    WORKING = "working"  # 工作中
    WAITING = "waiting"  # 等待输入
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 失败


class AgentLane(Enum):
    """Agent 通道 - 对应原项目的四大通道"""

    BUILD_ANALYSIS = "build_analysis"  # 构建/分析
    REVIEW = "review"  # 审查
    DOMAIN = "domain"  # 领域
    COORDINATION = "coordination"  # 协调


@dataclass
class AgentContext:
    """Agent 执行上下文"""

    project_path: Path  # 项目路径
    task_description: str  # 任务描述
    working_directory: Optional[Path] = None  # 工作目录
    relevant_files: list[Path] = field(default_factory=list)  # 相关文件
    previous_outputs: dict[str, Any] = field(default_factory=dict)  # 前序 Agent 输出
    metadata: dict[str, Any] = field(default_factory=dict)  # 其他元数据
    skill_context: str = ""  # Tier 0 自动注入：Skill 经验清单（由 Orchestrator 填充）
    override_model: Optional[str] = (
        None  # 用户指定的模型 ID（如 "glm-4-flash"），来自前端选择
    )


@dataclass
class AgentOutput:
    """Agent 输出"""

    agent_name: str  # Agent 名称
    status: AgentStatus  # 执行状态
    result: Optional[str] = None  # 主要结果
    artifacts: dict[str, Any] = field(default_factory=dict)  # 产物（文件、数据等）
    recommendations: list[str] = field(default_factory=list)  # 推荐后续步骤
    next_agent: Optional[str] = None  # 推荐下一个 Agent
    usage: dict[str, int] = field(default_factory=dict)  # Token 使用
    execution_time: float = 0.0  # 执行时间（秒）
    error: Optional[str] = None  # 错误信息
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class BaseAgent(ABC):
    """
    Agent 基类

    核心方法：
    - execute(): 执行任务（模板方法）
    - _prepare_prompt(): 准备 Prompt
    - _run(): 实际执行逻辑（子类实现）
    - _post_process(): 后处理

    子类需要实现：
    - _run(): 核心执行逻辑
    - 定义 name, description, default_tier 等属性
    """

    # 子类必须覆盖的属性
    name: str = "base_agent"
    description: str = "基类 Agent"
    lane: AgentLane = AgentLane.BUILD_ANALYSIS
    default_tier = "medium"  # low, medium, high

    # 可选属性
    icon: str = "🤖"
    tools: list[str] = ["web_fetch"]  # 可用工具列表，默认启用 web_fetch

    def __init__(
        self,
        model_router: Optional[ModelRouter] = None,
        config: Optional[dict[str, Any]] = None,
        orchestrator: Optional[Any] = None,
    ):
        """
        Args:
            model_router: 模型路由器（可选，CLI info 等只读场景可不传）
            config: Agent 特定配置
            orchestrator: Orchestrator 实例（用于调用子 Agent），由 Orchestrator.get_agent() 自动注入
        """
        self.model_router = model_router
        self.orchestrator = orchestrator
        self.config = config or {}
        self.status = AgentStatus.IDLE
        self._output_history: list[AgentOutput] = []
        self._last_model_response: Optional[Any] = (
            None  # 缓存最后一次 ModelResponse，用于 token 统计
        )

        # 初始化工作目录上下文扫描器
        try:
            from ..context import WorkspaceScanner

            project_path = config.get("project_path") if config else None
            if project_path:
                self.workspace_scanner = WorkspaceScanner(Path(project_path))
            else:
                self.workspace_scanner = WorkspaceScanner(Path.cwd())
        except Exception:
            # 浏览器上下文感知失败不影响 Agent 初始化
            self.workspace_scanner = None

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """返回系统提示词（定义 Agent 的角色和行为）"""
        pass

    def get_workspace_context(self, max_depth: int = 3) -> str:
        """
        获取工作目录上下文

        扫描项目目录，生成文件树结构，用于增强 Agent 的上下文感知能力。

        Args:
            max_depth: 最大扫描深度

        Returns:
            str: 文件树上下文字符串
        """
        if self.workspace_scanner is None:
            return "[工作目录上下文不可用]"

        try:
            return self.workspace_scanner.to_context_string(max_depth=max_depth)
        except Exception as e:
            return f"[工作目录上下文扫描失败: {e}]"

    def get_full_context(self, max_depth: int = 3) -> dict[str, str]:
        """
        获取完整上下文（文件 + 浏览器）

        Returns:
            Dict[str, str]: 包含 workspace 和 browser 上下文字典
        """
        from ..context import BrowserAwareness

        result = {
            "workspace": self.get_workspace_context(max_depth=max_depth),
        }

        try:
            awareness = BrowserAwareness()
            browser_ctx = asyncio.run(awareness.get_current_tab())
            result["browser"] = browser_ctx.to_context_string()
        except Exception:
            result["browser"] = "[浏览器上下文不可用]"

        return result

    def get_context_prompt(self, context: AgentContext) -> str:
        """根据上下文生成额外提示词"""
        parts = []

        if context.task_description:
            parts.append(f"## 当前任务\n{context.task_description}")

        if context.project_path:
            parts.append(f"## 项目路径\n{context.project_path}")

        # 添加工目录上下文（文件树）
        workspace_ctx = self.get_workspace_context()
        if workspace_ctx and workspace_ctx != "[工作目录上下文不可用]":
            parts.append(f"## 项目文件结构\n{workspace_ctx}")

        if context.relevant_files:
            files_str = "\n".join(str(f) for f in context.relevant_files)
            parts.append(f"## 相关文件\n{files_str}")

        if context.previous_outputs:
            parts.append("## 前序工作成果")
            for agent_name, output in context.previous_outputs.items():
                parts.append(f"### {agent_name}\n{output}")

        # Tier 0: 追加 Skill 经验上下文
        if context.skill_context:
            parts.append(context.skill_context)

        return "\n\n".join(parts)

    async def execute(self, context: AgentContext, **kwargs) -> AgentOutput:
        """
        执行任务（模板方法）

        流程：
        1. 更新状态
        2. 准备 Prompt
        3. 调用模型
        4. 后处理
        5. 记录输出
        """
        import time

        start_time = time.time()

        self.status = AgentStatus.WORKING

        try:
            # 保存用户指定的模型（供 _run 中 route_and_call 使用）
            self._override_model = getattr(context, "override_model", None)

            # 准备 Prompt
            prompt = self._prepare_prompt(context)

            # 执行
            result = await self._run(context, prompt, **kwargs)

            # 后处理
            output = self._post_process(result, context)

            # 填充 token 使用统计（从缓存的 ModelResponse 中提取）
            if self._last_model_response is not None:
                usage = self._last_model_response.usage
                output.usage = {
                    "prompt_tokens": getattr(usage, "prompt_tokens", 0),
                    "completion_tokens": getattr(usage, "completion_tokens", 0),
                    "total_tokens": getattr(usage, "total_tokens", 0),
                }

            output.execution_time = time.time() - start_time
            self.status = AgentStatus.COMPLETED

        except Exception as e:
            output = AgentOutput(
                agent_name=self.name,
                status=AgentStatus.FAILED,
                error=f"{type(e).__name__}",  # 只记录类型，不泄露详情
                execution_time=time.time() - start_time,
            )
            self.status = AgentStatus.FAILED

        # 记录历史
        self._output_history.append(output)

        return output

    def _prepare_prompt(self, context: AgentContext) -> list[dict[str, str]]:
        """
        准备完整的 Prompt

        Returns:
            List[Dict]: 消息列表（系统 + 用户）
        """
        messages = [
            {"role": "system", "content": self.system_prompt},
        ]

        context_prompt = self.get_context_prompt(context)
        if context_prompt:
            messages.append({"role": "user", "content": context_prompt})

        return messages

    @abstractmethod
    async def _run(
        self, context: AgentContext, prompt: list[dict[str, str]], **kwargs
    ) -> str:
        """
        实际执行逻辑（子类实现）

        Args:
            context: 执行上下文
            prompt: 准备好的 Prompt
            **kwargs: 额外参数

        Returns:
            str: 执行结果
        """
        pass

    def _post_process(
        self,
        result: str,
        context: AgentContext,
    ) -> AgentOutput:
        """
        后处理（子类可覆盖）

        默认实现：直接包装为输出
        """
        return AgentOutput(agent_name=self.name,
            status=AgentStatus.COMPLETED,
            result=result,
        )

    async def call_model(
        self,
        task_type: str,
        messages: list[Message],
        complexity: str = "medium",
        use_cache: bool = True,
        **kwargs,
    ) -> ModelResponse:
        """
        调用模型（自动注入用户指定的模型覆盖）

        支持工具调用：self.tools 非空时自动注入工具定义，
        模型返回 tool_calls 时自动执行工具并回传结果，最多 5 轮。
        """
        # 强制注入 web_fetch 工具（所有 Agent 默认可用）
        if "tools" not in kwargs:
            if "web_fetch" in SUPPORTED_TOOLS:
                kwargs["tools"] = [SUPPORTED_TOOLS["web_fetch"]]

        available_tools = {"web_fetch": self._web_fetch_tool}
        current_messages: list[Message] = list(messages)

        for _ in range(5):  # 最多 5 轮工具调用
            response = await self.model_router.route_and_call(
                task_type=task_type,
                messages=current_messages,
                complexity=complexity,
                use_cache=use_cache,
                override_model=getattr(self, "_override_model", None),
                **kwargs,
            )
            self._last_model_response = response

            if not response.tool_calls:
                return response

            # 执行工具调用
            for tc in response.tool_calls:
                func_name = tc.get("function", {}).get("name", "")
                func_args_str = tc.get("function", {}).get("arguments", "{}")
                try:
                    func_args = json.loads(func_args_str)
                except Exception:
                    func_args = {}

                if func_name in available_tools:
                    try:
                        result = await available_tools[func_name](func_args)
                    except Exception as e:
                        result = f"Error: {type(e).__name__}: {e}"
                else:
                    result = f"Error: unknown tool {func_name}"

                # 追加 assistant 消息和 tool 结果
                current_messages.append(Message(
                    role="assistant",
                    content=response.content or "",
                    tool_calls=response.tool_calls,
                ))
                current_messages.append(Message(
                    role="tool",
                    content=result,
                    tool_call_id=tc.get("id", ""),
                    name=func_name,
                ))

            # 后续轮次不再传 tools
            kwargs = {k: v for k, v in kwargs.items() if k != "tools"}

        return response

    async def _web_fetch_tool(self, args_json) -> str:
        """web_fetch 工具：获取 URL 的网页文本内容（HTML 转纯文本）"""
        import json
        import re
        import subprocess
        # 接受 dict（直接调用）或 JSON 字符串（call_model 传过来）
        if isinstance(args_json, dict):
            args = args_json
        else:
            try:
                args = json.loads(args_json)
            except Exception:
                return f"[web_fetch error] Invalid arguments (not JSON): {str(args_json)[:200]}"

        url = args.get("url", "")
        if not url:
            return "[web_fetch error] Missing url parameter"

        try:
            result = subprocess.run(
                ["curl", "-s", "-L", "--max-time", "15", url],
                capture_output=True, timeout=20
            )
            html = result.stdout.decode("utf-8", errors="replace")[:8000]
            # 简单去除 HTML 标签
            text = re.sub(r'<[^>]+>', ' ', html)
            text = re.sub(r'\s+', ' ', text).strip()
            return text[:8000]
        except Exception as e:
            return f"[web_fetch error] {type(e).__name__}: {e}"

    def get_last_output(self) -> Optional[AgentOutput]:
        """获取最后一次输出"""
        return self._output_history[-1] if self._output_history else None

    def get_output_history(self) -> list[AgentOutput]:
        """获取输出历史"""
        return self._output_history.copy()

    async def call_subagent(
        self,
        agent_name: str,
        task: str,
        context: AgentContext,
        max_depth: int = 3,
    ) -> AgentOutput:
        """
        调用子 Agent（P1-6 Agent 子系统重构 Phase 1）

        允许当前 Agent 将复杂任务分解，委托给其他专业 Agent 处理。
        通过 orchestrator 实现，支持防递归和超时控制。

        用法示例（由任意 Agent 在 execute() 中调用）：
            result = await self.call_subagent(
                agent_name="analyst",
                task="分析这段代码的性能瓶颈",
                context=context,
            )
            if result.status == AgentStatus.COMPLETED:
                self.logger.info(f"Analyst 子任务完成: {result.result}")

        Args:
            agent_name: 子 Agent 名称（如 "analyst", "planner"）
            task: 子任务描述
            context: 当前 Agent 的执行上下文（会被转发）
            max_depth: 最大调用深度，默认 3

        Returns:
            AgentOutput: 子 Agent 的执行结果

        Raises:
            RuntimeError: 如果 Orchestrator 未注入（不应该发生）
        """
        if self.orchestrator is None:
            raise RuntimeError(
                f"Agent '{self.name}' 无法调用子 Agent：Orchestrator 未注入。"
                "请确认是通过 Orchestrator.get_agent() 创建此 Agent 实例。"
            )

        # 将当前 Agent 的 previous_outputs 合并到 context 中供子 Agent 使用
        if not hasattr(context, "previous_outputs"):
            context.previous_outputs = {}  # type: ignore
        if self._output_history:
            context.previous_outputs[self.name] = self._output_history[-1]

        return await self.orchestrator.invoke_subagent(
            agent_name=agent_name,
            task=task,
            context={
                "project_path": str(context.project_path),
                "override_model": context.override_model,
                "skill_context": context.skill_context,
                "working_directory": str(context.working_directory)
                if context.working_directory
                else None,
                "previous_outputs": context.previous_outputs,
                "_subagent_depth": context.metadata.get("_subagent_depth", 0),
            },
            max_depth=max_depth,
        )

    def save_output(self, output_path: Path):
        """保存输出到文件"""
        if not self._output_history:
            return

        last_output = self._output_history[-1]
        output_file = (
            output_path / f"{self.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "agent": last_output.agent_name,
                    "status": last_output.status.value,
                    "result": last_output.result,
                    "artifacts": last_output.artifacts,
                    "recommendations": last_output.recommendations,
                    "error": last_output.error,
                    "timestamp": last_output.timestamp,
                },
                f,
                ensure_ascii=False,
                indent=2,
            )


# Agent 注册表（用于动态发现和创建）
AGENT_REGISTRY: dict[str, type[BaseAgent]] = {}


def register_agent(agent_class: type[BaseAgent]):
    """注册 Agent"""
    AGENT_REGISTRY[agent_class.name] = agent_class
    return agent_class


def get_agent(name: str) -> Optional[type[BaseAgent]]:
    """获取已注册的 Agent"""
    return AGENT_REGISTRY.get(name)


def list_all_agents() -> list[dict[str, Any]]:
    """
    列出所有已注册的 Agent

    Returns:
        Agent 信息列表，每个元素包含 name, description, lane, default_tier 等
    """
    result = []
    for name, agent_class in AGENT_REGISTRY.items():
        info = {
            "name": name,
            "description": getattr(agent_class, "description", ""),
            "lane": getattr(agent_class, "lane", ""),
            "default_tier": getattr(agent_class, "default_tier", ""),
            "icon": getattr(agent_class, "icon", ""),
        }
        result.append(info)
    return result


def list_agents() -> list[str]:
    """列出所有已注册的 Agent"""
    return list(AGENT_REGISTRY.keys())
