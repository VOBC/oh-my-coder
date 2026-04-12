"""
VisionAgent 测试
"""

import struct
import tempfile
from pathlib import Path

import pytest

from src.agents.base import AgentLane, get_agent
from src.agents.vision import (
    VisionAgent,
    _default_filename,
    _extract_code_blocks,
    _infer_output_dir,
    _load_image_meta,
)


# ---------------------------------------------------------------------------
# 辅助函数测试
# ---------------------------------------------------------------------------


class TestExtractCodeBlocks:
    """测试代码块提取"""

    def test_basic_html_block(self):
        text = "```html:index.html\n<!DOCTYPE html>\n</html>\n```"
        blocks = _extract_code_blocks(text)
        assert len(blocks) == 1
        assert blocks[0]["language"] == "html"
        assert blocks[0]["filename"] == "index.html"
        assert "<!DOCTYPE html>" in blocks[0]["code"]

    def test_multiple_blocks(self):
        text = """```html:index.html
<html></html>
```
```css:style.css
body { margin: 0; }
```
```tsx:App.tsx
const App = () => <div />;
```"""
        blocks = _extract_code_blocks(text)
        assert len(blocks) == 3
        assert blocks[0]["filename"] == "index.html"
        assert blocks[1]["filename"] == "style.css"
        assert blocks[2]["filename"] == "App.tsx"

    def test_no_language(self):
        text = "```\ncode without language\n```"
        blocks = _extract_code_blocks(text)
        assert len(blocks) == 1
        assert blocks[0]["language"] == "text"

    def test_no_filename_uses_default(self):
        text = "```tsx\nconst x = 1;\n```"
        blocks = _extract_code_blocks(text)
        assert len(blocks) == 1
        assert blocks[0]["filename"] == "Component.tsx"

    def test_python_with_path(self):
        text = "```python:src/utils/helper.py\ndef foo(): pass\n```"
        blocks = _extract_code_blocks(text)
        assert len(blocks) == 1
        assert blocks[0]["filename"] == "src/utils/helper.py"
        assert blocks[0]["language"] == "python"

    def test_empty_input(self):
        assert _extract_code_blocks("no code here") == []


class TestDefaultFilename:
    """测试默认文件名推断"""

    def test_all_formats(self):
        assert _default_filename("html") == "index.html"
        assert _default_filename("css") == "style.css"
        assert _default_filename("js") == "script.js"
        assert _default_filename("jsx") == "Component.jsx"
        assert _default_filename("tsx") == "Component.tsx"
        assert _default_filename("vue") == "Component.vue"
        assert _default_filename("svelte") == "Component.svelte"
        assert _default_filename("svg") == "icon.svg"
        assert _default_filename("python") == "generated.py"
        assert _default_filename("json") == "data.json"
        assert _default_filename("unknown_lang") == "generated.unknown_lang"


class TestInferOutputDir:
    """测试输出目录推断"""

    def test_working_directory_takes_precedence(self, tmp_path):
        from src.agents.base import AgentContext

        work_dir = tmp_path / "work"
        work_dir.mkdir()
        proj_dir = tmp_path / "project"
        proj_dir.mkdir()

        context = AgentContext(
            project_path=proj_dir,
            task_description="test",
            working_directory=work_dir,
        )
        assert _infer_output_dir(context) == work_dir

    def test_falls_back_to_project_path(self, tmp_path):
        from src.agents.base import AgentContext

        proj_dir = tmp_path / "project"
        proj_dir.mkdir()

        context = AgentContext(
            project_path=proj_dir,
            task_description="test",
        )
        assert _infer_output_dir(context) == proj_dir

    def test_falls_back_to_cwd(self):
        from src.agents.base import AgentContext

        context = AgentContext(
            project_path=Path("/nonexistent"),
            task_description="test",
        )
        result = _infer_output_dir(context)
        assert result.name == "vision_output"


# ---------------------------------------------------------------------------
# 图片元数据测试
# ---------------------------------------------------------------------------


