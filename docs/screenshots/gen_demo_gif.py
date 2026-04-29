#!/usr/bin/env python3
"""
生成 oh-my-coder Terminal 模拟动图（GIF）
风格：深色 Terminal，绿色/青色文字，模拟 Agent 执行过程
"""

import os
import math
from PIL import Image, ImageDraw, ImageFont

# ── 配置 ─────────────────────────────────────────────────────────────────────
OUTPUT = os.path.join(os.path.dirname(__file__), "demo.gif")
WIDTH, HEIGHT = 1280, 720
FPS = 10
DURATION = 8  # 秒
TOTAL_FRAMES = FPS * DURATION

# 颜色（Terminal 风格）
BG = (15, 20, 25)           # 深蓝黑背景
FG_GREEN = (0, 230, 100)    # 亮绿（成功/路径）
FG_CYAN = (0, 210, 230)     # 青色（命令）
FG_WHITE = (220, 220, 220)  # 白色（普通文字）
FG_YELLOW = (255, 200, 50)  # 黄色（高亮）
FG_GRAY = (100, 100, 100)   # 灰色（次要信息）
FG_RED = (255, 80, 80)      # 红色（错误）
BORDER = (40, 50, 60)        # 边框

# 字体（尝试几种常见等宽字体）
FONT_CANDIDATES = [
    "/System/Library/Fonts/Menlo.ttc",
    "/System/Library/Fonts/Monaco.ttf",
    "/Library/Fonts/Andale Mono.ttf",
    "/System/Library/Fonts/Courier New.ttf",
]
FONT_PATH = next((f for f in FONT_CANDIDATES if os.path.exists(f)), None)
FONT_SIZE = 22
FONT_SMALL = 16

def get_font(size=FONT_SIZE):
    if FONT_PATH:
        return ImageFont.truetype(FONT_PATH, size)
    return ImageFont.load_default()

def get_font_small():
    if FONT_PATH:
        return ImageFont.truetype(FONT_PATH, FONT_SMALL)
    return ImageFont.load_default()

# ── Terminal 画面内容 ────────────────────────────────────────────────────────
# 模拟一个 oh-my-coder 执行任务的 Terminal 输出
# 随时间逐步显示内容（打字机效果）

SCENES = [
    # (start_frame, lines)  — 每行: (text, color, indent)
    # 场景 1: 启动
    (0, [
        ("$ omc agent run '给 projects/api-service 添加 JWT 鉴权中间件'", FG_WHITE, 0),
        ("", FG_WHITE, 0),
    ]),
    # 场景 2: 加载上下文
    (10, [
        ("$ omc agent run '给 projects/api-service 添加 JWT 鉴权中间件'", FG_WHITE, 0),
        ("", FG_WHITE, 0),
        ("🔍 加载项目上下文...", FG_CYAN, 0),
        ("   • 发现 3 个 Agent: CodeAgent, TestAgent, DocAgent", FG_GRAY, 0),
        ("   • 工作目录: /Users/vobc/projects/api-service", FG_GRAY, 0),
    ]),
    # 场景 3: 分析
    (25, [
        ("$ omc agent run '给 projects/api-service 添加 JWT 鉴权中间件'", FG_WHITE, 0),
        ("", FG_WHITE, 0),
        ("🔍 加载项目上下文... ✅", FG_CYAN, 0),
        ("   • 发现 3 个 Agent: CodeAgent, TestAgent, DocAgent", FG_GRAY, 0),
        ("   • 工作目录: /Users/vobc/projects/api-service", FG_GRAY, 0),
        ("", FG_WHITE, 0),
        ("🧠 CodeAgent 分析中...", FG_GREEN, 0),
        ("   → 检测到 Express.js 框架", FG_GRAY, 0),
        ("   → 建议添加 jsonwebtoken 依赖", FG_GRAY, 0),
    ]),
    # 场景 4: 执行
    (40, [
        ("$ omc agent run '给 projects/api-service 添加 JWT 鉴权中间件'", FG_WHITE, 0),
        ("", FG_WHITE, 0),
        ("🔍 加载项目上下文... ✅", FG_CYAN, 0),
        ("   • 发现 3 个 Agent: CodeAgent, TestAgent, DocAgent", FG_GRAY, 0),
        ("   • 工作目录: /Users/vobc/projects/api-service", FG_GRAY, 0),
        ("", FG_WHITE, 0),
        ("🧠 CodeAgent 分析中... ✅", FG_GREEN, 0),
        ("   → 检测到 Express.js 框架", FG_GRAY, 0),
        ("   → 建议添加 jsonwebtoken 依赖", FG_GRAY, 0),
        ("", FG_WHITE, 0),
        ("⚡ 执行修改...", FG_YELLOW, 0),
        ("   • 创建 src/middleware/auth.js", FG_GRAY, 0),
        ("   • 更新 src/app.js 注册中间件", FG_GRAY, 0),
    ]),
    # 场景 5: 测试 + 完成
    (55, [
        ("$ omc agent run '给 projects/api-service 添加 JWT 鉴权中间件'", FG_WHITE, 0),
        ("", FG_WHITE, 0),
        ("🔍 加载项目上下文... ✅", FG_CYAN, 0),
        ("   • 发现 3 个 Agent: CodeAgent, TestAgent, DocAgent", FG_GRAY, 0),
        ("   • 工作目录: /Users/vobc/projects/api-service", FG_GRAY, 0),
        ("", FG_WHITE, 0),
        ("🧠 CodeAgent 分析中... ✅", FG_GREEN, 0),
        ("   → 检测到 Express.js 框架", FG_GRAY, 0),
        ("   → 建议添加 jsonwebtoken 依赖", FG_GRAY, 0),
        ("", FG_WHITE, 0),
        ("⚡ 执行修改... ✅", FG_YELLOW, 0),
        ("   • 创建 src/middleware/auth.js", FG_GRAY, 0),
        ("   • 更新 src/app.js 注册中间件", FG_GRAY, 0),
        ("", FG_WHITE, 0),
        ("🧪 TestAgent 验证中...", FG_GREEN, 0),
        ("   → 运行 pytest tests/ ... 通过 ✅", FG_GRAY, 0),
        ("", FG_WHITE, 0),
        ("✨ 完成！3 个文件已修改，2 个测试通过", FG_GREEN, 0),
        ("", FG_WHITE, 0),
        ("$ ", FG_WHITE, 0),  # 光标闪烁位置
    ]),
]

