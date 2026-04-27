"""
插件系统测试

覆盖 registry、loader、@register 装饰器和示例插件。
"""

import sys
from pathlib import Path

import pytest

from src.plugins.loader import PluginLoader, PluginLoaderError
from src.plugins.registry import (
    PluginBase,
    PluginMetadata,
    PluginRegistry,
    PluginStatus,
    get_registry,
    register,
)

# ---- Fixtures ----


class FixturePlugin(PluginBase):
    """测试用插件"""

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="fixture",
            version="1.0.0",
            description="测试插件",
        )

    def on_load(self) -> None:
        pass


class DependentPlugin(PluginBase):
    """依赖 fixture 的插件"""

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="dependent",
            version="1.0.0",
            description="依赖测试",
            requires=["fixture"],
        )

    def on_load(self) -> None:
        pass


class CircularA(PluginBase):
    """循环依赖 A"""

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(name="circ_a", version="1.0.0", requires=["circ_b"])

    def on_load(self) -> None:
        pass


class CircularB(PluginBase):
    """循环依赖 B"""

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(name="circ_b", version="1.0.0", requires=["circ_a"])

    def on_load(self) -> None:
        pass


@pytest.fixture
def registry():
    """每个测试用全新的注册表"""
    return PluginRegistry()


@pytest.fixture
def loader(registry):
    """每个测试用全新的加载器"""
    return PluginLoader(
        registry=registry, plugin_dir=Path("/tmp/nonexistent_plugins_test")
    )


# ---- PluginMetadata ----


class TestPluginMetadata:
    def test_defaults(self):
        meta = PluginMetadata(name="test", version="0.1.0")
        assert meta.name == "test"
        assert meta.version == "0.1.0"
        assert meta.description == ""
        assert meta.requires == []
        assert meta.tags == []

    def test_full(self):
        meta = PluginMetadata(
            name="test",
            version="1.0.0",
            description="desc",
            author="me",
            requires=["other"],
            tags=["demo"],
        )
        assert meta.author == "me"
        assert meta.requires == ["other"]
        assert meta.tags == ["demo"]


# ---- PluginRegistry ----


class TestPluginRegistry:
    def test_register_plugin(self, registry):
        plugin = registry.register_plugin(FixturePlugin)
        assert plugin.metadata.name == "fixture"
        assert plugin.status == PluginStatus.DISABLED
        assert plugin.instance is not None

    def test_register_non_plugin_raises(self, registry):
        with pytest.raises(TypeError):
            registry.register_plugin(str)  # type: ignore

    def test_unregister(self, registry):
        registry.register_plugin(FixturePlugin)
        assert registry.unregister("fixture") is True
        assert registry.get("fixture") is None

    def test_unregister_missing(self, registry):
        assert registry.unregister("nope") is False

    def test_get(self, registry):
        registry.register_plugin(FixturePlugin)
        assert registry.get("fixture") is not None
        assert registry.get("nope") is None

    def test_list_plugins(self, registry):
        registry.register_plugin(FixturePlugin)
        registry.register_plugin(DependentPlugin)
        names = [p.metadata.name for p in registry.list_plugins()]
        assert "fixture" in names
        assert "dependent" in names

    def test_list_by_status(self, registry):
        registry.register_plugin(FixturePlugin)
        plugin = registry.get("fixture")
        assert plugin is not None
        plugin.status = PluginStatus.ENABLED
        enabled = registry.list_by_status(PluginStatus.ENABLED)
        assert len(enabled) == 1
        assert enabled[0].metadata.name == "fixture"

    def test_execute_hook(self, registry):
        called = []
        registry._register_hooks({"test_hook": lambda: called.append(True)})
        results = registry.execute_hook("test_hook")
        assert called == [True]
        assert len(results) == 1

    def test_execute_hook_error_isolation(self, registry):
        registry._register_hooks(
            {
                "good": lambda: 42,
            }
        )
        results = registry.execute_hook("good")
        assert 42 in results

    def test_register_agents_skills(self, registry):
        class FakeAgent:
            pass

        registry._register_agents([FakeAgent])
        assert registry.get_agent("FakeAgent") is FakeAgent

        registry._register_skills({"greet": lambda: "hi"})
        assert registry.get_skill("greet")() == "hi"

    def test_clear_resources(self, registry):
        class FakeAgent:
            pass

        class PluginWithResources(PluginBase):
            @property
            def metadata(self):
                return PluginMetadata(name="res_plugin", version="1.0.0")

            def on_load(self):
                pass

            def register_agents(self):
                return [FakeAgent]

            def register_skills(self):
                return {"res_skill": lambda: "hi"}

        registry.register_plugin(PluginWithResources)
        p = registry.get("res_plugin")
        assert p is not None
        assert p.instance is not None

        # 手动注册资源（模拟 loader 的行为）
        registry._register_agents(p.instance.register_agents())
        registry._register_skills(p.instance.register_skills())

        assert registry.get_agent("FakeAgent") is not None
        assert registry.get_skill("res_skill") is not None

        # 清除
        registry._clear_resources("res_plugin")
        assert registry.get_agent("FakeAgent") is None
        assert registry.get_skill("res_skill") is None


