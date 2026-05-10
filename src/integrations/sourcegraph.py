
# mypy: disable-error-code="abstract, arg-type, assignment, attr-defined, call-arg, call-overload, dict-item, func-returns-value, import-untyped, index, misc, no-any-return, no-redef, operator, override, return, return-value, syntax, union-attr, var-annotated"
"""

Sourcegraph 集成模块 - 公开 API 客户端

使用 Sourcegraph 公开 streaming API，无需 API Key。
支持代码搜索、文件获取、仓库搜索。

API 文档: https://sourcegraph.com/docs/api
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import httpx

# =============================================================================
# 配置
# =============================================================================

SG_API_BASE = "https://sourcegraph.com/.api"
SG_CACHE_DIR = Path.home() / ".omc" / "cache" / "sourcegraph"
SG_CACHE_TTL = 300  # 5 分钟缓存


# =============================================================================
# 数据模型
# =============================================================================


@dataclass
class SearchMatch:
    """单个搜索结果"""

    repo: str
    file_path: str
    line_number: int = 0
    line_content: str = ""
    language: str = ""
    repository_stars: int = 0
    url: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "repo": self.repo,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "line_content": self.line_content,
            "language": self.language,
            "repository_stars": self.repository_stars,
            "url": self.url,
        }


@dataclass
class FileContent:
    """文件内容结果"""

    repo: str
    path: str
    content: str
    language: str = ""
    url: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "repo": self.repo,
            "path": self.path,
            "content": self.content,
            "language": self.language,
            "url": self.url,
        }


@dataclass
class RepoInfo:
    """仓库信息"""

    name: str
    description: str = ""
    stars: int = 0
    language: str = ""
    url: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "stars": self.stars,
            "language": self.language,
            "url": self.url,
        }


@dataclass
class SearchResult:
    """搜索结果"""

    query: str
    total: int
    matches: list[SearchMatch]
    elapsed_ms: float = 0
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "total": self.total,
            "elapsed_ms": self.elapsed_ms,
            "matches": [m.to_dict() for m in self.matches],
            "warnings": self.warnings,
        }


# =============================================================================
# Sourcegraph Client
# =============================================================================


class SourcegraphClient:
    """
    Sourcegraph 公开 API 客户端

    使用 streaming API，无需 API Key。

    示例:
        client = SourcegraphClient()
        result = client.search("func main() lang:go", limit=10)
        for match in result.matches:
            print(f"{match.repo}:{match.file_path}:{match.line_number}")
    """

    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        cache_ttl: int = SG_CACHE_TTL,
        timeout: float = 30.0,
    ):
        self.cache_dir = cache_dir or SG_CACHE_DIR
        self.cache_ttl = cache_ttl
        self.timeout = timeout
        self._client: Optional[httpx.Client] = None

    def _get_client(self) -> httpx.Client:
        """获取 HTTP 客户端"""
        if self._client is None:
            self._client = httpx.Client(
                timeout=self.timeout,
                follow_redirects=True,
                headers={
                    "Accept": "application/json",
                    "User-Agent": "omc-sourcegraph-client/1.0",
                },
            )
        return self._client

    def _cache_get(self, key: str) -> Optional[Any]:
        """从缓存获取数据"""
        if not self.cache_dir.exists():
            return None

        cache_file = self.cache_dir / f"{hashlib.sha256(key.encode()).hexdigest()}.json"
        if not cache_file.exists():
            return None

        try:
            data = json.loads(cache_file.read_text(encoding="utf-8"))
            if time.time() - data.get("timestamp", 0) < self.cache_ttl:
                return data.get("value")
        except (json.JSONDecodeError, KeyError):
            pass
        return None

    def _cache_set(self, key: str, value: Any) -> None:
        """设置缓存"""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = self.cache_dir / f"{hashlib.sha256(key.encode()).hexdigest()}.json"
        cache_file.write_text(
            json.dumps({"timestamp": time.time(), "value": value}, ensure_ascii=False),
            encoding="utf-8",
        )

    def _build_search_query(
        self,
        query: str,
        repo_filter: Optional[str] = None,
        lang: Optional[str] = None,
        limit: int = 20,
    ) -> str:
        """构建搜索查询"""
        parts = [query]
        if repo_filter:
            parts.append(f"repo:{repo_filter}")
        if lang:
            parts.append(f"lang:{lang}")
        parts.append(f"count:{limit}")
        return " ".join(parts)

    def search(
        self,
        query: str,
        repo_filter: Optional[str] = None,
        lang: Optional[str] = None,
        limit: int = 20,
        use_cache: bool = True,
    ) -> SearchResult:
        """
        搜索代码

        Args:
            query: 搜索关键词或 Sourcegraph 查询语法
            repo_filter: 仓库过滤，支持 glob 模式如 "github.com/golang/*"
            lang: 语言过滤，如 "go", "python", "typescript"
            limit: 返回结果数量
            use_cache: 是否使用缓存

        Returns:
            SearchResult 包含匹配列表
        """
        full_query = self._build_search_query(query, repo_filter, lang, limit)
        cache_key = f"search:{full_query}"

        # 检查缓存
        if use_cache:
            cached = self._cache_get(cache_key)
            if cached:
                matches = [SearchMatch(**m) for m in cached.get("matches", [])]
                return SearchResult(
                    query=query,
                    total=cached.get("total", len(matches)),
                    matches=matches,
                    elapsed_ms=0,
                    warnings=["from cache"],
                )

        # 调用 streaming API
        url = f"{SG_API_BASE}/search/stream"
        client = self._get_client()

        start_time = time.time()
        matches: list[SearchMatch] = []
        warnings: list[str] = []

        try:
            # streaming API 使用 POST
            with client.stream(
                "POST",
                url,
                content=full_query,
                headers={"Content-Type": "text/plain"},
            ) as response:
                response.raise_for_status()

                for line in response.iter_lines():
                    if not line.strip():
                        continue

                    # 解析 streaming 格式
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])
                            match = self._parse_search_result(data)
                            if match:
                                matches.append(match)
                                if len(matches) >= limit:
                                    break
                        except json.JSONDecodeError:
                            continue
                    elif line.startswith("error: "):
                        warnings.append(line[7:])

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                warnings.append("API 限流，请稍后重试")
            elif e.response.status_code == 401:
                warnings.append("需要认证（公开 API 不应出现此错误）")
            else:
                warnings.append(f"HTTP 错误: {e.response.status_code}")
        except httpx.TimeoutException:
            warnings.append("请求超时")
        except Exception as e:
            warnings.append(f"请求失败: {e}")

        elapsed = (time.time() - start_time) * 1000

        result = SearchResult(
            query=query,
            total=len(matches),
            matches=matches,
            elapsed_ms=elapsed,
            warnings=warnings,
        )

        # 缓存结果
        if use_cache and matches:
            self._cache_set(cache_key, result.to_dict())

        return result

    def _parse_search_result(self, data: dict[str, Any]) -> Optional[SearchMatch]:
        """解析搜索结果"""
        # streaming API 返回格式可能是多种类型
        result_type = data.get("__typename") or data.get("type")

        if result_type == "FileMatch" or "file" in data:
            repo_info = data.get("repository", {})
            file_info = data.get("file", {})
            line_matches = data.get("lineMatches", [])

            if line_matches:
                first_line = line_matches[0]
                return SearchMatch(
                    repo=repo_info.get("name", ""),
                    file_path=file_info.get("path", ""),
                    line_number=first_line.get("lineNumber", 0) + 1,  # 0-indexed to 1-indexed
                    line_content=first_line.get("preview", ""),
                    language=file_info.get("language", ""),
                    repository_stars=repo_info.get("stars", {}).get("totalCount", 0)
                    if isinstance(repo_info.get("stars"), dict)
                    else repo_info.get("stars", 0),
                    url=f"https://sourcegraph.com/{repo_info.get('name', '')}/-/{file_info.get('path', '')}",
                )
            else:
                return SearchMatch(
                    repo=repo_info.get("name", ""),
                    file_path=file_info.get("path", ""),
                    url=f"https://sourcegraph.com/{repo_info.get('name', '')}/-/{file_info.get('path', '')}",
                )

        # 兼容其他格式
        if "repository" in data and "path" in data:
            return SearchMatch(
                repo=data.get("repository", ""),
                file_path=data.get("path", ""),
                line_number=data.get("line", 0),
                line_content=data.get("content", ""),
                url=data.get("url", ""),
            )

        return None

    def get_file(
        self,
        repo: str,
        path: str,
        use_cache: bool = True,
    ) -> Optional[FileContent]:
        """
        获取文件内容

        Args:
            repo: 仓库名，如 "github.com/golang/go"
            path: 文件路径，如 "src/runtime/proc.go"
            use_cache: 是否使用缓存

        Returns:
            FileContent 或 None
        """
        cache_key = f"file:{repo}:{path}"

        if use_cache:
            cached = self._cache_get(cache_key)
            if cached:
                return FileContent(**cached)

        url = f"{SG_API_BASE}/repos/{repo}/-/raw/{path}"
        client = self._get_client()

        try:
            response = client.get(url)
            response.raise_for_status()
            content = response.text

            # 推断语言
            lang = self._infer_language(path)

            result = FileContent(
                repo=repo,
                path=path,
                content=content,
                language=lang,
                url=f"https://sourcegraph.com/{repo}/-/{path}",
            )

            if use_cache:
                self._cache_set(cache_key, result.to_dict())

            return result

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise
        except Exception:
            return None

    def list_repos(
        self,
        query: str,
        limit: int = 10,
        use_cache: bool = True,
    ) -> list[RepoInfo]:
        """
        搜索仓库

        Args:
            query: 搜索关键词
            limit: 返回数量
            use_cache: 是否使用缓存

        Returns:
            RepoInfo 列表
        """
        cache_key = f"repos:{query}:{limit}"

        if use_cache:
            cached = self._cache_get(cache_key)
            if cached:
                return [RepoInfo(**r) for r in cached]

        # 使用搜索 API 的 type:repo 过滤
        search_query = f"type:repo {query} count:{limit}"
        url = f"{SG_API_BASE}/search/stream"
        client = self._get_client()

        repos: list[RepoInfo] = []

        try:
            with client.stream(
                "POST",
                url,
                content=search_query,
                headers={"Content-Type": "text/plain"},
            ) as response:
                response.raise_for_status()

                for line in response.iter_lines():
                    if not line.strip() or not line.startswith("data: "):
                        continue

                    try:
                        data = json.loads(line[6:])
                        if data.get("__typename") == "Repository" or "name" in data:
                            repo = RepoInfo(
                                name=data.get("name", ""),
                                description=data.get("description", ""),
                                stars=data.get("stars", {}).get("totalCount", 0)
                                if isinstance(data.get("stars"), dict)
                                else data.get("stars", 0),
                                language=data.get("primaryLanguage", {}).get("name", "")
                                if isinstance(data.get("primaryLanguage"), dict)
                                else "",
                                url=f"https://sourcegraph.com/{data.get('name', '')}",
                            )
                            repos.append(repo)
                            if len(repos) >= limit:
                                break
                    except json.JSONDecodeError:
                        continue

        except Exception:
            pass

        if use_cache and repos:
            self._cache_set(cache_key, [r.to_dict() for r in repos])

        return repos

    def _infer_language(self, path: str) -> str:
        """从文件扩展名推断语言"""
        ext_map = {
            ".py": "Python",
            ".js": "JavaScript",
            ".ts": "TypeScript",
            ".tsx": "TypeScript",
            ".jsx": "JavaScript",
            ".go": "Go",
            ".rs": "Rust",
            ".java": "Java",
            ".kt": "Kotlin",
            ".swift": "Swift",
            ".c": "C",
            ".cpp": "C++",
            ".cc": "C++",
            ".h": "C",
            ".hpp": "C++",
            ".cs": "C#",
            ".rb": "Ruby",
            ".php": "PHP",
            ".scala": "Scala",
            ".clj": "Clojure",
            ".ex": "Elixir",
            ".erl": "Erlang",
            ".hs": "Haskell",
            ".ml": "OCaml",
            ".fs": "F#",
            ".vue": "Vue",
            ".svelte": "Svelte",
            ".sh": "Shell",
            ".bash": "Shell",
            ".zsh": "Shell",
            ".ps1": "PowerShell",
            ".lua": "Lua",
            ".r": "R",
            ".m": "MATLAB",
            ".sql": "SQL",
            ".html": "HTML",
            ".css": "CSS",
            ".scss": "SCSS",
            ".less": "Less",
            ".json": "JSON",
            ".yaml": "YAML",
            ".yml": "YAML",
            ".xml": "XML",
            ".toml": "TOML",
            ".md": "Markdown",
            ".rst": "reStructuredText",
        }
        ext = Path(path).suffix.lower()
        return ext_map.get(ext, "")

    def close(self) -> None:
        """关闭客户端"""
        if self._client:
            self._client.close()
            self._client = None

    def __enter__(self) -> SourcegraphClient:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()


# =============================================================================
# 便捷函数
# =============================================================================


def search(
    query: str,
    repo: Optional[str] = None,
    lang: Optional[str] = None,
    limit: int = 20,
) -> SearchResult:
    """
    快捷搜索函数

    示例:
        result = search("http.Client", lang="go", limit=5)
        for m in result.matches:
            print(f"{m.repo}:{m.file_path}:{m.line_number}")
    """
    with SourcegraphClient() as client:
        return client.search(query, repo_filter=repo, lang=lang, limit=limit)


def get_file(repo: str, path: str) -> Optional[FileContent]:
    """快捷获取文件内容"""
    with SourcegraphClient() as client:
        return client.get_file(repo, path)


def list_repos(query: str, limit: int = 10) -> list[RepoInfo]:
    """快捷搜索仓库"""
    with SourcegraphClient() as client:
        return client.list_repos(query, limit=limit)
