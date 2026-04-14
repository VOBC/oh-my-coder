# 教程二：为开源项目写测试

> **目标**：为一个真实的开源 Python 库编写完整的测试套件  
> **耗时**：约 15-20 分钟  
> **前置**：已安装 oh-my-coder，有一个需要测试的开源项目

---

## 📋 场景说明

你 fork 了一个开源项目，发现它缺少测试，或者测试覆盖率极低。作为贡献者，你希望为它补充测试。

本文用一个**简化版的工具库**作为示例，演示如何用 oh-my-coder 从零构建测试套件。

**示例项目结构（待测试）：**

```
my-toolkit/
├── src/
│   └── toolkit/
│       ├── __init__.py
│       ├── calculator.py     # 计算器（纯函数）
│       ├── text_utils.py     # 文本处理工具
│       └── validator.py      # 数据校验器
├── requirements.txt
└── README.md
```

---

## 🚀 开始写测试

### 第一步：创建示例项目

```bash
mkdir -p ~/tmp/my-toolkit/src/toolkit
cd ~/tmp/my-toolkit

cat > src/toolkit/__init__.py << 'EOF'
from .calculator import add, subtract, multiply, divide
from .text_utils import truncate, word_count, slugify
from .validator import is_email, is_url, is_phone

__all__ = [
    "add", "subtract", "multiply", "divide",
    "truncate", "word_count", "slugify",
    "is_email", "is_url", "is_phone",
]
EOF

cat > src/toolkit/calculator.py << 'EOF'
"""简单计算器工具。"""


def add(a, b):
    """返回 a + b"""
    return a + b


def subtract(a, b):
    """返回 a - b"""
    return a - b


def multiply(a, b):
    """返回 a * b"""
    return a * b


def divide(a, b):
    """返回 a / b，b 不能为 0"""
    if b == 0:
        raise ValueError("除数不能为 0")
    return a / b
EOF

cat > src/toolkit/text_utils.py << 'EOF'
"""文本处理工具。"""
import re


def truncate(text, max_length, suffix="..."):
    """截断文本，超过 max_length 的部分用 suffix 替代"""
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix


def word_count(text):
    """统计单词数量（英文，按空格/空白分隔）"""
    return len(text.split())


def slugify(text):
    """将文本转为 URL 友好的 slug"""
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[-\s]+", "-", text)
    return text.strip("-")
EOF

cat > src/toolkit/validator.py << 'EOF'
"""数据校验工具。"""
import re


def is_email(value: str) -> bool:
    """校验是否为合法邮箱格式"""
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, value))


def is_url(value: str) -> bool:
    """校验是否为合法 URL"""
    pattern = r"^https?://[^\s/$.?#].[^\s]*$"
    return bool(re.match(pattern, value))


def is_phone(value: str) -> bool:
    """校验是否为合法手机号（中国大陆 11 位）"""
    pattern = r"^1[3-9]\d{9}$"
    return bool(re.match(pattern, value))
EOF

cat > requirements.txt << 'EOF'
pytest>=7.0.0
EOF
```

---

### 第二步：让 oh-my-coder 分析项目并规划测试

```bash
cd ~/tmp/my-toolkit

omc run "分析 src/toolkit/ 目录下的代码，总结每个模块的函数签名和功能，\
然后制定测试计划（列出每个函数需要测试的用例）" \
  -w ~/tmp/my-toolkit
```

**预期输出示例：**

```
[EXPLORER] 📁 扫描项目结构...
  发现 3 个模块：
    - calculator.py   (add, subtract, multiply, divide)
    - text_utils.py   (truncate, word_count, slugify)
    - validator.py    (is_email, is_url, is_phone)

[ANALYST] 📊 分析测试需求...
  calculator.py:
    ✅ add: 正常相加、负数相加、浮点数相加、类型边界
    ✅ subtract: 正常相减、借位、负数结果
    ✅ multiply: 正常相乘、零、负数
    ✅ divide: 正常除法、浮点结果、除零异常

  text_utils.py:
    ✅ truncate: 正常截断、恰好等于长度、不需截断、自定义后缀
    ✅ word_count: 正常计数、空字符串、单字
    ✅ slugify: 正常转换、空格替换、特殊字符过滤

  validator.py:
    ✅ is_email: 合法邮箱、非法格式、无@、无域名
    ✅ is_url: 合法 https、非法协议、无域名
    ✅ is_phone: 合法号段、非法位数、非法首位
```

