# Terminal Forge — Electron Desktop UI for oh-my-coder

> 命令行工具的桌面界面。Terminal Forge = 命令行的灵魂 + 现代化交互。

## 设计

- **Terminal Forge** 风格：暗色工业 + 琥珀色强调，代码原生感 + 现代 UI 精度
- 左 sidebar：Session 管理 / Model 选择 / Server 状态 / Config 面板
- 主区域：Chat 界面（消息流 + 模型选择器）
- 技术栈：Electron 33 + React 18 + Vite 5 + TypeScript

## 开发

```bash
cd desktop

# 安装依赖（需 npm/node）
npm install

# 启动 Vite dev server
npm run dev

# 启动 Electron（两个命令并发运行）
npm run electron:dev

# 生产构建
npm run build
npm run electron:build   # electron-builder 打包
```

## 架构

```
desktop/
├── electron/
│   ├── main.js          # BrowserWindow, IPC handlers, omc lifecycle
│   └── preload.js       # contextBridge API bridge
├── src/
│   ├── main.tsx         # React 入口
│   ├── App.tsx          # 主组件
│   ├── App.css          # Terminal Forge 样式
│   ├── index.css        # 基础样式重置
│   ├── types/           # TypeScript 类型
│   ├── components/      # React 组件
│   └── hooks/           # 自定义 hooks
├── vite.config.ts
├── package.json
└── tsconfig.json
```

## IPC API（window.omc）

| 方法 | 说明 |
|------|------|
| `omc.getStatus()` | omc server 状态 |
| `omc.startServer()` | 启动 omc server |
| `omc.stopServer()` | 停止 omc server |
| `omc.listModels()` | 模型列表 |
| `omc.setModel(name)` | 切换模型 |
| `omc.getConfig()` | 获取配置 |
| `omc.setConfig(key, value)` | 设置配置项 |
| `omc.getHistory()` | Session 历史 |
| `omc.getHistoryById(id)` | 指定 Session |
| `omc.newChat()` | 新建 Session |
| `omc.sendMessage(text)` | 发送消息 |
| `omc.getSessions()` | 所有 Session |

## 状态

- ✅ Vite build 通过（152KB JS, 12KB CSS）
- ⏳ Electron GUI 需本地运行验证
- ⏳ electron-builder 打包待完成

## 后续

Electron MVP 验证通过后，可选迁移到 Tauri（Rust 后端，体积更小）
