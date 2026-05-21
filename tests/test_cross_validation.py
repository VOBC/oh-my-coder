"""
Tests for cross_validation.py

Tests the cross-validation layer that validates agent outputs.
All external dependencies (model router, file I/O) are mocked.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.cross_validation import (
    CrossValidationLayer,
    CrossValidationResult,
    ValidationIssue,
    ValidationSeverity,
    ValidationStatus,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_model_router():
    """Create a mock model router."""
    router = MagicMock()
    router.route_and_call = AsyncMock()
    return router


@pytest.fixture
def cv_layer(tmp_path, mock_model_router):
    """Create a CrossValidationLayer instance with temp directory."""
    layer = CrossValidationLayer(
        model_router=mock_model_router,
        state_dir=tmp_path / ".omc" / "state",
    )
    return layer


@pytest.fixture
def mock_workflow_result():
    """Create a mock workflow result with agent outputs."""
    result = MagicMock()
    result.workflow_id = "wf-12345"
    result.outputs = {
        "executor": MagicMock(result="def hello():\n    return 'world'\n", error=None),
        "verifier": MagicMock(result="All tests passed", error=None),
    }
    return result


@pytest.fixture
def mock_workflow_result_with_error():
    """Create a mock workflow result with errors."""
    result = MagicMock()
    result.workflow_id = "wf-67890"
    result.outputs = {
        "executor": MagicMock(result=None, error="SyntaxError: invalid syntax"),
    }
    return result


@pytest.fixture
def mock_workflow_result_empty():
    """Create a mock workflow result with no outputs."""
    result = MagicMock()
    result.workflow_id = "wf-empty"
    result.outputs = {}
    return result


# ---------------------------------------------------------------------------
# ValidationStatus & ValidationSeverity Enums
# ---------------------------------------------------------------------------


class TestValidationStatus:
    """Test ValidationStatus enum."""

    def test_pass_value(self):
        assert ValidationStatus.PASS.value == "pass"

    def test_fail_value(self):
        assert ValidationStatus.FAIL.value == "fail"

    def test_need_fix_value(self):
        assert ValidationStatus.NEED_FIX.value == "need_fix"

    def test_skipped_value(self):
        assert ValidationStatus.SKIPPED.value == "skipped"

    def test_all_members(self):
        assert len(ValidationStatus) == 4
        assert ValidationStatus.PASS in ValidationStatus
        assert ValidationStatus.FAIL in ValidationStatus
        assert ValidationStatus.NEED_FIX in ValidationStatus
        assert ValidationStatus.SKIPPED in ValidationStatus


class TestValidationSeverity:
    """Test ValidationSeverity enum."""

    def test_critical_value(self):
        assert ValidationSeverity.CRITICAL.value == "critical"

    def test_high_value(self):
        assert ValidationSeverity.HIGH.value == "high"

    def test_medium_value(self):
        assert ValidationSeverity.MEDIUM.value == "medium"

    def test_low_value(self):
        assert ValidationSeverity.LOW.value == "low"

    def test_all_members(self):
        assert len(ValidationSeverity) == 4


# ---------------------------------------------------------------------------
# ValidationIssue
# ---------------------------------------------------------------------------


class TestValidationIssue:
    """Test ValidationIssue dataclass."""

    def test_creation_minimal(self):
        issue = ValidationIssue(
            severity=ValidationSeverity.CRITICAL,
            category="logic",
            description="Null pointer dereference",
        )
        assert issue.severity == ValidationSeverity.CRITICAL
        assert issue.category == "logic"
        assert issue.description == "Null pointer dereference"
        assert issue.location == ""
        assert issue.suggestion == ""
        assert issue.original_agent == ""
        assert issue.evidence == ""

    def test_creation_full(self):
        issue = ValidationIssue(
            severity=ValidationSeverity.HIGH,
            category="security",
            description="SQL injection vulnerability",
            location="src/db.py:42",
            suggestion="Use parameterized queries",
            original_agent="executor",
            evidence="query = 'SELECT * FROM users WHERE id = ' + user_input",
        )
        assert issue.location == "src/db.py:42"
        assert issue.suggestion == "Use parameterized queries"
        assert issue.original_agent == "executor"

    def test_defaults(self):
        issue = ValidationIssue(
            severity=ValidationSeverity.LOW,
            category="style",
            description="Line too long",
        )
        assert issue.location == ""
        assert issue.suggestion == ""
        assert issue.original_agent == ""
        assert issue.evidence == ""


# ---------------------------------------------------------------------------
# CrossValidationResult
# ---------------------------------------------------------------------------


class TestCrossValidationResult:
    """Test CrossValidationResult dataclass and methods."""

    def test_creation_minimal(self):
        result = CrossValidationResult(
            validation_id="abc123",
            workflow_id="wf-001",
            workflow_name="test-workflow",
            status=ValidationStatus.PASS,
            agent_outputs={"agent1": "output1"},
        )
        assert result.validation_id == "abc123"
        assert result.workflow_id == "wf-001"
        assert result.workflow_name == "test-workflow"
        assert result.status == ValidationStatus.PASS
        assert result.agent_outputs == {"agent1": "output1"}
        assert result.issues == []
        assert result.raw_validation_text == ""
        assert result.execution_time == 0.0
        assert result.mode == "verify_only"
        assert result.fix_applied is False

    def test_pass_rate_no_issues(self):
        result = CrossValidationResult(
            validation_id="test",
            workflow_id="wf",
            workflow_name="test",
            status=ValidationStatus.PASS,
            agent_outputs={},
        )
        assert result.pass_rate == "100%"

    def test_pass_rate_critical_issues(self):
        result = CrossValidationResult(
            validation_id="test",
            workflow_id="wf",
            workflow_name="test",
            status=ValidationStatus.FAIL,
            agent_outputs={},
            issues=[
                ValidationIssue(
                    severity=ValidationSeverity.CRITICAL,
                    category="logic",
                    description="Critical bug",
                ),
            ],
        )
        assert result.pass_rate == "0%"

    def test_pass_rate_high_issues(self):
        result = CrossValidationResult(
            validation_id="test",
            workflow_id="wf",
            workflow_name="test",
            status=ValidationStatus.NEED_FIX,
            agent_outputs={},
            issues=[
                ValidationIssue(
                    severity=ValidationSeverity.HIGH,
                    category="security",
                    description="Security issue",
                ),
            ],
        )
        assert result.pass_rate == "50%"

    def test_pass_rate_medium_issues(self):
        result = CrossValidationResult(
            validation_id="test",
            workflow_id="wf",
            workflow_name="test",
            status=ValidationStatus.PASS,
            agent_outputs={},
            issues=[
                ValidationIssue(
                    severity=ValidationSeverity.MEDIUM,
                    category="style",
                    description="Style issue",
                ),
            ],
        )
        assert result.pass_rate == "80%"

    def test_pass_rate_low_issues(self):
        result = CrossValidationResult(
            validation_id="test",
            workflow_id="wf",
            workflow_name="test",
            status=ValidationStatus.PASS,
            agent_outputs={},
            issues=[
                ValidationIssue(
                    severity=ValidationSeverity.LOW,
                    category="style",
                    description="Minor issue",
                ),
            ],
        )
        assert result.pass_rate == "80%"

    def test_pass_rate_multiple_issues_mixed(self):
        result = CrossValidationResult(
            validation_id="test",
            workflow_id="wf",
            workflow_name="test",
            status=ValidationStatus.NEED_FIX,
            agent_outputs={},
            issues=[
                ValidationIssue(
                    severity=ValidationSeverity.HIGH,
                    category="security",
                    description="High issue",
                ),
                ValidationIssue(
                    severity=ValidationSeverity.LOW,
                    category="style",
                    description="Low issue",
                ),
            ],
        )
        assert result.pass_rate == "50%"

    def test_to_summary_pass(self):
        result = CrossValidationResult(
            validation_id="abc12345",
            workflow_id="wf-001",
            workflow_name="my-workflow",
            status=ValidationStatus.PASS,
            agent_outputs={"agent1": "output"},
        )
        summary = result.to_summary()
        assert "🔍 交叉验证报告" in summary
        assert "abc12345" in summary
        assert "my-workflow" in summary
        assert "PASS" in summary
        assert "✅ 未发现明显问题" in summary

    def test_to_summary_with_issues(self):
        result = CrossValidationResult(
            validation_id="def67890",
            workflow_id="wf-002",
            workflow_name="buggy-workflow",
            status=ValidationStatus.FAIL,
            agent_outputs={"agent1": "output"},
            issues=[
                ValidationIssue(
                    severity=ValidationSeverity.CRITICAL,
                    category="logic",
                    description="Null pointer exception when user is None",
                    location="src/main.py:42",
                    suggestion="Add null check before accessing user properties",
                ),
            ],
        )
        summary = result.to_summary()
        assert "🔍 交叉验证报告" in summary
        assert "FAIL" in summary
        assert "critical" in summary  # severity.value is lowercase
        assert "logic" in summary
        assert "Null pointer exception" in summary
        assert "src/main.py:42" in summary

    def test_to_summary_with_suggestions(self):
        result = CrossValidationResult(
            validation_id="test",
            workflow_id="wf",
            workflow_name="test",
            status=ValidationStatus.NEED_FIX,
            agent_outputs={},
            issues=[
                ValidationIssue(
                    severity=ValidationSeverity.HIGH,
                    category="security",
                    description="SQL injection risk",
                    suggestion="Use prepared statements",
                ),
                ValidationIssue(
                    severity=ValidationSeverity.MEDIUM,
                    category="performance",
                    description="N+1 query problem",
                    suggestion="Use select_related or prefetch_related",
                ),
            ],
        )
        summary = result.to_summary()
        assert "修复建议" in summary
        assert "SQL injection risk" in summary
        assert "Use prepared statements" in summary

    def test_to_summary_table_format(self):
        result = CrossValidationResult(
            validation_id="test",
            workflow_id="wf",
            workflow_name="test",
            status=ValidationStatus.FAIL,
            agent_outputs={},
            issues=[
                ValidationIssue(
                    severity=ValidationSeverity.CRITICAL,
                    category="security",
                    description="Very long description that should be truncated in table",
                ),
            ],
        )
        summary = result.to_summary()
        # Check table format
        assert "| 项目 | 值 |" in summary
        assert "| 严重性 | 分类 | 描述 | 位置 |" in summary


# ---------------------------------------------------------------------------
# CrossValidationLayer - Initialization
# ---------------------------------------------------------------------------


class TestCrossValidationLayerInit:
    """Test CrossValidationLayer initialization."""

    def test_init_with_default_state_dir(self, mock_model_router):
        layer = CrossValidationLayer(model_router=mock_model_router)
        assert layer.model_router == mock_model_router
        assert layer.state_dir == Path(".omc/state").resolve()
        assert layer._cv_dir == Path(".omc/state/cross_validation").resolve()

    def test_init_with_custom_state_dir(self, tmp_path, mock_model_router):
        custom_dir = tmp_path / "custom" / "state"
        layer = CrossValidationLayer(
            model_router=mock_model_router,
            state_dir=custom_dir,
        )
        assert layer.state_dir == custom_dir.resolve()
        assert layer._cv_dir == custom_dir.resolve() / "cross_validation"

    def test_init_creates_cv_dir_on_save(self, tmp_path, mock_model_router):
        state_dir = tmp_path / ".omc" / "state"
        layer = CrossValidationLayer(
            model_router=mock_model_router,
            state_dir=state_dir,
        )
        # Directory should not exist yet
        assert not layer._cv_dir.exists()

        # Create a result and save it
        result = CrossValidationResult(
            validation_id="test",
            workflow_id="wf",
            workflow_name="test",
            status=ValidationStatus.PASS,
            agent_outputs={},
        )
        layer._save_result(result)
        assert layer._cv_dir.exists()


# ---------------------------------------------------------------------------
# CrossValidationLayer - _extract_outputs
# ---------------------------------------------------------------------------


class TestExtractOutputs:
    """Test _extract_outputs method."""

    def test_extract_with_results(self, cv_layer):
        workflow_result = MagicMock()
        workflow_result.outputs = {
            "agent1": MagicMock(result="output1", error=None),
            "agent2": MagicMock(result="output2", error=None),
        }
        outputs = cv_layer._extract_outputs(workflow_result)
        assert len(outputs) == 2
        assert "agent1" in outputs
        assert "agent2" in outputs
        assert outputs["agent1"] == "output1"[:3000]
        assert outputs["agent2"] == "output2"[:3000]

    def test_extract_truncates_long_output(self, cv_layer):
        workflow_result = MagicMock()
        long_output = "x" * 5000
        workflow_result.outputs = {
            "agent1": MagicMock(result=long_output, error=None),
        }
        outputs = cv_layer._extract_outputs(workflow_result)
        assert len(outputs["agent1"]) == 3000

    def test_extract_with_errors(self, cv_layer):
        workflow_result = MagicMock()
        workflow_result.outputs = {
            "agent1": MagicMock(result=None, error="Some error occurred"),
        }
        outputs = cv_layer._extract_outputs(workflow_result)
        assert len(outputs) == 1
        assert "[ERROR] Some error occurred" in outputs["agent1"]

    def test_extract_empty_outputs(self, cv_layer):
        workflow_result = MagicMock()
        workflow_result.outputs = {}
        outputs = cv_layer._extract_outputs(workflow_result)
        assert outputs == {}

    def test_extract_none_output(self, cv_layer):
        """When result is None and no error, output is not extracted."""
        workflow_result = MagicMock()
        workflow_result.outputs = {
            "agent1": MagicMock(result=None, error=None),
        }
        outputs = cv_layer._extract_outputs(workflow_result)
        # _extract_outputs only extracts when result is truthy
        assert len(outputs) == 0


# ---------------------------------------------------------------------------
# CrossValidationLayer - _build_validation_messages
# ---------------------------------------------------------------------------


class TestBuildValidationMessages:
    """Test _build_validation_messages method."""

    def test_build_messages(self, cv_layer):
        agent_outputs = {
            "executor": "def hello():\n    return 'world'",
            "verifier": "All tests passed",
        }
        messages = cv_layer._build_validation_messages("test-workflow", agent_outputs)
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        content = messages[0]["content"]
        assert "test-workflow" in content
        assert "executor" in content
        assert "verifier" in content
        assert "def hello()" in content
        assert "All tests passed" in content

    def test_build_messages_empty_outputs(self, cv_layer):
        messages = cv_layer._build_validation_messages("test-workflow", {})
        assert len(messages) == 1
        content = messages[0]["content"]
        assert "test-workflow" in content

    def test_build_messages_special_chars(self, cv_layer):
        agent_outputs = {
            "agent1": "print('hello\\nworld')",
        }
        messages = cv_layer._build_validation_messages("test", agent_outputs)
        content = messages[0]["content"]
        assert "print('hello" in content


# ---------------------------------------------------------------------------
# CrossValidationLayer - _build_validation_prompt (alias)
# ---------------------------------------------------------------------------


class TestBuildValidationPrompt:
    """Test _build_validation_prompt method (alias)."""

    def test_alias_works(self, cv_layer):
        agent_outputs = {"agent1": "output1"}
        result1 = cv_layer._build_validation_messages("test", agent_outputs)
        result2 = cv_layer._build_validation_prompt("test", agent_outputs)
        assert result1 == result2


# ---------------------------------------------------------------------------
# CrossValidationLayer - _parse_severity
# ---------------------------------------------------------------------------


class TestParseSeverity:
    """Test _parse_severity method."""

    def test_parse_critical_english(self, cv_layer):
        assert cv_layer._parse_severity("critical") == ValidationSeverity.CRITICAL
        assert cv_layer._parse_severity("CRITICAL") == ValidationSeverity.CRITICAL
        assert cv_layer._parse_severity("[CRITICAL]") == ValidationSeverity.CRITICAL

    def test_parse_critical_chinese(self, cv_layer):
        assert cv_layer._parse_severity("严重") == ValidationSeverity.CRITICAL

    def test_parse_high_english(self, cv_layer):
        assert cv_layer._parse_severity("high") == ValidationSeverity.HIGH
        assert cv_layer._parse_severity("HIGH") == ValidationSeverity.HIGH

    def test_parse_high_chinese(self, cv_layer):
        assert cv_layer._parse_severity("高") == ValidationSeverity.HIGH

    def test_parse_medium_english(self, cv_layer):
        assert cv_layer._parse_severity("medium") == ValidationSeverity.MEDIUM
        assert cv_layer._parse_severity("MEDIUM") == ValidationSeverity.MEDIUM

    def test_parse_medium_chinese(self, cv_layer):
        assert cv_layer._parse_severity("中") == ValidationSeverity.MEDIUM

    def test_parse_low_default(self, cv_layer):
        assert cv_layer._parse_severity("low") == ValidationSeverity.LOW
        assert cv_layer._parse_severity("unknown") == ValidationSeverity.LOW
        assert cv_layer._parse_severity("") == ValidationSeverity.LOW


# ---------------------------------------------------------------------------
# CrossValidationLayer - _parse_validation_output
# ---------------------------------------------------------------------------


class TestParseValidationOutput:
    """Test _parse_validation_output method."""

    def test_parse_empty_text(self, cv_layer):
        issues = cv_layer._parse_validation_output("")
        assert issues == []

    def test_parse_none_text(self, cv_layer):
        issues = cv_layer._parse_validation_output(None)
        assert issues == []

    def test_parse_pass_no_issues(self, cv_layer):
        text = "PASS\n\nNo issues found."
        issues = cv_layer._parse_validation_output(text)
        assert issues == []

    def test_parse_single_critical_issue(self, cv_layer):
        text = """### [CRITICAL] logic: Null pointer dereference
