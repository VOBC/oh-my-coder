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

Oh My Coder Demo Video Generator
生成 3 分钟演示 GIF（~180秒播放时间，约60帧/6秒 = 30帧总）

| 指标 | 数值 |
|------|------|
| 总文件数 | 196 |
| 总类数 | 391 |
| 总函数数 | 644 |

### 核心依赖

```python
import __future__
import os
import pathlib
import asyncio
import os
import pathlib
import __future__
import asyncio
import json
```

## 项目结构

```
│   ├── examples/
│   │   ├── advanced_demo.py
│   │   ├── advanced_usage.py
│   │   ├── basic_usage.py
│   │   ├── cli_demo.py
│   │   ├── demo.py
│   │   ├── example_cicd.py
│   │   ├── example_cli.py
│   │   ├── example_config.py
│   │   ├── example_django.py
│   │   ├── example_fastapi.py
│   │   └── web_demo.py
│   ├── screenshots/
│   │   ├── gen_demo_gif.py
│   │   └── generate_terminal_demo.py
│   │   │   ├── simple-agent/
│   │   │   │   └── weather_agent.py
├── scripts/
│   ├── check_doc_sync.py
│   ├── gen_demo.py
│   └── gen_demo_gif.py
├── src/
│   ├── cli.py
│   ├── main.py
│   └── model_discovery.py
│   ├── agents/
│   │   ├── analyst.py
│   │   ├── api_agent.py
│   │   ├── architect.py
│   │   ├── auth_agent.py
│   │   ├── base.py
│   │   ├── code_cleaner.py
│   │   ├── code_research.py
│   │   ├── code_reviewer.py
│   │   ├── code_simplifier.py
│   │   ├── cost_optimizer.py
│   │   ├── critic.py
│   │   ├── cross_validation.py
│   │   ├── data_agent.py
│   │   ├── database.py
│   │   ├── debugger.py
│   │   ├── designer.py
│   │   ├── devops.py
│   │   ├── document.py
│   │   ├── evolution.py
│   │   ├── executor.py
│   │   ├── explore.py
│   │   ├── git_master.py
│   │   ├── health_check.py
│   │   ├── migration.py
│   │   ├── performance.py
│   │   ├── planner.py
│   │   ├── prompt_agent.py
│   │   ├── qa_tester.py
│   │   ├── scientist.py
│   │   ├── security.py
│   │   ├── self_improving.py
│   │   ├── skill_manage.py
│   │   ├── tracer.py
│   │   ├── transparency.py
│   │   ├── uml.py
│   │   ├── verifier.py
│   │   ├── vision.py
│   │   └── writer.py
│   │   ├── persistence/
│   │   │   └── store.py
│   ├── api/
│   │   ├── openapi.py
│   │   └── server_api.py
│   ├── capabilities/
│   │   └── package.py
│   ├── capsule/
│   │   ├── capsule.py
│   │   ├── gene.py
│   │   └── registry.py
│   ├── commands/
│   │   ├── cli.py
│   │   ├── cli_agent.py
│   │   ├── cli_checkpoint.py
│   │   ├── cli_clean.py
│   │   ├── cli_commands.py
│   │   ├── cli_config.py
│   │   ├── cli_config_ext.py
│   │   ├── cli_cost.py
│   │   ├── cli_doc.py
│   │   ├── cli_doctor.py
│   │   ├── cli_gateway.py
│   │   ├── cli_init.py
│   │   ├── cli_lsp.py
│   │   ├── cli_mcp.py
│   │   ├── cli_migrate.py
│   │   ├── cli_model.py
│   │   ├── cli_monorepo.py
│   │   ├── cli_multiagent.py
│   │   ├── cli_package_manager.py
│   │   ├── cli_plan.py
│   │   ├── cli_profile.py
│   │   ├── cli_quality.py
│   │   ├── cli_quest.py
│   │   ├── cli_review.py
│   │   ├── cli_run.py
│   │   ├── cli_search.py
│   │   ├── cli_security.py
│   │   ├── cli_self_config.py
│   │   ├── cli_server.py
│   │   ├── cli_skill.py
│   │   ├── cli_task.py
│   │   ├── cli_template.py
│   │   ├── cli_tui.py
│   │   ├── cli_usage.py
│   │   ├── quickstart.py
│   │   └── share.py
│   ├── config/
│   │   ├── agent_config.py
│   │   └── workflow_loader.py
│   ├── context/
│   │   ├── browser_context.py
│   │   └── workspace_scanner.py
│   ├── core/
│   │   ├── chain_of_thought.py
│   │   ├── checkpoint.py
│   │   ├── context_compressor.py
│   │   ├── dependency_resolver.py
│   │   ├── history.py
│   │   ├── local_model_discovery.py
│   │   ├── monorepo.py
│   │   ├── ollama_health.py
│   │   ├── orchestrator.py
│   │   ├── profile_manager.py
│   │   ├── router.py
│   │   ├── skill_extractor.py
│   │   └── summary.py
│   ├── gateway/
│   │   ├── base.py
│   │   └── gateway.py
│   │   ├── platforms/
│   │   │   ├── base.py
│   │   │   ├── dingtalk.py
│   │   │   ├── discord.py
│   │   │   ├── feishu.py
│   │   │   ├── slack.py
│   │   │   ├── telegram.py
│   │   │   ├── wecom.py
│   │   │   └── whatsapp.py
│   ├── integrations/
│   │   └── sourcegraph.py
│   ├── mcp/
│   │   ├── resources.py
│   │   ├── server.py
│   │   └── tools.py
│   ├── memory/
│   │   ├── auto_compact.py
│   │   ├── learnings.py
│   │   ├── long_term.py
│   │   ├── manager.py
│   │   ├── short_term.py
│   │   └── skill_manager.py
│   ├── models/
│   │   ├── baichuan.py
│   │   ├── base.py
│   │   ├── deepseek.py
│   │   ├── doubao.py
│   │   ├── glm.py
│   │   ├── hunyuan.py
│   │   ├── kimi.py
│   │   ├── mimo.py
│   │   ├── minimax.py
│   │   ├── ollama.py
│   │   ├── spark.py
│   │   ├── tiangong.py
│   │   ├── tongyi.py
│   │   └── wenxin.py
│   ├── multiagent/
│   │   └── coordinator.py
│   ├── plugins/
│   │   ├── example_plugin.py
│   │   ├── loader.py
│   │   └── registry.py
│   ├── quest/
│   │   ├── executor.py
│   │   ├── manager.py
│   │   ├── models.py
│   │   ├── notifications.py
│   │   ├── spec_generator.py
│   │   └── store.py
│   ├── rag/
│   │   ├── indexer.py
│   │   └── search.py
│   ├── sandbox/
│   │   ├── dangerous_command_blocker.py
│   │   └── sandbox.py
│   ├── security/
│   │   └── permissions.py
│   ├── skills/
│   │   └── registry.py
│   ├── state/
│   │   └── task_state.py
│   ├── stats/
│   │   ├── counter.py
│   │   └── models.py
│   ├── tasks/
│   │   ├── t1_extract_posts.py
│   │   ├── t2_classify_posts.py
│   │   └── t3_write_summary.py
│   ├── team/
│   │   ├── auth.py
│   │   ├── notification.py
│   │   ├── statistics.py
│   │   └── task_sync.py
│   ├── tools/
│   │   └── sourcegraph.py
│   ├── utils/
│   │   ├── api_key_mask.py
│   │   ├── notify.py
│   │   ├── performance.py
│   │   └── safe_executor.py
│   ├── web/
│   │   ├── app.py
│   │   ├── coverage_api.py
│   │   ├── dashboard_api.py
│   │   ├── history_api.py
│   │   ├── local_models_api.py
│   │   ├── share_api.py
│   │   └── team_api.py
│   ├── wiki/
│   │   ├── generator.py
│   │   └── parser.py
├── tools/
│   ├── demo_video_generator.py
│   ├── generate_demo_v020.py
│   ├── todo_demo.py
│   └── verify_gateway.py
```

### 目录说明

| 目录 | 说明 |
|------|------|
| src/ | 源代码目录 |
| tests/ | 测试文件 |
| docs/ | 文档 |

## 模块详解

### `docs/examples/advanced_demo.py`

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

### `docs/examples/advanced_usage.py`

高级示例：多 Agent 协作和多模型使用

演示：
1. 多 Agent 协作
2. 多模型配置
3. 工作流编排
4. 任务总结

### `docs/examples/basic_usage.py`

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

### `docs/examples/cli_demo.py`

CLI 使用示例

展示如何使用 Oh My Coder 的命令行界面。

运行方式：
    python examples/cli_demo.py

#### 函数

##### `run(cmd, desc)`

执行命令并打印输出

##### `main()`

### `docs/examples/demo.py`

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

### `docs/examples/example_cicd.py`

CI/CD 集成示例 - 展示如何在 CI 环境中使用 Oh My Coder

适用场景：
- GitHub Actions
- GitLab CI
- Jenkins
- 任何 CI/CD 环境

运行方式：
    python examples/example_cicd.py

前置条件：
    export DEEPSEEK_API_KEY=your_key_here

#### 函数

##### `demo_github_actions()`

GitHub Actions 集成示例

##### `demo_gitlab_ci()`

GitLab CI 集成示例

##### `demo_precommit()`

Pre-commit Hook 集成

##### `demo_dockerfile()`

Docker 环境集成

##### `demo_ci_script()`

实际可用的 CI 脚本

##### `main()`

### `docs/examples/example_cli.py`

CLI 工具示例

演示如何使用 Oh My Coder 开发命令行工具。

场景：实现一个项目管理 CLI 工具

#### 类

##### `Priority`

任务优先级

**继承**: StrEnum

##### `Status`

任务状态

**继承**: StrEnum

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

### `docs/examples/example_config.py`

配置系统示例 - 展示如何加载和使用 Agent 配置文件

运行方式：
    python examples/example_config.py

本示例演示：
1. 加载 YAML 配置
2. 使用配置创建 Agent
3. 配置验证
4. 批量加载目录

#### 函数

##### `demo_load_single()`

演示 1: 加载单个配置文件

##### `demo_validate()`

演示 2: 验证配置文件

##### `demo_batch_load()`

演示 3: 批量加载配置目录

##### `demo_render_template()`

演示 4: 渲染 Prompt 模板

##### `demo_agent_config_usage()`

演示 5: 配置与 Agent 的实际使用

##### `demo_create_config()`

演示 6: 程序化创建配置

##### `main()`

### `docs/examples/example_django.py`

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

### `docs/examples/example_fastapi.py`

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

### `docs/examples/web_demo.py`

Web 界面使用示例

展示如何使用 Web 界面的 API 端点。

运行方式：
    python examples/web_demo.py

#### 函数

##### `pretty_json(data)`

格式化打印 JSON

### `docs/screenshots/gen_demo_gif.py`

生成 oh-my-coder Terminal 模拟动图（GIF）
风格：深色 Terminal，绿色/青色文字，模拟 Agent 执行过程

#### 函数

##### `get_font(size)`

##### `get_font_small()`

##### `cursor_visible(frame)`

光标每 0.5 秒闪烁一次

##### `render_frame(frame_idx)`

##### `main()`

### `docs/screenshots/generate_terminal_demo.py`

Generate a terminal execution demo GIF for oh-my-coder CLI.

#### 函数

##### `load_font()`

Load a monospace font.

##### `render_frame(lines, cursor_y, font)`

Render a single frame.

##### `get_lines_for_frame(frame_num)`

Determine which lines to show at this frame.

### `examples/templates/community/simple-agent/weather_agent.py`

Simple Weather Agent - Community Template Example

A minimal agent that demonstrates:
- Tool definition with @tool decorator
- OpenAI-compatible API integration
- Error handling and graceful degradation

#### 类

##### `WeatherResult`

Structured weather result.

**继承**: BaseModel

##### `WeatherAgent`

A simple weather query agent.

**继承**: Agent

#### 函数

##### `get_weather(city)`

Fetch weather information for a given city.

##### `main()`

CLI entry point.

### `scripts/check_doc_sync.py`

Documentation sync checker for Oh My Coder.

Checks:
1. Files that exist in both docs/ and docs/zh/ - verify structural sync (sections match)
2. Files only in docs/ - flag as missing Chinese translation
3. Files only in docs/zh/ - flag as missing English version

Exit codes:
  0 = All synced
  1 = Sync issues found

#### 函数

##### `extract_headings(content)`

Extract markdown headings with their levels.

##### `get_heading_outline(headings)`

Convert headings to a normalized outline for comparison.

##### `find_md_files(base_path, subdir, exclude_zh)`

Find all .md files in a directory.

##### `read_file_headings(file_path)`

Read file and extract headings.

##### `compare_headings(headings1, headings2)`

Compare two heading lists and return differences.

##### `check_docs_sync(project_root)`

Check documentation sync between docs/ and docs/zh/.

##### `main()`

Main entry point.

### `scripts/gen_demo.py`

Generate demo screenshots for oh-my-coder.

#### 函数

##### `make_terminal(title, lines, height)`

Render a terminal-like image.

##### `gen_demo_workflow()`

##### `gen_demo_agents()`

##### `gen_demo_web()`

##### `gen_flowchart_svg(out_path)`

Generate the workflow SVG.

##### `main()`

### `scripts/gen_demo_gif.py`

Generate oh-my-coder Demo GIF
3 steps: List Agents → Ask Question → Code Generated

#### 函数

##### `get_font(size)`

##### `make_terminal(title, lines, width, height)`

Render a terminal-like image.

##### `gen_step1_list_agents()`

Step 1: List Agents

##### `gen_step2_ask_question()`

Step 2: Ask Question

##### `gen_step3_code_generated()`

Step 3: Code Generated

##### `main()`

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
| `search_code(self, query, language, repo)` | 搜索公开代码库（通过 Sourcegraph） |
| `system_prompt(self)` |  |

### `src/agents/api_agent.py`

API Agent - REST API 设计与实现智能体

职责：
1. RESTful API 设计与规范编写
2. API 端点实现（FastAPI/Flask）
3. API 文档生成（OpenAPI/Swagger）
4. API 认证与权限设计

模型层级：MEDIUM（平衡）

#### 类

##### `APIAgent`

REST API 设计与实现智能体

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

### `src/agents/auth_agent.py`

Auth Agent - 认证与授权智能体

职责：
1. JWT / OAuth2 / API Key 认证方案设计
2. RBAC 权限模型设计
3. 登录注册流程实现
4. 安全中间件配置

模型层级：MEDIUM（平衡）

#### 类

##### `AuthAgent`

认证与授权智能体

**继承**: BaseAgent

| 方法 | 说明 |
|------|------|
| `system_prompt(self)` |  |

### `src/agents/base.py`

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
| `get_workspace_context(self, max_depth)` | 获取工作目录上下文 |
| `get_full_context(self, max_depth)` | 获取完整上下文（文件 + 浏览器） |
| `get_context_prompt(self, context)` | 根据上下文生成额外提示词 |
| `get_last_output(self)` | 获取最后一次输出 |
| `get_output_history(self)` | 获取输出历史 |
| `save_output(self, output_path)` | 保存输出到文件 |