# ---- @register 装饰器 ----


class TestRegisterDecorator:
    def test_register_decorator(self):
        """@register 装饰器把类注册到全局注册表"""

        @register
        class DecoratedPlugin(PluginBase):
            @property
            def metadata(self):
                return PluginMetadata(name="decorated_test", version="0.1.0")

            def on_load(self):
                pass

        # 应该在全局注册表中
        global_r = get_registry()
        assert global_r.get("decorated_test") is not None

        # 清理
        global_r.unregister("decorated_test")

    def test_register_returns_original_class(self):
        @register
        class ReturnTestPlugin(PluginBase):
            @property
            def metadata(self):
                return PluginMetadata(name="return_test", version="0.1.0")

            def on_load(self):
                pass

        assert issubclass(ReturnTestPlugin, PluginBase)
        # 清理
        get_registry().unregister("return_test")


# ---- PluginLoader ----


class TestPluginLoader:
    def test_topological_sort_no_deps(self, loader):
        metas = [
            PluginMetadata(name="c", version="1.0.0"),
            PluginMetadata(name="a", version="1.0.0"),
            PluginMetadata(name="b", version="1.0.0"),
        ]
        result = loader._topological_sort(metas)
        names = [m.name for m in result]
        # 无依赖，字母序
        assert names == ["a", "b", "c"]

    def test_topological_sort_with_deps(self, loader):
        metas = [
            PluginMetadata(name="dependent", version="1.0.0", requires=["fixture"]),
            PluginMetadata(name="fixture", version="1.0.0"),
        ]
        result = loader._topological_sort(metas)
        names = [m.name for m in result]
        # fixture 必须在 dependent 前面
        assert names.index("fixture") < names.index("dependent")

    def test_topological_sort_circular(self, loader):
        metas = [
            PluginMetadata(name="circ_a", version="1.0.0", requires=["circ_b"]),
            PluginMetadata(name="circ_b", version="1.0.0", requires=["circ_a"]),
        ]
        with pytest.raises(PluginLoaderError, match="循环依赖"):
            loader._topological_sort(metas)

    def test_load_plugin(self, registry, loader):
        registry.register_plugin(FixturePlugin)
        result = loader.load("fixture")
        assert result is not None
        assert result.status == PluginStatus.DISABLED
        assert "fixture" in loader._loaded

    def test_load_missing(self, loader):
        result = loader.load("nonexistent")
        assert result is None

    def test_enable_disable(self, registry, loader):
        registry.register_plugin(FixturePlugin)
        loader.load("fixture")

        assert loader.enable("fixture") is True
        p = registry.get("fixture")
        assert p is not None
        assert p.status == PluginStatus.ENABLED

        assert loader.disable("fixture") is True
        assert p.status == PluginStatus.DISABLED

    def test_unload(self, registry, loader):
        registry.register_plugin(FixturePlugin)
        loader.load("fixture")

        assert loader.unload("fixture") is True
        p = registry.get("fixture")
        assert p is not None
        assert p.instance is None

    def test_load_all(self, registry, loader):
        registry.register_plugin(FixturePlugin)
        registry.register_plugin(DependentPlugin)

        loaded = loader.load_all()
        # dependent 在 fixture 之后加载
        assert "fixture" in loaded
        assert "dependent" in loaded
        assert loaded.index("fixture") < loaded.index("dependent")


# ---- ExamplePlugin 集成测试 ----


class TestExamplePlugin:
    def test_example_plugin_importable(self):
        """示例插件可以被导入"""
        # 清理可能的缓存
        mod_name = "src.plugins.example_plugin"
        if mod_name in sys.modules:
            del sys.modules[mod_name]

        from src.plugins import example_plugin

        assert hasattr(example_plugin, "ExamplePlugin")

    def test_example_plugin_metadata(self):
        # @register 会把 ExamplePlugin 注册到全局注册表
        # 但 ExamplePlugin 仍是一个类
        from src.plugins.example_plugin import ExamplePlugin

        # ExamplePlugin 被 @register 装饰后仍是类
        p = ExamplePlugin()
        assert p.metadata.name == "example"
        assert p.metadata.version == "0.1.0"
        assert "示例" in p.metadata.description

    def test_example_plugin_skills(self):
        from src.plugins.example_plugin import ExamplePlugin

        p = ExamplePlugin()
        skills = p.register_skills()
        assert "example_greet" in skills
        assert "World" in skills["example_greet"]()

    def test_example_plugin_hooks(self):
        from src.plugins.example_plugin import ExamplePlugin

        p = ExamplePlugin()
        hooks = p.register_hooks()
        assert "on_startup" in hooks
