# Web UI 技术调研报告

**项目**: oh-my-coder Web 在线版本  
**日期**: 2026-04-25  
**目标**: 确定 Web UI 技术栈和架构方案

---

## 1. 竞品分析

### 1.1 OpenCode（GitHub）

| 维度 | OpenCode |
|------|----------|
| **官网** | opencode.ai |
| **技术栈** | Next.js + TailwindCSS + 自研 WebSocket 服务 |
| **核心功能** | 代码对话、Terminal、Web Search、文件编辑 |
| **特点** | 开源、完全在浏览器运行，支持 SSH 连接远程 |
| **代码编辑器** | Monaco Editor（VSCode 同款） |
| **部署方式** | Docker 自托管 / Cloud 服务 |

**优势**:
- 完整的 Web Terminal 体验
- 实时流式响应
- 开源可自托管

**劣势**:
- 主要面向 AI 对话，CLI 集成较弱
- 不支持多模型切换

### 1.2 Cursor

| 维度 | Cursor |
|------|--------|
| **官网** | cursor.com |
| **技术栈** | Electron + React（封装 VSCode） |
| **核心功能** | AI 代码补全、Chat、Agent |
| **特点** | 桌面应用，Web 版（cursor.com）正在发展 |
| **代码编辑器** | Monaco（同 VSCode） |

**优势**:
- 最强代码补全体验
- 生态完善

**劣势**:
- 闭源，API 依赖 OpenAI/Anthropic
- 桌面为主，Web 功能有限

### 1.3 GitHub Copilot Workspace

| 维度 | Copilot Workspace |
|------|-------------------|
| **技术栈** | Next.js + React |
| **核心功能** | 自然语言 → 代码 → PR |
| **特点** | 纯云端，Web Only |

### 1.4 国内同类工具

| 工具 | 特点 |
|------|------|
| **阿里通义灵码** | VSCode/JetBrains 插件，Web UI 较弱 |
| **百度文心快码** | 企业内部为主 |
| **讯飞友伴** | 对话为主，无代码编辑 |

### 1.5 竞品启示

```
OpenCode 是最佳参考：
- 开源 + 可自托管
- 技术栈（Next.js + Monaco）成熟
- 架构（WebSocket 长连接）适合流式输出
- 与 CLI 工具结合的方式值得借鉴
```

---

## 2. 技术选型

### 2.1 前端框架

| 框架 | 推荐度 | 理由 |
|------|--------|------|
| **Next.js (React)** | ⭐⭐⭐⭐⭐ | 成熟 SEO 好，API Routes 内置，支持 RSC |
| Vue | ⭐⭐⭐ | 学习曲线低，但组件生态不如 React |
| Svelte | ⭐⭐ | 轻量，但团队熟悉度低 |
| SvelteKit | ⭐⭐ | 同上 |

**推荐**: Next.js 14+ (App Router)

### 2.2 代码编辑器

| 编辑器 | 推荐度 | 理由 |
|--------|--------|------|
| **Monaco Editor** | ⭐⭐⭐⭐⭐ | VSCode 同款，功能最强 |
| CodeMirror 6 | ⭐⭐⭐ | 轻量，定制强，但功能少 |
| Ace | ⭐ | 老旧，维护差 |
| CodePen Embed | ❌ | 不适合集成 |

**推荐**: Monaco Editor via `@monaco-editor/react`

### 2.3 Markdown 渲染

| 库 | 推荐度 | 理由 |
|----|--------|------|
| **react-markdown** | ⭐⭐⭐⭐⭐ | 插件化、支持 GFM、支持代码高亮 |
| **@uiw/react-md-editor** | ⭐⭐⭐⭐ | Markdown 编辑器二合一 |
| markdown-it | ⭐⭐⭐ | 老牌，纯渲染 |
| remark / rehype | ⭐⭐⭐⭐ | 低层 API，灵活 |

**推荐**: `react-markdown` + `rehype-highlight` + `remark-gfm`

### 2.4 流式输出

| 方案 | 推荐度 | 理由 |
|------|--------|------|
| **SSE (Server-Sent Events)** | ⭐⭐⭐⭐⭐ | 简单、HTTP 兼容、浏览器原生支持 |
| WebSocket | ⭐⭐⭐ | 双向，但服务端复杂度高 |
| 长轮询 | ⭐⭐ | 简单场景 |

**推荐**: SSE

### 2.5 完整依赖列表

