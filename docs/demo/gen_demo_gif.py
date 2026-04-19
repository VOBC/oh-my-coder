#!/usr/bin/env python3
"""
Oh My Coder 演示视频 GIF 生成器

使用 PIL 生成终端风格的动画帧，合成 GIF 演示视频。
无需 ffmpeg，纯 Python 实现。

Usage:
    python gen_demo_gif.py

Output:
    docs/demo/frames/     - 帧图片目录
    docs/demo/oh-my-coder-demo.gif  - 最终 GIF
"""

import os
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# ============================================================
# 配置
# ============================================================
CONFIG = {
    "width": 900,
    "height": 540,
    "fps": 2,  # 帧率
    "bg_color": "#1e1e1e",  # VS Code 暗色背景
    "text_color": "#d4d4d4",  # 主文字颜色
    "green": "#4ec9b0",  # 强调色（绿色）
    "blue": "#569cd6",  # 蓝色
    "yellow": "#dcdcaa",  # 黄色
    "red": "#f44747",  # 红色
    "gray": "#6e7681",  # 灰色
    "terminal_bg": "#0d0d0d",  # 终端背景
    "font_size": 14,
    "line_height": 20,
    "margin": 30,
    "terminal_margin": 40,
}

# 场景定义（场景名，持续秒数）
SCENES = [
    ("intro", 30),      # 开场介绍
    ("install", 30),    # 安装演示
    ("config", 30),     # 配置演示
    ("code_input", 15), # 代码示例
    ("run", 75),        # 运行演示
    ("code_output", 15), # 结果展示
    ("outro", 15),      # 总结结尾
]

# ============================================================
# 工具函数
# ============================================================
def get_font(size=None):
    """获取等宽字体"""
    size = size or CONFIG["font_size"]
    
    # 尝试常见等宽字体
    font_names = [
        "/System/Library/Fonts/Monaco.dfont",  # macOS
        "/System/Library/Fonts/Menlo.ttc",     # macOS
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",  # Linux
        "C:\\Windows\\Fonts\\consola.ttf",      # Windows
    ]
    
    for font_path in font_names:
        if os.path.exists(font_path):
            try:
                return ImageFont.truetype(font_path, size)
            except:
                pass
    
    return ImageFont.load_default()


def create_frame():
    """创建空白帧"""
    img = Image.new("RGB", (CONFIG["width"], CONFIG["height"]), CONFIG["bg_color"])
    return img, ImageDraw.Draw(img)


