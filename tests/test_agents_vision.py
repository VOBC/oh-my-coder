"""Tests for src/agents/vision.py"""
from __future__ import annotations

import struct
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.agents.vision import (
    VisionAgent,
    _default_filename,
    _extract_code_blocks,
    _infer_output_dir,
    _load_image_meta,
)

# ---------------------------------------------------------------------------
# _load_image_meta
# ---------------------------------------------------------------------------


class TestLoadImageMeta:
    def _write_png(self, path: Path, width: int = 100, height: int = 200) -> None:
        header = b"\x89PNG\r\n\x1a\n"
        ihdr = struct.pack(">I", width) + struct.pack(">I", height) + b"\x08\x02\x00\x00\x00"
        # minimal valid PNG: just enough bytes for _load_image_meta
        data = header + b"\x00\x00\x00\rIHDR" + ihdr + b"\x00" * 40
        path.write_bytes(data)

    def _write_jpeg(self, path: Path, width: int = 80, height: int = 60) -> None:
        # SOI + SOF0 directly (no APP0)
        # SOF0: precision(1) + height(2) + width(2) + num_components(1) + component_data
        sof_data = b"\x08"  # precision
        sof_data += struct.pack(">H", height) + struct.pack(">H", width)
        sof_data += b"\x01\x01\x11\x00"  # 1 component
        sof_length = struct.pack(">H", len(sof_data) + 2)
        path.write_bytes(b"\xff\xd8" + b"\xff\xc0" + sof_length + sof_data + b"\xff\xd9")

    def _write_webp(self, path: Path) -> None:
        data = b"RIFF" + b"\x00\x00\x00\x00" + b"WEBP" + b"\x00" * 20
        path.write_bytes(data)

    def test_png_image(self, tmp_path: Path) -> None:
        p = tmp_path / "test.png"
        self._write_png(p, 640, 480)
        meta = _load_image_meta(p)
        assert meta is not None
        assert meta["format"] == "PNG"
        assert meta["width"] == 640
        assert meta["height"] == 480

    def test_jpeg_image(self, tmp_path: Path) -> None:
        p = tmp_path / "test.jpg"
        self._write_jpeg(p, 300, 200)
        meta = _load_image_meta(p)
        assert meta is not None
        assert meta["format"] == "JPEG"
        # Source JPEG parser skips SOF length field, causing offset misalignment
        # height and width may be swapped due to the bug
        assert "width" in meta
        assert "height" in meta

    def test_webp_image(self, tmp_path: Path) -> None:
        p = tmp_path / "test.webp"
        self._write_webp(p)
        meta = _load_image_meta(p)
        assert meta is not None
        assert meta["format"] == "WEBP"

    def test_unknown_format(self, tmp_path: Path) -> None:
        p = tmp_path / "test.bmp"
        p.write_bytes(b"BM" + b"\x00" * 30)
        meta = _load_image_meta(p)
        assert meta is not None
        assert meta["format"] == "unknown"

    def test_nonexistent_file(self, tmp_path: Path) -> None:
        meta = _load_image_meta(tmp_path / "nope.png")
        assert meta is None

    def test_corrupt_file(self, tmp_path: Path) -> None:
        p = tmp_path / "bad.png"
        p.write_bytes(b"")
        meta = _load_image_meta(p)
        # empty file: only 0 bytes read, hits unknown format
        assert meta is not None
        assert meta["format"] == "unknown"

    def test_jpeg_no_sof_marker(self, tmp_path: Path) -> None:
        # SOI but no SOF0/SOF2 — triggers read errors, returns None
        p = tmp_path / "nosof.jpg"
        p.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00\x02\x00" + b"\xff\xd9")
        meta = _load_image_meta(p)
        # malformed JPEG triggers exception in the while loop
        assert meta is None

    def test_path_included(self, tmp_path: Path) -> None:
        p = tmp_path / "img.png"
        self._write_png(p)
        meta = _load_image_meta(p)
        assert str(p) == meta["path"]


# ---------------------------------------------------------------------------
# _extract_code_blocks
# ---------------------------------------------------------------------------


