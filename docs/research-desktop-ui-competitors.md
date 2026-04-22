# AI 编程工具桌面端 / Terminal UI 设计调研报告

> 调研时间：2026-04-21
> 调研范围：OpenCode / Cursor / Windsurf / Claude Code / Aider / Cline / Roo Code / Crush
> 报告目标：为 Oh My Coder Desktop 提供 UI/UX 改进参考

---

## 1. Executive Summary

**一句话结论：** 当前主流 AI 编程工具的 UI 分化为两个流派——以 Cursor/Windsurf 为代表的"IDE 内嵌 AI 面板"（侧边栏对话+内联 diff）和以 OpenCode/Crush/Aider 为代表的"Terminal TUI"（全屏终端交互）；最值得借鉴的桌面设计是 Cursor 的 Cmd+K/Cmd+L 双入口模式 + Windsurf 的 Cascade Flow 概念，而 OpenCode 的 Bubble Tea TUI + MCP 生态是最接近 Oh My Coder 的参考实现，Oh My Coder Desktop 应重点参考 OpenCode 的命令行 UX 和 Cursor 的可视化交互模式，走"Terminal TUI + 轻量桌面壳"的差异化路线。

---

## 2. 逐产品详细分析

---

### 2.1 OpenCode (anomalyco → charmbracelet/crush)

**官方链接：** https://opencode.ai | https://github.com/charmbracelet/crush

**产品定位：** 原 OpenCode 项目已迁移并重命名为 **Crush**，由 terminal.shop 团队和 Charm 团队联合开发，基于 Go 语言，用 Bubble Tea 框架构建 TUI。

#### 整体布局

- **纯 Terminal TUI**，无桌面 GUI壳——全屏终端应用，Vim-like 编辑体验
- 主界面分为：
  - **消息区域（上部）：** 滚动显示对话历史，AI 回复带语法高亮和工具调用卡片
  - **编辑/输入区（底部）：** 类似 Vim 的多行编辑区，支持 `i` 进入编辑模式，`Esc` 切回消息浏览
  - **覆盖层/对话框：** Ctrl+K 命令面板、Ctrl+O 模型选择、Ctrl+A 会话切换，均以浮层形式覆盖
- **无侧边栏**，文件管理通过 `ls`/`glob`/`grep` 等工具命令实现，由 AI 代为执行
- Settings 通过 JSON 配置文件（`crush.json`）管理，也支持内置的 `crush-config` skill 让 AI 自配置

#### 视觉风格

- **Terminal 原生暗色**：Charm 风格，使用 Lip Gloss 渲染样式，色彩在 ANSI 24-bit 范围内
- **字体**：终端等宽字体（用户自定义）
- **配色**：Bubble Tea 组件自带渐变色标题栏（如粉色/蓝色渐变），消息区黑白为主，工具调用卡片带边框高亮
- **图标**：ASCII/Unicode 字符图标（如 ✓/✗/→），无外部图标依赖
- **动画**：打字机效果（逐字输出）+ spinner 加载动画，丝滑流畅
- **间距**：紧凑型，大量留白在对话气泡之间，按时间线排列

#### 关键交互

- **模型切换**：Ctrl+O 打开模型选择浮层，上下左右导航选择（类 VS Code 快捷键风格），支持切换 LLM 供应商（OpenAI/Anthropic/Gemini/Groq/OpenRouter/Vercel AI Gateway 等 20+）
- **API Key 配置**：首次启动引导式输入；支持环境变量（ANTHROPIC_API_KEY 等）；crush.json 中配置 providers
- **对话历史**：SQLite 本地持久化，自动 session 管理；Ctrl+A 切换会话，上下箭头导航历史
- **文件管理**：AI 通过工具（ls/globs/grep/write/edit）操作，无原生文件树；支持 LSP 增强代码理解
- **上下文注入**：`.crushignore` 文件类似 .gitignore，Agent Skills 支持（Skill 目录）

#### 桌面端特有

- **无原生桌面窗口**：纯 TUI，适合终端重度用户
- **快捷键体系**：类 Vim + 类 VS Code 快捷键融合（Ctrl+K 命令、Ctrl+O 模型、Ctrl+A 会话）
- **MCP 支持**：stdio / http / sse 三种传输方式，配置灵活
- **Agent Skills**：`~/.config/agents/skills/` + `.agen/` 目录发现 SKILL.md
- **--yolo 模式**：跳过所有工具执行确认，极速但危险

