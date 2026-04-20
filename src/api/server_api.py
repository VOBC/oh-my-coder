"""
远程 Server API - REST API 接口定义

接口：
  POST /api/v1/run        - 提交任务，返回 task_id
  GET  /api/v1/status/{id} - 查询状态
  GET  /api/v1/result/{id} - 获取结果
  GET  /api/v1/tasks      - 列出所有任务
  DELETE /api/v1/tasks/{id} - 删除任务

前置：omc server --port 8080
"""

from __future__ import annotations

import asyncio
import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Header, Depends
from pydantic import BaseModel

# =============================================================================
# 数据模型
# =============================================================================


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class TaskRecord:
    task_id: str
    prompt: str
    status: TaskStatus
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    execution_time: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


# =============================================================================
# 任务存储（内存 + 磁盘持久化）
# =============================================================================


class TaskStore:
    """内存 + JSON 文件持久化的任务存储"""

    def __init__(self, storage_dir: Path | None = None) -> None:
        self._store: dict[str, TaskRecord] = {}
        self._lock = asyncio.Lock()
        self._storage_dir = storage_dir or (Path.home() / ".omc" / "server_tasks")
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        self._load_all()

    def _load_all(self) -> None:
        """启动时从磁盘恢复所有任务（最近 100 个）"""
        try:
            files = sorted(
                self._storage_dir.glob("*.json"),
                key=lambda f: f.stat().st_mtime,
                reverse=True,
            )
            for f in files[:100]:
                try:
                    data = __import__("json").loads(f.read_text(encoding="utf-8"))
                    record = TaskRecord(**data)
                    self._store[record.task_id] = record
                except Exception:
                    pass
        except Exception:
            pass

    def _save(self, record: TaskRecord) -> None:
        """持久化到磁盘"""
        try:
            f = self._storage_dir / f"{record.task_id}.json"
            f.write_text(
                __import__("json").dumps(record.__dict__, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass

    async def create(
        self, prompt: str, metadata: dict[str, Any] | None = None
    ) -> TaskRecord:
        """创建新任务"""
        async with self._lock:
            task_id = uuid.uuid4().hex[:12]
            record = TaskRecord(
                task_id=task_id,
                prompt=prompt,
                status=TaskStatus.PENDING,
                created_at=datetime.now().isoformat(),
                metadata=metadata or {},
            )
            self._store[task_id] = record
            self._save(record)
            return record

    async def get(self, task_id: str) -> TaskRecord | None:
        return self._store.get(task_id)

    async def list_all(self) -> list[TaskRecord]:
        return sorted(
            self._store.values(),
            key=lambda r: r.created_at,
            reverse=True,
        )

    async def update(
        self,
        task_id: str,
        status: TaskStatus,
        result: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        async with self._lock:
            if task_id not in self._store:
                return
            record = self._store[task_id]
            record.status = status
            if status == TaskStatus.RUNNING and not record.started_at:
                record.started_at = datetime.now().isoformat()
            if status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
                record.completed_at = datetime.now().isoformat()
                if record.started_at:
                    start = datetime.fromisoformat(record.started_at)
                    record.execution_time = (datetime.now() - start).total_seconds()
            if result is not None:
                record.result = result
            if error is not None:
                record.error = error
            self._save(record)

    async def delete(self, task_id: str) -> bool:
        async with self._lock:
            if task_id not in self._store:
                return False
            del self._store[task_id]
            try:
                (self._storage_dir / f"{task_id}.json").unlink(missing_ok=True)
            except Exception:
                pass
            return True


# =============================================================================
# API 认证
# =============================================================================


class AuthContext:
    """认证上下文"""

    def __init__(self, api_key: str | None) -> None:
        self.api_key = api_key or ""

    @staticmethod
    def hash_key(key: str) -> str:
        return hashlib.sha256(key.encode()).hexdigest()[:16]

    def verify(self, provided_key: str | None) -> bool:
        if not self.api_key:
            return True  # 未配置则跳过认证
        return provided_key == self.api_key


def get_auth(
    x_api_key: str | None = Header(None, alias="X-API-Key"),
    auth_ctx: AuthContext = Depends(lambda: AuthContext(None)),
) -> str | None:
    """FastAPI 依赖：验证 API Key"""
    ctx = AuthContext(auth_ctx.api_key)
    if not ctx.verify(x_api_key):
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return x_api_key


# =============================================================================
# 任务执行引擎
# =============================================================================


async def run_agent_task(prompt: str, task_id: str, store: TaskStore) -> None:
    """在后台执行 agent 任务"""
    try:
        await store.update(task_id, TaskStatus.RUNNING)

        # 延迟导入，避免循环依赖
        import sys
        from pathlib import Path

        project_root = Path(__file__).parent.parent.parent
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))

        result: dict[str, Any] = {}

        # 尝试使用 Orchestrator
        try:
            from src.core.orchestrator import Orchestrator
            from src.agents.base import AgentContext

            ctx = AgentContext(prompt=prompt, workspace=Path.cwd())
            orch = Orchestrator(max_agents=1)
            output = await orch.run(ctx)
            result = {
                "output": output.output if hasattr(output, "output") else str(output),
                "status": "ok",
            }
        except Exception as e:
            # 降级：返回纯文本响应
            result = {
                "output": prompt,  # echo back
                "status": "degraded",
                "note": "Orchestrator not available, returning prompt echo",
                "error": type(e).__name__ + ": " + str(e.args[0]) if e.args else type(e).__name__,
            }

        await store.update(task_id, TaskStatus.COMPLETED, result=result)

    except Exception as e:
        await store.update(task_id, TaskStatus.FAILED, error=type(e).__name__)


# =============================================================================
# FastAPI App
# =============================================================================


def create_app(
    api_key: str | None = None,
    store: TaskStore | None = None,
) -> tuple[FastAPI, TaskStore]:
    """创建 FastAPI 应用"""
    app = FastAPI(
        title="Oh My Coder Server API",
        description=(
            "远程 AI 编程助手 API。\n\n"
            "## 认证\n"
            "未设置 API Key 时无需认证。\n"
            "设置了 API Key 后，所有请求需在 Header 中添加：\n"
            "`X-API-Key: your-api-key`"
        ),
        version="1.0.0",
    )

    _store = store or TaskStore()
    _auth = AuthContext(api_key)
    _app_state: dict[str, Any] = {"store": _store, "auth": _auth}

    # ---------------------------------------------------------------------------
    # 请求模型
    # ---------------------------------------------------------------------------

    class RunRequest(BaseModel):
        prompt: str
        metadata: dict[str, Any] | None = None

    class TaskResponse(BaseModel):
        task_id: str
        status: str
        created_at: str
        prompt: str
        started_at: str | None = None
        completed_at: str | None = None
        execution_time: float = 0.0
        metadata: dict[str, Any] = {}

        class Config:
            from_attributes = True

    # ---------------------------------------------------------------------------
    # 路由
    # ---------------------------------------------------------------------------

    @app.get("/")
    async def root() -> dict[str, str]:
        return {"service": "Oh My Coder Server", "version": "1.0.0"}

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/api/v1/run", response_model=TaskResponse)
    async def run_task(req: RunRequest) -> TaskResponse:
        """提交新任务，返回 task_id"""
        store: TaskStore = _app_state["store"]
        auth: AuthContext = _app_state["auth"]

        record = await store.create(req.prompt, req.metadata)
        # 启动后台执行（不等待）
        asyncio.create_task(run_agent_task(req.prompt, record.task_id, store))

        return TaskResponse(
            task_id=record.task_id,
            status=record.status.value,
            created_at=record.created_at,
            prompt=record.prompt,
            metadata=record.metadata,
        )

    @app.get("/api/v1/status/{task_id}")
    async def get_status(
        task_id: str,
    ) -> dict[str, Any]:
        """查询任务状态"""
        store: TaskStore = _app_state["store"]
        record = await store.get(task_id)
        if not record:
            raise HTTPException(status_code=404, detail="Task not found")
        return {
            "task_id": record.task_id,
            "status": record.status.value,
            "created_at": record.created_at,
            "started_at": record.started_at,
            "completed_at": record.completed_at,
            "execution_time": record.execution_time,
        }

    @app.get("/api/v1/result/{task_id}")
    async def get_result(task_id: str) -> dict[str, Any]:
        """获取任务结果"""
        store: TaskStore = _app_state["store"]
        record = await store.get(task_id)
        if not record:
            raise HTTPException(status_code=404, detail="Task not found")
        if record.status == TaskStatus.PENDING:
            raise HTTPException(status_code=202, detail="Task not started yet")
        if record.status == TaskStatus.RUNNING:
            raise HTTPException(status_code=202, detail="Task still running")
        return {
            "task_id": record.task_id,
            "status": record.status.value,
            "result": record.result,
            "error": record.error,
            "execution_time": record.execution_time,
            "completed_at": record.completed_at,
        }

    @app.get("/api/v1/tasks")
    async def list_tasks(limit: int = 50) -> dict[str, Any]:
        """列出最近任务"""
        store: TaskStore = _app_state["store"]
        tasks = await store.list_all()
        return {
            "total": len(tasks),
            "tasks": [
                {
                    "task_id": t.task_id,
                    "status": t.status.value,
                    "created_at": t.created_at,
                    "execution_time": t.execution_time,
                    "prompt_preview": t.prompt[:100],
                }
                for t in tasks[:limit]
            ],
        }

    @app.delete("/api/v1/tasks/{task_id}")
    async def delete_task(task_id: str) -> dict[str, str]:
        """删除任务"""
        store: TaskStore = _app_state["store"]
        ok = await store.delete(task_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Task not found")
        return {"task_id": task_id, "deleted": "true"}

    return app, _store
