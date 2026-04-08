/**
 * 任务管理器
 */

import * as vscode from 'vscode';
import * as path from 'path';
import { spawn, ChildProcess } from 'child_process';

export enum TaskStatus {
    Idle = 'idle',
    Running = 'running',
    Completed = 'completed',
    Error = 'error',
}

export interface Task {
    id: string;
    description: string;
    workflow?: string;
    fileName?: string;
    selectedText?: string;
    fileContent?: string;
    status: TaskStatus;
    output?: string;
    startTime?: Date;
    endTime?: Date;
    error?: string;
}

export interface TaskResult {
    success: boolean;
    output: string;
    files?: string[];
    metrics?: {
        tokens: number;
        duration: number;
        cost: number;
    };
}

export class TaskManager implements vscode.Disposable {
    private context: vscode.ExtensionContext;
    private currentTask: Task | null = null;
    private process: ChildProcess | null = null;
    private _onDidChangeStatus = new vscode.EventEmitter<TaskStatus>();
    private _onDidChangeOutput = new vscode.EventEmitter<string>();
    private outputBuffer: string = '';

    readonly onDidChangeStatus = this._onDidChangeStatus.event;
    readonly onDidChangeOutput = this._onDidChangeOutput.event;

    constructor(context: vscode.ExtensionContext) {
        this.context = context;
    }

    getStatus(): TaskStatus {
        return this.currentTask?.status ?? TaskStatus.Idle;
    }

    getCurrentTask(): Task | null {
        return this.currentTask;
    }

    getOutput(): string {
        return this.outputBuffer;
    }

    async runTask(taskData: Omit<Task, 'id' | 'status'>): Promise<TaskResult> {
        if (this.currentTask && this.currentTask.status === TaskStatus.Running) {
            vscode.window.showWarningMessage('已有任务在运行，请等待完成或停止');
            return { success: false, output: '已有任务在运行' };
        }

        const task: Task = {
            id: `task-${Date.now()}`,
            status: TaskStatus.Running,
            startTime: new Date(),
            ...taskData,
        };

        this.currentTask = task;
        this.outputBuffer = '';
        this._onDidChangeStatus.fire(TaskStatus.Running);

        try {
            const result = await this.executeTask(task);
            task.status = TaskStatus.Completed;
            task.endTime = new Date();
            task.output = result.output;
            this._onDidChangeStatus.fire(TaskStatus.Completed);
            return result;
        } catch (error) {
            task.status = TaskStatus.Error;
            task.endTime = new Date();
            task.error = error instanceof Error ? error.message : String(error);
            task.output = task.error;
            this._onDidChangeStatus.fire(TaskStatus.Error);
            throw error;
        }
    }

    private async executeTask(task: Task): Promise<TaskResult> {
        const config = vscode.workspace.getConfiguration('omc');
        const apiKey = config.get<string>('apiKey') || process.env.DEEPSEEK_API_KEY || '';
        const defaultModel = config.get<string>('defaultModel') || 'deepseek';
        const maxTokens = config.get<number>('maxTokens') || 4096;
        const temperature = config.get<number>('temperature') || 0.7;

        if (!apiKey) {
            throw new Error('请配置 API Key：设置中搜索 "omc.apiKey" 或设置环境变量');
        }

        return new Promise((resolve, reject) => {
            // 调用 oh-my-coder CLI
            const cliPath = this.getCliPath();
            const args = [
                'run',
                task.description,
                '--model', defaultModel,
                '--max-tokens', String(maxTokens),
                '--temperature', String(temperature),
            ];

            if (task.workflow) {
                args.push('--workflow', task.workflow);
            }

            if (task.fileName) {
                args.push('--file', task.fileName);
            }

            this.process = spawn('python', ['-m', 'src.main', ...args], {
                cwd: cliPath,
                env: {
                    ...process.env,
                    DEEPSEEK_API_KEY: apiKey,
                },
            });

            let output = '';
            let error = '';

            this.process.stdout?.on('data', (data) => {
                const chunk = data.toString();
                output += chunk;
                this.outputBuffer += chunk;
                this._onDidChangeOutput.fire(chunk);
            });

            this.process.stderr?.on('data', (data) => {
                const chunk = data.toString();
                error += chunk;
                this.outputBuffer += chunk;
                this._onDidChangeOutput.fire(chunk);
            });

            this.process.on('close', (code) => {
                this.process = null;

                if (code === 0) {
                    resolve({
                        success: true,
                        output: output,
                        metrics: this.parseMetrics(output),
                    });
                } else {
                    reject(new Error(error || `进程退出码: ${code}`));
                }
            });

            this.process.on('error', (err) => {
                this.process = null;
                reject(err);
            });
        });
    }

    private getCliPath(): string {
        // 尝试查找 oh-my-coder 安装路径
        const workspaceFolders = vscode.workspace.workspaceFolders;
        if (workspaceFolders) {
            const localPath = path.join(workspaceFolders[0].uri.fsPath, 'oh-my-coder');
            // 检查是否存在
            return localPath;
        }
        return path.dirname(path.dirname(path.dirname(__dirname)));
    }

    private parseMetrics(output: string): { tokens: number; duration: number; cost: number } {
        // 从输出中解析指标
        const tokenMatch = output.match(/Tokens[:\s]+(\d+)/i);
        const durationMatch = output.match(/Duration[:\s]+(\d+\.?\d*)\s*s/i);
        const costMatch = output.match(/Cost[:\s]+\$?(\d+\.?\d*)/i);

        return {
            tokens: tokenMatch ? parseInt(tokenMatch[1], 10) : 0,
            duration: durationMatch ? parseFloat(durationMatch[1]) : 0,
            cost: costMatch ? parseFloat(costMatch[1]) : 0,
        };
    }

    stop(): void {
        if (this.process) {
            this.process.kill();
            this.process = null;
        }
        if (this.currentTask) {
            this.currentTask.status = TaskStatus.Idle;
            this._onDidChangeStatus.fire(TaskStatus.Idle);
        }
    }

    dispose(): void {
        this.stop();
        this._onDidChangeStatus.dispose();
        this._onDidChangeOutput.dispose();
    }
}