- 位置: src/main.py:42
- 证据: if user.profile is None: ...
- 建议: Add null check
"""
        issues = cv_layer._parse_validation_output(text)
        assert len(issues) == 1
        assert issues[0].severity == ValidationSeverity.CRITICAL
        assert issues[0].category == "logic"
        assert "Null pointer" in issues[0].description
        assert issues[0].location == "src/main.py:42"
        assert "Add null check" in issues[0].suggestion

    def test_parse_multiple_issues(self, cv_layer):
        text = """### [CRITICAL] security: SQL injection
- 位置: src/db.py:15
- 证据: query = "SELECT * FROM users WHERE id = " + user_id
- 建议: Use parameterized queries

### [HIGH] performance: N+1 query
- 位置: src/views.py:78
- 证据: for user in users: print(user.profile.name)
- 建议: Use select_related
"""
        issues = cv_layer._parse_validation_output(text)
        assert len(issues) == 2
        assert issues[0].severity == ValidationSeverity.CRITICAL
        assert issues[1].severity == ValidationSeverity.HIGH

    def test_parse_issue_without_location(self, cv_layer):
        text = """### [MEDIUM] style: Line too long
- 建议: Break line
"""
        issues = cv_layer._parse_validation_output(text)
        assert len(issues) == 1
        assert issues[0].location == ""
        assert issues[0].suggestion == "Break line"

    def test_parse_issue_chinese_severity(self, cv_layer):
        text = """### [严重] logic: 空指针