#### 亮点

1. **Bubble Tea TUI 美学标杆**：Charm 团队的 TUI 设计语言非常成熟，渐变标题栏、精心调校的色彩层次是 Oh My Coder 可以直接借鉴的
2. **Agent Skills 生态**：支持 SKILL.md 技能包复用，与 Oh My Coder 定位高度重合
3. **多供应商 + MCP 扩展**：crush-config skill 自配置、丰富的 provider 支持，是完美的工具链集成参考

#### 缺陷

1. **纯 TUI，无桌面 GUI**：对非终端用户有较高门槛，安装和首次配置体验不够友好
2. **无原生文件树/项目管理界面**：文件管理完全依赖 AI 工具调用，对习惯可视化操作的用户不够直观

---

### 2.2 Cursor

**官方链接：** https://cursor.com | https://github.com/getcursor/cursor

**产品定位：** AI 原生代码编辑器，fork VS Code，深度集成 AI 的桌面应用；2026年已有完整桌面端 UI。

#### 整体布局

- **IDE 布局（VS Code Fork）**：
  - **左侧活动栏**：文件管理器/搜索/Git/扩展/AI 功能入口（图标式）
  - **主编辑器区**：代码编辑 + 内联 diff 展示
  - **AI 面板（右侧/底部）**：Cmd+K（内联编辑）、Cmd+L（侧边对话），可拖拽分屏
- **Chat 面板（Cmd+L）**：右侧面板，滚动对话历史，支持 @ 文件/文档/代码库 引用
- **Composer（Cmd+I）**：结构化编程模式，拆解任务为子步骤
- **Notepad**：轻量临时笔记区
- **Settings**：Ctrl+Shift+J 打开，完整 VS Code 风格设置页（General/Rules/Editor/Privacy/Tab/Chat 等）

#### 视觉风格

- **暗色为主，官方主题**：深蓝/灰色背景，白色文字，蓝色高亮（VS Code 暗色风格）
- **字体**：用户自定义，编辑器默认 JetBrains Mono 或 Fira Code（支持连字）
- **AI 面板设计**：对话框气泡风格，AI 回复带 Markdown 渲染和代码高亮
- **图标**：VS Code 图标集（文件类型、活动栏图标）
- **间距**：IDE 标准间距，消息气泡间距适中
- **动画**：内联补全渐入、diff 视图平滑过渡

#### 关键交互

- **模型切换**：Settings > General > Account，可选内嵌订阅模式或自定义 API（支持 OpenAI/Anthropic/Gemini/xAI/Cursor 自有模型）；支持 Rules for AI（自定义行为规则）
- **API Key 配置**：Settings 页面 GUI 配置，支持 Custom API Endpoint
- **对话历史**：右侧面板滚动，消息按时间排列，支持引用特定消息
- **文件管理**：完整 VS Code 文件资源管理器，支持多标签、分屏、终端面板

#### 桌面端特有

- **macOS 标题栏交通灯**：标准 macOS 窗口控件（关闭/最小化/缩放），与 VS Code 一致
- **原生菜单栏**：完整的 macOS 菜单（文件/编辑/视图/终端/帮助等）
- **快捷键体系**：VS Code 快捷键继承（Cmd+P 文件跳转、Cmd+Shift+P 命令面板等），AI 专用快捷键（Cmd+K/Cmd+L/Cmd+I）
- **窗口管理**：VS Code 分屏/标签页体系完整继承，多工作区支持
- **隐私模式**：Privacy mode 可关闭遥测

#### 亮点

1. **双入口 AI 交互（Cmd+K + Cmd+L）**：内联编辑 + 侧边对话分离，体验极其流畅，Cursor 是这一范式的开创者
2. **Codebase Indexing**：完整理解代码库结构，聊天时自动检索相关文件上下文，无需手动 @ 大量文件
3. **Diff 可视化**：AI 修改直接以内联 diff 展示，用户逐块接受/拒绝，完全掌控感

#### 缺陷

1. **基于 VS Code Fork**：UI 定制受限于 VS Code 架构，个性化空间有限，内存占用较高
2. **订阅制依赖**：完整功能需要付费订阅，对团队/企业用户成本较高

