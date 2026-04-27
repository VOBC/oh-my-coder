"""
腾讯混元 (Hunyuan) 模型适配器

API: https://api.hunyuan.cn
文档: https://cloud.tencent.com/document/product/

特点：
- 腾讯自研大模型
- 中文理解能力强
- 支持多模态（文本/图像）
"""

import hashlib
import hmac
import json
import time

import httpx

from .base import (
    BaseModel,
    Message,
    ModelConfig,
    ModelProvider,
    ModelResponse,
    ModelTier,
    Usage,
)

# 混元模型配置
HUNYUAN_MODELS = {
    "low": {
        "name": "hunyuan-standard",
        "cost_per_1k_prompt": 0.0,  # 可能有免费额度
        "cost_per_1k_completion": 0.0,
    },
    "medium": {
        "name": "hunyuan-standard",
        "cost_per_1k_prompt": 0.0,
        "cost_per_1k_completion": 0.0,
    },
    "high": {
        "name": "hunyuan-pro",
        "cost_per_1k_prompt": 0.0,
        "cost_per_1k_completion": 0.0,
    },
}


class HunyuanModel(BaseModel):
    """
    腾讯混元 (Hunyuan) 模型适配器

    使用腾讯云 TC3-HMAC-SHA256 签名认证
    base URL: https://api.hunyuan.cn
    """

    def __init__(
        self,
        config: ModelConfig,
        tier: ModelTier = ModelTier.MEDIUM,
        secret_id: str | None = None,
        secret_key: str | None = None,
    ):
        if config.base_url is None:
            config.base_url = "https://api.hunyuan.cn"

        tier_key = tier.value
        model_info = HUNYUAN_MODELS.get(tier_key, HUNYUAN_MODELS["medium"])
        config.cost_per_1k_prompt = model_info["cost_per_1k_prompt"]
        config.cost_per_1k_completion = model_info["cost_per_1k_completion"]

        super().__init__(config, tier)
        self._client: httpx.AsyncClient | None = None
        self._secret_id = secret_id
        self._secret_key = secret_key

    @property
    def provider(self) -> ModelProvider:
        return ModelProvider.HUNYUAN

    @property
    def model_name(self) -> str:
        return HUNYUAN_MODELS[self.tier.value]["name"]

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.config.base_url,
                headers={"Content-Type": "application/json"},
                timeout=self.config.timeout,
            )
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    def _sign_tc3(
        self, secret_key: str, date: str, service: str, action: str, payload: str
    ) -> str:
        """TC3-HMAC-SHA256 签名"""

        def _hmac_sha256(key: bytes, msg: str) -> bytes:
            return hmac.new(key, msg.encode(), hashlib.sha256).digest()

        def _sha256(msg: str) -> bytes:
            return hashlib.sha256(msg.encode()).digest()

        # 步骤 1: 拼接规范请求串
        http_request_method = "POST"
        http_request_uri = "/"
        http_request_params = ""
        canonical_request = (
            f"{http_request_method}\n{http_request_uri}\n{http_request_params}\n"
            f"{_sha256(payload).hexdigest()}\n{_sha256('').hexdigest()}"
        )

        # 步骤 2: 拼接待签名字符串
        algorithm = "TC3-HMAC-SHA256"
        timestamp = int(time.time())
        credential_scope = f"{date}/{service}/tc3_request"
        hashed_canonical_request = hashlib.sha256(
            canonical_request.encode()
        ).hexdigest()
        string_to_sign = (
            f"{algorithm}\n{timestamp}\n{credential_scope}\n{hashed_canonical_request}"
        )

        # 步骤 3: 计算签名
        secret_date = _hmac_sha256(("TC3" + secret_key).encode(), date)
        secret_service = _hmac_sha256(secret_date, service)
        secret_signing = _hmac_sha256(secret_service, "tc3_request")
        signature = hmac.new(
            secret_signing, string_to_sign.encode(), hashlib.sha256
        ).hexdigest()

        # 步骤 4: 拼接 Authorization
        return (
            f"{algorithm} "
            f"Credential={self._secret_id}/{credential_scope}, "
            f"SignedHeaders=content-type;host, "
            f"Signature={signature}"
        )

    def _format_messages(self, messages: list[Message]) -> list[dict[str, str]]:
        formatted = []
        for msg in messages:
            item: dict[str, str] = {"role": msg.role, "content": msg.content}
            if msg.name:
                item["name"] = msg.name
            formatted.append(item)
        return formatted

    async def generate(self, messages: list[Message], **kwargs) -> ModelResponse:
        client = await self._get_client()

        payload = json.dumps(
            {
                "model": self.model_name,
                "messages": self._format_messages(messages),
                "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
                "temperature": kwargs.get("temperature", self.config.temperature),
            }
        )

        timestamp = int(time.time())
        date = time.strftime("%Y-%m-%d", time.gmtime(timestamp))
        host = "api.hunyuan.cn"

        headers = {
            "Content-Type": "application/json",
            "Host": host,
            "X-TC-Action": "ChatCompletions",
            "X-TC-Version": "2023-06-01",
            "X-TC-Timestamp": str(timestamp),
        }

        if self._secret_id and self._secret_key:
            headers["Authorization"] = self._sign_tc3(
                self._secret_key, date, "hunyuan", "ChatCompletions", payload
            )
            headers["X-TC-Region"] = "ap-guangzhou"

        start_time = time.time()

        try:
            response = await client.post("/", content=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            latency_ms = (time.time() - start_time) * 1000

            choice = data["choices"][0]
            content = choice["message"]["content"]

            usage_data = data.get("usage", {})
            usage = Usage(
                prompt_tokens=usage_data.get("prompt_tokens", 0),
                completion_tokens=usage_data.get("completion_tokens", 0),
                total_tokens=usage_data.get("total_tokens", 0),
            )
            self.update_usage(usage)

            return ModelResponse(
                content=content,
                model=self.model_name,
                provider=self.provider,
                tier=self.tier,
                usage=usage,
                finish_reason=choice.get("finish_reason", "stop"),
                latency_ms=latency_ms,
            )

        except httpx.HTTPStatusError as e:
            raise HunyuanAPIError(f"混元 API 错误 ({e.response.status_code}): {e}")
        except httpx.RequestError as e:
            raise HunyuanAPIError(f"网络请求失败: {e}")


class HunyuanAPIError(Exception):
    """腾讯混元 API 错误"""
