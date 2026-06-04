from __future__ import annotations

# mypy: disable-error-code="abstract, arg-type, assignment, attr-defined, call-arg, call-overload, dict-item, func-returns-value, import-untyped, index, misc, no-any-return, no-redef, operator, override, return, return-value, syntax, union-attr, var-annotated"


"""
Web 界面入口 - FastAPI 应用
提供可视化界面执行 AI 编程任务
"""

import asyncio
import json as _json
import re
import shutil
import subprocess
import sys
import tempfile
import uuid
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

import uvicorn
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request
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
    from src.config.workflow_loader import WorkflowLoader
    from src.core.orchestrator import (
        WORKFLOW_TEMPLATES,
        Orchestrator,
        WorkflowResult,
        WorkflowStatus,
    )
    from src.core.router import ModelRouter, RouterConfig
    from src.web.coverage_api import format_coverage_report, run_coverage_analysis
    from src.web.dashboard_api import router as dashboard_router
    from src.web.history_api import (
        agent_router,
        history_router,
        history_store,
        verify_api_token,
    )
    from src.web.local_models_api import router as local_models_router
    from src.web.share_api import router as share_router
    from src.web.team_api import router as team_router
except ImportError as e:
    print(f"导入错误: {e}")
    raise

# ========================================
# URL / 目标预处理
# ========================================


def _detect_target_type(target: str) -> str:
    """自动检测输入类型：github / url / local"""
    target = target.strip()
    if not target:
        return "local"
    # GitHub URL
    if re.match(r"https?://(www\.)?github\.com/[^/]+/[^/]+", target):
        return "github"
    # Git URL (git@...)
    if target.startswith("git@"):
        return "github"
    # 其他 HTTP URL
    if target.startswith("http://") or target.startswith("https://"):
        return "url"
    return "local"


def _preprocess_target(target: str, target_type: str, task_id: str) -> tuple:
    """
    预处理分析目标，返回 (project_path, extra_context).
    - github: clone 到临时目录，返回路径
    - url: fetch 网页内容，返回 ('.', extra_context)
    - local: 直接返回原路径
    """
    target = target.strip()
    if not target:
        return ".", ""

    if target_type == "github":
        # 规范化 GitHub URL → .git clone URL
        clone_url = target
        if not target.endswith(".git"):
            clone_url = target.rstrip("/") + ".git"
        if clone_url.startswith("https://github.com") and ".git" not in target:
            clone_url = target.rstrip("/") + ".git"

        tmp_dir = Path(tempfile.mkdtemp(prefix=f"omc-gh-{task_id[:8]}-"))
        try:
            result = subprocess.run(
                ["git", "clone", "--depth", "1", clone_url, str(tmp_dir)],
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode != 0:
                shutil.rmtree(tmp_dir, ignore_errors=True)
                raise RuntimeError(f"git clone 失败: {result.stderr.strip()[:200]}")
            return str(
                tmp_dir
            ), f"\n\n## 源代码来源\nGitHub 仓库: {target}\n已克隆到: {tmp_dir}"
        except Exception as e:
            print(f"[ERROR] Git clone failed: {e}")
            shutil.rmtree(tmp_dir, ignore_errors=True)
            raise

    elif target_type == "url":
        # Fetch 网页内容
        try:
            import requests

            resp = requests.get(
                target,
                timeout=30,
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
                },
            )
            # 自动检测编码
            content = resp.text
            # 简单 HTML → 文本：去标签
            text = re.sub(r"<script[^>]*>[\s\S]*?</script>", "", content, flags=re.I)
            text = re.sub(r"<style[^>]*>[\s\S]*?</style>", "", text, flags=re.I)
            text = re.sub(r"<[^>]+>", " ", text)
            text = re.sub(r"\s+", " ", text).strip()
            # 截断到 8000 字符避免 token 爆炸
            if len(text) > 8000:
                text = text[:8000] + "\n\n... (内容已截断)"
            return ".", f"\n\n## 网页内容\n来源: {target}\n\n{text}"
        except Exception as e:
            raise RuntimeError(f"获取网页失败: {e}")

    else:
        # 本地路径
        return target, ""


def _cleanup_target(project_path: str, target_type: str):
    """清理临时目录（GitHub clone）"""
    if target_type == "github" and project_path.startswith(tempfile.gettempdir()):
        shutil.rmtree(project_path, ignore_errors=True)


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