# ── 光标闪烁 ──────────────────────────────────────────────────────────────────
def cursor_visible(frame):
    """光标每 0.5 秒闪烁一次"""
    return (frame // (FPS // 2)) % 2 == 0


# ── 渲染一帧 ──────────────────────────────────────────────────────────────────
def render_frame(frame_idx):
    img = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(img)
    font = get_font()
    font_small = get_font_small()

    # Terminal 标题栏
    draw.rectangle([0, 0, WIDTH, 40], fill=(30, 35, 42))
    draw.text((20, 10), "oh-my-coder  ●  Terminal", font=font_small, fill=FG_GRAY)
    # 红黄绿圆点
    for i, color in enumerate([(255,95,86), (255,189,46), (39,201,63)]):
        draw.ellipse([WIDTH-100+i*25, 13, WIDTH-100+i*25+14, 27], fill=color)

    # Terminal 内容区域
    PADDING = 30
    LINE_HEIGHT = 32
    START_Y = 60

    # 收集此帧应显示的行（带打字机效果）
    visible_lines = []
    for scene_start, lines in SCENES:
        if frame_idx >= scene_start:
            for line_text, line_color, indent in lines:
                visible_lines.append((line_text, line_color, indent))

    # 打字机效果：最后一行逐步显示字符
    total_lines = len(visible_lines)
    # 计算当前场景已过去的帧数
    current_scene_start = 0
    for scene_start, lines in SCENES:
        if frame_idx >= scene_start:
            current_scene_start = scene_start
    chars_per_frame = 2  # 每帧显示2个字符
    elapsed_in_scene = frame_idx - current_scene_start
    total_chars_to_show = elapsed_in_scene * chars_per_frame

    # 逐步显示最后一行
    display_lines = visible_lines[:-1] if total_lines > 1 else []
    if visible_lines:
        last_text, last_color, last_indent = visible_lines[-1]
        if total_chars_to_show < len(last_text):
            display_lines.append((last_text[:total_chars_to_show], last_color, last_indent))
        else:
            display_lines.append((last_text, last_color, last_indent))

    # 绘制所有行
    for i, (text, color, indent) in enumerate(display_lines):
        x = PADDING + indent * 20
        y = START_Y + i * LINE_HEIGHT
        if y > HEIGHT - 60:
            break
        draw.text((x, y), text, font=font, fill=color)

    # 光标（在最后一行末尾）
    if total_lines > 0 and cursor_visible(frame_idx):
        last_text = display_lines[-1][0] if display_lines else ""
        last_x = PADDING
        if display_lines:
            bbox = draw.textbbox((last_x, START_Y + (total_lines-1) * LINE_HEIGHT),
                                last_text, font=font)
            last_x = bbox[2] + 5
        cursor_y = START_Y + (total_lines - 1) * LINE_HEIGHT
        draw.rectangle([last_x, cursor_y + 4, last_x + 10, cursor_y + FONT_SIZE - 2],
                       fill=FG_WHITE)

    # 底部状态栏
    draw.rectangle([0, HEIGHT-30, WIDTH, HEIGHT], fill=(30, 35, 42))
    status = f" omc v0.2.0  |  Agent: CodeAgent  |  Model: gpt-4o  |  Files: 3 changed"
    draw.text((20, HEIGHT-25), status, font=font_small, fill=FG_GRAY)

    return img


# ── 主流程 ────────────────────────────────────────────────────────────────────
def main():
    print(f"生成 GIF: {TOTAL_FRAMES} 帧, {FPS}fps, {DURATION}s, {WIDTH}x{HEIGHT}")
    frames = []
    for i in range(TOTAL_FRAMES):
        if i % 10 == 0:
            print(f"  渲染帧 {i}/{TOTAL_FRAMES}...")
        frame = render_frame(i)
        frames.append(frame)

    print(f"保存 GIF 到 {OUTPUT} ...")
    # GIF 优化：减少颜色数以控制文件大小
    frames[0].save(
        OUTPUT,
        save_all=True,
        append_images=frames[1:],
        optimize=True,
        duration=int(1000 / FPS),  # 毫秒每帧
        loop=0,
    )

    size_mb = os.path.getsize(OUTPUT) / (1024 * 1024)
    print(f"✅ 完成！文件大小: {size_mb:.2f} MB")
    if size_mb > 5:
        print(f"⚠️  文件超过 5MB，建议降低分辨率或帧数")
    else:
        print(f"✅ 文件大小符合要求 (< 5MB)")


if __name__ == "__main__":
    main()
