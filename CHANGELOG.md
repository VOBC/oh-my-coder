# 更新日志 (Changelog)

所有重要的项目变更都将记录在此文件中。

格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/) 规范。

## [v0.1.0] - 2026-04-04

### 🎉 首次发布

这是 Oh My Coder 的首个公开版本！

### 新增功能

#### 🤖 智能 Agent 系统（18个）

**Build/Analysis Lane（构建/分析通道）**
- `explore` - 代码库探索智能体，快速扫描项目结构
- `analyst` - 需求分析智能体，深度理解需求
- `planner` - 任务规划智能体，制定执行计划
- `architect` - 架构设计智能体，系统设计
- `executor` - 代码实现智能体，功能开发
- `verifier` - 验证测试智能体，质量保证
- `debugger` - 调试修复智能体，问题定位
- `tracer` - 因果追踪智能体，根因分析

**Review Lane（审查通道）**
- `code-reviewer` - 代码审查智能体
- `security-reviewer` - 安全审查智能体

**Domain Lane（领域通道）**
- `test-engineer` - 测试工程师智能体
- `designer` - UI/UX 设计智能体
- `writer` - 文档编写智能体
- `git-master` - Git 操作智能体
- `code-simplifier` - 代码简化智能体
- `scientist` - 数据分析智能体
- `qa-tester` - QA 测试智能体

**Coordination Lane（协调通道）**
- `critic` - 批评家智能体，审查计划

#### 🔌 模型适配器

- **DeepSeek** - 免费额度高，优先使用
- **文心一言** - 百度，中文能力强
- **通义千问** - 阿里，多模型选择

#### ⚙️ 核心功能

- **三层模型路由** - LOW/MEDIUM/HIGH 自动选择
- **智能编排引擎** - 支持顺序/并行/条件执行
- **工作流模板** - build/review/debug/test
- **完整 CLI 工具** - agents/status/run 命令

### 技术特性

- ✅ Python 3.10+ 
- ✅ 异步 API 设计
- ✅ 类型注解完整
- ✅ 统一模型接口
- ✅ 成本控制机制
- ✅ 状态持久化

### 文档

- ✅ README.md - 项目介绍
- ✅ CHANGELOG.md - 更新日志
- ✅ CONTRIBUTING.md - 贡献指南
- ✅ LICENSE - MIT 协议
- ✅ 架构文档 - docs/ARCHITECTURE.md

### 快速开始

```bash
# 克隆项目
git clone <repository-url>
cd oh-my-coder

# 安装依赖
pip install -r requirements.txt

# 配置 API Key
export DEEPSEEK_API_KEY=your_key

# 运行演示
python demo.py
```

### 致谢

- 感谢 [oh-my-claudecode](https://github.com/Yeachan-Heo/oh-my-claudecode) 项目启发
- 感谢 DeepSeek、文心一言、通义千问提供的 API
- 感谢所有测试用户

---

## 版本说明

- **v0.1.0** - 首个公开版本，功能基本完善
- 后续版本将持续优化和增加功能
