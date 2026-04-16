#!/usr/bin/env python3
"""
Oh My Coder Demo Video Frame Generator
使用 PIL 生成演示视频的关键帧
"""

from PIL import Image, ImageDraw, ImageFont
import os

# 配置
WIDTH, HEIGHT = 1920, 1080
BG_COLOR = (30, 30, 30)  # #1e1e1e
TEXT_COLOR = (212, 212, 212)  # #d4d4d4
BLUE = (79, 193, 255)  # #4fc1ff
GREEN = (78, 201, 176)  # #4ec9b0
YELLOW = (220, 220, 170)  # #dcdcaa
ORANGE = (206, 145, 120)  # #ce9178
GRAY = (128, 128, 128)
DARK_GRAY = (60, 60, 60)

def get_font(size=24, bold=False):
    """获取字体"""
    try:
        # macOS 常用字体
        if bold:
            return ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", size)
        return ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", size)
    except:
        try:
            return ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", size)
        except:
            return ImageFont.load_default()

def create_base_image():
    """创建基础背景"""
    img = Image.new('RGB', (WIDTH, HEIGHT), BG_COLOR)
    return img

def draw_terminal_frame(img, title="Terminal", content_lines=None):
    """绘制终端窗口框架"""
    draw = ImageDraw.Draw(img)
    
    # 终端窗口背景
    margin = 100
    draw.rounded_rectangle(
        [margin, margin, WIDTH - margin, HEIGHT - margin],
        radius=10,
        fill=(40, 40, 40),
        outline=DARK_GRAY,
        width=2
    )
    
    # 标题栏
    draw.rounded_rectangle(
        [margin, margin, WIDTH - margin, margin + 40],
        radius=10,
        fill=(50, 50, 50)
    )
    # 标题栏底部直线（覆盖圆角底部）
    draw.rectangle([margin, margin + 30, WIDTH - margin, margin + 40], fill=(50, 50, 50))
    
    # 窗口按钮
    btn_y = margin + 12
    for i, color in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        draw.ellipse([margin + 15 + i * 25, btn_y, margin + 27 + i * 25, btn_y + 12], fill=color)
    
    # 标题文字
    font = get_font(16)
    draw.text((WIDTH // 2 - 40, margin + 10), title, font=font, fill=TEXT_COLOR)
    
    return img

def frame_001_intro():
    """开场 Logo 帧"""
    img = create_base_image()
    draw = ImageDraw.Draw(img)
    
    # 大 Logo
    logo_text = "🤖"
    font_large = get_font(120)
    bbox = draw.textbbox((0, 0), logo_text, font=font_large)
    logo_width = bbox[2] - bbox[0]
    draw.text((WIDTH // 2 - logo_width // 2, 200), logo_text, font=font_large, fill=BLUE)
    
    # 标题
    title = "Oh My Coder"
    font_title = get_font(64, bold=True)
    bbox = draw.textbbox((0, 0), title, font=font_title)
    title_width = bbox[2] - bbox[0]
    draw.text((WIDTH // 2 - title_width // 2, 400), title, font=font_title, fill=TEXT_COLOR)
    
    # 副标题
    subtitle = "多智能体 AI 编程助手"
    font_sub = get_font(36)
    bbox = draw.textbbox((0, 0), subtitle, font=font_sub)
    sub_width = bbox[2] - bbox[0]
    draw.text((WIDTH // 2 - sub_width // 2, 500), subtitle, font=font_sub, fill=GRAY)
    
    # 特性标签
    features = [
        ("✨ 12 家国产大模型", 600),
        ("🤖 30 个专业 Agent", 660),
        ("💰 GLM-4.7-Flash 完全免费", 720),
    ]
    font_feat = get_font(28)
    for text, y in features:
        bbox = draw.textbbox((0, 0), text, font=font_feat)
        text_width = bbox[2] - bbox[0]
        draw.text((WIDTH // 2 - text_width // 2, y), text, font=font_feat, fill=GREEN)
    
    # 版本号
    version = "v0.1.0"
    font_ver = get_font(20)
    bbox = draw.textbbox((0, 0), version, font=font_ver)
    ver_width = bbox[2] - bbox[0]
    draw.text((WIDTH // 2 - ver_width // 2, 850), version, font=font_ver, fill=GRAY)
    
    return img

def frame_002_install():
    """安装演示帧"""
    img = create_base_image()
    img = draw_terminal_frame(img, "Terminal - Install")
    draw = ImageDraw.Draw(img)
    
    font = get_font(22)
    font_bold = get_font(22, bold=True)
    
    lines = [
        ("$ ", BLUE),
        ("pip install oh-my-coder", TEXT_COLOR),
    ]
    
    y = 180
    x = 150
    for text, color in lines:
        draw.text((x, y), text, font=font_bold if color == BLUE else font, fill=color)
        bbox = draw.textbbox((0, 0), text, font=font_bold if color == BLUE else font)
        x += bbox[2] - bbox[0]
    
    # 输出内容
    y = 240
    outputs = [
        "Collecting oh-my-coder",
        "  Downloading oh-my-coder-0.1.0.tar.gz (45 kB)",
        "     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 45.0/45.0 kB",
        "  Preparing metadata (setup.py) ... done",
        "Building wheels for collected packages: oh-my-coder",
        "  Building wheel for oh-my-coder (setup.py) ... done",
        "Successfully installed oh-my-coder-0.1.0",
        "",
        "$ omc --version",
        "oh-my-coder 0.1.0",
    ]
    
    for i, line in enumerate(outputs):
        if i == len(outputs) - 1:  # 最后一行高亮
            draw.text((150, y), line, font=font_bold, fill=GREEN)
        else:
            draw.text((150, y), line, font=font, fill=GRAY if i < 6 else TEXT_COLOR)
        y += 35
    
    # 成功提示
    y += 20
    draw.text((150, y), "✅ 安装成功！", font=get_font(28, bold=True), fill=GREEN)
    
    return img

def frame_003_config():
    """配置演示帧"""
    img = create_base_image()
    img = draw_terminal_frame(img, "Terminal - Config")
    draw = ImageDraw.Draw(img)
    
    font = get_font(22)
    font_bold = get_font(22, bold=True)
    
    # 命令
    y = 180
    draw.text((150, y), "$ ", font=font_bold, fill=BLUE)
    draw.text((180, y), "omc config set -k GLM_API_KEY -v \"free\"", font=font, fill=TEXT_COLOR)
    
    # 输出
    y = 250
    outputs = [
        ("✅ 配置已保存", GREEN),
        ("", TEXT_COLOR),
        ("   Key: GLM_API_KEY", TEXT_COLOR),
        ("   Value: free", TEXT_COLOR),
        ("   Model: glm-4-flash (完全免费)", GREEN),
        ("", TEXT_COLOR),
        ("$ omc config show", TEXT_COLOR),
        ("", TEXT_COLOR),
        ("📋 当前配置:", ORANGE),
        ("   默认模型: glm", TEXT_COLOR),
        ("   API Key: 已配置 (GLM-4.7-Flash 免费版)", GREEN),
        ("   工作目录: /home/user/project", TEXT_COLOR),
        ("", TEXT_COLOR),
        ("💡 提示: GLM-4.7-Flash 完全免费，无需付费即可使用！", YELLOW),
    ]
    
    for text, color in outputs:
        draw.text((150, y), text, font=font, fill=color)
        y += 32
    
    return img

def frame_004_explore():
    """代码探索帧"""
    img = create_base_image()
    img = draw_terminal_frame(img, "Terminal - Explore")
    draw = ImageDraw.Draw(img)
    
    font = get_font(20)
    font_bold = get_font(20, bold=True)
    
    # 命令
    y = 160
    draw.text((130, y), "$ ", font=font_bold, fill=BLUE)
    draw.text((155, y), "omc run \"解释这段代码\" --workflow explore --file main.py", font=font, fill=TEXT_COLOR)
    
    # 输出
    y = 220
    outputs = [
        ("🚀 Oh My Coder", ORANGE),
        ("任务: 解释这段代码", TEXT_COLOR),
        ("工作流: explore", TEXT_COLOR),
        ("", TEXT_COLOR),
        ("✅ ExploreAgent    → 发现 3 个模块，12 个函数", GREEN),
        ("✅ AnalystAgent    → 识别 FastAPI 应用结构", GREEN),
        ("", TEXT_COLOR),
        ("📊 代码结构:", ORANGE),
        ("   ├── main.py          # 应用入口", TEXT_COLOR),
        ("   ├── routers/", TEXT_COLOR),
        ("   │   ├── users.py     # 用户路由", TEXT_COLOR),
        ("   │   └── items.py     # 商品路由", TEXT_COLOR),
        ("   └── models/", TEXT_COLOR),
        ("       └── database.py  # 数据库模型", TEXT_COLOR),
        ("", TEXT_COLOR),
        ("💡 这是一个 FastAPI REST API 项目，实现了用户管理和商品管理功能。", YELLOW),
    ]
    
    for text, color in outputs:
        draw.text((130, y), text, font=font, fill=color)
        y += 28
    
    return img

def frame_005_build():
    """代码生成帧"""
    img = create_base_image()
    img = draw_terminal_frame(img, "Terminal - Build")
    draw = ImageDraw.Draw(img)
    
    font = get_font(18)
    font_bold = get_font(18, bold=True)
    
    # 命令
    y = 140
    draw.text((120, y), "$ ", font=font_bold, fill=BLUE)
    draw.text((145, y), "omc run \"为用户模块添加分页查询接口\" --workflow build", font=font, fill=TEXT_COLOR)
    
    # Agent 执行流程
    y = 190
    agents = [
        ("✅ ExploreAgent", "2.3s", "1,200"),
        ("✅ AnalystAgent", "5.1s", "3,500"),
        ("✅ ArchitectAgent", "8.2s", "5,200"),
        ("✅ ExecutorAgent", "15.7s", "12,000"),
        ("✅ VerifierAgent", "10.3s", "4,800"),
    ]
    
    draw.text((120, y), "Agent 执行流程:", font=font_bold, fill=ORANGE)
    y += 35
    
    for agent, time, tokens in agents:
        draw.text((120, y), f"{agent:20} → {time:>6} | {tokens:>6} tokens", font=font, fill=GREEN)
        y += 30
    
    # 生成文件
    y += 20
    draw.text((120, y), "✨ 已生成文件:", font=font_bold, fill=GREEN)
    y += 35
    draw.text((140, y), "routers/users.py    (+45 行)", font=font, fill=TEXT_COLOR)
    y += 28
    draw.text((140, y), "tests/test_users.py (+38 行)", font=font, fill=TEXT_COLOR)
    
    # 统计信息
    y += 40
    stats = [
        ("⏱️  总耗时: 41.6s", TEXT_COLOR),
        ("💰 总成本: ¥0.03 (GLM-4.7-Flash 免费)", GREEN),
        ("🔢 总 Token: 26,700", TEXT_COLOR),
    ]
    
    for text, color in stats:
        draw.text((120, y), text, font=get_font(22, bold=True), fill=color)
        y += 38
    
    return img

def frame_006_agents():
    """Agent 协作可视化帧"""
    img = create_base_image()
    draw = ImageDraw.Draw(img)
    
    font_title = get_font(36, bold=True)
    font = get_font(20)
    font_bold = get_font(20, bold=True)
    
    # 标题
    title = "🤖 Agent 协作流程"
    bbox = draw.textbbox((0, 0), title, font=font_title)
    title_width = bbox[2] - bbox[0]
    draw.text((WIDTH // 2 - title_width // 2, 80), title, font=font_title, fill=TEXT_COLOR)
    
    # Agent 节点
    agents = [
        ("🧭 ExploreAgent", "探索项目结构", GREEN),
        ("📊 AnalystAgent", "分析需求", GREEN),
        ("🏗️  ArchitectAgent", "设计 API 接口", GREEN),
        ("⚡ ExecutorAgent", "生成代码", GREEN),
        ("✅ VerifierAgent", "运行测试", GREEN),
    ]
    
    box_width = 500
    box_height = 80
    start_x = WIDTH // 2 - box_width // 2
    start_y = 180
    gap = 30
    
    for i, (name, desc, color) in enumerate(agents):
        y = start_y + i * (box_height + gap)
        
        # 节点背景
        draw.rounded_rectangle(
            [start_x, y, start_x + box_width, y + box_height],
            radius=10,
            fill=(50, 50, 50),
            outline=color,
            width=3
        )
        
        # Agent 名称
        draw.text((start_x + 20, y + 15), name, font=font_bold, fill=color)
        # 描述
        draw.text((start_x + 20, y + 45), desc, font=font, fill=GRAY)
        
        # 箭头（除了最后一个）
        if i < len(agents) - 1:
            arrow_y = y + box_height + 5
            # 箭头
            draw.polygon([
                (WIDTH // 2, arrow_y + 20),
                (WIDTH // 2 - 10, arrow_y),
                (WIDTH // 2 + 10, arrow_y),
            ], fill=GRAY)
    
    # 完成提示
    final_y = start_y + len(agents) * (box_height + gap) + 20
    draw.text((WIDTH // 2 - 100, final_y), "🎉 任务完成！", font=get_font(32, bold=True), fill=GREEN)
    
    return img

def frame_007_summary():
    """总结帧"""
    img = create_base_image()
    draw = ImageDraw.Draw(img)
    
    font_title = get_font(42, bold=True)
    font = get_font(24)
    font_bold = get_font(24, bold=True)
    
    # 标题
    title = "🎯 为什么选择 Oh My Coder?"
    bbox = draw.textbbox((0, 0), title, font=font_title)
    title_width = bbox[2] - bbox[0]
    draw.text((WIDTH // 2 - title_width // 2, 100), title, font=font_title, fill=TEXT_COLOR)
    
    # 特性列表
    features = [
        ("✅ 12 家国产大模型支持", GREEN),
        ("✅ 30 个专业 Agent 协作", GREEN),
        ("✅ GLM-4.7-Flash 完全免费", GREEN),
        ("✅ 中文优先，本土优化", GREEN),
        ("✅ 完全开源，MIT 协议", GREEN),
    ]
    
    y = 220
    for text, color in features:
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        draw.text((WIDTH // 2 - text_width // 2, y), text, font=font, fill=color)
        y += 50
    
    # 安装命令
    y += 40
    draw.text((WIDTH // 2 - 200, y), "📦 安装命令:", font=font_bold, fill=ORANGE)
    y += 45
    
    cmd = "pip install oh-my-coder"
    bbox = draw.textbbox((0, 0), cmd, font=get_font(32, bold=True))
    cmd_width = bbox[2] - bbox[0]
    draw.text((WIDTH // 2 - cmd_width // 2, y), cmd, font=get_font(32, bold=True), fill=BLUE)
    
    # GitHub 链接
    y += 100
    github = "🌟 GitHub: github.com/VOBC/oh-my-coder"
    bbox = draw.textbbox((0, 0), github, font=font)
    github_width = bbox[2] - bbox[0]
    draw.text((WIDTH // 2 - github_width // 2, y), github, font=font, fill=GRAY)
    
    return img

def generate_all_frames():
    """生成所有帧"""
    output_dir = os.path.expanduser("~/.qclaw/workspace-agent-bf627e2b/projects/oh-my-coder/docs/demo/frames")
    os.makedirs(output_dir, exist_ok=True)
    
    frames = [
        ("frame_001_intro.png", frame_001_intro),
        ("frame_002_install.png", frame_002_install),
        ("frame_003_config.png", frame_003_config),
        ("frame_004_explore.png", frame_004_explore),
        ("frame_005_build.png", frame_005_build),
        ("frame_006_agents.png", frame_006_agents),
        ("frame_007_summary.png", frame_007_summary),
    ]
    
    for filename, func in frames:
        filepath = os.path.join(output_dir, filename)
        img = func()
        img.save(filepath, "PNG")
        print(f"✅ Generated: {filename}")
    
    print(f"\n🎉 All frames saved to: {output_dir}")

if __name__ == "__main__":
    generate_all_frames()
