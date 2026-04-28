"""
Agent 状态持久化存储

功能：
- save: 保存 Agent 配置、历史、状态到 ~/.oh-my-coder/agents/<name>/
- restore: 从磁盘恢复 Agent 会话
- export: 打包 Agent 为 JSON（可分享）
- import: 从 JSON 导入 Agent 配置
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import builtins

# 默认存储根目录
DEFAULT_STORE_ROOT = Path.home() / ".oh-my-coder" / "agents"


@dataclass
class AgentConfig:
    """Agent 配置快照"""

    name: str
    description: str = ""
    model: str = "deepseek"
    lane: str = "build"
    default_tier: str = "standard"
    tools: list[str] = field(default_factory=list)
    max_tokens: int = 8000
    temperature: float = 0.7
    timeout: int = 60
    system_prompt: str = ""


@dataclass
class HistoryEntry:
    """单条对话历史"""

    role: str  # "user" | "assistant" | "system"
    content: str
    timestamp: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> HistoryEntry:
        return cls(
            role=data["role"],
            content=data["content"],
            timestamp=data["timestamp"],
            metadata=data.get("metadata", {}),
        )


@dataclass
class AgentState:
    """Agent 运行时状态"""

    agent_name: str
    session_id: str = ""
    created_at: str = ""
    updated_at: str = ""
    total_tokens: int = 0
    total_cost: float = 0.0
    workflow_id: str = ""
    last_task: str = ""
    checkpoints: list[str] = field(default_factory=list)
    custom_state: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_name": self.agent_name,
            "session_id": self.session_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "total_tokens": self.total_tokens,
            "total_cost": self.total_cost,
            "workflow_id": self.workflow_id,
            "last_task": self.last_task,
            "checkpoints": self.checkpoints,
            "custom_state": self.custom_state,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AgentState:
        return cls(
            agent_name=data.get("agent_name", ""),
            session_id=data.get("session_id", ""),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            total_tokens=data.get("total_tokens", 0),
            total_cost=data.get("total_cost", 0.0),
            workflow_id=data.get("workflow_id", ""),
            last_task=data.get("last_task", ""),
            checkpoints=data.get("checkpoints", []),
            custom_state=data.get("custom_state", {}),
        )


class AgentStateStore:
    """
    Agent 状态持久化管理器

    用法:
        store = AgentStateStore()

        # 保存 Agent
        store.save("planner", config, history, state)

        # 恢复 Agent
        config, history, state = store.restore("planner")

        # 导出为 JSON
        store.export("planner", "planner-backup.json")

        # 从 JSON 导入
        store.import_agent("planner-backup.json")
    """

    def __init__(self, store_root: Path | None = None):
        self.store_root = store_root or DEFAULT_STORE_ROOT
        self.store_root.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # 核心操作
    # ------------------------------------------------------------------

    def save(
        self,
        agent_name: str,
        config: AgentConfig,
        history: list[HistoryEntry] | None = None,
        state: AgentState | None = None,
        append_history: bool = True,
    ) -> Path:
        """
        保存 Agent 状态到磁盘

        Args:
            agent_name: Agent 名称
            config: Agent 配置
            history: 对话历史（可选）
            state: 运行时状态（可选）
            append_history: 是否追加历史（True=追加到 jsonl，False=覆盖）

        Returns:
            Agent 目录路径
        """
        agent_dir = self.store_root / agent_name
        agent_dir.mkdir(parents=True, exist_ok=True)

        # 1. 写 config.json
        config_file = agent_dir / "config.json"
        config_data = {
            "name": config.name,
            "description": config.description,
            "model": config.model,
            "lane": config.lane,
            "default_tier": config.default_tier,
            "tools": config.tools,
            "max_tokens": config.max_tokens,
            "temperature": config.temperature,
            "timeout": config.timeout,
            "system_prompt": config.system_prompt,
        }
        config_file.write_text(
            json.dumps(config_data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        # 2. 写 history.jsonl（追加模式）
        if history:
            history_file = agent_dir / "history.jsonl"
            mode = "a" if append_history else "w"
            with open(history_file, mode, encoding="utf-8") as f:
                for entry in history:
                    f.write(json.dumps(entry.to_dict(), ensure_ascii=False) + "\n")

        # 3. 写 state.json
        if state:
            state_file = agent_dir / "state.json"
            state.updated_at = time.strftime("%Y-%m-%dT%H:%M:%S")
            state_file.write_text(
                json.dumps(state.to_dict(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

        return agent_dir

    def restore(
        self, agent_name: str, include_history: bool = True
    ) -> tuple[AgentConfig | None, list[HistoryEntry], AgentState | None]:
        """
        从磁盘恢复 Agent 状态

        Args:
            agent_name: Agent 名称
            include_history: 是否加载历史（可能很大）

        Returns:
            (config, history, state) 元组，不存在时返回 (None, [], None)
        """
        agent_dir = self.store_root / agent_name
        if not agent_dir.exists():
            return None, [], None

        # 1. 读 config.json
        config_file = agent_dir / "config.json"
        config: AgentConfig | None = None
        if config_file.exists():
            data = json.loads(config_file.read_text(encoding="utf-8"))
            config = AgentConfig(
                name=data.get("name", agent_name),
                description=data.get("description", ""),
                model=data.get("model", "deepseek"),
                lane=data.get("lane", "build"),
                default_tier=data.get("default_tier", "standard"),
                tools=data.get("tools", []),
                max_tokens=data.get("max_tokens", 8000),
                temperature=data.get("temperature", 0.7),
                timeout=data.get("timeout", 60),
                system_prompt=data.get("system_prompt", ""),
            )

        # 2. 读 history.jsonl
        history: list[HistoryEntry] = []
        if include_history:
            history_file = agent_dir / "history.jsonl"
            if history_file.exists():
                for line in history_file.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line:
                        try:
                            entry_data = json.loads(line)
                            history.append(HistoryEntry.from_dict(entry_data))
                        except json.JSONDecodeError:
                            continue

        # 3. 读 state.json
        state_file = agent_dir / "state.json"
        state: AgentState | None = None
        if state_file.exists():
            data = json.loads(state_file.read_text(encoding="utf-8"))
            state = AgentState.from_dict(data)

        return config, history, state

    def delete(self, agent_name: str) -> bool:
        """删除 Agent 状态目录"""
        import shutil

        agent_dir = self.store_root / agent_name
        if agent_dir.exists():
            shutil.rmtree(agent_dir)
            return True
        return False

    def list_saved(self) -> builtins.list[str]:
        """列出所有已保存的 Agent"""
        return [d.name for d in self.store_root.iterdir() if d.is_dir()]

    # ------------------------------------------------------------------
    # 导出 / 导入
    # ------------------------------------------------------------------

    def export_agent(
        self,
        agent_name: str,
        output_path: Path,
        include_history: bool = False,
        max_history: int = 100,
    ) -> Path:
        """
        导出 Agent 为单个 JSON 文件（可分享）

        Args:
            agent_name: Agent 名称
            output_path: 输出文件路径
            include_history: 是否包含历史
            max_history: 最多导出的历史条数

        Returns:
            输出文件路径
        """
        config, history, state = self.restore(
            agent_name, include_history=include_history
        )
        if config is None:
            raise FileNotFoundError(f"Agent '{agent_name}' 不存在")

        export_data: dict[str, Any] = {
            "format_version": "1.0",
            "exported_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "agent_name": agent_name,
            "config": {
                "name": config.name,
                "description": config.description,
                "model": config.model,
                "lane": config.lane,
                "default_tier": config.default_tier,
                "tools": config.tools,
                "max_tokens": config.max_tokens,
                "temperature": config.temperature,
                "timeout": config.timeout,
                "system_prompt": config.system_prompt,
            },
        }

        if state:
            export_data["state"] = state.to_dict()

        if include_history and history:
            export_data["history"] = [e.to_dict() for e in history[-max_history:]]

        output_path.write_text(
            json.dumps(export_data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return output_path

    def import_agent(
        self,
        source_path: Path,
        new_name: str | None = None,
        merge_history: bool = False,
    ) -> str:
        """
        从 JSON 文件导入 Agent

        Args:
            source_path: 源文件路径
            new_name: 新名称（可选，默认用文件中的名称）
            merge_history: 是否合并历史（True=追加，False=覆盖）

        Returns:
            导入后的 Agent 名称
        """
        data = json.loads(source_path.read_text(encoding="utf-8"))

        # 解析配置
        config_data = data.get("config", {})
        config = AgentConfig(
            name=new_name or data.get("agent_name", config_data.get("name", "unnamed")),
            description=config_data.get("description", ""),
            model=config_data.get("model", "deepseek"),
            lane=config_data.get("lane", "build"),
            default_tier=config_data.get("default_tier", "standard"),
            tools=config_data.get("tools", []),
            max_tokens=config_data.get("max_tokens", 8000),
            temperature=config_data.get("temperature", 0.7),
            timeout=config_data.get("timeout", 60),
            system_prompt=config_data.get("system_prompt", ""),
        )

        # 解析状态
        state: AgentState | None = None
        if "state" in data:
            state = AgentState.from_dict(data["state"])
            state.agent_name = config.name

        # 解析历史
        history: list[HistoryEntry] = []
        if "history" in data:
            for entry_data in data["history"]:
                history.append(HistoryEntry.from_dict(entry_data))

        # 如果 merge_history，先加载现有历史
        if merge_history:
            _, existing_history, _ = self.restore(config.name, include_history=True)
            history = existing_history + history

        # 保存
        self.save(config.name, config, history if history else None, state)
        return config.name

    # ------------------------------------------------------------------
    # 快捷方法
    # ------------------------------------------------------------------

    def save_from_agent_instance(
        self,
        agent_instance: Any,
        history: list[HistoryEntry] | None = None,
        custom_state: dict[str, Any] | None = None,
    ) -> Path:
        """
        从 Agent 实例保存状态（便捷方法）

        Args:
            agent_instance: Agent 实例（需要有 name, description 等属性）
            history: 对话历史
            custom_state: 自定义状态数据

        Returns:
            Agent 目录路径
        """
        config = AgentConfig(
            name=getattr(agent_instance, "name", "unnamed"),
            description=getattr(agent_instance, "description", ""),
            model=getattr(agent_instance, "model", "deepseek"),
            lane=getattr(agent_instance, "lane", "build"),
            default_tier=getattr(agent_instance, "default_tier", "standard"),
            tools=getattr(agent_instance, "tools", []),
            max_tokens=getattr(agent_instance, "max_tokens", 8000),
            temperature=getattr(agent_instance, "temperature", 0.7),
            timeout=getattr(agent_instance, "timeout", 60),
            system_prompt=getattr(agent_instance, "system_prompt", ""),
        )

        state = AgentState(
            agent_name=config.name,
            custom_state=custom_state or {},
        )

        return self.save(config.name, config, history, state)

    def get_stats(self) -> dict[str, Any]:
        """获取存储统计"""
        agents = self.list_saved()
        total_size = 0
        total_history_entries = 0

        for agent_name in agents:
            agent_dir = self.store_root / agent_name
            for f in agent_dir.rglob("*"):
                if f.is_file():
                    total_size += f.stat().st_size

            _, history, _ = self.restore(agent_name, include_history=True)
            total_history_entries += len(history)

        return {
            "total_agents": len(agents),
            "total_size_bytes": total_size,
            "total_history_entries": total_history_entries,
            "store_root": str(self.store_root),
        }
