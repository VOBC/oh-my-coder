"""Tests for src/agents/executor.py - ExecutorAgent - additional coverage tests.

Covers remaining uncovered lines:
- _run async method (lines 154-178)
- _find_relevant_files no-walk fallback (lines 235, 237, 239)
- _build_implementation_hint fastapi/react hints (lines 244-253)
- _extract_code_blocks empty path edge case (lines 336, 338-341)
- _resolve_dependencies missing deps branch (line 391)
- _try_format_code js/ts/go formatters (lines 451, 478)
- _try_run_tests exception handler (lines 547-548)
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.agents.base import AgentContext, AgentStatus
from src.agents.executor import ExecutorAgent


@pytest.fixture
def agent():
    return ExecutorAgent()


# ── _run async method ────────────────────────────────────────────

@pytest.mark.asyncio
class TestRunAsync:
    async def test_run_calls_model(self, agent, tmp_path):
        """Normal path: _run calls call_model and returns content."""
        ctx = MagicMock(spec=AgentContext)
        ctx.project_path = tmp_path
        ctx.task_description = "实现一个计算器"
        ctx.relevant_files = []
        ctx.previous_outputs = {}
        prompt = [{"role": "system", "content": agent.system_prompt}]

        mock_response = MagicMock()
        mock_response.content = "好的，我来实现代码\n\n```python:src/calc.py\nclass Calc:\n    pass\n```"

        async def mock_call(**kwargs):
            return mock_response

        with patch.object(agent, "call_model", side_effect=mock_call):
            result = await agent._run(ctx, prompt)
        assert result == mock_response.content

    async def test_run_injects_previous_outputs(self, agent, tmp_path):
        """Previous outputs (architect/analyst) are injected into prompt."""
        ctx = MagicMock(spec=AgentContext)
        ctx.project_path = tmp_path
        ctx.task_description = "实现功能"
        ctx.relevant_files = None
        arch_out = MagicMock()
        arch_out.result = "架构方案 v1"
        ctx.previous_outputs = {"architect": arch_out}
        prompt = [{"role": "system", "content": agent.system_prompt}]

        mock_response = MagicMock()
        mock_response.content = "done"
        call_tracker = []

        async def mock_call(**kwargs):
            call_tracker.append(kwargs)
            return mock_response

        with patch.object(agent, "call_model", side_effect=mock_call):
            await agent._run(ctx, prompt)

        assert len(call_tracker) == 1
        messages = call_tracker[0]["messages"]
        assert any("架构方案" in m.content for m in messages)

    async def test_run_with_relevant_files(self, agent, tmp_path):
        """When relevant_files is not None, they are injected."""
        test_file = tmp_path / "existing.py"
        test_file.write_text("existing code", encoding="utf-8")
        ctx = MagicMock(spec=AgentContext)
        ctx.project_path = tmp_path
        ctx.task_description = "添加新功能"
        ctx.relevant_files = [test_file]
        ctx.previous_outputs = {}
        prompt = [{"role": "system", "content": agent.system_prompt}]

        mock_response = MagicMock()
        mock_response.content = "done"
        call_tracker = []

        async def mock_call(**kwargs):
            call_tracker.append(kwargs)
            return mock_response

        with patch.object(agent, "call_model", side_effect=mock_call):
            await agent._run(ctx, prompt)

        assert len(call_tracker) == 1
        messages = call_tracker[0]["messages"]
        assert any("existing.py" in m.content for m in messages)

    async def test_run_builds_implementation_hint(self, agent, tmp_path):
        """Implementation hint is appended to prompt."""
        ctx = MagicMock(spec=AgentContext)
        ctx.project_path = tmp_path
        ctx.task_description = "实现功能"
        ctx.relevant_files = None
        ctx.previous_outputs = {}
        prompt = [{"role": "system", "content": agent.system_prompt}]

        mock_response = MagicMock()
        mock_response.content = "done"
        call_tracker = []

        async def mock_call(**kwargs):
            call_tracker.append(kwargs)
            return mock_response

        with patch.object(agent, "call_model", side_effect=mock_call):
            await agent._run(ctx, prompt)

        assert len(call_tracker) == 1
        messages = call_tracker[0]["messages"]
        user_msgs = [m for m in messages if m.role == "user"]
        assert any("实现要求" in m.content for m in user_msgs)


# ── _find_relevant_files ────────────────────────────────────────

class TestFindRelevantFilesUncovered:
    def test_no_walk_attribute(self, agent, tmp_path):
        """Fallback when Path has no walk() attribute."""
        # Create a mock path without walk
        mock_path = MagicMock(spec=Path)
        mock_path.__str__ = lambda self: str(tmp_path)
        # Remove walk attribute
        del mock_path.walk

        files = agent._find_relevant_files(mock_path, "用户登录认证")
        assert files == []

    def test_walk_returns_empty(self, agent, tmp_path):
        """When project_path.walk() yields nothing, returns empty list."""
        mock_path = MagicMock()
        mock_path.walk.return_value = iter([])  # empty iterator

        files = agent._find_relevant_files(mock_path, "用户登录认证")
        assert files == []

    def test_database_keyword(self, agent, tmp_path):
        """Database keyword matches 'model', 'db', 'schema' files."""
        mock_path = MagicMock()
        mock_path.__truediv__ = lambda self, x: tmp_path / x
        mock_path.walk.return_value = iter([
            (tmp_path, [], ["model.py", "db_utils.py", "schema.sql"])
        ])

        files = agent._find_relevant_files(mock_path, "数据库设计")
        # Should match files with db/model/schema patterns
        assert len(files) >= 1


# ── _build_implementation_hint ──────────────────────────────────

class TestBuildImplementationHintUncovered:
    def test_fastapi_hint_added(self, agent):
        """FastAPI keyword triggers FastAPI framework hint."""
        ctx = MagicMock()
        ctx.task_description = "用 FastAPI 写一个 Web 服务"
        hint = agent._build_implementation_hint(ctx)
        assert "FastAPI" in hint

    def test_python_hint_added(self, agent):
        """Python keyword triggers FastAPI hint."""
        ctx = MagicMock()
        ctx.task_description = "python 脚本"
        hint = agent._build_implementation_hint(ctx)
        assert "FastAPI" in hint

    def test_react_hint_added(self, agent):
        """React keyword triggers React framework hint."""
        ctx = MagicMock()
        ctx.task_description = "React 组件开发"
        hint = agent._build_implementation_hint(ctx)
        assert "React" in hint

    def test_frontend_hint_added(self, agent):
        """前端 keyword triggers React hint."""
        ctx = MagicMock()
        ctx.task_description = "前端页面"
        hint = agent._build_implementation_hint(ctx)
        assert "React" in hint

    def test_no_framework_hint(self, agent):
        """No special framework keyword: no framework hint appended."""
        ctx = MagicMock()
        ctx.task_description = "实现加法功能"
        hint = agent._build_implementation_hint(ctx)
        assert "FastAPI" not in hint
        assert "React" not in hint


# ── _extract_code_blocks edge cases ─────────────────────────────

class TestExtractCodeBlocksUncovered:
    def test_regex_no_lang_no_path(self, agent):
        """``` alone is handled gracefully."""
        content = "```\nsome code\n```"
        # Should not crash; returns empty list when no path found
        result = agent._extract_code_blocks(content)
        assert isinstance(result, list)

    def test_triple_backtick_only(self, agent):
        """Pure ``` block without language or path returns empty."""
        content = "```\nx=1\n```"
        blocks = agent._extract_code_blocks(content)
        assert blocks == []

    def test_backtick_path_only_format(self, agent):
        """```:path format with colon and no lang."""
        content = "```:src/utils.py\ndef foo():\n    pass\n```"
        blocks = agent._extract_code_blocks(content)
        assert len(blocks) == 1
        assert blocks[0][0] == "src/utils.py"

    def test_python_code_without_path_in_comment(self, agent):
        """Code block with # path comment is still extracted if non-comment line follows."""
        content = "```python\n# src/comment.py\nx=1\n```"
        blocks = agent._extract_code_blocks(content)
        # The path comment check should filter out "# src/comment.py" as path
        # but the next line "x=1" is valid code - however since path is comment, it may be empty
        # This tests that the code doesn't crash
        assert isinstance(blocks, list)

    def test_whitespace_only_code_block(self, agent):
        """Code block with only whitespace is ignored."""
        content = "```python:src/space.py\n   \n\n```"
        blocks = agent._extract_code_blocks(content)
        assert blocks == []

    def test_mixed_content(self, agent):
        """Mixed markdown text with code blocks extracts correctly."""
        content = """Some description.

```python:src/main.py
def main():
    pass
```

More text here.

```python:tests/test_main.py
def test_main():
    pass
```
"""
        blocks = agent._extract_code_blocks(content)
        assert len(blocks) == 2
        assert blocks[0][0] == "src/main.py"
        assert blocks[1][0] == "tests/test_main.py"


