# Release Notes

## [Unreleased]

_(暂无待发布内容)_

---

## [v0.7.0] - 2026-08-01

### 新增
- 新增 CLI 命令 `omc init`（项目初始化）和 `omc review`（代码审查）
- 新增 `cli_plan.py` 命令（计划管理）
- 新增 `memory/manager.py` 模块（记忆管理）
- 新增 `models/base.py` 基础模型层测试覆盖

### 修复
- 修复 CI 配置：`-o 'addopts='` 覆盖 pytest.ini 中的 `-n auto`，避免 xdist 并行参数重复叠加导致测试超时
- 修复 `save_report` 在 `task.result` 为字符串时触发的 `AttributeError`
- 修复 `run_task` 在所有步骤均失败时仍标记为 `completed` 的状态错误
- 修复 `FALLBACK_MODELS` 数据不一致问题
- 修复遗留 lint 错误（ruff I001/F401/F841/E741）
- 修复 `src/cli.py` 路径引用过时问题（指向 `src/commands/cli.py`）
- 修复 `test_history_api.py` 路由路径（`/api/v1/history` → `/api/history`）

### 变更
- 移除所有 Gateway 渠道实现（Telegram / Discord / WhatsApp / 飞书 / 企业微信 / 钉钉 / Slack），保留 NoopHandler 占位
- 移除 `src/cli.py` 遗留 monolith 文件，统一使用 `src/commands/cli.py`
- CI Workflow 新增 `workflow_dispatch` 触发器，支持手动运行

### 测试
- 测试覆盖率提升至 **96%+**（7954 tests，0 failed）
- `src/monorepo.py` 覆盖率：99%
- `src/server_api.py` 覆盖率：99.5%
- `cli_plan.py` 覆盖率：98%
- `cli_lsp.py` 覆盖率：99%
- `capsule/registry.py` 覆盖率：100%
- `cost_optimizer` 覆盖率：99%

---

## [v0.6.4] - 2026-06-04

### 新增
- Desktop 端支持保存任务报告到 `~/.omc/reports/`
- Settings / Coverage API 测试用例
- Sessions API 测试用例

### 修复
- 修复 `omc config set -k GLM_API_KEY` 写入当前目录 `.env` 而非 `~/.omc/.env` 的问题
- 修复 Desktop 端往 `~/Desktop/` 保存文件的问题（改为 `~/.omc/reports/`）
- `cli_tui.py` 测试修复（127 tests）
- `web/app.py` 覆盖率：77% → 94%
- `cli_tui.py` 覆盖率：80% → 96%
- CI 超时配置优化：xdist 并行禁用，timeout 120s → 300s

### 变更
- GitHub Actions CI Workflow 全面优化（新增 `workflow_dispatch`）

---

## [v0.6.0] - 2026-05-30

### 新增
- `test_web_app_routes.py` 133 个测试用例
- `test_quest_executor.py` 新增 11 个测试（35 → 46 tests）
- `cli_cost.py` 命令（成本管理）

### 测试
- 测试覆盖率提升至 **81%**（5904 passed, 45 skipped, 0 failed）
- 修复 `Typer OptionInfo` truthiness 问题
- 修复 asyncio event loop 污染问题（`conftest.py` 新增 `_restore_event_loop` fixture）
- 修复 ruff lint errors（`typing_extensions` import, unused imports）

---

## [v0.5.0] - 2026-05-29

### 新增
- 完整的测试覆盖体系
- `cli_package_manager.py` 测试覆盖（89 tests）
- `cli_run.py` 测试覆盖

### 修复
- 修复 pytest-xdist 并行执行导致的全局状态污染
- 修复 `test_memory_auto_compact.py` 4 个失败测试
- 修复 `cli_quest.py` 测试（43% → 80%）

### 测试
- 测试覆盖率提升至 **80%**（5747 passed, 39 skipped, 0 failed）
- 全量并行 8 workers 通过（148.64s）

---

## [v0.4.0] - 2026-05-25

### 新增
- 测试覆盖率提升工程启动（起点 37%）
- 18 个新测试文件

### 变更
- 启动 oh-my-coder 全面测试覆盖率提升任务

---

## [v0.x.x] - YYYY-MM-DD

### 新增
- 31 个 AI Agent 支持
- 12 个国产模型深度集成
- 自进化系统
- VS Code 插件
- Electron Desktop 客户端

### 修复
- Python 3.9+ 兼容性修复
- FALLBACK_MODELS 数据同步

### 文档
- 完整 README（含模型对比表、Agent 架构图）
- GitHub Issue/PR 模板
- Demo GIF 展示
