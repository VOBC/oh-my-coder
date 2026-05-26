"""
Tests for cli_monorepo.py

Uses typer.testing.CliRunner and mocks for external dependencies.
Target coverage: ≥80%
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from src.commands.cli_monorepo import (
    MONOREPO_CONFIGS,
    MonorepoInfo,
    _find_packages,
    app,
    detect_monorepo,
)


@pytest.fixture
def runner():
    """Create a CLI test runner"""
    return CliRunner()


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


class TestDetectMonorepo:
    """Tests for detect_monorepo function"""

    def test_detect_pnpm_monorepo(self, temp_dir):
        """Test detecting pnpm workspace monorepo"""
        # Create pnpm-workspace.yaml
        (temp_dir / "pnpm-workspace.yaml").write_text("packages:\n  - 'packages/*'\n")

        # Create packages directory with a package
        packages_dir = temp_dir / "packages" / "my-app"
        packages_dir.mkdir(parents=True)
        (packages_dir / "package.json").write_text("{}")

        result = detect_monorepo(temp_dir)

        assert result is not None
        assert result.type == "pnpm"
        assert result.root == temp_dir
        assert any("my-app" in str(p) for p in result.packages)

    def test_detect_lerna_monorepo(self, temp_dir):
        """Test detecting lerna monorepo"""
        import json

        # Create lerna.json
        lerna_config = {"packages": ["packages/*"]}
        (temp_dir / "lerna.json").write_text(json.dumps(lerna_config))

        # Create packages directory
        packages_dir = temp_dir / "packages" / "pkg1"
        packages_dir.mkdir(parents=True)
        (packages_dir / "package.json").write_text("{}")

        result = detect_monorepo(temp_dir)

        assert result is not None
        assert result.type == "lerna"
        assert len(result.packages) >= 1

    def test_detect_nx_monorepo(self, temp_dir):
        """Test detecting nx monorepo"""
        # Create nx.json
        (temp_dir / "nx.json").write_text("{}")

        # Create packages directory
        packages_dir = temp_dir / "packages" / "lib1"
        packages_dir.mkdir(parents=True)
        (packages_dir / "package.json").write_text("{}")

        result = detect_monorepo(temp_dir)

        assert result is not None
        assert result.type == "nx"

    def test_detect_turborepo(self, temp_dir):
        """Test detecting turborepo"""
        (temp_dir / "turbo.json").write_text("{}")

        result = detect_monorepo(temp_dir)

        assert result is not None
        assert result.type == "turborepo"

    def test_detect_bazel(self, temp_dir):
        """Test detecting bazel workspace"""
        (temp_dir / "WORKSPACE").write_text("# Bazel workspace")

        result = detect_monorepo(temp_dir)

        assert result is not None
        assert result.type == "bazel"

    def test_detect_rush(self, temp_dir):
        """Test detecting rush monorepo"""
        (temp_dir / "rush.json").write_text("{}")

        result = detect_monorepo(temp_dir)

        assert result is not None
        assert result.type == "rush"

    def test_not_a_monorepo(self, temp_dir):
        """Test directory that is not a monorepo"""
        result = detect_monorepo(temp_dir)

        assert result is None

    def test_detect_with_workspace_file_parsing(self, temp_dir):
        """Test pnpm workspace file parsing"""
        workspace_content = """packages:
  - 'packages/*'
  - 'apps/*'
