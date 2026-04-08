/**
 * 历史视图提供者
 */

import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';

interface HistoryEntry {
    id: string;
    description: string;
    timestamp: string;
    status: 'completed' | 'failed';
    workflow?: string;
    duration?: number;
    tokens?: number;
}

export class HistoryProvider implements vscode.TreeDataProvider<HistoryItem> {
    private _onDidChangeTreeData = new vscode.EventEmitter<HistoryItem | undefined | null>();
    readonly onDidChangeTreeData = this._onDidChangeTreeData.event;

    private historyFile: string;

    constructor(context: vscode.ExtensionContext) {
        this.historyFile = path.join(
            context.globalStorageUri.fsPath,
            'history.json'
        );
        this.ensureHistoryFile();
    }

    private ensureHistoryFile(): void {
        const dir = path.dirname(this.historyFile);
        if (!fs.existsSync(dir)) {
            fs.mkdirSync(dir, { recursive: true });
        }
        if (!fs.existsSync(this.historyFile)) {
            fs.writeFileSync(this.historyFile, '[]', 'utf-8');
        }
    }

    addEntry(entry: Omit<HistoryEntry, 'id' | 'timestamp'>): void {
        const history = this.loadHistory();
        const newEntry: HistoryEntry = {
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

    private loadHistory(): HistoryEntry[] {
        try {
            const content = fs.readFileSync(this.historyFile, 'utf-8');
            return JSON.parse(content);
        } catch {
            return [];
        }
    }

    private saveHistory(history: HistoryEntry[]): void {
        fs.writeFileSync(this.historyFile, JSON.stringify(history, null, 2), 'utf-8');
    }

    refresh(): void {
        this._onDidChangeTreeData.fire(null);
    }

    getTreeItem(element: HistoryItem): vscode.TreeItem {
        return element;
    }

    getChildren(element?: HistoryItem): Thenable<HistoryItem[]> {
        if (element) {
            return Promise.resolve([]);
        }

        const history = this.loadHistory();
        const items = history.slice(0, 50).map(
            (entry) =>
                new HistoryItem(
                    entry.id,
                    entry.description,
                    entry.timestamp,
                    entry.status,
                    entry.workflow,
                    entry.duration,
                    entry.tokens
                )
        );

        return Promise.resolve(items);
    }
}

class HistoryItem extends vscode.TreeItem {
    constructor(
        public readonly id: string,
        public readonly description: string,
        public readonly timestamp: string,
        public readonly status: 'completed' | 'failed',
        public readonly workflow?: string,
        public readonly duration?: number,
        public readonly tokens?: number
    ) {
        super(description, vscode.TreeItemCollapsibleState.None);

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

    private getTooltip(): string {
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

    private getIcon(): vscode.ThemeIcon {
        return this.status === 'completed'
            ? new vscode.ThemeIcon('check-circle')
            : new vscode.ThemeIcon('error');
    }
}
