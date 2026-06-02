"""Exception handler tests for src.web.app"""

import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Prevent concurrent execution - global singleton pollution
pytestmark = pytest.mark.xdist_group("web_app")


class TestOpenFolderException:
    """Tests for /api/open-folder exception handler."""

    @patch("src.web.app.subprocess.run")
    def test_open_folder_subprocess_error_returns_500(self, mock_run):
        """Test subprocess error returns 500 status."""
        from fastapi.testclient import TestClient
        from src.web.app import app

        mock_run.side_effect = Exception("subprocess failed")








class TestPreprocessTargetGitClone:
    """Tests for _preprocess_target git clone exception."""

    @patch("src.web.app.subprocess.run")
    @patch("src.web.app.shutil.rmtree")
    def test_git_clone_failure_raises_error(self, mock_rmtree, mock_run):
        """Test git clone failure raises RuntimeError."""
        from src.web.app import _preprocess_target


















class TestPreprocessTargetUrlFetch:






























    pass

class TestCreateOrchestratorAgentWarning:

    pass




























class TestChatCompletionNonStreamingException:


















    pass

