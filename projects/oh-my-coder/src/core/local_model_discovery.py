"""
本地模型发现模块

自动发现本地 Ollama 部署的模型，支持动态获取模型列表和详情。

使用方式：
    from src.core.local_model_discovery import (
        discover_ollama_models,
        get_model_info,
        is_ollama_running,
    )

    # 检测 Ollama 是否运行
    if is_ollama_running():
        # 获取已安装模型列表
        models = discover_ollama_models()
        for m in models:
            print(m.model_name, m.size, m.quantization)

        # 获取单个模型详情
        info = get_model_info("qwen2:7b")
        print(info.parameter_size, info.quantization, info.template)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import httpx

from src.models.ollama import OLLAMA_DEFAULT_URL

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class OllamaModelInfo:
    """
    单个 Ollama 模型的结构化信息

    Attributes:
        model_name: 模型名称，如 qwen2:7b、llama3:8b
        size: 模型大小（字节），可自行转换为 GB/MB
        quantization: 量化方式，如 q4_K_M、q5_K_M、q8_0、fp16
        modified_at: 模型文件的最后修改时间
        parameter_size: 参数量，如 7B、13B、72B（仅 /api/show 可获取）
        template: 聊天模板（仅 /api/show 可获取）
        license: 模型许可证（仅 /api/show 可获取）
        system: 系统提示（仅 /api/show 可获取）
        raw: 原始 API 响应（供调试用）
    """

    model_name: str
    size: int = 0
    quantization: str | None = None
    modified_at: str | None = None
    parameter_size: str | None = field(default=None, repr=False)
    template: str | None = field(default=None, repr=False)
    license: str | None = field(default=None, repr=False)
    system: str | None = field(default=None, repr=False)
    raw: dict[str, Any] = field(default_factory=dict, repr=False)

    @property
    def size_gb(self) -> float:
        """返回模型大小（GB）"""
        if self.size <= 0:
            return 0.0
        return round(self.size / (1024**3), 2)

    @property
    def size_mb(self) -> float:
        """返回模型大小（MB）"""
        if self.size <= 0:
            return 0.0
        return round(self.size / (1024**2), 2)

    def to_dict(self) -> dict[str, Any]:
        """导出为字典（不含 raw 字段）"""
        return {
            "model_name": self.model_name,
            "size": self.size,
            "size_gb": self.size_gb,
            "quantization": self.quantization,
            "modified_at": self.modified_at,
            "parameter_size": self.parameter_size,
            "template": self.template,
            "license": self.license,
            "system": self.system,
        }


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------

# 同步 httpx client 复用的 timeout 配置
_OLLAMA_TIMEOUT = httpx.Timeout(5.0, connect=2.0)


def _make_client() -> httpx.Client:
    """创建同步 httpx client，复用连接"""
    return httpx.Client(timeout=_OLLAMA_TIMEOUT)


def is_ollama_running(base_url: str = OLLAMA_DEFAULT_URL) -> bool:
    """
    检测 Ollama 服务是否正在运行

    通过调用 /api/tags 端点判断服务可用性。
    Ollama 未运行时返回 False，不会抛出异常。

    Args:
        base_url: Ollama API 地址，默认 http://localhost:11434

    Returns:
        bool: True 表示 Ollama 服务可用

    Example:
        >>> is_ollama_running()
        True
    """
    try:
        url = f"{base_url.rstrip('/')}/api/tags"
        with _make_client() as client:
            response = client.get(url)
            return response.status_code == 200
    except Exception:
        return False


def discover_ollama_models(
    base_url: str = OLLAMA_DEFAULT_URL,
) -> list[OllamaModelInfo]:
    """
    发现所有本地已安装的 Ollama 模型

    调用 GET /api/tags 获取模型列表，返回结构化的模型信息。
    Ollama 未运行时返回空列表，不会抛出异常。

    Args:
        base_url: Ollama API 地址，默认 http://localhost:11434

    Returns:
        List[OllamaModelInfo]: 已安装模型列表，按 modified_at 降序排列（最新在前）

    Example:
        >>> models = discover_ollama_models()
        >>> for m in models:
        ...     print(f"{m.model_name} ({m.size_gb} GB)")
        qwen2:7b (4.4 GB)
        llama3:8b (4.7 GB)
    """
    try:
        url = f"{base_url.rstrip('/')}/api/tags"
        with _make_client() as client:
            response = client.get(url)
            if response.status_code != 200:
                return []
            data = response.json()

        raw_models: list[dict[str, Any]] = data.get("models", [])
        result: list[OllamaModelInfo] = []

        for raw in raw_models:
            model = OllamaModelInfo(
                model_name=raw.get("name", ""),
                size=raw.get("size", 0),
                quantization=raw.get("quantization"),
                modified_at=raw.get("modified_at"),
                raw=raw,
            )
            # 过滤掉空名称
            if model.model_name:
                result.append(model)

        # 按 modified_at 降序排列
        result.sort(
            key=lambda m: m.modified_at or "",
            reverse=True,
        )
        return result

    except Exception:
        return []


def get_model_info(
    model_name: str,
    base_url: str = OLLAMA_DEFAULT_URL,
) -> OllamaModelInfo | None:
    """
    获取单个模型的详细信息

    调用 POST /api/show 获取模型详情，包含参数量、量化方式、模板等。
    模型不存在或 Ollama 未运行时返回 None，不会抛出异常。

    Args:
        model_name: 模型名称，如 qwen2:7b、llama3:8b
        base_url: Ollama API 地址，默认 http://localhost:11434

    Returns:
        Optional[OllamaModelInfo]: 模型详情，失败时返回 None

    Example:
        >>> info = get_model_info("qwen2:7b")
        >>> if info:
        ...     print(info.parameter_size)
        ...     print(info.quantization)
        ...     print(info.template[:80])
        7B
        q4_K_M
        {{ if .System }}...
    """
    if not model_name or not model_name.strip():
        return None

    try:
        url = f"{base_url.rstrip('/')}/api/show"
        with _make_client() as client:
            response = client.post(
                url,
                json={"name": model_name.strip()},
            )
            if response.status_code != 200:
                return None
            data: dict[str, Any] = response.json()

        # /api/tags 部分（模型文件信息）
        tags_data: dict[str, Any] = data.get("model_info", {})
        # /api/show 专用字段
        parameter_size: str | None = tags_data.get("parameter_size")
        # license / template / system 可能在 model_info 也可能在顶层
        license_val = data.get("license") or tags_data.get("license")
        template_val = data.get("template") or tags_data.get("template")
        system_val = data.get("system") or tags_data.get("system")

        # /api/tags 字段（如果可用）
        try:
            size = tags_data.get("size", 0)
        except Exception:
            size = 0

        return OllamaModelInfo(
            model_name=model_name.strip(),
            size=size,
            quantization=tags_data.get("quantization"),
            modified_at=tags_data.get("modified_at"),
            parameter_size=parameter_size,
            template=template_val,
            license=license_val,
            system=system_val,
            raw=data,
        )

    except Exception:
        return None


# ---------------------------------------------------------------------------
# Async variants (for consistency with rest of codebase)
# ---------------------------------------------------------------------------

_async_client: httpx.AsyncClient | None = None


async def _get_async_client() -> httpx.AsyncClient:
    """获取/创建全局异步 httpx client"""
    global _async_client
    if _async_client is None or _async_client.is_closed:
        _async_client = httpx.AsyncClient(timeout=_OLLAMA_TIMEOUT)
    return _async_client


async def is_ollama_running_async(
    base_url: str = OLLAMA_DEFAULT_URL,
) -> bool:
    """异步版本：检测 Ollama 是否运行"""
    try:
        url = f"{base_url.rstrip('/')}/api/tags"
        client = await _get_async_client()
        response = await client.get(url)
        return response.status_code == 200
    except Exception:
        return False


async def discover_ollama_models_async(
    base_url: str = OLLAMA_DEFAULT_URL,
) -> list[OllamaModelInfo]:
    """异步版本：发现所有本地模型"""
    try:
        url = f"{base_url.rstrip('/')}/api/tags"
        client = await _get_async_client()
        response = await client.get(url)
        if response.status_code != 200:
            return []
        data = response.json()

        raw_models: list[dict[str, Any]] = data.get("models", [])
        result: list[OllamaModelInfo] = [
            OllamaModelInfo(
                model_name=raw.get("name", ""),
                size=raw.get("size", 0),
                quantization=raw.get("quantization"),
                modified_at=raw.get("modified_at"),
                raw=raw,
            )
            for raw in raw_models
            if raw.get("name")
        ]

        result.sort(key=lambda m: m.modified_at or "", reverse=True)
        return result

    except Exception:
        return []


async def get_model_info_async(
    model_name: str,
    base_url: str = OLLAMA_DEFAULT_URL,
) -> OllamaModelInfo | None:
    """异步版本：获取单个模型详情"""
    if not model_name or not model_name.strip():
        return None

    try:
        url = f"{base_url.rstrip('/')}/api/show"
        client = await _get_async_client()
        response = await client.post(
            url,
            json={"name": model_name.strip()},
        )
        if response.status_code != 200:
            return None
        data: dict[str, Any] = response.json()

        model_info: dict[str, Any] = data.get("model_info", {})
        parameter_size: str | None = model_info.get("parameter_size")
        license_val = data.get("license") or model_info.get("license")
        template_val = data.get("template") or model_info.get("template")
        system_val = data.get("system") or model_info.get("system")

        try:
            size = model_info.get("size", 0)
        except Exception:
            size = 0

        return OllamaModelInfo(
            model_name=model_name.strip(),
            size=size,
            quantization=model_info.get("quantization"),
            modified_at=model_info.get("modified_at"),
            parameter_size=parameter_size,
            template=template_val,
            license=license_val,
            system=system_val,
            raw=data,
        )

    except Exception:
        return None
