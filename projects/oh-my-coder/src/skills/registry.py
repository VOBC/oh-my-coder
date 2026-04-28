"""
Skill 注册中心 - 统一管理和执行 Skill

设计：
- Skill 是接收 (code, context) 返回 SkillResult 的 Python 函数
- 内置 Skill：/review、/test、/doc
- 用户自定义 Skill：~/.omc/skills/*.py，自动加载
- 支持 CLI 调用：omc skill list / omc skill run <name>
"""

from __future__ import annotations

import importlib.util
import logging
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.table import Table

logger = logging.getLogger(__name__)
console = Console()


# ─── 数据结构 ────────────────────────────────────────────────────────────────


@dataclass
class Skill:
    """Skill 定义"""

    name: str
    description: str
    func: Callable[[str, dict[str, Any]], SkillResult]
    source: str = "builtin"  # builtin | custom
    file_path: Path | None = None

    def __post_init__(self) -> None:
        # 自动从函数 docstring 填充 description
        if not self.description and self.func.__doc__:
            first_line = self.func.__doc__.strip().split("\n")[0]
            self.description = first_line.strip()


@dataclass
class SkillResult:
    """Skill 执行结果"""

    success: bool
    output: str = ""
    error: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0

    def as_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "metadata": self.metadata,
            "duration_ms": self.duration_ms,
        }


# ─── 内置 Skill 实现 ─────────────────────────────────────────────────────────


def _review_skill(code: str, context: dict[str, Any]) -> SkillResult:
    """代码审查 Skill"""
    import time

    start = time.perf_counter()
    lines = code.splitlines()
    issues: list[str] = []
    suggestions: list[str] = []

    # 基础代码质量检查
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        # TODO 注释检查
        if len(stripped) > 120 and not stripped.startswith("#"):
            issues.append(f"L{i}: 行过长 ({len(stripped)} chars)")

        if stripped.endswith(",") and i < len(lines):
            next_line = lines[i].strip()
            if not next_line:
                issues.append(f"L{i}: 可能缺少换行")

        # 检测明显的安全问题
        if "eval(" in stripped:
            issues.append(f"L{i}: 使用 eval() 可能导致代码注入")
        if "shell=True" in stripped and "subprocess" in stripped:
            issues.append(f"L{i}: subprocess shell=True 可能导致命令注入")

    # 检测重复代码块（简化版）
    line_hashes: dict[str, list[int]] = {}
    for i, line in enumerate(lines, 1):
        h = hash(line.strip())
        if h in line_hashes:
            line_hashes[h].append(i)
        else:
            line_hashes[h] = [i]

    duplicates = {h: idx for h, idx in line_hashes.items() if len(idx) >= 3}
    suggestions.extend(
        [
            f"连续相似行 L{idx_list[0]}-{idx_list[-1]}: 考虑提取为函数"
            for idx_list in duplicates.values()
        ]
    )

    suggestions.append(f"代码总行数: {len(lines)}")
    suggestions.append(f"审查时间: {(time.perf_counter() - start) * 1000:.1f}ms")

    return SkillResult(
        success=True,
        output=f"发现 {len(issues)} 个问题，{len(suggestions)} 条建议",
        metadata={"issues": issues, "suggestions": suggestions},
        duration_ms=(time.perf_counter() - start) * 1000,
    )


def _test_skill(code: str, context: dict[str, Any]) -> SkillResult:
    """测试生成 Skill"""
    import time

    start = time.perf_counter()
    test_cases: list[str] = []
    lines = code.splitlines()
    functions: list[str] = []

    # 检测函数定义
    for _i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith(("def test_", "async def test_")):
            functions.append(stripped)
        elif (stripped.startswith(("def ", "async def "))) and not stripped.startswith(
            "def __"
        ):
            # 提取函数名
            import re

            m = re.match(r"(?:async\s+)?def\s+(\w+)", stripped)
            if m:
                fname = m.group(1)
                functions.append(stripped)
                test_cases.append(
                    f"def test_{fname}():\n"
                    f'    """Test {fname}"""'
                    f"\n    # TODO: 实现测试逻辑\n    pass\n"
                )

    # 生成测试框架
    test_content = (
        '"`python"\n'
        + "# 自动生成的测试文件\n"
        + "# 运行: python -m pytest tests/\n\n"
        + "import pytest\n"
        + "from pathlib import Path\n\n"
    )

    for tc in test_cases:
        test_content += tc + "\n"

    duration_ms = (time.perf_counter() - start) * 1000
    return SkillResult(
        success=True,
        output=test_content,
        metadata={
            "functions_found": len(functions),
            "test_cases_generated": len(test_cases),
        },
        duration_ms=duration_ms,
    )


