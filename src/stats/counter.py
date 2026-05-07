"""
项目文件统计核心模块。

提供文件遍历、分类统计、排除规则等功能。
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from .models import FileStats, StatsResult


def _is_excluded(
    path: Path,
    exclude_dirs: Set[str],
    exclude_files: Set[str],
    exclude_extensions: Set[str],
) -> bool:
    """检查路径是否应被排除。

    Args:
        path: 要检查的路径
        exclude_dirs: 要排除的目录名集合（不区分大小写）
        exclude_files: 要排除的文件名集合（不区分大小写）
        exclude_extensions: 要排除的文件扩展名集合（不区分大小写）

    Returns:
        如果路径应被排除则返回 True
    """
    name_lower = path.name.lower()

    # 检查是否在排除的文件名列表中
    if path.is_file() and name_lower in exclude_files:
        return True

    # 检查是否在排除的目录名列表中
    if path.is_dir() and name_lower in exclude_dirs:
        return True

    # 检查文件扩展名
    if path.is_file():
        ext = path.suffix.lower()
        if ext in exclude_extensions:
            return True

    return False


def _get_file_type(path: Path) -> str:
    """根据文件扩展名获取文件类型分类。

    Args:
        path: 文件路径

    Returns:
        文件类型描述字符串
    """
    ext = path.suffix.lower()
    type_map = {
        ".py": "Python",
        ".js": "JavaScript",
        ".ts": "TypeScript",
        ".tsx": "TypeScript React",
        ".jsx": "JavaScript React",
        ".md": "Markdown",
        ".json": "JSON",
        ".yaml": "YAML",
        ".yml": "YAML",
        ".toml": "TOML",
        ".html": "HTML",
        ".css": "CSS",
        ".scss": "SCSS",
        ".less": "LESS",
        ".rs": "Rust",
        ".go": "Go",
        ".java": "Java",
        ".cpp": "C++",
        ".c": "C",
        ".h": "C/C++ Header",
        ".sh": "Shell Script",
        ".bash": "Bash Script",
        ".ps1": "PowerShell",
        ".bat": "Batch",
        ".dockerfile": "Dockerfile",
        ".xml": "XML",
        ".svg": "SVG",
        ".png": "PNG Image",
        ".jpg": "JPEG Image",
        ".jpeg": "JPEG Image",
        ".gif": "GIF Image",
        ".ico": "Icon",
        ".txt": "Text",
        ".cfg": "Config",
        ".ini": "Config",
        ".conf": "Config",
        ".lock": "Lock File",
        ".env": "Environment",
        ".gitignore": "Git Ignore",
        ".gitkeep": "Git Keep",
        ".editorconfig": "Editor Config",
        ".prettierrc": "Prettier Config",
        ".eslintrc": "ESLint Config",
        ".babelrc": "Babel Config",
    }

    # 特殊处理无扩展名的文件（如 Dockerfile, Makefile）
    if not ext:
        name_lower = path.name.lower()
        special_files = {
            "dockerfile": "Dockerfile",
            "makefile": "Makefile",
            "gemfile": "Gemfile",
            "rakefile": "Rakefile",
            "procfile": "Procfile",
        }
        return special_files.get(name_lower, "Other")

    return type_map.get(ext, f"Other ({ext})")


def count_files(
    root_path: str | Path,
    exclude_dirs: Optional[Set[str]] = None,
    exclude_files: Optional[Set[str]] = None,
    exclude_extensions: Optional[Set[str]] = None,
    follow_symlinks: bool = False,
    max_depth: Optional[int] = None,
) -> StatsResult:
    """递归统计项目文件数量。

    Args:
        root_path: 项目根目录路径
        exclude_dirs: 要排除的目录名集合（不区分大小写），默认排除常见构建产物
        exclude_files: 要排除的文件名集合（不区分大小写）
        exclude_extensions: 要排除的文件扩展名集合（不区分大小写）
        follow_symlinks: 是否跟随符号链接
        max_depth: 最大递归深度，None 表示不限制

    Returns:
        StatsResult 对象，包含统计结果

    Raises:
        FileNotFoundError: 如果根目录不存在
        PermissionError: 如果没有权限访问根目录
    """
    root = Path(root_path).resolve()

    if not root.exists():
        raise FileNotFoundError(f"目录不存在: {root}")
    if not root.is_dir():
        raise NotADirectoryError(f"路径不是目录: {root}")
    if not os.access(root, os.R_OK):
        raise PermissionError(f"没有权限访问目录: {root}")

    # 默认排除目录
    default_exclude_dirs = {
        "node_modules",
        "__pycache__",
        ".git",
        ".svn",
        ".hg",
        ".idea",
        ".vscode",
        ".vs",
        ".github",
        "site",
        "dist",
        "build",
        ".egg-info",
        ".tox",
        "venv",
        ".venv",
        "env",
        ".env",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".cache",
        ".next",
        ".nuxt",
        ".output",
        "coverage",
        ".coverage",
        "htmlcov",
        ".sass-cache",
        ".DS_Store",
        "thumbs.db",
        "__MACOSX",
        "target",  # Rust build
        "bin",
        "obj",  # .NET build
        ".serverless",
        ".terraform",
        ".serverless_nextjs",
        "cdk.out",
    }

    # 默认排除的文件
    default_exclude_files = {
        ".ds_store",
        "thumbs.db",
        "desktop.ini",
        ".gitkeep",
    }

    # 默认排除的扩展名
    default_exclude_extensions = {
        ".pyc",
        ".pyo",
        ".pyd",
        ".so",
        ".dll",
        ".dylib",
        ".class",
        ".o",
        ".obj",
        ".lib",
        ".exe",
        ".msi",
        ".app",
        ".dmg",
        ".deb",
        ".rpm",
        ".zip",
        ".tar",
        ".gz",
        ".bz2",
        ".7z",
        ".rar",
        ".iso",
        ".img",
        ".log",
        ".tmp",
        ".temp",
        ".swp",
        ".swo",
        ".bak",
        ".orig",
    }

    # 合并排除列表（默认 + 自定义）
    final_exclude_dirs = default_exclude_dirs | (exclude_dirs or set())
    final_exclude_files = default_exclude_files | (exclude_files or set())
    final_exclude_extensions = default_exclude_extensions | (exclude_extensions or set())

    # 统计结果
    total_files = 0
    total_dirs = 0
    total_size = 0
    by_type: Dict[str, FileStats] = {}
    by_directory: Dict[str, int] = {}
    errors: List[str] = []

    # 使用栈进行深度优先遍历（避免递归深度限制）
    # 栈元素: (路径, 当前深度)
    stack: List[Tuple[Path, int]] = [(root, 0)]

    while stack:
        current_path, current_depth = stack.pop()

        # 检查最大深度
        if max_depth is not None and current_depth >= max_depth:
            continue

        try:
            with os.scandir(current_path) as entries:
                for entry in entries:
                    entry_path = Path(entry.path)

                    # 检查是否应排除
                    if _is_excluded(
                        entry_path,
                        final_exclude_dirs,
                        final_exclude_files,
                        final_exclude_extensions,
                    ):
                        continue

                    if entry.is_dir(follow_symlinks=follow_symlinks):
                        total_dirs += 1
                        stack.append((entry_path, current_depth + 1))
                    elif entry.is_file(follow_symlinks=follow_symlinks):
                        total_files += 1
                        file_size = entry.stat(follow_symlinks=follow_symlinks).st_size
                        total_size += file_size

                        # 按文件类型统计
                        file_type = _get_file_type(entry_path)
                        if file_type not in by_type:
                            by_type[file_type] = FileStats(
                                count=0, size=0, files=[]
                            )
                        by_type[file_type].count += 1
                        by_type[file_type].size += file_size
                        by_type[file_type].files.append(str(entry_path.relative_to(root)))

                        # 按目录统计
                        parent_dir = str(entry_path.parent.relative_to(root))
                        if parent_dir == ".":
                            parent_dir = "/"
                        if parent_dir not in by_directory:
                            by_directory[parent_dir] = 0
                        by_directory[parent_dir] += 1

        except PermissionError as e:
            errors.append(f"权限不足，跳过目录: {current_path}")
        except OSError as e:
            errors.append(f"访问错误，跳过目录: {current_path} - {e}")

    return StatsResult(
        total_files=total_files,
        total_dirs=total_dirs,
        total_size=total_size,
        by_type=dict(sorted(by_type.items(), key=lambda x: x[1].count, reverse=True)),
        by_directory=dict(
            sorted(by_directory.items(), key=lambda x: x[1], reverse=True)
        ),
        errors=errors,
        root_path=str(root),
    )