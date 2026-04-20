"""
Sourcegraph 集成 - 让 AI 能搜索公开代码库

支持两种模式：
1. Sourcegraph API（需要 API Key，免费 tier 足够日常使用）
2. src CLI（本地安装，无需 API Key）

文档：https://sourcegraph.com/docs
免费 API Key: https://sourcegraph.com/user/settings/tokens
"""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

# =============================================================================
# 配置
# =============================================================================

SG_API_KEY = os.getenv("SOURCEGRAPH_API_KEY", "")
SG_ENDPOINT = os.getenv("SOURCEGRAPH_ENDPOINT", "https://sourcegraph.com/.api")
SG_CLI_PATH = os.getenv("SRC_CLI_PATH", "src")  # src 或完整路径

# src CLI 安装：brew install sourcegraph/tap/src
SRC_CLI_INSTALL_CMD = "brew install sourcegraph/tap/src"

# =============================================================================
# 数据模型
# =============================================================================


@dataclass
class SearchMatch:
    """单个搜索结果"""

    repo: str
    file_path: str
    repository_stars: int = 0
    repo_description: str = ""
    content_preview: str = ""  # 匹配行上下文
    line_number: int = 0
    language: str = ""
    url: str = ""
    symbols: list[str] = field(default_factory=list)  # 函数/类名

    def format_code(self) -> str:
        """格式化代码片段"""
        lines = [f"[{self.repo}:{self.file_path}:{self.line_number}]"]
        if self.symbols:
            lines.append(f"  # 定义: {', '.join(self.symbols[:3])}")
        if self.content_preview:
            for line in self.content_preview.splitlines()[:8]:
                lines.append(f"  {line}")
        return "\n".join(lines)


@dataclass
class SearchResult:
    """完整搜索结果"""

    query: str
    total_matches: int
    matches: list[SearchMatch]
    elapsed_ms: int
    source: str  # "api" | "cli"
    warnings: list[str] = field(default_factory=list)

    def format_table(self, limit: int = 10) -> str:
        """格式化表格输出"""
        lines = [
            f"[cyan]Query:[/] {self.query}  "
            f"[green]Matches:[/] {self.total_matches}  "
            f"[dim]Time:[/] {self.elapsed_ms}ms  "
            f"[dim]Source:[/] {self.source}"
        ]
        if self.warnings:
            for w in self.warnings:
                lines.append(f"[yellow]⚠ {w}[/yellow]")
        lines.append("")
        for i, m in enumerate(self.matches[:limit], 1):
            stars = f"⭐{m.repo_stars}" if m.repo_stars else ""
            lang = f"[blue]{m.language}[/blue]" if m.language else ""
            lines.append(
                f"  {i}. [green]{m.repo}[/green]{stars} {m.file_path}:{m.line_number} {lang}"
            )
            if m.symbols:
                lines.append(f"     └─ {' | '.join(m.symbols[:3])}")
            if m.content_preview:
                for ln in m.content_preview.splitlines()[:3]:
                    lines.append(f"     {ln[:120]}")
        if len(self.matches) > limit:
            lines.append(
                f"\n  [dim]... 还有 {len(self.matches) - limit} 个结果，使用 --limit 调整[/dim]"
            )
        return "\n".join(lines)

    def format_json(self) -> str:
        """JSON 输出"""
        return json.dumps(
            {
                "query": self.query,
                "total": self.total_matches,
                "elapsed_ms": self.elapsed_ms,
                "source": self.source,
                "matches": [
                    {
                        "repo": m.repo,
                        "file": m.file_path,
                        "line": m.line_number,
                        "language": m.language,
                        "stars": m.repo_stars,
                        "symbols": m.symbols,
                        "preview": m.content_preview[:200],
                        "url": m.url,
                    }
                    for m in self.matches
                ],
            },
            ensure_ascii=False,
            indent=2,
        )

    def format_code(self, limit: int = 5) -> str:
        """AI 友好的代码输出"""
        lines = [f"# Search: {self.query} ({self.total_matches} matches)\n"]
        for m in self.matches[:limit]:
            lines.append(m.format_code())
            lines.append("")
        return "\n".join(lines)


# =============================================================================
# Sourcegraph API 客户端
# =============================================================================


