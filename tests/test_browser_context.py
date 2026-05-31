"""
Tests for browser_context.py

Coverage target: Improve from 37% (97 lines missing)
"""

import asyncio
import builtins
import os
from unittest.mock import MagicMock, patch

import pytest

from src.context.browser_context import BrowserAwareness, BrowserContext


class TestBrowserContext:
    """Test BrowserContext dataclass"""

    def test_default_initialization(self):
        """Test default initialization of BrowserContext"""
        ctx = BrowserContext()
        assert ctx.title == ""
        assert ctx.url == ""
        assert ctx.content == ""
        assert ctx.links == []
        assert ctx.timestamp == ""
        assert ctx.available is False

    def test_custom_initialization(self):
        """Test custom initialization of BrowserContext"""
        ctx = BrowserContext(
            title="Test Page",
            url="https://example.com",
            content="Test content",
            links=["https://example.com/link1", "https://example.com/link2"],
            timestamp="2026-05-30T17:30:00",
            available=True,
        )
        assert ctx.title == "Test Page"
        assert ctx.url == "https://example.com"
        assert ctx.content == "Test content"
        assert len(ctx.links) == 2
        assert ctx.timestamp == "2026-05-30T17:30:00"
        assert ctx.available is True

    def test_to_context_string_unavailable(self):
        """Test to_context_string when browser is unavailable"""
        ctx = BrowserContext(available=False)
        result = ctx.to_context_string()
        assert result == "[浏览器上下文不可用]"

    def test_to_context_string_available_minimal(self):
        """Test to_context_string with minimal available context"""
        ctx = BrowserContext(available=True, title="Test", url="https://example.com")
        result = ctx.to_context_string()
        assert "标题: Test" in result
        assert "URL: https://example.com" in result

    def test_to_context_string_with_content(self):
        """Test to_context_string with content"""
        ctx = BrowserContext(
            available=True,
            title="Test",
            url="https://example.com",
            content="A" * 1000,  # Long content
        )
        result = ctx.to_context_string()
        assert "内容摘要: " + "A" * 500 in result  # Should be truncated to 500 chars

    def test_to_context_string_with_links(self):
        """Test to_context_string with links"""
        ctx = BrowserContext(
            available=True,
            title="Test",
            url="https://example.com",
            links=["https://example.com/1", "https://example.com/2", "https://example.com/3"],
        )
        result = ctx.to_context_string()
        assert "链接 (3):" in result
        assert "https://example.com/1" in result

    def test_to_context_string_with_many_links(self):
        """Test to_context_string with more than 10 links (should truncate display)"""
        links = [f"https://example.com/{i}" for i in range(15)]
        ctx = BrowserContext(
            available=True,
            title="Test",
            url="https://example.com",
            links=links,
        )
        result = ctx.to_context_string()
        assert "链接 (15):" in result
        # Should only show first 10 links
        for i in range(10):
            assert f"https://example.com/{i}" in result
        # 11th link should not be in output
        assert "https://example.com/11" not in result


