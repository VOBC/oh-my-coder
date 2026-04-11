# Oh My Coder - 智能编程助手

> 🤖 用 AI 团队帮你写代码

---

## 🌟 一句话介绍

Oh My Coder 是一个**多智能体 AI 编程助手**，通过多个专业 Agent 协作，像指挥真实工程团队一样完成复杂开发任务。支持 DeepSeek、文心一言、通义千问等国内主流大模型，**零成本即可使用**。

---

## ✨ 核心能力

### 🤖 智能团队协作

系统内置 **21 个专业 Agent**，覆盖开发全流程：

- 🔍 **探索** → 🧠 **分析** → 🏗️ **设计** → 💻 **实现** → ✅ **验证**

每个 Agent 各司其职：代码探索、需求分析、架构设计、代码实现、测试验证……就像有一个完整的工程团队在为你工作。

### 🧠 智能路由，省钱 50%

传统方案：用最贵的模型处理所有任务，成本高。

Oh My Coder：根据任务类型自动选择最优模型：
- 简单探索 → 用 **LOW tier**（便宜）
- 代码实现 → 用 **MEDIUM tier**（平衡）
- 架构设计 → 用 **HIGH tier**（高质量）

实测节省 **30-50% Token**，且优先使用 DeepSeek 免费额度，**几乎零成本**。

### 🌐 开箱即用的 Web 界面

```bash
python -m src.web.app
# 浏览器打开 http://localhost:8000
```

可视化 Agent 工作流水线，SSE 实时推送执行进度，深色/浅色主题一键切换。

### 🇨🇳 中文优化，本土首选

- 全中文注释和文档
- 支持 DeepSeek / 文心一言 / 通义千问 / GLM / MiniMax / Kimi 等国内模型
- 无需代理，直接调用

---

## 🚀 快速开始

### 安装（30 秒）

```bash
git clone https://github.com/VOBC/oh-my-coder.git
cd oh-my-coder
pip install -r requirements.txt
```

### 配置 API Key

```bash
export DEEPSEEK_API_KEY=your_key_here  # 推荐，免费额度高
```

### 运行

```bash
# 🌐 Web 界面（推荐）
python -m src.web.app

# 💻 命令行
python -m src.cli run "实现一个用户认证系统"

# 🔌 API
python -m uvicorn src.main:app --reload
```

---

## 💡 适用场景

| 场景 | 效果 |
|------|------|
| **新项目启动** | 输入需求，Agent 团队自动完成从设计到实现的完整流程 |
| **代码审查** | 自动扫描代码质量和安全漏洞，给出改进建议 |
| **Bug 调试** | 智能定位根因，提供修复方案 |
| **快速原型** | 输入想法，几分钟生成可运行代码 |

---

## 📊 技术栈

- **Python 3.9+**，异步优先
- **FastAPI** Web 界面 + SSE 实时推送
- **21 个专业 Agent**，覆盖全开发流程
- **9 个模型适配器**，支持主流 LLM
- **43 个测试用例**，质量有保障

---

## ⭐ 支持我们

- 给项目点个 ⭐
- 分享给需要的朋友
- 提交 Issue 和 PR
- 成为赞助商

---

**仓库地址**：https://github.com/VOBC/oh-my-coder

**开源协议**：MIT License
