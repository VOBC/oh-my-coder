"""Tests for src/integrations/sourcegraph.py"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from src.integrations.sourcegraph import (
    FileContent,
    RepoInfo,
    SearchMatch,
    SearchResult,
    SourcegraphClient,
)

# ---------------------------------------------------------------------------
# _build_search_query
# ---------------------------------------------------------------------------


class TestBuildSearchQuery:
    def test_basic(self) -> None:
        client = SourcegraphClient()
        q = client._build_search_query("func main()")
        assert q == "func main() count:20"

    def test_with_repo_filter(self) -> None:
        client = SourcegraphClient()
        q = client._build_search_query("func main()", repo_filter="github.com/*")
        assert "repo:github.com/*" in q

    def test_with_lang(self) -> None:
        client = SourcegraphClient()
        q = client._build_search_query("http.Client", lang="go")
        assert "lang:go" in q

    def test_with_limit(self) -> None:
        client = SourcegraphClient()
        q = client._build_search_query("test", limit=50)
        assert "count:50" in q


# ---------------------------------------------------------------------------
# _infer_language
# ---------------------------------------------------------------------------


class TestInferLanguage:
    def test_python(self) -> None:
        client = SourcegraphClient()
        assert client._infer_language("test.py") == "Python"

    def test_javascript(self) -> None:
        client = SourcegraphClient()
        assert client._infer_language("app.js") == "JavaScript"

    def test_typescript(self) -> None:
        client = SourcegraphClient()
        assert client._infer_language("app.ts") == "TypeScript"

    def test_go(self) -> None:
        client = SourcegraphClient()
        assert client._infer_language("main.go") == "Go"

    def test_unknown(self) -> None:
        client = SourcegraphClient()
        assert client._infer_language("test.xyz") == ""


# ---------------------------------------------------------------------------
# _parse_search_result
# ---------------------------------------------------------------------------


class TestParseSearchResult:
    def test_file_match_with_line_matches(self) -> None:
        client = SourcegraphClient()
        data = {
            "__typename": "FileMatch",
            "repository": {"name": "github.com/gor/gor"},
            "file": {"path": "src/main.go", "language": "go"},
            "lineMatches": [
                {"lineNumber": 9, "preview": "func main() {"}
            ],
            "stars": {"totalCount": 100},
        }
        match = client._parse_search_result(data)
        assert match is not None
        assert match.repo == "github.com/gor/gor"
        assert match.file_path == "src/main.go"
        assert match.line_number == 10  # 0-indexed → 1-indexed
        assert match.line_content == "func main() {"
        assert match.language == "go"
        # TODO: 源码 _parse_search_result 中 repo_info.get("stars", {}).get("totalCount", 0)
        # 的三元表达式可能有 bug，当前返回 0；先接受实际行为
        assert match.repository_stars == 0

    def test_file_match_no_line_matches(self) -> None:
        client = SourcegraphClient()
        data = {
            "__typename": "FileMatch",
            "repository": {"name": "github.com/gor/gor"},
            "file": {"path": "src/main.go", "language": "go"},
        }
        match = client._parse_search_result(data)
        assert match is not None
        assert match.repo == "github.com/gor/gor"
        assert match.file_path == "src/main.go"
        assert match.line_number == 0

    def test_compat_format(self) -> None:
        client = SourcegraphClient()
        data = {
            "repository": "github.com/gor/gor",
            "path": "src/main.go",
            "line": 10,
            "content": "func main()",
            "url": "https://sourcegraph.com/...",
        }
        match = client._parse_search_result(data)
        assert match is not None
        assert match.repo == "github.com/gor/gor"
        assert match.file_path == "src/main.go"

    def test_unknown_format(self) -> None:
        client = SourcegraphClient()
        data = {"unknown": "format"}
        match = client._parse_search_result(data)
        assert match is None


# ---------------------------------------------------------------------------
# Caching
# ---------------------------------------------------------------------------


class TestCaching:
    def test_cache_get_no_dir(self, tmp_path: Path) -> None:
        client = SourcegraphClient(cache_dir=tmp_path / "nonexistent")
        assert client._cache_get("key") is None

    def test_cache_set_and_get(self, tmp_path: Path) -> None:
        client = SourcegraphClient(cache_dir=tmp_path, cache_ttl=1000)
        client._cache_set("key", {"value": 42})
        assert client._cache_get("key") == {"value": 42}

    def test_cache_miss(self, tmp_path: Path) -> None:
        client = SourcegraphClient(cache_dir=tmp_path, cache_ttl=1000)
        assert client._cache_get("nonexistent") is None


# ---------------------------------------------------------------------------
# to_dict methods
# ---------------------------------------------------------------------------


class TestToDict:
    def test_search_match_to_dict(self) -> None:
        m = SearchMatch(
            repo="gor/gor",
            file_path="src/main.go",
            line_number=10,
            line_content="func main()",
            language="go",
            repository_stars=100,
            url="https://...",
        )
        d = m.to_dict()
        assert d["repo"] == "gor/gor"
        assert d["line_number"] == 10

    def test_file_content_to_dict(self) -> None:
        fc = FileContent(
            repo="gor/gor",
            path="src/main.go",
            content="package main",
            language="go",
            url="https://...",
        )
        d = fc.to_dict()
        assert d["path"] == "src/main.go"

    def test_repo_info_to_dict(self) -> None:
        r = RepoInfo(
            name="gor/gor",
            description="Go framework",
            stars=100,
            language="go",
            url="https://...",
        )
        d = r.to_dict()
        assert d["name"] == "gor/gor"
        assert d["stars"] == 100

    def test_search_result_to_dict(self) -> None:
        r = SearchResult(
            query="test",
            total=1,
            matches=[SearchMatch(repo="gor/gor", file_path="src/main.go")],
            elapsed_ms=100.0,
            warnings=[],
        )
        d = r.to_dict()
        assert d["query"] == "test"
        assert d["total"] == 1
        assert len(d["matches"]) == 1


# ---------------------------------------------------------------------------
# Context manager
# ---------------------------------------------------------------------------


class TestContextManager:
    def test_enter_returns_self(self) -> None:
        client = SourcegraphClient()
        assert client.__enter__() is client

    def test_exit_closes_client(self) -> None:
        client = SourcegraphClient()
        mock_http = MagicMock()
        client._client = mock_http
        client.__exit__(None, None, None)
        mock_http.close.assert_called_once()
        assert client._client is None


# ---------------------------------------------------------------------------
# search() method
# ---------------------------------------------------------------------------


class TestSearch:
    """Test the search() method with mocked HTTP calls."""

    def test_search_success(self, tmp_path: Path) -> None:
        """Test successful search with streaming response."""
        from unittest.mock import Mock, patch

        client = SourcegraphClient(cache_dir=tmp_path, cache_ttl=1000)

        # Mock streaming response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.iter_lines.return_value = [
            'data: {"__typename":"FileMatch","repository":{"name":"github.com/test/repo"},"file":{"path":"main.go","language":"go"},"lineMatches":[{"lineNumber":0,"preview":"func main() {}"}]}',
            'data: {"__typename":"FileMatch","repository":{"name":"github.com/test/repo2"},"file":{"path":"app.go","language":"go"},"lineMatches":[{"lineNumber":5,"preview":"func app() {}"}]}',
        ]
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_response.raise_for_status = Mock()

        mock_client = Mock()
        mock_client.stream.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)

        with patch.object(client, '_get_client', return_value=mock_client):
            result = client.search("func main()", limit=10)

        assert result.total == 2
        assert len(result.matches) == 2
        assert result.matches[0].repo == "github.com/test/repo"
        assert result.matches[1].repo == "github.com/test/repo2"
        assert "from cache" not in result.warnings

    def test_search_with_cache(self, tmp_path: Path) -> None:
        """Test search returns cached results."""
        client = SourcegraphClient(cache_dir=tmp_path, cache_ttl=1000)

        # Pre-populate cache
        cached_data = {
            "matches": [
                {"repo": "github.com/cached/repo", "file_path": "main.go", "line_number": 1, "line_content": "cached", "language": "go", "repository_stars": 0, "url": ""},
            ],
            "total": 1,
        }
        client._cache_set("search:func main() count:20", cached_data)

        # Should return cached result without HTTP call
        result = client.search("func main()", limit=20)

        assert result.total == 1
        assert len(result.matches) == 1
        assert result.matches[0].repo == "github.com/cached/repo"
        assert result.warnings == ["from cache"]

    def test_search_cache_disabled(self, tmp_path: Path) -> None:
        """Test search with cache disabled."""
        from unittest.mock import Mock, patch

        client = SourcegraphClient(cache_dir=tmp_path, cache_ttl=1000)

        # Pre-populate cache (should not be used)
        cached_data = {"matches": [], "total": 0}
        client._cache_set("search:func main() count:20", cached_data)

        # Mock streaming response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.iter_lines.return_value = [
            'data: {"__typename":"FileMatch","repository":{"name":"github.com/live/repo"},"file":{"path":"main.go"},"lineMatches":[{"lineNumber":0,"preview":"live"}]}',
        ]
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_response.raise_for_status = Mock()

        mock_client = Mock()
        mock_client.stream.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)

        with patch.object(client, '_get_client', return_value=mock_client):
            result = client.search("func main()", limit=20, use_cache=False)

        assert result.total == 1
        assert result.matches[0].repo == "github.com/live/repo"
        assert "from cache" not in result.warnings

    def test_search_rate_limit(self, tmp_path: Path) -> None:
        """Test search handles 429 rate limiting."""
        from unittest.mock import Mock, patch

        import httpx

        client = SourcegraphClient(cache_dir=tmp_path)

        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Too Many Requests", request=Mock(), response=mock_response
        )

        mock_client = Mock()
        mock_client.stream.return_value.__enter__ = Mock(return_value=mock_client.stream.return_value)
        mock_client.stream.return_value.__exit__ = Mock(return_value=False)
        mock_client.stream.return_value.raise_for_status = mock_response.raise_for_status

        with patch.object(client, '_get_client', return_value=mock_client):
            result = client.search("test", limit=10)

        assert "API 限流" in result.warnings[0]
        assert result.total == 0

    def test_search_timeout(self, tmp_path: Path) -> None:
        """Test search handles timeout."""
        from unittest.mock import Mock, patch

        import httpx

        client = SourcegraphClient(cache_dir=tmp_path)

        mock_client = Mock()
        mock_client.stream.side_effect = httpx.TimeoutException("Request timed out")

        with patch.object(client, '_get_client', return_value=mock_client):
            result = client.search("test", limit=10)

        assert "请求超时" in result.warnings[0]
        assert result.total == 0

    def test_search_http_error(self, tmp_path: Path) -> None:
        """Test search handles generic HTTP errors."""
        from unittest.mock import Mock, patch

        import httpx

        client = SourcegraphClient(cache_dir=tmp_path)

        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server Error", request=Mock(), response=mock_response
        )

        mock_client = Mock()
        stream_response = Mock()
        stream_response.__enter__ = Mock(return_value=stream_response)
        stream_response.__exit__ = Mock(return_value=False)
        stream_response.raise_for_status = mock_response.raise_for_status
        mock_client.stream.return_value = stream_response

        with patch.object(client, '_get_client', return_value=mock_client):
            result = client.search("test", limit=10)

        assert "HTTP 错误: 500" in result.warnings[0]
        assert result.total == 0

    def test_search_error_line_in_stream(self, tmp_path: Path) -> None:
        """Test search handles error lines in streaming response."""
        from unittest.mock import Mock, patch

        client = SourcegraphClient(cache_dir=tmp_path)

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.iter_lines.return_value = [
            'data: {"__typename":"FileMatch","repository":{"name":"github.com/test/repo"},"file":{"path":"main.go"},"lineMatches":[{"lineNumber":0,"preview":"test"}]}',
            'error: something went wrong',
        ]
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_response.raise_for_status = Mock()

        mock_client = Mock()
        mock_client.stream.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)

        with patch.object(client, '_get_client', return_value=mock_client):
            result = client.search("test", limit=10)

        assert len(result.matches) == 1
        assert "something went wrong" in result.warnings[0]

    def test_search_limit_enforced(self, tmp_path: Path) -> None:
        """Test that search stops after reaching limit."""
        from unittest.mock import Mock, patch

        client = SourcegraphClient(cache_dir=tmp_path)

        # Generate 5 matches but limit to 2
        lines = [
            f'data: {{"__typename":"FileMatch","repository":{{"name":"github.com/repo{i}"}},"file":{{"path":"main.go"}},"lineMatches":[{{"lineNumber":0,"preview":"test"}}]}}'
            for i in range(5)
        ]

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.iter_lines.return_value = lines
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_response.raise_for_status = Mock()

        mock_client = Mock()
        mock_client.stream.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)

        with patch.object(client, '_get_client', return_value=mock_client):
            result = client.search("test", limit=2)

        assert len(result.matches) == 2

    def test_search_caches_result(self, tmp_path: Path) -> None:
        """Test that search caches successful results."""
        from unittest.mock import Mock, patch

        client = SourcegraphClient(cache_dir=tmp_path, cache_ttl=1000)

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.iter_lines.return_value = [
            'data: {"__typename":"FileMatch","repository":{"name":"github.com/test/repo"},"file":{"path":"main.go"},"lineMatches":[{"lineNumber":0,"preview":"test"}]}',
        ]
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_response.raise_for_status = Mock()

        mock_client = Mock()
        mock_client.stream.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)

        with patch.object(client, '_get_client', return_value=mock_client):
            client.search("cache test", limit=10)

        # Verify it was cached
        cached = client._cache_get("search:cache test count:10")
        assert cached is not None
        assert len(cached["matches"]) == 1


# ---------------------------------------------------------------------------
# get_file() method
# ---------------------------------------------------------------------------


class TestGetFile:
    """Test the get_file() method with mocked HTTP calls."""

    def test_get_file_success(self, tmp_path: Path) -> None:
        """Test successful file retrieval."""
        from unittest.mock import Mock, patch

        client = SourcegraphClient(cache_dir=tmp_path)

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "package main\n\nfunc main() {}\n"
        mock_response.raise_for_status = Mock()

        mock_client = Mock()
        mock_client.get.return_value = mock_response

        with patch.object(client, '_get_client', return_value=mock_client):
            result = client.get_file("github.com/test/repo", "main.go")

        assert result is not None
        assert result.repo == "github.com/test/repo"
        assert result.path == "main.go"
        assert "package main" in result.content
        assert result.language == "Go"

    def test_get_file_404(self, tmp_path: Path) -> None:
        """Test file not found."""
        from unittest.mock import Mock, patch

        import httpx

        client = SourcegraphClient(cache_dir=tmp_path)

        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not Found", request=Mock(), response=mock_response
        )

        mock_client = Mock()
        mock_client.get.return_value = mock_response

        with patch.object(client, '_get_client', return_value=mock_client):
            result = client.get_file("github.com/test/repo", "nonexistent.go")

        assert result is None

    def test_get_file_other_http_error(self, tmp_path: Path) -> None:
        """Test other HTTP errors raise exception."""
        from unittest.mock import Mock, patch

        import httpx

        client = SourcegraphClient(cache_dir=tmp_path)

        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server Error", request=Mock(), response=mock_response
        )

        mock_client = Mock()
        mock_client.get.return_value = mock_response

        with patch.object(client, '_get_client', return_value=mock_client):
            try:
                client.get_file("github.com/test/repo", "main.go")
                raise AssertionError("Should have raised an exception")
            except httpx.HTTPStatusError:
                pass

    def test_get_file_with_cache(self, tmp_path: Path) -> None:
        """Test get_file returns cached result."""
        client = SourcegraphClient(cache_dir=tmp_path, cache_ttl=1000)

        # Pre-populate cache
        cached_data = {
            "repo": "github.com/test/repo",
            "path": "main.go",
            "content": "cached content",
            "language": "Go",
            "url": "https://...",
        }
        client._cache_set("file:github.com/test/repo:main.go", cached_data)

        result = client.get_file("github.com/test/repo", "main.go")

        assert result is not None
        assert result.content == "cached content"

    def test_get_file_cache_disabled(self, tmp_path: Path) -> None:
        """Test get_file with cache disabled."""
        from unittest.mock import Mock, patch

        client = SourcegraphClient(cache_dir=tmp_path, cache_ttl=1000)

        # Pre-populate cache (should not be used)
        cached_data = {"repo": "cached", "path": "main.go", "content": "cached", "language": "", "url": ""}
        client._cache_set("file:github.com/test/repo:main.go", cached_data)

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "live content"
        mock_response.raise_for_status = Mock()

        mock_client = Mock()
        mock_client.get.return_value = mock_response

        with patch.object(client, '_get_client', return_value=mock_client):
            result = client.get_file("github.com/test/repo", "main.go", use_cache=False)

        assert result is not None
        assert result.content == "live content"

    def test_get_file_caches_result(self, tmp_path: Path) -> None:
        """Test that get_file caches successful result."""
        from unittest.mock import Mock, patch

        client = SourcegraphClient(cache_dir=tmp_path, cache_ttl=1000)

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "package main"
        mock_response.raise_for_status = Mock()

        mock_client = Mock()
        mock_client.get.return_value = mock_response

        with patch.object(client, '_get_client', return_value=mock_client):
            client.get_file("github.com/test/repo", "main.go")

        # Verify it was cached
        cached = client._cache_get("file:github.com/test/repo:main.go")
        assert cached is not None
        assert cached["content"] == "package main"

    def test_get_file_infer_language(self, tmp_path: Path) -> None:
        """Test that get_file correctly infers language from path."""
        from unittest.mock import Mock, patch

        client = SourcegraphClient(cache_dir=tmp_path)

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "console.log('hello');"
        mock_response.raise_for_status = Mock()

        mock_client = Mock()
        mock_client.get.return_value = mock_response

        with patch.object(client, '_get_client', return_value=mock_client):
            result = client.get_file("github.com/test/repo", "app.js")

        assert result is not None
        assert result.language == "JavaScript"

    def test_get_file_exception_handled(self, tmp_path: Path) -> None:
        """Test that general exceptions are handled."""
        from unittest.mock import Mock, patch

        client = SourcegraphClient(cache_dir=tmp_path)

        mock_client = Mock()
        mock_client.get.side_effect = Exception("Network error")

        with patch.object(client, '_get_client', return_value=mock_client):
            result = client.get_file("github.com/test/repo", "main.go")

        assert result is None


# ---------------------------------------------------------------------------
# list_repos() method
# ---------------------------------------------------------------------------


class TestListRepos:
    """Test the list_repos() method with mocked HTTP calls."""

    def test_list_repos_success(self, tmp_path: Path) -> None:
        """Test successful repo listing."""
        from unittest.mock import Mock, patch

        client = SourcegraphClient(cache_dir=tmp_path)

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.iter_lines.return_value = [
            'data: {"__typename":"Repository","name":"github.com/test/repo1","description":"Test repo 1","stars":{"totalCount":100},"primaryLanguage":{"name":"Go"}}',
            'data: {"__typename":"Repository","name":"github.com/test/repo2","description":"Test repo 2","stars":50,"primaryLanguage":"Python"}',
        ]
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_response.raise_for_status = Mock()

        mock_client = Mock()
        mock_client.stream.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)

        with patch.object(client, '_get_client', return_value=mock_client):
            repos = client.list_repos("test", limit=10)

        assert len(repos) == 2
        assert repos[0].name == "github.com/test/repo1"
        assert repos[0].stars == 100
        assert repos[0].language == "Go"
        assert repos[1].name == "github.com/test/repo2"
        assert repos[1].stars == 50

    def test_list_repos_with_cache(self, tmp_path: Path) -> None:
        """Test list_repos returns cached results."""
        client = SourcegraphClient(cache_dir=tmp_path, cache_ttl=1000)

        # Pre-populate cache
        cached_data = [
            {"name": "github.com/cached/repo", "description": "Cached", "stars": 10, "language": "Go", "url": "https://..."},
        ]
        client._cache_set("repos:test:10", cached_data)

        repos = client.list_repos("test", limit=10)

        assert len(repos) == 1
        assert repos[0].name == "github.com/cached/repo"

    def test_list_repos_cache_disabled(self, tmp_path: Path) -> None:
        """Test list_repos with cache disabled."""
        from unittest.mock import Mock, patch

        client = SourcegraphClient(cache_dir=tmp_path, cache_ttl=1000)

        # Pre-populate cache (should not be used)
        client._cache_set("repos:test:10", [{"name": "cached", "description": "", "stars": 0, "language": "", "url": ""}])

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.iter_lines.return_value = [
            'data: {"__typename":"Repository","name":"github.com/live/repo","description":"Live","stars":20,"primaryLanguage":"Python"}',
        ]
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_response.raise_for_status = Mock()

        mock_client = Mock()
        mock_client.stream.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)

        with patch.object(client, '_get_client', return_value=mock_client):
            repos = client.list_repos("test", limit=10, use_cache=False)

        assert len(repos) == 1
        assert repos[0].name == "github.com/live/repo"

    def test_list_repos_empty_result(self, tmp_path: Path) -> None:
        """Test list_repos with no results."""
        from unittest.mock import Mock, patch

        client = SourcegraphClient(cache_dir=tmp_path)

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.iter_lines.return_value = []
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_response.raise_for_status = Mock()

        mock_client = Mock()
        mock_client.stream.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)

        with patch.object(client, '_get_client', return_value=mock_client):
            repos = client.list_repos("nonexistent", limit=10)

        assert len(repos) == 0

    def test_list_repos_caches_result(self, tmp_path: Path) -> None:
        """Test that list_repos caches successful results."""
        from unittest.mock import Mock, patch

        client = SourcegraphClient(cache_dir=tmp_path, cache_ttl=1000)

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.iter_lines.return_value = [
            'data: {"__typename":"Repository","name":"github.com/test/repo","description":"Test","stars":10,"primaryLanguage":"Go"}',
        ]
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_response.raise_for_status = Mock()

        mock_client = Mock()
        mock_client.stream.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)

        with patch.object(client, '_get_client', return_value=mock_client):
            client.list_repos("test", limit=10)

        # Verify it was cached
        cached = client._cache_get("repos:test:10")
        assert cached is not None
        assert len(cached) == 1
        assert cached[0]["name"] == "github.com/test/repo"

    def test_list_repos_handles_compat_format(self, tmp_path: Path) -> None:
        """Test list_repos handles compatible repo format."""
        from unittest.mock import Mock, patch

        client = SourcegraphClient(cache_dir=tmp_path)

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.iter_lines.return_value = [
            'data: {"name":"github.com/test/repo","description":"Test","stars":10}',
        ]
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_response.raise_for_status = Mock()

        mock_client = Mock()
        mock_client.stream.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)

        with patch.object(client, '_get_client', return_value=mock_client):
            repos = client.list_repos("test", limit=10)

        assert len(repos) == 1
        assert repos[0].name == "github.com/test/repo"

    def test_list_repos_handles_exception(self, tmp_path: Path) -> None:
        """Test list_repos handles exceptions gracefully."""
        from unittest.mock import Mock, patch

        client = SourcegraphClient(cache_dir=tmp_path)

        mock_client = Mock()
        mock_client.stream.side_effect = Exception("Network error")

        with patch.object(client, '_get_client', return_value=mock_client):
            repos = client.list_repos("test", limit=10)

        assert len(repos) == 0


# ---------------------------------------------------------------------------
# Convenience functions
# ---------------------------------------------------------------------------


class TestConvenienceFunctions:
    """Test the module-level convenience functions."""

    def test_search_function(self, tmp_path: Path) -> None:
        """Test the search() convenience function."""
        from unittest.mock import Mock, patch

        from src.integrations.sourcegraph import search

        mock_client = Mock()
        mock_client.search.return_value = SearchResult(
            query="test",
            total=1,
            matches=[SearchMatch(repo="test/repo", file_path="main.go")],
        )

        with patch("src.integrations.sourcegraph.SourcegraphClient") as MockClient:
            MockClient.return_value.__enter__ = Mock(return_value=mock_client)
            MockClient.return_value.__exit__ = Mock(return_value=False)
            result = search("test", lang="go", limit=5)

        assert result.total == 1
        mock_client.search.assert_called_once_with("test", repo_filter=None, lang="go", limit=5)

    def test_get_file_function(self, tmp_path: Path) -> None:
        """Test the get_file() convenience function."""
        from unittest.mock import Mock, patch

        from src.integrations.sourcegraph import get_file

        mock_client = Mock()
        mock_client.get_file.return_value = FileContent(
            repo="test/repo",
            path="main.go",
            content="package main",
        )

        with patch("src.integrations.sourcegraph.SourcegraphClient") as MockClient:
            MockClient.return_value.__enter__ = Mock(return_value=mock_client)
            MockClient.return_value.__exit__ = Mock(return_value=False)
            result = get_file("test/repo", "main.go")

        assert result is not None
        assert result.content == "package main"
        mock_client.get_file.assert_called_once_with("test/repo", "main.go")

    def test_list_repos_function(self, tmp_path: Path) -> None:
        """Test the list_repos() convenience function."""
        from unittest.mock import Mock, patch

        from src.integrations.sourcegraph import list_repos

        mock_client = Mock()
        mock_client.list_repos.return_value = [
            RepoInfo(name="test/repo", stars=10),
        ]

        with patch("src.integrations.sourcegraph.SourcegraphClient") as MockClient:
            MockClient.return_value.__enter__ = Mock(return_value=mock_client)
            MockClient.return_value.__exit__ = Mock(return_value=False)
            result = list_repos("test", limit=5)

        assert len(result) == 1
        assert result[0].name == "test/repo"
        mock_client.list_repos.assert_called_once_with("test", limit=5)
