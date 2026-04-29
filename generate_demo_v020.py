#!/usr/bin/env python3
"""
Oh My Coder v0.2.0 Demo Video Generator
生成 60-90 秒演示视频 (1080p MP4)
使用 OpenCV 直接编码
"""
import cv2
import numpy as np
from pathlib import Path

# ============================================================
# 配置
# ============================================================
W, H = 1920, 1080  # 1080p
FPS = 30
OUTPUT = Path(__file__).parent / "docs/screenshots/demo-v0.2.0.mp4"

# 颜色 (BGR)
BG = (23, 17, 13)  # #0d1117
TITLE_BAR = (34, 27, 22)  # #161b22
GREEN = (80, 185, 63)  # #3fb950
ORANGE = (62, 136, 240)  # #f0883e
CYAN = (221, 212, 86)  # #56d4dd
PURPLE = (255, 168, 210)  # #d2a8ff
YELLOW = (65, 179, 227)  # #e3b341
WHITE = (217, 209, 201)  # #c9d1d9
DIM = (158, 148, 139)  # #8b949e
BLUE = (235, 111, 31)  # #1f6feb

# 字体
FONT = cv2.FONT_HERSHEY_SIMPLEX
FONT_D = cv2.FONT_HERSHEY_DUPLEX

# ============================================================
# 工具函数
# ============================================================
def new_frame():
    """创建新帧"""
    return np.zeros((H, W, 3), dtype=np.uint8)
    img[:] = BG
    return img

def draw_text(img, text, x, y, font_scale=1, color=WHITE, thickness=2):
    """绘制文字"""
    cv2.putText(img, text, (x, y), FONT, font_scale, color, thickness, cv2.LINE_AA)

def draw_text_centered(img, text, y, font_scale=1, color=WHITE, thickness=2):
    """居中绘制文字"""
    size = cv2.getTextSize(text, FONT, font_scale, thickness)[0]
    x = (W - size[0]) // 2
    cv2.putText(img, text, (x, y), FONT, font_scale, color, thickness, cv2.LINE_AA)

def ease_in_out(t):
    """缓动函数"""
    return t * t * (3 - 2 * t)

