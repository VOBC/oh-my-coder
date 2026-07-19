from __future__ import annotations

# mypy: disable-error-code="abstract, arg-type, assignment, attr-defined, call-arg, call-overload, dict-item, func-returns-value, import-untyped, index, misc, no-any-return, no-redef, operator, override, return, return-value, syntax, union-attr, var-annotated"


"""
Gateway - 多平台统一消息网关

注意：渠道实现（Telegram/Discord/WhatsApp/飞书/企业微信/钉钉/Slack）
已移除（见 MEMORY.md），当前所有平台仅使用 NoopHandler 占位。

职责：
1. 管理所有平台处理器（默认 NoopHandler 占位）
2. 接收来自各平台的消息，统一转为 IncomingMessage
3. 转发给 Orchestrator 处理
4. 返回结果到对应平台

用法：
```python
gateway = Gateway(orchestrator=orch)
await gateway.start_all()
```

CLI:
    omc gateway status
    omc gateway start
"""


import asyncio
import logging
from pathlib import Path
from typing import Any, Optional

from .base import (
    IncomingMessage,
    NoopHandler,
    OutgoingMessage,
    Platform,
    PlatformHandler,
)

logger = logging.getLogger(__name__)


class Gateway:
    """
    多平台消息网关

    生命周期：
    1. __init__: 配置各平台
    2. start_all(): 启动所有已配置平台
    3. on_platform_message(): 接收消息 → Orchestrator → 回复
    4. stop_all(): 停止所有平台
    """

    def __init__(
        self,
        orchestrator: Any = None,
        allowed_user_ids: Optional[dict[Platform, list[str]]] = None,
        plugins_dir: Optional[Path] = None,
    ):
        """
        Args:
            orchestrator: Orchestrator 实例（用于处理消息）
            allowed_user_ids: 各平台的白名单用户 ID
            plugins_dir: 插件目录（预留）
        """
        self.orchestrator = orchestrator
        self._handlers: dict[Platform, PlatformHandler] = {}
        self._started_platforms: list[str] = []
        self._lock = asyncio.Lock()
        self._stop_event = asyncio.Event()

        # 渠道实现已移除（见 MEMORY.md）：各渠道平台默认使用 NoopHandler 占位
        # WECHAT 为内置主渠道，不经 Gateway 注册，保持无 handler
        for platform in Platform:
            if platform == Platform.WECHAT:
                continue
            self._handlers[platform] = NoopHandler(
                platform=platform, on_message=self._noop_handler
            )

    # ---- 消息处理 ----

    def on_platform_message(self, message: IncomingMessage) -> None:
        """
        收到各平台消息时的回调。

        默认实现：打印日志。
        子类/外部可覆盖此方法接入真实 Orchestrator。

        Args:
            message: 统一格式的收件消息
        """
        logger.info(
            f"[gateway] [{message.platform.value}] {message.user_id}: {message.text[:80]}"
        )

        if self.orchestrator is None:
            logger.debug("[gateway] No orchestrator configured, skipping processing")
            return

        # 异步处理（不阻塞平台回调）
        asyncio.create_task(self._process_message(message))

    async def _process_message(self, message: IncomingMessage) -> None:
        """处理消息 → Orchestrator → 回复"""
        try:
            if self.orchestrator is None:
                return

            # 构建 context
            context = {
                "task": message.text,
                "project_path": str(Path.cwd()),
                "_platform": message.platform.value,
                "_user_id": message.user_id,
                "_chat_id": message.chat_id,
            }

            # 执行工作流
            result = await self.orchestrator.execute_workflow(
                "autopilot",
                context,
            )

            # 提取结果文本
            response_text = self._extract_response(result)

            # 发回平台
            reply = OutgoingMessage(
                platform=message.platform,
                chat_id=message.chat_id,
                text=response_text,
                reply_to=message.reply_to,
            )
            handler = self._handlers.get(message.platform)
            if handler and handler.is_started:
                await handler.send(reply)

        except Exception as e:
            logger.exception(f"[gateway] _process_message error: {e}")
            # 尝试发错误回复
            try:
                error_reply = OutgoingMessage(
                    platform=message.platform,
                    chat_id=message.chat_id,
                    text=f"⚠️ 处理失败: {type(e).__name__}",
                )
                handler = self._handlers.get(message.platform)
                if handler and handler.is_started:
                    await handler.send(error_reply)
            except Exception:
                pass

    @staticmethod
    def _extract_response(result: Any) -> str:
        """从 WorkflowResult 提取响应文本"""
        if result is None:
            return "（无结果）"

        # 尝试 outputs
        if hasattr(result, "outputs") and result.outputs:
            parts = []
            for agent_name, output in result.outputs.items():
                content = getattr(output, "result", None)
                if content:
                    parts.append(f"**[{agent_name}]**\n{content[:500]}")
            if parts:
                return "\n\n".join(parts)

        # 降级：直接 str
        return str(result)[:1000]

    # ---- 生命周期 ----

    async def start_all(self) -> None:
        """启动所有已配置的平台"""
        async with self._lock:
            tasks = []
            for platform, handler in self._handlers.items():
                if not handler.is_started:
                    tasks.append(self._start_platform(platform, handler))

            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

        started = [p for p, h in self._handlers.items() if h.is_started]
        logger.info(f"[gateway] Started platforms: {[p.value for p in started]}")

    async def _start_platform(
        self, platform: Platform, handler: PlatformHandler
    ) -> None:
        try:
            await handler.start()
            self._started_platforms.append(platform.value)
        except Exception as e:
            logger.exception(f"[gateway] Failed to start {platform.value}: {e}")

    async def stop_all(self) -> None:
        """停止所有平台"""
        async with self._lock:
            tasks = []
            for platform, handler in self._handlers.items():
                if handler.is_started:
                    tasks.append(self._stop_platform(platform, handler))

            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

        self._stop_event.set()
        logger.info("[gateway] All platforms stopped")

    async def _stop_platform(
        self, platform: Platform, handler: PlatformHandler
    ) -> None:
        try:
            await handler.stop()
            if platform.value in self._started_platforms:
                self._started_platforms.remove(platform.value)
        except Exception as e:
            logger.exception(f"[gateway] Error stopping {platform.value}: {e}")

    # ---- 状态查询 ----

    def status(self) -> dict[str, Any]:
        """返回网关状态"""
        handlers_info = {
            platform.value: {
                "configured": handler.__class__ != NoopHandler,
                "started": handler.is_started,
                "type": handler.__class__.__name__,
            }
            for platform, handler in self._handlers.items()
        }
        return {
            "started_platforms": self._started_platforms,
            "handlers": handlers_info,
        }

    def get_handler(self, platform: Platform) -> Optional[PlatformHandler]:
        return self._handlers.get(platform)

    def _noop_handler(self, message: IncomingMessage) -> None:
        """NoopHandler 的 on_message 回调"""
