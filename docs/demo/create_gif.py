#!/usr/bin/env python3
"""
Oh My Coder Demo GIF Generator
将帧合成为 GIF 动画
"""

from PIL import Image
import os

def create_gif():
    """创建演示 GIF"""
    frames_dir = os.path.expanduser("~/.qclaw/workspace-agent-bf627e2b/projects/oh-my-coder/docs/demo/frames")
    output_path = os.path.expanduser("~/.qclaw/workspace-agent-bf627e2b/projects/oh-my-coder/docs/demo/oh-my-coder-demo.gif")
    
    # 帧文件列表（按顺序）
    frame_files = [
        "frame_001_intro.png",
        "frame_002_install.png",
        "frame_003_config.png",
        "frame_004_explore.png",
        "frame_005_build.png",
        "frame_006_agents.png",
        "frame_007_summary.png",
    ]
    
    # 每帧持续时间（毫秒）
    # 总时长约 3 分钟 = 180 秒 = 180000 毫秒
    # 分配到 7 帧，平均每帧约 25 秒
    durations = [
        5000,   # intro: 5秒
        4000,   # install: 4秒
        4000,   # config: 4秒
        6000,   # explore: 6秒
        8000,   # build: 8秒
        6000,   # agents: 6秒
        5000,   # summary: 5秒
    ]
    
    images = []
    for filename in frame_files:
        filepath = os.path.join(frames_dir, filename)
        img = Image.open(filepath)
        # 转换为 RGB 模式（GIF 需要）
        if img.mode != 'RGB':
            img = img.convert('RGB')
        images.append(img)
        print(f"📷 Loaded: {filename}")
    
    # 保存为 GIF
    images[0].save(
        output_path,
        save_all=True,
        append_images=images[1:],
        duration=durations,
        loop=0,  # 无限循环
        optimize=True,
    )
    
    print(f"\n🎬 GIF saved: {output_path}")
    
    # 获取文件大小
    file_size = os.path.getsize(output_path)
    print(f"📦 File size: {file_size / 1024:.1f} KB")
    
    # 计算总时长
    total_duration = sum(durations) / 1000
    print(f"⏱️  Total duration: {total_duration:.1f} seconds")

def create_small_gif():
    """创建小尺寸 GIF（用于 README）"""
    frames_dir = os.path.expanduser("~/.qclaw/workspace-agent-bf627e2b/projects/oh-my-coder/docs/demo/frames")
    output_path = os.path.expanduser("~/.qclaw/workspace-agent-bf627e2b/projects/oh-my-coder/docs/demo/oh-my-coder-demo-small.gif")
    
    frame_files = [
        "frame_001_intro.png",
        "frame_002_install.png",
        "frame_003_config.png",
        "frame_004_explore.png",
        "frame_005_build.png",
        "frame_006_agents.png",
        "frame_007_summary.png",
    ]
    
    durations = [3000, 2500, 2500, 4000, 5000, 4000, 3000]
    
    images = []
    target_width = 800  # 缩小到 800px 宽
    
    for filename in frame_files:
        filepath = os.path.join(frames_dir, filename)
        img = Image.open(filepath)
        
        # 计算新尺寸
        ratio = target_width / img.width
        target_height = int(img.height * ratio)
        
        # 缩小图片
        img_small = img.resize((target_width, target_height), Image.Resampling.LANCZOS)
        
        if img_small.mode != 'RGB':
            img_small = img_small.convert('RGB')
        
        images.append(img_small)
        print(f"📷 Resized: {filename} -> {target_width}x{target_height}")
    
    images[0].save(
        output_path,
        save_all=True,
        append_images=images[1:],
        duration=durations,
        loop=0,
        optimize=True,
    )
    
    print(f"\n🎬 Small GIF saved: {output_path}")
    file_size = os.path.getsize(output_path)
    print(f"📦 File size: {file_size / 1024:.1f} KB")

if __name__ == "__main__":
    print("🎨 Generating demo GIFs...\n")
    
    print("=" * 50)
    print("Generating full-size GIF...")
    print("=" * 50)
    create_gif()
    
    print("\n" + "=" * 50)
    print("Generating small GIF...")
    print("=" * 50)
    create_small_gif()
    
    print("\n✅ All GIFs generated successfully!")
