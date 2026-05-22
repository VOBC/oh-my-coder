"""
Tests for src/tools/sourcegraph.py

Covers:
- SearchMatch dataclass and format_code()
- SearchResult dataclass and format_table(), format_json(), format_code()
- _sg_api_search() with mocked httpx.post
- _check_src_cli() with mocked subprocess.run
- _src_cli_search() with mocked subprocess.run
- search() main entry point (API priority + CLI fallback)
- install_src_cli()
- setup_api_key()
- check_status()
"""

import json
import subprocess
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import httpx

from src.tools.sourcegraph import (
    SearchMatch,
    SearchResult,
    _check_src_cli,
    _sg_api_search,
    _src_cli_search,
    check_status,
    install_src_cli,
    search,
    setup_api_key,
)

# =============================================================================
# Fixtures & Helpers
# =============================================================================

def make_match(**overrides: Any) -> SearchMatch:
    """Create a SearchMatch with sensible defaults."""
    defaults: dict[str, Any] = dict(
        repo="owner/repo",
        file_path="src/main.py",
        repository_stars=42,
        repo_description="A cool repo",
        content_preview='def hello():\n    print("world")',
        line_number=10,
        language="python",
        url="https://sourcegraph.com/owner/repo/-/src/main.py",
        symbols=["hello", "main"],
    )
    defaults.update(overrides)
    return SearchMatch(**defaults)


def make_result(**overrides: Any) -> SearchResult:
    """Create a SearchResult with sensible defaults."""
    defaults: dict[str, Any] = dict(
        query="def hello",
        total_matches=2,
        matches=[make_match(), make_match(repo="other/repo")],
        elapsed_ms=150,
        source="api",
        warnings=[],
    )
    defaults.update(overrides)
    return SearchResult(**defaults)


