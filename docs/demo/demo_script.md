# Oh My Coder 演示视频脚本

## 📹 视频信息
- **时长**: 3 分钟 (180秒)
- **格式**: 1920x1080 分辨率，30fps
- **目标**: 展示 oh-my-coder 核心功能，吸引用户安装使用

---

## 🎬 分镜脚本

### 第 1 段：开场 + 介绍 (0:00 - 0:30, 30秒)

**画面**: 黑色背景，Logo 淡入

**字幕/旁白**:
```
🤖 Oh My Coder
多智能体 AI 编程助手

✨ 12 家国产大模型
🤖 31 个专业 Agent
💰 GLM-4.7-Flash 完全免费
```

**动画效果**:
- Logo 从中心放大
- 文字逐行淡入
- 最后显示版本号 v0.1.0

---

### 第 2 段：安装演示 (0:30 - 1:00, 30秒)

**画面**: 终端界面

**命令展示**:
```bash
$ pip install oh-my-coder

Collecting oh-my-coder
  Downloading oh-my-coder-0.1.0.tar.gz (45 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 45.0/45.0 kB 1.2 MB/s eta 0:00:00
  Preparing metadata (setup.py) ... done
Building wheels for collected packages: oh-my-coder
  Building wheel for oh-my-coder (setup.py) ... done
  Created wheel for oh-my-coder: filename=oh_my_coder-0.1.0-py3-none-any.whl
Successfully installed oh-my-coder-0.1.0

$ omc --version
oh-my-coder 0.1.0
```

**动画效果**:
- 光标闪烁输入命令
- 下载进度条动画
- 成功提示绿色高亮

---

### 第 3 段：配置演示 (1:00 - 1:30, 30秒)

**画面**: 终端界面

**命令展示**:
```bash
$ omc config set -k GLM_API_KEY -v "free"

✅ 配置已保存
   Key: GLM_API_KEY
   Value: free
   Model: glm-4-flash (完全免费)

$ omc config show

📋 当前配置:
   默认模型: glm
   API Key: 已配置 (GLM-4.7-Flash 免费版)
   工作目录: /home/user/project
   
💡 提示: GLM-4.7-Flash 完全免费，无需付费即可使用！
```

**动画效果**:
- 配置成功绿色勾选
- 配置信息表格展示
- 免费提示黄色高亮

---

### 第 4 段：运行演示 (1:30 - 2:30, 60秒)

**画面**: 终端界面 + 代码编辑器分屏

**场景 1 - 代码探索** (20秒):
```bash
$ omc run "解释这段代码" --workflow explore --file main.py

🚀 Oh My Coder
任务: 解释这段代码
工作流: explore

✅ ExploreAgent    → 发现 3 个模块，12 个函数
✅ AnalystAgent    → 识别 FastAPI 应用结构

📊 代码结构:
   ├── main.py          # 应用入口
   ├── routers/
   │   ├── users.py     # 用户路由
   │   └── items.py     # 商品路由
   └── models/
       └── database.py  # 数据库模型

💡 这是一个 FastAPI REST API 项目，实现了用户管理和商品管理功能。
```

**场景 2 - 代码生成** (20秒):
```bash
$ omc run "为用户模块添加分页查询接口" --workflow build

🚀 Oh My Coder
任务: 为用户模块添加分页查询接口
工作流: build

✅ ExploreAgent    → 2.3s | 1,200 tokens
✅ AnalystAgent    → 5.1s | 3,500 tokens  
✅ ArchitectAgent  → 8.2s | 5,200 tokens
✅ ExecutorAgent   → 15.7s | 12,000 tokens
✅ VerifierAgent   → 10.3s | 4,800 tokens

✨ 已生成文件:
   routers/users.py    (+45 行)
   tests/test_users.py (+38 行)

⏱️  总耗时: 41.6s
💰 总成本: ¥0.03 (GLM-4.7-Flash 免费)
🔢 总 Token: 26,700
```

