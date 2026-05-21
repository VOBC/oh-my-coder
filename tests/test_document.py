"""DocumentAgent 单元测试（纯逻辑，不调 API）"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from src.agents.base import AgentContext, AgentOutput, AgentStatus
from src.agents.document import DocumentAgent


def _make_context(**overrides):
    defaults = dict(
        task_description="write doc",
        project_path=None,
        metadata={},
        previous_outputs={},
    )
    defaults.update(overrides)
    return AgentContext(**defaults)


# ─────────────────────────────────────────────────────────────────
# system_prompt
# ─────────────────────────────────────────────────────────────────


class TestSystemPrompt:
    def test_contains_key_sections(self):
        agent = DocumentAgent()
        prompt = agent.system_prompt
        assert "技术文档架构师" in prompt
        assert "架构文档" in prompt
        assert "API 参考" in prompt


# ─────────────────────────────────────────────────────────────────
# _run
# ─────────────────────────────────────────────────────────────────


class TestRun:
    @patch.object(DocumentAgent, "call_model", new_callable=AsyncMock)
    def test_basic_run(self, mock_call):
        mock_resp = MagicMock()
        mock_resp.content = "# Test Doc\n内容"
        mock_call.return_value = mock_resp

        agent = DocumentAgent()
        ctx = _make_context()
        result = asyncio.get_event_loop().run_until_complete(
            agent._run(ctx, [{"role": "user", "content": "写文档"}])
        )
        assert result == "# Test Doc\n内容"
        mock_call.assert_called_once()

    @patch.object(DocumentAgent, "call_model", new_callable=AsyncMock)
    def test_run_with_architect_previous_output(self, mock_call):
        mock_resp = MagicMock()
        mock_resp.content = "doc result"
        mock_call.return_value = mock_resp

        architect_output = MagicMock()
        architect_output.result = "A" * 4000  # will be truncated to 3000
        ctx = _make_context(previous_outputs={"architect": architect_output})

        agent = DocumentAgent()
        asyncio.get_event_loop().run_until_complete(
            agent._run(ctx, [{"role": "user", "content": "写"}])
        )

        # Check that architect context was appended
        call_args = mock_call.call_args
        messages = call_args.kwargs["messages"]
        roles = [m.role for m in messages]
        assert "system" in roles

    @patch.object(DocumentAgent, "call_model", new_callable=AsyncMock)
    def test_run_with_writer_previous_output(self, mock_call):
        mock_resp = MagicMock()
        mock_resp.content = "doc"
        mock_call.return_value = mock_resp

        writer_output = MagicMock()
        writer_output.result = "existing doc content"
        ctx = _make_context(previous_outputs={"writer": writer_output})

        agent = DocumentAgent()
        asyncio.get_event_loop().run_until_complete(
            agent._run(ctx, [{"role": "user", "content": "写"}])
        )
        mock_call.assert_called_once()

    @patch.object(DocumentAgent, "call_model", new_callable=AsyncMock)
    def test_run_reads_project_docs(self, mock_call, tmp_path):
        mock_resp = MagicMock()
        mock_resp.content = "doc"
        mock_call.return_value = mock_resp

        # Create a markdown file in project
        (tmp_path / "README.md").write_text("readme content", encoding="utf-8")

        ctx = _make_context(project_path=tmp_path)

        agent = DocumentAgent()
        asyncio.get_event_loop().run_until_complete(
            agent._run(ctx, [{"role": "user", "content": "写"}])
        )
        mock_call.assert_called_once()

    @patch.object(DocumentAgent, "call_model", new_callable=AsyncMock)
    def test_run_skips_large_docs(self, mock_call, tmp_path):
        mock_resp = MagicMock()
        mock_resp.content = "doc"
        mock_call.return_value = mock_resp

        # Create a large markdown file (>5000 chars)
        (tmp_path / "big.md").write_text("x" * 6000, encoding="utf-8")

        ctx = _make_context(project_path=tmp_path)

        agent = DocumentAgent()
        asyncio.get_event_loop().run_until_complete(
            agent._run(ctx, [{"role": "user", "content": "写"}])
        )

        # The large file should not be in the messages
        call_args = mock_call.call_args
        messages = call_args.kwargs["messages"]
        contents = [m.content for m in messages]
        assert not any("x" * 100 in c for c in contents)

    @patch.object(DocumentAgent, "call_model", new_callable=AsyncMock)
    def test_run_handles_read_error(self, mock_call, tmp_path):
        mock_resp = MagicMock()
        mock_resp.content = "doc"
        mock_call.return_value = mock_resp

        # Create a file that will cause read error (use unreadable path)
        md_file = tmp_path / "bad.md"
        md_file.write_text("ok", encoding="utf-8")
        md_file.chmod(0o000)

        ctx = _make_context(project_path=tmp_path)

        agent = DocumentAgent()
        asyncio.get_event_loop().run_until_complete(
            agent._run(ctx, [{"role": "user", "content": "写"}])
        )
        mock_call.assert_called_once()

        # Restore permissions for cleanup
        md_file.chmod(0o644)

    @patch.object(DocumentAgent, "call_model", new_callable=AsyncMock)
    def test_run_with_custom_metadata(self, mock_call):
        mock_resp = MagicMock()
        mock_resp.content = "custom doc"
        mock_call.return_value = mock_resp

        ctx = _make_context(
            metadata={"doc_type": "api_reference", "title": "API Docs"}
        )

        agent = DocumentAgent()
        asyncio.get_event_loop().run_until_complete(
            agent._run(ctx, [{"role": "user", "content": "写"}])
        )

        # Verify doc_hint was appended with custom type and title
        call_args = mock_call.call_args
        messages = call_args.kwargs["messages"]
        last_msg = messages[-1]
        assert "api_reference" in last_msg.content
        assert "API Docs" in last_msg.content

    @patch.object(DocumentAgent, "call_model", new_callable=AsyncMock)
    def test_run_no_project_path(self, mock_call):
        mock_resp = MagicMock()
        mock_resp.content = "doc"
        mock_call.return_value = mock_resp

        ctx = _make_context(project_path=None)

        agent = DocumentAgent()
        asyncio.get_event_loop().run_until_complete(
            agent._run(ctx, [{"role": "user", "content": "写"}])
        )
        mock_call.assert_called_once()


# ─────────────────────────────────────────────────────────────────
# _post_process
# ─────────────────────────────────────────────────────────────────


class TestPostProcess:
    def test_post_process(self):
        agent = DocumentAgent()
        ctx = _make_context()
        output = agent._post_process("result text", ctx)
        assert isinstance(output, AgentOutput)
        assert output.status == AgentStatus.COMPLETED
        assert output.result == "result text"
        assert output.agent_name == "document"
        assert len(output.recommendations) == 2

    def test_post_process_recommendations(self):
        agent = DocumentAgent()
        ctx = _make_context()
        output = agent._post_process("x", ctx)
        assert any("docs/" in r for r in output.recommendations)


# ─────────────────────────────────────────────────────────────────
# Agent metadata
# ─────────────────────────────────────────────────────────────────


class TestAgentMetadata:
    def test_agent_attributes(self):
        agent = DocumentAgent()
        assert agent.name == "document"
        assert agent.icon == "📄"
        assert agent.default_tier == "low"
        assert "file_read" in agent.tools
        assert "file_write" in agent.tools
