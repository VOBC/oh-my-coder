"""
Ollama 健康检查模块

提供 Ollama 服务的综合健康检查、模型可用性检测和状态查询。
内置缓存机制（30 秒），避免频繁 ping 影响性能。

使用方式：
    from src.core.ollama_health import OllamaHealthChecker, OllamaHealthStatus

    checker = OllamaHealthChecker()
    status = checker.check_ollama()
    print(status.running, status.version, status.model_count)

    # 检查特定模型
    if checker.check_model_available("qwen2:7b"):
        print("模型可用")

    # 获取完整状态
    info = checker.get_ollama_status()
    print(info["running"], info["models"])
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

import httpx

from src.core.local_model_discovery import (
    discover_ollama_models,
    is_ollama_running,
)
from src.models.ollama import OLLAMA_DEFAULT_URL


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class OllamaHealthStatus:
    """
    Ollama 健康检查结果

    Attributes:
        running: Ollama 服务是否正在运行
        version: Ollama 版本号（如 0.1.45），服务未运行时为 None
        model_count: 已下载模型数量
        available_models: 已下载模型名称列表
        latency_ms: 健康检查响应延迟（毫秒）
        last_check_time: 最后检查时间
    """

    running: bool = False
    version: Optional[str] = None
    model_count: int = 0
    available_models: List[str] = field(default_factory=list)
    latency_ms: float = 0.0
    last_check_time: Optional[datetime] = field(default_factory=None)

    def to_dict(self) -> dict:
        """导出为字典，便于序列化或日志记录"""
        return {
            "running": self.running,
            "version": self.version,
            "model_count": self.model_count,
            "available_models": self.available_models,
            "latency_ms": round(self.latency_ms, 2),
            "last_check_time": (
                self.last_check_time.isoformat()
                if self.last_check_time
                else None
            ),
        }


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# 缓存有效期（秒）
_CACHE_TTL_SECONDS = 30.0

# HTTP 超时配置
_CONNECT_TIMEOUT = 2.0
_READ_TIMEOUT = 5.0


# ---------------------------------------------------------------------------
# Health checker
# ---------------------------------------------------------------------------


class OllamaHealthChecker:
    """
    Ollama 服务健康检查器

    提供：
    - 综合健康检查（服务状态 + 版本 + 模型列表）
    - 单模型可用性检查
    - 原始状态字典查询

    特性：
    - 内置 30 秒结果缓存，避免频繁网络请求
    - 可配置连接超时（默认 2 秒）和读取超时（默认 5 秒）
    - 复用 local_model_discovery 中的发现逻辑

    Example:
        >>> checker = OllamaHealthChecker()
        >>> status = checker.check_ollama()
        >>> print(status.running)
        True
        >>> checker.check_model_available("qwen2:7b")
        True
    """

    def __init__(
        self,
        base_url: str = OLLAMA_DEFAULT_URL,
        cache_ttl: float = _CACHE_TTL_SECONDS,
        connect_timeout: float = _CONNECT_TIMEOUT,
        read_timeout: float = _READ_TIMEOUT,
    ) -> None:
        """
        初始化健康检查器

        Args:
            base_url: Ollama API 地址
            cache_ttl: 缓存有效期（秒），默认 30 秒
            connect_timeout: 连接超时（秒），默认 2 秒
            read_timeout: 读取超时（秒），默认 5 秒
        """
        self.base_url = base_url.rstrip("/")
        self.cache_ttl = cache_ttl
        self.connect_timeout = connect_timeout
        self.read_timeout = read_timeout

        # 缓存
        self._cached_status: Optional[OllamaHealthStatus] = None
        self._cache_timestamp: float = 0.0

        # httpx client 复用
        self._client: Optional[httpx.Client] = None

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    def check_ollama(self) -> OllamaHealthStatus:
        """
        综合健康检查

        检查 Ollama 服务是否运行、获取版本号和已下载模型列表。
        结果缓存 30 秒，期间多次调用直接返回缓存值。

        Returns:
            OllamaHealthStatus: 健康检查结果
        """
        now = time.monotonic()

        # 缓存命中
        if (
            self._cached_status is not None
            and (now - self._cache_timestamp) < self.cache_ttl
        ):
            return self._cached_status

        # 执行检查
        status = self._do_check(now)
        self._cached_status = status
        self._cache_timestamp = now
        return status

    def check_model_available(self, model_name: str) -> bool:
        """
        检查特定模型是否已下载可用

        Args:
            model_name: 模型名称，如 qwen2:7b、llama3:8b

        Returns:
            bool: 模型是否可用（已下载）
        """
        if not model_name or not model_name.strip():
            return False

        # 先用缓存检查整体状态，避免每次都发网络请求
        status = self.check_ollama()
        if not status.running:
            return False

        return model_name.strip() in status.available_models

    def get_ollama_status(self) -> dict:
        """
        获取 Ollama 状态字典

        Returns:
            dict: 包含 running(bool)、version(str|None)、model_count(int)、models(List[str])
        """
        status = self.check_ollama()
        return {
            "running": status.running,
            "version": status.version,
            "model_count": status.model_count,
            "models": status.available_models,
        }

    # -----------------------------------------------------------------------
    # Internal
    # -----------------------------------------------------------------------

    def _do_check(self, timestamp: float) -> OllamaHealthStatus:
        """执行实际的健康检查（无缓存）"""
        start = time.perf_counter()

        # 1. 检查服务是否运行
        running = is_ollama_running(self.base_url)

        if not running:
            return OllamaHealthStatus(
                running=False,
                version=None,
                model_count=0,
                available_models=[],
                latency_ms=(time.perf_counter() - start) * 1000,
                last_check_time=datetime.now(),
            )

        # 2. 并行获取版本和模型列表
        version = self._fetch_version()
        models = discover_ollama_models(self.base_url)

        return OllamaHealthStatus(
            running=True,
            version=version,
            model_count=len(models),
            available_models=[m.model_name for m in models],
            latency_ms=(time.perf_counter() - start) * 1000,
            last_check_time=datetime.now(),
        )

    def _fetch_version(self) -> Optional[str]:
        """
        获取 Ollama 版本号

        调用 GET /api/version 端点。失败时返回 None。
        """
        try:
            client = self._get_client()
            response = client.get(f"{self.base_url}/api/version")
            if response.status_code == 200:
                data = response.json()
                return data.get("version")
            return None
        except Exception:
            return None

    def _get_client(self) -> httpx.Client:
        """获取/创建复用的 httpx client"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.Client(
                timeout=httpx.Timeout(
                    connect=self.connect_timeout,
                    read=self.read_timeout,
                )
            )
        return self._client

    def clear_cache(self) -> None:
        """手动清除缓存，强制下次检查时重新请求"""
        self._cached_status = None
        self._cache_timestamp = 0.0

    def close(self) -> None:
        """关闭内部 httpx client"""
        if self._client is not None and not self._client.is_closed:
            self._client.close()
            self._client = None

    def __enter__(self) -> "OllamaHealthChecker":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