def _sg_api_search(query: str, **kwargs: Any) -> SearchResult | None:
    """通过 Sourcegraph API 搜索"""
    if not SG_API_KEY:
        return None

    # 构建 GraphQL 查询
    variables = {
        "query": query,
        "first": min(kwargs.get("limit", 20), 100),
    }
    if kwargs.get("repo"):
        variables["query"] = f"{query} repo:{kwargs['repo']}"
    if kwargs.get("language"):
        variables["query"] = f"{query} lang:{kwargs['language']}"
    if kwargs.get("after"):
        variables["query"] = f"{variables['query']} after:{kwargs['after']}"
    if kwargs.get("before"):
        variables["query"] = f"{variables['query']} before:{kwargs['before']}"

    gql_query = """
    query Search($query: String!, $first: Int!) {
        search(query: $query, version: V3) {
            results {
                matchCount
                timedOut { timedOut }
                __typename
                ... on SearchConnection {
                    results {
                        __typename
                        ... on Repository {
                            name
                            url
                            stars { totalCount }
                            description
                        }
                        ... on FileMatch {
                            repository { name url stars { totalCount } description }
                            file { path url }
                            lineMatches {
                                preview
                                lineNumber
                                offsetAndLengths { offset length }
                            }
                            symbols {
                                name
                                kind
                                containerName
                                url
                            }
                        }
                    }
                }
            }
            elapsedMilliseconds
        }
    }
    """

    body = {"query": gql_query, "variables": variables}
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"token {SG_API_KEY}",
    }

    try:
        resp = httpx.post(
            f"{SG_ENDPOINT}/graphql",
            json=body,
            headers=headers,
            timeout=15.0,
        )
        resp.raise_for_status()
        data = resp.json()
    except httpx.HTTPStatusError as e:
        return SearchResult(
            query=query,
            total_matches=0,
            matches=[],
            elapsed_ms=0,
            source="api",
            warnings=[f"API 错误: {e.response.status_code}"],
        )
    except Exception as e:
        return SearchResult(
            query=query,
            total_matches=0,
            matches=[],
            elapsed_ms=0,
            source="api",
            warnings=[f"连接失败: {e}"],
        )

    search_data = data.get("data", {}).get("search", {})
    results_conn = search_data.get("results", {})
    raw_results = results_conn.get("results", [])
    elapsed = search_data.get("elapsedMilliseconds", 0)

    matches: list[SearchMatch] = []
    total = 0

    for item in raw_results:
        typename = item.get("__typename", "")
        if typename == "Repository":
            continue  # 跳过纯仓库结果
        if typename == "FileMatch":
            repo_info = item.get("repository", {})
            file_info = item.get("file", {})
            repo_name = repo_info.get("name", "")
            file_path = file_info.get("path", "")

            for lm in item.get("lineMatches", []):
                symbols = [
                    (
                        f"{s['containerName']}.{s['name']}"
                        if s.get("containerName")
                        else s.get("name", "")
                    )
                    for s in item.get("symbols", [])
                    if s.get("name")
                ]
                match = SearchMatch(
                    repo=repo_name,
                    file_path=file_path,
                    repo_stars=repo_info.get("stars", {}).get("totalCount", 0),
                    repo_description=repo_info.get("description", ""),
                    content_preview=lm.get("preview", ""),
                    line_number=lm.get("lineNumber", 0),
                    url=f"https://sourcegraph.com/{repo_name}/-{file_path}",
                )
                matches.append(match)

    # 估算 total
    match_count = results_conn.get("matchCount", 0)
    if isinstance(match_count, int):
        total = match_count

    return SearchResult(
        query=query,
        total_matches=total,
        matches=matches,
        elapsed_ms=int(elapsed),
        source="api",
    )


# =============================================================================
# src CLI 客户端
# =============================================================================


def _check_src_cli() -> bool:
    """检查 src CLI 是否可用"""
    try:
        result = subprocess.run(
            [SG_CLI_PATH, "version"],
            capture_output=True,
            timeout=5,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _src_cli_search(query: str, **kwargs: Any) -> SearchResult | None:
    """通过 src CLI 搜索"""
    if not _check_src_cli():
        return None

    cmd = [SG_CLI_PATH, "search", "-json", "-limit", str(kwargs.get("limit", 20))]
    if kwargs.get("language"):
        cmd.extend(["-pattern", f"lang:{kwargs['language']}"])
    if kwargs.get("repo"):
        cmd.extend(["-pattern", f"repo:{kwargs['repo']}"])

    cmd.append(query)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            timeout=30,
            env={**os.environ, "SRC_ENDPOINT": SG_ENDPOINT},
        )
        if result.returncode != 0:
            return SearchResult(
                query=query,
                total_matches=0,
                matches=[],
                elapsed_ms=0,
                source="cli",
                warnings=[result.stderr.decode().strip()[:200]],
            )
        output = result.stdout.decode("utf-8", errors="replace")
    except Exception as e:
        return SearchResult(
            query=query,
            total_matches=0,
            matches=[],
            elapsed_ms=0,
            source="cli",
            warnings=[f"src CLI 错误: {e}"],
        )

    matches: list[SearchMatch] = []
    try:
        for line in output.splitlines():
            if not line.strip():
                continue
            item = json.loads(line)
            if item.get("type") == "content":
                match = SearchMatch(
                    repo=item.get("repo", ""),
                    file_path=item.get("path", ""),
                    content_preview=item.get("content", {}).get("preview", ""),
                    line_number=item.get("line", 0),
                    language=item.get("language", ""),
                    url=item.get("url", ""),
                )
                matches.append(match)
            elif item.get("type") == "symbol":
                # 符号搜索结果
                context = item.get("context", {})
                match = SearchMatch(
                    repo=item.get("repo", ""),
                    file_path=context.get("file", {}).get("path", ""),
                    content_preview=item.get("symbol", {}).get("name", ""),
                    symbols=[item.get("symbol", {}).get("name", "")],
                    url=item.get("url", ""),
                )
                matches.append(match)
    except json.JSONDecodeError:
        return SearchResult(
            query=query,
            total_matches=0,
            matches=[],
            elapsed_ms=0,
            source="cli",
            warnings=["src CLI 输出解析失败"],
        )

    return SearchResult(
        query=query,
        total_matches=len(matches),
        matches=matches,
        elapsed_ms=0,
        source="cli",
    )


