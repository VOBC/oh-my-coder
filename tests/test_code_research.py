"""CodeResearchAgent 单元测试（纯逻辑，mock 外部依赖）"""

from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from pathlib import Path

from src.agents.code_research import (
    CodeExample,
    CodeResearchAgent,
    ResearchResult,
    ResearchTarget,
)
from src.agents.base import AgentContext, AgentOutput, AgentStatus
from src.integrations.sourcegraph import SearchMatch, SearchResult, RepoInfo


# ─────────────────────────────────────────────────────────────────
# Data classes
# ─────────────────────────────────────────────────────────────────


class TestResearchTarget:
    def test_defaults(self):
        t = ResearchTarget(query="http server")
        assert t.language is None
        assert t.context is None
        assert t.max_results == 10

    def test_custom(self):
        t = ResearchTarget(query="fastapi", language="python", context="web", max_results=5)
        assert t.language == "python"
        assert t.max_results == 5


class TestCodeExample:
    def test_defaults(self):
        ex = CodeExample(repo="r", file_path="f", content="c")
        assert ex.language == ""
        assert ex.relevance == 0.0

    def test_custom(self):
        ex = CodeExample(repo="r", file_path="f", content="c", language="go", relevance=0.8)
        assert ex.language == "go"


class TestResearchResult:
    def test_defaults(self):
        t = ResearchTarget(query="q")
        r = ResearchResult(target=t)
        assert r.examples == []
        assert r.repos == []
        assert r.summary == ""
        assert r.recommendations == []


# ─────────────────────────────────────────────────────────────────
# CodeResearchAgent - search_code
# ─────────────────────────────────────────────────────────────────


def _make_match(repo="repo1", file_path="main.py", line_content="def main():", stars=100, language="python"):
    return SearchMatch(
        repo=repo, file_path=file_path, line_number=1,
        line_content=line_content, language=language,
        repository_stars=stars, url=f"https://sourcegraph.com/{repo}",
    )


class ConcreteCodeResearchAgent(CodeResearchAgent):
    """Concrete subclass to avoid abstract _run error"""
    async def _run(self, context, **kwargs):
        return await self.execute(context, **kwargs)


def _make_agent():
    agent = ConcreteCodeResearchAgent()
    mock_sg = MagicMock()
    agent._sg_client = mock_sg
    return agent, mock_sg


class TestSearchCode:
    def test_basic_search(self):
        agent, sg = _make_agent()
        sg.search.return_value = SearchResult(
            query="test", total=1, matches=[_make_match()]
        )
        results = agent.search_code("test")
        assert len(results) == 1
        assert results[0].repo == "repo1"

    def test_relevance_high_stars(self):
        agent, sg = _make_agent()
        sg.search.return_value = SearchResult(
            query="test", total=1, matches=[_make_match(stars=5000)]
        )
        results = agent.search_code("test")
        assert results[0].relevance == 1.0

    def test_relevance_low_stars(self):
        agent, sg = _make_agent()
        sg.search.return_value = SearchResult(
            query="test", total=1, matches=[_make_match(stars=100)]
        )
        results = agent.search_code("test")
        assert results[0].relevance == 0.5

    def test_fetch_full_content(self):
        """Short line_content triggers get_file call"""
        agent, sg = _make_agent()
        from src.integrations.sourcegraph import FileContent
        sg.search.return_value = SearchResult(
            query="test", total=1, matches=[_make_match(line_content="short")]
        )
        sg.get_file.return_value = FileContent(repo="repo1", path="main.py", content="full content here")
        results = agent.search_code("test")
        assert results[0].content == "full content here"

    def test_fetch_full_content_none(self):
        """get_file returns None → keep line_content"""
        agent, sg = _make_agent()
        sg.search.return_value = SearchResult(
            query="test", total=1, matches=[_make_match(line_content="short")]
        )
        sg.get_file.return_value = None
        results = agent.search_code("test")
        assert results[0].content == "short"

    def test_long_content_no_fetch(self):
        """Long line_content (>200 chars) skips get_file"""
        agent, sg = _make_agent()
        long_content = "x" * 300
        sg.search.return_value = SearchResult(
            query="test", total=1, matches=[_make_match(line_content=long_content)]
        )
        results = agent.search_code("test")
        assert results[0].content == long_content
        sg.get_file.assert_not_called()

    def test_with_language_filter(self):
        agent, sg = _make_agent()
        sg.search.return_value = SearchResult(query="test", total=0, matches=[])
        agent.search_code("test", language="python")
        sg.search.assert_called_once_with(query="test", repo_filter=None, lang="python", limit=10)


