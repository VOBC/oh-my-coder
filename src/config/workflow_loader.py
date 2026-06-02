"""工作流加载器 - 支持 YAML 格式工作流定义与热重载"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml

from src.core.orchestrator import WORKFLOW_TEMPLATES, WorkflowStep

# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class StepConfig:
    """单个工作流步骤的配置（对应 YAML 中的 step）"""

    id: str
    agent: str
    description: str
    dependencies: list[str] = field(default_factory=list)
    timeout: float = 300.0
    retry: int = 0
    metadata: dict = field(default_factory=dict)

    def to_workflow_step(self) -> WorkflowStep:
        """转换为 orchestrator.WorkflowStep"""
        return WorkflowStep(
            agent_name=self.agent,
            description=self.description,
            dependencies=self.dependencies,
            retry_count=self.retry,
            timeout=self.timeout,
            metadata={**self.metadata, "step_id": self.id},
        )


@dataclass
class WorkflowConfig:
    """完整工作流配置（对应 YAML 文件）"""

    name: str
    description: str = ""
    steps: list[StepConfig] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    source: str = "builtin"  # builtin | user

    def to_workflow_steps(self) -> list[WorkflowStep]:
        """转换为 orchestrator.WorkflowStep 列表"""
        return [s.to_workflow_step() for s in self.steps]


# ---------------------------------------------------------------------------
# WorkflowLoader
# ---------------------------------------------------------------------------


class WorkflowLoader:
    """
    工作流加载器

    特性：
    - 加载默认工作流（src/config/default_workflows/*.yaml）
    - 加载用户工作流（~/.omc/workflows/*.yaml，用户定义优先）
    - 热重载：缓存 + mtime 检查（5秒冷却）
    - 回退：YAML 加载失败时使用 WORKFLOW_TEMPLATES
    """

    def __init__(self, default_workflows_dir: Optional[Path] = None) -> None:
        """
        Args:
            default_workflows_dir: 默认工作流目录（默认：src/config/default_workflows）
        """
        # 项目根路径
        project_root = Path(__file__).parent.parent.parent
        self._default_dir = (
            default_workflows_dir
            or project_root / "src" / "config" / "default_workflows"
        )
        self._user_dir = Path.home() / ".omc" / "workflows"

        # 缓存：workflow_name -> (cached_at, mtime, config)
        self._cache: dict[str, tuple[float, float, WorkflowConfig]] = {}
        self._cache_ttl = 5.0  # 5秒冷却

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_workflow(self, name: str) -> list[WorkflowStep]:
        """
        加载工作流步骤列表。

        优先从 YAML 加载，用户 workflows 覆盖默认。
        加载失败时 fallback 到 WORKFLOW_TEMPLATES。

        Args:
            name: 工作流名称

        Returns:
            list[WorkflowStep]: 步骤列表
        """
        config = self.get_workflow_config(name)
        if config:
            return config.to_workflow_steps()
        # Fallback
        return WORKFLOW_TEMPLATES.get(name, [])

    def list_workflows(self) -> list[str]:
        """返回所有工作流名称（含来源）"""
        names: set[str] = set()

        # 默认工作流
        if self._default_dir.exists():
            for p in self._default_dir.glob("*.yaml"):
                names.add(p.stem)

        # 用户工作流
        if self._user_dir.exists():
            for p in self._user_dir.glob("*.yaml"):
                names.add(p.stem)

        # WORKFLOW_TEMPLATES 中的额外条目（未写成 YAML 的兜底）
        names.update(WORKFLOW_TEMPLATES.keys())

        return sorted(names)

    def list_builtins(self) -> list[str]:
        """返回内置工作流名称列表"""
        names: set[str] = set()
        if self._default_dir.exists():
            for p in self._default_dir.glob("*.yaml"):
                names.add(p.stem)
        names.update(WORKFLOW_TEMPLATES.keys())
        return sorted(names)

    def is_builtin(self, name: str) -> bool:
        """判断是否为内置工作流"""
        return name in self.list_builtins()

    def parse_yaml_string(
        self, yaml_str: str, name: str = ""
    ) -> Optional[WorkflowConfig]:
        """
        将 YAML 字符串解析为 WorkflowConfig。

        Args:
            yaml_str: YAML 内容字符串
            name: 工作流名称（用于报错上下文）

        Returns:
            WorkflowConfig 或解析失败时 None
        """
        try:
            raw = yaml.safe_load(yaml_str) or {}
            steps = []
            for s in raw.get("steps", []):
                steps.append(
                    StepConfig(
                        id=s.get("id", s.get("agent", "step")),
                        agent=s.get("agent", ""),
                        description=s.get("description", ""),
                        dependencies=list(s.get("dependencies", [])),
                        timeout=float(s.get("timeout", 300)),
                        retry=int(s.get("retry", 0)),
                        metadata=s.get("metadata", {}),
                    )
                )
            return WorkflowConfig(
                name=raw.get("name", name) or name,
                description=raw.get("description", ""),
                steps=steps,
                metadata=raw.get("metadata", {}),
                source="user",
            )
        except Exception:
            return None

    def get_workflow_config(self, name: str) -> Optional[WorkflowConfig]:
        """
        获取完整工作流配置（含 metadata）。

        热重载：检查文件 mtime，5秒内不重复读取。

        Args:
            name: 工作流名称

        Returns:
            WorkflowConfig 或 None（找不到时返回 None，由调用方 fallback）
        """
        # 用户 workflows 优先
        user_path = self._user_dir / f"{name}.yaml"
        default_path = self._default_dir / f"{name}.yaml"

        # 确定要读取的文件（优先用户）
        file_path: Optional[Path] = None
        source = "user"
        if user_path.exists():
            file_path = user_path
        elif default_path.exists():
            file_path = default_path
            source = "builtin"

        # 检查缓存
        now = time.time()
        if name in self._cache:
            cached_at, cached_mtime, config = self._cache[name]
            if now - cached_at < self._cache_ttl:
                if file_path is None or cached_mtime >= file_path.stat().st_mtime:
                    return config

        # 无缓存或已过期，重新加载
        if file_path is None:
            # 没有 YAML 文件 → 从缓存中移除（强制 fallback）
            self._cache.pop(name, None)
            return None

        try:
            with open(file_path, encoding="utf-8") as f:
                raw = yaml.safe_load(f) or {}

            steps = []
            for s in raw.get("steps", []):
                steps.append(
                    StepConfig(
                        id=s.get("id", s.get("agent", "step")),
                        agent=s.get("agent", ""),
                        description=s.get("description", ""),
                        dependencies=list(s.get("dependencies", [])),
                        timeout=float(s.get("timeout", 300)),
                        retry=int(s.get("retry", 0)),
                        metadata=s.get("metadata", {}),
                    )
                )

            config = WorkflowConfig(
                name=raw.get("name", name),
                description=raw.get("description", ""),
                steps=steps,
                metadata=raw.get("metadata", {}),
                source=source,
            )

            # 写入缓存
            mtime = file_path.stat().st_mtime
            self._cache[name] = (now, mtime, config)
            return config

        except Exception:
            # YAML 解析失败 → 从缓存移除，强制 fallback
            self._cache.pop(name, None)
            return None

    def _ensure_user_dir(self) -> None:
        """确保用户工作流目录存在"""
        self._user_dir.mkdir(parents=True, exist_ok=True)

    def save_workflow(self, name: str, config: WorkflowConfig) -> Path:
        """
        保存用户工作流到 ~/.omc/workflows/。

        Args:
            name: 工作流名称
            config: 工作流配置

        Returns:
            Path: 保存的文件路径
        """
        self._ensure_user_dir()
        file_path = self._user_dir / f"{name}.yaml"

        data = {
            "name": name,
            "description": config.description,
            "steps": [
                {
                    "id": s.id,
                    "agent": s.agent,
                    "description": s.description,
                    "dependencies": s.dependencies,
                    "timeout": s.timeout,
                    "retry": s.retry,
                }
                for s in config.steps
            ],
        }

        with open(file_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False)

        # 使缓存失效
        self._cache.pop(name, None)
        return file_path

    def delete_workflow(self, name: str) -> bool:
        """
        删除用户工作流（~/.omc/workflows/<name>.yaml）。

        内置工作流不可删除（返回 False）。

        Args:
            name: 工作流名称

        Returns:
            bool: 是否删除成功
        """
        # 内置工作流检查（存在 default_workflows 中的）
        default_path = self._default_dir / f"{name}.yaml"
        if default_path.exists():
            return False

        user_path = self._user_dir / f"{name}.yaml"
        if user_path.exists():
            user_path.unlink()
            self._cache.pop(name, None)
            return True
        return False
