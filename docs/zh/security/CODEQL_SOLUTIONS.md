# CodeQL 解决方案库

本文档记录 CodeQL 扫描发现的问题及其标准修复方案。

---

## 1. py/weak-cryptographic-algorithm

### 问题描述
使用弱加密算法（MD5、SHA1）可能存在安全风险。

### 触发条件
```python
import hashlib
hashlib.md5(data)  # ❌
hashlib.sha1(data)  # ❌
```

### 解决方案

**场景 A：密码存储**
```python
# ❌ 错误
hashed = hashlib.md5(password.encode()).hexdigest()

# ✅ 正确
import secrets
salt = secrets.token_bytes(16)
hashed = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
```

**场景 B：缓存键/ID生成（非密码用途）**
```python
# ⚠️ 可接受（添加注释说明）
# 非密码用途，仅用于缓存键
key = hashlib.sha256(content.encode()).hexdigest()[:16]
```

### 相关文件
- `src/agents/self_improving.py:392`
- `src/utils/performance.py:205`
- `src/rag/indexer.py:234,308`

---

## 2. py/clear-text-logging-sensitive-data

### 问题描述
敏感数据（API Key、密码）以明文形式记录到日志。

### 触发条件
```python
logger.info(f"API Key: {api_key}")  # ❌
print(f"Password: {password}")  # ❌
```

### 解决方案
```python
# ❌ 错误
logger.info(f"API Key: {api_key}")

# ✅ 正确
logger.info("API Key: [REDACTED]")
# 或
logger.info(f"API Key: {api_key[:4]}...{api_key[-4:]}")  # 部分脱敏
```

---

## 3. 异常信息泄露 (str(e))

### 问题描述
`str(e)` 可能包含敏感信息（文件路径、API Key、内部结构）。

### 触发条件
```python
except Exception as e:
    return {"error": str(e)}  # ❌
```

### 解决方案

**场景 A：API 错误响应**
```python
# ❌ 错误
except httpx.HTTPStatusError as e:
    error_detail = str(e)

# ✅ 正确
except httpx.HTTPStatusError as e:
    try:
        error_body = e.response.json()
        error_detail = error_body.get("message", "HTTP error")
    except Exception:
        error_detail = f"HTTP {e.response.status_code}"
```

**场景 B：内部错误记录**
```python
# ❌ 错误
result.error = str(e)

# ✅ 正确
result.error = type(e).__name__  # 只记录类型
# 或
result.error = f"{type(e).__name__}: {str(e)[:200]}"  # 截断
```

---

## 4. URL 域名验证 (in url)

### 问题描述
使用 `in` 操作符验证 URL 域名可被绕过。

### 触发条件
```python
assert "api.deepseek.com" in url  # ❌
# 绕过: "evil-api.deepseek.com.evil.com"
```

### 解决方案
```python
from urllib.parse import urlparse

# ✅ 精确匹配
assert urlparse(url).netloc == "api.deepseek.com"

# ✅ 子域名安全
assert urlparse(url).netloc.endswith(".deepseek.com")

# ✅ 白名单
ALLOWED_DOMAINS = {"api.deepseek.com", "api.openai.com"}
assert urlparse(url).netloc in ALLOWED_DOMAINS
```

---

## 5. py/taint (污点分析)

### 问题描述
用户输入未经净化直接传递到危险函数。

### 触发条件
```python
filename = request.args.get("file")
os.system(f"cat {filename}")  # ❌ 命令注入
```

### 解决方案
```python
import subprocess
import re

filename = request.args.get("file")

# ✅ 验证输入
if not re.match(r'^[\w\-\.]+$', filename):
    raise ValueError("Invalid filename")

# ✅ 使用参数列表
subprocess.run(["cat", filename], check=True)
```

---

## 修复历史

| 日期 | 问题类型 | 文件 | 修复方式 |
|------|----------|------|----------|
| 2026-04-18 | str(e) 泄露 | src/models/*.py | type(e).__name__ |
| 2026-04-18 | MD5 | src/rag/indexer.py | SHA256 |
| 2026-04-18 | in url | tests/test_models/test_glm.py | urlparse |
