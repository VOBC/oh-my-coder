# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-04-13

### Added

- **30 专业 Agent 系统**
  - 构建/分析通道：ExploreAgent、AnalystAgent、PlannerAgent、ArchitectAgent、ExecutorAgent、VerifierAgent、DebuggerAgent、TracerAgent
  - 审查通道：CodeReviewerAgent、SecurityReviewerAgent
  - 领域通道：TestEngineer、Designer、Vision、Document、Writer、Scientist、GitMaster、Database、API、DevOps、UML、Performance、Migration、Prompt、Auth、Data
  - 协调通道：CriticAgent、SelfImprovingAgent

- **7 种执行模式**
  - `sequential`：顺序执行
  - `parallel`：并行执行
  - `conditional`：条件分支
  - `doc`：文档生成
  - `build`：完整开发流程
  - `review`：代码审查
  - `autopilot`：自动路由

- **多模型支持（12 家国产模型，7 个生产就绪，5 个 Beta/待完善）**
  - DeepSeek（性价比最高，推荐）
  - 智谱 GLM（GLM-4-Flash 开源免费）
  - 文心一言（百度云）
  - 通义千问（阿里云）
  - Kimi（月之暗面）
  - 混元（腾讯云）
  - 豆包（字节跳动）
  - 天工（昆仑万维）
  - 讯飞星火（科大讯飞）
  - 百川（百川智能）
  - GLM 自定义（支持私有部署）

- **能力包系统（Capability Pack）**
  - `.omcp` 打包分享
  - Skill 自进化系统
  - Tier 0 自动注入

- **MCP Server 扩展**
  - Tools: run / explore / quest / checkpoint
  - Resources: project structure / git history / agent states
  - Prompts: task templates / workflow guides

- **Checkpoint & Rollback**
  - 断点续传
  - 进度回退
  - 状态快照

- **Web 界面**
  - HTTP API（`/api/execute`、`/api/status`、`/api/agent/live`）
  - SSE 实时推送
  - 团队协作统计

- **MkDocs 文档站**
  - Material 主题
  - 中英双语
  - Demo 截图

- **Quest Mode**
  - 后台异步任务
  - 实时进度推送
  - 任务管理 CLI

### Security

- 危险命令拦截（`rm -rf`、`sudo` 等）
- 沙箱执行环境
- 审计日志

### Documentation

- README.md：快速开始 + 架构说明
- docs/：MkDocs 文档站
- CHANGELOG.md：版本变更记录