@app.get("/favicon.ico")
async def favicon():
    from fastapi.responses import FileResponse
    return FileResponse(web_dir / "static" / "favicon.svg", media_type="image/svg+xml")

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

    def create_task(
        self,
        task_desc: str = "",
        model: str = "",
        workflow: str = "",
        project_path: str = "",
    ) -> str:
        task_id = str(uuid.uuid4())[:8]
        queue = asyncio.Queue()
        self._tasks[task_id] = {
            "task_id": task_id,
            "task": task_desc,
            "model": model,
            "workflow": workflow,
            "project_path": project_path,
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

    def get_queue(self, task_id: str) -> Optional[asyncio.Queue]:
        return self._queues.get(task_id)

    def update_step(
        self, task_id: str, step: str, status: str, content: Optional[str] = None
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
            except Exception as e:
                print(f"[WARNING] Queue full, skipping step event: {e}")

    def complete_task(
        self, task_id: str, result: Any = None, error: Optional[str] = None
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
            except Exception as e:
                print(f"[WARNING] Queue full, skipping complete event: {e}")

    def delete_task(self, task_id: str) -> bool:
        if task_id not in self._tasks:
            return False
        # Close queue if exists
        queue = self._queues.pop(task_id, None)
        if queue:
            try:
                queue.put_nowait(None)  # Sentinel to close SSE
            except Exception as e:
                print(f"[WARNING] Queue full, skipping delete event: {e}")
        del self._tasks[task_id]
        return True

    def get_task(self, task_id: str) -> Optional[dict]:
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


def get_orchestrator() -> Orchestrator:
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
        "code-reviewer",
        "test_engineer",
        "security",
        "tracer",
    ]:
        try:
            agent_cls = get_agent(name)
            if agent_cls:
                orch.register_agent(agent_cls(router))
        except Exception as e:
            print(f"[WARNING] Failed to register agent {name}: {e}")

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
            except Exception as e:
                print(f"[WARNING] Failed to get orchestrator state: {e}")
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


@app.delete("/api/tasks/{task_id}")
async def delete_task(
    task_id: str,
    token: Optional[str] = Depends(verify_api_token),
):
    """删除任务（需要 API token 校验）"""
    if not task_manager.delete_task(task_id):
        raise HTTPException(status_code=404, detail="Task not found")
    return JSONResponse({"status": "deleted"})


@app.get("/api/history")
async def api_history():
    """获取任务历史（兼容 history.html）"""
    tasks = task_manager.list_tasks()
    tasks.sort(key=lambda t: t.get("started_at", ""), reverse=True)
    return JSONResponse({"records": tasks})


@app.get("/api/dashboard/stats")
async def dashboard_stats():
    """仪表板统计数据 — 返回真实的任务统计"""
    stats = history_store.get_stats()
    return JSONResponse(stats)


@app.get("/api/dashboard/files")
async def dashboard_files():
    """仪表板项目文件列表 — 从最近任务获取项目路径并列出文件"""
    # 从最近任务获取项目路径
    records = history_store.list_all(limit=10)
    project_path = "."

    for r in records:
        if r.get("project_path") and Path(r.get("project_path", ".")).exists():
            project_path = r.get("project_path", ".")
            break

    # 如果没有历史任务，使用当前工作目录
    if project_path == "." and project_root.exists():
        project_path = str(project_root)

    # 列出文件
    files = []
    try:
        p = Path(project_path)
        if p.exists() and p.is_dir():
            for f in sorted(p.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True)[
                :30
            ]:
                if f.is_file() and not f.name.startswith("."):
                    size = f.stat().st_size
                    size_str = f"{size // 1024}KB" if size >= 1024 else f"{size}B"
                    files.append({"name": f.name, "size": size_str, "path": str(f)})
    except Exception as e:
        print(f"[WARNING] Failed to list project files: {e}")

    return JSONResponse({"files": files, "project_path": project_path})


@app.post("/api/open-folder")
async def open_folder(payload: Optional[dict] = None):
    """打开指定路径的文件夹（在文件管理器中显示）"""
    if not payload or not payload.get("path"):
        raise HTTPException(status_code=400, detail="path required")

    path = payload["path"]
    import platform
    import subprocess

    try:
        system = platform.system()
        if system == "Darwin":  # macOS
            subprocess.run(["open", path], check=True)
        elif system == "Windows":
            subprocess.run(["explorer", path], check=True)
        else:  # Linux
            subprocess.run(["xdg-open", path], check=True)
        return JSONResponse({"status": "ok", "message": f"已打开: {path}"})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@app.post("/api/save-report")
async def save_report(payload: Optional[dict] = None):
    """保存任务报告到文件"""
    if not payload or not payload.get("task_id"):
        raise HTTPException(status_code=400, detail="task_id required")

    task_id = payload["task_id"]
    # 先从内存查找（当前会话任务）
    task = task_manager.get_task(task_id)
    # 如果内存没有，从历史记录查找（持久化任务）
    if not task:
        task = history_store.load(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # 默认保存到桌面
    desktop = Path.home() / "Desktop" / "omc-reports"
    desktop.mkdir(parents=True, exist_ok=True)

    # 生成文件名
    ts = task.get("started_at", "").replace(":", "-").replace(" ", "_")[:19]
    task_desc = task.get("task", "task")[:30].replace("/", "_").replace("\\", "_")
    filename = f"{ts}_{task_desc}_{task_id[:8]}.md"
    filepath = desktop / filename

    # 生成报告内容
    lines = [
        f"# 任务报告: {task.get('task', '未知任务')}\n",
        f"- **任务 ID**: {task_id}",
        f"- **状态**: {task.get('status', 'unknown')}",
        f"- **开始时间**: {task.get('started_at', '-')}",
        f"- **模型**: {task.get('model', '-')}",
        f"- **工作流**: {task.get('workflow', '-')}",
        f"- **项目路径**: {task.get('project_path', '-')}\n",
        "## 统计\n",
        f"- Tokens: {task.get('stats', {}).get('total_tokens', 0)}",
        f"- 执行时间: {task.get('stats', {}).get('execution_time', 0)}s",
        f"- 成本: ¥{task.get('stats', {}).get('total_cost', 0):.4f}",
        f"- 完成步骤: {task.get('stats', {}).get('steps_completed', [])}",
        f"- 失败步骤: {task.get('stats', {}).get('steps_failed', [])}\n",
    ]

    # 各步骤输出
    # 先从 result.outputs 找（持久化历史任务）
    step_outputs = (task.get("result") or {}).get("outputs", {})
    # 兼容：如果 result.outputs 没有，尝试 step_outputs（内存任务）
    if not step_outputs:
        step_outputs = task.get("step_outputs", {})
    if step_outputs:
        lines.append("## 各步骤输出\n")
        for step_name, output in step_outputs.items():
            lines.append(f"### {step_name}\n")
            # 根据类型正确处理换行符
            if isinstance(output, str):
                lines.append(output)
            elif isinstance(output, dict):
                # 如果字典中有 result 字段，直接使用 result 字符串
                result = (
                    output.get("result")
                    or output.get("output")
                    or output.get("content")
                )
                if isinstance(result, str):
                    lines.append(result)
                else:
                    lines.append(_json.dumps(output, ensure_ascii=False, indent=2))
            else:
                lines.append(
                    _json.dumps(output, ensure_ascii=False, indent=2)
                    if output
                    else "无输出"
                )
            lines.append("")

    # 最终结果
    final = task.get("result", {})
    if final:
        lines.append("## 最终结果\n")
        if isinstance(final, dict):
            lines.append(f"- 摘要: {final.get('summary', '-')}")
            lines.append(f"- 耗时: {final.get('execution_time', 0)}s")
            lines.append(f"- Tokens: {final.get('total_tokens', 0)}\n")
            for key, val in final.items():
                if key not in ("summary", "execution_time", "total_tokens", "outputs"):
                    lines.append(f"### {key}\n")
                    # 正确处理不同类型
                    if isinstance(val, str):
                        lines.append(val)
                    elif isinstance(val, dict):
                        lines.append(_json.dumps(val, ensure_ascii=False, indent=2))
                    else:
                        lines.append(str(val))
                    lines.append("")
        else:
            lines.append(str(final))

    filepath.write_text("\n".join(lines), encoding="utf-8")
    return JSONResponse({"path": str(filepath), "status": "saved"})


# ========================================
# Chat API - 对话式任务创建
# ========================================


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []


class ChatResponse(BaseModel):
    reply: str
    ready_to_execute: bool = False
    summary: str = ""
    task: dict | None = None


# 工作流关键词映射
WORKFLOW_KEYWORDS = {
    "review": ["审查", "review", "检查", "代码质量", "安全漏洞", "security", "quality"],
    "debug": ["调试", "debug", "修复", "fix", "bug", "错误", "error", "问题"],
    "test": ["测试", "test", "单元测试", "unittest", "coverage", "覆盖率"],
    "build": ["开发", "实现", "build", "create", "写", "添加", "开发"],
}

# 模型关键词映射
MODEL_KEYWORDS = {
    "deepseek": ["deepseek", "v4", "便宜", "低成本"],
    "glm-4-flash": ["glm", "flash", "免费", "智谱"],
    "MiniMax-Text-01": ["mimo", "小米", "minimax"],
    "moonshot-v1-128k": ["kimi", "月之暗面", "128k"],
    "doubao-pro-32k": ["doubao", "豆包", "字节"],
    "tiangong-3": ["tiangong", "天工"],
    "Baichuan4": ["baichuan", "百川"],
}


def _detect_workflow(message: str) -> str:
    """根据消息内容检测工作流类型"""
    message_lower = message.lower()
    scores = {}
    for workflow, keywords in WORKFLOW_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw.lower() in message_lower)
        if score > 0:
            scores[workflow] = score
    return max(scores, key=scores.get) if scores else "build"


def _detect_model(message: str) -> str:
    """根据消息内容检测模型偏好"""
    message_lower = message.lower()
    scores = {}
    for model, keywords in MODEL_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw.lower() in message_lower)
        if score > 0:
            scores[model] = score
    return max(scores, key=scores.get) if scores else "deepseek"


def _detect_target_type_from_message(message: str) -> tuple[str, str]:
    """检测目标类型和路径"""
    # GitHub URL
    github_match = re.search(r"github\.com/[^/\s]+/[^/\s]+", message)
    if github_match:
        return "github", f"https://{github_match.group(0)}"

    # HTTP URL
    url_match = re.search(r'https?://[^\s<>"\']+', message)
    if url_match:
        parsed = urlparse(url_match.group(0))
        if parsed.netloc == "github.com":
            return "github", parsed.geturl()
        return "url", parsed.geturl()

    # 本地路径（简单检测）
    path_match = re.search(r'[~./][^\s<>"\']*', message)
    if path_match:
        path = path_match.group(0)
        if path.startswith((".", "~/", "/")):
            return "local", path

    return "local", "."


def _generate_task_summary(task: dict) -> str:
    """生成任务摘要"""
    workflow_names = {
        "build": "完整开发",
        "review": "代码审查",
        "debug": "调试修复",
        "test": "测试用例",
    }
    model_names = {
        "deepseek": "DeepSeek V4",
        "glm-4-flash": "GLM-4.7-Flash",
        "MiniMax-Text-01": "MiMo Flash",
        "moonshot-v1-128k": "Kimi 128K",
        "doubao-pro-32k": "Doubao-Pro",
        "tiangong-3": "天工 3.0",
        "Baichuan4": "百川 4",
    }

    wf_name = workflow_names.get(task["workflow"], task["workflow"])
    model_name = model_names.get(task["model"], task["model"])

    target_desc = task["project_path"]
    if task["target_type"] == "github":
        target_desc = f"GitHub 仓库 {task['project_path']}"
    elif task["target_type"] == "url":
        target_desc = f"网页 {task['project_path']}"

    return f"{wf_name} · {model_name} · {target_desc}"


@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    """
    对话式任务创建 API

    理解用户意图，收集必要信息，最终生成可执行的任务配置
    """
    message = request.message.strip()
    history = request.history

    # 检测意图
    workflow = _detect_workflow(message)
    model = _detect_model(message)
    target_type, target_path = _detect_target_type_from_message(message)

    # 检查是否需要更多信息
    # 简单启发式：如果消息很短（<10字），可能需要更多信息
    if len(message) < 10 and len(history) < 2:
        return ChatResponse(
            reply="请详细描述你的需求，比如：\n• 你想实现什么功能？\n• 需要审查/修复什么代码？\n• 目标代码在哪里（本地路径/GitHub链接）？",
            ready_to_execute=False,
        )

    # 构建任务配置
    task_config = {
        "description": message,
        "workflow": workflow,
        "model": model,
        "target_type": target_type,
        "project_path": target_path,
    }

    summary = _generate_task_summary(task_config)

    # 生成确认回复
    workflow_desc = {
        "build": "开发新功能",
        "review": "审查代码质量",
        "debug": "调试修复问题",
        "test": "生成测试用例",
    }

    reply = "好的，我理解了！让我确认一下：\n\n"
    reply += f"**任务类型：** {workflow_desc.get(workflow, workflow)}\n"
    reply += f"**使用模型：** {model}\n"
    reply += f"**目标：** {target_path if target_type == 'local' else target_path}\n\n"
    reply += "确认无误后，我将启动 AI 团队开始执行。"

    return ChatResponse(
        reply=reply, ready_to_execute=True, summary=summary, task=task_config
    )


class ChatCompletionRequest(BaseModel):
    """AI 聊天补全请求"""

    messages: list[dict]  # [{role: "user"|"assistant", content: "..."}]
    model: str = "deepseek"  # 模型 ID
    stream: bool = False  # 是否流式返回


class ChatCompletionResponse(BaseModel):
    """AI 聊天补全响应"""

    content: str
    model: str
    usage: dict = {}


@app.post("/api/chat/completions")
async def chat_completion_endpoint(request: ChatCompletionRequest):
    """
    真正的 AI 聊天接口 — 调用模型路由器生成回复

    支持流式 (SSE) 和非流式两种模式。
    """
    orch = get_orchestrator()
    router = orch.model_router

    # 构建消息列表
    from src.models.base import Message as BaseMessage

    base_messages = [
        BaseMessage(role=m["role"], content=m["content"]) for m in request.messages
    ]

    if request.stream:
        # 流式响应：使用 SSE
        async def event_stream():
            try:
                response = await router.route_and_call(
                    task_type="chat",
                    messages=base_messages,
                    complexity="medium",
                    use_cache=False,
                    override_model=request.model,
                )
                content = response.content or ""
                # 分块发送（模拟流式）
                chunk_size = max(1, len(content) // 20)
                for i in range(0, len(content), chunk_size):
                    chunk = content[i : i + chunk_size]
                    data = _json.dumps({"content": chunk, "done": False})
                    yield f"data: {data}\n\n"
                    await asyncio.sleep(0.02)
                # 发送完成信号
                done_data = _json.dumps(
                    {
                        "content": "",
                        "done": True,
                        "usage": {
                            "prompt_tokens": response.usage.prompt_tokens,
                            "completion_tokens": response.usage.completion_tokens,
                            "total_tokens": response.usage.total_tokens,
                        },
                        "model": response.model,
                    }
                )
                yield f"data: {done_data}\n\n"
            except Exception as e:
                err_data = _json.dumps(
                    {
                        "content": f"\n\n❌ 模型调用失败: {type(e).__name__}",
                        "done": True,
                        "error": True,
                    }
                )
                yield f"data: {err_data}\n\n"

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )
    else:
        # 非流式响应
        try:
            response = await router.route_and_call(
                task_type="chat",
                messages=base_messages,
                complexity="medium",
                use_cache=False,
                override_model=request.model,
            )
            return ChatCompletionResponse(
                content=response.content or "",
                model=response.model,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                },
            )
        except Exception as e:
            return ChatCompletionResponse(
                content=f"❌ 模型调用失败: {type(e).__name__}",
                model=request.model,
            )


