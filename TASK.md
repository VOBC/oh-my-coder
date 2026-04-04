# 代可行 - 开发任务文档

**项目**: Oh My Coder (OMC 中文版)  
**路径**: ~/.qclaw/workspace-agent-bf627e2b/projects/oh-my-coder/  
**时间**: 2 周  
**预算**: 4000万 Token/天（DeepSeek 免费）

---

## 📋 任务概述

重写 GitHub 项目 [oh-my-claudecode](https://github.com/Yeachan-Heo/oh-my-claudecode)，将其从 TypeScript + Claude Code 生态，改造为 Python + 国内多模型支持。

**原项目特点：**
- 17.8k stars，韩国开发者
- 32 个专业智能体（架构师、UI设计师、安全专家等）
- 7 种执行模式
- 智能模型路由（节省 30-50% token）

**目标：** 国内开发者还没注意到这个项目，我们要抢先本土化！

---

## 🎯 第一阶段（本周）目标

### Day 1-2: 代码分析
- [ ] Fork 原项目到本地
- [ ] 深度阅读 TypeScript 代码
- [ ] 理解 32 个 Agent 的分工逻辑
- [ ] 理解 7 种执行模式的实现
- [ ] 输出技术架构文档

### Day 3-4: 架构设计
- [ ] 设计 Python 版本架构
- [ ] 模型适配层设计（支持 DeepSeek/文心/通义/GLM）
- [ ] Agent 编排引擎设计
- [ ] 输出详细设计文档

### Day 5-7: 核心实现
- [ ] 搭建 FastAPI 骨架
- [ ] 实现模型适配层（至少 DeepSeek）
- [ ] 实现 3-5 个核心 Agent
- [ ] 实现基础编排引擎

---

## 🏗️ 技术架构

```
oh-my-coder/
├── src/
│   ├── core/              # 核心编排引擎
│   │   ├── orchestrator.py    # 智能体调度器
│   │   ├── router.py          # 模型路由（节省token关键）
│   │   └── executor.py        # 执行引擎
│   ├── agents/            # 32个专业智能体
│   │   ├── architect.py       # 架构师
│   │   ├── designer.py        # UI设计师
│   │   ├── security.py        # 安全专家
│   │   ├── reviewer.py        # 代码审查
│   │   ├── tester.py          # 测试工程师
│   │   └── ...                # 其他27个
│   ├── models/            # 模型适配层
│   │   ├── base.py            # 基类
│   │   ├── deepseek.py        # DeepSeek（优先）
│   │   ├── wenxin.py          # 文心一言
│   │   ├── tongyi.py          # 通义千问
│   │   └── glm.py             # ChatGLM
│   ├── skills/            # 40+专业技能
│   └── utils/             # 工具函数
├── config/                # 配置文件
├── tests/                 # 测试
└── docs/                  # 文档
```

---

## 🔧 技术栈

- **语言**: Python 3.10+
- **框架**: FastAPI
- **模型**: DeepSeek（主力）、文心、通义、GLM
- **工具**: 
  - `httpx` - HTTP 客户端
  - `pydantic` - 数据验证
  - `rich` - 终端美化
  - `typer` - CLI 框架

---

## 💡 核心改造点

### 1. 模型层替换（最关键）

**原项目:**
```typescript
// 依赖 Claude Code API
const response = await claude.sendMessage(prompt);
```

**新项目:**
```python
# 支持多模型，智能路由
router = ModelRouter()
model = router.select(task_type, complexity, budget)
response = await model.generate(prompt)
```

**路由策略:**
- 简单任务 → DeepSeek（便宜）
- 复杂推理 → GPT-4/Claude（贵但强）
- 中文场景 → 文心/通义（本土优势）

### 2. 智能体 Prompt 中文化

保留原逻辑，全部改为中文：
- 架构师 Agent → 输出中文架构设计
- 审查 Agent → 用中文写代码审查意见
- 安全 Agent → 中文安全报告

### 3. 执行模式本土化

保留 7 种模式，适配国内场景：
1. `autopilot` - 全自动模式
2. `pair` - 结对编程
3. `review` - 代码审查
4. `debug` - 调试模式
5. `refactor` - 重构模式
6. `test` - 测试生成
7. `doc` - 文档生成

---

## 🚀 快速开始

```bash
# 进入项目目录
cd ~/.qclaw/workspace-agent-bf627e2b/projects/oh-my-coder/

# 启动开发环境
./start-dev.sh

# 或者手动
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m uvicorn src.main:app --reload
```

---

## 📝 开发规范

### 代码风格
- 遵循 PEP 8
- 类型注解必须（Python 3.10+）
- 函数文档字符串

### 提交规范
```
feat: 添加架构师 Agent
fix: 修复模型路由bug
docs: 更新API文档
refactor: 重构执行引擎
```

### 测试要求
- 核心函数必须有单元测试
- 集成测试覆盖主要流程

---

## 💰 成本控制

**Token 预算:** 4000万/天（DeepSeek 免费额度）

**使用策略:**
- 日常开发 → DeepSeek（免费）
- 复杂架构设计 → 少量 Claude/GPT-4（付费）
- 代码审查 → DeepSeek（免费）

**预计成本:** ¥0-100（几乎为零）

---

## ⏰ 里程碑

| 日期 | 目标 | 验收标准 |
|------|------|---------|
| Day 2 | 架构文档 | 技术方案文档完成 |
| Day 5 | MVP | 3个Agent + 基础编排 |
| Day 10 | Beta | 10个Agent + 完整路由 |
| Day 14 | Release | 32个Agent + 7种模式 |

---

## 🤝 协作方式

- **你（代可行）**: 全权负责技术实现
- **小麦（我）**: 协助调研、记录、协调
- **Michael**: 产品决策、验收成果

**沟通方式:**
- 每 3 天汇报一次进度
- 有问题随时问
- 不要憋着自己扛

---

## 🎯 成功标准

1. **功能完整**: 32个Agent + 7种模式全部实现
2. **模型支持**: 至少支持 DeepSeek + 1个国内模型
3. **中文优先**: 所有交互都是中文
4. **成本优势**: 比原项目节省 30%+ token
5. **易用性**: 一行命令安装，5分钟上手

---

## 📚 参考资料

- 原项目: https://github.com/Yeachan-Heo/oh-my-claudecode
- 架构文档: ./docs/ARCHITECTURE.md
- DeepSeek API: https://platform.deepseek.com/

---

**不要废话，直接开始干活。**

有问题就问，有进展就汇报。

Let's build this! 🚀