- 位置: main.py:10
"""
        issues = cv_layer._parse_validation_output(text)
        assert len(issues) == 1
        assert issues[0].severity == ValidationSeverity.CRITICAL

    def test_parse_issue_with_colon_in_description(self, cv_layer):
        text = """### [LOW] style: Function name: should be snake_case
- 位置: utils.py:5
"""
        issues = cv_layer._parse_validation_output(text)
        assert len(issues) == 1
        assert "Function name" in issues[0].description
        assert "should be snake_case" in issues[0].description

    def test_parse_malformed_header_no_bracket(self, cv_layer):
        text = """### CRITICAL: logic: issue
- 位置: file.py:1
"""
        issues = cv_layer._parse_validation_output(text)
        # Should not parse (no brackets)
        assert len(issues) == 0

    def test_parse_preserves_last_issue(self, cv_layer):
        text = """### [HIGH] security: XSS vulnerability
- 位置: templates/home.html:23
- 证据: {{ user.bio|safe }}
- 建议: Remove |safe or escape
"""
        issues = cv_layer._parse_validation_output(text)
        assert len(issues) == 1
        assert issues[0].evidence == "{{ user.bio|safe }}"


# ---------------------------------------------------------------------------
# CrossValidationLayer - _determine_status
# ---------------------------------------------------------------------------


class TestDetermineStatus:
    """Test _determine_status method."""

    def test_no_issues(self, cv_layer):
        status = cv_layer._determine_status([])
        assert status == ValidationStatus.PASS

    def test_critical_issue(self, cv_layer):
        issues = [
            ValidationIssue(
                severity=ValidationSeverity.CRITICAL,
                category="logic",
                description="Bug",
            ),
        ]
        status = cv_layer._determine_status(issues)
        assert status == ValidationStatus.FAIL

    def test_high_issue(self, cv_layer):
        issues = [
            ValidationIssue(
                severity=ValidationSeverity.HIGH,
                category="security",
                description="Issue",
            ),
        ]
        status = cv_layer._determine_status(issues)
        assert status == ValidationStatus.NEED_FIX

    def test_medium_issue(self, cv_layer):
        issues = [
            ValidationIssue(
                severity=ValidationSeverity.MEDIUM,
                category="style",
                description="Issue",
            ),
        ]
        status = cv_layer._determine_status(issues)
        assert status == ValidationStatus.PASS

    def test_low_issue(self, cv_layer):
        issues = [
            ValidationIssue(
                severity=ValidationSeverity.LOW,
                category="style",
                description="Issue",
            ),
        ]
        status = cv_layer._determine_status(issues)
        assert status == ValidationStatus.PASS

    def test_mixed_issues_critical_priority(self, cv_layer):
        issues = [
            ValidationIssue(
                severity=ValidationSeverity.LOW,
                category="style",
                description="Low",
            ),
            ValidationIssue(
                severity=ValidationSeverity.CRITICAL,
                category="logic",
                description="Critical",
            ),
        ]
        status = cv_layer._determine_status(issues)
        assert status == ValidationStatus.FAIL

    def test_mixed_issues_high_no_critical(self, cv_layer):
        issues = [
            ValidationIssue(
                severity=ValidationSeverity.LOW,
                category="style",
                description="Low",
            ),
            ValidationIssue(
                severity=ValidationSeverity.HIGH,
                category="security",
                description="High",
            ),
        ]
        status = cv_layer._determine_status(issues)
        assert status == ValidationStatus.NEED_FIX


# ---------------------------------------------------------------------------
# CrossValidationLayer - _save_result
# ---------------------------------------------------------------------------


class TestSaveResult:
    """Test _save_result method."""

    def test_save_result_creates_file(self, cv_layer):
        result = CrossValidationResult(
            validation_id="abc12345",
            workflow_id="wf-001",
            workflow_name="test-workflow",
            status=ValidationStatus.PASS,
            agent_outputs={"agent1": "output1"},
            issues=[],
            execution_time=1.5,
            mode="verify_only",
        )
        cv_layer._save_result(result)

        # Check file exists
        result_file = cv_layer._cv_dir / "abc12345.json"
        assert result_file.exists()

        # Check content
        with open(result_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["validation_id"] == "abc12345"
        assert data["workflow_id"] == "wf-001"
        assert data["status"] == "pass"
        assert data["execution_time"] == 1.5
        assert data["mode"] == "verify_only"
        assert data["pass_rate"] == "100%"

    def test_save_result_with_issues(self, cv_layer):
        issues = [
            ValidationIssue(
                severity=ValidationSeverity.CRITICAL,
                category="logic",
                description="Null pointer",
                location="main.py:42",
                suggestion="Add check",
            ),
        ]
        result = CrossValidationResult(
            validation_id="def67890",
            workflow_id="wf-002",
            workflow_name="buggy-workflow",
            status=ValidationStatus.FAIL,
            agent_outputs={"agent1": "output"},
            issues=issues,
            execution_time=2.3,
        )
        cv_layer._save_result(result)

        result_file = cv_layer._cv_dir / "def67890.json"
        assert result_file.exists()

        with open(result_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert len(data["issues"]) == 1
        assert data["issues"][0]["severity"] == "critical"
        assert data["issues"][0]["category"] == "logic"
        assert data["issues"][0]["description"] == "Null pointer"
        assert data["issues"][0]["location"] == "main.py:42"

    def test_save_result_creates_directory(self, tmp_path, mock_model_router):
        state_dir = tmp_path / "new_state"
        layer = CrossValidationLayer(
            model_router=mock_model_router,
            state_dir=state_dir,
        )
        result = CrossValidationResult(
            validation_id="test",
            workflow_id="wf",
            workflow_name="test",
            status=ValidationStatus.PASS,
            agent_outputs={},
        )
        layer._save_result(result)
        assert layer._cv_dir.exists()
        assert (layer._cv_dir / "test.json").exists()


# ---------------------------------------------------------------------------
# CrossValidationLayer - call_model
# ---------------------------------------------------------------------------


class TestCallModel:
    """Test call_model method."""

    @pytest.mark.asyncio
    async def test_call_model_delegates_to_router(self, cv_layer):
        cv_layer.model_router.route_and_call.return_value = "model response"
        result = await cv_layer.call_model(
            task_type="code_review",
            messages=[{"role": "user", "content": "test"}],
            complexity="high",
            use_cache=False,
        )
        assert result == "model response"
        cv_layer.model_router.route_and_call.assert_called_once_with(
            task_type="code_review",
            messages=[{"role": "user", "content": "test"}],
            complexity="high",
            use_cache=False,
        )


# ---------------------------------------------------------------------------
# CrossValidationLayer - validate_workflow (async)
# ---------------------------------------------------------------------------


class TestValidateWorkflow:
    """Test validate_workflow method."""

    @pytest.mark.asyncio
    async def test_validate_workflow_skipped_no_outputs(self, cv_layer, mock_workflow_result_empty):
        result = await cv_layer.validate_workflow(
            mock_workflow_result_empty,
            "test-workflow",
        )
        assert result.status == ValidationStatus.SKIPPED
        assert result.issues == []
        assert result.agent_outputs == {}

    @pytest.mark.asyncio
    async def test_validate_workflow_pass(self, cv_layer, mock_workflow_result):
        # Mock model response
        mock_response = MagicMock()
        mock_response.content = "PASS\n\nNo issues found in the code."
        cv_layer.model_router.route_and_call.return_value = mock_response

        result = await cv_layer.validate_workflow(
            mock_workflow_result,
            "test-workflow",
        )
        assert result.status == ValidationStatus.PASS
        assert len(result.issues) == 0
        assert result.validation_id != ""
        assert result.execution_time >= 0
        assert result.mode == "verify_only"

    @pytest.mark.asyncio
    async def test_validate_workflow_with_issues(self, cv_layer, mock_workflow_result):
        # Mock model response with issues
        mock_response = MagicMock()
        mock_response.content = """FAIL

