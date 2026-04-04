# 演示脚本说明 (Demo Script)

本文档提供 Oh My Coder 演示脚本的文字版说明，用于帮助理解系统功能和演示流程。

---

## 🎬 演示概述

本演示展示 Oh My Coder 的核心功能：
**多智能体协作完成编程任务**

### 演示任务

> 开发一个待办事项 CLI 应用（todo.py）

### 涉及 Agent

1. **Explore Agent** - 探索代码库结构
2. **Analyst Agent** - 分析需求
3. **Executor Agent** - 生成代码

---

## 📺 演示流程

### 第一步：初始化

```
╔════════════════════════════════════════════════════════════════════╗
║                    🎯 Oh My Coder 演示                     ║
║          多智能体协作 - Explore → Analyst → Executor          ║
╚════════════════════════════════════════════════════════════════════╝

✅ Oh My Coder 初始化成功!
   - 模型: DeepSeek
   - 每日预算: ¥10.0
```

**说明：**
- 系统加载 DeepSeek API 配置
- 初始化模型路由器
- 设置每日预算控制

---

### 第二步：Explore Agent（探索）

```
📌 步骤 1/3: Explore Agent - 探索代码库结构
----------------------------------------------------------------------
✅ Explore Agent 执行成功!

探索结果摘要:
----------------------------------------
  # 项目地图：oh-my-coder
  
  ## 1. 项目概览
  
  | 项目属性 | 详细信息 |
  |---------|----------|
  | **主要语言** | Python (100%) |
  | **项目类型** | 多智能体系统 / AI 助手框架 |
  | **项目规模** | 46 个文件，约 7,337 行代码 |
  | **架构风格** | 模块化、基于智能体的架构 |

  ## 2. 技术栈
  
  - FastAPI - Web 框架
  - Uvicorn - ASGI 服务器
  - Pydantic - 数据验证
  - HTTPX - 异步 HTTP 客户端
  - Typer - CLI 框架
  - Rich - 终端美化
```

**Agent 行为：**
1. 扫描项目目录结构
2. 识别文件类型和分布
3. 提取技术栈信息
4. 生成项目地图

**使用的模型层级：** LOW（快速便宜）

---

### 第三步：Analyst Agent（分析）

```
📌 步骤 2/3: Analyst Agent - 分析需求
----------------------------------------------------------------------
✅ Analyst Agent 执行成功!

需求分析摘要:
----------------------------------------

  ### 1. 需求摘要
  开发一个独立的、简单的命令行待办事项管理工具（`todo.py`），
  支持任务的增、删、改、查，并将数据持久化存储到本地 JSON 文件中。

  ### 2. 功能需求
  
  | ID | 描述 | 优先级 | 验收标准 |
  |----|------|--------|----------|
  | F1 | **添加任务** | Must | 1. 命令执行后任务被创建<br>2. 状态为"待办" |
  | F2 | **查看任务列表** | Must | 1. 以表格格式输出<br>2. 显示序号、状态、描述 |
  | F3 | **标记完成** | Must | 1. 更新任务状态<br>2. 错误提示 |
  | F4 | **删除任务** | Must | 1. 移除任务<br>2. 序号重整 |
  | F5 | **数据持久化** | Must | JSON 文件存储 |

  ### 3. 非功能需求
  
  | ID | 类型 | 描述 |
  |----|------|------|
  | NF1 | 性能 | 操作响应 < 100ms |
  | NF2 | 可靠性 | 文件损坏时友好处理 |
  | NF3 | 易用性 | 清晰的错误提示 |

  ### 4. 约束条件
  
  - 技术约束：纯 Python，仅使用标准库
  - 数据格式：JSON 文件
  - 运行环境：独立 CLI 脚本
```

**Agent 行为：**
1. 理解用户需求
2. 识别功能点和优先级
3. 发现隐藏约束
4. 生成验收标准

**使用的模型层级：** HIGH（深度推理）

---

### 第四步：Executor Agent（生成）

```
📌 步骤 3/3: Executor Agent - 生成代码
----------------------------------------------------------------------
✅ Executor Agent 执行成功!

生成的代码:
==================================================

## 实现方案

基于需求分析，实现一个简单的待办事项 CLI 应用。

## 代码变更

### todo.py - 主入口

```python
#!/usr/bin/env python3
"""
待办事项 CLI 应用
支持添加、查看，完成、删除任务
"""

import sys
import argparse
from pathlib import Path

# 导入模块
from src.todo.storage import TodoStorage
from src.todo.logic import TodoManager


