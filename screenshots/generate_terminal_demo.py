#!/usr/bin/env python3
"""Generate a terminal execution demo GIF for oh-my-coder CLI."""

import os

from PIL import Image, ImageDraw, ImageFont

# Config
OUTPUT_PATH = "/Users/vobc/.qclaw/workspace-agent-bf627e2b/docs/screenshots/demo.gif"
WIDTH, HEIGHT = 800, 450
FPS = 12
DURATION_MS = int(1000 / FPS)
FRAMES = 90  # 7.5 seconds at 12fps

# Colors (terminal style)
BG_COLOR = (30, 32, 34)  # Dark background
TEXT_COLOR = (192, 197, 206)  # Light gray text
PROMPT_COLOR = (121, 192, 255)  # Blue prompt
CMD_COLOR = (152, 195, 121)  # Green command
OUTPUT_COLOR = (190, 190, 197)  # Gray output
SUCCESS_COLOR = (152, 195, 121)  # Green success

# Terminal lines to animate
TERMINAL_LINES = [
    {"type": "prompt", "text": "➜ ~ "},
    {"type": "command", "text": "omc ask --model gpt-4.1 'how to center a div?'"},
    {"type": "output", "text": ""},
    {"type": "output", "text": "🤖 Thinking..."},
    {"type": "output", "text": ""},
    {"type": "output", "text": "Use CSS flexbox:"},
    {"type": "output", "text": "  .container {"},
    {"type": "output", "text": "    display: flex;"},
    {"type": "output", "text": "    justify-content: center;"},
    {"type": "output", "text": "    align-items: center;"},
    {"type": "output", "text": "  }"},
    {"type": "output", "text": ""},
    {"type": "output", "text": "✓ Generated in 1.2s (3 tokens/sec)"},
    {"type": "prompt", "text": "➜ ~ "},
    {"type": "command", "text": "omc run 'hello world' --model gpt-4o-mini"},
    {"type": "output", "text": ""},
    {"type": "output", "text": "⚡ Running in sandbox..."},
    {"type": "output", "text": "Output:"},
    {"type": "output", "text": "  hello world"},
    {"type": "output", "text": ""},
    {"type": "output", "text": "✓ Exit code: 0"},
    {"type": "prompt", "text": "➜ ~ "},
    {"type": "command", "text": "omc chat --expert frontend"},
    {"type": "output", "text": ""},
    {"type": "output", "text": "👋 Frontend Expert Mode activated"},
    {"type": "output", "text": "  Models: gpt-4.1, claude-sonnet-4-20250514"},
    {"type": "output", "text": ""},
    {"type": "prompt", "text": "➜ ~ "},
]


def load_font():
    """Load a monospace font."""
    # Try system fonts first
    font_paths = [
        "/System/Library/Fonts/Menlo.ttc",
        "/System/Library/Fonts/SF Mono.ttc",
        "/Library/Fonts/SF Mono.ttc",
        "/System/Library/Fonts/Courier.ttf",
    ]
    for fp in font_paths:
        if os.path.exists(fp):
            return ImageFont.truetype(fp, 20)
    # Fallback to default
    return ImageFont.load_default()


def render_frame(lines, cursor_y, font):
    """Render a single frame."""
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # Draw each line
    y = 30
    for i, line in enumerate(lines):
        color = {
            "prompt": PROMPT_COLOR,
            "command": CMD_COLOR,
            "output": OUTPUT_COLOR,
        }.get(line["type"], OUTPUT_COLOR)

        draw.text((20, y), line["text"], font=font, fill=color)

        # Cursor blinking effect for prompt lines
        if line["type"] == "prompt" and i == cursor_y:
            # Draw blinking cursor
            text_width = draw.textlength(line["text"], font=font)
            cursor_x = 20 + text_width
            if frame_num % 2 == 0:  # Blink effect
                draw.rectangle(
                    (cursor_x, y + 4, cursor_x + 10, y + 20), fill=PROMPT_COLOR
                )

        y += 26

    # Draw status bar at bottom
    draw.rectangle((0, HEIGHT - 30, WIDTH, HEIGHT), fill=(40, 44, 48))
    draw.text((15, HEIGHT - 24), "oh-my-coder CLI", font=font, fill=(120, 120, 130))
    draw.text((WIDTH - 100, HEIGHT - 24), "zsh", font=font, fill=(120, 120, 130))

    return img


# Calculate which lines to show based on frame
def get_lines_for_frame(frame_num):
    """Determine which lines to show at this frame."""
    # Simple animation: reveal lines progressively
    lines = []

    # Reveal lines gradually
    reveal_speed = 3  # frames per line reveal
    current_line_idx = frame_num // reveal_speed

    for i in range(min(current_line_idx + 1, len(TERMINAL_LINES))):
        line = TERMINAL_LINES[i].copy()

        # Animate typing for command/prompt lines
        if line["type"] in ("command", "prompt") and i == current_line_idx:
            char_reveal = (frame_num % reveal_speed) * 3
            line["text"] = line["text"][:char_reveal]

        lines.append(line)

    return lines


# Generate frames
font = load_font()
frames = []

print(f"Generating {FRAMES} frames...")

for frame_num in range(FRAMES):
    lines = get_lines_for_frame(frame_num)
    img = render_frame(lines, len(lines) - 1, font)
    frames.append(img)
    if frame_num % 20 == 0:
        print(f"  Frame {frame_num}/{FRAMES}")

# Save as GIF
print(f"Saving to {OUTPUT_PATH}...")
frames[0].save(
    OUTPUT_PATH,
    save_all=True,
    append_images=frames[1:],
    duration=DURATION_MS,
    loop=0,
    optimize=True,
)

# Check file size
size = os.path.getsize(OUTPUT_PATH) / 1024 / 1024
print(f"✓ Saved: {OUTPUT_PATH} ({size:.2f} MB)")