#### 函数

##### `register_agent(agent_class)`

注册 Agent

##### `get_agent(name)`

获取已注册的 Agent

##### `list_all_agents()`

列出所有已注册的 Agent

##### `list_agents()`

列出所有已注册的 Agent

### `src/agents/code_cleaner.py`

#### 类

##### `CleanerStrategy`

清理策略白名单

##### `CleaningIssue`

单个清理问题

##### `CleanerReport`

清理报告

##### `CodeCleaner`

代码清理器

| 方法 | 说明 |
|------|------|
| `scan(self)` | 扫描项目，返回清理报告 |
| `fix(self, issue)` | 尝试自动修复单个问题 |
| `fix_all_auto(self)` | 自动修复所有可修复的问题 |
| `generate_report_md(self, report)` | 生成 Markdown 格式的清理报告 |

#### 函数

##### `main()`

CLI 入口

### `src/agents/code_research.py`

Code Research Agent - 代码研究智能体

职责：
1. 搜索公开代码库，获取参考实现
2. 查找 API 使用示例和最佳实践
3. 发现相关开源项目和库
4. 为代码编写提供外部参考

模型层级：MEDIUM（平衡质量与成本）

工作流程：
1. 解析研究目标（函数、模式、库）
2. 使用 Sourcegraph 搜索公开代码
3. 获取相关文件内容
4. 总结发现并提供建议

#### 类

##### `ResearchTarget`

研究目标

##### `CodeExample`

代码示例

##### `ResearchResult`

研究结果

##### `CodeResearchAgent`

代码研究 Agent

**继承**: BaseAgent

| 方法 | 说明 |
|------|------|
| `sg_client(self)` | 获取 Sourcegraph 客户端 |
| `system_prompt(self)` |  |
| `search_code(self, query, language, repo_filter, limit)` | 搜索代码并获取示例 |
| `find_repos(self, query, language, limit)` | 搜索相关仓库 |
| `research(self, target)` | 执行代码研究 |
| `cleanup(self)` | 清理资源 |

#### 函数

##### `research_code(query, language, limit)`

快捷代码研究函数

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

### `src/agents/cost_optimizer.py`

#### 类

##### `Complexity`

任务复杂度

**继承**: Enum

##### `ModelRecommendation`

模型推荐结果

##### `CostOptimizer`

成本优化器

| 方法 | 说明 |
|------|------|
| `analyze_task(self, task_description, file_count, new_files)` | 分析任务特征 |
| `recommend(self, task_description, file_count, new_files)` | 推荐最优模型 |
| `get_all_models(self)` | 获取所有可用模型 |

##### `CostEstimate`

费用估算结果

#### 函数

##### `calculate_cost(model, input_tokens, output_tokens)`

计算指定模型的 token 费用

##### `calculate_multi_model_cost(model_usages)`

计算多模型组合费用

##### `main()`

CLI 入口

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

### `src/agents/cross_validation.py`

#### 类

##### `ValidationStatus`

**继承**: Enum

##### `ValidationSeverity`

**继承**: Enum

##### `ValidationIssue`

发现的问题

##### `CrossValidationResult`

交叉验证报告

| 方法 | 说明 |
|------|------|
| `pass_rate(self)` | 验证通过率 |
| `to_summary(self)` | 生成人类可读摘要 |

##### `CrossValidationLayer`

交叉验证层

### `src/agents/data_agent.py`

DataAgent - 数据处理与 ETL 智能体

职责：
1. 数据清洗与转换
2. ETL 流水线设计
3. 数据导出与导入
4. 数据验证脚本

模型层级：MEDIUM（平衡）

#### 类

##### `DataAgent`

数据处理与 ETL 智能体

**继承**: BaseAgent

| 方法 | 说明 |
|------|------|
| `system_prompt(self)` |  |

### `src/agents/database.py`

Database Agent - 数据库设计与 SQL 智能体

职责：
1. 数据库表结构设计
2. SQL 查询编写与优化
3. 数据库迁移脚本生成
4. 索引优化建议

模型层级：MEDIUM（平衡）

#### 类

##### `DatabaseAgent`

数据库设计与 SQL 智能体

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

### `src/agents/devops.py`

DevOps Agent - CI/CD 与运维自动化智能体

职责：
1. CI/CD 流水线配置（GitHub Actions / GitLab CI）
2. Dockerfile 与容器化
3. 部署脚本编写
4. 监控与告警配置

模型层级：MEDIUM（平衡）

#### 类

##### `DevOpsAgent`

DevOps 与 CI/CD 自动化智能体

**继承**: BaseAgent

| 方法 | 说明 |
|------|------|
| `system_prompt(self)` |  |

### `src/agents/document.py`

Document Agent - 长篇技术文档撰写智能体

职责：
1. 长篇技术文档编写
2. 结构化文档模板
3. API 参考文档
4. 架构文档 / 设计文档

模型层级：LOW（快速，对应 haiku），但长文档用 MEDIUM 路由

#### 类

##### `DocumentAgent`

长篇文档 Agent - 结构化技术文档（比 WriterAgent 更专注长文档）

**继承**: BaseAgent

| 方法 | 说明 |
|------|------|
| `system_prompt(self)` |  |

### `src/agents/evolution.py`

#### 类

##### `EvolutionRecord`

进化记录

##### `SuccessPattern`

成功模式

##### `EvolutionConfig`

自进化配置

##### `EvolutionStore`

进化状态存储

| 方法 | 说明 |
|------|------|
| `load_evolution_history(self, agent_name, limit)` | 加载进化历史 |
| `save_evolution_record(self, record)` | 保存进化记录 |
| `get_current_generation(self, agent_name)` | 获取当前进化代数 |
| `load_success_patterns(self, agent_name)` | 加载成功模式库 |
| `save_success_pattern(self, pattern)` | 保存成功模式 |
| `add_success_pattern(self, agent_name, pattern_type, description, context, example)` | 添加成功模式 |
| `load_optimized_prompt(self, agent_name)` | 加载优化后的 system prompt |
| `save_optimized_prompt(self, agent_name, prompt)` | 保存优化后的 system prompt |
| `get_prompt_version(self, agent_name)` | 获取 prompt 版本号 |
| `get_evolution_stats(self, agent_name)` | 获取进化统计信息 |

##### `DecisionRecord`

重要决策记录 - 解决鬼打墙问题

##### `DecisionMemory`

版本迭代记忆 - 解决 Agent 鬼打墙问题

| 方法 | 说明 |
|------|------|
| `record_decision(self, title, problem, chosen_solution, agent_type, category, rejected_alternatives, result, outcome, reusable_for, keywords, related_files, version_tag)` | 记录一次重要决策 |
| `retrieve(self, query, limit)` | 检索历史决策 |
| `list_decisions(self, category, limit)` | 列出决策记录 |
| `get_stats(self)` | 获取决策记忆统计 |

### `src/agents/executor.py`

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

### `src/agents/health_check.py`

#### 类

##### `AgentStatus`

Agent 状态

**继承**: Enum

##### `AgentHealth`

单个 Agent 的健康状态

| 方法 | 说明 |
|------|------|
| `touch(self)` | 更新心跳时间 |
| `is_stale(self, threshold)` | 判断是否超时无心跳 |
| `record_failure(self, error)` | 记录一次失败，返回是否超过重试上限。 |
| `can_retry(self)` |  |
| `to_dict(self)` |  |

##### `HealthCheckResult`

单次健康检查的结果

| 方法 | 说明 |
|------|------|
| `to_dict(self)` |  |

##### `HealthChecker`

Agent 健康检查器

| 方法 | 说明 |
|------|------|
| `register_agent(self, agent_name, task_id, workflow_id, step_index)` | 注册一个 Agent 开始执行任务（心跳开始计时）。 |
| `unregister_agent(self, agent_name)` | 取消注册（任务完成后调用） |
| `register_task(self, agent_name, task)` | 注册 Agent 当前正在执行的 asyncio.Task（用于取消） |
| `heartbeat(self, agent_name)` | 更新 Agent 心跳。 |
| `record_failure(self, agent_name, error, workflow_id, step)` | 记录 Agent 执行失败。 |
| `reassign_task(self, agent_name, workflow_id, step)` | 将任务重新分配给空闲 Agent。 |
| `get_all_health(self)` | 获取所有 Agent 的健康状态 |
| `get_summary(self)` | 获取健康检查摘要 |

#### 函数

##### `format_health_display(health_map)`

格式化健康状态为可读文本，用于 `omc agent health` 输出。

### `src/agents/migration.py`

Migration Agent - 数据迁移与版本管理智能体

职责：
1. 数据库迁移脚本生成
2. 数据迁移方案设计
3. 迁移回滚策略
4. 迁移验证脚本

模型层级：MEDIUM（平衡）

#### 类

##### `MigrationAgent`

数据迁移与版本管理智能体

**继承**: BaseAgent

| 方法 | 说明 |
|------|------|
| `system_prompt(self)` |  |

### `src/agents/performance.py`

Performance Agent - 性能分析与优化智能体

职责：
1. 性能瓶颈定位与分析
2. 数据库查询优化
3. 缓存策略设计
4. 并发与异步优化建议

模型层级：HIGH（分析类任务）

#### 类

##### `PerformanceAgent`

性能分析与优化智能体

**继承**: BaseAgent

| 方法 | 说明 |
|------|------|
| `system_prompt(self)` |  |

### `src/agents/persistence/store.py`

#### 类

##### `AgentConfig`

Agent 配置快照

##### `HistoryEntry`

单条对话历史

| 方法 | 说明 |
|------|------|
| `to_dict(self)` |  |
| `from_dict(cls, data)` |  |

##### `AgentState`

Agent 运行时状态

| 方法 | 说明 |
|------|------|
| `to_dict(self)` |  |
| `from_dict(cls, data)` |  |

##### `AgentStateStore`

Agent 状态持久化管理器

| 方法 | 说明 |
|------|------|
| `save(self, agent_name, config, history, state, append_history)` | 保存 Agent 状态到磁盘 |
| `restore(self, agent_name, include_history)` | 从磁盘恢复 Agent 状态 |
| `delete(self, agent_name)` | 删除 Agent 状态目录 |
| `list_saved(self)` | 列出所有已保存的 Agent |
| `export_agent(self, agent_name, output_path, include_history, max_history)` | 导出 Agent 为单个 JSON 文件（可分享） |
| `import_agent(self, source_path, new_name, merge_history)` | 从 JSON 文件导入 Agent |
| `save_from_agent_instance(self, agent_instance, history, custom_state)` | 从 Agent 实例保存状态（便捷方法） |
| `get_stats(self)` | 获取存储统计 |

### `src/agents/planner.py`

#### 类

##### `TaskPriority`

任务优先级

**继承**: str, Enum

| 方法 | 说明 |
|------|------|
| `from_string(cls, value)` | 从字符串解析优先级，支持中文容错。 |

##### `TaskStatus`

任务状态

**继承**: str, Enum

##### `TaskComplexity`

任务复杂度

**继承**: str, Enum

| 方法 | 说明 |
|------|------|
| `from_string(cls, value)` | 从字符串解析复杂度，支持中文容错。 |

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
| `adjust_plan(plan, completed_tasks, failed_tasks, new_requirements)` | 自适应调整计划 |

### `src/agents/prompt_agent.py`

PromptAgent - Prompt 工程与提示词优化智能体

职责：
1. 优化 Agent 的 Prompt
2. 设计 Few-shot 示例
3. Prompt 版本管理与测试
4. Chain-of-Thought 引导设计

模型层级：LOW（文字类任务）

#### 类

##### `PromptAgent`

Prompt 工程与优化智能体

**继承**: BaseAgent

| 方法 | 说明 |
|------|------|
| `system_prompt(self)` |  |

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

### `src/agents/self_improving.py`

#### 类

##### `ExecutionFeedback`

执行反馈记录

##### `StrategyAdjustment`

策略调整记录

##### `LearningStore`

学习数据存储（SQLite）

| 方法 | 说明 |
|------|------|
| `record_feedback(self, feedback)` | 记录执行反馈 |
| `record_adjustment(self, adjustment)` | 记录策略调整 |
| `get_recent_failures(self, agent_type, limit)` | 获取最近的失败记录 |
| `get_error_patterns(self, agent_type, min_count)` | 分析错误模式 |
| `get_success_rate(self, agent_type, days)` | 计算成功率 |
| `get_adjustments(self, agent_type)` | 获取策略调整记录 |

##### `SelfImprovingAgent`

主动学习 Agent

**继承**: BaseAgent

| 方法 | 说明 |
|------|------|
| `system_prompt(self)` |  |
| `record_execution(self, agent_type, task_description, success, execution_time, error, user_correction, retry_count)` | 记录执行结果 |
| `analyze_and_improve(self, agent_type)` | 分析并生成改进建议 |
| `get_improved_prompt(self, agent_type, base_prompt)` | 获取改进后的提示词 |
| `report(self, agent_type)` | 生成学习报告 |
| `auto_create_skill(self, task_context)` | 自动生成 Skill 文件。 |
| `promote_best_practices_to_skills(self, dry_run)` | 将 LearningsMemory 中标记为 best-practice 的条目 |
| `analyze_task_logs(self, agent_type, recent_count)` | 分析任务执行日志，提取经验教训 |
| `extract_patterns(self, agent_type, pattern_type)` | 提取成功/失败模式并存储到模式库 |
| `update_system_prompt(self, agent_type, base_prompt, analysis)` | 根据进化分析更新 system prompt |
| `evolve(self, agent_type, trigger)` | 执行一次自进化 |
| `retrieve_past_decisions(self, problem_description, limit)` | 检索历史决策，避免重复踩坑 |
| `record_decision(self, title, problem, chosen_solution, agent_type, category, rejected_alternatives, result, outcome, reusable_for, related_files)` | 记录重要决策 |
| `list_decisions(self, category, limit)` | 列出决策记录 |
| `get_decision_stats(self)` | 获取决策记忆统计 |
| `get_evolution_stats(self, agent_type)` | 获取 Agent 的进化统计信息 |

### `src/agents/skill_manage.py`

#### 类

##### `SkillManageAgent`

Skill 管理 Agent

**继承**: BaseAgent

| 方法 | 说明 |
|------|------|
| `system_prompt(self)` |  |
| `tool_list(self, category, tag, limit)` | 工具：列出 Skills |
| `tool_view(self, skill_id, include_body)` | 工具：查看单个 Skill |
| `tool_create(self, name, body, category, description, tags, triggers)` | 工具：创建新 Skill（自动 patch 优先） |
| `tool_patch(self, skill_id, body, description, tags, triggers, name, category)` | 工具：增量更新 Skill（优先于 create） |
| `tool_delete(self, skill_id)` | 工具：删除 Skill |
| `tool_search(self, query, category, tags, limit)` | 工具：全文搜索 Skills |

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

