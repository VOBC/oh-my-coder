"""
Agent 自进化模块 - Evolution System

让 Agent 像生物基因一样遗传、变异、进化。
存储进化历史、成功模式库、优化的 system prompt、版本迭代决策。

目录结构：
.omc/state/agents/{agent_name}/
├── evolution_history.json  # 进化记录
├── success_patterns.json   # 成功模式库
└── optimized_prompt.md     # 优化后的 prompt

.omc/state/decisions/
└── {yyyy-MM-dd}-{slug}.md  # 每次重要决策记录
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class EvolutionRecord:
    """进化记录"""

    id: str = ""  # 时间戳-based ID
    timestamp: str = ""
    agent_type: str = ""
    generation: int = 1  # 进化代数
    trigger: str = ""  # 触发原因：success_rate_low, user_correction, error_pattern
    before_state: Dict[str, Any] = field(default_factory=dict)  # 进化前状态
    after_state: Dict[str, Any] = field(default_factory=dict)  # 进化后状态
    changes: List[str] = field(default_factory=list)  # 变更列表
    effectiveness: Optional[float] = None  # 效果评分（后续验证）


@dataclass
class SuccessPattern:
    """成功模式"""

    id: str = ""
    pattern_type: str = ""  # strategy, workflow, prompt_technique
    description: str = ""
    context: str = ""  # 适用上下文
    effectiveness_score: float = 0.0
    occurrences: int = 0  # 出现次数
    last_seen: str = ""
    examples: List[str] = field(default_factory=list)  # 成功案例


@dataclass
class EvolutionConfig:
    """自进化配置"""

    enabled: bool = True  # 是否开启自进化
    improvement_threshold: float = 0.8  # 成功率阈值，低于此触发优化
    min_samples: int = 5  # 最小样本数，少于此不触发进化分析
    max_evolution_history: int = 100  # 最大进化历史记录数
    pattern_confidence_threshold: float = 0.7  # 模式置信度阈值
    evolution_cooldown_hours: int = 24  # 进化冷却时间（小时）


class EvolutionStore:
    """进化状态存储"""

    def __init__(self, state_dir: Path):
        """
        Args:
            state_dir: .omc/state 目录
        """
        self.state_dir = Path(state_dir)
        self.agents_dir = self.state_dir / "agents"

    def _agent_dir(self, agent_name: str) -> Path:
        """获取 Agent 进化目录"""
        agent_dir = self.agents_dir / agent_name
        agent_dir.mkdir(parents=True, exist_ok=True)
        return agent_dir

    # ------------------------------------------------------------------
    # 进化历史
    # ------------------------------------------------------------------

    def load_evolution_history(
        self, agent_name: str, limit: int = 50
    ) -> List[EvolutionRecord]:
        """加载进化历史"""
        history_file = self._agent_dir(agent_name) / "evolution_history.json"
        if not history_file.exists():
            return []

        try:
            data = json.loads(history_file.read_text(encoding="utf-8"))
            records = [EvolutionRecord(**r) for r in data.get("records", [])]
            return records[:limit]
        except (json.JSONDecodeError, KeyError):
            return []

    def save_evolution_record(self, record: EvolutionRecord) -> str:
        """保存进化记录"""
        agent_name = record.agent_type
        history_file = self._agent_dir(agent_name) / "evolution_history.json"

        # 读取现有历史
        existing = []
        if history_file.exists():
            try:
                data = json.loads(history_file.read_text(encoding="utf-8"))
                existing = data.get("records", [])
            except (json.JSONDecodeError, KeyError):
                existing = []

        # 添加新记录
        record_dict = {
            "id": record.id or f"evo-{int(time.time())}",
            "timestamp": record.timestamp or time.strftime("%Y-%m-%d %H:%M:%S"),
            "agent_type": record.agent_type,
            "generation": record.generation,
            "trigger": record.trigger,
            "before_state": record.before_state,
            "after_state": record.after_state,
            "changes": record.changes,
            "effectiveness": record.effectiveness,
        }
        existing.append(record_dict)

        # 限制历史长度
        max_records = 100
        if len(existing) > max_records:
            existing = existing[-max_records:]

        # 保存
        history_file.write_text(
            json.dumps({"records": existing}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return record_dict["id"]

    def get_current_generation(self, agent_name: str) -> int:
        """获取当前进化代数"""
        history = self.load_evolution_history(agent_name, limit=1)
        if not history:
            return 1
        return max(1, history[0].generation + 1)

    # ------------------------------------------------------------------
    # 成功模式库
    # ------------------------------------------------------------------

    def load_success_patterns(self, agent_name: str) -> List[SuccessPattern]:
        """加载成功模式库"""
        patterns_file = self._agent_dir(agent_name) / "success_patterns.json"
        if not patterns_file.exists():
            return []

        try:
            data = json.loads(patterns_file.read_text(encoding="utf-8"))
            return [SuccessPattern(**p) for p in data.get("patterns", [])]
        except (json.JSONDecodeError, KeyError):
            return []

    def save_success_pattern(self, pattern: SuccessPattern) -> str:
        """保存成功模式"""
        # 直接调用内部方法保存
        return self._save_pattern_internal(pattern)

    def _save_pattern_internal(self, pattern: SuccessPattern) -> str:
        """内部方法：保存成功模式"""
        # 从 pattern.id 提取 agent_name（假设格式：agentname-patternid）
        agent_name = pattern.id.split("-")[0] if "-" in pattern.id else "default"
        patterns_file = self._agent_dir(agent_name) / "success_patterns.json"

        existing = []
        if patterns_file.exists():
            try:
                data = json.loads(patterns_file.read_text(encoding="utf-8"))
                existing = data.get("patterns", [])
            except (json.JSONDecodeError, KeyError):
                existing = []

        pattern_dict = {
            "id": pattern.id or f"pattern-{int(time.time())}",
            "pattern_type": pattern.pattern_type,
            "description": pattern.description,
            "context": pattern.context,
            "effectiveness_score": pattern.effectiveness_score,
            "occurrences": pattern.occurrences,
            "last_seen": pattern.last_seen or time.strftime("%Y-%m-%d %H:%M:%S"),
            "examples": pattern.examples,
        }

        # 查找是否已存在，存在则更新
        found = False
        for i, p in enumerate(existing):
            if p.get("id") == pattern_dict["id"]:
                existing[i] = pattern_dict
                found = True
                break

        if not found:
            existing.append(pattern_dict)

        patterns_file.write_text(
            json.dumps({"patterns": existing}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return pattern_dict["id"]

    def add_success_pattern(
        self,
        agent_name: str,
        pattern_type: str,
        description: str,
        context: str = "",
        example: str = "",
    ) -> str:
        """添加成功模式"""
        patterns_file = self._agent_dir(agent_name) / "success_patterns.json"

        existing = []
        if patterns_file.exists():
            try:
                data = json.loads(patterns_file.read_text(encoding="utf-8"))
                existing = data.get("patterns", [])
            except (json.JSONDecodeError, KeyError):
                existing = []

        # 检查是否已有类似模式
        pattern_id = f"{agent_name}-{pattern_type}-{int(time.time())}"

        pattern_dict = {
            "id": pattern_id,
            "pattern_type": pattern_type,
            "description": description,
            "context": context,
            "effectiveness_score": 0.7,  # 初始置信度
            "occurrences": 1,
            "last_seen": time.strftime("%Y-%m-%d %H:%M:%S"),
            "examples": [example] if example else [],
        }

        existing.append(pattern_dict)

        patterns_file.write_text(
            json.dumps({"patterns": existing}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return pattern_id

    # ------------------------------------------------------------------
    # 优化 Prompt
    # ------------------------------------------------------------------

    def load_optimized_prompt(self, agent_name: str) -> Optional[str]:
        """加载优化后的 system prompt"""
        prompt_file = self._agent_dir(agent_name) / "optimized_prompt.md"
        if not prompt_file.exists():
            return None
        return prompt_file.read_text(encoding="utf-8")

    def save_optimized_prompt(self, agent_name: str, prompt: str) -> None:
        """保存优化后的 system prompt"""
        prompt_file = self._agent_dir(agent_name) / "optimized_prompt.md"
        prompt_file.write_text(prompt, encoding="utf-8")

    def get_prompt_version(self, agent_name: str) -> int:
        """获取 prompt 版本号"""
        prompt_file = self._agent_dir(agent_name) / "optimized_prompt.md"
        if not prompt_file.exists():
            return 0
        content = prompt_file.read_text(encoding="utf-8")
        # 从文件中提取版本号
        for line in content.split("\n")[:5]:
            if "version:" in line.lower():
                try:
                    return int(line.split(":")[-1].strip())
                except ValueError:
                    pass
        return 1

    # ------------------------------------------------------------------
    # 统计信息
    # ------------------------------------------------------------------

    def get_evolution_stats(self, agent_name: str) -> Dict[str, Any]:
        """获取进化统计信息"""
        history = self.load_evolution_history(agent_name)
        patterns = self.load_success_patterns(agent_name)
        prompt_version = self.get_prompt_version(agent_name)

        return {
            "agent_name": agent_name,
            "current_generation": self.get_current_generation(agent_name),
            "total_evolutions": len(history),
            "total_patterns": len(patterns),
            "prompt_version": prompt_version,
            "last_evolution": history[0].timestamp if history else None,
        }


# ------------------------------------------------------------------
# 版本迭代记忆 - DecisionMemory（解决鬼打墙问题）
# ------------------------------------------------------------------


@dataclass
class DecisionRecord:
    """重要决策记录 - 解决鬼打墙问题

    记录每次重要决策，让 Agent 记住：
    - 这个问题上次是什么？怎么修的？
    - 类似的坑以后怎么处理？
    - 版本之间的关键决策是什么？
    """

    id: str = ""  # {yyyy-MM-dd}-{slug}
    title: str = ""  # 决策标题
    timestamp: str = ""  # 决策时间
    agent_type: str = ""  # 做出决策的 Agent 类型
    category: str = ""  # 决策类别: bug_fix, solution_choice, rejection, architecture

    # 问题背景
    problem: str = ""  # 遇到的问题描述
    context: str = ""  # 上下文（文件、函数、错误信息等）

    # 决策内容
    chosen_solution: str = ""  # 选择的方案
    rejected_alternatives: List[str] = field(default_factory=list)  # 放弃的方案及原因

    # 结果
    result: str = ""  # 成功/失败
    outcome: str = ""  # 效果描述

    # 可复用性
    reusable_for: str = ""  # 类似场景描述
    keywords: List[str] = field(default_factory=list)  # 检索关键词

    # 元数据
    related_files: List[str] = field(default_factory=list)  # 相关文件
    version_tag: str = ""  # 版本标签（如 v1.2.3）


class DecisionMemory:
    """版本迭代记忆 - 解决 Agent 鬼打墙问题

    核心功能：
    1. 记录重要决策（解决方案选择、bug修复、拒绝的建议）
    2. 检索历史决策，避免重复踩坑
    3. 自动提取关键词便于检索

    目录结构：
    .omc/state/decisions/
    └── {yyyy-MM-dd}-{slug}.md  # 每次决策一条 Markdown 记录
    """

    def __init__(self, state_dir: Path):
        """
        Args:
            state_dir: .omc/state 目录
        """
        self.state_dir = Path(state_dir)
        self.decisions_dir = self.state_dir / "decisions"
        self.decisions_dir.mkdir(parents=True, exist_ok=True)

    def _slugify(self, text: str) -> str:
        """将文本转为 URL-friendly slug"""
        # 简单实现：只保留字母数字和短横线
        s = text.lower()
        s = re.sub(r"[^\w\s-]", "", s)
        s = re.sub(r"[\s_]+", "-", s)
        s = re.sub(r"-+", "-", s)
        s = s.strip("-")
        # 限制长度
        if len(s) > 40:
            s = s[:40].rstrip("-")
        return s

    def _decision_file(self, decision_id: str) -> Path:
        """获取决策文件路径"""
        return self.decisions_dir / f"{decision_id}.md"

    def record_decision(
        self,
        title: str,
        problem: str,
        chosen_solution: str,
        agent_type: str = "",
        category: str = "solution_choice",
        rejected_alternatives: Optional[List[str]] = None,
        result: str = "",
        outcome: str = "",
        reusable_for: str = "",
        keywords: Optional[List[str]] = None,
        related_files: Optional[List[str]] = None,
        version_tag: str = "",
    ) -> str:
        """
        记录一次重要决策

        Args:
            title: 决策标题
            problem: 遇到的问题
            chosen_solution: 选择的方案
            agent_type: Agent 类型
            category: 决策类别 (bug_fix/solution_choice/rejection/architecture)
            rejected_alternatives: 放弃的方案列表
            result: 结果 (success/failure)
            outcome: 效果描述
            reusable_for: 适用场景
            keywords: 检索关键词
            related_files: 相关文件
            version_tag: 版本标签

        Returns:
            decision_id: 决策记录 ID
        """
        # 生成决策 ID
        date_str = datetime.now().strftime("%Y-%m-%d")
        slug = self._slugify(title)
        decision_id = f"{date_str}-{slug}"

        # 自动提取关键词
        if keywords is None:
            keywords = self._extract_keywords(problem, chosen_solution)

        # 构建 Markdown 内容
        content = self._build_decision_markdown(
            title=title,
            problem=problem,
            chosen_solution=chosen_solution,
            agent_type=agent_type,
            category=category,
            rejected_alternatives=rejected_alternatives or [],
            result=result,
            outcome=outcome,
            reusable_for=reusable_for,
            keywords=keywords,
            related_files=related_files or [],
            version_tag=version_tag,
        )

        # 保存文件
        decision_file = self._decision_file(decision_id)
        decision_file.write_text(content, encoding="utf-8")

        return decision_id

    def _extract_keywords(self, problem: str, solution: str) -> List[str]:
        """从问题和方案中自动提取关键词"""
        text = f"{problem} {solution}".lower()
        # 提取技术术语（简化版）
        words = re.findall(r"\b[a-z_]+\b", text)
        # 过滤常见词
        stopwords = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "from",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "being",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "could",
            "should",
            "may",
            "might",
            "must",
            "shall",
            "can",
            "need",
            "this",
            "that",
            "these",
            "those",
            "i",
            "you",
            "he",
            "she",
            "it",
            "we",
            "they",
            "what",
            "which",
            "who",
            "whom",
            "when",
            "where",
            "why",
            "how",
            "all",
            "each",
            "every",
            "both",
            "few",
            "more",
            "most",
            "other",
            "some",
            "such",
            "no",
            "nor",
            "not",
            "only",
            "own",
            "same",
            "so",
            "than",
            "too",
            "very",
            "just",
            "if",
            "then",
            "else",
            "also",
            "now",
            "here",
            "there",
        }
        keywords = [w for w in words if len(w) >= 3 and w not in stopwords]
        # 去重并返回前10个
        return list(dict.fromkeys(keywords))[:10]

    def _build_decision_markdown(
        self,
        title: str,
        problem: str,
        chosen_solution: str,
        agent_type: str,
        category: str,
        rejected_alternatives: List[str],
        result: str,
        outcome: str,
        reusable_for: str,
        keywords: List[str],
        related_files: List[str],
        version_tag: str,
    ) -> str:
        """构建决策记录的 Markdown 内容"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        lines = [
            f"# {timestamp} {title}",
            "",
            "---",
            f"**Agent**: {agent_type or 'unknown'}",
            f"**类别**: {category}",
            f"**结果**: {result or 'pending'}",
            f"**版本**: {version_tag or 'N/A'}",
            "---",
            "",
            "## 问题背景",
            problem,
            "",
            "## 选择的方案",
            chosen_solution,
        ]

        if rejected_alternatives:
            lines.extend(
                [
                    "",
                    "## 放弃的方案",
                ]
            )
            for alt in rejected_alternatives:
                lines.append(f"- {alt}")

        if outcome:
            lines.extend(
                [
                    "",
                    "## 效果",
                    outcome,
                ]
            )

        if reusable_for:
            lines.extend(
                [
                    "",
                    "## 可复用性",
                    "以后遇到类似场景 → 用此方案",
                    "",
                    f"**适用场景**: {reusable_for}",
                ]
            )

        if keywords:
            lines.extend(
                [
                    "",
                    "## 关键词",
                    ", ".join(f"`{k}`" for k in keywords),
                ]
            )

        if related_files:
            lines.extend(
                [
                    "",
                    "## 相关文件",
                    *[f"- {f}" for f in related_files],
                ]
            )

        return "\n".join(lines)

    def retrieve(
        self,
        query: str,
        limit: int = 5,
    ) -> List[DecisionRecord]:
        """
        检索历史决策

        根据关键词检索相关决策，帮助 Agent 避免重复踩坑。

        Args:
            query: 搜索关键词
            limit: 返回数量上限

        Returns:
            匹配的决策记录列表
        """
        query_terms = set(query.lower().split())
        results: List[tuple[int, DecisionRecord]] = []

        # 遍历所有决策文件
        for decision_file in self.decisions_dir.glob("*.md"):
            try:
                content = decision_file.read_text(encoding="utf-8")
                record = self._parse_decision_file(decision_file, content)
                if not record:
                    continue

                # 计算相关度分数
                score = self._calculate_relevance(query_terms, record)
                if score > 0:
                    results.append((score, record))
            except Exception:
                continue

        # 按相关度排序
        results.sort(key=lambda x: x[0], reverse=True)
        return [r[1] for r in results[:limit]]

    def _parse_decision_file(
        self, file_path: Path, content: str
    ) -> Optional[DecisionRecord]:
        """解析决策文件为 DecisionRecord"""
        # 从文件名提取 ID
        decision_id = file_path.stem

        # 解析标题（第一行）
        lines = content.split("\n")
        title = ""
        if lines and lines[0].startswith("# "):
            title = lines[0][2:].strip()
            # 去掉时间戳前缀
            title = re.sub(r"^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\s+", "", title)

        # 解析元数据
        agent_type = ""
        category = "solution_choice"
        result = ""
        version_tag = ""

        for line in lines:
            if line.startswith("**Agent**:"):
                agent_type = line.split(":**")[1].strip()
            elif line.startswith("**类别**:"):
                category = line.split(":**")[1].strip()
            elif line.startswith("**结果**:"):
                result = line.split(":**")[1].strip()
            elif line.startswith("**版本**:"):
                version_tag = line.split(":**")[1].strip()

        # 解析章节内容
        problem = self._extract_section(content, "问题背景")
        chosen_solution = self._extract_section(content, "选择的方案")
        outcome = self._extract_section(content, "效果")
        reusable_for = self._extract_section(content, "可复用性")

        # 解析关键词
        keywords_str = self._extract_section(content, "关键词")
        keywords = (
            [k.strip("`,") for k in keywords_str.split(",")] if keywords_str else []
        )

        return DecisionRecord(
            id=decision_id,
            title=title,
            timestamp=file_path.stem[:10],  # 日期部分
            agent_type=agent_type,
            category=category,
            problem=problem,
            chosen_solution=chosen_solution,
            result=result,
            outcome=outcome,
            reusable_for=reusable_for,
            keywords=keywords,
            version_tag=version_tag,
        )

    def _extract_section(self, content: str, section_name: str) -> str:
        """提取 Markdown 文档中的指定章节内容"""
        pattern = f"## {section_name}\\n(.*?)(?=\\n## |\\Z)"
        match = re.search(pattern, content, re.DOTALL)
        if match:
            return match.group(1).strip()
        return ""

    def _calculate_relevance(self, query_terms: set, record: DecisionRecord) -> int:
        """计算查询与决策记录的相关度分数"""
        score = 0

        # 标题匹配
        if record.title:
            title_lower = record.title.lower()
            for term in query_terms:
                if term in title_lower:
                    score += 5

        # 问题匹配
        if record.problem:
            problem_lower = record.problem.lower()
            for term in query_terms:
                if term in problem_lower:
                    score += 3

        # 关键词匹配
        if record.keywords:
            for term in query_terms:
                if term in record.keywords:
                    score += 2

        # 可复用场景匹配
        if record.reusable_for:
            reusable_lower = record.reusable_for.lower()
            for term in query_terms:
                if term in reusable_lower:
                    score += 2

        return score

    def list_decisions(
        self,
        category: Optional[str] = None,
        limit: int = 20,
    ) -> List[DecisionRecord]:
        """
        列出决策记录

        Args:
            category: 按类别过滤
            limit: 返回数量上限

        Returns:
            决策记录列表（按时间倒序）
        """
        results = []

        # 按修改时间倒序遍历
        files = sorted(
            self.decisions_dir.glob("*.md"),
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        )

        for decision_file in files:
            if limit and len(results) >= limit:
                break

            try:
                content = decision_file.read_text(encoding="utf-8")
                record = self._parse_decision_file(decision_file, content)
                if record and (category is None or record.category == category):
                    results.append(record)
            except Exception:
                continue

        return results

    def get_stats(self) -> Dict[str, Any]:
        """获取决策记忆统计"""
        decisions = self.list_decisions(limit=1000)

        # 按类别统计
        category_counts: Dict[str, int] = {}
        for d in decisions:
            category_counts[d.category] = category_counts.get(d.category, 0) + 1

        return {
            "total_decisions": len(decisions),
            "by_category": category_counts,
            "latest_decision": decisions[0].id if decisions else None,
        }