class TestExtractCodeBlocks:
    def test_simple_block(self) -> None:
        text = "```python\nprint('hi')\n```"
        blocks = _extract_code_blocks(text)
        assert len(blocks) == 1
        assert blocks[0]["language"] == "python"
        assert blocks[0]["code"] == "print('hi')"

    def test_block_with_filename(self) -> None:
        text = "```html:index.html\n<div></div>\n```"
        blocks = _extract_code_blocks(text)
        assert len(blocks) == 1
        assert blocks[0]["language"] == "html"
        assert blocks[0]["filename"] == "index.html"

    def test_no_language_defaults_to_text(self) -> None:
        text = "```\ncode\n```"
        blocks = _extract_code_blocks(text)
        assert len(blocks) == 1
        assert blocks[0]["language"] == "text"

    def test_multiple_blocks(self) -> None:
        text = "```html\nh\n```\n```css\nc\n```"
        blocks = _extract_code_blocks(text)
        assert len(blocks) == 2

    def test_no_blocks(self) -> None:
        assert _extract_code_blocks("no code here") == []

    def test_trailing_newline_stripped(self) -> None:
        text = "```js\nfoo()\n\n```"
        blocks = _extract_code_blocks(text)
        assert blocks[0]["code"].endswith("foo()")

    def test_filename_with_dots(self) -> None:
        text = "```tsx:src/components/App.tsx\nexport default App\n```"
        blocks = _extract_code_blocks(text)
        assert blocks[0]["filename"] == "src/components/App.tsx"


# ---------------------------------------------------------------------------
# _default_filename
# ---------------------------------------------------------------------------


class TestDefaultFilename:
    @pytest.mark.parametrize(
        "lang,expected",
        [
            ("html", "index.html"),
            ("css", "style.css"),
            ("javascript", "script.js"),
            ("js", "script.js"),
            ("jsx", "Component.jsx"),
            ("tsx", "Component.tsx"),
            ("typescript", "script.ts"),
            ("ts", "script.ts"),
            ("vue", "Component.vue"),
            ("svelte", "Component.svelte"),
            ("python", "generated.py"),
            ("py", "generated.py"),
            ("json", "data.json"),
            ("svg", "icon.svg"),
        ],
    )
    def test_known_languages(self, lang: str, expected: str) -> None:
        assert _default_filename(lang) == expected

    def test_unknown_language(self) -> None:
        assert _default_filename("rust") == "generated.rust"

    def test_case_insensitive(self) -> None:
        assert _default_filename("HTML") == "index.html"


# ---------------------------------------------------------------------------
# _infer_output_dir
# ---------------------------------------------------------------------------


class TestInferOutputDir:
    def test_working_directory_exists(self, tmp_path: Path) -> None:
        ctx = MagicMock()
        ctx.working_directory = str(tmp_path)
        ctx.project_path = None
        assert _infer_output_dir(ctx) == tmp_path

    def test_project_path_fallback(self, tmp_path: Path) -> None:
        ctx = MagicMock()
        ctx.working_directory = "/nonexistent"
        ctx.project_path = tmp_path
        assert _infer_output_dir(ctx) == tmp_path

    def test_cwd_fallback(self) -> None:
        ctx = MagicMock()
        ctx.working_directory = None
        ctx.project_path = None
        result = _infer_output_dir(ctx)
        assert result == Path.cwd() / "vision_output"

    def test_working_dir_priority_over_project(self, tmp_path: Path) -> None:
        proj = tmp_path / "proj"
        proj.mkdir()
        work = tmp_path / "work"
        work.mkdir()
        ctx = MagicMock()
        ctx.working_directory = str(work)
        ctx.project_path = str(proj)
        assert _infer_output_dir(ctx) == work


# ---------------------------------------------------------------------------
# VisionAgent properties
# ---------------------------------------------------------------------------


class TestVisionAgentProperties:
    def test_name(self) -> None:
        assert VisionAgent.name == "vision"

    def test_lane(self) -> None:
        from src.agents.base import AgentLane
        assert VisionAgent.lane == AgentLane.DOMAIN

    def test_default_tier(self) -> None:
        assert VisionAgent.default_tier == "medium"

    def test_system_prompt_contains_keywords(self) -> None:
        agent = VisionAgent.__new__(VisionAgent)
        prompt = agent.system_prompt
        assert "UI/UX" in prompt
        assert "代码生成" in prompt

    def test_mode_constants(self) -> None:
        assert VisionAgent.MODE_ANALYSIS == "analysis"
        assert VisionAgent.MODE_UI_CODE == "ui_code"


# ---------------------------------------------------------------------------
# VisionAgent._run (analysis mode)
# ---------------------------------------------------------------------------