# ── _resolve_dependencies uncovered branches ─────────────────────

class TestResolveDependenciesUncovered:
    def test_missing_deps_installed(self, agent, tmp_path, capsys):
        """Missing deps are detected and install_dependencies is called."""
        py_file = tmp_path / "test.py"
        py_file.write_text("import requests\nimport pandas", encoding="utf-8")

        with patch("src.agents.executor.DependencyResolver") as mock_resolver:
            mock_resolver_instance = MagicMock()
            mock_resolver_instance.resolve.return_value = MagicMock(
                missing=["requests", "pandas"],
                installed=["numpy"],
            )
            mock_resolver_instance.install_dependencies.return_value = {
                "installed": ["requests", "pandas"],
                "failed": [],
            }
            mock_resolver.return_value = mock_resolver_instance

            result = agent._resolve_dependencies(tmp_path, ["test.py"])

            assert result is not None
            mock_resolver_instance.install_dependencies.assert_called_once_with(
                ["requests", "pandas"]
            )
            captured = capsys.readouterr()
            assert "发现缺失依赖" in captured.out
            assert "已安装" in captured.out

    def test_install_failed_deps(self, agent, tmp_path, capsys):
        """When some deps fail to install, the failure is reported."""
        py_file = tmp_path / "test.py"
        py_file.write_text("import unknown_pkg", encoding="utf-8")

        with patch("src.agents.executor.DependencyResolver") as mock_resolver:
            mock_resolver_instance = MagicMock()
            mock_resolver_instance.resolve.return_value = MagicMock(
                missing=["unknown_pkg"],
            )
            mock_resolver_instance.install_dependencies.return_value = {
                "installed": [],
                "failed": ["unknown_pkg"],
            }
            mock_resolver.return_value = mock_resolver_instance

            agent._resolve_dependencies(tmp_path, ["test.py"])
            captured = capsys.readouterr()
            assert "安装失败" in captured.out


