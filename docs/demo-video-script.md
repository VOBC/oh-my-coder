# oh-my-coder Demo Video Script
# 视频规格：1280×720，142 秒（2 分 22 秒），GIF 格式，10fps

---

## 🎬 场景 1：开场（12 秒）

**画面：** 深色背景 + 居中 Logo + 副标题渐入

**文案：**
> **oh-my-coder**
> 多智能体 AI 编程助手
>
> 🤖 30 个专业 Agent  ·  12 家国产大模型  ·  GLM-4.7 完全免费
> 🌐 多 Agent 协作  ·  本地运行  ·  完全开源

**旁白（0:00 - 0:12）：**
> "oh-my-coder，一款基于国产大模型的多智能体 AI 编程助手。支持 GLM、DeepSeek、Qwen 等 12 家模型，GLM-4.7-Flash 完全免费。内置 30 个专业 Agent，覆盖代码探索、审查、调试、文档生成等全流程。"

---

## 🎬 场景 2：安装（18 秒）

**画面：** 终端窗口，带 tab bar，打字机效果

**脚本：**
```
zsh ●  omc  python

# 安装 oh-my-coder
$ pip install oh-my-coder

  Collecting oh-my-coder
  Downloading oh-my-coder-1.0.0-py3-none-any.whl
  Installing collected packages: oh-my-coder
  Successfully installed oh-my-coder-1.0.0

  ✅ 安装成功！
```

**旁白（0:14 - 0:32）：**
> "安装只需一条命令。pip install oh-my-coder，支持 Python 3.10+，安装完成后即可使用 omc 命令行工具。"

---

## 🎬 场景 3：配置（20 秒）

**画面：** 终端窗口（omc tab 高亮），打字机效果显示配置命令

**脚本：**
```
# 设置 GLM 免费 API Key
$ omc config set -k GLM_API_KEY -v "free"

  ✅ GLM_API_KEY 已设置为: free

# 查看所有配置
$ omc config list

  DEEPSEEK_API_KEY = *************
  GLM_API_KEY       = free
  DEFAULT_MODEL     = glm-4-flash
  MAX_TOKENS        = 4096
```

**旁白（0:34 - 0:54）：**
> "配置同样简单。omc config set 设置 API Key，GLM-4.7-Flash 完全免费，无需申请。也可以使用 DeepSeek、Qwen 等其他国产模型，一行命令完成配置。"

---

## 🎬 场景 4：运行 - 代码探索（25 秒）

**画面：** 终端窗口 + Explore Agent 输出

**脚本：**
```
omc run "解释这段代码" --workflow explore --file src/core/router.py

🎯 Explore Agent 开始探索代码库...

📂 扫描目录: src/core/
  ├── router.py (模型路由器)
  ├── config.py (配置管理)
  └── __init__.py

📊 代码复杂度: 中等
📝 主要功能: 模型路由 + 成本控制
✅ 探索完成，生成摘要报告
```

**旁白（0:56 - 1:21）：**
> "运行同样简单。omc run 指定任务，--workflow 指定工作流，--file 指定代码文件。Explore Agent 会自动分析代码结构、复杂度，给出专业的分析报告。整个过程无需配置代理，完全本地运行。"

---

## 🎬 场景 5：多 Agent 协作（22 秒）

**画面：** 工作流可视化，5 个 Agent 方块依次高亮

**脚本：**
```
[ Explore ] → [ Analyst ] → [ Architect ] → [ Executor ] → [ Reviewer ]
  🔍 探索        📋 分析         🏗️ 设计          ⚡ 生成         🔍 审查

多 Agent 协作，自动串联最适合当前任务的 Agent 组合
每个 Agent 专注单一职责，通过共享上下文协作
```

**旁白（1:23 - 1:45）：**
> "oh-my-coder 的核心是多 Agent 协作系统。Explore 探索代码结构，Analyst 分析需求，Architect 设计架构，Executor 生成代码，Reviewer 审查质量。每个 Agent 专注单一职责，系统自动串联最优组合完成任务。"

---

## 🎬 场景 6：运行结果（18 秒）

**画面：** 终端窗口 + 代码输出 + 统计信息

**脚本：**
```
🎯 分析结果
==================================================

📝 ModelRouter 核心功能:
  1. 支持 12 家国产大模型
  2. 智能路由选择最优模型
  3. 成本控制与用量统计

✅ 任务完成!  耗时: 12.3s  消耗: ¥0.02
✅ 任务完成!  耗时: 12.3s  消耗: ¥0.02

💡 建议: 可用性高，建议集成到 CI/CD

代码预览：
class ModelRouter:
    def route(self, task):
        return self.models["glm-4-flash"]
```

**旁白（1:47 - 2:05）：**
> "任务完成后，oh-my-coder 提供完整的分析报告、成本统计和代码建议。使用 GLM-4.7-Flash 完成整个分析仅需 0.02 元，成本极低。"

---

## 🎬 场景 7：总结（15 秒）

**画面：** 深色背景 + 三步上手指南

**文案：**
> **开始使用 oh-my-coder**
>
> ```
> pip install oh-my-coder
> omc config set -k GLM_API_KEY -v "free"
> omc run "你的第一个任务"
> ```
>
> GitHub: github.com/VOBC/oh-my-coder  ⭐ 完全开源

**旁白（2:07 - 2:22）：**
> "三步开始使用：安装、配置 API Key、运行任务。完整开源，完全免费，欢迎 Star。GitHub 地址：github.com/VOBC/oh-my-coder。"

---

## 📁 素材清单

| 文件 | 说明 |
|------|------|
| `demo_video_generator.py` | Python 生成脚本（可重复生成） |
| `docs/screenshots/demo-video.gif` | 最终输出 GIF（1280×720，142秒，7.4MB） |
| `docs/screenshots/demo-agents.png` | Agent 系统架构图 |
| `docs/screenshots/demo-workflow.png` | 工作流对比图 |
| `docs/screenshots/demo-web.png` | Web 界面预览 |

---

## 🔧 技术说明

- **生成工具**：纯 Python + PIL，无需 ffmpeg
- **分辨率**：1280×720（16:9 标准）
- **帧率**：10fps
- **时长**：142 秒（可调整 `FPS` 和场景时长参数）
- **重新生成**：`python3 demo_video_generator.py`
- **升级为 MP4**：安装 ffmpeg 后执行 `ffmpeg -f gif -i demo-video.gif -vf "fps=15,scale=1280:-1:flags=lanczos" demo-video.mp4`
