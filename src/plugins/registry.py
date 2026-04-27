"""
插件注册表

提供插件元信息管理、@register 装饰器和全局注册表。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type

from pydantic import BaseModel


class PluginStatus(str, Enum):
    """插件状态"""

    ENABLED = "enabled"
    DISABLED = "disabled"
    ERROR = "error"
    LOADING = "loading"


class PluginMetadata(BaseModel):
    """插件元数据"""

    name: str
    version: str
    description: str = ""
    author: str = ""
    homepage: str = ""
    license: str = "MIT"
    requires: List[str] = []  # 依赖的其他插件名
    entrypoint: str = ""
    tags: List[str] = []


@dataclass
class Plugin:
    """插件实例"""

    metadata: PluginMetadata
    status: PluginStatus = PluginStatus.DISABLED
    module: Optional[Any] = None
    instance: Optional["PluginBase"] = None
    error: Optional[str] = None
    config: Dict[str, Any] = field(default_factory=dict)


class PluginBase(ABC):
    """
    插件基类

    所有插件必须继承此类并实现必要方法。

    Example::

        class MyPlugin(PluginBase):
            @property
            def metadata(self) -> PluginMetadata:
                return PluginMetadata(name="my", version="0.1.0")

            def on_load(self) -> None:
                print("loaded")
    """

    @property
    @abstractmethod
    def metadata(self) -> PluginMetadata:
        """返回插件元数据"""
        pass

    @abstractmethod
    def on_load(self) -> None:
        """插件加载时调用"""
        pass

    def on_enable(self) -> None:
        """插件启用时调用"""
        pass

    def on_disable(self) -> None:
        """插件禁用时调用"""
        pass

    def on_unload(self) -> None:
        """插件卸载时调用"""
        pass

    def register_agents(self) -> List[Type]:
        """注册 Agent 类"""
        return []

    def register_skills(self) -> Dict[str, Callable]:
        """注册技能函数"""
        return {}

    def register_hooks(self) -> Dict[str, Callable]:
        """注册钩子函数"""
        return {}


class PluginRegistry:
    """
    插件注册表

    管理已注册插件的元信息和实例。
    支持通过 @register 装饰器或手动注册。
    """

    def __init__(self) -> None:
        self._plugins: Dict[str, Plugin] = {}
        self._agents: Dict[str, Type] = {}
        self._skills: Dict[str, Callable] = {}
        self._hooks: Dict[str, List[Callable]] = {}

    # ---- 注册 ----

    def register_plugin(self, plugin_cls: Type[PluginBase]) -> Plugin:
        """
        注册一个插件类（不加载，仅记录元信息）。

        Args:
            plugin_cls: 插件类（必须继承 PluginBase）

        Returns:
            Plugin 实例

        Raises:
            TypeError: 如果 plugin_cls 不是 PluginBase 子类
        """
        if not (isinstance(plugin_cls, type) and issubclass(plugin_cls, PluginBase)):
            raise TypeError(f"{plugin_cls} 不是 PluginBase 的子类")

        # 临时实例化获取元信息
        temp = plugin_cls()
        meta = temp.metadata

        plugin = Plugin(metadata=meta, instance=temp)
        self._plugins[meta.name] = plugin
        return plugin

    def unregister(self, name: str) -> bool:
        """
        注销插件。

        Args:
            name: 插件名称

        Returns:
            是否成功
        """
        if name not in self._plugins:
            return False
        del self._plugins[name]
        return True

    # ---- 查询 ----

    def get(self, name: str) -> Optional[Plugin]:
        """获取插件"""
        return self._plugins.get(name)

    def list_plugins(self) -> List[Plugin]:
        """列出所有插件"""
        return list(self._plugins.values())

    def list_by_status(self, status: PluginStatus) -> List[Plugin]:
        """按状态过滤插件"""
        return [p for p in self._plugins.values() if p.status == status]

    def get_agent(self, name: str) -> Optional[Type]:
        """获取注册的 Agent 类"""
        return self._agents.get(name)

    def get_skill(self, name: str) -> Optional[Callable]:
        """获取注册的技能"""
        return self._skills.get(name)

    def execute_hook(self, name: str, *args: Any, **kwargs: Any) -> List[Any]:
        """
        执行钩子

        Args:
            name: 钩子名称

        Returns:
            钩子执行结果列表
        """
        hooks = self._hooks.get(name, [])
        results: List[Any] = []
        for hook in hooks:
            try:
                results.append(hook(*args, **kwargs))
            except Exception:
                pass
        return results

    # ---- 资源注册（由 loader 调用）----

    def _register_agents(self, agents: List[Type]) -> None:
        for agent_cls in agents:
            self._agents[agent_cls.__name__] = agent_cls

    def _register_skills(self, skills: Dict[str, Callable]) -> None:
        self._skills.update(skills)

    def _register_hooks(self, hooks: Dict[str, Callable]) -> None:
        for hook_name, hook_fn in hooks.items():
            if hook_name not in self._hooks:
                self._hooks[hook_name] = []
            self._hooks[hook_name].append(hook_fn)

    def _clear_resources(self, name: str) -> None:
        """清除指定插件的已注册资源"""
        plugin = self._plugins.get(name)
        if not plugin or not plugin.instance:
            return

        # 清除 agents
        for agent_cls in plugin.instance.register_agents():
            self._agents.pop(agent_cls.__name__, None)

        # 清除 skills
        for skill_name in plugin.instance.register_skills():
            self._skills.pop(skill_name, None)

        # 清除 hooks
        for hook_name in plugin.instance.register_hooks():
            hook_list = self._hooks.get(hook_name, [])
            self._hooks[hook_name] = [
                h
                for h in hook_list
                if h not in plugin.instance.register_hooks().values()
            ]


# ---- 全局注册表 ----

_registry: Optional[PluginRegistry] = None


def get_registry() -> PluginRegistry:
    """获取全局插件注册表"""
    global _registry
    if _registry is None:
        _registry = PluginRegistry()
    return _registry


# ---- @register 装饰器 ----


def register(cls: Type[PluginBase]) -> Type[PluginBase]:
    """
    类装饰器，将插件类注册到全局注册表。

    Example::

        @register
        class MyPlugin(PluginBase):
            @property
            def metadata(self):
                return PluginMetadata(name="my", version="0.1.0")

            def on_load(self):
                pass

    Args:
        cls: 插件类

    Returns:
        原始类（无修改）
    """
    get_registry().register_plugin(cls)
    return cls
