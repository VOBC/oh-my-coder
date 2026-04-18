"use strict";
/**
 * Oh My Coder VS Code Extension
 *
 * 多智能体 AI 编程助手扩展
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
exports.activate = activate;
exports.deactivate = deactivate;
const vscode = __importStar(require("vscode"));
const agentPanel_1 = require("./agentPanel");
const statusBar_1 = require("./statusBar");
const commands_1 = require("./commands");
const taskManager_1 = require("./taskManager");
const historyProvider_1 = require("./historyProvider");
const agentsProvider_1 = require("./agentsProvider");
let statusBar;
let commandManager;
let taskManager;
function activate(context) {
    console.log('Oh My Coder is now active!');
    // 初始化任务管理器
    taskManager = new taskManager_1.TaskManager(context);
    // 初始化状态栏
    statusBar = new statusBar_1.StatusBarManager(taskManager);
    context.subscriptions.push(statusBar);
    // 初始化命令管理器
    commandManager = new commands_1.CommandManager(taskManager, statusBar);
    commandManager.registerCommands(context);
    // 注册侧边栏视图
    registerViews(context);
    // 注册 Webview 面板
    const provider = new agentPanel_1.OMCProvider(context.extensionUri, taskManager);
    context.subscriptions.push(vscode.window.registerWebviewViewProvider('omc-tasks', provider));
    // 监听配置变更
    context.subscriptions.push(vscode.workspace.onDidChangeConfiguration((e) => {
        if (e.affectsConfiguration('omc')) {
            statusBar.update();
        }
    }));
    // 首次启动检测 API Key
    const config = vscode.workspace.getConfiguration('omc');
    const apiKey = config.get('apiKey') || process.env.DEEPSEEK_API_KEY || '';
    if (!apiKey) {
        setTimeout(() => {
            vscode.window.showWarningMessage('Oh My Coder: 未检测到 API Key，请先配置后再使用', '配置 API Key', '使用 GLM 免费模型').then((selection) => {
                if (selection === '配置 API Key') {
                    vscode.commands.executeCommand('workbench.action.openSettings', 'omc.apiKey');
                }
                else if (selection === '使用 GLM 免费模型') {
                    vscode.window.showInformationMessage('GLM 免费模型快速配置：\n1. 访问 https://open.bigmodel.cn 注册\n2. 获取 API Key\n3. 在设置中填入 omc.apiKey，模型选 glm');
                }
            });
        }, 3000);
    }
    // 显示欢迎消息
    if (config.get('showWelcome')) {
        vscode.window.showInformationMessage('🤖 Oh My Coder 已启动！使用 Ctrl+Shift+Enter 运行任务', '打开面板', '不再显示').then((selection) => {
            if (selection === '打开面板') {
                vscode.commands.executeCommand('omc.openPanel');
            }
            else if (selection === '不再显示') {
                config.update('showWelcome', false);
            }
        });
    }
}
function registerViews(context) {
    // 任务视图
    const tasksProvider = new agentPanel_1.OMCProvider(context.extensionUri, taskManager);
    context.subscriptions.push(vscode.window.registerTreeDataProvider('omc-tasks', tasksProvider));
    // 历史视图
    const historyProvider = new historyProvider_1.HistoryProvider(context);
    context.subscriptions.push(vscode.window.registerTreeDataProvider('omc-history', historyProvider));
    // Agents 视图
    const agentsProvider = new agentsProvider_1.AgentsProvider();
    context.subscriptions.push(vscode.window.registerTreeDataProvider('omc-agents', agentsProvider));
}
function deactivate() {
    console.log('Oh My Coder is now deactivated');
    if (taskManager) {
        taskManager.dispose();
    }
}
//# sourceMappingURL=extension.js.map