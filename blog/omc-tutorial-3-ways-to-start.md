# Oh My Coder 上手教程：3 种方式，3 分钟，从零开始用 AI 写代码

> 你不需要翻墙，不需要信用卡，不需要 Claude 订阅。装好 Python，一行命令，31 个 AI Agent 替你干活。

## 先说结论

Oh My Coder 有三种使用方式：**CLI 命令行**、**Web 界面**、**Desktop 桌面端**。三种方式共享同一个配置文件，选哪个都行，后面随时切换。

- 想最快体验 → 选 CLI
- 想要图形界面 → 选 Web 或 Desktop
- 想在界面里配 API Key → Web 和 Desktop 直接配，CLI 用命令配

下面一步一步来。

---

## 第 0 步：检查 Python（三种方式都必做！）

不管你用哪种方式，都需要 Python 3.9 以上。打开终端检查一下：

**Mac**：按 `Command ⌘ + 空格`，输入「终端」，按回车

**Windows**：按 `Win + R`，输入 `cmd`，按回车

打开终端后，粘贴这行按回车：

```bash
python3 --version
```

- ✅ 看到 `Python 3.9.x` 或更高 → 没问题，继续！
- ❌ 提示找不到 → 去 [python.org](https://python.org) 下载安装 Python 3.9+，安装完重新打开终端再试

---

## 方式一：CLI 命令行（最快上手）

### 1. 安装

```bash
pip3 install oh-my-coder
```

验证安装成功：

```bash
omc --version
```

> ⚠️ Mac 用户如果提示 `omc: command not found`，粘贴这行后再试：
> ```bash
> export PATH="$HOME/Library/Python/3.9/bin:$PATH"
> ```

### 2. 配置 API Key

Oh My Coder 支持 12 家国产大模型，推荐先用免费的：

**推荐：智谱 GLM（完全免费）**

1. 注册：[https://open.bigmodel.cn/](https://open.bigmodel.cn/)
2. 获取 API Key
3. 运行配置命令：

```bash
omc config set -m glm -k api_key -v "你的API Key"
omc config set -k DEFAULT_MODEL -v glm-4-flash
```

**备选：DeepSeek（新用户赠送余额，代码能力强）**

1. 注册：[https://platform.deepseek.com/](https://platform.deepseek.com/)
2. 获取 API Key
3. 配置：

```bash
omc config set -m deepseek -k api_key -v "你的API Key"
```

### 3. 开始使用

最简单的用法——直接告诉它你要干什么：

```bash
omc run --simple "帮我在桌面创建一个 hello.txt"
```

加了 `--simple` 会跳过多 Agent 工作流，单 Agent 直接执行，速度快。

**稍复杂一点的任务——多 Agent 自动协作：**

```bash
omc run "帮我分析这个项目的代码结构"
```

不加 `--simple`，系统会自动调度多个 Agent：ExploreAgent 先探索代码库 → AnalystAgent 分析需求 → PlannerAgent 制定计划 → ExecutorAgent 执行，像一个小团队在替你干活。

**更多常用命令：**

```bash
# 查看全部 31 个 Agent
omc agents

# 代码审查
omc run "审查 src/api 目录下的代码" -w review

# 调试问题
omc run "修复登录接口偶发的超时问题" -w debug

# 查看当前配置
omc config show

# 列出可用模型
omc config list-models

# 一键切换模型
omc model switch glm
```

### 工作流说明

`-w` 参数指定工作流，不同工作流触发不同 Agent 组合：

| 工作流 | 命令 | 说明 |
|--------|------|------|
| `build` | `-w build` | 完整开发：探索→分析→设计→实现→验证 |
| `review` | `-w review` | 代码审查 + 安全审查 |
| `debug` | `-w debug` | 问题定位→修复→验证 |
| `test` | `-w test` | 设计测试→实现→运行验证 |
| `autopilot` | `-w autopilot` | 自动路由，根据任务关键词选工作流 |
| `pair` | `-w pair` | 结对编程，Explorer + Critic 交替审查 |
| `refactor` | `-w refactor` | 重构：分析热点→制定计划→执行→验证 |

---

## 方式二：Web 界面（图形界面，浏览器直接用）

### 1. 安装（和 CLI 一样）

```bash
pip3 install oh-my-coder
```

### 2. 启动 Web 服务

```bash
omc server start
```

默认端口 8080，浏览器打开：[http://localhost:8080](http://localhost:8080)

指定端口：

```bash
omc server start --port 9090
```

### 3. 在界面里配置 API Key

Web 界面内置了配置面板，不需要敲命令：

1. 打开网页后，找到 **API Keys 配置面板**
2. 选择模型供应商（如 GLM、DeepSeek）
3. 填入 API Key
4. 保存

配置和 CLI 共享，在 Web 里配好，CLI 也能用，反之亦然。

### 4. 使用

Web 界面是**对话式**的：

1. 在输入框描述你的任务，比如"为用户模块添加 CRUD 接口"
2. 点击发送
3. 界面实时显示每个 Agent 的执行进度（SSE 流式推送）
4. 查看结果

**Web API 也可以直接调用：**

```python
import httpx

# 异步执行（SSE 实时推送）
resp = httpx.post(
    "http://localhost:8080/api/execute",
    json={"task": "实现用户认证模块", "workflow": "build"},
    timeout=30
)

# 同步执行（直接返回结果）
resp = httpx.post(
    "http://localhost:8080/api/execute-sync",
    json={"task": "审查 src/core 目录", "workflow": "review"}
)
print(resp.json()["result"])
```

---

## 方式三：Desktop 桌面端（本地应用，功能最全）

### 1. 前置条件

Desktop 基于 Electron，需要先装好：

- **Node.js** 18+（[下载地址](https://nodejs.org/)）
- **oh-my-coder CLI**（先完成方式一的安装步骤）

### 2. 安装和启动

```bash
# 克隆项目
git clone https://github.com/VOBC/oh-my-coder.git
cd oh-my-coder/desktop

# 安装依赖
npm install

# 启动开发模式
npm run electron:dev
```

### 3. 功能一览

Desktop 把 CLI + Web 的功能都搬到了本地应用里，还额外加了：

| 功能 | 说明 |
|------|------|
| **对话式任务** | 输入任务描述，多 Agent 自动执行 |
| **普通聊天** | 不走工作流，直接和 AI 对话 |
| **模型选择** | 侧边栏一键切换 12 家模型 |
| **API Key 配置** | 界面内直接配置，不用敲命令 |
| **语音输入** | 内置 Whisper 语音识别，说话就能下任务 |
| **任务进度** | 5 阶段进度条 + Agent 执行详情 + 实时日志 |
| **Session 管理** | 侧边栏 Chat 历史列表，随时切换 |
| **亮色/暗色主题** | 一键切换 ☀️/🌙 |
| **繁简转换** | 内置 opencc 繁简转换 |

### 4. 构建安装包

```bash
cd oh-my-coder/desktop
npm run build
npm run electron:build
```

Mac 生成 `.app` / `.dmg`，Windows 生成 `.exe` 安装包。

---

## 免费模型推荐

别被"12 家模型"吓到，先用免费的：

| 模型 | 免费额度 | 上下文长度 | 推荐理由 |
|------|----------|-----------|----------|
| **GLM-4.7-Flash** | **完全免费** | 200K | 首选，零成本，中文优化 |
| **DeepSeek V4** | 新用户赠送余额 | 128K | 代码能力强，性价比高 |
| **小米 MiMo** | 免费活动 | 长上下文 | 大文件处理 |

💡 **策略**：先用 GLM-4.7-Flash（完全免费），不够再切 DeepSeek，长文档用 MiMo。

---

## 常见问题

**Q: `omc: command not found` 怎么办？**

Mac 用户粘贴：`export PATH="$HOME/Library/Python/3.9/bin:$PATH"`

**Q: 简单任务卡住了？**

加 `--simple` 跳过工作流直接执行：`omc run --simple "你的任务"`

**Q: 三种方式的配置互通吗？**

完全互通。三种方式修改的是同一个 `~/.omc/config.json`，任选其一配置即可。

**Q: 支持 Windows 吗？**

支持。Python 3.9+ + pip install 即可。详见 [Windows 安装指南](https://github.com/VOBC/oh-my-coder/blob/main/docs/guide/windows-install.md)。

**Q: 数据安全吗？**

完全本地运行，代码不上传云端，API Key 仅存储在本地。安全审查由 SecurityReviewerAgent 自动执行。

---

## 开始你的第一次

最短路径，复制粘贴就能跑：

```bash
pip3 install oh-my-coder
omc config set -m glm -k api_key -v "你的API Key"
omc config set -k DEFAULT_MODEL -v glm-4-flash
omc run --simple "你好，介绍一下你自己"
```

试试看吧！有问题来 [GitHub Issues](https://github.com/VOBC/oh-my-coder/issues) 反馈，觉得有用就点个 ⭐ Star。

---

*Oh My Coder — 国产首个多 Agent 编程框架，31 个专业 Agent，12 家国产大模型，完全本地运行，零成本起步。*

*GitHub: [https://github.com/VOBC/oh-my-coder](https://github.com/VOBC/oh-my-coder)*
*官网: [https://vobc.github.io/oh-my-coder/](https://vobc.github.io/oh-my-coder/)*
