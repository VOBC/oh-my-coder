"""
CLI-level tests for share.py commands (share_create, share_import,
share_list, share_delete, share_show).
"""
from __future__ import annotations

import json
from unittest.mock import Mock, patch

from typer.testing import CliRunner

from src.commands.share import app

runner = CliRunner()

SAMPLE_SHARE = {
    "share_id": "abc12345",
    "version": 1,
    "created_at": "2026-01-01T00:00:00",
    "expires_at": None,
    "tags": ["demo"],
    "session": {
        "history": {
            "task_description": "test task",
            "workflow_name": "build",
            "steps": [{"id": "s1"}, {"id": "s2"}],
            "total_tokens": 5000,
            "total_cost": 0.003,
        },
        "config": {"model": "gpt-4"},
    },
}


# ── share_create CLI ───────────────────────────────────────────────────


class TestShareCreateCLI:
    @patch("src.commands.share.export_session")
    def test_create_default(self, mock_export):
        mock_export.return_value = SAMPLE_SHARE
        result = runner.invoke(app, ["create"])
        assert result.exit_code == 0
        assert "abc12345" in result.stdout
        mock_export.assert_called_once()

    @patch("src.commands.share.export_session")
    def test_create_with_tags(self, mock_export):
        mock_export.return_value = SAMPLE_SHARE
        result = runner.invoke(app, ["create", "--tags", "bug,fix"])
        assert result.exit_code == 0
        mock_export.assert_called_once()
        call_args = mock_export.call_args[1]
        assert call_args["tags"] == ["bug", "fix"]

    @patch("src.commands.share.export_session")
    def test_create_no_config(self, mock_export):
        mock_export.return_value = SAMPLE_SHARE
        result = runner.invoke(app, ["create", "--no-config"])
        assert result.exit_code == 0
        call_args = mock_export.call_args[1]
        assert call_args["include_config"] is False

    @patch("src.commands.share.export_session")
    def test_create_with_expires(self, mock_export):
        mock_export.return_value = SAMPLE_SHARE
        result = runner.invoke(app, ["create", "--expires", "24"])
        assert result.exit_code == 0
        call_args = mock_export.call_args[1]
        assert call_args["expires_hours"] == 24

    @patch("src.commands.share.export_session")
    def test_create_with_task_id(self, mock_export):
        mock_export.return_value = SAMPLE_SHARE
        result = runner.invoke(app, ["create", "--task", "task-123"])
        assert result.exit_code == 0
        call_args = mock_export.call_args[1]
        assert call_args["task_id"] == "task-123"

    @patch("src.commands.share.export_session")
    def test_create_no_result(self, mock_export):
        """When export_session returns empty dict, no Panel shown."""
        mock_export.return_value = {}
        result = runner.invoke(app, ["create"])
        assert result.exit_code == 0
        assert "分享已创建" not in result.stdout


# ── share_import CLI ───────────────────────────────────────────────────


class TestShareImportCLI:
    @patch("src.commands.share.import_session")
    def test_import_success(self, mock_import):
        mock_import.return_value = {"history_id": "h12345"}
        result = runner.invoke(app, ["import", "abc12345"])
        assert result.exit_code == 0
        assert "h12345" in result.stdout

    @patch("src.commands.share.import_session")
    def test_import_no_result(self, mock_import):
        mock_import.return_value = {}
        result = runner.invoke(app, ["import", "dead"])
        assert result.exit_code == 0
        assert "会话已导入" not in result.stdout


# ── share_list CLI ─────────────────────────────────────────────────────


class TestShareListCLI:
    @patch("src.commands.share.list_shares")
    def test_list_empty(self, mock_list):
        mock_list.return_value = []
        result = runner.invoke(app, ["list"])
        assert result.exit_code == 0
        assert "暂无分享记录" in result.stdout

    @patch("src.commands.share.list_shares")
    def test_list_with_shares(self, mock_list):
        mock_list.return_value = [
            {
                "share_id": "abc123",
                "created_at": "2026-01-01T00:00:00",
                "expires_at": None,
                "tags": ["demo"],
                "task": "test task",
                "steps": 5,
            }
        ]
        result = runner.invoke(app, ["list"])
        assert result.exit_code == 0
        assert "abc123" in result.stdout
        assert "test task" in result.stdout
        assert "5" in result.stdout


# ── share_delete CLI ───────────────────────────────────────────────────


class TestShareDeleteCLI:
    @patch("src.commands.share.delete_share")
    def test_delete(self, mock_delete):
        mock_delete.return_value = True
        result = runner.invoke(app, ["delete", "abc123"])
        assert result.exit_code == 0

    @patch("src.commands.share.delete_share")
    def test_delete_not_found(self, mock_delete):
        mock_delete.return_value = False
        result = runner.invoke(app, ["delete", "nonexist"])
        assert result.exit_code == 0


# ── share_show CLI ─────────────────────────────────────────────────────


class TestShareShowCLI:
    @patch("src.commands.share.get_share")
    def test_show_not_found(self, mock_get):
        mock_get.return_value = None
        result = runner.invoke(app, ["show", "nonexist"])
        assert result.exit_code == 0
        assert "分享不存在" in result.stdout

    @patch("src.commands.share.get_share")
    def test_show_full_details(self, mock_get):
        mock_get.return_value = SAMPLE_SHARE
        result = runner.invoke(app, ["show", "abc12345"])
        assert result.exit_code == 0
        assert "abc12345" in result.stdout
        assert "test task" in result.stdout
        assert "build" in result.stdout
        assert "2" in result.stdout  # steps
        assert "5000" in result.stdout  # tokens
        assert "0.0030" in result.stdout  # cost
        assert "是" in result.stdout  # has config

    @patch("src.commands.share.get_share")
    def test_show_no_config(self, mock_get):
        data = dict(SAMPLE_SHARE)
        del data["session"]["config"]
        mock_get.return_value = data
        result = runner.invoke(app, ["show", "abc12345"])
        assert result.exit_code == 0
        assert "否" in result.stdout  # no config

    @patch("src.commands.share.get_share")
    def test_show_expired(self, mock_get):
        data = dict(SAMPLE_SHARE)
        data["expires_at"] = "2025-01-01T00:00:00"
        mock_get.return_value = data
        result = runner.invoke(app, ["show", "abc12345"])
        assert result.exit_code == 0
        assert "2025" in result.stdout

    @patch("src.commands.share.get_share")
    def test_show_minimal_fields(self, mock_get):
        """Show with minimal history data"""
        mock_get.return_value = {
            "share_id": "min",
            "version": 1,
            "created_at": "2026-01-01T00:00:00",
            "expires_at": None,
            "tags": [],
            "session": {"history": {}},
        }
        result = runner.invoke(app, ["show", "min"])
        assert result.exit_code == 0
        assert "min" in result.stdout
