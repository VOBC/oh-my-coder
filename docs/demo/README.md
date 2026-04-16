# Oh My Coder 演示素材清单

## 📹 生成的视频文件

| 文件 | 尺寸 | 大小 | 用途 |
|------|------|------|------|
| `oh-my-coder-demo.gif` | 1920x1080 | ~155 KB | 完整演示动画 |
| `oh-my-coder-demo-small.gif` | 800x450 | ~107 KB | README 展示 |

## 🖼️ 帧图片

| 文件 | 内容 | 时长 |
|------|------|------|
| `frame_001_intro.png` | 开场 Logo + 特性介绍 | 5秒 |
| `frame_002_install.png` | pip 安装演示 | 4秒 |
| `frame_003_config.png` | GLM 免费配置 | 4秒 |
| `frame_004_explore.png` | 代码探索功能 | 6秒 |
| `frame_005_build.png` | 代码生成演示 | 8秒 |
| `frame_006_agents.png` | Agent 协作可视化 | 6秒 |
| `frame_007_summary.png` | 总结 + 行动号召 | 5秒 |

**总时长**: 38 秒（可循环播放）

## 📝 脚本和代码

| 文件 | 说明 |
|------|------|
| `demo_script.md` | 完整视频脚本（含分镜、旁白、动画说明） |
| `generate_frames.py` | 帧生成脚本（PIL） |
| `create_gif.py` | GIF 合成脚本 |
| `demo_code.py` | 演示用示例代码（FastAPI） |

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

## 🚀 使用方式

### 在 README 中展示
```markdown
![Oh My Coder Demo](docs/demo/oh-my-coder-demo-small.gif)
```

### 在文档中展示
```markdown
<img src="docs/demo/oh-my-coder-demo.gif" width="100%">
```

### 在社交媒体上分享
- 直接上传 `oh-my-coder-demo.gif`
- 或转换为 MP4 格式（如需）

## 📦 文件结构

```
docs/demo/
├── README.md                      # 本文件
├── demo_script.md                 # 视频脚本
├── generate_frames.py             # 帧生成脚本
├── create_gif.py                  # GIF 合成脚本
├── demo_code.py                   # 示例代码
├── oh-my-coder-demo.gif           # 完整演示 GIF
├── oh-my-coder-demo-small.gif     # 小尺寸 GIF
└── frames/                        # 帧图片目录
    ├── frame_001_intro.png
    ├── frame_002_install.png
    ├── frame_003_config.png
    ├── frame_004_explore.png
    ├── frame_005_build.png
    ├── frame_006_agents.png
    └── frame_007_summary.png
```

## 🔄 重新生成

如需修改或重新生成：

```bash
cd docs/demo

# 生成帧
python3 generate_frames.py

# 合成 GIF
python3 create_gif.py
```

## 📝 注意事项

1. **文件大小**: GIF 文件已优化，适合网页展示
2. **循环播放**: GIF 设置为无限循环
3. **兼容性**: 支持所有主流浏览器和平台
4. **版权**: 素材为原创，可自由使用
