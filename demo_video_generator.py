#!/usr/bin/env python3
"""
Oh My Coder Demo Video Generator
生成 3 分钟演示 GIF（~180秒播放时间，约60帧/6秒 = 30帧总）
"""
import math
import textwrap
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# ============================================================
# 配置
# ============================================================
W, H = 1280, 720  # 输出分辨率
FPS = 10  # 每秒帧数（GIF 用）
OUTPUT_PATH = Path(__file__).parent / "docs/screenshots/demo-video.gif"
BG = (13, 17, 23)  # #0d1117 窗口背景
TITLE_BAR = (22, 27, 34)  # #161b22
TAB_BAR = (28, 33, 40)  # #1c2128
GREEN_TAB = (35, 134, 54)  # #238636
GRAY_TAB = (33, 38, 45)  # #21262d
DIM_TEXT = (139, 148, 158)  # #8b949e
GREEN_TXT = (63, 185, 80)  # #3fb950
ORANGE_TXT = (240, 136, 62)  # #f0883e
CYAN_TXT = (86, 212, 221)  # #56d4dd
PURPLE_TXT = (210, 168, 255)  # #d2a8ff
YELLOW_TXT = (227, 179, 65)  # #e3b341
WHITE_TXT = (201, 209, 217)  # #c9d1d9
BLUE_HL = (31, 111, 235)  # #1f6feb
RED_TXT = (248, 81, 73)  # #f85149

# 终端内容区（左下角偏移）
WIN_X, WIN_Y = 50, 50
WIN_W, WIN_H = W - WIN_X * 2, H - WIN_Y * 2 - 20
TERM_X = WIN_X + 20
TERM_Y = WIN_Y + 50
TERM_W = WIN_W - 40
TERM_H = WIN_H - 60

# 字体
FONT_T = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 36)
FONT_T2 = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 28)
FONT_T3 = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 22)
FONT_T4 = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 18)
FONT_M = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 20)
FONT_M2 = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 17)
FONT_S = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 15)
FONT_S2 = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 13)


# ============================================================
# 工具函数
# ============================================================
def ease_in_out(t):
    return t * t * (3 - 2 * t)


