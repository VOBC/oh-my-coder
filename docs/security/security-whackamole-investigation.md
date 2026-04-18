# GitHub Security "打地鼠" 问题深度调查报告

## 执行摘要

2026-04-18 上午，用户反馈 GitHub Security 出现大量错误，修复后反复出现新问题。经调查，这是一个典型的**"打地鼠"式修复模式**（Whack-a-Mole Bug Fixing），根本原因是：

1. **修复策略错误**：采用"见一个修一个"的被动模式
2. **缺乏系统性**：没有建立预防机制，导致同类问题反复出现
3. **知识沉淀不足**：虽然建立了文档，但没有转化为开发流程约束

---

## 问题时间线

```
09:33  首次出现 CodeQL 告警
09:35  修复 Alert #1/#2/#3 (permissions)
09:40  修复 Alert #4 (str(e) 泄露)
09:45  修复 Alert #8/#7/#6 (URL 验证)
09:50  修复 Alert #12/#13 (URL 子串检查)
10:00  第二批 str(e) 修复
10:15  MD5 → SHA256 修复
10:28  ShellCheck CI 失败
10:32  修复 ShellCheck 参数错误
10:35  修复 checkout 版本错误
11:13  修复 SC2261 错误
11:17  建立 P1/P2 安全体系
11:25  CodeQL 配置冲突错误
11:32  删除 CodeQL job
```

**统计：12 个 CodeQL 相关 commits，涉及 6 轮修复**

---

## 根本原因分析

### 1. 修复策略问题

| 问题 | 说明 |
|------|------|
| **被动修复** | 等 CI 报错了才修，而不是写代码时就避免 |
| **局部修复** | 只修报错的文件，不检查同类问题 |
| **重复犯错** | `str(e)` 问题在多个文件反复出现 |

### 2. 流程缺失

```
理想流程：
写代码 → 本地安全扫描 → 修复问题 → 提交 → CI 通过

实际流程：
写代码 → 提交 → CI 报错 → 修复 → 提交 → CI 又报错 → ...
```

### 3. 知识转化失败

虽然建立了：
- ✅ `SECURITY_CODING_GUIDE.md` - 安全编码规范
- ✅ `docs/security/CODEQL_SOLUTIONS.md` - 问题解决方案库
- ✅ `.githooks/pre-commit-security.sh` - 本地安全钩子
- ✅ `tests/test_security_patterns.py` - 安全模式测试

**但是**：这些文档没有转化为**强制性约束**，开发者（包括 AI）仍然可以写出不安全的代码。

---

## 经验教训（整合小麦的 6 条核心经验）

> 以下经验来自小麦的实际踩坑总结，已整合到本报告中。

### 经验 1：不要打地鼠 — 批量修复同类问题

**小麦原话**：修一个 CodeQL 问题前，先全库扫描所有同类问题，一次性全修。

**错误做法**：
```bash
# 第 1 轮：修复 src/models/a.py 的 str(e)
# 第 2 轮：修复 src/models/b.py 的 str(e)
# 第 3 轮：修复 src/models/c.py 的 str(e)
# ... 重复 5+ 次
```

**正确做法**：
```bash
# 一次性扫描所有文件，批量修复
grep -rn "str(e)" src/ tests/ --include="*.py"
# 然后一次性全部修改
```

### 经验 2：扫描有延迟 — 不要期待即时反馈

**小麦原话**：GitHub CodeQL 修复后要等几小时到一天才更新，不是立刻消失。

**关键认知**：
- CodeQL 扫描是异步的，修复后不会立即反映
- 不要因为"修完还报错"而反复修改
- 提交修复后，等待 2-24 小时再检查状态

### 经验 3：测试代码也要安全

**小麦原话**：`assert "domain" in url` 这种写法即使在 test 文件里也会被标记。

**常见误区**：
```python
# ❌ 错误：测试文件里也不安全
assert "api.deepseek.com" in url  # CodeQL 会标记

# ✅ 正确：测试文件也要用 urlparse
from urllib.parse import urlparse
assert urlparse(url).netloc == "api.deepseek.com"
```

### 经验 4：str(e) 禁止 — 异常信息不能直接暴露

**小麦原话**：异常信息不能直接暴露，用 `"Internal server error"` 替代。

**错误示例**：
```python
except Exception as e:
    return {"error": str(e)}  # ❌ 可能泄露敏感信息
```

**正确做法**：
```python
except Exception as e:
    return {"error": "Internal server error"}  # ✅ 固定消息
    # 或
    return {"error": type(e).__name__}  # ✅ 只暴露类型
    # 或
    return {"error": f"HTTP {e.response.status_code}"}  # ✅ 脱敏状态码
```

### 经验 5：修复前先扫描，修复后验证

**小麦原话**：不要修完就不管了。

**标准流程**：
```bash
# 1. 修复前：扫描确认问题范围
grep -rn "str(e)" src/ tests/

# 2. 修复：批量修改所有同类问题

# 3. 修复后：验证是否还有残留
grep -rn "str(e)" src/ tests/

# 4. 本地测试
python3 -m pytest tests/ -q

# 5. 提交后：等待 CI 完成，确认通过
```

### 经验 6：建立门禁 — 多重防护体系

