"use strict";
/**
 * 历史视图提供者
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
exports.HistoryProvider = void 0;
const vscode = __importStar(require("vscode"));
const path = __importStar(require("path"));
const fs = __importStar(require("fs"));
class HistoryProvider {
    _onDidChangeTreeData = new vscode.EventEmitter();
    onDidChangeTreeData = this._onDidChangeTreeData.event;
    historyFile;
    constructor(context) {
        this.historyFile = path.join(context.globalStorageUri.fsPath, 'history.json');
        this.ensureHistoryFile();
    }
    ensureHistoryFile() {
        const dir = path.dirname(this.historyFile);
        if (!fs.existsSync(dir)) {
            fs.mkdirSync(dir, { recursive: true });
        }
        if (!fs.existsSync(this.historyFile)) {
            fs.writeFileSync(this.historyFile, '[]', 'utf-8');
        }
    }
    addEntry(entry) {
        const history = this.loadHistory();
        const newEntry = {
            id: `h-${Date.now()}`,
            timestamp: new Date().toISOString(),
            ...entry,
        };
        history.unshift(newEntry);
        // 只保留最近 100 条
        if (history.length > 100) {
            history.pop();
        }
        this.saveHistory(history);
        this.refresh();
    }
    loadHistory() {
        try {
            const content = fs.readFileSync(this.historyFile, 'utf-8');
            return JSON.parse(content);
        }
        catch {
            return [];
        }
    }
    saveHistory(history) {
        fs.writeFileSync(this.historyFile, JSON.stringify(history, null, 2), 'utf-8');
    }
    refresh() {
        this._onDidChangeTreeData.fire(null);
    }
    getTreeItem(element) {
        return element;
    }
    getChildren(element) {
        if (element) {
            return Promise.resolve([]);
        }
        const history = this.loadHistory();
        const items = history.slice(0, 50).map((entry) => new HistoryItem(entry.id, entry.description, entry.timestamp, entry.status, entry.workflow, entry.duration, entry.tokens));
        return Promise.resolve(items);
    }
}
exports.HistoryProvider = HistoryProvider;
class HistoryItem extends vscode.TreeItem {
    id;
    description;
    timestamp;
    status;
    workflow;
    duration;
    tokens;
    constructor(id, description, timestamp, status, workflow, duration, tokens) {
        super(description, vscode.TreeItemCollapsibleState.None);
        this.id = id;
        this.description = description;
        this.timestamp = timestamp;
        this.status = status;
        this.workflow = workflow;
        this.duration = duration;
        this.tokens = tokens;
        const time = new Date(timestamp);
        const timeStr = time.toLocaleString('zh-CN', {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
        });
        this.description = timeStr;
        this.tooltip = this.getTooltip();
        this.iconPath = this.getIcon();
        this.contextValue = 'historyItem';
        this.command = {
            command: 'omc.viewHistoryDetail',
            title: '查看详情',
            arguments: [id],
        };
    }
    getTooltip() {
        const lines = [
            `任务: ${this.description}`,
            `状态: ${this.status === 'completed' ? '✓ 完成' : '✗ 失败'}`,
        ];
        if (this.workflow) {
            lines.push(`工作流: ${this.workflow}`);
        }
        if (this.duration) {
            lines.push(`耗时: ${this.duration.toFixed(1)}s`);
        }
        if (this.tokens) {
            lines.push(`Token: ${this.tokens}`);
        }
        return lines.join('\n');
    }
    getIcon() {
        return this.status === 'completed'
            ? new vscode.ThemeIcon('check-circle')
            : new vscode.ThemeIcon('error');
    }
}
//# sourceMappingURL=historyProvider.js.map