### `src/agents/transparency.py`

#### 类

##### `TraceEventType`

Trace 事件类型

**继承**: str, Enum

##### `TraceEvent`

Trace 单条事件

| 方法 | 说明 |
|------|------|
| `to_dict(self)` |  |

##### `AgentTrace`

单个 Agent 的完整执行轨迹

| 方法 | 说明 |
|------|------|
| `start(self)` | 开始追踪 |
| `end(self, status, output_summary, error)` | 结束追踪 |
| `log(self, event_type, description, details, output_preview)` | 记录任意事件 |
| `log_read(self, file_path, lines)` | 记录读取文件 |
| `log_write(self, file_path, lines)` | 记录写入文件 |
| `log_api(self, model, tokens, duration_ms)` | 记录 API 调用 |
| `log_command(self, command, exit_code)` | 记录命令执行 |
| `log_error(self, error_msg)` | 记录错误 |
| `to_dict(self)` |  |
| `to_jsonl_line(self)` |  |

##### `TraceStore`

Trace 存储管理器

| 方法 | 说明 |
|------|------|
| `get_instance(cls)` |  |
| `save(self, trace)` | 保存 trace 到文件 |
| `list_sessions(self)` | 列出所有 session |
| `list_traces(self, session_id)` | 列出某个 session 下的所有 trace |
| `get_trace(self, session_id, agent_name)` | 获取指定 agent 的最新 trace |
| `get_latest_session(self)` | 获取最新 session ID |
| `get_all_agents_in_session(self, session_id)` | 获取某个 session 下所有 agent 名 |

##### `TraceContext`

与某个 Agent 执行绑定的 trace 上下文

| 方法 | 说明 |
|------|------|
| `start(self)` |  |
| `stop(self, status, output_summary, error)` |  |
| `log(self, event_type, description, details)` |  |
| `log_read(self, path, lines)` |  |
| `log_write(self, path, lines)` |  |
| `log_api(self, model, tokens, duration_ms)` |  |
| `log_command(self, command, exit_code)` |  |
| `log_error(self, msg)` |  |

#### 函数

##### `get_trace_context(agent_name)`

##### `set_trace_context(agent_name, ctx)`

##### `remove_trace_context(agent_name)`

### `src/agents/uml.py`

UML Agent - 架构图与可视化智能体

职责：
1. 架构图生成（Mermaid / PlantUML）
2. 类图、时序图、用例图
3. 流程图与数据流图
4. 架构决策记录（ADR）

模型层级：LOW（快速）

#### 类

##### `UMLAgent`

架构图与可视化智能体

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

### `src/agents/vision.py`

#### 类

##### `VisionAgent`

视觉分析与 UI 代码生成 Agent

**继承**: BaseAgent

| 方法 | 说明 |
|------|------|
| `system_prompt(self)` |  |

#### 函数

##### `_load_image_meta(image_path)`

提取图片元信息（宽高、尺寸），无需 Pillow 也可工作。

##### `_extract_code_blocks(text)`

从文本中提取代码块。

##### `_default_filename(language)`

根据语言返回默认文件名。

##### `_infer_output_dir(context)`

推断输出目录。

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

### `src/api/server_api.py`

#### 类

##### `TaskStatus`

**继承**: str, Enum

##### `TaskRecord`

##### `TaskStore`

内存 + JSON 文件持久化的任务存储

##### `AuthContext`

认证上下文

| 方法 | 说明 |
|------|------|
| `hash_key(key)` | 哈希 API 密钥 |
| `verify(self, provided_key)` | 验证提供的 API 密钥 |

##### `RunRequest`

**继承**: BaseModel

##### `TaskResponse`

**继承**: BaseModel

#### 函数

##### `get_auth(x_api_key, auth_ctx)`

FastAPI 依赖：验证 API Key

##### `create_app(api_key, store)`

创建 FastAPI 应用

### `src/capabilities/package.py`

#### 类

##### `CapabilityPackage`

能力包数据结构

| 方法 | 说明 |
|------|------|
| `save(self, path)` | 保存能力包到 JSON 文件 |
| `load(cls, path)` | 从 JSON 文件加载能力包 |
| `to_dict(self)` | 转换为字典 |
| `from_dict(cls, data)` | 从字典创建 |
| `validate(self)` | 验证能力包完整性 |

##### `CapabilityPackageManager`

能力包管理器

| 方法 | 说明 |
|------|------|
| `list_packages(self)` | 列出所有本地能力包 |
| `get_package(self, name)` | 获取指定名称的能力包 |
| `save_package(self, package)` | 保存能力包 |
| `delete_package(self, name)` | 删除能力包 |
| `export_from_config(self, name, version, description, author, tags, agents, model_config, tools, prompts, readme, examples)` | 从当前配置导出能力包 |
| `apply_package(self, name, target_config)` | 应用能力包配置 |

#### 函数

##### `get_manager()`

获取默认的能力包管理器

### `src/capsule/capsule.py`

Capsule - 完整能力包结构

由 Gene（元数据）+ manifest（配置）+ dependencies + checksum 组成。

#### 类

##### `Capsule`

GEP Capsule — 完整能力包

| 方法 | 说明 |
|------|------|
| `compute_checksum(self)` | 基于 gene + manifest + dependencies 计算 SHA256 |
| `verify_checksum(self)` |  |
| `to_dict(self)` |  |
| `to_json(self)` |  |
| `from_dict(cls, data)` |  |
| `from_json(cls, text)` |  |
| `from_omcp(cls, data, file_name)` | 从旧 .omcp 格式升级为 Capsule。 |
| `save(self, path)` |  |
| `load(cls, path)` |  |

#### 函数

##### `_sha256_hex(data)`

##### `_infer_category(data)`

从 .omcp 内容推断能力分类

### `src/capsule/gene.py`

#### 类

##### `Gene`

能力元数据（GEP Gene）

| 方法 | 说明 |
|------|------|
| `to_dict(self)` |  |
| `to_json(self)` |  |
| `from_dict(cls, data)` |  |
| `validate(self)` |  |

### `src/capsule/registry.py`

#### 类

##### `GEPRegistry`

GEP 能力注册表

| 方法 | 说明 |
|------|------|
| `register(self, capsule)` | 注册一个 Capsule，返回 Gene ID。 |
| `discover(self, query)` | 按关键词发现能力。 |
| `resolve(self, gene_id)` | 根据 Gene ID 获取 Capsule，不存在返回 None |
| `export_event(self, gene_id)` | 导出 GEP Event 格式。 |
| `list_all(self)` | 列出所有已注册的 Gene |
| `unregister(self, gene_id)` | 移除注册，返回是否成功 |
| `count(self)` |  |

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

##### `run(task, project_path, model, workflow, dry_run, notify, no_checkpoint, cross_validate)`

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

##### `quest_pause(quest_id, project_path)`

⏸️ 暂停 Quest（在当前步骤完成后暂停）

##### `quest_resume(quest_id, project_path)`

▶️ 恢复已暂停的 Quest（从断点继续）

##### `quest_notify(quest_id, project_path, dingtalk_webhook, dingtalk_secret, telegram_bot_token, telegram_chat_id, discord_webhook, slack_webhook, teams_webhook, feishu_webhook, wecom_webhook, pushplus_token)`

🔔 订阅 Quest 通知（桌面 + 多种 Webhook 渠道）

##### `quest_wait(quest_id, project_path, timeout)`

⏳ 阻塞等待 Quest 完成并展示验收结果

##### `_show_acceptance_report(quest, console)`

展示 Quest 验收报告

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

##### `_resolve_default_model(config)`

解析默认模型：环境变量 > config.json > 第一个有 api_key 的模型 > deepseek

##### `_check_env()`

检查当前默认模型的 API Key 是否就绪（读 config.json），返回 True 表示就绪

##### `_load_config()`

从 ~/.omc/config.json 读取配置

##### `_display_result(result)`

显示工作流结果

##### `_display_cross_validation_result(result)`

显示交叉验证结果

##### `config(action, key, value)`

⚙️ 管理配置

##### `_mask_secret(value)`

脱敏显示密钥

##### `_status_color(status)`

给状态上色

### `src/commands/cli.py`

#### 函数

##### `main(ctx, version)`

Oh My Coder CLI 主入口函数。

##### `_print_version()`

打印版本信息

##### `agents()`

列出所有可用 Agent

##### `status()`

查看系统状态

##### `_mask_secret(value)`

脱敏显示密钥

### `src/commands/cli_agent.py`

#### 函数

##### `list_agents(monorepo)`

列出所有可用 Agent

##### `show_agent(name, evolution)`

显示 Agent 详细信息

##### `export_agent(name, output, include_evolution, include_patterns)`

导出 Agent 配置为 JSON

##### `import_agent(source, name)`

从文件或 URL 导入 Agent 配置

##### `evolve_agent(name, trigger)`

手动触发 Agent 自进化

##### `agent_stats(name)`

显示 Agent 进化统计

##### `list_decisions(category, limit)`

列出历史决策记录

##### `retrieve_decision(problem, limit)`

检索历史决策，避免重复踩坑

##### `record_decision(title, problem, solution, category, result, outcome, reusable_for)`

记录重要决策

##### `decision_stats()`

显示决策记忆统计

##### `agent_health(show_logs)`

显示所有 Agent 的健康状态（读取 .omc/state/health/ 目录）

##### `save_agent(name, model, description, output)`

保存 Agent 配置到 ~/.oh-my-coder/agents/<name>/

##### `restore_agent(name, show_history)`

从 ~/.oh-my-coder/agents/<name>/ 恢复 Agent 状态

##### `export_agent_state(name, output, include_history, max_history)`

导出 Agent 为单个 JSON 文件（可分享）

##### `import_agent_state(source, new_name, merge_history)`

从 JSON 文件导入 Agent 配置

##### `list_saved_agents()`

列出所有已保存的 Agent

##### `delete_saved_agent(name, force)`

删除已保存的 Agent 状态

### `src/commands/cli_checkpoint.py`

#### 函数

##### `list(task_id, project_path, limit)`

列出所有 Checkpoint

##### `restore(checkpoint_id, project_path, yes)`

回滚到指定 Checkpoint（恢复前自动备份当前状态）

##### `diff(checkpoint_id, project_path)`

查看 Checkpoint 与当前工作区的差异

##### `delete(checkpoint_id, project_path, yes)`

删除指定 Checkpoint

##### `info(checkpoint_id, project_path)`

查看 Checkpoint 详情

##### `stats(project_path)`

查看 Checkpoint 统计

### `src/commands/cli_clean.py`

#### 函数

##### `clean(path, fix, strategy, output, verbose)`

扫描并清理项目中的冗余代码

##### `_display_report(report, verbose)`

显示清理报告

### `src/commands/cli_commands.py`

#### 类

##### `Command`

命令定义

| 方法 | 说明 |
|------|------|
| `description(self)` |  |
| `usage(self)` |  |
| `render_usage(self, args)` | 渲染命令脚本，支持变量替换 |

#### 函数

##### `load_commands()`

加载所有命令

##### `_create_example_commands()`

创建示例命令

##### `run(name, args, dry_run)`

##### `list_commands()`

列出所有可用命令

##### `create_command(name, description)`

创建新命令

##### `edit_command(name)`

编辑命令

### `src/commands/cli_config.py`

配置管理命令

#### 函数

##### `show(model)`

查看当前配置

##### `list()`

列出所有配置项

##### `set(key, value, model)`

设置配置项

##### `models()`

列出已配置的模型

### `src/commands/cli_config_ext.py`

#### 函数

##### `load_config(file, verbose)`

加载 Agent 配置文件

##### `validate_config(file)`

验证 Agent 配置文件合法性

##### `list_configs(dir)`

列出本地 Agent 配置文件

##### `create_from_config(file, output)`

从配置创建 Agent（生成配置快照）

### `src/commands/cli_cost.py`

#### 函数

##### `_cost_ensure_config_dir()`

##### `_cost_load_prices()`

加载模型价格配置（用户自定义优先级更高）

##### `_cost_save_prices(prices)`

##### `_cost_load_usage_data()`

加载使用记录

##### `_cost_record_usage(model, prompt_tokens, completion_tokens)`

记录一次 API 调用（由 Router/Orchestrator 调用）

##### `_cost_calculate_cost(model, prompt_tokens, completion_tokens)`

计算单次调用成本（元）

##### `_cost_format_cost(cost)`

##### `_cost_format_datetime(iso_str)`

##### `suggest(task, files, list_models, prefer_local)`

Recommend optimal model based on task complexity

##### `report(days)`

Show token usage summary (month/week/today)

##### `model_breakdown(days)`

Show usage and cost grouped by model

##### `history(limit, model)`

显示最近 API 调用历史

##### `prices(edit, reset)`

查看或编辑模型价格配置

##### `export(output)`

导出原始使用记录为 JSON

##### `record_usage(model, prompt_tokens, completion_tokens)`

记录一次 API 调用的 token 用量。

### `src/commands/cli_doc.py`

omc doc 命令 - 文档生成与管理

提供文档生成、验证、同步等功能：
- omc doc generate    # 生成 API 文档
- omc doc check       # 检查文档同步状态
- omc doc serve       # 启动文档本地服务器

#### 函数

##### `generate_docs(output, format)`

自动生成 API 文档

##### `check_docs()`

检查文档同步状态

##### `serve_docs(port)`

启动文档本地预览服务器

##### `generate_index()`

生成文档索引

##### `_collect_cli_commands()`

收集 CLI 命令信息

##### `_collect_web_api()`

收集 Web API 端点信息

##### `_write_markdown_docs(output, cli_info, api_info)`

写入 Markdown 格式文档

##### `_write_json_docs(output, cli_info, api_info)`

写入 JSON 格式文档

### `src/commands/cli_doctor.py`

#### 函数

##### `_check_python_version()`

检查 Python 版本

##### `_check_package(module_name, package_name, version_req)`

检查单个依赖包

##### `_check_config_file()`

检查配置文件

##### `_check_network(url, timeout)`

测试网络连通性

##### `run(verbose, skip_network)`

🏥 运行环境诊断

### `src/commands/cli_gateway.py`

#### 函数

##### `_load_gateway()`

懒加载 Gateway（避免未安装依赖时 import 报错）

##### `status()`

查看网关状态

##### `start(telegram, discord)`

启动网关（会阻塞当前进程，按 Ctrl+C 停止）

##### `stop()`

停止网关（仅在使用后台进程时有意义）

### `src/commands/cli_init.py`

Init CLI - 交互式初始化引导

命令：
- omc init  # 交互式引导新用户完成首次配置

流程：
1. 欢迎界面
2. 选择模型
3. 输入 API Key
4. 设置工作目录
5. 配置验证
6. 完成提示

#### 函数

##### `_ensure_config_dir()`

确保配置目录存在

##### `_load_config()`

加载配置文件

##### `_save_config(config)`

保存配置文件

##### `_mask_api_key(key)`

脱敏显示 API Key

