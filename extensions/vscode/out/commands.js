"use strict";
/**
 * 命令管理器
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
exports.CommandManager = void 0;
const vscode = __importStar(require("vscode"));
class CommandManager {
    taskManager;
    statusBar;
    outputChannel;
    constructor(taskManager, statusBar) {
        this.taskManager = taskManager;
        this.statusBar = statusBar;
        this.outputChannel = vscode.window.createOutputChannel('Oh My Coder');
    }
    registerCommands(context) {
        // 运行任务
        context.subscriptions.push(vscode.commands.registerCommand('omc.runTask', async () => {
            await this.runTask();
        }));
        // 探索代码库
        context.subscriptions.push(vscode.commands.registerCommand('omc.exploreCode', async () => {
            await this.exploreCode();
        }));
        // 代码审查
        context.subscriptions.push(vscode.commands.registerCommand('omc.reviewCode', async () => {
            await this.reviewCode();
        }));
        // 调试代码
        context.subscriptions.push(vscode.commands.registerCommand('omc.debugCode', async () => {
            await this.debugCode();
        }));
        // 生成测试
        context.subscriptions.push(vscode.commands.registerCommand('omc.generateTest', async () => {
            await this.generateTest();
        }));
        // 显示历史
        context.subscriptions.push(vscode.commands.registerCommand('omc.showHistory', () => {
            this.showHistory();
        }));
        // 打开面板
        context.subscriptions.push(vscode.commands.registerCommand('omc.openPanel', () => {
            vscode.commands.executeCommand('workbench.view.extension.omc-sidebar');
        }));
        // 停止任务
        context.subscriptions.push(vscode.commands.registerCommand('omc.stopTask', () => {
            this.stopTask();
        }));
    }
    async runTask() {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            vscode.window.showWarningMessage('请先打开一个文件');
            return;
        }
        const selection = editor.selection;
        const selectedText = editor.document.getText(selection);
        const fileContent = editor.document.getText();
        const fileName = editor.document.fileName;
        // 获取任务描述
        const taskDescription = await vscode.window.showInputBox({
            prompt: '请输入任务描述',
            placeHolder: '例如：重构这段代码，添加类型注解',
            value: selectedText ? '解释选中的代码' : '',
        });
        if (!taskDescription) {
            return;
        }
        this.outputChannel.appendLine(`\n${'='.repeat(50)}`);
        this.outputChannel.appendLine(`任务: ${taskDescription}`);
        this.outputChannel.appendLine(`文件: ${fileName}`);
        this.outputChannel.appendLine(`${'='.repeat(50)}\n`);
        this.outputChannel.show(true);
        try {
            await this.taskManager.runTask({
                description: taskDescription,
                fileName,
                selectedText,
                fileContent,
            });
        }
        catch (error) {
            const errorMessage = error instanceof Error ? error.message : String(error);
            this.outputChannel.appendLine(`\n❌ 错误: ${errorMessage}`);
            vscode.window.showErrorMessage(`任务执行失败: ${errorMessage}`);
        }
    }
    async exploreCode() {
        const workspaceFolders = vscode.workspace.workspaceFolders;
        if (!workspaceFolders) {
            vscode.window.showWarningMessage('请先打开一个工作区');
            return;
        }
        const query = await vscode.window.showInputBox({
            prompt: '搜索代码库',
            placeHolder: '输入搜索关键词或问题',
        });
        if (!query) {
            return;
        }
        this.outputChannel.appendLine(`\n🔍 搜索: ${query}`);
        this.outputChannel.show(true);
        await this.taskManager.runTask({
            description: `探索代码库：${query}`,
            workflow: 'explore',
        });
    }
    async reviewCode() {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            vscode.window.showWarningMessage('请先打开一个文件');
            return;
        }
        const selection = editor.selection;
        const code = selection.isEmpty
            ? editor.document.getText()
            : editor.document.getText(selection);
        this.outputChannel.appendLine(`\n🔍 代码审查: ${editor.document.fileName}`);
        this.outputChannel.show(true);
        await this.taskManager.runTask({
            description: '审查代码质量',
            workflow: 'review',
            fileContent: code,
            fileName: editor.document.fileName,
        });
    }
    async debugCode() {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            vscode.window.showWarningMessage('请先打开一个文件');
            return;
        }
        const selection = editor.selection;
        const code = editor.document.getText(selection);
        if (!code) {
            vscode.window.showWarningMessage('请选中需要调试的代码');
            return;
        }
        const errorMessage = await vscode.window.showInputBox({
            prompt: '描述遇到的问题',
            placeHolder: '例如：这段代码运行时报错 xxx',
        });
        if (!errorMessage) {
            return;
        }
        this.outputChannel.appendLine(`\n🐛 调试: ${errorMessage}`);
        this.outputChannel.show(true);
        await this.taskManager.runTask({
            description: `调试问题：${errorMessage}`,
            workflow: 'debug',
            fileContent: code,
            fileName: editor.document.fileName,
        });
    }
    async generateTest() {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            vscode.window.showWarningMessage('请先打开一个文件');
            return;
        }
        const selection = editor.selection;
        const code = selection.isEmpty
            ? editor.document.getText()
            : editor.document.getText(selection);
        this.outputChannel.appendLine(`\n🧪 生成测试: ${editor.document.fileName}`);
        this.outputChannel.show(true);
        await this.taskManager.runTask({
            description: '生成单元测试',
            workflow: 'test',
            fileContent: code,
            fileName: editor.document.fileName,
        });
    }
    showHistory() {
        vscode.commands.executeCommand('workbench.view.extension.omc-sidebar');
        vscode.commands.executeCommand('omc-history.focus');
    }
    stopTask() {
        this.taskManager.stop();
        this.outputChannel.appendLine('\n⏹️ 任务已停止');
        vscode.window.showInformationMessage('任务已停止');
    }
    async showTaskResult(result) {
        if (typeof result === 'object' && result !== null) {
            const r = result;
            if (r.output) {
                const action = await vscode.window.showInformationMessage('任务完成！查看输出？', '查看输出', '打开文件', '关闭');
                if (action === '查看输出') {
                    this.outputChannel.show();
                }
            }
        }
    }
    dispose() {
        this.outputChannel.dispose();
    }
}
exports.CommandManager = CommandManager;
//# sourceMappingURL=commands.js.map