# ── _try_format_code uncovered formatters ───────────────────────

class TestTryFormatCodeUncovered:
    def test_js_file_formatter(self, agent, tmp_path):
        """JS/TS files use prettier formatter."""
        (tmp_path / "utils.js").write_text("const x=1", encoding="utf-8")
        with patch("subprocess.run") as mock_run:
            agent._try_format_code(tmp_path, ["utils.js"])
        assert mock_run.called
        call_args = mock_run.call_args[0][0]
        assert call_args[0] == "npx"
        assert "prettier" in call_args

    def test_tsx_file_formatter(self, agent, tmp_path):
        """TSX files use prettier formatter."""
        (tmp_path / "Component.tsx").write_text("export const C=()=>null", encoding="utf-8")
        with patch("subprocess.run") as mock_run:
            agent._try_format_code(tmp_path, ["Component.tsx"])
        assert mock_run.called
        call_args = mock_run.call_args[0][0]
        assert "prettier" in call_args

    def test_go_file_formatter(self, agent, tmp_path):
        """Go files use gofmt formatter."""
        (tmp_path / "main.go").write_text("package main", encoding="utf-8")
        with patch("subprocess.run") as mock_run:
            agent._try_format_code(tmp_path, ["main.go"])
        assert mock_run.called
        call_args = mock_run.call_args[0][0]
        assert call_args[0] == "gofmt"

    def test_subprocess_timeout(self, agent, tmp_path):
        """Formatter subprocess timeout is handled."""
        (tmp_path / "f.py").write_text("x=1", encoding="utf-8")
        with patch("subprocess.run", side_effect=TimeoutError("timed out")):
            result = agent._try_format_code(tmp_path, ["f.py"])
        # Should not raise; formatted list may be empty
        assert result["errors"] == []

    def test_subprocess_exception(self, agent, tmp_path):
        """Formatter subprocess exception is handled."""
        (tmp_path / "f.py").write_text("x=1", encoding="utf-8")
        with patch("subprocess.run", side_effect=OSError("no such file")):
            result = agent._try_format_code(tmp_path, ["f.py"])
        assert result["errors"] == []


# ── _try_run_tests uncovered branches ──────────────────────────

