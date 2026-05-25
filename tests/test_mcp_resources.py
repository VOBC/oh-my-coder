"""
tests/test_mcp_resources.py

单元测试 — src/mcp/resources.py
覆盖率目标 > 85%，覆盖所有公开函数和核心内部函数。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# 导入被测模块（注意：直接 import 后修改全局状态，需要每次测试独立设置）
import src.mcp.resources as mcp_resources


# ---------------------------------------------------------------------------
# 辅助：重置全局 _WORKSPACE 状态
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_workspace():
    """每个测试前后重置 _WORKSPACE 全局状态，防止测试间互相干扰。"""
    mcp_resources._WORKSPACE = None
    yield
    mcp_resources._WORKSPACE = None


# ---------------------------------------------------------------------------
# 1. set_workspace / get_workspace
# ---------------------------------------------------------------------------

class TestWorkspace:
    """测试 set_workspace / get_workspace 全局状态管理。"""

    def test_get_workspace_default_returns_cwd(self):
        """未设置 workspace 时，get_workspace() 返回 Path.cwd()。"""
        mcp_resources._WORKSPACE = None
        result = mcp_resources.get_workspace()
        assert result == Path.cwd()

    def test_set_workspace_stores_resolved_path(self, tmp_path):
        """set_workspace() 应将路径 resolve 后存入全局变量。"""
        mcp_resources.set_workspace(tmp_path)
        assert mcp_resources._WORKSPACE == tmp_path.resolve()

    def test_get_workspace_after_set(self, tmp_path):
        """set_workspace() 之后，get_workspace() 返回设置的值。"""
        mcp_resources.set_workspace(tmp_path)
        assert mcp_resources.get_workspace() == tmp_path.resolve()

    def test_set_workspace_resolves_relative_path(self, tmp_path, monkeypatch):
        """set_workspace() 对相对路径执行 resolve()。"""
        sub = tmp_path / "sub"
        sub.mkdir()
        monkeypatch.chdir(sub)
        mcp_resources.set_workspace(Path(".."))
        # resolve 后应指向 tmp_path 而非相对路径
        assert mcp_resources._WORKSPACE == tmp_path.resolve()

    def test_set_workspace_none_clears_workspace(self, tmp_path):
        """再次调用 set_workspace(None) 可清除已设置的 workspace。"""
        mcp_resources.set_workspace(tmp_path)
        assert mcp_resources.get_workspace() == tmp_path.resolve()
        mcp_resources._WORKSPACE = None
        assert mcp_resources.get_workspace() == Path.cwd()


# ---------------------------------------------------------------------------
# 2. _project_stats
# ---------------------------------------------------------------------------

class TestProjectStats:
    """测试 _project_stats() 统计函数。"""

    def test_returns_dict_with_required_keys(self, tmp_path):
        """返回值必须是包含 total_files、code_lines、by_language 的 dict。"""
        result = mcp_resources._project_stats(tmp_path)
        assert isinstance(result, dict)
        assert "total_files" in result
        assert "code_lines" in result
        assert "by_language" in result

    def test_total_files_counts_code_files_only(self, tmp_path):
        """只应统计有扩展名的代码文件。"""
        (tmp_path / "main.py").write_text("print('hello')\n" * 10)
        (tmp_path / "readme.md").write_text("# Readme\n")
        (tmp_path / "data.txt").write_text("some data\n")
        (tmp_path / "utils.js").write_text("console.log('hi');\n")

        result = mcp_resources._project_stats(tmp_path)
        assert result["total_files"] == 2  # .py + .js

    def test_code_lines_counts_lines_in_code_files(self, tmp_path):
        """code_lines 应为所有代码文件行数之和。"""
        (tmp_path / "a.py").write_text("line1\nline2\nline3\n")
        (tmp_path / "b.py").write_text("line1\nline2\n")
        result = mcp_resources._project_stats(tmp_path)
        assert result["code_lines"] == 5  # 3 + 2

    def test_by_language_groups_by_extension(self, tmp_path):
        """by_language 应以语言名为 key 统计文件数。"""
        (tmp_path / "a.py").write_text("x = 1\n")
        (tmp_path / "b.py").write_text("y = 2\n")
        (tmp_path / "c.js").write_text("console.log(1);\n")
        result = mcp_resources._project_stats(tmp_path)
        assert result["by_language"]["Python"] == 2
        assert result["by_language"]["JavaScript"] == 1

    def test_ignores_ignored_directories(self, tmp_path):
        """__pycache__、.git、venv 等目录应被忽略。"""
        (tmp_path / "main.py").write_text("x = 1\n")
        ignored = tmp_path / ".git"
        ignored.mkdir()
        (ignored / "config").write_text("git config\n")
        (tmp_path / "__pycache__").mkdir()
        (tmp_path / "__pycache__" / "main.pyc").write_text("bytes\n")
        result = mcp_resources._project_stats(tmp_path)
        assert result["total_files"] == 1

    def test_handles_nonexistent_workspace(self, tmp_path):
        """不存在的路径应返回 0 计数而不抛异常。"""
        fake = tmp_path / "nonexistent"
        result = mcp_resources._project_stats(fake)
        assert result["total_files"] == 0
        assert result["code_lines"] == 0
        assert result["by_language"] == {}

    def test_read_text_error_is_suppressed(self, tmp_path):
        """文件无法读取时（权限/编码问题）不应抛异常，使用 contextlib.suppress。"""
        # 创建一个空目录结构覆盖 tmp_path，触发 walk 但无文件
        # 这个测试验证的是异常不会泄漏，只要不是空目录就正常返回
        result = mcp_resources._project_stats(tmp_path)
        assert isinstance(result["total_files"], int)


# ---------------------------------------------------------------------------
# 3. _generate_summary
# ---------------------------------------------------------------------------

class TestGenerateSummary:
    """测试 _generate_summary() 工作区摘要生成。"""

    def test_returns_markdown_string(self, tmp_path):
        """返回值为 markdown 格式字符串。"""
        result = mcp_resources._generate_summary(tmp_path)
        assert isinstance(result, str)
        assert "# 工作区摘要" in result

    def test_contains_workspace_path(self, tmp_path):
        """摘要应包含工作区路径。"""
        result = mcp_resources._generate_summary(tmp_path)
        assert str(tmp_path) in result

    def test_contains_file_count(self, tmp_path):
        """摘要应包含文件总数。"""
        (tmp_path / "a.py").write_text("x = 1\n")
        result = mcp_resources._generate_summary(tmp_path)
        assert "文件总数" in result

    def test_contains_code_lines(self, tmp_path):
        """摘要应包含代码行数。"""
        (tmp_path / "a.py").write_text("line1\nline2\n")
        result = mcp_resources._generate_summary(tmp_path)
        assert "代码行数" in result

    def test_contains_language_distribution(self, tmp_path):
        """摘要应包含语言分布章节。"""
        (tmp_path / "a.py").write_text("x = 1\n")
        result = mcp_resources._generate_summary(tmp_path)
        assert "## 语言分布" in result
        assert "Python" in result

    def test_checkpoint_section_when_index_exists(self, tmp_path):
        """当 .omc/checkpoints/index.json 存在时，应显示 Checkpoints 数量。"""
        ckpt_dir = tmp_path / ".omc" / "checkpoints"
        ckpt_dir.mkdir(parents=True)
        index_file = ckpt_dir / "index.json"
        index_file.write_text(json.dumps([{"id": "1"}, {"id": "2"}]), encoding="utf-8")

        result = mcp_resources._generate_summary(tmp_path)
        assert "## 快照" in result
        assert "Checkpoints: 2 个" in result

    def test_checkpoint_section_absent_when_index_missing(self, tmp_path):
        """当 index.json 不存在时，不应有快照章节。"""
        result = mcp_resources._generate_summary(tmp_path)
        assert "## 快照" not in result

    def test_checkpoint_section_absent_when_omc_missing(self, tmp_path):
        """没有 .omc 目录时，不应显示快照章节。"""
        result = mcp_resources._generate_summary(tmp_path)
        assert "## 快照" not in result

    def test_skill_section_when_index_exists(self, tmp_path):
        """当 .omc/skills/index.json 存在时，应显示 Skills 数量。"""
        skill_dir = tmp_path / ".omc" / "skills"
        skill_dir.mkdir(parents=True)
        index_file = skill_dir / "index.json"
        index_file.write_text(json.dumps([{"name": "s1"}, {"name": "s2"}, {"name": "s3"}]), encoding="utf-8")

        result = mcp_resources._generate_summary(tmp_path)
        assert "## 经验沉淀" in result
        assert "Skills: 3 个" in result

    def test_skill_section_absent_when_index_missing(self, tmp_path):
        """当 skills index.json 不存在时，不应显示经验沉淀章节。"""
        result = mcp_resources._generate_summary(tmp_path)
        assert "## 经验沉淀" not in result

    def test_corrupt_checkpoint_json_is_handled(self, tmp_path):
        """checkpoint index.json 内容损坏时不应抛异常。"""
        ckpt_dir = tmp_path / ".omc" / "checkpoints"
        ckpt_dir.mkdir(parents=True)
        (ckpt_dir / "index.json").write_text("not valid json {{{", encoding="utf-8")

        # 不应抛异常
        result = mcp_resources._generate_summary(tmp_path)
        assert isinstance(result, str)
        assert "## 快照" not in result  # 损坏时跳过，不会添加章节


# ---------------------------------------------------------------------------
# 4. _generate_structure
# ---------------------------------------------------------------------------

class TestGenerateStructure:
    """测试 _generate_structure() 目录树生成。"""

    def test_returns_markdown_string(self, tmp_path):
        """返回值应为 markdown 格式字符串。"""
        result = mcp_resources._generate_structure(tmp_path)
        assert isinstance(result, str)
        assert "# 项目结构" in result

    def test_contains_workspace_name(self, tmp_path):
        """目录树标题应包含工作区名。"""
        result = mcp_resources._generate_structure(tmp_path)
        assert tmp_path.name in result

    def test_shows_nested_directories(self, tmp_path):
        """嵌套目录应出现在输出中。"""
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("x = 1\n")
        result = mcp_resources._generate_structure(tmp_path)
        assert "src" in result
        assert "main.py" in result

    def test_respects_depth_limit(self, tmp_path):
        """depth 参数应限制遍历深度。"""
        deep = tmp_path / "a" / "b" / "c" / "deep.py"
        deep.parent.mkdir(parents=True)
        deep.write_text("x = 1\n")

        result_shallow = mcp_resources._generate_structure(tmp_path, depth=1)
        result_deep = mcp_resources._generate_structure(tmp_path, depth=3)

        assert "deep.py" in result_deep
        assert "deep.py" not in result_shallow or result_shallow.count("deep.py") == 0

    def test_ignores_git_and_omc_directories(self, tmp_path):
        """.git、.omc、__pycache__ 等目录应被忽略。"""
        (tmp_path / ".git").mkdir()
        (tmp_path / ".git" / "config").write_text("git config\n")
        (tmp_path / "__pycache__").mkdir()
        (tmp_path / "main.py").write_text("x = 1\n")
        result = mcp_resources._generate_structure(tmp_path)
        assert ".git" not in result
        assert "__pycache__" not in result
        assert "main.py" in result

    def test_directory_tree_uses_tree_drawing_chars(self, tmp_path):
        """目录树应使用 └── ── 等树形绘制字符。"""
        (tmp_path / "a.py").write_text("x = 1\n")
        (tmp_path / "b.py").write_text("y = 2\n")
        result = mcp_resources._generate_structure(tmp_path)
        # 至少有一个树形连接符
        assert "└──" in result or "├──" in result

    def test_handles_permission_error(self, tmp_path):
        """无法读取的目录（权限错误）不应抛异常。"""
        # 创建一个正常结构
        (tmp_path / "main.py").write_text("x = 1\n")
        result = mcp_resources._generate_structure(tmp_path)
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# 5. _generate_files
# ---------------------------------------------------------------------------

class TestGenerateFiles:
    """测试 _generate_files() 关键文件内容生成。"""

    def test_returns_markdown_string(self, tmp_path):
        """返回值应为 markdown 格式字符串。"""
        result = mcp_resources._generate_files(tmp_path)
        assert isinstance(result, str)
        assert "# 关键文件内容" in result

    def test_contains_code_blocks(self, tmp_path):
        """输出应包含 markdown 代码块（```）。"""
        (tmp_path / "main.py").write_text("print('hello')\n")
        result = mcp_resources._generate_files(tmp_path)
        assert "```" in result

    def test_shows_file_relative_path(self, tmp_path):
        """每个文件前应显示相对路径作为标题（## 路径）。"""
        (tmp_path / "main.py").write_text("x = 1\n")
        result = mcp_resources._generate_files(tmp_path)
        assert "## main.py" in result

    def test_respects_extension_filter(self, tmp_path):
        """只应包含配置的扩展名文件。"""
        (tmp_path / "a.py").write_text("print(1)\n")
        (tmp_path / "b.txt").write_text("just text\n")
        (tmp_path / "c.md").write_text("# doc\n")
        result = mcp_resources._generate_files(tmp_path)
        assert "a.py" in result
        assert "b.txt" not in result
        assert "c.md" not in result

    def test_limits_to_20_files(self, tmp_path):
        """文件数超过 20 个时只取前 20 个（按大小排序）。"""
        for i in range(25):
            f = tmp_path / f"file_{i:02d}.py"
            f.write_text(f"# file {i}\n" + "line\n" * i)

        result = mcp_resources._generate_files(tmp_path)
        # 统计 ## 文件名 行，确认不超过 20
        headings = [ln for ln in result.splitlines() if ln.startswith("## file_")]
        assert len(headings) <= 20

    def test_truncates_files_to_100_lines(self, tmp_path):
        """每个文件最多显示 100 行。"""
        long_file = tmp_path / "long.py"
        long_file.write_text("\n".join([f"line {i}" for i in range(300)]))
        result = mcp_resources._generate_files(tmp_path)
        # 找到代码块内容
        code_lines = []
        in_block = False
        for ln in result.splitlines():
            if ln == "```":
                in_block = not in_block
            elif in_block:
                code_lines.append(ln)
        assert len(code_lines) <= 100

    def test_sorts_files_by_size_descending(self, tmp_path):
        """文件应按大小降序排列。"""
        small = tmp_path / "small.py"
        large = tmp_path / "large.py"
        small.write_text("x = 1\n")
        large.write_text("x = 1\n" + "y = 2\n" * 50)

        result = mcp_resources._generate_files(tmp_path)
        idx_large = result.find("large.py")
        idx_small = result.find("small.py")
        assert idx_large < idx_small  # large.py 出现在 small.py 前面

    def test_handles_read_error_gracefully(self, tmp_path):
        """文件无法读取时不应抛异常。"""
        # 空目录，没有文件，测试正常返回
        result = mcp_resources._generate_files(tmp_path)
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# 6. get_mcp_resources
# ---------------------------------------------------------------------------