class TestImageMetadata:
    """测试图片元数据提取（纯标准库，无需 Pillow）"""

    @pytest.fixture
    def temp_png(self):
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            path = Path(f.name)
        yield path
        path.unlink(missing_ok=True)

    @pytest.fixture
    def temp_jpg(self):
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            path = Path(f.name)
        yield path
        path.unlink(missing_ok=True)

    def test_png_metadata(self, temp_png):
        """PNG 文件元数据提取"""
        png = (
            b"\x89PNG\r\n\x1a\n"
            b"\x00\x00\x00\rIHDR"
            + struct.pack(">I", 100)
            + struct.pack(">I", 200)
            + b"\x08\x02\x00\x00\x00"
            b"\x00\x00\x00\x00IEND"
        )
        temp_png.write_bytes(png)

        meta = _load_image_meta(temp_png)
        assert meta is not None
        assert meta["format"] == "PNG"
        assert meta["width"] == 100
        assert meta["height"] == 200
        assert meta["path"] == str(temp_png)

    def test_jpeg_metadata(self, temp_jpg):
        """JPEG 文件元数据提取"""
        jpg = (
            b"\xff\xd8"  # SOI
            b"\xff\xc0"  # SOF0 marker
            b"\x00"  # discarded by f.read(1)
            b"\x01\x2c"  # height = 300 (bytes 5-6)
            b"\x01\x90"  # width = 400 (bytes 7-8)
            b"\x00\x00"  # padding
            b"\xff\xd9"  # EOI
        )
        temp_jpg.write_bytes(jpg)

        meta = _load_image_meta(temp_jpg)
        assert meta is not None
        assert meta["format"] == "JPEG"
        assert meta["height"] == 300, f"expected 300, got {meta['height']}"
        assert meta["width"] == 400, f"expected 400, got {meta['width']}"

    def test_unknown_format(self):
        """未知格式返回 unknown"""
        with tempfile.NamedTemporaryFile(suffix=".xyz", delete=False) as f:
            path = Path(f.name)
            f.write(b"not an image")
        try:
            meta = _load_image_meta(path)
            assert meta is not None
            assert meta["format"] == "unknown"
        finally:
            path.unlink(missing_ok=True)

    def test_nonexistent_file(self):
        """不存在的文件返回 None"""
        meta = _load_image_meta(Path("/nonexistent/file.png"))
        assert meta is None


# ---------------------------------------------------------------------------
# VisionAgent 元数据和注册测试
# ---------------------------------------------------------------------------


class TestVisionAgentMetadata:
    """测试 VisionAgent 元数据和注册"""

    def test_vision_agent_registered(self):
        """VisionAgent 已正确注册"""
        cls = get_agent("vision")
        assert cls is not None
        assert cls == VisionAgent

    def test_vision_agent_metadata(self):
        """元数据正确"""
        agent = VisionAgent.__new__(VisionAgent)
        assert agent.name == "vision"
        assert agent.icon == "\U0001f441\ufe0f"
        assert agent.lane == AgentLane.DOMAIN
        assert agent.default_tier == "medium"
        assert "file_read" in agent.tools
        assert "file_write" in agent.tools

    def test_vision_agent_system_prompt(self):
        """system_prompt 包含关键分析维度"""
        agent = VisionAgent.__new__(VisionAgent)
        prompt = agent.system_prompt
        assert "布局" in prompt
        assert "配色" in prompt
        assert "交互" in prompt
        assert "P0" in prompt
        assert "P1" in prompt
        assert "P2" in prompt
        assert "视觉审查报告" in prompt

    def test_vision_agent_system_prompt_ui_code_mode(self):
        """system_prompt 包含 UI 代码生成模式"""
        agent = VisionAgent.__new__(VisionAgent)
        prompt = agent.system_prompt
        assert "UI 代码生成" in prompt
        assert "html:index.html" in prompt
        assert "tsx" in prompt
        assert "Flexbox" in prompt

    def test_mode_constants(self):
        """模式常量正确"""
        agent = VisionAgent.__new__(VisionAgent)
        assert agent.MODE_ANALYSIS == "analysis"
        assert agent.MODE_UI_CODE == "ui_code"

    def test_description_contains_ui_code(self):
        """description 包含 UI 代码生成描述"""
        agent = VisionAgent.__new__(VisionAgent)
        assert "UI 代码生成" in agent.description

    def test_post_process_analysis_mode(self):
        """后处理（分析模式）返回正确的 AgentOutput"""
        from src.agents.base import AgentStatus

        agent = VisionAgent.__new__(VisionAgent)
        agent.name = "vision"
        from src.agents.base import AgentContext

        context = AgentContext(
            project_path=Path("/tmp"),
            task_description="test",
            metadata={"output_format": VisionAgent.MODE_ANALYSIS},
        )
        output = agent._post_process("分析结果", context)
        assert output.status == AgentStatus.COMPLETED
        assert output.result == "分析结果"
        assert "应用视觉修改建议" in output.recommendations[0]

    def test_post_process_ui_code_mode(self):
        """后处理（UI 代码生成模式）返回正确的推荐"""
        from src.agents.base import AgentStatus

        agent = VisionAgent.__new__(VisionAgent)
        agent.name = "vision"
        from src.agents.base import AgentContext

        context = AgentContext(
            project_path=Path("/tmp"),
            task_description="test",
            metadata={"output_format": VisionAgent.MODE_UI_CODE},
        )
        output = agent._post_process("生成完毕", context)
        assert output.status == AgentStatus.COMPLETED
        assert "浏览器中打开" in output.recommendations[0]
        assert output.artifacts is not None
