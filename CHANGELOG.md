# 更新日志 (Changelog)

所有重要的项目变更都将记录在此文件中。

格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/) 规范。

---

## [v1.0.0] - 2026-04-05

### 🎉 正式版发布

> 经过多个迭代版本的打磨，Oh My Coder 正式发布 v1.0.0！

### 新增功能

#### Executor Agent 重大升级

- **自动代码提取与保存** - `_extract_code_blocks()` 从 LLM 输出中精准提取代码块
  - 支持 ` ```language:path/to/file.ext ` 格式
  - 支持 ` ```:path/to/file.ext ` 格式
  - 自动创建目录结构并保存文件
- **智能格式化** - 保存后自动运行代码格式化工具
  - Python: `black`
  - JS/TS: `prettier`
  - Go: `gofmt`
- **自动测试运行** - 保存测试文件后自动运行 pytest
  - 解析测试结果（通过/失败数量）
  - 返回结构化测试报告
- **相关文件智能注入** - `_inject_relevant_files()` 根据任务关键词查找相关代码
- **多语言支持** - 14 种编程语言代码块识别

#### 项目基础设施

- **完整测试套件** - 43 个测试用例，100% 通过
- **API 参考文档** - `docs/API.md` 完整覆盖 Web API 和 Python SDK
- **Web 界面** - 可视化工作流 + SSE 实时推送 + 深色模式
- **CLI 增强** - `--version` / `--help` / 友好主面板
- **社区配置** - GitHub Issue/PR 模板、FUNDING 文件

### 性能优化

- **ResponseCache** - 消息内容哈希缓存，避免重复 API 调用（节省 30%+ Token）
- **增强故障转移** - 递增重试等待（2s→4s→6s），全链路日志追踪
- **惰性 Agent 加载** - `Orchestrator.get_agent()` 按需加载

### 错误处理

- `NoModelAvailableError` - 所有模型不可用时的明确异常
- SSE `put_nowait` 替代 `create_task` - 避免 event loop 依赖
- `try_format_code()` / `try_run_tests()` - 所有外部调用均有异常保护

### 代码质量

- 43/43 测试通过，0 warnings
- Starlette TemplateResponse 参数顺序修正
- WORKFLOW_TEMPLATES 字段访问修复
- Router TaskType 从 Enum 改为类常量（避免序列化问题）
- 完整类型注解覆盖

### 文档

- `README.md` - 徽章（Stars/Issues/License）、项目结构图、测试说明
- `docs/API.md` - 7 大章节完整 API 参考
- `CHANGELOG.md` - 版本历史记录
- `CONTRIBUTING.md` - 贡献指南
- `.github/ISSUE_TEMPLATE/bug_report.yml` - 结构化 Bug 报告
- `.github/PULL_REQUEST_TEMPLATE.md` - PR 规范模板
- `FUNDING.yml` - 赞助说明
- `examples/web_demo.py` - Web API 5 场景示例
- `examples/cli_demo.py` - CLI 7 场景示例

---

## [v0.2.1] - 2026-04-05

### 📚 API 文档

首个完整 API 参考手册上线！

- `docs/API.md` - 完整 Web API 和 Python SDK 文档

### ⚡ 性能优化

- **响应缓存** - `ResponseCache` 类，基于消息内容哈希缓存响应
- **故障转移增强** - 递增重试等待时间（2s → 4s → 6s）
- **日志增强** - 全链路日志记录

---

## [v0.2.0] - 2026-04-05

### 🌐 Web 界面

首个完整的 Web 界面版本上线！

- FastAPI Web 应用 + SSE 实时进度推送
- 可视化 Agent 流水线动画
- 深色/浅色主题切换
- 4 种工作流快捷卡片

---

## [v0.1.0] - 2026-04-04

### 🎉 首次发布

18 个 Agent、多模型适配器（DeepSeek/文心/通义）、CLI 工具、编排引擎。
