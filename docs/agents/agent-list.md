# Agent 系统 — 完整清单

> 本文从 README.md 迁移而来，包含全部 31 个专业 Agent 的详细说明。

## 🤖 Agent 系统（31 个专业 Agent）<a id="-agent-系统31-个专业-agent"></a>

### 构建 / 分析通道（9）
| Agent | 功能描述 |
|-------|---------|
| `ExploreAgent` | 探索代码库结构，生成项目地图 |
| `AnalystAgent` | 分析需求和任务，发现隐藏约束 |
| `PlannerAgent` | 规划开发计划，制定执行步骤 |
| `ArchitectAgent` | 设计系统架构和技术选型 |
| `ExecutorAgent` | 执行代码生成，支持 14 种语言 |
| `VerifierAgent` | 验证代码正确性，运行测试 |
| `DebuggerAgent` | 调试和修复代码错误 |
| `TracerAgent` | 追踪代码执行流程，定位根因 |
| `PerformanceAgent` | 性能分析、瓶颈定位和优化建议 |

### 审查通道（2）
| Agent | 功能描述 |
|-------|---------|
| `CodeReviewerAgent` | 代码质量审查，发现坏味道 |
| `SecurityReviewerAgent` | 代码安全审查，扫描漏洞 |

### 领域通道（16）
| Agent | 功能描述 |
|-------|---------|
| `TestEngineerAgent` | 生成单元测试和集成测试 |
| `DesignerAgent` | 界面和交互设计 |
| `VisionAgent` | 截图布局分析 + UI 代码自动生成（HTML/CSS/React） |
| `DocumentAgent` | 长篇技术文档、API 参考、架构文档 |
| `WriterAgent` | 快速文档、README、注释生成 |
| `ScientistAgent` | 技术调研和可行性分析 |
| `GitMasterAgent` | Git 操作自动化 |
| `CodeSimplifierAgent` | 代码简化优化 |
| `QATesterAgent` | QA 测试和质量验证 |
| `DatabaseAgent` | 数据库设计、SQL 优化和迁移 |
| `APIAgent` | REST API 设计、接口规范和文档 |
| `DevOpsAgent` | CI/CD 流水线、容器化和部署 |
| `UMLAgent` | UML 图表生成（类图/时序图/流程图） |
| `MigrationAgent` | 代码迁移、框架升级和技术债清理 |
| `AuthAgent` | 认证授权设计、安全策略审查 |
| `DataAgent` | 数据处理、ETL 流程和数据质量 |

### 协调通道（4）
| Agent | 功能描述 |
|-------|---------|
| `PromptAgent` | Prompt 工程优化和模板管理 |
| `SelfImprovingAgent` | 从执行结果中学习，优化路由策略 |
| `SkillManageAgent` | Skill 管理和自进化、经验沉淀 |
| `CriticAgent` | 审查计划和设计，提供改进建议 |

**模型层级说明：**
- **LOW** - 快速便宜（DeepSeek-V3 / GLM-4-Flash / Qwen-Turbo）
- **MEDIUM** - 平衡性能和成本（DeepSeek-R1 / Qwen-Max）
- **HIGH** - 最高质量推理（DeepSeek-R1-Reasoner / Qwen-Plus）

---

