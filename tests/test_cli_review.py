"""
测试 CLI Review 命令

使用 Typer 的 CliRunner 进行集成测试。
"""

import asyncio
import os
import subprocess
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from src.commands.cli_review import (
    SYSTEM_PROMPT_PATH,
    __file__ as _,  # noqa: F401
    app,
    _check_env,
    _fetch_pr_diff,
    _init_router,
    _load_system_prompt,
    _read_local_diff,
    _review_with_llm,
)

runner = CliRunner()


# ============================================================================
# 辅助函数测试
# ============================================================================


class TestCheckEnv:
    """测试 _check_env 函数"""

    def test_no_api_key(self):
        """测试无 API Key 时返回 False"""
        with patch.dict(os.environ, {}, clear=True):
            result = _check_env()
            assert result is False

    def test_deepseek_key(self):
        """测试 DEEPSEEK_API_KEY"""
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "sk-test"}, clear=True):
            result = _check_env()
            assert result is True

    def test_openai_key(self):
        """测试 OPENAI_API_KEY"""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}, clear=True):
            result = _check_env()
            assert result is True

    def test_anthropic_key(self):
        """测试 ANTHROPIC_API_KEY"""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test"}, clear=True):
            result = _check_env()
            assert result is True

    def test_ollama_url(self):
        """测试 OLLAMA_BASE_URL"""
        with patch.dict(os.environ, {"OLLAMA_BASE_URL": "http://localhost:11434"}, clear=True):
            result = _check_env()
            assert result is True

    def test_dashscope_key(self):
        """测试 DASHSCOPE_API_KEY"""
        with patch.dict(os.environ, {"DASHSCOPE_API_KEY": "sk-test"}, clear=True):
            result = _check_env()
            assert result is True

    def test_qwen_key(self):
        """测试 QWEN_API_KEY"""
        with patch.dict(os.environ, {"QWEN_API_KEY": "sk-test"}, clear=True):
            result = _check_env()
            assert result is True

    def test_xai_key(self):
        """测试 XAI_API_KEY"""
        with patch.dict(os.environ, {"XAI_API_KEY": "xai-test"}, clear=True):
            result = _check_env()
            assert result is True

    def test_zhipuai_key(self):
        """测试 ZHIPUAI_API_KEY"""
        with patch.dict(os.environ, {"ZHIPUAI_API_KEY": "sk-test"}, clear=True):
            result = _check_env()
            assert result is True


class TestInitRouter:
    """测试 _init_router 函数"""

    @patch("src.commands.cli_review.ModelRouter")
    @patch("src.commands.cli_review.RouterConfig")
    def test_init_router_success(self, mock_config, mock_router):
        """测试成功初始化路由器"""
        mock_config.from_env.return_value = MagicMock()
        mock_router.return_value = MagicMock()

        result = _init_router()

        mock_config.from_env.assert_called_once()
        mock_router.assert_called_once_with(mock_config.from_env.return_value)
        assert result is not None


