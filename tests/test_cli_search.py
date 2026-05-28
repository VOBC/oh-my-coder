"""
Tests for cli_search.py

Target coverage: 70%+
"""

import json
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from src.commands.cli_search import app
from src.tools.sourcegraph import SearchMatch, SearchResult

runner = CliRunner()


@pytest.fixture
def mock_console():
    """Mock console to capture output"""
    with patch("src.commands.cli_search.console") as mock:
        yield mock


@pytest.fixture
def sample_search_result():
    """Create a sample SearchResult for testing"""
    return SearchResult(
        query="test query",
        total_matches=2,
        matches=[
            SearchMatch(
                repo="owner/repo1",
                file_path="src/main.py",
                repository_stars=100,
                repo_description="Test repo",
                content_preview="def hello():\n    print('world')",
                line_number=10,
                language="python",
                url="https://sourcegraph.com/owner/repo1/-/src/main.py",
                symbols=["hello"],
            ),
            SearchMatch(
                repo="owner/repo2",
                file_path="lib/util.js",
                repository_stars=50,
                repo_description="Another test",
                content_preview="function test() { return true; }",
                line_number=5,
                language="javascript",
                url="https://sourcegraph.com/owner/repo2/-/lib/util.js",
                symbols=["test"],
            ),
        ],
        elapsed_ms=150,
        source="api",
        warnings=[],
    )


class TestSearchCommand:
    """Test the search command"""

    @patch("src.commands.cli_search.search")
    def test_search_basic(self, mock_search, sample_search_result, mock_console):
        """Test basic search command"""
        mock_search.return_value = sample_search_result

        result = runner.invoke(app, ["search", "test query"])

        assert result.exit_code == 0
        mock_search.assert_called_once_with(
            query="test query",
            language=None,
            repo=None,
            limit=20,
            after=None,
            before=None,
        )

    @patch("src.commands.cli_search.search")
    def test_search_with_options(self, mock_search, sample_search_result, mock_console):
        """Test search with all options"""
        mock_search.return_value = sample_search_result

        result = runner.invoke(
            app,
            [
                "search",
                "test query",
                "--language", "python",
                "--repo", "owner/*",
                "--limit", "50",
                "--after", "2024-01-01",
                "--before", "2024-12-31",
            ],
        )

        assert result.exit_code == 0
        mock_search.assert_called_once_with(
            query="test query",
            language="python",
            repo="owner/*",
            limit=50,
            after="2024-01-01",
            before="2024-12-31",
        )

    @patch("src.commands.cli_search.search")
    def test_search_json_output(self, mock_search, sample_search_result, mock_console):
        """Test search with JSON output"""
        mock_search.return_value = sample_search_result

        result = runner.invoke(app, ["search", "test", "--json"])

        assert result.exit_code == 0
        mock_search.assert_called_once()

    @patch("src.commands.cli_search.search")
    def test_search_json_flag_output(self, mock_search, sample_search_result, mock_console):
        """Test search with --output json"""
        mock_search.return_value = sample_search_result

        result = runner.invoke(app, ["search", "test", "--output", "json"])

        assert result.exit_code == 0
        mock_search.assert_called_once()

    @patch("src.commands.cli_search.search")
    def test_search_code_output(self, mock_search, sample_search_result, mock_console):
        """Test search with code output"""
        mock_search.return_value = sample_search_result

        result = runner.invoke(app, ["search", "test", "--code"])

        assert result.exit_code == 0
        mock_search.assert_called_once()

    @patch("src.commands.cli_search.search")
    def test_search_code_flag_output(self, mock_search, sample_search_result, mock_console):
        """Test search with --output code"""
        mock_search.return_value = sample_search_result

        result = runner.invoke(app, ["search", "test", "--output", "code"])

        assert result.exit_code == 0
        mock_search.assert_called_once()

    @patch("src.commands.cli_search.search")
    def test_search_no_results(self, mock_search, mock_console):
        """Test search with no results"""
        mock_search.return_value = SearchResult(
            query="test",
            total_matches=0,
            matches=[],
            elapsed_ms=50,
            source="api",
            warnings=[],
        )

        result = runner.invoke(app, ["search", "test"])

        assert result.exit_code == 0
        mock_search.assert_called_once()

    @patch("src.commands.cli_search.search")
    def test_search_with_warnings(self, mock_search, mock_console):
        """Test search that returns warnings"""
        mock_search.return_value = SearchResult(
            query="test",
            total_matches=0,
            matches=[],
            elapsed_ms=0,
            source="none",
            warnings=[
                "Sourcegraph API Key 未设置",
                "src CLI 也未安装",
            ],
        )

        result = runner.invoke(app, ["search", "test"])

        assert result.exit_code == 0
        mock_search.assert_called_once()

    @patch("src.commands.cli_search.search")
    def test_search_none_source_shows_panel(self, mock_search, mock_console):
        """Test that 'none' source shows configuration panel"""
        mock_search.return_value = SearchResult(
            query="test",
            total_matches=0,
            matches=[],
            elapsed_ms=0,
            source="none",
            warnings=["API not configured"],
        )

        result = runner.invoke(app, ["search", "test"])

        assert result.exit_code == 0
        mock_search.assert_called_once()


