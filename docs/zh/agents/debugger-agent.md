# DebuggerAgent - 调试专家 Agent

> Bug 定位、错误分析和修复

## 功能概述

DebuggerAgent 是 oh-my-coder 的调试专家，专门用于：
- 分析错误信息和堆栈跟踪
- 定位 Bug 根因
- 提供修复方案并验证

## 使用场景

### 1. 报错分析

分析代码报错并提供修复方案：

```bash
omc run "修复这个报错" --agent DebuggerAgent --file buggy.py
```

### 2. 逻辑错误定位

定位业务逻辑中的隐藏 Bug：

```bash
omc run "检查这个函数的逻辑错误" --agent DebuggerAgent --file logic.py
```

### 3. 性能问题分析

分析性能瓶颈：

```bash
omc run "分析这个函数的性能问题" --agent DebuggerAgent --file slow.py
```

## 工作流程

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐     ┌─────────────┐
│  错误信息   │ ──▶ │  Debugger    │ ──▶ │  定位根因   │ ──▶ │  修复代码   │
│  /堆栈跟踪  │     │  Agent       │     │             │     │  + 验证     │
└─────────────┘     └──────────────┘     └─────────────┘     └─────────────┘
```

1. **错误解析**：理解错误类型、消息和堆栈跟踪
2. **代码分析**：扫描相关代码，定位问题根因
3. **方案生成**：提供修复方案和代码
4. **验证修复**：运行测试验证修复有效

## 常见错误类型支持

| 错误类型 | 示例 | 支持情况 |
|---------|------|---------|
| 语法错误 | SyntaxError | ✅ 自动修复 |
| 类型错误 | TypeError | ✅ 定位+修复 |
| 索引错误 | IndexError | ✅ 定位+修复 |
| 空值错误 | NoneType / NullPointer | ✅ 定位+修复 |
| 异步错误 | asyncio timeout | ✅ 定位+修复 |
| 内存问题 | Memory leak | ✅ 分析建议 |
| 并发问题 | Race condition | ✅ 分析+建议 |

## 使用方法

### 基本用法

```bash
# 直接分析文件中的错误
omc run "调试 main.py 中的错误" --workflow debug --file main.py

# 指定具体错误信息
omc run "修复 TypeError: 'NoneType' object is not subscriptable" --file app.py
```

### 交互式调试

```bash
# 进入调试模式
omc debug app.py

# 设置断点后分析
omc debug --breakpoint app.py:20
```

## 示例

### 示例 1：修复索引错误

**错误代码：**
```python
def get_user_name(users, user_id):
    return users[user_id]["name"]  # 如果 user_id 不存在会报错
```

**DebuggerAgent 分析：**
```
🔍 问题定位：
- users 字典中不存在 user_id 对应的键
- 缺少对 user_id 存在性的检查

💡 修复方案：
- 添加 if user_id in users 判断
- 或者使用 users.get(user_id) 提供默认值

✅ 建议修复代码：
```python
def get_user_name(users, user_id):
    user = users.get(user_id)
    if user is None:
        return None  # 或者抛出自定义异常
    return user["name"]
```
```

### 示例 2：修复空值错误

**错误代码：**
```python
def process_order(order):
    for item in order["items"]:  # order 可能为 None
        print(item["name"])
```

**DebuggerAgent 分析：**
```
🔍 问题定位：
- order 参数可能为 None
- 直接访问 order["items"] 会导致 TypeError

💡 修复方案：
- 添加空值检查
- 使用 get() 方法提供默认值

✅ 建议修复代码：
```python
def process_order(order):
    if order is None:
        return
    items = order.get("items", [])
    for item in items:
        print(item["name"])
```
```

### 示例 3：修复异步超时

**错误代码：**
```python
async def fetch_data():
    result = await asyncio.wait_for(
        get_data(),
        timeout=5
    )
    return result
```

**DebuggerAgent 分析：**
```
🔍 问题定位：
- wait_for 会在超时后抛出 asyncio.TimeoutError
- 调用方没有处理超时异常

💡 修复方案：
- 添加 try/except 捕获 TimeoutError
- 提供超时后的降级处理

✅ 建议修复代码：
```python
async def fetch_data():
    try:
        result = await asyncio.wait_for(
            get_data(),
            timeout=5
        )
        return result
    except asyncio.TimeoutError:
        logger.warning("获取数据超时，使用缓存数据")
        return get_cached_data()
```
```

## 与其他 Agent 配合

DebuggerAgent 可以与其他 Agent 配合使用：

```
ExploreAgent → DebuggerAgent → ExecutorAgent → VerifierAgent
  (理解代码)   (定位问题)     (应用修复)      (验证修复)
```

## 调试技巧

### 1. 提供完整错误信息

```bash
# 推荐：提供完整错误堆栈
omc run "修复这个错误" --file app.py --error "$(cat error.log)"

# 或者提供错误类型和位置
omc run "修复 app.py 第 42 行的 IndexError" --file app.py
```

### 2. 多次迭代

复杂问题可能需要多次调试：

```bash
# 第一次：初步分析
omc run "分析这个 bug" --file app.py

# 第二次：根据建议修复后再次分析
omc run "验证修复并检查是否有其他问题" --file app.py
```

### 3. 结合测试

```bash
# 修复后运行测试验证
omc run "修复并运行测试" --file app.py --test
```

## 配置选项

DebuggerAgent 可以通过以下配置优化：

```bash
# 设置调试详细程度
omc config set -k DEBUG_VERBOSE -v "true"

# 设置最大分析时间（秒）
omc config set -k DEBUG_TIMEOUT -v "30"

# 设置是否自动修复
omc config set -k DEBUG_AUTO_FIX -v "true"
```

## 相关命令

```bash
# 查看 DebuggerAgent 详情
omc agents list | grep Debug

# 使用 DebuggerAgent
omc run "调试这个错误" --workflow debug --file buggy.py

# 交互式调试
omc debug app.py

# 运行测试
omc test --file app.py
```

## 常见问题

### Q1: 调试时间太长怎么办？
A: 使用 `--timeout` 参数限制调试时间，或者先缩小分析范围。

### Q2: 修复方案不安全？
A: DebuggerAgent 会提供多种方案，包括保守方案和激进方案，请根据实际情况选择。

### Q3: 修复后仍然报错？
A: 可能存在多个关联问题，使用 `omc run "继续调试"` 继续分析。