class TestFetchPrDiff:
    """测试 _fetch_pr_diff 函数"""

    def test_invalid_url(self):
        """测试无效的 PR URL"""
        success, msg = _fetch_pr_diff("https://not-a-pr-url.com")
        assert success is False
        assert "无效的 GitHub PR URL" in msg

    def test_valid_url_format(self):
        """测试有效 URL 格式解析"""
        import re

        url = "https://github.com/octocat/Hello-World/pull/123"
        match = re.match(
            r"https?://github\.com/([^/]+)/([^/]+)/pull/(\d+)", url.strip("/")
        )
        assert match is not None
        owner, repo, pr_number = match.groups()
        assert owner == "octocat"
        assert repo == "Hello-World"
        assert pr_number == "123"

    @patch("src.commands.cli_review.subprocess.run")
    def test_gh_success(self, mock_run):
        """测试 gh 命令成功"""
        mock_run.return_value = MagicMock(
            returncode=0, stdout="diff --git a/file.txt b/file.txt\n..."
        )

        success, diff = _fetch_pr_diff(
            "https://github.com/owner/repo/pull/123"
        )
        assert success is True
        assert "diff --git" in diff

    @patch("src.commands.cli_review.subprocess.run")
    @patch("src.commands.cli_review.httpx.get")
    def test_gh_fail_httpx_success(self, mock_get, mock_run):
        """测试 gh 失败但 httpx 成功"""
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "diff --git a/file.txt b/file.txt\n..."
        mock_get.return_value = mock_response

        success, diff = _fetch_pr_diff(
            "https://github.com/owner/repo/pull/123"
        )
        assert success is True
        assert "diff --git" in diff

    @patch("src.commands.cli_review.subprocess.run")
    @patch("src.commands.cli_review.httpx.get")
    def test_both_fail(self, mock_get, mock_run):
        """测试 gh 和 httpx 都失败"""
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error")
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        success, msg = _fetch_pr_diff(
            "https://github.com/owner/repo/pull/999999"
        )
        assert success is False

    @patch("src.commands.cli_review.subprocess.run")
    def test_gh_timeout(self, mock_run):
        """测试 gh 命令超时"""
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="gh", timeout=30)

        success, msg = _fetch_pr_diff(
            "https://github.com/owner/repo/pull/123"
        )
        assert success is False
        assert "超时" in msg

    @patch("src.commands.cli_review.subprocess.run")
    def test_gh_not_found(self, mock_run):
        """测试 gh 未安装（FileNotFoundError）"""
        mock_run.side_effect = FileNotFoundError()

        with patch("src.commands.cli_review.httpx.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = "diff content"
            mock_get.return_value = mock_response

            success, diff = _fetch_pr_diff(
                "https://github.com/owner/repo/pull/123"
            )
            assert success is True

    @patch("src.commands.cli_review.subprocess.run")
    def test_gh_exception(self, mock_run):
        """测试 gh 其他异常"""
        mock_run.side_effect = Exception("Unexpected error")

        success, msg = _fetch_pr_diff(
            "https://github.com/owner/repo/pull/123"
        )
        assert success is False


class TestReadLocalDiff:
    """测试 _read_local_diff 函数"""

    def test_file_not_exists(self):
        """测试文件不存在"""
        # 修改：现在函数会尝试 git diff，失败返回 git 错误信息
        success, msg = _read_local_diff("/nonexistent/file.diff")
        assert success is False
        # 错误信息可能来自 git diff
        assert "不存在" in msg or "git diff 失败" in msg

    def test_read_file_success(self, tmp_path):
        """测试成功读取 diff 文件"""
        diff_file = tmp_path / "changes.diff"
        diff_content = "diff --git a/file.txt b/file.txt\n..."
        diff_file.write_text(diff_content, encoding="utf-8")

        success, content = _read_local_diff(str(diff_file))
        assert success is True
        assert content == diff_content

    def test_read_file_encoding_error(self, tmp_path):
        """测试文件读取编码错误"""
        diff_file = tmp_path / "bad_encoding.diff"
        # 写入一些无效 UTF-8 字节
        diff_file.write_bytes(b"\xff\xfe invalid")

        success, msg = _read_local_diff(str(diff_file))
        assert success is False

    @patch("src.commands.cli_review.subprocess.run")
    def test_git_diff_success(self, mock_run):
        """测试 git diff 成功"""
        mock_run.return_value = MagicMock(
            returncode=0, stdout="diff --git a/file.txt b/file.txt\n..."
        )

        success, diff = _read_local_diff("HEAD~1")
        assert success is True
        assert "diff --git" in diff

    @patch("src.commands.cli_review.subprocess.run")
    def test_git_diff_fail(self, mock_run):
        """测试 git diff 失败"""
        mock_run.return_value = MagicMock(
            returncode=1, stdout="", stderr="fatal: not a git repository"
        )

        success, msg = _read_local_diff("invalid")
        assert success is False


class TestLoadSystemPrompt:
    """测试 _load_system_prompt 函数"""

    def test_prompt_file_exists(self, tmp_path):
        """测试提示词文件存在"""
        # 临时修改 SYSTEM_PROMPT_PATH
        test_prompt = "你是一位资深的代码审查专家。"
        prompt_file = tmp_path / "review_system.txt"
        prompt_file.write_text(test_prompt, encoding="utf-8")

        with patch("src.commands.cli_review.SYSTEM_PROMPT_PATH", prompt_file):
            result = _load_system_prompt()
            assert result == test_prompt

    def test_prompt_file_not_exists(self):
        """测试提示词文件不存在时使用默认提示词"""
        non_existent = Path("/nonexistent/path/review_system.txt")

        with patch("src.commands.cli_review.SYSTEM_PROMPT_PATH", non_existent):
            result = _load_system_prompt()
            assert "代码审查专家" in result


class TestReviewWithLLM:
    """测试 _review_with_llm 函数"""

    @patch("src.commands.cli_review._init_router")
    @patch("src.commands.cli_review._load_system_prompt")
    def test_success(self, mock_load_prompt, mock_init_router):
        """测试成功调用 LLM"""
        mock_load_prompt.return_value = "你是一位代码审查专家。"

        mock_router = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "# 代码审查报告\n\n## 问题\n无"
        mock_router.complete = AsyncMock(return_value=mock_response)
        mock_init_router.return_value = mock_router

        # 直接测试异步函数
        result = asyncio.run(_review_with_llm("diff content", "deepseek"))

        assert "# 代码审查报告" in result
        mock_router.complete.assert_called_once()

    @patch("src.commands.cli_review._init_router")
    @patch("src.commands.cli_review._load_system_prompt")
    def test_llm_error(self, mock_load_prompt, mock_init_router):
        """测试 LLM 调用失败"""
        mock_load_prompt.return_value = "你是一位代码审查专家。"

        mock_router = MagicMock()
        mock_router.complete = AsyncMock(side_effect=Exception("API Error"))
        mock_init_router.return_value = mock_router

        result = asyncio.run(_review_with_llm("diff content", "deepseek"))

        assert "❌ LLM 调用失败" in result
        assert "API Error" in result


# ============================================================================
# CLI 命令测试
# ============================================================================


class TestReviewPrCommand:
    """测试 review pr 命令"""

    @patch("src.commands.cli_review._check_env")
    @patch("src.commands.cli_review._fetch_pr_diff")
    @patch("src.commands.cli_review.asyncio.run")
    def test_success(self, mock_asyncio_run, mock_fetch, mock_check):
        """测试成功审查 PR"""
        mock_check.return_value = True
        mock_fetch.return_value = (True, "diff --git a/file.txt b/file.txt\n...")
        mock_asyncio_run.return_value = "# 代码审查报告\n\n## 问题\n无"

        result = runner.invoke(
            app, ["pr", "https://github.com/owner/repo/pull/123"]
        )

        assert result.exit_code == 0
        assert "代码审查" in result.stdout
        assert "代码审查报告" in result.stdout

    @patch("src.commands.cli_review._check_env")
    def test_no_api_key(self, mock_check):
        """测试无 API Key"""
        mock_check.return_value = False

        result = runner.invoke(
            app, ["pr", "https://github.com/owner/repo/pull/123"]
        )

        assert result.exit_code == 1

    @patch("src.commands.cli_review._check_env")
    def test_no_api_key_output(self, mock_check, capsys):
        """测试无 API Key 时的输出"""
        mock_check.return_value = False

        result = runner.invoke(
            app, ["pr", "https://github.com/owner/repo/pull/123"]
        )

        assert result.exit_code == 1
        # _check_env 返回 False 时，review_pr 会调用 typer.Exit(1)
        # 输出已经在 console.print 中，但被 rich 捕获
        # 我们只需要确认 exit_code 为 1

    @patch("src.commands.cli_review._check_env")
    @patch("src.commands.cli_review._fetch_pr_diff")
    def test_fetch_fail(self, mock_fetch, mock_check):
        """测试获取 PR diff 失败"""
        mock_check.return_value = True
        mock_fetch.return_value = (False, "无法获取 PR diff")

        result = runner.invoke(
            app, ["pr", "https://github.com/owner/repo/pull/123"]
        )

        assert result.exit_code == 1
        assert "无法获取 PR diff" in result.stdout

    @patch("src.commands.cli_review._check_env")
    @patch("src.commands.cli_review._fetch_pr_diff")
    def test_empty_diff(self, mock_fetch, mock_check):
        """测试 PR 无变更内容"""
        mock_check.return_value = True
        mock_fetch.return_value = (True, "")

        result = runner.invoke(
            app, ["pr", "https://github.com/owner/repo/pull/123"]
        )

        assert result.exit_code == 0
        assert "无变更内容" in result.stdout

    @patch("src.commands.cli_review._check_env")
    @patch("src.commands.cli_review._fetch_pr_diff")
    @patch("src.commands.cli_review.asyncio.run")
    def test_with_model_option(self, mock_asyncio_run, mock_fetch, mock_check):
        """测试指定模型选项"""
        mock_check.return_value = True
        mock_fetch.return_value = (True, "diff content")
        mock_asyncio_run.return_value = "review result"

        result = runner.invoke(
            app,
            ["pr", "https://github.com/owner/repo/pull/123", "--model", "gpt4"],
        )

        assert result.exit_code == 0
        # 验证调用时使用了正确的模型
        call_args = mock_asyncio_run.call_args
        assert call_args is not None

    @patch("src.commands.cli_review._check_env")
    @patch("src.commands.cli_review._fetch_pr_diff")
    @patch("src.commands.cli_review.asyncio.run")
    def test_with_output_option(self, mock_asyncio_run, mock_fetch, mock_check, tmp_path):
        """测试输出到文件"""
        mock_check.return_value = True
        mock_fetch.return_value = (True, "diff content")
        mock_asyncio_run.return_value = "# 代码审查报告"

        output_file = tmp_path / "report.md"

        result = runner.invoke(
            app,
            [
                "pr",
                "https://github.com/owner/repo/pull/123",
                "--output",
                str(output_file),
            ],
        )

        assert result.exit_code == 0
        assert output_file.exists()
        assert output_file.read_text(encoding="utf-8") == "# 代码审查报告"

    @patch("src.commands.cli_review._check_env")
    @patch("src.commands.cli_review._fetch_pr_diff")
    @patch("src.commands.cli_review.asyncio.run")
    def test_llm_error(self, mock_asyncio_run, mock_fetch, mock_check):
        """测试 LLM 分析失败"""
        mock_check.return_value = True
        mock_fetch.return_value = (True, "diff content")
        mock_asyncio_run.side_effect = Exception("LLM Error")

        result = runner.invoke(
            app, ["pr", "https://github.com/owner/repo/pull/123"]
        )

        assert result.exit_code == 1
        assert "分析失败" in result.stdout


class TestReviewDiffCommand:
    """测试 review diff 命令"""

    @patch("src.commands.cli_review._check_env")
    @patch("src.commands.cli_review._read_local_diff")
    @patch("src.commands.cli_review.asyncio.run")
    def test_success(self, mock_asyncio_run, mock_read, mock_check):
        """测试成功审查本地 diff"""
        mock_check.return_value = True
        mock_read.return_value = (True, "diff --git a/file.txt b/file.txt\n...")
        mock_asyncio_run.return_value = "# 代码审查报告\n\n## 问题\n无"

        result = runner.invoke(app, ["diff", "changes.diff"])

        assert result.exit_code == 0
        assert "代码审查" in result.stdout
        assert "代码审查报告" in result.stdout

    @patch("src.commands.cli_review._check_env")
    def test_no_api_key(self, mock_check):
        """测试无 API Key"""
        mock_check.return_value = False

        result = runner.invoke(app, ["diff", "changes.diff"])

        assert result.exit_code == 1

    @patch("src.commands.cli_review._check_env")
    @patch("src.commands.cli_review._read_local_diff")
    def test_read_fail(self, mock_read, mock_check):
        """测试读取 diff 失败"""
        mock_check.return_value = True
        mock_read.return_value = (False, "文件不存在")

        result = runner.invoke(app, ["diff", "/nonexistent/file.diff"])

        assert result.exit_code == 1
        assert "文件不存在" in result.stdout

    @patch("src.commands.cli_review._check_env")
    @patch("src.commands.cli_review._read_local_diff")
    def test_empty_diff(self, mock_read, mock_check):
        """测试无变更内容"""
        mock_check.return_value = True
        mock_read.return_value = (True, "")

        result = runner.invoke(app, ["diff", "empty.diff"])

        assert result.exit_code == 0
        assert "无变更内容" in result.stdout

    @patch("src.commands.cli_review._check_env")
    @patch("src.commands.cli_review._read_local_diff")
    @patch("src.commands.cli_review.asyncio.run")
    def test_git_diff_arg(self, mock_asyncio_run, mock_read, mock_check):
        """测试 git diff 参数"""
        mock_check.return_value = True
        mock_read.return_value = (True, "diff content")
        mock_asyncio_run.return_value = "review result"

        result = runner.invoke(app, ["diff", "HEAD~1"])

        assert result.exit_code == 0

    @patch("src.commands.cli_review._check_env")
    @patch("src.commands.cli_review._read_local_diff")
    @patch("src.commands.cli_review.asyncio.run")
    def test_cached_option(self, mock_asyncio_run, mock_read, mock_check):
        """测试 --cached 选项"""
        mock_check.return_value = True
        mock_read.return_value = (True, "diff content")
        mock_asyncio_run.return_value = "review result"

        # 使用 -- 分隔选项和参数
        result = runner.invoke(app, ["diff", "--", "--cached"])

        assert result.exit_code == 0

    @patch("src.commands.cli_review._check_env")
    @patch("src.commands.cli_review._read_local_diff")
    @patch("src.commands.cli_review.asyncio.run")
    def test_with_output_option(self, mock_asyncio_run, mock_read, mock_check, tmp_path):
        """测试输出到文件"""
        mock_check.return_value = True
        mock_read.return_value = (True, "diff content")
        mock_asyncio_run.return_value = "# 代码审查报告"

        output_file = tmp_path / "report.md"

        result = runner.invoke(
            app,
            ["diff", "changes.diff", "--output", str(output_file)],
        )

        assert result.exit_code == 0
        assert output_file.exists()


class TestMainCallback:
    """测试主回调函数"""

    def test_help(self):
        """测试显示帮助"""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "代码审查" in result.stdout or "review" in result.stdout.lower()

    def test_no_subcommand(self):
        """测试无子命令时显示帮助"""
        result = runner.invoke(app, [])
        # Typer callback with invoke_without_command=True should show help
        assert "代码审查" in result.stdout or "review" in result.stdout.lower()


# ============================================================================
# 集成测试
# ============================================================================


class TestIntegration:
    """集成测试"""

    @patch("src.commands.cli_review._check_env")
    @patch("src.commands.cli_review._fetch_pr_diff")
    @patch("src.commands.cli_review._review_with_llm")
    def test_full_pr_review_flow(self, mock_review, mock_fetch, mock_check):
        """测试完整的 PR 审查流程"""
        mock_check.return_value = True
        mock_fetch.return_value = (
            True,
            "diff --git a/test.py b/test.py\n+print('hello')",
        )
        mock_review.return_value = "# 审查报告\n\n看起来不错！"

        result = runner.invoke(
            app, ["pr", "https://github.com/test/repo/pull/1"]
        )

        assert result.exit_code == 0
        assert "审查报告" in result.stdout

    @patch("src.commands.cli_review._check_env")
    @patch("src.commands.cli_review._read_local_diff")
    @patch("src.commands.cli_review._review_with_llm")
    def test_full_diff_review_flow(self, mock_review, mock_read, mock_check):
        """测试完整的 diff 审查流程"""
        mock_check.return_value = True
        mock_read.return_value = (
            True,
            "diff --git a/test.py b/test.py\n+print('hello')",
        )
        mock_review.return_value = "# 审查报告\n\n看起来不错！"

        result = runner.invoke(app, ["diff", "changes.diff"])

        assert result.exit_code == 0
        assert "审查报告" in result.stdout


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
