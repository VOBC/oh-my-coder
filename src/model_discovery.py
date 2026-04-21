"""
Model Discovery - 动态模型发现系统

从各厂商 API 拉取可用模型列表，检测新模型
"""

from __future__ import annotations

import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import requests


class ModelDiscovery:
    """动态模型发现：从各厂商 API 拉取可用模型列表"""

    # 各厂商的 /models 端点配置
    PROVIDER_APIS = {
        "deepseek": {
            "url": "https://api.deepseek.com/models",
            "key_env": "DEEPSEEK_API_KEY",
            "format": "openai",  # OpenAI 兼容格式
        },
        "glm": {
            "url": "https://open.bigmodel.cn/api/paas/v4/models",
            "key_env": "ZHIPU_API_KEY",
            "format": "openai",
        },
        "tongyi": {
            "url": "https://dashscope.aliyuncs.com/compatible-mode/v1/models",
            "key_env": "DASHSCOPE_API_KEY",
            "format": "openai",
        },
        "kimi": {
            "url": "https://api.moonshot.cn/v1/models",
            "key_env": "KIMI_API_KEY",
            "format": "openai",
        },
        "doubao": {
            "url": "https://ark.cn-beijing.volces.com/api/v3/models",
            "key_env": "DOUBAO_API_KEY",
            "format": "openai",
        },
        "wenxin": {
            # 百度文心没有标准 /models 端点，跳过动态发现
            "skip": True,
            "reason": "百度文心没有标准 /models 端点",
        },
        "hunyuan": {
            # 腾讯混元没有标准 /models 端点，跳过
            "skip": True,
            "reason": "腾讯混元没有标准 /models 端点",
        },
        "minimax": {
            "url": "https://api.minimax.chat/v1/models",
            "key_env": "MINIMAX_API_KEY",
            "format": "openai",
        },
        "tiangong": {
            # 天工没有标准 /models 端点，跳过
            "skip": True,
            "reason": "天工没有标准 /models 端点",
        },
        "spark": {
            # 讯飞星火没有标准 /models 端点，跳过
            "skip": True,
            "reason": "讯飞星火没有标准 /models 端点",
        },
        "baichuan": {
            "url": "https://api.baichuan-ai.com/v1/models",
            "key_env": "BAICHUAN_API_KEY",
            "format": "openai",
        },
        "openai": {
            "url": "https://api.openai.com/v1/models",
            "key_env": "OPENAI_API_KEY",
            "format": "openai",
        },
        "anthropic": {
            # Anthropic 没有 /models 端点，跳过
            "skip": True,
            "reason": "Anthropic 没有标准 /models 端点",
        },
        "google": {
            # Google 使用不同的 API 格式，暂时跳过
            "skip": True,
            "reason": "Google API 格式不兼容",
        },
        "mimo": {
            # 小米 MiMo 没有标准 /models 端点，跳过
            "skip": True,
            "reason": "小米 MiMo 没有标准 /models 端点",
        },
    }

    # 缓存文件路径
    CACHE_FILE = Path.home() / ".omc" / "discovered_models.json"
    CACHE_TTL_HOURS = 24

    def __init__(self):
        self.cache_file = self.CACHE_FILE

    def _fetch_provider_models(
        self, provider: str, config: dict, timeout: int = 5
    ) -> list[dict]:
        """
        获取单个厂商的模型列表

        Args:
            provider: 厂商 ID
            config: 厂商配置
            timeout: 请求超时时间（秒）

        Returns:
            模型列表，失败返回空列表
        """
        # 检查是否跳过
        if config.get("skip"):
            return []

        url = config.get("url")
        key_env = config.get("key_env")
        api_format = config.get("format", "openai")

        if not url or not key_env:
            return []

        # 检查 API Key
        api_key = os.getenv(key_env)
        if not api_key:
            return []

        try:
            headers = {"Authorization": f"Bearer {api_key}"}
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            data = response.json()

            # 解析 OpenAI 兼容格式
            if api_format == "openai":
                models = data.get("data", [])
                # 过滤掉非对话模型（如 embedding, tts 等）
                chat_models = []
                for m in models:
                    model_id = m.get("id", "")
                    # 简单启发式：排除明显非对话的模型
                    skip_keywords = [
                        "embedding",
                        "tts",
                        "whisper",
                        "dall-e",
                        "image",
                        "audio",
                        "moderation",
                    ]
                    if any(kw in model_id.lower() for kw in skip_keywords):
                        continue
                    chat_models.append(
                        {
                            "id": model_id,
                            "created": m.get("created"),
                            "object": m.get("object"),
                            "owned_by": m.get("owned_by"),
                        }
                    )
                return chat_models

            return []

        except requests.exceptions.Timeout:
            return []
        except requests.exceptions.RequestException:
            return []
        except Exception:
            return []

    def discover_all(self, timeout: int = 5) -> dict[str, list[dict]]:
        """
        并发调用所有支持动态发现的厂商 API

        Args:
            timeout: 每个请求的超时时间（秒）

        Returns:
            {provider: [model_info, ...]}
            超时/无 key/报错 的 provider 返回空列表，不影响其他
        """
        results = {}

        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_provider = {
                executor.submit(
                    self._fetch_provider_models, provider, config, timeout
                ): provider
                for provider, config in self.PROVIDER_APIS.items()
                if not config.get("skip")
            }

            for future in as_completed(future_to_provider):
                provider = future_to_provider[future]
                try:
                    models = future.result()
                    results[provider] = models
                except Exception:
                    results[provider] = []

        return results

    def get_cached(self) -> dict | None:
        """
        读取本地缓存

        Returns:
            缓存数据或 None（如果缓存不存在或已过期）
        """
        if not self.cache_file.exists():
            return None

        try:
            with open(self.cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            cached_at = data.get("cached_at")
            if not cached_at:
                return None

            # 解析缓存时间
            try:
                cache_time = datetime.fromisoformat(cached_at)
                expiry_time = cache_time + timedelta(hours=self.CACHE_TTL_HOURS)

                if datetime.now() > expiry_time:
                    return None  # 缓存已过期

                return data
            except (ValueError, TypeError):
                return None

        except (json.JSONDecodeError, IOError):
            return None

    def save_cache(self, data: dict) -> None:
        """
        保存到本地缓存

        Args:
            data: 要缓存的数据
        """
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)

        cache_data = {
            "cached_at": datetime.now().isoformat(),
            "providers": data,
        }

        with open(self.cache_file, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)

    def compare_with_builtin(
        self,
        discovered: dict[str, list[dict]],
        builtin_models: list[dict],
    ) -> dict[str, Any]:
        """
        对比发现的模型 vs 内置模型

        Args:
            discovered: discover_all() 返回的结果
            builtin_models: 内置模型列表（如 BUILTIN_CATWALK_MODELS）

        Returns:
            {
                "new_models": [...],      # 厂商有但内置没有的（新模型！）
                "removed_models": [...],  # 内置有但厂商没返回的（可能下线）
                "unchanged": [...],       # 一致的
            }
        """
        # 构建内置模型 ID 集合
        builtin_model_ids = set()
        builtin_by_provider: dict[str, set[str]] = {}

        for m in builtin_models:
            provider = m.get("provider", "")
            model_id = m.get("model", "")
            if provider and model_id:
                builtin_model_ids.add(f"{provider}:{model_id}")
                if provider not in builtin_by_provider:
                    builtin_by_provider[provider] = set()
                builtin_by_provider[provider].add(model_id)

        # 对比结果
        new_models = []
        removed_models = []
        unchanged = []

        for provider, models in discovered.items():
            builtin_ids = builtin_by_provider.get(provider, set())

            for m in models:
                model_id = m.get("id", "")
                full_id = f"{provider}:{model_id}"

                if model_id in builtin_ids or full_id in builtin_model_ids:
                    unchanged.append(
                        {
                            "provider": provider,
                            "model_id": model_id,
                            "source": "discovery",
                        }
                    )
                else:
                    new_models.append(
                        {
                            "provider": provider,
                            "model_id": model_id,
                            "created": m.get("created"),
                            "owned_by": m.get("owned_by"),
                        }
                    )

        # 检查可能下线的模型（内置有但厂商没返回）
        discovered_ids = set()
        for provider, models in discovered.items():
            for m in models:
                model_id = m.get("id", "")
                discovered_ids.add(f"{provider}:{model_id}")

        for m in builtin_models:
            provider = m.get("provider", "")
            model_id = m.get("model", "")
            full_id = f"{provider}:{model_id}"

            # 如果该厂商有返回数据，但内置模型不在返回列表中
            if provider in discovered and discovered[provider]:
                if full_id not in discovered_ids and model_id not in {
                    mm.get("id", "") for mm in discovered.get(provider, [])
                }:
                    removed_models.append(
                        {
                            "provider": provider,
                            "model_id": model_id,
                            "name": m.get("name", ""),
                        }
                    )

        return {
            "new_models": new_models,
            "removed_models": removed_models,
            "unchanged": unchanged,
        }

    def sync(self, force: bool = False, timeout: int = 5) -> dict[str, Any]:
        """
        执行同步检查

        Args:
            force: 是否强制刷新（忽略缓存）
            timeout: 请求超时时间

        Returns:
            同步结果，包含状态信息
        """
        if not force:
            cached = self.get_cached()
            if cached:
                return {
                    "status": "cached",
                    "message": "使用缓存数据",
                    "data": cached.get("providers", {}),
                    "cached_at": cached.get("cached_at"),
                }

        # 执行发现
        discovered = self.discover_all(timeout=timeout)

        # 保存缓存
        self.save_cache(discovered)

        # 统计结果
        total_models = sum(len(models) for models in discovered.values())
        active_providers = [p for p, m in discovered.items() if m]

        return {
            "status": "success",
            "message": f"发现 {total_models} 个模型来自 {len(active_providers)} 个厂商",
            "data": discovered,
            "providers": {
                provider: len(models) for provider, models in discovered.items()
            },
        }