##### `_tier_style(tier)`

根据 tier 返回颜色

##### `init_wizard(ctx)`

交互式初始化引导 - 帮助新用户完成首次配置

##### `reset_config()`

重置配置（删除配置文件）

##### `show_config()`

显示当前配置

### `src/commands/cli_lsp.py`

#### 类

##### `DiagnosticSeverity`

#### 函数

##### `find_lsp_diagnostics(file_path)`

查找 LSP 诊断信息

##### `format_diagnostics_for_ai(diagnostics)`

格式化诊断信息为 AI 可读的格式

##### `check(file, source, format)`

检查代码诊断信息

##### `fix(dry_run, source)`

自动修复代码问题

##### `setup(tool)`

快速设置 LSP 工具

##### `_setup_ruff()`

设置 ruff

##### `_setup_mypy()`

设置 mypy

##### `_setup_eslint()`

设置 ESLint

### `src/commands/cli_mcp.py`

#### 函数

##### `start(workspace)`

启动 MCP Server（stdio 模式）

##### `install(client, project_path, yes)`

生成 MCP 客户端配置文件

##### `list()`

列出所有可用 MCP tools 和 resources

##### `status()`

查看 MCP 连接状态

### `src/commands/cli_migrate.py`

#### 函数

##### `list_sources()`

列出支持的迁移来源

##### `migrate_claude(path, dry_run)`

从 Claude Code 导入配置

##### `migrate_gemini(path, dry_run)`

从 Gemini CLI 导入配置

##### `_parse_claude_config(content)`

解析 CLAUDE.md 内容

### `src/commands/cli_model.py`

#### 函数

##### `local_check_status()`

检查 Ollama 服务状态

##### `local_list_models()`

列出本地可用的模型

##### `local_pull_model(model_name)`

拉取模型到本地

##### `local_run_ollama(model_name, port)`

启动 Ollama 服务（如果未运行）

##### `local_model_info(model_name)`

显示模型详细信息

##### `local_chat_model(model_name, system, temperature, no_stream)`

与本地模型聊天（交互式）

##### `_get_current_model()`

获取当前默认模型

##### `_get_current_api_key(model_id)`

获取当前模型的 API Key（从环境变量推断）

##### `_ensure_shared_dir()`

确保分享目录存在

##### `_list_shared_configs()`

列出所有已分享的配置

##### `_get_author_name()`

获取作者名称（优先环境变量，其次 git config）

##### `_resolve_task(task)`

解析任务类型（支持别名）

##### `_show_all_recommendations()`

显示所有类型的推荐表

##### `_show_task_recommendation(task)`

显示特定任务类型的推荐

##### `_list_yaml_configs()`

扫描所有 YAML 模型配置文件

##### `_validate_model_config(data)`

验证模型配置是否合法

##### `_save_model_config(data)`

保存模型配置到用户目录，返回保存路径

##### `list_models(extended, tier, provider, status, all, beta, json_output, source)`

列出所有可用模型（支持 Catwalk 详细视图）

##### `catwalk(tier, provider, search)`

交互式浏览 Catwalk 模型仓库（交互模式）

##### `import_model(url, name, force)`

从 URL 或本地文件导入 YAML 模型配置

##### `export_model(name, yaml_out, copy)`

导出模型配置（支持 YAML/JSON）

##### `show_current()`

显示当前默认模型

##### `switch_model_cmd(model_name)`

切换默认模型（写入配置文件，无需重启）

##### `sync_models(force, timeout)`

同步检查各厂商最新模型

##### `recommend_model(task)`

模型精选推荐 — 按场景推荐免费模型

##### `share_model(name, provider, base_url, model, description, author, interactive)`

分享模型配置到社区目录

##### `browse_models(provider, author, search, limit)`

浏览社区分享的模型配置

##### `show_shared_model(config_id, export)`

查看模型配置详情

##### `list_shared()`

列出本地分享的所有配置

##### `remove_shared_model(config_id, force)`

删除已分享的配置

##### `main(ctx)`

模型管理 - 查看/切换/分享/推荐.

### `src/commands/cli_monorepo.py`

#### 类

##### `MonorepoInfo`

Monorepo 信息

#### 函数

##### `detect_monorepo(root)`

检测目录是否为 monorepo 根目录

##### `_find_packages(root, repo_type)`

根据 monorepo 类型查找 packages 目录

##### `detect(path)`

检测是否为 monorepo 并显示信息

##### `monorepo_status(path, show_dirty)`

显示所有包的 Git 状态

##### `monorepo_run(script, scope, path, parallel, dry_run)`

在所有/指定包中运行脚本

### `src/commands/cli_multiagent.py`

#### 函数

##### `_agent_status_color(status)`

##### `multiagent_status()`

查看多 Agent 协作状态

##### `multiagent_spawn(role, name, metadata)`

创建子 Agent

##### `multiagent_list()`

列出所有子 Agent

##### `multiagent_dispatch(task, agent_ids, mode)`

分发任务给子 Agent

##### `multiagent_remove(agent_id, force)`

移除子 Agent

##### `multiagent_clear(force)`

清空所有子 Agent

### `src/commands/cli_package_manager.py`

#### 类

##### `Platform`

支持的平台

**继承**: Enum

##### `PackageManager`

包管理器

**继承**: Enum

#### 函数

##### `get_current_platform()`

获取当前平台

##### `get_available_managers()`

获取可用的包管理器

##### `_is_command_available(cmd)`

检查命令是否可用

##### `_run_command(cmd, capture)`

运行命令

##### `install(package, manager, sudo)`

安装包

##### `_select_best_manager(package)`

选择最佳包管理器

##### `_build_install_command(manager, package, sudo)`

构建安装命令

##### `search(query, manager)`

搜索包

##### `_search_with_manager(manager, query)`

使用指定管理器搜索

##### `list_installed(manager)`

列出已安装的包

##### `_list_with_manager(manager)`

列出指定管理器的包

##### `update(package, manager)`

更新包

##### `recommend()`

显示推荐安装的开发工具

##### `check()`

检查可用的包管理器

### `src/commands/cli_plan.py`

#### 函数

##### `_init_router()`

初始化模型路由器

##### `_check_env()`

检查环境配置

##### `plan(task, project_path, model, yes, output)`

Plan Mode - 分析任务并输出改动计划，确认后执行。

##### `_display_plan(plan_data, execution_order, console)`

展示计划

##### `_save_plan(plan_data, execution_order, output, console)`

保存计划到文件

### `src/commands/cli_profile.py`

Profile CLI - omc profile 命令

管理子 Agent 的隔离 profile，解决上下文污染问题。

#### 函数

##### `create_profile(agent_id, name, template)`

创建新的 Agent Profile

##### `list_profiles()`

列出所有 Agent Profiles

##### `show_profile(agent_id)`

查看 Profile 详情

##### `show_context(agent_id)`

查看 Agent 的隔离上下文（用于调试）

##### `add_memory(agent_id, memory)`

向 Profile 添加记忆

##### `add_task(agent_id, task, status)`

记录任务执行历史

##### `delete_profile(agent_id)`

删除 Profile

##### `list_templates()`

列出预定义 Profile 模板

### `src/commands/cli_quality.py`

#### 函数

##### `_check_ruff_installed()`

检查 ruff 是否已安装

##### `_check_black_installed()`

检查 black 是否已安装

##### `_check_mypy_installed()`

检查 mypy 是否已安装

##### `quality_check(path)`

运行 ruff check 检查代码

##### `quality_fix(path)`

运行 ruff check --fix 自动修复代码

##### `quality_type(path)`

运行 mypy 类型检查

##### `quality_all(path)`

先运行 black 格式化，再运行 ruff check，最后运行 mypy 类型检查

##### `main(ctx)`

默认显示帮助

### `src/commands/cli_quest.py`

#### 函数

##### `_print_fatal(msg)`

打印致命错误

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

##### `quest_pause(quest_id, project_path)`

⏸️ 暂停 Quest（在当前步骤完成后暂停）

##### `quest_resume(quest_id, project_path)`

▶️ 恢复已暂停的 Quest（从断点继续）

##### `quest_notify(quest_id, project_path, dingtalk_webhook, dingtalk_secret, telegram_bot_token, telegram_chat_id, discord_webhook, slack_webhook, teams_webhook, feishu_webhook, wecom_webhook, pushplus_token)`

🔔 订阅 Quest 通知（桌面 + 多种 Webhook 渠道）

##### `quest_wait(quest_id, project_path, timeout)`

⏳ 阻塞等待 Quest 完成并展示验收结果

##### `_show_acceptance_report(quest, console)`

展示 Quest 验收报告

### `src/commands/cli_review.py`

#### 函数

##### `_init_router()`

初始化模型路由器

##### `_check_env()`

检查环境配置

##### `_fetch_pr_diff(pr_url)`

抓取 GitHub PR diff

##### `_read_local_diff(diff_file)`

读取本地 diff 文件

##### `_load_system_prompt()`

加载系统提示词

##### `review_pr(pr_url, model, output)`

审查 GitHub PR 内容

##### `review_diff(diff_file, model, output)`

审查本地代码 diff

##### `main(ctx)`

默认显示帮助

### `src/commands/cli_run.py`

#### 函数

##### `run(task, project_path, model, workflow, dry_run, notify, no_checkpoint, simple, cross_validate, use_sourcegraph)`

执行编程任务

##### `explore(project_path)`

探索代码库

##### `wiki(project_path, output)`

生成项目 Wiki 文档

##### `_detect_project_name(project_path)`

检测项目名称

##### `_load_config()`

从 ~/.omc/config.json 读取配置

##### `_resolve_default_model(config)`

解析默认模型：环境变量 > config.json > 第一个有 api_key 的模型 > deepseek

##### `_get_api_key(config, model)`

获取模型对应的 API Key：config.json > 环境变量

##### `_run_simple_task(router, task)`

简单模式：不经过工作流，直接调用模型生成并执行 shell 命令。

##### `_init_router()`

初始化模型路由器，失败时给出友好提示

##### `_print_missing_key_hint(key, reason, url)`

打印缺失 API Key 的友好提示

##### `_print_fatal(msg, hint)`

打印致命错误并退出

##### `_check_env()`

检查当前默认模型的 API Key 是否就绪，返回 True 表示就绪

##### `_display_result(result)`

显示工作流结果

##### `_display_cross_validation_result(result)`

显示交叉验证结果

##### `_status_color(status)`

给状态上色

### `src/commands/cli_search.py`

#### 函数

##### `search_cmd(query, language, repo, limit, output, json_output, code_output, after, before)`

搜索 GitHub/GitLab 等公开代码库

##### `setup_cmd(api_key, install_cli)`

配置 Sourcegraph API Key

##### `status_cmd()`

检查 Sourcegraph 搜索状态

##### `install_cmd()`

安装 src CLI

##### `main(ctx)`

默认显示帮助

### `src/commands/cli_security.py`

#### 函数

##### `security_check(command, config_file)`

预检命令是否安全

##### `security_list()`

列出内置危险命令模式

##### `sandbox_test(path)`

测试沙箱路径限制

##### `security_run(command, timeout)`

在沙箱中安全执行命令

### `src/commands/cli_self_config.py`

#### 函数

##### `parse_config_intent(text)`

解析配置意图

##### `detect_api_key_in_text(text)`

从文本中提取 API Key

##### `config(intent, key, provider, non_interactive)`

自配置命令 - 用自然语言配置一切

##### `list_configs()`

列出当前配置

### `src/commands/cli_server.py`

#### 函数

##### `_find_free_port(port)`

查找可用端口

##### `_is_port_in_use(port)`

##### `start(port, host, api_key, no_auth, no_open, reload)`

启动 Server

##### `stop()`

停止 Server（通过 PID 文件）

##### `status()`

检查 Server 运行状态

##### `logs(lines)`

查看 Server 日志

##### `_load_api_key_from_config()`

从 ~/.omc/.env 读取 API Key

##### `_open_browser(url)`

##### `main(ctx)`

omc server — 启动远程 AI 编程助手 HTTP API

### `src/commands/cli_skill.py`

#### 函数

##### `list_skills(builtin_only, custom_only)`

列出所有可用 Skill

##### `skill_info(name)`

查看 Skill 详细信息

##### `run_skill(name, code, output_file)`

执行指定 Skill

##### `init_custom_skills()`

初始化自定义 Skill 目录

##### `propose_skill(task, steps, reflections)`

从任务中提取 Skill 提议

##### `review_proposals()`

查看待处理的 Skill 提议

##### `accept_skill_proposal(proposal_id)`

接受 Skill 提议

##### `reject_skill_proposal(proposal_id)`

拒绝 Skill 提议

### `src/commands/cli_task.py`

#### 函数

##### `_status_color(status)`

状态颜色映射

##### `_status_emoji(status)`

状态 emoji 映射

##### `task_list(status_filter, limit)`

列出所有任务

##### `task_status(task_id, verbose)`

查看任务详情

##### `task_pause(task_id)`

暂停任务

##### `task_resume(task_id)`

恢复任务

##### `task_delete(task_id, force)`

删除任务

### `src/commands/cli_template.py`

#### 函数

##### `list_templates(category)`

列出可用模板

##### `show_template(name, raw)`

显示模板详情

##### `use_template(name, task, project_path, dry_run)`

使用模板创建工作流

##### `create_template(name, base)`

创建新模板（交互式）

### `src/commands/cli_tui.py`

#### 类

##### `Keys`

##### `State`

TUI 状态机

**继承**: Enum

##### `TUISession`

TUI 会话状态

| 方法 | 说明 |
|------|------|
| `render(self)` | 渲染当前状态 |
| `handle_key(self, key)` | 处理键盘事件，返回是否需要继续 |

#### 函数

##### `start(task, workflow, model)`

启动 TUI 交互界面

##### `list_agents()`

列出所有 Agent

##### `list_workflows()`

列出所有工作流

##### `list_models()`

列出所有可用模型

### `src/commands/cli_usage.py`

#### 函数

##### `_get_count_files()`

延迟导入 count_files 以避免 stats 模块的兼容性问题

##### `stats_command(path, output_json, exclude_dirs, exclude_files, exclude_extensions, max_depth, follow_symlinks, sort_by)`

统计项目文件数量。

##### `_get_store()`

延迟导入 TraceStore

##### `trace_list(session, limit)`

列出最近执行记录

##### `trace_show(agent, session)`

显示某个 Agent 的详细执行过程

##### `trace_agents(session)`

显示当前 session 的所有 Agent

##### `trace_latest()`

显示最新 session

##### `_get_manager(project_path)`

初始化 MemoryManager

##### `memory_tier0(project_path)`

🧠 查看 Tier 0 核心记忆（< 500 token）

##### `memory_tier1(project_path)`

📋 查看 Tier 1 精选记忆（< 2000 token）

##### `memory_summary(project_path)`

📦 查看完整记忆摘要（Tier 2 存档）

##### `memory_stats(project_path)`

📊 查看记忆统计

