from __future__ import annotations

"""
Vision Agent - 视觉分析与 UI 生成智能体

职责：
1. 截图 / UI 图片分析
2. 布局问题检测
3. 视觉修改建议
4. UI 代码生成（HTML/CSS/React 组件等）
5. 设计规范审查

模型层级：MEDIUM（平衡，对应 sonnet）
"""

from pathlib import Path

from ..core.router import TaskType
from .base import (
    AgentContext,
    AgentLane,
    AgentOutput,
    AgentStatus,
    BaseAgent,
    register_agent,
)


def _load_image_meta(image_path: Path) -> dict | None:
    """提取图片元信息（宽高、尺寸），无需 Pillow 也可工作。"""
    try:
        import struct

        with open(image_path, "rb") as f:
            data = f.read(64)

        # PNG: IHDR chunk starts at offset 16
        if data[:8] == b"\x89PNG\r\n\x1a\n":
            w = struct.unpack(">I", data[16:20])[0]
            h = struct.unpack(">I", data[20:24])[0]
            return {"format": "PNG", "width": w, "height": h, "path": str(image_path)}

        # JPEG: SOF0 at offset 2+7 ~ 160
        if data[:2] == b"\xff\xd8":
            with open(image_path, "rb") as f:
                f.read(2)
                while True:
                    marker = f.read(2)
                    if len(marker) < 2:
                        break
                    m = struct.unpack(">H", marker)[0]
                    if m == 0xFFC0 or m == 0xFFC2:
                        f.read(1)
                        h = struct.unpack(">H", f.read(2))[0]
                        w = struct.unpack(">H", f.read(2))[0]
                        return {
                            "format": "JPEG",
                            "width": w,
                            "height": h,
                            "path": str(image_path),
                        }
                    length = struct.unpack(">H", f.read(2))[0]
                    f.read(length - 2)
            return {"format": "JPEG", "path": str(image_path)}

        # WebP: RIFF....WEBP
        if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
            return {"format": "WEBP", "path": str(image_path)}

        return {"format": "unknown", "path": str(image_path)}

    except Exception:
        return None


def _extract_code_blocks(text: str) -> list[dict[str, str]]:
    """
    从文本中提取代码块。

    支持格式：
    ```language
    code
    ```
    或
    ```lang:filename
    code
    ```

    Returns:
        List[Dict]: [{"language": str, "filename": str, "code": str}]
    """
    import re

    blocks = []
    # Match ```language or ```language:filename
    pattern = re.compile(
        r"```(\w+)?(?::([\w./\\-]+))?\n(.*?)```",
        re.DOTALL,
    )
    for match in pattern.finditer(text):
        language = match.group(1) or "text"
        filename = match.group(2) or _default_filename(language)
        code = match.group(3).rstrip("\n")
        blocks.append({"language": language, "filename": filename, "code": code})
    return blocks


def _default_filename(language: str) -> str:
    """根据语言返回默认文件名。"""
    defaults = {
        "html": "index.html",
        "css": "style.css",
        "javascript": "script.js",
        "js": "script.js",
        "jsx": "Component.jsx",
        "tsx": "Component.tsx",
        "typescript": "script.ts",
        "ts": "script.ts",
        "vue": "Component.vue",
        "svelte": "Component.svelte",
        "python": "generated.py",
        "py": "generated.py",
        "json": "data.json",
        "svg": "icon.svg",
    }
    return defaults.get(language.lower(), f"generated.{language}")


def _infer_output_dir(context: AgentContext) -> Path:
    """推断输出目录。"""
    if context.working_directory and Path(context.working_directory).exists():
        return Path(context.working_directory)
    if context.project_path and Path(context.project_path).exists():
        return Path(context.project_path)
    return Path.cwd() / "vision_output"


