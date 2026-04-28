"""
DevOps Agent - CI/CD 与运维自动化智能体

职责：
1. CI/CD 流水线配置（GitHub Actions / GitLab CI）
2. Dockerfile 与容器化
3. 部署脚本编写
4. 监控与告警配置

模型层级：MEDIUM（平衡）
"""

from ..core.router import TaskType
from .base import (
    AgentContext,
    AgentLane,
    AgentOutput,
    AgentStatus,
    BaseAgent,
    register_agent,
)


@register_agent
class DevOpsAgent(BaseAgent):
    """DevOps 与 CI/CD 自动化智能体"""

    name = "devops"
    description = "CI/CD 与 DevOps 智能体 - 流水线配置、容器化、部署"
    lane = AgentLane.DOMAIN
    default_tier = "medium"
    icon = "🚀"
    tools = ["file_read", "file_write"]

    @property
    def system_prompt(self) -> str:
        return """你是一个资深的 DevOps 工程师。

## 角色
你擅长 CI/CD 流水线设计、容器化、自动化部署和运维脚本编写。

## 能力
1. **CI/CD 配置** - GitHub Actions, GitLab CI, Jenkins
2. **容器化** - Dockerfile, docker-compose
3. **部署脚本** - Shell, Ansible, Terraform
4. **监控告警** - Prometheus, Grafana, ELK

## CI/CD 最佳实践

### GitHub Actions 流水线
```yaml
name: CI Pipeline
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run tests
        run: pytest --junitxml=report.xml
```

### Dockerfile 最佳实践
- 使用多阶段构建减少镜像体积
- 合并 RUN 指令减少层数
- 使用 .dockerignore 排除不必要文件
- 以非 root 用户运行容器

```dockerfile
FROM python:3.11-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY . .
ENV PATH=/root/.local/bin:$PATH
CMD ["python", "main.py"]
```

## 输出格式

### 1. CI/CD 流水线
完整的 YAML 配置文件

### 2. Dockerfile
优化的多阶段构建

### 3. 部署检查清单
- 环境变量配置
- 健康检查端点
- 日志收集
- 告警规则
"""

    async def _run(
        self, context: AgentContext, prompt: list[dict[str, str]], **kwargs
    ) -> str:
        """执行 DevOps 配置"""
        if context.previous_outputs.get("architect"):
            prompt.append(
                {
                    "role": "user",
                    "content": f"## 架构设计\n{context.previous_outputs['architect'].result}",
                }
            )

        devops_hint = """

请设计 DevOps 方案：
1. 根据项目语言和框架选择 CI/CD 工具
2. 设计流水线阶段：lint → test → build → deploy
3. 提供完整的 CI/CD 配置文件
4. 如需要，提供 Dockerfile
5. 提供部署脚本或配置

推荐：Python 项目使用 GitHub Actions + Docker
"""
        prompt.append({"role": "user", "content": devops_hint})

        from ..models.base import Message

        messages = [Message(role=msg["role"], content=msg["content"]) for msg in prompt]

        response = await self.model_router.route_and_call(
            task_type=TaskType.SIMPLE_QA,
            messages=messages,
        )

        return response.content

    def _post_process(self, result: str, context: AgentContext) -> AgentOutput:
        """后处理"""
        return AgentOutput(
            agent_name=self.name,
            status=AgentStatus.COMPLETED,
            result=result,
            recommendations=[
                "将 CI/CD 配置保存到 .github/workflows/",
                "测试 Docker 镜像构建",
                "配置 Secrets 环境变量",
            ],
            next_agent="executor",
        )
