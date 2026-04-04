# oh-my-claudecode 原项目架构分析

> 来源：https://github.com/Yeachan-Heo/oh-my-claudecode
> 分析时间：2026-04-03

---

## 一、核心系统概述

oh-my-claudecode 是一个 **Claude Code 插件**，通过四个互联系统实现多智能体编排：

```
用户输入 → Hooks（事件检测）→ Skills（行为注入）→ Agents（任务执行）→ State（进度追踪）
```

---

## 二、Agent 系统（19 个专业智能体）

### 2.1 四大通道

#### Build/Analysis Lane（构建/分析通道）

| Agent | 默认模型 | 职责 |
|-------|---------|------|
| `explore` | haiku | 代码库发现、文件/符号映射 |
| `analyst` | opus | 需求分析、隐藏约束发现 |
| `planner` | opus | 任务排序、执行计划创建 |
| `architect` | opus | 系统设计、接口定义、权衡分析 |
| `debugger` | sonnet | 根因分析、构建错误解决 |
| `executor` | sonnet | 代码实现、重构 |
| `verifier` | sonnet | 完成验证、测试充分性确认 |
| `tracer` | sonnet | 证据驱动的因果追踪、竞争假设分析 |

#### Review Lane（审查通道）

| Agent | 默认模型 | 职责 |
|-------|---------|------|
| `security-reviewer` | sonnet | 安全漏洞、信任边界、认证/授权审查 |
| `code-reviewer` | opus | 全面代码审查、API契约、向后兼容性 |

#### Domain Lane（领域通道）

| Agent | 默认模型 | 职责 |
|-------|---------|------|
| `test-engineer` | sonnet | 测试策略、覆盖率、flaky-test加固 |
| `designer` | sonnet | UI/UX架构、交互设计 |
| `writer` | haiku | 文档编写、迁移说明 |
| `qa-tester` | sonnet | 通过tmux进行交互式CLI/服务运行时验证 |
| `scientist` | sonnet | 数据分析、统计研究 |
| `git-master` | sonnet | Git操作、提交、rebase、历史管理 |
| `document-specialist` | sonnet | 外部文档、API/SDK参考查找 |
| `code-simplifier` | opus | 代码清晰度、简化、可维护性改进 |

#### Coordination Lane（协调通道）

| Agent | 默认模型 | 职责 |
|-------|---------|------|
| `critic` | opus | 计划和设计的缺口分析、多角度审查 |

### 2.2 模型路由策略

三层模型分级：

| 级别 | 模型 | 特点 | 成本 |
|------|------|------|------|
| LOW | haiku | 快速、便宜 | 低 |
| MEDIUM | sonnet | 性能与成本平衡 | 中 |
| HIGH | opus | 最高质量推理 | 高 |

**默认分配规则：**
- **haiku**：快速查找和简单任务（`explore`, `writer`）
- **sonnet**：代码实现、调试、测试（`executor`, `debugger`, `test-engineer`）
- **opus**：架构、战略分析、审查（`architect`, `planner`, `critic`, `code-reviewer`）

### 2.3 典型 Agent 工作流

```
explore → analyst → planner → critic → executor → verifier
(发现)    (分析)     (排序)     (审查)   (实现)      (确认)
```

---

## 三、Skills 系统（31 个技能）

### 3.1 技能分层

```
┌─────────────────────────────────────────────────────────────┐
│  GUARANTEE LAYER（可选）                                     │
│  ralph: "不验证完成就不停止"                                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  ENHANCEMENT LAYER（0-N个技能）                              │
│  ultrawork（并行）| git-master（提交）| frontend-ui-ux       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  EXECUTION LAYER（主技能）                                   │
│  default（构建）| orchestrate（协调）| planner（计划）        │
└─────────────────────────────────────────────────────────────┘
```

**公式：** `[执行技能] + [0-N增强技能] + [可选保证技能]`

### 3.2 核心工作流技能

| 技能 | 触发词 | 作用 |
|------|--------|------|
| `autopilot` | `autopilot`, `build me`, `I want a` | 全自主5阶段流水线 |
| `ralph` | `ralph`, `don't stop`, `must complete` | 循环直到验证完成 |
| `ultrawork` | `ultrawork`, `ulw` | 最大并行度 |
| `team` | `/team N:agent "task"` | N个Claude agent协调流水线 |
| `ccg` | `ccg`, `claude-codex-gemini` | 三模型编排（Claude+Codex+Gemini）|
| `ralplan` | `ralplan` | 迭代规划直到共识 |

### 3.3 Magic Keywords 完整列表

| 关键词 | 效果 |
|--------|------|
| `ultrawork`, `ulw`, `uw` | 并行agent编排 |
| `autopilot`, `build me`, `I want a`, `handle it all`, `end to end`, `e2e this` | 自主执行流水线 |
| `ralph`, `don't stop`, `must complete`, `until done` | 循环直到验证完成 |
| `ccg`, `claude-codex-gemini` | 三模型编排 |
| `ralplan` | 基于共识的规划 |
| `deep interview`, `ouroboros` | 苏格拉底式深度访谈 |
| `code review`, `review code` | 全面代码审查模式 |
| `security review`, `review security` | 安全审查模式 |
| `deepsearch`, `search the codebase`, `find in codebase` | 代码库搜索模式 |
| `deepanalyze`, `deep-analyze` | 深度分析模式 |
| `ultrathink`, `think hard`, `think deeply` | 深度推理模式 |
| `tdd`, `test first`, `red green` | TDD工作流 |
| `deslop`, `anti-slop` | AI表达清理 |
| `cancelomc`, `stopomc` | 取消活动执行模式 |

