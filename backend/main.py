"""
oh-my-coder Web UI Backend
FastAPI 服务 - SSE 流式输出 + CLI 桥接

用法:
  cd backend && pip install -r requirements.txt
  uvicorn main:app --reload --port 8000

API:
  POST /api/chat  - SSE 流式对话
  GET  /api/models - 获取模型列表
"""

import json
import os
import subprocess
from pathlib import Path
from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

app = FastAPI(title="oh-my-coder Web UI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PROJECT_ROOT = Path(__file__).parent.parent
MODEL_META = PROJECT_ROOT / "src" / "models" / "model_metadata.json"


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    model: str = "glm-4-flash"
    apiKey: str = ""
    sessionHistory: List[ChatMessage] = []


@app.get("/api/models")
def get_models():
    if MODEL_META.exists():
        try:
            return json.loads(MODEL_META.read_text())
        except Exception:
            pass
    return {"error": "model_metadata.json not found"}


@app.post("/api/chat")
def chat(req: ChatRequest):
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="message is required")

    def generate():
        try:
            messages = [{"role": m.role, "content": m.content} for m in req.sessionHistory]
            messages.append({"role": "user", "content": req.message})

            env = os.environ.copy()
            if req.apiKey:
                ml = req.model.lower()
                if "glm" in ml: env["ZHIPU_API_KEY"] = req.apiKey
                elif "deepseek" in ml: env["DEEPSEEK_API_KEY"] = req.apiKey
                elif "gpt" in ml: env["OPENAI_API_KEY"] = req.apiKey
                elif "claude" in ml: env["ANTHROPIC_API_KEY"] = req.apiKey
                elif "gemini" in ml: env["GOOGLE_API_KEY"] = req.apiKey
                else: env["ZHIPU_API_KEY"] = req.apiKey

            cli_path = PROJECT_ROOT / "src" / "cli.py"
            if not cli_path.exists():
                yield "data: [ERROR] CLI not found\n\n"
                return

            proc = subprocess.Popen(
                ["python3", str(cli_path), "--model", req.model, "--stream"],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, env=env, text=True, bufsize=1,
            )

            while True:
                line = proc.stdout.readline()
                if not line:
                    break
                line = line.strip()
                if line.startswith("data: "):
                    chunk = line[6:]
                    if chunk == "[DONE]":
                        break
                    yield f"data: {chunk}\n\n"
                elif line.startswith("[ERROR]"):
                    yield f"data: {line[7:]}\n\n"
                    break

            proc.wait()
        except Exception as e:
            yield f"data: [ERROR] {str(e)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
