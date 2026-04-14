# Agent 系统

## 30 个专业 Agent

oh-my-coder 内置 30 个专业 Agent，分为四个协作通道。

### 构建 / 分析通道

| Agent | 功能 | 模型层级 |
|-------|------|----------|
| `ExploreAgent` | 探索代码库结构，生成项目地图 | LOW |
| `AnalystAgent` | 分析需求和任务，发现隐藏约束 | LOW |
| `PlannerAgent` | 规划开发计划，制定执行步骤 | MEDIUM |
| `ArchitectAgent` | 设计系统架构和技术选型 | HIGH |
| `ExecutorAgent` | 执行代码生成，支持 14 种语言 | MEDIUM |
| `VerifierAgent` | 验证代码正确性，运行测试 | MEDIUM |
| `DebuggerAgent` | 调试和修复代码错误 | MEDIUM |
| `TracerAgent` | 追踪代码执行流程，定位根因 | MEDIUM |

### 审查通道

| Agent | 功能 | 模型层级 |
|-------|------|----------|
| `CodeReviewerAgent` | 代码质量审查，发现坏味道 | MEDIUM |
| `SecurityReviewerAgent` | 代码安全审查，扫描漏洞 | HIGH |

### 领域通道

| Agent | 功能 |
|-------|------|
| `TestEngineerAgent` | 生成单元测试和集成测试 |
| `DesignerAgent` | 界面和交互设计 |
| `VisionAgent` | 截图布局分析 + UI 代码自动生成 |
| `DocumentAgent` | 技术文档、API 参考、架构文档 |
| `WriterAgent` | 快速文档、README、注释生成 |
| `ScientistAgent` | 技术调研和可行性分析 |
| `GitMasterAgent` | Git 操作自动化 |
| `CodeSimplifierAgent` | 代码简化优化 |
| `QATesterAgent` | QA 测试和质量验证 |
| `DatabaseAgent` | 数据库设计、SQL 优化和迁移 |
| `APIAgent` | REST API 设计、接口规范和文档 |
| `DevOpsAgent` | CI/CD 流水线、容器化和部署 |
| `UMLAgent` | UML 图表生成（类图/时序图/流程图） |
| `PerformanceAgent` | 性能分析、瓶颈定位和优化建议 |
| `MigrationAgent` | 代码迁移、框架升级和技术债清理 |
| `PromptAgent` | Prompt 工程优化和模板管理 |
| `AuthAgent` | 认证授权设计、安全策略审查 |
| `DataAgent` | 数据处理、ETL 流程和数据质量 |

### 协调通道

| Agent | 功能 | 模型层级 |
|-------|------|----------|
| `CriticAgent` | 审查计划和设计，提供改进建议 | MEDIUM |
| `SelfImprovingAgent` | 从执行结果中学习，优化路由策略 | LOW |

## 自定义 Agent

在 `src/agents/` 目录下创建新的 Agent 类：

```python
from src.agents.base import BaseAgent

class MyAgent(BaseAgent):
    name = "my-agent"
    description = "自定义 Agent 描述"
    model_tier = ModelTier.LOW

    async def execute(self, context: AgentContext) -> AgentResult:
        # 实现 Agent 逻辑
        ...
```

## 模型层级说明

- **LOW**：快速便宜，适合探索、分析等轻量任务
- **MEDIUM**：平衡性能和成本，适合大多数任务
- **HIGH**：最高质量推理，适合架构设计、安全审查等复杂场景
