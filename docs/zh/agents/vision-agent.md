# VisionAgent - 视觉理解 Agent

> 截图布局分析 + UI 代码自动生成

## 功能概述

VisionAgent 是 oh-my-coder 的多模态 AI Agent，专门用于：
- 分析截图、UI 设计稿
- 理解界面布局和组件
- 自动生成对应的 HTML/CSS/React 代码

## 使用场景

### 1. 截图转代码

将 UI 截图转换为可运行的代码：

```bash
omc run "根据这个截图生成对应的 HTML/CSS 代码" --agent VisionAgent --file screenshot.png
```

### 2. UI 布局分析

分析现有界面的布局结构：

```bash
omc run "分析这个界面的布局结构" --agent VisionAgent --file ui.png
```

### 3. 设计稿还原

将设计稿图片还原为代码实现：

```bash
omc run "将设计稿还原为 React 组件" --agent VisionAgent --file design.png
```

## 工作原理

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  用户上传   │ ──▶ │  VisionAgent │ ──▶ │  生成代码   │
│  截图/图片  │     │  (多模态理解) │     │  (HTML/CSS/ │
│             │     │              │     │   React)    │
└─────────────┘     └──────────────┘     └─────────────┘
```

1. **图像理解**：分析截图中的布局、颜色、字体、间距
2. **组件识别**：识别按钮、输入框、卡片、导航栏等组件
3. **代码生成**：生成语义化的 HTML/CSS/React 代码

## 适用模型

VisionAgent 需要使用支持多模态的模型：

| 模型 | 支持情况 | 推荐度 |
|-----|---------|--------|
| GLM-4V | ✅ 原生支持 | ⭐⭐⭐⭐⭐ |
| Qwen-VL | ✅ 支持 | ⭐⭐⭐⭐ |
| GPT-4V | ✅ 支持 | ⭐⭐⭐⭐ |
| Claude-3-Vision | ✅ 支持 | ⭐⭐⭐⭐ |

配置示例：
```bash
omc config set -k DEFAULT_MODEL -v "glm-4v"
```

## 示例输出

### 输入：UI 截图

假设有以下登录界面截图：

### 输出：生成的代码

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>登录</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f5f5;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
        }
        .login-container {
            background: white;
            padding: 40px;
            border-radius: 12px;
            box-shadow: 0 2px 12px rgba(0,0,0,0.1);
            width: 100%;
            max-width: 400px;
        }
        .login-title {
            font-size: 24px;
            font-weight: 600;
            margin-bottom: 24px;
            text-align: center;
            color: #333;
        }
        .input-group {
            margin-bottom: 16px;
        }
        .input-group label {
            display: block;
            margin-bottom: 8px;
            color: #666;
            font-size: 14px;
        }
        .input-group input {
            width: 100%;
            padding: 12px;
            border: 1px solid #ddd;
            border-radius: 8px;
            font-size: 14px;
        }
        .login-button {
            width: 100%;
            padding: 12px;
            background: #1677ff;
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            cursor: pointer;
        }
    </style>
</head>
<body>
    <div class="login-container">
        <h1 class="login-title">登录</h1>
        <form>
            <div class="input-group">
                <label>用户名</label>
                <input type="text" placeholder="请输入用户名">
            </div>
            <div class="input-group">
                <label>密码</label>
                <input type="password" placeholder="请输入密码">
            </div>
            <button type="submit" class="login-button">登录</button>
        </form>
    </div>
</body>
</html>
```

## 与其他 Agent 配合

VisionAgent 可以与其他 Agent 配合使用：

```
VisionAgent → DesignerAgent → ExecutorAgent → VerifierAgent
  (分析截图)   (优化设计)     (生成代码)      (验证实现)
```

示例：
```bash
omc run "分析设计稿并生成完整的登录页面" --workflow build --agents VisionAgent,ExecutorAgent --file login.png
```

## 注意事项

1. **图片清晰度**：建议使用清晰的截图，越清晰生成效果越好
2. **模型选择**：确保使用支持多模态的模型
3. **复杂界面**：对于非常复杂的界面，可能需要多次迭代调整

## 相关命令

```bash
# 查看 VisionAgent 详情
omc agents list | grep Vision

# 使用 VisionAgent
omc run "分析截图" --agent VisionAgent --file screenshot.png
```