---

### 第三步：生成测试文件

```bash
omc run "为 src/toolkit/ 目录下的所有模块生成完整的 pytest 测试套件：\
1. 在 tests/ 目录下创建 test_calculator.py、test_text_utils.py、test_validator.py \
2. 每个测试文件使用 pytest 风格 \
3. 覆盖所有公开函数，包含边界用例 \
4. 包含正确的 fixture 和 setup \
5. 运行 pytest tests/ 确认全部通过" \
  -w ~/tmp/my-toolkit
```

**生成测试的典型输出：**

```
[TEST_ENGINEER] 🧪 开始生成测试...

  生成文件：tests/test_calculator.py
  生成文件：tests/test_text_utils.py
  生成文件：tests/test_validator.py

[EXECUTOR] 💻 写入测试文件...

[VERIFIER] ✅ 运行测试...

tests/test_calculator.py::test_add_positive        PASSED
tests/test_calculator.py::test_add_negative         PASSED
tests/test_calculator.py::test_add_float            PASSED
tests/test_calculator.py::test_divide_by_zero       PASSED
tests/test_text_utils.py::test_truncate_normal     PASSED
tests/test_text_utils.py::test_slugify_chinese      PASSED
tests/test_validator.py::test_is_email_valid        PASSED
tests/test_validator.py::test_is_phone_china        PASSED
...
15 passed in 0.8s ✅
```

---

### 第四步：检查测试覆盖率

```bash
cd ~/tmp/my-toolkit
pip install pytest-cov -q

pytest tests/ --cov=src.toolkit --cov-report=term-missing -v
```

**覆盖率报告示例：**

```
Name                 Stmts   Miss  Cover   Missing
------------------------------------------------------
src/toolkit/__init__      1      0   100%
src/toolkit/calculator   15      0   100%
src/toolkit/text_utils   20      2    90%   slugify 中文处理
src/toolkit/validator    18      0   100%
------------------------------------------------------
TOTAL                 54      2    96%
```

---

## 💡 关键技巧

**1. 补充边界用例**

生成的测试通过后，手动补充一些边界用例：

```python
# 在 test_validator.py 中补充
def test_is_phone_edge_cases():
    assert is_phone("13812340000") is True
    assert is_phone("0123456789") is False   # 10位
    assert is_phone("23812340000") is False   # 2开头非法
    assert is_phone("138123400001") is False  # 12位
    assert is_phone("") is False               # 空字符串
```

**2. Mock 外部依赖**

如果被测代码有 I/O 操作（网络请求、文件读写），先让 Agent 识别，再补充 mock：

```bash
omc run "检查 src/toolkit/ 中是否有外部 I/O 依赖（网络、文件），\
如果有，生成带 unittest.mock 的测试用例" \
  -w ~/tmp/my-toolkit
```

**3. 查看生成的测试内容**

```bash
cat tests/test_calculator.py
```

**4. 指定测试框架**

如果项目使用 `unittest` 而非 `pytest`，在 prompt 中明确指定：

```bash
omc run "使用 unittest 框架生成测试（不要 pytest），\
目标目录 tests/" -w /path/to/project
```

---

## 📊 测试生成质量对比

| 维度 | 手动编写 | oh-my-coder 生成 |
|------|----------|-----------------|
| 基础用例覆盖 | ✅ | ✅ |
| 边界值测试 | ⚠️ 易遗漏 | ✅ 自动生成 |
| 异常路径测试 | ⚠️ 易遗漏 | ✅ |
| Mock 外部依赖 | ✅ 熟练后可做 | ⚠️ 需要人工补充 |
| 测试可读性 | ⚠️ 依赖经验 | ✅ 结构清晰 |

**最佳实践**：oh-my-coder 生成初版 → 人工审查边界用例 → 补充 mock → 最终运行确认

---

## 📖 相关资源

- [pytest 官方文档](https://docs.pytest.org/)
- [测试覆盖率工具 Coverage.py](https://coverage.readthedocs.io/)
- [教程一：Flask 项目重构](./flask-restructure.md)
- [教程三：Code Review 实战](./code-review.md)
