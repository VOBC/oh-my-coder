# Oh My Coder - VS Code Extension

> 多智能体 AI 编程助手，支持 11 个国产大模型

## 功能特性

### 🎯 核心功能

- **快捷键调用** - 一键运行 AI 任务
  - `Ctrl+Shift+Enter` / `Cmd+Shift+Enter` - 运行选中代码的任务
  - `Ctrl+Shift+R` / `Cmd+Shift+R` - 代码审查
  - `Ctrl+Shift+O` / `Cmd+Shift+O` - 打开侧边栏面板

- **侧边栏面板** - 完整的任务管理界面
  - 任务输入和执行
  - 实时输出显示
  - 工作流选择

- **状态栏集成** - 显示当前任务状态
  - 就绪/运行中/错误状态
  - 点击快速打开面板

### 🤖 支持的 Agent

| 通道 | Agents |
|------|--------|
| 构建 | Planner, Architect, Executor, Verifier |
| 审查 | CodeReviewer, SecurityReviewer |
| 调试 | Debugger, Tracer |
| 领域 | TestEngineer, Designer, Writer, Scientist, GitMaster |
| 协调 | Coordinator, Critic |

### 🔧 工作流模板

- **build** - 完整的构建流程（规划 → 架构 → 编码 → 验证）
- **review** - 代码审查（质量检查 + 安全扫描）
- **debug** - 调试流程（问题定位 → 根因分析 → 修复）
- **test** - 测试生成（单元测试 + 集成测试）
- **explore** - 代码库探索

## 安装

### 从 VSIX 安装

1. 下载最新的 `.vsix` 文件
2. 打开 VS Code
3. 按 `Ctrl+Shift+P` 打开命令面板
4. 输入 "Extensions: Install from VSIX"
5. 选择下载的文件

### 从源码构建

```bash
cd extensions/vscode
npm install
npm run compile
npm run package
```

## 配置

在 VS Code 设置中搜索 "omc"：

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `omc.apiKey` | API Key（DeepSeek） | - |
| `omc.defaultModel` | 默认模型 | `deepseek` |
| `omc.autoSave` | 自动保存生成的代码 | `true` |
| `omc.showStatusBar` | 显示状态栏 | `true` |
| `omc.maxTokens` | 最大输出 Token | `4096` |
| `omc.temperature` | 生成温度 | `0.7` |

### API Key 配置

方式 1：VS Code 设置
```
打开设置 → 搜索 "omc.apiKey" → 输入你的 API Key
```

方式 2：环境变量
```bash
export DEEPSEEK_API_KEY=your_key_here
```

## 使用示例

### 1. 代码审查

1. 选中需要审查的代码
2. 右键 → "Oh My Coder: 代码审查"
3. 或按 `Ctrl+Shift+R`

### 2. 生成测试

1. 选中需要测试的函数/类
2. 右键 → "Oh My Coder: 生成测试"
3. 测试文件将自动创建

### 3. 调试问题

1. 选中报错的代码
2. 按 `Ctrl+Shift+Enter`
3. 输入问题描述，例如："这段代码报错 IndexError"

## 开发

### 构建

```bash
npm run compile
```

### 监听模式

```bash
npm run watch
```

### 运行测试

```bash
npm test
```

## 故障排除

### 插件无法启动

1. 检查 Node.js 版本（需要 18+）
2. 检查 oh-my-coder CLI 是否已安装
3. 查看 Output 面板中的日志

### API Key 无效

1. 确认 Key 有效且未过期
2. 检查环境变量是否正确设置
3. 尝试在设置中直接配置 Key

## 许可证

MIT License
