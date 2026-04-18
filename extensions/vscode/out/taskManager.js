"use strict";
/**
 * 任务管理器
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
exports.TaskManager = exports.TaskStatus = void 0;
const vscode = __importStar(require("vscode"));
const child_process_1 = require("child_process");
const path = __importStar(require("path"));
const fs = __importStar(require("fs"));
var TaskStatus;
(function (TaskStatus) {
    TaskStatus["Idle"] = "idle";
    TaskStatus["Running"] = "running";
    TaskStatus["Completed"] = "completed";
    TaskStatus["Error"] = "error";
})(TaskStatus || (exports.TaskStatus = TaskStatus = {}));
class TaskManager {
    context;
    currentTask = null;
    process = null;
    _onDidChangeStatus = new vscode.EventEmitter();
    _onDidChangeOutput = new vscode.EventEmitter();
    outputBuffer = "";
    onDidChangeStatus = this._onDidChangeStatus.event;
    onDidChangeOutput = this._onDidChangeOutput.event;
    constructor(context) {
        this.context = context;
    }
    /**
     * 获取 CLI 路径
     * 优先使用 which/where 查找，找不到则尝试默认路径
     */
    getCliPath() {
        try {
            // 尝试使用 which (Unix/macOS) 或 where (Windows) 查找
            if (process.platform === "win32") {
                return (0, child_process_1.execSync)("where omc", { encoding: "utf-8" }).trim().split("\n")[0];
            }
            else {
                return (0, child_process_1.execSync)("which omc", { encoding: "utf-8" }).trim();
            }
        }
        catch {
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
    getStatus() {
        return this.currentTask?.status ?? TaskStatus.Idle;
    }
    getCurrentTask() {
        return this.currentTask;
    }
    getOutput() {
        return this.outputBuffer;
    }
    async runTask(taskData) {
        if (this.currentTask && this.currentTask.status === TaskStatus.Running) {
            vscode.window.showWarningMessage("已有任务在运行，请等待完成或停止");
            return { success: false, output: "已有任务在运行" };
        }
        const task = {
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
            this._onDidChangeStatus.fire(TaskStatus.Completed);
            return result;
        }
        catch (error) {
            task.status = TaskStatus.Error;
            task.endTime = new Date();
            task.error = error instanceof Error ? error.message : String(error);
            task.output = task.error;
            this._onDidChangeStatus.fire(TaskStatus.Error);
            throw error;
        }
    }
    async executeTask(task) {
        const config = vscode.workspace.getConfiguration("omc");
        const apiKey = config.get("apiKey") || process.env.DEEPSEEK_API_KEY || "";
        const defaultModel = config.get("defaultModel") || "deepseek";
        const maxTokens = config.get("maxTokens") || 4096;
        const temperature = config.get("temperature") || 0.7;
        if (!apiKey) {
            throw new Error("请配置 API Key：设置中搜索 \"omc.apiKey\" 或设置环境变量");
        }
        return new Promise((resolve, reject) => {
            const args = [
                "run",
                task.description,
                "--model", defaultModel,
                "--max-tokens", String(maxTokens),
                "--temperature", String(temperature),
            ];
            if (task.workflow) {
                args.push("--workflow", task.workflow);
            }
            if (task.fileName) {
                args.push("--file", task.fileName);
            }
            const env = {
                ...process.env,
                DEEPSEEK_API_KEY: apiKey,
            };
            const cliPath = this.getCliPath();
            this.process = (0, child_process_1.spawn)(cliPath, args, { env });
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
                }
                else {
                    reject(new Error(error || `进程退出码: ${code}`));
                }
            });
            this.process.on("error", (err) => {
                this.process = null;
                if (err.code === "ENOENT") {
                    reject(new Error("找不到 omc 命令，请先安装 oh-my-coder：pip install oh-my-coder"));
                }
                else {
                    reject(err);
                }
            });
        });
    }
    parseMetrics(output) {
        const tokenMatch = output.match(/Tokens[:\s]+(\d+)/i);
        const durationMatch = output.match(/Duration[:\s]+(\d+\.?\d*)\s*s/i);
        const costMatch = output.match(/Cost[:\s]+\$?(\d+\.?\d*)/i);
        return {
            tokens: tokenMatch ? parseInt(tokenMatch[1], 10) : 0,
            duration: durationMatch ? parseFloat(durationMatch[1]) : 0,
            cost: costMatch ? parseFloat(costMatch[1]) : 0,
        };
    }
    stop() {
        if (this.process) {
            this.process.kill();
            this.process = null;
        }
        if (this.currentTask) {
            this.currentTask.status = TaskStatus.Idle;
            this._onDidChangeStatus.fire(TaskStatus.Idle);
        }
    }
    dispose() {
        this.stop();
        this._onDidChangeStatus.dispose();
        this._onDidChangeOutput.dispose();
    }
}
exports.TaskManager = TaskManager;
//# sourceMappingURL=taskManager.js.map