from __future__ import annotations

"""
SPEC 生成器

根据用户需求描述，使用 AI 模型生成详细的 SPEC.md 规格文档。
"""

import re
from pathlib import Path

from ..core.router import TaskType
from ..models.base import Message
from .models import AcceptanceCriteria, Quest, QuestSpec, SpecSection

SYSTEM_PROMPT = """你是一个资深的技术架构师，擅长将需求转化为详细的规格文档。

## 你的任务
根据用户的需求描述，生成一份完整、清晰、可执行的 SPEC.md 规格文档。

## 输出要求

### 必须包含的章节
1. **概述** - 一句话描述这个任务是什么
2. **动机** - 为什么要做这个？解决了什么问题？
3. **包含范围** - 具体要实现哪些功能（用列表）
4. **不包含范围** - 明确排除哪些（用列表）
5. **验收标准** - 至少 5 条可测试的验收标准（每条格式: [ ] **[AC1]** 具体描述）
6. **风险提示** - 可能遇到的问题和解决方案
7. **技术方案** - 简要的技术实现思路
8. **文件规划** - 需要新建或修改的文件列表

### 风格要求
- 简洁、明确、可执行
- 验收标准必须可测试（能写测试用例来验证）
- 不要过度设计，保持 MVP 原则
- 用中文输出

### 验收标准格式
```
- [ ] **[AC1]** 标准描述（可测试的）
- [ ] **[AC2]** 标准描述
```

### 示例
```
## 包含范围
- 用户注册和登录
- JWT 认证
- 密码重置

## 验收标准
- [ ] **[AC1]** 用户可以使用邮箱注册新账号
- [ ] **[AC2]** 用户可以使用密码登录系统
- [ ] **[AC3]** 登录后获得有效期为 7 天的 JWT token
```

## 重要原则
1. 验收标准 = 测试用例描述（能直接转化为测试代码）
2. 范围明确 = 减少后期扯皮
3. MVP = 先做核心功能，不做锦上添花
"""


