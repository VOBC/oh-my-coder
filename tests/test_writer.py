"""Tests for WriterAgent"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.base import AgentContext, AgentOutput, AgentStatus
from src.agents.writer import WriterAgent


@pytest.fixture
def writer_agent():
    """Create a WriterAgent instance."""
    return WriterAgent()


@pytest.fixture
def agent_context(tmp_path):
    """Create an AgentContext for testing."""
    return AgentContext(
        task_description="Test task",
        project_path=tmp_path,
    )


class TestWriterAgentInit:
    """Test WriterAgent initialization and class attributes."""

    def test_class_attributes(self):
        """Test class-level attributes."""
        from src.agents.base import AgentLane

        assert WriterAgent.name == "writer"
        assert WriterAgent.description == "文档编写智能体 - 技术文档和 API 文档生成"
        assert WriterAgent.lane == AgentLane.DOMAIN
        assert WriterAgent.default_tier == "low"
        assert WriterAgent.icon == "📝"
        assert WriterAgent.tools == ["file_read", "file_write"]

    def test_instantiation(self, writer_agent):
        """Test that WriterAgent can be instantiated."""
        assert writer_agent is not None
        assert writer_agent.name == "writer"

    def test_system_prompt_property(self, writer_agent):
        """Test the system_prompt property returns expected content."""
        prompt = writer_agent.system_prompt
        assert isinstance(prompt, str)
        assert "技术文档撰写者" in prompt
        assert "API 文档" in prompt
        assert "README" in prompt


class TestWriterAgentRun:
    """Test WriterAgent._run() method."""

    @pytest.mark.asyncio
    async def test_run_basic(self, writer_agent, agent_context, tmp_path):
        """Test basic _run() execution."""
        # Create a README.md to test the readme exists path
        readme = tmp_path / "README.md"
        readme.write_text("# Test Project\n\nThis is a test.", encoding="utf-8")

        prompt = [{"role": "user", "content": "Write docs"}]

        # Mock the call_model method
        mock_response = MagicMock()
        mock_response.content = "# Generated Documentation\n\nContent here."

        with patch.object(writer_agent, "call_model", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_response
            result = await writer_agent._run(agent_context, prompt)

        assert result == "# Generated Documentation\n\nContent here."
        mock_call.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_with_doc_type_metadata(self, writer_agent, agent_context, tmp_path):
        """Test _run() with custom doc_type in metadata."""
        agent_context.metadata["doc_type"] = "api"

        prompt = [{"role": "user", "content": "Write API docs"}]

        mock_response = MagicMock()
        mock_response.content = "# API Documentation"

        with patch.object(writer_agent, "call_model", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_response
            result = await writer_agent._run(agent_context, prompt)

        assert result == "# API Documentation"
        # Verify the prompt contains the doc_type
        call_args = mock_call.call_args
        messages_arg = call_args[1].get("messages") or call_args[0][1]
        # Check that the doc_hint was added with the correct doc_type
        assert any("api" in msg.content.lower() for msg in messages_arg if hasattr(msg, 'content'))

    @pytest.mark.asyncio
    async def test_run_with_previous_executor_output(self, writer_agent, agent_context):
        """Test _run() when executor output exists in previous_outputs."""
        agent_context.previous_outputs["executor"] = AgentOutput(
            agent_name="executor",
            status=AgentStatus.COMPLETED,
            result="def hello():\n    return 'world'",
        )

        prompt = [{"role": "user", "content": "Write docs"}]

        mock_response = MagicMock()
        mock_response.content = "# Docs with code"

        with patch.object(writer_agent, "call_model", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_response
            result = await writer_agent._run(agent_context, prompt)

        assert result == "# Docs with code"
        # Verify that the executor output was added to prompt
        call_args = mock_call.call_args
        messages_arg = call_args[1].get("messages") or call_args[0][1]
        assert any("hello" in str(msg) for msg in messages_arg)

    @pytest.mark.asyncio
    async def test_run_without_readme(self, writer_agent, agent_context):
        """Test _run() when README.md doesn't exist."""
        # Don't create README.md - agent_context has tmp_path as project_path
        assert not (agent_context.project_path / "README.md").exists()

        prompt = [{"role": "user", "content": "Write docs"}]

        mock_response = MagicMock()
        mock_response.content = "# New Docs"

        with patch.object(writer_agent, "call_model", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_response
            result = await writer_agent._run(agent_context, prompt)

        assert result == "# New Docs"

    @pytest.mark.asyncio
    async def test_run_calls_model_with_correct_params(self, writer_agent, agent_context):
        """Test that _run() calls call_model with correct parameters."""
        prompt = [{"role": "user", "content": "Test"}]

        mock_response = MagicMock()
        mock_response.content = "Result"

        with patch.object(writer_agent, "call_model", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_response
            await writer_agent._run(agent_context, prompt)

        # Verify call_model was called with correct task_type and complexity
        call_kwargs = mock_call.call_args.kwargs
        # task_type can be either string or enum, check accordingly
        task_type = call_kwargs["task_type"]
        if hasattr(task_type, "value"):
            assert task_type.value == "simple_qa"  # TaskType.SIMPLE_QA
        else:
            assert task_type == "simple_qa"
        assert call_kwargs["complexity"] == "low"


class TestWriterAgentPostProcess:
    """Test WriterAgent._post_process() method."""

    def test_post_process_basic(self, writer_agent, agent_context):
        """Test basic _post_process() behavior."""
        result = "# Documentation\n\nContent"
        output = writer_agent._post_process(result, agent_context)

        assert isinstance(output, AgentOutput)
        assert output.agent_name == "writer"
        assert output.status == AgentStatus.COMPLETED
        assert output.result == result
        assert len(output.recommendations) == 2
        assert "文档保存" in output.recommendations[0]
        assert "定期更新" in output.recommendations[1]

    def test_post_process_empty_result(self, writer_agent, agent_context):
        """Test _post_process() with empty result."""
        result = ""
        output = writer_agent._post_process(result, agent_context)

        assert output.result == ""
        assert output.status == AgentStatus.COMPLETED

    def test_post_process_long_result(self, writer_agent, agent_context):
        """Test _post_process() with long documentation."""
        result = "# Title\n\n" + "Content " * 1000
        output = writer_agent._post_process(result, agent_context)

        assert output.result == result
        assert output.status == AgentStatus.COMPLETED


class TestWriterAgentIntegration:
    """Integration tests for WriterAgent."""

    @pytest.mark.asyncio
    async def test_full_flow(self, writer_agent, agent_context, tmp_path):
        """Test the full flow: _run() -> _post_process()."""
        # Create README.md
        readme = tmp_path / "README.md"
        readme.write_text("# Existing Project\n\nOld content.", encoding="utf-8")

        # Prepare context
        agent_context.metadata["doc_type"] = "readme"

        # Mock the model response
        mock_response = MagicMock()
        mock_response.content = "# Updated README\n\nNew content."

        prompt = [{"role": "user", "content": "Update README"}]

        with patch.object(writer_agent, "call_model", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_response
            result = await writer_agent._run(agent_context, prompt)

        # Post-process
        output = writer_agent._post_process(result, agent_context)

        assert output.status == AgentStatus.COMPLETED
        assert "Updated README" in output.result
        assert len(output.recommendations) > 0
