# 免费模型推荐

> 零成本开始 AI 编程之旅

## 免费额度详情

⚠️ **注意**：以下免费额度信息需要实际验证，建议直接访问各平台官网确认最新政策。

## 详细说明

### 1. DeepSeek（强烈推荐）⭐⭐⭐⭐⭐

**状态**: Production Ready ✅

**特点**:
- 提供免费额度（请访问官网确认最新政策）
- 响应速度快
- 代码能力强
- 支持函数调用

**配置方法**:

```bash
# 设置 API Key
omc config set -k DEEPSEEK_API_KEY -v "your_api_key"

# 设置为默认模型
omc config set -k DEFAULT_MODEL -v "deepseek"
```

**获取 API Key**: [DeepSeek 开放平台](https://platform.deepseek.com/)

---

### 2. MiMo（小米大模型）⭐⭐⭐⭐

**状态**: Production Ready ✅

**特点**:
- 提供免费额度（请访问官网确认最新政策）
- 长上下文支持
- 支持长文本处理

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

### 3. 智谱 GLM ⭐⭐⭐⭐

**状态**: Production Ready ✅

**特点**:
- 提供免费额度（请访问官网确认最新政策）
- 中文优化
- 智谱搬家计划（针对 Claude 用户）

**配置方法**:

```bash
# 免费版本（无需 Key）
omc config set -k GLM_API_KEY -v "free"

# 或使用智谱 API Key
omc config set -k GLM_API_KEY -v "your_api_key"

# 设置为默认模型
omc config set -k DEFAULT_MODEL -v "glm"
```

**获取 API Key**: [智谱 AI 开放平台](https://open.bigmodel.cn/)

**特别说明**: 智谱已推出"Claude 用户搬家计划"，新用户赠送一定额度 Tokens。

---

## 快速开始

### 1. 选择最适合你的模型

```bash
# 如果你是新用户，推荐 DeepSeek
omc config set -k DEEPSEEK_API_KEY -v "your_key"
omc config set -k DEFAULT_MODEL -v "deepseek"

# 如果需要大上下文，选择 MiMo
omc config set -k MIMOX_API_KEY -v "your_key"
omc config set -k DEFAULT_MODEL -v "mimo"

# 如果主要处理中文，选择 GLM
omc config set -k GLM_API_KEY -v "free"
omc config set -k DEFAULT_MODEL -v "glm"
```

### 2. 验证配置

```bash
omc run "你好，介绍一下你自己"
```

### 3. 开始编程

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

| 特性 | DeepSeek V3.2 | MiMo | GLM-4.7-Flash |
|------|---------------|------|---------------|
| **免费额度** | 新用户赠送（注册即得） | 注册赠送（详见官网） | **完全免费** |
| **上下文长度** | **128K** | 长上下文（官网确认） | **200K** |
| **中文能力** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **代码能力** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **响应速度** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **函数调用** | ✅ | ✅ | ✅ |

---

## 常见问题

### Q: 我应该选择哪个模型？

**A**: 
- **零成本首选**: 智谱 GLM-4.7-Flash（**完全免费**，200K 上下文，中文优化）
- **日常开发**: DeepSeek V3.2（代码能力强，128K 上下文，新用户有赠送额度）
- **大文件处理**: MiMo（长上下文，请访问官网确认具体参数）

💡 **推荐策略**：先用 GLM-4.7-Flash（完全免费），不够再切换 DeepSeek

### Q: 免费额度用完了怎么办？

**A**: 
1. 换一个模型继续使用
2. 等待下个月额度重置
3. 使用 MiMo（完全免费）

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