### [CRITICAL] logic: Null pointer dereference
- 位置: src/main.py:42
- 证据: if user.profile is None: ...
- 建议: Add null check
"""
        cv_layer.model_router.route_and_call.return_value = mock_response

        result = await cv_layer.validate_workflow(
            mock_workflow_result,
            "test-workflow",
        )
        assert result.status == ValidationStatus.FAIL
        assert len(result.issues) == 1
        assert result.issues[0].severity == ValidationSeverity.CRITICAL

    @pytest.mark.asyncio
    async def test_validate_workflow_auto_fix_mode(self, cv_layer, mock_workflow_result):
        mock_response = MagicMock()
        mock_response.content = "PASS"
        cv_layer.model_router.route_and_call.return_value = mock_response

        result = await cv_layer.validate_workflow(
            mock_workflow_result,
            "test-workflow",
            mode="auto_fix",
        )
        assert result.mode == "auto_fix"

    @pytest.mark.asyncio
    async def test_validate_workflow_model_exception(self, cv_layer, mock_workflow_result):
        # Model raises exception
        cv_layer.model_router.route_and_call.side_effect = Exception("Model error")

        result = await cv_layer.validate_workflow(
            mock_workflow_result,
            "test-workflow",
        )
        assert result.status == ValidationStatus.SKIPPED
        assert result.raw_validation_text == ""

    @pytest.mark.asyncio
    async def test_validate_workflow_model_returns_none(self, cv_layer, mock_workflow_result):
        # Model returns None
        cv_layer.model_router.route_and_call.return_value = None

        result = await cv_layer.validate_workflow(
            mock_workflow_result,
            "test-workflow",
        )
        assert result.status == ValidationStatus.PASS  # No issues parsed
        assert result.raw_validation_text == ""

    @pytest.mark.asyncio
    async def test_validate_workflow_saves_result(self, cv_layer, mock_workflow_result, tmp_path):
        mock_response = MagicMock()
        mock_response.content = "PASS"
        cv_layer.model_router.route_and_call.return_value = mock_response

        result = await cv_layer.validate_workflow(
            mock_workflow_result,
            "test-workflow",
        )
        # Check that result was saved
        result_file = cv_layer._cv_dir / f"{result.validation_id}.json"
        assert result_file.exists()

    @pytest.mark.asyncio
    async def test_validate_workflow_with_error_outputs(self, cv_layer, mock_workflow_result_with_error):
        mock_response = MagicMock()
        mock_response.content = "PASS"
        cv_layer.model_router.route_and_call.return_value = mock_response

        result = await cv_layer.validate_workflow(
            mock_workflow_result_with_error,
            "test-workflow",
        )
        # Should still validate (error outputs are included)
        assert result.agent_outputs != {}
        assert any("[ERROR]" in output for output in result.agent_outputs.values())


# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------


class TestCrossValidationIntegration:
    """Integration tests for cross validation flow."""

    @pytest.mark.asyncio
    async def test_full_flow_with_multiple_agents(self, cv_layer):
        """Test validation with multiple agent outputs."""
        workflow_result = MagicMock()
        workflow_result.workflow_id = "wf-integration"
        workflow_result.outputs = {
            "explorer": MagicMock(
                result="Found 10 Python files\nFound 2 config files",
                error=None,
            ),
            "executor": MagicMock(
                result="def add(a, b):\n    return a + b\n\nresult = add(1, 2)",
                error=None,
            ),
            "verifier": MagicMock(
                result="Tests passed: 5/5",
                error=None,
            ),
        }

        mock_response = MagicMock()
        mock_response.content = """### [MEDIUM] completeness: Missing edge case handling