class TestTryRunTestsUncovered:
    def test_pytest_version_check_exception(self, agent, tmp_path):
        """FileNotFoundError on pytest version check returns early."""
        with patch("subprocess.run", side_effect=FileNotFoundError):
            result = agent._try_run_tests(tmp_path, ["tests/test_x.py"])
        assert result["ran"] is True
        # pytest not available → ran=True but passed stays False

    def test_pytest_run_exception(self, agent, tmp_path):
        """subprocess.run raises exception during test run."""
        def side_effect(*args, **kwargs):
            if "--version" in str(args):
                return MagicMock(returncode=0)
            raise OSError("permission denied")

        with patch("subprocess.run", side_effect=side_effect):
            result = agent._try_run_tests(tmp_path, ["tests/test_x.py"])

        assert result["ran"] is True
        assert "Error" in result["output"]

    def test_pytest_timeout(self, agent, tmp_path):
        """subprocess.run timeout during test run."""
        def side_effect(*args, **kwargs):
            if "--version" in str(args):
                return MagicMock(returncode=0)
            raise TimeoutError("pytest timed out")

        with patch("subprocess.run", side_effect=side_effect):
            result = agent._try_run_tests(tmp_path, ["tests/test_x.py"])

        assert result["ran"] is True
        assert "Error" in result["output"]


# ── _inject_relevant_files edge cases ──────────────────────────

class TestInjectRelevantFilesUncovered:
    def test_file_read_truncated(self, agent, tmp_path):
        """Large files are truncated to 3000 characters."""
        large_file = tmp_path / "large.py"
        large_file.write_text("x=" + "a" * 5000, encoding="utf-8")
        ctx = MagicMock()
        ctx.relevant_files = [large_file]
        ctx.project_path = tmp_path
        ctx.task_description = "test"
        prompt = []
        agent._inject_relevant_files(ctx, prompt)
        assert len(prompt) == 1
        # Content should be truncated
        assert len(prompt[0]["content"]) <= 3000 + 200  # content + header overhead

    def test_context_manager_exception(self, agent, tmp_path):
        """File read error is handled gracefully."""
        ctx = MagicMock()
        bad_file = MagicMock(spec=Path)
        bad_file.__str__ = lambda: str(tmp_path / "bad.py")

        ctx.relevant_files = [bad_file]
        ctx.project_path = tmp_path
        ctx.task_description = "test"
        prompt = []

        with patch("builtins.open", side_effect=OSError("read error")):
            agent._inject_relevant_files(ctx, prompt)
        # Should not crash; prompt stays empty since file read failed
        assert prompt == []

    def test_more_than_8_files(self, agent, tmp_path):
        """Only first 8 files are injected."""
        ctx = MagicMock()
        files = [tmp_path / f"file{i}.py" for i in range(12)]
        for f in files:
            f.write_text("code", encoding="utf-8")
        ctx.relevant_files = files
        ctx.project_path = tmp_path
        ctx.task_description = "test"
        prompt = []
        agent._inject_relevant_files(ctx, prompt)
        # At most 8 files injected
        content = prompt[0]["content"] if prompt else ""
        injected_count = content.count("### file")
        assert injected_count <= 8


# ── _post_process uncovered branches ───────────────────────────