def _doc_skill(code: str, context: dict[str, Any]) -> SkillResult:
    """文档生成 Skill"""
    import time

    start = time.perf_counter()
    lines = code.splitlines()
    doc_parts: list[str] = []
    in_docstring = False
    current_doc: list[str] = []
    module_name = context.get("module_name", "module")
    file_path = context.get("file_path", "")

    doc_parts.append(f"# {Path(file_path).stem if file_path else module_name}\n")
    doc_parts.append("> 自动生成的模块文档\n")

    # 收集 docstring
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith(('"""', "'''")):
            if not in_docstring:
                in_docstring = True
                current_doc = []
            else:
                in_docstring = False
                if current_doc:
                    doc_parts.append("\n## 模块说明\n")
                    doc_parts.append("\n".join(current_doc) + "\n")
                    current_doc = []

        elif in_docstring and stripped:
            current_doc.append(f"{i}: {stripped}")

    # 收集函数签名
    funcs: list[str] = []
    for _i, line in enumerate(lines, 1):
        stripped = line.strip()
        if (stripped.startswith(("def ", "async def "))) and not stripped.startswith(
            "def _"
        ):
            import re

            m = re.match(r"(async\s+)?def\s+(\w+)\((.*?)\)", stripped)
            if m:
                fname = m.group(2)
                params = m.group(3)
                funcs.append(f"- `{fname}({params})`")

    if funcs:
        doc_parts.append("\n## 公开 API\n\n")
        doc_parts.append("\n".join(funcs) + "\n")

    doc_parts.append(
        f"\n<!-- 自动生成于 {datetime.now().strftime('%Y-%m-%d %H:%M')} -->\n"
    )

    duration_ms = (time.perf_counter() - start) * 1000
    return SkillResult(
        success=True,
        output="".join(doc_parts),
        metadata={"functions_documented": len(funcs)},
        duration_ms=duration_ms,
    )


# ─── SkillRegistry ────────────────────────────────────────────────────────────


