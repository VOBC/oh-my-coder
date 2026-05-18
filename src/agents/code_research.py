# mypy: disable-error-code="abstract, arg-type, assignment, attr-defined, call-arg, call-overload, dict-item, func-returns-value, import-untyped, index, misc, no-any-return, no-redef, operator, override, return, return-value, syntax, union-attr, var-annotated"
"""

Code Research Agent - 代码研究智能体

职责：
1. 搜索公开代码库，获取参考实现
2. 查找 API 使用示例和最佳实践
3. 发现相关开源项目和库
4. 为代码编写提供外部参考

模型层级：MEDIUM（平衡质量与成本）

工作流程：
1. 解析研究目标（函数、模式、库）
2. 使用 Sourcegraph 搜索公开代码
3. 获取相关文件内容
4. 总结发现并提供建议
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from ..integrations.sourcegraph import SourcegraphClient
from .base import (
    AgentContext,
    AgentLane,
    AgentOutput,
    AgentStatus,
    BaseAgent,
    register_agent,
)


@dataclass
class ResearchTarget:
    """研究目标"""

    query: str  # 搜索关键词
    language: Optional[str] = None  # 目标语言
    context: Optional[str] = None  # 上下文（如特定框架）
    max_results: int = 10


@dataclass
class CodeExample:
    """代码示例"""

    repo: str
    file_path: str
    content: str
    language: str = ""
    source_url: str = ""
    relevance: float = 0.0  # 相关性评分


@dataclass
class ResearchResult:
    """研究结果"""

    target: ResearchTarget
    examples: list[CodeExample] = field(default_factory=list)
    repos: list[dict[str, Any]] = field(default_factory=list)
    summary: str = ""
    recommendations: list[str] = field(default_factory=list)


@register_agent
class CodeResearchAgent(BaseAgent):
    """
    代码研究 Agent

    特点：
    - 使用 Sourcegraph 搜索公开代码库
    - 无需 API Key，使用公开 streaming API
    - 为开发者提供参考实现和最佳实践
    """

    name = "code-research"
    description = "代码研究智能体 - 搜索公开代码库获取参考实现"
    lane = AgentLane.BUILD_ANALYSIS
    default_tier = "medium"
    icon = "🔎"
    tools = ["web_search", "web_fetch"]  # 可选的补充搜索

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._sg_client: Optional[SourcegraphClient] = None

    @property
    def sg_client(self) -> SourcegraphClient:
        """获取 Sourcegraph 客户端"""
        if self._sg_client is None:
            self._sg_client = SourcegraphClient()
        return self._sg_client

    @property
    def system_prompt(self) -> str:
        return """你是一个专业的代码研究智能体。

## 角色
你的职责是搜索公开代码库，为开发者提供参考实现和最佳实践。

## 能力
1. **代码搜索** - 使用 Sourcegraph 搜索 GitHub/GitLab 等公开代码
2. **示例发现** - 找到函数、API、模式的使用示例
3. **项目发现** - 发现相关的开源项目和库
4. **内容提取** - 获取相关文件内容进行分析

## 工作原则
1. **相关性优先** - 选择高质量、高相关性的结果
2. **多样性** - 提供不同风格和场景的实现
3. **可操作性** - 输出可直接使用的代码片段
4. **来源标注** - 标注代码来源，方便追溯

## 输出格式
你的输出应该包含：
1. 搜索结果摘要
2. 代码示例（带来源标注）
3. 相关项目推荐
4. 最佳实践建议

