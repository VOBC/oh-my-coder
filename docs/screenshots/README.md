# 截图目录 - docs/screenshots/

本目录展示 Oh My Coder 各工作流的实际运行效果。

## 📁 目录结构

```
screenshots/
├── README.md              # 本文件
├── cli-help.png           # omc --help 主界面
├── cli-agents.png         # omc agents 智能体列表
├── workflow-run.png       # omc run 工作流执行
├── quest-mode.png         # omc quest 异步自主编程
├── multiagent.png         # omc multiagent 协作
├── web-dashboard.png      # Web Dashboard 界面
└── workflow-comparison.md # 各工作流对比图（ASCII）
```

## 📸 如何截取截图

### 方式一：CLI 截图（推荐）

```bash
cd oh-my-coder
source .venv/bin/activate   # 激活虚拟环境

# 主界面
omc --help > /tmp/cli-help.txt
# 全屏截图保存为 cli-help.png

# Agent 列表
omc agents > /tmp/cli-agents.txt
# 全屏截图保存为 cli-agents.png
```

### 方式二：Web UI 截图

```bash
# 启动 Web 服务
omc web

# 浏览器访问 http://localhost:8000
# 截图保存为 web-dashboard.png
```

### 方式三：运行任务截图

```bash
# 运行重构工作流
omc run "重构这个项目" -w refactor

# 截图保存为 workflow-run.png
```

## 🎯 推荐截图顺序

1. `cli-help.png` — 让用户一眼看懂 CLI 能力
2. `cli-agents.png` — 展示 21 个专业 Agent
3. `workflow-run.png` — 实际运行效果
4. `quest-mode.png` — 异步自主编程亮点

## ⚠️ 注意事项

- 截图前请先配置 `.env` 文件，不要包含真实 API Key
- 推荐分辨率：1920×1080 或更高
- 推荐格式：PNG
- 深色模式截图效果更好（macOS Terminal 支持）
