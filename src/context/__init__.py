"""
Context Module - 工作目录上下文感知

提供：
- WorkspaceScanner: 工作目录扫描器
- BrowserAwareness: 浏览器上下文感知
"""

from .workspace_scanner import FileNode, WorkspaceScanner
from .browser_context import BrowserContext, BrowserAwareness

__all__ = [
    "FileNode",
    "WorkspaceScanner",
    "BrowserContext",
    "BrowserAwareness",
]