def draw_terminal(img, title, lines, y_offset=200):
    """绘制终端窗口"""
    # 终端背景
    cv2.rectangle(img, (100, y_offset), (W-100, y_offset+500), TITLE_BAR, -1)
    cv2.rectangle(img, (100, y_offset), (W-100, y_offset+40), (45, 35, 30), -1)
    
    # 窗口按钮
    cv2.circle(img, (130, y_offset+20), 8, (70, 87, 210), -1)  # 红
    cv2.circle(img, (155, y_offset+20), 8, (61, 191, 245), -1)  # 黄
    cv2.circle(img, (180, y_offset+20), 8, (80, 185, 63), -1)  # 绿
    
    # 标题
    draw_text(img, title, W//2-80, y_offset+28, 0.6, DIM, 1)
    
    # 内容行
    for i, (text, color) in enumerate(lines):
        draw_text(img, text, 130, y_offset + 80 + i*35, 0.6, color, 1)

# ============================================================
# 场景生成
# ============================================================
def scene_intro(frames, duration=5):
    """开场 (5秒)"""
    total = duration * FPS
    for i in range(total):
        img = new_frame()
        progress = ease_in_out(i / total)
        
        # 标题
        alpha = min(1, progress * 2)
        if alpha > 0:
            draw_text_centered(img, "oh-my-coder", 350, 3, WHITE, 6)
            draw_text_centered(img, "v0.2.0", 430, 1.5, GREEN, 3)
        
        # 副标题
        if progress > 0.3:
            sub_alpha = min(1, (progress - 0.3) * 2)
            draw_text_centered(img, "32 Agents  ·  VS Code Extension  ·  Self-Improving", 550, 1.2, DIM, 2)
        
        frames.append(img)

def scene_agents_list(frames, duration=10):
    """Agents 列表展示 (10秒)"""
    agents = [
        ("BUILD Channel:", GREEN),
        ("  Planner, Architect, Executor, Verifier", WHITE),
        ("  CodeSimplifier, Migration", WHITE),
        ("", WHITE),
        ("REVIEW Channel:", ORANGE),
        ("  CodeReviewer, SecurityReviewer, Critic", WHITE),
        ("  Performance", WHITE),
        ("", WHITE),
        ("DEBUG Channel:", CYAN),
        ("  Debugger, Tracer", WHITE),
        ("", WHITE),
        ("DOMAIN Channel:", PURPLE),
        ("  TestEngineer, QATester, Designer, Writer", WHITE),
        ("  Document, Scientist, GitMaster, Explore", WHITE),
        ("  Vision, UML, Analyst, Database, DevOps", WHITE),
        ("  API, Auth, Data, Prompt, SkillManage", WHITE),
        ("  SelfImproving", GREEN),
    ]
    
    total = duration * FPS
    for i in range(total):
        img = new_frame()
        
        # 标题
        draw_text_centered(img, "$ omc agents list", 150, 1.2, GREEN, 2)
        
        # 终端窗口
        lines_to_show = min(len(agents), int(i / (total / len(agents)) * 1.5) + 1)
        terminal_lines = agents[:lines_to_show]
        draw_terminal(img, "Terminal — omc agents list", terminal_lines, 200)
        
        # 统计
        if i > total * 0.8:
            draw_text_centered(img, "32 Agents Ready", 800, 1.5, GREEN, 3)
        
        frames.append(img)

def scene_workflow(frames, duration=15):
    """工作流执行 (15秒)"""
    steps = [
        ("$ omc run --workflow code-review --file src/example.py", GREEN),
        ("", WHITE),
        ("[Planner] Analyzing task requirements...", DIM),
        ("[Architect] Designing review strategy...", DIM),
        ("[CodeReviewer] Scanning code patterns...", CYAN),
        ("  → Found 3 style issues", YELLOW),
        ("  → Found 1 potential bug", ORANGE),
        ("[SecurityReviewer] Checking vulnerabilities...", CYAN),
        ("  → No critical issues found", GREEN),
        ("[Critic] Generating improvement suggestions...", DIM),
        ("", WHITE),
        ("✓ Review Complete: 4 findings", GREEN),
        ("  - Style: Use f-strings instead of % formatting", YELLOW),
        ("  - Bug: Unhandled exception on line 42", ORANGE),
        ("  - Suggestion: Add type hints to improve clarity", DIM),
    ]
    
    total = duration * FPS
    for i in range(total):
        img = new_frame()
        draw_text_centered(img, "Multi-Agent Workflow", 150, 1.2, GREEN, 2)
        
        lines_to_show = min(len(steps), int(i / (total / len(steps)) * 1.2) + 1)
        terminal_lines = [(s[0], s[1] if len(s) > 1 else WHITE) for s in steps[:lines_to_show]]
        draw_terminal(img, "Terminal — omc run", terminal_lines, 200)
        
        frames.append(img)

def scene_vscode(frames, duration=15):
    """VS Code 插件展示 (15秒)"""
    total = duration * FPS
    for i in range(total):
        img = new_frame()
        
        # VS Code 风格窗口
        cv2.rectangle(img, (50, 100), (W-50, H-100), (30, 30, 30), -1)
        
        # 侧边栏
        cv2.rectangle(img, (50, 100), (350, H-100), (40, 40, 40), -1)
        draw_text(img, "OH-MY-CODER", 70, 150, 0.7, WHITE, 2)
        draw_text(img, "Agents (32)", 70, 200, 0.6, DIM, 1)
        
        # Agent 列表
        agents = ["Planner", "Architect", "Executor", "CodeReviewer", "Debugger"]
        for j, agent in enumerate(agents):
            color = GREEN if j == int(i / FPS) % len(agents) else DIM
            draw_text(img, f"  {agent}", 70, 250 + j*30, 0.5, color, 1)
        
        # 主编辑区
        draw_text(img, "Task Input", 400, 150, 0.7, WHITE, 1)
        cv2.rectangle(img, (380, 180), (W-80, 280), (50, 50, 50), -1)
        draw_text(img, "Review this code for security issues...", 400, 240, 0.5, WHITE, 1)
        
        # 按钮
        cv2.rectangle(img, (380, 320), (600, 360), (80, 185, 63), -1)
        draw_text(img, "Run Task", 430, 348, 0.6, WHITE, 2)
        
        # 状态栏
        cv2.rectangle(img, (50, H-80), (W-50, H-100), (20, 80, 200), -1)
        draw_text(img, "Model: deepseek-chat | Status: Ready", 70, H-85, 0.5, WHITE, 1)
        
        frames.append(img)

def scene_local_models(frames, duration=10):
    """本地模型支持 (10秒)"""
    models = [
        ("$ omc local status", GREEN),
        ("", WHITE),
        ("Ollama Models Detected:", CYAN),
        ("  ✓ llama3.2:latest (4.7GB)", GREEN),
        ("  ✓ qwen2.5:7b (4.4GB)", GREEN),
        ("  ✓ deepseek-coder:6.7b (3.8GB)", GREEN),
        ("", WHITE),
        ("Cloud Models Available:", CYAN),
        ("  • deepseek-chat (API)", DIM),
        ("  • glm-4-flash (FREE)", DIM),
        ("  • qwen-turbo (API)", DIM),
        ("", WHITE),
        ("Total: 6 models ready", GREEN),
    ]
    
    total = duration * FPS
    for i in range(total):
        img = new_frame()
        draw_text_centered(img, "Local Model Support", 150, 1.2, GREEN, 2)
        
        lines_to_show = min(len(models), int(i / (total / len(models)) * 1.5) + 1)
        terminal_lines = [(m[0], m[1] if len(m) > 1 else WHITE) for m in models[:lines_to_show]]
        draw_terminal(img, "Terminal — omc local status", terminal_lines, 200)
        
        frames.append(img)

def scene_self_improving(frames, duration=10):
    """自进化系统 (10秒)"""
    content = [
        ("$ omc learn --show", GREEN),
        ("", WHITE),
        ("Learning Records:", CYAN),
        ("  [2026-04-29] Improved routing accuracy +5%", GREEN),
        ("  [2026-04-28] Optimized agent selection", GREEN),
        ("  [2026-04-27] Added 12 new patterns", GREEN),
        ("", WHITE),
        ("Self-Improvement Suggestions:", YELLOW),
        ("  → Add more test cases for edge cases", DIM),
        ("  → Fine-tune CodeReviewer thresholds", DIM),
        ("", WHITE),
        ("System Status: Actively Learning", GREEN),
    ]
    
    total = duration * FPS
    for i in range(total):
        img = new_frame()
        draw_text_centered(img, "Self-Improving System", 150, 1.2, GREEN, 2)
        
        lines_to_show = min(len(content), int(i / (total / len(content)) * 1.5) + 1)
        terminal_lines = [(c[0], c[1] if len(c) > 1 else WHITE) for c in content[:lines_to_show]]
        draw_terminal(img, "Terminal — omc learn --show", terminal_lines, 200)
        
        frames.append(img)

def scene_outro(frames, duration=5):
    """结尾 (5秒)"""
    total = duration * FPS
    for i in range(total):
        img = new_frame()
        progress = ease_in_out(i / total)
        
        draw_text_centered(img, "github.com/VOBC/oh-my-coder", 400, 1.5, WHITE, 3)
        draw_text_centered(img, "pip install oh-my-coder", 500, 1.2, GREEN, 2)
        
        if progress > 0.5:
            draw_text_centered(img, "Star us on GitHub!", 600, 1, YELLOW, 2)
        
        frames.append(img)

# ============================================================
# 主函数
# ============================================================
def main():
    print("生成 Demo 视频...")
    frames = []
    
    print("  1/7 开场...")
    scene_intro(frames, 5)
    
    print("  2/7 Agents 列表...")
    scene_agents_list(frames, 10)
    
    print("  3/7 工作流演示...")
    scene_workflow(frames, 15)
    
    print("  4/7 VS Code 插件...")
    scene_vscode(frames, 15)
    
    print("  5/7 本地模型...")
    scene_local_models(frames, 10)
    
    print("  6/7 自进化系统...")
    scene_self_improving(frames, 10)
    
    print("  7/7 结尾...")
    scene_outro(frames, 5)
    
    print(f"总帧数: {len(frames)}, 时长: {len(frames)/FPS:.1f}秒")
    
    # 保存视频
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(str(OUTPUT), fourcc, FPS, (W, H))
    
    for i, frame in enumerate(frames):
        out.write(frame)
        if i % 100 == 0:
            print(f"  写入帧 {i}/{len(frames)}...")
    
    out.release()
    print(f"✓ 视频已保存: {OUTPUT}")
    print(f"  文件大小: {OUTPUT.stat().st_size / 1024 / 1024:.1f} MB")

if __name__ == "__main__":
    main()
