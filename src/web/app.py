"""
Web 界面入口 - FastAPI 应用
提供可视化界面执行 AI 编程任务
"""

import asyncio
import json as _json
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

# 确保可以导入 src 模块
project_root = Path(__file__).parent.parent.parent

sys.path.insert(0, str(project_root))

# 导入必须在 sys.path.insert 之后
try:
    from src.agents.base import AgentContext, AgentOutput, AgentStatus, get_agent
    from src.core.orchestrator import WORKFLOW_TEMPLATES, Orchestrator
    from src.core.router import ModelRouter, RouterConfig
    from src.web.dashboard_api import router as dashboard_router
    from src.web.history_api import agent_router, history_router, history_store
    from src.web.local_models_api import router as local_models_router
    from src.web.share_api import router as share_router
    from src.web.team_api import router as team_router
except ImportError as e:
    print(f"导入错误: {e}")
    raise

# ========================================
# FastAPI App
# ========================================
app = FastAPI(
    title="Oh My Coder Web",
    description="多智能体 AI 编程助手 Web 界面",
    version="0.1.0",
)

# 挂载静态文件和模板
web_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=web_dir / "static"), name="static")
templates = Jinja2Templates(directory=web_dir / "templates")

# 注册增强路由
app.include_router(history_router)
app.include_router(agent_router)
app.include_router(dashboard_router)
app.include_router(team_router)
app.include_router(local_models_router)
app.include_router(share_router)


# ========================================
# SSE Manager (Task → SSE subscribers)
# ========================================
class TaskManager:
    """管理所有运行中的任务"""

    def __init__(self):
        self._tasks: dict[str, dict[str, Any]] = {}
        self._queues: dict[str, asyncio.Queue] = {}

    def create_task(self) -> str:
        task_id = str(uuid.uuid4())[:8]
        queue = asyncio.Queue()
        self._tasks[task_id] = {
            "status": "pending",
            "started_at": None,
            "completed_at": None,
            "result": None,
            "error": None,
            "step_status": {},
            "step_outputs": {},
            "stats": {
                "total_tokens": 0,
                "total_cost": 0.0,
                "execution_time": 0.0,
                "steps_completed": [],
                "steps_failed": [],
                "steps_total": 5,
            },
        }
        self._queues[task_id] = queue
        return task_id

    def get_queue(self, task_id: str) -> asyncio.Queue | None:
        return self._queues.get(task_id)

    def update_step(
        self, task_id: str, step: str, status: str, content: str | None = None
    ):
        if task_id not in self._tasks:
            return
        task = self._tasks[task_id]
        task["step_status"][step] = status
        if content:
            task["step_outputs"][step] = content
        # Push SSE event (use put_nowait to avoid needing running event loop)
        queue = self._queues.get(task_id)
        if queue:
            data = {"type": f"step_{status}", "step": step, "content": content}
            try:
                queue.put_nowait(data)
            except Exception:
                pass  # Queue full, skip

    def complete_task(
        self, task_id: str, result: Any = None, error: str | None = None
    ):
        if task_id not in self._tasks:
            return
        task = self._tasks[task_id]
        task["status"] = "completed" if not error else "failed"
        task["completed_at"] = datetime.now().isoformat()
        task["result"] = result
        task["error"] = error
        # Push final event (use put_nowait to avoid needing running event loop)
        queue = self._queues.get(task_id)
        if queue:
            data = {
                "type": "complete" if not error else "error",
                "result": result,
                "content": error,
                "stats": task["stats"],
            }
            try:
                queue.put_nowait(data)
                queue.put_nowait(None)  # Sentinel to close SSE
            except Exception:
                pass  # Queue full, skip

    def get_task(self, task_id: str) -> dict | None:
        return self._tasks.get(task_id)

    def list_tasks(self) -> list[dict]:
        return [
            {
                "task_id": k,
                "status": v["status"],
                "started_at": v["started_at"],
                "completed_at": v["completed_at"],
            }
            for k, v in self._tasks.items()
        ]


task_manager = TaskManager()

# ========================================
# Orchestrator Singleton (shared across SSE + task execution)
# ========================================
_global_orchestrator = None


