"""
测试交叉验证层

运行: pytest tests/test_cross_validation.py -v
"""

import sys
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, "/Users/vobc/.qclaw/workspace-agent-bf627e2b/projects/oh-my-coder")


from src.agents.cross_validation import (
    CrossValidationLayer,
    CrossValidationResult,
    ValidationIssue,
    ValidationSeverity,
    ValidationStatus,
)

# ------------------------------------------------------------------
# Mock 对象
# ------------------------------------------------------------------


class MockAgentOutput:
    """模拟 AgentOutput"""

    def __init__(self, result: str = "", error: str = ""):
        self.result = result
        self.error = error


class MockWorkflowResult:
    """模拟 WorkflowResult"""

    def __init__(
        self,
        workflow_id: str = "abc123",
        status: str = "completed",
        steps_completed: list | None = None,
        outputs: dict | None = None,
        error: str = "",
    ):
        self.workflow_id = workflow_id
        self.status = status
        self.steps_completed = steps_completed or ["analyst", "executor"]
        self.outputs = outputs or {
            "analyst": MockAgentOutput(result="分析了需求，生成了5个功能点"),
            "executor": MockAgentOutput(result="# 实现代码\n\ndef foo():\n    pass"),
        }
        self.error = error


class MockModelResponse:
    """模拟 ModelResponse"""

    def __init__(self, content: str = ""):
        self.content = content


# ------------------------------------------------------------------
# 模型解析测试
# ------------------------------------------------------------------


class TestParseValidationOutput:
    """测试输出解析"""

    def setup_method(self):
        self.layer = CrossValidationLayer(model_router=None)

    def test_parse_empty_output(self):
        issues = self.layer._parse_validation_output("")
        assert issues == []

    def test_parse_none_output(self):
        issues = self.layer._parse_validation_output(None)
        assert issues == []

    def test_parse_single_issue(self):
        text = """### 验证结论
NEED_FIX

### [CRITICAL] logic: 空指针检查缺失
- 位置: src/main.py:42
- 证据: if user.profile is None: return
- 建议: 添加空值断言或默认行为
"""
        issues = self.layer._parse_validation_output(text)
        assert len(issues) == 1
        assert issues[0].severity == ValidationSeverity.CRITICAL
        assert issues[0].category == "logic"
        assert "空指针" in issues[0].description
        assert issues[0].location == "src/main.py:42"
        assert "添加空值断言" in issues[0].suggestion

    def test_parse_multiple_issues(self):
        text = """### 验证结论
FAIL

### [HIGH] security: SQL 注入风险
- 位置: src/db.py:10
- 建议: 使用参数化查询

### [MEDIUM] style: 命名不规范
- 位置: src/utils.py:5
- 建议: 变量名使用 snake_case
"""
        issues = self.layer._parse_validation_output(text)
        assert len(issues) == 2
        assert issues[0].severity == ValidationSeverity.HIGH
        assert issues[1].severity == ValidationSeverity.MEDIUM

    def test_parse_pass_output(self):
        text = """### 验证结论
PASS

代码质量良好，未发现明显问题。
"""
        issues = self.layer._parse_validation_output(text)
        assert issues == []

    def test_parse_chinese_severity(self):
        text = "### [严重] logic: 描述"
        issues = self.layer._parse_validation_output(text)
        assert len(issues) == 1
        assert issues[0].severity == ValidationSeverity.CRITICAL


class TestParseSeverity:
    """测试严重性解析"""

    def setup_method(self):
        self.layer = CrossValidationLayer(model_router=None)

    def test_critical(self):
        assert self.layer._parse_severity("critical") == ValidationSeverity.CRITICAL
        assert self.layer._parse_severity("CRITICAL") == ValidationSeverity.CRITICAL

    def test_high(self):
        assert self.layer._parse_severity("high") == ValidationSeverity.HIGH
        assert self.layer._parse_severity("HIGH") == ValidationSeverity.HIGH

    def test_medium(self):
        assert self.layer._parse_severity("medium") == ValidationSeverity.MEDIUM

    def test_low(self):
        assert self.layer._parse_severity("low") == ValidationSeverity.LOW

    def test_unknown_defaults_to_low(self):
        assert self.layer._parse_severity("unknown") == ValidationSeverity.LOW


class TestDetermineStatus:
    """测试状态判定"""

    def setup_method(self):
        self.layer = CrossValidationLayer(model_router=None)

    def test_empty_issues_is_pass(self):
        assert self.layer._determine_status([]) == ValidationStatus.PASS

    def test_critical_issue_is_fail(self):
        issues = [
            ValidationIssue(
                severity=ValidationSeverity.CRITICAL,
                category="logic",
                description="致命错误",
            )
        ]
        assert self.layer._determine_status(issues) == ValidationStatus.FAIL

    def test_high_issue_is_need_fix(self):
        issues = [
            ValidationIssue(
                severity=ValidationSeverity.HIGH,
                category="security",
                description="安全问题",
            )
        ]
        assert self.layer._determine_status(issues) == ValidationStatus.NEED_FIX

    def test_medium_issue_is_pass(self):
        issues = [
            ValidationIssue(
                severity=ValidationSeverity.MEDIUM,
                category="style",
                description="代码风格",
            )
        ]
        assert self.layer._determine_status(issues) == ValidationStatus.PASS


