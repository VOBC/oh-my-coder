"""
插件注册表

@register 装饰器 + 全局单例 registry。
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from src.plugins.loader import PluginLoader


class PluginStatus(Enum):
    UNLOADED = "unloaded"
    LOADING = "loading"
    LOADED = "loaded"
    FAILED = "failed"
    DISABLED = "disabled"


@dataclass
class PluginMetadata:
    name: str
    version: str
    description: str = ""
    author: str = ""
    dependencies: list[str] = field(default_factory=list)
    entrypoint: str = "register"  # 入口函数名，默认 register()


@dataclass
class PluginBase:
    """所有插件的基类"""

    metadata: PluginMetadata

    def on_load(self, loader: PluginLoader) -> None:
        """插件加载时调用，可用于初始化"""
        pass

    def on_unload(self) -> None:
        """插件卸载时调用"""
        pass


class Plugin:
    """注册表中的插件条目"""

    __slots__ = (
        "metadata",
        "instance",
        "status",
        "error",
        "_loaded",
        "_enabled",
    )

    def __init__(
        self,
        metadata: PluginMetadata,
        instance: PluginBase | None = None,
    ) -> None:
        self.metadata = metadata
        self.instance = instance
        self.status: PluginStatus = PluginStatus.UNLOADED
        self.error: str | None = None
        self._loaded = False
        self._enabled = True

    @property
    def loaded(self) -> bool:
        return self._loaded

    @loaded.setter
    def loaded(self, value: bool) -> None:
        self._loaded = value

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        self._enabled = value


class PluginRegistry:
    """
    全局插件注册表（单例）。

    用法::

        from src.plugins import register, get_registry

        @register(name="my-plugin", version="1.0.0", description="示例插件")
        class MyPlugin(PluginBase):
            ...
    """

    _instance: PluginRegistry | None = None

    def __init__(self) -> None:
        self._plugins: dict[str, Plugin] = {}
        self._sorted: list[str] = []

    @classmethod
    def get_instance(cls) -> PluginRegistry:
        if cls._instance is None:
            cls._instance = PluginRegistry()
        return cls._instance

    # ---- public API ----

    def register(self, plugin: Plugin) -> None:
        name = plugin.metadata.name
        if name in self._plugins:
            raise ValueError(f"Plugin '{name}' already registered")
        self._plugins[name] = plugin
        self._sorted = []

    def unregister(self, name: str) -> None:
        self._plugins.pop(name, None)
        self._sorted = []

    def get(self, name: str) -> Plugin | None:
        return self._plugins.get(name)

    def list_all(self) -> list[Plugin]:
        return list(self._plugins.values())

    def sorted_names(self) -> list[str]:
        """按依赖拓扑排序后的插件名列表"""
        if self._sorted:
            return self._sorted
        self._sorted = self._topo_sort()
        return self._sorted

    def enable(self, name: str) -> None:
        p = self._plugins.get(name)
        if p:
            p._enabled = True

    def disable(self, name: str) -> None:
        p = self._plugins.get(name)
        if p:
            p._enabled = False

    # ---- private ----

    def _topo_sort(self) -> list[str]:
        """Kahn 算法拓扑排序"""
        visited: dict[str, int] = {}
        order: list[str] = []

        def dfs(name: str) -> None:
            if name in visited:
                return
            visited[name] = 0  # visiting
            p = self._plugins.get(name)
            if p:
                for dep in p.metadata.dependencies:
                    if dep in self._plugins:
                        dfs(dep)
            visited[name] = 1  # visited
            order.insert(0, name)

        for name in self._plugins:
            dfs(name)

        return order


# ---- decorator ----

def register(
    name: str,
    version: str = "0.0.0",
    description: str = "",
    author: str = "",
    dependencies: list[str] | None = None,
) -> Callable[[type[PluginBase]], type[PluginBase]]:
    """
    插件注册装饰器。

    用法::

        @register(name="my-plugin", version="1.0.0", description="My first plugin")
        class MyPlugin(PluginBase):
            ...
    """
    def decorator(cls: type[PluginBase]) -> type[PluginBase]:
        metadata = PluginMetadata(
            name=name,
            version=version,
            description=description,
            author=author,
            dependencies=dependencies or [],
        )
        instance = cls(metadata)
        plugin = Plugin(metadata, instance)
        get_instance().register(plugin)
        return cls

    return decorator


# ---- helpers ----

def get_registry() -> PluginRegistry:
    """获取全局插件注册表单例"""
    return PluginRegistry.get_instance()


def get_instance() -> PluginRegistry:
    """别名，兼容旧代码"""
    return get_registry()