def get_orchestrator() -> "Orchestrator":
    """获取全局 Orchestrator 单例（复用已有 router）"""
    global _global_orchestrator
    if _global_orchestrator is None:
        router = create_router()
        _global_orchestrator = create_orchestrator(router)
    return _global_orchestrator


# ========================================
# Model & Orchestrator Factory
# ========================================
def create_router() -> ModelRouter:
    """创建模型路由器"""
    config = RouterConfig()
    return ModelRouter(config)


def create_orchestrator(router: ModelRouter) -> Orchestrator:
    """创建编排器"""
    orch = Orchestrator(model_router=router, state_dir=project_root / ".omc" / "state")

    # 注册所有已实现的 Agent
    for name in [
        "explore",
        "analyst",
        "architect",
        "executor",
        "verifier",
        "debugger",
        "code_reviewer",
        "test_engineer",
        "security",
        "tracer",
    ]:
        try:
            agent_cls = get_agent(name)
            if agent_cls:
                orch.register_agent(agent_cls(router))
        except Exception:
            pass

    return orch


# ========================================
# SSE Endpoint
# ========================================
@app.get("/sse/execute/{task_id}")
async def sse_execute(task_id: str):
    """SSE 流式推送执行进度"""
    queue = task_manager.get_queue(task_id)
    if not queue:
        raise HTTPException(status_code=404, detail="Task not found")

    async def event_generator():
        while True:
            data = await queue.get()
            if data is None:  # Sentinel
                break
            yield f"data: {json_dumps(data)}\n\n"
            await asyncio.sleep(0.01)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/agent/live")