# =============================================================================
# 主搜索函数
# =============================================================================


def search(
    query: str,
    language: str | None = None,
    repo: str | None = None,
    limit: int = 20,
    after: str | None = None,
    before: str | None = None,
    prefer_api: bool = True,
) -> SearchResult:
    """
    搜索代码。自动选择可用后端：
    1. Sourcegraph API（有 API Key）
    2. src CLI（本地安装）
    """
    kwargs: dict[str, Any] = {
        "limit": limit,
        "language": language,
        "repo": repo,
        "after": after,
        "before": before,
    }

    # 优先 API
    if prefer_api and SG_API_KEY:
        result = _sg_api_search(query, **kwargs)
        if result:
            return result

    # 回退到 CLI
    result = _src_cli_search(query, **kwargs)
    if result:
        return result

    # 兜底：返回友好的错误信息
    return SearchResult(
        query=query,
        total_matches=0,
        matches=[],
        elapsed_ms=0,
        source="none",
        warnings=[
            "Sourcegraph API Key 未设置（SOURCEGRAPH_API_KEY）",
            "src CLI 也未安装",
            f"安装 src CLI: {SRC_CLI_INSTALL_CMD}",
            "或获取 API Key: https://sourcegraph.com/user/settings/tokens",
        ],
    )


def install_src_cli() -> tuple[bool, str]:
    """安装 src CLI，返回 (成功, 消息)"""
    import platform

    system = platform.system()
    if system == "Darwin":
        cmd = ["brew", "install", "sourcegraph/tap/src"]
    elif system == "Linux":
        cmd = ["sh", "-c", "curl -L https://sourcegraph.com/.api/src-cli.sh | sh"]
    elif system == "Windows":
        cmd = ["scoop", "install", "src"]
    else:
        return False, f"不支持的系统: {system}"

    try:
        result = subprocess.run(cmd, capture_output=True, timeout=60)
        if result.returncode == 0:
            return True, "src CLI 安装成功"
        stderr = result.stderr.decode(errors="replace")
        return False, f"安装失败: {stderr[:200]}"
    except Exception as e:
        return False, f"安装异常: {e}"


def setup_api_key(api_key: str) -> tuple[bool, str]:
    """配置 Sourcegraph API Key"""

    if not api_key:
        return False, "API Key 不能为空"

    # 写入 .env 文件
    env_file = Path.home() / ".omc" / ".env"
    env_file.parent.mkdir(parents=True, exist_ok=True)

    content = env_file.read_text(errors="replace") if env_file.exists() else ""
    lines = content.splitlines()
    # 替换或追加
    found = False
    new_lines: list[str] = []
    for line in lines:
        if line.strip().startswith("SOURCEGRAPH_API_KEY"):
            new_lines.append(f"SOURCEGRAPH_API_KEY={api_key}")
            found = True
        else:
            new_lines.append(line)
    if not found:
        new_lines.append(f"SOURCEGRAPH_API_KEY={api_key}")

    env_file.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    return True, f"已保存到 {env_file}"


def check_status() -> dict[str, Any]:
    """检查各后端状态"""
    has_api = bool(SG_API_KEY)
    has_cli = _check_src_cli()

    return {
        "api": {
            "available": has_api,
            "endpoint": SG_ENDPOINT if has_api else None,
            "key_prefix": f"{SG_API_KEY[:4]}..." if has_api else None,
        },
        "cli": {
            "available": has_cli,
            "path": SG_CLI_PATH,
        },
        "recommendation": "api" if has_api else ("cli" if has_cli else "none"),
    }