@app.post("/api/execute")
async def execute_task(background: BackgroundTasks, payload: Optional[dict] = None):
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
    target_type = payload.get("target_type", "")  # github / url / local / auto

    if not task:
        raise HTTPException(status_code=400, detail="Missing 'task' field")

    # 自动检测目标类型
    if not target_type or target_type == "auto":
        target_type = _detect_target_type(project_path)

    # 创建任务
    task_id = task_manager.create_task(
        task_desc=task, model=model, workflow=workflow_name, project_path=project_path
    )
    task_manager._tasks[task_id]["started_at"] = datetime.now().isoformat()
    task_manager._tasks[task_id]["status"] = "running"
    task_manager._tasks[task_id]["target_type"] = target_type

    # 后台执行
    background.add_task(
        run_task, task_id, task, project_path, model, workflow_name, target_type
    )

    return JSONResponse(
        {
            "status": "started",
            "task_id": task_id,
            "target_type": target_type,
            "message": "任务已启动，请通过 SSE 连接获取进度",
        }
    )


async def run_task(
    task_id: str,
    task: str,
    project_path: str,
    model: str,
    workflow_name: str,
    target_type: str = "local",
):
    """后台执行任务"""
    import time

    start_time = time.time()
    orch = None
    extra_context = ""

    # 预处理目标（clone GitHub / fetch URL）
    try:
        project_path, extra_context = _preprocess_target(
            project_path, target_type, task_id
        )
    except Exception as e:
        err_type = type(e).__name__
        task_manager.complete_task(task_id, error=f"目标预处理失败 ({err_type})")
        history_store.save(
            task_id,
            {
                "task_id": task_id,
                "task": task,
                "status": "failed",
                "error_type": err_type,
                "started_at": datetime.now().isoformat(),
            },
        )
        return

    workflow_id = None
    try:
        # 复用全局 orchestrator（与 SSE /api/agent/live 共用同一实例）
        orch = get_orchestrator()

        # 确定工作流
        steps = WORKFLOW_TEMPLATES.get(workflow_name, WORKFLOW_TEMPLATES["build"])

        # 更新任务状态中的步骤总数
        task_manager._tasks[task_id]["stats"]["steps_total"] = len(steps)

        # 在 orchestrator 中注册当前任务（供 /api/agent/live SSE 消费）
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
                    task_description=task + extra_context,
                    previous_outputs=previous_outputs,
                    override_model=model if model != "deepseek" else None,
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

            except TimeoutError:
                wf_result.steps_failed.append(agent_name)
                task_manager.update_step(task_id, agent_name, "failed", "执行超时")
                task_manager._tasks[task_id]["stats"]["steps_failed"].append(agent_name)
            except Exception as e:
                wf_result.steps_failed.append(agent_name)
                # 提取用户友好的错误信息
                err_str = str(e)
                if "429" in err_str or "Too Many Requests" in err_str:
                    error_msg = "API 限流 (429)，请稍后重试或切换模型"
                elif "401" in err_str or "Unauthorized" in err_str:
                    error_msg = "API Key 无效或已过期，请检查设置"
                elif "403" in err_str or "Forbidden" in err_str:
                    error_msg = "API 访问被拒绝，请检查 API Key 权限"
                elif "timeout" in err_str.lower() or "超时" in err_str:
                    error_msg = "API 请求超时，请稍后重试"
                elif "NoModelAvailable" in type(e).__name__:
                    error_msg = f"所有模型均不可用: {err_str[:150]}"
                else:
                    error_msg = f"{type(e).__name__}: {err_str[:200]}"
                task_manager.update_step(task_id, agent_name, "failed", error_msg)
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
        if orch is not None and workflow_id is not None and workflow_id in orch._active_workflows:
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

    finally:
        # 清理临时目录（GitHub clone）
        _cleanup_target(project_path, target_type)


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

            except TimeoutError:
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

    except Exception as e:
        print(f"[ERROR] API endpoint error: {e}")
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
    except Exception as e:
        print(f"[WARNING] Failed to parse settings JSON: {e}")
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
        # 保留原始 key 供前端回填（localhost 安全）
        # 不删除 api_key 字段，前端需要回填到 input
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


