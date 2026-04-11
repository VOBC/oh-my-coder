"""
Vision Agent - 视觉分析与 UI 审查智能体

职责：
1. 截图 / UI 图片分析
2. 布局问题检测
3. 视觉修改建议
4. 设计规范审查

模型层级：MEDIUM（平衡，对应 sonnet）
"""

from pathlib import Path
from typing import Dict, List, Optional

from ..core.router import TaskType
from .base import (
    AgentContext,
    AgentLane,
    AgentOutput,
    AgentStatus,
    BaseAgent,
    register_agent,
)


def _load_image_meta(image_path: Path) -> Optional[Dict]:
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
            size = len(data)
            # Fallback: read more
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
                        return {"format": "JPEG", "width": w, "height": h, "path": str(image_path)}
                    else:
                        length = struct.unpack(">H", f.read(2))[0]
                        f.read(length - 2)
            return {"format": "JPEG", "path": str(image_path)}

        # WebP: RIFF....WEBP
        if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
            return {"format": "WEBP", "path": str(image_path)}

        return {"format": "unknown", "path": str(image_path)}

    except Exception:
        return None


@register_agent
class VisionAgent(BaseAgent):
    """视觉分析 Agent - 截图 / UI 图片分析与修改建议"""

    name = "vision"
    description = "视觉分析与 UI 审查智能体 - 截图布局分析与修改建议"
    lane = AgentLane.DOMAIN
    default_tier = "medium"
    icon = "👁️"
    tools = ["file_read", "file_write", "web_search"]

    @property
    def system_prompt(self) -> str:
        return """你是一个资深的 UI/UX 设计师和前端开发者。

## 角色
你擅长分析截图和 UI 图片，识别视觉问题，并给出具体的修改建议。

## 能力
1. **布局分析** - 间距、对齐、层级结构
2. **配色审查** - 色彩对比度、可访问性
3. **交互分析** - 按钮位置、点击区域、响应区域
4. **问题识别** - 视觉不一致、留白问题、排版问题
5. **修改建议** - 具体到 CSS 属性 / 组件代码

## 分析维度

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

## 输出格式

### 视觉审查报告
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

## 注意事项
- 提供可执行的 CSS/代码片段
- 给出修改前后的对比说明
- 标注具体的颜色值、像素值
"""

    async def _run(
        self, context: AgentContext, prompt: List[Dict[str, str]], **kwargs
    ) -> str:
        """执行视觉分析"""
        image_path: Optional[Path] = context.metadata.get("image_path")

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

        # 扫描项目中的图片（如果 context 中有 project_path）
        if context.project_path and context.project_path.exists():
            image_extensions = {".png", ".jpg", ".jpeg", ".webp", ".svg", ".gif"}
            images = [
                str(p) for p in context.project_path.rglob("*")
                if p.suffix.lower() in image_extensions and p.is_file()
            ]
            if images:
                extra_context += f"## 📁 项目中的图片文件\n" + "\n".join(f"- {i}" for i in images[:10]) + "\n"

        if extra_context:
            prompt.append({
                "role": "system",
                "content": f"## 额外信息\n{extra_context}",
            })

        # 分析提示
        analysis_hint = """

请对上述截图/UI 图片进行全面视觉分析：
1. 识别所有布局和视觉问题
2. 给出每个问题的严重程度（P0/P1/P2）
3. 提供具体的修改建议（带代码/CSS）
4. 输出完整的视觉审查报告

如果提供了多个图片，请逐一分析并对比。
"""
        prompt.append({"role": "user", "content": analysis_hint})

        # 调用模型（使用视觉能力）
        from ..models.base import Message

        messages = [Message(role=msg["role"], content=msg["content"]) for msg in prompt]

        response = await self.model_router.route_and_call(
            task_type=TaskType.CODE_GENERATION,
            messages=messages,
        )

        return response.content

    def _post_process(self, result: str, context: AgentContext) -> AgentOutput:
        """后处理"""
        return AgentOutput(
            agent_name=self.name,
            status=AgentStatus.COMPLETED,
            result=result,
            recommendations=[
                "应用视觉修改建议到代码",
                "使用 VisionAgent 再次审查修改后的效果",
            ],
        )
