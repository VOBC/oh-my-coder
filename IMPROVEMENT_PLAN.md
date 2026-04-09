# Oh-My-Coder 改进计划

> 基于 Qoder 对比分析及用户反馈整理
> 日期：2026-04-08

---

## 一、用户反馈中肯建议

### ✅ 需要改进的痛点

| 问题 | 现状 | 改进方向 |
|------|------|----------|
| CLI 体验割裂 | 纯命令行，无法边看边改 | 开发 VS Code 插件 / Web UI |
| 配置复杂 | 需手动配置 Python + API Key | 一键安装脚本 / Docker 镜像 |
| 文档不足 | 刚发布，文档不完善 | 完善文档，建立 Issue 模板 |
| 依赖免费政策 | 依赖 DeepSeek 免费额度 | 支持更多模型，增加本地模型 |

---

## 二、Qoder 值得借鉴的核心特性

### 1. Quest Mode（异步自主编程）⭐⭐⭐ 优先级最高

**Qoder 实现：**
```
开发者描述需求 → Agent 生成 Spec → 后台自主编码 → 开发者验收
```

**我们需要实现：**
```bash
# 用户发起任务
oh-my-coder quest "实现用户认证模块，支持 JWT + 刷新令牌"

# 系统生成 spec.md
# → 后台执行编码
# → 完成后通知验收
# → 用户确认或修改
```

**技术方案：**
1. 新增 `QuestAgent` 负责任务拆解和 Spec 生成
2. 后台执行队列（可用 Python 的 `asyncio` 或 `celery`）
3. 完成后通过通知机制（桌面通知 / 钉钉 / 飞书）告知用户

**工作量：** 中等（约 1-2 周）

---

### 2. Repo Wiki（项目知识库）⭐⭐⭐ 优先级最高

**Qoder 实现：**
- 自动解析代码库，生成结构化文档
- 减少模型"幻觉"，提升准确性
- 支持 10 万文件规模

**我们需要实现：**
```bash
# 生成项目 Wiki
oh-my-coder wiki generate

# 输出 REPO_WIKI.md，包含：
# - 项目结构
# - 模块依赖关系
# - 核心类/函数说明
# - API 文档
# - 测试覆盖情况
```

**技术方案：**
1. 使用 `ast` 模块解析 Python 代码结构
2. 使用 `tree-sitter` 支持多语言
3. 生成 Markdown 格式的 Wiki
4. 后续对话自动引用 Wiki 内容

**工作量：** 中等（约 1-2 周）

---

### 3. 长短期记忆系统 ⭐⭐ 优先级中

**Qoder 实现：**
- 短期记忆：当前会话上下文
- 长期记忆：项目偏好、常用模式、踩坑记录
- 自我学习和进化

**我们需要实现：**
```
~/.oh-my-coder/
  memory/
    short-term/     # 当前会话
    long-term/      # 项目偏好、常用模式
    learnings/      # 踩坑记录、最佳实践
```

**技术方案：**
1. 参考 Claude Code 的三层记忆架构
2. 会话结束自动总结沉淀
3. 新会话自动召回相关记忆

**工作量：** 中等（约 1 周）

---

### 4. VS Code 插件 ⭐⭐⭐ 优先级最高

**现状：** 纯 CLI，体验割裂

**需要实现：**
- VS Code 扩展
- 侧边栏对话界面
- 代码内联建议
- 文件操作集成

**技术方案：**
1. 使用 VS Code Extension API
2. 集成现有 CLI 核心逻辑
3. WebSocket 通信

**工作量：** 大（约 3-4 周）

---

### 5. 一键安装 ⭐⭐ 优先级高

**现状：** 需手动配置 Python + API Key

**需要实现：**
```bash
# macOS/Linux
curl -fsSL https://raw.githubusercontent.com/vobc/oh-my-coder/main/install.sh | bash

# Windows
powershell -c "irm https://raw.githubusercontent.com/vobc/oh-my-coder/main/install.ps1 | iex"
```

**技术方案：**
1. 自动检测 Python 环境
2. 自动安装依赖
3. 交互式配置 API Key
4. 可选：Docker 镜像

**工作量：** 小（约 2-3 天）

---

## 三、改进优先级排序

| 优先级 | 改进项 | 工作量 | 影响 | 建议排期 |
|--------|--------|--------|------|----------|
| **P0** | 一键安装脚本 | 小 | 降低门槛 | 第 1 周 |
| **P0** | Repo Wiki | 中 | 提升准确性 | 第 2-3 周 |
| **P1** | Quest Mode | 中 | 差异化竞争力 | 第 3-4 周 |
| **P1** | 长短期记忆 | 中 | 体验一致性 | 第 4-5 周 |
| **P2** | VS Code 插件 | 大 | 解决最大痛点 | 第 5-8 周 |

---

## 四、我们的差异化优势（保持）

| 优势 | 说明 |
|------|------|
| **开源** | 社区可以贡献、定制、审计 |
| **完全免费** | 不依赖付费模型 |
| **轻量** | CLI 即可，无需 IDE |
| **可定制** | 用户可修改 Agent 配置 |

---

## 五、下一步行动

### 立即执行（本周）

1. **一键安装脚本**
   - [ ] 创建 `install.sh`（macOS/Linux）
   - [ ] 创建 `install.ps1`（Windows）
   - [ ] 测试安装流程

2. **Repo Wiki MVP**
   - [ ] 实现基础代码解析（Python）
   - [ ] 生成 Markdown 文档
   - [ ] 集成到 CLI

### 近期执行（下周）

3. **Quest Mode 设计**
   - [ ] 设计 Spec 格式
   - [ ] 实现任务队列
   - [ ] 实现验收流程

4. **长短期记忆系统**
   - [ ] 设计存储结构
   - [ ] 实现自动总结
   - [ ] 实现召回机制

### 中期执行（后续）

5. **VS Code 插件**
   - [ ] 搭建扩展框架
   - [ ] 实现对话界面
   - [ ] 集成 CLI 核心

---

## 六、参考链接

- Qoder 官网：https://qoder.ai
- Qoder 功能介绍：https://new.qq.com/rain/a/20250822A088HA00
- Claude Code 记忆架构：https://github.com/anthropics/claude-code

---

*本文档由小麦整理，2026-04-08*
