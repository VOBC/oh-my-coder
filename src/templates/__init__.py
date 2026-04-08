"""
模板市场

预定义工作流模板的存储和管理。
"""

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class TemplateCategory(str, Enum):
    """模板分类"""

    BUILD = "build"
    REVIEW = "review"
    DEBUG = "debug"
    TEST = "test"
    REFACTOR = "refactor"
    DOCUMENT = "document"
    DEPLOY = "deploy"
    CUSTOM = "custom"


@dataclass
class WorkflowStep:
    """工作流步骤"""

    agent_name: str
    description: str = ""
    dependencies: List[str] = field(default_factory=list)
    condition: Optional[str] = None
    timeout: int = 300
    retry: int = 0
    config: Dict[str, Any] = field(default_factory=dict)


class TemplateMetadata(BaseModel):
    """模板元数据"""

    name: str
    display_name: str
    description: str
    category: TemplateCategory
    version: str = "1.0.0"
    author: str = ""
    tags: List[str] = []
    icon: str = "📦"
    difficulty: str = "beginner"  # beginner, intermediate, advanced
    estimated_time: str = ""


@dataclass
class WorkflowTemplate:
    """工作流模板"""

    metadata: TemplateMetadata
    steps: List[WorkflowStep]
    variables: Dict[str, Any] = field(default_factory=dict)
    hooks: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "metadata": self.metadata.model_dump(),
            "steps": [
                {
                    "agent_name": s.agent_name,
                    "description": s.description,
                    "dependencies": s.dependencies,
                    "condition": s.condition,
                    "timeout": s.timeout,
                    "retry": s.retry,
                    "config": s.config,
                }
                for s in self.steps
            ],
            "variables": self.variables,
            "hooks": self.hooks,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowTemplate":
        """从字典创建"""
        metadata = TemplateMetadata(**data["metadata"])
        steps = [
            WorkflowStep(
                agent_name=s["agent_name"],
                description=s.get("description", ""),
                dependencies=s.get("dependencies", []),
                condition=s.get("condition"),
                timeout=s.get("timeout", 300),
                retry=s.get("retry", 0),
                config=s.get("config", {}),
            )
            for s in data["steps"]
        ]
        return cls(
            metadata=metadata,
            steps=steps,
            variables=data.get("variables", {}),
            hooks=data.get("hooks", {}),
        )