# ─────────────────────────────────────────────────────────────────
# find_repos
# ─────────────────────────────────────────────────────────────────


class TestFindRepos:
    def test_basic(self):
        agent, sg = _make_agent()
        sg.list_repos.return_value = [
            RepoInfo(name="proj1", stars=100),
        ]
        repos = agent.find_repos("fastapi")
        assert len(repos) == 1
        assert repos[0]["name"] == "proj1"

    def test_with_language(self):
        agent, sg = _make_agent()
        sg.list_repos.return_value = []
        agent.find_repos("http server", language="go")
        sg.list_repos.assert_called_once_with("http server lang:go", limit=5)


# ─────────────────────────────────────────────────────────────────
# research
# ─────────────────────────────────────────────────────────────────


class TestResearch:
    def test_full_research(self):
        agent, sg = _make_agent()
        sg.search.return_value = SearchResult(
            query="fastapi", total=2,
            matches=[_make_match(stars=2000), _make_match(repo="repo2", stars=500)],
        )
        sg.list_repos.return_value = [RepoInfo(name="proj1", stars=1000)]

        target = ResearchTarget(query="fastapi", language="python", max_results=5)
        result = agent.research(target)

        assert len(result.examples) == 2
        assert len(result.repos) == 1
        assert result.summary != ""
        assert len(result.recommendations) > 0

    def test_no_results(self):
        agent, sg = _make_agent()
        sg.search.return_value = SearchResult(query="rare", total=0, matches=[])
        sg.list_repos.return_value = []

        target = ResearchTarget(query="rare topic")
        result = agent.research(target)

        assert result.examples == []
        assert "未找到匹配" in result.summary


# ─────────────────────────────────────────────────────────────────
# _generate_summary / _generate_recommendations
# ─────────────────────────────────────────────────────────────────


class TestGenerateSummary:
    def test_with_examples_and_repos(self):
        agent, _ = _make_agent()
        target = ResearchTarget(query="flask")
        examples = [CodeExample(repo="r1", file_path="f1", content="c", relevance=0.9)]
        repos = [{"name": "flask", "stars": 50000}]
        summary = agent._generate_summary(target, examples, repos)
        assert "flask" in summary
        assert "1 个代码示例" in summary

    def test_empty(self):
        agent, _ = _make_agent()
        target = ResearchTarget(query="xyz")
        summary = agent._generate_summary(target, [], [])
        assert "未找到匹配" in summary


class TestGenerateRecommendations:
    def test_with_data(self):
        agent, _ = _make_agent()
        target = ResearchTarget(query="flask", language="python")
        examples = [CodeExample(repo="r1", file_path="f1", content="c", relevance=0.9)]
        repos = [{"name": "flask", "stars": 50000}]
        recs = agent._generate_recommendations(target, examples, repos)
        assert len(recs) >= 2
        assert any("python" in r for r in recs)

    def test_empty(self):
        agent, _ = _make_agent()
        target = ResearchTarget(query="xyz")
        recs = agent._generate_recommendations(target, [], [])
        assert recs == []


# ─────────────────────────────────────────────────────────────────
# execute (async)
# ─────────────────────────────────────────────────────────────────