class SpecGenerator:
    """SPEC 文档生成器"""

    def __init__(
        self,
        model_router,  # ModelRouter instance
        project_path: Path | None = None,
    ):
        self.model_router = model_router
        self.project_path = project_path or Path(".")

    async def generate(self, quest: Quest) -> "QuestSpec":
        """
        生成 SPEC 文档

        Args:
            quest: Quest 任务对象

        Returns:
            QuestSpec 规格文档对象
        """
        # 构建 prompt
        context_info = await self._gather_context(quest)

        prompt = f"""## 用户需求
{quest.description}

{context_info}

请根据以上需求，生成完整的 SPEC.md 规格文档。
"""

        messages = [
            Message(role="system", content=SYSTEM_PROMPT),
            Message(role="user", content=prompt),
        ]

        response = await self.model_router.route_and_call(
            task_type=TaskType.PLANNING,
            messages=messages,
            complexity="high",
        )

        return self._parse_spec(response.content, quest.title)

    async def _gather_context(self, quest: Quest) -> str:
        """收集项目上下文信息"""
        parts = []

        # 项目信息
        project_path = Path(quest.project_path)
        parts.append(f"### 项目路径\n{project_path}")

        # pyproject.toml
        pyproject = project_path / "pyproject.toml"
        if pyproject.exists():
            try:
                content = pyproject.read_text()[:500]
                parts.append(f"### pyproject.toml\n```\n{content}\n```")
            except Exception:
                pass

        # 目录结构（最多 3 层）
        try:
            tree_lines = []
            for p in sorted(project_path.iterdir())[:15]:
                if p.is_dir() and not p.name.startswith("."):
                    tree_lines.append(f"  📁 {p.name}/")
                    for pp in sorted(p.iterdir())[:5]:
                        if not pp.name.startswith("."):
                            tree_lines.append(f"    └─ {pp.name}")
                elif p.is_file() and not p.name.startswith("."):
                    tree_lines.append(f"  📄 {p.name}")
            if tree_lines:
                parts.append("### 项目结构\n```\n" + "\n".join(tree_lines) + "\n```")
        except Exception:
            pass

        # README
        readme = project_path / "README.md"
        if readme.exists():
            try:
                content = readme.read_text()[:800]
                parts.append(f"### README.md\n{content}")
            except Exception:
                pass

        return "\n\n".join(parts) if parts else ""

    def _parse_spec(self, content: str, fallback_title: str) -> QuestSpec:
        """解析模型输出，构建 QuestSpec 对象"""
        lines = content.split("\n")

        # 提取标题
        title = fallback_title
        for line in lines:
            if line.startswith("# "):
                title = line[2:].strip()
                break

        # 提取章节
        sections: list[SpecSection] = []
        current_title = "概述"
        current_content: list[str] = []
        in_acceptance = False
        acceptance_criteria: list[AcceptanceCriteria] = []
        scope: list[str] = []
        out_of_scope: list[str] = []
        motivation = ""
        overview = ""
        risks: list[str] = []
        estimated_time = "1h"

        for line in lines:
            stripped = line.strip()

            # 检测章节标题
            if stripped.startswith("##"):
                # 保存上一个章节
                if current_content:
                    content_text = "\n".join(current_content).strip()
                    if content_text:
                        sections.append(
                            SpecSection(
                                title=current_title,
                                content=content_text,
                                order=len(sections),
                            )
                        )
                    current_content = []

                title = stripped[2:].strip()
                current_title = title

                if "概述" in title:
                    in_acceptance = False
                elif "验收标准" in title:
                    in_acceptance = True
                elif "动机" in title or "包含范围" in title or "风险" in title:
                    in_acceptance = False
                continue

            # 收集内容
            if in_acceptance:
                # 解析验收标准
                match = re.search(r"\[AC?\d+\]", stripped, re.IGNORECASE)
                if match or stripped.startswith(("- [ ]", "-[**")):
                    # 提取标准描述
                    desc = re.sub(r"^\[[ x]\]\s*", "", stripped).strip()
                    desc = re.sub(r"\[\*\*[AC?\d+\]\*\*]\s*", "", desc).strip()
                    if desc:
                        ac_id = f"AC{len(acceptance_criteria) + 1}"
                        acceptance_criteria.append(
                            AcceptanceCriteria(id=ac_id, description=desc)
                        )
            else:
                if current_title == "概述" and overview == "":
                    overview = stripped
                elif current_title == "动机" and motivation == "":
                    motivation = stripped
                elif current_title == "包含范围" and stripped.startswith("-"):
                    scope.append(stripped.lstrip("- ").lstrip("• "))
                elif current_title == "不包含范围" and stripped.startswith("-"):
                    out_of_scope.append(stripped.lstrip("- ").lstrip("• "))
                elif current_title == "风险提示" and stripped.startswith("-"):
                    risks.append(stripped.lstrip("- ⚠️").lstrip("- ").lstrip("• "))
                elif current_title == "预估耗时" or "耗时" in current_title:
                    if stripped and not stripped.startswith("#"):
                        estimated_time = (
                            stripped.split()[0] if stripped.split() else "1h"
                        )
                else:
                    if stripped:
                        current_content.append(stripped)

        # 保存最后一个章节
        if current_content:
            content_text = "\n".join(current_content).strip()
            if content_text:
                sections.append(
                    SpecSection(
                        title=current_title,
                        content=content_text,
                        order=len(sections),
                    )
                )

        # 清理 sections，去除已解析的章节
        excluded_titles = {
            "概述",
            "动机",
            "包含范围",
            "不包含范围",
            "验收标准",
            "风险提示",
        }
        sections = [s for s in sections if s.title not in excluded_titles]

        # 如果没有 acceptance_criteria，生成默认值
        if not acceptance_criteria:
            acceptance_criteria = [
                AcceptanceCriteria(
                    id="AC1",
                    description=f"完成 {title} 功能的实现",
                ),
                AcceptanceCriteria(
                    id="AC2",
                    description="所有新增代码通过代码审查",
                ),
            ]

        return QuestSpec(
            title=title or fallback_title,
            overview=overview or title or fallback_title,
            motivation=motivation or "提升项目质量和开发效率",
            scope=scope,
            out_of_scope=out_of_scope,
            acceptance_criteria=acceptance_criteria,
            risks=risks,
            estimated_time=estimated_time,
            sections=sections,
        )
