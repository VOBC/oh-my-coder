"""
代码清理 Agent - 自动清理冗余代码，提升可维护性

清理策略白名单：
1. 未使用的 import / 函数 / 变量（ruff 可检测）
2. 重复代码片段（>5 行相同视为重复）
3. 死代码文件（无引用模块）
4. 空文件 / 占位文件
5. 过时配置文件

不删除：
- 有注释的业务逻辑文件
- 测试文件
- 配置文件
- 文档文件
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class CleanerStrategy:
    """清理策略白名单"""

    # 是否启用该策略
    enabled: bool = True

    # 1. 未使用 import/函数/变量
    unused_imports: bool = True  # ruff check --fix
    unused_functions: bool = True
    unused_variables: bool = True

    # 2. 重复代码检测
    detect_duplicates: bool = True
    duplicate_min_lines: int = 5  # 超过此行数视为重复

    # 3. 死代码检测
    detect_dead_code: bool = True
    dead_code_safe_mode: bool = True  # 标记但不自动删除

    # 4. 空文件检测
    detect_empty_files: bool = True
    auto_delete_empty: bool = False  # 是否自动删除空文件

    # 5. 过时配置文件
    detect_outdated_configs: bool = True
    outdated_patterns: list[str] = field(
        default_factory=lambda: [
            r"\.env\.example\.bak",
            r"config\.old",
            r"\.pyc$",
            r"__pycache__",
        ]
    )


@dataclass
class CleaningIssue:
    """单个清理问题"""

    file_path: str
    issue_type: str  # unused_import, duplicate, dead_code, empty, outdated
    line_start: int | None = None
    line_end: int | None = None
    content: str = ""  # 问题内容摘要
    severity: str = "warning"  # info/warning/error
    auto_fixable: bool = False
    fix_suggestion: str = ""


@dataclass
class CleanerReport:
    """清理报告"""

    timestamp: str = ""
    project_path: str = ""

    # 统计
    total_issues: int = 0
    files_scanned: int = 0

    # 按类型统计
    by_type: dict[str, int] = field(default_factory=dict)

    # 问题列表
    issues: list[CleaningIssue] = field(default_factory=list)

    # 已修复
    fixed_count: int = 0
    fixed_files: list[str] = field(default_factory=list)

    # 待确认（需人工审核）
    pending_count: int = 0
    pending_issues: list[CleaningIssue] = field(default_factory=list)

    # token 节省估算
    lines_removed: int = 0
    estimated_token_savings: int = 0


class CodeCleaner:
    """代码清理器

    使用策略白名单自动检测和清理冗余代码。
    """

    def __init__(
        self,
        project_path: Path,
        strategy: CleanerStrategy | None = None,
    ):
        self.project_path = Path(project_path)
        self.strategy = strategy or CleanerStrategy()

        # 扫描到的 Python 文件
        self.python_files: list[Path] = []

        # 分析结果
        self.issues: list[CleaningIssue] = []

    def scan(self) -> CleanerReport:
        """扫描项目，返回清理报告"""
        report = CleanerReport(
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            project_path=str(self.project_path),
        )

        # 1. 收集 Python 文件
        self.python_files = self._collect_python_files()
        report.files_scanned = len(self.python_files)

        # 2. 执行各项检测
        if self.strategy.unused_imports or self.strategy.unused_functions:
            self._check_unused_code()

        if self.strategy.detect_duplicates:
            self._check_duplicate_code()

        if self.strategy.detect_dead_code:
            self._check_dead_code()

        if self.strategy.detect_empty_files:
            self._check_empty_files()

        if self.strategy.detect_outdated_configs:
            self._check_outdated_configs()

        # 3. 生成报告
        self.issues = self.issues
        report.issues = self.issues
        report.total_issues = len(self.issues)

        # 按类型统计
        for issue in self.issues:
            report.by_type[issue.issue_type] = (
                report.by_type.get(issue.issue_type, 0) + 1
            )

        # 分类：自动修复 vs 待确认
        auto_fixable = [i for i in self.issues if i.auto_fixable]
        pending = [i for i in self.issues if not i.auto_fixable]

        report.pending_issues = pending
        report.pending_count = len(pending)

        # 计算 token 节省
        report.lines_removed = sum(
            (i.line_end or 0) - (i.line_start or 0) + 1 for i in auto_fixable
        )
        report.estimated_token_savings = report.lines_removed * 10  # 估算

        return report

    def _collect_python_files(self) -> list[Path]:
        """收集所有 Python 文件（排除测试、虚拟环境等）"""
        files = []
        exclude_dirs = {
            ".git",
            ".venv",
            "venv",
            "env",
            "__pycache__",
            ".pytest_cache",
            "node_modules",
            "build",
            "dist",
            ".tox",
        }

        for path in self.project_path.rglob("*.py"):
            # 跳过排除目录
            if any(ex in path.parts for ex in exclude_dirs):
                continue
            # 跳过测试文件（可选）
            if "test_" in path.name or path.name.startswith("test_"):
                continue
            files.append(path)

        return files

    def _check_unused_code(self):
        """检测未使用的 import/函数/变量"""
        # 使用 ruff 检测
        try:
            result = subprocess.run(
                [
                    "python3",
                    "-m",
                    "ruff",
                    "check",
                    "--select",
                    "F401,F841,F821",
                    "--output-format",
                    "json",
                    str(self.project_path),
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode != 0:
                try:
                    errors = json.loads(result.stdout)
                except json.JSONDecodeError:
                    return

                for err in errors:
                    location = err.get("location", {})
                    file_path = err.get("filename", "")

                    if not file_path:
                        continue

                    # 判断问题类型
                    code = err.get("code", "")
                    if code == "F401":
                        issue_type = "unused_import"
                    elif code == "F841":
                        issue_type = "unused_variable"
                    else:
                        issue_type = "unused_code"

                    self.issues.append(
                        CleaningIssue(
                            file_path=file_path,
                            issue_type=issue_type,
                            line_start=location.get("row"),
                            line_end=location.get("row"),
                            content=err.get("message", "")[:100],
                            severity="warning",
                            auto_fixable=True,
                            fix_suggestion="删除未使用的代码",
                        )
                    )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass  # ruff 未安装或超时，跳过

    def _check_duplicate_code(self):
        """检测重复代码片段"""
        # 简化版：按函数/方法哈希检测
        # 完整实现需要更复杂的 AST 分析

        code_hashes: dict[str, list[tuple[Path, int]]] = {}

        for py_file in self.python_files:
            try:
                content = py_file.read_text(encoding="utf-8")
                lines = content.split("\n")

                # 按函数分割（简化：空行分隔的大于5行代码块）
                current_block = []
                for i, line in enumerate(lines, 1):
                    stripped = line.strip()
                    if not stripped or stripped.startswith("#"):
                        continue
                    current_block.append(line)

                    # 如果遇到函数定义，处理之前的块
                    if re.match(r"^def\s+", stripped) or re.match(
                        r"^class\s+", stripped
                    ):
                        if len(current_block) >= self.strategy.duplicate_min_lines:
                            block_text = "\n".join(current_block)
                            block_hash = hash(block_text)
                            if block_hash not in code_hashes:
                                code_hashes[block_hash] = []
                            code_hashes[block_hash].append(
                                (py_file, i - len(current_block))
                            )

                        current_block = []

                # 处理最后一个块
                if len(current_block) >= self.strategy.duplicate_min_lines:
                    block_text = "\n".join(current_block)
                    block_hash = hash(block_text)
                    if block_hash not in code_hashes:
                        code_hashes[block_hash] = []
                    code_hashes[block_hash].append(
                        (py_file, len(lines) - len(current_block))
                    )

            except Exception:
                continue

        # 找出重复的代码块
        for locations in code_hashes.values():
            if len(locations) >= 2:
                locations_str = ", ".join(
                    f"{p.name}:{line}" for p, line in locations[:3]
                )
                self.issues.append(
                    CleaningIssue(
                        file_path=locations[0][0].name,
                        issue_type="duplicate_code",
                        line_start=locations[0][1],
                        line_end=locations[0][1] + self.strategy.duplicate_min_lines,
                        content=f"疑似重复代码，可能在其他位置出现: {locations_str}",
                        severity="info",
                        auto_fixable=False,
                        fix_suggestion="提取为公共函数",
                    )
                )

    def _check_dead_code(self):
        """检测死代码（无引用的函数/类）"""
        # 构建引用图
        all_names: set[str] = set()  # 所有定义的名称
        referenced_names: set[str] = set()  # 被引用的名称

        for py_file in self.python_files:
            try:
                content = py_file.read_text(encoding="utf-8")

                # 提取定义的函数/类名
                for match in re.finditer(
                    r"^(?:def|class)\s+(\w+)", content, re.MULTILINE
                ):
                    all_names.add(match.group(1))

                # 提取被引用的名称（简化）
                for match in re.finditer(r"\b(\w+)\b", content):
                    name = match.group(1)
                    if name in all_names:
                        referenced_names.add(name)

            except Exception:
                continue

        # 找出未被引用的定义
        dead_names = all_names - referenced_names

        # 只报告明显未使用的（谨慎）
        for py_file in self.python_files:
            try:
                content = py_file.read_text(encoding="utf-8")
                for name in dead_names:
                    # 检查是否在文件中定义
                    if re.search(
                        rf"^(?:def|class)\s+{re.escape(name)}", content, re.MULTILINE
                    ):
                        self.issues.append(
                            CleaningIssue(
                                file_path=str(py_file),
                                issue_type="dead_code",
                                content=f"函数/类 '{name}' 未被引用",
                                severity="info",
                                auto_fixable=False,
                                fix_suggestion="确认后删除或添加文档说明其用途",
                            )
                        )
            except Exception:
                continue

    def _check_empty_files(self):
        """检测空文件"""
        for py_file in self.python_files:
            try:
                content = py_file.read_text(encoding="utf-8")
                stripped = content.strip()

                # 空文件或只有注释的文件
                if not stripped or (
                    stripped
                    and all(
                        line.strip().startswith(("#", '"""', "'''"))
                        for line in stripped.split("\n")
                    )
                ):
                    self.issues.append(
                        CleaningIssue(
                            file_path=str(py_file),
                            issue_type="empty_file",
                            content="空文件或只有注释",
                            severity="info",
                            auto_fixable=self.strategy.auto_delete_empty,
                            fix_suggestion="删除或添加内容",
                        )
                    )
            except Exception:
                continue

    def _check_outdated_configs(self):
        """检测过时的配置文件"""
        patterns = self.strategy.outdated_patterns

        for pattern in patterns:
            for path in self.project_path.rglob("*"):
                if re.search(pattern, path.name):
                    self.issues.append(
                        CleaningIssue(
                            file_path=str(path),
                            issue_type="outdated_config",
                            content=f"疑似过时配置文件: {path.name}",
                            severity="info",
                            auto_fixable=False,
                            fix_suggestion="确认后删除或归档",
                        )
                    )

    def fix(self, issue: CleaningIssue) -> bool:
        """尝试自动修复单个问题"""
        if not issue.auto_fixable:
            return False

        try:
            if issue.issue_type in ("unused_import", "unused_variable", "unused_code"):
                # 使用 ruff auto-fix
                result = subprocess.run(
                    [
                        "python3",
                        "-m",
                        "ruff",
                        "--fix",
                        issue.file_path,
                    ],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                return result.returncode == 0

            if issue.issue_type == "empty_file" and self.strategy.auto_delete_empty:
                # 删除空文件
                Path(issue.file_path).unlink()
                return True

        except Exception:
            pass

        return False

    def fix_all_auto(self) -> CleanerReport:
        """自动修复所有可修复的问题"""
        report = CleanerReport(
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            project_path=str(self.project_path),
        )

        # 先扫描
        self.scan()

        fixed_files = set()

        for issue in self.issues:
            if issue.auto_fixable and self.fix(issue):
                fixed_files.add(issue.file_path)
                report.fixed_count += 1

        report.fixed_files = list(fixed_files)
        return report

    def generate_report_md(self, report: CleanerReport) -> str:
        """生成 Markdown 格式的清理报告"""
        lines = [
            "# 代码清理报告",
            "",
            f"**时间**: {report.timestamp}",
            f"**项目**: {report.project_path}",
            f"**扫描文件数**: {report.files_scanned}",
            "",
            "---",
            "",
            "## 统计",
            "",
            f"- **问题总数**: {report.total_issues}",
            f"- **已自动修复**: {report.fixed_count}",
            f"- **待确认**: {report.pending_count}",
            f"- **预计减少行数**: {report.lines_removed}",
            f"- **预计节省 Token**: ~{report.estimated_token_savings}",
            "",
        ]

        if report.by_type:
            lines.extend(["## 问题类型分布", ""])
            for issue_type, count in sorted(report.by_type.items()):
                lines.append(f"- {issue_type}: {count}")
            lines.append("")

        if report.fixed_files:
            lines.extend(["## 已自动修复", ""])
            lines.extend([f"- {f}" for f in report.fixed_files])
            lines.append("")

        if report.pending_issues:
            lines.extend(["## 待确认（需人工审核）", ""])
            for issue in report.pending_issues:
                lines.append(f"### {issue.file_path}")
                lines.append(f"- 类型: {issue.issue_type}")
                lines.append(f"- 内容: {issue.content}")
                lines.append(f"- 建议: {issue.fix_suggestion}")
                lines.append("")

        return "\n".join(lines)


# ------------------------------------------------------------------
# CLI 入口
# ------------------------------------------------------------------


def main():
    """CLI 入口"""
    import argparse

    parser = argparse.ArgumentParser(description="代码清理工具")
    parser.add_argument("path", nargs="?", default=".", help="项目路径")
    parser.add_argument("--strategy", choices=["safe", "aggressive"], default="safe")
    parser.add_argument("--fix", action="store_true", help="自动修复")
    parser.add_argument("--output", "-o", help="报告输出路径")

    args = parser.parse_args()

    # 策略
    strategy = CleanerStrategy()
    if args.strategy == "aggressive":
        strategy.auto_delete_empty = True
        strategy.dead_code_safe_mode = False

    # 清理
    cleaner = CodeCleaner(Path(args.path), strategy)

    report = cleaner.fix_all_auto() if args.fix else cleaner.scan()

    # 输出报告
    report_md = cleaner.generate_report_md(report)
    print(report_md)

    if args.output:
        Path(args.output).write_text(report_md, encoding="utf-8")
        print(f"\n报告已保存到: {args.output}")


if __name__ == "__main__":
    main()
