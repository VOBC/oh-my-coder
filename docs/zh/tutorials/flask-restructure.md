# 教程一：用 oh-my-coder 重构 Flask 项目

> **目标**：将一个混乱的 Flask 单文件应用，重构为规范的多模块结构  
> **耗时**：约 10-15 分钟  
> **前置**：已安装 oh-my-coder（参考 [安装指南](../getting-started.md)）

---

## 📋 场景说明

假设你接手了一个旧 Flask 项目，所有代码写在一个 800 行的 `app.py` 里：
路由、数据库模型、业务逻辑、配置全挤在一起，完全无法维护。

**原项目结构：**
```
flask-old/
├── app.py          # 800 行，所有代码混在一起
├── requirements.txt
└── .env
```

**重构目标：**
```
flask-refactored/
├── app/
│   ├── __init__.py    # Flask 工厂模式
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── user.py     # 用户相关路由
│   │   └── order.py    # 订单相关路由
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py
│   │   └── order.py
│   └── services/
│       ├── __init__.py
│       └── biz.py
├── tests/
├── config.py
└── run.py
```

---

## 🚀 开始重构

### 第一步：准备项目

```bash
# 创建测试目录
mkdir -p ~/tmp/flask-test && cd ~/tmp/flask-test

# 模拟一个混乱的 Flask 项目
cat > app.py << 'EOF'
from flask import Flask, request, jsonify
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret')

# ========== 数据库模拟（不要学）==========
_db = []

def get_db():
    return _db

# ========== 路由：用户 ==========
@app.route('/users', methods=['GET'])
def list_users():
    users = get_db()
    return jsonify([{'id': u['id'], 'name': u['name']} for u in users])

@app.route('/users', methods=['POST'])
def create_user():
    data = request.get_json()
    user = {'id': len(get_db()) + 1, 'name': data.get('name', '')}
    get_db().append(user)
    return jsonify(user), 201

@app.route('/users/<int:uid>', methods=['GET'])
def get_user(uid):
    users = get_db()
    user = next((u for u in users if u['id'] == uid), None)
    if not user:
        return jsonify({'error': 'not found'}), 404
    return jsonify(user)

@app.route('/users/<int:uid>', methods=['PUT'])
def update_user(uid):
    data = request.get_json()
    users = get_db()
    user = next((u for u in users if u['id'] == uid), None)
    if not user:
        return jsonify({'error': 'not found'}), 404
    user.update(data)
    return jsonify(user)

@app.route('/users/<int:uid>', methods=['DELETE'])
def delete_user(uid):
    users = get_db()
    for i, u in enumerate(users):
        if u['id'] == uid:
            users.pop(i)
            return '', 204
    return jsonify({'error': 'not found'}), 404

# ========== 路由：订单 ==========
@app.route('/orders', methods=['GET'])
def list_orders():
    return jsonify([])

@app.route('/orders', methods=['POST'])
def create_order():
    data = request.get_json()
    order = {'id': 1, 'user_id': data.get('user_id'), 'amount': data.get('amount', 0)}
    return jsonify(order), 201

# ========== 健康检查 ==========
@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'time': datetime.now().isoformat()})

if __name__ == '__main__':
    app.run(debug=True)
EOF

echo "Flask>=2.0" > requirements.txt
echo "SECRET_KEY=change-me" > .env
```

---

### 第二步：让 oh-my-coder 分析项目

```bash
cd ~/tmp/flask-test

omc run "分析这个 Flask 项目，总结当前代码存在的问题，然后制定重构计划" \
  -w ~/tmp/flask-test
```

**预期输出示例：**

```
🧠 正在分析项目结构...
📊 发现：app.py 共 800 行，路由 7 个，零模块化

🎯 发现以下问题：
1. 所有代码在单文件中，路由/模型/业务逻辑未分离
2. 硬编码数据库（内存字典），无 ORM
3. 错误处理不一致，部分路由返回不同格式的错误
4. 缺少输入验证
5. SECRET_KEY 直接硬编码在代码中

📋 重构计划：
  ✅ P0: 拆分为 app/ 包（工厂模式）
  ✅ P0: 路由按功能拆分到 app/routes/
  ✅ P0: 数据模型拆分到 app/models/
  ✅ P1: 添加输入验证和统一错误处理
  ✅ P1: 配置文件外置（config.py）
```

---

### 第三步：执行重构

```bash
omc run "按照重构计划，将 app.py 重构为标准的多模块 Flask 项目结构：\
1. 创建 app/ 包，使用工厂模式 \
2. 路由拆分到 app/routes/user.py 和 app/routes/order.py \
3. 数据模型拆分到 app/models/ \
4. 添加 app/config.py 配置文件 \
5. 创建 run.py 作为入口 \
6. 创建 tests/ 目录 \
完成后运行 pytest 确认测试通过" \
  -w ~/tmp/flask-test
```

**重构过程中的典型输出：**

```
[EXPLORER] 📁 分析项目结构...
[ARCHITECT] 🏗️ 设计分层架构...
[EXECUTOR] 💻 正在生成代码...

生成文件清单：
  ✅ app/__init__.py      (Flask 工厂)
  ✅ app/routes/__init__.py
  ✅ app/routes/user.py   (用户 CRUD)
  ✅ app/routes/order.py  (订单管理)
  ✅ app/models/__init__.py
  ✅ app/models/user.py
  ✅ app/models/order.py
  ✅ app/config.py
  ✅ run.py
  ✅ tests/test_user.py

[VERIFIER] 🧪 运行测试...
```

---

### 第四步：验证重构结果

```bash
cd ~/tmp/flask-test

# 查看新结构
tree app/ -L 2

# 运行测试
pip install -q flask pytest && pytest tests/ -v
```

**预期输出：**

```
tests/test_user.py::test_health_ok        PASSED
tests/test_user.py::test_create_user      PASSED
tests/test_user.py::test_get_user         PASSED
tests/test_user.py::test_update_user      PASSED
tests/test_user.py::test_delete_user      PASSED
tests/test_user.py::test_user_not_found   PASSED

6 passed in 1.2s
```

对比重构前后的关键差异：

| 维度 | 重构前 | 重构后 |
|------|--------|--------|
| 文件数 | 1 个 | 9 个 |
| app.py 行数 | 800 行 | 40 行（工厂入口） |
| 路由组织 | 扁平混放 | 按功能域拆分 |
| 测试覆盖 | 无 | 6 个用例 |
| 可维护性 | ❌ 差 | ✅ 良好 |

---

## 💡 关键技巧

**1. 重构分步执行**

不要一次性让 Agent 生成所有代码，分步执行更稳定：
```bash
# 第一步：架构设计
omc run "设计重构架构，生成 app/__init__.py 工厂模式"

# 第二步：路由拆分
omc run "将 user 路由拆分到 app/routes/user.py"
```

**2. 指定输出目录**

使用 `-w` 参数指定项目目录，Agent 会自动扫描项目上下文：
```bash
omc run "重构这个项目" -w /path/to/project
```

**3. 查看重构差异**

```bash
# 重构前后对比
diff <(cat app.py) <(find app -name "*.py" -exec cat {} \;)
```

**4. 结合 CodeReview 二次检查**

重构完成后，让 CodeReviewer 审查新代码：
```bash
omc agent code-reviewer "审查 app/routes/user.py 的代码质量"
```

---

## 📖 相关资源

- [Flask 工厂模式最佳实践](https://flask.palletsprojects.com/en/2.3.x/patterns/appfactories/)
- [教程二：为开源项目写测试](./open-source-test.md)
- [教程三：Code Review 实战](./code-review.md)