async def agent_live_stream():
    """
    SSE 实时推送当前 Agent 协作状态

    Returns:
        StreamingResponse: text/event-stream，每 2 秒推送一次
        orchestrator.get_current_state()
    """
    orch = get_orchestrator()

    async def event_generator():
        while True:
            try:
                state = orch.get_current_state()
                yield f"data: {json_dumps(state)}\n\n"
                await asyncio.sleep(2)
            except Exception:
                error_state = {
                    "error": "服务端状态获取失败",
                    "timestamp": datetime.now().isoformat(),
                }
                yield f"data: {json_dumps(error_state)}\n\n"
                await asyncio.sleep(5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ========================================
# JSON Helper (avoid orjson dependency)
# ========================================


def json_dumps(obj):
    return _json.dumps(obj, ensure_ascii=False, default=str)


# ========================================
# API Routes
# ========================================
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """主页 - Web 界面"""
    return templates.TemplateResponse(request, "index.html")


@app.get("/history", response_class=HTMLResponse)
async def history_page(request: Request):
    """历史记录页面"""
    return templates.TemplateResponse(request, "history.html")


@app.get("/agents", response_class=HTMLResponse)
async def agents_page(request: Request):
    """Agent 状态页面"""
    return templates.TemplateResponse(request, "agents.html")


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    """项目仪表板页面"""
    return templates.TemplateResponse(request, "dashboard.html")


@app.get("/api/tasks")
async def list_tasks():
    """列出所有任务"""
    return JSONResponse({"tasks": task_manager.list_tasks()})


@app.get("/api/tasks/{task_id}")
async def get_task(task_id: str):
    """获取任务状态"""
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return JSONResponse(task)


@app.post("/api/execute")
async def execute_task(background: BackgroundTasks, payload: dict | None = None):
    """
    执行任务 API（异步，事件驱动）

    步骤：
    1. 创建任务，返回 task_id
    2. 通过 SSE /sse/execute/{task_id} 接收实时进度
    3. 完成后 SSE 推送 complete 事件
    """
    if not payload:
        raise HTTPException(status_code=400, detail="Missing JSON body")

    task = payload.get("task")
    project_path = payload.get("project_path", ".")
    model = payload.get("model", "deepseek")
    workflow_name = payload.get("workflow", "build")

    if not task:
        raise HTTPException(status_code=400, detail="Missing 'task' field")

    # 创建任务
    task_id = task_manager.create_task()
    task_manager._tasks[task_id]["started_at"] = datetime.now().isoformat()
    task_manager._tasks[task_id]["status"] = "running"

    # 后台执行
    background.add_task(run_task, task_id, task, project_path, model, workflow_name)

    return JSONResponse(
        {
            "status": "started",
            "task_id": task_id,
            "message": "任务已启动，请通过 SSE 连接获取进度",
        }
    )


async def run_task(
    task_id: str, task: str, project_path: str, model: str, workflow_name: str
):
    """后台执行任务"""
    import time

    start_time = time.time()
    orch = None

    try:
        # 复用全局 orchestrator（与 SSE /api/agent/live 共用同一实例）
        orch = get_orchestrator()

        # 确定工作流
        steps = WORKFLOW_TEMPLATES.get(workflow_name, WORKFLOW_TEMPLATES["build"])

        # 更新任务状态中的步骤总数
        task_manager._tasks[task_id]["stats"]["steps_total"] = len(steps)

        # 在 orchestrator 中注册当前任务（供 /api/agent/live SSE 消费）
        from src.core.orchestrator import WorkflowResult, WorkflowStatus

        workflow_id = task_id
        wf_result = WorkflowResult(
            workflow_id=workflow_id,
            status=WorkflowStatus.RUNNING,
            steps_completed=[],
            steps_failed=[],
            outputs={},
            total_tokens=0,
            total_cost=0.0,
            execution_time=0.0,
            agent_names=[s.agent_name for s in steps],
        )
        orch._active_workflows[workflow_id] = wf_result

        # 按顺序执行每个步骤
        # context = {
        #             "project_path": project_path,
        #             "task": task,
        # }
        previous_outputs = {}

        for step in steps:
            agent_name = step.agent_name

            # 通知开始
            task_manager.update_step(task_id, agent_name, "active")

            try:
                agent = orch.get_agent(agent_name)
                agent_context = AgentContext(
                    project_path=Path(project_path),
                    task_description=task,
                    previous_outputs=previous_outputs,
                )

                output: AgentOutput = await asyncio.wait_for(
                    agent.execute(agent_context),
                    timeout=step.timeout,
                )

                if output.status == AgentStatus.COMPLETED:
                    previous_outputs[agent_name] = output
                    wf_result.steps_completed.append(agent_name)
                    wf_result.outputs[agent_name] = output
                    wf_result.total_tokens += output.usage.get("total_tokens", 0)
                    task_manager.update_step(
                        task_id, agent_name, "completed", output.result
                    )
                    task_manager._tasks[task_id]["stats"]["steps_completed"].append(
                        agent_name
                    )
                    task_manager._tasks[task_id]["stats"]["total_tokens"] += (
                        output.usage.get("total_tokens", 0)
                    )
                else:
                    wf_result.steps_failed.append(agent_name)
                    task_manager.update_step(
                        task_id, agent_name, "failed", output.error or "Unknown error"
                    )
                    task_manager._tasks[task_id]["stats"]["steps_failed"].append(
                        agent_name
                    )

            except asyncio.TimeoutError:
                wf_result.steps_failed.append(agent_name)
                task_manager.update_step(task_id, agent_name, "failed", "执行超时")
                task_manager._tasks[task_id]["stats"]["steps_failed"].append(agent_name)
            except Exception:
                wf_result.steps_failed.append(agent_name)
                task_manager.update_step(
                    task_id, agent_name, "failed", "Agent 执行失败"
                )
                task_manager._tasks[task_id]["stats"]["steps_failed"].append(agent_name)

        # 标记工作流完成
        wf_result.execution_time = time.time() - start_time
        wf_result.status = (
            WorkflowStatus.COMPLETED
            if not wf_result.steps_failed
            else WorkflowStatus.FAILED
        )

        # 汇总结果
        total_time = time.time() - start_time
        task_manager._tasks[task_id]["stats"]["execution_time"] = round(total_time, 1)

        result = {
            "result": f"工作流 '{workflow_name}' 执行完成",
            "outputs": {
                name: {
                    "result": out.result,
                    "status": out.status.value,
                    "usage": out.usage,
                }
                for name, out in previous_outputs.items()
            },
            "stats": task_manager._tasks[task_id]["stats"],
        }

        task_manager.complete_task(task_id, result=result)

        # 保存历史记录
        history_record = {
            "task_id": task_id,
            "task": task,
            "workflow": workflow_name,
            "project_path": project_path,
            "model": model,
            "status": "completed",
            "started_at": task_manager._tasks[task_id].get("started_at"),
            "completed_at": datetime.now().isoformat(),
            "stats": task_manager._tasks[task_id]["stats"],
            "result": result,
        }
        history_store.save(task_id, history_record)

    except Exception as e:
        if orch is not None and workflow_id in orch._active_workflows:
            orch._active_workflows[workflow_id].status = WorkflowStatus.FAILED
        task_manager.complete_task(task_id, error="任务执行失败")

        # 保存失败记录（仅记录异常类型，不泄露详情）
        history_record = {
            "task_id": task_id,
            "task": task,
            "workflow": workflow_name,
            "project_path": project_path,
            "model": model,
            "status": "failed",
            "started_at": task_manager._tasks[task_id].get("started_at"),
            "completed_at": datetime.now().isoformat(),
            "error_type": type(e).__name__,
        }
        history_store.save(task_id, history_record)


# ===== 同步执行端点（适用于小任务）=====
class ExecuteRequest(BaseModel):
    task: str
    project_path: str = "."
    model: str = "deepseek"
    workflow: str = "build"


@app.post("/api/execute-sync")
async def execute_task_sync(req: ExecuteRequest):
    """同步执行任务（直接返回结果，适合小任务）"""
    import time

    start_time = time.time()

    try:
        router = create_router()
        orch = create_orchestrator(router)

        steps = WORKFLOW_TEMPLATES.get(req.workflow, WORKFLOW_TEMPLATES["build"])
        previous_outputs = {}
        total_tokens = 0

        for step in steps:
            agent_name = step.agent_name
            try:
                agent = orch.get_agent(agent_name)
                output = await asyncio.wait_for(
                    agent.execute(
                        AgentContext(
                            project_path=Path(req.project_path),
                            task_description=req.task,
                            previous_outputs=previous_outputs,
                        )
                    ),
                    timeout=step.timeout,
                )

                if output.status == AgentStatus.COMPLETED:
                    previous_outputs[agent_name] = output
                    total_tokens += output.usage.get("total_tokens", 0)
                else:
                    return JSONResponse(
                        {
                            "status": "error",
                            "message": f"{agent_name} 执行失败: {output.error}",
                        }
                    )

            except asyncio.TimeoutError:
                return JSONResponse(
                    {
                        "status": "error",
                        "message": f"{agent_name} 执行超时",
                    }
                )

        return JSONResponse(
            {
                "status": "success",
                "result": {
                    "task": req.task,
                    "workflow": req.workflow,
                    "steps_completed": list(previous_outputs.keys()),
                    "total_tokens": total_tokens,
                    "execution_time": round(time.time() - start_time, 1),
                    "outputs": {
                        name: out.result for name, out in previous_outputs.items()
                    },
                },
            }
        )

    except Exception:
        return JSONResponse(
            {
                "status": "error",
                "message": "服务器内部错误，请稍后重试",
            }
        )


# ===== 配置端点 =====
@app.get("/api/config")
async def get_config():
    """获取可用配置"""
    return JSONResponse(
        {
            "models": ["deepseek", "tongyi", "wenxin"],
            "workflows": list(WORKFLOW_TEMPLATES.keys()),
            "agents": [s.agent_name for s in WORKFLOW_TEMPLATES["build"]],
        }
    )


# ===== Settings 页面 & API =====
SETTINGS_DIR = Path.home() / ".omc"
SETTINGS_FILE = SETTINGS_DIR / "config.json"


def _read_settings() -> dict[str, Any]:
    """读取 ~/.omc/config.json，不存在则返回默认值"""
    if not SETTINGS_FILE.exists():
        return {
            "models": {
                "deepseek": {
                    "provider": "DeepSeek",
                    "api_key": "",
                    "cost_level": "free",
                    "enabled": True,
                },
                "tongyi": {
                    "provider": "阿里云",
                    "api_key": "",
                    "cost_level": "low",
                    "enabled": False,
                },
                "wenxin": {
                    "provider": "百度",
                    "api_key": "",
                    "cost_level": "low",
                    "enabled": False,
                },
            },
            "defaults": {
                "model": "deepseek",
                "workflow": "build",
                "timeout": 300,
            },
        }
    try:
        import json

        raw = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return (
            _read_settings.__wrapped__()
            if hasattr(_read_settings, "__wrapped__")
            else {
                "models": {
                    "deepseek": {
                        "provider": "DeepSeek",
                        "api_key": "",
                        "cost_level": "free",
                        "enabled": True,
                    },
                    "tongyi": {
                        "provider": "阿里云",
                        "api_key": "",
                        "cost_level": "low",
                        "enabled": False,
                    },
                    "wenxin": {
                        "provider": "百度",
                        "api_key": "",
                        "cost_level": "low",
                        "enabled": False,
                    },
                },
                "defaults": {
                    "model": "deepseek",
                    "workflow": "build",
                    "timeout": 300,
                },
            }
        )
    # 确保必要字段存在
    if "models" not in raw:
        raw["models"] = {}
    if "defaults" not in raw:
        raw["defaults"] = {}
    for key in ("deepseek", "tongyi", "wenxin"):
        if key not in raw["models"]:
            raw["models"][key] = {
                "provider": {
                    "deepseek": "DeepSeek",
                    "tongyi": "阿里云",
                    "wenxin": "百度",
                }.get(key, key),
                "api_key": "",
                "cost_level": {
                    "deepseek": "free",
                    "tongyi": "low",
                    "wenxin": "low",
                }.get(key, "low"),
                "enabled": key == "deepseek",
            }
    for dk, dv in {
        "model": "deepseek",
        "workflow": "build",
        "timeout": 300,
    }.items():
        raw["defaults"].setdefault(dk, dv)
    return raw


def _mask_key(key: str) -> str:
    """对 API Key 做脱敏处理，只显示后 4 位"""
    if not key or len(key) <= 4:
        return key or ""
    return "*" * (len(key) - 4) + key[-4:]


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    """设置页面"""
    return templates.TemplateResponse(request, "settings.html")


@app.get("/api/settings")
async def get_settings():
    """获取当前设置（API Key 脱敏）"""
    settings = _read_settings()
    # 脱敏 API Key
    # masked = json_dumps(settings, ensure_ascii=False)  # keep original for structure
    # Deep-copy models with masked keys
    for _m in settings.get("models", {}).values():
        raw_key = _m.get("api_key", "")
        _m["api_key_masked"] = _mask_key(raw_key)
        _m["has_key"] = bool(raw_key)
    return JSONResponse(settings)


@app.post("/api/settings")
async def save_settings(payload: dict):
    """保存设置到 ~/.omc/config.json"""
    import json

    # 读取现有设置做合并
    current = _read_settings()

    # 合并 models
    if "models" in payload:
        for name, model_conf in payload["models"].items():
            if name not in current["models"]:
                current["models"][name] = {}
            for k, v in model_conf.items():
                if k == "api_key":
                    # 跳过脱敏值（以 * 开头的不写入）
                    if isinstance(v, str) and v.startswith("*"):
                        continue
                current["models"][name][k] = v

    # 合并 defaults
    if "defaults" in payload:
        current["defaults"].update(payload["defaults"])

    SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(
        json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return JSONResponse({"status": "ok", "message": "设置已保存"})


# ===== 健康检查 =====
@app.get("/health")
async def health_check():
    """健康检查"""
    return JSONResponse({"status": "healthy", "version": "0.1.0"})


# ===== API 文档覆盖 =====
@app.get("/docs", response_class=HTMLResponse)
async def docs_page(request: Request):
    """使用文档页面"""
    return templates.TemplateResponse(request, "docs.html")


# ========================================
# Main Entry
# ========================================
def run():
    """启动服务"""
    print("=" * 50)
    print("  🤖 Oh My Coder Web Interface")
    print("  📍 http://localhost:8000")
    print("  📖 API Docs: http://localhost:8000/docs")
    print("=" * 50)
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    run()
