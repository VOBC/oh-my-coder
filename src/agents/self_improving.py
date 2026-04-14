"""
主动学习模块 - Self-Improving Agent

收集执行反馈，分析失败模式，自动优化策略。
"""

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import (
    AgentLane,
    AgentOutput,
    AgentStatus,
    BaseAgent,
    register_agent,
)


@dataclass
class ExecutionFeedback:
    """执行反馈记录"""

    id: Optional[int] = None
    timestamp: str = ""
    agent_type: str = ""  # executor, planner, debugger, etc.
    task_description: str = ""
    context_hash: str = ""  # 任务上下文的简单哈希
    success: bool = False
    execution_time: float = 0.0
    error_type: Optional[str] = None  # syntax_error, logic_error, timeout, etc.
    error_message: Optional[str] = None
    user_correction: Optional[str] = None  # 用户提供的修正
    retry_count: int = 0
    final_success: bool = False  # 重试后是否成功


@dataclass
class StrategyAdjustment:
    """策略调整记录"""

    id: Optional[int] = None
    timestamp: str = ""
    agent_type: str = ""
    pattern_detected: str = ""  # 检测到的模式
    adjustment_type: str = ""  # prompt_update, parameter_tune, workflow_change
    adjustment_content: str = ""  # 具体的调整内容
    effectiveness_score: float = 0.0  # 1.0 = 完全有效
    applied_count: int = 0  # 应用次数


class LearningStore:
    """学习数据存储（SQLite）"""

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """初始化数据库表"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS execution_feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    agent_type TEXT NOT NULL,
                    task_description TEXT,
                    context_hash TEXT,
                    success BOOLEAN,
                    execution_time REAL,
                    error_type TEXT,
                    error_message TEXT,
                    user_correction TEXT,
                    retry_count INTEGER DEFAULT 0,
                    final_success BOOLEAN DEFAULT 0
                )
            """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS strategy_adjustments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    agent_type TEXT NOT NULL,
                    pattern_detected TEXT NOT NULL,
                    adjustment_type TEXT NOT NULL,
                    adjustment_content TEXT NOT NULL,
                    effectiveness_score REAL DEFAULT 0.0,
                    applied_count INTEGER DEFAULT 0
                )
            """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_feedback_agent_type 
                ON execution_feedback(agent_type)
            """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_feedback_error_type 
                ON execution_feedback(error_type)
            """
            )

    def record_feedback(self, feedback: ExecutionFeedback) -> int:
        """记录执行反馈"""
        feedback.timestamp = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO execution_feedback 
                (timestamp, agent_type, task_description, context_hash, success,
                 execution_time, error_type, error_message, user_correction,
                 retry_count, final_success)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    feedback.timestamp,
                    feedback.agent_type,
                    feedback.task_description,
                    feedback.context_hash,
                    feedback.success,
                    feedback.execution_time,
                    feedback.error_type,
                    feedback.error_message,
                    feedback.user_correction,
                    feedback.retry_count,
                    feedback.final_success,
                ),
            )
            return cursor.lastrowid

    def record_adjustment(self, adjustment: StrategyAdjustment) -> int:
        """记录策略调整"""
        adjustment.timestamp = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO strategy_adjustments
                (timestamp, agent_type, pattern_detected, adjustment_type,
                 adjustment_content, effectiveness_score, applied_count)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    adjustment.timestamp,
                    adjustment.agent_type,
                    adjustment.pattern_detected,
                    adjustment.adjustment_type,
                    adjustment.adjustment_content,
                    adjustment.effectiveness_score,
                    adjustment.applied_count,
                ),
            )
            return cursor.lastrowid

    def get_recent_failures(
        self, agent_type: str, limit: int = 10
    ) -> List[ExecutionFeedback]:
        """获取最近的失败记录"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT * FROM execution_feedback 
                WHERE agent_type = ? AND success = 0
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (agent_type, limit),
            ).fetchall()
            return [ExecutionFeedback(**dict(row)) for row in rows]

    def get_error_patterns(self, agent_type: str, min_count: int = 3) -> List[Dict]:
        """分析错误模式"""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT error_type, COUNT(*) as count,
                       AVG(execution_time) as avg_time,
                       AVG(retry_count) as avg_retries
                FROM execution_feedback 
                WHERE agent_type = ? AND error_type IS NOT NULL
                GROUP BY error_type
                HAVING count >= ?
                ORDER BY count DESC
                """,
                (agent_type, min_count),
            ).fetchall()
            return [
                {
                    "error_type": row[0],
                    "count": row[1],
                    "avg_execution_time": row[2],
                    "avg_retries": row[3],
                }
                for row in rows
            ]

    def get_success_rate(self, agent_type: str, days: int = 7) -> float:
        """计算成功率"""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT 
                    COUNT(CASE WHEN success = 1 THEN 1 END) * 1.0 / COUNT(*)
                FROM execution_feedback 
                WHERE agent_type = ? 
                AND timestamp > datetime('now', '-{} days')
                """.format(
                    days
                ),
                (agent_type,),
            ).fetchone()
            return row[0] if row and row[0] else 0.0

    def get_adjustments(self, agent_type: str) -> List[StrategyAdjustment]:
        """获取策略调整记录"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT * FROM strategy_adjustments 
                WHERE agent_type = ?
                ORDER BY effectiveness_score DESC, applied_count DESC
                """,
                (agent_type,),
            ).fetchall()
            return [StrategyAdjustment(**dict(row)) for row in rows]


