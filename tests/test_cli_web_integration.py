"""
CLI + Web 集成测试

测试 CLI 命令中调用 Web API 的场景（使用 mock）
"""

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from src.commands.cli_agent import app as cli_agent_app
from src.commands.cli_review import app as cli_review_app

runner = CliRunner()


class TestCLIAgentWebIntegration:
    """测试 cli_agent 的 Web API 调用"""

    @patch("src.commands.cli_agent.httpx.Client")
    def test_fetch_remote_source(self, mock_client):
        """测试从远程 URL 获取源代码"""
        mock_response = MagicMock()
        mock_response.text = "# Test Agent\nYou are a test assistant."
        mock_response.raise_for_status = MagicMock()
        mock_client.return_value.__enter__.return_value.get.return_value = mock_response

        result = runner.invoke(cli_agent_app, ["list"])
        assert result.exit_code == 0


class TestCLIReviewWebIntegration:
    """测试 cli_review 的 Web API 调用"""

    @patch("src.commands.cli_review.httpx.get")
    def test_fetch_pr_diff(self, mock_get):
        """测试从 GitHub API 获取 PR diff"""
        mock_response = MagicMock()
        mock_response.text = "diff --git a/file.py b/file.py\n@@ -1,3 +1,4 @@\n+new line"
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = runner.invoke(cli_review_app, ["123"])
        assert result.exit_code == 0
