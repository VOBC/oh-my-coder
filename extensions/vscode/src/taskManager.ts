/**
 * 任务管理器 - 适配 Monorepo CLI API
 */

import * as vscode from "vscode";
import { spawn, ChildProcess, execSync } from "child_process";
import * as path from "path";
import * as fs from "fs";

export enum TaskStatus {
    Idle = "idle",
    Running = "running",
    Completed = "completed",
    Error = "error",
}

export interface Task {
    id: string;
    description: string;
    model?: string;
    workflow?: string;
    project?: string;
    notify?: string;
    crossValidate?: boolean;
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
    private historyProvider: any = null;
    private _onDidChangeStatus = new vscode.EventEmitter<TaskStatus>();
    private _onDidChangeOutput = new vscode.EventEmitter<string>();
    private outputBuffer: string = "";

    readonly onDidChangeStatus = this._onDidChangeStatus.event;
    readonly onDidChangeOutput = this._onDidChangeOutput.event;

    constructor(context: vscode.ExtensionContext) {
        this.context = context;
    }

    setHistoryProvider(historyProvider: any): void {
        this.historyProvider = historyProvider;
    }

    /**
     * 获取 CLI 路径
     * 优先使用 which/where 查找，找不到则尝试默认路径
     */
    private getCliPath(): string {
        try {
            // 尝试使用 which (Unix/macOS) 或 where (Windows) 查找
            if (process.platform === "win32") {
                return execSync("where omc", { encoding: "utf-8" }).trim().split("\n")[0];
            } else {
                return execSync("which omc", { encoding: "utf-8" }).trim();
            }
        } catch {
            // 找不到，尝试默认路径
            const defaultPaths = [
                path.join(process.env.HOME || "", ".local", "bin", "omc"),
                path.join(process.env.HOME || "", ".cargo", "bin", "omc"),
                "/usr/local/bin/omc",
                "/usr/bin/omc",
            ];
            for (const p of defaultPaths) {
                if (fs.existsSync(p)) {
                    return p;
                }
            }
            // 最后尝试直接用 "omc"，让系统 PATH 去解析
            return "omc";
        }
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

    /**
     * 检查是否为本地模型（ollama 系列）
     */
    private isLocalModel(model: string): boolean {
        const localModels = ["ollama", "llama", "mistral", "codellama", "deepseek-coder"];
        return localModels.some(m => model.toLowerCase().includes(m));
    }

    async runTask(taskData: Omit<Task, "id" | "status">): Promise<TaskResult> {
        if (this.currentTask && this.currentTask.status === TaskStatus.Running) {
            vscode.window.showWarningMessage("已有任务在运行，请等待完成或停止");
            return { success: false, output: "已有任务在运行" };
        }

        const task: Task = {
            id: `task-${Date.now()}`,
            status: TaskStatus.Running,
            startTime: new Date(),
            ...taskData,
        };

        this.currentTask = task;
        this.outputBuffer = "";
        this._onDidChangeStatus.fire(TaskStatus.Running);

        try {
            const result = await this.executeTask(task);
            task.status = TaskStatus.Completed;
            task.endTime = new Date();
            task.output = result.output;
            
            // 记录到历史
            if (this.historyProvider) {
                const duration = task.startTime && task.endTime
                    ? (task.endTime.getTime() - task.startTime.getTime()) / 1000
                    : undefined;
                this.historyProvider.addEntry({
                    description: task.description,
                    status: 'completed',
                    model: task.model,
                    workflow: task.workflow,
                    duration: duration,
                    tokens: result.metrics?.tokens,
                });
            }
            
            this._onDidChangeStatus.fire(TaskStatus.Completed);
            return result;
        } catch (error) {
            task.status = TaskStatus.Error;
            task.endTime = new Date();
            task.error = error instanceof Error ? error.message : String(error);
            task.output = task.error;
            
            // 记录失败任务到历史
            if (this.historyProvider) {
                const duration = task.startTime && task.endTime
                    ? (task.endTime.getTime() - task.startTime.getTime()) / 1000
                    : undefined;
                this.historyProvider.addEntry({
                    description: task.description,
                    status: 'failed',
                    model: task.model,
                    workflow: task.workflow,
                    duration: duration,
                });
            }
            
            this._onDidChangeStatus.fire(TaskStatus.Error);
            throw error;
        }
    }

    private async executeTask(task: Task): Promise<TaskResult> {
        const config = vscode.workspace.getConfiguration("omc");
        const apiKey = config.get<string>("apiKey") || process.env.API_KEY || "";
        // 优先使用任务指定的模型，否则使用配置中的默认模型
        const taskModel = task.model || config.get<string>("defaultModel") || "deepseek";

        // 本地模型不需要 API key
        if (!apiKey && !this.isLocalModel(taskModel)) {
            throw new Error("请配置 API Key：设置中搜索 \"omc.apiKey\" 或设置环境变量 API_KEY");
        }

        // 判断使用本地模型路径还是普通 run 路径
        const useLocalModel = this.isLocalModel(taskModel);
        
        return new Promise((resolve, reject) => {
            let args: string[];
            
            if (useLocalModel) {
                // 本地模型路径: omc local chat <message> --model <model>
                args = [
                    "local",
                    "chat",
                    task.description,
                    "--model", taskModel,
                ];
            } else {
                // 标准路径: omc run <task> --model/-m --workflow/-w --project/-p --notify/-n --cross-validate
                args = [
                    "run",
                    task.description,
                    "--model", taskModel,
                ];

                // 新增参数映射
                if (task.workflow) {
                    args.push("--workflow", task.workflow);
                }

                if (task.project) {
                    args.push("--project", task.project);
                }

                if (task.notify) {
                    args.push("--notify", task.notify);
                }

                if (task.crossValidate) {
                    args.push("--cross-validate");
                }

                if (task.fileName) {
                    args.push("--file", task.fileName);
                }
            }

            const env: Record<string, string> = {
                ...process.env as Record<string, string>,
                API_KEY: apiKey,
            };

            const cliPath = this.getCliPath();
            this.process = spawn(cliPath, args, { env });

            let output = "";
            let error = "";

            this.process.stdout?.on("data", (data) => {
                const chunk = data.toString();
                output += chunk;
                this.outputBuffer += chunk;
                this._onDidChangeOutput.fire(chunk);
            });

            this.process.stderr?.on("data", (data) => {
                const chunk = data.toString();
                error += chunk;
                this.outputBuffer += chunk;
                this._onDidChangeOutput.fire(chunk);
            });

            this.process.on("close", (code) => {
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

            this.process.on("error", (err) => {
                this.process = null;
                if ((err as NodeJS.ErrnoException).code === "ENOENT") {
                    reject(new Error(
                        "找不到 omc 命令，请先安装 oh-my-coder：pip install oh-my-coder"
                    ));
                } else {
                    reject(err);
                }
            });
        });
    }

    /**
     * 获取本地模型列表
     */
    async getLocalModels(): Promise<string[]> {
        return new Promise((resolve, reject) => {
            const cliPath = this.getCliPath();
            const proc = spawn(cliPath, ["local", "list"], { 
                env: process.env as Record<string, string> 
            });

            let output = "";
            let error = "";

            proc.stdout?.on("data", (data) => {
                output += data.toString();
            });

            proc.stderr?.on("data", (data) => {
                error += data.toString();
            });

            proc.on("close", (code) => {
                if (code === 0) {
                    // 解析模型列表，每行一个模型名
                    const models = output
                        .split("\n")
                        .map(line => line.trim())
                        .filter(line => line && !line.startsWith("#"));
                    resolve(models);
                } else {
                    reject(new Error(error || `获取本地模型列表失败，退出码: ${code}`));
                }
            });

            proc.on("error", reject);
        });
    }

    /**
     * 检查本地模型服务状态
     */
    async checkLocalModelStatus(): Promise<{ running: boolean; version?: string }> {
        return new Promise((resolve) => {
            const cliPath = this.getCliPath();
            const proc = spawn(cliPath, ["local", "status"], { 
                env: process.env as Record<string, string> 
            });

            let output = "";

            proc.stdout?.on("data", (data) => {
                output += data.toString();
            });

            proc.on("close", () => {
                const versionMatch = output.match(/version[\s:]+(\S+)/i);
                resolve({
                    running: output.toLowerCase().includes("running") || output.includes("已运行"),
                    version: versionMatch?.[1],
                });
            });

            proc.on("error", () => {
                resolve({ running: false });
            });
        });
    }

    /**
     * 获取 Skill 列表
     */
    async getSkillList(): Promise<Array<{ name: string; description: string }>> {
        return new Promise((resolve, reject) => {
            const cliPath = this.getCliPath();
            const proc = spawn(cliPath, ["skill", "list", "--json"], { 
                env: process.env as Record<string, string> 
            });

            let output = "";
            let error = "";

            proc.stdout?.on("data", (data) => {
                output += data.toString();
            });

            proc.stderr?.on("data", (data) => {
                error += data.toString();
            });

            proc.on("close", (code) => {
                if (code === 0) {
                    try {
                        const skills = JSON.parse(output);
                        resolve(Array.isArray(skills) ? skills : []);
                    } catch {
                        // 非 JSON 格式，按行解析
                        const skills = output
                            .split("\n")
                            .map(line => line.trim())
                            .filter(line => line && !line.startsWith("#"))
                            .map(line => {
                                const parts = line.split(/\s{2,}/);
                                return { 
                                    name: parts[0] || line, 
                                    description: parts[1] || "" 
                                };
                            });
                        resolve(skills);
                    }
                } else {
                    reject(new Error(error || `获取 Skill 列表失败，退出码: ${code}`));
                }
            });

            proc.on("error", reject);
        });
    }

    /**
     * 运行 Skill
     */
    async runSkill(skillName: string, args: string[] = []): Promise<TaskResult> {
        return new Promise((resolve, reject) => {
            const cliPath = this.getCliPath();
            const proc = spawn(cliPath, ["skill", "run", skillName, ...args], { 
                env: process.env as Record<string, string> 
            });

            let output = "";
            let error = "";

            proc.stdout?.on("data", (data) => {
                const chunk = data.toString();
                output += chunk;
                this.outputBuffer += chunk;
                this._onDidChangeOutput.fire(chunk);
            });

            proc.stderr?.on("data", (data) => {
                const chunk = data.toString();
                error += chunk;
                this.outputBuffer += chunk;
                this._onDidChangeOutput.fire(chunk);
            });

            proc.on("close", (code) => {
                if (code === 0) {
                    resolve({
                        success: true,
                        output: output,
                        metrics: this.parseMetrics(output),
                    });
                } else {
                    reject(new Error(error || `Skill 运行失败，退出码: ${code}`));
                }
            });

            proc.on("error", reject);
        });
    }

    private parseMetrics(output: string): { tokens: number; duration: number; cost: number } {
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