@register_agent
class VisionAgent(BaseAgent):
    """
    视觉分析与 UI 代码生成 Agent

    支持两种模式：
    1. **视觉审查**（默认）- 分析截图，给出布局/配色/交互问题及修改建议
    2. **UI 代码生成** - 根据截图自动生成对应的 HTML/CSS/React 组件代码
    """

    name = "vision"
    description = "视觉分析与 UI 代码生成智能体 - 截图布局分析与 UI 代码自动生成"
    lane = AgentLane.DOMAIN
    default_tier = "medium"
    icon = "👁️"
    tools = ["file_read", "file_write", "web_search"]

    # 模式列表
    MODE_ANALYSIS = "analysis"
    MODE_UI_CODE = "ui_code"

    @property
    def system_prompt(self) -> str:
        base = """你是一个资深的 UI/UX 设计师和前端开发者。

## 角色
你擅长分析截图和 UI 图片，识别视觉问题，并给出具体的修改建议。
同时，你能够根据 UI 截图**自动生成对应的代码**。

## 能力
1. **布局分析** - 间距、对齐、层级结构
2. **配色审查** - 色彩对比度、可访问性
3. **交互分析** - 按钮位置、点击区域、响应区域
4. **问题识别** - 视觉不一致、留白问题、排版问题
5. **修改建议** - 具体到 CSS 属性 / 组件代码
6. **UI 代码生成** - 根据截图生成 HTML/CSS/React/Vue 等代码

## 分析维度（视觉审查模式）

### 1. 布局问题
- [ ] 元素对齐是否一致
- [ ] 间距是否均匀
- [ ] 视觉层级是否清晰
- [ ] 是否存在元素重叠

### 2. 配色问题
- [ ] 文字与背景对比度是否 ≥ 4.5:1
- [ ] 主次颜色是否区分明确
- [ ] 是否符合品牌色彩规范

### 3. 排版问题
- [ ] 字体大小是否层次分明
- [ ] 行高是否舒适（建议 1.5-1.8）
- [ ] 标题、正文、说明文字是否区分明确

### 4. 交互问题
- [ ] 关键按钮是否突出
- [ ] 可点击区域是否足够大（≥ 44px）
- [ ] 是否有足够的视觉反馈

## 视觉审查报告格式

```
# 视觉审查报告

## 📊 图片信息
- 尺寸: 1920×1080
- 格式: PNG

## 🎯 核心问题（按优先级）

### P0 - 严重问题
1. **文字对比度不足**
   - 位置: 导航栏右侧辅助文字
   - 当前: #999999 在 #FFFFFF 背景
   - 对比度: 2.8:1（要求 ≥ 4.5:1）
   - 修改: 改为 #666666 → 对比度 5.9:1

### P1 - 重要问题
1. **按钮尺寸过小**
   - 位置: 底部操作栏
   - 当前: 高度 28px
   - 修改: ≥ 44px
   - CSS: `height: 44px; min-height: 44px;`

### P2 - 优化建议
1. 间距建议统一为 8px 的倍数
2. 图标尺寸建议 20×20px
3. 卡片阴影可加深以增强层次感

## ✅ 修改优先级
| 优先级 | 问题 | 修改成本 |
|--------|------|---------|
| P0 | 文字对比度 | 1行 CSS |
| P1 | 按钮尺寸 | 2行 CSS |
| P2 | 间距优化 | 结构调整 |
```
"""

        ui_code_prompt = """
---

## UI 代码生成模式（output_format=ui_code）

当用户要求生成 UI 代码时，你需要：
1. **仔细分析截图**：识别所有 UI 元素（按钮、表单、导航、卡片等）
2. **提取设计细节**：颜色、字体大小、间距、圆角、阴影、图标
3. **生成高质量代码**：输出格式用 ```language:filename 代码 ``` 标记

### 支持的输出格式

| 格式 | 说明 | 典型用途 |
|------|------|---------|
| `html` | 纯 HTML + 内联样式 | 快速原型 |
| `css` | 独立 CSS 文件 | 与 HTML 配合 |
| `javascript` / `js` | 交互逻辑 | 表单验证、动画 |
| `jsx` / `tsx` | React 组件 | React 项目 |
| `vue` | Vue 组件 | Vue 项目 |
| `svelte` | Svelte 组件 | Svelte 项目 |

### 生成原则

**精准还原**：
- 颜色值尽量精确（从截图提取 hex/rgb）
- 字体大小、间距使用截图中的实际像素值
- 保持视觉比例和层级关系

**代码质量**：
- HTML 语义化（header/nav/main/section/article/footer）
- CSS 使用 Flexbox/Grid 布局，BEM 命名
- React 组件用函数组件 + hooks 风格

**渐进增强**：
- 基础版本：HTML + CSS（最通用）
- 增强版本：React/Vue 组件（可选）

### 输出示例

```
我已分析截图，识别到以下 UI 结构：

**页面布局**：顶部导航 + 侧边栏 + 主内容区 + 底部操作栏
**色彩体系**：
- 主色: #3B82F6（蓝）
- 背景: #F9FAFB（浅灰）
- 文字: #111827（深灰）
**组件列表**：
- 导航栏（logo + 菜单项 + 用户头像）
- 搜索框（圆角输入框 + 搜索图标）
- 卡片列表（图片 + 标题 + 描述 + 操作按钮）
- 底部 TabBar（首页/发现/消息/我的）

以下是生成的代码：

```html:index.html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Generated UI</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <header class="navbar">
    <div class="navbar-logo">Logo</div>
    <nav class="navbar-menu">...</nav>
  </header>
  <!-- 完整 HTML 结构 -->
</body>
</html>
```

```css:style.css
/* 精确还原截图的样式 */
.navbar {
  display: flex;
  align-items: center;
  height: 56px;
  padding: 0 16px;
  background: #ffffff;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}
/* 更多样式 */
*/
```

```tsx:components/PageLayout.tsx
import React from "react";

export const PageLayout: React.FC = () => {
  return (
    <header className="navbar">
      {/* ... */}
    </header>
  );
};
```

---

**重要**：每个代码块必须以 `language:filename` 开头（如 `html:index.html`），
方便自动提取和保存文件。
"""
        return base + ui_code_prompt

    async def _run(
        self, context: AgentContext, prompt: list[dict[str, str]], **kwargs
    ) -> str:
        """执行视觉分析或 UI 代码生成"""
        image_path: Path | None = context.metadata.get("image_path")
        output_format: str = context.metadata.get("output_format", self.MODE_ANALYSIS)

        extra_context = ""

        if image_path:
            path = Path(image_path)
            if path.exists():
                meta = _load_image_meta(path)
                if meta:
                    size_info = (
                        f"{meta['width']}×{meta['height']}"
                        if meta.get("width")
                        else "未知"
                    )
                    extra_context = (
                        f"\n## 📊 图片信息\n"
                        f"- 路径: `{path}`\n"
                        f"- 格式: {meta.get('format', 'unknown')}\n"
                        f"- 尺寸: {size_info}\n\n"
                    )

        # 扫描项目中的图片
        if context.project_path and context.project_path.exists():
            image_extensions = {".png", ".jpg", ".jpeg", ".webp", ".svg", ".gif"}
            images = [
                str(p)
                for p in context.project_path.rglob("*")
                if p.suffix.lower() in image_extensions and p.is_file()
            ]
            if images:
                extra_context += (
                    "## 📁 项目中的图片文件\n"
                    + "\n".join(f"- {i}" for i in images[:10])
                    + "\n"
                )

        # 模式判断：优先使用 metadata 中的 output_format
        mode_hint: str
        if output_format == self.MODE_UI_CODE:
            mode_hint = """

## 🎯 当前模式：UI 代码生成

请对上述截图进行全面的 UI 分析，并**自动生成对应的代码**：

1. **识别 UI 元素**：导航栏、按钮、输入框、卡片、列表等
2. **提取设计细节**：颜色、字体、间距、圆角、阴影
3. **生成代码文件**：使用 ```language:filename 代码 ``` 格式输出

请生成以下文件（按需选择）：
- `html:index.html` - 页面结构
- `css:style.css` - 样式表
- `tsx:components/*.tsx` - React 组件（可选）

**要求**：
- 代码可直接运行（复制到文件中用浏览器打开即可预览）
- 颜色值尽量精确（从截图提取）
- 保持响应式适配
- HTML 语义化，CSS 使用 Flexbox/Grid
"""
        else:
            mode_hint = """

## 🎯 当前模式：视觉审查

请对上述截图/UI 图片进行全面视觉分析：
1. 识别所有布局和视觉问题
2. 给出每个问题的严重程度（P0/P1/P2）
3. 提供具体的修改建议（带代码/CSS）
4. 输出完整的视觉审查报告

如果提供了多个图片，请逐一分析并对比。
"""

        if extra_context:
            prompt.append(
                {
                    "role": "system",
                    "content": f"## 额外信息\n{extra_context}",
                }
            )
        prompt.append({"role": "user", "content": mode_hint})

        # 调用模型
        from ..models.base import Message

        messages = [Message(role=msg["role"], content=msg["content"]) for msg in prompt]

        response = await self.model_router.route_and_call(
            task_type=TaskType.CODE_GENERATION,
            messages=messages,
        )

        # UI 代码生成模式：提取代码块并保存
        if output_format == self.MODE_UI_CODE:
            blocks = _extract_code_blocks(response.content)
            if blocks:
                output_dir = _infer_output_dir(context)
                saved_files: dict[str, str] = {}
                for block in blocks:
                    file_path = output_dir / block["filename"]
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    file_path.write_text(block["code"], encoding="utf-8")
                    saved_files[block["filename"]] = str(file_path)
                # 将保存路径注入到结果中
                file_list = "\n".join(
                    f"- `{fn}` → `{fp}`" for fn, fp in saved_files.items()
                )
                response.content += (
                    f"\n\n---\n"
                    f"**📁 已生成 {len(saved_files)} 个文件**:\n{file_list}\n"
                    f"**输出目录**: `{output_dir}`"
                )

        return response.content

    def _post_process(self, result: str, context: AgentContext) -> AgentOutput:
        """后处理"""
        output_format: str = context.metadata.get("output_format", self.MODE_ANALYSIS)
        recommendations: list[str]
        if output_format == self.MODE_UI_CODE:
            recommendations = [
                "在浏览器中打开生成的 HTML 文件预览效果",
                "根据实际渲染效果调整细节",
                "可将生成的组件集成到现有项目中",
            ]
        else:
            recommendations = [
                "应用视觉修改建议到代码",
                "使用 VisionAgent 再次审查修改后的效果",
            ]

        # 提取已保存的文件路径（从结果末尾的列表中）
        artifacts: dict[str, str] = {}
        if output_format == self.MODE_UI_CODE:
            blocks = _extract_code_blocks(result)
            for block in blocks:
                filename = block["filename"]
                # 尝试从结果中找到完整路径
                for line in result.split("\n"):
                    if f"`{filename}`" in line:
                        import re

                        m = re.search(r"`(/[^`]*)`", line)
                        if m:
                            artifacts[filename] = m.group(1)
                        break
                if filename not in artifacts:
                    output_dir = _infer_output_dir(context)
                    artifacts[filename] = str(output_dir / filename)

        return AgentOutput(
            agent_name=self.name,
            status=AgentStatus.COMPLETED,
            result=result,
            artifacts=artifacts,
            recommendations=recommendations,
        )