- 位置: general
- 证据: No handling for None inputs
- 建议: Add input validation

### [LOW] style: Consider adding type hints
- 位置: general
- 证据: def add(a, b) has no type hints
- 建议: Add TypeVar or type annotations
"""
        cv_layer.model_router.route_and_call.return_value = mock_response

        result = await cv_layer.validate_workflow(
            workflow_result,
            "integration-test",
        )
        assert result.status == ValidationStatus.PASS  # No critical/high issues
        assert len(result.issues) == 2
        assert result.issues[0].severity == ValidationSeverity.MEDIUM
        assert result.issues[1].severity == ValidationSeverity.LOW
        assert result.pass_rate == "80%"

    def test_result_to_summary_format(self):
        """Test that to_summary() produces valid markdown."""
        result = CrossValidationResult(
            validation_id="abc123",
            workflow_id="wf-001",
            workflow_name="test",
            status=ValidationStatus.FAIL,
            agent_outputs={"agent1": "output"},
            issues=[
                ValidationIssue(
                    severity=ValidationSeverity.CRITICAL,
                    category="security",
                    description="SQL injection in user input handling",
                    location="src/handlers.py:89",
                    suggestion="Use ORM or parameterized queries",
                ),
                ValidationIssue(
                    severity=ValidationSeverity.HIGH,
                    category="logic",
                    description="Race condition in concurrent updates",
                    location="src/models.py:156",
                    suggestion="Add locking mechanism",
                ),
            ],
            execution_time=3.7,
        )
        summary = result.to_summary()

        # Check markdown table format
        lines = summary.split("\n")
        assert any("| 项目 | 值 |" in line for line in lines)
        assert any("SQL injection" in line for line in lines)
        assert any("Race condition" in line for line in lines)
        assert "3.7" in summary  # execution time