**小麦原话**：CI 安全检查 + pre-commit hook + 安全编码规范。

**三层防护**：

| 层级 | 工具 | 作用 |
|------|------|------|
| **第一层** | Pre-commit hook | 本地拦截，提交前检查 |
| **第二层** | CI 快速检查 | PR 阶段拦截 |
| **第三层** | CodeQL 完整扫描 | 合并后深度检查 |

---

## 补充经验教训（AI 反思）

### 教训 1：预防 > 修复

**错误做法**：
```python
# 写代码时不考虑安全
except Exception as e:
    return {"error": str(e)}  # 提交后等 CI 报错

# CI 报错后再修复
except Exception as e:
    return {"error": type(e).__name__}  # 第 N 次修复
```

**正确做法**：
```python
# 写代码时就遵循规范
except Exception as e:
    return {"error": type(e).__name__}  # 一次做对
```

### 教训 2：批量修复 > 逐个修复

**错误做法**：
```bash
# 第 1 轮：修复 src/models/a.py
# 第 2 轮：修复 src/models/b.py
# 第 3 轮：修复 src/models/c.py
# ... 重复 N 次
```

**正确做法**：
```bash
# 一次性扫描所有文件，批量修复同类问题
grep -r "str(e)" src/ | xargs -I {} sed -i 's/str(e)/type(e).__name__/g'
```

### 教训 3：强制约束 > 文档建议

**错误做法**：
```markdown
# SECURITY_CODING_GUIDE.md
请不要使用 str(e)，建议使用 type(e).__name__
# （开发者可以忽略）
```

**正确做法**：
```python
# .githooks/pre-commit
if grep -r "str(e)" src/; then
    echo "❌ 禁止使用 str(e)，请使用 type(e).__name__"
    exit 1
fi
```

### 教训 4：测试先行 > 事后补测

**错误做法**：
```python
# 先写业务代码，等 CI 失败后再写测试
```

**正确做法**：
```python
# test_security_patterns.py - 先定义安全规则
def test_no_str_e_in_except():
    """禁止在 except 中使用 str(e)"""
    code = inspect.getsource(module)
    assert "str(e)" not in code
```

---

## 系统性解决方案

### 方案 1：强制 Pre-commit 检查（立即实施）

```bash
#!/bin/bash
# .githooks/pre-commit

ERRORS=0

echo "🔍 安全扫描..."

# 检查 str(e)
if grep -rn "str(e)" src/ --include="*.py"; then
    echo "❌ 发现 str(e)，请使用 type(e).__name__"
    ERRORS=$((ERRORS + 1))
fi

# 检查 in url
if grep -rn '".*" in.*url' src/ --include="*.py"; then
    echo "❌ 发现不安全的 URL 验证，请使用 urlparse"
    ERRORS=$((ERRORS + 1))
fi

# 检查 MD5/SHA1
if grep -rn "hashlib\.md5\|hashlib\.sha1" src/ --include="*.py"; then
    echo "❌ 发现弱加密算法，请使用 SHA256"
    ERRORS=$((ERRORS + 1))
fi

if [ $ERRORS -gt 0 ]; then
    echo "❌ 发现 $ERRORS 个安全问题，提交被拒绝"
    echo "📖 参考: SECURITY_CODING_GUIDE.md"
    exit 1
fi

echo "✅ 安全扫描通过"
```

### 方案 2：IDE/编辑器集成（推荐）

在 `.vscode/settings.json` 中添加：
```json
{
  "python.analysis.diagnosticSeverityOverrides": {
    "reportGeneralTypeIssues": "error"
  },
  "editor.codeActionsOnSave": {
    "source.fixAll": true
  }
}
```

### 方案 3：CI 前置检查

在 `.github/workflows/security.yml` 中添加快速检查：
```yaml
jobs:
  quick-security-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Security Pattern Check
        run: |
          # 在完整扫描前先做快速检查
          if grep -rn "str(e)" src/ --include="*.py"; then
            echo "❌ 发现 str(e)，请先本地修复"
            exit 1
          fi
```

### 方案 4：Code Review 清单

```markdown
## PR Review 安全清单

- [ ] 所有 `except` 块中没有 `str(e)`
- [ ] 所有 URL 验证使用 `urlparse`
- [ ] 没有使用 MD5/SHA1
- [ ] 没有硬编码敏感信息
- [ ] 所有用户输入都有验证
```

---

## 责任分析

### AI（我）的责任

1. **修复策略错误**：采用被动修复模式，没有主动预防
2. **缺乏系统性思维**：没有一次性扫描所有同类问题
3. **知识转化失败**：虽然建立了文档，但没有转化为强制约束

### 改进措施

1. **写代码前**：先读安全规范
2. **写代码时**：遵循安全模式
3. **提交前**：运行本地安全扫描
4. **修复时**：批量修复同类问题，而不是逐个文件修

---

## 结论

GitHub Security "打地鼠"问题的根本原因是**修复策略错误**，而不是技术问题。建立文档和知识库是好的，但更重要的是将知识转化为**强制性约束**，让不安全的代码无法通过 CI。

**核心原则**：
- 预防 > 修复
- 批量 > 逐个
- 强制 > 建议
- 测试先行 > 事后补测

---

*报告生成时间：2026-04-18*
*调查人：代可行*
