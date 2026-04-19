# Oh My Coder 架构设计

## 系统架构总览

```mermaid
graph TB
    subgraph 用户层["用户层"]
        CLI[CLI 客户端]
        WEB[Web 界面]
        API[REST API]
    end

    subgraph 编排层["编排层"]
        ORCH[Orchestrator<br/>智能编排引擎]
        ROUTER[ModelRouter<br/>模型路由器]
    end

    subgraph Agent层["Agent 层"]
        direction TB
        A1[ExploreAgent]
        A2[AnalystAgent]
        A3[ArchitectAgent]
        A4[ExecutorAgent]
        A5[VerifierAgent]
        A6[CodeReviewerAgent]
        A7[SecurityReviewerAgent]
        A8[其他 24 个...]
    end

    subgraph 模型层["模型适配层"]
        M1[DeepSeek]
        M2[Kimi]
        M3[豆包]
        M4[通义千问]
        M5[智谱 GLM]
        M6[其他 6 个...]
    end

    CLI --> ORCH
    WEB --> ORCH
    API --> ORCH
    
    ORCH --> ROUTER
    ORCH --> A1
    ORCH --> A2
    ORCH --> A3
    ORCH --> A4
    ORCH --> A5
    ORCH --> A6
    ORCH --> A7
    ORCH --> A8

    A1 --> ROUTER
    A2 --> ROUTER
    A3 --> ROUTER
    A4 --> ROUTER
    A5 --> ROUTER

    ROUTER --> M1
    ROUTER --> M2
    ROUTER --> M3
    ROUTER --> M4
    ROUTER --> M5
    ROUTER --> M6

    style ORCH fill:#4A90E2,stroke:#fff,color:#fff
    style ROUTER fill:#50C878,stroke:#fff,color:#fff
```

## 三层模型路由机制

```mermaid
flowchart LR
    TASK[任务类型] --> ROUTER{智能路由器}
    
    ROUTER -->|EXPLORE| LOW[LOW 层]
    ROUTER -->|ANALYST| MED[MEDIUM 层]
    ROUTER -->|ARCHITECT| HIGH[HIGH 层]
    ROUTER -->|CODE_GEN| MED
    ROUTER -->|REVIEW| LOW
    
    LOW --> DS1[DeepSeek-V3<br/>¥0.001/1K]
    MED --> DS2[DeepSeek-R1<br/>¥0.002/1K]
    HIGH --> DS3[DeepSeek-R1-Reasoner<br/>¥0.003/1K]

    style ROUTER fill:#50C878,stroke:#fff,color:#fff
    style LOW fill:#90EE90,stroke:#333
    style MED fill:#FFD700,stroke:#333
    style HIGH fill:#FF6B6B,stroke:#fff,color:#fff
```

## 工作流执行流程

### Build 工作流（构建）

```mermaid
sequenceDiagram
    participant U as 用户
    participant O as Orchestrator
    participant E as ExploreAgent
    participant A as AnalystAgent
    participant P as PlannerAgent
    participant AR as ArchitectAgent
    participant EX as ExecutorAgent
    participant V as VerifierAgent

    U->>O: 提交构建任务
    O->>E: 探索项目结构
    E-->>O: 返回项目地图
    O->>A: 分析需求
    A-->>O: 返回需求分析
    O->>P: 制定计划
    P-->>O: 返回执行计划
    O->>AR: 设计架构
    AR-->>O: 返回架构设计
    O->>EX: 生成代码
    EX-->>O: 返回代码文件
    O->>V: 验证测试
    V-->>O: 返回测试结果
    O-->>U: 任务完成
```

### Review 工作流（审查）

```mermaid
sequenceDiagram
    participant U as 用户
    participant O as Orchestrator
    participant CR as CodeReviewerAgent
    participant SR as SecurityReviewerAgent

    U->>O: 提交审查任务
    O->>CR: 代码质量审查
    CR-->>O: 返回质量报告
    O->>SR: 安全审查
    SR-->>O: 返回安全报告
    O-->>U: 返回综合审查报告
```

### Debug 工作流（调试）

```mermaid
sequenceDiagram
    participant U as 用户
    participant O as Orchestrator
    participant DB as DebuggerAgent
    participant TR as TracerAgent

    U->>O: 提交调试任务
    O->>DB: 定位问题
    DB-->>O: 返回问题定位
    O->>TR: 追踪根因
    TR-->>O: 返回根因分析
    O->>DB: 修复问题
    DB-->>O: 返回修复代码
    O-->>U: 返回修复结果
```

## 数据流图