---

### 2.3 Windsurf

**官方链接：** https://windsurf.com | https://windsurf.ai

**产品定位：** Codeium 推出的"首个 Agentic IDE"，fork VS Code，以 Cascade AI 和 Flow 概念为核心。

#### 整体布局

- **VS Code Fork 布局**：与 Cursor 高度相似的 IDE 布局
  - **左侧活动栏**：Explorer/Search/Git/Debug/Windsurf AI（Cascade）
  - **Cascade AI 面板**：主 AI 交互区，包含 Chat、Write Mode、Flow Actions
  - **Memories 面板**：记录对代码库的记忆，类似 RAG 知识库
  - **Rules 配置**：AI 行为规则（.windsurfrc）
- **Flow Actions**：将复杂任务分解为多步骤工作流，带进度指示
- **Supercomplete**：深度代码补全，类似 Copilot 但更激进

#### 视觉风格

- **暗色 IDE 风格**：深灰背景，蓝色主色调，与 VS Code/Cursor 高度一致
- **字体**：编辑器等宽字体
- **配色**：蓝色高亮 + 绿色（接受）/ 红色（拒绝）diff 提示
- **Flow 可视化**：任务步骤以卡片/列表形式展示，清晰直观
- **图标**：VS Code 图标体系

#### 关键交互

- **模型切换**：Settings > Account，订阅 Codeium Workspace 或配置自定义 API
- **API Key 配置**：GUI 设置页，支持自定义 Provider
- **对话历史**：Cascade 面板内滚动，带文件引用高亮
- **文件管理**：VS Code 文件树，支持工作区管理
- **Memories**：AI 记住关键代码结构和工作流偏好，类似持久化上下文

#### 亮点

1. **Memories 功能**：RAG 风格的代码库记忆机制，解决长会话上下文丢失问题
2. **Flow Actions**：将复杂任务拆解为可管理的步骤，用户可以看到 AI 的完整执行计划
3. **MCP Server 一键集成**：Settings 中直接浏览和配置 MCP 服务（Figma/Slack/Stripe 等），开箱即用

#### 缺陷

1. **与 Cursor 功能高度重叠**：没有足够差异化的 UX 创新，用户容易在两者间摇摆
2. **VS Code Fork 的包袱**：与 Cursor 面临相同的性能和定制化限制

---

### 2.4 Claude Code

**官方链接：** https://claude.ai/code

**产品定位：** Anthropic 官方 CLI 工具 + VS Code 扩展 + JetBrains 插件 + 桌面应用，五种运行环境。

#### 整体布局

- **CLI（TUI）模式**：
  - 全屏终端界面，打印模式输出（彩色进度、代码块高亮）
  - 命令面板通过 `/` 触发（`/search`/`/web-search`/`/lsp` 等）
  - permission 确认交互：工具执行前弹确认提示
- **VS Code 扩展模式**：
  - 侧边栏面板，聊天 + 命令入口
  - 内联编辑（Shift+Tab 切换模式）
  - 终端集成（VS Code v1.93+ Shell Integration）
- **桌面应用**：独立 Electron 窗口，完整 GUI 界面
- **Settings**：`.claude.json` 配置文件 + GUI 设置页

#### 视觉风格

- **暗色 Terminal 输出**：ASCII 表格、彩色状态指示（绿色成功/红色错误）
- **VS Code 扩展**：继承 VS Code 暗色主题
- **字体**：终端等宽字体（用户配置）
- **动画**：打字机输出 + ASCII 进度条
- **代码块**：语法高亮（ANSI 色彩或 Pygments 风格）

#### 关键交互

- **模型切换**：`/general-config` 命令 或 Settings GUI；支持环境变量 `ANTHROPIC_MODEL`
- **API Key 配置**：首次引导配置 + 环境变量（ANTHROPIC_API_KEY）+ Settings GUI；支持 Custom Endpoint
- **对话历史**：基于会话，JSON 文件持久化；`--save-session` 导出
- **文件管理**：CLI 下无文件树；VS Code 扩展模式下使用 VS Code 文件系统
- **模式切换**：Shift+Tab 在默认/ask/edit 模式间切换

#### 亮点

