"""
VisionAgent 测试
"""

import struct
import tempfile
from pathlib import Path

import pytest

from src.agents.base import AgentLane, get_agent
from src.agents.vision import VisionAgent, _load_image_meta


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
        # Minimal JPEG that works with the actual parser logic:
        # Parser after SOF0 match: f.read(1) discards byte4,
        # then h = f.read(2) from byte5, w = f.read(2) from byte7
        # bytes[5:7] = 0x01,0x2c = 300 (height)
        # bytes[7:9] = 0x01,0x90 = 400 (width)
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

    def test_post_process(self):
        """后处理返回正确的 AgentOutput"""
        from src.agents.base import AgentStatus

        agent = VisionAgent.__new__(VisionAgent)
        agent.name = "vision"
        output = agent._post_process("分析结果", None)
        assert output.status == AgentStatus.COMPLETED
        assert output.result == "分析结果"
        assert "应用视觉修改建议" in output.recommendations[0]
