"""
Skill 自进化系统 - SkillManager

职责：
1. 管理 .omc/skills/ 目录下的 Skill 文件（CRUD）
2. 维护 .omc/skills/index.json 实时索引
3. 提供搜索能力（按 name/description/tags/category）
4. patch 优先于 create（节省 token）
5. 自动沉淀触发器评估

目录结构：
.omc/skills/
├── index.json          # 全量索引
├── debugging/
│   ├── slow-query-fix/
│   │   └── SKILL.md    # YAML frontmatter + Markdown 正文
│   └── ...
├── workflow/
├── corrections/
└── best-practices/

SKILL.md 格式：
---
name: slow-query-fix
description: 优化 SQL 查询性能的步骤
category: debugging
tags: [sql, performance, database]
triggers:
  - 查询慢
  - database timeout
created_at: 2026-04-12
updated_at: 2026-04-12
---

# Slow Query Fix

当发现 SQL 查询响应慢时...
"""

from __future__ import annotations

import json
import re
import shutil
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


class SkillManager:
    """Skill 文件管理器"""

    # 合法 categories
    CATEGORIES = ["debugging", "workflow", "corrections", "best-practices"]

    def __init__(self, skills_dir: Optional[Path] = None):
        """
        Args:
            skills_dir: Skills 根目录，默认为 .omc/skills
        """
        self.skills_dir = skills_dir or Path(".omc/skills")
        self.index_file = self.skills_dir / "index.json"
        self._index: Dict[str, Dict[str, Any]] = {}
        self._init()
        self._load_index()

    # ------------------------------------------------------------------
    # 初始化
    # ------------------------------------------------------------------

    def _init(self) -> None:
        """初始化目录结构"""
        self.skills_dir.mkdir(parents=True, exist_ok=True)
        for cat in self.CATEGORIES:
            (self.skills_dir / cat).mkdir(exist_ok=True)

    def _load_index(self) -> None:
        """加载索引文件"""
        if self.index_file.exists():
            try:
                self._index = json.loads(self.index_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, IOError):
                self._index = {}
        else:
            self._index = {}

    def _save_index(self) -> None:
        """保存索引文件"""
        self.index_file.write_text(
            json.dumps(self._index, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    # ------------------------------------------------------------------
    # 索引重建（用于修复损坏的索引）
    # ------------------------------------------------------------------

    def rebuild_index(self) -> int:
        """扫描所有 SKILL.md 文件，重建 index.json"""
        self._index = {}
        count = 0
        for cat in self.CATEGORIES:
            cat_dir = self.skills_dir / cat
            if not cat_dir.exists():
                continue
            for skill_dir in cat_dir.iterdir():
                if not skill_dir.is_dir():
                    continue
                skill_md = skill_dir / "SKILL.md"
                if not skill_md.exists():
                    continue
                meta = self._parse_frontmatter(skill_md)
                if meta:
                    skill_id = skill_dir.name
                    self._index[skill_id] = {
                        "name": meta.get("name", skill_id),
                        "description": meta.get("description", ""),
                        "category": cat,
                        "tags": meta.get("tags", []),
                        "triggers": meta.get("triggers", []),
                        "created_at": meta.get("created_at", ""),
                        "updated_at": meta.get("updated_at", ""),
                        "path": str(skill_md),
                    }
                    count += 1
        self._save_index()
        return count

    # ------------------------------------------------------------------
    # Frontmatter 解析
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_frontmatter(skill_md: Path) -> Optional[Dict[str, Any]]:
        """从 SKILL.md 解析 YAML frontmatter"""
        try:
            content = skill_md.read_text(encoding="utf-8")
        except (IOError, OSError):
            return None

        match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
        if not match:
            return None

        try:
            return yaml.safe_load(match.group(1)) or {}
        except yaml.YAMLError:
            return None

    @staticmethod
    def _serialize_frontmatter(meta: Dict[str, Any]) -> str:
        """序列化 frontmatter 为 YAML 字符串"""
        # 只保留 frontmatter 字段
        keys = [
            "name",
            "description",
            "category",
            "tags",
            "triggers",
            "created_at",
            "updated_at",
        ]
        fm = {k: meta[k] for k in keys if k in meta}
        return yaml.dump(
            fm, allow_unicode=True, default_flow_style=False, sort_keys=False
        )

    # ------------------------------------------------------------------
    # 核心 CRUD
    # ------------------------------------------------------------------

    def create(
        self,
        name: str,
        body: str,
        category: str = "workflow",
        tags: Optional[List[str]] = None,
        triggers: Optional[List[str]] = None,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        创建新的 Skill

        Args:
            name: Skill 名称（用于目录名，自动 slugify）
            body: Markdown 正文
            category: 分类（debugging/workflow/corrections/best-practices）
            tags: 标签列表
            triggers: 触发关键词列表
            description: 一句话描述（自动从 body 首行提取如果为空）

        Returns:
            创建的 Skill 信息 dict（含 skill_id）
        """
        if category not in self.CATEGORIES:
            raise ValueError(f"无效 category '{category}'，可选: {self.CATEGORIES}")

        # Slugify 目录名
        skill_id = self._slugify(name)
        if not skill_id:
            raise ValueError(f"无法从 name '{name}' 生成有效 slug")

        skill_dir = self.skills_dir / category / skill_id
        skill_dir.mkdir(parents=True, exist_ok=True)

        skill_md = skill_dir / "SKILL.md"

        # 检查是否已存在
        if skill_md.exists():
            raise FileExistsError(
                f"Skill '{skill_id}' 已存在，请用 patch() 而非 create()"
            )

        # 自动提取 description
        if description is None:
            # 取 body 第一行非空行作为描述
            first_line = ""
            for line in body.strip().split("\n"):
                stripped = line.strip()
                if stripped and not stripped.startswith("#"):
                    first_line = stripped
                    break
            description = first_line[:200] if first_line else name

        now = time.strftime("%Y-%m-%d")
        meta = {
            "name": name,
            "description": description,
            "category": category,
            "tags": tags or [],
            "triggers": triggers or [],
            "created_at": now,
            "updated_at": now,
        }

        full_content = (
            f"---\n{self._serialize_frontmatter(meta)}---\n\n{body.strip()}\n"
        )
        skill_md.write_text(full_content, encoding="utf-8")

        self._index[skill_id] = {
            "name": name,
            "description": description,
            "category": category,
            "tags": tags or [],
            "triggers": triggers or [],
            "created_at": now,
            "updated_at": now,
            "path": str(skill_md),
        }
        self._save_index()

        return {"skill_id": skill_id, **meta}

    def patch(
        self,
        skill_id: str,
        body: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        triggers: Optional[List[str]] = None,
        name: Optional[str] = None,
        category: str = "workflow",
    ) -> Dict[str, Any]:
        """
        增量更新 Skill（优先于 create）

        只更新传入的字段，保留原有值。
        如果 Skill 不存在，自动转为 create。

        Args:
            skill_id: Skill ID（目录名）
            body: Markdown 正文（只替换 --- 之后的部分）
            description: 一句话描述
            tags: 标签列表（替换）
            triggers: 触发关键词列表（替换）
            name: Skill 名称

        Returns:
            更新后的 Skill 信息
        """
        # 先查找原文件
        skill_path = self._find_skill_path(skill_id)

        if skill_path is None:
            # 不存在，自动 create（body 必填）
            if body is None:
                raise ValueError(f"Skill '{skill_id}' 不存在，且未提供 body，无法创建")
            return self.create(
                name=name or skill_id,
                body=body,
                category=category,
                tags=tags,
                triggers=triggers,
                description=description,
            )

        # 读取原有 frontmatter
        old_meta = self._parse_frontmatter(skill_path) or {}
        category = old_meta.get("category", "workflow")

        # 合并更新
        now = time.strftime("%Y-%m-%d")
        new_meta = {**old_meta}
        if description is not None:
            new_meta["description"] = description
        if tags is not None:
            new_meta["tags"] = tags
        if triggers is not None:
            new_meta["triggers"] = triggers
        if name is not None:
            new_meta["name"] = name
        new_meta["updated_at"] = now

        # 如果只更新 body 而非 frontmatter，保留原有 meta
        if body is not None:
            # 读取原有 body
            content = skill_path.read_text(encoding="utf-8")
            match = re.match(r"^---\n.*?\n---\n(.*)$", content, re.DOTALL)
            old_body = match.group(1).strip() if match else content.strip()
            new_body = body.strip()

            full_content = (
                f"---\n{self._serialize_frontmatter(new_meta)}---\n\n{new_body}\n"
            )
        else:
            # 只更新 frontmatter
            full_content = skill_path.read_text(encoding="utf-8")
            full_content = re.sub(
                r"^---\n.*?\n---",
                f"---\n{self._serialize_frontmatter(new_meta)}---",
                full_content,
                count=1,
                flags=re.DOTALL,
            )

        skill_path.write_text(full_content, encoding="utf-8")

        # 更新索引
        self._index[skill_id] = {
            "name": new_meta.get("name", skill_id),
            "description": new_meta.get("description", ""),
            "category": category,
            "tags": new_meta.get("tags", []),
            "triggers": new_meta.get("triggers", []),
            "created_at": new_meta.get("created_at", now),
            "updated_at": now,
            "path": str(skill_path),
        }
        self._save_index()

        return {"skill_id": skill_id, **self._index[skill_id]}

    def delete(self, skill_id: str) -> bool:
        """删除 Skill 及其目录"""
        skill_path = self._find_skill_path(skill_id)
        if skill_path is None:
            return False

        # 删除目录
        skill_dir = skill_path.parent
        shutil.rmtree(skill_dir)

        # 从索引移除
        if skill_id in self._index:
            del self._index[skill_id]
            self._save_index()

        return True

    # ------------------------------------------------------------------
    # 查询
    # ------------------------------------------------------------------

    def list_skills(
        self,
        category: Optional[str] = None,
        tag: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        列出 Skills

        Args:
            category: 按分类过滤
            tag: 按标签过滤
            limit: 返回上限

        Returns:
            Skill 信息列表（不含 body）
        """
        results = []
        for sid, info in self._index.items():
            if category and info.get("category") != category:
                continue
            if tag and tag not in (info.get("tags") or []):
                continue
            results.append({**info, "skill_id": sid})

        # 按 updated_at 倒序
        results.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        return results[:limit]

    def get_skill(
        self,
        skill_id: str,
        include_body: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """
        获取单个 Skill

        Args:
            skill_id: Skill ID
            include_body: 是否包含 Markdown 正文

        Returns:
            Skill 信息 dict，含 skill_id；不存在返回 None
        """
        info = self._index.get(skill_id)
        if info is None:
            return None

        result = {"skill_id": skill_id, **info}

        if include_body:
            path = Path(info["path"])
            if path.exists():
                content = path.read_text(encoding="utf-8")
                # 去掉 frontmatter
                match = re.match(r"^---\n.*?\n---\n(.*)$", content, re.DOTALL)
                result["body"] = match.group(1).strip() if match else content.strip()
            else:
                result["body"] = ""

        return result

    def search(
        self,
        query: str,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        全文搜索 Skills

        Args:
            query: 搜索关键词（空格分词，AND 逻辑）
            category: 按分类过滤
            tags: 按标签过滤（任一匹配）
            limit: 返回上限

        Returns:
            匹配的 Skill 信息列表
        """
        query_terms = query.lower().split()
        results = []

        for sid, info in self._index.items():
            if category and info.get("category") != category:
                continue
            if tags and not any(t in (info.get("tags") or []) for t in tags):
                continue

            # 拼接搜索文本
            searchable = " ".join(
                [
                    info.get("name", ""),
                    info.get("description", ""),
                    " ".join(info.get("tags", [])),
                    " ".join(info.get("triggers", [])),
                ]
            ).lower()

            # AND 匹配所有 term
            if all(term in searchable for term in query_terms):
                results.append({**info, "skill_id": sid})

        # 相关度排序：完全匹配 > 名称包含 > 描述包含
        def score(x: Dict[str, Any]) -> int:
            s = 0
            full = f"{x.get('name','')} {x.get('description','')}".lower()
            for term in query_terms:
                if term in x.get("name", "").lower():
                    s += 3
                elif term in full:
                    s += 1
            return s

        results.sort(key=score, reverse=True)
        return results[:limit]

    # ------------------------------------------------------------------
    # 工具方法
    # ------------------------------------------------------------------

    @staticmethod
    def _slugify(text: str) -> str:
        """将任意文本转为合法的目录名"""
        # 小写化
        s = text.lower()
        # 替换空格/特殊字符
        s = re.sub(r"[^\w\s-]", "", s)
        s = re.sub(r"[_\s]+", "-", s)
        s = re.sub(r"-+", "-", s)
        s = s.strip("-")
        # 限制长度
        if len(s) > 48:
            s = s[:48].rstrip("-")
        return s

    def _find_skill_path(self, skill_id: str) -> Optional[Path]:
        """在所有 category 中查找 skill_id 对应的 SKILL.md 路径"""
        for cat in self.CATEGORIES:
            path = self.skills_dir / cat / skill_id / "SKILL.md"
            if path.exists():
                return path
        return None

    def get_skill_inventory(self, max_chars: int = 500) -> str:
        """
        生成所有 Skill 的名字+一句话描述，供注入到系统 Prompt

        Args:
            max_chars: 最大字符数（截断）

        Returns:
            形如 "skill_id: description\n..." 的字符串
        """
        lines = []
        total = 0
        for sid, info in self._index.items():
            line = f"- {sid}: {info.get('description', '')}"
            if total + len(line) + 1 > max_chars:
                break
            lines.append(line)
            total += len(line) + 1

        header = f"[{len(self._index)} Skills Available]\n"
        if lines:
            return (
                header
                + "\n".join(lines)
                + (
                    f"\n... (共 {len(self._index)} 个)"
                    if len(self._index) > len(lines)
                    else ""
                )
            )
        return f"[{len(self._index)} Skills Available] (none)"

    # ------------------------------------------------------------------
    # 自动沉淀评估
    # ------------------------------------------------------------------

    @staticmethod
    def evaluate_skill_worthy(
        tool_call_count: int,
        had_error: bool,
        had_fix: bool,
        had_user_correction: bool,
        is_nontrivial_workflow: bool,
    ) -> bool:
        """
        判断当前执行是否值得沉淀为 Skill

        触发条件（满足任一）：
        1. 工具调用 ≥5 次且成功
        2. 错误 → 解决
        3. 用户纠正
        4. 非平凡工作流（多步骤）

        Args:
            tool_call_count: 工具调用次数
            had_error: 是否出过错
            had_fix: 是否从错误中恢复
            had_user_correction: 用户是否纠正过
            is_nontrivial_workflow: 是否为多步骤工作流

        Returns:
            True = 值得沉淀
        """
        if tool_call_count >= 5:
            return True
        if had_error and had_fix:
            return True
        if had_user_correction:
            return True
        if is_nontrivial_workflow:
            return True
        return False

    @staticmethod
    def build_skill_from_execution(
        agent_name: str,
        task_description: str,
        workflow_name: str,
        final_result: str,
        key_steps: Optional[List[str]] = None,
        error_context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        从一次执行构建 Skill 草稿

        用于自动沉淀时生成 SKILL.md 内容。

        Args:
            agent_name: 使用的 Agent 名
            task_description: 任务描述
            workflow_name: 工作流名
            final_result: 最终结果摘要
            key_steps: 关键步骤列表
            error_context: 错误上下文（如果有）

        Returns:
            可直接传给 create() 的 dict（含 name, body, category, tags, triggers）
        """
        # 提取关键词作为 triggers
        triggers = []
        for word in task_description.split():
            if len(word) >= 3 and word.lower() not in {
                "the",
                "and",
                "for",
                "with",
                "from",
            }:
                triggers.append(word.strip(".,!?;:"))

        # 判断 category
        if error_context or "error" in task_description.lower():
            category = "debugging"
        elif workflow_name in {"build", "refactor", "test"}:
            category = "workflow"
        elif had_user_correction := bool(error_context):
            category = "corrections"
        else:
            category = "workflow"

        # 生成 name
        name = f"{workflow_name}-{agent_name}"[:48]

        # 构建 body
        body_lines = [
            f"# {workflow_name.title()} with {agent_name.title()}",
            "",
            f"**任务**: {task_description}",
            f"**工作流**: {workflow_name}",
            f"**Agent**: {agent_name}",
            "",
            "## 关键步骤",
        ]

        if key_steps:
            for i, step in enumerate(key_steps, 1):
                body_lines.append(f"{i}. {step}")
        else:
            body_lines.append(f"1. 识别任务类型: {workflow_name}")
            body_lines.append("2. 规划执行步骤")
            body_lines.append("3. 按计划执行")
            body_lines.append("4. 验证结果")

        body_lines.extend(
            [
                "",
                "## 执行结果",
                final_result[:300],
            ]
        )

        if error_context:
            body_lines.extend(
                [
                    "",
                    "## 错误处理",
                    error_context[:200],
                ]
            )

        body_lines.extend(
            [
                "",
                "## 适用条件",
                f"- 任务类型: {workflow_name}",
                f"- 触发词: {', '.join(triggers[:5])}",
            ]
        )

        return {
            "name": name,
            "body": "\n".join(body_lines),
            "category": category,
            "tags": [workflow_name, agent_name] + triggers[:3],
            "triggers": triggers[:5],
            "description": task_description[:120].strip(),
        }
