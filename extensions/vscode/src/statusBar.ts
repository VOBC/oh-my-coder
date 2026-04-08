/**
 * 状态栏管理器
 */

import * as vscode from 'vscode';
import { TaskManager, TaskStatus } from './taskManager';

export class StatusBarManager implements vscode.Disposable {
    private statusBarItem: vscode.StatusBarItem;
    private taskManager: TaskManager;

    constructor(taskManager: TaskManager) {
        this.taskManager = taskManager;
        this.statusBarItem = vscode.window.createStatusBarItem(
            vscode.StatusBarAlignment.Right,
            100
        );
        this.update();
        this.statusBarItem.show();

        // 监听任务状态变化
        this.taskManager.onDidChangeStatus(() => this.update());
    }

    update(): void {
        const config = vscode.workspace.getConfiguration('omc');
        if (!config.get('showStatusBar')) {
            this.statusBarItem.hide();
            return;
        }

        const status = this.taskManager.getStatus();

        if (status === TaskStatus.Idle) {
            this.statusBarItem.text = '$(hubot) OMC';
            this.statusBarItem.tooltip = 'Oh My Coder - 就绪';
            this.statusBarItem.command = 'omc.openPanel';
            this.statusBarItem.backgroundColor = undefined;
        } else if (status === TaskStatus.Running) {
            this.statusBarItem.text = '$(sync~spin) OMC 运行中...';
            this.statusBarItem.tooltip = '点击查看进度';
            this.statusBarItem.command = 'omc.openPanel';
            this.statusBarItem.backgroundColor = new vscode.ThemeColor(
                'statusBarItem.warningBackground'
            );
        } else if (status === TaskStatus.Error) {
            this.statusBarItem.text = '$(error) OMC 错误';
            this.statusBarItem.tooltip = '任务执行失败，点击查看详情';
            this.statusBarItem.command = 'omc.showHistory';
            this.statusBarItem.backgroundColor = new vscode.ThemeColor(
                'statusBarItem.errorBackground'
            );
        }

        this.statusBarItem.show();
    }

    showProgress(message: string): void {
        this.statusBarItem.text = `$(sync~spin) ${message}`;
        this.statusBarItem.show();
    }

    dispose(): void {
        this.statusBarItem.dispose();
    }
}