##### `stats_main(ctx, path, json_output, exclude_dir, exclude_file, exclude_ext, max_depth, follow_symlinks, sort)`

统计项目文件数量

##### `trace_list_cmd(session, limit)`

列出最近执行记录

##### `trace_show_cmd(agent, session)`

显示某个 Agent 的详细执行过程

##### `trace_agents_cmd(session)`

显示当前 session 的所有 Agent

##### `trace_latest_cmd()`

显示最新 session

##### `memory_tier0_cmd(project_path)`

🧠 查看 Tier 0 核心记忆（< 500 token）

##### `memory_tier1_cmd(project_path)`

📋 查看 Tier 1 精选记忆（< 2000 token）

##### `memory_summary_cmd(project_path)`

📦 查看完整记忆摘要（Tier 2 存档）

##### `memory_stats_cmd(project_path)`

📊 查看记忆统计

##### `compact_stats(project_path)`

📊 显示当前会话的压缩统计

##### `compact_sweep(project_path, since_last_user, dry_run)`

🧹 手动触发压缩（sweep）

##### `thought_start(task, agent)`

开始记录思维链

##### `thought_step(chain_id, step_type, description, reasoning, conclusion, confidence)`

添加推理步骤

##### `thought_complete(chain_id, conclusion)`

完成思维链

##### `thought_show(chain_id, format)`

查看思维链

##### `thought_list(agent)`

列出思维链

##### `_get_scanner()`

延迟导入 WorkspaceScanner

##### `_get_browser_awareness()`

延迟导入 BrowserAwareness

##### `context_scan(project_path, depth, json_output)`

扫描当前工作目录，生成文件树结构

##### `context_summary(path, max_lines, project_path)`

生成文件摘要

##### `context_browser(watch, interval)`

获取浏览器当前上下文

##### `context_tree(project_path, depth, filter_ext)`

显示文件树

##### `context_stats(project_path)`

显示项目统计信息

### `src/commands/quickstart.py`

#### 函数

##### `detect_completed_steps()`

检测已完成步骤（自动跳过）

##### `_check_api_key_works(env_key, provider)`

轻量检测 API Key 是否有效（不真正调用，只检查格式和环境）

##### `_step1_select_model()`

交互式选择模型，返回选中的模型信息或 None（跳过）

##### `_step2_config_apikey(model_info)`

配置 API Key，返回是否成功

##### `_set_env_var(key, value)`

设置环境变量（写入 .env + 设置当前进程）

##### `_step3_run_demo(model_info)`

运行示例任务验证配置

##### `_get_wenxin_access_token(api_key)`

获取文心一言 access_token（简化版）

##### `_get_hunyuan_access_token(api_key, secret_key)`

获取腾讯混元 access_token（简化版）

##### `_truncate(s, max_len)`

截断字符串

##### `_show_summary(model_info, steps_completed)`

展示完成总结

##### `main(step, model, force)`

交互式引导 - 3 步完成配置并运行第一个任务

### `src/commands/share.py`

#### 函数

##### `_ensure_dir()`

确保分享目录存在

##### `_generate_share_id()`

生成 8 位简短分享 ID

##### `_share_path(share_id)`

获取分享文件路径

##### `export_session(task_id, history_dir, include_config, tags, expires_hours)`

导出会话为分享记录。

##### `_sanitize_config(config)`

脱敏配置，移除 API Key

##### `import_session(share_id, target_dir)`

通过分享 ID 导入会话。

##### `list_shares()`

列出所有分享

##### `delete_share(share_id)`

删除分享

##### `get_share(share_id)`

获取分享详情

##### `share_create(task_id, tags, no_config, expires)`

导出会话并生成分享链接

##### `share_import(share_id)`

通过分享 ID 导入会话

##### `share_list()`

列出所有分享

##### `share_delete(share_id)`

删除分享

##### `share_show(share_id)`

查看分享详情

### `src/config/agent_config.py`

#### 类

##### `ToolConfig`

工具配置

##### `EnvironmentConfig`

环境配置

##### `PromptTemplate`

Prompt 模板

##### `AgentConfig`

Agent 配置

| 方法 | 说明 |
|------|------|
| `get_system_prompt(self)` | 获取 system prompt |
| `get_prompt_template(self, key)` | 获取指定 key 的 prompt 模板，支持 {{变量}} 替换 |
| `render_template(self, key)` | 渲染 prompt 模板，替换 {{变量}} |
| `to_dict(self)` | 序列化为 dict |
| `from_dict(cls, data)` | 从 dict 反序列化 |
| `validate(self)` | 验证配置合法性，返回错误列表 |

#### 函数

##### `load_config_file(path)`

加载 YAML 或 JSON 格式的 Agent 配置文件

##### `load_config_dir(dir_path)`

加载目录下所有 YAML/JSON 配置文件

##### `validate_config_file(path)`

验证配置文件合法性

##### `list_configs_in_dir(dir_path)`

列出目录下所有配置文件的绝对路径

##### `_load_yaml(raw)`

解析 YAML（使用标准库实现，零依赖）

##### `_parse_value(value)`

解析 YAML 值

### `src/config/workflow_loader.py`

工作流加载器 - 支持 YAML 格式工作流定义与热重载

#### 类

##### `StepConfig`

单个工作流步骤的配置（对应 YAML 中的 step）

| 方法 | 说明 |
|------|------|
| `to_workflow_step(self)` | 转换为 orchestrator.WorkflowStep |

##### `WorkflowConfig`

完整工作流配置（对应 YAML 文件）

| 方法 | 说明 |
|------|------|
| `to_workflow_steps(self)` | 转换为 orchestrator.WorkflowStep 列表 |

##### `WorkflowLoader`

工作流加载器

| 方法 | 说明 |
|------|------|
| `load_workflow(self, name)` | 加载工作流步骤列表。 |
| `list_workflows(self)` | 返回所有工作流名称（含来源） |
| `list_builtins(self)` | 返回内置工作流名称列表 |
| `is_builtin(self, name)` | 判断是否为内置工作流 |
| `parse_yaml_string(self, yaml_str, name)` | 将 YAML 字符串解析为 WorkflowConfig。 |
| `get_workflow_config(self, name)` | 获取完整工作流配置（含 metadata）。 |
| `save_workflow(self, name, config)` | 保存用户工作流到 ~/.omc/workflows/。 |
| `delete_workflow(self, name)` | 删除用户工作流（~/.omc/workflows/<name>.yaml）。 |

### `src/context/browser_context.py`

浏览器上下文感知 - Browser Context Awareness

通过浏览器扩展/API 获取当前标签页上下文，支持：
- 获取当前标签页的标题、URL、内容摘要
- 搜索相关上下文
- 与 AI Agent 集成

注意：此功能需要浏览器扩展或 Playwright/Selenium 支持。
当无可用浏览器时，功能降级为优雅的空实现。

#### 类

##### `BrowserContext`

浏览器上下文

| 方法 | 说明 |
|------|------|
| `to_context_string(self)` | 生成上下文字符串 |

##### `BrowserAwareness`

浏览器感知模块

| 方法 | 说明 |
|------|------|
| `to_context_string(self)` | 生成上下文字符串（同步版本，获取当前标签页） |

### `src/context/workspace_scanner.py`

#### 类

##### `FileNode`

文件树节点

| 方法 | 说明 |
|------|------|
| `to_dict(self)` | 转换为字典（用于 JSON 序列化） |

##### `WorkspaceScanner`

工作目录扫描器

| 方法 | 说明 |
|------|------|
| `scan(self, max_depth)` | 扫描工作目录，返回文件树 |
| `get_file_summary(self, path, max_lines)` | 获取文件摘要（用于上下文） |
| `to_context_string(self, max_depth)` | 生成可用于 Prompt 的上下文字符串 |

### `src/core/chain_of_thought.py`

思维链可视化 — 记录和展示 Agent 推理过程

功能：
1. 捕获 Agent 的思维链（推理步骤、决策依据）
2. 结构化存储推理过程
3. 可视化展示（文本/JSON/HTML）
4. 支持回溯和调试

#### 类

##### `ReasoningStepType`

推理步骤类型

**继承**: Enum

##### `ConfidenceLevel`

置信度级别

**继承**: Enum

##### `ReasoningStep`

推理步骤

| 方法 | 说明 |
|------|------|
| `to_dict(self)` |  |

##### `ChainOfThought`

思维链

| 方法 | 说明 |
|------|------|
| `to_dict(self)` |  |
| `add_step(self, step)` | 添加推理步骤 |
| `complete(self, conclusion)` | 完成思维链 |
| `fail(self, error)` | 标记为失败 |

##### `ChainOfThoughtRecorder`

思维链记录器

| 方法 | 说明 |
|------|------|
| `start_chain(self, task_description, agent_name, metadata)` | 开始记录思维链 |
| `add_step(self, chain_id, step_type, description, reasoning, evidence, conclusion, confidence, parent_step_id)` | 添加推理步骤 |
| `complete_chain(self, chain_id, conclusion)` | 完成思维链 |
| `fail_chain(self, chain_id, error)` | 标记思维链失败 |
| `get_chain(self, chain_id)` | 获取思维链 |
| `list_chains(self, agent_name)` | 列出思维链 |

##### `ChainVisualizer`

思维链可视化

| 方法 | 说明 |
|------|------|
| `to_text(chain)` | 转换为文本格式 |
| `to_html(chain)` | 转换为 HTML 格式 |
| `to_mermaid(chain)` | 转换为 Mermaid 流程图 |

#### 函数

##### `create_recorder()`

创建思维链记录器

##### `visualize_chain(chain, format)`

可视化思维链

### `src/core/checkpoint.py`

#### 类

##### `SnapshotEntry`

快照中的单个文件条目

##### `Checkpoint`

快照元数据

| 方法 | 说明 |
|------|------|
| `to_dict(self)` |  |
| `from_dict(cls, data)` |  |

##### `CheckpointManager`

Checkpoint 管理器

| 方法 | 说明 |
|------|------|
| `create(self, task_id, description, max_files)` | 创建 checkpoint（快照当前工作区） |
| `restore(self, checkpoint_id)` | 恢复 checkpoint（覆盖工作区文件） |
| `diff(self, checkpoint_id)` | 对比 checkpoint 与当前工作区的差异 |
| `delete(self, checkpoint_id)` | 删除 checkpoint |
| `list(self, task_id, limit)` | 列出 checkpoint |
| `get_checkpoint(self, checkpoint_id)` | 获取单个 checkpoint 完整信息 |
| `get_stats(self)` | 获取快照统计 |
| `format_diff(self, diff_result)` | 格式化 diff 结果为可读字符串 |

### `src/core/context_compressor.py`

上下文压缩优化 — 智能压缩静态知识，保留动态推理

核心策略：
1. 识别静态知识（文件内容、文档、配置）→ 压缩为摘要
2. 保留动态推理（思维链、决策过程、错误修复）→ 完整保留
3. 分级压缩：根据消息类型和重要性应用不同压缩策略

#### 类

##### `MessageType`

消息类型分类

**继承**: Enum

##### `CompressionLevel`

压缩级别

**继承**: Enum

##### `CompressionRule`

压缩规则

##### `CompressedMessage`

压缩后的消息

##### `ContextCompressor`

上下文压缩器

| 方法 | 说明 |
|------|------|
| `classify_message(self, role, content)` | 分类消息类型 |
| `compress(self, role, content, tokens_before)` | 压缩单条消息 |
| `compress_session(self, messages, token_counter)` | 压缩整个会话 |

##### `CompressionSummary`

压缩摘要

| 方法 | 说明 |
|------|------|
| `to_dict(self)` |  |

### `src/core/dependency_resolver.py`

依赖解析器 - 从生成的代码中自动检测和安装依赖

#### 类

##### `DependencyInfo`

依赖信息

##### `ResolutionResult`

依赖解析结果

##### `DependencyResolver`

依赖解析器

| 方法 | 说明 |
|------|------|
| `extract_from_code(self, code)` | 从代码字符串中提取依赖 |
| `check_installed(self, package_name)` | 检查包是否已安装 |
| `check_dependencies(self, dependencies)` | 检查依赖是否已安装 |
| `install_missing(self, missing, quiet)` | 安装缺失的依赖 |
| `resolve(self, code, auto_install)` | 解析代码依赖并可选安装 |

#### 函数

##### `get_resolver()`

获取默认解析器

##### `resolve_dependencies(code, auto_install)`

便利函数：解析代码依赖

### `src/core/history.py`

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

### `src/core/local_model_discovery.py`

#### 类

##### `OllamaModelInfo`

单个 Ollama 模型的结构化信息

| 方法 | 说明 |
|------|------|
| `size_gb(self)` | 返回模型大小（GB） |
| `size_mb(self)` | 返回模型大小（MB） |
| `to_dict(self)` | 导出为字典（不含 raw 字段） |

#### 函数

##### `_make_client()`

创建同步 httpx client，复用连接

##### `is_ollama_running(base_url)`

检测 Ollama 服务是否正在运行

##### `discover_ollama_models(base_url)`

发现所有本地已安装的 Ollama 模型

##### `get_model_info(model_name, base_url)`

获取单个模型的详细信息

### `src/core/monorepo.py`

#### 类

##### `MonorepoInfo`

Monorepo workspace information.

| 方法 | 说明 |
|------|------|
| `to_dict(self)` | Serialize to dict. |

##### `SubProject`

A sub-project within a monorepo.

| 方法 | 说明 |
|------|------|
| `to_dict(self)` | Serialize to dict. |

#### 函数

##### `detect_monorepo(root)`

Detect if directory is a monorepo root.

##### `find_monorepo_root(start)`

Find monorepo root by walking up from start directory.

##### `_find_packages(root, repo_type)`

Find all packages in a monorepo.

##### `_parse_pnpm_workspace(root)`

Parse pnpm-workspace.yaml for package paths.

##### `_parse_lerna_packages(root)`

Parse lerna.json for package paths.

##### `_parse_nx_workspace(root)`

Parse nx workspace for projects.

##### `_parse_rush_packages(root)`

Parse rush.json for package paths.

##### `_find_common_package_dirs(root)`

Find packages in common directory names.

##### `detect_language(project_path)`

Detect programming language of a project.

##### `detect_framework(project_path)`

Detect framework of a project.

##### `list_subprojects(monorepo_info)`

List all sub-projects in a monorepo.

##### `_has_agent_config(project_path)`

Check if project has omc agent configuration.

##### `get_monorepo_context(project_path)`

Get monorepo context for agent initialization.

### `src/core/ollama_health.py`

#### 类

##### `OllamaHealthStatus`

Ollama 健康检查结果

| 方法 | 说明 |
|------|------|
| `to_dict(self)` | 导出为字典，便于序列化或日志记录 |

##### `OllamaHealthChecker`

Ollama 服务健康检查器

| 方法 | 说明 |
|------|------|
| `check_ollama(self)` | 综合健康检查 |
| `check_model_available(self, model_name)` | 检查特定模型是否已下载可用 |
| `get_ollama_status(self)` | 获取 Ollama 状态字典 |
| `clear_cache(self)` | 手动清除缓存，强制下次检查时重新请求 |
| `close(self)` | 关闭内部 httpx client |

