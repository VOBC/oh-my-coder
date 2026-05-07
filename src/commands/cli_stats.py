"""
oh-my-coder stats 命令实现。

提供项目文件统计功能，支持按类型、按目录分类统计。
"""

import json
import sys
from typing import Optional, Set

import click

from src.stats import count_files


@click.command(name="stats")
@click.argument(
    "path",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, readable=True),
    default=".",
    required=False,
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="以 JSON 格式输出统计结果",
)
@click.option(
    "--exclude-dir",
    "exclude_dirs",
    multiple=True,
    help="额外排除的目录名（可多次指定）",
)
@click.option(
    "--exclude-file",
    "exclude_files",
    multiple=True,
    help="额外排除的文件名（可多次指定）",
)
@click.option(
    "--exclude-ext",
    "exclude_extensions",
    multiple=True,
    help="额外排除的文件扩展名（可多次指定）",
)
@click.option(
    "--max-depth",
    type=int,
    default=None,
    help="最大递归深度",
)
@click.option(
    "--follow-symlinks",
    is_flag=True,
    default=False,
    help="跟随符号链接",
)
@click.option(
    "--sort",
    "sort_by",
    type=click.Choice(["type", "count", "size", "directory"]),
    default="count",
    help="排序方式（仅 JSON 输出有效）",
)
def stats_command(
    path: str,
    output_json: bool,
    exclude_dirs: tuple,
    exclude_files: tuple,
    exclude_extensions: tuple,
    max_depth: Optional[int],
    follow_symlinks: bool,
    sort_by: str,
) -> None:
    """统计项目文件数量。

    PATH 是要