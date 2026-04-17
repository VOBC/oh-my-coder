# Bug 修复工作流

## 模板信息
- **名称**: bug-fix
- **类别**: workflow
- **适用场景**: 线上问题排查、Bug 定位与修复、回归测试
- **预计时间**: 20-40 分钟

## 工作流定义

```yaml
name: bug-fix
description: Bug 定位与修复工作流 - 分析、定位、修复、验证
version: 1.0.0

steps:
  - agent: explorer
    description: 复现问题，收集日志和上下文
    timeout: 180
    
  - agent: debugger
    description: 分析错误日志，定位根因
    dependencies: [explorer]
    timeout: 300
    
  - agent: executor
    description: 实施修复方案
    dependencies: [debugger]
    timeout: 240
    
  - agent: verifier
    description: 验证修复效果，执行回归测试
    dependencies: [executor]
    timeout: 180
    
  - agent: documentor
    description: 记录问题和解决方案
    dependencies: [verifier]
    timeout: 60

environment:
  log_level: DEBUG
  capture_screenshots: true
```

## 使用说明

### 快速开始

```bash
omc template use bug-fix --task "修复用户登录时出现 500 错误的问题"
```

### 带错误日志

```bash
omc run debug --task "API 返回空数据" --context "错误日志: TypeError in /api/users"
```

### 预期产出

1. **问题分析报告**
   - 错误现象描述
   - 根因分析
   - 影响范围评估

2. **修复补丁**
   - 代码变更 diff
   - 相关测试用例
   - 部署说明

3. **验证报告**
   - 测试结果
   - 回归测试通过率
   - 性能对比

## Bug 分类处理

### 1. 逻辑错误

```
现象: 代码能运行但结果不正确
策略: 
  1. 复现问题，记录输入输出
  2. 分析数据流，定位错误逻辑
  3. 编写测试用例覆盖边界情况
  4. 修复并验证
```

### 2. 运行时错误

```
现象: 代码抛出异常或崩溃
策略:
  1. 收集完整堆栈信息
  2. 定位抛出异常的代码位置
  3. 分析触发条件
  4. 添加防护代码或修复根因
```

### 3. 性能问题

```
现象: 响应慢、内存占用高
策略:
  1. 性能分析（profiling）
  2. 识别瓶颈函数
  3. 优化算法或数据结构
  4. 基准测试验证
```

### 4. 安全漏洞

```
现象: 存在攻击风险
策略:
  1. 评估漏洞严重程度
  2. 立即修复核心问题
  3. 加固相关代码
  4. 安全测试验证
```

## 调试技巧

### 日志分析

```python
# 添加调试日志
import logging
logger = logging.getLogger(__name__)

def problematic_function(data):
    logger.debug(f"Input data: {data}")
    # ... 业务逻辑
    logger.debug(f"Intermediate result: {result}")
    return result
```

### 单元测试定位

```python
def test_bug_case():
    """复现 Bug 的测试用例"""
    input_data = {"user_id": "abc123"}  # 触发 Bug 的输入
    result = process_user(input_data)
    assert result is not None  # 原本会失败
    assert result["status"] == "success"
```

### 断点调试

```python
# 使用 pdb 断点
import pdb

def buggy_function():
    # ... 代码
    pdb.set_trace()  # 断点
    # ... 可疑代码
```

## 修复最佳实践

### ✅ 推荐做法

1. **先复现，后修复**
   - 编写能复现问题的测试用例
   - 理解问题根因后再动手

2. **最小化变更**
   - 只修复必要的代码
   - 避免引入新功能

3. **添加测试**
   - 为修复添加回归测试
   - 确保未来不会再次出现

4. **文档记录**
   - 记录问题原因
   - 记录修复方案

### ❌ 避免做法

1. **盲目修改** - 不理解就改代码
2. **掩盖问题** - 只处理表象，不治根因
3. **过度重构** - 修 Bug 顺便重构代码
4. **跳过测试** - 认为小程序不需要测试

## 问题记录模板

```markdown
## Bug #XXX: [简短描述]

### 环境
- 版本: v1.2.3
- 平台: macOS / Linux / Windows
- 浏览器: Chrome 120

### 现象
[详细描述问题表现]

### 复现步骤
1. 步骤一
2. 步骤二
3. ...

### 期望结果
[正确的行为应该是...]

### 实际结果
[实际发生了什么...]

### 根因分析
[技术层面的原因]

### 修复方案
[采用的解决方案]

### 验证方法
[如何验证修复成功]
```

## 相关资源

- [Debugging Guide](https://medium.com/@alexgolec/how-to-debug-any-program-93710e758fd5)
- [Python 调试技巧](https://realpython.com/python-debugging-pdb/)
- [故障排查流程](https://sre.google/sre-book/troubleshooting-down-the-stack/)
