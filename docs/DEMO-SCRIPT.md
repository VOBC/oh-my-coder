# Oh My Coder Demo 脚本

> 版本：v0.1.0 | 目标时长：3 分钟 | 适合观众：开发者、潜在用户

---

## 场景 1：开场介绍（30 秒）

**画面**：标题卡（深色背景，Oh My Coder 大字）

**配音/字幕**：

> 👋 大家好，今天给大家介绍一款完全开源的多智能体 AI 编程助手——**Oh My Coder**。
>
> 它基于国产大模型，支持 GLM-4-Flash（永久免费），内置 31 个专业 Agent，
> 可以帮你自动写代码、跑测试、做代码审查。

**画面停留：2 秒**

**转场**：淡入下一场景

---

## 场景 2：安装（30 秒）

**画面**：终端窗口，显示 pip install 过程

```
$ pip install oh-my-coder

  Collecting oh-my-coder
    Downloading oh-my-coder-0.1.0-py3-none-any.whl
  Installing collected packages: oh-my-coder
  Successfully installed oh-my-coder 0.1.0

$ omc --version
  oh-my-coder 0.1.0
```

**配音/字幕**：

> 安装只需一行命令。pip install 搞定，支持 macOS、Windows、Linux。
> 如果你想用开发版，git clone 源码，pip install -e . 即可。

**画面停留：28 秒**

**转场**：淡入下一场景

---

## 场景 3：配置（30 秒）

**画面**：终端窗口，显示 omc config show 和 omc config set

```
$ omc config show

  当前配置:
  GLM_API_KEY:           未设置
  DEFAULT_MODEL:         glm-4-flash

$ omc config set -k GLM_API_KEY \
         -v "your-key-from-open.bigmodel.cn"
  ✅ 已保存到 ~/.omc/config.json
```

**配音/字幕**：

> 首次使用需要配置一个 API Key。去智谱 AI 开放平台注册，完全免费。
> 用 config set 命令指定 Key，GLM-4-Flash 永久免费，无需付费。

**画面停留：28 秒**

**转场**：淡入下一场景

---

## 场景 4：Agent 系统（30 秒）

**画面**：终端窗口，显示 omc agents 输出

```
$ omc agents

  🤖 Oh My Coder — 31 个专业 Agent

  构建/分析通道
  ├── ExplorerAgent       探索代码库，生成项目地图
  ├── AnalystAgent        分析需求，发现隐藏约束
  ├── PlannerAgent        制定执行计划
  ├── ArchitectAgent       设计系统架构
  ├── ExecutorAgent       生成代码（14 种语言）
  ├── VerifierAgent       运行测试，验证正确性

  审查通道
  ├── CodeReviewerAgent      代码质量审查
  └── SecurityReviewerAgent  安全漏洞扫描

  领域通道（16 个）
  Vision · Document · TestEngineer · Designer ·
  Scientist · GitMaster · Database · API · DevOps ...

  协调通道
  └── SelfImprovingAgent   主动学习优化路由
```

**配音/字幕**：

> Oh My Coder 内置 31 个专业 Agent，分成四类通道：
> 构建分析通道负责理解需求和生成代码；
> 审查通道做质量把关；
> 14 个领域 Agent 覆盖前端、数据库、安全等专门场景；
> 协调 Agent 负责动态路由，持续优化任务分配。

**画面停留：28 秒**

**转场**：淡入下一场景

---

## 场景 5：运行演示（60 秒）

**画面**：终端窗口，完整展示 omc run 执行流程

```
$ omc run "实现一个 REST API"

  🤖 [Explorer]   扫描项目结构...
             ✅   找到 12 个文件，3 个目录

  🤖 [Analyst]    理解需求约束...
             ✅   识别 5 个实体，2 个 API 端点

  🤖 [Planner]    制定执行计划...
             ✅   8 步计划，预计 45s

  🤖 [Architect]  设计 API 架构...
             ✅   RESTful，Flask + SQLAlchemy

  🤖 [Executor]   生成代码...
             ✅   src/api/rest.py (42 行)
             ✅   src/models/user.py (28 行)
             ✅   src/models/order.py (35 行)

  🤖 [Verifier]   运行测试...
             ✅   pytest 18/18 passed

  ✨ 完成！        生成 6 个文件，耗时 38.2s
  💰 成本: ¥0.03  ·  🔢 Token: 24,500
```

**配音/字幕**：

> 输入一个自然语言任务，比如"实现一个 REST API"。
> 多 Agent 协作自动完成：探索项目结构，分析需求，制定计划，设计架构，
> 生成代码，最后运行测试验证。生成 6 个文件，耗时不到 40 秒，成本只要 3 分钱。
> 如果代码有 Bug，Debugger Agent 会自动定位并修复。
> 想看 UI 界面？运行 omc web，一个浏览器窗口即可查看实时协作状态。

**画面停留：58 秒**

**转场**：淡入下一场景

---

## 场景 6：总结（30 秒）

**画面**：总结卡片，4 步快速上手 + GitHub 链接

```
快速上手

  1 安装        pip install oh-my-coder
  2 配置 Key    omc config set -k GLM_API_KEY -v "your-key"
  3 运行任务    omc run "你的任务描述"
  4 查看结果    ls src/

  📖 文档：github.com/VOBC/oh-my-coder
  ⭐ Star：github.com/VOBC/oh-my-coder
```

**配音/字幕**：

> 总结一下，4 行命令即可开始：
> 安装、配置 Key、输入任务、查看结果。
> 全部开源，MIT 协议，支持 12 个国产大模型。
> 欢迎 Star，欢迎贡献！
> GitHub 链接在视频描述栏。

---

## 技术备注

- **视频格式**：GIF（无声音），可在 README / 官网直接嵌入
- **如需带声音视频**：将 GIF 帧导出为图片，用 CapCut /剪映 + 配音合成
- **帧生成工具**：`scripts/gen_video.py`
- **帧率**：2fps，每场景 30 秒（60 帧 × 6 场景）
- **分辨率**：900 × 540 px

## 更新日志

| 日期 | 内容 |
|------|------|
| 2026-04-16 | 初始版本，6 场景 × 30s |