# ===== 连接测试 =====
@app.post("/api/test-connection")
async def test_connection(payload: dict):
    """测试 API Key 是否可用。

    支持两类模式：
    - provider 模式: { provider, api_key, base_url } → 用已知模型测试指定 provider
    - custom 模式: { url, api_key, model_id } → 用指定 URL 测试自定义模型

    返回: { ok: bool, msg: str, latency_ms?: number }
    """
    import time

    import httpx

    provider = payload.get("provider")
    api_key = payload.get("api_key")
    base_url = payload.get("base_url")
    model_id = payload.get("model_id")  # 仅 custom 模式

    # ── Provider 模式 ──────────────────────────────────
    if provider:
        # 构造最小请求体（不实际发 token 消耗）
        try:
            if provider == "glm":
                url = (
                    base_url or "https://open.bigmodel.cn/api/paas/v4"
                ) + "/chat/completions"
                body = {
                    "model": "glm-4-flash",
                    "messages": [{"role": "user", "content": "Hi"}],
                    "max_tokens": 5,
                }
            elif provider == "deepseek":
                url = (base_url or "https://api.deepseek.com/v1") + "/chat/completions"
                body = {
                    "model": "deepseek-chat",
                    "messages": [{"role": "user", "content": "Hi"}],
                    "max_tokens": 5,
                }
            elif provider == "kimi":
                url = (base_url or "https://api.moonshot.cn/v1") + "/chat/completions"
                body = {
                    "model": "moonshot-v1-8k",
                    "messages": [{"role": "user", "content": "Hi"}],
                    "max_tokens": 5,
                }
            elif provider == "doubao":
                url = (
                    base_url or "https://ark.cn-beijing.volces.com/api/v3"
                ) + "/chat/completions"
                body = {
                    "model": "doubao-pro-32k",
                    "messages": [{"role": "user", "content": "Hi"}],
                    "max_tokens": 5,
                }
            elif provider == "mimo":
                url = (
                    base_url or "https://api.xiaomimimo.com/v1"
                ) + "/chat/completions"
                body = {
                    "model": "MiMo-V2-Flash",
                    "messages": [{"role": "user", "content": "Hi"}],
                    "max_tokens": 5,
                }
            elif provider == "tiangong":
                url = (
                    base_url or "https://model-platform.tiangong.cn/v1"
                ) + "/chat/completions"
                body = {
                    "model": "tiangong",
                    "messages": [{"role": "user", "content": "Hi"}],
                    "max_tokens": 5,
                }
            elif provider == "baichuan":
                url = (
                    base_url or "https://api.baichuan-ai.com/v1"
                ) + "/chat/completions"
                body = {
                    "model": "Baichuan4",
                    "messages": [{"role": "user", "content": "Hi"}],
                    "max_tokens": 5,
                }
            else:
                return JSONResponse(
                    {"ok": False, "msg": f"未知供应商: {provider}"}, status_code=400
                )

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            start = time.time()
            with httpx.Client(timeout=15.0) as client:
                resp = client.post(url, json=body, headers=headers)
            latency_ms = round((time.time() - start) * 1000)

            if resp.status_code == 200:
                # Check if response is actually JSON (not an HTML page)
                ct = resp.headers.get("content-type", "")
                if "html" in ct.lower():
                    return JSONResponse(
                        {
                            "ok": False,
                            "msg": "返回了网页而非 API 响应——请检查 Base URL 是否为 API 接口地址（非网页地址）",
                        }
                    )
                return JSONResponse(
                    {
                        "ok": True,
                        "msg": f"连接成功 ({latency_ms}ms)",
                        "latency_ms": latency_ms,
                    }
                )
            elif resp.status_code == 401:
                return JSONResponse(
                    {"ok": False, "msg": "API Key 无效（401 Unauthorized）"}
                )
            elif resp.status_code == 403:
                return JSONResponse(
                    {"ok": False, "msg": "API Key 被拒绝（403 Forbidden）"}
                )
            else:
                try:
                    err = resp.json().get("error", {}).get("message", resp.text[:100])
                except Exception as e:
                    print(f"[WARNING] Failed to parse error JSON: {e}")
                    err = resp.text[:100]
                return JSONResponse(
                    {"ok": False, "msg": f"API 错误 {resp.status_code}: {err}"},
                    status_code=502,
                )

        except httpx.TimeoutException:
            return JSONResponse(
                {"ok": False, "msg": "连接超时（15s），请检查 Base URL 或网络"}
            )
        except httpx.ConnectError as e:
            return JSONResponse({"ok": False, "msg": f"连接失败：{e}"}, status_code=502)
        except Exception as e:
            return JSONResponse({"ok": False, "msg": f"测试失败: {e}"}, status_code=500)

    # ── Custom 模式 ──────────────────────────────────
    if base_url and model_id:
        if not api_key:
            return JSONResponse(
                {"ok": False, "msg": "API Key 为空（自定义模型通常需要 Key）"},
                status_code=400,
            )
        try:
            url = base_url.rstrip("/") + "/chat/completions"
            body = {
                "model": model_id,
                "messages": [{"role": "user", "content": "Hi"}],
                "max_tokens": 5,
            }
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            start = time.time()
            with httpx.Client(timeout=15.0) as client:
                resp = client.post(url, json=body, headers=headers)
            latency_ms = round((time.time() - start) * 1000)
            if resp.status_code == 200:
                return JSONResponse(
                    {
                        "ok": True,
                        "msg": f"连接成功 ({latency_ms}ms)",
                        "latency_ms": latency_ms,
                    }
                )
            else:
                try:
                    err = resp.json().get("error", {}).get("message", resp.text[:100])
                except Exception as e:
                    print(f"[WARNING] Failed to parse error JSON: {e}")
                    err = resp.text[:100]
                return JSONResponse(
                    {"ok": False, "msg": f"API 错误 {resp.status_code}: {err}"},
                    status_code=502,
                )
        except httpx.TimeoutException:
            return JSONResponse({"ok": False, "msg": "连接超时（15s）"})
        except httpx.ConnectError as e:
            return JSONResponse({"ok": False, "msg": f"连接失败：{e}"}, status_code=502)
        except Exception as e:
            return JSONResponse({"ok": False, "msg": f"测试失败: {e}"}, status_code=500)

    return JSONResponse(
        {"ok": False, "msg": "参数不完整（需 provider 或 base_url+model_id）"},
        status_code=400,
    )