def mock_httpx_success() -> MagicMock:
    """Return a mock httpx response for successful API call."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "data": {
            "search": {
                "results": {
                    "results": [
                        {
                            "__typename": "FileMatch",
                            "repository": {
                                "name": "owner/repo",
                                "url": "https://sourcegraph.com/owner/repo",
                                "stars": {"totalCount": 100},
                                "description": "Test repo",
                            },
                            "file": {"path": "src/main.py", "url": "..."},
                            "lineMatches": [
                                {
                                    "preview": "def hello():",
                                    "lineNumber": 10,
                                    "offsetAndLengths": [[4, 5]],
                                }
                            ],
                            "symbols": [
                                {"name": "hello", "kind": "FUNCTION", "containerName": ""}
                            ],
                        }
                    ],
                    "matchCount": 1,
                    "timedOut": {"timedOut": False},
                },
                "elapsedMilliseconds": 150,
            }
        }
    }
    mock_resp.raise_for_status = MagicMock()
    return mock_resp


def mock_httpx_error(status_code: int = 401) -> MagicMock:
    """Return a mock httpx response that raises HTTPStatusError."""
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.json.return_value = {}
    http_error = httpx.HTTPStatusError(
        "Client error", request=MagicMock(), response=mock_resp
    )
    mock_resp.raise_for_status.side_effect = http_error
    return mock_resp


def make_completed_process(
    stdout: bytes, stderr: bytes = b"", returncode: int = 0
) -> subprocess.CompletedProcess:
    """Helper to create CompletedProcess with bytes."""
    return subprocess.CompletedProcess(
        args=["src"], returncode=returncode, stdout=stdout, stderr=stderr
    )


# =============================================================================
# SearchMatch Tests
# =============================================================================

class TestSearchMatch:
    """Tests for SearchMatch dataclass."""

    def test_basic_creation(self) -> None:
        m = make_match()
        assert m.repo == "owner/repo"
        assert m.file_path == "src/main.py"
        assert m.line_number == 10
        assert m.language == "python"

    def test_format_code_basic(self) -> None:
        m = make_match(
            repo="torch/torch",
            file_path="nn/modules/linear.py",
            line_number=25,
            content_preview='class Linear(nn.Module):\n    def __init__(self):',
            symbols=[],
        )
        out = m.format_code()
        assert "[torch/torch:nn/modules/linear.py:25]" in out
        assert "class Linear" in out

    def test_format_code_with_symbols(self) -> None:
        m = make_match(symbols=["MyClass.my_method", "helper"])
        out = m.format_code()
        assert "# 定义:" in out
        assert "MyClass.my_method" in out

    def test_format_code_multiline_preview(self) -> None:
        m = make_match(
            content_preview="line1\nline2\nline3\nline4\nline5\nline6\nline7\nline8\nline9"
        )
        out = m.format_code()
        # Should truncate to 8 lines
        assert out.count("\n") <= 9  # header + max 8 lines

    def test_format_code_empty_preview(self) -> None:
        m = make_match(content_preview="")
        out = m.format_code()
        assert "[owner/repo:src/main.py:10]" in out

    def test_defaults(self) -> None:
        m = SearchMatch(repo="r", file_path="f")
        assert m.repository_stars == 0
        assert m.symbols == []
        assert m.language == ""


# =============================================================================
# SearchResult Tests
# =============================================================================

class TestSearchResult:
    """Tests for SearchResult dataclass."""

    def test_format_table_basic(self) -> None:
        r = make_result()
        out = r.format_table()
        assert "Query:" in out
        assert "def hello" in out
        assert "Matches:" in out
        assert "Time:" in out
        assert "Source:" in out

    def test_format_table_with_warnings(self) -> None:
        r = make_result(warnings=["API 错误: 429"])
        out = r.format_table()
        assert "⚠" in out
        assert "API 错误" in out

    def test_format_table_limit(self) -> None:
        matches = [make_match(repo=f"repo/{i}") for i in range(20)]
        r = make_result(matches=matches, total_matches=20)
        out = r.format_table(limit=5)
        # Should only show 5 matches
        assert out.count("repo/") <= 5 + 1  # +1 for header context

    def test_format_table_more_than_limit(self) -> None:
        matches = [make_match(repo=f"repo/{i}") for i in range(15)]
        r = make_result(matches=matches, total_matches=15)
        out = r.format_table(limit=5)
        assert "还有 10 个结果" in out

    def test_format_json(self) -> None:
        r = make_result()
        out = r.format_json()
        data = json.loads(out)
        assert data["query"] == "def hello"
        assert data["total"] == 2
        assert len(data["matches"]) == 2
        assert "repo" in data["matches"][0]
        assert "preview" in data["matches"][0]

    def test_format_json_non_ascii(self) -> None:
        r = make_result(query="def 你好")
        out = r.format_json()
        data = json.loads(out)
        assert data["query"] == "def 你好"

    def test_format_code(self) -> None:
        r = make_result()
        out = r.format_code(limit=2)
        assert "# Search:" in out
        assert "def hello" in out

    def test_format_code_limit(self) -> None:
        matches = [make_match() for _ in range(10)]
        r = make_result(matches=matches)
        out = r.format_code(limit=3)
        assert out.count("[owner/repo:") == 3

    def test_dataclass_defaults(self) -> None:
        r = SearchResult(
            query="q", total_matches=0, matches=[], elapsed_ms=0, source="test"
        )
        assert r.warnings == []


# =============================================================================
# _sg_api_search Tests
# =============================================================================

class TestSgApiSearch:
    """Tests for _sg_api_search()."""

    @patch("src.tools.sourcegraph.SG_API_KEY", "fake-key")
    @patch("src.tools.sourcegraph.httpx.post")
    def test_success(self, mock_post: MagicMock) -> None:
        mock_post.return_value = mock_httpx_success()
        result = _sg_api_search("def hello")
        assert result is not None
        assert result.source == "api"
        assert result.total_matches >= 0
        mock_post.assert_called_once()

    @patch("src.tools.sourcegraph.SG_API_KEY", "")
    def test_no_api_key(self) -> None:
        result = _sg_api_search("def hello")
        assert result is None

    @patch("src.tools.sourcegraph.SG_API_KEY", "fake-key")
    @patch("src.tools.sourcegraph.httpx.post")
    def test_http_error(self, mock_post: MagicMock) -> None:
        mock_post.return_value = mock_httpx_error(401)
        result = _sg_api_search("def hello")
        assert result is not None
        assert result.source == "api"
        assert len(result.warnings) > 0
        assert "API 错误" in result.warnings[0]

    @patch("src.tools.sourcegraph.SG_API_KEY", "fake-key")
    @patch("src.tools.sourcegraph.httpx.post")
    def test_connection_error(self, mock_post: MagicMock) -> None:
        mock_post.side_effect = httpx.RequestError("Connection failed")
        result = _sg_api_search("def hello")
        assert result is not None
        assert result.source == "api"
        assert any("连接失败" in w for w in result.warnings)

    @patch("src.tools.sourcegraph.SG_API_KEY", "fake-key")
    @patch("src.tools.sourcegraph.httpx.post")
    def test_with_repo_filter(self, mock_post: MagicMock) -> None:
        mock_post.return_value = mock_httpx_success()
        _sg_api_search("def hello", repo="owner/repo")
        call_args = mock_post.call_args
        body = call_args[1]["json"]
        assert "repo:owner/repo" in body["variables"]["query"]

    @patch("src.tools.sourcegraph.SG_API_KEY", "fake-key")
    @patch("src.tools.sourcegraph.httpx.post")
    def test_with_language_filter(self, mock_post: MagicMock) -> None:
        mock_post.return_value = mock_httpx_success()
        _sg_api_search("def hello", language="python")
        call_args = mock_post.call_args
        body = call_args[1]["json"]
        assert "lang:python" in body["variables"]["query"]

    @patch("src.tools.sourcegraph.SG_API_KEY", "fake-key")
    @patch("src.tools.sourcegraph.httpx.post")
    def test_with_date_filters(self, mock_post: MagicMock) -> None:
        mock_post.return_value = mock_httpx_success()
        _sg_api_search("def hello", after="2024-01-01", before="2024-12-31")
        call_args = mock_post.call_args
        body = call_args[1]["json"]
        query = body["variables"]["query"]
        assert "after:2024-01-01" in query
        assert "before:2024-12-31" in query

    @patch("src.tools.sourcegraph.SG_API_KEY", "fake-key")
    @patch("src.tools.sourcegraph.httpx.post")
    def test_limit_clamped_to_100(self, mock_post: MagicMock) -> None:
        mock_post.return_value = mock_httpx_success()
        _sg_api_search("def hello", limit=999)
        call_args = mock_post.call_args
        body = call_args[1]["json"]
        assert body["variables"]["first"] == 100

    @patch("src.tools.sourcegraph.SG_API_KEY", "fake-key")
    @patch("src.tools.sourcegraph.httpx.post")
    def test_skips_repository_typename(self, mock_post: MagicMock) -> None:
        mock_resp = mock_httpx_success()
        # Add a Repository-type result
        mock_resp.json.return_value["data"]["search"]["results"]["results"].insert(
            0, {"__typename": "Repository", "name": "some/repo"}
        )
        mock_post.return_value = mock_resp
        result = _sg_api_search("def hello")
        # Should not crash and should skip Repository type
        assert result is not None


# =============================================================================
# _check_src_cli Tests
# =============================================================================

class TestCheckSrcCli:
    """Tests for _check_src_cli()."""

    @patch("src.tools.sourcegraph.subprocess.run")
    def test_cli_available(self, mock_run: MagicMock) -> None:
        mock_run.return_value = make_completed_process(
            stdout=b"src version 5.0.0", stderr=b"", returncode=0
        )
        assert _check_src_cli() is True

    @patch("src.tools.sourcegraph.subprocess.run")
    def test_cli_not_available(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = FileNotFoundError("No such file")
        assert _check_src_cli() is False

    @patch("src.tools.sourcegraph.subprocess.run")
    def test_cli_timeout(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = subprocess.TimeoutExpired(cmd=["src"], timeout=5)
        assert _check_src_cli() is False

    @patch("src.tools.sourcegraph.subprocess.run")
    def test_cli_returns_error_code(self, mock_run: MagicMock) -> None:
        mock_run.return_value = make_completed_process(
            stdout=b"", stderr=b"error", returncode=1
        )
        assert _check_src_cli() is False


# =============================================================================
# _src_cli_search Tests
# =============================================================================

class TestSrcCliSearch:
    """Tests for _src_cli_search()."""

    @patch("src.tools.sourcegraph._check_src_cli")
    @patch("src.tools.sourcegraph.subprocess.run")
    def test_success_content_match(
        self, mock_run: MagicMock, mock_check: MagicMock
    ) -> None:
        mock_check.return_value = True
        output = json.dumps(
            {
                "type": "content",
                "repo": "owner/repo",
                "path": "src/main.py",
                "content": {"preview": "def hello():"},
                "line": 10,
                "language": "python",
                "url": "https://sourcegraph.com/owner/repo/-/src/main.py",
            }
        )
        mock_run.return_value = make_completed_process(
            stdout=(output + "\n").encode(), stderr=b""
        )
        result = _src_cli_search("def hello")
        assert result is not None
        assert result.source == "cli"
        assert len(result.matches) == 1

    @patch("src.tools.sourcegraph._check_src_cli")
    @patch("src.tools.sourcegraph.subprocess.run")
    def test_success_symbol_match(
        self, mock_run: MagicMock, mock_check: MagicMock
    ) -> None:
        mock_check.return_value = True
        output = json.dumps(
            {
                "type": "symbol",
                "repo": "owner/repo",
                "url": "https://...",
                "symbol": {"name": "hello", "kind": "FUNCTION"},
                "context": {"file": {"path": "src/main.py"}},
            }
        )
        mock_run.return_value = make_completed_process(
            stdout=(output + "\n").encode(), stderr=b""
        )
        result = _src_cli_search("hello")
        assert result is not None
        assert len(result.matches) == 1
        assert "hello" in result.matches[0].symbols

    @patch("src.tools.sourcegraph._check_src_cli")
    def test_cli_not_available(self, mock_check: MagicMock) -> None:
        mock_check.return_value = False
        result = _src_cli_search("def hello")
        assert result is None

    @patch("src.tools.sourcegraph._check_src_cli")
    @patch("src.tools.sourcegraph.subprocess.run")
    def test_cli_error(
        self, mock_run: MagicMock, mock_check: MagicMock
    ) -> None:
        mock_check.return_value = True
        mock_run.return_value = make_completed_process(
            stdout=b"", stderr=b"error: something went wrong", returncode=1
        )
        result = _src_cli_search("def hello")
        assert result is not None
        assert result.source == "cli"
        assert len(result.warnings) > 0

    @patch("src.tools.sourcegraph._check_src_cli")
    @patch("src.tools.sourcegraph.subprocess.run")
    def test_cli_timeout(
        self, mock_run: MagicMock, mock_check: MagicMock
    ) -> None:
        mock_check.return_value = True
        mock_run.side_effect = subprocess.TimeoutExpired(cmd=["src"], timeout=30)
        result = _src_cli_search("def hello")
        assert result is not None
        assert any("src CLI 错误" in w for w in result.warnings)

    @patch("src.tools.sourcegraph._check_src_cli")
    @patch("src.tools.sourcegraph.subprocess.run")
    def test_json_decode_error(
        self, mock_run: MagicMock, mock_check: MagicMock
    ) -> None:
        mock_check.return_value = True
        mock_run.return_value = make_completed_process(
            stdout=b"not valid json\n", stderr=b""
        )
        result = _src_cli_search("def hello")
        assert result is not None
        assert any("解析失败" in w for w in result.warnings)

    @patch("src.tools.sourcegraph._check_src_cli")
    @patch("src.tools.sourcegraph.subprocess.run")
    def test_with_language_filter(
        self, mock_run: MagicMock, mock_check: MagicMock
    ) -> None:
        mock_check.return_value = True
        mock_run.return_value = make_completed_process(
            stdout=b"\n", stderr=b""
        )
        _src_cli_search("def hello", language="python")
        cmd = mock_run.call_args[0][0]
        assert "-pattern" in cmd
        assert "lang:python" in cmd

    @patch("src.tools.sourcegraph._check_src_cli")
    @patch("src.tools.sourcegraph.subprocess.run")
    def test_with_repo_filter(
        self, mock_run: MagicMock, mock_check: MagicMock
    ) -> None:
        mock_check.return_value = True
        mock_run.return_value = make_completed_process(
            stdout=b"\n", stderr=b""
        )
        _src_cli_search("def hello", repo="owner/repo")
        cmd = mock_run.call_args[0][0]
        assert "repo:owner/repo" in cmd


# =============================================================================
# search() Tests
# =============================================================================

class TestSearch:
    """Tests for search() main entry point."""

    @patch("src.tools.sourcegraph.SG_API_KEY", "fake-key")
    @patch("src.tools.sourcegraph._sg_api_search")
    @patch("src.tools.sourcegraph._src_cli_search")
    def test_api_preferred(
        self, mock_cli: MagicMock, mock_api: MagicMock
    ) -> None:
        mock_api.return_value = make_result(source="api")
        result = search("def hello")
        mock_api.assert_called_once()
        mock_cli.assert_not_called()
        assert result.source == "api"

    @patch("src.tools.sourcegraph.SG_API_KEY", "")
    @patch("src.tools.sourcegraph._sg_api_search")
    @patch("src.tools.sourcegraph._src_cli_search")
    def test_fallback_to_cli(
        self, mock_cli: MagicMock, mock_api: MagicMock
    ) -> None:
        mock_cli.return_value = make_result(source="cli")
        result = search("def hello")
        mock_api.assert_not_called()
        mock_cli.assert_called_once()
        assert result.source == "cli"

    @patch("src.tools.sourcegraph.SG_API_KEY", "fake-key")
    @patch("src.tools.sourcegraph._sg_api_search")
    @patch("src.tools.sourcegraph._src_cli_search")
    def test_api_fails_fallback_cli(
        self, mock_cli: MagicMock, mock_api: MagicMock
    ) -> None:
        mock_api.return_value = None  # API returns None (no key or error)
        mock_cli.return_value = make_result(source="cli")
        result = search("def hello", prefer_api=True)
        mock_api.assert_called_once()
        mock_cli.assert_called_once()
        assert result.source == "cli"

    @patch("src.tools.sourcegraph.SG_API_KEY", "")
    @patch("src.tools.sourcegraph._check_src_cli")
    def test_no_backend_available(self, mock_check: MagicMock) -> None:
        mock_check.return_value = False
        result = search("def hello")
        assert result.source == "none"
        assert len(result.warnings) > 0
        assert any("API Key 未设置" in w for w in result.warnings)

    @patch("src.tools.sourcegraph._sg_api_search")
    @patch("src.tools.sourcegraph._src_cli_search")
    def test_prefer_api_false(
        self, mock_cli: MagicMock, mock_api: MagicMock
    ) -> None:
        mock_cli.return_value = make_result(source="cli")
        search("def hello", prefer_api=False)
        mock_cli.assert_called_once()
        mock_api.assert_not_called()


# =============================================================================
# install_src_cli Tests
# =============================================================================

class TestInstallSrcCli:
    """Tests for install_src_cli()."""

    @patch("src.tools.sourcegraph.subprocess.run")
    @patch("platform.system")
    def test_install_macos(
        self, mock_system: MagicMock, mock_run: MagicMock
    ) -> None:
        mock_system.return_value = "Darwin"
        mock_run.return_value = make_completed_process(
            stdout=b"", stderr=b"", returncode=0
        )
        success, msg = install_src_cli()
        assert success is True
        assert "成功" in msg

    @patch("src.tools.sourcegraph.subprocess.run")
    @patch("platform.system")
    def test_install_linux(
        self, mock_system: MagicMock, mock_run: MagicMock
    ) -> None:
        mock_system.return_value = "Linux"
        mock_run.return_value = make_completed_process(
            stdout=b"", stderr=b"", returncode=0
        )
        success, msg = install_src_cli()
        assert success is True

    @patch("src.tools.sourcegraph.subprocess.run")
    @patch("platform.system")
    def test_install_windows(
        self, mock_system: MagicMock, mock_run: MagicMock
    ) -> None:
        mock_system.return_value = "Windows"
        mock_run.return_value = make_completed_process(
            stdout=b"", stderr=b"", returncode=0
        )
        success, msg = install_src_cli()
        assert success is True

    @patch("platform.system")
    def test_unsupported_system(self, mock_system: MagicMock) -> None:
        mock_system.return_value = "Unknown"
        success, msg = install_src_cli()
        assert success is False
        assert "不支持" in msg

    @patch("src.tools.sourcegraph.subprocess.run")
    @patch("platform.system")
    def test_install_failure(
        self, mock_system: MagicMock, mock_run: MagicMock
    ) -> None:
        mock_system.return_value = "Darwin"
        mock_run.return_value = make_completed_process(
            stdout=b"", stderr=b"brew error", returncode=1
        )
        success, msg = install_src_cli()
        assert success is False
        assert "失败" in msg


# =============================================================================
# setup_api_key Tests
# =============================================================================

class TestSetupApiKey:
    """Tests for setup_api_key()."""

    def test_empty_key(self, tmp_path: Path) -> None:
        with patch("src.tools.sourcegraph.Path.home", return_value=tmp_path):
            success, msg = setup_api_key("")
            assert success is False
            assert "不能为空" in msg

    def test_new_key(self, tmp_path: Path) -> None:
        with patch("src.tools.sourcegraph.Path.home", return_value=tmp_path):
            success, msg = setup_api_key("sgp_abc123")
            assert success is True
            env_file = tmp_path / ".omc" / ".env"
            assert env_file.exists()
            content = env_file.read_text()
            assert "SOURCEGRAPH_API_KEY=sgp_abc123" in content

    def test_update_existing_key(self, tmp_path: Path) -> None:
        with patch("src.tools.sourcegraph.Path.home", return_value=tmp_path):
            # First setup
            setup_api_key("old_key")
            # Update
            success, msg = setup_api_key("new_key")
            assert success is True
            env_file = tmp_path / ".omc" / ".env"
            content = env_file.read_text()
            assert "SOURCEGRAPH_API_KEY=new_key" in content
            # old key should not appear as a standalone assignment
            lines = content.splitlines()
            key_lines = [line for line in lines if line.startswith("SOURCEGRAPH_API_KEY=")]
            assert key_lines == ["SOURCEGRAPH_API_KEY=new_key"]

    def test_preserves_other_env_vars(self, tmp_path: Path) -> None:
        with patch("src.tools.sourcegraph.Path.home", return_value=tmp_path):
            env_file = tmp_path / ".omc" / ".env"
            env_file.parent.mkdir(parents=True, exist_ok=True)
            env_file.write_text("OTHER_VAR=foo\nSOURCEGRAPH_API_KEY=old\n")
            setup_api_key("new")
            content = env_file.read_text()
            assert "OTHER_VAR=foo" in content


# =============================================================================
# check_status Tests
# =============================================================================

class TestCheckStatus:
    """Tests for check_status()."""

    @patch("src.tools.sourcegraph.SG_API_KEY", "fake-key")
    @patch("src.tools.sourcegraph._check_src_cli")
    def test_api_available(self, mock_check: MagicMock) -> None:
        mock_check.return_value = False
        status = check_status()
        assert status["api"]["available"] is True
        assert status["cli"]["available"] is False
        assert status["recommendation"] == "api"

    @patch("src.tools.sourcegraph.SG_API_KEY", "")
    @patch("src.tools.sourcegraph._check_src_cli")
    def test_cli_available(self, mock_check: MagicMock) -> None:
        mock_check.return_value = True
        status = check_status()
        assert status["api"]["available"] is False
        assert status["cli"]["available"] is True
        assert status["recommendation"] == "cli"

    @patch("src.tools.sourcegraph.SG_API_KEY", "")
    @patch("src.tools.sourcegraph._check_src_cli")
    def test_none_available(self, mock_check: MagicMock) -> None:
        mock_check.return_value = False
        status = check_status()
        assert status["recommendation"] == "none"

    @patch("src.tools.sourcegraph.SG_API_KEY", "fake-key")
    @patch("src.tools.sourcegraph._check_src_cli")
    def test_api_key_prefix(self, mock_check: MagicMock) -> None:
        mock_check.return_value = False
        status = check_status()
        assert status["api"]["key_prefix"] is not None
        assert status["api"]["key_prefix"].endswith("...")


# =============================================================================
# Edge Cases
# =============================================================================

class TestEdgeCases:
    """Edge case tests."""

    @patch("src.tools.sourcegraph.SG_API_KEY", "fake-key")
    @patch("src.tools.sourcegraph.httpx.post")
    def test_api_search_empty_results(self, mock_post: MagicMock) -> None:
        mock_resp = mock_httpx_success()
        mock_resp.json.return_value["data"]["search"]["results"]["results"] = []
        mock_resp.json.return_value["data"]["search"]["results"]["matchCount"] = 0
        mock_post.return_value = mock_resp
        result = _sg_api_search("nothing")
        assert result is not None
        assert result.total_matches == 0
        assert len(result.matches) == 0

    @patch("src.tools.sourcegraph._check_src_cli")
    @patch("src.tools.sourcegraph.subprocess.run")
    def test_cli_search_empty_output(
        self, mock_run: MagicMock, mock_check: MagicMock
    ) -> None:
        mock_check.return_value = True
        mock_run.return_value = make_completed_process(
            stdout=b"\n\n", stderr=b""
        )
        result = _src_cli_search("def hello")
        assert result is not None
        assert len(result.matches) == 0
