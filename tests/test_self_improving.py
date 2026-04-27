"""
主动学习模块测试
"""

import tempfile
from pathlib import Path

import pytest

from src.agents.self_improving import (
    ExecutionFeedback,
    LearningStore,
    SelfImprovingAgent,
    StrategyAdjustment,
)


class TestLearningStore:
    """测试学习数据存储"""

    @pytest.fixture
    def temp_db(self):
        """临时数据库"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)
        yield db_path
        db_path.unlink(missing_ok=True)

    @pytest.fixture
    def store(self, temp_db):
        """LearningStore 实例"""
        return LearningStore(temp_db)

    def test_init_creates_tables(self, temp_db):
        """测试初始化创建表"""
        LearningStore(temp_db)
        import sqlite3

        with sqlite3.connect(temp_db) as conn:
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            table_names = [t[0] for t in tables]
            assert "execution_feedback" in table_names
            assert "strategy_adjustments" in table_names

    def test_record_feedback(self, store):
        """测试记录反馈"""
        feedback = ExecutionFeedback(
            agent_type="executor",
            task_description="test task",
            success=True,
            execution_time=1.5,
        )
        feedback_id = store.record_feedback(feedback)
        assert feedback_id > 0

    def test_get_recent_failures(self, store):
        """测试获取最近失败"""
        # 记录成功和失败
        store.record_feedback(
            ExecutionFeedback(
                agent_type="executor", task_description="success", success=True
            )
        )
        store.record_feedback(
            ExecutionFeedback(
                agent_type="executor", task_description="failure", success=False
            )
        )

        failures = store.get_recent_failures("executor", limit=10)
        assert len(failures) == 1
        assert failures[0].task_description == "failure"

    def test_get_error_patterns(self, store):
        """测试错误模式分析"""
        # 记录多个相同类型的错误
        for _ in range(3):
            store.record_feedback(
                ExecutionFeedback(
                    agent_type="executor",
                    task_description="test",
                    success=False,
                    error_type="syntax_error",
                    execution_time=1.0,
                )
            )

        patterns = store.get_error_patterns("executor", min_count=2)
        assert len(patterns) == 1
        assert patterns[0]["error_type"] == "syntax_error"
        assert patterns[0]["count"] == 3

    def test_get_success_rate(self, store):
        """测试成功率计算"""
        # 7成功 3失败
        for _ in range(7):
            store.record_feedback(
                ExecutionFeedback(agent_type="executor", success=True)
            )
        for _ in range(3):
            store.record_feedback(
                ExecutionFeedback(agent_type="executor", success=False)
            )

        rate = store.get_success_rate("executor", days=7)
        assert abs(rate - 0.7) < 0.01  # 70% 成功率


class TestSelfImprovingAgent:
    """测试主动学习 Agent"""

    @pytest.fixture
    def agent(self, tmp_path):
        """SelfImprovingAgent 实例"""
        db_path = tmp_path / "learning.db"
        store = LearningStore(db_path)
        return SelfImprovingAgent(store)

    def test_record_execution_success(self, agent):
        """测试记录成功执行"""
        feedback_id = agent.record_execution(
            agent_type="executor",
            task_description="test task",
            success=True,
            execution_time=2.0,
        )
        assert feedback_id > 0

    def test_record_execution_with_error(self, agent):
        """测试记录带错误的执行"""
        error = SyntaxError("invalid syntax")
        feedback_id = agent.record_execution(
            agent_type="executor",
            task_description="test task",
            success=False,
            error=error,
        )
        assert feedback_id > 0

        # 验证错误分类
        patterns = agent.store.get_error_patterns("executor", min_count=1)
        assert len(patterns) == 1
        assert "syntax" in patterns[0]["error_type"]

    def test_classify_error(self, agent):
        """测试错误分类"""
        assert agent._classify_error(TimeoutError("timeout")) == "timeout"
        assert (
            agent._classify_error(PermissionError("denied")) == "permissionerror_error"
        )
        assert agent._classify_error(ConnectionError("network")) == "network_error"

    def test_generate_adjustment(self, agent):
        """测试生成调整建议"""
        pattern = {"error_type": "syntax_error", "count": 3}
        adjustment = agent._generate_adjustment("executor", pattern)

        assert adjustment is not None
        assert adjustment.agent_type == "executor"
        assert adjustment.adjustment_type == "prompt_update"
        assert "syntax" in adjustment.pattern_detected

    def test_analyze_and_improve(self, agent):
        """测试分析并改进"""
        # 记录多个语法错误
        for _ in range(3):
            agent.record_execution(
                agent_type="executor",
                task_description="test",
                success=False,
                error=SyntaxError("error"),
            )

        adjustments = agent.analyze_and_improve("executor")
        assert len(adjustments) >= 1
        assert adjustments[0].adjustment_type == "prompt_update"

    def test_get_improved_prompt(self, agent):
        """测试获取改进后的提示词"""
        base_prompt = "You are a helpful assistant."

        # 先添加一个调整
        agent.store.record_adjustment(
            StrategyAdjustment(
                agent_type="executor",
                pattern_detected="test pattern",
                adjustment_type="prompt_update",
                adjustment_content="Always check syntax before output.",
                effectiveness_score=0.8,
            )
        )

        improved = agent.get_improved_prompt("executor", base_prompt)
        assert "学习优化" in improved
        assert "check syntax" in improved

    def test_report(self, agent):
        """测试生成报告"""
        # 记录一些数据
        agent.record_execution("executor", "task1", True, 1.0)
        agent.record_execution("executor", "task2", False, 2.0)

        report = agent.report("executor")
        assert "generated_at" in report
        assert "executor" in report["agents"]
        assert "success_rate_7d" in report["agents"]["executor"]


# ---------------------------------------------------------------------------
# 导入移到顶部重复使用会被 pytest 未使用导入警告干扰，
# 直接在下面类中 import local，避免 F401。
# ---------------------------------------------------------------------------


class TestAutoCreateSkill:
    """测试自动生成 Skill（auto_create_skill）"""

    @pytest.fixture
    def sia_with_temp(self, tmp_path, tmp_skill_dir):
        """带临时存储的 SelfImprovingAgent"""
        from src.agents.self_improving import LearningStore, SelfImprovingAgent
        from src.memory.learnings import LearningsMemory
        from src.memory.skill_manager import SkillManager

        db_path = tmp_path / "learning.db"
        store = LearningStore(db_path)
        sm = SkillManager(skills_dir=tmp_skill_dir)
        agent = SelfImprovingAgent(store=store, skill_manager=sm)
        agent._memory = LearningsMemory(tmp_path / "learnings")
        return agent

    def test_auto_create_skill_basic(self, sia_with_temp, tmp_skill_dir):
        """测试基本自动生成"""
        from src.memory.skill_manager import SkillManager

        sm = SkillManager(skills_dir=tmp_skill_dir)
        sia_with_temp._skill_manager = sm  # 确保测试用 temp dir

        task_context = {
            "agent_name": "executor",
            "task": "implement user authentication module",
            "workflow": "build",
            "result": "Successfully created auth.py with JWT support",
            "steps": ["explore", "analyst", "planner", "executor", "verifier"],
            "tool_call_count": 7,
        }
        result = sia_with_temp.auto_create_skill(task_context)

        assert result is not None
        assert "skill_id" in result
        # 验证文件已创建
        skill = sm.get_skill(result["skill_id"], include_body=True)
        assert skill is not None
        assert "auth" in skill["body"].lower()
        assert "executor" in skill["tags"]

    def test_auto_create_skill_not_worthy_low_tools(self, sia_with_temp, tmp_skill_dir):
        """工具调用 <5 且无其他条件时不生成"""
        from src.memory.skill_manager import SkillManager

        sia_with_temp._skill_manager = SkillManager(skills_dir=tmp_skill_dir)

        task_context = {
            "agent_name": "executor",
            "task": "simple task",
            "workflow": "build",
            "result": "done",
            "steps": ["explore", "executor"],
            "tool_call_count": 2,
        }
        result = sia_with_temp.auto_create_skill(task_context)
        assert result is None

    def test_auto_create_skill_error_then_fix(self, sia_with_temp, tmp_skill_dir):
        """错误后修复 → 值得沉淀"""
        from src.memory.skill_manager import SkillManager

        sia_with_temp._skill_manager = SkillManager(skills_dir=tmp_skill_dir)

        task_context = {
            "agent_name": "debugger",
            "task": "fix memory leak in background worker",
            "workflow": "debug",
            "result": "Fixed by adding proper cleanup handler",
            "steps": ["explore", "debugger", "verifier"],
            "error": "AttributeError: 'NoneType' has no attribute 'close'",
            "had_fix": True,
            "tool_call_count": 3,
        }
        result = sia_with_temp.auto_create_skill(task_context)
        assert result is not None
        assert result["category"] == "debugging"
        # 验证错误信息写入了 body
        skill = sia_with_temp._skill_manager.get_skill(
            result["skill_id"], include_body=True
        )
        assert skill is not None
        assert "AttributeError" in skill["body"]

    def test_auto_create_skill_user_correction(self, sia_with_temp, tmp_skill_dir):
        """用户纠正 → 值得沉淀"""
        from src.memory.skill_manager import SkillManager

        sia_with_temp._skill_manager = SkillManager(skills_dir=tmp_skill_dir)

        task_context = {
            "agent_name": "writer",
            "task": "write API documentation",
            "workflow": "doc",
            "result": "Revised based on user feedback",
            "steps": ["architect", "writer"],
            "had_user_correction": True,
            "tool_call_count": 1,
        }
        result = sia_with_temp.auto_create_skill(task_context)
        assert result is not None
        assert result["category"] == "corrections"

    def test_auto_create_skill_nontrivial_workflow(self, sia_with_temp, tmp_skill_dir):
        """多步骤工作流 → 值得沉淀"""
        from src.memory.skill_manager import SkillManager

        sia_with_temp._skill_manager = SkillManager(skills_dir=tmp_skill_dir)

        task_context = {
            "agent_name": "architect",
            "task": "design microservices architecture",
            "workflow": "build",
            "result": "Arch diagram created with 5 services",
            "steps": [
                "explore",
                "analyst",
                "planner",
                "architect",
                "executor",
                "verifier",
            ],
            "tool_call_count": 0,
        }
        result = sia_with_temp.auto_create_skill(task_context)
        assert result is not None
        assert result["category"] == "workflow"

    def test_auto_create_skill_patch_existing(self, sia_with_temp, tmp_skill_dir):
        """Skill 已存在时 patch 而非重复 create"""
        from src.memory.skill_manager import SkillManager

        sm = SkillManager(skills_dir=tmp_skill_dir)
        sia_with_temp._skill_manager = sm

        # 用相同 task 两次，第二次应该 patch 而不是 create
        task_context = {
            "agent_name": "executor",
            "task": "implement user authentication",
            "workflow": "build",
            "result": "first run",
            "steps": ["explore", "analyst", "executor"],
            "tool_call_count": 5,
        }

        # 第一次
        result1 = sia_with_temp.auto_create_skill(task_context)
        assert result1 is not None

        # 第二次（相同任务），应该 patch 而非创建新条目
        task_context["result"] = "second run (patched)"
        result2 = sia_with_temp.auto_create_skill(task_context)
        assert result2 is not None
        assert result2["skill_id"] == result1["skill_id"]

        # 列表中只有 1 个 skill
        all_skills = sm.list_skills()
        assert len(all_skills) == 1

        # 验证 body 更新了
        skill = sm.get_skill(result1["skill_id"], include_body=True)
        assert "second run" in skill["body"]

    def test_auto_create_skill_with_judgments(self, sia_with_temp, tmp_skill_dir):
        """重要判断写入 body"""
        from src.memory.skill_manager import SkillManager

        sia_with_temp._skill_manager = SkillManager(skills_dir=tmp_skill_dir)

        task_context = {
            "agent_name": "planner",
            "task": "plan database migration",
            "workflow": "build",
            "result": "Migration plan ready",
            "steps": ["analyst", "planner"],
            "judgments": [
                "Use transaction per batch (1000 rows)",
                "Keep old schema during transition",
            ],
            "tool_call_count": 6,
        }
        result = sia_with_temp.auto_create_skill(task_context)
        assert result is not None
        skill = sia_with_temp._skill_manager.get_skill(
            result["skill_id"], include_body=True
        )
        assert "transaction" in skill["body"]
        assert "重要判断" in skill["body"]

    def test_auto_create_skill_with_gotchas(self, sia_with_temp, tmp_skill_dir):
        """潜在陷阱写入 body"""
        from src.memory.skill_manager import SkillManager

        sia_with_temp._skill_manager = SkillManager(skills_dir=tmp_skill_dir)

        task_context = {
            "agent_name": "executor",
            "task": "run database backup",
            "workflow": "build",
            "result": "Backup completed",
            "steps": ["executor"],
            "gotchas": [
                "锁表期间不要有写入",
                "S3 上传超时设为 30min",
            ],
            "tool_call_count": 5,
        }
        result = sia_with_temp.auto_create_skill(task_context)
        assert result is not None
        skill = sia_with_temp._skill_manager.get_skill(
            result["skill_id"], include_body=True
        )
        assert "潜在陷阱" in skill["body"]
        assert "锁表" in skill["body"]

    def test_auto_create_skill_no_error_info_not_in_body(
        self, sia_with_temp, tmp_skill_dir
    ):
        """无错误时不写错误处理节"""
        from src.memory.skill_manager import SkillManager

        sia_with_temp._skill_manager = SkillManager(skills_dir=tmp_skill_dir)

        task_context = {
            "agent_name": "explorer",
            "task": "explore codebase",
            "workflow": "build",
            "result": "Explored 50 files",
            "steps": ["explorer", "analyst"],
            "tool_call_count": 10,
        }
        result = sia_with_temp.auto_create_skill(task_context)
        assert result is not None
        skill = sia_with_temp._skill_manager.get_skill(
            result["skill_id"], include_body=True
        )
        assert "错误处理" not in skill["body"]

    def test_auto_create_skill_refactor_category(self, sia_with_temp, tmp_skill_dir):
        """refactor 工作流 → category=workflow"""
        from src.memory.skill_manager import SkillManager

        sia_with_temp._skill_manager = SkillManager(skills_dir=tmp_skill_dir)

        task_context = {
            "agent_name": "code-simplifier",
            "task": "refactor legacy auth code",
            "workflow": "refactor",
            "result": "Refactored 800 lines to 200",
            "steps": ["analyst", "planner", "code-simplifier"],
            "tool_call_count": 5,
        }
        result = sia_with_temp.auto_create_skill(task_context)
        assert result is not None
        assert result["category"] == "workflow"


# ---------------------------------------------------------------------------
# Orchestrator 自动沉淀集成测试
# ---------------------------------------------------------------------------


class TestAutoSkillLearning:
    """测试 Orchestrator 工作流完成后自动沉淀"""

    @pytest.fixture
    def temp_skill_dir(self, tmp_path):
        """临时 skills 目录"""

        d = tmp_path / "skills"
        d.mkdir()
        return d

    @pytest.fixture
    def sia_fixture(self, tmp_path, tmp_skill_dir):
        """SelfImprovingAgent with temp stores"""
        from src.agents.self_improving import LearningStore, SelfImprovingAgent
        from src.memory.learnings import LearningsMemory
        from src.memory.skill_manager import SkillManager

        db = tmp_path / "learning.db"
        store = LearningStore(db)
        sm = SkillManager(skills_dir=tmp_skill_dir)
        agent = SelfImprovingAgent(store=store, skill_manager=sm)
        agent._memory = LearningsMemory(tmp_path / "learnings")
        return agent

    @pytest.mark.asyncio
    async def test_maybe_learn_creates_skill_after_workflow(
        self, temp_skill_dir, tmp_path
    ):
        """工作流完成后触发自动沉淀，Skill 文件被创建"""
        from src.core.orchestrator import Orchestrator, WorkflowResult, WorkflowStatus
        from src.memory.skill_manager import SkillManager

        sm = SkillManager(skills_dir=temp_skill_dir)
        orch = Orchestrator(
            model_router=None,
            state_dir=tmp_path / "state",
            skills_dir=temp_skill_dir,
        )
        orch._skill_manager = sm

        result = WorkflowResult(
            workflow_id="test-001",
            status=WorkflowStatus.COMPLETED,
            steps_completed=["explore", "analyst", "planner", "executor", "verifier"],
            steps_failed=[],
            outputs={},
            total_tokens=1000,
            total_cost=0.01,
            execution_time=10.0,
        )
        result.agent_names = result.steps_completed

        context = {
            "task": "implement new feature X",
            "_had_user_correction": True,
        }

        await orch._maybe_learn_from_workflow("build", context, result)

        # 验证：至少有 1 个 Skill 被创建
        skills = sm.list_skills()
        assert len(skills) >= 1
        # 验证 task 内容反映在 skill 里
        skill_ids = [s["skill_id"] for s in skills]
        assert any("feature" in sid or "build" in sid for sid in skill_ids)

    @pytest.mark.asyncio
    async def test_no_skill_when_trivial_workflow(self, temp_skill_dir, tmp_path):
        """简单工作流（<3步）+ 工具调用少 → 不沉淀"""
        from src.core.orchestrator import Orchestrator, WorkflowResult, WorkflowStatus
        from src.memory.skill_manager import SkillManager

        sm = SkillManager(skills_dir=temp_skill_dir)
        orch = Orchestrator(
            model_router=None,
            state_dir=tmp_path / "state",
            skills_dir=temp_skill_dir,
        )
        orch._skill_manager = sm

        result = WorkflowResult(
            workflow_id="trivial-001",
            status=WorkflowStatus.COMPLETED,
            steps_completed=["explorer"],
            steps_failed=[],
            outputs={},
            total_tokens=100,
            total_cost=0.001,
            execution_time=1.0,
        )
        result.agent_names = ["explorer"]

        context = {"task": "list files"}

        await orch._maybe_learn_from_workflow("sequential", context, result)

        # 无新增 skill
        assert len(sm.list_skills()) == 0

    def test_evaluate_skill_worthy_had_fix_true(self, tmp_skill_dir):
        """had_fix=True → 值得沉淀"""
        from src.memory.skill_manager import SkillManager

        assert SkillManager.evaluate_skill_worthy(
            tool_call_count=1,
            had_error=True,
            had_fix=True,
            had_user_correction=False,
            is_nontrivial_workflow=False,
        )

    def test_evaluate_skill_worthy_all_false(self, tmp_skill_dir):
        """全部条件为 False → 不值得"""
        from src.memory.skill_manager import SkillManager

        assert not SkillManager.evaluate_skill_worthy(
            tool_call_count=1,
            had_error=False,
            had_fix=False,
            had_user_correction=False,
            is_nontrivial_workflow=False,
        )
