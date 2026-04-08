"""
Oh My Coder Wiki - 项目文档自动生成

使用 AST 解析 Python 代码，自动生成结构化项目文档。
"""

from .parser import PythonParser
from .generator import WikiGenerator

__all__ = ["PythonParser", "WikiGenerator"]
