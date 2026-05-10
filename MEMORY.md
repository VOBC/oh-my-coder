# MEMORY.md — 长期记忆

> 最后更新：2026-05-07

---

## 🛡️ CI/CD 核心原则

### 代码修改后必须执行的流水线（铁律）
```bash
# 任何代码修改后，按顺序执行，缺一不可：
python3 -m ruff check . --fix    # 1. 全面检查+自动修复（整个项目，不是单个文件）
python3 -m ruff check .          # 2. 验证无错误
python3 -m pytest tests/ -q      # 3. 测试通过
git add -A && git commit && git push  # 4. 提交推送
```

### 本地 ≠ CI
CI 是干净环境，本地有缓存/残留。本地通过不代表 CI 绿。

### 常见 CI 问题

| 问题 | 原因 | 解决 |
|------|------|------|
| Typer exit_code 返回 2 | CLI 用 exit(1) 表示成功 | 测试输出内容，不测 exit_code |
| `[dev]` 被 shell 解析 | glob 在 CI 生效 | 加引号 `'.[dev]'` |
| 路径找不到 | 硬编码了用户名/绝对路径 | 用 `Path(__file__).parent` |
| ruff B905 zip strict | `strict=False` 是 Python 3.10+ | ruff.toml 加 `per-file-ignores = {"B905"}` |

---

## 🐍 Python 编码规范

### Python 3.9 兼容性（最高优先级）
```python
# ❌ Python 3.10+ 语法
def foo(x: Path | str) -> ModuleInfo | None: ...

# ✅ Python 3.9 兼容
from typing import Union, Optional
def foo(x: Union[Path, str]) -> Optional[ModuleInfo]: ...
```

### 导入规范
- 全部放顶部，不在函数内 import
- 用多少导多少，避免 F401 未使用导入
- 批量修复：`ruff check --fix`

---

## ⚠️ 重要教训

### 1. Ruff 安全门禁 — CI 卡住的根本原因（2026/05/05）⭐⭐⭐
连续多次 CI 失败，每次只修一个文件。根本原因：只对单个文件运行 ruff check，没有检查整个项目。

**正确 workflow**：每次提交前 `ruff check . --fix` 检查整个项目。

**安全门禁**：
- 禁止 `str(e)`，用 `type(e).__name__`
- 循环未使用变量加下划线 `for x, _url in items`
- import 块必须排序

### 2. 为什么 78 个错误会积累？（2026/05/07）⭐⭐⭐
**根因分析**：
1. **pre-commit hook 形同虚设** — 配置了 `language: system`，但很多提交绕过了 hook（GitHub Web UI、部分 git 客户端、AI 生成代码直接写文件）
2. **没有 CI 自动拦截** — 没有 GitHub Actions 在 PR 时跑 ruff check，错误可以合入主分支
3. **AI 写代码不跑 lint** — 我和其他 AI agent 生成代码后没有验证就提交，截断的文件（cli_stats.py、t3_write_summary.py）直接入库
4. **只修单文件不查全量** — 之前的教训（5/5）只修了当时出错的文件，没有定期全量扫描
5. **没有写后即检的习惯** — 代码写完 → 应该立即 lint → 但实际是写完就提交了

**解法**：
- **铁律**：任何代码修改后必须跑 `ruff check . --fix && ruff check . && pytest`
- **AI 写代码后必须验证**：写完文件后立即 `ruff check <file>`，截断的文件会报 syntax error
- **定期全量扫描**：每周至少一次 `ruff check .` 全量检查，不让错误积累
- **考虑加 GitHub Actions**：PR 必须过 ruff check 才能合入

### 3. --unsafe-fixes 的陷阱（2026/05/07）⭐⭐
ruff 的 `--unsafe-fixes` 会把 `Optional[str]` 改成 `str | None`，这是 Python 3.10+ 语法。项目 target 是 3.9 时，这会直接报 SyntaxError。

**规则**：
- `--fix` 是安全的，可以放心用
- `--unsafe-fixes` 必须人工审查改动，不能盲目用
- ruff.toml 中已 ignore UP045 的项目不受影响，但新项目/example 要注意

### 2. 改代码必须同步文档（2026/05/06）⭐⭐⭐
改了代码就 grep 一遍文档，旧值必须清零。详细规则见 `rules/doc-sync-rule.md`。

**检查方法**：`grep -rn "旧路径" . --include="*.md" --exclude-dir=.git --exclude-dir=node_modules`

**教训**：删除 SECURITY.md 后没检查 docs/CODE_REVIEW.md 中的引用，导致 CI lychee 失败。

### 4. ruff.toml 优先级 > pyproject.toml（2026/04）
同时存在时只读前者。改 pyproject.toml 的 ruff 配置不生效。

### 5. Desktop UI 组件必须有 fallback（2026/04）
`window.omc` API 在 Vite dev 模式不存在，所有组件必须提供 fallback 数据。

### 6. 任务完成汇报机制（2026/05/08）⭐⭐⭐
每完成一个任务（包括子任务），**必须立即向主会话汇报**，不能静默完成。

**汇报方式**：使用 `sessions_send` 工具发消息给主会话。

**汇报原则**：
- **立即汇报**：任务完成后立刻发送，不要等
- **简洁**：1-3 句话总结结果，不要长篇大论
- **包含关键信息**：改了哪些文件、测试是否通过、commit hash
- **如有阻塞**：说明原因，不要假装完成了

### 7. 里程碑即时存档（2026/05/08）⭐⭐
每完成一个重要里程碑，**立即保存进度**，不等最后一起写。

**存档路径**：
| 内容 | 保存位置 |
|------|---------|
| 技术架构文档 | `docs/ARCHITECTURE.md` |
| 核心代码模块 | `src/` 对应目录 |
| 进度记录 | `.learnings/PROGRESS.md`（每 2 小时更新一次） |

**进度记录格式（.learnings/PROGRESS.md）**：
```
## [时间] 完成内容
- 已完成：xxx
- 下一步：xxx
- 阻塞：xxx（如有）
```

---

## 📅 项目进度

### oh-my-coder (CLI)
https://github.com/VOBC/oh-my-coder
- **最新 HEAD**: `916abe7e` (2026-05-09)
- **测试**: 1120 passed, 52 skipped, 17 warnings
- **完成**: P2-7 社区模板、P2-8 Monorepo、ShellCheck 全绿、Python 3.9 兼容性、Web UI 布局修复
- **待完成**: P2-1 自动测试增强、P2-2 成本优化建议（`omc cost`）

### 桌面端 (oh-my-coder/desktop)
- 可运行 .app，18 个模型，完整 UI
- **待完成**: 应用图标 / Apple 签名 / notarization

---

_最后更新：2026-05-10 整合多日教训 + 更新项目进度_