"""
        (temp_dir / "pnpm-workspace.yaml").write_text(workspace_content)

        # Create packages
        (temp_dir / "packages" / "app1").mkdir(parents=True)
        (temp_dir / "apps" / "web").mkdir(parents=True)

        result = detect_monorepo(temp_dir)

        assert result is not None
        assert result.type == "pnpm"


class TestFindPackages:
    """Tests for _find_packages function"""

    def test_find_pnpm_packages(self, temp_dir):
        """Test finding pnpm packages"""
        # Create workspace file
        (temp_dir / "pnpm-workspace.yaml").write_text("packages:\n  - 'packages/*'\n")

        # Create packages
        pkg1 = temp_dir / "packages" / "pkg1"
        pkg2 = temp_dir / "packages" / "pkg2"
        pkg1.mkdir(parents=True)
        pkg2.mkdir(parents=True)

        packages = _find_packages(temp_dir, "pnpm")

        assert len(packages) >= 2

    def test_find_lerna_packages(self, temp_dir):
        """Test finding lerna packages"""
        import json

        lerna_config = {"packages": ["packages/*"]}
        (temp_dir / "lerna.json").write_text(json.dumps(lerna_config))

        pkg1 = temp_dir / "packages" / "module1"
        pkg1.mkdir(parents=True)

        packages = _find_packages(temp_dir, "lerna")

        assert len(packages) >= 1

    def test_find_nx_packages(self, temp_dir):
        """Test finding nx packages"""
        pkg1 = temp_dir / "packages" / "lib1"
        pkg1.mkdir(parents=True)

        packages = _find_packages(temp_dir, "nx")

        assert len(packages) >= 1

    def test_find_packages_fallback_to_common(self, temp_dir):
        """Test fallback to packages/ directory"""
        (temp_dir / "pnpm-workspace.yaml").write_text("")  # Empty workspace file

        pkg1 = temp_dir / "packages" / "app"
        pkg1.mkdir(parents=True)

        packages = _find_packages(temp_dir, "pnpm")

        assert len(packages) >= 1


class TestDetectCommand:
    """Tests for the 'detect' CLI command"""

    def test_detect_command_pnpm(self, runner, temp_dir):
        """Test detect command with pnpm monorepo"""
        (temp_dir / "pnpm-workspace.yaml").write_text("packages:\n  - 'packages/*'\n")
        (temp_dir / "packages" / "test-app").mkdir(parents=True)
        (temp_dir / "packages" / "test-app" / "package.json").write_text("{}")

        result = runner.invoke(app, ["detect", "--path", str(temp_dir)])

        assert result.exit_code == 0
        assert "pnpm" in result.output

    def test_detect_command_not_monorepo(self, runner, temp_dir):
        """Test detect command on non-monorepo"""
        result = runner.invoke(app, ["detect", "--path", str(temp_dir)])

        assert result.exit_code == 0
        # Rich may wrap text with newlines, so check with whitespace removed
        output_no_ws = result.output.replace("\n", "")
        assert "不是已知的 monorepo" in output_no_ws

    def test_detect_command_with_package_json(self, runner, temp_dir):
        """Test detect command shows package.json language"""
        (temp_dir / "pnpm-workspace.yaml").write_text("packages:\n  - 'packages/*'\n")

        pkg = temp_dir / "packages" / "node-app"
        pkg.mkdir(parents=True)
        (pkg / "package.json").write_text("{}")

        result = runner.invoke(app, ["detect", "--path", str(temp_dir)])

        assert result.exit_code == 0
        assert "Node/TS" in result.output

    def test_detect_command_with_pyproject(self, runner, temp_dir):
        """Test detect command shows Python language"""
        (temp_dir / "pnpm-workspace.yaml").write_text("packages:\n  - 'packages/*'\n")

        pkg = temp_dir / "packages" / "python-pkg"
        pkg.mkdir(parents=True)
        (pkg / "pyproject.toml").write_text("[project]\nname = 'test'\n")

        result = runner.invoke(app, ["detect", "--path", str(temp_dir)])

        assert result.exit_code == 0
        assert "Python" in result.output

    def test_detect_command_with_cargo(self, runner, temp_dir):
        """Test detect command shows Rust language"""
        (temp_dir / "pnpm-workspace.yaml").write_text("packages:\n  - 'packages/*'\n")

        pkg = temp_dir / "packages" / "rust-crate"
        pkg.mkdir(parents=True)
        (pkg / "Cargo.toml").write_text("[package]\nname = 'test'\n")

        result = runner.invoke(app, ["detect", "--path", str(temp_dir)])

        assert result.exit_code == 0
        assert "Rust" in result.output


class TestStatusCommand:
    """Tests for the 'status' CLI command"""

    @patch("subprocess.run")
    def test_status_command_clean(self, mock_run, runner, temp_dir):
        """Test status command with clean git status"""
        # Setup monorepo
        (temp_dir / "pnpm-workspace.yaml").write_text("packages:\n  - 'packages/*'\n")
        pkg = temp_dir / "packages" / "app1"
        pkg.mkdir(parents=True)

        # Mock git status returning empty (clean)
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = runner.invoke(app, ["status", "--path", str(temp_dir)])

        assert result.exit_code == 0
        assert "干净" in result.output or "0" in result.output

    @patch("subprocess.run")
    def test_status_command_dirty(self, mock_run, runner, temp_dir):
        """Test status command with dirty git status"""
        # Setup monorepo
        (temp_dir / "pnpm-workspace.yaml").write_text("packages:\n  - 'packages/*'\n")
        pkg = temp_dir / "packages" / "app1"
        pkg.mkdir(parents=True)

        # Mock git status returning modified files
        mock_run.return_value = MagicMock(
            returncode=0, stdout=" M src/main.py\n?? new.txt\n", stderr=""
        )

        result = runner.invoke(app, ["status", "--path", str(temp_dir)])

        assert result.exit_code == 0
        assert "2" in result.output or "文件" in result.output

    @patch("subprocess.run")
    def test_status_command_git_error(self, mock_run, runner, temp_dir):
        """Test status command when git command fails"""
        # Setup monorepo
        (temp_dir / "pnpm-workspace.yaml").write_text("packages:\n  - 'packages/*'\n")
        pkg = temp_dir / "packages" / "app1"
        pkg.mkdir(parents=True)

        # Mock git error
        mock_run.side_effect = Exception("Git error")

        result = runner.invoke(app, ["status", "--path", str(temp_dir)])

        assert result.exit_code == 0
        assert "无法获取" in result.output

    def test_status_command_not_monorepo(self, runner, temp_dir):
        """Test status command on non-monorepo"""
        result = runner.invoke(app, ["status", "--path", str(temp_dir)])

        assert result.exit_code == 1
        assert "不是 monorepo" in result.output


class TestRunCommand:
    """Tests for the 'run' CLI command"""

    @patch("subprocess.run")
    def test_run_command_pnpm(self, mock_run, runner, temp_dir):
        """Test run command with pnpm monorepo"""
        # Setup monorepo
        (temp_dir / "pnpm-workspace.yaml").write_text("packages:\n  - 'packages/*'\n")
        pkg = temp_dir / "packages" / "app1"
        pkg.mkdir(parents=True)
        (pkg / "package.json").write_text("{}")

        # Mock successful subprocess run
        mock_run.return_value = MagicMock(returncode=0, stdout="done", stderr="")

        result = runner.invoke(app, ["run", "build", "--path", str(temp_dir)])

        assert result.exit_code == 0
        assert "成功" in result.output or "✓" in result.output

    @patch("subprocess.run")
    def test_run_command_with_scope(self, mock_run, runner, temp_dir):
        """Test run command with scope filter"""
        # Setup monorepo with multiple packages
        (temp_dir / "pnpm-workspace.yaml").write_text("packages:\n  - 'packages/*'\n")

        pkg1 = temp_dir / "packages" / "app-frontend"
        pkg2 = temp_dir / "packages" / "app-backend"
        pkg1.mkdir(parents=True)
        pkg2.mkdir(parents=True)
        (pkg1 / "package.json").write_text("{}")
        (pkg2 / "package.json").write_text("{}")

        mock_run.return_value = MagicMock(returncode=0, stdout="done", stderr="")

        result = runner.invoke(
            app, ["run", "test", "--scope", "frontend", "--path", str(temp_dir)]
        )

        assert result.exit_code == 0

    @patch("subprocess.run")
    def test_run_command_dry_run(self, mock_run, runner, temp_dir):
        """Test run command with dry-run flag"""
        # Setup monorepo
        (temp_dir / "pnpm-workspace.yaml").write_text("packages:\n  - 'packages/*'\n")
        pkg = temp_dir / "packages" / "app1"
        pkg.mkdir(parents=True)
        (pkg / "package.json").write_text("{}")

        result = runner.invoke(
            app, ["run", "build", "--dry-run", "--path", str(temp_dir)]
        )

        assert result.exit_code == 0
        assert "dry" in result.output.lower() or "cd " in result.output

    @patch("subprocess.run")
    def test_run_command_failure(self, mock_run, runner, temp_dir):
        """Test run command when script fails"""
        # Setup monorepo
        (temp_dir / "pnpm-workspace.yaml").write_text("packages:\n  - 'packages/*'\n")
        pkg = temp_dir / "packages" / "app1"
        pkg.mkdir(parents=True)
        (pkg / "package.json").write_text("{}")

        # Mock failed subprocess run
        mock_run.return_value = MagicMock(
            returncode=1, stdout="", stderr="Build failed"
        )

        result = runner.invoke(app, ["run", "build", "--path", str(temp_dir)])

        assert result.exit_code == 0
        assert "✗" in result.output or "失败" in result.output

    @patch("subprocess.run")
    def test_run_command_timeout(self, mock_run, runner, temp_dir):
        """Test run command when script times out"""
        # Setup monorepo
        (temp_dir / "pnpm-workspace.yaml").write_text("packages:\n  - 'packages/*'\n")
        pkg = temp_dir / "packages" / "app1"
        pkg.mkdir(parents=True)
        (pkg / "package.json").write_text("{}")

        # Mock timeout exception
        mock_run.side_effect = TimeoutError("Command timed out")

        result = runner.invoke(app, ["run", "build", "--path", str(temp_dir)])

        assert result.exit_code == 0

    def test_run_command_not_monorepo(self, runner, temp_dir):
        """Test run command on non-monorepo"""
        result = runner.invoke(app, ["run", "build", "--path", str(temp_dir)])

        assert result.exit_code == 1
        assert "不是 monorepo" in result.output

    def test_run_command_no_matching_scope(self, runner, temp_dir):
        """Test run command with non-matching scope"""
        # Setup monorepo
        (temp_dir / "pnpm-workspace.yaml").write_text("packages:\n  - 'packages/*'\n")
        pkg = temp_dir / "packages" / "app1"
        pkg.mkdir(parents=True)
        (pkg / "package.json").write_text("{}")

        result = runner.invoke(
            app, ["run", "test", "--scope", "nonexistent", "--path", str(temp_dir)]
        )

        assert result.exit_code == 0
        assert "没有找到" in result.output or "⚠" in result.output

    @patch("subprocess.run")
    def test_run_command_lerna(self, mock_run, runner, temp_dir):
        """Test run command with lerna monorepo"""
        import json

        # Setup lerna monorepo
        lerna_config = {"packages": ["packages/*"]}
        (temp_dir / "lerna.json").write_text(json.dumps(lerna_config))

        pkg = temp_dir / "packages" / "pkg1"
        pkg.mkdir(parents=True)
        (pkg / "package.json").write_text("{}")

        mock_run.return_value = MagicMock(returncode=0, stdout="done", stderr="")

        result = runner.invoke(app, ["run", "build", "--path", str(temp_dir)])

        assert result.exit_code == 0

    @patch("subprocess.run")
    def test_run_command_nx(self, mock_run, runner, temp_dir):
        """Test run command with nx monorepo"""
        # Setup nx monorepo
        (temp_dir / "nx.json").write_text("{}")

        pkg = temp_dir / "packages" / "lib1"
        pkg.mkdir(parents=True)
        (pkg / "package.json").write_text("{}")

        mock_run.return_value = MagicMock(returncode=0, stdout="done", stderr="")

        result = runner.invoke(app, ["run", "build", "--path", str(temp_dir)])

        assert result.exit_code == 0


class TestMonorepoInfo:
    """Tests for MonorepoInfo dataclass"""

    def test_monorepo_info_creation(self, temp_dir):
        """Test creating MonorepoInfo instance"""
        config_file = temp_dir / "pnpm-workspace.yaml"
        config_file.write_text("")

        packages = [temp_dir / "packages" / "app1"]

        info = MonorepoInfo(
            root=temp_dir,
            type="pnpm",
            packages=packages,
            config_file=config_file,
        )

        assert info.root == temp_dir
        assert info.type == "pnpm"
        assert len(info.packages) == 1
        assert info.config_file == config_file


class TestEdgeCases:
    """Edge case tests"""

    def test_empty_packages_directory(self, temp_dir):
        """Test when packages directory exists but is empty"""
        (temp_dir / "pnpm-workspace.yaml").write_text("packages:\n  - 'packages/*'\n")
        (temp_dir / "packages").mkdir()

        result = detect_monorepo(temp_dir)

        # Should still detect as monorepo, just with empty packages
        assert result is not None
        assert result.type == "pnpm"

    def test_deeply_nested_packages(self, temp_dir):
        """Test detecting packages in nested structure"""
        (temp_dir / "pnpm-workspace.yaml").write_text(
            "packages:\n  - 'packages/**/*'\n"
        )

        # Create deeply nested package
        deep_pkg = temp_dir / "packages" / "category" / "subcategory" / "my-app"
        deep_pkg.mkdir(parents=True)
        (deep_pkg / "package.json").write_text("{}")

        result = detect_monorepo(temp_dir)

        assert result is not None

    @patch("subprocess.run")
    def test_run_command_subprocess_exception(self, mock_run, runner, temp_dir):
        """Test run command when subprocess raises exception"""
        # Setup monorepo
        (temp_dir / "pnpm-workspace.yaml").write_text("packages:\n  - 'packages/*'\n")
        pkg = temp_dir / "packages" / "app1"
        pkg.mkdir(parents=True)
        (pkg / "package.json").write_text("{}")

        # Mock exception
        mock_run.side_effect = Exception("Unexpected error")

        result = runner.invoke(app, ["run", "build", "--path", str(temp_dir)])

        assert result.exit_code == 0
        assert "✗" in result.output


class TestMonorepoConfigs:
    """Tests for MONOREPO_CONFIGS constant"""

    def test_monorepo_configs_structure(self):
        """Test MONOREPO_CONFIGS has correct structure"""
        assert isinstance(MONOREPO_CONFIGS, dict)

        for repo_type, config_files in MONOREPO_CONFIGS.items():
            assert isinstance(repo_type, str)
            assert isinstance(config_files, list)
            assert len(config_files) > 0

    def test_all_supported_types(self):
        """Test all expected monorepo types are supported"""
        expected_types = {"pnpm", "lerna", "nx", "turborepo", "bazel", "rush"}

        assert set(MONOREPO_CONFIGS.keys()) == expected_types


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