def main():
    parser = argparse.ArgumentParser(description="待办事项管理工具")
    subparsers = parser.add_subparsers(dest="command")
    
    # add 命令
    add_parser = subparsers.add_parser("add", help="添加任务")
    add_parser.add_argument("description", help="任务描述")
    
    # list 命令
    subparsers.add_parser("list", help="查看任务")
    
    # done 命令
    done_parser = subparsers.add_parser("done", help="完成任务")
    done_parser.add_argument("index", type=int)
    
    # delete 命令
    delete_parser = subparsers.add_parser("delete", help="删除任务")
    delete_parser.add_argument("index", type=int)
    
    args = parser.parse_args()
    
    # 执行业务逻辑
    storage = TodoStorage()
    manager = TodoManager(storage)
    
    if args.command == "add":
        task = manager.add_task(args.description)
        print(f"✓ 已添加: {task.description}")
    elif args.command == "list":
        tasks = manager.list_tasks()
        for i, task in enumerate(tasks, 1):
            status = "✓" if task.status == "done" else "□"
            print(f"{i}. [{status}] {task.description}")
    elif args.command == "done":
        task = manager.mark_done(args.index)
        print(f"✓ 已完成: {task.description}")
    elif args.command == "delete":
        task = manager.delete_task(args.index)
        print(f"✓ 已删除: {task.description}")


if __name__ == "__main__":
    main()
```

### storage.py - 数据存储

```python
import json
from pathlib import Path
from .models import TodoItem


class TodoStorage:
    def __init__(self):
        self.file_path = Path.home() / ".todo.json"
    
    def load(self):
        if not self.file_path.exists():
            return []
        with open(self.file_path) as f:
            return [TodoItem.from_dict(d) for d in json.load(f)]
    
    def save(self, tasks):
        with open(self.file_path, 'w') as f:
            json.dump([t.to_dict() for t in tasks], f)
```

### models.py - 数据模型

```python
import uuid
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class TodoItem:
    description: str
    status: str = "pending"
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    def to_dict(self):
        return {"id": self.id, "description": self.description, "status": self.status}
    
    @classmethod
    def from_dict(cls, data):
        return cls(**data)
```

## 测试代码

```python
import unittest


class TestTodoManager(unittest.TestCase):
    def test_add_task(self):
        # 测试添加任务
        pass
    
    def test_mark_done(self):
        # 测试完成任务
        pass
```

==================================================

💾 代码已保存到: todo_demo.py
   运行方式: python todo_demo.py
```

**Agent 行为：**
1. 理解需求和设计
2. 编写主入口代码
3. 实现数据存储
4. 定义数据模型
5. 编写测试代码

**使用的模型层级：** MEDIUM（平衡）

---

### 第五步：执行统计

```
📊 执行统计
----------------------------------------------------------------------
   总请求数: 3
   提供商分布: {'deepseek': 3}
   层级分布: {'low': 1, 'medium': 1, 'high': 1}


🎉 演示完成!
```

**统计说明：**
- 3 次 API 请求（每个 Agent 一次）
- 全部使用 DeepSeek（免费优先策略）
- LOW 层级 1 次，MEDIUM 层级 1 次，HIGH 层级 1 次

---

## 🎯 工作流总结

```
┌─────────────────────────────────────────────────────────────────┐
│                        用户输入                                   │
│                   "开发一个待办事项 CLI 应用"                      │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Explore Agent (LOW)                            │
│  🔍 探索代码库结构，识别技术栈                                    │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Analyst Agent (HIGH)                           │
│  📊 分析需求，识别功能点和约束                                    │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Executor Agent (MEDIUM)                        │
│  💻 生成代码和测试                                               │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                        输出代码                                   │
│              todo.py + storage.py + models.py                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 💡 关键特性展示

### 1. 智能路由

系统根据任务类型自动选择合适的模型层级：
- 简单任务 → LOW（节省成本）
- 复杂任务 → HIGH（保证质量）

### 2. Agent 协作

多个 Agent 分工合作：
- Explore：探索环境
- Analyst：理解需求
- Executor：实现功能

### 3. 上下文传递

后续 Agent 可以看到前序 Agent 的输出：
```python
context = AgentContext(
    previous_outputs={'explore': explore_result, 'analyst': analyst_result}
)
```

### 4. 成本控制

DeepSeek API 每日免费 4000 万 token：
- LOW 层级：极低成本
- MEDIUM 层级：中等成本
- HIGH 层级：较高成本（但仍然便宜）

---

## 🚀 扩展演示

### 其他工作流

**代码审查**
```
explore → code-reviewer
```

**调试问题**
```
explore → debugger → verifier
```

**架构设计**
```
explore → analyst → architect → executor
```

### 其他 Agent

| Agent | 层级 | 使用场景 |
|-------|------|---------|
| planner | HIGH | 制定详细计划 |
| architect | HIGH | 系统架构设计 |
| code-reviewer | HIGH | 代码审查 |
| security-reviewer | HIGH | 安全审查 |
| test-engineer | MEDIUM | 测试设计 |
| designer | MEDIUM | UI/UX 设计 |
| verifier | MEDIUM | 功能验证 |
| writer | LOW | 文档编写 |

---

## 📝 演示结束语

> Oh My Coder 将复杂的编程任务分解为多个专业 Agent 的协作，
> 通过智能路由选择最合适的模型，实现高效、低成本的代码生成。

**项目地址：** https://github.com/your-repo/oh-my-coder

---

*演示脚本版本：v0.1.0*
*更新日期：2026-04-04*
