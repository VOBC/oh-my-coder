"""
Agent 配置模块 - 支持 YAML/JSON 配置加载

用法:
    from src.config.agent_config import AgentConfig, load_config_file

    config = load_config_file("agents/code_review.yaml")
    agent = config.to_agent()
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# ─────────────────────────────────────────────────────────────
# 数据模型
# ─────────────────────────────────────────────────────────────


@dataclass
class ToolConfig:
    """工具配置"""

    name: str
    enabled: bool = True
    options: dict[str, Any] = field(default_factory=dict)


@dataclass
class EnvironmentConfig:
    """环境配置"""

    max_tokens: int = 8000
    temperature: float = 0.7
    timeout: int = 60
    retry: int = 3


@dataclass
class PromptTemplate:
    """Prompt 模板"""

    name: str
    template: str
    variables: list[str] = field(default_factory=list)


@dataclass
class AgentConfig:
    """Agent 配置"""

    name: str
    description: str
    model: str = "deepseek"
    tools: list[str] = field(default_factory=list)
    permissions: dict[str, Any] = field(default_factory=dict)
    environment: EnvironmentConfig = field(default_factory=EnvironmentConfig)
    prompts: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def get_system_prompt(self) -> str:
        """获取 system prompt"""
        return self.prompts.get("system", f"你是一个专业的 {self.name} Agent。")

    def get_prompt_template(self, key: str) -> str:
        """获取指定 key 的 prompt 模板，支持 {{变量}} 替换"""
        return self.prompts.get(key, "")

    def render_template(self, key: str, **kwargs: Any) -> str:
        """渲染 prompt 模板，替换 {{变量}}"""
        template = self.get_prompt_template(key)
        for var_name, var_value in kwargs.items():
            template = template.replace(f"{{{{{var_name}}}}}", str(var_value))
        return template

    def to_dict(self) -> dict[str, Any]:
        """序列化为 dict"""
        return {
            "name": self.name,
            "description": self.description,
            "model": self.model,
            "tools": self.tools,
            "permissions": self.permissions,
            "environment": {
                "max_tokens": self.environment.max_tokens,
                "temperature": self.environment.temperature,
                "timeout": self.environment.timeout,
                "retry": self.environment.retry,
            },
            "prompts": self.prompts,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AgentConfig:
        """从 dict 反序列化"""
        env_data = data.get("environment", {})
        env = EnvironmentConfig(
            max_tokens=env_data.get("max_tokens", 8000),
            temperature=env_data.get("temperature", 0.7),
            timeout=env_data.get("timeout", 60),
            retry=env_data.get("retry", 3),
        )
        return cls(
            name=data["name"],
            description=data.get("description", ""),
            model=data.get("model", "deepseek"),
            tools=data.get("tools", []),
            permissions=data.get("permissions", {}),
            environment=env,
            prompts=data.get("prompts", {}),
            metadata=data.get("metadata", {}),
        )

    def validate(self) -> list[str]:
        """验证配置合法性，返回错误列表"""
        errors = []

        if not self.name or not re.match(r"^[a-z0-9_-]+$", self.name):
            errors.append("name 必须是字母/数字/下划线/连字符组合")

        if self.environment.max_tokens < 100:
            errors.append("max_tokens 最小为 100")

        if not (0 <= self.environment.temperature <= 2):
            errors.append("temperature 必须在 0-2 之间")

        denied = self.permissions.get("denied_patterns", [])
        if denied:
            for pattern in denied:
                try:
                    re.compile(pattern)
                except re.error as e:
                    errors.append(f"denied_patterns 正则错误: {e}")

        return errors


# ─────────────────────────────────────────────────────────────
# 加载器
# ─────────────────────────────────────────────────────────────


def load_config_file(path: str | Path) -> AgentConfig:
    """
    加载 YAML 或 JSON 格式的 Agent 配置文件

    Args:
        path: 配置文件路径

    Returns:
        AgentConfig 实例

    Raises:
        FileNotFoundError: 文件不存在
        ValueError: 格式不支持或解析失败
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"配置文件不存在: {path}")

    raw = p.read_text(encoding="utf-8")

    if p.suffix in (".yaml", ".yml"):
        data = _load_yaml(raw)
    elif p.suffix == ".json":
        data = json.loads(raw)
    else:
        raise ValueError(f"不支持的文件格式: {p.suffix}，仅支持 .yaml/.yml/.json")

    return AgentConfig.from_dict(data)


def load_config_dir(dir_path: str | Path) -> list[AgentConfig]:
    """
    加载目录下所有 YAML/JSON 配置文件

    Args:
        dir_path: 目录路径

    Returns:
        AgentConfig 列表
    """
    p = Path(dir_path)
    if not p.is_dir():
        return []

    configs: list[AgentConfig] = []
    for ext in ("*.yaml", "*.yml", "*.json"):
        for fp in p.glob(ext):
            try:
                configs.append(load_config_file(fp))
            except Exception:
                pass  # 跳过解析失败的文件

    return configs


def validate_config_file(path: str | Path) -> tuple[bool, list[str]]:
    """
    验证配置文件合法性

    Returns:
        (是否合法, 错误列表)
    """
    try:
        config = load_config_file(path)
        errors = config.validate()
        return len(errors) == 0, errors
    except FileNotFoundError:
        return False, ["配置文件不存在"]
    except Exception as e:
        return False, [f"解析失败: {type(e).__name__}"]


def list_configs_in_dir(dir_path: str | Path) -> list[str]:
    """列出目录下所有配置文件的绝对路径"""
    p = Path(dir_path)
    if not p.is_dir():
        return []

    result: list[str] = []
    for ext in ("*.yaml", "*.yml", "*.json"):
        result.extend([str(fp.resolve()) for fp in p.glob(ext)])

    return sorted(result)


# ─────────────────────────────────────────────────────────────
# 内部
# ─────────────────────────────────────────────────────────────


def _load_yaml(raw: str) -> dict[str, Any]:
    """解析 YAML（使用标准库实现，零依赖）"""
    try:
        from ._yaml import yaml_safe_load

        return yaml_safe_load(raw)
    except ImportError:
        pass

    # 标准库 fallback：手动解析简单 YAML
    result: dict[str, Any] = {}
    current_key: str | None = None
    current_list: list[str] | None = None
    current_dict: dict[str, Any] | None = None
    in_dict = False

    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        # 检测缩进
        content = stripped.rstrip()

        # 列表项
        if content.startswith("- "):
            item = content[2:].strip()
            if current_list is not None:
                current_list.append(item)
            elif current_dict is not None:
                # dict 中的列表
                if current_key:
                    if current_key not in result:
                        result[current_key] = []
                    result[current_key].append(item)
        elif ":" in content and not content.startswith(":"):
            key, _, value = content.partition(":")
            key = key.strip()
            value = value.strip()

            if value:
                # 简单键值对
                if current_dict is not None:
                    current_dict[key] = _parse_value(value)
                else:
                    result[key] = _parse_value(value)
            else:
                # 嵌套对象
                if in_dict and current_dict is not None:
                    # 处理 dict 结束
                    if current_key and current_key not in result:
                        result[current_key] = current_dict
                current_key = key
                current_dict = {}
                in_dict = True

    if current_dict and current_key:
        result[current_key] = current_dict

    return result


def _parse_value(value: str) -> Any:
    """解析 YAML 值"""
    v = value.strip('"').strip("'")
    if v.lower() == "true":
        return True
    if v.lower() == "false":
        return False
    if v.lower() == "null":
        return None
    try:
        return int(v)
    except ValueError:
        pass
    try:
        return float(v)
    except ValueError:
        pass
    return v