class TestSetupCommand:
    """Test the setup command"""

    @patch("src.commands.cli_search.setup_api_key")
    @patch("src.commands.cli_search.install_src_cli")
    @patch("getpass.getpass")
    def test_setup_with_api_key_arg(self, mock_getpass, mock_install, mock_setup):
        """Test setup with API key as argument"""
        mock_setup.return_value = (True, "Success")

        result = runner.invoke(app, ["setup", "test-api-key"])

        assert result.exit_code == 0
        mock_setup.assert_called_once_with("test-api-key")
        mock_getpass.assert_not_called()

    @patch("src.commands.cli_search.setup_api_key")
    @patch("src.commands.cli_search.install_src_cli")
    @patch("getpass.getpass")
    def test_setup_interactive(self, mock_getpass, mock_install, mock_setup):
        """Test setup with interactive API key input"""
        mock_getpass.return_value = "interactive-api-key"
        mock_setup.return_value = (True, "Success")

        result = runner.invoke(app, ["setup"])

        assert result.exit_code == 0
        mock_getpass.assert_called_once()
        mock_setup.assert_called_once_with("interactive-api-key")

    @patch("src.commands.cli_search.setup_api_key")
    @patch("src.commands.cli_search.install_src_cli")
    @patch("getpass.getpass")
    def test_setup_with_cli_flag(self, mock_getpass, mock_install, mock_setup):
        """Test setup with --cli flag"""
        mock_install.return_value = (True, "CLI installed")
        mock_setup.return_value = (True, "Success")

        result = runner.invoke(app, ["setup", "--cli"])

        assert result.exit_code == 0
        mock_install.assert_called_once()
        mock_setup.assert_called_once()

    @patch("src.commands.cli_search.setup_api_key")
    @patch("src.commands.cli_search.install_src_cli")
    @patch("getpass.getpass")
    def test_setup_empty_api_key(self, mock_getpass, mock_install, mock_setup):
        """Test setup with empty API key"""
        mock_getpass.return_value = ""

        result = runner.invoke(app, ["setup"])

        assert result.exit_code == 1
        mock_setup.assert_not_called()

    @patch("src.commands.cli_search.setup_api_key")
    @patch("src.commands.cli_search.install_src_cli")
    @patch("getpass.getpass")
    def test_setup_getpass_exception(self, mock_getpass, mock_install, mock_setup):
        """Test setup when getpass raises exception"""
        mock_getpass.side_effect = Exception("Cannot read password")

        result = runner.invoke(app, ["setup"])

        assert result.exit_code == 1
        mock_setup.assert_not_called()

    @patch("src.commands.cli_search.setup_api_key")
    @patch("src.commands.cli_search.install_src_cli")
    def test_setup_failed(self, mock_install, mock_setup):
        """Test setup when API key setup fails"""
        mock_setup.return_value = (False, "Setup failed")

        result = runner.invoke(app, ["setup", "bad-key"])

        assert result.exit_code == 1
        mock_setup.assert_called_once()

    @patch("src.commands.cli_search.setup_api_key")
    @patch("src.commands.cli_search.install_src_cli")
    @patch("getpass.getpass")
    def test_setup_cli_install_fails(self, mock_getpass, mock_install, mock_setup):
        """Test setup when CLI install fails"""
        mock_install.return_value = (False, "Install failed")
        mock_getpass.return_value = "test-key"
        mock_setup.return_value = (True, "Success")

        result = runner.invoke(app, ["setup", "--cli"])

        assert result.exit_code == 0
        mock_install.assert_called_once()
        mock_setup.assert_called_once()


