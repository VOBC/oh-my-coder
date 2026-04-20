# 免费模型推荐

> 零成本开始 AI 编程之旅

## 免费额度详情

> 📊 数据来源：各平台官方文档（2026-04-20）

## 详细说明

### 1. DeepSeek V3.2（强烈推荐）⭐⭐⭐⭐⭐

**状态**: Production Ready ✅

**免费额度**: 新用户注册即获赠送余额（优先扣减，用完再扣充值）

**价格**（极低，赠送额度能用很久）:
- 输入（缓存命中）：**0.2 元/百万 tokens**
- 输入（缓存未命中）：**2 元/百万 tokens**
- 输出：**3 元/百万 tokens**

**规格**:
- 上下文：**128K**
- 最大输出：8K（非思考模式）/ 64K（思考模式）
- 函数调用：✅
- 思考模式：✅（deepseek-reasoner）

**特点**:
- 代码能力极强（开源模型 SOTA）
- 响应速度最快
- 价格极低，赠送余额够日常开发用很久

**配置方法**:

```bash
# 设置 API Key
omc config set -k DEEPSEEK_API_KEY -v "your_api_key"

# 设置为默认模型
omc config set -k DEFAULT_MODEL -v "deepseek"
```

**获取 API Key**: [DeepSeek 开放平台](https://platform.deepseek.com/)（注册即送余额）

---

### 2. 智谱 GLM-4.7-Flash（零成本首选）⭐⭐⭐⭐⭐

**状态**: Production Ready ✅

**免费额度**: **完全免费，无限使用**

**规格**:
- 上下文：**200K**
- 最大输出：**128K**
- 模型规模：30B 参数
- 函数调用：✅
- 思考模式：✅
- MCP 工具调用：✅
- 上下文缓存：✅

**特点**:
- **完全免费**，零成本起步
- 中文能力最强（智谱专注中文优化）
- 上下文最长（200K）
- Agentic Coding 场景强化

**配置方法**:

```bash
# 免费版本（无需 API Key）
omc config set -k GLM_API_KEY -v "free"

# 设置为默认模型
omc config set -k DEFAULT_MODEL -v "glm"
```

**获取 API Key**: [智谱 AI 开放平台](https://open.bigmodel.cn/)（免费模型无需付费）

---

### 3. 小米 MiMo ⭐⭐⭐⭐

**状态**: Production Ready ✅

**免费额度**: 新用户免费一周体验活动

**特点**:
- 小米出品（MiMo-V2 系列，309B 总参数 / 15B 激活参数）
- 长上下文支持
- 开源模型（MIT 协议）

**配置方法**:

```bash
# 设置 API Key
omc config set -k MIMOX_API_KEY -v "your_api_key"

# 设置为默认模型
omc config set -k DEFAULT_MODEL -v "mimo"
```

**获取 API Key**: [小米开放平台](https://platform.ai.xiaomi.com/)

**适用场景**:
- 长代码文件分析
- 大型项目理解
- 文档处理

---

## 快速开始

### 推荐策略

```bash
# 方案 A：零成本（推荐新手）
omc config set -k GLM_API_KEY -v "free"
omc config set -k DEFAULT_MODEL -v "glm"

# 方案 B：代码能力强（推荐开发者）
omc config set -k DEEPSEEK_API_KEY -v "your_key"
omc config set -k DEFAULT_MODEL -v "deepseek"

# 方案 C：大文件处理
omc config set -k MIMOX_API_KEY -v "your_key"
omc config set -k DEFAULT_MODEL -v "mimo"
```

### 验证配置

```bash
omc run "你好，介绍一下你自己"
```

### 开始编程

```bash
# 代码解释
omc run "解释这段代码" --workflow explore --file main.py

# 代码重构
omc run "重构这个函数" --workflow build --file utils.py

# Bug 修复
omc run "修复这个错误" --workflow debug --file buggy.py
```

---

## 模型对比

| 特性 | DeepSeek V3.2 | GLM-4.7-Flash | MiMo |
|------|---------------|---------------|------|
| **免费额度** | 新用户赠送余额 | **完全免费** | 免费一周 |
| **上下文长度** | **128K** | **200K** | 长上下文 |
| **最大输出** | 8K / 64K | **128K** | - |
| **输入价格** | 0.2~2 元/百万 tokens | **0 元** | 免费（活动期）|
| **输出价格** | 3 元/百万 tokens | **0 元** | 免费（活动期）|
| **中文能力** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **代码能力** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **响应速度** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **函数调用** | ✅ | ✅ | ✅ |

---

## 常见问题

### Q: 我应该选择哪个模型？

**A**: 
- **零成本首选**: 智谱 GLM-4.7-Flash（**完全免费**，200K 上下文，中文优化最强）
- **代码能力首选**: DeepSeek V3.2（代码 SOTA，128K 上下文，新用户赠送余额，输入仅 0.2~2 元/百万 tokens）
- **大文件处理**: 小米 MiMo（免费一周活动，长上下文）

💡 **推荐策略**：先用 GLM-4.7-Flash（完全免费，不用注册），需要更强代码能力时切换 DeepSeek

### Q: 免费额度用完了怎么办？

**A**: 
1. 切换到 GLM-4.7-Flash（完全免费，无限用）
2. DeepSeek 充值（价格极低，2 元/百万 tokens 够用很久）
3. 注册小米 MiMo 账号获取免费一周

### Q: 可以同时配置多个模型吗？

**A**: 可以。`DEFAULT_MODEL` 设置首选，任务中可用 `--model` 指定其他模型：

```bash
omc run "任务" --model glm
```

---

## 相关文档

- [模型配置](model-config.md)
- [模型列表](models.md)
- [Claude 迁移指南](claude-migration.md)
