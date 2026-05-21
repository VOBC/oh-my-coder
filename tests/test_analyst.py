"""Tests for AnalystAgent."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.analyst import AnalysisResult, AnalystAgent, Requirement
from src.agents.base import AgentContext, AgentLane, AgentOutput, AgentStatus


@pytest.fixture
def agent():
    router = MagicMock()
    return AnalystAgent(router)


@pytest.fixture
def mock_context():
    ctx = MagicMock(spec=AgentContext)
    ctx.task_description = "Analyze requirements"
    ctx.previous_outputs = {}
    ctx.metadata = {}
    return ctx


class TestRequirement:
    def test_creation(self):
        r = Requirement(
            id="F1",
            description="User login",
            priority="high",
            category="functional",
            dependencies=["DB"],
            acceptance_criteria=["User can login"],
        )
        assert r.id == "F1"
        assert r.priority == "high"
        assert len(r.acceptance_criteria) == 1


class TestAnalysisResult:
    def test_creation(self):
        ar = AnalysisResult(
            summary="Summary",
            requirements=[],
            questions=["Q1?"],
            constraints=["C1"],
            risks=["R1"],
        )
        assert ar.summary == "Summary"
        assert len(ar.questions) == 1
        assert len(ar.risks) == 1


class TestAnalystAgentAttributes:
    def test_name(self, agent):
        assert agent.name == "analyst"

    def test_description(self, agent):
        assert "需求" in agent.description

    def test_lane(self, agent):
        assert agent.lane == AgentLane.BUILD_ANALYSIS

    def test_default_tier(self, agent):
        assert agent.default_tier == "high"

    def test_icon(self, agent):
        assert agent.icon == "📊"

    def test_tools(self, agent):
        assert "file_read" in agent.tools
        assert "search" in agent.tools

    def test_sourcegraph_default_off(self, agent):
        assert agent.use_sourcegraph is False

    def test_sourcegraph_limit(self, agent):
        assert agent.sourcegraph_limit == 10


class TestSystemPrompt:
    def test_contains_analyst_role(self, agent):
        prompt = agent.system_prompt
        assert "需求分析" in prompt

    def test_contains_socratic(self, agent):
        prompt = agent.system_prompt
        assert "苏格拉底" in prompt

    def test_contains_output_format(self, agent):
        prompt = agent.system_prompt
        assert "功能需求" in prompt


class TestSearchCode:
    def test_search_code(self, agent):
        mock_result = MagicMock()
        mock_result.total_matches = 5
        with patch("src.agents.analyst.search", return_value=mock_result) as mock_search:
            result = agent.search_code("jwt auth", language="python")
        mock_search.assert_called_once_with(
            query="jwt auth", language="python", repo=None, limit=10
        )
        assert result.total_matches == 5

    def test_search_code_with_repo(self, agent):
        mock_result = MagicMock()
        with patch("src.agents.analyst.search", return_value=mock_result) as mock_search:
            agent.search_code("auth", repo="org/repo")
        mock_search.assert_called_once_with(
            query="auth", language=None, repo="org/repo", limit=10
        )


class TestPostProcess:
    def test_returns_completed(self, agent, mock_context):
        result = agent._post_process("Analysis result", mock_context)
        assert isinstance(result, AgentOutput)
        assert result.status == AgentStatus.COMPLETED
        assert result.agent_name == "analyst"
        assert result.next_agent == "planner"
        assert len(result.recommendations) == 2


class TestRun:
    @pytest.mark.asyncio
    async def test_run_basic(self, agent, mock_context):
        mock_response = MagicMock()
        mock_response.content = "Analysis result"
        agent.call_model = AsyncMock(return_value=mock_response)

        result = await agent._run(mock_context, [{"role": "user", "content": "test"}])
        assert result == "Analysis result"
        agent.call_model.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_with_explore_output(self, agent, mock_context):
        mock_context.previous_outputs = {
            "explore": MagicMock(result="Project structure: ...")
        }
        mock_response = MagicMock()
        mock_response.content = "Analysis"
        agent.call_model = AsyncMock(return_value=mock_response)

        prompt = [{"role": "user", "content": "test"}]
        await agent._run(mock_context, prompt)
        # explore result should be appended
        assert any("项目探索" in str(p) for p in prompt)

    @pytest.mark.asyncio
    async def test_run_with_sourcegraph(self, agent, mock_context):
        agent.use_sourcegraph = True
        mock_sr = MagicMock()
        mock_sr.total_matches = 3
        mock_sr.format_code.return_value = "code context"

        with patch.object(agent, "search_code", return_value=mock_sr):
            mock_response = MagicMock()
            mock_response.content = "Analysis"
            agent.call_model = AsyncMock(return_value=mock_response)

            prompt = [{"role": "user", "content": "test"}]
            await agent._run(
                mock_context, prompt,
                search_query="jwt",
                search_language="python",
            )
        # sourcegraph result should be appended
        assert any("Sourcegraph" in str(p) for p in prompt)

    @pytest.mark.asyncio
    async def test_run_sourcegraph_no_matches(self, agent, mock_context):
        agent.use_sourcegraph = True
        mock_sr = MagicMock()
        mock_sr.total_matches = 0
        mock_sr.warnings = ["Rate limit"]

        with patch.object(agent, "search_code", return_value=mock_sr):
            mock_response = MagicMock()
            mock_response.content = "Analysis"
            agent.call_model = AsyncMock(return_value=mock_response)

            prompt = [{"role": "user", "content": "test"}]
            await agent._run(
                mock_context, prompt,
                search_query="nonexistent",
            )
        # warnings stored in metadata
        assert mock_context.metadata.get("sourcegraph_warnings") == ["Rate limit"]

    @pytest.mark.asyncio
    async def test_run_sourcegraph_no_query(self, agent, mock_context):
        agent.use_sourcegraph = True
        mock_response = MagicMock()
        mock_response.content = "Analysis"
        agent.call_model = AsyncMock(return_value=mock_response)

        prompt = [{"role": "user", "content": "test"}]
        await agent._run(mock_context, prompt)
        # no search_query kwarg -> no sourcegraph call
        agent.call_model.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_appends_analysis_hint(self, agent, mock_context):
        mock_response = MagicMock()
        mock_response.content = "Result"
        agent.call_model = AsyncMock(return_value=mock_response)

        prompt = [{"role": "user", "content": "test"}]
        await agent._run(mock_context, prompt)
        assert any("需求分析" in str(p) for p in prompt)
