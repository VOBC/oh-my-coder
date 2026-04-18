"""
Executor Agent - 代码实现智能体

职责：
1. 代码实现 - 根据设计编写代码
2. 重构 - 改善代码结构
3. Bug 修复 - 定位和修复问题
4. 代码优化 - 性能、可读性、安全性

模型层级：MEDIUM（平衡性能和成本）

工作流程：
1. 理解任务需求
2. 参考架构设计（如有）
3. 分析现有代码（如有相关文件）
4. 实现功能代码
5. 提取并保存代码文件
6. 编写单元测试
"""

import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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
class ExecutorAgent(BaseAgent):
    """
    执行者 Agent - 核心代码实现智能体

    特点：
    - 使用 MEDIUM tier 模型
    - 支持多语言（Python/JavaScript/Go/TypeScript 等）
    - 自动从 LLM 输出中提取代码文件并保存
    - 遵循语言最佳实践和编码规范
    """

    name = "executor"
    description = "执行者智能体 - 代码实现、重构和优化"
    lane = AgentLane.BUILD_ANALYSIS
    default_tier = "medium"
    icon = "💻"
    tools = ["file_read", "file_write", "bash", "test", "git"]

    # 支持的编程语言
    LANGUAGE_EXTENSIONS = {
        "python": [".py"],
        "javascript": [".js"],
        "typescript": [".ts", ".tsx"],
        "jsx": [".jsx", ".tsx"],
        "go": [".go"],
        "rust": [".rs"],
        "java": [".java"],
        "csharp": [".cs"],
        "cpp": [".cpp", ".cc", ".h", ".hpp"],
        "c": [".c", ".h"],
        "ruby": [".rb"],
        "php": [".php"],
        "swift": [".swift"],
        "kotlin": [".kt", ".kts"],
        "shell": [".sh", ".bash"],
        "yaml": [".yaml", ".yml"],
        "json": [".json"],
        "toml": [".toml"],
        "markdown": [".md"],
    }

    @property
    def system_prompt(self) -> str:
        return """你是一个资深的全栈软件工程师。

## 角色
你的职责是根据需求和架构设计，实现高质量的代码。

## 能力
1. **代码实现** - 根据设计编写完整功能代码
2. **重构** - 改善代码结构、提升可读性
3. **Bug 修复** - 定位根因并修复
4. **测试编写** - 单元测试、集成测试

## 工作原则
1. **可读性优先** - 代码要让人看懂，注释清晰
2. **测试驱动** - 先写测试，再写实现（可选）
3. **渐进式** - 小步提交，频繁验证
4. **最佳实践** - 遵循语言惯例和设计模式
5. **安全第一** - 注意安全漏洞（SQL 注入、XSS、密码明文等）

## 编码规范
- **Python**: PEP 8 + 类型注解 + docstring
- **JavaScript/TypeScript**: ESLint + Prettier + JSDoc
- **Go**: gofmt + Effective Go + 错误处理
- **Rust**: clippy + cargo fmt

## 输出格式（重要）

### 方案说明
简要描述实现思路和技术选型

### 代码文件
用 markdown 代码块标记，格式：` ```language:path/to/file.ext `

示例：
```python:src/calculator.py
class Calculator:
    def add(self, a: int, b: int) -> int:
        return a + b
```

```javascript:src/utils/helper.js
export function formatDate(date) {
    return date.toISOString().split('T')[0];
}
```

### 测试代码
用 `test:` 前缀标记测试文件
```python:tests/test_calculator.py
def test_add():
    calc = Calculator()
    assert calc.add(1, 2) == 3
```

### 注意事项
- 任何需要特殊配置的依赖
- 可能的边界情况
- 向后兼容性考虑
"""

    async def _run(
        self,
        context: AgentContext,
        prompt: List[Dict[str, str]],
        **kwargs,
    ) -> str:
        """执行代码实现"""
        # 1. 添加前序输出（架构设计等）
        self._inject_previous_outputs(context, prompt)

        # 2. 读取相关文件
        self._inject_relevant_files(context, prompt)

        # 3. 添加实现指导
        prompt.append(
            {
                "role": "user",
                "content": self._build_implementation_hint(context),
            }
        )

        # 4. 调用模型
        from ..models.base import Message

        messages = [Message(role=msg["role"], content=msg["content"]) for msg in prompt]

        response = await self.model_router.route_and_call(
            task_type=TaskType.CODE_GENERATION,
            messages=messages,
            complexity="medium",
        )

        return response.content

    def _inject_previous_outputs(
        self, context: AgentContext, prompt: List[Dict[str, str]]
    ) -> None:
        """注入前序 Agent 的输出"""
        outputs = context.previous_outputs
        parts = []

        if outputs.get("architect"):
            parts.append(f"## 架构设计\n{outputs['architect'].result}")

        if outputs.get("analyst"):
            parts.append(f"## 需求分析\n{outputs['analyst'].result}")

        if parts:
            prompt.append({"role": "user", "content": "\n\n".join(parts)})

    def _inject_relevant_files(
        self, context: AgentContext, prompt: List[Dict[str, str]]
    ) -> None:
        """注入相关文件内容"""
        files = context.relevant_files or []
        if not files:
            # 自动查找相关文件
            files = self._find_relevant_files(
                context.project_path, context.task_description
            )

        if not files:
            return

        parts = ["## 相关文件\n"]
        for file_path in files[:8]:  # 最多 8 个文件
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read(3000)  # 限制每个文件 3000 字符
                    rel_path = file_path.relative_to(context.project_path)
                    parts.append(f"\n### {rel_path}\n```\n{content}\n```")
            except Exception:
                pass

        if len(parts) > 1:
            prompt.append({"role": "user", "content": "\n".join(parts)})

    def _find_relevant_files(
        self, project_path: Path, task_description: str
    ) -> List[Path]:
        """根据任务描述智能查找相关文件"""
        relevant = []
        keywords = task_description.lower()

        # 简单关键词匹配
        file_patterns = []
        if any(
            k in keywords for k in ["用户", "user", "认证", "auth", "登录", "login"]
        ):
            file_patterns.extend(["auth", "user", "login", "signup"])
        if any(k in keywords for k in ["api", "rest", "接口"]):
            file_patterns.extend(["api", "route", "endpoint"])
        if any(k in keywords for k in ["数据库", "db", "数据库", "model"]):
            file_patterns.extend(["model", "db", "database", "schema"])

        if not file_patterns:
            return []

        for root, _, files in (
            project_path.walk() if hasattr(project_path, "walk") else []
        ):
            for f in files:
                if any(p in f.lower() for p in file_patterns) and f.endswith(
                    (".py", ".js", ".ts", ".go")
                ):
                    relevant.append(root / f)

        return relevant[:8]

    def _build_implementation_hint(self, context: AgentContext) -> str:
        """构建实现提示"""
        hint = []

        hint.append("\n## 实现要求")
        hint.append("请根据以上信息和任务描述，实现所需功能。")
        hint.append("")
        hint.append("注意：")
        hint.append(
            "1. 使用 markdown 代码块标记文件路径，"
            "格式：` ```language:path/to/file.ext `"
        )
        hint.append("2. 代码块中的第一行必须是文件路径（相对于项目根目录）")
        hint.append("3. 每个主要文件单独一个代码块")
        hint.append("4. 测试文件用 `test:` 前缀标记，如 `test:tests/test_feature.py`")
        hint.append("5. 保持代码简洁，添加必要的类型注解和注释")
        hint.append("6. 遵循语言的 PEP/风格规范")

        # 如果有特定语言要求
        task_lower = context.task_description.lower()
        if "fastapi" in task_lower or "python" in task_lower:
            hint.append("\n提示：检测到 Python 项目，建议使用 FastAPI 框架。")
        elif "react" in task_lower or "前端" in task_lower:
            hint.append("\n提示：检测到前端项目，建议使用 React + TypeScript。")

        return "\n".join(hint)

    def _post_process(
        self,
        result: str,
        context: AgentContext,
    ) -> AgentOutput:
        """后处理 - 提取代码并保存到文件"""
        artifacts: Dict[str, Any] = {}
        saved_files: List[str] = []
        errors: List[str] = []

        # 1. 提取代码文件
        code_blocks = self._extract_code_blocks(result)

        # 2. 保存代码文件
        for file_path, code_content in code_blocks:
            try:
                # 清理路径
                clean_path = file_path.strip().lstrip("/")
                target_path = context.project_path / clean_path

                # 创建目录
                target_path.parent.mkdir(parents=True, exist_ok=True)

                # 保存文件
                with open(target_path, "w", encoding="utf-8") as f:
                    f.write(code_content)

                saved_files.append(clean_path)
                artifacts[clean_path] = {
                    "type": "code",
                    "path": clean_path,
                    "lines": len(code_content.splitlines()),
                    "size": len(code_content),
                }

            except Exception as e:
                errors.append(f"保存 {file_path} 失败: {e}")

        # 3. 尝试格式化代码（如果可用）
        self._try_format_code(context.project_path, saved_files)

        # 4. 尝试运行测试（如果写了测试）
        test_result = self._try_run_tests(context.project_path, saved_files)

        # 5. 构建推荐后续步骤
        recommendations = []
        if saved_files:
            recommendations.append(f"已保存 {len(saved_files)} 个代码文件")
        if test_result["ran"]:
            if test_result["passed"]:
                recommendations.append("✅ 所有测试通过")
            else:
                recommendations.append(f"⚠️ 测试有问题: {test_result['output'][:200]}")
        recommendations.extend(
            [
                "使用 verifier Agent 验证实现",
                "使用 code-reviewer Agent 审查代码",
            ]
        )

        return AgentOutput(
            agent_name=self.name,
            status=AgentStatus.COMPLETED,
            result=result,
            artifacts=artifacts,
            recommendations=recommendations,
            next_agent="verifier",
        )

    def _extract_code_blocks(self, content: str) -> List[Tuple[str, str]]:
        """
        从 LLM 输出中提取代码块

        支持格式：
        - ```python:path/to/file.py
        - ```:path/to/file.py
        - ```python
          # path/to/file.py
        """
        blocks: List[Tuple[str, str]] = []
        lines = content.splitlines()
        i = 0

        while i < len(lines):
            line = lines[i].strip()

            # 匹配代码块开始
            if line.startswith("```") and not line.startswith("```:"):
                # 格式: ```python:path/to/file.py 或 ```path/to/file.py
                match = re.match(r"```(\w+)?:?\s*(.+)?", line)
                if match:
                    _ = match.group(1) or ""  # lang, unused
                    file_path = match.group(2) or ""
                    if not file_path:
                        # 尝试从下一行获取路径
                        if (
                            i + 1 < len(lines)
                            and not lines[i + 1].startswith("#")
                            and not lines[i + 1].startswith("```")
                        ):
                            file_path = lines[i + 1].strip()
                            i += 1
                else:
                    _, file_path = "", ""

                if file_path and not file_path.startswith("#"):
                    # 收集代码内容
                    code_lines = []
                    i += 1
                    while i < len(lines) and not lines[i].startswith("```"):
                        code_lines.append(lines[i])
                        i += 1

                    code_content = "\n".join(code_lines).strip()
                    if code_content:
                        blocks.append((file_path, code_content))
                    continue

            elif line.startswith("```"):
                # 可能是 ```:path/to/file.py 格式
                match = re.match(r"```:?\s*(.+)", line)
                if match:
                    file_path = match.group(1).strip()
                    if file_path and not file_path.startswith("```"):
                        code_lines = []
                        i += 1
                        while i < len(lines) and not lines[i].startswith("```"):
                            code_lines.append(lines[i])
                            i += 1
                        code_content = "\n".join(code_lines).strip()
                        if code_content:
                            blocks.append((file_path, code_content))
                        continue

            i += 1

        return blocks

    def _try_format_code(
        self, project_path: Path, saved_files: List[str]
    ) -> Dict[str, Any]:
        """尝试格式化代码"""
        result = {"formatted": [], "errors": []}

        for file_path in saved_files:
            full_path = project_path / file_path
            if not full_path.exists():
                continue

            ext = full_path.suffix
            formatter: Optional[List[str]] = None

            if ext == ".py":
                formatter = ["black", "--quiet", str(full_path)]
            elif ext in (".js", ".ts", ".jsx", ".tsx"):
                formatter = ["npx", "prettier", "--write", str(full_path)]
            elif ext == ".go":
                formatter = ["gofmt", "-w", str(full_path)]

            if formatter:
                try:
                    subprocess.run(
                        formatter,
                        capture_output=True,
                        timeout=30,
                        check=False,
                    )
                    result["formatted"].append(file_path)
                except Exception:
                    pass

        return result

    def _try_run_tests(
        self, project_path: Path, saved_files: List[str]
    ) -> Dict[str, Any]:
        """尝试运行测试"""
        result = {
            "ran": False,
            "passed": False,
            "output": "",
            "tests_run": 0,
            "tests_failed": 0,
        }

        # 检查是否有测试文件被保存
        test_files = [f for f in saved_files if "test_" in f or f.startswith("tests/")]

        if not test_files:
            return result

        result["ran"] = True

        # 检查 pytest 是否可用
        try:
            subprocess.run(
                ["python3", "-m", "pytest", "--version"],
                capture_output=True,
                timeout=5,
                check=True,
            )
        except Exception:
            return result

        # 运行测试
        try:
            proc = subprocess.run(
                ["python3", "-m", "pytest", "-v", "--tb=short"],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=str(project_path),
            )
            result["output"] = proc.stdout + proc.stderr
            result["passed"] = proc.returncode == 0

            # 解析测试数量
            match = re.search(r"(\d+) passed", proc.stdout)
            if match:
                result["tests_run"] = int(match.group(1))
            match = re.search(r"(\d+) failed", proc.stdout)
            if match:
                result["tests_failed"] = int(match.group(1))

        except Exception as e:
            result["output"] = f"Error: {type(e).__name__}"

        return result
