# 教程三：用 oh-my-coder 做 Code Review

> **目标**：对一段代码进行专业的 Code Review，发现问题并提出改进建议  
> **耗时**：约 5-10 分钟  
> **前置**：已安装 oh-my-coder，有待审查的代码

---

## 📋 场景说明

你是一个 Tech Lead，每天要 review 多个 PR，代码风格各异，问题五花八门。手工 review 既耗时又容易遗漏。

本文演示用 oh-my-coder 的 `CodeReviewerAgent` 和 `SecurityReviewerAgent` 对代码进行自动化审查，覆盖**代码质量**和**安全漏洞**两个维度。

**审查对象：** 一个常见的用户认证模块（有安全问题的版本）

---

## 🚀 开始 Code Review

### 第一步：准备待审查代码

```bash
mkdir -p ~/tmp/code-review-demo/src
cd ~/tmp/code-review-demo

cat > src/auth.py << 'EOF'
"""用户认证模块（有问题版本）"""
import hashlib
import sqlite3
from flask import request, jsonify, g

app = Flask(__name__)
app.config['DATABASE'] = 'app.db'


def get_db():
    """获取数据库连接"""
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(app.config['DATABASE'])
        db.row_factory = sqlite3.Row
    return db


@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    # 问题1: SQL 注入风险
    query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
    db = get_db()
    cursor = db.execute(query)

    user = cursor.fetchone()
    if user:
        # 问题2: Session 直接存明文用户名
        session['user_id'] = user['id']
        session['username'] = user['username']
        return jsonify({'status': 'ok', 'user': user['username']})

    # 问题3: 错误信息泄露
    return jsonify({'error': f'登录失败，用户名或密码错误'}), 401


@app.route('/profile/<username>', methods=['GET'])
def profile(username):
    # 问题4: 未检查权限，任何人可以查看任意用户资料
    db = get_db()
    # 问题5: 仍然存在 SQL 注入
    result = db.execute(f"SELECT * FROM users WHERE username = '{username}'").fetchone()
    if not result:
        return jsonify({'error': '用户不存在'}), 404
    return jsonify({
        'id': result['id'],
        'username': result['username'],
        'email': result.get('email', ''),
        # 问题6: 泄露密码哈希（即使加了md5也不安全）
        'password': result.get('password_hash', ''),
    })


@app.route('/admin/execute', methods=['POST'])
def admin_exec():
    # 问题7: 危险！直接执行用户输入的命令
    cmd = request.json.get('cmd', '')
    import os
    output = os.popen(cmd).read()
    return jsonify({'result': output})


@app.route('/reset_password', methods=['POST'])
def reset_password():
    # 问题8: 密码重置逻辑不安全，无 token 验证
    data = request.get_json()
    new_password = data.get('new_password')
    db = get_db()
    db.execute(
        f"UPDATE users SET password='{new_password}' WHERE email='{data.get('email')}'"
    )
    db.commit()
    return jsonify({'status': '密码已重置'})
EOF

cat > src/app.py << 'EOF'
"""Flask 应用入口"""
from flask import Flask
app = Flask(__name__)
app.config['SECRET_KEY'] = 'hardcoded-secret-key-12345'

@app.route('/')
def index():
    return 'Hello World'

if __name__ == '__main__':
    app.run(debug=True)  # 生产环境不应开启 debug
EOF
```

---

### 第二步：执行代码质量审查

```bash
cd ~/tmp/code-review-demo

omc agent code-reviewer "审查 src/auth.py 和 src/app.py 的代码质量，\
重点检查：\
1. SQL 注入风险 \
2. 错误处理 \
3. 权限控制 \
4. 代码风格和可维护性 \
按严重程度分级（P0/P1/P2）输出问题清单，并给出修复建议"
```

**预期输出示例：**

```
[CODE_REVIEWER] 🔍 开始代码审查...

📁 审查文件：src/auth.py
📁 审查文件：src/app.py

🎯 发现 10 个问题（按严重程度排序）：

=== P0 - 严重问题（必须修复）===

❌ 1. [auth.py:31] SQL 注入漏洞
   代码：`query = f"SELECT * FROM users WHERE username = '{username}'..."`
   风险：攻击者可构造 `' OR '1'='1` 绕过认证
   修复：使用参数化查询
   ```python
   cursor = db.execute(
       "SELECT * FROM users WHERE username = ? AND password = ?",
       (username, password)
   )
   ```

❌ 2. [auth.py:64] 命令注入漏洞
   代码：`os.popen(cmd).read()`
   风险：攻击者可执行任意系统命令
   修复：完全删除此接口，或使用严格的命令白名单

❌ 3. [auth.py:74] 密码明文存储/不安全的密码重置
   代码：`db.execute(f"UPDATE users SET password='{new_password}'...")`
   风险：密码未哈希存储
   修复：使用 bcrypt/scrypt 哈希密码，添加 token 验证流程

=== P1 - 重要问题（尽快修复）===

⚠️ 4. [auth.py:47] 水平越权
   问题：用户可查看任意其他用户的资料，未做权限校验
   修复：添加 `@login_required` 并验证当前用户身份

⚠️ 5. [auth.py:54] 敏感信息泄露
   问题：返回了 password_hash 字段
   修复：从响应中移除该字段

⚠️ 6. [auth.py:21] Session 安全问题
   问题：session 直接存明文用户名
   修复：仅存储 user_id，会话数据存服务端

=== P2 - 优化建议 ===

💡 7. [app.py:8] 生产环境不应开启 debug=True
💡 8. [app.py:8] SECRET_KEY 硬编码
💡 9. [auth.py:35] 错误信息过于详细，可能泄露系统信息
💡 10. [auth.py] 数据库连接未使用 context manager，资源可能泄漏

📊 总结：
  P0: 3 个（安全漏洞）
  P1: 3 个（权限/信息泄露）
  P2: 4 个（配置/代码质量）
  建议优先修复 P0 和 P1
```

