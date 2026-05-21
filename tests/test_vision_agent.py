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


# ---------------------------------------------------------------------------
# VisionAgent._run 集成测试（mock call_model）
# ---------------------------------------------------------------------------

from unittest.mock import AsyncMock, MagicMock, patch

from src.agents.base import AgentContext, AgentStatus
from src.agents.vision import VisionAgent
from src.models.base import Message


class TestVisionAgentRun:
    """测试 VisionAgent._run 方法"""

    def _make_agent(self):
        """创建未初始化 agent"""
        agent = VisionAgent.__new__(VisionAgent)
        agent.name = "vision"
        agent.MODE_ANALYSIS = "analysis"
        agent.MODE_UI_CODE = "ui_code"
        return agent

    @pytest.mark.asyncio
    async def test_run_analysis_mode_no_image(self):
        """分析模式 + 无图片：直接调用模型"""
        agent = self._make_agent()
        context = AgentContext(
            project_path=Path("/nonexistent"),
            task_description="分析截图",
            metadata={"output_format": "analysis"},
        )
        prompt = [{"role": "user", "content": "请分析这张截图"}]
        mock_resp = MagicMock(content="这是视觉审查报告")

        async def fake_call_model(task_type, messages):
            return mock_resp

        with patch.object(agent, "call_model", side_effect=fake_call_model):
            result = await agent._run(context, prompt)

        assert "这是视觉审查报告" in result
        # 分析模式不写入文件
        assert not result.startswith("Traceback")

    @pytest.mark.asyncio
    async def test_run_analysis_mode_with_image(self):
        """分析模式 + 有图片：注入元数据"""
        agent = self._make_agent()
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            path = Path(f.name)
        png = (
            b"\x89PNG\r\n\x1a\n"
            b"\x00\x00\x00\rIHDR"
            + struct.pack(">I", 800)
            + struct.pack(">I", 600)
            + b"\x08\x02\x00\x00\x00"
            + b"\x00\x00\x00\x00IEND"
        )
        path.write_bytes(png)
        try:
            context = AgentContext(
                project_path=Path("/nonexistent"),
                task_description="分析截图",
                metadata={"output_format": "analysis", "image_path": str(path)},
            )
            prompt = [{"role": "user", "content": "请分析"}]
            mock_resp = MagicMock(content="分析报告")

            async def fake_call_model(task_type, messages):
                return mock_resp

            with patch.object(agent, "call_model", side_effect=fake_call_model):
                result = await agent._run(context, prompt)
            assert "分析报告" in result
        finally:
            path.unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_run_analysis_mode_project_with_images(self, tmp_path):
        """分析模式 + 项目目录含图片：注入图片列表"""
        agent = self._make_agent()
        # 在项目中放几张图片
        img_dir = tmp_path / "assets"
        img_dir.mkdir()
        (img_dir / "hero.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 30)
        (img_dir / "bg.jpg").write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 20)

        context = AgentContext(
            project_path=tmp_path,
            task_description="分析",
            metadata={"output_format": "analysis"},
        )
        prompt = [{"role": "user", "content": "分析"}]
        mock_resp = MagicMock(content="报告")

        async def fake_call_model(task_type, messages):
            # 检查是否注入了图片文件信息
            sys_msg = next(
                (m.content for m in messages if m.role == "system"), ""
            )
            assert "项目中的图片文件" in sys_msg
            return mock_resp

        with patch.object(agent, "call_model", side_effect=fake_call_model):
            await agent._run(context, prompt)

    @pytest.mark.asyncio
    async def test_run_ui_code_mode_saves_files(self, tmp_path):
        """UI 代码模式：提取代码块并写入文件"""
        agent = self._make_agent()
        context = AgentContext(
            project_path=tmp_path,
            task_description="生成 UI",
            metadata={"output_format": "ui_code"},
        )
        prompt = [{"role": "user", "content": "生成代码"}]
        mock_resp = MagicMock(
            content="""这里有一些描述。

```html:index.html
<!DOCTYPE html>
<html><body>Hello</body></html>
```

```css:style.css
body { margin: 0; }
```
"""
        )

        async def fake_call_model(task_type, messages):
            return mock_resp

        with patch.object(agent, "call_model", side_effect=fake_call_model):
            result = await agent._run(context, prompt)

        assert (tmp_path / "index.html").exists()
        assert (tmp_path / "style.css").exists()
        assert "已生成" in result
        assert "index.html" in result

    @pytest.mark.asyncio
    async def test_run_ui_code_mode_no_blocks_no_files(self, tmp_path):
        """UI 代码模式但无代码块：不写文件"""
        agent = self._make_agent()
        context = AgentContext(
            project_path=tmp_path,
            task_description="生成 UI",
            metadata={"output_format": "ui_code"},
        )
        prompt = [{"role": "user", "content": "生成"}]
        mock_resp = MagicMock(content="我无法生成代码，因为没有提供截图。")

        async def fake_call_model(task_type, messages):
            return mock_resp

        with patch.object(agent, "call_model", side_effect=fake_call_model):
            result = await agent._run(context, prompt)

        assert result == "我无法生成代码，因为没有提供截图。"
        # 无文件写入
        assert len(list(tmp_path.iterdir())) == 0

    @pytest.mark.asyncio
    async def test_run_ui_code_with_subpath_file(self, tmp_path):
        """UI 代码模式：文件路径含子目录（如 src/components/Button.tsx）"""
        agent = self._make_agent()
        context = AgentContext(
            project_path=tmp_path,
            task_description="生成",
            metadata={"output_format": "ui_code"},
        )
        prompt = [{"role": "user", "content": "生成"}]
        mock_resp = MagicMock(
            content="""```tsx:src/components/Button.tsx
export const Button = () => <button>Click</button>;
```
"""
        )

        async def fake_call_model(task_type, messages):
            return mock_resp

        with patch.object(agent, "call_model", side_effect=fake_call_model):
            result = await agent._run(context, prompt)

        assert (tmp_path / "src" / "components" / "Button.tsx").exists()


