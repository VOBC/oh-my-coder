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
        store = LearningStore(temp_db)
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