def draw_terminal_window(draw, x, y, width, height, title="Terminal"):
    """绘制终端窗口"""
    # 窗口阴影
    draw.rectangle(
        [x + 4, y + 4, x + width + 4, y + height + 4],
        fill="#00000040"
    )
    
    # 窗口背景
    draw.rounded_rectangle(
        [x, y, x + width, y + height],
        radius=8,
        fill=CONFIG["terminal_bg"],
        outline="#3c3c3c",
        width=1
    )
    
    # 标题栏
    draw.rounded_rectangle(
        [x, y, x + width, y + 28],
        radius=8,
        fill="#2d2d2d"
    )
    # 修复：标题栏下方填充直角
    draw.rectangle([x, y + 20, x + width, y + 28], fill="#2d2d2d")
    
    # 交通灯按钮
    btn_colors = ["#ff5f56", "#ffbd2e", "#27c93f"]
    for i, color in enumerate(btn_colors):
        draw.ellipse(
            [x + 12 + i * 16, y + 10, x + 22 + i * 16, y + 20],
            fill=color
        )
    
    # 标题
    font = get_font(12)
    title_width = draw.textlength(title, font=font)
    draw.text(
        (x + width // 2 - title_width // 2, y + 8),
        title,
        fill="#cccccc",
        font=font
    )
    
    # 返回内容区域位置
    return x + 10, y + 32, width - 20, height - 40


def draw_text_line(draw, x, y, text, color=None, font=None):
    """绘制单行文字"""
    color = color or CONFIG["text_color"]
    font = font or get_font()
    draw.text((x, y), text, fill=color, font=font)
    return y + CONFIG["line_height"]


def draw_typing_text(draw, x, y, text, progress, color=None):
    """绘制打字机效果的文字"""
    color = color or CONFIG["text_color"]
    font = get_font()
    
    # 根据进度显示部分文字
    visible_chars = int(len(text) * progress)
    visible_text = text[:visible_chars]
    
    draw.text((x, y), visible_text, fill=color, font=font)
    
    # 绘制光标
    if progress < 1.0 and int(progress * 10) % 2 == 0:
        cursor_x = x + draw.textlength(visible_text, font=font)
        draw.rectangle([cursor_x, y, cursor_x + 8, y + 14], fill=color)
    
    return y + CONFIG["line_height"]


def draw_code_block(draw, x, y, code_lines, highlight_lines=None):
    """绘制代码块"""
    highlight_lines = highlight_lines or []
    font = get_font(13)
    line_h = 18
    
    for i, line in enumerate(code_lines):
        line_y = y + i * line_h
        
        # 高亮背景
        if i in highlight_lines:
            draw.rectangle(
                [x - 5, line_y - 2, x + 550, line_y + line_h - 2],
                fill="#264f78"
            )
        
        # 行号
        draw.text((x, line_y), f"{i+1:3d} |", fill="#6e7681", font=font)
        
        # 代码内容（简单语法高亮）
        code_x = x + 45
        if line.strip():
            # 注释
            if line.strip().startswith("#"):
                draw.text((code_x, line_y), line, fill="#6a9955", font=font)
            # 关键字
            elif any(kw in line for kw in ["def ", "import ", "from ", "return", "for ", "if ", "in "]):
                # 简单处理：整行蓝色
                draw.text((code_x, line_y), line, fill="#569cd6", font=font)
            else:
                draw.text((code_x, line_y), line, fill="#d4d4d4", font=font)
        else:
            draw.text((code_x, line_y), line, fill="#d4d4d4", font=font)
    
    return y + len(code_lines) * line_h


# ============================================================
# 场景绘制函数
# ============================================================
def draw_scene_intro(frame_idx, total_frames):
    """场景1：开场介绍"""
    img, draw = create_frame()
    progress = frame_idx / total_frames
    
    # 大标题
    title_font = get_font(48)
    title = "Oh My Coder"
    title_width = draw.textlength(title, font=title_font)
    title_x = (CONFIG["width"] - title_width) // 2
    title_y = 150
    
    # 渐变显示效果
    if progress > 0.1:
        alpha = min(1.0, (progress - 0.1) / 0.3)
        draw.text((title_x, title_y), title, fill=CONFIG["green"], font=title_font)
    
    # 副标题
    if progress > 0.3:
        subtitle_font = get_font(20)
        subtitle = "多智能体 AI 编程助手"
        sub_width = draw.textlength(subtitle, font=subtitle_font)
        draw.text(
            ((CONFIG["width"] - sub_width) // 2, title_y + 70),
            subtitle,
            fill=CONFIG["text_color"],
            font=subtitle_font
        )
    
    # 特性标签
    if progress > 0.5:
        features = [
            "🤖 31 个专业 Agent",
            "🆓 GLM-4-Flash 永久免费",
            "🇨🇳 支持 12 家国产模型",
        ]
        feat_font = get_font(16)
        feat_y = 320
        for i, feat in enumerate(features):
            if progress > 0.5 + i * 0.1:
                feat_width = draw.textlength(feat, font=feat_font)
                draw.text(
                    ((CONFIG["width"] - feat_width) // 2, feat_y + i * 35),
                    feat,
                    fill=CONFIG["yellow"],
                    font=feat_font
                )
    
    # 版本信息
    version_font = get_font(12)
    version_text = "v0.1.0 | MIT License | github.com/VOBC/oh-my-coder"
    draw.text(
        (CONFIG["margin"], CONFIG["height"] - 30),
        version_text,
        fill=CONFIG["gray"],
        font=version_font
    )
    
    return img


def draw_scene_install(frame_idx, total_frames):
    """场景2：安装演示"""
    img, draw = create_frame()
    progress = frame_idx / total_frames
    
    # 绘制终端窗口
    tx, ty, tw, th = draw_terminal_window(
        draw, 50, 50, 800, 440, "Install Oh My Coder"
    )
    
    # 命令序列
    commands = [
        ("$ pip install oh-my-coder", CONFIG["text_color"]),
        ("", CONFIG["text_color"]),
        ("Collecting oh-my-coder", CONFIG["gray"]),
        ("  Downloading oh-my-coder-0.1.0-py3-none-any.whl (45 kB)", CONFIG["gray"]),
        ("     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 45.2/45.2 kB", CONFIG["green"]),
        ("Installing collected packages: oh-my-coder", CONFIG["gray"]),
        ("Successfully installed oh-my-coder-0.1.0", CONFIG["green"]),
        ("", CONFIG["text_color"]),
        ("$ omc --version", CONFIG["text_color"]),
        ("oh-my-coder 0.1.0", CONFIG["green"]),
        ("", CONFIG["text_color"]),
        ("$ omc --help", CONFIG["text_color"]),
        ("🤖 Oh My Coder - 多智能体 AI 编程助手", CONFIG["green"]),
        ("", CONFIG["text_color"]),
        ("Commands:", CONFIG["yellow"]),
        ("  run       运行任务", CONFIG["text_color"]),
        ("  config    配置管理", CONFIG["text_color"]),
        ("  agents    查看所有 Agent", CONFIG["text_color"]),
        ("  status    系统状态", CONFIG["text_color"]),
    ]
    
    # 根据进度显示命令
    y = ty + 10
    lines_to_show = int(len(commands) * min(1.0, progress * 1.5))
    
    for i, (cmd, color) in enumerate(commands[:lines_to_show]):
        if cmd:
            draw.text((tx + 10, y), cmd, fill=color, font=get_font(13))
        y += 18
    
    return img


def draw_scene_config(frame_idx, total_frames):
    """场景3：配置演示"""
    img, draw = create_frame()
    progress = frame_idx / total_frames
    
    tx, ty, tw, th = draw_terminal_window(
        draw, 50, 50, 800, 440, "Configure API Key"
    )
    
    y = ty + 10
    
    # 第一阶段：显示当前配置
    if progress < 0.4:
        phase_progress = progress / 0.4
        lines = [
            ("$ omc config show", CONFIG["text_color"]),
            ("", CONFIG["text_color"]),
            ("📋 当前配置:", CONFIG["yellow"]),
            ("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", CONFIG["gray"]),
            ("  GLM_API_KEY:      未设置 ⚠️", CONFIG["red"]),
            ("  DEFAULT_MODEL:    glm-4-flash", CONFIG["text_color"]),
            ("  WORKFLOW:         auto", CONFIG["text_color"]),
            ("  PROJECT_PATH:     /Users/demo/project", CONFIG["text_color"]),
        ]
        show_count = int(len(lines) * phase_progress)
        for cmd, color in lines[:show_count]:
            draw.text((tx + 10, y), cmd, fill=color, font=get_font(13))
            y += 18
    
    # 第二阶段：设置配置
    elif progress < 0.7:
        # 显示之前的配置
        for cmd, color in [
            ("$ omc config show", CONFIG["text_color"]),
            ("", CONFIG["text_color"]),
            ("📋 当前配置:", CONFIG["yellow"]),
            ("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", CONFIG["gray"]),
            ("  GLM_API_KEY:      未设置 ⚠️", CONFIG["red"]),
            ("  DEFAULT_MODEL:    glm-4-flash", CONFIG["text_color"]),
            ("  WORKFLOW:         auto", CONFIG["text_color"]),
            ("  PROJECT_PATH:     /Users/demo/project", CONFIG["text_color"]),
        ]:
            draw.text((tx + 10, y), cmd, fill=color, font=get_font(13))
            y += 18
        
        y += 20
        phase_progress = (progress - 0.4) / 0.3
        set_lines = [
            ("$ omc config set -k GLM_API_KEY -v \"free\"", CONFIG["text_color"]),
            ("", CONFIG["text_color"]),
            ("✅ 已保存到 ~/.omc/config.json", CONFIG["green"]),
            ("   使用 GLM-4-Flash 免费版（无需注册）", CONFIG["gray"]),
        ]
        show_count = int(len(set_lines) * phase_progress)
        for cmd, color in set_lines[:show_count]:
            draw.text((tx + 10, y), cmd, fill=color, font=get_font(13))
            y += 18
    
    # 第三阶段：显示更新后的配置
    else:
        y = ty + 10
        for cmd, color in [
            ("$ omc config set -k GLM_API_KEY -v \"free\"", CONFIG["text_color"]),
            ("", CONFIG["text_color"]),
            ("✅ 已保存到 ~/.omc/config.json", CONFIG["green"]),
            ("   使用 GLM-4-Flash 免费版（无需注册）", CONFIG["gray"]),
            ("", CONFIG["text_color"]),
            ("$ omc config show", CONFIG["text_color"]),
            ("", CONFIG["text_color"]),
            ("📋 当前配置:", CONFIG["yellow"]),
            ("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", CONFIG["gray"]),
            ("  GLM_API_KEY:      free ✅", CONFIG["green"]),
            ("  DEFAULT_MODEL:    glm-4-flash", CONFIG["text_color"]),
            ("  WORKFLOW:         auto", CONFIG["text_color"]),
            ("  PROJECT_PATH:     /Users/demo/project", CONFIG["text_color"]),
        ]:
            draw.text((tx + 10, y), cmd, fill=color, font=get_font(13))
            y += 18
    
    return img


def draw_scene_code_input(frame_idx, total_frames):
    """场景4：代码示例输入"""
    img, draw = create_frame()
    progress = frame_idx / total_frames
    
    # 标题
    title_font = get_font(18)
    draw.text((50, 30), "📄 example.py - 待优化的代码", fill=CONFIG["yellow"], font=title_font)
    
    # 代码编辑器窗口
    ex, ey, ew, eh = draw_terminal_window(draw, 50, 60, 800, 460, "example.py")
    
    code_lines = [
        "# 待优化的代码示例",
        "def calculate(items):",
        "    total = 0",
        "    for i in range(len(items)):",
        "        total = total + items[i]['price'] * items[i]['quantity']",
        "    return total",
        "",
        "def process(data):",
        "    result = []",
        "    for d in data:",
        "        if d['active'] == True:",
        "            result.append(d)",
        "    return result",
    ]
    
    # 打字机效果显示代码
    lines_to_show = int(len(code_lines) * min(1.0, progress * 2))
    draw_code_block(draw, ex + 10, ey + 10, code_lines[:lines_to_show])
    
    return img


def draw_scene_run(frame_idx, total_frames):
    """场景5：运行演示"""
    img, draw = create_frame()
    progress = frame_idx / total_frames
    
    tx, ty, tw, th = draw_terminal_window(
        draw, 30, 30, 840, 480, "omc run - Multi-Agent Workflow"
    )
    
    y = ty + 10
    
    # 命令
    cmd_lines = [
        ("$ omc run \"解释这段代码并优化\" --workflow explore --file example.py", CONFIG["text_color"]),
        ("", CONFIG["text_color"]),
        ("🚀 启动多 Agent 协作工作流", CONFIG["green"]),
        ("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", CONFIG["gray"]),
    ]
    
    for cmd, color in cmd_lines:
        draw.text((tx + 10, y), cmd, fill=color, font=get_font(12))
        y += 16
    
    # Agent 执行步骤
    agents = [
        ("🤖 [Explorer]", "扫描项目结构...", "✅ 找到 1 个文件，0 个问题", 0.15),
        ("🤖 [Analyst]", "分析代码...", "✅ 发现 2 个优化点", 0.30),
        ("🤖 [Planner]", "制定优化计划...", "✅ 3 步计划，预计 15s", 0.45),
        ("🤖 [Executor]", "生成优化代码...", "✅ example_optimized.py", 0.60),
        ("🤖 [Reviewer]", "代码审查...", "✅ 通过所有检查", 0.75),
    ]
    
    for agent_name, task, result, threshold in agents:
        if progress > threshold:
            agent_progress = min(1.0, (progress - threshold) / 0.1)
            
            # Agent 名称
            draw.text((tx + 10, y), agent_name, fill=CONFIG["blue"], font=get_font(12))
            y += 16
            
            # 任务（打字机效果）
            if agent_progress < 0.5:
                visible = int(len(task) * (agent_progress * 2))
                draw.text((tx + 30, y), task[:visible], fill=CONFIG["gray"], font=get_font(12))
            else:
                draw.text((tx + 30, y), task, fill=CONFIG["gray"], font=get_font(12))
                
                # 结果
                if agent_progress > 0.8:
                    draw.text((tx + 200, y), result, fill=CONFIG["green"], font=get_font(12))
            
            y += 20
    
    # 完成总结
    if progress > 0.90:
        y += 10
        draw.text((tx + 10, y), "✨ 完成!", fill=CONFIG["green"], font=get_font(14))
        y += 20
        draw.text((tx + 10, y), "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", fill=CONFIG["gray"], font=get_font(12))
        y += 18
        draw.text((tx + 10, y), "  📁 生成文件: example_optimized.py", fill=CONFIG["text_color"], font=get_font(12))
        y += 18
        draw.text((tx + 10, y), "  ⏱️  耗时: 12.5s", fill=CONFIG["text_color"], font=get_font(12))
        y += 18
        draw.text((tx + 10, y), "  💰 成本: ¥0.002", fill=CONFIG["text_color"], font=get_font(12))
        y += 18
        draw.text((tx + 10, y), "  🔢 Token: 1,850", fill=CONFIG["text_color"], font=get_font(12))
    
    return img


def draw_scene_code_output(frame_idx, total_frames):
    """场景6：优化后的代码展示"""
    img, draw = create_frame()
    progress = frame_idx / total_frames
    
    # 标题
    title_font = get_font(18)
    draw.text((50, 30), "📄 example_optimized.py - 优化后的代码", fill=CONFIG["green"], font=title_font)
    
    # 代码窗口
    ex, ey, ew, eh = draw_terminal_window(draw, 50, 60, 500, 460, "example_optimized.py")
    
    code_lines = [
        "# 优化后的代码",
        "from typing import List, Dict",
        "",
        "def calculate(items: List[Dict]) -> float:",
        "    \"\"\"计算订单总价\"\"\"",
        "    return sum(",
        "        item['price'] * item['quantity']",
        "        for item in items",
        "    )",
        "",
        "def process(data: List[Dict]) -> List[Dict]:",
        "    \"\"\"筛选活跃数据\"\"\"",
        "    return [d for d in data if d.get('active')]",
    ]
    
    draw_code_block(draw, ex + 10, ey + 10, code_lines)
    
    # 优化对比（右侧）
    if progress > 0.3:
        sx, sy = 580, 80
        draw.text((sx, sy), "✨ 优化改进:", fill=CONFIG["yellow"], font=get_font(14))
        
        improvements = [
            "✅ 添加类型注解",
            "✅ 使用生成器表达式",
            "✅ 列表推导式简化",
            "✅ 添加文档字符串",
            "✅ 更 Pythonic 的写法",
        ]
        
        for i, imp in enumerate(improvements):
            if progress > 0.3 + i * 0.12:
                draw.text((sx, sy + 35 + i * 28), imp, fill=CONFIG["green"], font=get_font(13))
    
    return img


def draw_scene_outro(frame_idx, total_frames):
    """场景7：总结结尾"""
    img, draw = create_frame()
    progress = frame_idx / total_frames
    
    # 大标题
    title_font = get_font(36)
    title = "🎯 Oh My Coder"
    title_width = draw.textlength(title, font=title_font)
    draw.text(
        ((CONFIG["width"] - title_width) // 2, 80),
        title,
        fill=CONFIG["green"],
        font=title_font
    )
    
    subtitle_font = get_font(20)
    subtitle = "快速上手"
    sub_width = draw.textlength(subtitle, font=subtitle_font)
    draw.text(
        ((CONFIG["width"] - sub_width) // 2, 130),
        subtitle,
        fill=CONFIG["text_color"],
        font=subtitle_font
    )
    
    # 4步快速上手
    steps = [
        ("1️⃣  安装", "pip install oh-my-coder", 0.2),
        ("2️⃣  配置", 'omc config set -k GLM_API_KEY -v "free"', 0.4),
        ("3️⃣  运行", 'omc run "你的任务"', 0.6),
        ("4️⃣  查看", "ls *.py", 0.8),
    ]
    
    y = 200
    for label, cmd, threshold in steps:
        if progress > threshold:
            draw.text((150, y), label, fill=CONFIG["yellow"], font=get_font(16))
            draw.text((280, y), cmd, fill=CONFIG["text_color"], font=get_font(14))
        y += 45
    
    # GitHub 链接
    if progress > 0.9:
        link_font = get_font(14)
        draw.text(
            (200, 420),
            "📖 文档: github.com/VOBC/oh-my-coder",
            fill=CONFIG["blue"],
            font=link_font
        )
        draw.text(
            (250, 450),
            "⭐ Star: 欢迎点亮 Star 支持开源！",
            fill=CONFIG["green"],
            font=link_font
        )
    
    return img


# ============================================================
# 主函数
# ============================================================
def main():
    """生成演示 GIF"""
    print("🎬 Oh My Coder 演示视频生成器")
    print("=" * 50)
    
    # 创建输出目录
    demo_dir = Path(__file__).parent
    frames_dir = demo_dir / "frames"
    frames_dir.mkdir(exist_ok=True)
    
    # 场景绘制函数映射
    scene_drawers = {
        "intro": draw_scene_intro,
        "install": draw_scene_install,
        "config": draw_scene_config,
        "code_input": draw_scene_code_input,
        "run": draw_scene_run,
        "code_output": draw_scene_code_output,
        "outro": draw_scene_outro,
    }
    
    # 生成所有帧
    all_frames = []
    frame_count = 0
    
    for scene_name, duration_sec in SCENES:
        num_frames = duration_sec * CONFIG["fps"]
        drawer = scene_drawers[scene_name]
        
        print(f"🎨 生成场景: {scene_name} ({duration_sec}s, {num_frames} frames)")
        
        for i in range(num_frames):
            img = drawer(i, num_frames)
            all_frames.append(img)
            
            # 保存关键帧（每10帧保存一张）
            if i % 10 == 0:
                img.save(frames_dir / f"frame_{frame_count:04d}.png")
            
            frame_count += 1
    
    print(f"\n📊 总计生成 {frame_count} 帧")
    
    # 保存 GIF
    if all_frames:
        gif_path = demo_dir / "oh-my-coder-demo.gif"
        print(f"\n💾 保存 GIF: {gif_path}")
        
        # 计算帧持续时间（毫秒）
        duration_ms = int(1000 / CONFIG["fps"])
        
        all_frames[0].save(
            gif_path,
            save_all=True,
            append_images=all_frames[1:],
            duration=duration_ms,
            loop=0,
            optimize=True
        )
        
        # 获取文件大小
        file_size = gif_path.stat().st_size / 1024  # KB
        print(f"✅ 完成! 文件大小: {file_size:.1f} KB")
        print(f"\n输出文件:")
        print(f"  - GIF: {gif_path}")
        print(f"  - 帧图片: {frames_dir}/")
        
        return 0
    
    return 1


if __name__ == "__main__":
    sys.exit(main())
