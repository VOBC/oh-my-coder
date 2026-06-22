"""
Final edge-case tests for share.py to push from 97% to 100%.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from src.commands.share import (
    _ensure_dir,
    _generate_share_id,
    _share_path,
    get_share,
    export_session,
    SHARE_DIR,
)


class TestGetShareEdgeCases:
    def test_get_share_corrupted(self, tmp_path, monkeypatch):
        """get_share with corrupted JSON returns None."""
        monkeypatch.setattr(
            "src.commands.share.SHARE_DIR", tmp_path / "shares"
        )
        _ensure_dir()
        sid = "corrupt-01"
        share_file = _share_path(sid)
        share_file.write_text("{not json[[[")
        result = get_share(sid)
        assert result is None

    def test_get_share_not_found(self, tmp_path, monkeypatch):
        """get_share with non-existent file."""
        monkeypatch.setattr(
            "src.commands.share.SHARE_DIR", tmp_path / "shares"
        )
        _ensure_dir()
        result = get_share("no-such-id")
        assert result is None


class TestExportConfigEdgeCases:
    def test_export_with_corrupted_config(self, tmp_path, monkeypatch):
        """export_session handles corrupted config.json gracefully."""
        monkeypatch.setattr(
            "src.commands.share.SHARE_DIR", tmp_path / "shares"
        )
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        cfg_dir = tmp_path / ".omc"
        cfg_dir.mkdir(parents=True, exist_ok=True)
        (cfg_dir / "config.json").write_text("{not json[[[")
        h_dir = tmp_path / "history"
        h_dir.mkdir()
        (h_dir / "task.json").write_text(
            json.dumps({"task_description": "test", "steps": []})
        )
        result = export_session(history_dir=h_dir, include_config=True)
        assert "share_id" in result
        # Config should be absent because JSON was corrupted
        assert "config" not in result.get("session", {})


class TestShareListCLIExpires:
    def test_list_permanent_share(self):
        """CLI list with permanent share displays ♾️ 永久."""
        with patch("src.commands.share.list_shares") as mock_list:
            mock_list.return_value = [
                {
                    "share_id": "perm-123",
                    "created_at": "2026-06-20T00:00:00",
                    "expires_at": None,
                    "tags": [],
                    "task": "permanent task",
                    "steps": 3,
                }
            ]
            from typer.testing import CliRunner
            from src.commands.share import app as share_app
            result = CliRunner().invoke(share_app, ["list"])
            assert result.exit_code == 0
            assert "perm-123" in result.stdout

    def test_list_expired_share(self):
        """CLI list with expired share."""
        with patch("src.commands.share.list_shares") as mock_list:
            mock_list.return_value = [
                {
                    "share_id": "old-456",
                    "created_at": "2026-01-01T00:00:00",
                    "expires_at": "2026-01-02T00:00:00",
                    "tags": [],
                    "task": "expired task",
                    "steps": 1,
                }
            ]
            from typer.testing import CliRunner
            from src.commands.share import app as share_app
            result = CliRunner().invoke(share_app, ["list"])
            assert result.exit_code == 0
            assert "old-456" in result.stdout
