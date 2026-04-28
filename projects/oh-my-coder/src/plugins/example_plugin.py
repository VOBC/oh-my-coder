"""
示例插件

演示如何使用 @register 装饰器创建插件。
"""

from src.plugins.registry import PluginBase, PluginMetadata, register


@register
class ExamplePlugin(PluginBase):
    """示例插件，展示插件系统的基本用法"""

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="example",
            version="0.1.0",
            description="示例插件，展示插件系统基本用法",
            author="oh-my-coder",
            tags=["example", "demo"],
        )

    def on_load(self) -> None:
        print("[example] 插件已加载")

    def on_enable(self) -> None:
        print("[example] 插件已启用")

    def on_disable(self) -> None:
        print("[example] 插件已禁用")

    def on_unload(self) -> None:
        print("[example] 插件已卸载")

    def register_skills(self):
        return {
            "example_greet": self._greet,
        }

    def register_hooks(self):
        return {
            "on_startup": self._on_startup,
        }

    @staticmethod
    def _greet(name: str = "World") -> str:
        """示例技能：问候"""
        return f"Hello, {name}! From example plugin."

    @staticmethod
    def _on_startup() -> None:
        """启动钩子"""
        print("[example] 系统启动通知")
