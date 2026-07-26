"""
Tests for coverage gaps in src/commands/cli_review.py
Covers: lines 105-107, 142-143, 290-292
"""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from src.commands.cli_review import (
    _fetch_pr_diff,
    _read_local_diff,
    _review_with_llm,
    app,
)

runner = CliRunner()


class TestFetchPrDiffGaps:
    """Lines 105-107: httpx.get exception after FileNotFoundError (gh not installed)"""

    @patch("src.commands.cli_review.subprocess.run")
    def test_gh_not_found_httpx_non_200(self, mock_run):
        """gh not installed (FileNotFoundError), httpx.get returns non-200 → line 105"""
        mock_run.side_effect = FileNotFoundError()

        with patch("src.commands.cli_review.httpx.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_get.return_value = mock_response
            success, msg = _fetch_pr_diff(
                "https://github.com/owner/repo/pull/123"
            )
            assert success is False
            assert "无法获取 PR diff" in msg
            assert "404" in msg

    @patch("src.commands.cli_review.subprocess.run")
    def test_gh_not_found_httpx_raises(self, mock_run):
        """gh not installed (FileNotFoundError), httpx.get raises exception → line 106-107"""
        mock_run.side_effect = FileNotFoundError()

        with patch("src.commands.cli_review.httpx.get") as mock_get:
            mock_get.side_effect = Exception("Connection refused")
            success, msg = _fetch_pr_diff(
                "https://github.com/owner/repo/pull/123"
            )
            assert success is False
            assert "网络请求失败" in msg


class TestReadLocalDiffGaps:
    """Line 142-143: git diff subprocess exception"""

    @patch("src.commands.cli_review.subprocess.run")
    def test_git_diff_subprocess_exception(self, mock_run):
        """git diff subprocess.run raises exception → handled gracefully"""
        mock_run.side_effect = OSError("git not found")
        success, msg = _read_local_diff("HEAD~1")
        assert success is False
        assert "执行 git diff 失败" in msg


class TestReviewWithLLMGap:
    """Line 290-292: _review_with_llm function call (integration)"""

    @patch("src.commands.cli_review._init_router")
    @patch("src.commands.cli_review._load_system_prompt")
    def test_review_with_llm_success(self, mock_load_prompt, mock_init_router):
        """_review_with_llm returns content from LLM (line 290 path)"""
        mock_load_prompt.return_value = "You are a code reviewer."
        mock_router = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "# Review\n\nAll good!"
        mock_router.complete = AsyncMock(return_value=mock_response)
        mock_init_router.return_value = mock_router

        result = asyncio.run(_review_with_llm("diff content", "deepseek"))
        assert "# Review" in result
        mock_router.complete.assert_called_once()

    @patch("src.commands.cli_review._init_router")
    @patch("src.commands.cli_review._load_system_prompt")
    def test_review_with_llm_router_exception(self, mock_load_prompt, mock_init_router):
        """_review_with_llm handles router.complete exception"""
        mock_load_prompt.return_value = "You are a code reviewer."
        mock_router = MagicMock()
        mock_router.complete = AsyncMock(side_effect=RuntimeError("Router failed"))
        mock_init_router.return_value = mock_router

        result = asyncio.run(_review_with_llm("diff content"))
        assert "❌ LLM 调用失败" in result


class TestCLIIntegrationGaps:
    """Lines 290-292 covered via CLI integration"""

    @patch("src.commands.cli_review._check_env")
    @patch("src.commands.cli_review._fetch_pr_diff")
    @patch("src.commands.cli_review._review_with_llm")
    def test_pr_review_llm_call_path(self, mock_review_llm, mock_fetch, mock_check):
        """Line 290: _review_with_llm(...) called in review_pr via asyncio.run"""
        mock_check.return_value = True
        mock_fetch.return_value = (True, "diff content")
        # Mock _review_with_llm directly (it's called via asyncio.run internally)
        mock_review_llm.return_value = "LLM review report"

        result = runner.invoke(
            app, ["pr", "https://github.com/owner/repo/pull/123"]
        )
        assert result.exit_code == 0
        mock_review_llm.assert_called()

    @patch("src.commands.cli_review._check_env")
    @patch("src.commands.cli_review._read_local_diff")
    @patch("src.commands.cli_review._review_with_llm")
    def test_diff_review_llm_call_path(self, mock_review_llm, mock_read, mock_check):
        """Line 290: _review_with_llm(...) called in review_diff via asyncio.run"""
        mock_check.return_value = True
        mock_read.return_value = (True, "diff content")
        mock_review_llm.return_value = "LLM review report"

        result = runner.invoke(app, ["diff", "HEAD~1"])
        assert result.exit_code == 0
        mock_review_llm.assert_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