### `src/core/orchestrator.py`

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
| `skill_manager(self)` | 懒加载 SkillManager |
| `checkpoint_manager(self)` | 懒加载 CheckpointManager |
| `memory_manager(self)` | 懒加载 MemoryManager（分层有限记忆） |
| `health_checker(self)` | 懒加载 HealthChecker |
| `inject_memory_context(self)` | 获取 Tier 0 核心记忆注入文本。 |
| `get_skill_inventory(self, max_tokens)` | 获取所有 Skill 的名字+一句话描述。 |
| `inject_skill_context(self, agent_class, max_tokens)` | 为指定 Agent 生成 Skill 上下文注入文本。 |
| `register_agent(self, agent)` | 注册 Agent 实例 |
| `get_agent(self, name)` | 获取 Agent 实例，**override_attrs 允许覆写实例属性（如 use_sourcegraph） |
| `load_workflow_result(self, workflow_id)` | 加载工作流结果 |
| `list_active_workflows(self)` | 列出活跃的工作流 |
| `get_workflow_status(self, workflow_id)` | 获取工作流状态 |
| `get_current_state(self)` | 获取当前所有 Agent 的协作状态 |

#### 函数

##### `_get_trace_context_cls()`

##### `_detect_workflow_for_autopilot(task)`

根据任务描述自动识别应使用的工作流

### `src/core/profile_manager.py`

Profile 隔离 — 子 Agent 上下文隔离管理

解决代可行等子 agent 的上下文污染问题：
- 每个子 agent 有独立的 profile（记忆/技能/偏好）
- 主 session 和子 session 上下文隔离
- 子 agent 只能访问自己的 profile，不能读写主 session 记忆

#### 类

##### `AgentProfile`

Agent Profile — 隔离的上下文容器

##### `ProfileManager`

Profile 管理器

| 方法 | 说明 |
|------|------|
| `create_profile(self, agent_id, agent_name, parent_profile)` | 创建新的 agent profile |
| `get_profile(self, agent_id)` | 获取 agent profile |
| `update_profile(self, profile)` | 更新 profile |
| `add_memory(self, agent_id, memory)` | 向 profile 添加记忆（隔离存储） |
| `add_task(self, agent_id, task, status)` | 记录任务执行历史 |
| `get_context_for_agent(self, agent_id)` | 获取 agent 的隔离上下文（用于传递给子 agent） |
| `list_profiles(self)` | 列出所有 profiles |
| `delete_profile(self, agent_id)` | 删除 profile |

#### 函数

##### `create_predefined_profile(agent_type)`

创建预定义 profile

##### `get_profile_summary(agent_id)`

获取 profile 摘要（用于调试）

### `src/core/router.py`

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

##### `RateLimitError`

429 限流错误，不重试

**继承**: Exception

##### `NoModelAvailableError`

没有可用模型

**继承**: Exception

### `src/core/skill_extractor.py`

Skill 沉淀闭环 — 从任务执行中提取可复用的 Skill

流程：任务完成 → 反思 → 生成 Skill 提议 → 用户确认 → 保存

#### 类

##### `SkillProposal`

Skill 提议

#### 函数

##### `extract_skill_from_task(task_description, execution_steps, reflections)`

从任务执行中提取 Skill 提议

##### `save_proposal(proposal)`

保存 Skill 提议到文件

##### `list_proposals()`

列出所有待处理的 Skill 提议

##### `accept_proposal(proposal_id)`

接受 Skill 提议，生成 SKILL.md 文件

##### `reject_proposal(proposal_id)`

拒绝 Skill 提议

##### `_is_worth_extracting(task_description, execution_steps, reflections)`

判断任务是否值得提取为 Skill

##### `_generate_title(task_description)`

生成 Skill 标题

##### `_generate_trigger(task_description)`

生成触发条件

##### `_generate_steps(execution_steps, reflections)`

生成标准化步骤

##### `_generalize_step(step)`

将具体步骤泛化

##### `_generate_description(title, steps)`

生成 Skill 描述

##### `_find_proposal(proposal_id)`

查找指定提议

##### `_generate_skill_md(proposal)`

生成 SKILL.md 内容

### `src/core/summary.py`

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

### `src/gateway/base.py`

#### 类

##### `Platform`

**继承**: Enum

##### `IncomingMessage`

统一收件消息格式

##### `OutgoingMessage`

统一发件消息格式

##### `PlatformHandler`

平台处理器基类。

**继承**: ABC

| 方法 | 说明 |
|------|------|
| `is_started(self)` |  |

##### `NoopHandler`

空实现 Handler（平台未配置时使用）。

**继承**: PlatformHandler

### `src/gateway/gateway.py`

#### 类

##### `Gateway`

多平台消息网关

| 方法 | 说明 |
|------|------|
| `on_platform_message(self, message)` | 收到各平台消息时的回调。 |
| `status(self)` | 返回网关状态 |
| `get_handler(self, platform)` |  |

### `src/gateway/platforms/base.py`

#### 类

##### `Platform`

**继承**: Enum

##### `IncomingMessage`

统一收件消息格式

##### `OutgoingMessage`

统一发件消息格式

##### `PlatformHandler`

平台处理器基类。

**继承**: ABC

| 方法 | 说明 |
|------|------|
| `is_started(self)` |  |

##### `NoopHandler`

空实现 Handler（平台未配置时使用）。

**继承**: PlatformHandler

### `src/gateway/platforms/dingtalk.py`

#### 类

##### `DingTalkHandler`

钉钉企业内部应用处理器

**继承**: PlatformHandler

#### 函数

##### `check_dingtalk_dependencies()`

### `src/gateway/platforms/discord.py`

#### 类

##### `DiscordHandler`

Discord Bot 处理器

**继承**: PlatformHandler

#### 函数

##### `_get_discord_client()`

延迟导入 discord.Client，避免模块级依赖

##### `_get_intents()`

##### `check_discord_dependencies()`

检查 Discord 依赖是否满足

### `src/gateway/platforms/feishu.py`

#### 类

##### `FeishuHandler`

飞书自建应用处理器

**继承**: PlatformHandler

#### 函数

##### `check_feishu_dependencies()`

检查飞书依赖是否满足

### `src/gateway/platforms/slack.py`

#### 类

##### `SlackHandler`

Slack Bot 处理器

**继承**: PlatformHandler

#### 函数

##### `check_slack_dependencies()`

### `src/gateway/platforms/telegram.py`

#### 类

##### `TelegramHandler`

Telegram Bot 处理器

**继承**: PlatformHandler

#### 函数

##### `check_telegram_dependencies()`

检查 Telegram 依赖是否满足

### `src/gateway/platforms/wecom.py`

#### 类

##### `WeComHandler`

企业微信自建应用处理器

**继承**: PlatformHandler

#### 函数

##### `check_wecom_dependencies()`

### `src/gateway/platforms/whatsapp.py`

#### 类

##### `WhatsAppHandler`

WhatsApp Business Cloud API 处理器

**继承**: PlatformHandler

#### 函数

##### `check_whatsapp_dependencies()`

检查 WhatsApp 依赖是否满足

### `src/integrations/sourcegraph.py`

Sourcegraph 集成模块 - 公开 API 客户端

使用 Sourcegraph 公开 streaming API，无需 API Key。
支持代码搜索、文件获取、仓库搜索。

API 文档: https://sourcegraph.com/docs/api

#### 类

##### `SearchMatch`

单个搜索结果

| 方法 | 说明 |
|------|------|
| `to_dict(self)` |  |

##### `FileContent`

文件内容结果

| 方法 | 说明 |
|------|------|
| `to_dict(self)` |  |

##### `RepoInfo`

仓库信息

| 方法 | 说明 |
|------|------|
| `to_dict(self)` |  |

##### `SearchResult`

搜索结果

| 方法 | 说明 |
|------|------|
| `to_dict(self)` |  |

##### `SourcegraphClient`

Sourcegraph 公开 API 客户端

| 方法 | 说明 |
|------|------|
| `search(self, query, repo_filter, lang, limit, use_cache)` | 搜索代码 |
| `get_file(self, repo, path, use_cache)` | 获取文件内容 |
| `list_repos(self, query, limit, use_cache)` | 搜索仓库 |
| `close(self)` | 关闭客户端 |

#### 函数

##### `search(query, repo, lang, limit)`

快捷搜索函数

##### `get_file(repo, path)`

快捷获取文件内容

##### `list_repos(query, limit)`

快捷搜索仓库

### `src/main.py`

FastAPI 主入口

### `src/mcp/resources.py`

#### 函数

##### `set_workspace(workspace)`

##### `get_workspace()`

##### `_generate_summary(workspace)`

生成工作区摘要

##### `_generate_structure(workspace, depth)`

生成项目目录结构

##### `_generate_files(workspace)`

生成关键文件内容

##### `_project_stats(workspace)`

统计项目信息

##### `get_mcp_resources()`

获取所有 MCP resources（dict 格式）

### `src/mcp/server.py`

#### 类

##### `McpServer`

MCP Server（手动 stdio 实现，Python 3.9 兼容）

| 方法 | 说明 |
|------|------|
| `run(self)` | 启动 stdio 主循环 |

#### 函数

##### `main()`

CLI 入口：python -m src.mcp.server

### `src/mcp/tools.py`

#### 函数

##### `set_workspace(workspace)`

设置工作区路径（MCPServer 启动时调用）

##### `get_workspace()`

获取工作区路径

##### `_resolve_path(path)`

解析路径：相对路径 → 工作区绝对路径

##### `_code_review_handler(args)`

omc_code_review — 执行代码审查

##### `_debug_handler(args)`

omc_debug — 自动定位并修复 Bug

##### `_test_handler(args)`

omc_test — 为代码生成测试用例

##### `_refactor_handler(args)`

omc_refactor — 重构代码改善结构和性能

##### `_security_handler(args)`

omc_security_review — 安全审查

##### `_vision_handler(args)`

omc_vision — 视觉分析（截图 / UI 代码生成）

##### `_explore_handler(args)`

omc_explore — 项目探索

##### `_plan_handler(args)`

omc_plan — 任务规划和拆分

##### `get_mcp_tools()`

获取所有 MCP tools（dict 格式，兼容 Python 3.9）

##### `get_tool_handler(name)`

根据工具名获取处理器

### `src/memory/auto_compact.py`

Auto Compact - 上下文自动压缩


当会话 token 接近模型上下文窗口限制时，自动压缩早期消息。
参考 OpenCode 的 95% 阈值策略，但使用 95%。

#### 类

##### `CompactResult`

压缩结果

| 方法 | 说明 |
|------|------|
| `tokens_saved(self)` |  |

##### `AutoCompact`

自动上下文压缩器

| 方法 | 说明 |
|------|------|
| `check_and_compact(self, session, provider, model, force, since_last_user)` | 检查并执行压缩 |

### `src/memory/learnings.py`

#### 类

##### `LearningEntry`

学习条目

| 方法 | 说明 |
|------|------|
| `to_dict(self)` |  |
| `from_dict(cls, data)` |  |

##### `LearningsMemory`

学习记忆管理器

| 方法 | 说明 |
|------|------|
| `add(self, title, content, category, tags, context)` | 添加学习条目 |
| `search(self, query, category)` | 搜索学习条目 |
| `get_by_category(self, category)` | 按类别获取 |
| `get_recent(self, limit)` | 获取最近添加的 |
| `delete(self, entry_id)` | 删除条目 |

### `src/memory/long_term.py`

#### 类

##### `ProjectPreference`

项目偏好

| 方法 | 说明 |
|------|------|
| `to_dict(self)` |  |
| `from_dict(cls, data)` |  |

##### `UserPreference`

用户全局偏好

| 方法 | 说明 |
|------|------|
| `to_dict(self)` |  |
| `from_dict(cls, data)` |  |

##### `LongTermMemory`

长期记忆管理器

| 方法 | 说明 |
|------|------|
| `get_user_prefs(self)` | 获取用户偏好 |
| `update_user_prefs(self)` | 更新用户偏好 |
| `get_project_prefs(self, project_path)` | 获取项目偏好 |
| `update_project_prefs(self, project_path)` | 更新项目偏好 |
| `add_recent_project(self, project_path)` | 添加最近项目 |
| `get_recent_projects(self, limit)` | 获取最近项目 |

### `src/memory/manager.py`

#### 类

##### `MemoryConfig`

记忆配置

##### `MemoryManager`

统一记忆管理器

| 方法 | 说明 |
|------|------|
| `compact_stats(self)` | 返回当前会话的压缩统计（持久化） |
| `record_compact(self, result)` | 记录一次压缩事件到持久化存储 |
| `count_tokens(self, text)` | 计算 token 数 |
| `auto_compact_check(self, session, provider, model, force, since_last_user)` | 检查并执行自动压缩 |
| `get_latest_session(self)` | 获取最新活跃的会话 |
| `save_session(self, session)` | 保存会话 |
| `from_project(cls, project_path)` | 从项目路径创建 |
| `from_home(cls)` | 从用户 home 目录创建（全局记忆） |
| `create_session(self, project_path, task)` | 创建新会话 |
| `get_current_session(self)` | 获取当前会话 |
| `save_current_session(self)` | 保存当前会话 |
| `get_user_prefs(self)` | 获取用户偏好 |
| `update_user_prefs(self)` | 更新用户偏好 |
| `get_project_prefs(self, project_path)` | 获取项目偏好 |
| `update_project_prefs(self, project_path)` | 更新项目偏好 |
| `add_recent_project(self, project_path)` | 添加最近项目 |
| `get_recent_projects(self, limit)` | 获取最近项目 |
| `add_learning(self, title, content, category, tags, context)` | 添加学习条目 |
| `search_learnings(self, query, category)` | 搜索学习记录 |
| `get_learnings_by_category(self, category)` | 按类别获取学习记录 |
| `get_recent_learnings(self, limit)` | 获取最近学习记录 |
| `recall(self, query)` | 综合召回：搜索所有记忆层 |
| `get_tier0_summary(self)` | 获取 Tier 0 记忆（< 500 token）。 |
| `get_tier1_summary(self, max_tokens)` | 获取 Tier 1 记忆（< 2000 token）。 |
| `get_tier2_archive(self)` | 获取 Tier 2 完整存档（无 token 限制）。 |
| `get_memory_stats(self)` | 获取记忆统计信息 |

### `src/memory/short_term.py`

#### 类

##### `Message`

单条消息

##### `SessionContext`

会话上下文

| 方法 | 说明 |
|------|------|
| `add_message(self, role, content, metadata)` | 添加消息 |
| `get_recent_messages(self, limit)` | 获取最近 N 条消息 |
| `to_dict(self)` | 序列化 |
| `from_dict(cls, data)` | 反序列化 |

##### `ShortTermMemory`

短期记忆管理器

