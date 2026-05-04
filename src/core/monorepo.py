"""Monorepo detection and workspace management.

Supports pnpm workspace, lerna, nx, turborepo, bazel, rush.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional, Union

# Monorepo configuration file mappings
MONOREPO_CONFIGS: dict[str, list[str]] = {
    "pnpm": ["pnpm-workspace.yaml"],
    "lerna": ["lerna.json"],
    "nx": ["nx.json", "workspace.json"],
    "turborepo": ["turbo.json"],
    "bazel": ["WORKSPACE", "WORKSPACE.bazel"],
    "rush": ["rush.json"],
}

# Common package directory names
COMMON_PACKAGE_DIRS = ["packages", "apps", "libs", "services", "tools"]


@dataclass
class MonorepoInfo:
    """Monorepo workspace information."""

    root: Path
    type: str  # pnpm, lerna, nx, etc.
    packages: list[Path] = field(default_factory=list)
    config_file: Optional[Path] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict."""
        return {
            "root": str(self.root),
            "type": self.type,
            "packages": [str(p) for p in self.packages],
            "config_file": str(self.config_file) if self.config_file else None,
            "metadata": self.metadata,
        }


@dataclass
class SubProject:
    """A sub-project within a monorepo."""

    name: str
    path: Path
    language: str = "unknown"
    framework: str = ""
    has_agent_config: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict."""
        return {
            "name": self.name,
            "path": str(self.path),
            "language": self.language,
            "framework": self.framework,
            "has_agent_config": self.has_agent_config,
        }


def detect_monorepo(root: Union[Path, str, None] = None) -> Optional[MonorepoInfo]:
    """Detect if directory is a monorepo root.

    Args:
        root: Directory to check (default: cwd)

    Returns:
        MonorepoInfo if detected, None otherwise
    """
    root_path = Path(root) if root else Path.cwd()
    root_path = root_path.resolve()

    for repo_type, config_files in MONOREPO_CONFIGS.items():
        for config_name in config_files:
            config_path = root_path / config_name
            if config_path.exists():
                packages = _find_packages(root_path, repo_type)
                return MonorepoInfo(
                    root=root_path,
                    type=repo_type,
                    packages=packages,
                    config_file=config_path,
                )
    return None


def find_monorepo_root(start: Union[Path, str, None] = None) -> Optional[Path]:
    """Find monorepo root by walking up from start directory.

    Args:
        start: Starting directory (default: cwd)

    Returns:
        Monorepo root Path if found, None otherwise
    """
    current = Path(start) if start else Path.cwd()
    current = current.resolve()

    while current != current.parent:
        if detect_monorepo(current):
            return current
        current = current.parent

    return None


def _find_packages(root: Path, repo_type: str) -> list[Path]:
    """Find all packages in a monorepo.

    Args:
        root: Monorepo root directory
        repo_type: Type of monorepo

    Returns:
        List of package directory paths
    """
    packages: list[Path] = []

    if repo_type == "pnpm":
        packages = _parse_pnpm_workspace(root)
    elif repo_type == "lerna":
        packages = _parse_lerna_packages(root)
    elif repo_type == "nx":
        packages = _parse_nx_workspace(root)
    elif repo_type == "turborepo":
        packages = _find_common_package_dirs(root)
    elif repo_type == "rush":
        packages = _parse_rush_packages(root)
    else:
        packages = _find_common_package_dirs(root)

    # Filter to only directories that exist
    return [p for p in packages if p.is_dir()]


def _parse_pnpm_workspace(root: Path) -> list[Path]:
    """Parse pnpm-workspace.yaml for package paths."""
    packages: list[Path] = []
    workspace_file = root / "pnpm-workspace.yaml"

    if workspace_file.exists():
        content = workspace_file.read_text(encoding="utf-8")
        in_packages = False
        for line in content.splitlines():
            stripped = line.strip()
            if stripped == "packages:":
                in_packages = True
                continue
            if in_packages:
                if stripped.startswith("-"):
                    pkg_pattern = stripped.lstrip("- ").strip()
                    # Handle glob patterns like "packages/*"
                    if "*" in pkg_pattern:
                        base_dir = root / pkg_pattern.replace("/*", "").replace("/**", "")
                        if base_dir.is_dir():
                            for sub in base_dir.iterdir():
                                if sub.is_dir():
                                    packages.append(sub)
                    else:
                        pkg_path = root / pkg_pattern
                        if pkg_path.is_dir():
                            packages.append(pkg_path)
                elif stripped and not stripped.startswith("#"):
                    # New section
                    in_packages = False

    # Fallback to common directories
    if not packages:
        packages = _find_common_package_dirs(root)

    return packages


def _parse_lerna_packages(root: Path) -> list[Path]:
    """Parse lerna.json for package paths."""
    packages: list[Path] = []
    lerna_file = root / "lerna.json"

    if lerna_file.exists():
        try:
            data = json.loads(lerna_file.read_text(encoding="utf-8"))
            pkg_patterns = data.get("packages", ["packages"])
            for pattern in pkg_patterns:
                if "*" in pattern:
                    base_dir = root / pattern.replace("/*", "")
                    if base_dir.is_dir():
                        for sub in base_dir.iterdir():
                            if sub.is_dir():
                                packages.append(sub)
                else:
                    pkg_path = root / pattern
                    if pkg_path.is_dir():
                        packages.append(pkg_path)
        except (json.JSONDecodeError, OSError):
            pass

    if not packages:
        packages = _find_common_package_dirs(root)

    return packages


def _parse_nx_workspace(root: Path) -> list[Path]:
    """Parse nx workspace for projects."""
    packages: list[Path] = []

    # Check workspace.json first
    workspace_file = root / "workspace.json"
    if workspace_file.exists():
        try:
            data = json.loads(workspace_file.read_text(encoding="utf-8"))
            projects = data.get("projects", {})
            for project_path in projects.values():
                pkg_path = root / project_path
                if pkg_path.is_dir():
                    packages.append(pkg_path)
        except (json.JSONDecodeError, OSError):
            pass

    if not packages:
        packages = _find_common_package_dirs(root)

    return packages


def _parse_rush_packages(root: Path) -> list[Path]:
    """Parse rush.json for package paths."""
    packages: list[Path] = []
    rush_file = root / "rush.json"

    if rush_file.exists():
        try:
            data = json.loads(rush_file.read_text(encoding="utf-8"))
            projects = data.get("projects", [])
            for project in projects:
                pkg_path = root / project.get("projectFolder", "")
                if pkg_path.is_dir():
                    packages.append(pkg_path)
        except (json.JSONDecodeError, OSError):
            pass

    return packages


def _find_common_package_dirs(root: Path) -> list[Path]:
    """Find packages in common directory names."""
    packages: list[Path] = []
    for dir_name in COMMON_PACKAGE_DIRS:
        pkg_dir = root / dir_name
        if pkg_dir.is_dir():
            for sub in pkg_dir.iterdir():
                if sub.is_dir():
                    packages.append(sub)
    return packages


def detect_language(project_path: Path) -> str:
    """Detect programming language of a project.

    Args:
        project_path: Project directory

    Returns:
        Language name
    """
    if (project_path / "package.json").exists():
        return "Node/TS"
    elif (project_path / "pyproject.toml").exists():
        return "Python"
    elif (project_path / "setup.py").exists():
        return "Python"
    elif (project_path / "Cargo.toml").exists():
        return "Rust"
    elif (project_path / "go.mod").exists():
        return "Go"
    elif (project_path / "pom.xml").exists():
        return "Java"
    elif (project_path / "build.gradle").exists() or (
        project_path / "build.gradle.kts"
    ).exists():
        return "Java/Kotlin"
    elif (project_path / "composer.json").exists():
        return "PHP"
    elif (project_path / "Gemfile").exists():
        return "Ruby"
    elif (project_path / "pubspec.yaml").exists():
        return "Dart/Flutter"
    return "unknown"


def detect_framework(project_path: Path) -> str:
    """Detect framework of a project.

    Args:
        project_path: Project directory

    Returns:
        Framework name or empty string
    """
    pkg_json = project_path / "package.json"
    if pkg_json.exists():
        try:
            data = json.loads(pkg_json.read_text(encoding="utf-8"))
            deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
            frameworks = {
                "next": "Next.js",
                "react": "React",
                "vue": "Vue",
                "@angular/core": "Angular",
                "svelte": "Svelte",
                "express": "Express",
                "nest": "NestJS",
                "fastify": "Fastify",
                "nuxt": "Nuxt",
            }
            for dep, name in frameworks.items():
                if any(d.startswith(dep) for d in deps):
                    return name
        except (json.JSONDecodeError, OSError):
            pass
    return ""


def list_subprojects(monorepo_info: Optional[MonorepoInfo] = None) -> list[SubProject]:
    """List all sub-projects in a monorepo.

    Args:
        monorepo_info: MonorepoInfo (auto-detect if None)

    Returns:
        List of SubProject
    """
    if monorepo_info is None:
        info = detect_monorepo()
        if info is None:
            return []
        monorepo_info = info

    subprojects: list[SubProject] = []
    for pkg_path in monorepo_info.packages:
        sub = SubProject(
            name=pkg_path.name,
            path=pkg_path,
            language=detect_language(pkg_path),
            framework=detect_framework(pkg_path),
            has_agent_config=_has_agent_config(pkg_path),
        )
        subprojects.append(sub)

    return subprojects


def _has_agent_config(project_path: Path) -> bool:
    """Check if project has omc agent configuration.

    Args:
        project_path: Project directory

    Returns:
        True if .omc/config.json or similar exists
    """
    omc_dir = project_path / ".omc"
    if omc_dir.is_dir():
        return any(
            (omc_dir / f).exists() for f in ["config.json", "agent.yaml", "agents"]
        )
    return False


def get_monorepo_context(project_path: Union[Path, str, None] = None) -> dict[str, Any]:
    """Get monorepo context for agent initialization.

    Args:
        project_path: Project path (default: cwd)

    Returns:
        Dict with monorepo info or empty dict if not in monorepo
    """
    path = Path(project_path) if project_path else Path.cwd()
    path = path.resolve()

    # Check if current dir is in a monorepo
    monorepo_root = find_monorepo_root(path)
    if not monorepo_root:
        return {}

    info = detect_monorepo(monorepo_root)
    if not info:
        return {}

    subprojects = list_subprojects(info)
    current_project = None
    for sp in subprojects:
        if sp.path == path or path.is_relative_to(sp.path):
            current_project = sp
            break

    return {
        "is_monorepo": True,
        "monorepo_root": str(monorepo_root),
        "monorepo_type": info.type,
        "current_project": current_project.to_dict() if current_project else None,
        "subprojects": [sp.to_dict() for sp in subprojects],
        "total_projects": len(subprojects),
    }