def get_discovery_summary(
    builtin_models: list[dict],
    discovery: ModelDiscovery | None = None,
) -> dict[str, Any]:
    """
    获取发现摘要（用于 omc model list 末尾提示）

    Args:
        builtin_models: 内置模型列表
        discovery: ModelDiscovery 实例（可选）

    Returns:
        摘要信息
    """
    if discovery is None:
        discovery = ModelDiscovery()

    # 尝试获取缓存或执行发现
    cached = discovery.get_cached()

    if cached:
        discovered = cached.get("providers", {})
        is_cached = True
    else:
        # 后台静默发现（不阻塞）
        discovered = discovery.discover_all(timeout=3)
        if discovered:
            discovery.save_cache(discovered)
        is_cached = False

    if not discovered:
        return {"has_new": False, "new_models": [], "is_cached": False}

    # 对比
    comparison = discovery.compare_with_builtin(discovered, builtin_models)
    new_models = comparison.get("new_models", [])

    return {
        "has_new": len(new_models) > 0,
        "new_models": new_models,
        "is_cached": is_cached,
        "total_discovered": sum(len(m) for m in discovered.values()),
    }


if __name__ == "__main__":
    # 测试代码
    discovery = ModelDiscovery()
    result = discovery.sync(force=True)
    print(json.dumps(result, ensure_ascii=False, indent=2))