## 注意事项
- 不要直接复制受版权保护的代码
- 推荐使用 MIT/Apache 等宽松许可证的项目
- 注明代码来源和许可证信息
"""

    def search_code(
        self,
        query: str,
        language: Optional[str] = None,
        repo_filter: Optional[str] = None,
        limit: int = 10,
    ) -> list[CodeExample]:
        """
        搜索代码并获取示例

        Args:
            query: 搜索关键词
            language: 语言过滤
            repo_filter: 仓库过滤
            limit: 结果数量

        Returns:
            CodeExample 列表
        """
        result = self.sg_client.search(
            query=query,
            repo_filter=repo_filter,
            lang=language,
            limit=limit,
        )

        examples: list[CodeExample] = []

        for match in result.matches:
            # 尝试获取完整内容
            content = match.line_content
            if match.repo and match.file_path and len(content) < 200:
                # 获取更多上下文
                file_content = self.sg_client.get_file(match.repo, match.file_path)
                if file_content:
                    content = file_content.content

            examples.append(
                CodeExample(
                    repo=match.repo,
                    file_path=match.file_path,
                    content=content,
                    language=match.language,
                    source_url=match.url,
                    relevance=1.0 if match.repository_stars > 1000 else 0.5,
                )
            )

        return examples

    def find_repos(
        self,
        query: str,
        language: Optional[str] = None,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """
        搜索相关仓库

        Args:
            query: 搜索关键词
            language: 语言过滤
            limit: 结果数量

        Returns:
            仓库信息列表
        """
        search_query = query
        if language:
            search_query = f"{query} lang:{language}"

        repos = self.sg_client.list_repos(search_query, limit=limit)
        return [r.to_dict() for r in repos]

    def research(
        self,
        target: ResearchTarget,
    ) -> ResearchResult:
        """
        执行代码研究

        Args:
            target: 研究目标

        Returns:
            ResearchResult
        """
        # 搜索代码示例
        examples = self.search_code(
            query=target.query,
            language=target.language,
            limit=target.max_results,
        )

        # 搜索相关仓库
        repos = self.find_repos(
            query=target.query,
            language=target.language,
            limit=5,
        )

        # 生成摘要
        summary = self._generate_summary(target, examples, repos)

        # 生成建议
        recommendations = self._generate_recommendations(target, examples, repos)

        return ResearchResult(
            target=target,
            examples=examples,
            repos=repos,
            summary=summary,
            recommendations=recommendations,
        )

    def _generate_summary(
        self,
        target: ResearchTarget,
        examples: list[CodeExample],
        repos: list[dict[str, Any]],
    ) -> str:
        """生成研究摘要"""
        lines = [f"## 研究结果: {target.query}\n"]

        if examples:
            lines.append(f"找到 {len(examples)} 个代码示例:")
            for i, ex in enumerate(examples[:5], 1):
                lines.append(f"  {i}. [{ex.repo}] {ex.file_path}")
        else:
            lines.append("未找到匹配的代码示例")

        if repos:
            lines.append(f"\n发现 {len(repos)} 个相关项目:")
            for repo in repos[:3]:
                lines.append(f"  - {repo.get('name', '')} (⭐{repo.get('stars', 0)})")

        return "\n".join(lines)

    def _generate_recommendations(
        self,
        target: ResearchTarget,
        examples: list[CodeExample],
        repos: list[dict[str, Any]],
    ) -> list[str]:
        """生成建议"""
        recs: list[str] = []

        if examples:
            # 按相关性排序
            sorted_examples = sorted(examples, key=lambda x: x.relevance, reverse=True)
            top = sorted_examples[0]
            recs.append(f"推荐参考: {top.repo}/{top.file_path}")

        if repos:
            top_repo = max(repos, key=lambda x: x.get("stars", 0))
            recs.append(f"推荐项目: {top_repo.get('name', '')}")

        if target.language:
            recs.append(f"建议使用 {target.language} 官方文档作为主要参考")

        return recs

    async def execute(self, context: AgentContext, **kwargs) -> AgentOutput:
        """
        执行代码研究任务

        从 context.task 中解析研究目标，或使用 kwargs 中的参数。
        """
        # 解析研究目标
        query = kwargs.get("query") or context.metadata.get("query", "")
        language = kwargs.get("language") or context.metadata.get("language")
        max_results = kwargs.get("max_results", 10)

        if not query:
            # 尝试从 task 提取
            task = context.metadata.get("task", "")
            if task:
                # 简单提取关键词
                query = task

        if not query:
            return AgentOutput(agent_name=self.name,
                status=AgentStatus.FAILED,
                summary="未提供搜索关键词",
                content="请在 context.metadata 或 kwargs 中提供 query 参数",
            )

        # 构建研究目标
        target = ResearchTarget(
            query=query,
            language=language,
            context=context.metadata.get("context"),
            max_results=max_results,
        )

        # 执行研究
        try:
            result = self.research(target)

            # 格式化输出
            output_lines = [
                result.summary,
                "",
                "## 代码示例",
                "",
            ]

            for i, ex in enumerate(result.examples[:5], 1):
                output_lines.append(f"### 示例 {i}: {ex.repo}")
                output_lines.append(f"文件: {ex.file_path}")
                output_lines.append(f"来源: {ex.source_url}")
                output_lines.append("")
                output_lines.append(f"```{ex.language}")
                # 只显示前 50 行
                content_lines = ex.content.splitlines()[:50]
                output_lines.extend(content_lines)
                if len(ex.content.splitlines()) > 50:
                    output_lines.append("... (已截断)")
                output_lines.append("```")
                output_lines.append("")

            if result.recommendations:
                output_lines.append("## 建议")
                output_lines.append("")
                for rec in result.recommendations:
                    output_lines.append(f"- {rec}")

            return AgentOutput(agent_name=self.name,
                status=AgentStatus.COMPLETED,
                summary=f"找到 {len(result.examples)} 个代码示例, {len(result.repos)} 个相关项目",
                content="\n".join(output_lines),
                artifacts={
                    "examples": [ex.to_dict() for ex in result.examples],
                    "repos": result.repos,
                    "recommendations": result.recommendations,
                },
            )

        except Exception as e:
            return AgentOutput(agent_name=self.name,
                status=AgentStatus.FAILED,
                summary="研究失败",
                content=f"错误: {e}",
            )

    def cleanup(self) -> None:
        """清理资源"""
        if self._sg_client:
            self._sg_client.close()
            self._sg_client = None


# 便捷函数
def research_code(
    query: str,
    language: Optional[str] = None,
    limit: int = 10,
) -> ResearchResult:
    """
    快捷代码研究函数

    示例:
        result = research_code("http server", language="go")
        for ex in result.examples:
            print(f"{ex.repo}: {ex.file_path}")
    """
    agent = CodeResearchAgent()
    target = ResearchTarget(query=query, language=language, max_results=limit)
    try:
        return agent.research(target)
    finally:
        agent.cleanup()