```mermaid
flowchart TD
    INPUT[用户输入] --> PARSE[任务解析]
    PARSE --> ROUTE{路由决策}
    
    ROUTE -->|简单任务| SINGLE[单 Agent 执行]
    ROUTE -->|复杂任务| WORKFLOW[工作流执行]
    
    SINGLE --> AGENT[Agent 处理]
    WORKFLOW --> SEQ[顺序执行]
    WORKFLOW --> PARALLEL[并行执行]
    WORKFLOW --> CONDITION[条件执行]
    
    AGENT --> MODEL[模型调用]
    SEQ --> MODEL
    PARALLEL --> MODEL
    CONDITION --> MODEL
    
    MODEL --> RESPONSE[响应生成]
    RESPONSE --> SUMMARY[任务总结]
    SUMMARY --> OUTPUT[输出结果]

    style ROUTE fill:#4A90E2,stroke:#fff,color:#fff
    style MODEL fill:#50C878,stroke:#fff,color:#fff
    style SUMMARY fill:#FFD700,stroke:#333
```

## Agent 注册机制

```mermaid
classDiagram
    class BaseModel {
        <<abstract>>
        +provider: ModelProvider
        +tier: ModelTier
        +model_name: str
        +generate(messages, **kwargs) ModelResponse
        +stream(messages, **kwargs) Generator
        +close()
    }

    class BaseAgent {
        <<abstract>>
        +name: str
        +description: str
        +default_tier: str
        +router: ModelRouter
        +execute(context) AgentResult
    }

    class AgentRegistry {
        +_agents: Dict
        +register(name, agent_class)
        +get(name) AgentClass
        +list_all() List
    }

    BaseAgent <|-- ExploreAgent
    BaseAgent <|-- AnalystAgent
    BaseAgent <|-- ArchitectAgent
    BaseAgent <|-- ExecutorAgent
    BaseAgent <|-- VerifierAgent
    
    BaseModel <|-- DeepSeekModel
    BaseModel <|-- KimiModel
    BaseModel <|-- DoubaoModel
    
    AgentRegistry --> BaseAgent: 管理
    BaseAgent --> BaseModel: 使用
```

## 组件依赖关系

```mermaid
graph BT
    subgraph 核心组件
        A[agents/base.py]
        B[core/router.py]
        C[core/orchestrator.py]
    end

    subgraph Agent 实现
        D[agents/explore.py]
        E[agents/analyst.py]
        F[agents/architect.py]
        G[agents/executor.py]
    end

    subgraph 模型适配
        H[models/base.py]
        I[models/deepseek.py]
        J[models/kimi.py]
    end

    subgraph 接口层
        K[cli.py]
        L[web/app.py]
    end

    D --> A
    E --> A
    F --> A
    G --> A
    
    A --> B
    A --> H
    
    I --> H
    J --> H
    
    B --> I
    B --> J
    
    C --> A
    C --> B
    
    K --> C
    L --> C

    style A fill:#4A90E2,stroke:#fff,color:#fff
    style B fill:#50C878,stroke:#fff,color:#fff
    style C fill:#FFD700,stroke:#333
```

## 状态管理

```mermaid
stateDiagram-v2
    [*] --> Pending: 创建任务
    Pending --> Running: 开始执行
    Running --> Step1: 探索项目
    Step1 --> Step2: 分析需求
    Step2 --> Step3: 设计架构
    Step3 --> Step4: 生成代码
    Step4 --> Step5: 验证测试
    Step5 --> Completed: 全部通过
    Step5 --> Failed: 测试失败
    Running --> Failed: 执行出错
    Failed --> Running: 重试
    Completed --> [*]: 返回结果
```

## 安全架构

```mermaid
flowchart TB
    subgraph 安全层["安全层"]
        AUTH[API Key 验证]
        SANDBOX[沙箱执行]
        SCAN[安全扫描]
        DIFF[Diff 预览]
    end

    subgraph 数据层["数据层"]
        ENV[环境变量<br/>本地存储]
        LOCAL[本地执行<br/>不上传]
        LOG[操作日志]
    end

    USER[用户请求] --> AUTH
    AUTH --> SANDBOX
    SANDBOX --> SCAN
    SCAN --> DIFF
    DIFF --> LOCAL
    LOCAL --> LOG
    LOG --> RESULT[返回结果]

    style AUTH fill:#FF6B6B,stroke:#fff,color:#fff
    style SANDBOX fill:#FF6B6B,stroke:#fff,color:#fff
    style SCAN fill:#FF6B6B,stroke:#fff,color:#fff
    style DIFF fill:#FF6B6B,stroke:#fff,color:#fff
```

## 扩展点

1. **新增 Agent**: 继承 `BaseAgent`，实现 `execute()` 方法
2. **新增模型**: 继承 `BaseModel`，实现 `generate()` 和 `stream()` 方法
3. **新增工作流**: 在 `orchestrator.py` 中添加新的工作流模板
4. **新增接口**: 使用 `Orchestrator` API 创建新的前端

---

**版本**: v1.0.0  
**更新日期**: 2026-04-08
