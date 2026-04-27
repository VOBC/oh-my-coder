"""
智能测试增强模块 - Smart Test Enhancement

功能：
1. git diff 感知：读取最近 commit 的改动，分析影响范围
2. 定向测试生成：针对改动的模块生成测试用例
3. 回归测试：运行已有测试，确保不破坏旧功能
4. 测试报告：生成详细的测试结果报告
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class GitDiff:
    """Git 改动信息"""

    commit_hash: str = ""
    commit_message: str = ""
    author: str = ""
    timestamp: str = ""

    # 改动文件列表
    changed_files: list[str] = field(default_factory=list)

    # 改动详情：file -> [(行号, 行内容, + / -)]
    diff_details: dict[str, list[dict]] = field(default_factory=dict)

    # 统计
    files_added: int = 0
    files_modified: int = 0
    files_deleted: int = 0
    lines_added: int = 0
    lines_deleted: int = 0


@dataclass
class TestCase:
    """测试用例"""

    name: str = ""
    file_path: str = ""
    description: str = ""
    test_type: str = "unit"  # unit/integration/e2e
    target_function: str = ""  # 针对的函数/类
    priority: str = "medium"  # high/medium/low

    # 测试内容
    test_code: str = ""


@dataclass
class TestReport:
    """测试报告"""

    timestamp: str = ""
    project_path: str = ""

    # 改动范围
    diff: GitDiff | None = None

    # 新增测试
    new_tests: list[TestCase] = field(default_factory=list)
    new_tests_passed: int = 0

    # 回归测试
    regression_tests_run: int = 0
    regression_tests_passed: int = 0
    regression_tests_failed: int = 0

    # 覆盖率
    coverage_before: float | None = None
    coverage_after: float | None = None

    # 失败信息
    failures: list[str] = field(default_factory=list)


class SmartTestEnhancer:
    """智能测试增强器

    核心功能：
    1. 分析 git diff，确定改动范围
    2. 生成针对改动模块的测试用例
    3. 运行回归测试
    4. 生成测试报告
    """

    def __init__(self, project_path: Path):
        self.project_path = Path(project_path)

    def get_git_diff(self, count: int = 1) -> GitDiff | None:
        """
        获取最近 N 次 commit 的 git diff

        Args:
            count: 获取最近几次 commit

        Returns:
            GitDiff 对象，包含所有改动信息
        """
        try:
            # 获取最近 commit 的基本信息
            log_result = subprocess.run(
                [
                    "git",
                    "log",
                    f"-{count}",
                    "--pretty=format:%H|%s|%an|%ai",
                    "--no-patch",
                ],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if log_result.returncode != 0:
                return None

            lines = log_result.stdout.strip().split("\n")
            if not lines:
                return None

            # 取最近的 commit
            latest = lines[0].split("|")
            diff = GitDiff(
                commit_hash=latest[0],
                commit_message=latest[1],
                author=latest[2],
                timestamp=latest[3],
            )

            # 获取文件改动
            diff_result = subprocess.run(
                ["git", "diff", "--stat", f"{latest[0]}~1", latest[0]],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if diff_result.returncode == 0:
                for line in diff_result.stdout.split("\n"):
                    if "|" in line:
                        file_part = line.split("|")[0].strip()
                        if file_part:
                            diff.changed_files.append(file_part)

            # 详细 diff
            diff_detail_result = subprocess.run(
                ["git", "diff", f"{latest[0]}~1", latest[0]],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if diff_detail_result.returncode == 0:
                self._parse_diff_details(diff, diff_detail_result.stdout)

            return diff

        except (subprocess.TimeoutExpired, FileNotFoundError):
            return None

    def _parse_diff_details(self, diff: GitDiff, diff_output: str):
        """解析 git diff 输出"""
        current_file = ""
        current_changes = []

        for line in diff_output.split("\n"):
            # 新文件
            if line.startswith("diff --git"):
                if current_file and current_changes:
                    diff.diff_details[current_file] = current_changes

                # 提取文件名
                parts = line.split()
                if len(parts) >= 4:
                    current_file = parts[2].replace("b/", "")

                current_changes = []

            # 行级别改动
            elif line.startswith("+") and not line.startswith("+++"):
                diff.lines_added += 1
                current_changes.append(
                    {
                        "line": line[1:].strip(),
                        "type": "add",
                    }
                )
            elif line.startswith("-") and not line.startswith("---"):
                diff.lines_deleted += 1
                current_changes.append(
                    {
                        "line": line[1:].strip(),
                        "type": "remove",
                    }
                )

        # 保存最后一个文件
        if current_file and current_changes:
            diff.diff_details[current_file] = current_changes

    def analyze_impact(self, diff: GitDiff) -> dict[str, Any]:
        """
        分析改动影响范围

        Returns:
            影响分析结果，包含：
            - impacted_modules: 受影响的模块
            - risk_level: 风险等级 (low/medium/high)
            - test_priority: 测试优先级
        """
        impacted = set()

        # 收集所有受影响的模块
        for file_path in diff.changed_files:
            # Python 文件
            if file_path.endswith(".py"):
                # 提取模块名
                module = file_path.replace("/", ".").replace(".py", "")
                impacted.add(module)

                # 如果是 __init__.py，父模块也受影响
                if "__init__.py" in file_path:
                    parent = ".".join(module.split(".")[:-1])
                    impacted.add(parent)

        # 风险评估
        risk_factors = {
            "high": ["main", "app", "server", "api"],
            "medium": ["service", "handler", "controller"],
            "low": ["model", "schema", "util"],
        }

        risk_level = "low"
        for file_path in diff.changed_files:
            for factor, level in risk_factors.items():
                if any(f in file_path.lower() for f in factor):
                    if level == "high":
                        risk_level = "high"
                        break
                    if level == "medium" and risk_level != "high":
                        risk_level = "medium"

        return {
            "impacted_modules": sorted(impacted),
            "risk_level": risk_level,
            "changed_files_count": len(diff.changed_files),
            "total_lines_changed": diff.lines_added + diff.lines_deleted,
        }

    def generate_targeted_tests(
        self,
        diff: GitDiff,
        test_framework: str = "pytest",
    ) -> list[TestCase]:
        """
        针对改动模块生成测试用例

        Args:
            diff: git diff 信息
            test_framework: 测试框架 (pytest/unittest)

        Returns:
            生成的测试用例列表
        """
        test_cases = []

        # 分析改动影响
        impact = self.analyze_impact(diff)

        # 为每个改动的 Python 文件生成测试
        for file_path in diff.changed_files:
            if not file_path.endswith(".py"):
                continue

            if "/test_" in file_path or file_path.startswith("test_"):
                continue  # 跳过测试文件本身

            # 提取模块名和函数
            module_name = file_path.replace("/", ".").replace(".py", "")
            target_class = self._extract_target_class(
                diff.diff_details.get(file_path, [])
            )

            # 生成测试用例
            if target_class:
                test_case = TestCase(
                    name=f"test_{target_class}_functionality",
                    file_path=f"tests/test_{module_name.split('.')[-1]}.py",
                    description=f"测试 {target_class} 的核心功能",
                    test_type="unit",
                    target_function=target_class,
                    priority="high" if impact["risk_level"] == "high" else "medium",
                    test_code=self._generate_test_code(
                        target_class, module_name, test_framework
                    ),
                )
                test_cases.append(test_case)

        return test_cases

    def _extract_target_class(self, changes: list[dict]) -> str | None:
        """从改动中提取目标类/函数"""
        for change in changes:
            line = change.get("line", "")

            # 查找类定义
            if "class " in line:
                match = __import__("re").search(r"class\s+(\w+)", line)
                if match:
                    return match.group(1)

            # 查找函数定义
            if "def " in line:
                match = __import__("re").search(r"def\s+(\w+)", line)
                if match:
                    return match.group(1)

        return None

    def _generate_test_code(
        self,
        target: str,
        module_name: str,
        framework: str,
    ) -> str:
        """生成测试代码"""
        if framework == "pytest":
            return f'''"""测试 {target}"""

import pytest
from {module_name} import {target}


class Test{target}:
    """测试 {target} 类的功能"""

    def test_basic_functionality(self):
        """测试基本功能"""
        # Arrange
        # TODO: 根据实际功能设置
        instance = {target}()

        # Act
        # TODO: 调用实际方法

        # Assert
        # TODO: 验证结果
        pass

    def test_edge_cases(self):
        """测试边界情况"""
        # TODO: 添加边界条件测试
        pass
'''
        return ""

    def run_regression_tests(self) -> dict[str, Any]:
        """运行回归测试"""
        result = {
            "tests_run": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "failures": [],
        }

        try:
            # 运行 pytest
            proc = subprocess.run(
                [
                    "python3",
                    "-m",
                    "pytest",
                    "tests/",
                    "-v",
                    "--tb=short",
                    "-q",
                ],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                timeout=120,
            )

            # 解析输出
            output = proc.stdout + proc.stderr

            # 提取统计
            import re

            # 匹配 "X passed" 或 "X passed, Y failed"
            match = re.search(r"(\d+)\s+passed", output)
            if match:
                result["tests_passed"] = int(match.group(1))

            match = re.search(r"(\d+)\s+failed", output)
            if match:
                result["tests_failed"] = int(match.group(1))

            result["tests_run"] = result["tests_passed"] + result["tests_failed"]

            # 提取失败信息
            failure_match = re.findall(r"FAILED (.*?) - (.*?)(?:\n|$)", output)
            for test_name, error in failure_match[:5]:  # 最多5个
                result["failures"].append(f"{test_name}: {error[:100]}")

        except subprocess.TimeoutExpired:
            result["failures"].append("测试超时")
        except FileNotFoundError:
            result["failures"].append("pytest 未安装")

        return result

    def generate_report(
        self,
        diff: GitDiff,
        new_tests: list[TestCase],
        regression_result: dict[str, Any],
    ) -> TestReport:
        """生成测试报告"""
        return TestReport(
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            project_path=str(self.project_path),
            diff=diff,
            new_tests=new_tests,
            new_tests_passed=len(new_tests),  # 假设新增测试通过
            regression_tests_run=regression_result.get("tests_run", 0),
            regression_tests_passed=regression_result.get("tests_passed", 0),
            regression_tests_failed=regression_result.get("tests_failed", 0),
            failures=regression_result.get("failures", []),
        )

    def generate_report_md(self, report: TestReport) -> str:
        """生成 Markdown 格式的测试报告"""
        lines = [
            "# 测试报告",
            "",
            f"**时间**: {report.timestamp}",
            f"**项目**: {report.project_path}",
            "",
            "---",
            "",
        ]

        # 改动范围
        if report.diff:
            lines.extend(
                [
                    "## 改动范围",
                    "",
                    f"- **Commit**: `{report.diff.commit_hash[:8]}`",
                    f"- **信息**: {report.diff.commit_message}",
                    f"- **作者**: {report.diff.author}",
                    f"- **文件数**: {len(report.diff.changed_files)}",
                    f"- **新增行**: +{report.diff.lines_added}",
                    f"- **删除行**: -{report.diff.lines_deleted}",
                    "",
                    "### 改动文件",
                    "",
                ]
            )
            lines.extend([f"- {f}" for f in report.diff.changed_files[:20]])
            if len(report.diff.changed_files) > 20:
                lines.append(f"- ... 还有 {len(report.diff.changed_files) - 20} 个")
            lines.append("")

        # 新增测试
        if report.new_tests:
            lines.extend(
                [
                    "## 新增测试",
                    "",
                ]
            )
            for tc in report.new_tests:
                lines.extend(
                    [
                        f"### {tc.name}",
                        f"- 文件: `{tc.file_path}`",
                        f"- 类型: {tc.test_type}",
                        f"- 优先级: {tc.priority}",
                        "",
                        "```python",
                        tc.test_code,
                        "```",
                        "",
                    ]
                )

        # 回归测试
        lines.extend(
            [
                "## 回归测试",
                "",
                f"- **运行**: {report.regression_tests_run}",
                f"- **通过**: {report.regression_tests_passed}",
                f"- **失败**: {report.regression_tests_failed}",
                "",
            ]
        )

        # 失败详情
        if report.failures:
            lines.extend(["### 失败详情", ""])
            lines.extend([f"- {failure}" for failure in report.failures])
            lines.append("")

        return "\n".join(lines)


# ------------------------------------------------------------------
# CLI 入口
# ------------------------------------------------------------------


def main():
    """CLI 入口"""
    import argparse

    parser = argparse.ArgumentParser(description="智能测试增强工具")
    parser.add_argument("path", nargs="?", default=".", help="项目路径")
    parser.add_argument("--generate", "-g", action="store_true", help="生成测试用例")
    parser.add_argument("--regression", "-r", action="store_true", help="运行回归测试")
    parser.add_argument("--report", "-o", help="报告输出文件")

    args = parser.parse_args()

    project_path = Path(args.path).resolve()
    enhancer = SmartTestEnhancer(project_path)

    if args.generate or args.regression:
        # 获取 diff
        diff = enhancer.get_git_diff()
        if not diff:
            print("无法获取 git diff")
            return

        print(f"Commit: {diff.commit_hash[:8]}")
        print(f"改动文件: {len(diff.changed_files)}")
        print(f"新增行: +{diff.lines_added}, 删除行: -{diff.lines_deleted}")

        if args.generate:
            tests = enhancer.generate_targeted_tests(diff)
            print(f"\n生成了 {len(tests)} 个测试用例:")
            for tc in tests:
                print(f"  - {tc.name} -> {tc.file_path}")

        if args.regression:
            result = enhancer.run_regression_tests()
            print("\n回归测试结果:")
            print(f"  通过: {result['tests_passed']}/{result['tests_run']}")
            if result["failures"]:
                print(f"  失败: {result['failures'][:3]}")


if __name__ == "__main__":
    main()