1. **五种运行环境**：Terminal/VS Code/JetBrains/Desktop/Web，适配所有用户习惯
2. **Permission 安全机制**：每步操作前确认，用户完全掌控，是"Human-in-the-loop"的最佳实践
3. **LSP 集成 + 深度代码理解**：Claude 的代码推理能力最强，IDE 扩展提供精确的代码库上下文

#### 缺陷

1. **国内访问限制**：Anthropic 官方服务在中国大陆不可用，需要第三方代理或 API 站点配置，学习成本高
2. **VS Code 扩展体验不如独立桌面应用**：依赖 VS Code 版本（需要 v1.93+ shell integration）

---

### 2.5 Aider

**官方链接：** https://aider.chat | https://github.com/Aider-AI/aider

**产品定位：** 最流行的开源 CLI AI 编程工具，Python 实现，Terminal 内配对编程，强调 Git 集成。

#### 整体布局

- **纯 Terminal 输出（无 TUI）**：非交互式命令行输出，逐行打印 AI 响应
- **无 GUI 界面**：所有交互在终端文本流中完成
- **工作方式**：`cd project && aider`，直接在代码库目录运行
- **输出格式**：Markdown 渲染的 AI 响应 + diff 输出 + git commit 记录
- **无侧边栏/无面板**：纯命令行体验

#### 视觉风格

- **Terminal 原生**：无自定义 UI，纯 ANSI 彩色输出
- **字体**：用户终端字体配置
- **配色**：基本的红/绿 diff 颜色 + Markdown ANSI 高亮
- **间距**：紧凑型，终端标准输出密度
- **动画**：无动画，纯文本流

#### 关键交互

- **模型切换**：`--model sonnet`/`--model deepseek` 命令行参数；`aider-install` 引导安装配置
- **API Key 配置**：环境变量（ANTHROPIC_API_KEY 等）或 `~/.aider.conf.yml` 配置文件；引导式设置
- **对话历史**：基于 git commit，自动生成 commit message；可通过 `--chat-mode` 选择交互模式
- **文件管理**：无原生文件树，通过 git 管理变更
- **--read-only 模式**：限制 AI 只读文件
- **Voice 输入**：支持语音输入（voice mode）

#### 亮点

1. **Git 深度集成**：每次变更自动 commit，git diff 可追溯，团队协作友好
2. **Repo Map**：代码库可视化地图，帮助 AI 理解大型项目结构
3. **多语言支持 + 几乎所有 LLM**：支持 Claude/DeepSeek/GPT/本地模型（Ollama/LM Studio）

#### 缺陷

1. **零 UI 设计**：纯命令输出，新手门槛高，无法直观看到对话历史和管理会话
2. **无 MCP/LSP 原生集成**：代码理解能力依赖 prompt engineering，非结构化上下文

---

### 2.6 Cline

**官方链接：** https://github.com/cline/cline

**产品定位：** VS Code 扩展，自主 AI 编程 Agent，每步操作需用户授权，Human-in-the-loop 设计。

#### 整体布局

- **VS Code 扩展界面**：
  - **侧边栏面板**：主交互区，展示任务进度、工具调用、diff 预览
  - **Diff 视图**：AI 修改的文件以内联 diff 展示，可逐块接受/拒绝
  - **Terminal 集成**：命令在 VS Code 内置终端执行（v1.93+ Shell Integration）
  - **Image 支持**：支持上传图片作为上下文（界面截图、设计稿）
  - **Timeline 追踪**：所有变更记录在文件 Timeline 中
- **无独立桌面窗口**：完全嵌入 VS Code

#### 视觉风格

- **VS Code 扩展面板**：继承 VS Code 暗色主题
- **消息气泡**：AI 回复 + 工具调用卡片 + diff 展示的组合面板
- **配色**：VS Code 标准配色，diff 用绿色（新增）/红色（删除）
- **图标**：VS Code 图标集
- **权限确认 UI**：弹窗式确认（Allow/Deny/Allow All Session）

#### 关键交互

- **模型切换**：Settings GUI，支持 OpenRouter（自动拉取最新模型列表）/Anthropic/OpenAI/Gemini/Bedrock 等；也支持本地模型（LM Studio/Ollama）
- **API Key 配置**：VS Code Settings GUI，输入 API Key
- **对话历史**：基于任务，每次任务独立，支持多轮迭代
- **文件管理**：VS Code 文件系统 + Timeline 追踪
- **Token 和费用追踪**：每步任务显示 Token 消耗和 API 费用