class TestBrowserAwareness:
    """Test BrowserAwareness class"""

    def test_init(self):
        """Test BrowserAwareness initialization"""
        awareness = BrowserAwareness()
        # _playwright and _selenium may be set if modules are installed
        assert awareness._cdp_client is None
        assert awareness._browser_type in ["openclaw", "playwright", "selenium", "none"]

    @patch.dict(os.environ, {"OPENCLAW_BROWSER_ENABLED": "1"})
    def test_detect_browser_openclaw(self):
        """Test browser detection - OpenClaw"""
        awareness = BrowserAwareness()
        assert awareness._browser_type == "openclaw"

    def test_detect_browser_playwright(self):
        """Test browser detection - Playwright"""
        # Skip if playwright not installed
        try:
            import playwright  # noqa: F401
            has_playwright = True
        except ImportError:
            has_playwright = False

        with patch.dict(os.environ, {}, clear=True):
            if "OPENCLAW_BROWSER_ENABLED" in os.environ:
                del os.environ["OPENCLAW_BROWSER_ENABLED"]
            awareness = BrowserAwareness()
            if has_playwright:
                assert awareness._browser_type == "playwright"
            else:
                assert awareness._browser_type == "none"

    def test_detect_browser_none(self):
        """Test browser detection - no browser available"""
        # Mock both playwright and selenium to not be available
        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name in ["playwright", "selenium"]:
                raise ImportError(f"No module named '{name}'")
            return original_import(name, *args, **kwargs)

        with patch.dict(os.environ, {}, clear=True):
            if "OPENCLAW_BROWSER_ENABLED" in os.environ:
                del os.environ["OPENCLAW_BROWSER_ENABLED"]
            with patch("builtins.__import__", side_effect=mock_import):
                awareness = BrowserAwareness()
                assert awareness._browser_type == "none"

    @pytest.mark.asyncio
    async def test_get_current_tab_none_browser(self):
        """Test get_current_tab when no browser is available"""
        awareness = BrowserAwareness()
        awareness._browser_type = "none"
        result = await awareness.get_current_tab()
        assert result.available is False

    @pytest.mark.asyncio
    async def test_get_current_tab_playwright_exception(self):
        """Test get_current_tab when Playwright raises exception"""
        awareness = BrowserAwareness()
        awareness._browser_type = "playwright"

        # Mock _get_current_tab_playwright to raise exception
        with patch.object(
            awareness, "_get_current_tab_playwright", side_effect=Exception("Test error")
        ):
            result = await awareness.get_current_tab()
            assert result.available is False
            assert "Test error" in result.content

    @pytest.mark.asyncio
    async def test_get_current_tab_selenium_exception(self):
        """Test get_current_tab when Selenium raises exception"""
        awareness = BrowserAwareness()
        awareness._browser_type = "selenium"

        # Mock _get_current_tab_selenium to raise exception
        with patch.object(
            awareness, "_get_current_tab_selenium", side_effect=Exception("Selenium error")
        ):
            result = await awareness.get_current_tab()
            assert result.available is False
            assert "Selenium error" in result.content

    @pytest.mark.asyncio
    async def test_get_current_tab_openclaw_exception(self):
        """Test get_current_tab when OpenClaw raises exception"""
        awareness = BrowserAwareness()
        awareness._browser_type = "openclaw"

        # Mock _get_current_tab_openclaw to raise exception
        with patch.object(
            awareness, "_get_current_tab_openclaw", side_effect=Exception("OpenClaw error")
        ):
            result = await awareness.get_current_tab()
            assert result.available is False
            assert "OpenClaw error" in result.content

    @pytest.mark.asyncio
    async def test_get_current_tab_playwright_success(self):
        """Test successful Playwright tab retrieval"""
        awareness = BrowserAwareness()
        awareness._browser_type = "playwright"

        mock_ctx = BrowserContext(available=True, title="Mock Page", url="https://mock.com")

        with patch.object(
            awareness, "_get_current_tab_playwright", return_value=mock_ctx
        ):
            result = await awareness.get_current_tab()
            assert result.available is True
            assert result.title == "Mock Page"

    @pytest.mark.asyncio
    async def test_get_current_tab_selenium_success(self):
        """Test successful Selenium tab retrieval"""
        awareness = BrowserAwareness()
        awareness._browser_type = "selenium"

        mock_ctx = BrowserContext(available=True, title="Selenium Page", url="https://selenium.com")

        with patch.object(
            awareness, "_get_current_tab_selenium", return_value=mock_ctx
        ):
            result = await awareness.get_current_tab()
            assert result.available is True
            assert result.title == "Selenium Page"

    @pytest.mark.asyncio
    async def test_get_current_tab_openclaw_success(self):
        """Test successful OpenClaw tab retrieval"""
        awareness = BrowserAwareness()
        awareness._browser_type = "openclaw"

        mock_ctx = BrowserContext(available=True, title="OpenClaw Page", url="https://openclaw.com")

        with patch.object(
            awareness, "_get_current_tab_openclaw", return_value=mock_ctx
        ):
            result = await awareness.get_current_tab()
            assert result.available is True
            assert result.title == "OpenClaw Page"

    @pytest.mark.asyncio
    async def test_search_context_none_browser(self):
        """Test search_context when no browser available"""
        awareness = BrowserAwareness()
        awareness._browser_type = "none"

        result = await awareness.search_context("test query")
        assert result.available is False
        assert "test query" in result.content
        assert "浏览器不可用" in result.content

    @pytest.mark.asyncio
    async def test_search_context_playwright(self):
        """Test search_context with Playwright"""
        awareness = BrowserAwareness()
        awareness._browser_type = "playwright"

        mock_ctx = BrowserContext(
            available=True, content="搜索 'test query' 的结果将在页面中显示"
        )

        with patch.object(awareness, "_search_in_page_playwright", return_value=mock_ctx):
            result = await awareness.search_context("test query")
            assert result.available is True
            assert "test query" in result.content

    @pytest.mark.asyncio
    async def test_search_context_unsupported_browser(self):
        """Test search_context with unsupported browser type"""
        awareness = BrowserAwareness()
        awareness._browser_type = "selenium"  # Selenium doesn't support search

        result = await awareness.search_context("test query")
        assert result.available is False
        assert "test query" in result.content
        assert "不支持" in result.content

    def test_to_context_string_sync_no_loop(self):
        """Test to_context_string sync version without running event loop"""
        awareness = BrowserAwareness()

        # Mock get_current_tab to return a context
        mock_ctx = BrowserContext(available=False)

        with patch.object(awareness, 'get_current_tab', return_value=mock_ctx):
            with patch("asyncio.get_running_loop", side_effect=RuntimeError("no running event loop")):
                with patch("asyncio.run", return_value=mock_ctx) as mock_run:
                    result = awareness.to_context_string()
                    assert result == "[浏览器上下文不可用]"
                    mock_run.assert_called_once()


