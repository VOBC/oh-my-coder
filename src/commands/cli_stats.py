
# mypy: disable-error-code="abstract, arg-type, assignment, attr-defined, call-arg, call-overload, dict-item, func-returns-value, import-untyped, index, misc, no-any-return, no-redef, operator, override, return, return-value, syntax, union-attr, var-annotated"
"""

oh-my-coder stats 命令实现。

提供项目文件统计功能，支持按类型、按目录分类统计。
"""

import json
from typing import Optional

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

    PATH 是要统计的项目根目录路径，默认为当前目录。
    """
    result = count_files(
        root_path=path,
        exclude_dirs=set(exclude_dirs),
        exclude_files=set(exclude_files),
        exclude_extensions=set(exclude_extensions),
        max_depth=max_depth,
        follow_symlinks=follow_symlinks,
    )

    if output_json:
        data = {
            "total_files": result.total_files,
            "total_dirs": result.total_dirs,
            "total_size": result.total_size,
            "by_type": {k: v.to_dict() for k, v in result.by_type.items()},
            "by_directory": result.by_directory,
            "errors": result.errors,
        }
        click.echo(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        click.echo(f"📊 项目统计: {path}")
        click.echo(f"  文件总数: {result.total_files}")
        click.echo(f"  目录总数: {result.total_dirs}")
        click.echo(f"  总大小: {result.total_size:,} 字节")
        if result.by_type:
            click.echo("\n📁 按类型分类:")
            sorted_types = sorted(
                result.by_type.items(),
                key=lambda x: x[1].count,
                reverse=True,
            )
            for ext, stats in sorted_types:
                click.echo(f"  {ext or '(无扩展名)'}: {stats.count} 个文件, {stats.total_size:,} 字节")
        if result.errors:
            click.echo(f"\n⚠️ {len(result.errors)} 个错误:", err=True)
            for error in result.errors:
                click.echo(f"  {error}", err=True)