---

### 第三步：执行安全专项审查

```bash
omc agent security-reviewer "对 src/auth.py 进行深度安全审计，\
检查OWASP Top 10 相关风险，\
包括但不限于：\
1. SQL 注入 \
2. 认证与会话管理 \
3. 敏感数据暴露 \
4. 访问控制 \
5. 其他安全漏洞 \
输出每个漏洞的 CVSS 评分、攻击向量和修复方案"
```

**预期输出示例：**

```
[SECURITY_REVIEWER] 🔒 开始安全审计...

⚠️ 高危漏洞（CVSS ≥ 7.0）：

🔴 1. SQL 注入 - CVSS 9.1（严重）
   文件：src/auth.py:31
   类型：认证绕过（Authentication Bypass）
   攻击：POST /login {"username": "' OR '1'='1", "password": ""}
   后果：可无需密码登录任意账户
   修复：使用 ORM 或参数化查询

🔴 2. OS 命令注入 - CVSS 10.0（严重）
   文件：src/auth.py:64
   攻击：POST /admin/execute {"cmd": "rm -rf /"}
   后果：服务器完全沦陷
   修复：删除该接口

🟡 3. 敏感数据暴露 - CVSS 6.5（中等）
   文件：src/auth.py:54
   问题：API 响应暴露 password_hash
   修复：从 ORM 查询中 exclude 该字段

🟡 4. 水平越权 - CVSS 6.5（中等）
   文件：src/auth.py:47
   问题：任意用户可通过修改 URL 访问他人资料
   修复：@login_required + 当前用户校验
```

---

### 第四步：生成修复后的代码

```bash
omc run "根据上面的 Code Review 结果，修复 src/auth.py 中的所有 P0 和 P1 问题：\
1. SQL 注入 → 使用 SQLAlchemy ORM \
2. 命令注入 → 删除危险接口 \
3. 密码安全 → 使用 werkzeug.security 生成和验证密码哈希 \
4. 水平越权 → 添加 @login_required \
5. 敏感信息泄露 → 移除响应中的 password_hash \
同时更新 src/app.py：移除 debug=True，硬编码 SECRET_KEY 改为从环境变量读取 \
不改变原有功能逻辑" \
  -w ~/tmp/code-review-demo
```

---

### 第五步：验证修复

```bash
cd ~/tmp/code-review-demo

# 查看修复后的代码
cat src/auth.py | head -60

# 再次运行安全审查，确认问题已修复
omc agent security-reviewer "重新审查修复后的 src/auth.py，确认：\
1. SQL 注入漏洞是否已修复 \
2. 命令注入接口是否已删除 \
3. 密码是否使用安全哈希 \
4. 敏感数据是否已从响应中移除" \
  -w ~/tmp/code-review-demo
```

**修复后再次审查的预期输出：**

```
[SECURITY_REVIEWER] 🔒 安全复查...

✅ 所有 P0 问题已修复
✅ SQL 注入已使用 SQLAlchemy 参数化查询
✅ 危险命令执行接口已删除
✅ 密码使用 werkzeug.security.generate_password_hash()

⚠️ 剩余 P2 优化项：
  💡 建议添加 rate limiting（防暴力破解）
  💡 建议添加登录失败次数限制
  💡 建议使用 HTTPS
```

---

## 💡 关键技巧

**1. 审查单个文件**

```bash
omc agent code-reviewer "审查 src/auth.py"
```

**2. 只看安全问题**

```bash
omc agent security-reviewer "审计整个 src/ 目录的 SQL 注入和 XSS 漏洞"
```

**3. 对比两次 Review 的差异**

```bash
# 修复前先保存审查结果
omc agent code-reviewer "审查 src/auth.py" > /tmp/before_review.txt

# 修复后再次审查
omc agent code-reviewer "审查 src/auth.py" > /tmp/after_review.txt

# 对比
diff /tmp/before_review.txt /tmp/after_review.txt
```

**4. 结合 CI 自动触发**

在 GitHub Actions 中集成 Code Review：

```yaml
# .github/workflows/review.yml
- name: AI Code Review
  run: |
    omc agent code-reviewer "审查 ${{ github.event.pull_request.changed_files }}" \
      --output review.md
    omc agent security-reviewer "审计 ${{ github.event.pull_request.changed_files }}"
```

---

## 📊 Review 效果对比

| 维度 | 手工 Review | oh-my-coder |
|------|------------|-------------|
| 覆盖速度 | 100行/分钟 | 500行/分钟 |
| SQL注入检测 | ⚠️ 依赖经验 | ✅ 自动识别 |
| OWASP Top 10 | ⚠️ 容易遗漏 | ✅ 全量扫描 |
| 修复建议 | ⚠️ 因人而异 | ✅ 给出代码示例 |
| 严重程度分级 | ⚠️ 标准不一 | ✅ CVSS 量化评分 |

**最佳实践**：oh-my-coder 快速扫描 → 人工复核关键安全问题 → 开发者修复 → oh-my-coder 复查确认

---

## 📖 相关资源

- [OWASP Top 10 2023](https://owasp.org/Top10/)
- [Flask 安全最佳实践](https://flask.palletsprojects.com/en/2.3.x/security/)
- [教程一：Flask 项目重构](./flask-restructure.md)
- [教程二：为开源项目写测试](./open-source-test.md)
