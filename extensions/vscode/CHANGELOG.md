# Changelog

## [0.1.0] - 2024-04-16

### ✨ 新增

- **30 个智能体** - 覆盖 BUILD/REVIEW/DEBUG/DOMAIN 四大通道
  - BUILD: Planner, Architect, Executor, Verifier, CodeSimplifier, Migration
  - REVIEW: CodeReviewer, SecurityReviewer, Critic, Performance
  - DEBUG: Debugger, Tracer
  - DOMAIN: TestEngineer, QATester, Designer, Writer, Document, Scientist, GitMaster, Explore, Vision, UML, Analyst, Database, DevOps, API, Auth, Data, Prompt, SkillManage, SelfImproving

- **12 个国产大模型支持**
  - deepseek, qwen, glm, kimi, hunyuan, wenxin, doubao, minimax, tiangong, spark, baichuan, siliconflow

- **CLI 自动查找**
  - 支持 `which omc` / `where omc` 自动查找
  - 回退到常见安装路径
  - 跨平台兼容（Windows/macOS/Linux）

- **侧边栏面板**
  - 任务管理界面
  - Agents 树形视图
  - 历史记录

- **快捷键支持**
  - `Ctrl+Shift+Enter` - 运行任务
  - `Ctrl+Shift+R` - 代码审查
  - `Ctrl+Shift+O` - 打开面板

- **状态栏集成** - 实时显示任务状态

### 🔧 技术改进

- TypeScript 严格模式
- 完整的类型定义
- 错误处理和用户提示

## [0.0.1] - 2024-04-08

### 🎉 初始版本

- 基础插件框架
- 简单的任务执行
- 侧边栏面板原型
