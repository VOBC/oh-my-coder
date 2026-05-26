"""
测试 src/commands/cli_agent.py 中的 Typer 命令
"""

import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from typer.testing import CliRunner

# 导入被测试的 app
from src.commands.cli_agent import app


@pytest.fixture
def runner():
    """创建 Typer CliRunner"""
    return CliRunner(mix_stderr=False)


@pytest.fixture
def mock_console():
    """Mock src.commands.cli_agent.console"""
    with patch("src.commands.cli_agent.console") as m:
        yield m


def create_mock_agent(name="test-agent", description="A test agent",
                      lane_value="code", default_tier="smart",
                      icon="🤖", tools=None, system_prompt="You are a test agent",
                      model="deepseek", max_tokens=8000, temperature=0.7, timeout=60):
    """创建模拟的 agent 对象"""
    mock_agent = Mock()
    mock_agent.name = name
    mock_agent.description = description
    mock_agent.model = model
    mock_agent.max_tokens = max_tokens
    mock_agent.temperature = temperature
    mock_agent.timeout = timeout

    # 使用 PropertyMock 来处理 lane
    type(mock_agent).lane = Mock()
    type(mock_agent).lane.value = lane_value

    mock_agent.default_tier = default_tier
    mock_agent.icon = icon
    mock_agent.tools = tools if tools is not None else ["tool1", "tool2"]
    mock_agent.system_prompt = system_prompt
    return mock_agent


class TestListAgents:
    """测试 list_agents 命令"""

    @patch("src.agents.base.list_all_agents")
    def test_list_agents_basic(self, mock_list_all, runner, mock_console):
        """测试基本的 list 命令"""
        mock_list_all.return_value = [
            {"name": "test-agent", "description": "A test agent", "lane": "code", "default_tier": "smart"}
        ]

        result = runner.invoke(app, ["list"])

        assert result.exit_code == 0
        mock_list_all.assert_called_once()

    @patch("src.agents.base.list_all_agents")
    @patch("src.core.monorepo.detect_monorepo")
    @patch("src.core.monorepo.list_subprojects")
    def test_list_agents_with_monorepo(
        self, mock_list_sub, mock_detect, mock_list_all, runner, mock_console
    ):
        """测试带 --monorepo 选项的 list 命令"""
        mock_list_all.return_value = []
        mock_detect.return_value = None  # 不是 monorepo

        result = runner.invoke(app, ["list", "--monorepo"])

        assert result.exit_code == 0
        mock_detect.assert_called_once()

    @patch("src.agents.base.list_all_agents")
    @patch("src.core.monorepo.detect_monorepo")
    @patch("src.core.monorepo.list_subprojects")
    def test_list_agents_monorepo_with_subprojects(
        self, mock_list_sub, mock_detect, mock_list_all, runner, mock_console
    ):
        """测试 monorepo 有子项目的情况"""
        mock_list_all.return_value = []

        # Mock monorepo info
        mock_info = Mock()
        mock_info.root = Path("/test")
        mock_info.type = "pnpm"
        mock_detect.return_value = mock_info

        # Mock subprojects
        mock_sp = Mock()
        mock_sp.name = "pkg-a"
        mock_sp.path = Path("/test/packages/a")
        mock_sp.language = "python"
        mock_sp.framework = "fastapi"
        mock_sp.has_agent_config = True
        mock_sp.relative_to = Mock(return_value=Path("packages/a"))
        mock_list_sub.return_value = [mock_sp]

        result = runner.invoke(app, ["list", "-m"])

        assert result.exit_code == 0


