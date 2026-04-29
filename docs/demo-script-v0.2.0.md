# Demo Video Script - v0.2.0

> 视频文件: `docs/screenshots/demo-v0.2.0.mp4`
> 时长: 70秒 | 分辨率: 1080p | 帧率: 30fps

## 场景分解

### 1. 开场 (0-5秒)
- 标题：oh-my-coder v0.2.0
- 副标题：32 Agents · VS Code Extension · Self-Improving
- 缓入动画效果

### 2. Agents 列表 (5-15秒)
- 命令：`omc agents list`
- 分类展示 32 个 Agent（BUILD/REVIEW/DEBUG/DOMAIN）
- 逐行打字机效果

### 3. 工作流执行 (15-30秒)
- 命令：`omc run --workflow code-review --file src/example.py`
- 多 Agent 协作过程：Planner → Architect → CodeReviewer → SecurityReviewer → Critic
- 展示审查结果（样式问题、潜在 Bug、安全检查）

### 4. VS Code 插件 (30-45秒)
- 侧边栏 Agent 列表视图
- 任务输入面板
- 一键运行按钮
- 状态栏模型切换

### 5. 本地模型支持 (45-55秒)
- 命令：`omc local status`
- 展示 Ollama 检测到的本地模型
- 云端模型列表
- 总计可用模型数

### 6. 自进化系统 (55-65秒)
- 命令：`omc learn --show`
- 学习记录展示
- 自改进建议
- 系统状态：Active Learning

### 7. 结尾 (65-70秒)
- GitHub: github.com/VOBC/oh-my-coder
- 安装：pip install oh-my-coder
- Star us on GitHub!

## 技术细节

- 生成器：`generate_demo_v020.py`
- 编码：OpenCV VideoWriter (mp4v)
- 颜色方案：GitHub Dark Theme
- 文件大小：< 12 MB
