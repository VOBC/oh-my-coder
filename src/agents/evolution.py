"""
Agent 自进化模块 - Evolution System

让 Agent 像生物基因一样遗传、变异、进化。
存储进化历史、成功模式库、优化的 system prompt。

目录结构：
.omc/state/agents/{agent_name}/
├── evolution_history.json  # 进化记录
├── success_patterns.json   # 成功模式库
└── optimized_prompt.md     # 优化后的 prompt
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class EvolutionRecord:
    """进化记录"""

    id: str = ""  # 时间戳-based ID
    timestamp: str = ""
    agent_type: str = ""
    generation: int = 1  # 进化代数
    trigger: str = ""  # 触发原因：success_rate_low, user_correction, error_pattern
    before_state: Dict[str, Any] = field(default_factory=dict)  # 进化前状态
    after_state: Dict[str, Any] = field(default_factory=dict)  # 进化后状态
    changes: List[str] = field(default_factory=list)  # 变更列表
    effectiveness: Optional[float] = None  # 效果评分（后续验证）


@dataclass
class SuccessPattern:
    """成功模式"""

    id: str = ""
    pattern_type: str = ""  # strategy, workflow, prompt_technique
    description: str = ""
    context: str = ""  # 适用上下文
    effectiveness_score: float = 0.0
    occurrences: int = 0  # 出现次数
    last_seen: str = ""
    examples: List[str] = field(default_factory=list)  # 成功案例


@dataclass
class EvolutionConfig:
    """自进化配置"""

    enabled: bool = True  # 是否开启自进化
    improvement_threshold: float = 0.8  # 成功率阈值，低于此触发优化
    min_samples: int = 5  # 最小样本数，少于此不触发进化分析
    max_evolution_history: int = 100  # 最大进化历史记录数
    pattern_confidence_threshold: float = 0.7  # 模式置信度阈值
    evolution_cooldown_hours: int = 24  # 进化冷却时间（小时）


class EvolutionStore:
    """进化状态存储"""

    def __init__(self, state_dir: Path):
        """
        Args:
            state_dir: .omc/state 目录
        """
        self.state_dir = Path(state_dir)
        self.agents_dir = self.state_dir / "agents"

    def _agent_dir(self, agent_name: str) -> Path:
        """获取 Agent 进化目录"""
        agent_dir = self.agents_dir / agent_name
        agent_dir.mkdir(parents=True, exist_ok=True)
        return agent_dir

    # ------------------------------------------------------------------
    # 进化历史
    # ------------------------------------------------------------------

    def load_evolution_history(
        self, agent_name: str, limit: int = 50
    ) -> List[EvolutionRecord]:
        """加载进化历史"""
        history_file = self._agent_dir(agent_name) / "evolution_history.json"
        if not history_file.exists():
            return []

        try:
            data = json.loads(history_file.read_text(encoding="utf-8"))
            records = [EvolutionRecord(**r) for r in data.get("records", [])]
            return records[:limit]
        except (json.JSONDecodeError, KeyError):
            return []

    def save_evolution_record(self, record: EvolutionRecord) -> str:
        """保存进化记录"""
        agent_name = record.agent_type
        history_file = self._agent_dir(agent_name) / "evolution_history.json"

        # 读取现有历史
        existing = []
        if history_file.exists():
            try:
                data = json.loads(history_file.read_text(encoding="utf-8"))
                existing = data.get("records", [])
            except (json.JSONDecodeError, KeyError):
                existing = []

        # 添加新记录
        record_dict = {
            "id": record.id or f"evo-{int(time.time())}",
            "timestamp": record.timestamp or time.strftime("%Y-%m-%d %H:%M:%S"),
            "agent_type": record.agent_type,
            "generation": record.generation,
            "trigger": record.trigger,
            "before_state": record.before_state,
            "after_state": record.after_state,
            "changes": record.changes,
            "effectiveness": record.effectiveness,
        }
        existing.append(record_dict)

        # 限制历史长度
        max_records = 100
        if len(existing) > max_records:
            existing = existing[-max_records:]

        # 保存
        history_file.write_text(
            json.dumps({"records": existing}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return record_dict["id"]

    def get_current_generation(self, agent_name: str) -> int:
        """获取当前进化代数"""
        history = self.load_evolution_history(agent_name, limit=1)
        if not history:
            return 1
        return max(1, history[0].generation + 1)

    # ------------------------------------------------------------------
    # 成功模式库
    # ------------------------------------------------------------------

    def load_success_patterns(self, agent_name: str) -> List[SuccessPattern]:
        """加载成功模式库"""
        patterns_file = self._agent_dir(agent_name) / "success_patterns.json"
        if not patterns_file.exists():
            return []

        try:
            data = json.loads(patterns_file.read_text(encoding="utf-8"))
            return [SuccessPattern(**p) for p in data.get("patterns", [])]
        except (json.JSONDecodeError, KeyError):
            return []

    def save_success_pattern(self, pattern: SuccessPattern) -> str:
        """保存成功模式"""
        # 直接调用内部方法保存
        return self._save_pattern_internal(pattern)

    def _save_pattern_internal(self, pattern: SuccessPattern) -> str:
        """内部方法：保存成功模式"""
        # 从 pattern.id 提取 agent_name（假设格式：agentname-patternid）
        agent_name = pattern.id.split("-")[0] if "-" in pattern.id else "default"
        patterns_file = self._agent_dir(agent_name) / "success_patterns.json"

        existing = []
        if patterns_file.exists():
            try:
                data = json.loads(patterns_file.read_text(encoding="utf-8"))
                existing = data.get("patterns", [])
            except (json.JSONDecodeError, KeyError):
                existing = []

        pattern_dict = {
            "id": pattern.id or f"pattern-{int(time.time())}",
            "pattern_type": pattern.pattern_type,
            "description": pattern.description,
            "context": pattern.context,
            "effectiveness_score": pattern.effectiveness_score,
            "occurrences": pattern.occurrences,
            "last_seen": pattern.last_seen or time.strftime("%Y-%m-%d %H:%M:%S"),
            "examples": pattern.examples,
        }

        # 查找是否已存在，存在则更新
        found = False
        for i, p in enumerate(existing):
            if p.get("id") == pattern_dict["id"]:
                existing[i] = pattern_dict
                found = True
                break

        if not found:
            existing.append(pattern_dict)

        patterns_file.write_text(
            json.dumps({"patterns": existing}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return pattern_dict["id"]

    def add_success_pattern(
        self,
        agent_name: str,
        pattern_type: str,
        description: str,
        context: str = "",
        example: str = "",
    ) -> str:
        """添加成功模式"""
        patterns_file = self._agent_dir(agent_name) / "success_patterns.json"

        existing = []
        if patterns_file.exists():
            try:
                data = json.loads(patterns_file.read_text(encoding="utf-8"))
                existing = data.get("patterns", [])
            except (json.JSONDecodeError, KeyError):
                existing = []

        # 检查是否已有类似模式
        pattern_id = f"{agent_name}-{pattern_type}-{int(time.time())}"

        pattern_dict = {
            "id": pattern_id,
            "pattern_type": pattern_type,
            "description": description,
            "context": context,
            "effectiveness_score": 0.7,  # 初始置信度
            "occurrences": 1,
            "last_seen": time.strftime("%Y-%m-%d %H:%M:%S"),
            "examples": [example] if example else [],
        }

        existing.append(pattern_dict)

        patterns_file.write_text(
            json.dumps({"patterns": existing}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return pattern_id

    # ------------------------------------------------------------------
    # 优化 Prompt
    # ------------------------------------------------------------------

    def load_optimized_prompt(self, agent_name: str) -> Optional[str]:
        """加载优化后的 system prompt"""
        prompt_file = self._agent_dir(agent_name) / "optimized_prompt.md"
        if not prompt_file.exists():
            return None
        return prompt_file.read_text(encoding="utf-8")

    def save_optimized_prompt(self, agent_name: str, prompt: str) -> None:
        """保存优化后的 system prompt"""
        prompt_file = self._agent_dir(agent_name) / "optimized_prompt.md"
        prompt_file.write_text(prompt, encoding="utf-8")

    def get_prompt_version(self, agent_name: str) -> int:
        """获取 prompt 版本号"""
        prompt_file = self._agent_dir(agent_name) / "optimized_prompt.md"
        if not prompt_file.exists():
            return 0
        content = prompt_file.read_text(encoding="utf-8")
        # 从文件中提取版本号
        for line in content.split("\n")[:5]:
            if "version:" in line.lower():
                try:
                    return int(line.split(":")[-1].strip())
                except ValueError:
                    pass
        return 1

    # ------------------------------------------------------------------
    # 统计信息
    # ------------------------------------------------------------------

    def get_evolution_stats(self, agent_name: str) -> Dict[str, Any]:
        """获取进化统计信息"""
        history = self.load_evolution_history(agent_name)
        patterns = self.load_success_patterns(agent_name)
        prompt_version = self.get_prompt_version(agent_name)

        return {
            "agent_name": agent_name,
            "current_generation": self.get_current_generation(agent_name),
            "total_evolutions": len(history),
            "total_patterns": len(patterns),
            "prompt_version": prompt_version,
            "last_evolution": history[0].timestamp if history else None,
        }
