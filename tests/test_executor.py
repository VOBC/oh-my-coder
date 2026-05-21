"""Tests for src/agents/executor.py - ExecutorAgent pure logic methods"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.agents.executor import ExecutorAgent


@pytest.fixture
def agent():
    return ExecutorAgent()


# ── LANGUAGE_EXTENSIONS ─────────────────────────────────────────

class TestLanguageExtensions:
    def test_python(self, agent):
        assert ".py" in agent.LANGUAGE_EXTENSIONS["python"]

    def test_multiple_typescript(self, agent):
        assert ".tsx" in agent.LANGUAGE_EXTENSIONS["typescript"]

    def test_has_shell(self, agent):
        assert ".sh" in agent.LANGUAGE_EXTENSIONS["shell"]


# ── _extract_code_blocks ────────────────────────────────────────

class TestExtractCodeBlocks:
    def test_python_with_path(self, agent):
        content = '```python:src/calc.py\nclass Calc:\n    pass\n```'
        blocks = agent._extract_code_blocks(content)
        assert len(blocks) == 1
        assert blocks[0][0] == "src/calc.py"
        assert "class Calc" in blocks[0][1]

    def test_language_colon_path(self, agent):
        content = '```:src/utils.js\nexport const x = 1;\n```'
        blocks = agent._extract_code_blocks(content)
        assert len(blocks) == 1
        assert blocks[0][0] == "src/utils.js"

    def test_multiple_blocks(self, agent):
        content = (
            '```python:src/a.py\nprint("a")\n```\n\n'
            '```python:tests/test_a.py\ndef test():\n    pass\n```'
        )
        blocks = agent._extract_code_blocks(content)
        assert len(blocks) == 2
        assert blocks[0][0] == "src/a.py"
        assert blocks[1][0] == "tests/test_a.py"

    def test_no_path_ignored(self, agent):
        content = '```python\nprint("hello")\n```'
        blocks = agent._extract_code_blocks(content)
        assert blocks == []

    def test_path_from_next_line(self, agent):
        content = '```python\nsrc/next.py\nprint("x")\n```'
        blocks = agent._extract_code_blocks(content)
        assert len(blocks) == 1
        assert blocks[0][0] == "src/next.py"

    def test_comment_path_ignored(self, agent):
        content = '```python\n# src/comment.py\nprint("x")\n```'
        blocks = agent._extract_code_blocks(content)
        assert blocks == []

    def test_empty_code_ignored(self, agent):
        content = '```python:src/empty.py\n```'
        blocks = agent._extract_code_blocks(content)
        assert blocks == []

    def test_plain_markdown_code_block_ignored(self, agent):
        content = '```\nsome text\n```'
        blocks = agent._extract_code_blocks(content)
        assert blocks == []

    def test_no_code_blocks(self, agent):
        assert agent._extract_code_blocks("just plain text") == []

    def test_raw_path_returned(self, agent):
        content = '```python:/src/abs.py\nx=1\n```'
        blocks = agent._extract_code_blocks(content)
        assert blocks[0][0] == "/src/abs.py"  # _extract_code_blocks returns raw; _post_process strips /

    def test_preserves_indentation(self, agent):
        content = '```python:src/indented.py\nclass A:\n    def f(self):\n        pass\n```'
        blocks = agent._extract_code_blocks(content)
        assert "    def f" in blocks[0][1]


# ── _find_relevant_files ────────────────────────────────────────

class TestFindRelevantFiles:
    def test_no_match(self, agent, tmp_path):
        files = agent._find_relevant_files(tmp_path, "something completely unrelated")
        assert files == []

    @pytest.mark.skipif(not hasattr(Path, 'walk'), reason="Path.walk requires Python 3.12+")
    def test_user_keyword(self, agent, tmp_path):
        (tmp_path / "auth.py").write_text("# auth")
        files = agent._find_relevant_files(tmp_path, "用户认证登录")
        assert len(files) >= 1
        assert any("auth" in f.name for f in files)

    @pytest.mark.skipif(not hasattr(Path, 'walk'), reason="Path.walk requires Python 3.12+")
    def test_api_keyword(self, agent, tmp_path):
        (tmp_path / "api_routes.py").write_text("# api")
        files = agent._find_relevant_files(tmp_path, "设计REST API接口")
        assert any("api" in f.name for f in files)

    @pytest.mark.skipif(not hasattr(Path, 'walk'), reason="Path.walk requires Python 3.12+")
    def test_limit_8_files(self, agent, tmp_path):
        for i in range(10):
            (tmp_path / f"auth_{i}.py").write_text(f"# auth{i}")
        files = agent._find_relevant_files(tmp_path, "用户认证")
        assert len(files) <= 8


# ── _build_implementation_hint ──────────────────────────────────

class TestBuildImplementationHint:
    def test_basic_hint(self, agent):
        ctx = MagicMock()
        ctx.task_description = "实现功能"
        hint = agent._build_implementation_hint(ctx)
        assert "实现要求" in hint
        assert "markdown" in hint

    def test_fastapi_hint(self, agent):
        ctx = MagicMock()
        ctx.task_description = "使用fastapi构建API"
        hint = agent._build_implementation_hint(ctx)
        assert "FastAPI" in hint

    def test_react_hint(self, agent):
        ctx = MagicMock()
        ctx.task_description = "前端React组件"
        hint = agent._build_implementation_hint(ctx)
        assert "React" in hint


# ── _inject_previous_outputs ────────────────────────────────────

class TestInjectPreviousOutputs:
    def test_with_architect(self, agent):
        ctx = MagicMock()
        arch_out = MagicMock()
        arch_out.result = "架构方案..."
        ctx.previous_outputs = {"architect": arch_out}
        prompt = []
        agent._inject_previous_outputs(ctx, prompt)
        assert any("架构设计" in msg["content"] for msg in prompt)

    def test_with_analyst(self, agent):
        ctx = MagicMock()
        analyst_out = MagicMock()
        analyst_out.result = "需求分析..."
        ctx.previous_outputs = {"analyst": analyst_out}
        prompt = []
        agent._inject_previous_outputs(ctx, prompt)
        assert any("需求分析" in msg["content"] for msg in prompt)

    def test_empty_outputs(self, agent):
        ctx = MagicMock()
        ctx.previous_outputs = {}
        prompt = []
        agent._inject_previous_outputs(ctx, prompt)
        assert prompt == []


# ── _try_format_code ────────────────────────────────────────────

class TestTryFormatCode:
    def test_py_file(self, agent, tmp_path):
        (tmp_path / "f.py").write_text("x=1")
        with patch("subprocess.run") as mock_run:
            agent._try_format_code(tmp_path, ["f.py"])
        assert mock_run.called

    def test_missing_file_skipped(self, agent, tmp_path):
        result = agent._try_format_code(tmp_path, ["nonexistent.py"])
        assert result["formatted"] == []

    def test_go_file(self, agent, tmp_path):
        (tmp_path / "main.go").write_text('package main')
        with patch("subprocess.run") as mock_run:
            agent._try_format_code(tmp_path, ["main.go"])
        assert mock_run.called

    def test_non_code_file_skipped(self, agent, tmp_path):
        (tmp_path / "readme.md").write_text("# hi")
        result = agent._try_format_code(tmp_path, ["readme.md"])
        assert result["formatted"] == []


# ── _try_run_tests ──────────────────────────────────────────────

class TestTryRunTests:
    def test_no_test_files(self, agent, tmp_path):
        result = agent._try_run_tests(tmp_path, ["src/main.py"])
        assert result["ran"] is False

    def test_with_test_files_no_pytest(self, agent, tmp_path):
        with patch("subprocess.run", side_effect=FileNotFoundError):
            result = agent._try_run_tests(tmp_path, ["tests/test_x.py"])
        assert result["ran"] is True
        assert result["passed"] is False

    def test_with_test_files_passing(self, agent, tmp_path):
        mock_proc = MagicMock(returncode=0, stdout="1 passed")
        calls = []
        def side_effect(*a, **kw):
            calls.append(kw.get("capture_output"))
            if not calls:  # first call is --version
                return MagicMock(returncode=0)
            return mock_proc
        with patch("subprocess.run", side_effect=side_effect):
            result = agent._try_run_tests(tmp_path, ["tests/test_x.py"])
        assert result["ran"] is True
        assert result["passed"] is True
        assert result["tests_run"] == 1

    def test_with_test_files_failing(self, agent, tmp_path):
        mock_proc = MagicMock(returncode=1, stdout="1 failed")
        def side_effect(*a, **kw):
            if kw.get("capture_output") is None:
                return MagicMock(returncode=0)
            return mock_proc
        with patch("subprocess.run", side_effect=side_effect):
            result = agent._try_run_tests(tmp_path, ["tests/test_x.py"])
        assert result["tests_failed"] == 1


# ── _inject_relevant_files ──────────────────────────────────────

class TestInjectRelevantFiles:
    def test_no_files(self, agent):
        ctx = MagicMock()
        ctx.relevant_files = None
        ctx.project_path = MagicMock(spec=Path)
        ctx.task_description = "test"
        prompt = []
        agent._inject_relevant_files(ctx, prompt)
        assert prompt == []

    def test_with_relevant_files(self, agent, tmp_path):
        test_file = tmp_path / "test_module.py"
        test_file.write_text("def test_func(): pass", encoding="utf-8")
        ctx = MagicMock()
        ctx.relevant_files = [test_file]
        ctx.project_path = tmp_path
        ctx.task_description = "test"
        prompt = []
        agent._inject_relevant_files(ctx, prompt)
        assert len(prompt) == 1
        assert "test_module.py" in prompt[0]["content"]

    def test_read_error_handled(self, agent, tmp_path):
        ctx = MagicMock()
        ctx.relevant_files = [tmp_path / "nonexistent.py"]
        ctx.project_path = tmp_path
        ctx.task_description = "test"
        prompt = []
        agent._inject_relevant_files(ctx, prompt)
        assert prompt == []


# ── _post_process ──────────────────────────────────────────────

class TestPostProcess:
    def test_extract_and_save_code(self, agent, tmp_path):
        ctx = MagicMock()
        ctx.project_path = tmp_path
        ctx.task_description = "test"
        result = '''```python:src/new_module.py
class NewClass:
    pass
```'''
        output = agent._post_process(result, ctx)
        assert output.status.name == "COMPLETED"
        assert (tmp_path / "src" / "new_module.py").exists()

    def test_multiple_code_blocks(self, agent, tmp_path):
        ctx = MagicMock()
        ctx.project_path = tmp_path
        ctx.task_description = "test"
        result = '''```python:src/a.py
class A:
    pass
```

```python:src/b.py
class B:
    pass
```'''
        agent._post_process(result, ctx)
        assert (tmp_path / "src" / "a.py").exists()
        assert (tmp_path / "src" / "b.py").exists()

    def test_path_lstrip_slash(self, agent, tmp_path):
        ctx = MagicMock()
        ctx.project_path = tmp_path
        ctx.task_description = "test"
        result = '```python:/src/absolute.py\nx=1\n```'
        agent._post_process(result, ctx)
        assert (tmp_path / "src" / "absolute.py").exists()

    def test_save_error_handled(self, agent, tmp_path, monkeypatch):
        ctx = MagicMock()
        ctx.project_path = tmp_path
        ctx.task_description = "test"
        result = '```python:src/test.py\nx=1\n```'

        # Mock open to raise error
        import builtins
        def mock_open(*args, **kwargs):
            if "test.py" in str(args):
                raise OSError("disk full")
            return original_open(*args, **kwargs)

        original_open = builtins.open
        monkeypatch.setattr(builtins, "open", mock_open)

        output = agent._post_process(result, ctx)
        # Should still complete with errors in recommendations
        assert output.status.name == "COMPLETED"


# ── _resolve_dependencies ───────────────────────────────────────

class TestResolveDependencies:
    def test_no_python_files(self, agent, tmp_path):
        result = agent._resolve_dependencies(tmp_path, ["src/utils.js"])
        assert result is None

    def test_no_missing_deps(self, agent, tmp_path):
        py_file = tmp_path / "test.py"
        py_file.write_text("print('hello')", encoding="utf-8")
        with patch("src.agents.executor.DependencyResolver") as mock_resolver:
            mock_resolver_instance = MagicMock()
            mock_resolver_instance.resolve.return_value = MagicMock(missing=[])
            mock_resolver.return_value = mock_resolver_instance
            result = agent._resolve_dependencies(tmp_path, ["test.py"])
            assert result is not None

    def test_with_missing_deps(self, agent, tmp_path, capsys):
        py_file = tmp_path / "test.py"
        py_file.write_text("import requests\nimport pandas", encoding="utf-8")
        with patch("src.agents.executor.DependencyResolver") as mock_resolver:
            mock_resolver_instance = MagicMock()
            mock_resolver_instance.resolve.return_value = MagicMock(missing=["requests", "pandas"])
            mock_install = MagicMock(return_value={"installed": ["requests"], "failed": []})
            mock_resolver_instance.install_dependencies = mock_install
            mock_resolver.return_value = mock_resolver_instance
            result = agent._resolve_dependencies(tmp_path, ["test.py"])
            assert result is not None

    def test_exception_handled(self, agent, tmp_path):
        py_file = tmp_path / "test.py"
        py_file.write_text("import something", encoding="utf-8")
        with patch("src.agents.executor.DependencyResolver", side_effect=Exception("fail")):
            result = agent._resolve_dependencies(tmp_path, ["test.py"])
            assert result is None


# ── system_prompt property ──────────────────────────────────────

class TestSystemPrompt:
    def test_system_prompt_exists(self, agent):
        prompt = agent.system_prompt
        assert "资深的全栈软件工程师" in prompt
        assert "代码实现" in prompt

    def test_system_prompt_contains_examples(self, agent):
        prompt = agent.system_prompt
        assert "```" in prompt  # contains code block markers
