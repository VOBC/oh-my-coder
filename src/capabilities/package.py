"""
能力包系统 - Capability Package System

参考 EvoMap 的 Gene/Capsule 理念，实现能力资产化基础功能。
用户可以将优化后的 Agent 配置打包导出，社区可以共享这些"能力包"。
"""

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class CapabilityPackage:
    """
    能力包数据结构

    包含完整的 Agent 配置、模型配置、工具列表和 Prompt 模板，
    可以被导出、分享和导入。
    """

    # 基本信息
    name: str  # 包名称
    version: str  # 版本号 (semver)
    description: str  # 功能描述
    author: str  # 作者
    created_at: str  # 创建时间
    tags: list[str] = field(
        default_factory=list
    )  # 标签 (e.g., ["code-review", "refactor"])

    # 核心配置
    agents: dict = field(default_factory=dict)  # Agent 配置
    model_config: dict = field(default_factory=dict)  # 模型配置
    tools: list[str] = field(default_factory=list)  # 启用的工具列表
    prompts: dict = field(default_factory=dict)  # 自定义 Prompt 模板

    # 元数据
    readme: str = ""  # 使用说明
    examples: list[dict] = field(default_factory=list)  # 使用示例

    def save(self, path: Path) -> None:
        """保存能力包到 JSON 文件"""
        with open(path, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=2, ensure_ascii=False)

    @classmethod
    def load(cls, path: Path) -> "CapabilityPackage":
        """从 JSON 文件加载能力包"""
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return cls(**data)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CapabilityPackage":
        """从字典创建"""
        return cls(**data)

    def validate(self) -> list[str]:
        """
        验证能力包完整性

        Returns:
            错误信息列表，空列表表示验证通过
        """
        errors = []

        if not self.name or not self.name.strip():
            errors.append("包名称不能为空")

        if not self.version:
            errors.append("版本号不能为空")

        # 简单的 semver 验证
        version_parts = self.version.split(".")
        if len(version_parts) < 2:
            errors.append("版本号格式应为 semver (如 1.0.0)")

        if not self.description:
            errors.append("功能描述不能为空")

        if not self.author:
            errors.append("作者不能为空")

        return errors


class CapabilityPackageManager:
    """
    能力包管理器

    负责能力包的存储、加载、列表和应用。
    """

    def __init__(self, packages_dir: Path | None = None):
        """
        初始化管理器

        Args:
            packages_dir: 能力包存储目录，默认 ~/.omc/capabilities/
        """
        if packages_dir is None:
            packages_dir = Path.home() / ".omc" / "capabilities"

        self.packages_dir = packages_dir
        self.packages_dir.mkdir(parents=True, exist_ok=True)

    def _get_package_path(self, name: str) -> Path:
        """获取能力包文件路径"""
        return self.packages_dir / f"{name}.json"

    def list_packages(self) -> list[CapabilityPackage]:
        """列出所有本地能力包"""
        packages = []

        if not self.packages_dir.exists():
            return packages

        for file_path in self.packages_dir.glob("*.json"):
            try:
                pkg = CapabilityPackage.load(file_path)
                packages.append(pkg)
            except Exception:
                # 跳过损坏的包
                continue

        # 按创建时间排序（最新的在前）
        packages.sort(key=lambda p: p.created_at, reverse=True)
        return packages

    def get_package(self, name: str) -> CapabilityPackage | None:
        """获取指定名称的能力包"""
        path = self._get_package_path(name)
        if not path.exists():
            return None

        try:
            return CapabilityPackage.load(path)
        except Exception:
            return None

    def save_package(self, package: CapabilityPackage) -> None:
        """保存能力包"""
        path = self._get_package_path(package.name)
        package.save(path)

    def delete_package(self, name: str) -> bool:
        """删除能力包"""
        path = self._get_package_path(name)
        if path.exists():
            path.unlink()
            return True
        return False

    def export_from_config(
        self,
        name: str,
        version: str,
        description: str,
        author: str,
        tags: list[str],
        agents: dict,
        model_config: dict,
        tools: list[str],
        prompts: dict,
        readme: str = "",
        examples: list[dict] | None = None,
    ) -> CapabilityPackage:
        """
        从当前配置导出能力包

        Args:
            name: 包名称
            version: 版本号
            description: 功能描述
            author: 作者
            tags: 标签列表
            agents: Agent 配置（会过滤敏感信息）
            model_config: 模型配置（会过滤敏感信息）
            tools: 工具列表
            prompts: Prompt 模板
            readme: 使用说明
            examples: 使用示例

        Returns:
            创建的能力包
        """
        # 过滤敏感信息
        safe_model_config = self._sanitize_model_config(model_config)
        safe_agents = self._sanitize_agents(agents)

        package = CapabilityPackage(
            name=name,
            version=version,
            description=description,
            author=author,
            created_at=datetime.now().isoformat(),
            tags=tags,
            agents=safe_agents,
            model_config=safe_model_config,
            tools=tools,
            prompts=prompts,
            readme=readme,
            examples=examples or [],
        )

        self.save_package(package)
        return package

    def _sanitize_model_config(self, config: dict) -> dict:
        """清理模型配置中的敏感信息"""
        safe_config = config.copy()

        # 移除或脱敏 API Key
        sensitive_keys = ["api_key", "api_secret", "secret", "token", "password"]
        for key in list(safe_config.keys()):
            if any(sk in key.lower() for sk in sensitive_keys):
                value = safe_config[key]
                if isinstance(value, str) and len(value) > 8:
                    # 保留前4位和后4位，中间用 *** 代替
                    safe_config[key] = value[:4] + "***" + value[-4:]
                else:
                    safe_config[key] = "***"

        return safe_config

    def _sanitize_agents(self, agents: dict) -> dict:
        """清理 Agent 配置中的敏感信息"""
        safe_agents = {}

        for agent_name, agent_config in agents.items():
            if isinstance(agent_config, dict):
                safe_agents[agent_name] = self._sanitize_model_config(agent_config)
            else:
                safe_agents[agent_name] = agent_config

        return safe_agents

    def apply_package(
        self,
        name: str,
        target_config: dict | None = None,
    ) -> dict:
        """
        应用能力包配置

        Args:
            name: 能力包名称
            target_config: 目标配置字典（会被修改）

        Returns:
            应用后的配置
        """
        package = self.get_package(name)
        if package is None:
            raise ValueError(f"能力包不存在: {name}")

        if target_config is None:
            target_config = {}

        # 合并配置
        if package.agents:
            target_config.setdefault("agents", {}).update(package.agents)

        if package.model_config:
            target_config.setdefault("model_config", {}).update(package.model_config)

        if package.tools:
            target_config.setdefault("tools", []).extend(package.tools)
            # 去重
            target_config["tools"] = list(set(target_config["tools"]))

        if package.prompts:
            target_config.setdefault("prompts", {}).update(package.prompts)

        return target_config


# 全局管理器实例
_default_manager: CapabilityPackageManager | None = None


def get_manager() -> CapabilityPackageManager:
    """获取默认的能力包管理器"""
    global _default_manager
    if _default_manager is None:
        _default_manager = CapabilityPackageManager()
    return _default_manager
