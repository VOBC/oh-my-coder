# Oh My Coder 演示素材包

> 版本: v1.0 | 生成日期: 2026-04-16 | 总时长: 3分30秒

---

## 📹 视频文件

| 文件 | 分辨率 | 大小 | 时长 | 用途 |
|------|--------|------|------|------|
| `oh-my-coder-demo.gif` | 900×540 | ~350 KB | 3分30秒 | 完整演示动画 |
| `oh-my-coder-demo-small.gif` | 800×450 | ~108 KB | 38秒 | 快速预览 |

---

## 🎬 视频脚本

**主脚本**: [VIDEO_SCRIPT.md](./VIDEO_SCRIPT.md)

### 7个场景（总时长 3分30秒）

| 场景 | 内容 | 时长 | 帧数 |
|------|------|------|------|
| 1. 开场介绍 | Oh My Coder 标题 + 特性标签 | 30秒 | 60 |
| 2. 安装演示 | pip install + omc --version | 30秒 | 60 |
| 3. 配置演示 | config show / config set | 30秒 | 60 |
| 4. 代码示例 | 待优化的 Python 代码 | 15秒 | 30 |
| 5. 运行演示 | 多 Agent 协作完整流程 | 75秒 | 150 |
| 6. 结果展示 | 优化后的代码 + 改进对比 | 15秒 | 30 |
| 7. 总结结尾 | 4步快速上手 + GitHub 链接 | 15秒 | 30 |

---

## 🖼️ 帧图片

**目录**: `frames/`

关键帧预览（每10帧保存一张）：
- `frame_0000.png` - 开场第1帧
- `frame_0010.png` - 开场中间帧
- `frame_0020.png` - 安装演示
- `frame_0030.png` - 配置演示
- ... 共 42 张关键帧

---

## 📝 代码示例

| 文件 | 说明 |
|------|------|
| `example.py` | 待优化的原始代码 |
| `example_optimized.py` | 优化后的代码 |

### 优化点对比

| 优化项 | 原始代码 | 优化后 |
|--------|----------|--------|
| 类型注解 | ❌ 无 | ✅ 完整类型提示 |
| 循环写法 | `range(len())` | 生成器表达式 |
| 列表过滤 | `for + if + append` | 列表推导式 |
| 文档 | ❌ 无 | ✅ 文档字符串 |

---

## 🛠️ 生成工具

### 主要脚本

| 脚本 | 功能 |
|------|------|
| `gen_demo_gif.py` | **主生成器** - 生成所有帧并合成 GIF |
| `generate_frames.py` | 旧版帧生成（备用） |
| `create_gif.py` | 旧版 GIF 合成（备用） |

### 使用方法

```bash
cd docs/demo

# 生成完整演示 GIF（3分30秒）
python3 gen_demo_gif.py

# 输出：
# - oh-my-coder-demo.gif（主文件）
# - frames/（帧图片目录）
```

---

## 🎨 视觉规格

### 配色方案（VS Code 暗色风格）

| 用途 | 色值 | 说明 |
|------|------|------|
| 背景 | `#1e1e1e` | VS Code 暗色背景 |
| 终端背景 | `#0d0d0d` | 终端窗口 |
| 主文字 | `#d4d4d4` | 普通文字 |
| 强调绿 | `#4ec9b0` | 成功、标题 |
| 强调蓝 | `#569cd6` | Agent 名称 |
| 强调黄 | `#dcdcaa` | 提示、关键字 |
| 强调红 | `#f44747` | 警告、错误 |
| 灰色 | `#6e7681` | 次要信息 |

### 技术参数

| 参数 | 值 |
|------|-----|
| 分辨率 | 900 × 540 px |
| 帧率 | 2 fps |
| 总帧数 | 420 帧 |
| 字体 | Monaco / Menlo（等宽） |
| 格式 | GIF (256色) |

---

## 📦 文件结构

```
docs/demo/
├── README.md                    # 本文件
├── VIDEO_SCRIPT.md              # 完整视频脚本
├── gen_demo_gif.py              # GIF 生成器（主脚本）
├── generate_frames.py           # 旧版帧生成
├── create_gif.py                # 旧版 GIF 合成
├── demo_script.md               # 旧版脚本
├── demo_code.py                 # 旧版示例代码
├── example.py                   # 待优化代码示例
├── example_optimized.py         # 优化后代码示例
├── oh-my-coder-demo.gif         # 完整演示 GIF (3分30秒)
├── oh-my-coder-demo-small.gif   # 快速预览 GIF (38秒)
└── frames/                      # 帧图片目录
    ├── frame_0000.png
    ├── frame_0010.png
    └── ... (42张关键帧)
```

---

## 🚀 使用方式

### 在 README 中嵌入

```markdown
## 🎬 效果演示

![Oh My Coder Demo](docs/demo/oh-my-coder-demo.gif)
```

### 在文档中使用

```markdown
<img src="docs/demo/oh-my-coder-demo.gif" width="800" alt="演示">
```

### 社交媒体分享

- 直接上传 `oh-my-coder-demo.gif`
- 文件大小 ~350KB，适合大多数平台

---

## 📝 更新日志

| 日期 | 版本 | 内容 |
|------|------|------|
| 2026-04-16 | v1.0 | 新版 3分30秒完整演示，7场景 |
| 2026-04-16 | v0.1 | 初始 38秒快速预览版本 |

---

## 📄 版权

所有素材均为原创，MIT 协议开源，可自由使用。