class TestPostProcessUncovered:
    def test_artifact_metadata(self, agent, tmp_path):
        """Artifacts contain correct type, path, lines, and size."""
        ctx = MagicMock()
        ctx.project_path = tmp_path
        ctx.task_description = "test"
        result = '```python:src/mymod.py\nclass Foo:\n    pass\n```'

        output = agent._post_process(result, ctx)

        assert "src/mymod.py" in output.artifacts
        artifact = output.artifacts["src/mymod.py"]
        assert artifact["type"] == "code"
        assert artifact["path"] == "src/mymod.py"
        assert artifact["lines"] == 2
        assert artifact["size"] > 0

    def test_recommendations_with_deps(self, agent, tmp_path):
        """Recommendations include installed deps when available."""
        ctx = MagicMock()
        ctx.project_path = tmp_path
        ctx.task_description = "test"
        result = '```python:src/test.py\nimport requests\n```'

        with patch.object(agent, "_resolve_dependencies") as mock_resolve:
            mock_res = MagicMock()
            mock_res.installed = ["requests"]
            mock_resolve.return_value = mock_res

            with patch.object(agent, "_try_run_tests", return_value={"ran": False}):
                output = agent._post_process(result, ctx)

        assert any("已安装依赖" in r for r in output.recommendations)
        assert output.next_agent == "verifier"

    def test_recommendations_with_failing_tests(self, agent, tmp_path):
        """Failing test results are reflected in recommendations."""
        ctx = MagicMock()
        ctx.project_path = tmp_path
        ctx.task_description = "test"
        result = '```python:tests/test_x.py\ndef test_fail(): assert False\n```'

        with patch.object(agent, "_resolve_dependencies", return_value=None):
            with patch.object(agent, "_try_run_tests", return_value={
                "ran": True,
                "passed": False,
                "output": "1 failed",
            }):
                output = agent._post_process(result, ctx)

        assert any("测试有问题" in r for r in output.recommendations)

    def test_recommendations_with_passing_tests(self, agent, tmp_path):
        """Passing test results are reflected in recommendations."""
        ctx = MagicMock()
        ctx.project_path = tmp_path
        ctx.task_description = "test"
        result = '```python:tests/test_x.py\ndef test_pass(): pass\n```'

        with patch.object(agent, "_resolve_dependencies", return_value=None):
            with patch.object(agent, "_try_run_tests", return_value={
                "ran": True,
                "passed": True,
                "output": "1 passed",
            }):
                output = agent._post_process(result, ctx)

        assert any("所有测试通过" in r for r in output.recommendations)

    def test_no_saved_files_no_deps_no_tests(self, agent, tmp_path):
        """No files saved: recommendations show no deps/test info."""
        ctx = MagicMock()
        ctx.project_path = tmp_path
        ctx.task_description = "test"
        result = "No code blocks here."

        output = agent._post_process(result, ctx)

        assert output.status == AgentStatus.COMPLETED
        # Should have default recommendations
        assert any("verifier" in r or "code-reviewer" in r for r in output.recommendations)

    def test_dep_result_no_installed(self, agent, tmp_path):
        """dep_result exists but installed is falsy."""
        ctx = MagicMock()
        ctx.project_path = tmp_path
        ctx.task_description = "test"
        result = '```python:src/test.py\nimport os\n```'

        with patch.object(agent, "_resolve_dependencies") as mock_resolve:
            mock_res = MagicMock()
            mock_res.installed = []  # empty list
            mock_resolve.return_value = mock_res

            with patch.object(agent, "_try_run_tests", return_value={"ran": False}):
                output = agent._post_process(result, ctx)

        # Should not crash; installed dep recommendation should not appear
        assert output.status == AgentStatus.COMPLETED

    def test_save_error_collects_error_message(self, agent, tmp_path, monkeypatch):
        """File save error is collected in errors."""
        ctx = MagicMock()
        ctx.project_path = tmp_path
        ctx.task_description = "test"
        result = '```python:src/fail.py\nx=1\n```'

        import builtins

        original_open = builtins.open

        def mock_open(*args, **kwargs):
            if "fail.py" in str(args[0]):
                raise OSError("disk full")
            return original_open(*args, **kwargs)

        monkeypatch.setattr(builtins, "open", mock_open)

        output = agent._post_process(result, ctx)
        # File was not saved due to error
        assert not (tmp_path / "src" / "fail.py").exists()
        assert output.status == AgentStatus.COMPLETED


# ── Agent class attributes ───────────────────────────────────────

class TestAgentAttributes:
    def test_name(self, agent):
        assert agent.name == "executor"

    def test_description(self, agent):
        assert "执行者" in agent.description

    def test_lane(self, agent):
        from src.agents.base import AgentLane

        assert agent.lane == AgentLane.BUILD_ANALYSIS

    def test_default_tier(self, agent):
        assert agent.default_tier == "medium"

    def test_icon(self, agent):
        assert agent.icon == "💻"

    def test_tools(self, agent):
        expected_tools = {"file_read", "file_write", "bash", "test", "git", "web_fetch"}
        assert set(agent.tools) == expected_tools

    def test_language_extensions_all_keys(self, agent):
        """All documented languages have entries."""
        expected = {
            "python", "javascript", "typescript", "jsx", "go", "rust",
            "java", "csharp", "cpp", "c", "ruby", "php", "swift", "kotlin",
            "shell", "yaml", "json", "toml", "markdown",
        }
        assert set(agent.LANGUAGE_EXTENSIONS.keys()) == expected

    def test_language_extension_python(self, agent):
        assert ".py" in agent.LANGUAGE_EXTENSIONS["python"]

    def test_language_extension_go(self, agent):
        assert ".go" in agent.LANGUAGE_EXTENSIONS["go"]

    def test_language_extension_rust(self, agent):
        assert ".rs" in agent.LANGUAGE_EXTENSIONS["rust"]