| 方法 | 说明 |
|------|------|
| `create_session(self, project_path, task)` | 创建新会话 |
| `get_current_session(self)` | 获取当前会话 |
| `set_current_session(self, session)` | 设置当前会话 |
| `load_session(self, session_id)` | 加载已有会话 |
| `save_session(self, session)` | 保存会话到临时文件 |
| `compress_if_needed(self, session)` | 当消息过多时压缩，返回保留的消息 |
| `list_sessions(self)` | 列出所有会话（按最后活跃时间倒序） |
| `get_latest_session(self)` | 获取最新活跃的会话 |
| `clear_expired(self, max_age_hours)` | 清理过期会话（超过 max_age_hours） |

### `src/memory/skill_manager.py`

#### 类

##### `SkillManager`

Skill 文件管理器

| 方法 | 说明 |
|------|------|
| `rebuild_index(self)` | 扫描所有 SKILL.md 文件，重建 index.json |
| `create(self, name, body, category, tags, triggers, description)` | 创建新的 Skill |
| `patch(self, skill_id, body, description, tags, triggers, name, category)` | 增量更新 Skill（优先于 create） |
| `delete(self, skill_id)` | 删除 Skill 及其目录 |
| `list_skills(self, category, tag, limit)` | 列出 Skills |
| `get_skill(self, skill_id, include_body)` | 获取单个 Skill |
| `search(self, query, category, tags, limit)` | 全文搜索 Skills |
| `get_skill_inventory(self, max_tokens)` | 生成 Tier 0 注入文本：Skill 名字 + 一句话描述。 |
| `evaluate_skill_worthy(tool_call_count, had_error, had_fix, had_user_correction, is_nontrivial_workflow)` | 判断当前执行是否值得沉淀为 Skill |
| `build_skill_from_execution(agent_name, task_description, workflow_name, final_result, key_steps, error_context)` | 从一次执行构建 Skill 草稿 |

### `src/model_discovery.py`

#### 类

##### `ModelDiscovery`

动态模型发现：从各厂商 API 拉取可用模型列表

| 方法 | 说明 |
|------|------|
| `discover_all(self, timeout)` | 并发调用所有支持动态发现的厂商 API |
| `get_cached(self)` | 读取本地缓存 |
| `save_cache(self, data)` | 保存到本地缓存 |
| `compare_with_builtin(self, discovered, builtin_models)` | 对比发现的模型 vs 内置模型 |
| `sync(self, force, timeout)` | 执行同步检查 |

#### 函数

##### `get_discovery_summary(builtin_models, discovery)`

获取发现摘要（用于 omc model list 末尾提示）

### `src/models/baichuan.py`

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

### `src/models/mimo.py`

#### 类

##### `MimoModel`

小米 MiMo 模型适配器

**继承**: BaseModel

| 方法 | 说明 |
|------|------|
| `provider(self)` |  |
| `model_name(self)` |  |

##### `MimoAPIError`

MiMo API 错误

**继承**: Exception

### `src/models/minimax.py`

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

### `src/models/ollama.py`

#### 类

##### `OllamaModel`

Ollama 本地模型适配器

**继承**: BaseModel

| 方法 | 说明 |
|------|------|
| `model_name(self)` | 返回实际使用的模型名称 |
| `is_available(base_url)` | 检查 Ollama 服务是否可用 |
| `list_models(base_url)` | 列出本地可用的 Ollama 模型 |
| `pull_model(model_name, base_url)` | 拉取模型到本地 |

#### 函数

##### `create_ollama_model(model_name, base_url, tier)`

创建 Ollama 模型实例的便捷函数

### `src/models/spark.py`

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

### `src/multiagent/coordinator.py`

#### 类

##### `AgentRole`

Agent 角色

**继承**: Enum

##### `SubAgentStatus`

子 Agent 状态

**继承**: Enum

##### `SubAgent`

子 Agent

| 方法 | 说明 |
|------|------|
| `to_dict(self)` |  |

##### `TaskResult`

任务执行结果

| 方法 | 说明 |
|------|------|
| `to_dict(self)` |  |

##### `CoordinationResult`

协作任务结果

| 方法 | 说明 |
|------|------|
| `to_dict(self)` |  |

##### `MultiAgentCoordinator`

多 Agent 协作调度器

| 方法 | 说明 |
|------|------|
| `set_runner(self, runner)` | 设置 Agent 执行器 |
| `spawn(self, role, name, metadata)` | 创建子 Agent |
| `get_status(self)` | 获取所有 Agent 状态 |
| `get_agent(self, agent_id)` | 获取指定 Agent |
| `remove_agent(self, agent_id)` | 移除 Agent |
| `clear_agents(self)` | 清空所有 Agent |

#### 函数

##### `get_coordinator()`

获取全局协调器实例

### `src/plugins/example_plugin.py`

示例插件

演示如何使用 @register 装饰器创建插件。

#### 类

##### `ExamplePlugin`

示例插件，展示插件系统的基本用法

**继承**: PluginBase

| 方法 | 说明 |
|------|------|
| `metadata(self)` |  |
| `on_load(self)` |  |
| `on_enable(self)` |  |
| `on_disable(self)` |  |
| `on_unload(self)` |  |
| `register_skills(self)` |  |
| `register_hooks(self)` |  |

### `src/plugins/loader.py`

#### 类

##### `PluginLoaderError`

插件加载异常

**继承**: Exception

##### `PluginLoader`

插件加载器

| 方法 | 说明 |
|------|------|
| `discover(self)` | 扫描 plugin_dir 下所有 .py 文件，发现可用插件。 |
| `load(self, name)` | 加载单个插件。 |
| `load_all(self)` | 发现所有插件，按依赖顺序加载。 |
| `enable(self, name)` | 启用插件 |
| `disable(self, name)` | 禁用插件 |
| `unload(self, name)` | 卸载插件。 |

#### 函数

##### `get_loader()`

获取全局插件加载器

### `src/plugins/registry.py`

#### 类

##### `PluginStatus`

插件状态

**继承**: str, Enum

##### `PluginMetadata`

插件元数据

**继承**: BaseModel

##### `Plugin`

插件实例

##### `PluginBase`

插件基类

**继承**: ABC

| 方法 | 说明 |
|------|------|
| `metadata(self)` | 返回插件元数据 |
| `on_load(self)` | 插件加载时调用 |
| `on_enable(self)` | 插件启用时调用 |
| `on_disable(self)` | 插件禁用时调用 |
| `on_unload(self)` | 插件卸载时调用 |
| `register_agents(self)` | 注册 Agent 类 |
| `register_skills(self)` | 注册技能函数 |
| `register_hooks(self)` | 注册钩子函数 |

##### `PluginRegistry`

插件注册表

| 方法 | 说明 |
|------|------|
| `register_plugin(self, plugin_cls)` | 注册一个插件类（不加载，仅记录元信息）。 |
| `unregister(self, name)` | 注销插件。 |
| `get(self, name)` | 获取插件 |
| `list_plugins(self)` | 列出所有插件 |
| `list_by_status(self, status)` | 按状态过滤插件 |
| `get_agent(self, name)` | 获取注册的 Agent 类 |
| `get_skill(self, name)` | 获取注册的技能 |
| `execute_hook(self, name)` | 执行钩子 |

#### 函数

##### `get_registry()`

获取全局插件注册表

##### `reset_registry()`

重置全局插件注册表（用于测试清理）

##### `register(cls)`

类装饰器，将插件类注册到全局注册表。

### `src/quest/executor.py`

#### 类

##### `QuestExecutor`

Quest 后台执行引擎

| 方法 | 说明 |
|------|------|
| `start(self, quest)` | 启动后台执行（仅启动，不会阻塞） |
| `stop(self, quest_id)` | 立即停止（不等完成，直接取消任务） |
| `cancel(self, quest_id)` | 取消 Quest |
| `pause(self, quest_id)` | 暂停 Quest（在当前步骤完成后暂停） |
| `resume(self, quest_id)` | 恢复暂停的 Quest，从断点继续 |
| `is_running(self, quest_id)` | 检查 Quest 是否在运行 |
| `get_breakpoint(self, quest_id)` | 获取暂停时的断点位置 |

### `src/quest/manager.py`

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

### `src/quest/notifications.py`

#### 类

##### `NotificationChannel`

通知渠道基类

| 方法 | 说明 |
|------|------|
| `send(self, title, body, level)` | 发送通知，返回是否成功 |

##### `MacOSNotificationChannel`

macOS 桌面通知（使用 osascript）

**继承**: NotificationChannel

| 方法 | 说明 |
|------|------|
| `send(self, title, body, level)` |  |

##### `WindowsNotificationChannel`

Windows 桌面通知（使用 PowerShell）

**继承**: NotificationChannel

| 方法 | 说明 |
|------|------|
| `send(self, title, body, level)` |  |

##### `DingTalkNotificationChannel`

钉钉自定义机器人 Webhook

**继承**: NotificationChannel

| 方法 | 说明 |
|------|------|
| `send(self, title, body, level)` |  |

##### `TelegramNotificationChannel`

Telegram Bot API 通知

**继承**: NotificationChannel

| 方法 | 说明 |
|------|------|
| `send(self, title, body, level)` |  |

##### `DiscordNotificationChannel`

Discord Webhook 通知

**继承**: NotificationChannel

| 方法 | 说明 |
|------|------|
| `send(self, title, body, level)` |  |

##### `SlackNotificationChannel`

Slack Incoming Webhook 通知

**继承**: NotificationChannel

| 方法 | 说明 |
|------|------|
| `send(self, title, body, level)` |  |

##### `TeamsNotificationChannel`

Microsoft Teams Incoming Webhook 通知

**继承**: NotificationChannel

| 方法 | 说明 |
|------|------|
| `send(self, title, body, level)` |  |

##### `FeishuNotificationChannel`

飞书（Lark）自定义机器人 Webhook 通知

**继承**: NotificationChannel

| 方法 | 说明 |
|------|------|
| `send(self, title, body, level)` |  |

##### `WeComNotificationChannel`

企业微信 Webhook 通知

**继承**: NotificationChannel

| 方法 | 说明 |
|------|------|
| `send(self, title, body, level)` |  |

##### `PushPlusNotificationChannel`

PushPlus 微信公众号推送通知

**继承**: NotificationChannel

| 方法 | 说明 |
|------|------|
| `send(self, title, body, level)` |  |

##### `ConsoleNotificationChannel`

控制台通知（CLI 实时输出）

**继承**: NotificationChannel

| 方法 | 说明 |
|------|------|
| `send(self, title, body, level)` |  |

##### `NotificationConfig`

通知配置

##### `NotificationManager`

Quest 通知管理器

| 方法 | 说明 |
|------|------|
| `send(self, title, body, event, quest_id)` | 发送通知到所有已配置的渠道 |
| `notify_started(self, quest_title, quest_id)` |  |
| `notify_spec_ready(self, quest_title, quest_id)` |  |
| `notify_step_completed(self, step_title, quest_id)` |  |
| `notify_step_failed(self, step_title, error, quest_id)` |  |
| `notify_completed(self, quest_title, summary, quest_id)` |  |
| `notify_failed(self, quest_title, error, quest_id)` |  |
| `notify_waiting_input(self, quest_title, message, quest_id)` |  |
| `notify_paused(self, quest_title, quest_id)` |  |
| `notify_resumed(self, quest_title, quest_id)` |  |

#### 函数

##### `_escape_shell(text)`

转义 shell 特殊字符

##### `create_notification_manager(desktop, dingtalk_webhook, dingtalk_secret)`

创建通知管理器（兼容旧 API）

### `src/quest/spec_generator.py`

#### 类

##### `SpecGenerator`

SPEC 文档生成器

### `src/quest/store.py`

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

### `src/sandbox/dangerous_command_blocker.py`

#### 类

##### `RiskLevel`

风险等级

**继承**: Enum

##### `BlockReason`

拦截原因

##### `BlockedCommandError`

被拦截的命令异常

**继承**: Exception

##### `DangerousCommandBlocker`

危险命令拦截器

| 方法 | 说明 |
|------|------|
| `check(self, command)` | 检查命令是否危险 |
| `validate(self, command, strict)` | 验证命令，危险时抛出异常 |

#### 函数

##### `_sanitize_for_error(text)`

对错误消息中的敏感信息进行脱敏处理

##### `is_whitelist_enabled()`

白名单模式是否启用（可通过环境变量禁用）

##### `extract_base_command(command)`

从完整命令中提取 base command（去路径、去 flags 前缀）

##### `get_blocker()`

获取全局拦截器单例

##### `check_command(command)`

快捷函数：检查命令

##### `validate_command(command, strict)`

快捷函数：验证命令

### `src/sandbox/sandbox.py`

#### 类

##### `SandboxConfig`

沙箱配置

##### `Sandbox`

轻量级沙箱（基于路径限制）

| 方法 | 说明 |
|------|------|
| `validate_path(self, path)` | 验证路径是否在允许范围内 |
| `validate_path_with_reason(self, path)` | 验证路径并返回拒绝原因 |
| `validate_paths(self, paths)` | 批量验证路径 |
| `validate_command(self, command)` | 验证命令的路径参数是否在沙箱允许范围内 |
| `run_command(self, cmd, timeout, check_permission, check_dangerous)` | 在沙箱内运行命令 |
| `run_command_with_output_limit(self, cmd, timeout)` | 运行命令并限制输出大小 |
| `get_allowed_dirs(self)` | 获取允许的目录列表 |
| `add_allowed_dir(self, path)` | 添加允许的目录 |

#### 函数

##### `create_sandbox(allowed_dirs, timeout)`

创建沙箱实例

##### `run_sandboxed(cmd, allowed_dirs, timeout)`

便捷函数：在沙箱中运行命令

### `src/security/permissions.py`

#### 类

##### `PermissionRule`

权限规则

| 方法 | 说明 |
|------|------|
| `compile_patterns(self)` | 预编译正则（供内部调用） |
| `from_dict(cls, data)` | 从 dict 创建规则 |
| `to_dict(self)` |  |

##### `CheckResult`

检查结果

| 方法 | 说明 |
|------|------|
| `to_tuple(self)` | 兼容旧接口 |

##### `PermissionGuard`

权限守卫

| 方法 | 说明 |
|------|------|
| `check(self, command)` | 检查命令是否允许执行 |
| `needs_approval(self, command)` | 检查是否需要审批 |
| `validate_rules(self)` | 验证规则合法性 |
| `from_agent_config(cls, config)` | 从 Agent 配置字典创建 PermissionGuard |

#### 函数

##### `check_command(command, rules)`

检查命令权限（便捷函数）

##### `needs_approval(command, rules)`

检查命令是否需要审批（便捷函数）

### `src/skills/registry.py`

#### 类

##### `Skill`

Skill 定义

##### `SkillResult`

Skill 执行结果

| 方法 | 说明 |
|------|------|
| `as_dict(self)` |  |

##### `SkillRegistry`

Skill 注册和管理中心