#### 亮点

1. **VS Code Shell Integration**：在 VS Code 内置终端执行命令，完美融入开发者工作流
2. **Image/截图上下文**：支持设计稿截图，AI 可以基于视觉理解生成代码（Computer Use）
3. **Permission 安全 + Diff 可视化**：每步确认 + diff 逐块接受，用户完全掌控

#### 缺陷

1. **纯 VS Code 依赖**：无法独立运行，不适合 JetBrains/其他编辑器用户
2. **复杂的上下文管理**：需要手动管理 token 预算，大型项目上下文压力大

---

### 2.7 Roo Code

**官方链接：** https://github.com/RooCodeInc/Roo-Code

**产品定位：** Cline 的社区分支（fork），定位为"VS Code 中的 AI 开发团队"，强调多模式工作流。

#### 整体布局

- **VS Code 扩展**：与 Cline 高度相似的界面
  - **侧边栏面板**：主交互区
  - **Mode 切换**：Code/Architect/Ask/Debug/Custom 五种模式
  - **Checkpoints**：快照/回滚机制，类似游戏存档
- **与 Cline 的区别**：
  - 多模式系统（Code Mode 日常编辑 / Architect Mode 系统设计 / Ask Mode 快速问答 / Debug Mode 调试）
  - Custom Mode：用户可自定义 AI 行为模式
  - 更积极的社区驱动迭代

#### 视觉风格

- **继承 VS Code/Cline 风格**：暗色主题，标准 VS Code UI
- **Mode 指示器**：侧边栏顶部显示当前模式（Code/Architect/Ask/Debug）
- **配色**：VS Code 标准配色

#### 关键交互

- **模型切换**：Settings GUI，支持多 Provider（Poe 直接集成）
- **API Key 配置**：VS Code Settings GUI
- **对话历史**：基于任务，多模式不影响历史记录
- **Codebase Indexing**：大型项目上下文优化

#### 亮点

1. **多模式 UX 创新**：Code/Architect/Ask/Debug/Custom 模式分离，不同场景用不同模式，UX 理念领先
2. **Poe 集成**：直接接入 Poe 平台模型，无需单独配置 API Key
3. **Checkpoints 快照**：类似游戏存档，回滚机制对实验性重构很有价值

#### 缺陷

1. **与 Cline 功能高度重叠**：fork 自 Cline，核心 UX 差异不够大，社区维护可持续性存疑
2. **VS Code 独占**：与 Cline 相同的局限性

---

### 2.8 Crush (charmbracelet/crush)

> 注：Crush 是 OpenCode 的后继者，同一团队开发，设计语言完全相同。

#### 与 OpenCode 的关系

- **同代码库**：Crush = OpenCode 重命名并继续开发
- **相同 TUI 设计**：Bubble Tea 框架、相同的交互模式、相同的 Charm 视觉风格
- **扩展功能**：Crush 新增了 Agent Skills 支持（SKILL.md 技能包）和更丰富的 MCP 集成

#### 额外亮点（相对 OpenCode）

1. **Agent Skills 生态**：内置 `crush-config` skill + Agent Skills 开放标准，技能可复用可分发
2. **更丰富的 Provider 集成**：crush.json 中直接配置 providers，包括自定义 API endpoint
3. **NixOS/Home Manager 模块**：对 Nix 用户开箱即用

---

## 3. 横向对比表