# ===== 工作流管理 API（P1-6 Agent 子系统重构 Phase 1）=====


@app.get("/api/workflows")
async def list_workflows():
    """列出所有可用工作流（内置 + 用户自定义）"""
    loader = WorkflowLoader()
    names = loader.list_workflows()
    builtin = set(loader.list_builtins())
    return JSONResponse(
        {
            "workflows": names,
            "builtin_count": len(builtin),
            "user_count": len(names) - len(builtin),
        }
    )


@app.get("/api/workflows/{name}")
async def get_workflow(name: str):
    """获取指定工作流完整配置"""
    loader = WorkflowLoader()
    config = loader.get_workflow_config(name)
    if config is None:
        # Fallback: 尝试从 WORKFLOW_TEMPLATES
        steps = WORKFLOW_TEMPLATES.get(name, [])
        if steps:
            return JSONResponse(
                {
                    "name": name,
                    "description": "",
                    "source": "builtin",
                    "steps": [
                        s.model_dump() if hasattr(s, "model_dump") else s for s in steps
                    ],
                }
            )
        return JSONResponse({"error": f"工作流 '{name}' 不存在"}, status_code=404)
    d = config.model_dump() if hasattr(config, "model_dump") else asdict(config)
    return JSONResponse({"name": name, **d})


