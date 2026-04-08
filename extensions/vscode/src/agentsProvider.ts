/**
 * Agents 视图提供者
 */

import * as vscode from 'vscode';

interface AgentInfo {
    name: string;
    className: string;
    description: string;
    channel: string;
    level: 'LOW' | 'MEDIUM' | 'HIGH';
}

const AGENTS: AgentInfo[] = [
    // 构建通道
    {
        name: 'Planner',
        className: 'PlannerAgent',
        description: '规划开发计划，制定执行步骤',
        channel: 'BUILD',
        level: 'MEDIUM',
    },
    {
        name: 'Architect',
        className: 'ArchitectAgent',
        description: '设计系统架构和技术选型',
        channel: 'BUILD',
        level: 'HIGH',
    },
    {
        name: 'Executor',
        className: 'ExecutorAgent',
        description: '执行代码生成，支持 14 种语言',
        channel: 'BUILD',
        level: 'LOW',
    },
    {
        name: 'Verifier',
        className: 'VerifierAgent',
        description: '验证代码正确性，运行测试',
        channel: 'BUILD',
        level: 'MEDIUM',
    },

    // 审查通道
    {
        name: 'CodeReviewer',
        className: 'CodeReviewerAgent',
        description: '代码质量审查，发现坏味道',
        channel: 'REVIEW',
        level: 'MEDIUM',
    },
    {
        name: 'SecurityReviewer',
        className: 'SecurityReviewerAgent',
        description: '代码安全审查，扫描漏洞',
        channel: 'REVIEW',
        level: 'HIGH',
    },

    // 调试通道
    {
        name: 'Debugger',
        className: 'DebuggerAgent',
        description: '调试和修复代码错误',
        channel: 'DEBUG',
        level: 'MEDIUM',
    },
    {
        name: 'Tracer',
        className: 'TracerAgent',
        description: '追踪代码执行流程，定位根因',
        channel: 'DEBUG',
        level: 'HIGH',
    },

    // 领域通道
    {
        name: 'TestEngineer',
        className: 'TestEngineerAgent',
        description: '生成单元测试和集成测试',
        channel: 'DOMAIN',
        level: 'LOW',
    },
    {
        name: 'Designer',
        className: 'DesignerAgent',
        description: '界面和交互设计',
        channel: 'DOMAIN',
        level: 'MEDIUM',
    },
    {
        name: 'Writer',
        className: 'WriterAgent',
        description: '文档和注释生成',
        channel: 'DOMAIN',
        level: 'LOW',
    },
    {
        name: 'Scientist',
        className: 'ScientistAgent',
        description: '技术调研和可行性分析',
        channel: 'DOMAIN',
        level: 'HIGH',
    },
    {
        name: 'GitMaster',
        className: 'GitMasterAgent',
        description: 'Git 操作自动化',
        channel: 'DOMAIN',
        level: 'LOW',
    },

    // 协调通道
    {
        name: 'Coordinator',
        className: 'CoordinatorAgent',
        description: '协调多 Agent 协作',
        channel: 'COORDINATION',
        level: 'MEDIUM',
    },
    {
        name: 'Critic',
        className: 'CriticAgent',
        description: '审查计划和设计，提供改进建议',
        channel: 'COORDINATION',
        level: 'HIGH',
    },
];

export class AgentsProvider implements vscode.TreeDataProvider<AgentItem> {
    private _onDidChangeTreeData = new vscode.EventEmitter<AgentItem | undefined | null>();
    readonly onDidChangeTreeData = this._onDidChangeTreeData.event;

    getTreeItem(element: AgentItem): vscode.TreeItem {
        return element;
    }

    getChildren(element?: AgentItem): Thenable<AgentItem[]> {
        if (element) {
            // 返回 Agent 详情
            return Promise.resolve([]);
        }

        // 按通道分组
        const channels = ['BUILD', 'REVIEW', 'DEBUG', 'DOMAIN', 'COORDINATION'];
        const items: AgentItem[] = [];

        for (const channel of channels) {
            const channelAgents = AGENTS.filter((a) => a.channel === channel);
            items.push(new AgentItem(channel, true, channelAgents.length));
        }

        return Promise.resolve(items);
    }
}

class AgentItem extends vscode.TreeItem {
    constructor(
        public readonly label: string,
        public readonly isChannel: boolean,
        public readonly count?: number
    ) {
        super(label, vscode.TreeItemCollapsibleState.Collapsed);

        if (isChannel) {
            this.description = `${count} agents`;
            this.iconPath = this.getChannelIcon();
        } else {
            this.iconPath = new vscode.ThemeIcon('robot');
        }
    }

    private getChannelIcon(): vscode.ThemeIcon {
        const icons: Record<string, string> = {
            BUILD: 'tools',
            REVIEW: 'eye',
            DEBUG: 'bug',
            DOMAIN: 'package',
            COORDINATION: 'organization',
        };
        return new vscode.ThemeIcon(icons[this.label] || 'circle');
    }
}