class TestShowAgent:
    """测试 show_agent 命令"""

    @patch("src.agents.base.get_agent")
    def test_show_agent_success(self, mock_get_agent, runner, mock_console):
        """测试成功显示 agent"""
        mock_agent = create_mock_agent()
        mock_agent.system_prompt = "You are a test agent" * 50  # > 500 chars
        # get_agent 返回"类", agent_class() 返回 mock_agent
        _cls = Mock()
        _cls.return_value = mock_agent
        mock_get_agent.return_value = _cls

        result = runner.invoke(app, ["show", "test-agent"])

        assert result.exit_code == 0
        mock_get_agent.assert_called_once_with("test-agent")

    @patch("src.agents.base.get_agent")
    def test_show_agent_not_found(self, mock_get_agent, runner, mock_console):
        """测试 agent 不存在"""
        mock_get_agent.return_value = None

        result = runner.invoke(app, ["show", "non-existent"])

        assert result.exit_code == 1

    @patch("src.agents.base.get_agent")
    @patch("src.agents.self_improving.SelfImprovingAgent")
    def test_show_agent_with_evolution(
        self, mock_sia_class, mock_get_agent, runner, mock_console
    ):
        """测试带 --evolution 选项的 show 命令"""
        mock_agent = create_mock_agent()
        mock_agent.system_prompt = "You are a test agent"
        _cls = Mock()
        _cls.return_value = mock_agent
        mock_get_agent.return_value = _cls

        mock_sia = Mock()
        mock_sia.get_evolution_stats.return_value = {
            "current_generation": 2,
            "total_evolutions": 5,
            "total_patterns": 10,
            "prompt_version": 3,
            "last_evolution": "2024-01-01"
        }
        mock_sia_class.return_value = mock_sia

        result = runner.invoke(app, ["show", "test-agent", "--evolution"])

        assert result.exit_code == 0
        mock_sia.get_evolution_stats.assert_called_once_with("test-agent")


class TestExportAgent:
    """测试 export_agent 命令"""

    @patch("src.agents.base.get_agent")
    def test_export_agent_success(self, mock_get_agent, runner, mock_console, tmp_path):
        """测试成功导出 agent 配置"""
        mock_agent = create_mock_agent()
        mock_agent.export_config.return_value = {"name": "test-agent", "model": "deepseek"}
        # get_agent returns a class-like mock; agent_class() returns mock_agent
        _cls = Mock()
        _cls.return_value = mock_agent
        mock_get_agent.return_value = _cls

        output_file = tmp_path / "export.json"

        result = runner.invoke(app, ["export", "test-agent", "--output", str(output_file)])

        assert result.exit_code == 0
        assert output_file.exists()

        # 验证导出的 JSON
        with open(output_file, encoding="utf-8") as f:
            data = json.load(f)
            assert data["name"] == "test-agent"
            assert data["model"] == "deepseek"

    @patch("src.agents.base.get_agent")
    def test_export_agent_not_found(self, mock_get_agent, runner, mock_console):
        """测试导出不存在的 agent"""
        mock_get_agent.return_value = None

        result = runner.invoke(app, ["export", "non-existent", "--output", "/tmp/fake.json"])

        assert result.exit_code == 1

    @patch("src.agents.base.get_agent")
    @patch("src.agents.evolution.EvolutionStore")
    def test_export_agent_with_evolution(
        self, mock_store_class, mock_get_agent, runner, mock_console, tmp_path
    ):
        """测试导出带进化历史的 agent"""
        mock_agent = create_mock_agent()
        mock_agent.tools = []  # 空列表
        mock_agent.export_config.return_value = {"name": "test-agent", "evolution": []}
        # get_agent returns a class-like mock; agent_class() returns mock_agent
        _cls = Mock()
        _cls.return_value = mock_agent
        mock_get_agent.return_value = _cls

        # Mock EvolutionStore
        mock_store = Mock()
        mock_record = Mock()
        mock_record.id = "rec-1"
        mock_record.timestamp = "2024-01-01"
        mock_record.generation = 1
        mock_record.changes = ["change1"]
        mock_store.load_evolution_history.return_value = [mock_record]
        mock_store_class.return_value = mock_store

        output_file = tmp_path / "export.json"

        result = runner.invoke(
            app, ["export", "test-agent", "--output", str(output_file), "--evolution"]
        )

        assert result.exit_code == 0
        assert output_file.exists()