def draw_terminal_frame(img, active_tab=0):
    """绘制终端窗口框架"""
    draw = ImageDraw.Draw(img)
    r = 12

    # 窗口背景（带圆角）
    _round_rect(draw, (WIN_X, WIN_Y, WIN_X + WIN_W, WIN_Y + WIN_H), r, BG)

    # 标题栏
    _round_rect_top(draw, (WIN_X, WIN_Y, WIN_X + WIN_W, WIN_Y + 50), r, TITLE_BAR)

    # 窗口按钮
    btn_y = WIN_Y + 17
    for i, (cx, col) in enumerate(
        [
            (WIN_X + 24, (210, 87, 70)),
            (WIN_X + 46, (245, 191, 61)),
            (WIN_X + 68, (63, 185, 80)),
        ]
    ):
        draw.ellipse((cx - 6, btn_y - 6, cx + 6, btn_y + 6), fill=col)

    # 标题文字
    title = "Terminal — oh-my-coder"
    draw.text(
        (WIN_X + WIN_W // 2, WIN_Y + 24),
        title,
        font=FONT_T4,
        fill=DIM_TEXT,
        anchor="mm",
    )

    # Tab bar
    tabs = ["zsh", "omc", "python"]
    tab_w = 80
    for i, tab in enumerate(tabs):
        tx = WIN_X + i * (tab_w + 4) + 12
        ty = WIN_Y + 50
        col = GREEN_TAB if i == active_tab else GRAY_TAB
        _round_rect(draw, (tx, ty, tx + tab_w, ty + 32), 6, col)
        draw.text(
            (tx + tab_w // 2, ty + 16),
            tab,
            font=FONT_S,
            fill=WHITE_TXT if i == active_tab else DIM_TEXT,
            anchor="mm",
        )

    return draw


def _round_rect(draw, bbox, r, fill):
    x0, y0, x1, y1 = bbox
    draw.rounded_rectangle(bbox, r, fill)


def _round_rect_top(draw, bbox, r, fill):
    x0, y0, x1, y1 = bbox
    draw.rounded_rectangle((x0, y0, x1, y1 - r), r, fill)
    draw.rounded_rectangle((x0, y0 + r, x1, y1), r, fill)
    draw.rectangle((x0, y0 + r, x1, y1 - r), fill)


def wrap_text(text, width_chars):
    """按字符数换行"""
    lines = []
    for line in text.split("\n"):
        if line.strip() == "":
            lines.append("")
        else:
            wrapped = textwrap.fill(
                line, width=width_chars, break_long_words=False, break_on_hyphens=True
            )
            lines.extend(wrapped.split("\n"))
    return lines


def draw_text_lines(draw, lines, x, y, font, color, line_h=None):
    """逐行绘制文字"""
    if line_h is None:
        line_h = font.getsize("M")[1] + 4
    for line in lines:
        draw.text((x, y), line, font=font, fill=color)
        y += line_h
    return y


def make_gradient_overlay(draw, bbox, color_top, color_bot, opacity=0.7):
    """从下往上渐变遮罩"""
    x0, y0, x1, y1 = bbox
    steps = y1 - y0
    for i in range(steps):
        t = i / steps
        r = int(color_top[0] * (1 - t) + color_bot[0] * t)
        g = int(color_top[1] * (1 - t) + color_bot[1] * t)
        b = int(color_top[2] * (1 - t) + color_bot[2] * t)
        draw.line([(x0, y0 + i), (x1, y0 + i)], fill=(r, g, b, int(255 * opacity)))


def type_text(full_text, char_count, prefix=""):
    """打字机效果"""
    visible = full_text[:char_count]
    return prefix + visible


# ============================================================
# 帧定义
# ============================================================


# 场景1: 开场
def frame_intro(progress):
    """开场白 + 标题"""
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    # 背景装饰
    for i in range(5):
        x = W // 2 + int(400 * math.cos(i * 1.2 + progress * 0.5))
        y = H // 2 + int(200 * math.sin(i * 1.8 + progress * 0.3))
        r = 80 + i * 30
        draw.ellipse((x - r, y - r, x + r, y + r), outline=(35, 134, 54, 30), width=1)

    # 标题
    title1 = "oh-my-coder"
    title2 = "多智能体 AI 编程助手"

    # Logo 框
    logo_box = (W // 2 - 320, H // 2 - 100, W // 2 + 320, H // 2 + 100)
    draw.rounded_rectangle(logo_box, 20, (22, 27, 34))
    draw.rounded_rectangle(
        (logo_box[0] + 2, logo_box[1] + 2, logo_box[2] - 2, logo_box[3] - 2), 18, BG
    )

    draw.text((W // 2, H // 2 - 30), title1, font=FONT_T, fill=GREEN_TXT, anchor="mm")
    draw.text((W // 2, H // 2 + 20), title2, font=FONT_T3, fill=WHITE_TXT, anchor="mm")

    # 副标题淡入
    if progress > 0.4:
        pass  # alpha controls subtitle fade, computed inline
        sub1 = "🤖 30 个专业 Agent  ·  12 家国产大模型  ·  GLM-4.7 完全免费"
        sub2 = "🌐 多 Agent 协作  ·  本地运行  ·  完全开源"
        draw.text((W // 2, H // 2 + 80), sub1, font=FONT_M, fill=DIM_TEXT, anchor="mm")
        draw.text(
            (W // 2, H // 2 + 110), sub2, font=FONT_M2, fill=DIM_TEXT, anchor="mm"
        )

    # 底部进度条
    bar_y = H - 60
    bar_w = int((W - 200) * progress)
    draw.rounded_rectangle((100, bar_y, W - 100, bar_y + 8), 4, (33, 38, 45))
    if bar_w > 0:
        draw.rounded_rectangle((100, bar_y, 100 + bar_w, bar_y + 8), 4, GREEN_TAB)

    return img


# 场景2: 安装
def frame_install(progress):
    """安装演示"""
    img = Image.new("RGB", (W, H), BG)
    draw = draw_terminal_frame(img, active_tab=0)

    # 标签
    draw.text((WIN_X + 100, WIN_Y + 70), "[ 1/5 安装 ]", font=FONT_T3, fill=GREEN_TXT)

    lines = [
        (f"{WHITE_TXT}", "#"),
        (f"{ORANGE_TXT}", " # 安装 oh-my-coder"),
        (f"{DIM_TEXT}", ""),
        (f"{ORANGE_TXT}", "$"),
        (f"{WHITE_TXT}", " pip install oh-my-coder"),
    ]

    ty = TERM_Y + 20
    line_h = 30
    for col, text in lines:
        draw.text((TERM_X, ty), text, font=FONT_M, fill=WHITE_TXT if text != "" else BG)
        ty += line_h

    # 输出（如果 progress > 0.3）
    if progress > 0.3:
        out_lines = [
            "Collecting oh-my-coder",
            "  Downloading oh-my-coder-1.0.0-py3-none-any.whl",
            "Installing collected packages: oh-my-coder",
            "Successfully installed oh-my-coder-1.0.0",
            "",
            f"{GREEN_TXT}  ✅ 安装成功！",
        ]
        ty2 = ty + 10
        for ol in out_lines:
            draw.text(
                (TERM_X, ty2),
                ol,
                font=FONT_S2,
                fill=GREEN_TXT if "✅" in ol else DIM_TEXT,
            )
            ty2 += 22

    # 进度条
    bar_y = WIN_Y + WIN_H - 20
    bar_w = int((WIN_W - 40) * progress)
    draw.rounded_rectangle(
        (WIN_X + 20, bar_y, WIN_X + WIN_W - 20, bar_y + 6), 3, (33, 38, 45)
    )
    if bar_w > 0:
        draw.rounded_rectangle(
            (WIN_X + 20, bar_y, WIN_X + 20 + bar_w, bar_y + 6), 3, GREEN_TAB
        )

    return img


# 场景3: 配置
def frame_config(progress):
    """配置 API Key"""
    img = Image.new("RGB", (W, H), BG)
    draw = draw_terminal_frame(img, active_tab=1)

    draw.text((WIN_X + 100, WIN_Y + 70), "[ 2/5 配置 ]", font=FONT_T3, fill=CYAN_TXT)

    ty = TERM_Y + 20
    line_h = 30

    cmd1 = 'omc config set -k GLM_API_KEY -v "free"'
    cmd2 = "omc config list"

    # 逐字符打字效果
    chars1 = int(len(cmd1) * min(progress * 2, 1.0)) if progress < 0.5 else len(cmd1)
    chars2 = int(len(cmd2) * max((progress - 0.5) * 4, 0)) if progress >= 0.5 else 0

    draw.text(
        (TERM_X, ty), f"{ORANGE_TXT}$ {cmd1[:chars1]}", font=FONT_M, fill=WHITE_TXT
    )
    ty += line_h

    if progress >= 0.3:
        draw.text(
            (TERM_X, ty),
            f"{GREEN_TXT}  ✅ GLM_API_KEY 已设置为: free",
            font=FONT_M2,
            fill=GREEN_TXT,
        )
        ty += line_h + 5

    if chars2 > 0:
        draw.text(
            (TERM_X, ty), f"{ORANGE_TXT}$ {cmd2[:chars2]}", font=FONT_M, fill=WHITE_TXT
        )
        ty += line_h

    if progress >= 0.6:
        config_lines = [
            ("DEEPSEEK_API_KEY", "sk-***", YELLOW_TXT),
            ("GLM_API_KEY", "free", GREEN_TXT),
            ("DEFAULT_MODEL", "glm-4-flash", CYAN_TXT),
            ("MAX_TOKENS", "4096", WHITE_TXT),
        ]
        ty += 5
        for k, v, vc in config_lines:
            draw.text(
                (TERM_X + 20, ty),
                f"  {DIM_TEXT}{k}{WHITE_TXT} = {vc}{v}",
                font=FONT_S2,
                fill=WHITE_TXT,
            )
            ty += 22

    # 进度条
    bar_y = WIN_Y + WIN_H - 20
    bar_w = int((WIN_W - 40) * progress)
    draw.rounded_rectangle(
        (WIN_X + 20, bar_y, WIN_X + WIN_W - 20, bar_y + 6), 3, (33, 38, 45)
    )
    if bar_w > 0:
        draw.rounded_rectangle(
            (WIN_X + 20, bar_y, WIN_X + 20 + bar_w, bar_y + 6), 3, GREEN_TAB
        )

    return img


# 场景4: 运行 - 代码探索
def frame_run_explore(progress):
    """运行演示 - explore"""
    img = Image.new("RGB", (W, H), BG)
    draw = draw_terminal_frame(img, active_tab=1)

    draw.text(
        (WIN_X + 100, WIN_Y + 70),
        "[ 3/5 运行 - Explore ]",
        font=FONT_T3,
        fill=PURPLE_TXT,
    )

    ty = TERM_Y + 20
    line_h = 30

    cmd = 'omc run "解释这段代码" --workflow explore --file src/core/router.py'
    chars = int(len(cmd) * min(progress * 2, 1.0)) if progress < 0.3 else len(cmd)
    draw.text(
        (TERM_X, ty), f"{ORANGE_TXT}$ {cmd[:chars]}", font=FONT_M2, fill=WHITE_TXT
    )
    ty += line_h

    if progress > 0.2:
        outputs = [
            (f"{PURPLE_TXT}", "🎯 Explore Agent 开始探索代码库..."),
            (f"{DIM_TEXT}", ""),
            (f"{CYAN_TXT}", "📂 扫描目录: src/core/"),
            (f"{WHITE_TXT}", "  ├── router.py (模型路由器)"),
            (f"{WHITE_TXT}", "  ├── config.py (配置管理)"),
            (f"{WHITE_TXT}", "  └── __init__.py"),
            (f"{DIM_TEXT}", ""),
            (f"{YELLOW_TXT}", "📊 代码复杂度: 中等"),
            (f"{YELLOW_TXT}", "📝 主要功能: 模型路由 + 成本控制"),
            (f"{GREEN_TXT}", "✅ 探索完成，生成摘要报告"),
        ]
        for col, line in outputs:
            draw.text((TERM_X + 10, ty), line, font=FONT_S2, fill=WHITE_TXT)
            ty += 20

    # 进度条
    bar_y = WIN_Y + WIN_H - 20
    bar_w = int((WIN_W - 40) * progress)
    draw.rounded_rectangle(
        (WIN_X + 20, bar_y, WIN_X + WIN_W - 20, bar_y + 6), 3, (33, 38, 45)
    )
    if bar_w > 0:
        draw.rounded_rectangle(
            (WIN_X + 20, bar_y, WIN_X + 20 + bar_w, bar_y + 6), 3, GREEN_TAB
        )

    return img


# 场景5: 多 Agent 协作
def frame_multiagent(progress):
    """多 Agent 协作工作流"""
    img = Image.new("RGB", (W, H), BG)
    draw = draw_terminal_frame(img, active_tab=1)

    draw.text(
        (WIN_X + 100, WIN_Y + 70),
        "[ 4/5 多 Agent 协作 ]",
        font=FONT_T3,
        fill=YELLOW_TXT,
    )

    # 工作流可视化
    agents = [
        ("Explore", GREEN_TXT, "🔍 探索代码结构"),
        ("Analyst", CYAN_TXT, "📋 分析需求"),
        ("Architect", PURPLE_TXT, "🏗️ 设计架构"),
        ("Executor", ORANGE_TXT, "⚡ 执行生成"),
        ("Reviewer", RED_TXT, "🔍 代码审查"),
    ]

    box_w, box_h = 160, 60
    spacing = 40
    total_w = len(agents) * box_w + (len(agents) - 1) * spacing
    start_x = (W - total_w) // 2
    box_y = H // 2 - 40

    for i, (name, color, desc) in enumerate(agents):
        bx = start_x + i * (box_w + spacing)
        # 进度：当前 agent + 前面的都高亮
        active = progress * len(agents) >= i
        current = abs(progress * len(agents) - i) < 1.0

        fill = color if active else GRAY_TAB
        border = color if current else (60, 65, 75)
        draw.rounded_rectangle((bx, box_y, bx + box_w, box_y + box_h), 8, fill)
        draw.rounded_rectangle(
            (bx, box_y, bx + box_w, box_y + box_h), 8, outline=border, width=2
        )
        draw.text(
            (bx + box_w // 2, box_y + 20), name, font=FONT_T4, fill=BG, anchor="mm"
        )
        draw.text(
            (bx + box_w // 2, box_y + 42), desc, font=FONT_S2, fill=BG, anchor="mm"
        )

        # 箭头
        if i < len(agents) - 1:
            ax = bx + box_w + 5
            ay = box_y + box_h // 2
            draw.polygon([(ax, ay - 8), (ax + 30, ay), (ax, ay + 8)], fill=DIM_TEXT)

    # 工作流描述
    if progress > 0.3:
        desc_y = box_y + box_h + 30
        descs = [
            "多 Agent 协作，自动串联最适合当前任务的 Agent 组合",
            "每个 Agent 专注单一职责，通过共享上下文协作",
        ]
        for i, d in enumerate(descs):
            draw.text(
                (W // 2, desc_y + i * 25), d, font=FONT_M2, fill=DIM_TEXT, anchor="mm"
            )

    return img


# 场景6: 输出结果
def frame_result(progress):
    """运行结果展示"""
    img = Image.new("RGB", (W, H), BG)
    draw = draw_terminal_frame(img, active_tab=2)

    draw.text(
        (WIN_X + 100, WIN_Y + 70), "[ 5/5 运行结果 ]", font=FONT_T3, fill=GREEN_TXT
    )

    ty = TERM_Y + 15
    line_h = 24

    output_lines = [
        (f"{PURPLE_TXT}", "🎯 分析结果"),
        (f"{WHITE_TXT}", "=" * 50),
        (f"{DIM_TEXT}", ""),
        (f"{CYAN_TXT}", "📝 ModelRouter 核心功能:"),
        (f"{WHITE_TXT}", "  1. 支持 12 家国产大模型"),
        (f"{WHITE_TXT}", "  2. 智能路由选择最优模型"),
        (f"{WHITE_TXT}", "  3. 成本控制与用量统计"),
        (f"{DIM_TEXT}", ""),
        (f"{GREEN_TXT}", "✅ 任务完成! 耗时: 12.3s  消耗: ¥0.02"),
        (f"{DIM_TEXT}", ""),
        (f"{YELLOW_TXT}", "💡 建议: 可用性高，建议集成到 CI/CD"),
    ]

    for i, (col, line) in enumerate(output_lines):
        alpha = 1.0
        if progress < 0.3:
            alpha = min(1.0, (progress - 0.1) / 0.2) if progress > 0.1 else 0.0
        if alpha > 0:
            draw.text((TERM_X + 10, ty), line, font=FONT_S2, fill=WHITE_TXT)
        ty += line_h

    # 代码片段
    if progress > 0.5:
        code_y = ty + 10
        code = (
            "class ModelRouter:\n"
            "    def route(self, task):\n"
            '        return self.models["glm-4-flash"]'
        )
        draw.rounded_rectangle(
            (TERM_X + 10, code_y, TERM_X + TERM_W - 20, code_y + 60), 6, (22, 27, 34)
        )
        draw.text((TERM_X + 20, code_y + 10), code, font=FONT_S2, fill=GREEN_TXT)

    return img


# 场景7: 总结
def frame_outro(progress):
    """总结"""
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    # 背景动画
    for i in range(8):
        x = W // 2 + int(350 * math.cos(i * 0.9 + progress * 0.3))
        y = H // 2 + int(250 * math.sin(i * 1.3 + progress * 0.2))
        r = 60 + i * 20
        draw.ellipse((x - r, y - r, x + r, y + r), outline=(35, 134, 54))

    title = "开始使用 oh-my-coder"
    sub1 = "pip install oh-my-coder"
    sub2 = 'omc config set -k GLM_API_KEY -v "free"'
    sub3 = 'omc run "你的第一个任务"'

    draw.text((W // 2, H // 2 - 100), title, font=FONT_T2, fill=WHITE_TXT, anchor="mm")
    draw.text((W // 2, H // 2 - 20), sub1, font=FONT_T3, fill=GREEN_TXT, anchor="mm")
    draw.text((W // 2, H // 2 + 30), sub2, font=FONT_T3, fill=CYAN_TXT, anchor="mm")
    draw.text((W // 2, H // 2 + 80), sub3, font=FONT_T3, fill=ORANGE_TXT, anchor="mm")

    if progress > 0.5:
        draw.text(
            (W // 2, H // 2 + 160),
            "GitHub: github.com/VOBC/oh-my-coder  ⭐ 完全开源",
            font=FONT_M2,
            fill=DIM_TEXT,
            anchor="mm",
        )

    return img


# ============================================================
# 主函数
# ============================================================
def generate_demo_video():
    """生成完整演示 GIF"""

    # 场景配置: (函数, 场景时长秒, 过渡时长秒)
    SCENES = [
        (frame_intro, 12, 2),
        (frame_install, 18, 2),
        (frame_config, 20, 2),
        (frame_run_explore, 25, 2),
        (frame_multiagent, 22, 2),
        (frame_result, 18, 2),
        (frame_outro, 15, 0),
    ]

    total_seconds = sum(s[1] + s[2] for s in SCENES)
    print(f"总时长: {total_seconds} 秒")
    print(f"总帧数: ~{total_seconds * FPS}")

    frames = []
    frame_durations = []

    for scene_idx, (scene_fn, duration, trans) in enumerate(SCENES):
        scene_frames = duration * FPS
        trans_frames = trans * FPS
        total_scene_frames = scene_frames + trans_frames

        next_fn = SCENES[scene_idx + 1][0] if scene_idx < len(SCENES) - 1 else None
        print(f"场景 {scene_idx+1}: {scene_fn.__name__} ({duration}s + {trans}s 过渡)")

        for f in range(total_scene_frames):
            t = f / total_scene_frames  # 0→1 场景进度

            # 过渡处理
            if f >= scene_frames and next_fn is not None:
                frames.append(next_fn(ease_in_out((f - scene_frames) / trans_frames)))
            else:
                frames.append(scene_fn(ease_in_out(t)))

            frame_durations.append(100)  # 100ms per frame

    # 保存 GIF
    print(f"\n保存 GIF: {OUTPUT_PATH}")
    frames[0].save(
        OUTPUT_PATH,
        save_all=True,
        append_images=frames[1:],
        duration=frame_durations,
        loop=0,
        optimize=False,
    )
    size_mb = OUTPUT_PATH.stat().st_size / 1024 / 1024
    print(f"✅ 完成! 文件大小: {size_mb:.1f} MB")
    print(f"   帧数: {len(frames)}")
    print(f"   时长: {len(frames) / FPS:.1f} 秒")


if __name__ == "__main__":
    generate_demo_video()
