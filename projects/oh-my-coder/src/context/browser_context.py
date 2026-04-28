"""
浏览器上下文感知 - Browser Context Awareness

通过浏览器扩展/API 获取当前标签页上下文，支持：
- 获取当前标签页的标题、URL、内容摘要
- 搜索相关上下文
- 与 AI Agent 集成

注意：此功能需要浏览器扩展或 Playwright/Selenium 支持。
当无可用浏览器时，功能降级为优雅的空实现。
"""

import asyncio
import os
from dataclasses import dataclass, field


@dataclass
class BrowserContext:
    """
    浏览器上下文

    存储当前浏览器标签页的信息。
    """

    title: str = ""
    url: str = ""
    content: str = ""  # 页面内容摘要
    links: list[str] = field(default_factory=list)
    timestamp: str = ""
    available: bool = False  # 浏览器是否可用

    def to_context_string(self) -> str:
        """生成上下文字符串"""
        if not self.available:
            return "[浏览器上下文不可用]"

        parts = [
            f"标题: {self.title}",
            f"URL: {self.url}",
        ]

        if self.content:
            parts.append(f"内容摘要: {self.content[:500]}")

        if self.links:
            parts.append(f"链接 ({len(self.links)}): {', '.join(self.links[:10])}")

        return "\n".join(parts)


class BrowserAwareness:
    """
    浏览器感知模块

    通过多种方式获取浏览器上下文：
    1. Playwright（推荐，支持 Chromium/Chrome/Edge）
    2. Selenium（备选，支持多种浏览器）
    3. OpenClaw Browser CDP（如果有）

    当所有方式都不可用时，返回空的 BrowserContext。
    """

    def __init__(self):
        self._playwright = None
        self._selenium = None
        self._cdp_client = None
        self._browser_type = self._detect_browser()

    def _detect_browser(self) -> str:
        """检测可用的浏览器自动化方式"""
        # 优先检测 OpenClaw Browser CDP
        if os.getenv("OPENCLAW_BROWSER_ENABLED") == "1":
            return "openclaw"

        # 检测 Playwright
        try:
            import playwright

            self._playwright = playwright
            return "playwright"
        except ImportError:
            pass

        # 检测 Selenium
        try:
            import selenium

            self._selenium = selenium
            return "selenium"
        except ImportError:
            pass

        return "none"

    async def get_current_tab(self) -> BrowserContext:
        """
        获取当前浏览器标签页上下文

        Returns:
            BrowserContext: 当前标签页上下文
        """
        if self._browser_type == "none":
            return BrowserContext(available=False)

        try:
            if self._browser_type == "playwright":
                return await self._get_current_tab_playwright()
            if self._browser_type == "selenium":
                return await self._get_current_tab_selenium()
            if self._browser_type == "openclaw":
                return await self._get_current_tab_openclaw()
        except Exception as e:
            return BrowserContext(
                available=False,
                content=f"[浏览器获取失败: {e}]",
            )

        return BrowserContext(available=False)

    async def _get_current_tab_playwright(self) -> BrowserContext:
        """通过 Playwright 获取当前标签页"""
        from playwright.async_api import async_playwright

        ctx = BrowserContext(available=True)

        async with async_playwright() as p:
            # 尝试连接已有浏览器或启动新浏览器
            browser = None
            try:
                # 尝试连接 Chrome DevTools Protocol
                browser = await p.chromium.connect_over_cdp("http://localhost:9222")
            except Exception:
                try:
                    browser = await p.chromium.launch(headless=True)
                except Exception:
                    return BrowserContext(
                        available=False,
                        content="[无法启动 Chromium 浏览器]",
                    )

            try:
                page = browser.contexts[0].pages[0] if browser.contexts else None
                if page is None:
                    return BrowserContext(
                        available=False,
                        content="[未找到浏览器标签页]",
                    )

                ctx.title = page.title()
                ctx.url = page.url

                # 获取页面正文文本（简化版）
                try:
                    body_text = await page.inner_text("body")
                    ctx.content = body_text[:1000] if body_text else ""
                except Exception:
                    pass

                # 获取链接
                try:
                    links = await page.query_selector_all("a")
                    ctx.links = [
                        await link.get_attribute("href")
                        for link in links[:20]
                        if await link.get_attribute("href")
                    ]
                except Exception:
                    pass

            finally:
                await browser.close()

        return ctx

    async def _get_current_tab_selenium(self) -> BrowserContext:
        """通过 Selenium 获取当前标签页"""
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options

        ctx = BrowserContext(available=True)

        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")

        driver = None
        try:
            driver = webdriver.Chrome(options=options)
            ctx.title = driver.title
            ctx.url = driver.current_url

            # 获取 body 文本
            try:
                body = driver.find_element("tag name", "body")
                ctx.content = body.text[:1000]
            except Exception:
                pass

            # 获取链接
            try:
                links = driver.find_elements("tag name", "a")
                ctx.links = [
                    link.get_attribute("href")
                    for link in links[:20]
                    if link.get_attribute("href")
                ]
            except Exception:
                pass

        finally:
            if driver:
                driver.quit()

        return ctx

    async def _get_current_tab_openclaw(self) -> BrowserContext:
        """通过 OpenClaw Browser CDP 获取当前标签页"""
        import json
        import subprocess

        ctx = BrowserContext(available=True)

        # 使用 openclaw browser snapshot 命令
        try:
            result = subprocess.run(
                ["openclaw", "browser", "snapshot", "--json"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                data = json.loads(result.stdout)
                ctx.title = data.get("title", "")
                ctx.url = data.get("url", "")
                ctx.content = data.get("text", "")[:1000]
                ctx.links = data.get("links", [])[:20]
        except Exception:
            pass

        return ctx

    async def search_context(self, query: str) -> BrowserContext:
        """
        搜索相关上下文

        在当前浏览器页面中搜索相关内容。

        Args:
            query: 搜索关键词

        Returns:
            BrowserContext: 搜索结果上下文
        """
        if self._browser_type == "none":
            return BrowserContext(
                available=False,
                content=f"[搜索 '{query}' - 浏览器不可用]",
            )

        # 对于 Playwright，可以在页面中执行搜索
        if self._browser_type == "playwright":
            return await self._search_in_page_playwright(query)

        return BrowserContext(
            available=False,
            content=f"[搜索 '{query}' - 当前浏览器类型不支持]",
        )

    async def _search_in_page_playwright(self, query: str) -> BrowserContext:
        """在 Playwright 页面中搜索"""
        from playwright.async_api import async_playwright

        ctx = BrowserContext(available=True)
        ctx.content = f"搜索 '{query}' 的结果将在页面中显示"

        async with async_playwright() as p:
            try:
                browser = await p.chromium.launch(headless=True)
                page = browser.contexts[0].pages[0] if browser.contexts else None

                if page:
                    # 在页面中查找匹配的文本
                    matches = await page.locator(f"text={query}").count()
                    ctx.content = f"在当前页面找到 {matches} 处匹配 '{query}'"
                    ctx.url = page.url
                    ctx.title = page.title()
                else:
                    ctx.content = "[未找到活动标签页]"

                await browser.close()
            except Exception as e:
                ctx.content = f"[搜索失败: {e}]"

        return ctx

    def to_context_string(self) -> str:
        """生成上下文字符串（同步版本，获取当前标签页）"""
        return asyncio.run(self.get_current_tab()).to_context_string()
