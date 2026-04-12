# 场景三：用 Oh My Coder 做 Code Review

> **目标**：对任意代码变更做深度 Review，发现 bug、性能问题、安全漏洞
> **用时**：约 3–8 分钟
> **前提**：已安装 Oh My Coder、配置好 `DEEPSEEK_API_KEY`

---

## 📦 前置准备：模拟一次代码变更

Review 需要有代码变更。可以是本地改动，也可以是 PR diff。

### 方式 A：本地未提交的改动

```bash
cd ~/flask-demo  # 你上一个场景的项目
# 故意引入一个有问题的改动
cat > app/bad_logic.py << 'EOF'
import hashlib

def hash_password(password: str) -> str:
    # ⚠️ 故意留一个 bug：未做 salt
    return hashlib.md5(password.encode()).hexdigest()

def get_user_data(user_id: int) -> dict:
    # ⚠️ SQL 注入漏洞
    import sqlite3
    conn = sqlite3.connect("app.db")
    row = conn.execute(f"SELECT * FROM users WHERE id = {user_id}").fetchone()
    conn.close()
    return {"id": row[0], "name": row[1]} if row else {}
EOF

git diff  # 查看变更
```

### 方式 B：直接 review 一个文件（最简单）

```bash
# 直接 review 任意文件
omc run "Review 这个文件 app.py，重点检查安全问题和代码质量" -w review
```

### 方式 C：Review GitHub PR diff

```bash
# 用 GitHub CLI 或手动下载 diff
gh pr diff 12345 > /tmp/pr.diff
omc run "Review /tmp/pr.diff 中的代码变更" -w review
```

---

## 🚀 运行 Code Review 工作流

以本地文件方式为例：

```bash
cd ~/flask-demo
omc run "Review app/bad_logic.py，重点：1)安全性 2)性能 3)可维护性 4)最佳实践" -w review
```

Oh My Coder 自动进行多维度 Review：

```
🔍 [1/6] explore  读取并分析代码...
   文件: app/bad_logic.py
   行数: 15
   语言: Python 3.x

🔒 [2/6] security  安全审查...
   🔴 严重: SQL 注入漏洞（第 10 行）
      f-string 直接拼接 user_id 变量
      建议: 使用参数化查询
      修复: conn.execute("SELECT * FROM users WHERE id = ?", (user_id,))

🟡 中等: 密码哈希不安全（第 5 行）
      MD5 用于密码哈希（可暴力破解）
      建议: 使用 bcrypt 或 argon2
      修复: from passlib.hash import bcrypt; bcrypt.hash(password)

⚡ [3/6] performance  性能审查...
   ✅ 未发现明显性能问题
   💡 建议: 考虑添加缓存层

📐 [4/6] quality  代码质量审查...
   ⚠️ 函数无类型注解（get_user_data 返回值）
   ⚠️ 魔法值（数据库文件名 hardcode）
   ⚠️ 错误处理缺失（fetchone() 可能返回 None）

📋 [5/6] reviewer  生成 Review 报告...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 Code Review 报告: app/bad_logic.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔴 严重 (1)
  L10: SQL 注入 — 直接拼接 user_id，可被注入攻击

🟡 中等 (2)
  L5:  弱哈希算法 — MD5 不适合密码存储
  L12: None 未处理 — row 为 None 时报错

💡 建议 (3)
  L3:  缺少类型注解
  L8:  数据库路径应配置化
  L1:  缺少 docstring

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
修复优先级: 🔴 > 🟡 > 💡
预估修复时间: 10 分钟

📁 自动生成修复补丁：app/bad_logic.py.fixed
✨ Review 完成！耗时 1 分 43 秒
```

---

## 📂 第二步：查看自动生成的修复版本

```bash
cat app/bad_logic.py.fixed
```

```python
"""app/bad_logic.py — Review 修复版"""
import hashlib
from typing import Optional
from passlib.hash import bcrypt
from functools import lru_cache


def hash_password(password: str) -> str:
    """安全哈希密码（使用 bcrypt）。

    Args:
        password: 明文密码

    Returns:
        bcrypt 哈希后的密码字符串
    """
    return bcrypt.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    """验证密码是否匹配。

    Args:
        password: 明文密码
        hashed: bcrypt 哈希值

    Returns:
        匹配返回 True，否则 False
    """
    return bcrypt.verify(password, hashed)


def get_user_data(user_id: int, db_path: str = "app.db") -> Optional[dict]:
    """根据 ID 获取用户数据。

    Args:
        user_id: 用户 ID
        db_path: 数据库路径（可配置）

    Returns:
        用户数据字典，不存在返回 None
    """
    import sqlite3

    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            "SELECT id, name FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        return {"id": row[0], "name": row[1]} if row else None
    finally:
        conn.close()
```

---

## 🧪 第三步：确认修复后代码通过 Review

```bash
# 替换旧文件
mv app/bad_logic.py.fixed app/bad_logic.py

# 再跑一次 Review，确认问题已消除
omc run "Re-review app/bad_logic.py" -w review
```

```
🔒 [2/6] security  安全审查...
   ✅ SQL 注入已修复（参数化查询）
   ✅ 密码哈希已修复（bcrypt）
   ✅ None 处理已添加

📋 Code Review 报告: app/bad_logic.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ 无严重问题
✅ 无中等问题
💡 建议 (1): 考虑添加缓存层

✨ Review 通过！耗时 1 分 28 秒
```

---

## 🔄 Bonus：结对 Review（pair 模式）

结对 Review 让 AI 扮演 Reviewer 角色，边讨论边改：

```bash
omc run "结对 Review：Reviewer 角色审查我的代码变更" -w pair
```

```
🤝 [Pair Review Mode]

Reviewer: 我来审查你这几行代码...
  L10: 这里有个边界条件需要注意...

你: 为什么这里会有问题？

Reviewer: 因为 fetchone() 在找不到记录时返回 None，
直接访问 row[0] 会抛 IndexError。

你: 那怎么改？

Reviewer: 改成:
  row = cur.fetchone()
  if not row:
      return None
  return {"id": row[0], "name": row[1]}

你: 好的，我接受这个建议。
→ 自动写入修复到 app/bad_logic.py

✅ Pair Review 完成！
```

---

## 🎯 总结

| 维度 | Review 内容 | 发现的问题 |
|------|------------|-----------|
| 🔒 安全 | SQL 注入、弱密码哈希 | 🔴 SQL 注入、🟡 MD5 弱哈希 |
| ⚡ 性能 | 缓存、N+1 查询 | 💡 建议加缓存 |
| 📐 质量 | 类型注解、错误处理 | 🟡 None 未处理、💡 缺少 docstring |
| 🔧 修复 | 自动生成修复补丁 | ✅ `.fixed` 文件直接可用 |

使用 `-w review`，Oh My Coder 从**安全 + 性能 + 质量 + 最佳实践**四个维度审查你的代码，并自动生成修复补丁。Review 完成后代码变干净，补丁可直接采纳。

> 💡 **提示**：如果只想快速扫一眼，不想看详细报告，加 `--summary` 参数：
> ```bash
> omc run "review app/" -w review --summary
> ```
