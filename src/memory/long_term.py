"""
长期记忆 - 项目偏好、常用模式

存储：
- 项目元信息（名称、语言、框架）
- 用户偏好（模型选择、工作流、Agent 配置）
- 常用命令模式
- 项目特定知识（API 端点、数据库结构等）

设计：
- JSON 格式持久化
- 按项目隔离（project_path 作为 key）
- 支持手动更新 + 自动学习
"""

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ProjectPreference:
    """项目偏好"""

    project_path: str
    name: str = ""
    language: str = ""  # python, go, rust, etc.
    framework: str = ""  # django, react, etc.
    default_model: str = "deepseek"
    default_workflow: str = "build"
    preferred_agents: list[str] = field(default_factory=list)
    custom_commands: dict[str, str] = field(default_factory=dict)  # alias -> command
    notes: str = ""  # 项目笔记
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProjectPreference":
        return cls(**data)


@dataclass
class UserPreference:
    """用户全局偏好"""

    user_id: str = "default"
    default_model: str = "deepseek"
    default_workflow: str = "build"
    notification_enabled: bool = True
    theme: str = "auto"  # auto, light, dark
    editor: str = "code"  # vscode, vim, nano
    shell: str = "bash"
    api_keys: dict[str, str] = field(default_factory=dict)  # 模型 -> key
    recent_projects: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "UserPreference":
        return cls(**data)


class LongTermMemory:
    """长期记忆管理器"""

    def __init__(self, storage_dir: Path):
        """
        Args:
            storage_dir: 存储目录
        """
        self.storage_dir = storage_dir / "long-term"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.user_prefs_file = self.storage_dir / "user_preferences.json"
        self.projects_file = self.storage_dir / "projects.json"
        self._user_prefs: UserPreference | None = None
        self._projects: dict[str, ProjectPreference] = {}

    def _load_projects(self) -> dict[str, ProjectPreference]:
        """加载项目偏好"""
        if self._projects:
            return self._projects

        if self.projects_file.exists():
            data = json.loads(self.projects_file.read_text())
            self._projects = {
                k: ProjectPreference.from_dict(v) for k, v in data.items()
            }
        return self._projects

    def _save_projects(self):
        """保存项目偏好"""
        data = {k: v.to_dict() for k, v in self._projects.items()}
        self.projects_file.write_text(json.dumps(data, ensure_ascii=False, indent=2))

    def get_user_prefs(self) -> UserPreference:
        """获取用户偏好"""
        if self._user_prefs is not None:
            return self._user_prefs

        if self.user_prefs_file.exists():
            data = json.loads(self.user_prefs_file.read_text())
            self._user_prefs = UserPreference.from_dict(data)
        else:
            self._user_prefs = UserPreference()
            self._save_user_prefs()
        return self._user_prefs

    def _save_user_prefs(self):
        """保存用户偏好"""
        self.user_prefs_file.write_text(
            json.dumps(self._user_prefs.to_dict(), ensure_ascii=False, indent=2)
        )

    def update_user_prefs(self, **kwargs):
        """更新用户偏好"""
        prefs = self.get_user_prefs()
        for k, v in kwargs.items():
            if hasattr(prefs, k):
                setattr(prefs, k, v)
        prefs.updated_at = time.time()
        self._save_user_prefs()

    def get_project_prefs(self, project_path: Path) -> ProjectPreference:
        """获取项目偏好"""
        projects = self._load_projects()
        key = str(project_path.resolve())

        if key not in projects:
            projects[key] = ProjectPreference(project_path=key)
            self._save_projects()

        return projects[key]

    def update_project_prefs(self, project_path: Path, **kwargs):
        """更新项目偏好"""
        projects = self._load_projects()
        key = str(project_path.resolve())

        if key not in projects:
            projects[key] = ProjectPreference(project_path=key)

        prefs = projects[key]
        for k, v in kwargs.items():
            if hasattr(prefs, k):
                setattr(prefs, k, v)
        prefs.updated_at = time.time()
        self._save_projects()

    def add_recent_project(self, project_path: Path):
        """添加最近项目"""
        prefs = self.get_user_prefs()
        key = str(project_path.resolve())

        # 移除已存在的
        if key in prefs.recent_projects:
            prefs.recent_projects.remove(key)

        # 添加到最前面
        prefs.recent_projects.insert(0, key)

        # 保留最近 10 个
        prefs.recent_projects = prefs.recent_projects[:10]
        prefs.updated_at = time.time()
        self._save_user_prefs()

    def get_recent_projects(self, limit: int = 5) -> list[Path]:
        """获取最近项目"""
        prefs = self.get_user_prefs()
        return [Path(p) for p in prefs.recent_projects[:limit] if Path(p).exists()]
