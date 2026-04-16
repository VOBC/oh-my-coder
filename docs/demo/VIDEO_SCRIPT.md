# Oh My Coder 3分钟演示视频脚本

> 版本：v1.0 | 目标时长：3分钟 | 分辨率：900×540 | 帧率：2fps

---

## 场景1：开场介绍（30秒 = 60帧）

**画面**：深色终端风格背景，Oh My Coder 大标题居中

**字幕/配音**：

> 👋 大家好，今天介绍一款完全开源的多智能体 AI 编程助手——**Oh My Coder**。
> 
> 它支持 GLM-4-Flash（永久免费），内置 30 个专业 Agent，
> 可以帮你自动写代码、跑测试、做代码审查。

**视觉元素**：
- 标题：Oh My Coder（大号绿色等宽字体）
- 副标题：多智能体 AI 编程助手
- 特性标签：🤖 30 Agents | 🆓 GLM-4-Flash 免费 | 🇨🇳 国产模型

---

## 场景2：安装演示（30秒 = 60帧）

**画面**：终端窗口，黑色背景，绿色文字

**命令序列**（逐行显示，带打字机效果）：

```bash
$ pip install oh-my-coder

Collecting oh-my-coder
  Downloading oh-my-coder-0.1.0-py3-none-any.whl (45 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 45.2/45.2 kB 1.2 MB/s eta 0:00:00
Installing collected packages: oh-my-coder
Successfully installed oh-my-coder-0.1.0

$ omc --version
oh-my-coder 0.1.0

$ omc --help
🤖 Oh My Coder - 多智能体 AI 编程助手

Usage: omc [OPTIONS] COMMAND [ARGS]...

Commands:
  run       运行任务
  config    配置管理
  agents    查看所有 Agent
  status    系统状态
  web       启动 Web 界面
```

**字幕/配音**：

> 安装只需一行命令：pip install oh-my-coder
> 支持 macOS、Windows、Linux，Python 3.10+。

---

## 场景3：配置演示（30秒 = 60帧）

**画面**：终端窗口，展示配置流程

**命令序列**：

```bash
$ omc config show

📋 当前配置:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  GLM_API_KEY:      未设置 ⚠️
  DEFAULT_MODEL:    glm-4-flash
  WORKFLOW:         auto
  PROJECT_PATH:     /Users/demo/project

$ omc config set -k GLM_API_KEY -v "free"

✅ 已保存到 ~/.omc/config.json
   使用 GLM-4-Flash 免费版（无需注册）

$ omc config show

📋 当前配置:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  GLM_API_KEY:      free ✅
  DEFAULT_MODEL:    glm-4-flash
  WORKFLOW:         auto
  PROJECT_PATH:     /Users/demo/project
```

**字幕/配音**：

> 首次使用配置 API Key。GLM-4-Flash 完全免费，
> 用 config set 指定 "free" 即可使用免费版。

---

## 场景4：代码示例准备（15秒 = 30帧）

**画面**：展示待分析的代码文件

**代码内容**（example.py）：

```python
# 待优化的代码示例
def calculate(items):
    total = 0
    for i in range(len(items)):
        total = total + items[i]['price'] * items[i]['quantity']
    return total

def process(data):
    result = []
    for d in data:
        if d['active'] == True:
            result.append(d)
    return result
```

**字幕/配音**：

> 假设我们有这段需要优化的 Python 代码。

---

## 场景5：运行演示（75秒 = 150帧）

**画面**：终端窗口，展示 omc run 完整执行流程

**命令及输出**：

```bash
$ omc run "解释这段代码并优化" --workflow explore --file example.py

🚀 启动多 Agent 协作工作流
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🤖 [Explorer]  扫描项目结构...
              ✅ 找到 1 个文件，0 个问题

🤖 [Analyst]   分析代码...
              ✅ 发现 2 个优化点:
                 • 使用 enumerate 替代 range(len())
                 • 列表推导式可简化 process 函数

🤖 [Planner]   制定优化计划...
              ✅ 3 步计划，预计 15s

🤖 [Executor]  生成优化代码...
              ✅ example_optimized.py

🤖 [Reviewer]  代码审查...
              ✅ 通过所有检查

✨ 完成!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  📁 生成文件: example_optimized.py
  ⏱️  耗时: 12.5s
  💰 成本: ¥0.002
  🔢 Token: 1,850
```

**字幕/配音**：

> 输入自然语言任务，多 Agent 自动协作完成：
> 探索代码结构，分析优化点，制定计划，生成代码，最后审查。
> 12秒完成，成本只要 0.2 分钱。

---

## 场景6：结果展示（15秒 = 30帧）

**画面**：展示优化后的代码

**代码内容**（example_optimized.py）：

```python
# 优化后的代码
from typing import List, Dict

def calculate(items: List[Dict]) -> float:
    """计算订单总价"""
    return sum(
        item['price'] * item['quantity']
        for item in items
    )

def process(data: List[Dict]) -> List[Dict]:
    """筛选活跃数据"""
    return [d for d in data if d.get('active')]
```

**优化对比**（侧边栏）：
- ✅ 添加类型注解
- ✅ 使用生成器表达式
- ✅ 列表推导式简化
- ✅ 添加文档字符串

**字幕/配音**：

> 优化后的代码添加了类型注解，使用更 Pythonic 的写法。

---

## 场景7：总结结尾（15秒 = 30帧）

**画面**：总结卡片

**内容**：

```
🎯 Oh My Coder - 快速上手

1️⃣  安装        pip install oh-my-coder
2️⃣  配置        omc config set -k GLM_API_KEY -v "free"
3️⃣  运行        omc run "你的任务"
4️⃣  查看        ls *.py

📖 文档: github.com/VOBC/oh-my-coder
⭐ Star: 欢迎点亮 Star 支持开源！
```

**字幕/配音**：

> 4 行命令即可开始。完全开源，MIT 协议，支持 12 个国产大模型。
> 欢迎访问 GitHub 了解更多！

---

## 技术规格

| 参数 | 值 |
|------|-----|
| 总时长 | 3分钟（180秒）|
| 总帧数 | 360帧 @ 2fps |
| 分辨率 | 900 × 540 px |
| 背景色 | #1e1e1e（VS Code 暗色）|
| 文字色 | #d4d4d4（主文字）|
| 强调色 | #4ec9b0（绿色）|
| 字体 | JetBrains Mono / SF Mono |

## 生成工具

使用 `scripts/gen_demo_gif.py` 生成动画帧：

```bash
cd ~/.qclaw/workspace-agent-bf627e2b/projects/oh-my-coder
python docs/demo/gen_demo_gif.py
```

输出：
- `docs/demo/frames/` - 所有帧图片
- `docs/demo/oh-my-coder-demo.gif` - 最终 GIF 文件

## 更新日志

| 日期 | 版本 | 内容 |
|------|------|------|
| 2026-04-16 | v1.0 | 初始版本，7 场景，3分钟 |
