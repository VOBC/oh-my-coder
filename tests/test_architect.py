"""
ArchitectAgent 单元测试（纯逻辑，不调 API）
"""

from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.architect import ArchitectureDecision, ArchitectAgent
from src.agents.base import AgentContext, AgentOutput, AgentStatus


# ─────────────────────────────────────────────────────────────────
# ArchitectureDecision
# ─────────────────────────────────────────────────────────────────


class TestArchitectureDecision:
    """测试 ArchitectureDecision 数据类"""

    def test_creation(self):
        decision = ArchitectureDecision(
            title="ADR-001: 使用微服务架构",
            status="proposed",
            context="需要支持独立部署和扩展",
            decision="采用微服务架构风格",
            consequences="增加运维复杂度，但提高可扩展性",
        )
        assert decision.title == "ADR-001: 使用微服务架构"
        assert decision.status == "proposed"
        assert decision.context == "需要支持独立部署和扩展"
        assert decision.decision == "采用微服务架构风格"
        assert decision.consequences == "增加运维复杂度，但提高可扩展性"

    def test_all_fields_required(self):
        """测试所有字段都是必需的"""
        # 不提供 status 应该报错
        with pytest.raises(TypeError):
            ArchitectureDecision(
                title="测试",
                context="背景",
                decision="决策",
                consequences="影响",
            )

    def test_status_accepted(self):
        """测试 accepted 状态"""
        decision = ArchitectureDecision(
            title="ADR-002: 数据库选型",
            status="accepted",
            context="需要选择数据库",
            decision="使用 PostgreSQL",
            consequences="需要学习 PostgreSQL",
        )
        assert decision.status == "accepted"

    def test_status_deprecated(self):
        """测试 deprecated 状态"""
        decision = ArchitectureDecision(
            title="ADR-003: 旧架构",
            status="deprecated",
            context="旧架构不再适用",
            decision="弃用旧架构",
            consequences="需要迁移到新架构",
        )
        assert decision.status == "deprecated"

    def test_repr(self):
        """测试字符串表示"""
        decision = ArchitectureDecision(
            title="测试",
            status="proposed",
            context="背景",
            decision="决策",
            consequences="影响",
        )
        # dataclass 应该有合理的 repr
        assert "测试" in repr(decision)


# ─────────────────────────────────────────────────────────────────
# ArchitectAgent 类属性
# ─────────────────────────────────────────────────────────────────


class TestArchitectAgentClassAttributes:
    """测试 ArchitectAgent 的类属性"""

    def test_name(self):
        assert ArchitectAgent.name == "architect"

    def test_description(self):
        assert ArchitectAgent.description == "架构师智能体 - 系统架构设计和技术选型"

    def test_lane(self):
        from src.agents.base import AgentLane
        assert ArchitectAgent.lane == AgentLane.BUILD_ANALYSIS

    def test_default_tier(self):
        assert ArchitectAgent.default_tier == "high"

    def test_icon(self):
        assert ArchitectAgent.icon == "🏗️"

    def test_tools(self):
        assert ArchitectAgent.tools == ["file_read", "file_write", "diagram", "web_fetch"]

    def test_tools_is_list(self):
        """测试 tools 是列表类型"""
        assert isinstance(ArchitectAgent.tools, list)

    def test_tools_contains_file_read(self):
        """测试 tools 包含 file_read"""
        assert "file_read" in ArchitectAgent.tools

    def test_tools_contains_diagram(self):
        """测试 tools 包含 diagram"""
        assert "diagram" in ArchitectAgent.tools


# ─────────────────────────────────────────────────────────────────
# system_prompt
# ─────────────────────────────────────────────────────────────────


class TestSystemPrompt:
    """测试 system_prompt 属性"""

    def test_system_prompt_contains_key_sections(self):
        agent = ArchitectAgent()
        prompt = agent.system_prompt
        assert "资深软件架构师" in prompt
        assert "KISS" in prompt
        assert "YAGNI" in prompt
        assert "架构概览" in prompt
        assert "技术栈" in prompt
        assert "架构决策记录" in prompt
        assert "风险和缓解" in prompt

    def test_system_prompt_is_string(self):
        agent = ArchitectAgent()
        assert isinstance(agent.system_prompt, str)
        assert len(agent.system_prompt) > 100  # 应该是一个较长的提示词

    def test_system_prompt_contains_principles(self):
        """测试包含工作原则"""
        agent = ArchitectAgent()
        prompt = agent.system_prompt
        assert "保持简单" in prompt  # KISS
        assert "不要提前设计" in prompt  # YAGNI
        assert "权衡透明" in prompt
        assert "可演进" in prompt

    def test_system_prompt_contains_output_format(self):
        """测试包含输出格式说明"""
        agent = ArchitectAgent()
        prompt = agent.system_prompt
        assert "架构概览" in prompt
        assert "核心模块" in prompt
        assert "接口设计" in prompt
        assert "ADR" in prompt


