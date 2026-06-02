"""Batch 2 tests for src.web.app.py - targeting 5 simple functions."""

import pytest

# Prevent concurrent execution - global singleton pollution
pytestmark = pytest.mark.xdist_group("web_app")


class TestGenerateTaskSummary:
    """Tests for _generate_task_summary function."""

    def test_build_workflow_deepseek(self):
        """Test build workflow with deepseek model."""
        from src.web.app import _generate_task_summary
        task = {
            "workflow": "build",
            "model": "deepseek",
            "project_path": "./my-project",
            "target_type": "local"
        }
        result = _generate_task_summary(task)
        assert "完整开发" in result
        assert "DeepSeek V4" in result
        assert "./my-project" in result

    def test_review_workflow_glm(self):
        """Test review workflow with glm model."""
        from src.web.app import _generate_task_summary
        task = {
            "workflow": "review",
            "model": "glm-4-flash",
            "project_path": "https://github.com/user/repo",
            "target_type": "github"
        }
        result = _generate_task_summary(task)
        assert "代码审查" in result
        assert "GLM-4.7-Flash" in result
        assert "GitHub 仓库" in result

    def test_debug_workflow_unknown_model(self):
        """Test debug workflow with unknown model."""
        from src.web.app import _generate_task_summary
        task = {
            "workflow": "debug",
            "model": "unknown-model",
            "project_path": "https://example.com",
            "target_type": "url"
        }
        result = _generate_task_summary(task)
        assert "调试修复" in result
        assert "unknown-model" in result
        assert "网页" in result


class TestDetectWorkflow:
    """Tests for _detect_workflow function."""

    def test_detect_build_keywords(self):
        """Test detection of build workflow."""
        from src.web.app import _detect_workflow
        assert _detect_workflow("创建一个新功能") == "build"
        assert _detect_workflow("build a feature") == "build"
        assert _detect_workflow("开发新模块") == "build"

    def test_detect_review_keywords(self):
        """Test detection of review workflow."""
        from src.web.app import _detect_workflow
        assert _detect_workflow("审查代码") == "review"
        assert _detect_workflow("review my code") == "review"
        assert _detect_workflow("代码审查") == "review"

    def test_detect_debug_keywords(self):
        """Test detection of debug workflow."""
        from src.web.app import _detect_workflow
        assert _detect_workflow("修复bug") == "debug"
        assert _detect_workflow("debug this issue") == "debug"
        assert _detect_workflow("调试问题") == "debug"

    def test_detect_test_keywords(self):
        """Test detection of test workflow."""
        from src.web.app import _detect_workflow
        assert _detect_workflow("添加测试") == "test"
        assert _detect_workflow("test my code") == "test"
        assert _detect_workflow("单元测试") == "test"

    def test_default_to_build(self):
        """Test default workflow is build."""
        from src.web.app import _detect_workflow
        assert _detect_workflow("random message") == "build"
        assert _detect_workflow("") == "build"


class TestDetectModel:
    """Tests for _detect_model function."""

    def test_detect_deepseek(self):
        """Test detection of deepseek model."""
        from src.web.app import _detect_model
        assert _detect_model("使用 deepseek") == "deepseek"
        assert _detect_model("deepseek v4") == "deepseek"

    def test_detect_glm(self):
        """Test detection of glm model."""
        from src.web.app import _detect_model
        assert _detect_model("使用 glm") == "glm-4-flash"
        assert _detect_model("智谱 glm") == "glm-4-flash"

    def test_detect_miniMax(self):
        """Test detection of MiniMax model."""
        from src.web.app import _detect_model
        assert _detect_model("使用 minimax") == "MiniMax-Text-01"
        assert _detect_model("mimo model") == "MiniMax-Text-01"

    def test_detect_moonshot(self):
        """Test detection of moonshot model."""
        from src.web.app import _detect_model
        assert _detect_model("使用 kimi") == "moonshot-v1-128k"
        assert _detect_model("128k context") == "moonshot-v1-128k"

    def test_default_to_deepseek(self):
        """Test default model is deepseek."""
        from src.web.app import _detect_model
        assert _detect_model("random message") == "deepseek"
        assert _detect_model("") == "deepseek"


class TestDetectTargetTypeFromMessage:
    """Tests for _detect_target_type_from_message function."""

    def test_github_url(self):
        """Test detection of GitHub URL."""
        from src.web.app import _detect_target_type_from_message
        target_type, path = _detect_target_type_from_message("检查 https://github.com/user/repo")
        assert target_type == "github"
        assert "github.com/user/repo" in path

    def test_http_url(self):
        """Test detection of HTTP URL."""
        from src.web.app import _detect_target_type_from_message
        target_type, path = _detect_target_type_from_message("分析 https://example.com")
        assert target_type == "url"
        assert "https://example.com" in path

    def test_local_path_with_dot(self):
        """Test detection of local path starting with dot."""
        from src.web.app import _detect_target_type_from_message
        target_type, path = _detect_target_type_from_message("分析 ./my-project")
        assert target_type == "local"
        assert path == "./my-project"

    def test_local_path_with_tilde(self):
        """Test detection of local path starting with tilde."""
        from src.web.app import _detect_target_type_from_message
        target_type, path = _detect_target_type_from_message("检查 ~/projects/app")
        assert target_type == "local"
        assert path == "~/projects/app"

    def test_no_path_detected(self):
        """Test when no path is detected."""
        from src.web.app import _detect_target_type_from_message
        target_type, path = _detect_target_type_from_message("帮我写代码")
        assert target_type == "local"
        assert path == "."


class TestTaskManagerGetQueue:
    """Tests for TaskManager.get_queue method."""

    def test_get_existing_queue(self):
        """Test getting existing queue."""
        from src.web.app import task_manager
        # Create a task first
        task_id = task_manager.create_task("test", "deepseek", "build", ".")
        queue = task_manager.get_queue(task_id)
        assert queue is not None
        # Cleanup
        task_manager.delete_task(task_id)

    def test_get_nonexistent_queue(self):
        """Test getting queue for nonexistent task."""
        from src.web.app import task_manager
        queue = task_manager.get_queue("nonexistent-id")
        assert queue is None