```json
{
  "dependencies": {
    "next": "^14.2.0",
    "react": "^18.3.0",
    "@monaco-editor/react": "^4.6.0",
    "react-markdown": "^9.0.0",
    "rehype-highlight": "^7.0.0",
    "remark-gfm": "^4.0.0",
    "react-syntax-highlighter": "^15.5.0",
    "zustand": "^4.5.0",
    "@tanstack/react-query": "^5.0.0",
    "lucide-react": "^0.400.0",
    "tailwindcss": "^3.4.0",
    "clsx": "^2.1.0"
  }
}
```

---

## 3. 架构设计

### 3.1 整体架构

```
┌─────────────────────────────────────────────────────────┐
│                      用户浏览器                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │  Chat Panel  │  │ Code Editor  │  │  Terminal    │ │
│  │  (消息流)    │  │  (Monaco)    │  │  (xterm.js)  │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
│         │                │                │           │
│         └────────────────┼────────────────┘           │
│                          │                             │
│                    Next.js Web UI                      │
│              (React + TailwindCSS)                     │
└──────────────────────────┬────────────────────────────┘
                           │ SSE / HTTP
                           ▼
┌─────────────────────────────────────────────────────────┐
│                     Web Server                           │
│         (FastAPI / Next.js API Routes)                  │
│  ┌─────────────────────────────────────────────────┐   │
│  │            CLI Core Engine (Python)              │   │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────────────┐   │   │
│  │  │ Router  │ │ Agents  │ │ Orchestrator   │   │   │
│  │  └─────────┘ └─────────┘ └─────────────────┘   │   │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────────────┐   │   │
│  │  │ Memory  │ │Context  │ │ Model Adapters │   │   │
│  │  └─────────┘ └─────────┘ └─────────────────┘   │   │
│  └─────────────────────────────────────────────────┘   │
└──────────────────────────┬────────────────────────────┘
                           │ 本地执行 / Docker 沙箱
                           ▼
                    模型 API (Claude/GPT/GLM...)
```

### 3.2 Web 项目结构

```
web/
├── app/                    # Next.js App Router
│   ├── page.tsx           # 首页 /Chat 入口
│   ├── chat/[id]/         # 会话页面
│   └── api/
│       ├── chat/          # 对话 API (SSE)
│       ├── sessions/      # 会话管理
│       └── projects/      # 项目管理
├── components/
│   ├── chat/
│   │   ├── ChatPanel.tsx  # 主对话面板
│   │   ├── MessageItem.tsx# 单条消息
│   │   ├── CodeBlock.tsx  # 代码块渲染
│   │   └── MarkdownRenderer.tsx
│   ├── editor/
│   │   ├── CodeEditor.tsx # Monaco 编辑器
│   │   └── FileTree.tsx   # 文件树
│   ├── terminal/
│   │   └── WebTerminal.tsx# xterm.js 终端
│   └── layout/
│       ├── Sidebar.tsx    # 侧边栏
│       └── Header.tsx     # 顶栏
├── lib/
│   ├── api-client.ts      # API 调用封装
│   ├── sse-client.ts       # SSE 流式读取
│   └── stores/
│       ├── chat-store.ts  # Zustand chat 状态
│       └── ui-store.ts    # UI 状态
├── server/
│   └── cli-bridge.ts      # Python CLI 桥接层
└── styles/
    └── globals.css        # Tailwind 入口
```

### 3.3 CLI ↔ Web 桥接方案

**方案 A: Python HTTP Server（推荐）**
```
Web (Node.js) --HTTP--> Python FastAPI Server --subprocess--> CLI Core
```
- Web 启动时 spawn Python FastAPI 服务
- FastAPI 封装 CLI 的所有功能
- 通过 HTTP SSE 返回流式输出

**方案 B: 直接调用 Python 模块**
```
Web ---> Next.js API Routes ---> Python subprocess ---> CLI
```
- 用 `child_process.spawn` 调用 `python -m src.cli`
- 更简单，但流式输出需特殊处理

**方案 C: 独立服务模式**
```
Web --> WebSocket --> Python FastAPI Service
```
- CLI 核心作为独立服务运行
- Web 只负责展示

**推荐**: 方案 A（FastAPI 桥接），平衡简单性和功能完整性

---

## 4. MVP 功能优先级

### 4.1 必须 (MVP)