@app.put("/api/workflows/{name}")
async def save_workflow(name: str, payload: dict):
    """保存或更新自定义工作流（PUT 用于创建或覆盖）"""
    try:
        loader = WorkflowLoader()
        # 清除旧缓存
        loader._cache.pop(name, None)
        # 解析 YAML 字符串
        yaml_str = payload.get("yaml", "")
        config = loader.parse_yaml_string(yaml_str, name)
        if config is None:
            return JSONResponse({"error": "YAML 解析失败，请检查格式"}, status_code=400)
        # 确保名称一致
        config.name = name
        config.source = "user"
        loader.save_workflow(name, config)
        return JSONResponse({"status": "ok", "message": f"工作流 '{name}' 已保存"})
    except Exception as e:
        return JSONResponse(
            {"error": f"工作流 '{name}' 保存失败: {e}"}, status_code=400
        )


@app.delete("/api/workflows/{name}")
async def delete_workflow(name: str):
    """删除自定义工作流（内置不可删除）"""
    loader = WorkflowLoader()
    if loader.is_builtin(name):
        return JSONResponse({"error": "内置工作流不可删除"}, status_code=403)
    try:
        loader.delete_workflow(name)
        return JSONResponse({"status": "ok", "message": f"工作流 '{name}' 已删除"})
    except FileNotFoundError:
        return JSONResponse({"error": f"工作流 '{name}' 不存在"}, status_code=404)
    except Exception as e:
        print(f"[ERROR] Failed to delete workflow '{name}': {e}")
        return JSONResponse({"error": f"工作流 '{name}' 删除失败"}, status_code=400)