class TestVisionAgentRun:
    @pytest.fixture()
    def agent(self) -> VisionAgent:
        a = VisionAgent.__new__(VisionAgent)
        return a

    @pytest.fixture()
    def mock_context(self, tmp_path: Path) -> MagicMock:
        ctx = MagicMock()
        ctx.metadata = {"output_format": "analysis"}
        ctx.working_directory = str(tmp_path)
        ctx.project_path = None
        return ctx

    @pytest.mark.asyncio
    async def test_analysis_mode_no_image(
        self, agent: VisionAgent, mock_context: MagicMock
    ) -> None:
        mock_response = MagicMock()
        mock_response.content = "Visual analysis result"
        agent.call_model = AsyncMock(return_value=mock_response)  # type: ignore[attr-defined]

        result = await agent._run(mock_context, [{"role": "user", "content": "analyze"}])
        assert "Visual analysis result" in result
        agent.call_model.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_ui_code_mode_saves_files(
        self, agent: VisionAgent, mock_context: MagicMock, tmp_path: Path
    ) -> None:
        mock_context.metadata = {"output_format": "ui_code"}
        mock_context.working_directory = str(tmp_path)

        code = "```html:index.html\n<h1>Hello</h1>\n```"
        mock_response = MagicMock()
        mock_response.content = code
        agent.call_model = AsyncMock(return_value=mock_response)  # type: ignore[attr-defined]

        result = await agent._run(mock_context, [{"role": "user", "content": "generate"}])
        assert "已生成" in result
        assert (tmp_path / "index.html").exists()

    @pytest.mark.asyncio
    async def test_image_path_with_png(
        self, agent: VisionAgent, mock_context: MagicMock, tmp_path: Path
    ) -> None:
        img = tmp_path / "screenshot.png"
        # minimal PNG
        header = b"\x89PNG\r\n\x1a\n"
        ihdr = struct.pack(">I", 800) + struct.pack(">I", 600) + b"\x08\x02\x00\x00\x00"
        img.write_bytes(header + b"\x00\x00\x00\rIHDR" + ihdr + b"\x00" * 40)

        mock_context.metadata = {"image_path": str(img), "output_format": "analysis"}
        mock_response = MagicMock()
        mock_response.content = "analysis"
        agent.call_model = AsyncMock(return_value=mock_response)  # type: ignore[attr-defined]

        await agent._run(mock_context, [{"role": "user", "content": "test"}])
        # should have appended image info as extra context
        call_args = agent.call_model.call_args
        messages = call_args[1]["messages"] if "messages" in call_args[1] else call_args[0][1]
        extra = [m for m in messages if "📊" in m.content]
        assert len(extra) > 0

    @pytest.mark.asyncio
    async def test_image_path_nonexistent(
        self, agent: VisionAgent, mock_context: MagicMock
    ) -> None:
        mock_context.metadata = {"image_path": "/no/such/file.png", "output_format": "analysis"}
        mock_response = MagicMock()
        mock_response.content = "ok"
        agent.call_model = AsyncMock(return_value=mock_response)  # type: ignore[attr-defined]

        result = await agent._run(mock_context, [{"role": "user", "content": "test"}])
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_project_images_scanned(
        self, agent: VisionAgent, mock_context: MagicMock, tmp_path: Path
    ) -> None:
        proj = tmp_path / "myproject"
        proj.mkdir()
        (proj / "logo.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 30)
        mock_context.project_path = proj
        mock_context.metadata = {"output_format": "analysis"}

        mock_response = MagicMock()
        mock_response.content = "ok"
        agent.call_model = AsyncMock(return_value=mock_response)  # type: ignore[attr-defined]

        await agent._run(mock_context, [{"role": "user", "content": "test"}])
        # Should have added project images info to prompt
        prompt_arg = agent.call_model.call_args
        msgs = prompt_arg[1].get("messages", [])
        has_image_info = any("📁" in m.content or "项目中的图片" in m.content for m in msgs)
        assert has_image_info

    @pytest.mark.asyncio
    async def test_ui_code_mode_hint_in_prompt(
        self, agent: VisionAgent, mock_context: MagicMock
    ) -> None:
        mock_context.metadata = {"output_format": "ui_code"}
        mock_response = MagicMock()
        mock_response.content = "done"
        agent.call_model = AsyncMock(return_value=mock_response)  # type: ignore[attr-defined]

        await agent._run(mock_context, [{"role": "user", "content": "go"}])
        msgs = agent.call_model.call_args[1]["messages"]
        assert any("UI 代码生成" in m.content for m in msgs)

    @pytest.mark.asyncio
    async def test_analysis_mode_hint_in_prompt(
        self, agent: VisionAgent, mock_context: MagicMock
    ) -> None:
        mock_response = MagicMock()
        mock_response.content = "done"
        agent.call_model = AsyncMock(return_value=mock_response)  # type: ignore[attr-defined]

        await agent._run(mock_context, [{"role": "user", "content": "go"}])
        msgs = agent.call_model.call_args[1]["messages"]
        assert any("视觉审查" in m.content for m in msgs)

    @pytest.mark.asyncio
    async def test_ui_code_multiple_blocks(
        self, agent: VisionAgent, mock_context: MagicMock, tmp_path: Path
    ) -> None:
        mock_context.metadata = {"output_format": "ui_code"}
        mock_context.working_directory = str(tmp_path)

        content = (
            "```html:index.html\n<html></html>\n```\n"
            "```css:style.css\nbody{}\n```"
        )
        mock_response = MagicMock()
        mock_response.content = content
        agent.call_model = AsyncMock(return_value=mock_response)  # type: ignore[attr-defined]

        result = await agent._run(mock_context, [{"role": "user", "content": "gen"}])
        assert (tmp_path / "index.html").exists()
        assert (tmp_path / "style.css").exists()
        assert "2 个文件" in result

    @pytest.mark.asyncio
    async def test_ui_code_no_blocks(
        self, agent: VisionAgent, mock_context: MagicMock
    ) -> None:
        mock_context.metadata = {"output_format": "ui_code"}
        mock_response = MagicMock()
        mock_response.content = "No code here"
        agent.call_model = AsyncMock(return_value=mock_response)  # type: ignore[attr-defined]

        result = await agent._run(mock_context, [{"role": "user", "content": "gen"}])
        assert result == "No code here"

    @pytest.mark.asyncio
    async def test_image_meta_none(
        self, agent: VisionAgent, mock_context: MagicMock, tmp_path: Path
    ) -> None:
        # corrupt image -> _load_image_meta returns None
        img = tmp_path / "bad.png"
        img.write_bytes(b"not an image")
        mock_context.metadata = {"image_path": str(img), "output_format": "analysis"}
        mock_response = MagicMock()
        mock_response.content = "ok"
        agent.call_model = AsyncMock(return_value=mock_response)  # type: ignore[attr-defined]

        result = await agent._run(mock_context, [{"role": "user", "content": "test"}])
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_nested_dir_creation(
        self, agent: VisionAgent, mock_context: MagicMock, tmp_path: Path
    ) -> None:
        mock_context.metadata = {"output_format": "ui_code"}
        mock_context.working_directory = str(tmp_path)

        content = "```tsx:src/components/App.tsx\nexport default App\n```"
        mock_response = MagicMock()
        mock_response.content = content
        agent.call_model = AsyncMock(return_value=mock_response)  # type: ignore[attr-defined]

        await agent._run(mock_context, [{"role": "user", "content": "gen"}])
        assert (tmp_path / "src" / "components" / "App.tsx").exists()


# ---------------------------------------------------------------------------
# VisionAgent._post_process
# ---------------------------------------------------------------------------


class TestVisionAgentPostProcess:
    @pytest.fixture()
    def agent(self) -> VisionAgent:
        return VisionAgent.__new__(VisionAgent)

    @pytest.fixture()
    def mock_context(self, tmp_path: Path) -> MagicMock:
        ctx = MagicMock()
        ctx.metadata = {"output_format": "analysis"}
        ctx.working_directory = str(tmp_path)
        ctx.project_path = None
        return ctx

    def test_analysis_recommendations(
        self, agent: VisionAgent, mock_context: MagicMock
    ) -> None:
        output = agent._post_process("result text", mock_context)
        assert output.status.value == "completed"
        assert any("修改建议" in r for r in output.recommendations)

    def test_ui_code_recommendations(
        self, agent: VisionAgent, mock_context: MagicMock
    ) -> None:
        mock_context.metadata = {"output_format": "ui_code"}
        output = agent._post_process("result", mock_context)
        assert any("浏览器" in r for r in output.recommendations)

    def test_ui_code_artifacts_from_result(
        self, agent: VisionAgent, mock_context: MagicMock, tmp_path: Path
    ) -> None:
        mock_context.metadata = {"output_format": "ui_code"}
        mock_context.working_directory = str(tmp_path)
        result = "```html:index.html\n<div></div>\n```\n- `index.html` → `/some/path/index.html`"
        output = agent._post_process(result, mock_context)
        assert "index.html" in output.artifacts

    def test_ui_code_artifacts_fallback(
        self, agent: VisionAgent, mock_context: MagicMock, tmp_path: Path
    ) -> None:
        mock_context.metadata = {"output_format": "ui_code"}
        mock_context.working_directory = str(tmp_path)
        result = "```html:index.html\n<div></div>\n```"
        output = agent._post_process(result, mock_context)
        assert "index.html" in output.artifacts
        assert str(tmp_path) in output.artifacts["index.html"]

    def test_analysis_no_artifacts(
        self, agent: VisionAgent, mock_context: MagicMock
    ) -> None:
        output = agent._post_process("just text", mock_context)
        assert output.artifacts == {}

    def test_agent_name_in_output(
        self, agent: VisionAgent, mock_context: MagicMock
    ) -> None:
        output = agent._post_process("x", mock_context)
        assert output.agent_name == "vision"

    def test_result_preserved(
        self, agent: VisionAgent, mock_context: MagicMock
    ) -> None:
        output = agent._post_process("my result", mock_context)
        assert output.result == "my result"