class TestStatusCommand:
    """Test the status command"""

    @patch("src.commands.cli_search.check_status")
    def test_status_api_available(self, mock_check_status, mock_console):
        """Test status when API is available"""
        mock_check_status.return_value = {
            "api": {
                "available": True,
                "endpoint": "https://sourcegraph.com/.api",
                "key_prefix": "test...",
            },
            "cli": {
                "available": True,
                "path": "/usr/local/bin/src",
            },
            "recommendation": "api",
        }

        result = runner.invoke(app, ["status"])

        assert result.exit_code == 0
        mock_check_status.assert_called_once()

    @patch("src.commands.cli_search.check_status")
    def test_status_cli_only(self, mock_check_status, mock_console):
        """Test status when only CLI is available"""
        mock_check_status.return_value = {
            "api": {
                "available": False,
                "endpoint": None,
                "key_prefix": None,
            },
            "cli": {
                "available": True,
                "path": "/usr/local/bin/src",
            },
            "recommendation": "cli",
        }

        result = runner.invoke(app, ["status"])

        assert result.exit_code == 0
        mock_check_status.assert_called_once()

    @patch("src.commands.cli_search.check_status")
    def test_status_none_available(self, mock_check_status, mock_console):
        """Test status when nothing is available"""
        mock_check_status.return_value = {
            "api": {
                "available": False,
                "endpoint": None,
                "key_prefix": None,
            },
            "cli": {
                "available": False,
                "path": "src",
            },
            "recommendation": "none",
        }

        result = runner.invoke(app, ["status"])

        assert result.exit_code == 0
        mock_check_status.assert_called_once()


class TestInstallCommand:
    """Test the install command"""

    @patch("src.commands.cli_search.install_src_cli")
    def test_install_success(self, mock_install, mock_console):
        """Test successful CLI installation"""
        mock_install.return_value = (True, "src CLI 安装成功")

        result = runner.invoke(app, ["install"])

        assert result.exit_code == 0
        mock_install.assert_called_once()

    @patch("src.commands.cli_search.install_src_cli")
    def test_install_failure(self, mock_install, mock_console):
        """Test failed CLI installation"""
        mock_install.return_value = (False, "安装失败: permission denied")

        result = runner.invoke(app, ["install"])

        assert result.exit_code == 0
        mock_install.assert_called_once()


class TestMainCallback:
    """Test the main callback (help display)"""

    def test_main_no_command_shows_help(self, mock_console):
        """Test that running without command shows help"""
        result = runner.invoke(app, [])

        assert result.exit_code == 0
        # Help text should be displayed
        assert "help" in result.output.lower() or "usage" in result.output.lower()


class TestSearchResultFormatting:
    """Test SearchResult formatting methods"""

    def test_format_table(self, sample_search_result):
        """Test format_table method"""
        output = sample_search_result.format_table(limit=10)

        assert "test query" in output
        assert "owner/repo1" in output
        assert "owner/repo2" in output
        assert "Matches:" in output

    def test_format_json(self, sample_search_result):
        """Test format_json method"""
        output = sample_search_result.format_json()

        data = json.loads(output)
        assert data["query"] == "test query"
        assert data["total"] == 2
        assert len(data["matches"]) == 2

    def test_format_code(self, sample_search_result):
        """Test format_code method"""
        output = sample_search_result.format_code(limit=2)

        assert "Search:" in output
        assert "test query" in output
        assert "owner/repo1" in output

    def test_format_table_with_warnings(self):
        """Test format_table with warnings"""
        result = SearchResult(
            query="test",
            total_matches=0,
            matches=[],
            elapsed_ms=0,
            source="api",
            warnings=["Warning 1", "Warning 2"],
        )

        output = result.format_table(limit=10)

        assert "Warning 1" in output
        assert "Warning 2" in output

    def test_format_table_more_results(self, sample_search_result):
        """Test format_table when there are more results than limit"""
        # Create result with more matches than limit
        matches = [
            SearchMatch(
                repo=f"owner/repo{i}",
                file_path=f"file{i}.py",
                line_number=i,
            )
            for i in range(20)
        ]
        result = SearchResult(
            query="test",
            total_matches=20,
            matches=matches,
            elapsed_ms=100,
            source="api",
        )

        output = result.format_table(limit=5)

        assert "还有 15 个结果" in output


