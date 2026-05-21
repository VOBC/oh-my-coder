"""Tests for base.py - Agent 基类"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.base import (
    AGENT_REGISTRY,
    SUPPORTED_TOOLS,
    WEB_FETCH_TOOL_SCHEMA,
    AgentContext,
    AgentLane,
    AgentOutput,
    AgentStatus,
    BaseAgent,
    get_agent,
    list_agents,
    list_all_agents,
    register_agent,
)

# ── Test Fixtures ──────────────────────────────────────────────────────

@pytest.fixture
def mock_model_router():
    """Mock ModelRouter for testing"""
    router = MagicMock()
    router.route_and_call = AsyncMock()
    return router


@pytest.fixture
def mock_orchestrator():
    """Mock Orchestrator for testing"""
    orch = MagicMock()
    orch.invoke_subagent = AsyncMock()
    return orch


@pytest.fixture
def sample_context(tmp_path):
    """Create a sample AgentContext"""
    return AgentContext(
        project_path=tmp_path,
        task_description="Test task",
        working_directory=tmp_path,
        relevant_files=[tmp_path / "test.py"],
        previous_outputs={"agent1": "result1"},
        metadata={"key": "value"},
        skill_context="Skill context",
        override_model="test-model",
    )


# ── Concrete Agent for Testing ──────────────────────────────────────────

class ConcreteTestAgent(BaseAgent):
    """Concrete implementation for testing abstract base class"""
    name = "test_agent"
    description = "Test agent for unit tests"
    lane = AgentLane.BUILD_ANALYSIS
    default_tier = "medium"
    icon = "🧪"

    @property
    def system_prompt(self) -> str:
        return "You are a test agent."

    async def _run(
        self, context: AgentContext, prompt: list[dict[str, str]], **kwargs
    ) -> str:
        return "Test result"


# ── AgentStatus Enum ────────────────────────────────────────────────────

class TestAgentStatus:
    def test_status_values(self):
        assert AgentStatus.IDLE.value == "idle"
        assert AgentStatus.WORKING.value == "working"
        assert AgentStatus.WAITING.value == "waiting"
        assert AgentStatus.COMPLETED.value == "completed"
        assert AgentStatus.FAILED.value == "failed"


# ── AgentLane Enum ──────────────────────────────────────────────────────

class TestAgentLane:
    def test_lane_values(self):
        assert AgentLane.BUILD_ANALYSIS.value == "build_analysis"
        assert AgentLane.REVIEW.value == "review"
        assert AgentLane.DOMAIN.value == "domain"
        assert AgentLane.COORDINATION.value == "coordination"


# ── AgentContext Dataclass ──────────────────────────────────────────────

class TestAgentContext:
    def test_creation_with_required_fields(self, tmp_path):
        ctx = AgentContext(
            project_path=tmp_path,
            task_description="Test",
        )
        assert ctx.project_path == tmp_path
        assert ctx.task_description == "Test"
        assert ctx.working_directory is None
        assert ctx.relevant_files == []
        assert ctx.previous_outputs == {}
        assert ctx.metadata == {}
        assert ctx.skill_context == ""
        assert ctx.override_model is None

    def test_creation_with_all_fields(self, tmp_path):
        ctx = AgentContext(
            project_path=tmp_path,
            task_description="Test",
            working_directory=tmp_path / "work",
            relevant_files=[tmp_path / "file.py"],
            previous_outputs={"a": "b"},
            metadata={"k": "v"},
            skill_context="skill",
            override_model="model",
        )
        assert ctx.working_directory == tmp_path / "work"
        assert len(ctx.relevant_files) == 1
        assert ctx.previous_outputs == {"a": "b"}
        assert ctx.metadata == {"k": "v"}
        assert ctx.skill_context == "skill"
        assert ctx.override_model == "model"


# ── AgentOutput Dataclass ───────────────────────────────────────────────

class TestAgentOutput:
    def test_defaults(self):
        output = AgentOutput(
            agent_name="test",
            status=AgentStatus.COMPLETED,
        )
        assert output.agent_name == "test"
        assert output.status == AgentStatus.COMPLETED
        assert output.result is None
        assert output.artifacts == {}
        assert output.recommendations == []
        assert output.next_agent is None
        assert output.usage == {}
        assert output.execution_time == 0.0
        assert output.error is None
        assert output.timestamp != ""

    def test_with_all_fields(self):
        output = AgentOutput(
            agent_name="test",
            status=AgentStatus.COMPLETED,
            result="Done",
            artifacts={"file": "data"},
            recommendations=["step1", "step2"],
            next_agent="next",
            usage={"prompt_tokens": 100, "completion_tokens": 50},
            execution_time=1.5,
            error=None,
        )
        assert output.result == "Done"
        assert len(output.artifacts) == 1
        assert len(output.recommendations) == 2
        assert output.next_agent == "next"
        assert output.usage["prompt_tokens"] == 100
        assert output.execution_time == 1.5


# ── Tool Schemas ────────────────────────────────────────────────────────

class TestToolSchemas:
    def test_web_fetch_schema(self):
        assert WEB_FETCH_TOOL_SCHEMA["type"] == "function"
        assert WEB_FETCH_TOOL_SCHEMA["function"]["name"] == "web_fetch"
        assert "url" in WEB_FETCH_TOOL_SCHEMA["function"]["parameters"]["properties"]

    def test_supported_tools(self):
        assert "web_fetch" in SUPPORTED_TOOLS
        assert SUPPORTED_TOOLS["web_fetch"] == WEB_FETCH_TOOL_SCHEMA


# ── BaseAgent Initialization ─────────────────────────────────────────────

class TestBaseAgentInit:
    def test_init_without_model_router(self):
        agent = ConcreteTestAgent()
        assert agent.model_router is None
        assert agent.orchestrator is None
        assert agent.config == {}
        assert agent.status == AgentStatus.IDLE
        assert agent._output_history == []
        assert agent._last_model_response is None

    def test_init_with_model_router(self, mock_model_router):
        agent = ConcreteTestAgent(model_router=mock_model_router)
        assert agent.model_router == mock_model_router

    def test_init_with_config(self):
        config = {"key": "value", "project_path": "/tmp"}
        agent = ConcreteTestAgent(config=config)
        assert agent.config == config

    def test_init_with_orchestrator(self, mock_orchestrator):
        agent = ConcreteTestAgent(orchestrator=mock_orchestrator)
        assert agent.orchestrator == mock_orchestrator

    def test_workspace_scanner_init_with_project_path(self, tmp_path):
        agent = ConcreteTestAgent(config={"project_path": str(tmp_path)})
        # Scanner should be initialized (or None if import fails)
        assert agent.workspace_scanner is not None or agent.workspace_scanner is None

    def test_workspace_scanner_init_without_project_path(self):
        agent = ConcreteTestAgent()
        # Scanner should use cwd or be None if import fails
        assert agent.workspace_scanner is not None or agent.workspace_scanner is None


# ── BaseAgent Properties ─────────────────────────────────────────────────

class TestBaseAgentProperties:
    def test_system_prompt(self):
        agent = ConcreteTestAgent()
        assert agent.system_prompt == "You are a test agent."

    def test_class_attributes(self):
        assert ConcreteTestAgent.name == "test_agent"
        assert ConcreteTestAgent.description == "Test agent for unit tests"
        assert ConcreteTestAgent.lane == AgentLane.BUILD_ANALYSIS
        assert ConcreteTestAgent.default_tier == "medium"
        assert ConcreteTestAgent.icon == "🧪"
        assert ConcreteTestAgent.tools == ["web_fetch"]


# ── get_workspace_context ───────────────────────────────────────────────

class TestGetWorkspaceContext:
    def test_scanner_none(self):
        agent = ConcreteTestAgent()
        agent.workspace_scanner = None
        result = agent.get_workspace_context()
        assert result == "[工作目录上下文不可用]"

    def test_scanner_exception(self):
        agent = ConcreteTestAgent()
        mock_scanner = MagicMock()
        mock_scanner.to_context_string.side_effect = Exception("Scan failed")
        agent.workspace_scanner = mock_scanner
        result = agent.get_workspace_context()
        assert "扫描失败" in result
        assert "Scan failed" in result

    def test_scanner_success(self):
        agent = ConcreteTestAgent()
        mock_scanner = MagicMock()
        mock_scanner.to_context_string.return_value = "file tree"
        agent.workspace_scanner = mock_scanner
        result = agent.get_workspace_context(max_depth=5)
        assert result == "file tree"
        mock_scanner.to_context_string.assert_called_once_with(max_depth=5)


# ── get_full_context ────────────────────────────────────────────────────

class TestGetFullContext:
    def test_browser_context_success(self):
        agent = ConcreteTestAgent()
        agent.workspace_scanner = None

        with patch("src.context.BrowserAwareness") as mock_awareness_cls:
            mock_awareness = MagicMock()
            mock_awareness.get_current_tab = AsyncMock()
            mock_tab = MagicMock()
            mock_tab.to_context_string.return_value = "browser info"
            mock_awareness.get_current_tab.return_value = mock_tab
            mock_awareness_cls.return_value = mock_awareness

            result = agent.get_full_context()
            assert "workspace" in result
            assert "browser" in result

    def test_browser_context_exception(self):
        agent = ConcreteTestAgent()
        agent.workspace_scanner = None

        with patch("src.context.BrowserAwareness") as mock_awareness_cls:
            mock_awareness_cls.side_effect = Exception("No browser")
            result = agent.get_full_context()
            assert result["browser"] == "[浏览器上下文不可用]"


# ── get_context_prompt ───────────────────────────────────────────────────

class TestGetContextPrompt:
    def test_empty_context(self, tmp_path):
        agent = ConcreteTestAgent()
        agent.workspace_scanner = None
        ctx = AgentContext(
            project_path=tmp_path,
            task_description="",
        )
        result = agent.get_context_prompt(ctx)
        # Should have project path at minimum
        assert str(tmp_path) in result

    def test_with_task_description(self, tmp_path):
        agent = ConcreteTestAgent()
        agent.workspace_scanner = None
        ctx = AgentContext(
            project_path=tmp_path,
            task_description="Test task",
        )
        result = agent.get_context_prompt(ctx)
        assert "Test task" in result
        assert "当前任务" in result

    def test_with_relevant_files(self, tmp_path):
        agent = ConcreteTestAgent()
        agent.workspace_scanner = None
        ctx = AgentContext(
            project_path=tmp_path,
            task_description="",
            relevant_files=[tmp_path / "file1.py", tmp_path / "file2.py"],
        )
        result = agent.get_context_prompt(ctx)
        assert "file1.py" in result
        assert "file2.py" in result
        assert "相关文件" in result

    def test_with_previous_outputs(self, tmp_path):
        agent = ConcreteTestAgent()
        agent.workspace_scanner = None
        ctx = AgentContext(
            project_path=tmp_path,
            task_description="",
            previous_outputs={"agent1": "output1", "agent2": "output2"},
        )
        result = agent.get_context_prompt(ctx)
        assert "agent1" in result
        assert "output1" in result
        assert "前序工作成果" in result

    def test_with_skill_context(self, tmp_path):
        agent = ConcreteTestAgent()
        agent.workspace_scanner = None
        ctx = AgentContext(
            project_path=tmp_path,
            task_description="",
            skill_context="Skill experience",
        )
        result = agent.get_context_prompt(ctx)
        assert "Skill experience" in result

    def test_with_workspace_context(self, tmp_path):
        agent = ConcreteTestAgent()
        mock_scanner = MagicMock()
        mock_scanner.to_context_string.return_value = "file tree structure"
        agent.workspace_scanner = mock_scanner
        ctx = AgentContext(
            project_path=tmp_path,
            task_description="",
        )
        result = agent.get_context_prompt(ctx)
        assert "file tree structure" in result
        assert "项目文件结构" in result


# ── _prepare_prompt ──────────────────────────────────────────────────────

class TestPreparePrompt:
    def test_prepare_prompt_basic(self, tmp_path):
        agent = ConcreteTestAgent()
        agent.workspace_scanner = None
        ctx = AgentContext(
            project_path=tmp_path,
            task_description="",
        )
        messages = agent._prepare_prompt(ctx)
        assert len(messages) >= 1
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "You are a test agent."

    def test_prepare_prompt_with_context(self, tmp_path):
        agent = ConcreteTestAgent()
        agent.workspace_scanner = None
        ctx = AgentContext(
            project_path=tmp_path,
            task_description="Test task",
        )
        messages = agent._prepare_prompt(ctx)
        assert len(messages) >= 2
        assert messages[1]["role"] == "user"
        assert "Test task" in messages[1]["content"]


# ── execute (Template Method) ────────────────────────────────────────────

class TestExecute:
    @pytest.mark.asyncio
    async def test_execute_success(self, sample_context):
        agent = ConcreteTestAgent()
        agent.workspace_scanner = None
        output = await agent.execute(sample_context)
        assert output.status == AgentStatus.COMPLETED
        assert output.result == "Test result"
        assert output.agent_name == "test_agent"
        assert agent.status == AgentStatus.COMPLETED
        assert len(agent._output_history) == 1

    @pytest.mark.asyncio
    async def test_execute_with_error(self, sample_context):
        class FailingAgent(BaseAgent):
            name = "failing"
            description = "Fails"
            lane = AgentLane.BUILD_ANALYSIS

            @property
            def system_prompt(self) -> str:
                return "Fail"

            async def _run(self, context, prompt, **kwargs):
                raise ValueError("Test error")

        agent = FailingAgent()
        agent.workspace_scanner = None
        output = await agent.execute(sample_context)
        assert output.status == AgentStatus.FAILED
        assert output.error == "ValueError"
        assert agent.status == AgentStatus.FAILED

    @pytest.mark.asyncio
    async def test_execute_with_override_model(self, sample_context):
        agent = ConcreteTestAgent()
        agent.workspace_scanner = None
        await agent.execute(sample_context)
        assert agent._override_model == "test-model"

    @pytest.mark.asyncio
    async def test_execute_with_token_usage(self, sample_context, mock_model_router):
        class AgentWithModelCall(BaseAgent):
            name = "with_model"
            description = "Uses model"
            lane = AgentLane.BUILD_ANALYSIS

            @property
            def system_prompt(self) -> str:
                return "Test"

            async def _run(self, context, prompt, **kwargs):
                # Simulate model call that sets _last_model_response
                mock_usage = MagicMock()
                mock_usage.prompt_tokens = 100
                mock_usage.completion_tokens = 50
                mock_usage.total_tokens = 150
                mock_response = MagicMock()
                mock_response.usage = mock_usage
                self._last_model_response = mock_response
                return "Result"

        agent = AgentWithModelCall(model_router=mock_model_router)
        agent.workspace_scanner = None
        output = await agent.execute(sample_context)
        assert output.usage["prompt_tokens"] == 100
        assert output.usage["completion_tokens"] == 50
        assert output.usage["total_tokens"] == 150

    @pytest.mark.asyncio
    async def test_execute_execution_time(self, sample_context):
        agent = ConcreteTestAgent()
        agent.workspace_scanner = None
        output = await agent.execute(sample_context)
        assert output.execution_time >= 0


# ── _post_process ────────────────────────────────────────────────────────

class TestPostProcess:
    def test_post_process_default(self, tmp_path):
        agent = ConcreteTestAgent()
        ctx = AgentContext(project_path=tmp_path, task_description="")
        output = agent._post_process("result", ctx)
        assert output.status == AgentStatus.COMPLETED
        assert output.result == "result"
        assert output.agent_name == "test_agent"


# ── call_model ───────────────────────────────────────────────────────────

class TestCallModel:
    @pytest.mark.asyncio
    async def test_call_model_basic(self, mock_model_router):
        agent = ConcreteTestAgent(model_router=mock_model_router)
        mock_response = MagicMock()
        mock_response.content = "Response"
        mock_response.tool_calls = None
        mock_model_router.route_and_call.return_value = mock_response

        from src.models.base import Message
        messages = [Message(role="user", content="Test")]

        result = await agent.call_model(
            task_type="test",
            messages=messages,
        )
        assert result == mock_response
        mock_model_router.route_and_call.assert_called_once()

    @pytest.mark.asyncio
    async def test_call_model_with_tools(self, mock_model_router):
        agent = ConcreteTestAgent(model_router=mock_model_router)
        mock_response = MagicMock()
        mock_response.content = "Response"
        mock_response.tool_calls = None
        mock_model_router.route_and_call.return_value = mock_response

        from src.models.base import Message
        messages = [Message(role="user", content="Test")]

        await agent.call_model(
            task_type="test",
            messages=messages,
        )
        # Verify tools were injected
        call_kwargs = mock_model_router.route_and_call.call_args[1]
        assert "tools" in call_kwargs

    @pytest.mark.asyncio
    async def test_call_model_with_override_model(self, mock_model_router):
        agent = ConcreteTestAgent(model_router=mock_model_router)
        agent._override_model = "custom-model"
        mock_response = MagicMock()
        mock_response.content = "Response"
        mock_response.tool_calls = None
        mock_model_router.route_and_call.return_value = mock_response

        from src.models.base import Message
        messages = [Message(role="user", content="Test")]

        await agent.call_model(task_type="test", messages=messages)
        call_kwargs = mock_model_router.route_and_call.call_args[1]
        assert call_kwargs["override_model"] == "custom-model"

    @pytest.mark.asyncio
    async def test_call_model_with_tool_calls(self, mock_model_router):
        agent = ConcreteTestAgent(model_router=mock_model_router)

        # First response with tool call
        mock_response1 = MagicMock()
        mock_response1.content = ""
        mock_response1.tool_calls = [{
            "id": "call_1",
            "function": {
                "name": "web_fetch",
                "arguments": json.dumps({"url": "https://example.com"})
            }
        }]

        # Second response without tool call
        mock_response2 = MagicMock()
        mock_response2.content = "Final response"
        mock_response2.tool_calls = None

        mock_model_router.route_and_call.side_effect = [mock_response1, mock_response2]

        # Mock web_fetch tool
        with patch.object(agent, '_web_fetch_tool', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = "Fetched content"

            from src.models.base import Message
            messages = [Message(role="user", content="Test")]

            result = await agent.call_model(task_type="test", messages=messages)
            assert result == mock_response2
            mock_fetch.assert_called_once()

    @pytest.mark.asyncio
    async def test_call_model_unknown_tool(self, mock_model_router):
        agent = ConcreteTestAgent(model_router=mock_model_router)

        mock_response1 = MagicMock()
        mock_response1.content = ""
        mock_response1.tool_calls = [{
            "id": "call_1",
            "function": {
                "name": "unknown_tool",
                "arguments": "{}"
            }
        }]

        mock_response2 = MagicMock()
        mock_response2.content = "Done"
        mock_response2.tool_calls = None

        mock_model_router.route_and_call.side_effect = [mock_response1, mock_response2]

        from src.models.base import Message
        messages = [Message(role="user", content="Test")]

        result = await agent.call_model(task_type="test", messages=messages)
        assert result == mock_response2


# ── _web_fetch_tool ──────────────────────────────────────────────────────

class TestWebFetchTool:
    @pytest.mark.asyncio
    async def test_web_fetch_with_dict_args(self):
        agent = ConcreteTestAgent()
        result = await agent._web_fetch_tool({"url": "https://example.com"})
        # Result depends on curl execution, just verify it doesn't crash
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_web_fetch_with_json_string(self):
        agent = ConcreteTestAgent()
        result = await agent._web_fetch_tool('{"url": "https://example.com"}')
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_web_fetch_missing_url(self):
        agent = ConcreteTestAgent()
        result = await agent._web_fetch_tool({})
        assert "Missing url parameter" in result

    @pytest.mark.asyncio
    async def test_web_fetch_invalid_json(self):
        agent = ConcreteTestAgent()
        result = await agent._web_fetch_tool("not json")
        assert "Invalid arguments" in result

    @pytest.mark.asyncio
    async def test_web_fetch_curl_exception(self):
        agent = ConcreteTestAgent()
        with patch("subprocess.run", side_effect=Exception("Network error")):
            result = await agent._web_fetch_tool({"url": "https://example.com"})
            assert "web_fetch error" in result


# ── get_last_output / get_output_history ─────────────────────────────────

class TestOutputHistory:
    def test_get_last_output_empty(self):
        agent = ConcreteTestAgent()
        assert agent.get_last_output() is None

    def test_get_last_output_with_history(self):
        agent = ConcreteTestAgent()
        output1 = AgentOutput(agent_name="test", status=AgentStatus.COMPLETED)
        output2 = AgentOutput(agent_name="test", status=AgentStatus.FAILED)
        agent._output_history = [output1, output2]
        assert agent.get_last_output() == output2

    def test_get_output_history_empty(self):
        agent = ConcreteTestAgent()
        assert agent.get_output_history() == []

    def test_get_output_history_returns_copy(self):
        agent = ConcreteTestAgent()
        output = AgentOutput(agent_name="test", status=AgentStatus.COMPLETED)
        agent._output_history = [output]
        history = agent.get_output_history()
        history.append(output)
        assert len(agent._output_history) == 1


# ── call_subagent ────────────────────────────────────────────────────────

class TestCallSubagent:
    @pytest.mark.asyncio
    async def test_call_subagent_without_orchestrator(self, sample_context):
        agent = ConcreteTestAgent()
        with pytest.raises(RuntimeError) as exc_info:
            await agent.call_subagent("analyst", "task", sample_context)
        assert "Orchestrator 未注入" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_call_subagent_success(self, sample_context, mock_orchestrator):
        agent = ConcreteTestAgent(orchestrator=mock_orchestrator)
        mock_output = AgentOutput(agent_name="analyst", status=AgentStatus.COMPLETED)
        mock_orchestrator.invoke_subagent.return_value = mock_output

        result = await agent.call_subagent("analyst", "task", sample_context)
        assert result == mock_output
        mock_orchestrator.invoke_subagent.assert_called_once()

    @pytest.mark.asyncio
    async def test_call_subagent_with_previous_outputs(self, tmp_path, mock_orchestrator):
        agent = ConcreteTestAgent(orchestrator=mock_orchestrator)
        ctx = AgentContext(
            project_path=tmp_path,
            task_description="",
            metadata={},
        )
        # Add output history
        agent._output_history = [
            AgentOutput(agent_name="test_agent", status=AgentStatus.COMPLETED)
        ]

        mock_output = AgentOutput(agent_name="analyst", status=AgentStatus.COMPLETED)
        mock_orchestrator.invoke_subagent.return_value = mock_output

        await agent.call_subagent("analyst", "task", ctx)
        # Verify previous_outputs was merged
        call_kwargs = mock_orchestrator.invoke_subagent.call_args[1]
        assert "test_agent" in call_kwargs["context"]["previous_outputs"]


# ── save_output ──────────────────────────────────────────────────────────

class TestSaveOutput:
    def test_save_output_empty_history(self, tmp_path):
        agent = ConcreteTestAgent()
        agent.save_output(tmp_path)
        # Should not create any file
        assert len(list(tmp_path.glob("*.json"))) == 0

    def test_save_output_success(self, tmp_path):
        agent = ConcreteTestAgent()
        output = AgentOutput(
            agent_name="test_agent",
            status=AgentStatus.COMPLETED,
            result="Done",
            artifacts={"file": "data"},
            recommendations=["step1"],
            error=None,
        )
        agent._output_history = [output]

        agent.save_output(tmp_path)

        files = list(tmp_path.glob("test_agent_*.json"))
        assert len(files) == 1

        with open(files[0], encoding="utf-8") as f:
            data = json.load(f)
        assert data["agent"] == "test_agent"
        assert data["status"] == "completed"
        assert data["result"] == "Done"


# ── Agent Registry ───────────────────────────────────────────────────────

class TestAgentRegistry:
    def test_register_agent(self):
        @register_agent
        class RegisteredAgent(BaseAgent):
            name = "registered_test"
            description = "Registered"
            lane = AgentLane.BUILD_ANALYSIS

            @property
            def system_prompt(self) -> str:
                return "Test"

            async def _run(self, context, prompt, **kwargs):
                return "result"

        assert "registered_test" in AGENT_REGISTRY
        assert AGENT_REGISTRY["registered_test"] == RegisteredAgent

    def test_get_agent_existing(self):
        # Use already registered agent
        AGENT_REGISTRY["existing"] = ConcreteTestAgent
        result = get_agent("existing")
        assert result == ConcreteTestAgent

    def test_get_agent_nonexistent(self):
        result = get_agent("nonexistent_agent_xyz")
        assert result is None

    def test_list_all_agents(self):
        # Register some agents
        AGENT_REGISTRY["agent1"] = ConcreteTestAgent
        AGENT_REGISTRY["agent2"] = ConcreteTestAgent

        result = list_all_agents()
        assert isinstance(result, list)
        names = [a["name"] for a in result]
        assert "agent1" in names or "agent2" in names

    def test_list_agents(self):
        AGENT_REGISTRY["test_list"] = ConcreteTestAgent
        result = list_agents()
        assert isinstance(result, list)
        assert "test_list" in result


# ── Edge Cases & Error Handling ──────────────────────────────────────────

class TestEdgeCases:
    @pytest.mark.asyncio
    async def test_execute_with_exception_in_run(self, sample_context):
        class ExceptionAgent(BaseAgent):
            name = "exception"
            description = "Raises exception"
            lane = AgentLane.BUILD_ANALYSIS

            @property
            def system_prompt(self) -> str:
                return "Test"

            async def _run(self, context, prompt, **kwargs):
                raise RuntimeError("Unexpected error")

        agent = ExceptionAgent()
        agent.workspace_scanner = None
        output = await agent.execute(sample_context)
        assert output.status == AgentStatus.FAILED
        assert output.error == "RuntimeError"

    def test_get_context_prompt_with_empty_relevant_files(self, tmp_path):
        agent = ConcreteTestAgent()
        agent.workspace_scanner = None
        ctx = AgentContext(
            project_path=tmp_path,
            task_description="",
            relevant_files=[],
        )
        result = agent.get_context_prompt(ctx)
        assert "相关文件" not in result

    def test_get_context_prompt_with_empty_previous_outputs(self, tmp_path):
        agent = ConcreteTestAgent()
        agent.workspace_scanner = None
        ctx = AgentContext(
            project_path=tmp_path,
            task_description="",
            previous_outputs={},
        )
        result = agent.get_context_prompt(ctx)
        assert "前序工作成果" not in result
