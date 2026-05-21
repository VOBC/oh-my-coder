"""SecurityReviewerAgent 单元测试"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.base import AgentContext, AgentLane, AgentOutput, AgentStatus
from src.agents.security import SecurityReviewerAgent


@pytest.fixture
def agent():
    return SecurityReviewerAgent()


@pytest.fixture
def context(tmp_path):
    return AgentContext(
        project_path=tmp_path,
        task_description="security review",
        relevant_files=[],
    )


class TestSecurityReviewerAgentProps:
    def test_class_attributes(self, agent):
        assert agent.name == "security-reviewer"
        assert agent.lane == AgentLane.REVIEW
        assert agent.default_tier == "high"
        assert agent.icon == "🔒"
        assert agent.tools == ["file_read", "search"]

    def test_system_prompt(self, agent):
        prompt = agent.system_prompt
        assert "安全审查" in prompt
        assert "SQL" in prompt
        assert "XSS" in prompt


class TestPostProcess:
    def test_post_process(self, agent, context):
        out = agent._post_process("review result", context)
        assert isinstance(out, AgentOutput)
        assert out.agent_name == "security-reviewer"
        assert out.status == AgentStatus.COMPLETED
        assert out.result == "review result"
        assert len(out.recommendations) == 2


class TestRun:
    @pytest.mark.asyncio
    async def test_run_no_relevant_files(self, agent, context):
        context.relevant_files = []
        mock_response = MagicMock()
        mock_response.content = "safe"

        with patch.object(agent, "call_model", new_callable=AsyncMock, return_value=mock_response):
            result = await agent._run(context, [{"role": "user", "content": "check"}])

        assert result == "safe"

    @pytest.mark.asyncio
    async def test_run_with_relevant_files(self, agent, context, tmp_path):
        f = tmp_path / "app.py"
        f.write_text("query = 'SELECT * FROM users WHERE id=' + user_input", encoding="utf-8")
        context.relevant_files = [f]

        mock_response = MagicMock()
        mock_response.content = "SQL injection found"

        with patch.object(agent, "call_model", new_callable=AsyncMock, return_value=mock_response) as mock_call:
            result = await agent._run(context, [{"role": "user", "content": "check"}])

        assert result == "SQL injection found"
        # Verify prompt includes code content
        call_args = mock_call.call_args
        messages = call_args.kwargs["messages"]
        # Should have original prompt + code + security hint appended
        assert len(messages) >= 3

    @pytest.mark.asyncio
    async def test_run_file_read_error(self, agent, context, tmp_path):
        bad_file = tmp_path / "nonexistent.py"
        context.relevant_files = [bad_file]

        mock_response = MagicMock()
        mock_response.content = "no code to review"

        with patch.object(agent, "call_model", new_callable=AsyncMock, return_value=mock_response):
            result = await agent._run(context, [{"role": "user", "content": "check"}])

        assert result == "no code to review"

    @pytest.mark.asyncio
    async def test_run_max_10_files(self, agent, context, tmp_path):
        files = []
        for i in range(15):
            f = tmp_path / f"f{i}.py"
            f.write_text(f"# file {i}", encoding="utf-8")
            files.append(f)
        context.relevant_files = files

        mock_response = MagicMock()
        mock_response.content = "reviewed"

        with patch.object(agent, "call_model", new_callable=AsyncMock, return_value=mock_response) as mock_call:
            await agent._run(context, [{"role": "user", "content": "check"}])

        # Only first 10 files should be read
        messages = mock_call.call_args.kwargs["messages"]
        code_msg = [m for m in messages if "待审查代码" in m.content]
        # At least one code message was added
        assert len(code_msg) == 1
