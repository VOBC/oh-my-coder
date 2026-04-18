# 安全编码规范

## 核心原则

1. **最小权限原则**：只请求必要的权限
2. **防御性编程**：假设所有输入都是恶意的
3. **安全默认值**：默认配置应该是安全的
4. **深度防御**：多层安全措施

---

## 常见安全问题与修复

### 1. 异常信息泄露

**问题**：`str(e)` 可能泄露敏感信息（API Key、路径、内部结构）

**错误示例**：
```python
except Exception as e:
    error_detail = str(e)  # ❌ 可能泄露敏感信息
```

**正确做法**：
```python
except Exception as e:
    error_detail = type(e).__name__  # ✅ 只暴露类型
    # 或
    error_detail = "Internal server error"  # ✅ 固定消息
    # 或
    error_detail = f"HTTP {e.response.status_code}"  # ✅ 脱敏状态码
```

---

### 2. URL 域名验证

**问题**：`"domain" in url` 可能被绕过（如 `evil-domain.com`）

**错误示例**：
```python
assert "api.deepseek.com" in config.base_url  # ❌ 不安全
```

**正确做法**：
```python
from urllib.parse import urlparse
assert urlparse(config.base_url).netloc == "api.deepseek.com"  # ✅ 精确匹配
# 或
assert urlparse(config.base_url).netloc.endswith(".deepseek.com")  # ✅ 子域名安全
```

---

### 3. 弱加密算法

**问题**：MD5/SHA1 已被证明不安全

**错误示例**：
```python
hashlib.md5(password.encode()).hexdigest()  # ❌ 弱哈希
```

**正确做法**：
```python
# 密码存储：使用 PBKDF2
import hashlib
hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)

# 缓存键/ID生成：SHA256（非密码用途）
hashlib.sha256(content.encode()).hexdigest()[:16]  # ✅ 可接受
```

---

### 4. 命令注入

**问题**：用户输入拼接到 shell 命令

**错误示例**：
```python
os.system(f"cat {filename}")  # ❌ 命令注入风险
```

**正确做法**：
```python
import subprocess
subprocess.run(["cat", filename], check=True)  # ✅ 参数分离
```

---

### 5. 路径遍历

**问题**：用户输入拼接到文件路径

**错误示例**：
```python
path = f"/data/{filename}"  # ❌ 路径遍历风险
```

**正确做法**：
```python
from pathlib import Path
base = Path("/data").resolve()
path = (base / filename).resolve()
if not str(path).startswith(str(base)):
    raise ValueError("Invalid path")  # ✅ 验证路径
```

---

## CodeQL 常见警告

| 警告 | 含义 | 修复 |
|------|------|------|
| `py/weak-cryptographic-algorithm` | 弱加密算法 | MD5 → SHA256 |
| `py/clear-text-logging-sensitive-data` | 敏感数据明文日志 | 脱敏或删除 |
| `py/taint` | 污点分析（输入到危险函数） | 验证输入 |

---

## Checklist

- [ ] 所有异常处理使用 `type(e).__name__` 或固定消息
- [ ] URL 验证使用 `urlparse`
- [ ] 密码存储使用 PBKDF2/bcrypt
- [ ] Shell 命令使用 `subprocess` + 参数列表
- [ ] 文件路径验证 `startswith(base)`
- [ ] 日志不包含敏感信息
- [ ] 所有 workflow 有 `permissions` 声明
