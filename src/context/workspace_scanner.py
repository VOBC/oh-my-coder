"""
工作目录扫描器 - Workspace Scanner

扫描工作目录，生成文件树结构，用于为 AI Agent 提供项目上下文。
支持语言检测、文件摘要、深度控制。
"""

import time
from dataclasses import dataclass, field
from pathlib import Path

# 排除的目录和文件（与 .gitignore 类似逻辑）
EXCLUDE_DIRS = {
    ".git",
    ".svn",
    ".hg",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    ".tox",
    ".venv",
    "venv",
    "env",
    ".env",
    "node_modules",
    "dist",
    "build",
    ".egg-info",
    ".coverage",
    ".hypothesis",
    "assets",
    "static",
    "public",
    ".idea",
    ".vscode",
    ".DS_Store",
}

EXCLUDE_EXTENSIONS = {
    ".pyc",
    ".pyo",
    ".so",
    ".dylib",
    ".dll",
    ".exe",
    ".bin",
    ".dat",
    ".log",
    ".lock",
    ".swp",
    ".swo",
    ".tmp",
    ".temp",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".ico",
    ".webp",
    ".svg",
    ".mp3",
    ".mp4",
    ".wav",
    ".flac",
    ".zip",
    ".tar",
    ".gz",
    ".rar",
    ".7z",
    ".pdf",
    ".class",
    ".o",
    ".obj",
}


@dataclass
class FileNode:
    """
    文件树节点

    用于表示目录或文件的树形结构。
    """

    name: str
    path: Path
    is_dir: bool
    size: int = 0
    modified: str = ""
    language: str | None = None  # 代码语言
    summary: str | None = None  # 文件摘要
    children: list["FileNode"] = field(default_factory=list)

    def to_dict(self) -> dict:
        """转换为字典（用于 JSON 序列化）"""
        return {
            "name": self.name,
            "path": str(self.path),
            "is_dir": self.is_dir,
            "size": self.size,
            "modified": self.modified,
            "language": self.language,
            "summary": self.summary,
            "children": [c.to_dict() for c in self.children],
        }