| 方法 | 说明 |
|------|------|
| `register(self, skill)` | 注册一个 Skill |
| `unregister(self, name)` | 注销一个 Skill |
| `get(self, name)` | 获取 Skill |
| `list_all(self)` | 列出所有 Skill（内置优先） |
| `list_builtin(self)` |  |
| `list_custom(self)` |  |
| `set_custom_dir(self, path)` | 设置自定义 Skill 目录 |
| `load_custom_skills(self)` | 从自定义目录加载 Skill |
| `run(self, name, code, context)` | 执行指定 Skill |
| `run_interactive(self, skill_name, code, context)` | 交互模式执行 Skill（支持 /name 语法） |
| `display_list(self)` | 以表格形式显示所有 Skill |

#### 函数

##### `_review_skill(code, context)`

代码审查 Skill

##### `_test_skill(code, context)`

测试生成 Skill

##### `_doc_skill(code, context)`

文档生成 Skill

##### `get_registry()`

获取全局 Skill 注册表（延迟初始化）

### `src/state/task_state.py`

#### 类

##### `TaskStatus`

任务状态

**继承**: Enum

##### `StepRecord`

步骤记录

| 方法 | 说明 |
|------|------|
| `to_dict(self)` |  |
| `from_dict(cls, data)` |  |

##### `TaskState`

任务状态

| 方法 | 说明 |
|------|------|
| `add_step(self, step, result)` | 记录执行步骤 |
| `pause(self)` | 暂停任务（保存断点） |
| `resume(self)` | 恢复任务 |
| `complete(self, result)` | 标记任务完成 |
| `fail(self, error)` | 标记任务失败 |
| `set_progress(self, progress)` | 设置进度 |
| `to_dict(self)` |  |
| `from_dict(cls, data)` |  |

##### `TaskStore`

任务状态持久化存储

| 方法 | 说明 |
|------|------|
| `get_instance(cls)` | 单例模式 |
| `save(self, state)` | 保存任务状态 |
| `load(self, task_id)` | 加载任务状态 |
| `delete(self, task_id)` | 删除任务 |
| `list_all(self)` | 列出所有任务 |
| `list_by_status(self, status)` | 按状态筛选任务 |

#### 函数

##### `create_task(task_id, metadata)`

创建新任务

##### `get_task(task_id)`

获取任务状态

##### `list_tasks(status)`

列出任务

##### `pause_task(task_id)`

暂停任务

##### `resume_task(task_id)`

恢复任务

##### `delete_task(task_id)`

删除任务

### `src/stats/counter.py`

项目文件统计核心模块。

提供文件遍历、分类统计、排除规则等功能。

#### 函数

##### `_is_excluded(path, exclude_dirs, exclude_files, exclude_extensions)`

检查路径是否应被排除。

##### `_get_file_type(path)`

根据文件扩展名获取文件类型分类。

##### `count_files(root_path, exclude_dirs, exclude_files, exclude_extensions, follow_symlinks, max_depth)`

递归统计项目文件数量。

### `src/stats/models.py`

文件统计结果的数据模型定义。

#### 类

##### `FileStats`

按类型统计的文件信息。

##### `StatsResult`

文件统计结果。

| 方法 | 说明 |
|------|------|
| `to_dict(self)` | 将统计结果转换为字典。 |

### `src/tasks/t1_extract_posts.py`

T1: 提取 Hacker News 首页帖子信息

从提供的网页内容中提取所有30条帖子的结构化信息。

#### 类

##### `Post`

表示 Hacker News 上的一条帖子

#### 函数

##### `extract_posts(raw_content)`

从原始网页内容中提取帖子列表。

##### `print_posts(posts)`

打印帖子列表

### `src/tasks/t2_classify_posts.py`

T2: 对 Hacker News 帖子进行主题分类和热点识别

根据标题和来源，判断每篇帖子的核心领域，并标记热门帖子。

#### 类

##### `ClassificationResult`

分类结果

#### 函数

##### `classify_post(post)`

对单条帖子进行分类。

##### `classify_all_posts(posts)`

对所有帖子进行分类并识别热门话题。

##### `print_classification(result)`

打印分类结果

### `src/tasks/t3_write_summary.py`

T3: 撰写 Hacker News 首页内容总结

基于分类结果，生成一段 200-300 字的自然语言总结。

#### 函数

##### `generate_summary(result)`

根据分类结果生成总结。

##### `main(raw_content)`

主函数：提取、分类、总结。

### `src/team/auth.py`

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

### `src/tools/sourcegraph.py`

#### 类

##### `SearchMatch`

单个搜索结果

| 方法 | 说明 |
|------|------|
| `format_code(self)` | 格式化代码片段 |

##### `SearchResult`

完整搜索结果

| 方法 | 说明 |
|------|------|
| `format_table(self, limit)` | 格式化表格输出 |
| `format_json(self)` | JSON 输出 |
| `format_code(self, limit)` | AI 友好的代码输出 |

#### 函数

##### `_sg_api_search(query)`

通过 Sourcegraph API 搜索

##### `_check_src_cli()`

检查 src CLI 是否可用

##### `_src_cli_search(query)`

通过 src CLI 搜索

##### `search(query, language, repo, limit, after, before, prefer_api)`

搜索代码。自动选择可用后端：

##### `install_src_cli()`

安装 src CLI，返回 (成功, 消息)

##### `setup_api_key(api_key)`

配置 Sourcegraph API Key

##### `check_status()`

检查各后端状态

### `src/utils/api_key_mask.py`

API Key 脱敏工具

提供 API Key 脱敏功能，避免在日志、错误信息中泄露敏感信息。

#### 类

##### `APIKeyMasker`

API Key 脱敏器（类版本，支持自定义规则）。

| 方法 | 说明 |
|------|------|
| `mask(self, text)` | 脱敏文本中的 API Key |
| `mask_dict(self, data, keys_to_mask)` | 脱敏字典中的敏感字段。 |

#### 函数

##### `mask_api_key(text, mask_char)`

对文本中的 API Key 进行脱敏处理。

##### `mask_headers(headers)`

对 HTTP Headers 中的敏感信息进行脱敏。

##### `safe_log(message, logger_func)`

安全的日志记录函数，自动脱敏 API Key。

### `src/utils/notify.py`

#### 函数

##### `send_notification(title, message, subtitle, sound)`

发送系统通知（macOS）。

##### `notify_workflow_complete(workflow, status, steps_completed, execution_time)`

通知工作流完成

##### `notify_quest_update(quest_name, message)`

通知 Quest 更新（用于异步任务）

##### `send_dingtalk_notification(webhook_url, title, message, at_all)`

发送钉钉群机器人通知。

##### `notify_workflow_complete_dingtalk(webhook_url, workflow, status, steps_completed, execution_time, project_path)`

通过钉钉通知工作流完成

##### `notify_quest_update_dingtalk(webhook_url, quest_name, message, status)`

通过钉钉通知 Quest 更新

### `src/utils/performance.py`

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

### `src/utils/safe_executor.py`

#### 类

##### `BlockedError`

命令被安全护栏拦截

**继承**: Exception

#### 函数

##### `_default_retry_if(exc)`

默认重试条件：仅重试网络超时类错误

##### `safe_execute(max_attempts, timeout, base_wait, max_wait)`

安全执行装饰器（异步函数）

##### `safe_execute_sync(max_attempts, timeout, base_wait, max_wait)`

安全执行装饰器（同步函数）

### `src/web/app.py`

#### 类

##### `TaskManager`

管理所有运行中的任务

| 方法 | 说明 |
|------|------|
| `create_task(self, task_desc, model, workflow, project_path)` |  |
| `get_queue(self, task_id)` |  |
| `update_step(self, task_id, step, status, content)` |  |
| `complete_task(self, task_id, result, error)` |  |
| `delete_task(self, task_id)` |  |
| `get_task(self, task_id)` |  |
| `list_tasks(self)` |  |

##### `ChatMessage`

**继承**: BaseModel

##### `ChatRequest`

**继承**: BaseModel

##### `ChatResponse`

**继承**: BaseModel

##### `ChatCompletionRequest`

AI 聊天补全请求

**继承**: BaseModel

##### `ChatCompletionResponse`

AI 聊天补全响应

**继承**: BaseModel

##### `ExecuteRequest`

**继承**: BaseModel

##### `SessionCreate`

**继承**: BaseModel

##### `SessionUpdate`

**继承**: BaseModel

#### 函数

##### `_detect_target_type(target)`

自动检测输入类型：github / url / local

##### `_preprocess_target(target, target_type, task_id)`

预处理分析目标，返回 (project_path, extra_context).

##### `_cleanup_target(project_path, target_type)`

清理临时目录（GitHub clone）

##### `get_orchestrator()`

获取全局 Orchestrator 单例（复用已有 router）

##### `create_router()`

创建模型路由器

##### `create_orchestrator(router)`

创建编排器

##### `json_dumps(obj)`

##### `_detect_workflow(message)`

根据消息内容检测工作流类型

##### `_detect_model(message)`

根据消息内容检测模型偏好

##### `_detect_target_type_from_message(message)`

检测目标类型和路径

##### `_generate_task_summary(task)`

生成任务摘要

##### `_read_settings()`

读取 ~/.omc/config.json，不存在则返回默认值

##### `_mask_key(key)`

对 API Key 做脱敏处理，只显示后 4 位

##### `run()`

启动服务

### `src/web/coverage_api.py`

测试覆盖率 API 模块
提供覆盖率数据收集和报告生成功能

#### 类

##### `FileCoverage`

单个文件的覆盖率数据

##### `CoverageSummary`

覆盖率汇总数据

#### 函数

##### `run_coverage_analysis(project_root)`

运行 pytest-cov 并解析结果

##### `_parse_coverage_json(data, project_root)`

解析 coverage.py 的 JSON 输出

##### `_parse_coverage_from_output(stdout)`

从 pytest-cov 终端输出解析总体覆盖率

##### `get_coverage_badge_color(coverage)`

根据覆盖率返回颜色

##### `format_coverage_report(summary)`

格式化覆盖率报告为 API 响应

### `src/web/dashboard_api.py`

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

##### `_get_real_stats(days)`

从 .omc/state/ 目录读取真实工作流数据统计

##### `_get_real_activity(days)`

从 .omc/state/ 读取最近 days 天的每日工作流活动数据

##### `_build_mock_activity(days)`

兜底：返回空活动数据

##### `_get_mock_stats()`

获取统计数据（现已从真实文件读取，7 天窗口）

##### `_get_mock_activity()`

获取活动数据（现已从真实文件读取，7 天窗口）

##### `_get_mock_agents()`

获取模拟 Agent 状态

##### `_get_mock_recent_tasks()`

获取模拟最近任务

### `src/web/history_api.py`

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

##### `AgentStatusManager`

Agent 状态管理器

| 方法 | 说明 |
|------|------|
| `register_agent(self, name, info)` | 注册 Agent |
| `update_status(self, name, status, task, progress)` | 更新 Agent 状态 |
| `get_agent(self, name)` | 获取 Agent 状态 |
| `get_all(self)` | 获取所有 Agent 状态 |
| `subscribe(self)` | 订阅状态变化 |

### `src/web/local_models_api.py`

#### 类

##### `LocalModelInfo`

本地模型信息

**继承**: BaseModel

##### `OllamaStatus`

Ollama 服务状态

**继承**: BaseModel

#### 函数

##### `_get_model_description(model_name)`

获取模型描述

### `src/web/share_api.py`

#### 类

##### `ShareCreateRequest`

创建分享请求

**继承**: BaseModel

##### `ShareImportRequest`

导入分享请求

**继承**: BaseModel

##### `ShareResponse`

分享响应

**继承**: BaseModel

##### `ShareDetailResponse`

分享详情响应

**继承**: BaseModel

#### 函数

##### `_ensure_dir()`

##### `_share_path(share_id)`

##### `_sanitize_config(config)`

脱敏配置

### `src/web/team_api.py`

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

#### 类

##### `WikiGenerator`

Wiki 文档生成器

| 方法 | 说明 |
|------|------|
| `generate(self, output_path)` | 生成 Wiki 文档 |

### `src/wiki/parser.py`

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

### `tools/demo_video_generator.py`

Oh My Coder Demo Video Generator
生成 3 分钟演示 GIF（~180秒播放时间，约60帧/6秒 = 30帧总）

#### 函数

##### `ease_in_out(t)`

##### `draw_terminal_frame(img, active_tab)`

绘制终端窗口框架

##### `_round_rect(draw, bbox, r, fill)`

##### `_round_rect_top(draw, bbox, r, fill)`

##### `wrap_text(text, width_chars)`

按字符数换行

##### `draw_text_lines(draw, lines, x, y, font, color, line_h)`

逐行绘制文字

##### `make_gradient_overlay(draw, bbox, color_top, color_bot, opacity)`

从下往上渐变遮罩

##### `type_text(full_text, char_count, prefix)`

打字机效果

##### `frame_intro(progress)`

开场白 + 标题

##### `frame_install(progress)`

安装演示

##### `frame_config(progress)`

配置 API Key

##### `frame_run_explore(progress)`

运行演示 - explore

##### `frame_multiagent(progress)`

多 Agent 协作工作流

##### `frame_result(progress)`

运行结果展示

##### `frame_outro(progress)`

总结

##### `generate_demo_video()`

生成完整演示 GIF

### `tools/generate_demo_v020.py`

Oh My Coder v0.2.0 Demo Video Generator
生成 60-90 秒演示视频 (1080p MP4)
使用 OpenCV 直接编码

#### 函数

##### `new_frame()`

创建新帧

##### `draw_text(img, text, x, y, font_scale, color, thickness)`

绘制文字

##### `draw_text_centered(img, text, y, font_scale, color, thickness)`

居中绘制文字

##### `ease_in_out(t)`

缓动函数

##### `draw_terminal(img, title, lines, y_offset)`

绘制终端窗口

##### `scene_intro(frames, duration)`

开场 (5秒)

##### `scene_agents_list(frames, duration)`

Agents 列表展示 (10秒)

##### `scene_workflow(frames, duration)`

工作流执行 (15秒)

##### `scene_vscode(frames, duration)`

VS Code 插件展示 (15秒)

##### `scene_local_models(frames, duration)`

本地模型支持 (10秒)

##### `scene_self_improving(frames, duration)`

自进化系统 (10秒)

##### `scene_outro(frames, duration)`

结尾 (5秒)

##### `main()`

### `tools/todo_demo.py`

待办事项 CLI 应用
支持添加、查看、完成、删除任务，数据存储在 JSON 文件中

#### 函数

##### `main()`

主函数：解析命令行参数并执行相应命令

### `tools/verify_gateway.py`

Gateway 功能验证脚本

验证：
1. Gateway 初始化（无 token 时用 NoopHandler）
2. 消息格式转换（IncomingMessage / OutgoingMessage）
3. Telegram/Discord Handler 依赖检查逻辑

---

*此文档由 [oh-my-coder](https://github.com/VOBC/oh-my-coder) 自动生成*
