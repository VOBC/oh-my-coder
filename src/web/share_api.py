from __future__ import annotations

"""
Share API - 会话分享 Web 端点

端点：
- POST /api/share        生成分享
- GET  /api/share/{id}   获取分享详情
- GET  /api/share        列出分享
- POST /api/share/{id}/import  导入分享
- DELETE /api/share/{id} 删除分享
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/share", tags=["share"])

# ========================================
# Share Storage (复用 commands/share.py 逻辑)
# ========================================

SHARE_DIR = Path.home() / ".omc" / "shares"
HISTORY_DIR = Path(".omc/history")


def _ensure_dir() -> None:
    SHARE_DIR.mkdir(parents=True, exist_ok=True)


def _share_path(share_id: str) -> Path:
    return SHARE_DIR / f"share_{share_id}.json"


def _sanitize_config(config: dict[str, Any]) -> dict[str, Any]:
    """脱敏配置"""
    safe = {}
    for key, value in config.items():
        if isinstance(value, dict):
            safe[key] = _sanitize_config(value)
        elif isinstance(value, str) and (
            "key" in key.lower()
            or "token" in key.lower()
            or "secret" in key.lower()
            or "password" in key.lower()
        ):
            safe[key] = value[:4] + "****" if len(value) > 4 else "****"
        else:
            safe[key] = value
    return safe


# ========================================
# Pydantic Models
# ========================================


class ShareCreateRequest(BaseModel):
    """创建分享请求"""

    task_id: str | None = Field(None, description="任务 ID，空则最近一次")
    include_config: bool = Field(True, description="是否包含配置")
    tags: list[str] = Field(default_factory=list, description="标签")
    expires_hours: int = Field(0, description="过期时间（小时），0=永不过期")


class ShareImportRequest(BaseModel):
    """导入分享请求"""

    target_dir: str | None = Field(None, description="导入目标目录")


class ShareResponse(BaseModel):
    """分享响应"""

    share_id: str
    created_at: str
    expires_at: str | None = None
    tags: list[str] = []
    task: str = ""
    steps: int = 0


class ShareDetailResponse(BaseModel):
    """分享详情响应"""

    share_id: str
    version: int = 1
    created_at: str
    expires_at: str | None = None
    tags: list[str] = []
    session: dict[str, Any] = {}


# ========================================
# API Endpoints
# ========================================


@router.post("", response_model=ShareDetailResponse)
async def create_share(req: ShareCreateRequest) -> Any:
    """生成分享"""
    _ensure_dir()

    # 查找目标历史
    target_file = None
    if req.task_id:
        for prefix in ["", "history_"]:
            candidate = HISTORY_DIR / f"{prefix}{req.task_id}.json"
            if candidate.exists():
                target_file = candidate
                break
        if not target_file:
            raise HTTPException(status_code=404, detail=f"任务不存在: {req.task_id}")
    else:
        json_files = sorted(
            HISTORY_DIR.glob("*.json"),
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        )
        if not json_files:
            raise HTTPException(status_code=404, detail="没有历史记录")
        target_file = json_files[0]

    try:
        with open(target_file, encoding="utf-8") as f:
            history_data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        raise HTTPException(status_code=500, detail=f"读取失败: {e}")

    # 生成分享 ID
    import uuid

    share_id = uuid.uuid4().hex[:8]
    now = datetime.now().isoformat()

    share_record = {
        "share_id": share_id,
        "version": 1,
        "created_at": now,
        "expires_at": (
            datetime.fromtimestamp(
                datetime.now().timestamp() + req.expires_hours * 3600
            ).isoformat()
            if req.expires_hours > 0
            else None
        ),
        "tags": req.tags,
        "session": {
            "history": history_data,
        },
    }

    if req.include_config:
        config_path = Path.home() / ".omc" / "config.json"
        if config_path.exists():
            try:
                with open(config_path, encoding="utf-8") as f:
                    config = json.load(f)
                share_record["session"]["config"] = _sanitize_config(config)
            except (json.JSONDecodeError, OSError):
                pass

    share_file = _share_path(share_id)
    with open(share_file, "w", encoding="utf-8") as f:
        json.dump(share_record, f, ensure_ascii=False, indent=2)

    return share_record


@router.get("", response_model=list[ShareResponse])
async def list_shares() -> Any:
    """列出所有分享"""
    _ensure_dir()

    shares = []
    for f in SHARE_DIR.glob("share_*.json"):
        try:
            with open(f, encoding="utf-8") as fh:
                data = json.load(fh)
            history = data.get("session", {}).get("history", {})
            shares.append(
                ShareResponse(
                    share_id=data.get("share_id", ""),
                    created_at=data.get("created_at", ""),
                    expires_at=data.get("expires_at"),
                    tags=data.get("tags", []),
                    task=history.get("task_description", ""),
                    steps=len(history.get("steps", [])),
                )
            )
        except (json.JSONDecodeError, OSError):
            continue

    shares.sort(key=lambda s: s.created_at, reverse=True)
    return shares


@router.get("/{share_id}", response_model=ShareDetailResponse)
async def get_share(share_id: str) -> Any:
    """获取分享详情"""
    share_file = _share_path(share_id)
    if not share_file.exists():
        raise HTTPException(status_code=404, detail=f"分享不存在: {share_id}")

    try:
        with open(share_file, encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        raise HTTPException(status_code=500, detail=f"读取失败: {e}")

    # 检查过期
    if data.get("expires_at"):
        expires = datetime.fromisoformat(data["expires_at"])
        if datetime.now() > expires:
            raise HTTPException(status_code=410, detail="分享已过期")

    return data


@router.post("/{share_id}/import")
async def import_share(share_id: str, req: ShareImportRequest) -> Any:
    """通过分享 ID 导入会话"""
    _ensure_dir()

    share_file = _share_path(share_id)
    if not share_file.exists():
        raise HTTPException(status_code=404, detail=f"分享不存在: {share_id}")

    try:
        with open(share_file, encoding="utf-8") as f:
            share_data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        raise HTTPException(status_code=500, detail=f"读取失败: {e}")

    # 检查过期
    if share_data.get("expires_at"):
        expires = datetime.fromisoformat(share_data["expires_at"])
        if datetime.now() > expires:
            raise HTTPException(status_code=410, detail="分享已过期")

    session = share_data.get("session", {})
    history_data = session.get("history", {})

    if not history_data:
        raise HTTPException(status_code=400, detail="分享中没有历史数据")

    t_dir = Path(req.target_dir) if req.target_dir else HISTORY_DIR
    t_dir.mkdir(parents=True, exist_ok=True)

    # 生成导入 ID
    import uuid

    orig_id = history_data.get("history_id", uuid.uuid4().hex[:8])
    imported_id = f"{orig_id}_imported_{share_id}"

    history_data["history_id"] = imported_id
    history_data["imported_from"] = share_id
    history_data["imported_at"] = datetime.now().isoformat()

    target_file = t_dir / f"history_{imported_id}.json"
    with open(target_file, "w", encoding="utf-8") as f:
        json.dump(history_data, f, ensure_ascii=False, indent=2)

    return {
        "status": "imported",
        "history_id": imported_id,
        "share_id": share_id,
        "file": str(target_file),
    }


@router.delete("/{share_id}")
async def delete_share(share_id: str) -> Any:
    """删除分享"""
    share_file = _share_path(share_id)
    if not share_file.exists():
        raise HTTPException(status_code=404, detail=f"分享不存在: {share_id}")

    share_file.unlink()
    return {"status": "deleted", "share_id": share_id}
