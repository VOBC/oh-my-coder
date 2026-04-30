#!/usr/bin/env python3
"""
Generate oh-my-coder Demo GIF
3 steps: List Agents → Ask Question → Code Generated
"""

import os

from PIL import Image, ImageDraw, ImageFont

# ── 配置 ─────────────────────────────────────────────────────────────────────
OUTPUT = os.path.join(os.path.dirname(__file__), "..", "assets", "demo.gif")
WIDTH, HEIGHT = 860, 540

# 帧持续时间 (毫秒)
DURATION = 600  # 每帧 0.6 秒

# 每步重复帧数 (控制每步停留时间)
# Step 1: List Agents (~7s)
# Step 2: Ask Question (~5s)
# Step 3: Code Generated (~11s)
REPEAT_COUNTS = (12, 8, 18)

# 颜色
BG = (30, 30, 30)
TITLE_BG = (45, 45, 45)
BORDER = (60, 60, 60)
TEXT = (212, 212, 212)
DIM = (130, 130, 130)
GREEN = (106, 168, 79)
BLUE = (78, 147, 209)
YELLOW = (229, 200, 100)
ORANGE = (229, 147, 78)
CYAN = (78, 200, 200)
WHITE = (245, 245, 245)

# 字体
FONT_PATH = "/System/Library/Fonts/Monaco.ttf"


def get_font(size=14):
    if os.path.exists(FONT_PATH):
        return ImageFont.truetype(FONT_PATH, size)
    return ImageFont.load_default()


def make_terminal(title: str, lines: list, width: int = 800, height: int = 480) -> Image.Image:
    """Render a terminal-like image."""
    img = Image.new("RGB", (width, height), BG)
    draw = ImageDraw.Draw(img)

    # Title bar
    draw.rectangle([0, 0, width - 1, 28], fill=TITLE_BG)
    draw.rectangle([0, 28, width - 1, 29], fill=BORDER)
    for i, color in enumerate([(210, 95, 85), (210, 165, 75), (75, 195, 90)]):
        draw.ellipse([10 + i * 22, 8, 22 + i * 22, 20], fill=color)

    try:
        font_b = ImageFont.truetype(FONT_PATH, 12)
        font_l = ImageFont.truetype(FONT_PATH, 13)
    except Exception:
        font_b = font_l = ImageFont.load_default()

    tw = draw.textlength(title, font=font_b)
    draw.text((width // 2 - tw // 2, 5), title, fill=TEXT, font=font_b)

    # Content
    y = 42
    for line in lines:
        if isinstance(line, tuple):
            color, text = line
        else:
            color = TEXT
            text = line
        draw.text((14, y), text, fill=color, font=font_l)
        y += 22

    draw.rectangle([0, 0, width - 1, height - 1], outline=BORDER, width=1)
    return img


def gen_step1_list_agents():
    """Step 1: List Agents"""
    lines = [
        (DIM, "$ omc agents list"),
        (DIM, ""),
        (GREEN, "Available Agents (31):"),
        (DIM, ""),
        (CYAN, "  BUILD Channel:"),
        (TEXT, "    Planner, Architect, Executor, Verifier"),
        (TEXT, "    CodeSimplifier, Migration"),
        (DIM, ""),
        (ORANGE, "  REVIEW Channel:"),
        (TEXT, "    CodeReviewer, SecurityReviewer, Critic"),
        (TEXT, "    Performance"),
        (DIM, ""),
        (BLUE, "  DEBUG Channel:"),
        (TEXT, "    Debugger, Tracer"),
        (DIM, ""),
        (YELLOW, "  DOMAIN Channel:"),
        (TEXT, "    TestEngineer, QATester, Designer, Writer"),
        (TEXT, "    Document, Scientist, GitMaster, Explore"),
        (DIM, ""),
        (DIM, "Use 'omc agent <name> --help' for details"),
    ]
    return make_terminal("Terminal — omc agents list", lines, WIDTH, HEIGHT)


def gen_step2_ask_question():
    """Step 2: Ask Question"""
    lines = [
        (DIM, "$ omc run 'Add JWT auth to API'"),
        (DIM, ""),
        (CYAN, "🔍 Loading context..."),
        (DIM, "   • Project: api-service"),
        (DIM, "   • Framework: Express.js"),
        (DIM, "   • Agents: CodeAgent, TestAgent"),
        (DIM, ""),
        (GREEN, "🧠 CodeAgent analyzing..."),
        (DIM, "   → Detected auth middleware gap"),
        (DIM, "   → Suggest: jsonwebtoken + bcrypt"),
        (DIM, ""),
        (YELLOW, "⚡ Generating implementation..."),
    ]
    return make_terminal("Terminal — omc run", lines, WIDTH, HEIGHT)


def gen_step3_code_generated():
    """Step 3: Code Generated"""
    lines = [
        (DIM, "$ omc run 'Add JWT auth to API'"),
        (DIM, ""),
        (CYAN, "🔍 Loading context... ✓"),
        (GREEN, "🧠 CodeAgent analyzing... ✓"),
        (YELLOW, "⚡ Generating implementation... ✓"),
        (DIM, ""),
        (GREEN, "✨ Task completed!"),
        (DIM, ""),
        (TEXT, "Files modified:"),
        (GREEN, "  + src/middleware/auth.js"),
        (GREEN, "  ~ src/app.js"),
        (GREEN, "  + tests/auth.test.js"),
        (DIM, ""),
        (DIM, "Stats: 3 files changed, 2 tests passed"),
        (DIM, "Cost: ¥0.03 | Time: 12.5s"),
    ]
    return make_terminal("Terminal — omc run", lines, WIDTH, HEIGHT)


def main():
    print("Generating Demo GIF...")
    print(f"  Duration per frame: {DURATION}ms")
    print(f"  Repeat counts: {REPEAT_COUNTS}")

    # Generate frames for each step
    frames = []
    step_generators = [gen_step1_list_agents, gen_step2_ask_question, gen_step3_code_generated]

    for i, (gen_fn, repeat) in enumerate(zip(step_generators, REPEAT_COUNTS, strict=True)):
        print(f"  Step {i+1}: {repeat} frames")
        img = gen_fn()
        for _ in range(repeat):
            frames.append(img)

    print(f"  Total frames: {len(frames)}")
    print(f"  Total duration: ~{len(frames) * DURATION / 1000:.1f}s")

    # Save GIF
    print(f"Saving to {OUTPUT}...")
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)

    frames[0].save(
        OUTPUT,
        save_all=True,
        append_images=frames[1:],
        optimize=True,
        duration=DURATION,
        loop=0,
    )

    size_kb = os.path.getsize(OUTPUT) / 1024
    print(f"✅ Done! File size: {size_kb:.1f} KB")

    if size_kb > 2048:
        print("⚠️  Warning: File exceeds 2MB")
    else:
        print("✅ File size OK (< 2MB)")


if __name__ == "__main__":
    main()
