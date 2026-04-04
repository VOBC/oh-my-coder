# 贡献指南

感谢您对 Oh My Coder 的兴趣！我们欢迎各种形式的贡献。

## 📋 目录

- [行为准则](#行为准则)
- [如何贡献](#如何贡献)
- [开发环境](#开发环境)
- [代码规范](#代码规范)
- [提交规范](#提交规范)
- [测试](#测试)
- [文档](#文档)
- [问题反馈](#问题反馈)
- [功能建议](#功能建议)

---

## 🤝 行为准则

我们承诺为所有参与者提供一个友好、安全的环境。请：

- 使用友好和包容的语言
- 尊重不同的观点和经验
- 优雅地接受建设性的批评
- 关注什么对社区最有利
- 对其他社区成员表现出同理心

## 🔧 如何贡献

### 报告 Bug

如果您发现了 Bug，请：

1. 在 GitHub Issues 中搜索是否已有类似问题
2. 如果没有，创建一个新的 Issue
3. 使用 Bug 报告模板，提供：
   - 清晰的标题和描述
   - 复现步骤
   - 预期行为 vs 实际行为
   - 环境信息（Python 版本、操作系统等）
   - 相关的错误日志

### 修复 Bug

1. Fork 本仓库
2. 创建分支：`git checkout -b fix/bug-description`
3. 编写修复代码
4. 添加或更新测试
5. 确保所有测试通过
6. 提交代码并发起 Pull Request

### 添加新功能

1. 在 GitHub Issues 中创建一个 Feature Request
2. 讨论功能设计的可行性
3. 获得认可后，创建分支：`git checkout -b feat/feature-name`
4. 实现功能
5. 添加完整的测试和文档
6. 提交代码并发起 Pull Request

---

## 💻 开发环境

### 前置要求

- Python 3.10 或更高版本
- Git
- DeepSeek API Key（用于测试）

### 设置开发环境

```bash
# 1. Fork 并克隆仓库
git clone https://github.com/your-username/oh-my-coder.git
cd oh-my-coder

# 2. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 3. 安装依赖
pip install -r requirements.txt

# 4. 设置环境变量
cp .env.example .env
# 编辑 .env 文件，填入 API Key

# 5. 验证安装
python -m src.cli agents
```

---

## 📝 代码规范

### Python 代码规范

我们遵循以下规范：

- **PEP 8** - Python 代码规范
- **类型注解** - 所有函数必须包含类型注解
- **文档字符串** - 所有公开函数必须有文档字符串

### 代码示例

```python
from typing import List, Optional


def process_data(
    data: List[str],
    options: Optional[dict] = None
) -> dict:
    """
    处理数据并返回结果。
    
    Args:
        data: 输入数据列表
        options: 可选配置参数
        
    Returns:
        包含处理结果的字典
        
    Raises:
        ValueError: 当数据为空时抛出
    """
    if not data:
        raise ValueError("数据不能为空")
    
    result = {
        "count": len(data),
        "options": options or {}
    }
    
    return result
```

### 命名规范

| 类型 | 规范 | 示例 |
|------|------|------|
| 模块 | 小写下划线 | `model_router.py` |
| 类 | 大写驼峰 | `class ExploreAgent` |
| 函数 | 小写下划线 | `def process_data()` |
| 常量 | 全大写下划线 | `MAX_RETRY = 3` |
| 变量 | 小写下划线 | `user_name` |

---

## 📤 提交规范

### 提交格式

```
<类型>(<范围>): <描述>

[可选的详细描述]

[可选的脚注]
```

### 类型

| 类型 | 描述 |
|------|------|
| `feat` | 新功能 |
| `fix` | Bug 修复 |
| `docs` | 文档更新 |
| `style` | 代码格式（不影响功能）|
| `refactor` | 重构（不影响功能）|
| `test` | 测试相关 |
| `chore` | 构建/工具变更 |

### 示例

```bash
# 新功能
git commit -m "feat(agents): 添加 Scientist Agent

- 实现数据分析功能
- 支持统计分析和可视化建议
- 添加相关测试"

# Bug 修复
git commit -m "fix(router): 修复网络超时问题

- 增加重试机制
- 调整超时配置
- 添加单元测试"

# 文档更新
git commit -m "docs: 更新 README

- 添加快速开始指南
- 更新安装说明"
```

---

## 🧪 测试

### 运行测试

```bash
# 运行所有测试
python -m pytest tests/

# 运行特定测试
python -m pytest tests/test_router.py

# 查看覆盖率
python -m pytest tests/ --cov=src
```

### 编写测试

```python
import pytest
from src.models.base import ModelConfig, ModelTier


class TestModelConfig:
    """测试模型配置"""
    
    def test_default_values(self):
        """测试默认值"""
        config = ModelConfig(api_key="test_key")
        
        assert config.max_tokens == 4096
        assert config.temperature == 0.7
        assert config.timeout == 60.0
    
    def test_custom_values(self):
        """测试自定义值"""
        config = ModelConfig(
            api_key="test_key",
            max_tokens=8192,
            temperature=0.5
        )
        
        assert config.max_tokens == 8192
        assert config.temperature == 0.5
```

### 测试覆盖率要求

- 核心模块：80%+
- Agent 模块：70%+
- 工具函数：60%+

---

## 📚 文档

### 文档位置

- `README.md` - 项目主页文档
- `docs/` - 详细技术文档
- `CHANGELOG.md` - 更新日志
- 代码内文档字符串

### 文档规范

- 使用中文编写
- Markdown 格式
- 代码示例使用三个反引号
- 保持简洁明了

---

## 🐛 问题反馈

### 创建 Issue

请使用以下模板：

```markdown
## Bug 描述
清晰描述 Bug

## 环境信息
- Python 版本：
- 操作系统：
- 项目版本：

## 复现步骤
1. 
2. 
3. 

## 预期行为
描述期望的行为

## 实际行为
描述实际发生的行为

## 错误日志
如果有，粘贴错误日志
```

---

## 💡 功能建议

### 创建 Feature Request

```markdown
## 功能描述
清晰描述建议的功能

## 使用场景
描述这个功能的使用场景

## 解决方案
如果有建议的实现方案

## 替代方案
是否有其他解决方案
```

---

## 📄 Pull Request 流程

1. Fork 仓库
2. 创建特性分支
3. 提交更改
4. 推送到分支
5. 打开 Pull Request
6. 等待代码审查
7. 合并到主分支

### Pull Request 模板

```markdown
## 描述
简要描述这个 PR

## 类型
- [ ] 新功能
- [ ] Bug 修复
- [ ] 文档更新
- [ ] 重构

## 测试
- [ ] 添加了测试
- [ ] 所有测试通过

## 截图
如果有 UI 变更，添加截图
```

---

## 📞 联系方式

- GitHub Issues: [链接](https://github.com/your-repo/issues)
- 邮箱: your-email@example.com

---

再次感谢您的贡献！ 🎉
