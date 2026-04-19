# Oh My Coder - VS Code Extension

> 多智能体 AI 编程助手，支持 12 个国产大模型 + 31 个智能体

## ✨ 功能特性

### 🎯 核心功能

- **快捷键调用** - 一键运行 AI 任务
  - `Ctrl+Shift+Enter` / `Cmd+Shift+Enter` - 运行选中代码的任务
  - `Ctrl+Shift+R` / `Cmd+Shift+R` - 代码审查
  - `Ctrl+Shift+O` / `Cmd+Shift+O` - 打开侧边栏面板

- **侧边栏面板** - 完整的任务管理界面
  - 任务输入和执行
  - 实时输出显示（Markdown 渲染）
  - 工作流选择
  - 模型切换

- **状态栏集成** - 显示当前任务状态
  - 就绪/运行中/错误状态
  - 点击快速打开面板

### 🤖 31 个智能体（4 大通道）

| 通道 | 智能体 | 说明 |
|------|--------|------|
| **BUILD** | Planner, Architect, Executor, Verifier, CodeSimplifier, Migration | 构建与开发 |
| **REVIEW** | CodeReviewer, SecurityReviewer, Critic, Performance | 代码审查 |
| **DEBUG** | Debugger, Tracer | 调试排错 |
| **DOMAIN** | TestEngineer, QATester, Designer, Writer, Document, Scientist, GitMaster, Explore, Vision, UML, Analyst, Database, DevOps, API, Auth, Data, Prompt, SkillManage, SelfImproving | 领域专家 |

### 🔧 工作流模板

- **build** - 完整构建流程（规划 → 架构 → 编码 → 验证）
- **review** - 代码审查（质量检查 + 安全扫描）
- **debug** - 调试流程（问题定位 → 根因分析 → 修复）
- **test** - 测试生成（单元测试 + 集成测试）
- **explore** - 代码库探索

### 🌐 支持的模型（12 个国产大模型）

`deepseek`, `qwen`, `glm`, `kimi`, `hunyuan`, `wenxin`, `doubao`, `minimax`, `tiangong`, `spark`, `baichuan`, `siliconflow`

## 📦 安装

### 从 VSIX 安装

1. 下载 `oh-my-coder-0.1.0.vsix`
2. VS Code 中按 `Ctrl+Shift+P`
3. 输入 "Extensions: Install from VSIX"
4. 选择下载的文件

### 从 Marketplace 安装（待发布）

搜索 "Oh My Coder" 并安装

## ⚙️ 配置

在 VS Code 设置中搜索 "omc"：

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `omc.apiKey` | API Key | - |
| `omc.defaultModel` | 默认模型 | `deepseek` |
| `omc.autoSave` | 自动保存生成的代码 | `true` |
| `omc.showStatusBar` | 显示状态栏 | `true` |
| `omc.maxTokens` | 最大输出 Token | `4096` |
| `omc.temperature` | 生成温度 | `0.7` |

### 🔑 API Key 配置

**方式 1：VS Code 设置**
```
设置 → 搜索 "omc.apiKey" → 输入你的 API Key
```

**方式 2：环境变量**
```bash
export DEEPSEEK_API_KEY=your_key_here
```

**方式 3：GLM 免费体验**
```bash
# 一行命令配置 GLM 免费模型
export OMC_DEFAULT_MODEL=glm
# GLM 提供 1M tokens 免费额度，无需信用卡
```

## 🚀 使用示例

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

### 4. 使用特定 Agent

1. 打开侧边栏（`Ctrl+Shift+O`）
2. 展开 "Agents" 视图
3. 选择需要的 Agent 类型
4. 在任务面板中指定工作流

## 🛠️ 开发

```bash
# 安装依赖
npm install

# 编译
npm run compile

# 监听模式
npm run watch

# 打包
npx vsce package
```

## 📝 故障排除

### 插件无法启动

1. 检查 Node.js 版本（需要 18+）
2. 确认 `omc` CLI 已安装：`pip install oh-my-coder`
3. 查看 Output 面板中的日志

### API Key 无效

1. 确认 Key 有效且未过期
2. 检查环境变量是否正确设置
3. 尝试在设置中直接配置 Key
4. 使用 GLM 免费模型测试：`omc run "hello" --model glm`

### CLI 命令找不到

插件会自动查找 `omc` 命令：
- 优先使用 `which omc` / `where omc` 查找
- 回退到常见安装路径
- 最后尝试系统 PATH

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE)

---

**Oh My Coder** - 让 AI 编程更简单 🚀