| 产品 | 类型 | 侧边栏 | 主聊天区域 | 输入框位置 | Settings 入口 | 配色方案 | 模型切换 | API Key 配置 | 对话历史 | 文件管理 | 快捷键风格 | 交通灯 |
|------|------|--------|-----------|-----------|-------------|---------|---------|-------------|---------|---------|-----------|-------|
| **OpenCode/Crush** | Terminal TUI（Go/Bubble Tea） | ❌ 无 | 上部消息区（可滚动） | 底部 Vim 编辑区 | JSON 配置文件 + 自配置 skill | Charm 暗色/渐变标题栏 | Ctrl+O 浮层 | 环境变量 + JSON 配置 | SQLite 持久化，Ctrl+A 切换 | 无原生文件树（工具命令） | Vim + VS Code 融合 | N/A（纯 TUI） |
| **Cursor** | Desktop IDE（VS Code Fork） | ✅ 左侧活动栏 | 右侧面板（Cmd+L）/ 内联（Cmd+K） | 底部输入框 | Ctrl+Shift+J | VS Code 暗色主题 | Settings GUI | Settings GUI | 右侧面板滚动 | VS Code 文件树 | VS Code 快捷键 + AI 专用键 | ✅ macOS 标准控件 |
| **Windsurf** | Desktop IDE（VS Code Fork） | ✅ 左侧活动栏 | Cascade 面板（主 AI 面板） | 底部输入框 | Settings GUI | VS Code 暗色主题 | Settings GUI | Settings GUI | Cascade 面板滚动 | VS Code 文件树 | VS Code 快捷键 | ✅ macOS 标准控件 |
| **Claude Code** | CLI TUI + VS Code 扩展 | ❌ CLI 无 / ✅ 扩展有侧边栏 | CLI：终端打印 / 扩展：侧边栏 | CLI：stdin / 扩展：底部 | `.claude.json` + GUI | Terminal 暗色 | `/general-config` 或 Settings | 环境变量 + 引导式 GUI | 基于会话文件 | CLI：无 / 扩展：VS Code | `/` 命令面板 + 扩展快捷键 | CLI 无 / 扩展 ✅ |
| **Aider** | CLI（无 TUI，Python） | ❌ 无 | 终端打印流 | stdin 参数 | `~/.aider.conf.yml` | ANSI 彩色 | `--model` 命令行参数 | 环境变量 + 引导式 | 基于 git commit | git 管理 | 命令行参数 | N/A（纯 CLI） |
| **Cline** | VS Code 扩展 | ✅ 侧边栏面板 | 侧边栏（任务/工具/diff） | 侧边栏底部 | VS Code Settings GUI | VS Code 暗色主题 | VS Code Settings GUI | VS Code Settings GUI | 基于任务 | VS Code 文件树 + Timeline | VS Code 快捷键 | ✅ 继承自 VS Code |
| **Roo Code** | VS Code 扩展 | ✅ 侧边栏面板 | 侧边栏（五模式切换） | 侧边栏底部 | VS Code Settings GUI | VS Code 暗色主题 | VS Code Settings GUI + Poe | VS Code Settings GUI | 基于任务 | VS Code 文件树 | VS Code 快捷键 + Mode 切换 | ✅ 继承自 VS Code |
| **Crush** | Terminal TUI（Go/Bubble Tea） | ❌ 无 | 上部消息区 | 底部 Vim 编辑区 | JSON 配置文件 + crush-config skill | Charm 暗色/渐变标题栏 | Ctrl+O 浮层 | 环境变量 + JSON 配置 | SQLite 持久化 | 无原生文件树 | Vim + VS Code 融合 | N/A（纯 TUI） |

### 特色功能对比

| 产品 | 特色功能 | 最适合场景 |
|------|---------|---------|
| **OpenCode/Crush** | Bubble Tea 美学 / Agent Skills / MCP / Auto-compact | Terminal 重度用户 / 追求 TUI 美学 |
| **Cursor** | Cmd+K 内联编辑 / Cmd+L 对话 / Codebase Indexing / Diff 接受 | 日常开发 / VS Code 用户 |
| **Windsurf** | Cascade Flow / Memories / MCP 一键集成 | AI 新手 / 需要持久化上下文 |
| **Claude Code** | 五种运行环境 / Permission 安全 / 深度代码理解 | Anthropic 生态用户 / 安全敏感场景 |
| **Aider** | Git 自动 commit / Repo Map / 多 LLM 支持 | 极简主义者 / Git 工作流团队 |
| **Cline** | VS Code Shell 集成 / 图片上下文 / 费用追踪 | VS Code 用户 / 需要视觉上下文 |
| **Roo Code** | 多模式 / Checkpoints / Poe 集成 | VS Code 用户 / 需要模式分离 |
| **Crush** | Agent Skills 生态 / 20+ Provider / Nix 集成 | Terminal 用户 / 多模型切换 |

---

## 4. 对 Oh My Coder Desktop 的改进建议

