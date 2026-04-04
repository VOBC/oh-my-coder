# 架构设计文档

## 模块划分

```
oh-my-coder/
├── src/
│   ├── core/           # 核心编排引擎
│   │   ├── orchestrator.py   # 智能体调度器
│   │   ├── router.py         # 模型路由
│   │   └── executor.py       # 执行引擎
│   ├── agents/         # 32个专业智能体
│   │   ├── architect.py      # 架构师
│   │   ├── designer.py       # UI设计师
│   │   ├── security.py       # 安全专家
│   │   └── ...               # 其他29个
│   ├── models/         # 模型适配层
│   │   ├── base.py           # 基类
│   │   ├── deepseek.py       # DeepSeek
│   │   ├── wenxin.py         # 文心一言
│   │   ├── tongyi.py         # 通义千问
│   │   └── glm.py            # ChatGLM
│   ├── skills/         # 40+专业技能
│   └── utils/          # 工具函数
├── config/             # 配置文件
├── tests/              # 测试
└── docs/               # 文档
```

## 数据流

1. 用户输入 → Orchestrator
2. Orchestrator 分析任务 → 选择 Agent
3. Agent 调用 Router → 选择最优模型
4. 模型返回 → Agent 处理 → 输出结果
5. 循环直到任务完成

## 核心改造点

### 1. 模型层替换
- 原: 依赖 Claude Code API
- 新: 支持多模型，可配置优先级

### 2. 智能体 Prompt 中文化
- 保留原逻辑，全部改为中文
- 适配国内开发场景

### 3. 执行模式本土化
- 保留 7 种模式
- 增加国内 IDE/编辑器支持
