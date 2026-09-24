# Changelog

All notable changes to this project will be documented in this file.


The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## [Unreleased]

### Documentation
- 修正文档中错误的 provider key 名：`MIMOX_API_KEY` → `MINIMAX_API_KEY`、`QWEN_API_KEY` → `DASHSCOPE_API_KEY`（对齐 `cli_run.py` 实际支持的 key）
- 修正不存在的 `omc config set --default-model` 选项 → `omc config set -k DEFAULT_MODEL -v`（`DEFAULT_MODEL` 是 `router.py` 实际读取的环境变量）
- 修正不存在的 `omc config list-models` 命令 → `omc config models`
- 官网 quickstart 统一为不带 `-m` 的全局配置命令（`omc config set -k ZHIPUAI_API_KEY -v`），与 CLI 真实签名及 README 保持一致

---

## [0.3.0] - 2026-09-24

### Fixed
- ci: 修复 link-check workflow 中 lychee `--accept` 重复传参（lychee-action v2.9.0 不允许多次 `--accept`），改为逗号分隔单次传入
- **config show/list 现在列出所有 provider 的 API Key** — 之前仅硬编码 DeepSeek/KIMI/豆包，
  配了智谱 GLM（ZHIPUAI_API_KEY）、MiniMax、通义千问、文心一言、混元后 `omc config show`
  看不到注入情况，与官网教程命令配合形成死锁（set 报错 + show 不显示 key）
- **config models 现在显示所有配置字段** — 之前仅硬编码 api_key/base_url/temperature，
  用户配置 max_tokens/system_prompt 后不可见

### Documentation Updates
- Update README coverage badge: 87% → 96% (2026-08-16)

---

## [0.2.1] - 2026-08-01

### Fixed
- Fix mypy type errors in cli.py (commit 1dbc576)
- Fix `leave_team` returns False when user is not a member of any team (commit e14ab6c)
- Replace deprecated Pydantic class Config with model_config (commit 119fab9)

### Changed / Refactored
- Add return type annotations to cli_cost.py (commit 0690d4f)
- Add type hints to server_api.py public functions (commit 8be0542)

### Documentation Updates
- Add docstrings to cli.py public functions (commit 12938f8)

