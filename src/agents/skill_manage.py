from __future__ import annotations

"""
Skill 自进化 Agent

提供工具化的 Skill CRUD 操作，供其他 Agent 调用。

工具（注册到模型）：
- create: 创建新 Skill
- patch: 增量更新 Skill（优先）
- delete: 删除 Skill
- list: 列出 Skills（支持 category/tag 过滤）
- view: 查看单个 Skill（含 body）

设计原则：
- patch 优先于 create（节省 token）
- 所有操作持久化到 .omc/skills/
- 通过 SkillManager 管理底层文件
"""

from pathlib import Path
from typing import Any

from ..memory.skill_manager import SkillManager
from .base import (
    AgentContext,
    AgentLane,
    AgentOutput,
    AgentStatus,
    BaseAgent,
    register_agent,
)


@register_agent
class SkillManageAgent(BaseAgent):
    """
    Skill 管理 Agent

    职责：
    1. 提供 Skill CRUD 工具（供模型调用）
    2. 维护 .omc/skills/ 目录和索引
    3. 支持搜索和查询
    """

    name = "skill-manage"
    description = "Skill 自进化管理 — 创建/更新/删除/查询 .omc/skills/ 中的经验沉淀文件"
    lane = AgentLane.COORDINATION
    default_tier = "low"  # 纯管理操作，用最低成本模型
    icon = "🧩"
    tools: list[str] = []  # 不需要外部工具，自身就是工具

    def __init__(self, model_router, config: dict[str, Any] | None = None):
        super().__init__(model_router, config)
        # SkillManager 实例，可共享
        skills_dir = None
        if config:
            skills_dir = config.get("skills_dir")
        if skills_dir:
            skills_dir = Path(skills_dir)
        self.sm = SkillManager(skills_dir=skills_dir)

    @property
    def system_prompt(self) -> str:
        return """你是一个 Skill 自进化管理员。

## 你的职责
维护 .omc/skills/ 下的经验沉淀文件，帮助其他 Agent 复用历史经验。

## 文件结构
.omc/skills/
├── index.json
├── debugging/      # 调试经验（bug fix、troubleshooting）
├── workflow/       # 工作流经验（重构、测试等）
├── corrections/    # 被纠正后的修复（用户纠错沉淀）
└── best-practices/ # 最佳实践

## SKILL.md 格式
```markdown
---
name: 技能名称
description: 一句话描述
category: debugging|workflow|corrections|best-practices
tags: [python, refactor]
triggers: [重构, flask]
created_at: 2026-04-12
updated_at: 2026-04-12
---

# 正文内容
...
```

## 工具

### list — 列出 Skills
过滤：category（调试经验/工作流/纠正/最佳实践）、tag
无参数 = 列出全部

### view — 查看单个 Skill
参数：skill_id（必填）
可选：include_body=true

### create — 创建新 Skill
参数：name, body（正文）, category, description, tags, triggers
⚠️ 先用 patch！只有 Skill 不存在时才 create

### patch — 增量更新（优先）
参数：skill_id（必填）, body, description, tags, triggers
- 只传要改的字段，保留其他
- 如果 Skill 不存在，有 body 时自动创建

### delete — 删除 Skill
参数：skill_id（必填）

### search — 全文搜索
参数：query（关键词，空格分词，AND 逻辑）
可选：category, tags

## 决策规则
- **patch 优先**：修改现有 Skill 总是用 patch，不是 create
- **先查后写**：创建前先 list 确认不存在
- **描述必填**：description 帮助其他 Agent 发现这个 Skill

## 输出格式
每次工具调用后，简洁汇报结果（成功/失败/内容摘要）。
"""

    # ------------------------------------------------------------------
    # 工具实现（直接方法，BaseAgent.execute 会暴露给模型）
    # ------------------------------------------------------------------

    def tool_list(
        self,
        category: str | None = None,
        tag: str | None = None,
        limit: int = 20,
    ) -> str:
        """工具：列出 Skills"""
        skills = self.sm.list_skills(category=category, tag=tag, limit=limit)
        if not skills:
            return "（无结果）"

        lines = []
        for s in skills:
            lines.append(
                f"- **{s['skill_id']}** [{s.get('category', '')}] "
                f"{s.get('description', '')} "
                f"[{' / '.join(s.get('tags', [])[:3])}]"
            )
        return "\n".join(lines) or "（无结果）"

    def tool_view(
        self,
        skill_id: str,
        include_body: bool = False,
    ) -> str:
        """工具：查看单个 Skill"""
        skill = self.sm.get_skill(skill_id, include_body=include_body)
        if skill is None:
            return f"Skill '{skill_id}' 不存在"

        parts = [
            f"## {skill['name']} (`{skill['skill_id']}`)",
            f"**分类**: {skill.get('category', '')}",
            f"**描述**: {skill.get('description', '')}",
            f"**标签**: {', '.join(skill.get('tags', []))}",
            f"**触发词**: {', '.join(skill.get('triggers', []))}",
            f"**创建**: {skill.get('created_at', '')} | **更新**: {skill.get('updated_at', '')}",
        ]
        if include_body and skill.get("body"):
            parts.append("\n---\n\n" + skill["body"])

        return "\n".join(parts)

    def tool_create(
        self,
        name: str,
        body: str,
        category: str = "workflow",
        description: str | None = None,
        tags: list[str] | None = None,
        triggers: list[str] | None = None,
    ) -> str:
        """
        工具：创建新 Skill（自动 patch 优先）

        先检查同名 Skill 是否存在：
        - 已存在 → 自动改为 patch（增量更新）
        - 不存在 → 创建新 Skill
        """
        skill_id = self.sm._slugify(name)

        # 检查是否存在（patch 优先）
        existing = self.sm.get_skill(skill_id)
        if existing:
            # 自动转为 patch
            try:
                result = self.sm.patch(
                    skill_id=skill_id,
                    body=body,
                    description=description,
                    tags=tags,
                    triggers=triggers,
                    name=name,
                    category=category,
                )
                return (
                    f"✅ Skill 已存在，自动转为 patch: `{skill_id}`\n"
                    f"   描述: {result.get('description', '')}"
                )
            except Exception as e:
                return f"❌ Patch 失败: {e}"

        # 不存在，创建新 Skill
        try:
            result = self.sm.create(
                name=name,
                body=body,
                category=category,
                description=description,
                tags=tags,
                triggers=triggers,
            )
            return (
                f"✅ Skill 创建成功: `{result['skill_id']}`\n"
                f"   路径: {self.sm.skills_dir}/{category}/{result['skill_id']}/SKILL.md"
            )
        except Exception as e:
            return f"❌ 创建失败: {e}"

    def tool_patch(
        self,
        skill_id: str,
        body: str | None = None,
        description: str | None = None,
        tags: list[str] | None = None,
        triggers: list[str] | None = None,
        name: str | None = None,
        category: str = "workflow",
    ) -> str:
        """工具：增量更新 Skill（优先于 create）"""
        try:
            existed_before = self.sm.get_skill(skill_id) is not None
            result = self.sm.patch(
                skill_id=skill_id,
                body=body,
                description=description,
                tags=tags,
                triggers=triggers,
                name=name,
                category=category,
            )
            action = "更新" if existed_before else "创建"
            return (
                f"✅ Skill {action}: `{result['skill_id']}`\n"
                f"   描述: {result.get('description', '')}"
            )
        except Exception as e:
            return f"❌ 操作失败: {e}"

    def tool_delete(self, skill_id: str) -> str:
        """工具：删除 Skill"""
        ok = self.sm.delete(skill_id)
        if ok:
            return f"✅ Skill 删除: `{skill_id}`"
        return f"⚠️ Skill 不存在: `{skill_id}`"

    def tool_search(
        self,
        query: str,
        category: str | None = None,
        tags: list[str] | None = None,
        limit: int = 10,
    ) -> str:
        """工具：全文搜索 Skills"""
        results = self.sm.search(
            query=query,
            category=category,
            tags=tags,
            limit=limit,
        )
        if not results:
            return f"（无匹配结果 for: {query}）"

        lines = [f"**{len(results)} 个结果** (for: {query}):\n"]
        for s in results:
            lines.append(
                f"- **{s['skill_id']}** [{s.get('category', '')}] "
                f"{s.get('description', '')}"
            )
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # 生命周期方法
    # ------------------------------------------------------------------

    async def _run(
        self,
        context: AgentContext,
        prompt: list[dict[str, str]],
        **kwargs,
    ) -> str:
        """
        执行 Skill 管理任务

        从 prompt 最后一个用户消息解析工具调用请求，
        执行对应的 tool_* 方法，返回结果。
        """
        # 提取最后一个用户消息
        user_msg = ""
        for msg in reversed(prompt):
            if msg.get("role") == "user":
                user_msg = msg.get("content", "")
                break

        # 解析工具调用
        action = self._parse_action(user_msg)
        params = self._parse_params(user_msg)

        # 执行对应工具
        if action == "list":
            return self.tool_list(**params)
        if action == "view":
            return self.tool_view(**params)
        if action == "create":
            return self.tool_create(**params)
        if action == "patch":
            return self.tool_patch(**params)
        if action == "delete":
            return self.tool_delete(**params)
        if action == "search":
            return self.tool_search(**params)
        # 默认：列出全部 + 搜索建议
        return self.tool_list() + "\n\n💡 提示：用 search <关键词> 搜索已有 Skill"

    def _post_process(self, result: str, context: AgentContext) -> AgentOutput:
        return AgentOutput(
            agent_name=self.name,
            status=AgentStatus.COMPLETED,
            result=result,
            recommendations=[
                "Skill 已更新/创建，其他 Agent 可通过 skill_manage 工具查询",
            ],
        )

    # ------------------------------------------------------------------
    # 辅助：简单意图识别（无需模型，直接规则）
    # ------------------------------------------------------------------

    def _parse_action(self, text: str) -> str:
        """从文本识别操作类型"""
        text_lower = text.lower()
        if "搜索" in text or "search" in text_lower:
            return "search"
        if "列出" in text or "list" in text_lower or "所有技能" in text:
            return "list"
        if "查看" in text or "view" in text_lower or "详情" in text:
            return "view"
        if "更新" in text or "patch" in text_lower or "修改" in text:
            return "patch"
        if "创建" in text or "create" in text_lower or "新建" in text:
            return "create"
        if "删除" in text or "delete" in text_lower:
            return "delete"
        return ""

    def _parse_params(self, text: str) -> dict[str, Any]:
        """从文本解析参数（简易版）"""
        params: dict[str, Any] = {}

        # category
        for cat in SkillManager.CATEGORIES:
            if cat in text:
                params["category"] = cat
                break

        # skill_id
        import re

        id_match = re.search(r"`([^`]+)`", text)
        if id_match:
            params["skill_id"] = id_match.group(1)

        return params
