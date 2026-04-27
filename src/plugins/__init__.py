"""
插件系统

支持第三方 Agent 插件的动态加载和管理。

核心组件:
- registry: 插件注册表，@register 装饰器
- loader:   插件加载器，依赖排序加载

示例插件:
- example_plugin: 示例插件
"""

from src.plugins.registry import (
    PluginBase,
    PluginMetadata,
    PluginStatus,
    Plugin,
    PluginRegistry,
    register,
    get_registry,
)
from src.plugins.loader import PluginLoader, get_loader

__all__ = [
    "PluginBase",
    "PluginMetadata",
    "PluginStatus",
    "Plugin",
    "PluginRegistry",
    "register",
    "get_registry",
    "PluginLoader",
    "get_loader",
]

# 自动发现并加载内置插件（供 main.py 调用）
def discover_and_load() -> list[str]:
    """发现所有内置插件并按依赖顺序加载，返回成功加载的插件名列表"""
    loader = get_loader()
    loader.discover()
    return loader.load_all()
