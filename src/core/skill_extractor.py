"""
Skill 沉淀闭环 — 从任务执行中提取可复用的 Skill

流程：任务完成 → 反思 → 生成 Skill 提议 → 用户确认 → 保存
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

SKILL_PROPOSALS_DIR = Path.home() / ".omc" / "skill-proposals"


@dataclass
class SkillProposal:
    """Skill 提议"""

    id: str
    title: str
    description: str
    trigger: str  # 触发条件
    steps: list[str]  # 执行步骤
    source_task: str  # 来源任务
    created_at: str
    status: str = "pending"  # pending / accepted / rejected


def extract_skill_from_task(
    task_description: str,
    execution_steps: list[str],
    reflections: list[str],
) -> Optional[SkillProposal]:
    """
    从任务执行中提取 Skill 提议

    Args:
        task_description: 原始任务描述
        execution_steps: 执行步骤列表
        reflections: 反思记录

    Returns:
        SkillProposal 或 None（如果不值得提取）
    """
    # 判断是否有提取价值
    if not _is_worth_extracting(task_description, execution_steps, reflections):
        return None

    # 生成 Skill 内容
    title = _generate_title(task_description)
    trigger = _generate_trigger(task_description)
    steps = _generate_steps(execution_steps, reflections)
    description = _generate_description(title, steps)

    proposal = SkillProposal(
        id=f"proposal-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        title=title,
        description=description,
        trigger=trigger,
        steps=steps,
        source_task=task_description[:100],
        created_at=datetime.now().isoformat(),
    )

    return proposal


def save_proposal(proposal: SkillProposal) -> Path:
    """保存 Skill 提议到文件"""
    SKILL_PROPOSALS_DIR.mkdir(parents=True, exist_ok=True)

    filepath = SKILL_PROPOSALS_DIR / f"{proposal.id}.json"
    filepath.write_text(
        json.dumps(asdict(proposal), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return filepath


def list_proposals() -> list[SkillProposal]:
    """列出所有待处理的 Skill 提议"""
    proposals: list[SkillProposal] = []

    if not SKILL_PROPOSALS_DIR.exists():
        return proposals

    for filepath in sorted(SKILL_PROPOSALS_DIR.glob("proposal-*.json")):
        try:
            data = json.loads(filepath.read_text(encoding="utf-8"))
            proposals.append(SkillProposal(**data))
        except Exception:
            continue

    return proposals


def accept_proposal(proposal_id: str) -> Optional[Path]:
    """
    接受 Skill 提议，生成 SKILL.md 文件

    Returns:
        生成的 SKILL.md 路径
    """
    proposal = _find_proposal(proposal_id)
    if not proposal:
        return None

    # 更新状态
    proposal.status = "accepted"
    save_proposal(proposal)

    # 生成 SKILL.md
    skill_content = _generate_skill_md(proposal)

    skills_dir = Path.home() / ".omc" / "skills" / proposal.id
    skills_dir.mkdir(parents=True, exist_ok=True)

    skill_path = skills_dir / "SKILL.md"
    skill_path.write_text(skill_content, encoding="utf-8")

    return skill_path


def reject_proposal(proposal_id: str) -> bool:
    """拒绝 Skill 提议"""
    proposal = _find_proposal(proposal_id)
    if not proposal:
        return False

    proposal.status = "rejected"
    save_proposal(proposal)
    return True


# ===== 内部函数 =====


def _is_worth_extracting(
    task_description: str,
    execution_steps: list[str],
    reflections: list[str],
) -> bool:
    """判断任务是否值得提取为 Skill"""
    # 步骤太少不值得
    if len(execution_steps) < 3:
        return False

    # 检查是否有通用性关键词
    generic_keywords = [
        "创建",
        "生成",
        "配置",
        "设置",
        "安装",
        "部署",
        "检查",
        "修复",
        "优化",
        "重构",
        "测试",
        "文档",
        "初始化",
        "同步",
        "更新",
        "清理",
    ]

    task_lower = task_description.lower()
    has_generic = any(kw in task_lower for kw in generic_keywords)

    # 检查反思中是否有正面评价
    positive_indicators = ["成功", "完成", "有效", "正确", "顺利", "✅"]
    has_positive = any(
        any(ind in ref for ind in positive_indicators) for ref in reflections
    )

    return has_generic and has_positive


def _generate_title(task_description: str) -> str:
    """生成 Skill 标题"""
    # 提取动词 + 名词
    patterns = [
        r"(?:实现|创建|生成|配置|设置|安装|部署|检查|修复|优化|重构|测试|文档化)\s*(.+?)(?:\s*[-—]|$)",
        r"(.+?)(?:的|之)(?:实现|创建|生成|配置|设置|安装|部署|检查|修复|优化|重构|测试|文档)",
    ]

    for pattern in patterns:
        match = re.search(pattern, task_description)
        if match:
            return match.group(1).strip()[:50]

    # 兜底：取前 30 个字符
    if len(task_description) > 30:
        return task_description[:30] + "..."
    return task_description


def _generate_trigger(task_description: str) -> str:
    """生成触发条件"""
    # 提取关键词作为触发条件
    keywords = []
    trigger_keywords = [
        "创建",
        "生成",
        "配置",
        "设置",
        "安装",
        "部署",
        "检查",
        "修复",
        "优化",
        "重构",
        "测试",
        "文档",
        "初始化",
        "同步",
        "更新",
        "清理",
    ]

    for kw in trigger_keywords:
        if kw in task_description:
            keywords.append(kw)

    if keywords:
        return f"当用户需要{'/'.join(keywords[:3])}时"

    return "当用户有类似需求时"


def _generate_steps(execution_steps: list[str], reflections: list[str]) -> list[str]:
    """生成标准化步骤"""
    # 去重和简化步骤
    simplified = []
    seen = set()

    for step in execution_steps:
        # 去掉具体文件名、路径等细节
        generalized = _generalize_step(step)
        if generalized and generalized not in seen:
            seen.add(generalized)
            simplified.append(generalized)

    # 添加反思中的改进建议
    for reflection in reflections:
        if any(kw in reflection for kw in ["建议", "改进", "优化", "下次"]):
            tip = f"💡 {reflection[:100]}"
            if tip not in seen:
                simplified.append(tip)

    return simplified[:10]  # 最多 10 步


def _generalize_step(step: str) -> str:
    """将具体步骤泛化"""
    # 去掉具体路径
    step = re.sub(r"/[\w/\-.]+", "<路径>", step)
    # 去掉具体文件名
    step = re.sub(r"\b[\w\-]+\.(py|js|ts|html|css|md|json|yaml|yml)\b", "<文件>", step)
    # 去掉具体时间
    step = re.sub(r"\d{4}-\d{2}-\d{2}(?:\s+\d{2}:\d{2})?", "<时间>", step)
    # 去掉 commit hash
    step = re.sub(r"\b[0-9a-f]{7,40}\b", "<commit>", step)

    return step.strip()


def _generate_description(title: str, steps: list[str]) -> str:
    """生成 Skill 描述"""
    return f"自动处理「{title}」任务，包含 {len(steps)} 个标准化步骤。"


def _find_proposal(proposal_id: str) -> Optional[SkillProposal]:
    """查找指定提议"""
    filepath = SKILL_PROPOSALS_DIR / f"{proposal_id}.json"
    if not filepath.exists():
        return None

    try:
        data = json.loads(filepath.read_text(encoding="utf-8"))
        return SkillProposal(**data)
    except Exception:
        return None


def _generate_skill_md(proposal: SkillProposal) -> str:
    """生成 SKILL.md 内容"""
    steps_md = "\n".join(f"{i + 1}. {step}" for i, step in enumerate(proposal.steps))

    return f"""# {proposal.title}

## 描述

{proposal.description}

## 触发条件

{proposal.trigger}

## 执行步骤

{steps_md}

## 来源

- 原始任务: {proposal.source_task}
- 提取时间: {proposal.created_at}

---

*由 Oh My Coder 自动提取*
"""
