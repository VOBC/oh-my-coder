# oh-my-coder

> ⚠️ **注意**: 此文档由 oh-my-coder 自动生成，请勿手动编辑。
> 生成时间: <!-- GENERATED_AT -->

---

## 目录

- [项目概述](#项目概述)
- [项目结构](#项目结构)
- [模块详解](#模块详解)
- [API 参考](#api-参考)

---

## 项目概述

待办事项 CLI 应用
支持添加、查看、完成、删除任务，数据存储在 JSON 文件中

| 指标 | 数值 |
|------|------|
| 总文件数 | 65 |
| 总类数 | 173 |
| 总函数数 | 70 |

### 核心依赖

```python
import django.db
import django.contrib.auth.models
import django.urls
import asyncio
import sys
import uuid
import typer
import typing
import pathlib
```

## 项目结构

```
oh-my-coder/
├── ├── demo.py
├── └── todo_demo.py
├── examples/
│   ├── advanced_demo.py
│   ├── advanced_usage.py
│   ├── basic_usage.py
│   ├── cli_demo.py
│   ├── example_cli.py
│   ├── example_django.py
│   ├── example_fastapi.py
│   └── web_demo.py
├── src/
│   ├── cli.py
│   └── main.py
│   ├── agents/
│   │   ├── analyst.py
│   │   ├── architect.py
│   │   ├── base.py
│   │   ├── code_reviewer.py
│   │   ├── code_simplifier.py
│   │   ├── critic.py
│   │   ├── debugger.py
│   │   ├── designer.py
│   │   ├── executor.py
│   │   ├── explore.py
│   │   ├── git_master.py
│   │   ├── planner.py
│   │   ├── qa_tester.py
│   │   ├── scientist.py
│   │   ├── security.py
│   │   ├── tracer.py
│   │   ├── verifier.py
│   │   └── writer.py
│   ├── api/
│   │   └── openapi.py
│   ├── core/
│   │   ├── history.py
│   │   ├── orchestrator.py
│   │   ├── router.py
│   │   └── summary.py
│   ├── models/
│   │   ├── baichuan.py
│   │   ├── base.py
│   │   ├── deepseek.py
│   │   ├── doubao.py
│   │   ├── glm.py
│   │   ├── hunyuan.py
│   │   ├── kimi.py
│   │   ├── minimax.py
│   │   ├── spark.py
│   │   ├── tiangong.py
│   │   ├── tongyi.py
│   │   └── wenxin.py
│   ├── quest/
│   │   ├── executor.py
│   │   ├── manager.py
│   │   ├── models.py
│   │   ├── spec_generator.py
│   │   └── store.py
│   ├── rag/
│   │   ├── indexer.py
│   │   └── search.py
│   ├── team/
│   │   ├── auth.py
│   │   ├── notification.py
│   │   ├── statistics.py
│   │   └── task_sync.py
│   ├── utils/
│   │   └── performance.py
│   ├── web/
│   │   ├── app.py
│   │   ├── dashboard_api.py
│   │   ├── history_api.py
│   │   └── team_api.py
│   ├── wiki/
│   │   ├── generator.py
│   │   └── parser.py
```

### 目录说明

| 目录 | 说明 |
|------|------|
| src/ | 源代码目录 |
| tests/ | 测试文件 |
| docs/ | 文档 |

## 模块详解

### `demo.py`

Oh My Coder - 多智能体协作演示脚本

本脚本演示如何使用 Oh My Coder 的多智能体系统：
1. explore Agent - 探索代码库结构
2. analyst Agent - 分析需求
3. executor Agent - 生成代码

运行方式：
    cd ~/.qclaw/workspace-agent-bf627e2b/projects/oh-my-coder
    python demo.py

#### 函数

##### `init_oh_my_coder()`

初始化 Oh My Coder

##### `save_code(code, project_path)`

保存生成的代码到文件

### `examples/advanced_demo.py`

高级示例 - 展示 Oh My Coder 的进阶用法

覆盖：
1. 多模型动态切换
2. Agent 协作与并行执行
3. 复杂任务处理
4. 任务总结生成

运行方式：
    python examples/advanced_demo.py

前置条件：
    export DEEPSEEK_API_KEY=your_key_here

#### 函数

##### `demo_multi_model_routing()`

演示如何在运行时动态切换不同模型

##### `demo_complex_task()`

演示如何处理需要多轮交互的复杂任务

##### `demo_summary_feature()`

演示任务总结功能的使用

##### `demo_custom_workflow()`

演示如何定义和使用自定义工作流

### `examples/advanced_usage.py`

高级示例：多 Agent 协作和多模型使用

演示：
1. 多 Agent 协作
2. 多模型配置
3. 工作流编排
4. 任务总结

### `examples/basic_usage.py`

基础示例：使用 Oh My Coder 完成简单任务

演示：
1. CLI 基本用法
2. Web API 调用
3. 工作流选择

#### 函数

##### `example_cli_basic()`

示例 1: CLI 基本用法

##### `example_cli_tasks()`

示例 2: CLI 任务执行

##### `example_curl()`

示例 5: curl 命令调用

### `examples/cli_demo.py`

CLI 使用示例

展示如何使用 Oh My Coder 的命令行界面。

运行方式：
    python examples/cli_demo.py

#### 函数

##### `run(cmd, desc)`

执行命令并打印输出

##### `main()`

### `examples/example_cli.py`

CLI 工具示例

演示如何使用 Oh My Coder 开发命令行工具。

场景：实现一个项目管理 CLI 工具

#### 类

##### `Priority`

任务优先级

**继承**: str, Enum

##### `Status`

任务状态

**继承**: str, Enum

##### `Project`

项目模型

##### `Task`

任务模型

##### `Database`

SQLite 数据库操作

| 方法 | 说明 |
|------|------|
| `create_project(self, name, description)` | 创建项目 |
| `get_project(self, project_id)` | 获取项目 |
| `get_all_projects(self)` | 获取所有项目 |
| `set_current_project(self, project_id)` | 设置当前项目 |
| `get_current_project(self)` | 获取当前项目ID |
| `create_task(self, project_id, name, priority, due_date)` | 创建任务 |
| `get_task(self, task_id)` | 获取任务 |
| `get_tasks(self, project_id, status)` | 获取项目任务 |
| `update_task_status(self, task_id, status)` | 更新任务状态 |
| `delete_task(self, task_id)` | 删除任务 |
| `get_task_count(self, project_id)` | 获取任务数量 |
| `get_task_stats(self, project_id)` | 获取任务统计 |

#### 函数

##### `create_project(name, description)`

创建新项目

##### `list_projects()`

列出所有项目

##### `add_task(name, priority, due_date)`

添加新任务

##### `list_tasks(status, all_status)`

列出任务

##### `start_task(task_id)`

开始任务

##### `complete_task(task_id)`

完成任务

##### `delete_task(task_id, force)`

删除任务

##### `generate_report(weekly, monthly, output)`

生成统计报告

##### `main(version)`

📋 项目管理 CLI 工具

### `examples/example_django.py`

Django 项目示例

演示如何使用 Oh My Coder 开发 Django 项目。

场景：为博客系统实现文章管理功能

#### 类

##### `Category`

文章分类

**继承**: models.Model

| 方法 | 说明 |
|------|------|
| `save(self)` |  |

##### `Tag`

文章标签

**继承**: models.Model

| 方法 | 说明 |
|------|------|
| `save(self)` |  |

##### `Article`

文章模型

**继承**: models.Model

| 方法 | 说明 |
|------|------|
| `save(self)` |  |
| `get_absolute_url(self)` |  |

##### `Comment`

评论模型

**继承**: models.Model

##### `ArticleListView`

文章列表视图

**继承**: ListView

| 方法 | 说明 |
|------|------|
| `get_queryset(self)` |  |
| `get_context_data(self)` |  |

##### `ArticleDetailView`

文章详情视图

**继承**: DetailView

| 方法 | 说明 |
|------|------|
| `get_object(self, queryset)` |  |
| `get_context_data(self)` |  |

##### `ArticleCreateView`

创建文章视图

**继承**: LoginRequiredMixin, CreateView

| 方法 | 说明 |
|------|------|
| `form_valid(self, form)` |  |

##### `ArticleUpdateView`

更新文章视图

**继承**: LoginRequiredMixin, UserPassesTestMixin, UpdateView

| 方法 | 说明 |
|------|------|
| `test_func(self)` |  |
| `form_valid(self, form)` |  |

##### `ArticleDeleteView`

删除文章视图

**继承**: LoginRequiredMixin, UserPassesTestMixin, DeleteView

| 方法 | 说明 |
|------|------|
| `test_func(self)` |  |
| `delete(self, request)` |  |

##### `ArticleViewSet`

文章 API 视图集

**继承**: viewsets.ModelViewSet

| 方法 | 说明 |
|------|------|
| `get_serializer_class(self)` |  |
| `perform_create(self, serializer)` |  |
| `like(self, request, pk)` | 点赞文章 |
| `featured(self, request)` | 获取推荐文章 |

### `examples/example_fastapi.py`

FastAPI 项目示例

演示如何使用 Oh My Coder 开发 FastAPI 项目。

场景：为电商系统实现商品管理 API

#### 类

##### `Product`

商品模型

**继承**: Base

##### `ProductBase`

商品基础 Schema

**继承**: BaseModel

##### `ProductCreate`

创建商品 Schema

**继承**: ProductBase

##### `ProductUpdate`

更新商品 Schema

**继承**: BaseModel

##### `ProductResponse`

商品响应 Schema

**继承**: ProductBase

### `examples/web_demo.py`

Web 界面使用示例

展示如何使用 Web 界面的 API 端点。

运行方式：
    python examples/web_demo.py

#### 函数

##### `pretty_json(data)`

格式化打印 JSON

### `src/agents/analyst.py`

Analyst Agent - 需求分析智能体

职责：
1. 深度理解用户需求
2. 发现隐藏约束和边界情况
3. 澄清模糊需求
4. 生成结构化需求文档

模型层级：HIGH（深度推理，对应 opus）

工作流程：
1. 分析用户输入
2. 识别关键需求点
3. 发现潜在问题
4. 提出澄清问题
5. 生成需求文档

#### 类

##### `Requirement`

需求项

##### `AnalysisResult`

分析结果

##### `AnalystAgent`

需求分析 Agent

**继承**: BaseAgent

| 方法 | 说明 |
|------|------|
| `system_prompt(self)` |  |

### `src/agents/architect.py`

Architect Agent - 系统架构设计智能体

职责：
1. 系统架构设计
2. 技术选型和权衡分析
3. 接口定义
4. 架构决策记录（ADR）

模型层级：HIGH（深度推理，对应 opus）

工作流程：
1. 分析需求和约束
2. 设计整体架构
3. 技术选型
4. 定义接口和数据流
5. 输出架构文档

#### 类

##### `ArchitectureDecision`

架构决策

##### `ArchitectAgent`

架构师 Agent

**继承**: BaseAgent

| 方法 | 说明 |
|------|------|
| `system_prompt(self)` |  |

### `src/agents/base.py`

Agent 基类 - 所有智能体的基类

设计原则：
1. 每个 Agent 职责单一、明确
2. 通过 Prompt 定义角色和行为
3. 自动记录工作过程和产出
4. 支持与其他 Agent 协作

Agent 生命周期：
1. 初始化（加载配置和 Prompt）
2. 接收任务
3. 执行（调用模型、使用工具）
4. 输出结果

#### 类

##### `AgentStatus`

Agent 状态

**继承**: Enum

##### `AgentLane`

Agent 通道 - 对应原项目的四大通道

**继承**: Enum

##### `AgentContext`

Agent 执行上下文

##### `AgentOutput`

Agent 输出

##### `BaseAgent`

Agent 基类

**继承**: ABC

| 方法 | 说明 |
|------|------|
| `system_prompt(self)` | 返回系统提示词（定义 Agent 的角色和行为） |
| `get_context_prompt(self, context)` | 根据上下文生成额外提示词 |
| `get_last_output(self)` | 获取最后一次输出 |
| `get_output_history(self)` | 获取输出历史 |
| `save_output(self, output_path)` | 保存输出到文件 |

#### 函数

##### `register_agent(agent_class)`

注册 Agent

##### `get_agent(name)`

获取已注册的 Agent

##### `list_agents()`

列出所有已注册的 Agent

### `src/agents/code_reviewer.py`

Code Reviewer Agent - 代码审查智能体

职责：
1. 全面代码审查
2. API 契约检查
3. 向后兼容性验证
4. 代码质量评估

模型层级：HIGH（深度推理，对应 opus）

#### 类

##### `CodeReviewerAgent`

代码审查 Agent - 全面的代码质量检查

**继承**: BaseAgent

| 方法 | 说明 |
|------|------|
| `system_prompt(self)` |  |

### `src/agents/code_simplifier.py`

Code Simplifier Agent - 代码简化智能体

职责：
1. 代码清晰度改进
2. 复杂度降低
3. 可维护性提升
4. 死代码清理

模型层级：HIGH（深度推理，对应 opus）

#### 类

##### `CodeSimplifierAgent`

代码简化 Agent - 提高代码质量和可读性

**继承**: BaseAgent

| 方法 | 说明 |
|------|------|
| `system_prompt(self)` |  |

### `src/agents/critic.py`

Critic Agent - 批评家智能体

职责：
1. 计划和设计的缺口分析
2. 多角度审查
3. 发现潜在问题
4. 提出改进建议

模型层级：HIGH（深度推理，对应 opus）

#### 类

##### `CriticAgent`

批评家 Agent - 多角度审查和缺口分析

**继承**: BaseAgent

| 方法 | 说明 |
|------|------|
| `system_prompt(self)` |  |

### `src/agents/debugger.py`

Debugger Agent - 调试智能体

职责：
1. 根因分析
2. 构建错误解决
3. 运行时错误修复
4. 日志分析

模型层级：MEDIUM（平衡，对应 sonnet）

#### 类

##### `DebuggerAgent`

调试 Agent - 定位和修复 Bug

**继承**: BaseAgent

| 方法 | 说明 |
|------|------|
| `system_prompt(self)` |  |

### `src/agents/designer.py`

Designer Agent - UI/UX 设计智能体

职责：
1. UI/UX 架构设计
2. 交互设计
3. 组件设计
4. 设计系统

模型层级：MEDIUM（平衡，对应 sonnet）

#### 类

##### `DesignerAgent`

UI/UX 设计 Agent - 界面和交互设计

**继承**: BaseAgent

| 方法 | 说明 |
|------|------|
| `system_prompt(self)` |  |

### `src/agents/executor.py`

Executor Agent - 代码实现智能体

职责：
1. 代码实现 - 根据设计编写代码
2. 重构 - 改善代码结构
3. Bug 修复 - 定位和修复问题
4. 代码优化 - 性能、可读性、安全性

模型层级：MEDIUM（平衡性能和成本）

工作流程：
1. 理解任务需求
2. 参考架构设计（如有）
3. 分析现有代码（如有相关文件）
4. 实现功能代码
5. 提取并保存代码文件
6. 编写单元测试

#### 类

##### `ExecutorAgent`

执行者 Agent - 核心代码实现智能体

**继承**: BaseAgent

| 方法 | 说明 |
|------|------|
| `system_prompt(self)` |  |

### `src/agents/explore.py`

Explore Agent - 代码库探索智能体

职责：
1. 快速扫描代码库，构建文件/符号映射
2. 识别项目结构、技术栈
3. 发现关键文件和依赖关系
4. 为后续 Agent 提供上下文

模型层级：LOW（快速便宜，对应 haiku）

工作流程：
1. 扫描目录结构
2. 识别文件类型和分布
3. 提取关键符号（函数、类、模块）
4. 生成项目地图

#### 类

##### `FileInfo`

文件信息

##### `ProjectMap`

项目地图

##### `ExploreAgent`

代码库探索 Agent

**继承**: BaseAgent

| 方法 | 说明 |
|------|------|
| `system_prompt(self)` |  |

### `src/agents/git_master.py`

Git Master Agent - Git 操作智能体

职责：
1. Git 操作执行
2. 提交管理
3. 分支管理
4. 历史管理

模型层级：MEDIUM（平衡，对应 sonnet）

#### 类

##### `GitMasterAgent`

Git 操作 Agent - 版本控制管理

**继承**: BaseAgent

| 方法 | 说明 |
|------|------|
| `system_prompt(self)` |  |

### `src/agents/planner.py`

Planner Agent - 任务规划智能体（增强版）

增强功能：
1. 结构化任务分解 - 使用 Pydantic 模型
2. COT 推理链 - 多步推理能力
3. 依赖图分析 - 自动拓扑排序
4. 自适应调整 - 根据执行反馈优化计划
5. 上下文理解 - 利用项目探索结果

参考：
- Windsurf Cascade 的深度推理
- LangGraph 的状态机编排

#### 类

##### `TaskPriority`

任务优先级

**继承**: str, Enum

##### `TaskStatus`

任务状态

**继承**: str, Enum

##### `TaskComplexity`

任务复杂度

**继承**: str, Enum

##### `SubTask`

子任务

**继承**: BaseModel

##### `TaskPhase`

任务阶段

**继承**: BaseModel

##### `ExecutionPlan`

执行计划

**继承**: BaseModel

##### `ReasoningStep`

推理步骤

##### `ChainOfThought`

思维链推理

| 方法 | 说明 |
|------|------|
| `add_step(self, thought, action, observation, conclusion)` | 添加推理步骤 |
| `to_prompt(self)` | 转换为 Prompt 格式 |

##### `DependencyGraph`

依赖图

| 方法 | 说明 |
|------|------|
| `add_task(self, task_id, dependencies)` | 添加任务节点 |
| `topological_sort(self)` | 拓扑排序，返回 (排序结果, 是否有环) |
| `find_critical_path(self)` | 找到关键路径（最长路径） |
| `get_ready_tasks(self, completed)` | 获取就绪任务（依赖已满足） |

##### `PlannerAgent`

规划 Agent - 任务分解和执行计划（增强版）

**继承**: BaseAgent

| 方法 | 说明 |
|------|------|
| `system_prompt(self)` |  |
| `adjust_plan(self, plan, completed_tasks, failed_tasks, new_requirements)` | 自适应调整计划 |

### `src/agents/qa_tester.py`

QA Tester Agent - QA 测试智能体

职责：
1. 交互式 CLI 测试
2. 服务运行时验证
3. 端到端测试
4. 回归测试

模型层级：MEDIUM（平衡，对应 sonnet）

#### 类

##### `QATesterAgent`

QA 测试 Agent - 交互式测试和端到端验证

**继承**: BaseAgent

| 方法 | 说明 |
|------|------|
| `system_prompt(self)` |  |

### `src/agents/scientist.py`

Scientist Agent - 数据分析智能体

职责：
1. 数据分析
2. 统计研究
3. 数据可视化建议
4. 洞察发现

模型层级：MEDIUM（平衡，对应 sonnet）

#### 类

##### `ScientistAgent`

数据分析 Agent - 统计分析和洞察发现

**继承**: BaseAgent

| 方法 | 说明 |
|------|------|
| `system_prompt(self)` |  |

### `src/agents/security.py`

Security Reviewer Agent - 安全审查智能体

职责：
1. 安全漏洞检测
2. 信任边界分析
3. 认证/授权审查
4. 安全最佳实践

模型层级：HIGH（深度推理，对应 opus）

#### 类

##### `SecurityReviewerAgent`

安全审查 Agent - 安全漏洞和风险检测

**继承**: BaseAgent

| 方法 | 说明 |
|------|------|
| `system_prompt(self)` |  |

### `src/agents/tracer.py`

Tracer Agent - 因果追踪智能体

职责：
1. 证据驱动的因果追踪
2. 竞争假设分析
3. 问题根因定位
4. 调用链分析

模型层级：MEDIUM（平衡，对应 sonnet）

#### 类

##### `Hypothesis`

假设

##### `TracerAgent`

追踪 Agent - 因果分析和根因定位

**继承**: BaseAgent

| 方法 | 说明 |
|------|------|
| `system_prompt(self)` |  |

### `src/agents/verifier.py`

Verifier Agent - 验证智能体

职责：
1. 验证代码功能正确性
2. 检查测试覆盖率
3. 运行测试套件
4. 确认任务完成

模型层级：MEDIUM（平衡，对应 sonnet）

#### 类

##### `VerifierAgent`

验证 Agent - 确保代码质量和功能正确

**继承**: BaseAgent

| 方法 | 说明 |
|------|------|
| `system_prompt(self)` |  |

### `src/agents/writer.py`

Writer Agent - 文档编写智能体

职责：
1. 技术文档编写
2. API 文档生成
3. README 编写
4. 迁移文档

模型层级：LOW（快速，对应 haiku）

#### 类

##### `WriterAgent`

文档编写 Agent - 技术文档和 API 文档

**继承**: BaseAgent

| 方法 | 说明 |
|------|------|
| `system_prompt(self)` |  |

### `src/api/openapi.py`

OpenAPI 规范

提供标准的 API 文档和 Swagger UI。

#### 函数

##### `custom_openapi(app)`

自定义 OpenAPI 规范

### `src/cli.py`

Oh My Coder CLI - 命令行入口

使用 typer 构建友好的 CLI 界面。

主要命令：
- omc run <task>         # 执行任务
- omc explore            # 探索代码库
- omc wiki               # 生成项目 Wiki
- omc agents             # 列出所有 Agent
- omc status             # 查看状态
- omc --version          # 显示版本
- omc --help             # 帮助信息

#### 函数

##### `main(ctx, version)`

Oh My Coder - 多智能体 AI 编程助手

##### `_print_version()`

打印版本信息

##### `run(task, project_path, model, workflow)`

执行编程任务

##### `explore(project_path)`

探索代码库

##### `wiki(project_path, output)`

生成项目 Wiki 文档

##### `_detect_project_name(project_path)`

检测项目名称

##### `quest(ctx, description, project_path, title, skip_spec, auto_confirm)`

🧙 Quest Mode - 异步自主编程

##### `quest_list(project_path, status_filter, all_quests)`

📋 查看 Quest 列表

##### `quest_status(quest_id, project_path)`

📊 查看 Quest 详细状态

##### `quest_exec(quest_id, project_path)`

▶️ 执行已就绪的 Quest

##### `quest_cancel(quest_id, project_path)`

⏹️ 取消 Quest

##### `agents()`

列出所有可用 Agent

##### `status()`

查看系统状态

##### `_init_router()`

初始化模型路由器，失败时给出友好提示

##### `_print_missing_key_hint(key, reason)`

打印缺失 API Key 的友好提示

##### `_print_fatal(msg, hint)`

打印致命错误并退出

##### `_check_env()`

检查环境是否就绪，返回 True 表示就绪

##### `_display_result(result)`

显示工作流结果

##### `_status_color(status)`

给状态上色

### `src/core/history.py`

任务历史和回放模块

功能：
1. TaskHistory - 任务历史记录
2. TaskReplay - 任务回放功能
3. TaskCheckpoint - 任务检查点
4. 支持从任意点恢复执行

#### 类

##### `ReplayStatus`

回放状态

**继承**: str, Enum

##### `StepStatus`

步骤状态

**继承**: str, Enum

##### `StepExecution`

步骤执行记录

| 方法 | 说明 |
|------|------|
| `to_dict(self)` | 转换为字典 |
| `from_dict(cls, data)` | 从字典创建 |

##### `TaskHistory`

任务历史记录

| 方法 | 说明 |
|------|------|
| `add_step(self, step)` | 添加步骤 |
| `update_totals(self)` | 更新总计 |
| `to_dict(self)` | 转换为字典 |
| `from_dict(cls, data)` | 从字典创建 |
| `get_step(self, step_id)` | 获取步骤 |
| `get_steps_by_agent(self, agent_name)` | 按 Agent 获取步骤 |
| `get_failed_steps(self)` | 获取失败步骤 |

##### `TaskCheckpoint`

任务检查点

| 方法 | 说明 |
|------|------|
| `can_resume_from(self, step_id)` | 检查是否可以从指定步骤恢复 |
| `get_resume_context(self)` | 获取恢复上下文 |
| `to_dict(self)` | 转换为字典 |

##### `TaskReplay`

任务回放器

| 方法 | 说明 |
|------|------|
| `on_step_start(self, callback)` | 注册步骤开始回调 |
| `on_step_complete(self, callback)` | 注册步骤完成回调 |
| `on_replay_complete(self, callback)` | 注册回放完成回调 |
| `pause(self)` | 暂停回放 |
| `resume(self)` | 恢复回放 |
| `stop(self)` | 停止回放 |
| `set_speed(self, speed)` | 设置回放速度 |
| `get_progress(self)` | 获取进度 |

##### `HistoryManager`

历史记录管理器

| 方法 | 说明 |
|------|------|
| `create_history(self, task_description, workflow_name, tags)` | 创建新的历史记录 |
| `save_history(self, history)` | 保存历史记录 |
| `load_history(self, history_id)` | 加载历史记录 |
| `list_histories(self, limit, tags)` | 列出历史记录 |
| `create_checkpoint(self, history, step_index)` | 创建检查点 |
| `load_checkpoint(self, checkpoint_id)` | 加载检查点 |
| `delete_history(self, history_id)` | 删除历史记录 |
| `get_stats(self)` | 获取统计信息 |

#### 函数

##### `create_step_execution(agent_name, description, input_context)`

创建步骤执行记录

##### `complete_step_execution(step, output, tokens_used, cost)`

完成步骤执行

##### `fail_step_execution(step, error)`

标记步骤失败

### `src/core/orchestrator.py`

Agent 编排器 - 智能体调度和编排引擎

核心功能：
1. Agent 工作流编排
2. 任务分解和分配
3. 状态追踪和持久化
4. 并行执行支持

设计思路：
原项目通过 Skills 系统编排多个 Agent 协作。
我们实现一个轻量级的编排引擎，支持：
- 顺序执行：explore → analyst → planner → executor
- 并行执行：多个 Agent 同时工作
- 条件执行：根据前序结果决定后续步骤

#### 类

##### `WorkflowStatus`

工作流状态

**继承**: Enum

##### `ExecutionMode`

执行模式

**继承**: Enum

##### `WorkflowStep`

工作流步骤

##### `WorkflowResult`

工作流执行结果

##### `Orchestrator`

Agent 编排器

| 方法 | 说明 |
|------|------|
| `register_agent(self, agent)` | 注册 Agent 实例 |
| `get_agent(self, name)` | 获取 Agent 实例 |
| `load_workflow_result(self, workflow_id)` | 加载工作流结果 |
| `list_active_workflows(self)` | 列出活跃的工作流 |
| `get_workflow_status(self, workflow_id)` | 获取工作流状态 |

### `src/core/router.py`

模型路由器 - 智能选择最优模型

核心功能：
1. 根据任务类型选择合适的模型层级
2. 根据成本预算选择提供商
3. 支持故障转移（fallback）
4. 记录路由决策用于优化
5. 响应缓存（避免重复请求）
6. 增强日志和错误处理

设计思路：
原项目使用 haiku/sonnet/opus 三层模型路由，节省 30-50% token。
我们扩展为多提供商路由，优先使用 DeepSeek（免费），必要时才调用付费模型。

#### 类

##### `TaskType`

任务类型 - 用于路由决策（使用类避免 Enum 序列化问题）

| 方法 | 说明 |
|------|------|
| `all(cls)` |  |

##### `RouterConfig`

路由器配置

##### `RoutingDecision`

路由决策记录

##### `ResponseCache`

简单 LRU 缓存，按消息内容哈希存储响应

| 方法 | 说明 |
|------|------|
| `get(self, messages)` | 获取缓存的响应 |
| `set(self, messages, response)` | 缓存响应 |
| `clear(self)` | 清空缓存 |
| `stats(self)` | 缓存统计 |

##### `ModelRouter`

模型路由器

| 方法 | 说明 |
|------|------|
| `select(self, task_type, complexity, budget_remaining)` | 选择最优模型 |
| `get_model(self, provider, tier)` | 直接获取指定模型 |
| `get_stats(self)` | 获取路由统计 |
| `clear_cache(self)` | 清空响应缓存 |
| `reset_stats(self)` | 重置统计信息 |

##### `NoModelAvailableError`

没有可用模型

**继承**: Exception

### `src/core/summary.py`

任务总结模块 - 自动化任务完成后生成结构化总结

功能：
- 记录工作流执行全过程
- 统计 Token 消耗和成本
- 分析 Agent 执行情况
- 导出多种格式（JSON/TXT/HTML）
- 生成下次优化建议

使用场景：
1. 任务完成后自动生成总结报告
2. 分析 Token 消耗，优化成本
3. 回顾工作流执行情况
4. 团队协作时分享执行结果

使用示例：
    from src.core.summary import generate_summary, print_summary, save_summary

    # 生成总结
    summary = generate_summary(
        task="实现用户认证模块",
        workflow="build",
        completed_steps=[...],
    )

    # 打印到终端
    print_summary(summary)

    # 保存到文件
    save_path = save_summary(summary, format="json")

#### 类

##### `StepRecord`

单个步骤的执行记录

| 方法 | 说明 |
|------|------|
| `to_dict(self)` |  |

##### `ModelUsage`

单个模型的调用统计

##### `TaskSummary`

任务总结数据类

| 方法 | 说明 |
|------|------|
| `to_dict(self)` |  |
| `from_dict(cls, data)` |  |

#### 函数

##### `generate_summary(task, workflow, completed_steps, project_path, start_time, end_time)`

根据已完成步骤生成任务总结

##### `_generate_recommendations(steps, total_cost, total_tokens, workflow)`

生成优化建议

##### `_infer_models(workflow, agent_count)`

推断使用的模型

##### `print_summary(summary)`

在终端打印总结（带格式）

##### `print_summary_compact(summary)`

紧凑版总结（单行）

##### `save_summary(summary, output_dir, format, filename)`

保存总结到文件

##### `_write_txt_summary(f, summary)`

写入 TXT 格式

##### `_write_html_summary(f, summary)`

写入 HTML 格式

##### `load_summary(filepath)`

从文件加载总结

##### `quick_summary(task, workflow, duration, tokens, steps)`

快速生成简单总结（用于不需要完整信息的场景）

### `src/main.py`

FastAPI 主入口

### `src/models/baichuan.py`

百川智能 (Baichuan) 模型适配器

API 地址：https://api.baichuan-ai.com
文档：https://platform.baichuan-ai.com/docs

特点：
- 王小川创办
- 中文能力出色
- 支持超长上下文
- 兼容 OpenAI 格式

#### 类

##### `BaichuanModel`

百川智能模型适配器，兼容 OpenAI 格式

**继承**: BaseModel

| 方法 | 说明 |
|------|------|
| `provider(self)` |  |
| `model_name(self)` |  |

##### `BaichuanAPIError`

百川智能 API 错误

**继承**: Exception

### `src/models/base.py`

模型基类 - 定义所有 LLM 提供商的统一接口

设计原则：
1. 异步优先 - 所有 API 调用都是异步的
2. 流式支持 - 支持流式输出，提升用户体验
3. 统一错误处理 - 捕获各提供商的差异
4. Token 计数 - 标准化的 token 使用统计

#### 类

##### `ModelTier`

模型性能层级 - 对应原项目的 haiku/sonnet/opus 三层

**继承**: Enum

##### `ModelProvider`

支持的模型提供商

**继承**: Enum

##### `Message`

统一的消息格式

##### `Usage`

Token 使用统计

##### `ModelResponse`

统一的响应格式

##### `ModelConfig`

模型配置

##### `BaseModel`

所有模型适配器的基类

**继承**: ABC

| 方法 | 说明 |
|------|------|
| `provider(self)` | 返回提供商标识 |
| `model_name(self)` | 返回实际使用的模型名称 |
| `get_cost(self, usage)` | 计算本次调用的成本（元） |
| `update_usage(self, usage)` | 更新累计使用量 |
| `get_total_usage(self)` | 获取累计使用量 |
| `reset_usage(self)` | 重置使用统计 |

### `src/models/deepseek.py`

DeepSeek 模型适配器

DeepSeek API 文档：https://platform.deepseek.com/api-docs/

特点：
1. 完全兼容 OpenAI API 格式
2. 免费额度：每天 4000 万 token
3. 支持中文，质量接近 GPT-4
4. 价格极低（免费额度内）

模型：
- deepseek-chat：通用对话模型（对应 sonnet）
- deepseek-coder：代码专用模型（代码任务首选）

#### 类

##### `DeepSeekModel`

DeepSeek 模型适配器

**继承**: BaseModel

| 方法 | 说明 |
|------|------|
| `provider(self)` |  |
| `model_name(self)` |  |

##### `DeepSeekAPIError`

DeepSeek API 错误

**继承**: Exception

### `src/models/doubao.py`

字节豆包 (Doubao) 模型适配器

API: https://ark.cn-beijing.volces.com/api/v3
文档: https://www.volcengine.com/docs/82379/1263482

特点：
- 字节跳动自研大模型
- 性价比高
- 支持长上下文

#### 类

##### `DoubaoModel`

字节豆包 (Doubao) 模型适配器

**继承**: BaseModel

| 方法 | 说明 |
|------|------|
| `provider(self)` |  |
| `model_name(self)` |  |

##### `DoubaoAPIError`

字节豆包 API 错误

**继承**: Exception

### `src/models/glm.py`

智谱 GLM (ChatGLM) 模型适配器

API: https://open.bigmodel.cn/api/paas/v4
文档: https://open.bigmodel.cn/dev/api

特点：
- 智谱华章自研大模型
- 中文能力出色
- 开源版本 ChatGLM3 可本地部署
- 支持工具调用（Function Calling）

#### 类

##### `GLMModel`

智谱 GLM (ChatGLM) 模型适配器

**继承**: BaseModel

| 方法 | 说明 |
|------|------|
| `provider(self)` |  |
| `model_name(self)` |  |

##### `GLMAPIError`

智谱 GLM API 错误

**继承**: Exception

### `src/models/hunyuan.py`

腾讯混元 (Hunyuan) 模型适配器

API: https://api.hunyuan.cn
文档: https://cloud.tencent.com/document/product/

特点：
- 腾讯自研大模型
- 中文理解能力强
- 支持多模态（文本/图像）

#### 类

##### `HunyuanModel`

腾讯混元 (Hunyuan) 模型适配器

**继承**: BaseModel

| 方法 | 说明 |
|------|------|
| `provider(self)` |  |
| `model_name(self)` |  |

##### `HunyuanAPIError`

腾讯混元 API 错误

**继承**: Exception

### `src/models/kimi.py`

Kimi模型适配器

API: https://api.moonshot.cn
文档: https://platform.moonshot.cn/docs

特点：
- 超长上下文（128K tokens）
- 支持文件理解（PDF/Word 等）
- 中文能力出色
- 代码生成能力强

#### 类

##### `KimiModel`

Kimi模型适配器

**继承**: BaseModel

| 方法 | 说明 |
|------|------|
| `provider(self)` |  |
| `model_name(self)` |  |

##### `KimiAPIError`

Kimi API 错误

**继承**: Exception

### `src/models/minimax.py`

MiniMax 模型适配器

API: https://api.minimax.chat
文档: https://www.minimaxi.com/document

特点：
- 长上下文支持（最高 1M tokens）
- 中文理解能力强
- 价格适中

#### 类

##### `MiniMaxModel`

MiniMax 模型适配器

**继承**: BaseModel

| 方法 | 说明 |
|------|------|
| `provider(self)` |  |
| `model_name(self)` |  |

##### `MiniMaxAPIError`

MiniMax API 错误

**继承**: Exception

### `src/models/spark.py`

讯飞星火 (Spark) 模型适配器

API 地址：https://spark-api.xf-yun.com
文档：https://www.xfyun.cn/doc/spark/

特点：
- 科大讯飞出品
- 语音交互能力强
- 中文语义理解优秀
- 需三个凭证：API Key / App ID / Secret Key

#### 类

##### `SparkModel`

讯飞星火模型适配器

**继承**: BaseModel

| 方法 | 说明 |
|------|------|
| `provider(self)` |  |
| `model_name(self)` |  |

##### `SparkAPIError`

讯飞星火 API 错误

**继承**: Exception

### `src/models/tiangong.py`

天工AI (Tiangong) 模型适配器

API 地址：https://model-platform.tiangong.cn
文档：https://model-platform.tiangong.cn/document

特点：
- 昆仑万维出品
- 中文理解能力强
- 支持超长上下文
- 兼容 OpenAI 格式

#### 类

##### `TiangongModel`

天工AI 模型适配器，兼容 OpenAI 格式

**继承**: BaseModel

| 方法 | 说明 |
|------|------|
| `provider(self)` |  |
| `model_name(self)` |  |

##### `TiangongAPIError`

天工AI API 错误

**继承**: Exception

### `src/models/tongyi.py`

通义千问 (Tongyi) 模型适配器

阿里云通义千问 API 文档：https://help.aliyun.com/zh/dashscope/

特点：
1. 阿里云出品，中文能力强
2. 支持多轮对话
3. 多种模型可选（qwen-max, qwen-plus, qwen-turbo）

模型：
- qwen-max：最强模型（对应 HIGH tier）
- qwen-plus：通用模型（对应 MEDIUM tier）
- qwen-turbo：快速模型（对应 LOW tier）

#### 类

##### `TongyiModel`

通义千问模型适配器

**继承**: BaseModel

| 方法 | 说明 |
|------|------|
| `provider(self)` |  |
| `model_name(self)` |  |

##### `TongyiAPIError`

通义千问 API 错误

**继承**: Exception

### `src/models/wenxin.py`

文心一言 (Wenxin) 模型适配器

百度文心一言 API 文档：https://cloud.baidu.com/doc/WENXINWORKSHOP/index.html

特点：
1. 百度出品，中文能力强
2. 支持多轮对话
3. 多种模型可选（ERNIE-Bot-4, ERNIE-Bot, ERNIE-Bot-turbo）

模型：
- ERNIE-Bot-4：最强模型（对应 HIGH tier）
- ERNIE-Bot：通用模型（对应 MEDIUM tier）
- ERNIE-Bot-turbo：快速模型（对应 LOW tier）

#### 类

##### `WenxinModel`

文心一言模型适配器

**继承**: BaseModel

| 方法 | 说明 |
|------|------|
| `provider(self)` |  |
| `model_name(self)` |  |

##### `WenxinAPIError`

文心一言 API 错误

**继承**: Exception

### `src/quest/executor.py`

Quest 执行引擎

负责任务的后台执行。
使用 asyncio 在后台运行 omc 工作流，实时跟踪进度。

#### 类

##### `QuestExecutor`

Quest 后台执行引擎

| 方法 | 说明 |
|------|------|
| `start(self, quest)` | 启动后台执行（仅启动，不会阻塞） |
| `stop(self, quest_id)` | 停止正在运行的 Quest |
| `is_running(self, quest_id)` | 检查 Quest 是否在运行 |
| `cancel(self, quest_id)` | 取消 Quest（不中断正在运行的，但标记为取消） |
| `pause(self, quest_id)` | 暂停 Quest |
| `resume(self, quest_id)` | 恢复暂停的 Quest |

### `src/quest/manager.py`

Quest 管理器

统一管理 Quest 的创建、SPEC 生成、执行、查询。

#### 类

##### `QuestManager`

Quest Mode 总管理器

| 方法 | 说明 |
|------|------|
| `router(self)` |  |
| `executor(self)` |  |
| `confirm_and_execute(self, quest_id)` | 用户确认 SPEC 后，开始后台执行 |
| `execute_without_spec(self, quest_id)` | 直接执行（不生成 SPEC） |
| `get_quest(self, quest_id)` | 获取单个 Quest |
| `list_quests(self, status_filter)` | 列出 Quest |
| `get_active_quests(self)` | 获取活跃的 Quest |
| `cancel(self, quest_id)` | 取消 Quest |
| `stop(self, quest_id)` | 停止执行 |
| `pause(self, quest_id)` | 暂停 |
| `resume(self, quest_id)` | 恢复 |
| `delete(self, quest_id)` | 删除 Quest |
| `is_running(self, quest_id)` | 检查是否在运行 |

### `src/quest/models.py`

Quest Mode 数据模型

Quest = 异步自主编程任务
一个 Quest 包含：描述、生成的 SPEC、执行状态、结果

#### 类

##### `QuestStatus`

任务状态

**继承**: str, Enum

##### `QuestPriority`

优先级

**继承**: str, Enum

##### `SpecSection`

SPEC 文档章节

**继承**: BaseModel

##### `AcceptanceCriteria`

验收标准

**继承**: BaseModel

##### `QuestSpec`

任务规格文档

**继承**: BaseModel

| 方法 | 说明 |
|------|------|
| `to_markdown(self)` | 转换为 Markdown 格式 |

##### `QuestStep`

Quest 执行步骤

**继承**: BaseModel

##### `Quest`

Quest 任务

**继承**: BaseModel

| 方法 | 说明 |
|------|------|
| `duration(self)` | 返回执行时长（秒） |
| `progress(self)` | 返回完成进度 0.0 - 1.0 |
| `to_summary(self)` | 转换为摘要字符串 |

##### `QuestDisplay`

Quest CLI 展示格式

| 方法 | 说明 |
|------|------|
| `from_quest(cls, quest)` |  |

##### `QuestNotification`

Quest 通知

### `src/quest/spec_generator.py`

SPEC 生成器

根据用户需求描述，使用 AI 模型生成详细的 SPEC.md 规格文档。

#### 类

##### `SpecGenerator`

SPEC 文档生成器

### `src/quest/store.py`

Quest 持久化存储

使用 JSON 文件存储 Quest 列表，每个 Quest 单独一个 JSON 文件。
存储在 <project_path>/.omc/quests/ 目录下。

#### 类

##### `QuestStore`

Quest 持久化存储

| 方法 | 说明 |
|------|------|
| `create(self, title, description, project_path)` | 创建新 Quest |
| `get(self, quest_id)` | 获取 Quest |
| `save(self, quest)` | 保存 Quest |
| `delete(self, quest_id)` | 删除 Quest |
| `list(self, status_filter)` | 列出所有 Quest |
| `get_active(self)` | 获取活跃的 Quest（未完成且未取消） |
| `update_status(self, quest_id, status)` | 更新 Quest 状态 |
| `set_spec(self, quest_id, spec)` | 设置 SPEC |

### `src/rag/indexer.py`

代码库索引器

功能：
1. 扫描项目文件
2. 解析代码结构
3. 生成嵌入向量
4. 构建向量索引

#### 类

##### `CodeElementType`

代码元素类型

**继承**: str, Enum

##### `ProgrammingLanguage`

编程语言

**继承**: str, Enum

##### `CodeElement`

代码元素

##### `FileIndex`

文件索引

##### `IndexConfig`

索引配置

##### `PythonParser`

Python 代码解析器

| 方法 | 说明 |
|------|------|
| `parse(self, source, file_path)` | 解析 Python 源码 |

##### `CodebaseIndexer`

代码库索引器

| 方法 | 说明 |
|------|------|
| `should_index(self, file_path)` | 判断是否应该索引该文件 |
| `detect_language(self, file_path)` | 检测文件语言 |
| `index_file(self, file_path)` | 索引单个文件 |
| `index_directory(self, progress_callback)` | 索引整个目录 |
| `get_stats(self)` | 获取索引统计 |
| `save(self, path)` | 保存索引 |
| `load(self, path)` | 加载索引 |

### `src/rag/search.py`

语义搜索模块

功能：
1. 向量相似度搜索
2. 混合搜索（关键词 + 语义）
3. 上下文相关搜索

#### 类

##### `SearchResult`

搜索结果

##### `SearchConfig`

搜索配置

##### `SemanticSearch`

语义搜索

| 方法 | 说明 |
|------|------|
| `search(self, query, search_type, filters)` | 执行搜索 |
| `search_context(self, query, context_elements, max_results)` | 上下文相关搜索 |

##### `ContextBuilder`

上下文构建器

| 方法 | 说明 |
|------|------|
| `build_context(self, task, relevant_files, max_tokens)` | 构建项目上下文 |

### `src/team/auth.py`

团队认证模块

管理团队创建、成员管理和权限控制。

#### 类

##### `TeamMember`

团队成员

| 方法 | 说明 |
|------|------|
| `to_dict(self)` |  |

##### `Team`

团队

| 方法 | 说明 |
|------|------|
| `to_dict(self)` |  |

##### `UserSession`

用户会话

| 方法 | 说明 |
|------|------|
| `is_valid(self)` |  |
| `to_dict(self)` |  |

##### `TeamAuth`

团队认证管理器

| 方法 | 说明 |
|------|------|
| `check_permission(self, user_id, team_id, required_role)` | 检查权限 |

### `src/team/notification.py`

消息通知模块

实现任务完成通知和团队广播。

#### 类

##### `NotificationType`

通知类型

**继承**: str, Enum

##### `NotificationPriority`

通知优先级

**继承**: str, Enum

##### `Notification`

通知消息

| 方法 | 说明 |
|------|------|
| `to_dict(self)` |  |

##### `ConnectionManager`

WebSocket 连接管理器

| 方法 | 说明 |
|------|------|
| `disconnect(self, websocket, user_id, team_id)` | 断开连接 |

##### `TeamNotifier`

团队通知器

| 方法 | 说明 |
|------|------|
| `register_handler(self, notification_type, handler)` | 注册通知处理器 |
| `get_team_notifications(self, team_id, unread_only)` | 获取团队通知 |
| `get_user_notifications(self, user_id, team_id, unread_only)` | 获取用户通知 |
| `mark_as_read(self, notification_id)` | 标记通知为已读 |

### `src/team/statistics.py`

团队统计模块

记录和查询团队使用数据。

#### 类

##### `UsageRecord`

使用记录

| 方法 | 说明 |
|------|------|
| `to_dict(self)` |  |

##### `TeamStats`

团队统计数据

| 方法 | 说明 |
|------|------|
| `to_dict(self)` |  |

##### `UserStats`

用户统计数据

| 方法 | 说明 |
|------|------|
| `to_dict(self)` |  |

##### `TeamStatistics`

团队统计管理器

| 方法 | 说明 |
|------|------|
| `record_usage(self, record_id, team_id, user_id, task_id, task_type, model, tokens_used, cost, execution_time, status)` | 记录使用数据 |
| `get_team_stats(self, team_id, period)` | 获取团队统计 |
| `get_user_stats(self, user_id, team_id, period)` | 获取用户统计 |
| `cleanup_old_records(self, days)` | 清理旧记录 |
| `get_all_teams(self)` | 获取所有团队 ID |

### `src/team/task_sync.py`

任务状态同步模块

实现多人共享任务状态，支持实时更新和订阅。

#### 类

##### `TaskStatus`

任务状态

**继承**: str, Enum

##### `MemberRole`

成员角色

**继承**: str, Enum

##### `TeamTask`

团队任务

| 方法 | 说明 |
|------|------|
| `to_dict(self)` | 转换为字典 |
| `from_dict(cls, data)` | 从字典创建 |

##### `TaskSync`

任务状态同步器

### `src/utils/performance.py`

性能优化模块

提供缓存、连接池、异步执行等优化功能。

#### 类

##### `LRUCache`

线程安全的 LRU 缓存

| 方法 | 说明 |
|------|------|
| `get(self, key)` | 获取缓存值 |
| `set(self, key, value)` | 设置缓存值 |
| `delete(self, key)` | 删除缓存条目 |
| `clear(self)` | 清空缓存 |
| `stats(self)` | 获取缓存统计 |

##### `AsyncExecutor`

异步任务执行器

##### `PerformanceMonitor`

性能监控器

| 方法 | 说明 |
|------|------|
| `record(self, name, duration)` | 记录执行时间 |
| `get_stats(self, name)` | 获取统计信息 |
| `get_all_stats(self)` | 获取所有操作的统计信息 |
| `clear(self)` | 清空所有记录 |

#### 函数

##### `cache_result(ttl_seconds)`

函数结果缓存装饰器

##### `measure_time(func)`

执行时间测量装饰器

##### `get_cache()`

获取全局缓存实例

##### `get_monitor()`

获取全局性能监控实例

### `src/web/app.py`

Web 界面入口 - FastAPI 应用
提供可视化界面执行 AI 编程任务

#### 类

##### `TaskManager`

管理所有运行中的任务

| 方法 | 说明 |
|------|------|
| `create_task(self)` |  |
| `get_queue(self, task_id)` |  |
| `update_step(self, task_id, step, status, content)` |  |
| `complete_task(self, task_id, result, error)` |  |
| `get_task(self, task_id)` |  |
| `list_tasks(self)` |  |

##### `ExecuteRequest`

**继承**: BaseModel

#### 函数

##### `create_router()`

创建模型路由器

##### `create_orchestrator(router)`

创建编排器

##### `json_dumps(obj)`

##### `run()`

启动服务

### `src/web/dashboard_api.py`

仪表板 API

提供项目统计和概览数据。

#### 类

##### `DashboardStats`

仪表板统计数据

**继承**: BaseModel

##### `ActivityData`

活动数据

**继承**: BaseModel

##### `AgentStatus`

Agent 状态

**继承**: BaseModel

##### `RecentTask`

最近任务

**继承**: BaseModel

#### 函数

##### `_get_mock_stats()`

获取模拟统计数据

##### `_get_mock_activity()`

获取模拟活动数据

##### `_get_mock_agents()`

获取模拟 Agent 状态

##### `_get_mock_recent_tasks()`

获取模拟最近任务

### `src/web/history_api.py`

Web UI 增强模块
- 任务历史界面
- Agent 状态面板
- 实时进度增强

#### 类

##### `HistoryStore`

历史记录存储

| 方法 | 说明 |
|------|------|
| `save(self, task_id, record)` | 保存历史记录 |
| `load(self, task_id)` | 加载历史记录 |
| `list_all(self, limit, offset, status, workflow)` | 列出所有历史记录 |
| `delete(self, task_id)` | 删除历史记录 |
| `get_stats(self)` | 获取统计信息 |

##### `HistoryFilter`

**继承**: BaseModel

##### `AgentStatusManager`

Agent 状态管理器

| 方法 | 说明 |
|------|------|
| `register_agent(self, name, info)` | 注册 Agent |
| `update_status(self, name, status, task, progress)` | 更新 Agent 状态 |
| `get_agent(self, name)` | 获取 Agent 状态 |
| `get_all(self)` | 获取所有 Agent 状态 |
| `subscribe(self)` | 订阅状态变化 |

### `src/web/team_api.py`

团队 API 路由

提供团队创建、加入、任务同步和统计等 API。

#### 类

##### `CreateTeamRequest`

创建团队请求

**继承**: BaseModel

##### `JoinTeamRequest`

加入团队请求

**继承**: BaseModel

##### `CreateTaskRequest`

创建任务请求

**继承**: BaseModel

##### `UpdateTaskRequest`

更新任务请求

**继承**: BaseModel

##### `RecordUsageRequest`

记录使用请求

**继承**: BaseModel

##### `BroadcastRequest`

广播消息请求

**继承**: BaseModel

### `src/wiki/generator.py`

Wiki Generator - Markdown 文档生成器

从解析的模块信息生成结构化 Markdown 文档。

#### 类

##### `WikiGenerator`

Wiki 文档生成器

| 方法 | 说明 |
|------|------|
| `generate(self, output_path)` | 生成 Wiki 文档 |

### `src/wiki/parser.py`

Wiki Parser - Python AST 解析器

使用 Python ast 模块解析代码结构，提取：
- 模块文档字符串
- 导入语句
- 类定义（名称、文档、方法）
- 函数定义（名称、文档、参数）

#### 类

##### `FunctionInfo`

函数信息

| 方法 | 说明 |
|------|------|
| `signature(self)` | 生成函数签名 |

##### `ClassInfo`

类信息

| 方法 | 说明 |
|------|------|
| `public_methods(self)` | 获取公开方法（不以 _ 开头） |
| `private_methods(self)` | 获取私有方法（以 _ 开头） |

##### `ImportInfo`

导入信息

##### `ModuleInfo`

模块信息

##### `ASTVisitorWithParent`

带父节点引用的 AST 访问器

**继承**: ast.NodeVisitor

| 方法 | 说明 |
|------|------|
| `visit(self, node)` |  |
| `get_parent(self, node)` | 获取父节点 |

##### `PythonParser`

Python 代码解析器

| 方法 | 说明 |
|------|------|
| `parse_file(self, file_path)` | 解析单个 Python 文件 |
| `scan_directory(self, directory, pattern)` | 扫描目录下的所有 Python 文件 |

### `todo_demo.py`

待办事项 CLI 应用
支持添加、查看、完成、删除任务，数据存储在 JSON 文件中

#### 函数

##### `main()`

主函数：解析命令行参数并执行相应命令

---

*此文档由 [oh-my-coder](https://github.com/VOBC/oh-my-coder) 自动生成*