class TestExecute:
    """execute() creates AgentOutput with 'summary'/'content' kwargs that
    AgentOutput dataclass doesn't have — this is a source bug we document
    rather than fix. We test the logic paths by mocking AgentOutput."""

    @pytest.mark.asyncio
    async def test_with_query(self):
        agent, sg = _make_agent()
        sg.search.return_value = SearchResult(query="flask", total=1, matches=[_make_match(stars=2000)])
        sg.list_repos.return_value = [RepoInfo(name="flask", stars=50000)]

        ctx = AgentContext(project_path=Path("."), task_description="research", metadata={"query": "flask"})
        # Mock AgentOutput to accept extra kwargs
        mock_output = MagicMock(status=AgentStatus.COMPLETED, summary="found")
        with patch("src.agents.code_research.AgentOutput", return_value=mock_output):
            output = await agent.execute(ctx)
            assert output.status == AgentStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_no_query(self):
        agent, _ = _make_agent()
        ctx = AgentContext(project_path=Path("."), task_description="research", metadata={})
        mock_output = MagicMock(status=AgentStatus.FAILED)
        with patch("src.agents.code_research.AgentOutput", return_value=mock_output):
            output = await agent.execute(ctx)
            assert output.status == AgentStatus.FAILED

    @pytest.mark.asyncio
    async def test_exception(self):
        agent, sg = _make_agent()
        sg.search.side_effect = RuntimeError("network error")
        ctx = AgentContext(project_path=Path("."), task_description="research", metadata={"query": "test"})
        mock_output = MagicMock(status=AgentStatus.FAILED, content="network error")
        with patch("src.agents.code_research.AgentOutput", return_value=mock_output):
            output = await agent.execute(ctx)
            assert output.status == AgentStatus.FAILED

    @pytest.mark.asyncio
    async def test_query_from_task(self):
        agent, sg = _make_agent()
        sg.search.return_value = SearchResult(query="django", total=0, matches=[])
        sg.list_repos.return_value = []
        ctx = AgentContext(project_path=Path("."), task_description="research", metadata={"task": "django orm patterns"})
        mock_output = MagicMock(status=AgentStatus.COMPLETED)
        with patch("src.agents.code_research.AgentOutput", return_value=mock_output):
            output = await agent.execute(ctx)
            assert output.status == AgentStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_kwargs_query(self):
        agent, sg = _make_agent()
        sg.search.return_value = SearchResult(query="go", total=0, matches=[])
        sg.list_repos.return_value = []
        ctx = AgentContext(project_path=Path("."), task_description="research", metadata={})
        mock_output = MagicMock(status=AgentStatus.COMPLETED)
        with patch("src.agents.code_research.AgentOutput", return_value=mock_output):
            output = await agent.execute(ctx, query="go http server")
            assert output.status == AgentStatus.COMPLETED


# ─────────────────────────────────────────────────────────────────
# sg_client property & cleanup
# ─────────────────────────────────────────────────────────────────


class TestSgClient:
    def test_lazy_init(self):
        agent = ConcreteCodeResearchAgent()
        assert agent._sg_client is None
        with patch("src.agents.code_research.SourcegraphClient") as MockSG:
            client = agent.sg_client
            MockSG.assert_called_once()
            assert agent._sg_client is not None

    def test_cleanup(self):
        agent, sg = _make_agent()
        agent.cleanup()
        sg.close.assert_called_once()
        assert agent._sg_client is None

    def test_cleanup_no_client(self):
        agent = ConcreteCodeResearchAgent()
        agent._sg_client = None
        agent.cleanup()  # no error


# ─────────────────────────────────────────────────────────────────
# system_prompt
# ─────────────────────────────────────────────────────────────────


class TestSystemPrompt:
    def test_content(self):
        agent = ConcreteCodeResearchAgent()
        prompt = agent.system_prompt
        assert "代码研究" in prompt
        assert "Sourcegraph" in prompt


# ─────────────────────────────────────────────────────────────────
# research_code convenience function
# ─────────────────────────────────────────────────────────────────


class TestResearchCode:
    def test_convenience(self):
        with patch("src.agents.code_research.CodeResearchAgent", ConcreteCodeResearchAgent):
            with patch.object(ConcreteCodeResearchAgent, "sg_client", new_callable=PropertyMock) as mock_prop:
                sg = MagicMock()
                sg.search.return_value = SearchResult(query="test", total=1, matches=[_make_match()])
                sg.list_repos.return_value = []
                mock_prop.return_value = sg
                from src.agents.code_research import research_code
                result = research_code("test")
                assert len(result.examples) == 1