@register_agent
class SelfImprovingAgent(BaseAgent):
    """
    主动学习 Agent

    功能：
    1. 收集执行反馈
    2. 分析失败模式
    3. 生成策略调整建议
    4. 跟踪调整效果
    """

    name = "self-improving"
    description = "主动学习智能体 - 收集反馈、分析模式、优化策略"
    lane = AgentLane.COORDINATION
    default_tier = "low"
    icon = "🧠"
    tools = ["file_read", "file_write"]

    def __init__(
        self,
        model_router=None,
        config: Optional[Dict[str, Any]] = None,
        store: Optional[LearningStore] = None,
        skill_manager: Optional[Any] = None,
    ):
        super().__init__(model_router, config)
        db_path = Path.home() / ".omc" / "learning.db"
        self.store = store or LearningStore(str(db_path))
        # LearningsMemory 用于 best-practice → Skill 升级（懒导入避免循环）
        from ..memory.learnings import LearningsMemory

        self._memory = LearningsMemory(Path.home() / ".omc")
        # SkillManager 可选注入（测试时注入临时目录）
        self._skill_manager: Optional[Any] = skill_manager

    @property
    def system_prompt(self) -> str:
        return """你是一个主动学习的优化助手。分析执行反馈，识别失败模式，生成策略调整建议。
关注：错误类型分布、成功率趋势、重试效果、prompt 优化方向。"""

    def record_execution(
        self,
        agent_type: str,
        task_description: str,
        success: bool,
        execution_time: float = 0.0,
        error: Optional[Exception] = None,
        user_correction: Optional[str] = None,
        retry_count: int = 0,
    ) -> int:
        """记录执行结果"""
        error_type = None
        error_message = None

        if error:
            error_type = self._classify_error(error)
            error_message = str(error)[:500]  # 限制长度

        feedback = ExecutionFeedback(
            agent_type=agent_type,
            task_description=task_description[:200],
            context_hash=self._hash_context(task_description),
            success=success,
            execution_time=execution_time,
            error_type=error_type,
            error_message=error_message,
            user_correction=user_correction,
            retry_count=retry_count,
            final_success=success or (retry_count > 0),
        )
        return self.store.record_feedback(feedback)

    def analyze_and_improve(self, agent_type: str) -> List[StrategyAdjustment]:
        """分析并生成改进建议"""
        patterns = self.store.get_error_patterns(agent_type, min_count=2)
        adjustments = []

        for pattern in patterns:
            adjustment = self._generate_adjustment(agent_type, pattern)
            if adjustment:
                adjustment_id = self.store.record_adjustment(adjustment)
                adjustment.id = adjustment_id
                adjustments.append(adjustment)

        return adjustments

    def get_improved_prompt(self, agent_type: str, base_prompt: str) -> str:
        """获取改进后的提示词"""
        adjustments = self.store.get_adjustments(agent_type)

        # 筛选高效果的 prompt 调整
        prompt_adjustments = [
            a
            for a in adjustments
            if a.adjustment_type == "prompt_update" and a.effectiveness_score > 0.5
        ]

        if not prompt_adjustments:
            return base_prompt

        # 应用最有效的调整
        improved = base_prompt
        for adj in prompt_adjustments[:3]:  # 最多应用前3个
            improved += (
                f"\n\n[学习优化] {adj.pattern_detected}:\n{adj.adjustment_content}"
            )

        return improved

    def _classify_error(self, error: Exception) -> str:
        """分类错误类型"""
        error_msg = str(error).lower()
        error_type = type(error).__name__.lower()

        if "syntax" in error_msg or "syntax" in error_type:
            return "syntax_error"
        elif "timeout" in error_msg or "timeout" in error_type:
            return "timeout"
        elif "memory" in error_msg or "memory" in error_type:
            return "memory_error"
        elif "permission" in error_msg or "access" in error_msg:
            return "permission_error"
        elif "network" in error_msg or "connection" in error_msg:
            return "network_error"
        elif "api" in error_msg or "rate limit" in error_msg:
            return "api_error"
        else:
            return f"{error_type}_error"

    def _hash_context(self, context: str) -> str:
        """简单的上下文哈希"""
        import hashlib

        return hashlib.md5(context.encode()).hexdigest()[:16]

    def _generate_adjustment(
        self, agent_type: str, pattern: Dict
    ) -> Optional[StrategyAdjustment]:
        """根据错误模式生成调整建议"""
        error_type = pattern["error_type"]

        # 预定义的调整策略
        adjustments_map = {
            "syntax_error": (
                "prompt_update",
                "在生成代码前，先验证语法正确性。使用 ast.parse 检查 Python 代码。",
            ),
            "timeout": (
                "parameter_tune",
                "增加超时时间限制，或拆分任务为更小的步骤。",
            ),
            "memory_error": (
                "parameter_tune",
                "限制单次处理的数据量，使用流式处理或分批处理。",
            ),
            "api_error": (
                "workflow_change",
                "添加指数退避重试机制，处理 API 限流。",
            ),
            "network_error": (
                "workflow_change",
                "添加网络连接检查和自动重试逻辑。",
            ),
        }

        if error_type not in adjustments_map:
            return None

        adj_type, adj_content = adjustments_map[error_type]

        return StrategyAdjustment(
            agent_type=agent_type,
            pattern_detected=f"{error_type} (出现 {pattern['count']} 次)",
            adjustment_type=adj_type,
            adjustment_content=adj_content,
            effectiveness_score=0.5,  # 初始分数，后续根据效果调整
        )

    def report(self, agent_type: Optional[str] = None) -> Dict:
        """生成学习报告"""
        report = {
            "generated_at": datetime.now().isoformat(),
            "agents": {},
        }

        # 如果没有指定 agent_type，分析所有
        agent_types = [agent_type] if agent_type else self._get_all_agent_types()

        for at in agent_types:
            report["agents"][at] = {
                "success_rate_7d": self.store.get_success_rate(at, days=7),
                "success_rate_30d": self.store.get_success_rate(at, days=30),
                "error_patterns": self.store.get_error_patterns(at, min_count=2),
                "active_adjustments": len(self.store.get_adjustments(at)),
            }

        return report

    def _get_all_agent_types(self) -> List[str]:
        """获取所有记录的 agent 类型"""
        with sqlite3.connect(self.store.db_path) as conn:
            rows = conn.execute(
                "SELECT DISTINCT agent_type FROM execution_feedback"
            ).fetchall()
            return [row[0] for row in rows]

    async def _run(self, task: str) -> AgentOutput:
        """执行自我改进任务"""
        import json

        parts = task.lower().split()
        if "report" in parts or "报告" in parts:
            data = self.report()
        elif "analyze" in parts or "分析" in parts:
            agent_type = parts[-1] if len(parts) > 1 else None
            adjustments = self.analyze_and_improve(agent_type) if agent_type else []
            data = {"adjustments": [str(a) for a in adjustments]}
        elif "promote" in parts or "升级" in parts or "skill" in parts:
            # 将 best-practice 条目升级为 Skill 文件
            data = self.promote_best_practices_to_skills()
        else:
            data = self.report()

        return AgentOutput(
            status=AgentStatus.SUCCESS,
            content=json.dumps(data, ensure_ascii=False, indent=2),
        )

    def auto_create_skill(
        self,
        task_context: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        自动生成 Skill 文件。

        从 task_context 提取：
        - 任务类型（category）
        - 关键步骤（key_steps）
        - 重要判断（judgments）
        - 潜在陷阱（gotchas）

        满足以下任一条件才创建：
        1. 工具调用 ≥5 次且成功
        2. 错误 → 解决
        3. 用户纠正
        4. 非平凡工作流（多步骤）

        Args:
            task_context: 包含以下键的字典：
                - agent_name: str
                - task: str（任务描述）
                - workflow: str（工作流名）
                - result: str（最终结果摘要）
                - steps: List[str]（步骤列表）
                - error: Optional[str]（错误信息）
                - had_fix: bool（是否从错误中恢复）
                - had_user_correction: bool
                - tool_call_count: int（工具调用次数）

        Returns:
            Skill 信息 dict；不满足条件返回 None
        """
        from ..memory.skill_manager import SkillManager

        # ---- 评估是否值得沉淀 ----
        tool_call_count = task_context.get("tool_call_count", 0)
        had_error = bool(task_context.get("error"))
        had_fix = task_context.get("had_fix", False)
        had_user_correction = task_context.get("had_user_correction", False)
        is_nontrivial = len(task_context.get("steps", [])) >= 3

        if not SkillManager.evaluate_skill_worthy(
            tool_call_count=tool_call_count,
            had_error=had_error,
            had_fix=had_fix,
            had_user_correction=had_user_correction,
            is_nontrivial_workflow=is_nontrivial,
        ):
            return None

        # ---- 生成 Skill 内容 ----
        agent_name = task_context.get("agent_name", "unknown")
        task = task_context.get("task", "")
        workflow = task_context.get("workflow", "general")
        result_summary = task_context.get("result", "")[:300]
        steps = task_context.get("steps", [])
        error_msg = task_context.get("error", "")
        judgments = task_context.get("judgments", [])
        gotchas = task_context.get("gotchas", [])

        # 判断 category
        if error_msg:
            category = "debugging"
        elif had_user_correction:
            category = "corrections"
        elif workflow in {"build", "refactor", "test", "doc"}:
            category = "workflow"
        else:
            category = "best-practices"

        # 生成 skill_id（避免重复）
        skill_id = SkillManager._slugify(f"{workflow}-{agent_name}-{task[:20]}")
        if len(skill_id) > 40:
            skill_id = skill_id[:40]

        # 提取 triggers
        triggers = []
        skip_words = {
            "the",
            "and",
            "for",
            "with",
            "from",
            "this",
            "that",
            "into",
            "your",
            "some",
            "any",
            "all",
            "but",
            "not",
            "are",
            "was",
            "were",
            "been",
            "have",
            "has",
            "had",
            "will",
            "would",
        }
        for word in task.split():
            w = word.strip(".,!?;:()[]{}").lower()
            if len(w) >= 3 and w not in skip_words:
                triggers.append(w)

        # 生成 tags
        tags = list({workflow, agent_name})
        tags.extend(triggers[:3])

        # ---- 构建 body ----
        body_lines = [
            f"# {workflow.title()} with {agent_name.title()}",
            "",
            f"**任务**: {task}",
            f"**工作流**: {workflow}",
            f"**Agent**: {agent_name}",
            "",
        ]

        # 关键步骤
        if steps:
            body_lines.append("## 关键步骤")
            for i, step in enumerate(steps, 1):
                body_lines.append(f"{i}. {step}")
            body_lines.append("")

        # 重要判断
        if judgments:
            body_lines.append("## 重要判断")
            for j in judgments:
                body_lines.append(f"- {j}")
            body_lines.append("")

        # 执行结果
        body_lines.append("## 执行结果")
        body_lines.append(result_summary if result_summary else "（无）")
        body_lines.append("")

        # 错误处理
        if error_msg:
            body_lines.append("## 错误处理")
            body_lines.append(error_msg[:200])
            body_lines.append("")

        # 潜在陷阱
        if gotchas:
            body_lines.append("## 潜在陷阱")
            for g in gotchas:
                body_lines.append(f"- ⚠️ {g}")
            body_lines.append("")

        # 适用条件
        body_lines.append("## 适用条件")
        body_lines.append(f"- 任务类型: {workflow}")
        if triggers:
            body_lines.append(f"- 触发词: {', '.join(triggers[:5])}")

        body = "\n".join(body_lines)
        description = task[:120].strip()

        # ---- 写入 Skill 文件（patch 优先）----
        sm = self._skill_manager or SkillManager()
        try:
            skill_info = sm.patch(
                skill_id=skill_id,
                body=body,
                category=category,
                description=description,
                tags=tags,
                triggers=triggers[:5],
            )
        except Exception:
            try:
                skill_info = sm.create(
                    name=skill_id,
                    body=body,
                    category=category,
                    description=description,
                    tags=tags,
                    triggers=triggers[:5],
                )
            except Exception:
                return None

        # ---- 同时记录到 LearningsMemory ----
        try:
            self._memory.add(
                title=f"[Auto] {workflow}: {task[:40]}",
                content=body,
                category="best-practice",
                tags=tags,
                context=", ".join(triggers[:3]),
            )
        except Exception:
            pass  # 不影响主流程

        return skill_info

    def promote_best_practices_to_skills(
        self,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        将 LearningsMemory 中标记为 best-practice 的条目
        自动升级为 .omc/skills/best-practices/*.md Skill 文件。

        用于：LearningsMemory.best_practices → SkillManager → .omc/skills/

        Args:
            dry_run: True = 只报告，不实际创建

        Returns:
            操作结果摘要
        """
        from ..memory.skill_manager import SkillManager

        sm = SkillManager()
        best_practices = self._memory.get_by_category("best-practice")
        results = {"created": [], "skipped": [], "errors": []}

        for entry in best_practices:
            skill_id = entry.id
            if not dry_run:
                try:
                    sm.patch(
                        skill_id=skill_id,
                        body=entry.content,
                        description=entry.title,
                        tags=entry.tags,
                        triggers=[entry.context] if entry.context else [],
                        category="best-practices",
                    )
                    results["created"].append(skill_id)
                except Exception as e:
                    results["errors"].append({"skill_id": skill_id, "error": str(e)})
            else:
                results["skipped"].append(skill_id)

        results["total_best_practices"] = len(best_practices)
        results["total_skills"] = len(sm.list_skills())
        return results