class WorkspaceScanner:
    """
    工作目录扫描器

    扫描指定目录，生成文件树结构，并提供文件摘要功能。

    使用示例：
        scanner = WorkspaceScanner(Path("/path/to/project"))
        tree = scanner.scan(max_depth=3)
        print(scanner.to_context_string())
    """

    # 支持的语言及文件扩展名
    LANGUAGE_EXTENSIONS = {
        ".py": "python",
        ".pyw": "python",
        ".js": "javascript",
        ".jsx": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".go": "go",
        ".rs": "rust",
        ".java": "java",
        ".kt": "kotlin",
        ".cs": "csharp",
        ".cpp": "cpp",
        ".c": "c",
        ".h": "c",
        ".hpp": "cpp",
        ".swift": "swift",
        ".rb": "ruby",
        ".php": "php",
        ".md": "markdown",
        ".rst": "rst",
        ".json": "json",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".toml": "toml",
        ".xml": "xml",
        ".html": "html",
        ".htm": "html",
        ".css": "css",
        ".scss": "scss",
        ".less": "less",
        ".sh": "bash",
        ".bash": "bash",
        ".zsh": "bash",
        ".fish": "bash",
        ".sql": "sql",
        ".graphql": "graphql",
        ".proto": "protobuf",
        ".dockerfile": "dockerfile",
        ".vue": "vue",
        ".svelte": "svelte",
        ".r": "r",
        ".lua": "lua",
        ".pl": "perl",
        ".hs": "haskell",
        ".ex": "elixir",
        ".exs": "elixir",
        ".erl": "erlang",
        ".jl": "julia",
        ".scala": "scala",
        ".groovy": "groovy",
        ".gradle": "groovy",
        ".tf": "hcl",
        ".tfvars": "hcl",
    }

    # 特殊文件名语言映射
    LANGUAGE_FILENAMES = {
        "dockerfile": "dockerfile",
        "makefile": "makefile",
        "gemfile": "ruby",
        "rakefile": "ruby",
        ".gitignore": "gitignore",
        ".dockerignore": "dockerignore",
        ".env.example": "bash",
        "cmakelists.txt": "cmake",
        "package.json": "json",
        "tsconfig.json": "json",
        "pyproject.toml": "toml",
        "setup.py": "python",
        "requirements.txt": "python",
        "pipfile": "toml",
        "poetry.lock": "json",
    }

    def __init__(self, root: Path):
        """
        初始化扫描器

        Args:
            root: 根目录路径
        """
        self.root = Path(root)
        self._cache: dict = {}
        self._scan_stats = {
            "files_scanned": 0,
            "dirs_scanned": 0,
            "bytes_scanned": 0,
            "errors": [],
        }

    def scan(self, max_depth: int = 3) -> FileNode:
        """
        扫描工作目录，返回文件树

        Args:
            max_depth: 最大递归深度（0 = 仅根目录文件）

        Returns:
            FileNode: 根节点
        """
        self._scan_stats = {
            "files_scanned": 0,
            "dirs_scanned": 0,
            "bytes_scanned": 0,
            "errors": [],
        }
        return self._scan_recursive(self.root, depth=0, max_depth=max_depth)

    def _scan_recursive(self, path: Path, depth: int, max_depth: int) -> FileNode:
        """递归扫描"""
        node = FileNode(
            name=path.name or str(path),
            path=path,
            is_dir=path.is_dir(),
        )

        if not path.exists():
            return node

        try:
            stat = path.stat()
            node.size = stat.st_size
            node.modified = time.strftime(
                "%Y-%m-%d %H:%M", time.localtime(stat.st_mtime)
            )
        except OSError:
            pass

        if not path.is_dir():
            node.language = self._detect_language(path)
            return node

        # 目录
        self._scan_stats["dirs_scanned"] += 1
        node.is_dir = True

        # 达到最大深度，不再递归子目录（但仍列出当前节点）
        # max_depth=0: 只显示根节点；max_depth=1: 显示根+一层子目录
        if depth >= max_depth:
            return node

        try:
            entries = list(path.iterdir())
        except PermissionError:
            self._scan_stats["errors"].append(f"Permission denied: {path}")
            return node
        except OSError as e:
            self._scan_stats["errors"].append(f"{path}: {e}")
            return node

        # 先收集，再排序（目录优先，同类型按名字排序）
        children: list[FileNode] = []
        for entry in entries:
            name = entry.name

            # 跳过隐藏文件（但保留 .gitignore 等特殊文件）
            if name.startswith(".") and name not in (
                ".gitignore",
                ".dockerignore",
                ".env.example",
                ".env",
            ):
                continue

            # 跳过排除的目录
            if entry.is_dir() and name in EXCLUDE_DIRS:
                continue

            # 跳过排除的扩展名
            if entry.is_file():
                ext = entry.suffix.lower()
                if ext in EXCLUDE_EXTENSIONS:
                    continue
                if name.startswith("."):
                    continue

            child = self._scan_recursive(entry, depth=depth + 1, max_depth=max_depth)
            children.append(child)

            if entry.is_file():
                self._scan_stats["files_scanned"] += 1
                self._scan_stats["bytes_scanned"] += child.size
            else:
                self._scan_stats["dirs_scanned"] += 1

        # 排序：目录优先，再按名字
        def sort_key(n: FileNode) -> tuple:
            return (not n.is_dir, n.name.lower())

        children.sort(key=sort_key)
        node.children = children

        return node

    def _detect_language(self, path: Path) -> str | None:
        """检测文件语言"""
        name = path.name.lower()
        ext = path.suffix.lower()

        # 优先检查特殊文件名
        if name in self.LANGUAGE_FILENAMES:
            return self.LANGUAGE_FILENAMES[name]

        # 再检查扩展名
        return self.LANGUAGE_EXTENSIONS.get(ext)

    def get_file_summary(self, path: Path, max_lines: int = 50) -> str:
        """
        获取文件摘要（用于上下文）

        对于代码文件，提取前 N 行作为摘要。
        对于大型文件，只读取配置或注释。

        Args:
            path: 文件路径
            max_lines: 最大读取行数

        Returns:
            str: 文件摘要字符串
        """
        path = Path(path)

        if not path.exists():
            return f"[文件不存在: {path}]"

        if path.is_dir():
            return f"[目录: {path}]"

        try:
            stat = path.stat()
        except OSError:
            return f"[无法读取: {path}]"

        # 小文件直接读取全部
        if stat.st_size < 10 * 1024:  # < 10KB
            lines = self._read_file_lines(path, max_lines)
        else:
            # 大文件只读取前面部分
            lines = self._read_file_lines(path, max_lines)

        if not lines:
            return f"[空文件: {path.name}]"

        # 构建摘要
        language = self._detect_language(path)
        lines[0] if lines else ""

        # 检测文件类型并提取关键信息
        summary_parts = []

        if language == "python":
            summary_parts = self._summarize_python(lines, path)
        elif language in ("javascript", "typescript"):
            summary_parts = self._summarize_js_ts(lines, path)
        elif language == "json":
            summary_parts = self._summarize_json(path)
        elif language in ("yaml", "toml"):
            summary_parts = self._summarize_config(lines, path)
        elif language in ("markdown", "rst"):
            summary_parts = self._summarize_doc(lines, path)
        elif language == "dockerfile":
            summary_parts = self._summarize_dockerfile(lines, path)
        else:
            # 通用摘要：前几行
            summary_parts = lines[: max_lines // 2]

        # 组合摘要
        if isinstance(summary_parts, list) and summary_parts:
            body = "\n".join(summary_parts)
        else:
            body = str(summary_parts)

        return f"""[{language or "unknown"}] {path.name}
路径: {path.relative_to(self.root) if path.is_relative_to(self.root) else path}
大小: {self._format_size(stat.st_size)}
修改: {time.strftime("%Y-%m-%d %H:%M", time.localtime(stat.st_mtime))}

--- 内容摘要 ---
{body}"""

    def _read_file_lines(self, path: Path, max_lines: int) -> list[str]:
        """安全读取文件行"""
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                lines = []
                for i, line in enumerate(f):
                    if i >= max_lines:
                        break
                    lines.append(line.rstrip("\n\r"))
                return lines
        except OSError:
            return []

    def _summarize_python(self, lines: list[str], path: Path) -> list[str]:
        """Python 文件摘要：提取导入、类、函数定义"""
        result = []
        imports = []
        classes = []
        functions = []

        for line in lines:
            stripped = line.strip()
            if stripped.startswith(("import ", "from ")):
                if len(imports) < 10:
                    imports.append(stripped)
            elif stripped.startswith("class "):
                # 提取类名
                parts = stripped.split()
                if len(parts) >= 2:
                    classes.append(parts[1].split("(")[0])
            elif stripped.startswith("def "):
                # 提取函数名
                parts = stripped.split("(", 1)
                if len(parts) >= 1:
                    fname = parts[0].replace("async ", "").replace("def ", "")
                    functions.append(fname)

        if imports:
            result.append(
                f"导入: {', '.join(imports[:5])}" + (" ..." if len(imports) > 5 else "")
            )
        if classes:
            result.append(f"类: {', '.join(classes)}")
        if functions:
            result.append(
                f"函数: {', '.join(functions[:10])}"
                + (" ..." if len(functions) > 10 else "")
            )

        # 如果没提取到，返回前几行
        if not result:
            result = lines[:10]

        return result

    def _summarize_js_ts(self, lines: list[str], path: Path) -> list[str]:
        """JS/TS 文件摘要：提取导入、导出、函数"""
        result = []
        imports = []
        exports = []
        functions = []

        for line in lines:
            stripped = line.strip()
            if stripped.startswith("import "):
                if len(imports) < 10:
                    imports.append(stripped[:80])
            elif stripped.startswith("export "):
                if len(exports) < 10:
                    exports.append(stripped[:80])
            elif "function " in stripped or "=> {" in stripped:
                if len(functions) < 10:
                    # 提取函数名
                    fn_match = (
                        stripped.split("function")[1].split("(")[0].strip()
                        if "function" in stripped
                        else ""
                    )
                    functions.append(fn_match or stripped[:50])

        if imports:
            result.append(f"导入: {len(imports)} 个依赖")
        if exports:
            result.append(
                f"导出: {', '.join(exports[:5])}" + (" ..." if len(exports) > 5 else "")
            )
        if functions:
            result.append(
                f"函数: {', '.join(functions[:10])}"
                + (" ..." if len(functions) > 10 else "")
            )

        if not result:
            result = lines[:10]

        return result

    def _summarize_json(self, path: Path) -> list[str]:
        """JSON 文件摘要"""
        try:
            import json

            with open(path, encoding="utf-8") as f:
                data = json.load(f)

            if isinstance(data, dict):
                keys = list(data.keys())[:20]
                return [f"键: {', '.join(keys)}" + (" ..." if len(data) > 20 else "")]
            if isinstance(data, list):
                return [
                    f"数组: {len(data)} 项，示例: {str(data[0])[:100] if data else '[]'}"
                ]
            return [str(data)[:200]]
        except Exception:
            return ["[JSON 解析失败]"]

    def _summarize_config(self, lines: list[str], path: Path) -> list[str]:
        """YAML/TOML 配置摘要"""
        result = []
        for line in lines[:30]:
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                if stripped.startswith("["):
                    result.append(f"章节: {stripped}")
                elif ":" in stripped:
                    key = stripped.split(":")[0].strip()
                    if key:
                        result.append(f"  {key}")
        return result[:20]

    def _summarize_doc(self, lines: list[str], path: Path) -> list[str]:
        """Markdown/RST 文档摘要"""
        result = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("#"):
                result.append(stripped)
            elif stripped.startswith(("===", "---")):
                continue
            elif result and len(result) < 10:
                result.append(stripped[:100])

        if result:
            return result[:15]
        return lines[:10]

    def _summarize_dockerfile(self, lines: list[str], path: Path) -> list[str]:
        """Dockerfile 摘要"""
        result = ["FROM / 指令:"]
        for line in lines:
            stripped = line.strip()
            if stripped.startswith(("FROM ", "RUN ", "COPY ", "WORKDIR ")):
                result.append(f"  {stripped}")
        return result[:15]

    def _format_size(self, size: int) -> str:
        """格式化文件大小"""
        if size < 1024:
            return f"{size}B"
        if size < 1024 * 1024:
            return f"{size / 1024:.1f}KB"
        if size < 1024 * 1024 * 1024:
            return f"{size / (1024 * 1024):.1f}MB"
        return f"{size / (1024 * 1024 * 1024):.1f}GB"

    def to_context_string(self, max_depth: int = 3) -> str:
        """
        生成可用于 Prompt 的上下文字符串

        扫描当前工作目录，生成人类可读的文件树。

        Args:
            max_depth: 扫描深度

        Returns:
            str: 上下文字符串
        """
        tree = self.scan(max_depth=max_depth)
        lines = self._render_tree(tree, prefix="", is_last=True)
        lines.append("")

        # 添加统计信息
        stats = self._scan_stats
        lines.append(
            f"共扫描 {stats['files_scanned']} 个文件，{stats['dirs_scanned']} 个目录"
        )
        lines.append(f"总大小: {self._format_size(stats['bytes_scanned'])}")

        if stats["errors"]:
            lines.append(f"扫描时发生 {len(stats['errors'])} 个错误")

        return "\n".join(lines)

    def _render_tree(self, node: FileNode, prefix: str, is_last: bool) -> list[str]:
        """渲染文件树"""
        lines = []

        # 当前节点
        connector = "└── " if is_last else "├── "
        size_str = f" ({self._format_size(node.size)})" if node.size > 0 else ""
        lang_str = f" [{node.language}]" if node.language else ""
        modified_str = f" {node.modified}" if node.modified else ""

        lines.append(
            f"{prefix}{connector}{node.name}{size_str}{lang_str}{modified_str}"
        )

        # 子节点
        if node.children:
            child_prefix = prefix + ("    " if is_last else "│   ")
            for i, child in enumerate(node.children):
                is_child_last = i == len(node.children) - 1
                child_lines = self._render_tree(child, child_prefix, is_child_last)
                lines.extend(child_lines)

        return lines
