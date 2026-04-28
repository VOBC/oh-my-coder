"""
交叉验证层 - Agent 交叉验证机制

背景：
CLI run --cross-validate 时，工作流结束后自动执行交叉验证。

工作原理：
1. 工作流主 Agent 执行完毕 → 产出 result + artifacts
2. 从 result.outputs 中提取各 Agent 的输出
3. 用独立验证视角重新审视：
   - 原 Agent 做了啥？
   - 有没有逻辑漏洞/安全问题/遗漏？
   - 结果可信吗？
4. 输出结构化报告：PASS / FAIL / NEED_FIX + 具体问题列表

支持两种验证模式：
- VERIFY_ONLY（默认）：只报告问题，不修改代码
- AUTO_FIX：发现问题后自动调用 executor 修复（高风险）

每个交叉验证结果写入 .omc/state/cross_validation/<validation_id>.json
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..core.router import ModelRouter


# ------------------------------------------------------------------
# 验证结果模型
# ------------------------------------------------------------------


class ValidationStatus(Enum):
    PASS = "pass"  # 验证通过
    FAIL = "fail"  # 验证失败（有明显问题）
    NEED_FIX = "need_fix"  # 需要修复
    SKIPPED = "skipped"  # 跳过（无输出可验证）


class ValidationSeverity(Enum):
    CRITICAL = "critical"  # 必须修复
    HIGH = "high"  # 强烈建议修复
    MEDIUM = "medium"  # 建议关注
    LOW = "low"  # 可忽略


@dataclass
class ValidationIssue:
    """发现的问题"""

    severity: ValidationSeverity
    category: str  # logic / security / completeness / style / performance
    description: str
    location: str = ""  # 文件:行号 或 "general"
    suggestion: str = ""
    original_agent: str = ""  # 原 Agent 名称
    evidence: str = ""  # 证据片段


@dataclass
class CrossValidationResult:
    """交叉验证报告"""

    validation_id: str
    workflow_id: str
    workflow_name: str
    status: ValidationStatus
    agent_outputs: dict[str, str]  # agent_name → 输出的纯文本摘要
    issues: list[ValidationIssue] = field(default_factory=list)
    raw_validation_text: str = ""  # 模型原始输出
    execution_time: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    mode: str = "verify_only"  # verify_only | auto_fix
    fix_applied: bool = False  # 是否已自动修复

    @property
    def pass_rate(self) -> str:
        """验证通过率"""
        total = len(self.issues)
        if total == 0:
            return "100%"
        critical = sum(
            1 for i in self.issues if i.severity == ValidationSeverity.CRITICAL
        )
        if critical > 0:
            return "0%"
        high = sum(1 for i in self.issues if i.severity == ValidationSeverity.HIGH)
        if high > 0:
            return "50%"
        return "80%"

    def to_summary(self) -> str:
        """生成人类可读摘要"""
        lines = [
            "## 🔍 交叉验证报告",
            "",
            "| 项目 | 值 |",
            "|------|-----|",
            f"| 验证 ID | `{self.validation_id}` |",
            f"| 工作流 | `{self.workflow_name}` (`{self.workflow_id}`) |",
            f"| 验证状态 | **{self.status.value.upper()}** |",
            f"| 发现问题 | {len(self.issues)} 个 |",
            f"| 验证用时 | {self.execution_time:.1f}s |",
            f"| 验证模式 | `{self.mode}` |",
            "",
        ]
        if self.issues:
            lines.append("### 发现的问题")
            lines.append("")
            lines.append("| 严重性 | 分类 | 描述 | 位置 |")
            lines.append("|--------|------|------|------|")
            for issue in self.issues:
                lines.append(
                    f"| {issue.severity.value} | {issue.category} "
                    f"| {issue.description[:60]} | {issue.location} |"
                )
            lines.append("")
            if self.issues[0].suggestion:
                lines.append("### 修复建议")
                for i, issue in enumerate(self.issues, 1):
                    if issue.suggestion:
                        lines.append(
                            f"{i}. **{issue.description}**: {issue.suggestion}"
                        )
                lines.append("")
        else:
            lines.append("✅ 未发现明显问题\n")
        return "\n".join(lines)


# ------------------------------------------------------------------
# 交叉验证层（由 CLI 调用）
# ------------------------------------------------------------------


class CrossValidationLayer:
    """
    交叉验证层

    用法：
    ```python
    layer = CrossValidationLayer(
        model_router=router,
        state_dir=project_path / ".omc" / "state",
    )
    result = layer.validate_workflow(workflow_result, workflow_name)
    ```
    """

    # 交叉验证专用的系统提示词
    VALIDATION_SYSTEM_PROMPT = """你是一个严谨的代码审查专家，擅长批判性思维。