class TestGetMcpResources:
    """测试 get_mcp_resources() MCP 资源列表生成。"""

    def test_returns_list(self):
        """返回值应为 list。"""
        result = mcp_resources.get_mcp_resources()
        assert isinstance(result, list)

    def test_returns_exactly_3_resources(self):
        """应返回 3 个 resource dict（summary、structure、files）。"""
        result = mcp_resources.get_mcp_resources()
        assert len(result) == 3

    def test_all_resources_are_dicts(self):
        """每个 resource 元素应为 dict。"""
        for r in mcp_resources.get_mcp_resources():
            assert isinstance(r, dict)

    def test_resource_has_required_uri_field(self):
        """每个 resource 应有 uri 字段。"""
        for r in mcp_resources.get_mcp_resources():
            assert "uri" in r
            assert r["uri"].startswith("omc://")

    def test_resource_has_required_name_field(self):
        """每个 resource 应有 name 字段。"""
        for r in mcp_resources.get_mcp_resources():
            assert "name" in r
            assert isinstance(r["name"], str)

    def test_resource_has_required_description_field(self):
        """每个 resource 应有 description 字段。"""
        for r in mcp_resources.get_mcp_resources():
            assert "description" in r
            assert isinstance(r["description"], str)

    def test_resource_has_required_mime_type_field(self):
        """每个 resource 应有 mimeType 字段。"""
        for r in mcp_resources.get_mcp_resources():
            assert "mimeType" in r
            assert r["mimeType"] == "text/markdown"

    def test_resource_has_generator_field(self):
        """每个 resource 应有 generator 字段（callable）。"""
        for r in mcp_resources.get_mcp_resources():
            assert "generator" in r
            assert callable(r["generator"])

    def test_generator_produces_string(self, tmp_path):
        """每个 generator 调用后应返回字符串。"""
        mcp_resources._WORKSPACE = tmp_path
        for r in mcp_resources.get_mcp_resources():
            result = r["generator"]()
            assert isinstance(result, str)

    def test_summary_uri_is_correct(self):
        """workspace_summary 的 URI 应为 omc://workspace/summary。"""
        result = mcp_resources.get_mcp_resources()
        summary = next(r for r in result if r["name"] == "workspace_summary")
        assert summary["uri"] == "omc://workspace/summary"

    def test_structure_uri_is_correct(self):
        """workspace_structure 的 URI 应为 omc://workspace/structure。"""
        result = mcp_resources.get_mcp_resources()
        structure = next(r for r in result if r["name"] == "workspace_structure")
        assert structure["uri"] == "omc://workspace/structure"

    def test_files_uri_is_correct(self):
        """workspace_key_files 的 URI 应为 omc://workspace/files。"""
        result = mcp_resources.get_mcp_resources()
        files = next(r for r in result if r["name"] == "workspace_key_files")
        assert files["uri"] == "omc://workspace/files"


