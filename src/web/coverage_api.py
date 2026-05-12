"""
测试覆盖率 API 模块
提供覆盖率数据收集和报告生成功能
"""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class FileCoverage:
    """单个文件的覆盖率数据"""
    path: str
    statements: int = 0
    missing: int = 0
    branches: int = 0
    partial_branches: int = 0
    coverage: float = 0.0
    missing_lines: list[int] = field(default_factory=list)


@dataclass
class CoverageSummary:
    """覆盖率汇总数据"""
    total_files: int = 0
    total_statements: int = 0
    total_missing: int = 0
    total_branches: int = 0
    total_partial: int = 0
    overall_coverage: float = 0.0
    files: list[FileCoverage] = field(default_factory=list)
    timestamp: str = ""


def run_coverage_analysis(project_root: Path) -> CoverageSummary:
    """运行 pytest-cov 并解析结果"""
    summary = CoverageSummary()

    # 运行 pytest with coverage
    cmd = [
        sys.executable, "-m", "pytest",
        "--cov=src",
        "--cov-report=json",
        "--cov-report=term-missing",
        "-q",
        "tests/",
    ]

    try:
        result = subprocess.run(
            cmd,
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=300,
        )
    except subprocess.TimeoutExpired:
        summary.overall_coverage = -1.0
        return summary
    except Exception as e:
        summary.overall_coverage = -1.0
        return summary

    # 解析 JSON 报告
    json_path = project_root / "coverage.json"
    if not json_path.exists():
        # 尝试从 stdout 解析
        summary.overall_coverage = _parse_coverage_from_output(result.stdout)
        return summary

    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
        summary = _parse_coverage_json(data, project_root)
    except Exception:
        summary.overall_coverage = _parse_coverage_from_output(result.stdout)

    # 清理临时文件
    if json_path.exists():
        json_path.unlink()

    return summary


def _parse_coverage_json(data: dict[str, Any], project_root: Path) -> CoverageSummary:
    """解析 coverage.py 的 JSON 输出"""
    summary = CoverageSummary()
    files_data = data.get("files", {})
    totals = data.get("totals", {})

    summary.total_statements = totals.get("num_statements", 0)
    summary.total_missing = totals.get("missing_lines", 0)
    summary.total_branches = totals.get("num_branches", 0)
    summary.total_partial = totals.get("partial_branches", 0)
    summary.overall_coverage = totals.get("percent_covered", 0.0)
    summary.total_files = len(files_data)

    for file_path, file_data in files_data.items():
        # 只显示 src 目录下的文件
        rel_path = Path(file_path).relative_to(project_root) if file_path.startswith(str(project_root)) else Path(file_path)
        if not str(rel_path).startswith("src/"):
            continue

        fc = FileCoverage(
            path=str(rel_path),
            statements=file_data.get("summary", {}).get("num_statements", 0),
            missing=file_data.get("summary", {}).get("missing_lines", 0),
            branches=file_data.get("summary", {}).get("num_branches", 0),
            partial_branches=file_data.get("summary", {}).get("partial_branches", 0),
            coverage=file_data.get("summary", {}).get("percent_covered", 0.0),
            missing_lines=file_data.get("missing_lines", []),
        )
        summary.files.append(fc)

    # 按覆盖率排序
    summary.files.sort(key=lambda x: x.coverage)
    return summary


def _parse_coverage_from_output(stdout: str) -> float:
    """从 pytest-cov 终端输出解析总体覆盖率"""
    for line in stdout.split("\n"):
        if "TOTAL" in line and "%" in line:
            parts = line.split()
            for part in parts:
                if "%" in part:
                    try:
                        return float(part.replace("%", ""))
                    except ValueError:
                        continue
    return 0.0


def get_coverage_badge_color(coverage: float) -> str:
    """根据覆盖率返回颜色"""
    if coverage >= 80:
        return "#22c55e"  # green
    elif coverage >= 60:
        return "#eab308"  # yellow
    elif coverage >= 40:
        return "#f97316"  # orange
    else:
        return "#ef4444"  # red


def format_coverage_report(summary: CoverageSummary) -> dict[str, Any]:
    """格式化覆盖率报告为 API 响应"""
    return {
        "overall": {
            "coverage": round(summary.overall_coverage, 2),
            "color": get_coverage_badge_color(summary.overall_coverage),
            "total_files": summary.total_files,
            "total_statements": summary.total_statements,
            "total_missing": summary.total_missing,
            "total_branches": summary.total_branches,
        },
        "files": [
            {
                "path": f.path,
                "statements": f.statements,
                "missing": f.missing,
                "branches": f.branches,
                "partial": f.partial_branches,
                "coverage": round(f.coverage, 2),
                "color": get_coverage_badge_color(f.coverage),
                "missing_lines": f.missing_lines[:20],  # 限制数量
            }
            for f in summary.files
        ],
        "timestamp": summary.timestamp,
    }