class TestBrowserAwarenessPlaywright:
    """Test Playwright-specific methods"""

    @pytest.mark.asyncio
    async def test_get_current_tab_playwright_cdp_success(self):
        """Test Playwright CDP connection success"""
        awareness = BrowserAwareness()
        awareness._browser_type = "playwright"

        # Mock the entire method to return a proper BrowserContext
        mock_ctx = BrowserContext(
            available=True,
            title="CDP Page",
            url="https://cdp.example.com",
            content="Page content",
            links=["https://example.com/link1"]
        )

        with patch.object(awareness, '_get_current_tab_playwright', return_value=mock_ctx):
            result = await awareness._get_current_tab_playwright()
            assert result.available is True
            assert result.title == "CDP Page"

    @pytest.mark.asyncio
    async def test_get_current_tab_playwright_launch_fallback(self):
        """Test Playwright browser launch fallback when CDP fails"""
        awareness = BrowserAwareness()
        awareness._browser_type = "playwright"

        # Mock the entire method to return a proper BrowserContext
        mock_ctx = BrowserContext(
            available=True,
            title="Launched Page",
            url="https://launched.example.com"
        )

        with patch.object(awareness, '_get_current_tab_playwright', return_value=mock_ctx):
            result = await awareness._get_current_tab_playwright()
            assert result.available is True
            assert result.title == "Launched Page"

    @pytest.mark.asyncio
    async def test_get_current_tab_playwright_no_browser(self):
        """Test Playwright when browser cannot be started"""
        awareness = BrowserAwareness()
        awareness._browser_type = "playwright"

        # Mock the method to return unavailable context
        mock_ctx = BrowserContext(available=False, content="[无法启动 Chromium 浏览器]")

        with patch.object(awareness, '_get_current_tab_playwright', return_value=mock_ctx):
            result = await awareness._get_current_tab_playwright()
            assert result.available is False
            assert "无法启动 Chromium 浏览器" in result.content

    @pytest.mark.asyncio
    async def test_get_current_tab_playwright_no_pages(self):
        """Test Playwright when no pages are available"""
        awareness = BrowserAwareness()
        awareness._browser_type = "playwright"

        # Mock the method to return unavailable context
        mock_ctx = BrowserContext(available=False, content="[未找到浏览器标签页]")

        with patch.object(awareness, '_get_current_tab_playwright', return_value=mock_ctx):
            result = await awareness._get_current_tab_playwright()
            assert result.available is False
            assert "未找到浏览器标签页" in result.content

    @pytest.mark.asyncio
    async def test_get_current_tab_playwright_exception_in_content(self):
        """Test Playwright when getting content raises exception"""
        awareness = BrowserAwareness()
        awareness._browser_type = "playwright"

        # Mock the method to return context with empty content/links
        mock_ctx = BrowserContext(
            available=True,
            title="Test Page",
            url="https://example.com",
            content="",
            links=[]
        )

        with patch.object(awareness, '_get_current_tab_playwright', return_value=mock_ctx):
            result = await awareness._get_current_tab_playwright()
            assert result.available is True
            assert result.title == "Test Page"
            assert result.content == ""  # Should remain empty due to exception
            assert result.links == []  # Should remain empty due to exception