# 内置模板
BUILTIN_TEMPLATES: List[WorkflowTemplate] = [
    # 构建模板
    WorkflowTemplate(
        metadata=TemplateMetadata(
            name="build",
            display_name="完整构建流程",
            description="从规划到验证的完整开发流程",
            category=TemplateCategory.BUILD,
            tags=["开发", "构建"],
            icon="🔨",
            difficulty="intermediate",
            estimated_time="5-15分钟",
        ),
        steps=[
            WorkflowStep(agent_name="Planner", description="制定开发计划"),
            WorkflowStep(
                agent_name="Architect",
                description="设计系统架构",
                dependencies=["Planner"],
            ),
            WorkflowStep(
                agent_name="Executor",
                description="生成代码",
                dependencies=["Architect"],
            ),
            WorkflowStep(
                agent_name="Verifier",
                description="验证和测试",
                dependencies=["Executor"],
            ),
        ],
    ),
    WorkflowTemplate(
        metadata=TemplateMetadata(
            name="quick-fix",
            display_name="快速修复",
            description="快速定位并修复问题",
            category=TemplateCategory.BUILD,
            tags=["修复", "快速"],
            icon="⚡",
            difficulty="beginner",
            estimated_time="1-5分钟",
        ),
        steps=[
            WorkflowStep(agent_name="Executor", description="直接修复"),
            WorkflowStep(agent_name="Verifier", description="验证修复"),
        ],
    ),
    # 审查模板
    WorkflowTemplate(
        metadata=TemplateMetadata(
            name="review",
            display_name="代码审查",
            description="全面的代码质量审查",
            category=TemplateCategory.REVIEW,
            tags=["审查", "质量"],
            icon="🔍",
            difficulty="beginner",
            estimated_time="2-5分钟",
        ),
        steps=[
            WorkflowStep(agent_name="CodeReviewer", description="代码质量审查"),
            WorkflowStep(agent_name="SecurityReviewer", description="安全漏洞扫描"),
        ],
    ),
    WorkflowTemplate(
        metadata=TemplateMetadata(
            name="pr-review",
            display_name="PR 审查",
            description="Pull Request 完整审查流程",
            category=TemplateCategory.REVIEW,
            tags=["PR", "审查"],
            icon="📋",
            difficulty="intermediate",
            estimated_time="5-10分钟",
        ),
        steps=[
            WorkflowStep(agent_name="CodeReviewer", description="代码质量审查"),
            WorkflowStep(agent_name="SecurityReviewer", description="安全审查"),
            WorkflowStep(agent_name="TestEngineer", description="测试覆盖检查"),
            WorkflowStep(
                agent_name="Writer",
                description="生成审查报告",
                dependencies=["CodeReviewer", "SecurityReviewer", "TestEngineer"],
            ),
        ],
    ),
    # 调试模板
    WorkflowTemplate(
        metadata=TemplateMetadata(
            name="debug",
            display_name="问题调试",
            description="系统化的问题定位和修复",
            category=TemplateCategory.DEBUG,
            tags=["调试", "修复"],
            icon="🐛",
            difficulty="intermediate",
            estimated_time="5-20分钟",
        ),
        steps=[
            WorkflowStep(agent_name="Debugger", description="定位问题"),
            WorkflowStep(
                agent_name="Tracer", description="追踪根因", dependencies=["Debugger"]
            ),
            WorkflowStep(
                agent_name="Executor", description="修复问题", dependencies=["Tracer"]
            ),
            WorkflowStep(
                agent_name="Verifier", description="验证修复", dependencies=["Executor"]
            ),
        ],
    ),
    # 测试模板
    WorkflowTemplate(
        metadata=TemplateMetadata(
            name="test",
            display_name="生成测试",
            description="自动生成单元测试",
            category=TemplateCategory.TEST,
            tags=["测试", "单元测试"],
            icon="🧪",
            difficulty="beginner",
            estimated_time="2-5分钟",
        ),
        steps=[
            WorkflowStep(agent_name="TestEngineer", description="生成单元测试"),
        ],
    ),
    WorkflowTemplate(
        metadata=TemplateMetadata(
            name="test-full",
            display_name="完整测试",
            description="生成单元测试和集成测试",
            category=TemplateCategory.TEST,
            tags=["测试", "集成测试"],
            icon="🔬",
            difficulty="intermediate",
            estimated_time="5-10分钟",
        ),
        steps=[
            WorkflowStep(agent_name="TestEngineer", description="生成单元测试"),
            WorkflowStep(
                agent_name="Executor",
                description="生成集成测试",
                dependencies=["TestEngineer"],
            ),
            WorkflowStep(
                agent_name="Verifier", description="运行测试", dependencies=["Executor"]
            ),
        ],
    ),
    # 重构模板
    WorkflowTemplate(
        metadata=TemplateMetadata(
            name="refactor",
            display_name="代码重构",
            description="智能代码重构和优化",
            category=TemplateCategory.REFACTOR,
            tags=["重构", "优化"],
            icon="🔧",
            difficulty="advanced",
            estimated_time="10-30分钟",
        ),
        steps=[
            WorkflowStep(agent_name="CodeReviewer", description="识别重构点"),
            WorkflowStep(
                agent_name="Architect",
                description="设计重构方案",
                dependencies=["CodeReviewer"],
            ),
            WorkflowStep(
                agent_name="Executor",
                description="执行重构",
                dependencies=["Architect"],
            ),
            WorkflowStep(
                agent_name="Verifier", description="验证功能", dependencies=["Executor"]
            ),
        ],
    ),
    # 文档模板
    WorkflowTemplate(
        metadata=TemplateMetadata(
            name="document",
            display_name="生成文档",
            description="自动生成项目文档",
            category=TemplateCategory.DOCUMENT,
            tags=["文档", "README"],
            icon="📝",
            difficulty="beginner",
            estimated_time="2-10分钟",
        ),
        steps=[
            WorkflowStep(agent_name="Writer", description="生成文档"),
        ],
    ),
    WorkflowTemplate(
        metadata=TemplateMetadata(
            name="api-doc",
            display_name="API 文档",
            description="生成 API 文档",
            category=TemplateCategory.DOCUMENT,
            tags=["文档", "API"],
            icon="📚",
            difficulty="beginner",
            estimated_time="5-15分钟",
        ),
        steps=[
            WorkflowStep(agent_name="Explorer", description="分析 API 结构"),
            WorkflowStep(
                agent_name="Writer",
                description="生成 API 文档",
                dependencies=["Explorer"],
            ),
        ],
    ),
    # 探索模板
    WorkflowTemplate(
        metadata=TemplateMetadata(
            name="explore",
            display_name="代码探索",
            description="探索和理解代码库",
            category=TemplateCategory.CUSTOM,
            tags=["探索", "分析"],
            icon="📖",
            difficulty="beginner",
            estimated_time="2-10分钟",
        ),
        steps=[
            WorkflowStep(agent_name="Explorer", description="探索代码库"),
            WorkflowStep(
                agent_name="Writer",
                description="生成分析报告",
                dependencies=["Explorer"],
            ),
        ],
    ),
]