# ========================================
# Session API - 会话管理
# ========================================

SESSIONS_DIR = Path.home() / ".omc" / "sessions"
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)


class SessionCreate(BaseModel):
    title: str = "新会话"


class SessionUpdate(BaseModel):
    title: Optional[str] = None
    messages: Optional[list] = None


@app.get("/api/sessions")
async def list_sessions():
    """获取所有会话列表"""
    sessions = []
    for f in sorted(
        SESSIONS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True
    ):
        try:
            data = _json.loads(f.read_text(encoding="utf-8"))
            sessions.append(
                {
                    "id": data.get("id", f.stem),
                    "title": data.get("title", "新会话"),
                    "created_at": data.get("created_at", ""),
                    "updated_at": data.get("updated_at", ""),
                    "message_count": len(data.get("messages", [])),
                }
            )
        except Exception as e:
            print(f"[WARNING] Failed to load session {f.name}: {e}")
    return JSONResponse({"sessions": sessions})


@app.post("/api/sessions")
async def create_session(req: SessionCreate):
    """创建新会话"""
    session_id = str(uuid.uuid4())[:12]
    now = datetime.now().isoformat()
    session_data = {
        "id": session_id,
        "title": req.title,
        "messages": [],
        "created_at": now,
        "updated_at": now,
    }
    filepath = SESSIONS_DIR / f"{session_id}.json"
    filepath.write_text(
        _json.dumps(session_data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return JSONResponse(
        {
            "status": "ok",
            "session": {
                "id": session_id,
                "title": req.title,
                "created_at": now,
                "updated_at": now,
                "message_count": 0,
            },
        }
    )


@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str):
    """获取单个会话详情"""
    filepath = SESSIONS_DIR / f"{session_id}.json"
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Session not found")
    try:
        data = _json.loads(filepath.read_text(encoding="utf-8"))
        return JSONResponse(data)
    except Exception as e:
        print(f"[WARNING] Failed to read session {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to read session")


@app.put("/api/sessions/{session_id}")
async def update_session(session_id: str, req: SessionUpdate):
    """更新会话（标题或消息）"""
    filepath = SESSIONS_DIR / f"{session_id}.json"
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Session not found")
    try:
        data = _json.loads(filepath.read_text(encoding="utf-8"))
        if req.title is not None:
            data["title"] = req.title
        if req.messages is not None:
            data["messages"] = req.messages
        data["updated_at"] = datetime.now().isoformat()
        filepath.write_text(
            _json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return JSONResponse({"status": "ok", "updated_at": data["updated_at"]})
    except Exception as e:
        print(f"[WARNING] Failed to update session {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update session")


@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    """删除会话"""
    filepath = SESSIONS_DIR / f"{session_id}.json"
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Session not found")
    try:
        filepath.unlink()
        return JSONResponse({"status": "ok"})
    except Exception as e:
        print(f"[WARNING] Failed to delete session {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete session")


# ===== 覆盖率 API =====
@app.get("/api/coverage")
async def get_coverage():
    """获取测试覆盖率数据"""
    try:
        summary = run_coverage_analysis(project_root)
        report = format_coverage_report(summary)
        return JSONResponse(report)
    except Exception as e:
        return JSONResponse(
            {
                "error": f"覆盖率分析失败: {type(e).__name__}",
                "overall": {"coverage": 0, "color": "#ef4444"},
            },
            status_code=500,
        )


@app.post("/api/coverage/run")
async def run_coverage():
    """重新运行覆盖率分析"""
    try:
        summary = run_coverage_analysis(project_root)
        report = format_coverage_report(summary)
        return JSONResponse(report)
    except Exception as e:
        return JSONResponse(
            {
                "error": f"覆盖率分析失败: {type(e).__name__}",
                "overall": {"coverage": 0, "color": "#ef4444"},
            },
            status_code=500,
        )


# ===== 健康检查 =====
@app.get("/health")
async def health_check():
    """健康检查"""
    return JSONResponse({"status": "healthy", "version": "0.1.0"})


# ===== 覆盖率页面 =====
@app.get("/coverage", response_class=HTMLResponse)
async def coverage_page(request: Request):
    """测试覆盖率页面"""
    return templates.TemplateResponse(request, "coverage.html")


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
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)  # nosec B104


if __name__ == "__main__":
    run()
