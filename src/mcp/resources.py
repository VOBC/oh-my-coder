from __future__ import annotations

"""
MCP Resources — 把 .omc/ 工作区暴露为 MCP resources

resource URI 格式：
- omc://workspace/summary     — 工作区摘要
- omc://workspace/structure    — 项目目录结构
- omc://workspace/files        — 关键文件内容
- omc://checkpoint/list       — 所有 checkpoint 列表
- omc://skill/list             — 所有 Skill 列表
"""

import contextlib
from pathlib import Path
from typing import Any

# 工作区根目录
_WORKSPACE: Path | None = None


def set_workspace(workspace: Path) -> None:
    global _WORKSPACE
    _WORKSPACE = workspace.resolve()


def get_workspace() -> Path:
    return _WORKSPACE or Path.cwd()


# ------------------------------------------------------------------
# Resource 内容生成
# ------------------------------------------------------------------


def _generate_summary(workspace: Path) -> str:
    """生成工作区摘要"""
    stats = _project_stats(workspace)
    omc_dir = workspace / ".omc"

    lines = [
        f"# 工作区摘要: {workspace.name}",
        "",
        f"**路径**: `{workspace}`",
        f"**文件总数**: {stats['total_files']}",
        f"**代码行数**: {stats['code_lines']}",
        "",
        "## 语言分布",
    ]
    for lang, count in stats.get("by_language", {}).items():
        lines.append(f"  - {lang}: {count} 文件")

    # Checkpoint 数量
    checkpoint_dir = omc_dir / "checkpoints"
    if checkpoint_dir.exists():
        import json

        index_file = checkpoint_dir / "index.json"
        if index_file.exists():
            try:
                data = json.loads(index_file.read_text(encoding="utf-8"))
                lines.append("")
                lines.append("## 快照")
                lines.append(f"  - Checkpoints: {len(data)} 个")
            except Exception:
                pass

    # Skill 数量
    skill_dir = omc_dir / "skills"
    if skill_dir.exists():
        import json

        index_file = skill_dir / "index.json"
        if index_file.exists():
            try:
                data = json.loads(index_file.read_text(encoding="utf-8"))
                lines.append("")
                lines.append("## 经验沉淀")
                lines.append(f"  - Skills: {len(data)} 个")
            except Exception:
                pass

    return "\n".join(lines)


def _generate_structure(workspace: Path, depth: int = 3) -> str:
    """生成项目目录结构"""
    lines = [f"# 项目结构: {workspace.name}", ""]

    ignore_dirs = {
        ".git",
        ".omc",
        "__pycache__",
        ".pytest_cache",
        ".ruff_cache",
        ".mypy_cache",
        ".venv",
        "venv",
        "node_modules",
        ".env",
        ".DS_Store",
        "dist",
        "build",
        "htmlcov",
        ".tox",
    }

    def walk(path: Path, prefix: str = "", level: int = 0):
        if level > depth:
            return
        try:
            items = sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name))
            for i, item in enumerate(items):
                if item.name in ignore_dirs:
                    continue
                is_last = i == len(items) - 1
                connector = "└── " if is_last else "├── "
                lines.append(f"{prefix}{connector}{item.name}")
                if item.is_dir():
                    new_prefix = prefix + ("    " if is_last else "│   ")
                    walk(item, new_prefix, level + 1)
        except PermissionError:
            pass

    lines.append(workspace.name)
    walk(workspace, "", 0)
    return "\n".join(lines)


def _generate_files(workspace: Path) -> str:
    """生成关键文件内容"""
    extensions = {".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".java"}
    key_files = []

    for ext in extensions:
        for f in workspace.rglob(f"*{ext}"):
            if f.is_file() and f.parent.name not in {
                ".git",
                ".omc",
                "venv",
                "node_modules",
            }:
                key_files.append(f)

    key_files.sort(key=lambda f: f.stat().st_size, reverse=True)
    key_files = key_files[:20]  # 最多 20 个文件

    lines = ["# 关键文件内容（按大小排序）", ""]
    for f in key_files:
        try:
            rel = f.relative_to(workspace)
            lines.append(f"## {rel}")
            content = f.read_text(encoding="utf-8", errors="replace")
            # 限制每个文件最多显示 100 行
            content_lines = content.splitlines()[:100]
            lines.append("```")
            lines.extend(content_lines)
            lines.append("```")
            lines.append("")
        except Exception:
            pass

    return "\n".join(lines)


def _project_stats(workspace: Path) -> dict[str, Any]:
    """统计项目信息"""
    extensions = {
        ".py": "Python",
        ".js": "JavaScript",
        ".ts": "TypeScript",
        ".jsx": "JSX",
        ".tsx": "TSX",
        ".go": "Go",
        ".rs": "Rust",
        ".java": "Java",
        ".c": "C",
        ".cpp": "C++",
        ".h": "C/C++ Header",
    }
    ignore_dirs = {
        ".git",
        ".omc",
        "__pycache__",
        ".pytest_cache",
        ".ruff_cache",
        ".mypy_cache",
        ".venv",
        "venv",
        "node_modules",
        ".env",
        "dist",
        "build",
        ".tox",
    }

    file_counts: dict[str, int] = {}
    code_lines = 0
    total_files = 0

    for item in workspace.rglob("*"):
        if item.is_dir():
            if item.name in ignore_dirs or any(p in item.parts for p in ignore_dirs):
                continue
        elif item.is_file():
            ext = item.suffix.lower()
            if ext in extensions:
                total_files += 1
                file_counts[extensions[ext]] = file_counts.get(extensions[ext], 0) + 1
                with contextlib.suppress(Exception):
                    code_lines += len(
                        item.read_text(encoding="utf-8", errors="ignore").splitlines()
                    )

    return {
        "total_files": total_files,
        "code_lines": code_lines,
        "by_language": file_counts,
    }


# ------------------------------------------------------------------
# MCP Resource 定义
# ------------------------------------------------------------------

MCP_RESOURCES: list[dict[str, Any]] = [
    {
        "uri": "omc://workspace/summary",
        "name": "workspace_summary",
        "description": "当前工作区摘要（文件统计、语言分布、checkpoint、skill 数量）",
        "mimeType": "text/markdown",
        "generator": lambda: _generate_summary(get_workspace()),
    },
    {
        "uri": "omc://workspace/structure",
        "name": "workspace_structure",
        "description": "项目目录结构（目录树，深度 3）",
        "mimeType": "text/markdown",
        "generator": lambda: _generate_structure(get_workspace()),
    },
    {
        "uri": "omc://workspace/files",
        "name": "workspace_key_files",
        "description": "关键文件内容（按大小排序，最多 20 个，每个最多 100 行）",
        "mimeType": "text/markdown",
        "generator": lambda: _generate_files(get_workspace()),
    },
]


def get_mcp_resources() -> list[dict[str, Any]]:
    """获取所有 MCP resources（dict 格式）"""
    return MCP_RESOURCES