### P0 — 必须做（直接影响核心体验）

#### P0-1：采用 OpenCode/Crush 的 Bubble Tea TUI 设计语言

**改什么：** 参考 Charm 团队的 Bubble Tea 视觉风格，实现 Oh My Coder 的 TUI 层：
- 渐变色标题栏（参考 Crush 的 pink/blue 渐变）
- 消息气泡带边框 + 间距节奏感
- 工具调用卡片（带状态图标 ✓/✗/⏳）
- 打字机效果 + spinner 加载动画
- Lip Gloss 样式系统保证跨 Terminal 渲染一致性

**参考谁：** charmbracelet/crush + charmbracelet/bubbletea

**为什么：** Charm 团队是 TUI 设计的行业标杆，Bubble Tea 生态成熟，Oh My Coder 定位为 Terminal 工具，直接借鉴可获得业界顶级的 TUI 美学，无需从零设计。

---

#### P0-2：实现 Cursor 的 Cmd+K / Cmd+L 双入口模式

**改什么：** 在桌面应用的编辑器区域和独立 AI 面板中同时支持：
- **Cmd+K（内联编辑）**：选中代码 → Cmd+K → AI 在原位编辑，带 inline diff 预览和逐块接受/拒绝
- **Cmd+L（侧边对话）**：独立侧边栏面板，滚动对话历史，支持 @ 文件/文件夹引用

**参考谁：** Cursor

**为什么：** Cmd+K/Cmd+L 是 Cursor 开创并验证的最佳 AI 编程交互范式，内联编辑保持代码上下文不丢失，侧边对话适合探索性问答，两者互补无死角。

---

#### P0-3：实现 Windsurf 的 Memories / 持久化上下文机制

**改什么：** 参考 Windsurf 的 Cascade Memories，在 Oh My Coder 中实现：
- AI 记住代码库结构、工作流偏好、重要文件位置
- 持久化到本地数据库（SQLite 或 JSON）
- 新会话时加载 relevant memories，减少上下文重复注入

**参考谁：** Windsurf Cascade Memories

**为什么：** 长会话中上下文丢失是 Terminal AI 编程的最大痛点，Memories 机制直接解决这一问题，提升多轮对话质量。

---

### P1 — 重要（显著提升产品竞争力）

#### P1-1：Vim 模式 + 传统模式并存

**改什么：** 参考 OpenCode 的设计，在输入组件中同时支持：
- **传统模式**：标准文本输入框，适合鼠标用户
- **Vim 模式**：`i` 进入编辑，`Esc` 切回浏览，`Ctrl+E` 外部编辑器
- Ctrl+K 命令面板（类 VS Code）
- Ctrl+A 会话切换面板
- 上下箭头浏览历史

**参考谁：** OpenCode + VS Code

**为什么：** 开发者群体中 Vim 用户比例高，Vim 模式是专业 Terminal 工具的标配；但也要兼顾非 Vim 用户，模式并存是最佳平衡。

---

#### P1-2：Diff 可视化 + Permission 安全确认

**改什么：** 参考 Cline 的设计：
- AI 修改文件时，弹出 diff 视图，用户逐块接受/拒绝
- 敏感操作（rm / 网络请求 / 高危命令）需显式授权
- 支持 "Allow All for Session" 快速信任
- 权限确认面板（类似 Cline 的 Allow/Deny 弹窗）

**参考谁：** Cline

**为什么：** 安全确认是 AI Agent 落地的信任基础，diff 逐块接受让用户保持掌控感，是"Human-in-the-loop"理念的最佳实现。

---

#### P1-3：MCP 集成 + Provider 切换面板

**改什么：** 参考 Crush 的 MCP 配置和 Windsurf 的 MCP 一键集成：
- Settings 中提供 MCP Server 管理面板（stdio/http/sse 三种传输）
- 模型选择面板（Ctrl+O 快捷键）：支持 OpenAI/Anthropic/Gemini/Groq/OpenRouter 等
- 每个 provider 配置 API Key（支持环境变量引用，敏感信息不上屏）
- 支持自定义 API endpoint（兼容 OpenAI 格式）

**参考谁：** Crush + Windsurf

**为什么：** 多模型竞争格局下，灵活性是核心需求；MCP 是 AI Agent 的扩展标准，早集成早受益。

