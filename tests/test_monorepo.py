"""Tests for monorepo detection and workspace management."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.core.monorepo import (
    COMMON_PACKAGE_DIRS,
    MONOREPO_CONFIGS,
    MonorepoInfo,
    SubProject,
    detect_framework,
    detect_language,
    detect_monorepo,
    find_monorepo_root,
    get_monorepo_context,
    list_subprojects,
    _find_common_package_dirs,
    _has_agent_config,
    _parse_lerna_packages,
    _parse_nx_workspace,
    _parse_pnpm_workspace,
)


class TestDetectMonorepo:
    """Test monorepo detection."""

    def test_detect_pnpm_workspace(self, tmp_path: Path):
        """Detect pnpm monorepo from pnpm-workspace.yaml."""
        (tmp_path / "pnpm-workspace.yaml").write_text(
            "packages:\n  - 'packages/*'\n", encoding="utf-8"
        )
        (tmp_path / "packages" / "app1").mkdir(parents=True)

        info = detect_monorepo(tmp_path)
        assert info is not None
        assert info.type == "pnpm"
        assert info.root == tmp_path
        assert len(info.packages) >= 1

    def test_detect_lerna(self, tmp_path: Path):
        """Detect lerna monorepo from lerna.json."""
        lerna_config = {"packages": ["packages/*"], "version": "1.0.0"}
        (tmp_path / "lerna.json").write_text(
            json.dumps(lerna_config), encoding="utf-8"
        )
        (tmp_path / "packages" / "lib1").mkdir(parents=True)

        info = detect_monorepo(tmp_path)
        assert info is not None
        assert info.type == "lerna"
        assert info.root == tmp_path

    def test_detect_nx(self, tmp_path: Path):
        """Detect nx monorepo from nx.json."""
        (tmp_path / "nx.json").write_text("{}", encoding="utf-8")
        (tmp_path / "packages" / "ui").mkdir(parents=True)

        info = detect_monorepo(tmp_path)
        assert info is not None
        assert info.type == "nx"

    def test_detect_none(self, tmp_path: Path):
        """Return None for non-monorepo directory."""
        info = detect_monorepo(tmp_path)
        assert info is None

    def test_detect_turborepo(self, tmp_path: Path):
        """Detect turborepo from turbo.json."""
        (tmp_path / "turbo.json").write_text("{}", encoding="utf-8")
        (tmp_path / "apps" / "web").mkdir(parents=True)

        info = detect_monorepo(tmp_path)
        assert info is not None
        assert info.type == "turborepo"


class TestFindMonorepoRoot:
    """Test finding monorepo root by walking up."""

    def test_find_root_from_subdirectory(self, tmp_path: Path):
        """Find monorepo root from a subdirectory."""
        (tmp_path / "pnpm-workspace.yaml").write_text(
            "packages:\n  - 'packages/*'\n", encoding="utf-8"
        )
        subdir = tmp_path / "packages" / "app1" / "src"
        subdir.mkdir(parents=True)

        root = find_monorepo_root(subdir)
        assert root == tmp_path

    def test_find_root_from_same_directory(self, tmp_path: Path):
        """Find monorepo root when already at root."""
        (tmp_path / "lerna.json").write_text('{"version": "1.0.0"}', encoding="utf-8")

        root = find_monorepo_root(tmp_path)
        assert root == tmp_path

    def test_find_root_none(self, tmp_path: Path):
        """Return None when not in a monorepo."""
        subdir = tmp_path / "some" / "deep" / "path"
        subdir.mkdir(parents=True)

        root = find_monorepo_root(subdir)
        assert root is None


class TestParsePnpmWorkspace:
    """Test pnpm workspace parsing."""

    def test_parse_packages_glob(self, tmp_path: Path):
        """Parse packages/* glob pattern."""
        (tmp_path / "pnpm-workspace.yaml").write_text(
            "packages:\n  - 'packages/*'\n  - 'apps/*'\n", encoding="utf-8"
        )
        (tmp_path / "packages" / "pkg1").mkdir(parents=True)
        (tmp_path / "apps" / "app1").mkdir(parents=True)

        packages = _parse_pnpm_workspace(tmp_path)
        assert len(packages) == 2
        names = {p.name for p in packages}
        assert names == {"pkg1", "app1"}

    def test_parse_fallback_common_dirs(self, tmp_path: Path):
        """Fallback to common package dirs when no packages declared."""
        (tmp_path / "pnpm-workspace.yaml").write_text("packages:\n", encoding="utf-8")
        (tmp_path / "packages" / "lib1").mkdir(parents=True)

        packages = _parse_pnpm_workspace(tmp_path)
        assert len(packages) >= 1


class TestParseLernaPackages:
    """Test lerna package parsing."""

    def test_parse_lerna_packages_array(self, tmp_path: Path):
        """Parse lerna packages array."""
        config = {"packages": ["packages/*"], "version": "1.0.0"}
        (tmp_path / "lerna.json").write_text(json.dumps(config), encoding="utf-8")
        (tmp_path / "packages" / "core").mkdir(parents=True)
        (tmp_path / "packages" / "utils").mkdir(parents=True)

        packages = _parse_lerna_packages(tmp_path)
        assert len(packages) == 2
        names = {p.name for p in packages}
        assert names == {"core", "utils"}

    def test_parse_lerna_invalid_json(self, tmp_path: Path):
        """Handle invalid lerna.json gracefully."""
        (tmp_path / "lerna.json").write_text("not json", encoding="utf-8")
        (tmp_path / "packages" / "pkg1").mkdir(parents=True)

        packages = _parse_lerna_packages(tmp_path)
        # Should fallback to common dirs
        assert len(packages) >= 1


class TestParseNxWorkspace:
    """Test nx workspace parsing."""

    def test_parse_workspace_json(self, tmp_path: Path):
        """Parse workspace.json projects."""
        config = {"projects": {"app1": "apps/app1", "lib1": "libs/lib1"}}
        (tmp_path / "workspace.json").write_text(json.dumps(config), encoding="utf-8")
        (tmp_path / "apps" / "app1").mkdir(parents=True)
        (tmp_path / "libs" / "lib1").mkdir(parents=True)

        packages = _parse_nx_workspace(tmp_path)
        assert len(packages) == 2
        names = {p.name for p in packages}
        assert names == {"app1", "lib1"}

    def test_parse_nx_fallback(self, tmp_path: Path):
        """Fallback to common dirs when workspace.json missing."""
        (tmp_path / "nx.json").write_text("{}", encoding="utf-8")
        (tmp_path / "packages" / "pkg1").mkdir(parents=True)

        packages = _parse_nx_workspace(tmp_path)
        assert len(packages) >= 1


class TestDetectLanguage:
    """Test project language detection."""

    def test_detect_node(self, tmp_path: Path):
        """Detect Node.js/TypeScript project."""
        (tmp_path / "package.json").write_text("{}", encoding="utf-8")
        assert detect_language(tmp_path) == "Node/TS"

    def test_detect_python_pyproject(self, tmp_path: Path):
        """Detect Python project via pyproject.toml."""
        (tmp_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
        assert detect_language(tmp_path) == "Python"

    def test_detect_python_setup(self, tmp_path: Path):
        """Detect Python project via setup.py."""
        (tmp_path / "setup.py").write_text("", encoding="utf-8")
        assert detect_language(tmp_path) == "Python"

    def test_detect_rust(self, tmp_path: Path):
        """Detect Rust project."""
        (tmp_path / "Cargo.toml").write_text("[package]\n", encoding="utf-8")
        assert detect_language(tmp_path) == "Rust"

    def test_detect_go(self, tmp_path: Path):
        """Detect Go project."""
        (tmp_path / "go.mod").write_text("module test\n", encoding="utf-8")
        assert detect_language(tmp_path) == "Go"

    def test_detect_unknown(self, tmp_path: Path):
        """Return unknown for unrecognized project."""
        assert detect_language(tmp_path) == "unknown"


class TestDetectFramework:
    """Test framework detection."""

    def test_detect_react(self, tmp_path: Path):
        """Detect React framework."""
        pkg = {"dependencies": {"react": "^18.0.0"}}
        (tmp_path / "package.json").write_text(json.dumps(pkg), encoding="utf-8")
        assert detect_framework(tmp_path) == "React"

    def test_detect_nextjs(self, tmp_path: Path):
        """Detect Next.js framework."""
        pkg = {"dependencies": {"next": "^14.0.0"}}
        (tmp_path / "package.json").write_text(json.dumps(pkg), encoding="utf-8")
        assert detect_framework(tmp_path) == "Next.js"

    def test_detect_no_framework(self, tmp_path: Path):
        """Return empty for project without framework."""
        pkg = {"dependencies": {"lodash": "^4.0.0"}}
        (tmp_path / "package.json").write_text(json.dumps(pkg), encoding="utf-8")
        assert detect_framework(tmp_path) == ""

    def test_detect_no_package_json(self, tmp_path: Path):
        """Return empty when no package.json exists."""
        assert detect_framework(tmp_path) == ""


class TestHasAgentConfig:
    """Test agent config detection."""

    def test_has_config_json(self, tmp_path: Path):
        """Detect .omc/config.json."""
        omc_dir = tmp_path / ".omc"
        omc_dir.mkdir(parents=True)
        (omc_dir / "config.json").write_text("{}", encoding="utf-8")
        assert _has_agent_config(tmp_path) is True

    def test_has_agent_yaml(self, tmp_path: Path):
        """Detect .omc/agent.yaml."""
        omc_dir = tmp_path / ".omc"
        omc_dir.mkdir(parents=True)
        (omc_dir / "agent.yaml").write_text("", encoding="utf-8")
        assert _has_agent_config(tmp_path) is True

    def test_no_config(self, tmp_path: Path):
        """Return False when no agent config exists."""
        assert _has_agent_config(tmp_path) is False


class TestListSubprojects:
    """Test listing subprojects."""

    def test_list_subprojects(self, tmp_path: Path):
        """List all subprojects in monorepo."""
        (tmp_path / "pnpm-workspace.yaml").write_text(
            "packages:\n  - 'packages/*'\n", encoding="utf-8"
        )
        (tmp_path / "packages" / "frontend").mkdir(parents=True)
        (tmp_path / "packages" / "backend").mkdir(parents=True)
        (tmp_path / "packages" / "frontend" / "package.json").write_text(
            '{"dependencies": {"react": "^18"}}', encoding="utf-8"
        )

        info = detect_monorepo(tmp_path)
        assert info is not None

        subprojects = list_subprojects(info)
        assert len(subprojects) == 2

        frontend = next(sp for sp in subprojects if sp.name == "frontend")
        assert frontend.language == "Node/TS"
        assert frontend.framework == "React"

    def test_list_subprojects_none(self):
        """Return empty list when not in monorepo."""
        subprojects = list_subprojects(None)
        assert subprojects == []


class TestGetMonorepoContext:
    """Test getting monorepo context."""

    def test_context_in_monorepo(self, tmp_path: Path):
        """Get context when inside monorepo."""
        (tmp_path / "pnpm-workspace.yaml").write_text(
            "packages:\n  - 'packages/*'\n", encoding="utf-8"
        )
        (tmp_path / "packages" / "app1").mkdir(parents=True)

        ctx = get_monorepo_context(tmp_path / "packages" / "app1")
        assert ctx["is_monorepo"] is True
        assert ctx["monorepo_type"] == "pnpm"
        assert ctx["total_projects"] == 1
        assert ctx["current_project"] is not None

    def test_context_not_in_monorepo(self, tmp_path: Path):
        """Get empty context when not in monorepo."""
        ctx = get_monorepo_context(tmp_path)
        assert ctx == {}


class TestFindCommonPackageDirs:
    """Test finding packages in common directory names."""

    def test_find_packages_dir(self, tmp_path: Path):
        """Find packages in packages/ directory."""
        (tmp_path / "packages" / "pkg1").mkdir(parents=True)
        (tmp_path / "packages" / "pkg2").mkdir(parents=True)

        packages = _find_common_package_dirs(tmp_path)
        assert len(packages) == 2
        names = {p.name for p in packages}
        assert names == {"pkg1", "pkg2"}

    def test_find_apps_dir(self, tmp_path: Path):
        """Find packages in apps/ directory."""
        (tmp_path / "apps" / "web").mkdir(parents=True)

        packages = _find_common_package_dirs(tmp_path)
        assert len(packages) == 1
        assert packages[0].name == "web"

    def test_find_no_dirs(self, tmp_path: Path):
        """Return empty when no common dirs exist."""
        packages = _find_common_package_dirs(tmp_path)
        assert packages == []


class TestMonorepoInfo:
    """Test MonorepoInfo dataclass."""

    def test_to_dict(self, tmp_path: Path):
        """Serialize MonorepoInfo to dict."""
        info = MonorepoInfo(
            root=tmp_path,
            type="pnpm",
            packages=[tmp_path / "pkg1"],
            config_file=tmp_path / "pnpm-workspace.yaml",
        )
        d = info.to_dict()
        assert d["type"] == "pnpm"
        assert d["root"] == str(tmp_path)
        assert d["packages"] == [str(tmp_path / "pkg1")]


class TestSubProject:
    """Test SubProject dataclass."""

    def test_to_dict(self, tmp_path: Path):
        """Serialize SubProject to dict."""
        sp = SubProject(
            name="test",
            path=tmp_path,
            language="Python",
            framework="FastAPI",
            has_agent_config=True,
        )
        d = sp.to_dict()
        assert d["name"] == "test"
        assert d["language"] == "Python"
        assert d["framework"] == "FastAPI"
        assert d["has_agent_config"] is True