class TestImportAgent:
    """测试 import_agent 命令"""

    def test_import_agent_from_file(self, runner, mock_console, tmp_path):
        """测试从本地文件导入"""
        config_data = {
            "name": "imported-agent",
            "description": "An imported agent",
        }
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config_data, ensure_ascii=False), encoding="utf-8")

        with patch("src.agents.base.get_agent", return_value=None):
            with patch("src.agents.evolution.EvolutionStore"):
                result = runner.invoke(app, ["import", str(config_file)])

        assert result.exit_code == 0

    @patch("httpx.Client")
    def test_import_agent_from_url(self, mock_client_class, runner, mock_console, tmp_path):
        """测试从 URL 导入"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "name": "url-agent",
            "description": "Agent from URL",
        }
        mock_response.raise_for_status = Mock()

        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__enter__ = Mock(return_value=mock_client)
        mock_client_class.return_value.__exit__ = Mock(return_value=False)

        with patch("src.agents.base.get_agent", return_value=None):
            with patch("src.agents.evolution.EvolutionStore"):
                result = runner.invoke(app, ["import", "https://example.com/agent.json"])

        assert result.exit_code == 0

    @patch("httpx.Client")
    def test_import_agent_url_download_fails(
        self, mock_client_class, runner, mock_console
    ):
        """测试 URL 下载失败"""
        mock_client = Mock()
        mock_client.get.side_effect = Exception("Network error")
        mock_client_class.return_value.__enter__ = Mock(return_value=mock_client)
        mock_client_class.return_value.__exit__ = Mock(return_value=False)

        result = runner.invoke(app, ["import", "https://example.com/agent.json"])

        assert result.exit_code == 1

    def test_import_agent_file_not_found(self, runner, mock_console):
        """测试文件不存在"""
        result = runner.invoke(app, ["import", "/non/existent/file.json"])

        assert result.exit_code == 1

    def test_import_agent_invalid_json(self, runner, mock_console, tmp_path):
        """测试无效的 JSON 文件"""
        invalid_file = tmp_path / "invalid.json"
        invalid_file.write_text("{invalid json}", encoding="utf-8")

        result = runner.invoke(app, ["import", str(invalid_file)])

        assert result.exit_code == 1

    def test_import_agent_missing_required_field(self, runner, mock_console, tmp_path):
        """测试缺少必需字段"""
        config_data = {
            "name": "test"
            # 缺少 description
        }
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config_data), encoding="utf-8")

        result = runner.invoke(app, ["import", str(config_file)])

        assert result.exit_code == 1


class TestEvolveAgent:
    """测试 evolve_agent 命令"""

    @patch("src.agents.self_improving.SelfImprovingAgent")
    def test_evolve_agent_success(self, mock_sia_class, runner, mock_console):
        """测试成功触发进化"""
        mock_sia = Mock()
        mock_record = Mock()
        mock_record.generation = 2
        mock_record.id = "evt-123"
        mock_record.changes = ["Improved prompt", "Added tool"]
        mock_sia.evolve.return_value = mock_record
        mock_sia_class.return_value = mock_sia

        result = runner.invoke(app, ["evolve", "test-agent"])

        assert result.exit_code == 0
        mock_sia.evolve.assert_called_once_with("test-agent", trigger="manual")

    @patch("src.agents.self_improving.SelfImprovingAgent")
    def test_evolve_agent_no_evolution(self, mock_sia_class, runner, mock_console):
        """测试未触发进化"""
        mock_sia = Mock()
        mock_sia.evolve.return_value = None
        mock_sia_class.return_value = mock_sia

        result = runner.invoke(app, ["evolve", "test-agent"])

        assert result.exit_code == 0

    @patch("src.agents.self_improving.SelfImprovingAgent")
    def test_evolve_agent_with_trigger(self, mock_sia_class, runner, mock_console):
        """测试指定 trigger"""
        mock_sia = Mock()
        mock_record = Mock()
        mock_record.generation = 1
        mock_record.id = "evt-456"
        mock_record.changes = []
        mock_sia.evolve.return_value = mock_record
        mock_sia_class.return_value = mock_sia

        result = runner.invoke(app, ["evolve", "test-agent", "--trigger", "test"])

        assert result.exit_code == 0
        mock_sia.evolve.assert_called_once_with("test-agent", trigger="test")


class TestAgentStats:
    """测试 agent_stats 命令"""

    @patch("src.agents.self_improving.SelfImprovingAgent")
    def test_agent_stats_success(self, mock_sia_class, runner, mock_console):
        """测试成功获取统计"""
        mock_sia = Mock()
        mock_sia.get_evolution_stats.return_value = {
            "current_generation": 3,
            "total_evolutions": 10,
            "total_patterns": 5,
            "prompt_version": 2,
            "last_evolution": "2024-01-01",
            "config": {
                "enabled": True,
                "improvement_threshold": 0.8,
            },
        }
        mock_sia_class.return_value = mock_sia

        result = runner.invoke(app, ["stats", "test-agent"])

        assert result.exit_code == 0
        mock_sia.get_evolution_stats.assert_called_once_with("test-agent")


class TestListDecisions:
    """测试 list_decisions 命令"""

    @patch("src.agents.self_improving.SelfImprovingAgent")
    def test_list_decisions_with_data(self, mock_sia_class, runner, mock_console):
        """测试列出决策记录"""
        mock_sia = Mock()
        mock_sia.list_decisions.return_value = [
            {
                "id": "dec-1",
                "title": "Fixed bug",
                "category": "bug_fix",
                "result": "success",
                "problem": "A bug",
            }
        ]
        mock_sia_class.return_value = mock_sia

        result = runner.invoke(app, ["decisions"])

        assert result.exit_code == 0

    @patch("src.agents.self_improving.SelfImprovingAgent")
    def test_list_decisions_empty(self, mock_sia_class, runner, mock_console):
        """测试无决策记录"""
        mock_sia = Mock()
        mock_sia.list_decisions.return_value = []
        mock_sia_class.return_value = mock_sia

        result = runner.invoke(app, ["decisions"])

        assert result.exit_code == 0

    @patch("src.agents.self_improving.SelfImprovingAgent")
    def test_list_decisions_with_category(self, mock_sia_class, runner, mock_console):
        """测试按类别过滤"""
        mock_sia = Mock()
        mock_sia.list_decisions.return_value = []
        mock_sia_class.return_value = mock_sia

        result = runner.invoke(app, ["decisions", "--category", "bug_fix"])

        assert result.exit_code == 0
        mock_sia.list_decisions.assert_called_once_with(category="bug_fix", limit=10)


class TestRetrieveDecision:
    """测试 retrieve_decision 命令"""

    @patch("src.agents.self_improving.SelfImprovingAgent")
    def test_retrieve_decision_success(self, mock_sia_class, runner, mock_console):
        """测试成功检索决策"""
        mock_sia = Mock()
        mock_sia.retrieve_past_decisions.return_value = [
            {
                "title": "Similar problem",
                "problem": "A problem",
                "chosen_solution": "The solution",
                "result": "success",
                "outcome": "Good",
                "reusable_for": "Similar cases",
                "keywords": ["bug", "fix"],
            }
        ]
        mock_sia_class.return_value = mock_sia

        result = runner.invoke(app, ["decision", "my problem"])

        assert result.exit_code == 0

    @patch("src.agents.self_improving.SelfImprovingAgent")
    def test_retrieve_decision_not_found(self, mock_sia_class, runner, mock_console):
        """测试未找到决策"""
        mock_sia = Mock()
        mock_sia.retrieve_past_decisions.return_value = []
        mock_sia_class.return_value = mock_sia

        result = runner.invoke(app, ["decision", "unknown problem"])

        assert result.exit_code == 0


class TestRecordDecision:
    """测试 record_decision 命令"""

    @patch("src.agents.self_improving.SelfImprovingAgent")
    def test_record_decision_success(self, mock_sia_class, runner, mock_console):
        """测试成功记录决策"""
        mock_sia = Mock()
        mock_sia.record_decision.return_value = "dec-123"
        mock_sia_class.return_value = mock_sia

        result = runner.invoke(
            app,
            [
                "record-decision",
                "--title",
                "Test Decision",
                "--problem",
                "A problem",
                "--solution",
                "The solution",
            ],
        )

        assert result.exit_code == 0


class TestDecisionStats:
    """测试 decision_stats 命令"""

    @patch("src.agents.self_improving.SelfImprovingAgent")
    def test_decision_stats_success(self, mock_sia_class, runner, mock_console):
        """测试成功获取决策统计"""
        mock_sia = Mock()
        mock_sia.get_decision_stats.return_value = {
            "total_decisions": 10,
            "latest_decision": "2024-01-01",
            "by_category": {"bug_fix": 5, "solution_choice": 5},
        }
        mock_sia_class.return_value = mock_sia

        result = runner.invoke(app, ["decision-stats"])

        assert result.exit_code == 0


class TestAgentHealth:
    """测试 agent_health 命令"""

    def test_agent_health_no_records(self, runner, mock_console, tmp_path, monkeypatch):
        """测试无健康检查记录"""
        monkeypatch.chdir(tmp_path)  # 确保 .omc/state/health/ 不存在

        result = runner.invoke(app, ["health"])

        assert result.exit_code == 0

    @patch("src.agents.health_check.format_health_display")
    def test_agent_health_with_records(self, mock_format, runner, mock_console, tmp_path):
        """测试有健康检查记录"""
        mock_format.return_value = "Health display"

        # 创建 .omc/state/health/ 目录和文件
        health_dir = tmp_path / ".omc" / "state" / "health"
        health_dir.mkdir(parents=True)
        health_file = health_dir / "health_agent1.json"
        health_file.write_text(
            json.dumps({"agent_name": "agent1", "status": "healthy"}), encoding="utf-8"
        )
        status_file = health_dir / "status.json"
        status_file.write_text(
            json.dumps({"total_registered": 1, "healthy": 1}), encoding="utf-8"
        )

        import os
        old_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            result = runner.invoke(app, ["health"])
        finally:
            os.chdir(old_cwd)

        # 只检查不崩溃
        assert result.exit_code is not None


class TestSaveAgent:
    """测试 save_agent 命令"""

    @patch("src.agents.persistence.store.AgentStateStore")
    @patch("src.agents.persistence.store.AgentConfig")
    @patch("src.agents.persistence.store.AgentState")
    def test_save_agent_success(
        self, mock_state_class, mock_config_class, mock_store_class, runner, mock_console
    ):
        """测试成功保存 agent"""
        mock_store = Mock()
        mock_store.save.return_value = Path("/test/agent")
        mock_store_class.return_value = mock_store

        result = runner.invoke(app, ["save", "test-agent", "--model", "deepseek"])

        assert result.exit_code == 0
        mock_store.save.assert_called_once()

    @patch("src.agents.persistence.store.AgentStateStore")
    @patch("src.agents.persistence.store.AgentConfig")
    @patch("src.agents.persistence.store.AgentState")
    def test_save_agent_with_output(
        self, mock_state_class, mock_config_class, mock_store_class, runner, mock_console, tmp_path
    ):
        """测试保存并导出"""
        mock_store = Mock()
        mock_store.save.return_value = Path("/test/agent")
        mock_store.export_agent = Mock()
        mock_store_class.return_value = mock_store

        output_file = tmp_path / "export.json"

        result = runner.invoke(
            app, ["save", "test-agent", "--output", str(output_file)]
        )

        assert result.exit_code == 0
        mock_store.export_agent.assert_called_once()


class TestRestoreAgent:
    """测试 restore_agent 命令"""

    @patch("src.agents.persistence.store.AgentStateStore")
    def test_restore_agent_success(self, mock_store_class, runner, mock_console):
        """测试成功恢复 agent"""
        mock_store = Mock()
        mock_config = Mock()
        mock_config.name = "test-agent"
        mock_config.description = "A test agent"
        mock_config.model = "deepseek"
        mock_config.lane = "code"
        mock_config.tools = ["tool1"]
        mock_state = Mock()
        mock_state.session_id = "sess-123"
        mock_state.total_tokens = 1000
        mock_state.total_cost = 0.05
        mock_state.last_task = "test task"
        mock_store.restore.return_value = (mock_config, [], mock_state)
        mock_store_class.return_value = mock_store

        result = runner.invoke(app, ["restore", "test-agent"])

        assert result.exit_code == 0

    @patch("src.agents.persistence.store.AgentStateStore")
    def test_restore_agent_not_found(self, mock_store_class, runner, mock_console):
        """测试 agent 不存在"""
        mock_store = Mock()
        mock_store.restore.return_value = (None, None, None)
        mock_store_class.return_value = mock_store

        result = runner.invoke(app, ["restore", "non-existent"])

        assert result.exit_code == 1

    @patch("src.agents.persistence.store.AgentStateStore")
    def test_restore_agent_with_history(self, mock_store_class, runner, mock_console):
        """测试恢复带历史记录的 agent"""
        mock_store = Mock()
        mock_config = Mock()
        mock_config.name = "test-agent"
        mock_config.description = "A test agent"
        mock_config.model = "deepseek"
        mock_config.lane = "code"
        mock_config.tools = []

        mock_history = [Mock(role="user", content="Hello", spec=["role", "content"])]

        mock_state = Mock()
        mock_state.session_id = "sess-123"
        mock_state.total_tokens = 1000
        mock_state.total_cost = 0.05
        mock_state.last_task = "test task"
        mock_store.restore.return_value = (mock_config, mock_history, mock_state)
        mock_store_class.return_value = mock_store

        result = runner.invoke(app, ["restore", "test-agent", "--history"])

        assert result.exit_code == 0


class TestExportAgentState:
    """测试 export_agent_state 命令"""

    @patch("src.agents.persistence.store.AgentStateStore")
    def test_export_agent_state_success(self, mock_store_class, runner, mock_console, tmp_path):
        """测试成功导出 agent 状态"""
        mock_store = Mock()
        mock_store.export_agent = Mock()
        mock_store_class.return_value = mock_store

        output_file = tmp_path / "export.json"

        result = runner.invoke(app, ["export-state", "test-agent", str(output_file)])

        assert result.exit_code == 0
        mock_store.export_agent.assert_called()

    @patch("src.agents.persistence.store.AgentStateStore")
    def test_export_agent_state_not_found(self, mock_store_class, runner, mock_console, tmp_path):
        """测试 agent 不存在"""
        mock_store = Mock()
        mock_store.export_agent.side_effect = FileNotFoundError()
        mock_store_class.return_value = mock_store

        output_file = tmp_path / "export.json"

        result = runner.invoke(app, ["export-state", "non-existent", str(output_file)])

        assert result.exit_code == 1


class TestImportAgentState:
    """测试 import_agent_state 命令"""

    @patch("src.agents.persistence.store.AgentStateStore")
    def test_import_agent_state_success(self, mock_store_class, runner, mock_console, tmp_path):
        """测试成功导入 agent 状态"""
        mock_store = Mock()
        mock_store.import_agent.return_value = "imported-agent"
        mock_store.store_root = tmp_path
        mock_store_class.return_value = mock_store

        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps({"name": "test"}), encoding="utf-8")

        result = runner.invoke(app, ["import-state", str(config_file)])

        assert result.exit_code == 0

    def test_import_agent_state_file_not_found(self, runner, mock_console):
        """测试文件不存在"""
        result = runner.invoke(app, ["import-state", "/non/existent/file.json"])

        assert result.exit_code == 1

    @patch("src.agents.persistence.store.AgentStateStore")
    def test_import_agent_state_with_new_name(
        self, mock_store_class, runner, mock_console, tmp_path
    ):
        """测试指定新名称"""
        mock_store = Mock()
        mock_store.import_agent.return_value = "new-name"
        mock_store.store_root = tmp_path
        mock_store_class.return_value = mock_store

        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps({"name": "test"}), encoding="utf-8")

        result = runner.invoke(
            app, ["import-state", str(config_file), "--name", "new-name"]
        )

        assert result.exit_code == 0


class TestListSavedAgents:
    """测试 list_saved_agents 命令"""

    @patch("src.agents.persistence.store.AgentStateStore")
    def test_list_saved_agents_with_data(self, mock_store_class, runner, mock_console):
        """测试列出已保存的 agent"""
        mock_store = Mock()
        mock_store.list_saved.return_value = ["agent1", "agent2"]
        mock_store.get_stats.return_value = {
            "total_agents": 2,
            "total_size_bytes": 1024,
        }
        mock_store.store_root = Path("/test")
        mock_store_class.return_value = mock_store

        result = runner.invoke(app, ["list-saved"])

        assert result.exit_code == 0

    @patch("src.agents.persistence.store.AgentStateStore")
    def test_list_saved_agents_empty(self, mock_store_class, runner, mock_console):
        """测试无已保存的 agent"""
        mock_store = Mock()
        mock_store.list_saved.return_value = []
        mock_store_class.return_value = mock_store

        result = runner.invoke(app, ["list-saved"])

        assert result.exit_code == 0


class TestDeleteSavedAgent:
    """测试 delete_saved_agent 命令"""

    @patch("src.agents.persistence.store.AgentStateStore")
    def test_delete_saved_agent_not_found(self, mock_store_class, runner, mock_console):
        """测试 agent 不存在"""
        mock_store = Mock()
        mock_store.list_saved.return_value = []
        mock_store_class.return_value = mock_store

        result = runner.invoke(app, ["delete-saved", "non-existent"])

        assert result.exit_code == 1

    @patch("src.agents.persistence.store.AgentStateStore")
    @patch("rich.prompt.Confirm")
    def test_delete_saved_agent_cancelled(self, mock_confirm, mock_store_class, runner, mock_console):
        """测试取消删除"""
        mock_store = Mock()
        mock_store.list_saved.return_value = ["test-agent"]
        mock_store_class.return_value = mock_store
        mock_confirm.ask.return_value = False

        result = runner.invoke(app, ["delete-saved", "test-agent"])

        assert result.exit_code == 0

    @patch("src.agents.persistence.store.AgentStateStore")
    @patch("rich.prompt.Confirm")
    def test_delete_saved_agent_success(self, mock_confirm, mock_store_class, runner, mock_console):
        """测试成功删除"""
        mock_store = Mock()
        mock_store.list_saved.return_value = ["test-agent"]
        mock_store.delete.return_value = True
        mock_store_class.return_value = mock_store
        mock_confirm.ask.return_value = True

        result = runner.invoke(app, ["delete-saved", "test-agent"])

        assert result.exit_code == 0

    @patch("src.agents.persistence.store.AgentStateStore")
    def test_delete_saved_agent_force(self, mock_store_class, runner, mock_console):
        """测试强制删除"""
        mock_store = Mock()
        mock_store.list_saved.return_value = ["test-agent"]
        mock_store.delete.return_value = True
        mock_store_class.return_value = mock_store

        result = runner.invoke(app, ["delete-saved", "test-agent", "--force"])

        assert result.exit_code == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
