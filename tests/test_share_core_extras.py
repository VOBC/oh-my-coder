"""
Additional tests for share.py core functions covering edge cases:
- export_session with task_id not found (history_ prefix fallback)
- export_session JSON decode error
- import_session with no history data
- list_shares JSON decode error (corrupted file)
- delete_share not found (core function path)
"""
from __future__ import annotations

import json
from pathlib import Path

from src.commands.share import (
    _ensure_dir,
    _generate_share_id,
    _share_path,
    export_session,
    import_session,
    list_shares,
    delete_share,
    SHARE_DIR,
)


class TestExportEdgeCases:
    def test_export_task_not_found(self, tmp_path, monkeypatch):
        """Task ID not found in history dir."""
        monkeypatch.setattr(
            "src.commands.share.SHARE_DIR", tmp_path / "shares"
        )
        h_dir = tmp_path / "history"
        h_dir.mkdir()
        # Create some file to make it exist, but not the target
        (h_dir / "other.json").write_text("{}")
        result = export_session(task_id="no-such-task", history_dir=h_dir)
        assert result == {}

    def test_export_history_has_task_id(self, tmp_path, monkeypatch):
        """Task ID with history_ prefix still works."""
        monkeypatch.setattr(
            "src.commands.share.SHARE_DIR", tmp_path / "shares"
        )
        h_dir = tmp_path / "history"
        h_dir.mkdir()
        task_file = h_dir / "task_abc.json"
        task_file.write_text(
            json.dumps({"task_description": "test", "steps": []})
        )
        result = export_session(task_id="task_abc", history_dir=h_dir)
        assert result != {}
        assert "share_id" in result

    def test_export_json_decode_error(self, tmp_path, monkeypatch):
        """JSON decode error in history file."""
        monkeypatch.setattr(
            "src.commands.share.SHARE_DIR", tmp_path / "shares"
        )
        h_dir = tmp_path / "history"
        h_dir.mkdir()
        # Write invalid JSON
        (h_dir / "bad.json").write_text("not valid json {{{")
        result = export_session(history_dir=h_dir)
        assert result == {}

    def test_export_no_history_files(self, tmp_path, monkeypatch):
        """Empty history directory."""
        monkeypatch.setattr(
            "src.commands.share.SHARE_DIR", tmp_path / "shares"
        )
        h_dir = tmp_path / "history"
        h_dir.mkdir()
        result = export_session(history_dir=h_dir)
        assert result == {}

    def test_export_history_dir_not_found(self, tmp_path, monkeypatch):
        """History directory doesn't exist."""
        monkeypatch.setattr(
            "src.commands.share.SHARE_DIR", tmp_path / "shares"
        )
        result = export_session(history_dir=tmp_path / "nonexistent")
        assert result == {}


class TestImportEdgeCases:
    def test_import_nonexistent_share(self, tmp_path, monkeypatch):
        """Import share that doesn't exist."""
        monkeypatch.setattr(
            "src.commands.share.SHARE_DIR", tmp_path / "shares"
        )
        result = import_session("deadbeef")
        assert result == {}

    def test_import_no_history_data(self, tmp_path, monkeypatch):
        """Import share with no history data in session."""
        monkeypatch.setattr(
            "src.commands.share.SHARE_DIR", tmp_path / "shares"
        )
        _ensure_dir()
        sid = _generate_share_id()
        share_file = _share_path(sid)
        share_file.write_text(
            json.dumps({"share_id": sid, "version": 1, "session": {}})
        )
        result = import_session(sid)
        assert result == {}

    def test_import_corrupted_share(self, tmp_path, monkeypatch):
        """Import share with corrupted JSON."""
        monkeypatch.setattr(
            "src.commands.share.SHARE_DIR", tmp_path / "shares"
        )
        _ensure_dir()
        sid = _generate_share_id()
        share_file = _share_path(sid)
        share_file.write_text("not json {{{")
        result = import_session(sid)
        assert result == {}


class TestListEdgeCases:
    def test_list_corrupted_file(self, tmp_path, monkeypatch):
        """List shares with one corrupted file, should skip it."""
        monkeypatch.setattr(
            "src.commands.share.SHARE_DIR", tmp_path / "shares"
        )
        _ensure_dir()
        # Create a valid share
        sid = _generate_share_id()
        share_file1 = _share_path(sid)
        share_file1.write_text(
            json.dumps({
                "share_id": sid,
                "created_at": "2026-06-20T00:00:00",
                "expires_at": None,
                "tags": [],
                "session": {"history": {"steps": []}},
            })
        )
        # Create a corrupted share
        sid2 = _generate_share_id()
        share_file2 = _share_path(sid2)
        share_file2.write_text("corrupted {{{")

        result = list_shares()
        # Should only have the valid share
        assert len(result) == 1
        assert result[0]["share_id"] == sid

    def test_delete_nonexistent_core(self, tmp_path, monkeypatch):
        """Core delete_share with non-existent share."""
        monkeypatch.setattr(
            "src.commands.share.SHARE_DIR", tmp_path / "shares"
        )
        result = delete_share("nonexistent123")
        assert result is False
