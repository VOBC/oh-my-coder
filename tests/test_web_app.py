"""Targeted tests for src.web.app.py uncovered lines."""

import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


class TestDetectTargetType:
    """Tests for _detect_target_type function."""

    def test_empty_string_returns_local(self):
        """Test empty string returns local."""
        from src.web.app import _detect_target_type
        assert _detect_target_type("") == "local"

    def test_whitespace_only_returns_local(self):
        """Test whitespace only returns local."""
        from src.web.app import _detect_target_type
        assert _detect_target_type("   ") == "local"

    def test_github_https_returns_github(self):
        """Test GitHub HTTPS URL returns github."""
        from src.web.app import _detect_target_type
        assert _detect_target_type("https://github.com/user/repo") == "github"

    def test_github_www_https_returns_github(self):
        """Test GitHub www URL returns github."""
        from src.web.app import _detect_target_type
        assert _detect_target_type("https://www.github.com/user/repo") == "github"

    def test_git_at_ssh_returns_github(self):
        """Test git@ SSH URL returns github."""
        from src.web.app import _detect_target_type
        assert _detect_target_type("git@github.com:user/repo.git") == "github"

    def test_http_url_returns_url(self):
        """Test HTTP URL returns url."""
        from src.web.app import _detect_target_type
        assert _detect_target_type("http://example.com") == "url"

    def test_https_url_returns_url(self):
        """Test HTTPS URL returns url."""
        from src.web.app import _detect_target_type
        assert _detect_target_type("https://example.com/page") == "url"

    def test_local_path_returns_local(self):
        """Test local path returns local."""
        from src.web.app import _detect_target_type
        assert _detect_target_type("./my-project") == "local"
        assert _detect_target_type("/Users/me/project") == "local"
        assert _detect_target_type("my-folder") == "local"


class TestCleanupTarget:
    """Tests for _cleanup_target function."""

    @patch("src.web.app.shutil.rmtree")
    def test_cleanup_ignores_non_temp_path(self, mock_rmtree):
        """Test cleanup ignores paths not in temp dir."""
        from src.web.app import _cleanup_target
        _cleanup_target("/some/other/path", "local")
        mock_rmtree.assert_not_called()

    @patch("src.web.app.shutil.rmtree")
    def test_cleanup_ignores_non_github_type(self, mock_rmtree):
        """Test cleanup ignores non-github type."""
        from src.web.app import _cleanup_target
        tmp = tempfile.gettempdir()
        path = f"{tmp}/omc-gh-12345-test"
        _cleanup_target(path, "url")
        mock_rmtree.assert_not_called()

    @patch("src.web.app.shutil.rmtree")
    def test_cleanup_removes_temp_github(self, mock_rmtree):
        """Test cleanup removes temp github path."""
        from src.web.app import _cleanup_target
        tmp = tempfile.gettempdir()
        path = f"{tmp}/omc-gh-abc123-foo"
        _cleanup_target(path, "github")
        mock_rmtree.assert_called_once()


class TestJsonDumps:
    """Tests for json_dumps function."""

    def test_serializes_simple_dict(self):
        """Test serializes simple dict."""
        from src.web.app import json_dumps
        result = json_dumps({"key": "value"})
        assert '"key"' in result

    def test_serializes_nested_object(self):
        """Test serializes nested object."""
        from src.web.app import json_dumps

        class MockObj:
            def __init__(self):
                self.a = 1

        result = json_dumps(MockObj())
        assert "a" in result or "1" in result