"""
Analyst Agent - 需求分析智能体

职责：
1. 深度理解用户需求
2. 发现隐藏约束和边界情况
3. 澄清模糊需求
4. 生成结构化需求文档

模型层级：HIGH（深度推理，对应 opus）

工作流程：
1. 分析用户输入
2. 识别关键需求点
3. 发现潜在问题
4. 提出澄清问题
5. 生成需求文档
"""

from dataclasses import dataclass
from typing import Optional

from ..core.router import TaskType
from ..tools.sourcegraph import SearchResult, search
from .base import (
    AgentContext,
    AgentLane,
    AgentOutput,
    AgentStatus,
    BaseAgent,
    register_agent,
)


@dataclass
class Requirement:
    """需求项"""

    id: str
    description: str
    priority: str  # high, medium, low
    category: str  # functional, non-functional, constraint
    dependencies: list[str]
    acceptance_criteria: list[str]


@dataclass
class AnalysisResult:
    """分析结果"""

    summary: str
    requirements: list[Requirement]
    questions: list[str]  # 需要澄清的问题
    constraints: list[str]  # 发现的约束
    risks: list[str]  # 潜在风险


@register_agent
class AnalystAgent(BaseAgent):
    """
    需求分析 Agent

    特点：
    - 使用 HIGH tier 模型（深度推理）
    - 苏格拉底式提问，澄清需求
    - 输出结构化需求文档
    - 可选 Sourcegraph 代码搜索增强
    """

    name = "analyst"
    description = "需求分析智能体 - 深度理解需求并发现隐藏约束"
    lane = AgentLane.BUILD_ANALYSIS
    default_tier = "high"
    icon = "📊"
    tools = ["file_read", "search", "sourcegraph"]

    # Sourcegraph 配置
    use_sourcegraph: bool = False
    sourcegraph_limit: int = 10

    def search_code(
        self,
        query: str,
        language: Optional[str] = None,  # noqa: UP045
        repo: Optional[str] = None,  # noqa: UP045
    ) -> SearchResult:
        """
        搜索公开代码库（通过 Sourcegraph）

        Args:
            query: 搜索关键词或 Sourcegraph 查询语法
            language: 语言过滤（如 rust/python/go）
            repo: 仓库过滤（支持 glob 模式）

        Returns:
            SearchResult: 搜索结果
        """
        return search(
            query=query,
            language=language,
            repo=repo,
            limit=self.sourcegraph_limit,
        )

    @property
    def system_prompt(self) -> str:
        return """你是一个资深的需求分析师。

## 角色
你的职责是深入理解用户需求，发现隐藏的约束和边界情况，确保开发团队有清晰的方向。

## 能力
1. 需求提取 - 从模糊描述中提取具体需求
2. 约束发现 - 识别技术、时间、资源约束
3. 风险识别 - 发现潜在的坑和风险点
4. 苏格拉底式提问 - 通过提问澄清需求
5. 代码搜索 - 通过 Sourcegraph 搜索公开代码库，参考已有实现

## 工作原则
1. **不要猜测** - 有疑问就提问，不要假设
2. **结构化输出** - 使用 Markdown 和表格组织信息
3. **优先级明确** - 区分必须、应该、可以
4. **可验证性** - 每个需求都有验收标准
5. **参考实现** - 搜索公开代码库，了解业界最佳实践

## 输出格式

### 1. 需求摘要
用 2-3 句话概括核心需求

### 2. 功能需求
| ID | 描述 | 优先级 | 验收标准 |
|----|------|--------|----------|
| F1 | ... | high | ... |

### 3. 非功能需求
| ID | 描述 | 类型 | 约束 |
|----|------|------|------|
| NF1 | ... | 性能 | ... |

### 4. 约束条件
- 技术约束：...
- 时间约束：...
- 资源约束：...

### 5. 需要澄清的问题
1. ...
2. ...

### 6. 风险提示
- ⚠️ ...
- ⚠️ ...

### 7. 下一步建议
- ...
"""

    async def _run(
        self, context: AgentContext, prompt: list[dict[str, str]], **kwargs
    ) -> str:
        """
        执行需求分析

        步骤：
        1. 分析用户输入
        2. 结合项目上下文
        3. 可选：搜索相关代码（Sourcegraph）
        4. 调用模型深度分析
        """
        # 添加项目上下文
        if context.previous_outputs.get("explore"):
            explore_result = context.previous_outputs["explore"].result
            prompt.append(
                {"role": "user", "content": f"## 项目探索结果\n\n{explore_result}"}
            )

        # Sourcegraph 代码搜索增强（可选）
        if self.use_sourcegraph and kwargs.get("search_query"):
            search_query = kwargs["search_query"]
            search_lang = kwargs.get("search_language")
            search_repo = kwargs.get("search_repo")

            result = self.search_code(
                search_query, language=search_lang, repo=search_repo
            )

            if result.total_matches > 0:
                code_context = result.format_code(limit=5)
                prompt.append(
                    {
                        "role": "user",
                        "content": f"## 相关代码参考（Sourcegraph 搜索）\n\n{code_context}",
                    }
                )
            elif result.warnings:
                # 记录警告但不中断
                context.metadata["sourcegraph_warnings"] = result.warnings

        # 添加分析提示
        analysis_hint = """

请基于以上信息，进行需求分析。特别注意：
1. 是否有模糊或矛盾的需求？
2. 是否有隐藏的技术约束？
3. 是否有潜在的性能、安全问题？
4. 需要哪些额外的信息？
"""
        prompt.append({"role": "user", "content": analysis_hint})

        # 调用模型
        from ..models.base import Message

        messages = [Message(role=msg["role"], content=msg["content"]) for msg in prompt]

        response = await self.call_model(
            task_type=TaskType.ARCHITECTURE,  # 使用 HIGH tier
            messages=messages,
            complexity="high",
        )

        return response.content

    def _post_process(
        self,
        result: str,
        context: AgentContext,
    ) -> AgentOutput:
        """后处理 - 提取关键信息"""
        # TODO: 使用正则或模型提取结构化需求

        return AgentOutput(
            agent_name=self.name,
            status=AgentStatus.COMPLETED,
            result=result,
            recommendations=[
                "使用 planner Agent 制定执行计划",
                "使用 architect Agent 设计系统架构",
            ],
            next_agent="planner",
        )
