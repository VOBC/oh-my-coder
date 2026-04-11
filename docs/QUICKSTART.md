# 如何使用 Oh My Coder

> 5 分钟快速入门指南

---

## 🚀 5 分钟速览

**Oh My Coder** 是一个**多智能体 AI 编程助手**，通过多个专业 Agent 协作完成编程任务。

**核心优势：**
- 🤖 21 个专业 Agent，分工协作
- 💰 成本极低（DeepSeek 免费额度）
- 🇨🇳 中文友好，本土化设计

**只需 3 步，5 分钟上手！**

---

## 第一步：安装（1 分钟）

### 环境要求

- Python 3.10+
- DeepSeek API Key（免费注册）

### 安装步骤

```bash
# 克隆项目
git clone <项目地址>
cd oh-my-coder

# 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # Mac/Linux
# venv\Scripts\activate     # Windows

# 安装依赖
pip install -r requirements.txt
```

### 注册 DeepSeek（1 分钟）

1. 访问 [platform.deepseek.com](https://platform.deepseek.com/)
2. 注册账号（手机号即可）
3. 点击「API Keys」→「创建 API Key」
4. 复制 Key备用

---

## 第二步：配置（1 分钟）

### 设置 API Key

```bash
# 方式 1：环境变量（推荐）
export DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxx

# 方式 2：创建配置文件
echo "DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxx" > .env
```

### 验证安装

```bash
# 查看所有可用 Agent
python -m src.cli agents
```

**预期输出：**
```
┏━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┓
┃ 名称      ┃ 描述                            ┃ 层级   ┃
┡━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━┩
│ explore   │ 代码库探索智能体                │ low    │
│ analyst   │ 需求分析智能体                  │ high   │
│ architect │ 架构师智能体                    │ high   │
│ executor  │ 执行者智能体                    │ medium │
│ ...       │ (共 21 个 Agent)               │        │
└───────────┴────────────────────────────────┴────────┘
```

---

## 第三步：运行第一个任务（2 分钟）

### 启动演示

```bash
python demo.py
```

**完整演示流程：**

```
╔════════════════════════════════════════════════════════════════════╗
║                    🎯 Oh My Coder 演示                     ║
║               多智能体协作 - Explore → Analyst → Executor      ║
╚════════════════════════════════════════════════════════════════════╝

✅ Oh My Coder 初始化成功!

🚀 开始执行多智能体工作流

📌 步骤 1/3: Explore Agent - 探索代码库结构
✅ Explore Agent 执行成功!

📌 步骤 2/3: Analyst Agent - 分析需求
✅ Analyst Agent 执行成功!

📌 步骤 3/3: Executor Agent - 生成代码
✅ Executor Agent 执行成功!

💾 代码已保存到: todo_demo.py

📊 执行统计
   总请求数: 3
   提供商: DeepSeek 100%

🎉 演示完成!
```

### 体验效果

演示任务：开发一个待办事项 CLI 应用

**生成的代码包含：**
- `todo.py` - 主程序
- 数据存储逻辑
- 完整的增删改查功能
- 单元测试

### 运行生成的应用

```bash
# 添加任务
python todo_demo.py add "买牛奶"

# 查看任务
python todo_demo.py list

# 完成任务
python todo_demo.py done 1
```

---

## 进阶使用（1 分钟）

### 使用 CLI 工具

```bash
# 查看系统状态
python -m src.cli status

# 列出所有 Agent
python -m src.cli agents

# 执行自定义任务
python -m src.cli run "实现一个用户登录系统"
```

### 指定工作流

```bash
# 代码审查
python -m src.cli run "审查代码" -w review

# 调试问题
python -m src.cli run "修复登录 Bug" -w debug
```

---

## 原理解析

### 为什么这么快？

传统方式：
```
用户 → 写代码 → 调试 → 重写 → 测试 → 完成
```

Oh My Coder 方式：
```
用户 → Agent 协作 → 完成
         ↓
    Explore（探索）
         ↓
    Analyst（分析）
         ↓
    Executor（实现）
```

### 三层模型路由

| 层级 | Agent | 成本 | 使用场景 |
|------|-------|------|---------|
| **LOW** | explore, writer | 极低 | 简单任务 |
| **MEDIUM** | executor, debugger | 中等 | 代码实现 |
| **HIGH** | analyst, architect | 较高 | 架构设计 |

**智能选择**：系统根据任务复杂度自动选择最合适的层级。

---

## 21 个 Agent 全览

### Build/Analysis Lane（构建分析）

| Agent | 功能 | 层级 |
|-------|------|------|
| explore | 代码库探索 | LOW |
| analyst | 需求分析 | HIGH |
| planner | 任务规划 | HIGH |
| architect | 架构设计 | HIGH |
| executor | 代码实现 | MEDIUM |
| verifier | 功能验证 | MEDIUM |
| debugger | Bug调试 | MEDIUM |
| tracer | 因果追踪 | MEDIUM |

### Review Lane（审查）

| Agent | 功能 | 层级 |
|-------|------|------|
| code-reviewer | 代码审查 | HIGH |
| security-reviewer | 安全审查 | HIGH |

### Domain Lane（领域）

| Agent | 功能 | 层级 |
|-------|------|------|
| test-engineer | 测试设计 | MEDIUM |
| designer | UI/UX设计 | MEDIUM |
| writer | 文档编写 | LOW |
| git-master | Git操作 | MEDIUM |
| code-simplifier | 代码简化 | HIGH |
| scientist | 数据分析 | MEDIUM |
| qa-tester | QA测试 | MEDIUM |

### Coordination Lane（协调）

| Agent | 功能 | 层级 |
|-------|------|------|
| critic | 计划审查 | HIGH |

---

## 常见问题

### Q: API Key 多少钱？

**A:** DeepSeek 每天 4000 万 token 免费额度，日常使用几乎免费。

### Q: 支持其他模型吗？

**A:** 支持 DeepSeek、文心一言、通义千问，默认使用 DeepSeek。

### Q: 代码安全吗？

**A:** 代码完全本地运行，API Key 仅用于模型调用。

### Q: 能生成什么类型的代码？

**A:** Python、JavaScript、TypeScript、Go、Java 等主流语言。

---

## 下一步

- 📖 阅读 [README.md](../README.md) 了解完整功能
- 🧪 运行 [demo.py](../demo.py) 体验完整流程
- 🔧 查看 [贡献指南](../CONTRIBUTING.md) 参与开发
- 📝 阅读 [架构文档](ARCHITECTURE.md) 深入理解

---

## 结语

> Oh My Coder 将复杂的编程任务分解为多个专业 Agent 的协作，
> 通过智能路由选择最合适的模型，实现高效、低成本的代码生成。

**立即开始，让 AI 帮你写代码！**

---

*如果觉得好用，欢迎 Star ⭐ 和分享！*
