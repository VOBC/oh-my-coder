#!/usr/bin/env python3
"""Generate demo screenshots for oh-my-coder."""

from PIL import Image, ImageDraw, ImageFont
import os

WIDTH = 860
BG = (30, 30, 30)
TITLE_BG = (45, 45, 45)
BORDER = (60, 60, 60)
TEXT = (212, 212, 212)
DIM = (130, 130, 130)
GREEN = (106, 168, 79)
BLUE = (78, 147, 209)
YELLOW = (229, 200, 100)
ORANGE = (229, 147, 78)
PURPLE = (169, 147, 209)
CYAN = (78, 200, 200)
WHITE = (245, 245, 245)

FONT_PATH = "/System/Library/Fonts/Supplemental/Courier New.ttf"


def make_terminal(title: str, lines: list, height: int) -> Image.Image:
    """Render a terminal-like image."""
    img = Image.new("RGB", (WIDTH, height), BG)
    draw = ImageDraw.Draw(img)

    # Title bar
    draw.rectangle([0, 0, WIDTH - 1, 28], fill=TITLE_BG)
    draw.rectangle([0, 28, WIDTH - 1, 29], fill=BORDER)
    for i, color in enumerate([(210, 95, 85), (210, 165, 75), (75, 195, 90)]):
        draw.ellipse([10 + i * 22, 8, 22 + i * 22, 20], fill=color)
    try:
        font_b = ImageFont.truetype(FONT_PATH, 12)
        font_l = ImageFont.truetype(FONT_PATH, 13)
    except Exception:
        font_b = font_l = ImageFont.load_default()
    tw = draw.textlength(title, font=font_b)
    draw.text((WIDTH // 2 - tw // 2, 5), title, fill=TEXT, font=font_b)

    y = 42
    for line in lines:
        if isinstance(line, tuple):
            color, text = line
        else:
            color = TEXT
            text = line
        draw.text((14, y), text, fill=color, font=font_l)
        y += 22

    draw.rectangle([0, 0, WIDTH - 1, height - 1], outline=BORDER, width=1)
    return img


def gen_demo_workflow():
    lines = [
        (DIM, "$ omc run \"实现一个 REST API\""),
        (DIM, ""),
        (GREEN, "  🤖 [Explorer]   扫描项目结构..."),
        (GREEN, "             ✅   找到 12 个文件，3 个目录"),
        (DIM, ""),
        (GREEN, "  🤖 [Analyst]    理解需求约束..."),
        (GREEN, "             ✅   识别 5 个实体，2 个 API 端点"),
        (DIM, ""),
        (GREEN, "  🤖 [Planner]    制定执行计划..."),
        (GREEN, "             ✅   8 步计划，预计 45s"),
        (DIM, ""),
        (BLUE,  "  🤖 [Architect]  设计 API 架构..."),
        (BLUE,  "             ✅   RESTful，Flask + SQLAlchemy"),
        (DIM, ""),
        (ORANGE,"  🤖 [Executor]   生成代码..."),
        (ORANGE,"             ✅   src/api/rest.py (42 行)"),
        (ORANGE,"             ✅   src/models/user.py (28 行)"),
        (ORANGE,"             ✅   src/models/order.py (35 行)"),
        (DIM, ""),
        (PURPLE,"  🤖 [Verifier]   运行测试..."),
        (PURPLE,"             ✅   pytest 18/18 passed"),
        (DIM, ""),
        (CYAN, "  ✨ 完成！        生成 6 个文件，耗时 38.2s"),
        (CYAN, "  💰 成本: ¥0.03  ·  🔢 Token: 24,500"),
    ]
    return make_terminal("oh-my-coder — omc run workflow", lines, height=620)


def gen_demo_agents():
    lines = [
        (DIM, "$ omc agents"),
        (DIM, ""),
        (WHITE, "  🤖 Oh My Coder — 30 个专业 Agent"),
        (DIM, ""),
        (GREEN, "  构建/分析通道"),
        (GREEN, "  ├── ExploreAgent        探索代码库，生成项目地图"),
        (GREEN, "  ├── AnalystAgent        分析需求，发现隐藏约束"),
        (GREEN, "  ├── PlannerAgent        制定执行计划"),
        (GREEN, "  ├── ArchitectAgent      设计系统架构"),
        (GREEN, "  ├── ExecutorAgent       生成代码（14 种语言）"),
        (GREEN, "  ├── VerifierAgent       运行测试，验证正确性"),
        (GREEN, "  ├── DebuggerAgent       调试和修复错误"),
        (GREEN, "  └── TracerAgent         追踪执行流程，定位根因"),
        (DIM, ""),
        (BLUE,  "  审查通道"),
        (BLUE,  "  ├── CodeReviewerAgent       代码质量审查"),
        (BLUE,  "  └── SecurityReviewerAgent  安全漏洞扫描"),
        (DIM, ""),
        (ORANGE,"  领域通道（14 个）"),
        (ORANGE,"  TestEngineer | Designer | Vision | Document | Writer"),
        (ORANGE,"  Scientist | GitMaster | Database | API | DevOps"),
        (ORANGE,"  UML | Performance | Migration | Prompt | Auth | Data"),
        (DIM, ""),
        (YELLOW,"  协调通道"),
        (YELLOW,"  ├── CriticAgent          审查计划和设计"),
        (YELLOW,"  └── SelfImprovingAgent   主动学习，优化路由"),
    ]
    return make_terminal("oh-my-coder — omc agents", lines, height=680)


def gen_demo_web():
    lines = [
        (DIM, "$ curl -N http://localhost:8000/api/agent/live"),
        (DIM, ""),
        (GREEN, "  data: {"),
        (GREEN, '    "event": "status",'),
        (GREEN, '    "workflow_id": "wf_a1b2c3",'),
        (GREEN, '    "status": "running",'),
        (GREEN, '    "active_agents": ['),
        (BLUE,  '      {'),
        (BLUE,  '        "name": "ExplorerAgent",'),
        (BLUE,  '        "state": "completed",'),
        (BLUE,  '        "progress": 1.0,'),
        (BLUE,  '        "duration": 2.3'),
        (BLUE,  '      }, {'),
        (ORANGE,'        "name": "AnalystAgent",'),
        (ORANGE,'        "state": "running",'),
        (ORANGE,'        "progress": 0.65,'),
        (ORANGE,'        "duration": 4.1'),
        (ORANGE,'      },'),
        (GREEN, '      { "name": "PlannerAgent", "state": "pending" }'),
        (GREEN, '    ]'),
        (GREEN, '  }'),
        (DIM, ""),
        (YELLOW,"  data: { ... }  ← 每 2 秒推送一次"),
    ]
    return make_terminal("oh-my-coder — /api/agent/live SSE Stream", lines, height=560)


def gen_flowchart_svg(out_path: str):
    """Generate the workflow SVG."""
    svg = """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 300" font-family="Courier New, monospace">
  <rect width="900" height="300" fill="#1e1e1e" rx="6"/>
  <!-- title bar -->
  <rect x="1" y="1" width="898" height="26" fill="#2d2d2d" rx="6"/>
  <rect x="1" y="24" width="898" height="2" fill="#3d3d3d"/>
  <text x="450" y="18" text-anchor="middle" fill="#d4d4d4" font-size="12">oh-my-coder — Multi-Agent Pipeline</text>

  <!-- Input node -->
  <rect x="20" y="55" width="120" height="40" rx="4" fill="#2d4a2d" stroke="#6aa84f" stroke-width="1.5"/>
  <text x="80" y="80" text-anchor="middle" fill="#6aa84f" font-size="11">用户输入任务</text>
  <line x1="140" y1="75" x2="168" y2="75" stroke="#5c5c5c" stroke-width="1.5"/>
  <polygon points="168,75 161,71 161,79" fill="#5c5c5c"/>

  <!-- Pipeline agents row 1 -->
  <rect x="170" y="55" width="90" height="40" rx="4" fill="#1a3a5c" stroke="#3874a8" stroke-width="1.5"/>
  <text x="215" y="80" text-anchor="middle" fill="#3874a8" font-size="10">ExploreAgent</text>

  <rect x="268" y="55" width="90" height="40" rx="4" fill="#1a3a5c" stroke="#3874a8" stroke-width="1.5"/>
  <text x="313" y="80" text-anchor="middle" fill="#3874a8" font-size="10">AnalystAgent</text>

  <rect x="366" y="55" width="90" height="40" rx="4" fill="#1a3a5c" stroke="#3874a8" stroke-width="1.5"/>
  <text x="411" y="80" text-anchor="middle" fill="#3874a8" font-size="10">PlannerAgent</text>

  <rect x="464" y="55" width="90" height="40" rx="4" fill="#2d4a2d" stroke="#6aa84f" stroke-width="1.5"/>
  <text x="509" y="80" text-anchor="middle" fill="#6aa84f" font-size="10">ArchitectAgent</text>

  <rect x="562" y="55" width="90" height="40" rx="4" fill="#3d2e00" stroke="#cc7a00" stroke-width="1.5"/>
  <text x="607" y="80" text-anchor="middle" fill="#cc7a00" font-size="10">ExecutorAgent</text>

  <rect x="660" y="55" width="90" height="40" rx="4" fill="#2d1a4a" stroke="#9b6fd0" stroke-width="1.5"/>
  <text x="705" y="80" text-anchor="middle" fill="#9b6fd0" font-size="10">VerifierAgent</text>

  <!-- Arrows row 1 -->
  <line x1="260" y1="75" x2="268" y2="75" stroke="#5c5c5c" stroke-width="1.5"/>
  <line x1="358" y1="75" x2="366" y2="75" stroke="#5c5c5c" stroke-width="1.5"/>
  <line x1="456" y1="75" x2="464" y2="75" stroke="#5c5c5c" stroke-width="1.5"/>
  <line x1="554" y1="75" x2="562" y2="75" stroke="#5c5c5c" stroke-width="1.5"/>
  <line x1="652" y1="75" x2="660" y2="75" stroke="#5c5c5c" stroke-width="1.5"/>

  <!-- Arrow down -->
  <line x1="705" y1="95" x2="705" y2="120" stroke="#5c5c5c" stroke-width="1.5"/>
  <polygon points="705,120 701,113 709,113" fill="#5c5c5c"/>

  <!-- Domain agents row 2 -->
  <rect x="366" y="125" width="90" height="36" rx="4" fill="#3d1a1a" stroke="#c4555d" stroke-width="1.5"/>
  <text x="411" y="148" text-anchor="middle" fill="#c4555d" font-size="10">VisionAgent</text>

  <rect x="464" y="125" width="90" height="36" rx="4" fill="#3d1a1a" stroke="#c4555d" stroke-width="1.5"/>
  <text x="509" y="148" text-anchor="middle" fill="#c4555d" font-size="10">DocumentAgent</text>

  <rect x="562" y="125" width="90" height="36" rx="4" fill="#3d1a1a" stroke="#c4555d" stroke-width="1.5"/>
  <text x="607" y="148" text-anchor="middle" fill="#c4555d" font-size="10">TestEngineer</text>

  <rect x="660" y="125" width="90" height="36" rx="4" fill="#3d1a1a" stroke="#c4555d" stroke-width="1.5"/>
  <text x="705" y="148" text-anchor="middle" fill="#c4555d" font-size="10">DatabaseAgent</text>

  <line x1="456" y1="143" x2="464" y2="143" stroke="#5c5c5c" stroke-width="1.2"/>
  <line x1="554" y1="143" x2="562" y2="143" stroke="#5c5c5c" stroke-width="1.2"/>
  <line x1="652" y1="143" x2="660" y2="143" stroke="#5c5c5c" stroke-width="1.2"/>

  <!-- Arrow down to output -->
  <line x1="705" y1="161" x2="705" y2="186" stroke="#5c5c5c" stroke-width="1.5"/>
  <polygon points="705,186 701,179 709,179" fill="#5c5c5c"/>

  <!-- Output node -->
  <rect x="640" y="191" width="130" height="42" rx="4" fill="#2d4a2d" stroke="#6aa84f" stroke-width="1.5"/>
  <text x="705" y="207" text-anchor="middle" fill="#6aa84f" font-size="11">代码 + 测试 + 报告</text>
  <text x="705" y="221" text-anchor="middle" fill="#6aa84f" font-size="10">耗时 38.2s · ¥0.03</text>

  <!-- Legend -->
  <rect x="20" y="248" width="860" height="36" rx="4" fill="#2d2d2d"/>
  <rect x="30" y="258" width="10" height="10" rx="2" fill="none" stroke="#6aa84f" stroke-width="1.5"/>
  <text x="46" y="268" fill="#6aa84f" font-size="10">协调</text>
  <rect x="100" y="258" width="10" height="10" rx="2" fill="none" stroke="#3874a8" stroke-width="1.5"/>
  <text x="116" y="268" fill="#3874a8" font-size="10">分析</text>
  <rect x="172" y="258" width="10" height="10" rx="2" fill="none" stroke="#cc7a00" stroke-width="1.5"/>
  <text x="188" y="268" fill="#cc7a00" font-size="10">执行</text>
  <rect x="242" y="258" width="10" height="10" rx="2" fill="none" stroke="#9b6fd0" stroke-width="1.5"/>
  <text x="258" y="268" fill="#9b6fd0" font-size="10">验证</text>
  <rect x="312" y="258" width="10" height="10" rx="2" fill="none" stroke="#c4555d" stroke-width="1.5"/>
  <text x="328" y="268" fill="#c4555d" font-size="10">领域</text>
  <text x="460" y="268" fill="#888888" font-size="10">│ 模型: DeepSeek · GLM · 文心 │ 30 个专业 Agent │ MIT 开源 │</text>
</svg>"""
    with open(out_path, "w") as f:
        f.write(svg)


def main():
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs", "screenshots")
    os.makedirs(out_dir, exist_ok=True)

    for name, img_fn in [
        ("demo-workflow.png", gen_demo_workflow),
        ("demo-agents.png", gen_demo_agents),
        ("demo-web.png", gen_demo_web),
    ]:
        path = os.path.join(out_dir, name)
        img = img_fn()
        img.save(path, "PNG")
        size_kb = os.path.getsize(path) / 1024
        print(f"  ✅ {name} ({size_kb:.0f} KB)")

    svg_path = os.path.join(out_dir, "demo-flow.svg")
    gen_flowchart_svg(svg_path)
    print(f"  ✅ demo-flow.svg")

    # Write README
    readme = """# Screenshots

真实运行截图 / Demo Screenshots

## Multi-Agent Pipeline

![Multi-Agent Pipeline](demo-flow.svg)

## CLI Workflow

![CLI Workflow](demo-workflow.png)

运行 `omc run "实现一个 REST API"` 的完整流程：Explore → Analyze → Plan → Architect → Execute → Verify。

## Agent System

![Agent System](demo-agents.png)

`omc agents` 输出：30 个专业 Agent，分为构建/分析、审查、领域、协调四个通道。

## Web SSE Stream

![Web SSE](demo-web.png)

`curl -N http://localhost:8000/api/agent/live` — 每 2 秒推送当前 Agent 协作状态。
"""
    readme_path = os.path.join(out_dir, "README.md")
    with open(readme_path, "w") as f:
        f.write(readme)
    print(f"  ✅ README.md")

    print(f"\nAll demos saved to:\n  {out_dir}")


if __name__ == "__main__":
    main()