# ---------------------------------------------------------------------------
# _post_process 边界情况
# ---------------------------------------------------------------------------

class TestPostProcessEdgeCases:
    """测试 _post_process 边界情况"""

    def _make_agent(self):
        agent = VisionAgent.__new__(VisionAgent)
        agent.name = "vision"
        agent.MODE_ANALYSIS = "analysis"
        agent.MODE_UI_CODE = "ui_code"
        return agent

    def test_post_process_ui_code_extracts_artifacts(self, tmp_path):
        """UI 模式：从结果中提取 artifacts 路径"""
        agent = self._make_agent()
        context = AgentContext(
            project_path=tmp_path,
            task_description="生成",
            metadata={"output_format": "ui_code"},
        )
        # 结果包含文件路径
        result = """```tsx:App.tsx
export const App = () => null;
```
---
📁 已生成 1 个文件:
- `App.tsx` → `/tmp/abc/App.tsx`
**输出目录**: `/tmp/abc`
"""
        output = agent._post_process(result, context)
        assert "App.tsx" in output.artifacts

    def test_post_process_ui_code_fallback_artifacts(self):
        """UI 模式：结果中无路径时，用 output_dir 补全"""
        agent = self._make_agent()
        context = AgentContext(
            project_path=Path("/tmp/nonexistent"),
            task_description="test",
            metadata={"output_format": "ui_code"},
        )
        result = """```tsx:Button.tsx
export const Button = () => <button />;
```"""
        output = agent._post_process(result, context)
        assert "Button.tsx" in output.artifacts
        # 路径应该指向 vision_output 目录
        assert "Button.tsx" in output.artifacts["Button.tsx"]

    def test_post_process_analysis_no_artifacts(self):
        """分析模式：artifacts 为空 dict"""
        agent = self._make_agent()
        context = AgentContext(
            project_path=Path("/tmp"),
            task_description="test",
            metadata={"output_format": "analysis"},
        )
        output = agent._post_process("分析完成", context)
        assert output.artifacts == {}

    def test_post_process_analysis_no_recommendations(self):
        """分析模式：推荐内容正确"""
        agent = self._make_agent()
        agent.name = "vision"
        context = AgentContext(
            project_path=Path("/tmp"),
            task_description="test",
            metadata={"output_format": "analysis"},
        )
        output = agent._post_process("完成", context)
        assert len(output.recommendations) == 2
        assert "应用视觉修改建议" in output.recommendations[0]


# ---------------------------------------------------------------------------
# WebP 格式测试
# ---------------------------------------------------------------------------

class TestImageMetadataWebP:
    """测试 WebP 格式识别"""

    def test_webp_format(self):
        """WebP 文件返回正确的格式信息"""
        with tempfile.NamedTemporaryFile(suffix=".webp", delete=False) as f:
            path = Path(f.name)
            # RIFF header + WEBP chunk
            path.write_bytes(b"RIFF" + b"\x00\x00\x00\x00" + b"WEBP" + b"VP8 " + b"\x00" * 20)
        try:
            meta = _load_image_meta(path)
            assert meta is not None
            assert meta["format"] == "WEBP"
        finally:
            path.unlink(missing_ok=True)

    def test_png_no_size_if_truncated(self):
        """PNG 文件元数据截断时返回 None"""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            path = Path(f.name)
            # 文件太短，无法读取完整 IHDR
            path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 10)
        try:
            meta = _load_image_meta(path)
            # 读取时会尝试 struct.unpack，可能抛出异常，被 except 捕获
            assert meta is None
        finally:
            path.unlink(missing_ok=True)

    def test_jpeg_no_sof_returns_partial_or_none(self):
        """JPEG 无 SOF 标记时可能返回部分元数据或 None（取决于文件结构）"""
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            path = Path(f.name)
            # SOI + APP0 + EOI，无 SOF
            path.write_bytes(b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xd9")
        try:
            meta = _load_image_meta(path)
            # 此结构下返回 None（读完 APP0 后遇到截断的 EOI）
            assert meta is None
        finally:
            path.unlink(missing_ok=True)
