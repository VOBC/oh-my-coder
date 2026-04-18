"use strict";
/**
 * 状态栏管理器
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
exports.StatusBarManager = void 0;
const vscode = __importStar(require("vscode"));
const taskManager_1 = require("./taskManager");
class StatusBarManager {
    statusBarItem;
    taskManager;
    constructor(taskManager) {
        this.taskManager = taskManager;
        this.statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
        this.update();
        this.statusBarItem.show();
        // 监听任务状态变化
        this.taskManager.onDidChangeStatus(() => this.update());
    }
    update() {
        const config = vscode.workspace.getConfiguration('omc');
        if (!config.get('showStatusBar')) {
            this.statusBarItem.hide();
            return;
        }
        const status = this.taskManager.getStatus();
        if (status === taskManager_1.TaskStatus.Idle) {
            this.statusBarItem.text = '$(hubot) OMC';
            this.statusBarItem.tooltip = 'Oh My Coder - 就绪';
            this.statusBarItem.command = 'omc.openPanel';
            this.statusBarItem.backgroundColor = undefined;
        }
        else if (status === taskManager_1.TaskStatus.Running) {
            this.statusBarItem.text = '$(sync~spin) OMC 运行中...';
            this.statusBarItem.tooltip = '点击查看进度';
            this.statusBarItem.command = 'omc.openPanel';
            this.statusBarItem.backgroundColor = new vscode.ThemeColor('statusBarItem.warningBackground');
        }
        else if (status === taskManager_1.TaskStatus.Error) {
            this.statusBarItem.text = '$(error) OMC 错误';
            this.statusBarItem.tooltip = '任务执行失败，点击查看详情';
            this.statusBarItem.command = 'omc.showHistory';
            this.statusBarItem.backgroundColor = new vscode.ThemeColor('statusBarItem.errorBackground');
        }
        this.statusBarItem.show();
    }
    showProgress(message) {
        this.statusBarItem.text = `$(sync~spin) ${message}`;
        this.statusBarItem.show();
    }
    dispose() {
        this.statusBarItem.dispose();
    }
}
exports.StatusBarManager = StatusBarManager;
//# sourceMappingURL=statusBar.js.map