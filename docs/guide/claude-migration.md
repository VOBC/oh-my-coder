# Claude Code → oh-my-coder 迁移指南

> 2026年4月15日更新 | 针对 Claude 封号事件

## 📰 事件背景

2026年4月14日，Claude 官方强制实名认证：
- 必须实体证件（护照/驾照/身份证原件）+ 人脸核验
- 明确写着"从不支持的地区注册，账号直接封"
- 中国大陆用户即使验证完也封号

这意味着 **Claude Code 对中国大陆用户基本不可用**。

## 🎯 为什么选择 oh-my-coder？

oh-my-coder 是 Claude Code 的**最佳国产开源替代方案**：

| 对比项 | Claude Code | oh-my-coder |
|--------|-------------|-------------|
| **模型** | 仅 Claude（需翻墙） | **12个国产模型**（GLM-4.7-Flash 完全免费） |
| **价格** | 需 Claude Pro ($25/月) | **完全免费开源** |
| **数据隐私** | 上传到海外服务器 | **本地处理，不上传** |
| **中国用户** | 封号风险高 | **完全支持** |
| **Agent数量** | 约10个 | **31个专业Agent** |
| **开源** | 闭源 | **MIT开源协议** |

## 🚀 快速迁移步骤

### 第1步：安装 oh-my-coder

```bash
# 方法1：pip安装（推荐）
pip install oh-my-coder

# 方法2：源码安装
git clone https://github.com/VOBC/oh-my-coder.git
cd oh-my-coder
pip install -e .
```

### 第2步：配置免费模型

```bash
# 使用 GLM-4.7-Flash（需注册获取 API Key，有免费额度）
omc config set -k GLM_API_KEY -v "your_key"  # https://open.bigmodel.cn/

# 或者使用其他国产模型（有免费额度）
omc config set -k DEEPSEEK_API_KEY -v "你的DeepSeek API Key"
omc config set -k QWEN_API_KEY -v "你的通义千问 API Key"
```

### 第3步：验证安装

```bash
omc run "你好，介绍一下你自己"
```

如果看到类似下面的输出，说明安装成功：
```
🤖 Oh My Coder 已启动！
支持 12 个国产大模型，31 个专业 Agent...
```

## 🔄 功能映射表

| Claude Code 功能 | oh-my-coder 对应功能 | 命令示例 |
|-----------------|---------------------|----------|
| `claude code explain` | `omc run` + `--workflow explore` | `omc run "解释这段代码" --workflow explore --file main.py` |
| `claude code refactor` | `omc run` + `--workflow build` | `omc run "重构这个函数" --workflow build --file utils.py` |
| `claude code debug` | `omc run` + `--workflow debug` | `omc run "调试这个错误" --workflow debug --file buggy.py` |
| `claude code review` | `omc run` + `--workflow review` | `omc run "审查代码质量" --workflow review --file api.py` |
| `claude code test` | `omc run` + `--workflow test` | `omc run "生成单元测试" --workflow test --file service.py` |
| `claude code autopilot` | `omc run` + `--workflow autopilot` | `omc run "自动完成这个功能" --workflow autopilot` |
| `claude code pair` | `omc run` + `--workflow pair` | `omc run "结对编程实现登录功能" --workflow pair` |

## 🧠 智谱 GLM 搬家计划对接

**好消息**：智谱 AI 已推出"Claude API 用户特别搬家计划"：

### 智谱搬家计划权益
- **新用户**：赠送 2000 万 Tokens 免费体验
- **API 兼容**：全面兼容 Claude 协议，只需替换 API URL
- **无缝切换**：从 Claude 无缝切换至 GLM 模型 API

### oh-my-coder 如何对接

oh-my-coder **原生支持 GLM 模型**，对接智谱搬家计划非常简单：

