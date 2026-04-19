# 模型配置详细指南

> 本文从 README.md 迁移而来，包含全部 12 个模型提供商的配置说明。

## 🧠 支持的模型

共 **12 个**模型提供商，系统自动按性价比选择：

### 模型支持状态

| 提供商 | 支持状态 | 备注 |
|--------|----------|------|
| **DeepSeek** | ✅ [生产就绪] | ⭐ 推荐首选，DeepSeek-V3 **免费额度**，推理能力强 |
| **MiMo** | ✅ [生产就绪] | 小米 MiMo，mimo-v2-flash **免费**，1M 上下文 |
| **智谱 GLM** | ✅ [生产就绪] | GLM-4-Flash **官方免费**，函数调用支持，兼容性好 |
| **Kimi** | ✅ [生产就绪] | 128K 上下文，适合大代码库 |
| **豆包** | ✅ [生产就绪] | 字节自研，响应速度快 |
| **天工AI** | ✅ [生产就绪] | 昆仑万维出品，中文理解强 |
| **百川智能** | ✅ [生产就绪] | 王小川创办，中文能力出色 |
| **MiniMax** | ⚠️ [Beta] | 中文理解强，但无函数调用（tools）实现 |
| **通义千问** | ⚠️ [Beta] | 阿里多模型，无重试机制，高并发偶发超时 |
| **讯飞星火** | ⚠️ [待完善] | 需三凭证（API Key + App ID + Secret Key），认证复杂 |
| **文心一言** | ⚠️ [待完善] | 需双 Key 认证（API Key + Secret Key），文档不完善 |
| **混元** | ⚠️ [待完善] | 需双 Key 认证（API Key + Secret Key），长文本处理慢 |

| 提供商 | 环境变量 | 默认模型 | 特点 |
|--------|----------|----------|------|
| **DeepSeek** | `DEEPSEEK_API_KEY` | `deepseek-chat` | ⭐ 免费额度，推理能力强 |
| **MiMo** | `MIMOAPIKEY` | `mimo-v2-flash` | 小米 MiMo，免费 256K / Pro 1M 上下文 |
| **智谱 GLM** | `GLM_API_KEY` | `glm-4-flash` | 官方免费，函数调用支持 |
| **Kimi** | `KIMI_API_KEY` | `moonshot-v1-128k` | 128K 超长上下文 |
| **豆包** | `DOUBAO_API_KEY` | `doubao-pro-32k` | 字节自研，响应快 |
| **天工AI** | `TIANGONG_API_KEY` | `skywork-v1.0` | 昆仑万维出品，中文强 |
| **百川智能** | `BAICHUAN_API_KEY` | `Baichuan4` | 王小川创办，中文出色 |
| **MiniMax** | `MINIMAX_API_KEY` | `abab6-chat` | 中文理解强 |
| **通义千问** | `TONGYI_API_KEY` | `qwen-turbo` | 阿里多模型 |
| **讯飞星火** | `SPARK_API_KEY` + `SPARK_APP_ID` + `SPARK_SECRET_KEY` | `generalv3.5` | 科大讯飞出品，语音交互 |
| **文心一言** | `WENXIN_API_KEY` + `WENXIN_SECRET_KEY` | `ernie-4.0-8k-latest` | 百度中文强 |
| **混元** | `HUNYUAN_API_KEY` + `HUNYUAN_SECRET_KEY` | `hunyuan-pro` | 腾讯自研 |

> 💡 只需配置 `DEEPSEEK_API_KEY` 即可使用，其他模型可选配置作为备用。

---