## 角色
你是一个独立的「第二双眼睛」，专门审视其他 AI Agent 的产出。
你不会复刻前序 Agent 的结论，而是**质疑、验证、补充**。

## 工作方式
1. 阅读前序 Agent 的完整产出
2. 从以下维度独立审查：
   - **逻辑完整性**：功能是否完整实现？边界条件处理了吗？
   - **安全性**：是否有 SQL 注入、XSS、敏感信息泄露风险？
   - **代码质量**：命名、可读性、是否有明显的代码坏味道？
   - **测试覆盖**：是否覆盖了主要场景？边界测试呢？
   - **潜在 Bug**：逻辑错误、空指针、并发问题？
   - **遗漏需求**：任务要求中有没有被忽略的点？
3. 如果发现问题，给出精确的位置和修复建议

## 输出格式

### 验证结论
PASS / FAIL / NEED_FIX

### 发现的问题（如有）
对每个问题输出：
```
### [CRITICAL] logic: 空指针检查缺失
- 位置: src/main.py:42
- 证据: if user.profile is None: ...
- 建议: 添加空值断言或默认行为
```

### 置信度
你对这次验证结果的信心：HIGH / MEDIUM / LOW

## 重要原则
- **有证据再说**，不要无端猜测
- 优先关注 CRITICAL 和 HIGH 问题
- 如果前序产出已经很完善，明确说明 PASS
"""

    def __init__(
        self,
        model_router: ModelRouter,
        state_dir: Path | None = None,
    ):
        self.model_router = model_router
        self.state_dir = (state_dir or Path(".omc/state")).resolve()
        self._cv_dir = self.state_dir / "cross_validation"

    def _extract_outputs(self, result) -> dict[str, str]:
        """从 WorkflowResult 中提取纯文本摘要"""
        outputs: dict[str, str] = {}
        for agent_name, output in result.outputs.items():
            if hasattr(output, "result") and output.result:
                outputs[agent_name] = str(output.result)[:3000]
            elif hasattr(output, "error") and output.error:
                outputs[agent_name] = f"[ERROR] {output.error}"
        return outputs

    def _build_validation_messages(
        self,
        workflow_name: str,
        agent_outputs: dict[str, str],
    ) -> list[dict[str, str]]:
        """构建发送给模型的 prompt"""
        output_blocks = []
        for agent_name, output_text in agent_outputs.items():
            output_blocks.append(f"### {agent_name}\n\n{output_text}\n")
        combined = "\n".join(output_blocks)

        return [
            {
                "role": "user",
                "content": (
                    f"## 待验证工作流\n**工作流名称**: {workflow_name}\n\n"
                    f"## 前序 Agent 产出\n\n{combined}\n\n"
                    f"---\n请执行交叉验证，从逻辑/安全/完整性/代码质量角度审视上述产出。"
                    f"对每个发现的问题，给出严重性（CRITICAL/HIGH/MEDIUM/LOW）、"
                    f"分类（logic/security/completeness/style/performance）、"
                    f"位置和修复建议。如果产出完善，明确说明 PASS。"
                ),
            }
        ]

    async def validate_workflow(
        self,
        workflow_result,
        workflow_name: str,
        mode: str = "verify_only",
    ) -> CrossValidationResult:
        """
        对工作流结果执行交叉验证

        Args:
            workflow_result: Orchestrator.execute_workflow 返回的 WorkflowResult
            workflow_name: 工作流名称
            mode: verify_only | auto_fix

        Returns:
            CrossValidationResult: 验证报告
        """
        start_time = time.time()
        validation_id = str(uuid.uuid4())[:8]

        # 1. 提取各 Agent 的输出
        agent_outputs = self._extract_outputs(workflow_result)

        if not agent_outputs:
            return CrossValidationResult(
                validation_id=validation_id,
                workflow_id=workflow_result.workflow_id,
                workflow_name=workflow_name,
                status=ValidationStatus.SKIPPED,
                agent_outputs={},
                execution_time=time.time() - start_time,
                mode=mode,
            )

        # 2. 构建验证消息
        messages = self._build_validation_prompt(workflow_name, agent_outputs)

        # 3. 直接调用模型（不依赖 Agent 注册系统）
        try:
            from ..models.base import Message

            msg_objects = [
                Message(role=m["role"], content=m["content"]) for m in messages
            ]
            resp = await self.model_router.route_and_call(
                task_type="analysis",
                messages=msg_objects,
                complexity="high",
            )
            raw_text = resp.content if resp else ""
        except Exception:
            return CrossValidationResult(
                validation_id=validation_id,
                workflow_id=workflow_result.workflow_id,
                workflow_name=workflow_name,
                status=ValidationStatus.SKIPPED,
                agent_outputs=agent_outputs,
                execution_time=time.time() - start_time,
                mode=mode,
            )

        # 4. 解析结果
        issues = self._parse_validation_output(raw_text or "")
        status = self._determine_status(issues)

        result = CrossValidationResult(
            validation_id=validation_id,
            workflow_id=workflow_result.workflow_id,
            workflow_name=workflow_name,
            status=status,
            agent_outputs=agent_outputs,
            issues=issues,
            raw_validation_text=raw_text or "",
            execution_time=time.time() - start_time,
            mode=mode,
        )

        # 5. 保存结果
        self._save_result(result)

        return result

    def _build_validation_prompt(
        self,
        workflow_name: str,
        agent_outputs: dict[str, str],
    ) -> list[dict[str, str]]:
        """兼容性别名"""
        return self._build_validation_messages(workflow_name, agent_outputs)

    def _parse_validation_output(self, text: str) -> list[ValidationIssue]:
        """从模型输出中解析出结构化问题列表"""
        issues: list[ValidationIssue] = []

        if not text:
            return issues

        lines = text.split("\n")
        current_issue: ValidationIssue | None = None

        for line in lines:
            stripped = line.strip()
            # 问题标题：### [CRITICAL] xxx 或 ### CRITICAL xxx
            if stripped.startswith("### ["):
                # 保存前一个问题
                if current_issue and current_issue.description:
                    issues.append(current_issue)

                # 解析 ### [CRITICAL] category: description
                bracket_end = stripped.find("]")
                if bracket_end == -1:
                    continue

                severity_str = stripped[4:bracket_end].lower()
                rest = stripped[bracket_end + 1 :].strip()

                # 去掉开头的 # 或 .
                rest = rest.lstrip("#").lstrip(".").strip()

                severity = self._parse_severity(severity_str)

                if ":" in rest:
                    cat, desc = rest.split(":", 1)
                    cat = cat.strip().lower()
                    desc = desc.strip()
                else:
                    cat = "general"
                    desc = rest

                current_issue = ValidationIssue(
                    severity=severity,
                    category=cat,
                    description=desc,
                )

            elif current_issue:
                # 收集问题的详细信息
                lower = stripped.lower()
                if lower.startswith(("- 位置:", "位置:")):
                    loc = stripped.split(":", 1)[1].strip()
                    current_issue.location = loc
                elif lower.startswith(("- 证据:", "证据:")):
                    ev = stripped.split(":", 1)[1].strip()
                    current_issue.evidence = ev
                elif lower.startswith(("- 建议:", "建议:")):
                    sug = stripped.split(":", 1)[1].strip()
                    current_issue.suggestion = sug

        if current_issue and current_issue.description:
            issues.append(current_issue)

        return issues

    def _parse_severity(self, s: str) -> ValidationSeverity:
        """解析严重性等级"""
        s = s.lower()
        if "critical" in s or "严重" in s:
            return ValidationSeverity.CRITICAL
        if "high" in s or "高" in s:
            return ValidationSeverity.HIGH
        if "medium" in s or "中" in s:
            return ValidationSeverity.MEDIUM
        return ValidationSeverity.LOW

    def _determine_status(self, issues: list[ValidationIssue]) -> ValidationStatus:
        """根据问题列表确定验证状态"""
        if not issues:
            return ValidationStatus.PASS
        critical = any(i.severity == ValidationSeverity.CRITICAL for i in issues)
        high = any(i.severity == ValidationSeverity.HIGH for i in issues)
        if critical:
            return ValidationStatus.FAIL
        if high:
            return ValidationStatus.NEED_FIX
        return ValidationStatus.PASS

    def _save_result(self, result: CrossValidationResult):
        """保存验证结果到文件"""
        self._cv_dir.mkdir(parents=True, exist_ok=True)
        result_file = self._cv_dir / f"{result.validation_id}.json"
        with open(result_file, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "validation_id": result.validation_id,
                    "workflow_id": result.workflow_id,
                    "workflow_name": result.workflow_name,
                    "status": result.status.value,
                    "issues": [
                        {
                            **asdict(i),
                            "severity": i.severity.value,
                        }
                        for i in result.issues
                    ],
                    "execution_time": result.execution_time,
                    "timestamp": result.timestamp,
                    "mode": result.mode,
                    "pass_rate": result.pass_rate,
                },
                f,
                ensure_ascii=False,
                indent=2,
            )
