"""
插件系统

支持第三方 Agent 插件的动态加载和管理。
"""

import importlib
import json
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
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
    requires: List[str] = []
    entrypoint: str = ""
    tags: List[str] = []


@dataclass
class Plugin:
    """插件实例"""

    metadata: PluginMetadata
    status: PluginStatus = PluginStatus.DISABLED
    module: Optional[Any] = None
    error: Optional[str] = None
    config: Dict[str, Any] = field(default_factory=dict)


class PluginBase(ABC):
    """
    插件基类

    所有插件必须继承此类并实现必要方法。

    Example:
        >>> class MyPlugin(PluginBase):
        ...     def on_load(self):
        ...         print("Plugin loaded")
        ...
        ...     def on_enable(self):
        ...         print("Plugin enabled")
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


class PluginManager:
    """
    插件管理器

    管理插件的生命周期、依赖和配置。

    Example:
        >>> manager = PluginManager(plugin_dir=Path(".omc/plugins"))
        >>> manager.load_all()
        >>> manager.enable("my_plugin")
    """

    def __init__(self, plugin_dir: Optional[Path] = None):
        """
        初始化插件管理器

        Args:
            plugin_dir: 插件目录
        """
        self.plugin_dir = plugin_dir or Path(".omc/plugins")
        self.plugin_dir.mkdir(parents=True, exist_ok=True)

        self._plugins: Dict[str, Plugin] = {}
        self._agents: Dict[str, Type] = {}
        self._skills: Dict[str, Callable] = {}
        self._hooks: Dict[str, List[Callable]] = {}

    def discover(self) -> List[PluginMetadata]:
        """
        发现所有可用插件

        Returns:
            插件元数据列表
        """
        discovered = []

        for plugin_path in self.plugin_dir.iterdir():
            if not plugin_path.is_dir():
                continue

            manifest_file = plugin_path / "plugin.json"
            if not manifest_file.exists():
                continue

            try:
                with open(manifest_file, encoding="utf-8") as f:
                    data = json.load(f)
                metadata = PluginMetadata(**data)
                discovered.append(metadata)
            except Exception as e:
                print(f"解析插件清单失败: {plugin_path}: {e}")

        return discovered

    def load(self, name: str) -> Optional[Plugin]:
        """
        加载单个插件

        Args:
            name: 插件名称

        Returns:
            插件实例，失败返回 None
        """
        # 检查是否已加载
        if name in self._plugins:
            return self._plugins[name]

        # 查找插件目录
        plugin_path = self.plugin_dir / name
        if not plugin_path.exists():
            return None

        manifest_file = plugin_path / "plugin.json"
        if not manifest_file.exists():
            return None

        try:
            # 解析元数据
            with open(manifest_file, encoding="utf-8") as f:
                data = json.load(f)
            metadata = PluginMetadata(**data)

            # 创建插件实例
            plugin = Plugin(metadata=metadata, status=PluginStatus.LOADING)
            self._plugins[name] = plugin

            # 添加到 Python 路径
            if str(plugin_path) not in sys.path:
                sys.path.insert(0, str(plugin_path))

            # 导入模块
            entrypoint = metadata.entrypoint or "main"
            module = importlib.import_module(entrypoint)

            # 获取插件类
            plugin_class = None
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    isinstance(attr, type)
                    and issubclass(attr, PluginBase)
                    and attr is not PluginBase
                ):
                    plugin_class = attr
                    break

            if plugin_class is None:
                raise ValueError("未找到插件类")

            # 实例化
            plugin.module = plugin_class()
            plugin.module.on_load()

            # 注册 Agent、技能、钩子
            for agent_cls in plugin.module.register_agents():
                agent_name = agent_cls.__name__
                self._agents[agent_name] = agent_cls

            for name, skill in plugin.module.register_skills().items():
                self._skills[name] = skill

            for name, hook in plugin.module.register_hooks().items():
                if name not in self._hooks:
                    self._hooks[name] = []
                self._hooks[name].append(hook)

            plugin.status = PluginStatus.DISABLED
            return plugin

        except Exception as e:
            plugin = self._plugins.get(name)
            if plugin:
                plugin.status = PluginStatus.ERROR
                plugin.error = f"{type(e).__name__}"
            return None

    def load_all(self) -> Dict[str, Plugin]:
        """
        加载所有插件

        Returns:
            名称到插件实例的映射
        """
        discovered = self.discover()
        for metadata in discovered:
            self.load(metadata.name)
        return self._plugins

    def enable(self, name: str) -> bool:
        """
        启用插件

        Args:
            name: 插件名称

        Returns:
            是否成功
        """
        plugin = self._plugins.get(name)
        if not plugin or plugin.status == PluginStatus.ERROR:
            return False

        try:
            if plugin.module:
                plugin.module.on_enable()
            plugin.status = PluginStatus.ENABLED
            return True
        except Exception as e:
            plugin.status = PluginStatus.ERROR
            plugin.error = f"{type(e).__name__}"
            return False

    def disable(self, name: str) -> bool:
        """
        禁用插件

        Args:
            name: 插件名称

        Returns:
            是否成功
        """
        plugin = self._plugins.get(name)
        if not plugin:
            return False

        try:
            if plugin.module:
                plugin.module.on_disable()
            plugin.status = PluginStatus.DISABLED
            return True
        except Exception:
            return False

    def unload(self, name: str) -> bool:
        """
        卸载插件

        Args:
            name: 插件名称

        Returns:
            是否成功
        """
        plugin = self._plugins.get(name)
        if not plugin:
            return False

        try:
            if plugin.module:
                plugin.module.on_unload()
            del self._plugins[name]
            return True
        except Exception:
            return False

    def get_plugin(self, name: str) -> Optional[Plugin]:
        """
        获取插件实例

        Args:
            name: 插件名称

        Returns:
            插件实例
        """
        return self._plugins.get(name)

    def list_plugins(self) -> List[Plugin]:
        """
        列出所有插件

        Returns:
            插件列表
        """
        return list(self._plugins.values())

    def get_agent(self, name: str) -> Optional[Type]:
        """
        获取注册的 Agent 类

        Args:
            name: Agent 名称

        Returns:
            Agent 类
        """
        return self._agents.get(name)

    def get_skill(self, name: str) -> Optional[Callable]:
        """
        获取注册的技能

        Args:
            name: 技能名称

        Returns:
            技能函数
        """
        return self._skills.get(name)

    def execute_hook(self, name: str, *args, **kwargs) -> List[Any]:
        """
        执行钩子

        Args:
            name: 钩子名称

        Returns:
            钩子执行结果列表
        """
        hooks = self._hooks.get(name, [])
        return [hook(*args, **kwargs) for hook in hooks]


def create_plugin_template(name: str, output_dir: Path) -> Path:
    """
    创建插件模板

    Args:
        name: 插件名称
        output_dir: 输出目录

    Returns:
        插件目录路径
    """
    plugin_dir = output_dir / name
    plugin_dir.mkdir(parents=True, exist_ok=True)

    # 创建 plugin.json
    manifest = {
        "name": name,
        "version": "0.1.0",
        "description": f"{name} 插件",
        "author": "",
        "license": "MIT",
        "entrypoint": "main",
        "requires": [],
        "tags": [],
    }

    with open(plugin_dir / "plugin.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    # 创建 main.py
    main_code = f'''"""
{name} 插件
"""

from src.plugins import PluginBase, PluginMetadata


class {name.replace("-", "_").title().replace("_", "")}Plugin(PluginBase):
    """插件实现"""

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="{name}",
            version="0.1.0",
            description="{name} 插件",
        )

    def on_load(self) -> None:
        print(f"[{name}] 插件已加载")

    def on_enable(self) -> None:
        print(f"[{name}] 插件已启用")

    def on_disable(self) -> None:
        print(f"[{name}] 插件已禁用")

    def register_agents(self):
        # 返回自定义 Agent 类
        return []

    def register_skills(self):
        # 返回自定义技能
        return {{}}
'''

    with open(plugin_dir / "main.py", "w", encoding="utf-8") as f:
        f.write(main_code)

    # 创建 README
    readme = f"""# {name} 插件

## 安装

将此目录复制到 `.omc/plugins/` 目录下。

## 配置

编辑 `plugin.json` 文件配置插件参数。

## 使用

```python
from src.plugins import get_plugin_manager

manager = get_plugin_manager()
manager.enable("{name}")
```
"""

    with open(plugin_dir / "README.md", "w", encoding="utf-8") as f:
        f.write(readme)

    return plugin_dir


# 全局实例
_plugin_manager: Optional[PluginManager] = None


def get_plugin_manager() -> PluginManager:
    """获取全局插件管理器实例"""
    global _plugin_manager
    if _plugin_manager is None:
        _plugin_manager = PluginManager()
    return _plugin_manager