1. **注册智谱 GLM API**：访问 [智谱AI开放平台](https://open.bigmodel.cn/)
2. **获取 API Key**：在控制台创建应用，获取 API Key
3. **配置 oh-my-coder**：
   ```bash
   omc config set -k GLM_API_KEY -v "你的智谱 API Key"
   ```

4. **开始使用**：所有 Claude Code 的功能都可以用 GLM 模型实现

### GLM-4.7-Flash 免费额度

即使不注册智谱 API，也可以使用 **GLM-4.7-Flash 的免费版本**：

```bash
omc config set -k GLM_API_KEY -v "your_key"  # https://open.bigmodel.cn/
```

这个免费版本：
- **完全免费**：无需注册，无需 API Key
- **性能接近 Claude 3.5**：代码生成能力强
- **适合个人使用**：日常开发足够用

## 📋 迁移检查清单

### ✅ 已完成
- [ ] 安装 oh-my-coder
- [ ] 配置 GLM 免费模型或智谱 API Key
- [ ] 验证基本功能可用

### 🔄 工作流迁移
- [ ] 将 `claude code explain` 改为 `omc run --workflow explore`
- [ ] 将 `claude code refactor` 改为 `omc run --workflow build`
- [ ] 将 `claude code debug` 改为 `omc run --workflow debug`
- [ ] 将 `claude code review` 改为 `omc run --workflow review`
- [ ] 将 `claude code test` 改为 `omc run --workflow test`

### 🎯 高级功能
- [ ] 尝试 Quest Mode（异步自主编程）：`omc quest "重构整个项目"`
- [ ] 使用分层记忆系统：自动记住你的编码习惯
- [ ] 配置多平台 Gateway：支持 Telegram、微信等通知

## 🎬 迁移示例

### 示例1：解释代码
**Claude Code**:
```bash
claude code explain main.py
```

**oh-my-coder**:
```bash
omc run "解释 main.py 的架构和功能" --workflow explore --file main.py
```

### 示例2：重构函数
**Claude Code**:
```bash
claude code refactor "提高这个函数的可读性" --file utils.py
```

**oh-my-coder**:
```bash
omc run "重构 utils.py，提高可读性和性能" --workflow build --file utils.py
```

### 示例3：调试错误
**Claude Code**:
```bash
claude code debug "这个函数报错：TypeError" --file buggy.py
```

**oh-my-coder**:
```bash
omc run "调试 buggy.py 中的 TypeError" --workflow debug --file buggy.py
```

## ❓ 常见问题

### Q1: oh-my-coder 和 Claude Code 有什么区别？
**A**: 主要区别：
1. **模型**：Claude Code 只能用 Claude，oh-my-coder 支持 12 个国产模型
2. **价格**：Claude Code 需 Claude Pro ($25/月)，oh-my-coder 完全免费
3. **数据隐私**：Claude Code 数据上传海外，oh-my-coder 本地处理
4. **中国用户**：Claude Code 封号风险高，oh-my-coder 完全支持

### Q2: GLM-4.7-Flash 免费版有限制吗？
**A**: 免费版适合个人日常开发使用。如果需要更高并发或企业级服务，建议注册智谱 API 获取更多额度。

### Q3: 迁移后我的工作流需要大改吗？
**A**: 不需要大改。主要变化是命令格式，功能基本对应。参考上面的"功能映射表"。

### Q4: oh-my-coder 支持哪些 IDE？
**A**: 目前主要是命令行工具。VS Code 插件正在开发中，预计近期发布。

### Q5: 如何获取技术支持？
**A**: 
- **GitHub Issues**: https://github.com/VOBC/oh-my-coder/issues
- **Discussions**: https://github.com/VOBC/oh-my-coder/discussions
- **文档**: https://github.com/VOBC/oh-my-coder#readme

## 🛠️ 故障排除

### 问题1: `omc config set` 命令不生效
**症状**: 配置了API Key但运行任务时提示"未配置模型"
**解决**:
```bash
# 方法1: 检查配置是否保存
omc config show

# 方法2: 直接设置环境变量
export GLM_API_KEY=your_key  # https://open.bigmodel.cn/
omc run "测试"  # 临时生效

# 方法3: 编辑 .env 文件
echo 'GLM_API_KEY=your_key' >> .env  # https://open.bigmodel.cn/
```

### 问题2: 安装失败（pip install oh-my-coder 报错）
**解决**:
```bash
# 方法1: 使用国内镜像
pip install oh-my-coder -i https://pypi.tuna.tsinghua.edu.cn/simple

# 方法2: 源码安装（推荐）
git clone https://github.com/VOBC/oh-my-coder.git
cd oh-my-coder
pip install -e .
```

### 问题3: 运行速度慢
**解决**:
```bash
# 使用更快的模型（DeepSeek响应最快）
omc config set -k DEFAULT_MODEL -v "deepseek"

# 或者指定模型运行
omc run "任务" --model deepseek
```

### 问题4: 中文支持问题
**解决**:
```bash
# 使用中文优化模型（GLM/通义千问）
omc config set -k DEFAULT_MODEL -v "glm"
omc run "任务" --model qwen
```

## 📈 性能对比

根据用户反馈，oh-my-coder + GLM-4.7-Flash 在以下场景表现优秀：

| 场景 | Claude Code | oh-my-coder + GLM-4.7-Flash |
|------|-------------|-----------------------------|
| 代码解释 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| 代码重构 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| 调试 | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| 测试生成 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| 中文交互 | ⭐⭐ | ⭐⭐⭐⭐⭐ |

**注**：GLM-4.7-Flash 在中文理解和国产框架支持方面有优势。

## 🎯 最后建议

1. **先试用免费版（需注册获取 API Key）**：用 `omc config set -k GLM_API_KEY -v "your_key"` 先体验
2. **逐步迁移**：从简单的解释、重构开始，逐步适应新工具
3. **反馈问题**：遇到问题及时在 GitHub Issues 反馈，我们会快速修复

## 🔗 相关链接

- **oh-my-coder GitHub**: https://github.com/VOBC/oh-my-coder
- **智谱 AI 开放平台**: https://open.bigmodel.cn/
- **Claude 封号新闻**: [难搞!Claude开始搞AI实名制了,国内用户可咋办](https://new.qq.com/rain/a/20260415A06C6F00)
- **智谱搬家计划**: [智谱AI开放平台](https://open.bigmodel.cn/) - 查看"Claude用户特别搬家计划"公告

---

**更新日志**：
- 2026-04-15：创建文档，针对 Claude 封号事件
- 2026-04-15：添加智谱搬家计划对接说明
- 2026-04-15：添加 GLM-4.7-Flash 免费版配置

**作者**：oh-my-coder 团队  
**声明**：本文档与智谱 AI 无商业合作关系，仅为技术迁移指南