---

## 四、Hooks 系统

### 4.1 生命周期事件

| 事件 | 触发时机 | OMC用途 |
|------|---------|---------|
| `UserPromptSubmit` | 用户提交prompt | 魔法关键词检测、技能注入 |
| `SessionStart` | 会话开始 | 初始设置、项目记忆加载 |
| `PreToolUse` | 工具使用前 | 权限验证、并行执行提示 |
| `PermissionRequest` | 权限请求 | Bash命令权限处理 |
| `PostToolUse` | 工具使用后 | 结果验证、项目记忆更新 |
| `PostToolUseFailure` | 工具失败后 | 错误恢复处理 |
| `SubagentStart` | 子agent启动 | Agent追踪 |
| `SubagentStop` | 子agent停止 | Agent追踪、输出验证 |
| `PreCompact` | 上下文压缩前 | 保存关键信息、项目记忆 |
| `Stop` | Claude即将停止 | 持久模式强制、代码简化 |
| `SessionEnd` | 会话结束 | 会话数据清理 |

### 4.2 核心Hooks

| Hook | 事件 | 功能 |
|------|------|------|
| `keyword-detector` | UserPromptSubmit | 检测魔法关键词并激活技能 |
| `persistent-mode` | Stop | 持久模式下阻止停止直到验证完成 |
| `pre-compact` | PreCompact | 压缩前保存关键信息到记事本 |
| `subagent-tracker` | SubagentStart/Stop | 追踪运行中的agent、验证输出 |
| `context-guard-stop` | Stop | 监控上下文使用、接近限制时警告 |
| `code-simplifier` | Stop | 停止时自动简化修改的文件（默认禁用）|

---

## 五、State 状态管理

### 5.1 目录结构

```
.omc/
├── state/                    # 每模式状态文件
│   ├── autopilot-state.json  # autopilot进度
│   ├── ralph-state.json      # ralph循环状态
│   ├── team/                 # team任务状态
│   └── sessions/             # 每会话状态
│       └── {sessionId}/
├── notepad.md                # 抗压缩记事本
├── project-memory.json       # 项目知识存储
├── plans/                    # 执行计划
├── notepads/                 # 每计划知识捕获
│   └── {plan-name}/
│       ├── learnings.md      # 发现的模式
│       ├── decisions.md      # 架构决策
│       ├── issues.md         # 问题和阻塞
│       └── problems.md       # 技术债务
├── autopilot/                # autopilot产物
│   └── spec.md
├── research/                 # 研究结果
└── logs/                     # 执行日志
```

### 5.2 MCP工具

**记事本工具：**
- `notepad_read` - 读取记事本内容
- `notepad_write_priority` - 写入高优先级备忘（永久保留）
- `notepad_write_working` - 写入工作备忘
- `notepad_write_manual` - 写入手动备忘
- `notepad_prune` - 清理旧备忘
- `notepad_stats` - 查看记事本统计

**项目记忆工具：**
- `project_memory_read` - 读取项目记忆
- `project_memory_write` - 覆盖项目记忆
- `project_memory_add_note` - 添加笔记
- `project_memory_add_directive` - 添加指令

---

## 六、验证协议

验证模块确保工作完成并有证据：

**标准检查：**
- BUILD: 编译通过
- TEST: 所有测试通过
- LINT: 无lint错误
- FUNCTIONALITY: 功能按预期工作
- ARCHITECT: Opus级别审查批准
- TODO: 所有任务完成
- ERROR_FREE: 无未解决错误

证据必须在5分钟内，包含实际命令输出。

---

## 七、关键技术发现（与TASK.md的差异）

### 7.1 实际数据

| 项目 | TASK.md描述 | 实际情况 |
|------|------------|---------|
| Agent数量 | 32个 | **19个**（带tier变体）|
| 执行模式 | 7种 | **8种**（Team/omc team/ccg/Autopilot/Ultrawork/Ralph/Pipeline/Ultrapilot）|
| 技能数量 | 未提及 | **31个**（28个用户可调用 + 3个内部）|
| 模型路由 | DeepSeek/文心/通义/GLM | **Claude三层**（haiku/sonnet/opus）|

### 7.2 核心改造要点

1. **模型层替换**
   - 原：Claude haiku/sonnet/opus三层
   - 新：DeepSeek + 国内模型（需设计新的路由策略）

2. **技术栈转换**
   - 原：TypeScript + Node.js + Claude Code插件机制
   - 新：Python + FastAPI（需重新设计插件/扩展机制）

3. **Hooks机制**
   - 原：依赖Claude Code生命周期事件
   - 新：需要自己实现事件系统或适配其他IDE

4. **状态管理**
   - 可保留：目录结构、MCP工具概念
   - 需适配：Python实现

---

## 八、下一步行动

1. ✅ 深度阅读原项目架构（已完成）
2. ⏳ 设计Python版本架构
3. ⏳ 实现模型适配层
4. ⏳ 实现核心Agent
5. ⏳ 实现编排引擎

---

**文档保存时间：** 2026-04-03 19:40
