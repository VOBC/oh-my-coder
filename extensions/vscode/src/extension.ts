/**
 * Oh My Coder VS Code Extension
 * 
 * 多智能体 AI 编程助手扩展
 */

import * as vscode from 'vscode';
import { OMCProvider } from './agentPanel';
import { StatusBarManager } from './statusBar';
import { CommandManager } from './commands';
import { TaskManager } from './taskManager';
import { HistoryProvider } from './historyProvider';
import { AgentsProvider } from './agentsProvider';

let statusBar: StatusBarManager;
let commandManager: CommandManager;
let taskManager: TaskManager;

export function activate(context: vscode.ExtensionContext) {
    console.log('Oh My Coder is now active!');

    // 初始化任务管理器
    taskManager = new TaskManager(context);

    // 初始化状态栏
    statusBar = new StatusBarManager(taskManager);
    context.subscriptions.push(statusBar);

    // 初始化命令管理器
    commandManager = new CommandManager(taskManager, statusBar);
    commandManager.registerCommands(context);

    // 注册侧边栏视图
    registerViews(context);

    // 注册 Webview 面板
    const provider = new OMCProvider(context.extensionUri, taskManager);
    context.subscriptions.push(
        vscode.window.registerWebviewViewProvider('omc-tasks', provider)
    );

    // 监听配置变更
    context.subscriptions.push(
        vscode.workspace.onDidChangeConfiguration((e) => {
            if (e.affectsConfiguration('omc')) {
                statusBar.update();
            }
        })
    );

    // 显示欢迎消息
    if (vscode.workspace.getConfiguration('omc').get('showWelcome')) {
        vscode.window.showInformationMessage(
            '🤖 Oh My Coder 已启动！使用 Ctrl+Shift+Enter 运行任务',
            '打开面板',
            '不再显示'
        ).then((selection) => {
            if (selection === '打开面板') {
                vscode.commands.executeCommand('omc.openPanel');
            } else if (selection === '不再显示') {
                vscode.workspace.getConfiguration('omc').update('showWelcome', false);
            }
        });
    }
}

function registerViews(context: vscode.ExtensionContext) {
    // 任务视图
    const tasksProvider = new OMCProvider(context.extensionUri, taskManager);
    context.subscriptions.push(
        vscode.window.registerTreeDataProvider('omc-tasks', tasksProvider)
    );

    // 历史视图
    const historyProvider = new HistoryProvider(context);
    context.subscriptions.push(
        vscode.window.registerTreeDataProvider('omc-history', historyProvider)
    );

    // Agents 视图
    const agentsProvider = new AgentsProvider();
    context.subscriptions.push(
        vscode.window.registerTreeDataProvider('omc-agents', agentsProvider)
    );
}

export function deactivate() {
    console.log('Oh My Coder is now deactivated');
    if (taskManager) {
        taskManager.dispose();
    }
}