class SkillRegistry:
    """Skill 注册和管理中心"""

    def __init__(self) -> None:
        self._skills: dict[str, Skill] = {}
        self._custom_skills_dir: Path | None = None
        self._loaded_custom: bool = False
        self._init_builtins()

    def _init_builtins(self) -> None:
        """注册内置 Skill"""
        builtins = [
            Skill(
                name="review",
                description="代码审查 - 检查代码质量和安全问题",
                func=_review_skill,
            ),
            Skill(
                name="test",
                description="生成测试 - 为代码生成 pytest 测试用例",
                func=_test_skill,
            ),
            Skill(
                name="doc",
                description="生成文档 - 为模块生成 Markdown 文档",
                func=_doc_skill,
            ),
        ]
        for skill in builtins:
            self.register(skill)

    # ─── 注册/查询 ───────────────────────────────────────────────────────────

    def register(self, skill: Skill) -> None:
        """注册一个 Skill"""
        self._skills[skill.name] = skill
        logger.debug("Registered skill: %s (source=%s)", skill.name, skill.source)

    def unregister(self, name: str) -> bool:
        """注销一个 Skill"""
        if name in self._skills:
            del self._skills[name]
            return True
        return False

    def get(self, name: str) -> Skill | None:
        """获取 Skill"""
        return self._skills.get(name)

    def list_all(self) -> list[Skill]:
        """列出所有 Skill（内置优先）"""
        return list(self._skills.values())

    def list_builtin(self) -> list[Skill]:
        return [s for s in self._skills.values() if s.source == "builtin"]

    def list_custom(self) -> list[Skill]:
        return [s for s in self._skills.values() if s.source == "custom"]

    # ─── 加载自定义 Skill ────────────────────────────────────────────────────

    def set_custom_dir(self, path: Path) -> None:
        """设置自定义 Skill 目录"""
        self._custom_skills_dir = path
        self._loaded_custom = False  # 重置，下次执行时重新加载

    def load_custom_skills(self) -> int:
        """从自定义目录加载 Skill"""
        if self._custom_skills_dir is None:
            # 默认 ~/.omc/skills/
            self._custom_skills_dir = Path.home() / ".omc" / "skills"

        skill_dir = self._custom_skills_dir
        if not skill_dir.is_dir():
            logger.debug("Custom skills dir does not exist: %s", skill_dir)
            return 0

        count = 0
        for py_file in skill_dir.glob("*.py"):
            # 跳过 __init__.py
            if py_file.name.startswith("__"):
                continue
            try:
                self._load_skill_from_file(py_file)
                count += 1
            except Exception as exc:
                logger.warning("Failed to load custom skill %s: %s", py_file.name, exc)

        self._loaded_custom = True
        logger.info("Loaded %d custom skills from %s", count, skill_dir)
        return count

    def _load_skill_from_file(self, file_path: Path) -> None:
        """从 Python 文件加载单个 Skill"""
        module_name = f"omc_custom_skill_{file_path.stem}"
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load spec from {file_path}")

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

        # 查找 skill_xxx 函数或 SKILL 常量
        if hasattr(module, "SKILL") and isinstance(module.SKILL, Skill):
            skill = module.SKILL
            skill.source = "custom"
            skill.file_path = file_path
            self.register(skill)
        else:
            # 收集所有 skill_ 开头的函数
            for attr_name in dir(module):
                if attr_name.startswith("skill_"):
                    func = getattr(module, attr_name)
                    if callable(func):
                        skill_name = attr_name[6:]  # 去掉 skill_ 前缀
                        skill = Skill(
                            name=skill_name,
                            description=func.__doc__ or attr_name,
                            func=func,
                            source="custom",
                            file_path=file_path,
                        )
                        self.register(skill)

    # ─── 执行 ────────────────────────────────────────────────────────────────

    def run(
        self, name: str, code: str = "", context: dict[str, Any] | None = None
    ) -> SkillResult:
        """执行指定 Skill"""
        # 确保自定义 Skill 已加载
        if not self._loaded_custom:
            self.load_custom_skills()

        skill = self._skills.get(name)
        if skill is None:
            return SkillResult(
                success=False,
                error=f"Skill '{name}' not found. Run 'omc skill list' to see available skills.",
            )

        ctx = context or {}
        try:
            return skill.func(code, ctx)
        except Exception as exc:
            logger.exception("Skill %s failed: %s", name, exc)
            return SkillResult(
                success=False,
                error=f"{type(exc).__name__}: {exc}",
            )

    def run_interactive(
        self, skill_name: str, code: str = "", context: dict[str, Any] | None = None
    ) -> SkillResult:
        """交互模式执行 Skill（支持 /name 语法）"""
        # 去掉开头的 /
        name = skill_name.lstrip("/")
        return self.run(name, code, context)

    # ─── 显示 ────────────────────────────────────────────────────────────────

    def display_list(self) -> None:
        """以表格形式显示所有 Skill"""
        table = Table(title="Available Skills")
        table.add_column("Name", style="cyan bold")
        table.add_column("Source", style="dim")
        table.add_column("Description", style="white")

        for skill in self.list_all():
            table.add_row(
                f"/{skill.name}",
                skill.source,
                skill.description or "",
            )

        console.print(table)


# ─── 全局单例 ────────────────────────────────────────────────────────────────
_default_registry: SkillRegistry | None = None


def get_registry() -> SkillRegistry:
    """获取全局 Skill 注册表（延迟初始化）"""
    global _default_registry
    if _default_registry is None:
        _default_registry = SkillRegistry()
        # 尝试加载用户自定义 Skill
        _default_registry.load_custom_skills()
    return _default_registry