class TemplateMarket:
    """
    模板市场

    管理工作流模板的存储、发现和分享。

    Example:
        >>> market = TemplateMarket()
        >>> templates = market.list_templates(category="build")
        >>> template = market.get_template("build")
    """

    def __init__(self, template_dir: Optional[Path] = None):
        """
        初始化模板市场

        Args:
            template_dir: 自定义模板目录
        """
        self.template_dir = template_dir or Path(".omc/templates")
        self.template_dir.mkdir(parents=True, exist_ok=True)

        self._templates: Dict[str, WorkflowTemplate] = {}
        self._load_builtin()

    def _load_builtin(self) -> None:
        """加载内置模板"""
        for template in BUILTIN_TEMPLATES:
            self._templates[template.metadata.name] = template

    def get_template(self, name: str) -> Optional[WorkflowTemplate]:
        """
        获取模板

        Args:
            name: 模板名称

        Returns:
            模板实例
        """
        return self._templates.get(name)

    def list_templates(
        self,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        difficulty: Optional[str] = None,
    ) -> List[WorkflowTemplate]:
        """
        列出模板

        Args:
            category: 分类过滤
            tags: 标签过滤
            difficulty: 难度过滤

        Returns:
            模板列表
        """
        templates = list(self._templates.values())

        if category:
            templates = [t for t in templates if t.metadata.category.value == category]

        if tags:
            templates = [
                t for t in templates if any(tag in t.metadata.tags for tag in tags)
            ]

        if difficulty:
            templates = [t for t in templates if t.metadata.difficulty == difficulty]

        return templates

    def register_template(self, template: WorkflowTemplate) -> None:
        """
        注册模板

        Args:
            template: 模板实例
        """
        self._templates[template.metadata.name] = template

    def save_template(self, template: WorkflowTemplate) -> Path:
        """
        保存模板到文件

        Args:
            template: 模板实例

        Returns:
            文件路径
        """
        file_path = self.template_dir / f"{template.metadata.name}.json"

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(template.to_dict(), f, indent=2, ensure_ascii=False)

        return file_path

    def load_template(self, name: str) -> Optional[WorkflowTemplate]:
        """
        从文件加载模板

        Args:
            name: 模板名称

        Returns:
            模板实例
        """
        file_path = self.template_dir / f"{name}.json"

        if not file_path.exists():
            return None

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        template = WorkflowTemplate.from_dict(data)
        self._templates[name] = template
        return template

    def load_all(self) -> None:
        """加载所有自定义模板"""
        for file_path in self.template_dir.glob("*.json"):
            try:
                self.load_template(file_path.stem)
            except Exception as e:
                print(f"加载模板失败: {file_path}: {e}")

    def get_categories(self) -> List[Dict[str, Any]]:
        """
        获取所有分类

        Returns:
            分类信息列表
        """
        categories = {}
        for template in self._templates.values():
            cat = template.metadata.category.value
            if cat not in categories:
                categories[cat] = {
                    "name": cat,
                    "icon": template.metadata.icon,
                    "count": 0,
                }
            categories[cat]["count"] += 1

        return list(categories.values())

    def search(self, query: str) -> List[WorkflowTemplate]:
        """
        搜索模板

        Args:
            query: 搜索关键词

        Returns:
            匹配的模板列表
        """
        query = query.lower()
        results = []

        for template in self._templates.values():
            meta = template.metadata
            if (
                query in meta.name.lower()
                or query in meta.display_name.lower()
                or query in meta.description.lower()
                or any(query in tag.lower() for tag in meta.tags)
            ):
                results.append(template)

        return results


# 全局实例
_template_market: Optional[TemplateMarket] = None


def get_template_market() -> TemplateMarket:
    """获取全局模板市场实例"""
    global _template_market
    if _template_market is None:
        _template_market = TemplateMarket()
    return _template_market
