"""Exception handler tests for src.web.app"""

from unittest.mock import patch

import pytest

# Prevent concurrent execution
pytestmark = pytest.mark.xdist_group("web_app")



class TestPreprocessTargetGitCloneException:

    """Tests for _preprocess_target git clone exception."""


    @patch("src.web.app.subprocess.run")

    @patch("src.web.app.shutil.rmtree")

    def test_git_clone_failure_raises_error(self, mock_rmtree, mock_run):


        from src.web.app import _preprocess_target


        # Mock git clone failure

        mock_run.return_value.returncode = 1

        mock_run.return_value.stderr = "fatal: not found"



        # Should raise RuntimeError

        with pytest.raises(RuntimeError):
            _preprocess_target("https://github.com/user/repo", "github", "test-id")























class TestPreprocessTargetUrlFetchException:





    """Tests for _preprocess_target URL fetch exception."""


























class TestOpenFolderException:



































    pass

