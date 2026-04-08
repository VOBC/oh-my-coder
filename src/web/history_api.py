"""
Web UI 增强模块
- 任务历史界面
- Agent 状态面板
- 实时进度增强
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# 创建路由器
history_router = APIRouter(prefix="/api/history", tags=["history"])
agent_router = APIRouter(prefix="/api/agents", tags=["agents"])


# ========================================
# 历史记录存储
# ========================================
class HistoryStore:
    """历史记录存储"""

    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = storage_dir or Path(".omc/history")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._cache: Dict[str, Dict] = {}

    def save(self, task_id: str, record: Dict) -> None:
        """保存历史记录"""
        record["saved_at"] = datetime.now().isoformat()
        self._cache[task_id] = record

        # 持久化到文件
        file_path = self.storage_dir / f"{task_id}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False, indent=2)

    def load(self, task_id: str) -> Optional[Dict]:
        """加载历史记录"""
        if task_id in self._cache:
            return self._cache[task_id]

        file_path = self.storage_dir / f"{task_id}.json"
        if not file_path.exists():
            return None

        with open(file_path, "r", encoding="utf-8") as f:
            record = json.load(f)
            self._cache[task_id] = record
            return record

    def list_all(
        self,
        limit: int = 50,
        offset: int = 0,
        status: Optional[str] = None,
        workflow: Optional[str] = None,
    ) -> List[Dict]:
        """列出所有历史记录"""
        records = []

        for file_path in self.storage_dir.glob("*.json"):
            try:
                record = self.load(file_path.stem)
                if record:
                    # 过滤
                    if status and record.get("status") != status:
                        continue
                    if workflow and record.get("workflow") != workflow:
                        continue
                    records.append(record)
            except Exception:
                continue

        # 按时间排序
        records.sort(key=lambda x: x.get("started_at", ""), reverse=True)
        return records[offset : offset + limit]

    def delete(self, task_id: str) -> bool:
        """删除历史记录"""
        file_path = self.storage_dir / f"{task_id}.json"
        if file_path.exists():
            file_path.unlink()
        if task_id in self._cache:
            del self._cache[task_id]
        return True

    def get_stats(self) -> Dict:
        """获取统计信息"""
        all_records = self.list_all(limit=1000)

        total_tasks = len(all_records)
        completed_tasks = sum(1 for r in all_records if r.get("status") == "completed")
        failed_tasks = sum(1 for r in all_records if r.get("status") == "failed")
        total_tokens = sum(
            r.get("stats", {}).get("total_tokens", 0) for r in all_records
        )
        total_cost = sum(r.get("stats", {}).get("total_cost", 0) for r in all_records)
        total_duration = sum(
            r.get("stats", {}).get("execution_time", 0) for r in all_records
        )

        return {
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "failed_tasks": failed_tasks,
            "success_rate": (
                round(completed_tasks / total_tasks * 100, 1) if total_tasks > 0 else 0
            ),
            "total_tokens": total_tokens,
            "total_cost": round(total_cost, 4),
            "total_duration_hours": round(total_duration / 3600, 2),
        }


history_store = HistoryStore()


# ========================================
# 历史记录 API
# ========================================
class HistoryFilter(BaseModel):
    status: Optional[str] = None
    workflow: Optional[str] = None
    limit: int = Query(default=50, ge=1, le=200)
    offset: int = Query(default=0, ge=0)


@history_router.get("")
async def list_history(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    status: Optional[str] = Query(default=None),
    workflow: Optional[str] = Query(default=None),
):
    """获取历史记录列表"""
    records = history_store.list_all(
        limit=limit,
        offset=offset,
        status=status,
        workflow=workflow,
    )
    stats = history_store.get_stats()

    return JSONResponse(
        {
            "records": records,
            "pagination": {
                "total": stats["total_tasks"],
                "limit": limit,
                "offset": offset,
            },
            "stats": stats,
        }
    )


@history_router.get("/{task_id}")
async def get_history_detail(task_id: str):
    """获取历史记录详情"""
    record = history_store.load(task_id)
    if not record:
        raise HTTPException(status_code=404, detail="Task not found")
    return JSONResponse(record)


@history_router.delete("/{task_id}")
async def delete_history(task_id: str):
    """删除历史记录"""
    success = history_store.delete(task_id)
    return JSONResponse({"success": success})


@history_router.get("/stats/summary")
async def get_history_stats():
    """获取历史统计摘要"""
    stats = history_store.get_stats()

    # 按工作流分组统计
    all_records = history_store.list_all(limit=1000)
    workflow_stats = {}
    for record in all_records:
        wf = record.get("workflow", "unknown")
        if wf not in workflow_stats:
            workflow_stats[wf] = {"count": 0, "success": 0, "failed": 0}
        workflow_stats[wf]["count"] += 1
        if record.get("status") == "completed":
            workflow_stats[wf]["success"] += 1
        else:
            workflow_stats[wf]["failed"] += 1

    stats["workflow_stats"] = workflow_stats
    return JSONResponse(stats)


# ========================================
# Agent 状态管理
# ========================================
class AgentStatusManager:
    """Agent 状态管理器"""

    def __init__(self):
        self._agents: Dict[str, Dict] = {}
        self._status_subscribers: List[asyncio.Queue] = []

    def register_agent(self, name: str, info: Dict) -> None:
        """注册 Agent"""
        self._agents[name] = {
            "name": name,
            "status": "idle",
            "current_task": None,
            "last_activity": None,
            **info,
        }

    def update_status(
        self,
        name: str,
        status: str,
        task: Optional[str] = None,
        progress: Optional[float] = None,
    ) -> None:
        """更新 Agent 状态"""
        if name in self._agents:
            self._agents[name]["status"] = status
            self._agents[name]["current_task"] = task
            self._agents[name]["last_activity"] = datetime.now().isoformat()
            if progress is not None:
                self._agents[name]["progress"] = progress

            # 通知订阅者
            self._notify_subscribers(name)

    def get_agent(self, name: str) -> Optional[Dict]:
        """获取 Agent 状态"""
        return self._agents.get(name)

    def get_all(self) -> List[Dict]:
        """获取所有 Agent 状态"""
        return list(self._agents.values())

    def subscribe(self) -> asyncio.Queue:
        """订阅状态变化"""
        queue: asyncio.Queue = asyncio.Queue()
        self._status_subscribers.append(queue)
        return queue

    def _notify_subscribers(self, agent_name: str) -> None:
        """通知所有订阅者"""
        agent = self._agents.get(agent_name)
        if agent:
            for queue in self._status_subscribers:
                try:
                    queue.put_nowait(
                        {
                            "type": "agent_status",
                            "agent": agent_name,
                            "data": agent,
                        }
                    )
                except asyncio.QueueFull:
                    pass  # 队列满，跳过


agent_status_manager = AgentStatusManager()

# 注册默认 Agents
DEFAULT_AGENTS = [
    {"name": "Planner", "channel": "BUILD", "level": "MEDIUM"},
    {"name": "Architect", "channel": "BUILD", "level": "HIGH"},
    {"name": "Executor", "channel": "BUILD", "level": "LOW"},
    {"name": "Verifier", "channel": "BUILD", "level": "MEDIUM"},
    {"name": "CodeReviewer", "channel": "REVIEW", "level": "MEDIUM"},
    {"name": "SecurityReviewer", "channel": "REVIEW", "level": "HIGH"},
    {"name": "Debugger", "channel": "DEBUG", "level": "MEDIUM"},
    {"name": "Tracer", "channel": "DEBUG", "level": "HIGH"},
    {"name": "TestEngineer", "channel": "DOMAIN", "level": "LOW"},
    {"name": "Designer", "channel": "DOMAIN", "level": "MEDIUM"},
    {"name": "Writer", "channel": "DOMAIN", "level": "LOW"},
    {"name": "Scientist", "channel": "DOMAIN", "level": "HIGH"},
    {"name": "GitMaster", "channel": "DOMAIN", "level": "LOW"},
    {"name": "Coordinator", "channel": "COORDINATION", "level": "MEDIUM"},
    {"name": "Critic", "channel": "COORDINATION", "level": "HIGH"},
]

for agent_info in DEFAULT_AGENTS:
    agent_status_manager.register_agent(agent_info["name"], agent_info)


# ========================================
# Agent 状态 API
# ========================================
@agent_router.get("")
async def list_agents():
    """获取所有 Agent 状态"""
    return JSONResponse({"agents": agent_status_manager.get_all()})


@agent_router.get("/{agent_name}")
async def get_agent_status(agent_name: str):
    """获取单个 Agent 状态"""
    agent = agent_status_manager.get_agent(agent_name)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return JSONResponse(agent)


@agent_router.get("/sse/status")
async def agent_status_sse():
    """SSE 流式推送 Agent 状态变化"""
    from fastapi.responses import StreamingResponse

    queue = agent_status_manager.subscribe()

    async def event_generator():
        while True:
            try:
                data = await asyncio.wait_for(queue.get(), timeout=30.0)
                yield f"data: {json.dumps(data)}\n\n"
            except asyncio.TimeoutError:
                # 发送心跳
                yield ": heartbeat\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
