"""
API Key 脱敏工具

提供 API Key 脱敏功能，避免在日志、错误信息中泄露敏感信息。
"""

import re
from typing import Optional


# 常见 API Key 模式
API_KEY_PATTERNS = [
    # OpenAI / DeepSeek / Zhipu AI 等 (sk-...)
    (r"(sk-[a-zA-Z0-9]{4})[a-zA-Z0-9]{4,}([a-zA-Z0-9]{4})", r"\1....\2"),
    # Bearer Token
    (r"(Bearer\s+[a-zA-Z0-9]{4})[a-zA-Z0-9]{4,}([a-zA-Z0-9]{4})", r"\1....\2"),
    # ZHIPUAI_API_KEY (zai-...)
    (r"(zai-[a-zA-Z0-9]{4})[a-zA-Z0-9]{4,}([a-zA-Z0-9]{4})", r"\1....\2"),
    # 通用 API Key (至少8字符，字母数字+少量特殊字符)
    (r"([a-zA-Z0-9]{4})[a-zA-Z0-9+/=_-]{4,}([a-zA-Z0-9]{4})", r"\1....\2"),
]


def mask_api_key(text: str, mask_char: str = "....") -> str:
    """
    对文本中的 API Key 进行脱敏处理。

    Args:
        text: 原始文本（可能包含 API Key）
        mask_char: 脱敏替换字符，默认 "...."

    Returns:
        脱敏后的文本

    Examples:
        >>> mask_api_key("my key is sk-abc123def456")
        'my key is sk-ab....56'
        >>> mask_api_key("ZHIPUAI_API_KEY=zai-1234567890abcdef")
        'ZHIPUAI_API_KEY=zai-1....def'
    """
    if not text:
        return text

    result = text
    for pattern, replacement in API_KEY_PATTERNS:
        result = re.sub(pattern, replacement, result)

    return result


def mask_headers(headers: dict) -> dict:
    """
    对 HTTP Headers 中的敏感信息进行脱敏。

    Args:
        headers: HTTP Headers 字典

    Returns:
        脱敏后的 Headers 字典

    Examples:
        >>> mask_headers({"Authorization": "Bearer sk-abc123"})
        {'Authorization': 'Bearer sk-....'}
    """
    if not headers:
        return headers

    masked = headers.copy()
    sensitive_keys = ["authorization", "x-api-key", "api-key", "token"]

    for key in masked:
        if key.lower() in sensitive_keys:
            masked[key] = mask_api_key(masked[key])

    return masked


def safe_log(message: str, logger_func, *args, **kwargs) -> None:
    """
    安全的日志记录函数，自动脱敏 API Key。

    Args:
        message: 日志消息（可能包含 API Key）
        logger_func: 日志函数（如 logger.info, logger.debug）
        *args, **kwargs: 传递给 logger_func 的参数
    """
    masked_message = mask_api_key(message)
    logger_func(masked_message, *args, **kwargs)


class APIKeyMasker:
    """
    API Key 脱敏器（类版本，支持自定义规则）。
    """

    def __init__(self, custom_patterns: Optional[list] = None) -> None:
        """
        Args:
            custom_patterns: 自定义脱敏规则，格式为 [(pattern, replacement), ...]
        """
        self.patterns = custom_patterns if custom_patterns else API_KEY_PATTERNS

    def mask(self, text: str) -> str:
        """脱敏文本中的 API Key"""
        if not text:
            return text

        result = text
        for pattern, replacement in self.patterns:
            result = re.sub(pattern, replacement, result)

        return result

    def mask_dict(self, data: dict, keys_to_mask: Optional[list] = None) -> dict:
        """
        脱敏字典中的敏感字段。

        Args:
            data: 原始字典
            keys_to_mask: 需要脱敏的键列表，默认 ["api_key", "token", "password"]
        """
        if not data:
            return data

        masked = data.copy()
        keys_to_mask = keys_to_mask or ["api_key", "token", "password", "secret"]

        for key in masked:
            if key.lower() in [k.lower() for k in keys_to_mask]:
                if isinstance(masked[key], str):
                    masked[key] = self.mask(masked[key])

        return masked
