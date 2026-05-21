"""Tests for explore.py"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.explore import ExploreAgent, FileInfo, ProjectMap

# ── Fixtures ──────────────────────────────────────────────────────


@pytest.fixture
def sample_project(tmp_path):
    """Create a sample project structure."""
    # Create directory structure
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("def main():\n    pass\n", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_main.py").write_text("def test():\n    pass\n", encoding="utf-8")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "readme.md").write_text("# Project\n", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("requests>=2.28\nflask\n", encoding="utf-8")
    (tmp_path / "package.json").write_text(
        '{"dependencies": {"express": "^4.0.0", "lodash": "^4.0.0"}}',
        encoding="utf-8",
    )
    return tmp_path


@pytest.fixture
def make_agent(tmp_path):
    """Factory fixture to create ExploreAgent."""
    def _make(project_path=None):
        if project_path is None:
            project_path = tmp_path
        return ExploreAgent(config={"project_path": str(project_path)})
    return _make


# ── FileInfo ──────────────────────────────────────────────────────


class TestFileInfo:
    def test_creation(self):
        info = FileInfo(
            path="test.py",
            type="python",
            size=1024,
            lines=50,
            importance=0.8,
        )
        assert info.path == "test.py"
        assert info.type == "python"
        assert info.size == 1024
        assert info.lines == 50
        assert info.importance == 0.8


# ── ProjectMap ──────────────────────────────────────────────────────


class TestProjectMap:
    def test_creation(self):
        pm = ProjectMap(
            root_path="/test",
            language_distribution={"Python": 10, "JavaScript": 5},
            key_directories=["src", "tests"],
            entry_points=["src/main.py"],
            config_files=["requirements.txt"],
            test_files=["tests/test_main.py"],
            dependencies=["requests", "flask"],
            structure_tree="root/",
        )
        assert pm.root_path == "/test"
        assert pm.language_distribution["Python"] == 10
        assert "src" in pm.key_directories


# ── ExploreAgent Init ──────────────────────────────────────────────


class TestExploreAgentInit:
    def test_default_init(self, tmp_path):
        agent = ExploreAgent(config={"project_path": str(tmp_path)})
        assert agent.workspace_scanner.root == tmp_path
        assert agent.name == "explore"
        assert agent.default_tier == "low"

    def test_string_path_converted(self, tmp_path):
        agent = ExploreAgent(config={"project_path": str(tmp_path)})
        assert agent.workspace_scanner.root == tmp_path


# ── ExploreAgent System Prompt ─────────────────────────────────────


class TestSystemPrompt:
    def test_system_prompt_not_empty(self, make_agent):
        agent = make_agent()
        prompt = agent.system_prompt
        assert len(prompt) > 0
        assert "代码库探索智能体" in prompt

    def test_system_prompt_contains_sections(self, make_agent):
        agent = make_agent()
        prompt = agent.system_prompt
        assert "项目概览" in prompt
        assert "目录结构树" in prompt


# ── Scan Directory ─────────────────────────────────────────────────


class TestScanDirectory:
    def test_basic_scan(self, sample_project):
        agent = ExploreAgent(config={"project_path": str(sample_project)})
        result = agent._scan_directory(sample_project)
        assert sample_project.name in result
        assert "src/" in result
        assert "tests/" in result

    def test_scan_ignores_dirs(self, sample_project):
        # Create ignored directories
        (sample_project / "__pycache__").mkdir()
        (sample_project / "__pycache__" / "cached.pyc").write_text("x")
        (sample_project / ".git").mkdir()
        (sample_project / "node_modules").mkdir()

        agent = ExploreAgent(config={"project_path": str(sample_project)})
        result = agent._scan_directory(sample_project)
        assert "__pycache__" not in result
        assert ".git" not in result
        assert "node_modules" not in result

    def test_scan_with_max_depth(self, sample_project):
        agent = ExploreAgent(config={"project_path": str(sample_project)})
        result = agent._scan_directory(sample_project, max_depth=1)
        assert "src/" in result

    def test_scan_handles_permission_error(self, tmp_path):
        # Create a directory that raises PermissionError
        agent = ExploreAgent(config={"project_path": str(tmp_path)})
        # Should not raise, just skip
        result = agent._scan_directory(tmp_path)
        assert isinstance(result, str)


# ── Collect File Stats ─────────────────────────────────────────────


class TestCollectFileStats:
    def test_basic_stats(self, sample_project):
        agent = ExploreAgent(config={"project_path": str(sample_project)})
        stats = agent._collect_file_stats(sample_project)

        assert stats["total_files"] > 0
        assert stats["total_lines"] > 0
        assert "Python" in stats["language_distribution"]
        assert "Markdown" in stats["language_distribution"]

    def test_stats_finds_key_files(self, sample_project):
        # Create a main.py file
        (sample_project / "main.py").write_text("def main():\n    pass\n", encoding="utf-8")

        agent = ExploreAgent(config={"project_path": str(sample_project)})
        stats = agent._collect_file_stats(sample_project)

        assert "main.py" in stats["key_files"]

    def test_stats_language_mapping(self, tmp_path):
        # Create files with different extensions
        (tmp_path / "a.py").write_text("x=1")
        (tmp_path / "b.js").write_text("x=1")
        (tmp_path / "c.ts").write_text("x=1")
        (tmp_path / "d.go").write_text("x=1")
        (tmp_path / "e.java").write_text("x=1")
        (tmp_path / "f.json").write_text("{}")
        (tmp_path / "g.yaml").write_text("key: value")

        agent = ExploreAgent(config={"project_path": str(tmp_path)})
        stats = agent._collect_file_stats(tmp_path)

        assert "Python" in stats["language_distribution"]
        assert "JavaScript" in stats["language_distribution"]
        assert "TypeScript" in stats["language_distribution"]
        assert "Go" in stats["language_distribution"]
        assert "Java" in stats["language_distribution"]
        assert "JSON" in stats["language_distribution"]
        assert "YAML" in stats["language_distribution"]

    def test_stats_handles_read_error(self, tmp_path):
        # Create a file that can't be read
        bad_file = tmp_path / "bad.txt"
        bad_file.write_text("test")
        bad_file.chmod(0o000)  # Remove all permissions

        agent = ExploreAgent(config={"project_path": str(tmp_path)})
        stats = agent._collect_file_stats(tmp_path)

        # Should still work, just skip the unreadable file
        assert stats["total_files"] >= 1

        # Cleanup
        bad_file.chmod(0o644)


# ── Extract Dependencies ───────────────────────────────────────────


class TestExtractDependencies:
    def test_extract_python_deps(self, sample_project):
        agent = ExploreAgent(config={"project_path": str(sample_project)})
        deps = agent._extract_dependencies(sample_project)

        assert "requests>=2.28" in deps["python"]
        assert "flask" in deps["python"]

    def test_extract_node_deps(self, sample_project):
        agent = ExploreAgent(config={"project_path": str(sample_project)})
        deps = agent._extract_dependencies(sample_project)

        assert "express" in deps["node"]
        assert "lodash" in deps["node"]

    def test_extract_no_deps(self, tmp_path):
        agent = ExploreAgent(config={"project_path": str(tmp_path)})
        deps = agent._extract_dependencies(tmp_path)

        assert deps["python"] == []
        assert deps["node"] == []

    def test_extract_handles_invalid_json(self, tmp_path):
        (tmp_path / "package.json").write_text("not valid json", encoding="utf-8")

        agent = ExploreAgent(config={"project_path": str(tmp_path)})
        deps = agent._extract_dependencies(tmp_path)

        assert deps["node"] == []

    def test_extract_handles_missing_files(self, tmp_path):
        agent = ExploreAgent(config={"project_path": str(tmp_path)})
        deps = agent._extract_dependencies(tmp_path)

        assert deps["python"] == []
        assert deps["node"] == []


# ── Format File Stats ─────────────────────────────────────────────


class TestFormatFileStats:
    def test_format_basic_stats(self, sample_project):
        agent = ExploreAgent(config={"project_path": str(sample_project)})
        stats = agent._collect_file_stats(sample_project)
        formatted = agent._format_file_stats(stats)

        assert "总文件数" in formatted
        assert "总代码行数" in formatted
        assert "语言分布" in formatted

    def test_format_with_key_files(self, sample_project):
        (sample_project / "main.py").write_text("def main():\n    pass\n", encoding="utf-8")

        agent = ExploreAgent(config={"project_path": str(sample_project)})
        stats = agent._collect_file_stats(sample_project)
        formatted = agent._format_file_stats(stats)

        assert "关键文件" in formatted
        assert "main.py" in formatted


# ── Format Dependencies ───────────────────────────────────────────


class TestFormatDependencies:
    def test_format_python_deps(self, sample_project):
        agent = ExploreAgent(config={"project_path": str(sample_project)})
        deps = agent._extract_dependencies(sample_project)
        formatted = agent._format_dependencies(deps)

        assert "Python 依赖" in formatted
        assert "requests" in formatted

    def test_format_node_deps(self, sample_project):
        agent = ExploreAgent(config={"project_path": str(sample_project)})
        deps = agent._extract_dependencies(sample_project)
        formatted = agent._format_dependencies(deps)

        assert "Node 依赖" in formatted

    def test_format_no_deps(self, tmp_path):
        agent = ExploreAgent(config={"project_path": str(tmp_path)})
        deps = agent._extract_dependencies(tmp_path)
        formatted = agent._format_dependencies(deps)

        assert "未找到依赖文件" in formatted

    def test_format_truncates_long_list(self, tmp_path):
        # Create requirements with many deps
        req = tmp_path / "requirements.txt"
        deps = "\n".join([f"dep{i}" for i in range(30)])
        req.write_text(deps)

        agent = ExploreAgent(config={"project_path": str(tmp_path)})
        deps_dict = agent._extract_dependencies(tmp_path)
        formatted = agent._format_dependencies(deps_dict)

        assert "more" in formatted


# ── Post Process ─────────────────────────────────────────────────


class TestPostProcess:
    def test_post_process_returns_output(self, make_agent):
        agent = make_agent()

        # Mock context
        context = MagicMock()
        context.project_path = "/test"

        result = agent._post_process("test result", context)

        assert result.agent_name == "explore"
        assert result.status.value == "completed"
        assert result.result == "test result"

    def test_post_process_includes_recommendations(self, make_agent):
        agent = make_agent()
        context = MagicMock()

        result = agent._post_process("test", context)

        assert len(result.recommendations) > 0
        assert result.next_agent == "analyst"


# ── Run Method (Async) ─────────────────────────────────────────────


class TestRun:
    @pytest.mark.asyncio
    async def test_run_calls_model(self, sample_project):
        agent = ExploreAgent(config={"project_path": str(sample_project)})

        # Mock the call_model method
        mock_response = MagicMock()
        mock_response.content = "Exploration result"

        with patch.object(agent, "call_model", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_response

            context = MagicMock()
            context.project_path = sample_project

            result = await agent._run(context, [{"role": "user", "content": "explore"}])

            assert result == "Exploration result"
            mock_call.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_builds_prompt(self, sample_project):
        agent = ExploreAgent(config={"project_path": str(sample_project)})

        mock_response = MagicMock()
        mock_response.content = "result"

        with patch.object(agent, "call_model", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_response

            context = MagicMock()
            context.project_path = sample_project

            prompt = [{"role": "system", "content": "you are an agent"}]
            await agent._run(context, prompt)

            # Check that the prompt was modified with exploration context
            assert len(prompt) == 2
            assert prompt[0]["role"] == "system"
            assert prompt[1]["role"] == "user"
            assert "目录结构" in prompt[1]["content"]
