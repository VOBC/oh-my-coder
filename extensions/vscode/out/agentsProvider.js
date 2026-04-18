"use strict";
/**
 * Agents 视图提供者 - 30 个 Agent
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
exports.AgentsProvider = void 0;
const vscode = __importStar(require("vscode"));
const AGENTS = [
    // === 构建通道 (BUILD) ===
    {
        name: "Planner",
        className: "PlannerAgent",
        description: "规划开发计划，制定执行步骤",
        channel: "BUILD",
        level: "MEDIUM",
    },
    {
        name: "Architect",
        className: "ArchitectAgent",
        description: "设计系统架构和技术选型",
        channel: "BUILD",
        level: "HIGH",
    },
    {
        name: "Executor",
        className: "ExecutorAgent",
        description: "执行代码生成，支持 14 种语言",
        channel: "BUILD",
        level: "LOW",
    },
    {
        name: "Verifier",
        className: "VerifierAgent",
        description: "验证代码正确性，运行测试",
        channel: "BUILD",
        level: "MEDIUM",
    },
    {
        name: "CodeSimplifier",
        className: "CodeSimplifierAgent",
        description: "简化代码，提高质量和可读性",
        channel: "BUILD",
        level: "LOW",
    },
    {
        name: "Migration",
        className: "MigrationAgent",
        description: "数据迁移与版本管理",
        channel: "BUILD",
        level: "MEDIUM",
    },
    // === 审查通道 (REVIEW) ===
    {
        name: "CodeReviewer",
        className: "CodeReviewerAgent",
        description: "代码质量审查，发现坏味道",
        channel: "REVIEW",
        level: "MEDIUM",
    },
    {
        name: "SecurityReviewer",
        className: "SecurityReviewerAgent",
        description: "代码安全审查，扫描漏洞",
        channel: "REVIEW",
        level: "HIGH",
    },
    {
        name: "Critic",
        className: "CriticAgent",
        description: "多角度审查计划和设计，提供改进建议",
        channel: "REVIEW",
        level: "HIGH",
    },
    {
        name: "Performance",
        className: "PerformanceAgent",
        description: "性能分析与优化建议",
        channel: "REVIEW",
        level: "MEDIUM",
    },
    // === 调试通道 (DEBUG) ===
    {
        name: "Debugger",
        className: "DebuggerAgent",
        description: "调试和修复代码错误",
        channel: "DEBUG",
        level: "MEDIUM",
    },
    {
        name: "Tracer",
        className: "TracerAgent",
        description: "追踪代码执行流程，定位根因",
        channel: "DEBUG",
        level: "HIGH",
    },
    // === 领域通道 (DOMAIN) ===
    {
        name: "TestEngineer",
        className: "TestEngineerAgent",
        description: "生成单元测试和集成测试",
        channel: "DOMAIN",
        level: "LOW",
    },
    {
        name: "QATester",
        className: "QATesterAgent",
        description: "交互式测试和端到端验证",
        channel: "DOMAIN",
        level: "MEDIUM",
    },
    {
        name: "Designer",
        className: "DesignerAgent",
        description: "界面和交互设计",
        channel: "DOMAIN",
        level: "MEDIUM",
    },
    {
        name: "Writer",
        className: "WriterAgent",
        description: "文档和注释生成",
        channel: "DOMAIN",
        level: "LOW",
    },
    {
        name: "Document",
        className: "DocumentAgent",
        description: "长篇结构化技术文档编写",
        channel: "DOMAIN",
        level: "MEDIUM",
    },
    {
        name: "Scientist",
        className: "ScientistAgent",
        description: "技术调研和可行性分析",
        channel: "DOMAIN",
        level: "HIGH",
    },
    {
        name: "GitMaster",
        className: "GitMasterAgent",
        description: "Git 操作自动化",
        channel: "DOMAIN",
        level: "LOW",
    },
    {
        name: "Explore",
        className: "ExploreAgent",
        description: "代码库结构探索，生成项目地图",
        channel: "DOMAIN",
        level: "LOW",
    },
    {
        name: "Vision",
        className: "VisionAgent",
        description: "视觉分析与 UI 代码生成",
        channel: "DOMAIN",
        level: "MEDIUM",
    },
    {
        name: "UML",
        className: "UMLAgent",
        description: "架构图与可视化",
        channel: "DOMAIN",
        level: "MEDIUM",
    },
    {
        name: "Analyst",
        className: "AnalystAgent",
        description: "需求分析，苏格拉底式提问",
        channel: "DOMAIN",
        level: "HIGH",
    },
    {
        name: "Database",
        className: "DatabaseAgent",
        description: "数据库设计与 SQL 优化",
        channel: "DOMAIN",
        level: "MEDIUM",
    },
    {
        name: "DevOps",
        className: "DevOpsAgent",
        description: "DevOps 与 CI/CD 自动化",
        channel: "DOMAIN",
        level: "MEDIUM",
    },
    {
        name: "API",
        className: "APIAgent",
        description: "REST API 设计与实现",
        channel: "DOMAIN",
        level: "MEDIUM",
    },
    {
        name: "Auth",
        className: "AuthAgent",
        description: "认证与授权实现",
        channel: "DOMAIN",
        level: "HIGH",
    },
    {
        name: "Data",
        className: "DataAgent",
        description: "数据处理与 ETL",
        channel: "DOMAIN",
        level: "LOW",
    },
    {
        name: "Prompt",
        className: "PromptAgent",
        description: "Prompt 工程与优化",
        channel: "DOMAIN",
        level: "LOW",
    },
    {
        name: "SkillManage",
        className: "SkillManageAgent",
        description: "Skill 管理与索引维护",
        channel: "DOMAIN",
        level: "LOW",
    },
    {
        name: "SelfImproving",
        className: "SelfImprovingAgent",
        description: "自我改进与持续学习",
        channel: "DOMAIN",
        level: "HIGH",
    },
];
class AgentsProvider {
    _onDidChangeTreeData = new vscode.EventEmitter();
    onDidChangeTreeData = this._onDidChangeTreeData.event;
    getTreeItem(element) {
        return element;
    }
    getChildren(element) {
        if (element) {
            // 返回该通道下的 Agent 列表
            const agents = AGENTS.filter((a) => a.channel === element.label);
            return Promise.resolve(agents.map((a) => new AgentItem(a.name, false, undefined, a.description, a.level)));
        }
        // 按通道分组
        const channels = ["BUILD", "REVIEW", "DEBUG", "DOMAIN"];
        const items = [];
        for (const channel of channels) {
            const channelAgents = AGENTS.filter((a) => a.channel === channel);
            items.push(new AgentItem(channel, true, channelAgents.length));
        }
        return Promise.resolve(items);
    }
}
exports.AgentsProvider = AgentsProvider;
class AgentItem extends vscode.TreeItem {
    label;
    isChannel;
    count;
    desc;
    level;
    constructor(label, isChannel, count, desc, level) {
        super(label, isChannel
            ? vscode.TreeItemCollapsibleState.Collapsed
            : vscode.TreeItemCollapsibleState.None);
        this.label = label;
        this.isChannel = isChannel;
        this.count = count;
        this.desc = desc;
        this.level = level;
        if (isChannel) {
            this.description = `${count} agents`;
            this.iconPath = this.getChannelIcon();
        }
        else {
            this.description = level || "";
            this.tooltip = desc || label;
            this.iconPath = this.getLevelIcon();
        }
    }
    getChannelIcon() {
        const icons = {
            BUILD: "tools",
            REVIEW: "eye",
            DEBUG: "bug",
            DOMAIN: "package",
        };
        return new vscode.ThemeIcon(icons[this.label] || "circle");
    }
    getLevelIcon() {
        const icons = {
            LOW: "circle-outline",
            MEDIUM: "circle-filled",
            HIGH: "star",
        };
        return new vscode.ThemeIcon(icons[this.level || ""] || "robot");
    }
}
//# sourceMappingURL=agentsProvider.js.map