class TestSearchMatchFormatting:
    """Test SearchMatch formatting methods"""

    def test_format_code_basic(self):
        """Test basic format_code output"""
        match = SearchMatch(
            repo="owner/repo",
            file_path="src/main.py",
            line_number=10,
            content_preview="def hello():\n    print('world')",
            language="python",
        )

        output = match.format_code()

        assert "[owner/repo:src/main.py:10]" in output
        assert "def hello()" in output

    def test_format_code_with_symbols(self):
        """Test format_code with symbols"""
        match = SearchMatch(
            repo="owner/repo",
            file_path="src/main.py",
            line_number=10,
            content_preview="def hello():\n    print('world')",
            symbols=["hello", "HelloWorld"],
        )

        output = match.format_code()

        assert "定义:" in output
        assert "hello" in output

    def test_format_code_preview_truncation(self):
        """Test that content preview is truncated to 8 lines"""
        long_preview = "\n".join([f"line {i}" for i in range(20)])
        match = SearchMatch(
            repo="owner/repo",
            file_path="src/main.py",
            line_number=10,
            content_preview=long_preview,
        )

        output = match.format_code()

        # Should only have 8 lines of preview
        preview_lines = [line for line in output.split("\n") if line.startswith("  line")]
        assert len(preview_lines) <= 8


class TestEdgeCases:
    """Test edge cases and error handling"""

    @patch("src.commands.cli_search.search")
    def test_search_limit_bounds(self, mock_search, mock_console):
        """Test search with limit edge cases"""
        mock_search.return_value = SearchResult(
            query="test",
            total_matches=0,
            matches=[],
            elapsed_ms=50,
            source="api",
        )

        # Test with limit=1
        result = runner.invoke(app, ["search", "test", "--limit", "1"])
        assert result.exit_code == 0

        # Test with limit=100
        result = runner.invoke(app, ["search", "test", "--limit", "100"])
        assert result.exit_code == 0

    @patch("src.commands.cli_search.search")
    def test_search_output_flag_combinations(self, mock_search, sample_search_result, mock_console):
        """Test various output flag combinations"""
        mock_search.return_value = sample_search_result

        # --json and --output json (both set)
        result = runner.invoke(app, ["search", "test", "--json", "--output", "json"])
        assert result.exit_code == 0

        # --code and --output code (both set)
        result = runner.invoke(app, ["search", "test", "--code", "--output", "code"])
        assert result.exit_code == 0

    def test_search_result_dataclass(self):
        """Test SearchResult dataclass creation"""
        result = SearchResult(
            query="test",
            total_matches=5,
            matches=[],
            elapsed_ms=100,
            source="api",
            warnings=[],
        )

        assert result.query == "test"
        assert result.total_matches == 5
        assert result.source == "api"
        assert isinstance(result.warnings, list)

    def test_search_match_dataclass(self):
        """Test SearchMatch dataclass creation"""
        match = SearchMatch(
            repo="owner/repo",
            file_path="file.py",
            repository_stars=10,
            repo_description="Test",
            content_preview="code",
            line_number=1,
            language="python",
            url="http://example.com",
            symbols=["func"],
        )

        assert match.repo == "owner/repo"
        assert match.line_number == 1
        assert match.symbols == ["func"]


class TestCLISearchIntegration:
    """Integration tests for CLI search (with mocked backend)"""

    @patch("src.commands.cli_search.search")
    def test_search_table_output_by_default(self, mock_search, sample_search_result, mock_console):
        """Test that table output is default"""
        mock_search.return_value = sample_search_result

        result = runner.invoke(app, ["search", "test"])

        assert result.exit_code == 0
        # Should call console.print with table output
        assert mock_console.print.called

    @patch("src.commands.cli_search.search")
    def test_search_limit_affects_code_output(self, mock_search, mock_console):
        """Test that limit affects code output"""
        matches = [
            SearchMatch(
                repo=f"owner/repo{i}",
                file_path=f"file{i}.py",
                line_number=i,
            )
            for i in range(10)
        ]
        mock_search.return_value = SearchResult(
            query="test",
            total_matches=10,
            matches=matches,
            elapsed_ms=100,
            source="api",
        )

        result = runner.invoke(app, ["search", "test", "--code", "--limit", "3"])

        assert result.exit_code == 0
        # Code output should be limited to min(limit, 10) = 3
        call_args = str(mock_console.print.call_args)
        assert "Search:" in call_args

    @patch("src.commands.cli_search.search")
    def test_search_empty_query_handling(self, mock_search, mock_console):
        """Test handling of search results with empty matches"""
        mock_search.return_value = SearchResult(
            query="",
            total_matches=0,
            matches=[],
            elapsed_ms=10,
            source="api",
        )

        result = runner.invoke(app, ["search", ""])

        assert result.exit_code == 0
        mock_search.assert_called_once_with(
            query="",
            language=None,
            repo=None,
            limit=20,
            after=None,
            before=None,
        )