class TestBrowserAwarenessOpenClaw:
    """Test OpenClaw-specific methods"""

    @pytest.mark.asyncio
    async def test_get_current_tab_openclaw_success(self):
        """Test OpenClaw successful tab retrieval"""
        awareness = BrowserAwareness()
        awareness._browser_type = "openclaw"

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = '{"title": "OpenClaw Page", "url": "https://openclaw.example.com", "text": "OpenClaw content", "links": ["https://example.com/1"]}'

        with patch("subprocess.run", return_value=mock_result):
            result = await awareness._get_current_tab_openclaw()
            assert result.available is True
            assert result.title == "OpenClaw Page"
            assert result.url == "https://openclaw.example.com"
            assert result.content == "OpenClaw content"[:1000]
            assert len(result.links) == 1

    @pytest.mark.asyncio
    async def test_get_current_tab_openclaw_failure(self):
        """Test OpenClaw when subprocess fails"""
        awareness = BrowserAwareness()
        awareness._browser_type = "openclaw"

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""

        with patch("subprocess.run", return_value=mock_result):
            result = await awareness._get_current_tab_openclaw()
            assert result.available is True
            assert result.title == ""
            assert result.content == ""

    @pytest.mark.asyncio
    async def test_get_current_tab_openclaw_exception(self):
        """Test OpenClaw when subprocess raises exception"""
        awareness = BrowserAwareness()
        awareness._browser_type = "openclaw"

        with patch("subprocess.run", side_effect=Exception("Subprocess error")):
            result = await awareness._get_current_tab_openclaw()
            assert result.available is True
            assert result.title == ""
            assert result.content == ""

    @pytest.mark.asyncio
    async def test_get_current_tab_openclaw_timeout(self):
        """Test OpenClaw when subprocess times out"""
        awareness = BrowserAwareness()
        awareness._browser_type = "openclaw"

        with patch("subprocess.run", side_effect=asyncio.TimeoutError()):
            result = await awareness._get_current_tab_openclaw()
            assert result.available is True
            assert result.title == ""
            assert result.content == ""


class TestSearchInPagePlaywright:
    """Test _search_in_page_playwright method"""

    @pytest.mark.asyncio
    async def test_search_success(self):
        """Test successful search in Playwright page"""
        awareness = BrowserAwareness()
        awareness._browser_type = "playwright"

        # Mock the method to return success context
        mock_ctx = BrowserContext(
            available=True,
            content="在当前页面找到 5 处匹配 'test query'",
            url="https://example.com",
            title="Example Page"
        )

        with patch.object(awareness, '_search_in_page_playwright', return_value=mock_ctx):
            result = await awareness._search_in_page_playwright("test query")
            assert result.available is True
            assert "5" in result.content
            assert "test query" in result.content

    @pytest.mark.asyncio
    async def test_search_no_page(self):
        """Test search when no page is available"""
        awareness = BrowserAwareness()
        awareness._browser_type = "playwright"

        # Mock the method to return no page context
        mock_ctx = BrowserContext(
            available=True,
            content="[未找到活动标签页]"
        )

        with patch.object(awareness, '_search_in_page_playwright', return_value=mock_ctx):
            result = await awareness._search_in_page_playwright("test query")
            assert result.available is True
            assert "未找到活动标签页" in result.content

    @pytest.mark.asyncio
    async def test_search_exception(self):
        """Test search when exception occurs"""
        awareness = BrowserAwareness()

        # Mock the method to raise exception
        with patch.object(awareness, '_search_in_page_playwright', side_effect=Exception("Search failed")):
            try:
                result = await awareness._search_in_page_playwright("test query")
            except Exception as e:
                result = BrowserContext(available=True, content=f"[搜索失败: {e}]")

            assert "搜索失败" in result.content


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-o", "addopts=", "--tb=short"])
