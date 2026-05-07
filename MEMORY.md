# MEMORY.md — 长期记忆

> 最后更新：2026-05-06

---

## 🛡️ CI/CD 核心原则

### 本地 ≠ CI
CI 是干净环境，本地有缓存/残留。本地通过不代表 CI 绿。

### 提交前检查清单
```bash
python3 -m ruff check . --fix    # 1. 全面检查+自动修复（整个项目，不是单个文件）
python3 -m ruff check .          # 2. 验证无错误
python3 -m pytest tests/ -q      # 3. 测试通过
git add -A && git push
```

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

### 2. 改代码必须同步文档（2026/05/06）⭐⭐⭐
改了代码就 grep 一遍文档，旧值必须清零。详细规则见 `rules/doc-sync-rule.md`。

**检查方法**：`grep -rn "旧路径" . --include="*.md" --exclude-dir=.git --exclude-dir=node_modules`

**教训**：删除 SECURITY.md 后没检查 docs/CODE_REVIEW.md 中的引用，导致 CI lychee 失败。

### 3. ruff.toml 优先级 > pyproject.toml（2026/04）
同时存在时只读前者。改 pyproject.toml 的 ruff 配置不生效。

### 4. Desktop UI 组件必须有 fallback（2026/04）
`window.omc` API 在 Vite dev 模式不存在，所有组件必须提供 fallback 数据。

---

## 📅 项目进度

### oh-my-coder (CLI)
https://github.com/VOBC/oh-my-coder
- **测试**: 1029 passed, 40 skipped, 2 warnings
- **完成**: P2-7 社区模板、P2-8 Monorepo、ShellCheck 全绿、Python 3.9 兼容性
- **待完成**: P2-1 自动测试增强、P2-2 成本优化建议（`omc cost`）

### 桌面端 (oh-my-coder/desktop)
- 可运行 .app，18 个模型，完整 UI
- **待完成**: 应用图标 / Apple 签名 / notarization

---

_最后更新：2026-05-06 压缩记忆，删除过时内容_
