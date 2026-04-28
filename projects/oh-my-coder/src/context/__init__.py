"""
Context Module - 工作目录上下文感知

提供：
- WorkspaceScanner: 工作目录扫描器
- BrowserAwareness: 浏览器上下文感知
"""

from .browser_context import BrowserAwareness, BrowserContext
from .workspace_scanner import FileNode, WorkspaceScanner

__all__ = [
    "BrowserAwareness",
    "BrowserContext",
    "FileNode",
    "WorkspaceScanner",
]