class TestExtractOutputs:
    """测试输出提取"""

    def setup_method(self):
        self.layer = CrossValidationLayer(model_router=None)

    def test_extract_normal_outputs(self):
        result = MockWorkflowResult(
            outputs={
                "analyst": MockAgentOutput(result="分析结果"),
                "executor": MockAgentOutput(result="代码实现"),
            }
        )
        outputs = self.layer._extract_outputs(result)
        assert outputs["analyst"] == "分析结果"
        assert outputs["executor"] == "代码实现"

    def test_extract_error_outputs(self):
        result = MockWorkflowResult(
            outputs={
                "analyst": MockAgentOutput(result="", error="连接超时"),
            }
        )
        outputs = self.layer._extract_outputs(result)
        assert "[ERROR] 连接超时" in outputs["analyst"]

    def test_extract_empty_outputs(self):
        result = MagicMock()
        result.outputs = {}
        outputs = self.layer._extract_outputs(result)
        assert outputs == {}


class TestCrossValidationResult:
    """测试结果数据类"""

    def test_pass_rate_no_issues(self):
        result = CrossValidationResult(
            validation_id="v1",
            workflow_id="w1",
            workflow_name="build",
            status=ValidationStatus.PASS,
            agent_outputs={},
        )
        assert result.pass_rate == "100%"

    def test_pass_rate_with_critical(self):
        result = CrossValidationResult(
            validation_id="v1",
            workflow_id="w1",
            workflow_name="build",
            status=ValidationStatus.FAIL,
            agent_outputs={},
            issues=[
                ValidationIssue(
                    severity=ValidationSeverity.CRITICAL,
                    category="logic",
                    description="致命",
                )
            ],
        )
        assert result.pass_rate == "0%"

    def test_pass_rate_with_high(self):
        result = CrossValidationResult(
            validation_id="v1",
            workflow_id="w1",
            workflow_name="build",
            status=ValidationStatus.NEED_FIX,
            agent_outputs={},
            issues=[
                ValidationIssue(
                    severity=ValidationSeverity.HIGH,
                    category="security",
                    description="高危",
                )
            ],
        )
        assert result.pass_rate == "50%"

    def test_to_summary(self):
        result = CrossValidationResult(
            validation_id="v12345",
            workflow_id="w999",
            workflow_name="build",
            status=ValidationStatus.PASS,
            agent_outputs={"executor": "实现了功能"},
            issues=[],
            execution_time=5.5,
            mode="verify_only",
        )
        summary = result.to_summary()
        assert "v12345" in summary
        assert "build" in summary
        assert "PASS" in summary
        assert "✅ 未发现明显问题" in summary


class TestValidateWorkflow:
    """测试工作流验证集成"""

    def setup_method(self):
        self.layer = CrossValidationLayer(model_router=None)

    @pytest.mark.asyncio
    async def test_validate_skipped_when_no_outputs(self):
        """无输出时跳过验证"""
        result = MockWorkflowResult(outputs={})

        cv_result = await self.layer.validate_workflow(result, "build")
        assert cv_result.status == ValidationStatus.SKIPPED

    @pytest.mark.asyncio
    async def test_validate_pass_when_no_issues(self):
        """无问题时报 PASS"""
        result = MockWorkflowResult(
            outputs={"executor": MockAgentOutput(result="好代码")}
        )

        # Mock router 永远返回 PASS
        mock_router = MagicMock()
        mock_router.route_and_call = AsyncMock(
            return_value=MockModelResponse("### 验证结论\n\nPASS\n\n代码质量良好。")
        )
        self.layer.model_router = mock_router

        cv_result = await self.layer.validate_workflow(result, "build")
        assert cv_result.status == ValidationStatus.PASS
        assert cv_result.validation_id  # 有 ID
        assert cv_result.execution_time >= 0

    @pytest.mark.asyncio
    async def test_validate_fail_with_critical_issue(self):
        """发现 CRITICAL 问题时报 FAIL"""
        result = MockWorkflowResult(
            outputs={"analyst": MockAgentOutput(result="分析了需求")}
        )

        mock_router = MagicMock()
        mock_router.route_and_call = AsyncMock(
            return_value=MockModelResponse(
                "### [CRITICAL] logic: 死循环风险\n- 位置: src/app.py:10\n- 建议: 添加退出条件"
            )
        )
        self.layer.model_router = mock_router

        cv_result = await self.layer.validate_workflow(result, "debug")
        assert cv_result.status == ValidationStatus.FAIL
        assert len(cv_result.issues) >= 1
        assert cv_result.issues[0].severity == ValidationSeverity.CRITICAL

    @pytest.mark.asyncio
    async def test_validate_workflow_name_preserved(self):
        """工作流名称被正确保存"""
        result = MockWorkflowResult(
            outputs={"explorer": MockAgentOutput(result="探索完成")}
        )

        mock_router = MagicMock()
        mock_router.route_and_call = AsyncMock(
            return_value=MockModelResponse("### 验证结论\nPASS\n")
        )
        self.layer.model_router = mock_router

        cv_result = await self.layer.validate_workflow(result, "refactor")
        assert cv_result.workflow_name == "refactor"


# ------------------------------------------------------------------
# Mock WorkflowResult（兼容 workflow_result 的实际属性）
# ------------------------------------------------------------------


class TestWorkflowResultCompat:
    """测试与真实 WorkflowResult 的兼容性"""

    def setup_method(self):
        self.layer = CrossValidationLayer(model_router=None)

    def test_extract_outputs_from_real_workflow_result(self):
        """使用真实 WorkflowResult 结构测试"""
        # 模拟真实结构
        mock_output = MagicMock()
        mock_output.result = "executor 生成了文件"
        mock_output.artifacts = {"files": ["src/foo.py"]}

        mock_result = MagicMock()
        mock_result.workflow_id = "wf-abc"
        mock_result.outputs = {"executor": mock_output}

        outputs = self.layer._extract_outputs(mock_result)
        assert "executor" in outputs
        assert "文件" in outputs["executor"]