# ─────────────────────────────────────────────────────────────────
# _run() 方法
# ─────────────────────────────────────────────────────────────────


class TestRunMethod:
    """测试 _run() 方法的逻辑"""

    @pytest.fixture
    def agent(self):
        return ArchitectAgent()

    @pytest.fixture
    def basic_context(self):
        return AgentContext(
            task_description="设计一个用户管理系统",
            project_path="/fake/path",
        )

    @pytest.mark.asyncio
    async def test_run_without_previous_outputs(self, agent, basic_context):
        """测试没有前序输出时的情况"""
        prompt = [{"role": "user", "content": "设计架构"}]

        # Mock call_model 返回
        mock_response = MagicMock()
        mock_response.content = "# 架构设计方案\n\n## 1. 架构概览..."

        with patch.object(agent, "call_model", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_response
            result = await agent._run(basic_context, prompt)

        assert result == "# 架构设计方案\n\n## 1. 架构概览..."
        assert mock_call.called

    @pytest.mark.asyncio
    async def test_run_with_explore_output(self, agent):
        """测试有 explore 前序输出时的情况"""
        context = AgentContext(
            task_description="设计系统",
            project_path="/fake/path",
            previous_outputs={
                "explore": AgentOutput(
                    agent_name="explore",
                    status=AgentStatus.COMPLETED,
                    result="项目有 10 个 Python 文件",
                )
            },
        )
        prompt = [{"role": "user", "content": "开始设计"}]

        mock_response = MagicMock()
        mock_response.content = "架构设计结果"

        with patch.object(agent, "call_model", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_response
            result = await agent._run(context, prompt)

        assert result == "架构设计结果"
        # 验证 call_model 被调用
        assert mock_call.called

    @pytest.mark.asyncio
    async def test_run_with_analyst_output(self, agent):
        """测试有 analyst 前序输出时的情况"""
        context = AgentContext(
            task_description="设计系统",
            project_path="/fake/path",
            previous_outputs={
                "analyst": AgentOutput(
                    agent_name="analyst",
                    status=AgentStatus.COMPLETED,
                    result="需求分析结果：需要支持用户登录",
                )
            },
        )
        prompt = [{"role": "user", "content": "开始设计"}]

        mock_response = MagicMock()
        mock_response.content = "架构设计结果"

        with patch.object(agent, "call_model", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_response
            result = await agent._run(context, prompt)

        assert result == "架构设计结果"

    @pytest.mark.asyncio
    async def test_run_with_both_previous_outputs(self, agent):
        """测试同时有 explore 和 analyst 前序输出时的情况"""
        context = AgentContext(
            task_description="设计系统",
            project_path="/fake/path",
            previous_outputs={
                "explore": AgentOutput(
                    agent_name="explore",
                    status=AgentStatus.COMPLETED,
                    result="项目结构：MVC 模式",
                ),
                "analyst": AgentOutput(
                    agent_name="analyst",
                    status=AgentStatus.COMPLETED,
                    result="需求：用户管理、权限控制",
                ),
            },
        )
        prompt = [{"role": "user", "content": "开始设计"}]

        mock_response = MagicMock()
        mock_response.content = "完整架构设计"

        with patch.object(agent, "call_model", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_response
            result = await agent._run(context, prompt)

        assert result == "完整架构设计"

    @pytest.mark.asyncio
    async def test_run_adds_design_hint(self, agent, basic_context):
        """测试是否添加了设计提示"""
        prompt = [{"role": "user", "content": "设计"}]

        mock_response = MagicMock()
        mock_response.content = "结果"

        with patch.object(agent, "call_model", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_response
            result = await agent._run(basic_context, prompt)

        # 验证 prompt 中包含了设计提示
        # 没有前序输出时，prompt 长度应该是 2 (原始 + 设计提示)
        assert len(prompt) == 2
        assert "架构风格" in prompt[1]["content"]
        assert "技术选型" in prompt[1]["content"]

    @pytest.mark.asyncio
    async def test_run_with_explore_adds_context_and_hint(self, agent):
        """测试有 explore 输出时添加了上下文和设计提示"""
        context = AgentContext(
            task_description="设计系统",
            project_path="/fake/path",
            previous_outputs={
                "explore": AgentOutput(
                    agent_name="explore",
                    status=AgentStatus.COMPLETED,
                    result="项目结构",
                )
            },
        )
        prompt = [{"role": "user", "content": "开始"}]

        mock_response = MagicMock()
        mock_response.content = "结果"

        with patch.object(agent, "call_model", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_response
            result = await agent._run(context, prompt)

        # prompt 应该包含：原始 + explore上下文 + 设计提示 = 3
        assert len(prompt) == 3
        assert "项目探索" in prompt[1]["content"]
        assert "架构风格" in prompt[2]["content"]

    @pytest.mark.asyncio
    async def test_run_calls_model_with_correct_params(self, agent, basic_context):
        """测试调用模型时传递了正确的参数"""
        prompt = [{"role": "user", "content": "设计"}]

        mock_response = MagicMock()
        mock_response.content = "结果"

        with patch.object(agent, "call_model", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_response
            await agent._run(basic_context, prompt)

        # 验证 call_model 被调用时的参数
        assert mock_call.called
        call_args = mock_call.call_args
        assert call_args is not None
        # 检查是否传递了 task_type 和 messages
        assert "task_type" in call_args.kwargs or len(call_args[0]) > 0

    @pytest.mark.asyncio
    async def test_run_returns_string(self, agent, basic_context):
        """测试返回类型是字符串"""
        prompt = [{"role": "user", "content": "设计"}]

        mock_response = MagicMock()
        mock_response.content = "架构设计结果"

        with patch.object(agent, "call_model", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_response
            result = await agent._run(basic_context, prompt)

        assert isinstance(result, str)


# ─────────────────────────────────────────────────────────────────
# _post_process() 方法
# ─────────────────────────────────────────────────────────────────


class TestPostProcessMethod:
    """测试 _post_process() 方法"""

    @pytest.fixture
    def agent(self):
        return ArchitectAgent()

    def test_post_process_returns_agent_output(self, agent):
        """测试返回的是 AgentOutput"""
        result = "架构设计方案"
        context = AgentContext(
            task_description="测试",
            project_path="/fake/path",
        )

        output = agent._post_process(result, context)

        assert isinstance(output, AgentOutput)
        assert output.agent_name == "architect"
        assert output.status == AgentStatus.COMPLETED
        assert output.result == "架构设计方案"

    def test_post_process_includes_recommendations(self, agent):
        """测试返回的推荐建议"""
        result = "架构设计"
        context = AgentContext(
            task_description="测试",
            project_path="/fake/path",
        )

        output = agent._post_process(result, context)

        assert len(output.recommendations) == 2
        assert "executor Agent" in output.recommendations[0]
        assert "critic Agent" in output.recommendations[1]

    def test_post_process_sets_next_agent(self, agent):
        """测试设置的下一个 agent"""
        result = "架构设计"
        context = AgentContext(
            task_description="测试",
            project_path="/fake/path",
        )

        output = agent._post_process(result, context)

        assert output.next_agent == "executor"

    def test_post_process_recommendations_content(self, agent):
        """测试推荐建议的具体内容"""
        result = "架构设计"
        context = AgentContext(
            task_description="测试",
            project_path="/fake/path",
        )

        output = agent._post_process(result, context)

        assert "executor" in output.recommendations[0].lower()
        assert "critic" in output.recommendations[1].lower()

    def test_post_process_with_empty_result(self, agent):
        """测试处理空结果"""
        result = ""
        context = AgentContext(
            task_description="测试",
            project_path="/fake/path",
        )

        output = agent._post_process(result, context)

        assert output.result == ""
        assert output.status == AgentStatus.COMPLETED

    def test_post_process_with_none_result(self, agent):
        """测试处理 None 结果"""
        result = None
        context = AgentContext(
            task_description="测试",
            project_path="/fake/path",
        )

        output = agent._post_process(result, context)

        assert output.result is None
        assert output.status == AgentStatus.COMPLETED

    def test_post_process_output_has_correct_agent_name(self, agent):
        """测试输出的 agent_name 正确"""
        result = "测试"
        context = AgentContext(
            task_description="测试",
            project_path="/fake/path",
        )

        output = agent._post_process(result, context)

        assert output.agent_name == "architect"


# ─────────────────────────────────────────────────────────────────
# 集成测试
# ─────────────────────────────────────────────────────────────────


class TestArchitectAgentIntegration:
    """集成测试：测试各组件协同"""

    def test_agent_can_be_instantiated(self):
        """测试可以实例化 Agent"""
        agent = ArchitectAgent()
        assert agent is not None
        assert agent.name == "architect"

    def test_system_prompt_property_accessible(self):
        """测试可以访问 system_prompt 属性"""
        agent = ArchitectAgent()
        prompt = agent.system_prompt
        assert isinstance(prompt, str)
        assert len(prompt) > 0

    def test_agent_has_correct_lane(self):
        """测试 agent 的 lane 正确"""
        agent = ArchitectAgent()
        from src.agents.base import AgentLane
        assert agent.lane == AgentLane.BUILD_ANALYSIS

    def test_agent_has_high_tier(self):
        """测试 agent 使用 high tier"""
        agent = ArchitectAgent()
        assert agent.default_tier == "high"

    def test_post_process_result_matches_input(self):
        """测试后处理结果与原结果一致"""
        agent = ArchitectAgent()
        context = AgentContext(
            task_description="测试",
            project_path="/fake/path",
        )

        input_result = "# 完整架构设计\n\n## 1. 架构概览"
        output = agent._post_process(input_result, context)

        assert output.result == input_result
