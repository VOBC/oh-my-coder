"""
插件加载器

负责插件发现、加载和依赖排序。
"""

import importlib
import importlib.util
import sys
from pathlib import Path
from typing import Dict, List, Optional

from src.plugins.registry import (
    Plugin,
    PluginBase,
    PluginMetadata,
    PluginRegistry,
    PluginStatus,
    get_registry,
)


class PluginLoaderError(Exception):
    """插件加载异常"""

    pass


class PluginLoader:
    """
    插件加载器

    扫描指定目录下的 .py 文件，发现并加载插件。
    支持按依赖拓扑排序加载。

    Example::

        loader = PluginLoader(registry=get_registry())
        loader.discover()  # 扫描 src/plugins/ 下 .py 文件
        loader.load_all()  # 按依赖顺序加载
    """

    # 跳过的模块名
    SKIP_MODULES = {"__init__", "registry", "loader"}

    def __init__(
        self,
        registry: Optional[PluginRegistry] = None,
        plugin_dir: Optional[Path] = None,
    ) -> None:
        """
        Args:
            registry: 插件注册表，默认使用全局注册表
            plugin_dir: 插件扫描目录，默认为 src/plugins/
        """
        self.registry = registry or get_registry()
        self.plugin_dir = plugin_dir or self._default_plugin_dir()
        self._loaded: List[str] = []

    @staticmethod
    def _default_plugin_dir() -> Path:
        """默认插件目录 = src/plugins/"""
        return Path(__file__).parent

    # ---- 发现 ----

    def discover(self) -> List[PluginMetadata]:
        """
        扫描 plugin_dir 下所有 .py 文件，发现可用插件。

        跳过 __init__.py、registry.py、loader.py 等框架文件。
        对每个 .py 文件动态导入，查找被 @register 装饰的 PluginBase 子类
        或直接定义的 PluginBase 子类。

        Returns:
            发现的插件元信息列表
        """
        discovered: List[PluginMetadata] = []

        if not self.plugin_dir.exists():
            return discovered

        for py_file in sorted(self.plugin_dir.glob("*.py")):
            module_name = py_file.stem
            if module_name in self.SKIP_MODULES:
                continue

            try:
                self._import_module(py_file, module_name)
            except Exception:
                continue

        # 导入后注册表中就有了 @register 装饰的插件
        # 再扫描模块，查找未注册但有 PluginBase 子类的
        for py_file in sorted(self.plugin_dir.glob("*.py")):
            module_name = py_file.stem
            if module_name in self.SKIP_MODULES:
                continue

            try:
                mod = sys.modules.get(f"src.plugins.{module_name}")
                if mod is None:
                    continue

                # 查找模块中所有 PluginBase 子类
                for attr_name in dir(mod):
                    attr = getattr(mod, attr_name)
                    if (
                        isinstance(attr, type)
                        and issubclass(attr, PluginBase)
                        and attr is not PluginBase
                    ):
                        # 检查是否已在注册表
                        try:
                            temp = attr()
                            meta = temp.metadata
                            if not self.registry.get(meta.name):
                                self.registry.register_plugin(attr)
                            if meta not in discovered:
                                discovered.append(meta)
                        except Exception:
                            continue
            except Exception:
                continue

        # 合并已通过 @register 注册的
        for plugin in self.registry.list_plugins():
            if plugin.metadata not in discovered:
                discovered.append(plugin.metadata)

        return discovered

    def _import_module(self, py_file: Path, module_name: str) -> object:
        """动态导入单个 .py 文件为模块"""
        full_name = f"src.plugins.{module_name}"

        # 如果已导入，先卸载以支持热重载
        if full_name in sys.modules:
            del sys.modules[full_name]

        spec = importlib.util.spec_from_file_location(full_name, str(py_file))
        if spec is None or spec.loader is None:
            raise PluginLoaderError(f"无法创建模块 spec: {py_file}")

        module = importlib.util.module_from_spec(spec)
        sys.modules[full_name] = module
        spec.loader.exec_module(module)
        return module

    # ---- 依赖排序 ----

    def _topological_sort(self, plugins: List[PluginMetadata]) -> List[PluginMetadata]:
        """
        按依赖拓扑排序，被依赖的插件先加载。

        Args:
            plugins: 待排序的插件元信息列表

        Returns:
            排序后的列表

        Raises:
            PluginLoaderError: 检测到循环依赖
        """
        name_map: Dict[str, PluginMetadata] = {p.name: p for p in plugins}
        plugin_names = set(name_map.keys())

        # 构建邻接表：name -> 依赖它的插件（反向边）
        dependents: Dict[str, List[str]] = {n: [] for n in plugin_names}
        in_degree: Dict[str, int] = {n: 0 for n in plugin_names}

        for p in plugins:
            for req in p.requires:
                if req in plugin_names:
                    dependents[req].append(p.name)
                    in_degree[p.name] += 1
                # 外部依赖跳过（不阻塞加载，由运行时校验）

        # Kahn 算法
        queue: List[str] = [n for n in plugin_names if in_degree[n] == 0]
        sorted_names: List[str] = []

        while queue:
            # 字母序稳定排序
            queue.sort()
            name = queue.pop(0)
            sorted_names.append(name)
            for dep_name in dependents[name]:
                in_degree[dep_name] -= 1
                if in_degree[dep_name] == 0:
                    queue.append(dep_name)

        if len(sorted_names) != len(plugins):
            raise PluginLoaderError("检测到循环依赖，无法确定加载顺序")

        return [name_map[n] for n in sorted_names]

    # ---- 加载 ----

    def load(self, name: str) -> Optional[Plugin]:
        """
        加载单个插件。

        Args:
            name: 插件名称

        Returns:
            加载后的 Plugin 实例，失败返回 None
        """
        plugin = self.registry.get(name)
        if plugin is None:
            return None

        if plugin.status == PluginStatus.ENABLED:
            return plugin

        try:
            plugin.status = PluginStatus.LOADING

            if plugin.instance is None:
                raise PluginLoaderError(f"插件 {name} 没有实例")

            # 调用 on_load
            plugin.instance.on_load()

            # 注册资源
            self.registry._register_agents(plugin.instance.register_agents())
            self.registry._register_skills(plugin.instance.register_skills())
            self.registry._register_hooks(plugin.instance.register_hooks())

            plugin.status = PluginStatus.DISABLED
            self._loaded.append(name)
            return plugin

        except Exception as e:
            plugin.status = PluginStatus.ERROR
            plugin.error = f"{type(e).__name__}: {e}"
            return None

    def load_all(self) -> List[str]:
        """
        发现所有插件，按依赖顺序加载。

        同时处理已通过 @register 或 register_plugin 手动注册
        但尚未加载的插件。

        Returns:
            成功加载的插件名列表
        """
        discovered = self.discover()

        # 合并注册表中已注册但未在 discovered 中的插件
        registered = self.registry.list_plugins()
        registered_metas = [p.metadata for p in registered]
        for meta in registered_metas:
            if meta not in discovered:
                discovered.append(meta)

        if not discovered:
            return list(self._loaded)

        sorted_plugins = self._topological_sort(discovered)

        for meta in sorted_plugins:
            self.load(meta.name)

        return list(self._loaded)

    def enable(self, name: str) -> bool:
        """启用插件"""
        plugin = self.registry.get(name)
        if not plugin or plugin.status == PluginStatus.ERROR:
            return False

        try:
            if plugin.instance:
                plugin.instance.on_enable()
            plugin.status = PluginStatus.ENABLED
            return True
        except Exception as e:
            plugin.status = PluginStatus.ERROR
            plugin.error = f"{type(e).__name__}: {e}"
            return False

    def disable(self, name: str) -> bool:
        """禁用插件"""
        plugin = self.registry.get(name)
        if not plugin:
            return False

        try:
            if plugin.instance:
                plugin.instance.on_disable()
            plugin.status = PluginStatus.DISABLED
            return True
        except Exception:
            return False

    def unload(self, name: str) -> bool:
        """
        卸载插件。

        Args:
            name: 插件名称

        Returns:
            是否成功
        """
        plugin = self.registry.get(name)
        if not plugin:
            return False

        try:
            if plugin.instance:
                plugin.instance.on_unload()
            self.registry._clear_resources(name)
            if name in self._loaded:
                self._loaded.remove(name)
            plugin.status = PluginStatus.DISABLED
            plugin.instance = None
            return True
        except Exception:
            return False


# ---- 全局加载器 ----

_loader: Optional[PluginLoader] = None


def get_loader() -> PluginLoader:
    """获取全局插件加载器"""
    global _loader
    if _loader is None:
        _loader = PluginLoader()
    return _loader