---

### P2 — 增强（提升差异化竞争力）

#### P2-1：Agent Skills 支持

**改什么：** 参考 Crush 的 Agent Skills 生态：
- 支持 `.ohmycoder/skills/` 目录发现 SKILL.md 技能包
- 内置 `ohmycoder-config` skill 让 AI 自配置
- 支持从 ClawdHub/SkillHub 搜索和安装技能

**参考谁：** Crush Agent Skills + Oh My Coder 的 SkillHub 生态

**为什么：** Oh My Coder 已有 SkillHub 生态，将 Skills 能力延伸到 Terminal TUI 层，形成桌面端 + 命令行统一的技能体系，差异化竞争力强。

---

#### P2-2：Session/Project 管理面板

**改什么：** 参考 OpenCode 的 Ctrl+A 会话切换 + Windsurf 的工作区概念：
- 项目列表面板（Recent Projects）
- Session 历史面板（带时间戳和摘要预览）
- 支持 Session 导出/导入
- Session 持久化到 SQLite

**参考谁：** OpenCode + Cursor

**为什么：** 多项目管理是刚需，用户经常在多个项目间切换，独立的项目/会话管理面板比文件树更直观。

---

#### P2-3：模式切换（Code/Architect/Ask/Debug）

**改什么：** 参考 Roo Code 的多模式设计：
- **Code Mode**：日常编辑、文件操作
- **Architect Mode**：系统设计、架构讨论
- **Ask Mode**：快速问答、代码解释
- **Debug Mode**：问题追踪、日志分析
- 侧边栏顶部模式指示器，不同模式不同的 system prompt

**参考谁：** Roo Code

**为什么：** 模式分离让 AI 在不同场景下表现更专业，减少"全能但平庸"的问题；用户也更容易建立对 AI 行为的预期。

---

#### P2-4：Token/费用实时追踪

**改什么：** 参考 Cline 的 token 计数和费用显示：
- 当前会话的 Token 消耗（输入/输出）
- 当前请求的 API 费用
- 上下文窗口使用百分比（参考 OpenCode 的 auto-compact 阈值）

**参考谁：** Cline

**为什么：** 开发者对成本敏感，实时显示 Token 和费用有助于用户合理规划使用，防止意外超支。

---

## 附录：关键参考资源

### 截图/界面资源

- **Cursor UI 详解**：https://zhuanlan.zhihu.com/p/26745647855
- **Windsurf 界面截图**：https://blog.csdn.net/chusi777/article/details/143994369
- **OpenCode/Crush GitHub**：https://github.com/charmbracelet/crush
- **Cline VS Code 扩展截图**：https://github.com/cline/cline
- **Windsurf 官网**：https://windsurf.com

### 技术参考

- **Bubble Tea 框架**：https://github.com/charmbracelet/bubbletea（TUI 构建框架）
- **Lip Gloss**：https://github.com/charmbracelet/lip gloss（终端样式库）
- **OpenCode README**：https://github.com/opencode-ai/opencode
- **Crush README**：https://github.com/charmbracelet/crush
- **Aider 文档**：https://aider.chat/docs/
- **Claude Code 文档**：https://docs.anthropic.com/en/docs/claude-code/overview
- **Roo Code 文档**：https://docs.roocode.com

### 截图 URL（来自产品 GitHub README）

- Crush UI GIF：https://private-user-images.githubusercontent.com/25087/471774478-58280caf-851b-470a-b6f7-d5c4ea8a1968.gif
- Cline Demo GIF：https://media.githubusercontent.com/media/cline/cline/main/assets/docs/demo.gif
- Cline Settings：https://private-user-images.githubusercontent.com/7799382/374832520-3cf21e04-7ce9-4d22-a7b9-ba2c595e88a4.png
- Cline Diff View：https://private-user-images.githubusercontent.com/7799382/374832624-81be79a8-1fdb-4028-9129-5fe055e01e76.png
- Cline Terminal：https://private-user-images.githubusercontent.com/7799382/374860276-ee14e6f7-20b8-4391-9091-8e8e25561929.png

---

*报告生成时间：2026-04-21*
*调研方式：GitHub README 文档抓取 + 官方文档页面获取 + CSDN/博客园产品评测文章*