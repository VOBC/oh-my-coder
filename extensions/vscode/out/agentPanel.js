"use strict";
/**
 * 侧边栏面板 - Agent 任务视图
 */
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.OMCProvider = void 0;
const vscode = __importStar(require("vscode"));
const taskManager_1 = require("./taskManager");
class OMCProvider {
    _onDidChangeTreeData = new vscode.EventEmitter();
    onDidChangeTreeData = this._onDidChangeTreeData.event;
    extensionUri;
    taskManager;
    view;
    constructor(extensionUri, taskManager) {
        this.extensionUri = extensionUri;
        this.taskManager = taskManager;
        // 监听任务状态变化
        this.taskManager.onDidChangeStatus(() => {
            this.refresh();
        });
        this.taskManager.onDidChangeOutput((chunk) => {
            if (this.view) {
                this.view.webview.postMessage({
                    type: 'output',
                    data: chunk,
                });
            }
        });
    }
    resolveWebviewView(webviewView, _context, _token) {
        this.view = webviewView;
        webviewView.webview.options = {
            enableScripts: true,
            localResourceRoots: [this.extensionUri],
        };
        webviewView.webview.html = this.getWebviewContent(webviewView.webview);
        // 接收来自 webview 的消息
        webviewView.webview.onDidReceiveMessage((data) => {
            switch (data.type) {
                case 'runTask':
                    vscode.commands.executeCommand('omc.runTask');
                    break;
                case 'stopTask':
                    vscode.commands.executeCommand('omc.stopTask');
                    break;
                case 'openFile':
                    if (data.path) {
                        vscode.commands.executeCommand('vscode.open', vscode.Uri.file(data.path));
                    }
                    break;
            }
        });
    }
    getWebviewContent(webview) {
        const task = this.taskManager.getCurrentTask();
        const isRunning = task?.status === taskManager_1.TaskStatus.Running;
        const config = vscode.workspace.getConfiguration('omc');
        const currentModel = config.get('defaultModel') || 'deepseek';
        return `<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Oh My Coder</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            padding: 12px;
            color: var(--vscode-foreground);
            background: var(--vscode-sideBar-background);
        }
        .header {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 12px;
        }
        .header h2 {
            font-size: 16px;
            font-weight: 600;
        }
        .status {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
        }
        .status.idle {
            background: var(--vscode-inputValidation-infoBackground);
            color: var(--vscode-inputValidation-infoForeground);
        }
        .status.running {
            background: var(--vscode-inputValidation-warningBackground);
            color: var(--vscode-inputValidation-warningForeground);
        }
        .status.error {
            background: var(--vscode-inputValidation-errorBackground);
            color: var(--vscode-inputValidation-errorForeground);
        }
        .select-row {
            display: flex;
            gap: 8px;
            margin-bottom: 12px;
        }
        .select-row select {
            flex: 1;
            padding: 8px;
            border: 1px solid var(--vscode-input-border);
            background: var(--vscode-input-background);
            color: var(--vscode-input-foreground);
            border-radius: 4px;
            font-size: 13px;
        }
        .task-input {
            width: 100%;
            padding: 8px;
            border: 1px solid var(--vscode-input-border);
            background: var(--vscode-input-background);
            color: var(--vscode-input-foreground);
            border-radius: 4px;
            font-size: 13px;
            margin-bottom: 12px;
        }
        .task-input:focus {
            outline: 1px solid var(--vscode-focusBorder);
        }
        .buttons {
            display: flex;
            gap: 8px;
            margin-bottom: 12px;
        }
        .btn {
            flex: 1;
            padding: 8px 12px;
            border: none;
            border-radius: 4px;
            font-size: 13px;
            cursor: pointer;
            transition: opacity 0.2s;
        }
        .btn:hover {
            opacity: 0.9;
        }
        .btn-primary {
            background: var(--vscode-button-background);
            color: var(--vscode-button-foreground);
        }
        .btn-secondary {
            background: var(--vscode-button-secondaryBackground);
            color: var(--vscode-button-secondaryForeground);
        }
        .btn-danger {
            background: #d32f2f;
            color: white;
        }
        .output {
            background: var(--vscode-editor-background);
            border: 1px solid var(--vscode-input-border);
            border-radius: 4px;
            padding: 12px;
            font-size: 13px;
            height: 300px;
            overflow-y: auto;
            line-height: 1.6;
        }
        .output h1, .output h2, .output h3 {
            margin: 16px 0 8px 0;
            font-weight: 600;
        }
        .output h1 { font-size: 18px; border-bottom: 1px solid var(--vscode-input-border); padding-bottom: 8px; }
        .output h2 { font-size: 16px; }
        .output h3 { font-size: 14px; }
        .output p { margin: 8px 0; }
        .output code {
            background: var(--vscode-textCodeBlock-background);
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Consolas', 'Monaco', monospace;
            font-size: 12px;
        }
        .output pre {
            background: var(--vscode-textCodeBlock-background);
            padding: 12px;
            border-radius: 4px;
            overflow-x: auto;
            margin: 8px 0;
        }
        .output pre code {
            background: none;
            padding: 0;
        }
        .output ul, .output ol {
            margin: 8px 0;
            padding-left: 24px;
        }
        .output li {
            margin: 4px 0;
        }
        .output blockquote {
            border-left: 4px solid var(--vscode-input-border);
            padding-left: 12px;
            margin: 8px 0;
            color: var(--vscode-descriptionForeground);
        }
        .output hr {
            border: none;
            border-top: 1px solid var(--vscode-input-border);
            margin: 16px 0;
        }
        .output table {
            border-collapse: collapse;
            width: 100%;
            margin: 8px 0;
        }
        .output th, .output td {
            border: 1px solid var(--vscode-input-border);
            padding: 8px;
            text-align: left;
        }
        .output th {
            background: var(--vscode-textCodeBlock-background);
            font-weight: 600;
        }
        .empty-state {
            color: var(--vscode-descriptionForeground);
            font-style: italic;
            text-align: center;
            padding: 40px 0;
        }
    </style>
</head>
<body>
    <div class="header">
        <h2>🤖 Oh My Coder</h2>
        <span class="status ${isRunning ? 'running' : 'idle'}" id="status">
            ${isRunning ? '⏳ 运行中' : '✓ 就绪'}
        </span>
    </div>

    <div class="select-row">
        <select id="model">
            <option value="deepseek" ${currentModel === 'deepseek' ? 'selected' : ''}>DeepSeek</option>
            <option value="qwen" ${currentModel === 'qwen' ? 'selected' : ''}>通义千问</option>
            <option value="glm" ${currentModel === 'glm' ? 'selected' : ''}>智谱 GLM</option>
            <option value="kimi" ${currentModel === 'kimi' ? 'selected' : ''}>Kimi</option>
            <option value="hunyuan" ${currentModel === 'hunyuan' ? 'selected' : ''}>腾讯混元</option>
            <option value="wenxin" ${currentModel === 'wenxin' ? 'selected' : ''}>文心一言</option>
            <option value="doubao" ${currentModel === 'doubao' ? 'selected' : ''}>豆包</option>
            <option value="minimax" ${currentModel === 'minimax' ? 'selected' : ''}>MiniMax</option>
            <option value="tiangong" ${currentModel === 'tiangong' ? 'selected' : ''}>天工</option>
            <option value="spark" ${currentModel === 'spark' ? 'selected' : ''}>讯飞星火</option>
            <option value="baichuan" ${currentModel === 'baichuan' ? 'selected' : ''}>百川</option>
            <option value="siliconflow" ${currentModel === 'siliconflow' ? 'selected' : ''}>SiliconFlow</option>
        </select>
        <select id="workflow">
            <option value="">默认工作流</option>
            <option value="build">🔨 构建</option>
            <option value="review">🔍 审查</option>
            <option value="debug">🐛 调试</option>
            <option value="test">🧪 测试</option>
            <option value="explore">📖 探索</option>
        </select>
    </div>

    <input type="text" class="task-input" id="taskInput" 
           placeholder="输入任务描述...">

    <div class="buttons">
        <button class="btn btn-primary" id="runBtn" ${isRunning ? 'disabled' : ''}>
            ▶ 运行
        </button>
        <button class="btn btn-danger" id="stopBtn" ${!isRunning ? 'disabled' : ''}>
            ⏹ 停止
        </button>
    </div>

    <div class="output" id="output">
        ${this.taskManager.getOutput() ? this.renderMarkdown(this.taskManager.getOutput()) : '<div class="empty-state">等待任务...</div>'}
    </div>

    <script>
        const vscode = acquireVsCodeApi();
        const outputEl = document.getElementById('output');
        const statusEl = document.getElementById('status');
        const runBtn = document.getElementById('runBtn');
        const stopBtn = document.getElementById('stopBtn');

        document.getElementById('runBtn').addEventListener('click', () => {
            const input = document.getElementById('taskInput').value;
            const workflow = document.getElementById('workflow').value;
            const model = document.getElementById('model').value;
            if (input.trim()) {
                vscode.postMessage({
                    type: 'runTask',
                    description: input,
                    workflow: workflow,
                    model: model
                });
            }
        });

        document.getElementById('stopBtn').addEventListener('click', () => {
            vscode.postMessage({ type: 'stopTask' });
        });

        window.addEventListener('message', (event) => {
            const message = event.data;
            if (message.type === 'output') {
                // Append raw text, will be rendered as markdown on next refresh
                outputEl.innerHTML = message.html || '<div class="empty-state">等待任务...</div>';
                outputEl.scrollTop = outputEl.scrollHeight;
            } else if (message.type === 'status') {
                const running = message.status === 'running';
                statusEl.className = 'status ' + (running ? 'running' : 'idle');
                statusEl.textContent = running ? '⏳ 运行中' : '✓ 就绪';
                runBtn.disabled = running;
                stopBtn.disabled = !running;
            }
        });

        document.getElementById('taskInput').addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                document.getElementById('runBtn').click();
            }
        });
    </script>
</body>
</html>`;
    }
    escapeHtml(text) {
        return text
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }
    /**
     * 简单的 Markdown 渲染
     */
    renderMarkdown(text) {
        let html = this.escapeHtml(text);
        // Headers
        html = html.replace(/^### (.*$)/gim, '<h3>$1</h3>');
        html = html.replace(/^## (.*$)/gim, '<h2>$1</h2>');
        html = html.replace(/^# (.*$)/gim, '<h1>$1</h1>');
        // Bold and Italic
        html = html.replace(/\*\*\*(.*?)\*\*\*/g, '<strong><em>$1</em></strong>');
        html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');
        // Inline code
        html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
        // Code blocks
        html = html.replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>');
        // Blockquotes
        html = html.replace(/^&gt; (.*$)/gim, '<blockquote>$1</blockquote>');
        // Horizontal rules
        html = html.replace(/^---$/gim, '<hr>');
        // Unordered lists
        html = html.replace(/^- (.*$)/gim, '<li>$1</li>');
        html = html.replace(/(<li>.*<\/li>\n?)+/g, '<ul>$&</ul>');
        // Ordered lists
        html = html.replace(/^\d+\. (.*$)/gim, '<li>$1</li>');
        // Links
        html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2">$1</a>');
        // Line breaks
        html = html.replace(/\n/g, '<br>');
        return html;
    }
    refresh() {
        this._onDidChangeTreeData.fire(null);
    }
    getTreeItem(_element) {
        return _element;
    }
    getChildren(_element) {
        if (_element) {
            return Promise.resolve([]);
        }
        const task = this.taskManager.getCurrentTask();
        const items = [];
        if (task) {
            items.push(new TaskItem(task.description, task.status, task.startTime?.toLocaleTimeString() || ''));
        }
        return Promise.resolve(items);
    }
}
exports.OMCProvider = OMCProvider;
class TaskItem extends vscode.TreeItem {
    label;
    status;
    time;
    constructor(label, status, time) {
        super(label, vscode.TreeItemCollapsibleState.None);
        this.label = label;
        this.status = status;
        this.time = time;
        this.tooltip = `${label} - ${status}`;
        this.description = time;
        this.iconPath = this.getIcon();
    }
    getIcon() {
        switch (this.status) {
            case taskManager_1.TaskStatus.Running:
                return new vscode.ThemeIcon('sync~spin');
            case taskManager_1.TaskStatus.Completed:
                return new vscode.ThemeIcon('check');
            case taskManager_1.TaskStatus.Error:
                return new vscode.ThemeIcon('error');
            default:
                return new vscode.ThemeIcon('circle-outline');
        }
    }
}
//# sourceMappingURL=agentPanel.js.map