| 功能 | 优先级 | 说明 |
|------|--------|------|
| Chat 对话 | P0 | 输入任务 → AI 回复，支持流式输出 |
| 代码高亮 | P0 | AI 回复的代码块语法高亮 |
| 多模型切换 | P0 | 支持 GLM/DeepSeek/Claude/GPT |
| 会话管理 | P0 | 新建/切换/删除会话 |
| 上下文感知 | P0 | 上传文件、Git 仓库 URL |
| 模型 API Key 配置 | P0 | 用户自填 API Key，后端不存储 |
| 响应流式输出 | P0 | SSE 实现逐字显示 |

### 4.2 重要（第二版）

| 功能 | 优先级 | 说明 |
|------|--------|------|
| 文件树 + 编辑器 | P1 | 左侧文件树 + Monaco 代码编辑 |
| Web Terminal | P1 | 在浏览器内运行命令 |
| 会话历史持久化 | P1 | 存储到本地 / IndexedDB |
| 暗色/亮色主题 | P1 | TailwindCSS 切换 |
| Markdown 完整渲染 | P1 | 表格、任务列表、数学公式 |
| 模型上下文窗口显示 | P2 | Token 使用率可视化 |

### 4.3 可砍 (后续版本)

| 功能 | 优先级 | 说明 |
|------|--------|------|
| 多 Tab 同时对话 | P2 |  |
| 项目管理（多 repo） | P2 |  |
| 插件系统 | P3 | 外部工具集成 |
| 团队协作 | P3 |  |
| 自定义 Agent | P3 |  |
| 本地模型支持（Ollama）| P3 | WebUI 模式下 |

### 4.4 不做

- 完整 VSCode 集成（太重，超出 scope）
- 在线代码执行（安全风险）
- 付费订阅系统

---

## 5. 预估工时

### 5.1 简单版（纯对话，无编辑器）

| 模块 | 工作量 | 说明 |
|------|--------|------|
| 项目初始化 + TailwindCSS | 0.5d | Next.js 14 + Tailwind |
| Chat UI 组件 | 1d | 消息列表、输入框、流式输出 |
| SSE 流式后端 | 1d | Python FastAPI + SSE |
| CLI 桥接层 | 1d | subprocess 封装 |
| 会话管理 | 0.5d | 列表、切换、删除 |
| Markdown 渲染 | 0.5d | react-markdown |
| 多模型切换 UI | 0.5d | 模型选择下拉 |
| API Key 配置页 | 0.5d | 安全提示 |
| 部署文档 | 0.5d | Docker / Vercel |
| **合计** | **6d** | 约 1.2 周 |

### 5.2 完整版（含编辑器 + Terminal）

| 模块 | 工作量 | 说明 |
|------|--------|------|
| 简单版全部 | 6d | 同上 |
| Monaco 编辑器 | 2d | 文件打开、编辑、保存 |
| 文件树组件 | 1.5d | 树形结构、目录切换 |
| Web Terminal (xterm.js) | 2d | 命令执行、输出回显 |
| 代码执行结果展示 | 1d | 终端输出渲染 |
| 会话持久化 (IndexedDB) | 1.5d | 本地存储 |
| 主题切换 | 0.5d | 暗/亮模式 |
| 响应式布局优化 | 1d | 移动端适配 |
| Bug 修复 + 集成测试 | 2d | |
| **合计** | **18.5d** | 约 3.7 周 |

### 5.3 风险项

- **Python/Node 桥接层的流式输出调试**：预估 1-2d Buffer
- **Monaco + Next.js App Router 兼容性**：已有成熟方案，风险低
- **API Key 安全传输**：必须使用 HTTPS，避免日志泄露

---

## 6. 结论

### 推荐方案

```
前端: Next.js 14 (App Router) + TailwindCSS + Zustand
编辑器: Monaco Editor
Markdown: react-markdown + rehype-highlight
后端: Python FastAPI 桥接 CLI 核心
流式: SSE (Server-Sent Events)
部署: Docker / Vercel
```

### 下一步行动

1. **立即开始**: 搭建 Next.js 项目 + Chat UI 基础框架
2. **第 2 周**: FastAPI 桥接层 + SSE 流式输出
3. **第 3 周**: Monaco 编辑器 + 文件树
4. **第 4 周**: Terminal + 持久化 + 部署

**MVP 目标**: 6 天内完成纯对话版，用户可在 Web 上使用 oh-my-coder 完成日常 Coding 助手任务。
