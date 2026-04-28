"""
Agent 状态持久化模块

将 Agent 会话状态保存到本地文件系统，支持重启恢复和 export/import。

目录结构:
    ~/.oh-my-coder/agents/<agent_name>/
    ├── config.json       # Agent 配置快照
    ├── history.jsonl     # 对话历史（append-only）
    └── state.json        # 运行时状态
"""

from .store import AgentStateStore

__all__ = ["AgentStateStore"]