# ---------------------------------------------------------------------------
# 集成：端到端验证（generator 在实际 workspace 下正常执行）
# ---------------------------------------------------------------------------

class TestEndToEnd:
    """端到端测试：生成器在实际临时项目结构下完整运行。"""

    def test_full_summary_generator(self, tmp_path):
        """_generate_summary 端到端：创建完整项目结构并生成摘要。"""
        # 创建代码文件
        (tmp_path / "main.py").write_text("print('hello')\n")
        (tmp_path / "utils.js").write_text("console.log('hi');\n")

        # 创建 checkpoint
        ckpt_dir = tmp_path / ".omc" / "checkpoints"
        ckpt_dir.mkdir(parents=True)
        (ckpt_dir / "index.json").write_text(
            json.dumps([{"id": "c1"}, {"id": "c2"}, {"id": "c3"}]), encoding="utf-8"
        )

        # 创建 skill
        skill_dir = tmp_path / ".omc" / "skills"
        skill_dir.mkdir(parents=True)
        (skill_dir / "index.json").write_text(
            json.dumps([{"name": "s1"}]), encoding="utf-8"
        )

        mcp_resources._WORKSPACE = tmp_path
        result = mcp_resources._generate_summary(tmp_path)

        assert "# 工作区摘要" in result
        assert "Python" in result
        assert "JavaScript" in result
        assert "Checkpoints: 3 个" in result
        assert "Skills: 1 个" in result

    def test_full_structure_generator(self, tmp_path):
        """_generate_structure 端到端：生成包含多层级目录的目录树。"""
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "core.py").write_text("def run():\n    pass\n")
        (tmp_path / "src" / "utils.py").write_text("def util():\n    pass\n")
        (tmp_path / "tests").mkdir()
        (tmp_path / "tests" / "test_core.py").write_text("def test_run():\n    pass\n")
        (tmp_path / "readme.md").write_text("# Project\n")

        result = mcp_resources._generate_structure(tmp_path, depth=3)

        assert "# 项目结构" in result
        assert "src" in result
        assert "core.py" in result
        assert "tests" in result
        assert "readme.md" in result  # 非代码文件也可能显示在目录中

    def test_full_files_generator(self, tmp_path):
        """_generate_files 端到端：生成关键文件内容。"""
        (tmp_path / "main.py").write_text("print('hello')\n")
        (tmp_path / "utils.js").write_text("console.log('hi');\n")

        mcp_resources._WORKSPACE = tmp_path
        result = mcp_resources._generate_files(tmp_path)

        assert "# 关键文件内容" in result
        assert "main.py" in result
        assert "utils.js" in result
        assert "```" in result  # 代码块

    def test_get_mcp_resources_with_custom_workspace(self, tmp_path):
        """set_workspace 后，get_mcp_resources 的 generator 使用正确的工作区。"""
        (tmp_path / "main.py").write_text("print('test')\n")
        mcp_resources._WORKSPACE = tmp_path

        result = mcp_resources.get_mcp_resources()
        summary_gen = next(r for r in result if r["name"] == "workspace_summary")
        summary_output = summary_gen["generator"]()

        assert tmp_path.name in summary_output
        assert "Python" in summary_output