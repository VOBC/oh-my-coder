# 常见问题解答 (FAQ)

## 目录
- [安装与配置](#安装与配置)
- [API Key 相关](#api-key-相关)
- [使用问题](#使用问题)
- [错误排查](#错误排查)
- [功能增强](#功能增强)

---

## 安装与配置

### Q1: 如何安装 Oh My Coder？

**A:** 提供三种安装方式：

```bash
# 方式1: pip 安装（推荐）
git clone https://github.com/VOBC/oh-my-coder.git
cd oh-my-coder
pip install -e '.[dev]'

# 方式2: requirements.txt
pip install -r requirements.txt

# 方式3: Docker
docker compose up -d
```

### Q2: 支持哪些 Python 版本？

**A:** 支持 Python 3.9 及以上版本：
- Python 3.9 ✅
- Python 3.10 ✅（推荐）
- Python 3.11 ✅
- Python 3.12 ✅

### Q3: 如何验证安装成功？

**A:** 运行以下命令：

```bash
# 验证 CLI
omc --version

# 运行测试
pytest tests/ -v

# 启动 Web 界面
python -m src.web.app
# 浏览器打开: http://localhost:8000
```

---

## API Key 相关

### Q4: API Key 如何获取？

**A:** 各平台获取方式：

| 平台 | 获取地址 | 备注 |
|------|----------|------|
| DeepSeek | https://platform.deepseek.com/ | 推荐首选 |
| Kimi | https://platform.moonshot.cn/ | 128K 上下文 |
| 豆包 | https://console.volcengine.com/ | 字节出品 |
| 通义千问 | https://dashscope.console.aliyun.com/ | 阿里云 |
| 智谱 GLM | https://open.bigmodel.cn/ | 清华团队 |
| 天工AI | https://model-platform.tiangong.cn/ | 昆仑万维 |
| 百川智能 | https://platform.baichuan-ai.com/ | 王小川创办 |

### Q5: API Key 如何配置？

**A:** 提供三种配置方式：

```bash
# 方式1: 环境变量（推荐）
export DEEPSEEK_API_KEY=your_key_here

# 方式2: .env 文件
echo "DEEPSEEK_API_KEY=your_key_here" > .env

# 方式3: 代码中配置
from src.core.router import RouterConfig
config = RouterConfig(deepseek_api_key="your_key_here")
```

### Q6: API Key 泄露了怎么办？

**A:** 立即执行以下步骤：
1. 登录对应平台，撤销旧 Key
2. 生成新 Key
3. 更新本地配置
4. 检查是否有异常调用记录

**预防措施：**
- 不要将 Key 提交到 Git
- 使用 `.env` 文件并添加到 `.gitignore`
- 定期轮换 API Key

### Q7: 可以同时配置多个 API Key 吗？

**A:** 可以，系统会自动选择：

```bash
# 配置多个 Key
export DEEPSEEK_API_KEY=sk_xxx
export KIMI_API_KEY=sk_yyy
export GLM_API_KEY=sk_zzz
```

系统会按以下优先级选择：
1. 成本最低的可用模型
2. 响应速度最快的模型
3. 任务类型匹配的模型

---

## 使用问题

### Q8: 第一次使用应该做什么？

**A:** 推荐执行流程：

```bash
# 1. 探索项目
omc explore .

# 2. 查看可用 Agent
omc agents

# 3. 执行简单任务测试
omc run "为 utils.py 添加类型注解"

# 4. 查看系统状态
omc status
```

### Q9: CLI 和 Web 界面有什么区别？

**A:** 对比表：

| 特性 | CLI | Web |
|------|-----|-----|
| 适用场景 | 快速操作、脚本集成 | 可视化、调试、演示 |
| 实时反馈 | 文本流 | SSE 动画 |
| 输出格式 | 终端文本 | HTML/JSON |
| 多任务管理 | 单任务 | 多任务并行 |
| 学习曲线 | 需熟悉命令 | 图形化友好 |

### Q10: 如何选择合适的工作流？

**A:** 工作流选择指南：

| 任务类型 | 推荐工作流 | 说明 |
|---------|-----------|------|
| 新功能开发 | `build` | 完整的探索→设计→实现→验证流程 |
| 代码审查 | `review` | 质量+安全双重审查 |
| Bug 修复 | `debug` | 定位→追踪→修复→验证 |
| 测试生成 | `test` | 设计→实现→运行验证 |
| 文档生成 | `build` | 使用 WriterAgent |
| 架构设计 | `build` | 侧重 ArchitectAgent |

### Q11: 任务执行时间过长怎么办？

**A:** 优化建议：

1. **缩小任务范围**
   ```bash
   # 不好的例子
   omc run "重构整个项目"
   
   # 好的例子
   omc run "重构 src/api 模块，使其符合 RESTful 规范"
   ```

2. **使用更快的模型**
   ```bash
   export DEEPSEEK_MODEL=deepseek-chat  # 比 deepseek-reasoner 更快
   ```

3. **分步执行**
   ```bash
   # 先探索
   omc explore .
   
   # 再逐步执行
   omc run "第一步：..." -w build
   ```

---

## 错误排查

### Q12: 提示 "API Key 未配置" 怎么办？

**A:** 检查步骤：

```bash
# 1. 检查环境变量
echo $DEEPSEEK_API_KEY

# 2. 检查 .env 文件
cat .env

# 3. 验证配置
omc status
```

常见原因：
- Key 名称拼写错误
- 未重启终端/IDE
- .env 文件路径错误

### Q13: 模型调用超时怎么办？

**A:** 排查步骤：

```bash
# 1. 检查网络
ping api.deepseek.com

# 2. 增加超时时间
export REQUEST_TIMEOUT=120  # 秒

# 3. 切换模型
export DEEPSEEK_API_KEY=  # 清空
export KIMI_API_KEY=your_key  # 使用备用模型
```

### Q14: 生成的代码有语法错误怎么办？

**A:** 处理流程：

```bash
# 1. 使用 VerifierAgent 验证
omc run "验证生成的代码" -w test

# 2. 请求修复
omc run "修复以下代码的语法错误: ..."

# 3. 使用安全审查
omc run "审查代码质量" -w review
```

### Q15: 测试覆盖率不足怎么办？

**A:** 提升策略：

```bash
# 生成更多测试用例
omc run "为 src/core 模块生成完整的单元测试" -w test

# 使用 TestEngineerAgent
omc run "生成边界条件测试和异常处理测试"
```

---

## 功能增强

### Q16: 如何添加自定义 Agent？

**A:** 三步完成：

```python
# 1. 创建 Agent 类
# src/agents/my_agent.py
from src.agents.base import BaseAgent, AgentResult, AgentContext

class MyAgent(BaseAgent):
    name = "my_agent"
    description = "自定义 Agent"
    default_tier = "medium"

    async def execute(self, context: AgentContext) -> AgentResult:
        # 实现逻辑
        result = await self.generate(prompt)
        return AgentResult(
            agent=self.name,
            status="completed",
            result=result
        )

# 2. 注册到 __init__.py
from .my_agent import MyAgent

__all__ = [..., "MyAgent"]

# 3. 使用
omc run "使用 my_agent 处理任务"
```

### Q17: 如何添加新的模型支持？

**A:** 参考现有实现：

```python
# src/models/my_model.py
from src.models.base import BaseModel, ModelConfig, ModelTier

class MyModel(BaseModel):
    def __init__(self, config: ModelConfig, tier: ModelTier):
        super().__init__(config, tier)
        self.api_base = "https://api.example.com/v1"

    @property
    def model_name(self) -> str:
        return "my-model-v1"

    async def generate(self, messages, **kwargs):
        # 实现 API 调用
        pass

    async def stream(self, messages, **kwargs):
        # 实现流式输出
        pass
```

### Q18: 如何集成到 CI/CD？

**A:** 示例 GitHub Action：

```yaml
name: AI Code Review

on: [pull_request]

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
      - name: Install OMC
        run: pip install -e '.[dev]'
      - name: AI Review
        env:
          DEEPSEEK_API_KEY: ${{ secrets.DEEPSEEK_API_KEY }}
        run: |
          omc run "审查本次 PR 的代码变更" -w review > review_report.md
      - uses: actions/upload-artifact@v4
        with:
          name: review-report
          path: review_report.md
```

### Q19: 如何自定义工作流？

**A:** 修改 `orchestrator.py`：

```python
# 在 WORKFLOW_TEMPLATES 中添加
WORKFLOW_TEMPLATES = {
    "my_workflow": {
        "name": "自定义工作流",
        "steps": [
            {"agent": "explore", "required": True},
            {"agent": "analyst", "required": True},
            {"agent": "my_agent", "required": False},
            {"agent": "verifier", "required": True},
        ],
        "execution_mode": "sequential"
    }
}
```

### Q20: 如何导出执行报告？

**A:** 使用任务总结功能：

```python
from src.core.summary import generate_summary, save_summary

# 任务完成后
summary = generate_summary(
    task="任务描述",
    workflow="build",
    completed_steps=steps
)

# 导出为多种格式
save_summary(summary, format="html")  # HTML 报告
save_summary(summary, format="json")  # JSON 数据
save_summary(summary, format="txt")   # 纯文本
```

---

## 还没找到答案？

- 📖 查看 [完整文档](./)
- 🐛 [提交 Issue](https://github.com/VOBC/oh-my-coder/issues)
- 💬 [参与讨论](https://github.com/VOBC/oh-my-coder/discussions)

---

**最后更新**: 2026-04-08
