# 模型配置

## 支持的模型（11 家国内模型）

| 模型 | API Key 环境变量 | 特点 |
|------|-----------------|------|
| **DeepSeek** | `DEEPSEEK_API_KEY` | 性价比最高，推荐 |
| **智谱 GLM** | `GLM_API_KEY` | GLM-4-Flash **永久免费** |
| **文心一言** | `WENXIN_API_KEY` + `WENXIN_SECRET_KEY` | 百度云 |
| **通义千问** | `TONGYI_API_KEY` | 阿里云 |
| **Kimi** | `KIMI_API_KEY` | 月之暗面 |
| **混元** | `HUNYUAN_API_KEY` + `HUNYUAN_SECRET_KEY` | 腾讯云 |
| **豆包** | `DOUBAO_API_KEY` | 字节跳动 |
| **天工** | `TIANGONG_API_KEY` | 昆仑万维 |
| **讯飞星火** | `SPARK_API_KEY` + `SPARK_SECRET_KEY` + `SPARK_APP_ID` | 科大讯飞 |
| **百川** | `BAICHUAN_API_KEY` | 百川智能 |
| **GLM（自定义）** | `GLM_API_KEY` + `GLM_API_BASE` | 支持私有部署 |

## 模型层级

| 层级 | 模型 | 用途 |
|------|------|------|
| **LOW** | DeepSeek-V3 / GLM-4-Flash / Qwen-Turbo | 快速任务、探索 |
| **MEDIUM** | DeepSeek-R1 / Qwen-Max | 平衡性能和成本 |
| **HIGH** | DeepSeek-R1-Reasoner / Qwen-Plus | 复杂推理、高质量输出 |

## 默认模型配置

修改 `pyproject.toml` 或设置环境变量：

```bash
export OMC_DEFAULT_MODEL=deepseek-chat
export OMC_MODEL_TIER=medium
```

## 自定义 API 地址

```bash
export DEEPSEEK_API_BASE=https://your-proxy.com/v1
```

## 验证模型配置

```python
from src.llm import get_model_info

info = get_model_info("deepseek-chat")
print(info)  # {'model': 'deepseek-chat', 'provider': 'deepseek', ...}
```