**场景 3 - 多 Agent 协作可视化** (20秒):
```
┌─────────────────────────────────────────────────────────────┐
│  🤖 Agent 协作流程                                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  🧭 ExploreAgent      ✅ 探索项目结构                        │
│       ↓                                                     │
│  📊 AnalystAgent      ✅ 分析需求                            │
│       ↓                                                     │
│  🏗️  ArchitectAgent   ✅ 设计 API 接口                       │
│       ↓                                                     │
│  ⚡ ExecutorAgent      ✅ 生成代码                           │
│       ↓                                                     │
│  ✅ VerifierAgent      ✅ 运行测试                           │
│                                                             │
│  🎉 任务完成！                                               │
└─────────────────────────────────────────────────────────────┘
```

**动画效果**:
- Agent 执行时显示旋转进度
- 完成时绿色勾选
- Token 消耗实时更新
- 成本计算动态显示

---

### 第 5 段：总结 + 结尾 (2:30 - 3:00, 30秒)

**画面**: 功能特性展示 + 行动号召

**字幕展示**:
```
🎯 为什么选择 Oh My Coder?

✅ 12 家国产大模型支持
✅ 31 个专业 Agent 协作
✅ GLM-4.7-Flash 完全免费
✅ 中文优先，本土优化
✅ 完全开源，MIT 协议

📦 安装命令:
pip install oh-my-coder

🌟 GitHub: github.com/VOBC/oh-my-coder
```

**动画效果**:
- 特性列表逐项淡入
- GitHub Star 图标闪烁
- 二维码/链接展示
- 结束语淡出

---

## 🎨 视觉风格

### 配色方案
- **背景**: #1e1e1e (深色终端)
- **主色**: #4fc1ff (蓝色，命令)
- **成功**: #4ec9b0 (绿色，成功状态)
- **警告**: #dcdcaa (黄色，提示)
- **强调**: #ce9178 (橙色，重要信息)
- **文字**: #d4d4d4 (白色，普通文字)

### 字体
- **终端**: JetBrains Mono / Consolas
- **标题**: 思源黑体 / Noto Sans SC
- **正文**: 微软雅黑 / PingFang SC

### 动画规范
- **淡入**: 300ms ease-out
- **打字**: 50ms/字符
- **进度条**: 平滑过渡
- **勾选**: 缩放 + 弹跳效果

---

## 📦 素材清单

### 需要生成的素材
1. `frame_001_intro.png` - 开场 Logo
2. `frame_002_install.png` - 安装命令
3. `frame_003_config.png` - 配置展示
4. `frame_004_explore.png` - 代码探索
5. `frame_005_build.png` - 代码生成
6. `frame_006_agents.png` - Agent 协作图
7. `frame_007_summary.png` - 总结页面

### 代码示例文件
- `demo_code.py` - 用于演示的示例代码
- `demo_output.txt` - 预期输出内容

---

## 📝 旁白脚本（可选）

```
[0:00-0:30]
"Oh My Coder，多智能体 AI 编程助手。
支持 12 家国产大模型，31 个专业 Agent 协作。
GLM-4.7-Flash 完全免费，开箱即用。"

[0:30-1:00]
"安装非常简单，一条命令搞定。
pip install oh-my-coder"

[1:00-1:30]
"配置 GLM API Key，使用免费版即可。
omc config set -k GLM_API_KEY -v free"

[1:30-2:30]
"现在运行任务。Oh My Coder 会自动调度多个 Agent 协作完成。
探索、分析、设计、实现、验证，一气呵成。"

[2:30-3:00]
"Oh My Coder，让 AI 编程更简单。
立即体验：pip install oh-my-coder"
```

---

## ✅ 检查清单

- [ ] 所有帧图片生成完成
- [ ] 动画效果测试通过
- [ ] 总时长控制在 3 分钟内
- [ ] 输出格式为 MP4 或 GIF
- [ ] 文件大小 < 50MB
