
# mypy: disable-error-code="abstract, arg-type, assignment, attr-defined, call-arg, call-overload, dict-item, func-returns-value, import-untyped, index, misc, no-any-return, no-redef, operator, override, return, return-value, syntax, union-attr, var-annotated"
"""

文件统计结果的数据模型定义。
"""

from dataclasses import dataclass, field


@dataclass
class FileStats:
    """按类型统计的文件信息。"""

    count: int = 0
    """文件数量"""

    size: int = 0
    """文件总大小（字节）"""

    files: list[str] = field(default_factory=list)
    """文件路径列表（相对于项目根目录）"""


@dataclass
class StatsResult:
    """文件统计结果。"""

    total_files: int = 0
    """总文件数"""

    total_dirs: int = 0
    """总目录数"""

    total_size: int = 0
    """总大小（字节）"""

    by_type: dict[str, FileStats] = field(default_factory=dict)
    """按文件类型分类的统计结果"""

    by_directory: dict[str, int] = field(default_factory=dict)
    """按目录分类的文件数量"""

    errors: list[str] = field(default_factory=list)
    """统计过程中遇到的错误列表"""

    root_path: str = ""
    """统计的根目录路径"""

    def to_dict(self) -> dict:
        """将统计结果转换为字典。

        Returns:
            可序列化的字典
        """
        return {
            "total_files": self.total_files,
            "total_dirs": self.total_dirs,
            "total_size": self.total_size,
            "total_size_human": self._format_size(self.total_size),
            "by_type": {
                k: {
                    "count": v.count,
                    "size": v.size,
                    "size_human": self._format_size(v.size),
                    "files": v.files,
                }
                for k, v in self.by_type.items()
            },
            "by_directory": self.by_directory,
            "errors": self.errors,
            "root_path": self.root_path,
        }

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """将字节大小格式化为人类可读的字符串。

        Args:
            size_bytes: 字节大小

        Returns:
            格式化后的大小字符串，如 "1.23 MB"
        """
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size_bytes < 1024:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.2f} PB"

    def __str__(self) -> str:
        """生成人类可读的统计报告。"""
        lines = []
        lines.append("=" * 50)
        lines.append("📊 项目文件统计报告")
        lines.append("=" * 50)
        lines.append(f"根目录: {self.root_path}")
        lines.append("")
        lines.append(f"📁 总目录数: {self.total_dirs}")
        lines.append(f"📄 总文件数: {self.total_files}")
        lines.append(f"💾 总大小:   {self._format_size(self.total_size)}")
        lines.append("")

        if self.by_type:
            lines.append("📂 按文件类型统计:")
            lines.append(f"{'类型':<25} {'数量':>8} {'大小':>12}")
            lines.append("-" * 47)
            for file_type, stats in self.by_type.items():
                lines.append(
                    f"{file_type:<25} {stats.count:>8} {self._format_size(stats.size):>12}"
                )
            lines.append("")

        if self.by_directory:
            lines.append("📁 按目录统计 (Top 20):")
            lines.append(f"{'目录':<40} {'数量':>8}")
            lines.append("-" * 48)
            for i, (directory, count) in enumerate(self.by_directory.items()):
                if i >= 20:
                    lines.append(f"{'... (更多)':<40}")
                    break
                lines.append(f"{directory:<40} {count:>8}")
            lines.append("")

        if self.errors:
            lines.append(f"⚠️ 统计过程中的错误 ({len(self.errors)}):")
            for err in self.errors[:5]:
                lines.append(f"  - {err}")
            if len(self.errors) > 5:
                lines.append(f"  ... 还有 {len(self.errors) - 5} 个错误")
            lines.append("")

        lines.append("=" * 50)
        return "\n".join(lines)
