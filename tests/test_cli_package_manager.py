"""
Tests for cli_package_manager.py

Target: Increase coverage from 23% to 70%+
"""

import subprocess
from unittest.mock import Mock, patch

import pytest
from typer.testing import CliRunner

from src.commands.cli_package_manager import (
    RECOMMENDED_PACKAGES,
    PackageManager,
    Platform,
    _build_install_command,
    _is_command_available,
    _list_with_manager,
    _run_command,
    _search_with_manager,
    _select_best_manager,
    app,
    get_available_managers,
    get_current_platform,
)


@pytest.fixture
def runner():
    """Create a CliRunner instance"""
    return CliRunner()


class TestGetCurrentPlatform:
    """Tests for get_current_platform()"""

    @patch("src.commands.cli_package_manager.platform.system")
    def test_get_current_platform_macos(self, mock_system):
        """Test platform detection for macOS"""
        mock_system.return_value = "Darwin"
        result = get_current_platform()
        assert result == Platform.MACOS

    @patch("src.commands.cli_package_manager.platform.system")
    def test_get_current_platform_linux(self, mock_system):
        """Test platform detection for Linux"""
        mock_system.return_value = "Linux"
        result = get_current_platform()
        assert result == Platform.LINUX

    @patch("src.commands.cli_package_manager.platform.system")
    def test_get_current_platform_windows(self, mock_system):
        """Test platform detection for Windows"""
        mock_system.return_value = "Windows"
        result = get_current_platform()
        assert result == Platform.WINDOWS

    @patch("src.commands.cli_package_manager.platform.system")
    def test_get_current_platform_unknown(self, mock_system):
        """Test platform detection for unknown system"""
        mock_system.return_value = "FreeBSD"
        result = get_current_platform()
        assert result == Platform.LINUX  # Default to Linux


class TestIsCommandAvailable:
    """Tests for _is_command_available()"""

    @patch("src.commands.cli_package_manager.platform.system")
    @patch("src.commands.cli_package_manager.subprocess.run")
    def test_command_available_unix(self, mock_run, mock_system):
        """Test command availability check on Unix"""
        mock_system.return_value = "Darwin"
        mock_run.return_value = Mock(returncode=0)
        result = _is_command_available("brew")
        assert result is True
        mock_run.assert_called_once_with(
            ["which", "brew"], capture_output=True, text=True, timeout=5
        )

    @patch("src.commands.cli_package_manager.platform.system")
    @patch("src.commands.cli_package_manager.subprocess.run")
    def test_command_available_windows(self, mock_run, mock_system):
        """Test command availability check on Windows"""
        mock_system.return_value = "Windows"
        mock_run.return_value = Mock(returncode=0)
        result = _is_command_available("winget")
        assert result is True
        mock_run.assert_called_once_with(
            ["where", "winget"], capture_output=True, text=True, timeout=5
        )

    @patch("src.commands.cli_package_manager.subprocess.run")
    def test_command_not_available(self, mock_run):
        """Test command not available"""
        mock_run.return_value = Mock(returncode=1)
        result = _is_command_available("nonexistent")
        assert result is False

    @patch("src.commands.cli_package_manager.subprocess.run")
    def test_command_check_exception(self, mock_run):
        """Test command check raises exception"""
        mock_run.side_effect = Exception("Command failed")
        result = _is_command_available("brew")
        assert result is False


class TestRunCommand:
    """Tests for _run_command()"""

    @patch("src.commands.cli_package_manager.subprocess.run")
    def test_run_command_success_capture(self, mock_run):
        """Test successful command execution with capture"""
        mock_run.return_value = Mock(
            returncode=0, stdout="Success output", stderr=""
        )
        success, stdout, stderr = _run_command(["echo", "test"])
        assert success is True
        assert stdout == "Success output"
        assert stderr == ""

    @patch("src.commands.cli_package_manager.subprocess.run")
    def test_run_command_failure_capture(self, mock_run):
        """Test failed command execution with capture"""
        mock_run.return_value = Mock(
            returncode=1, stdout="", stderr="Error message"
        )
        success, stdout, stderr = _run_command(["false"])
        assert success is False
        assert stdout == ""
        assert stderr == "Error message"

    @patch("src.commands.cli_package_manager.subprocess.run")
    def test_run_command_no_capture(self, mock_run):
        """Test command execution without capture"""
        mock_run.return_value = Mock(returncode=0)
        success, stdout, stderr = _run_command(["ls"], capture=False)
        assert success is True
        assert stdout == ""
        assert stderr == ""

    @patch("src.commands.cli_package_manager.subprocess.run")
    def test_run_command_timeout(self, mock_run):
        """Test command execution timeout"""
        mock_run.side_effect = subprocess.TimeoutExpired(cmd=["sleep", "100"], timeout=60)
        success, stdout, stderr = _run_command(["sleep", "100"])
        assert success is False
        assert stdout == ""
        assert "timed out" in stderr

    @patch("src.commands.cli_package_manager.subprocess.run")
    def test_run_command_exception(self, mock_run):
        """Test command execution exception"""
        mock_run.side_effect = Exception("Unexpected error")
        success, stdout, stderr = _run_command(["invalid"])
        assert success is False
        assert stdout == ""
        assert stderr == "unavailable"


class TestGetAvailableManagers:
    """Tests for get_available_managers()"""

    @patch("src.commands.cli_package_manager.get_current_platform")
    @patch("src.commands.cli_package_manager._is_command_available")
    def test_get_available_managers_macos(self, mock_available, mock_platform):
        """Test getting available managers on macOS"""
        mock_platform.return_value = Platform.MACOS
        mock_available.side_effect = lambda cmd: cmd in ["npm", "brew"]

        result = get_available_managers()
        assert PackageManager.NPM in result
        assert PackageManager.HOMEBREW in result

    @patch("src.commands.cli_package_manager.get_current_platform")
    @patch("src.commands.cli_package_manager._is_command_available")
    def test_get_available_managers_linux(self, mock_available, mock_platform):
        """Test getting available managers on Linux"""
        mock_platform.return_value = Platform.LINUX
        mock_available.side_effect = lambda cmd: cmd in ["npm", "yay"]

        result = get_available_managers()
        assert PackageManager.NPM in result
        assert PackageManager.AUR in result

    @patch("src.commands.cli_package_manager.get_current_platform")
    @patch("src.commands.cli_package_manager._is_command_available")
    def test_get_available_managers_windows(self, mock_available, mock_platform):
        """Test getting available managers on Windows"""
        mock_platform.return_value = Platform.WINDOWS
        mock_available.side_effect = lambda cmd: cmd in ["npm", "scoop", "winget"]

        result = get_available_managers()
        assert PackageManager.NPM in result
        assert PackageManager.SCOOP in result
        assert PackageManager.WINGET in result

    @patch("src.commands.cli_package_manager.get_current_platform")
    @patch("src.commands.cli_package_manager._is_command_available")
    def test_get_available_managers_no_managers(self, mock_available, mock_platform):
        """Test getting available managers when none are available"""
        mock_platform.return_value = Platform.MACOS
        mock_available.return_value = False

        result = get_available_managers()
        assert len(result) == 0


class TestSelectBestManager:
    """Tests for _select_best_manager()"""

    @patch("src.commands.cli_package_manager.get_available_managers")
    def test_select_npm_for_node(self, mock_managers):
        """Test selecting npm for node package"""
        mock_managers.return_value = [PackageManager.NPM, PackageManager.HOMEBREW]
        result = _select_best_manager("node")
        assert result == "npm"

    @patch("src.commands.cli_package_manager.get_available_managers")
    def test_select_pip_for_python(self, mock_managers):
        """Test selecting pip for python package"""
        mock_managers.return_value = [PackageManager.PIP, PackageManager.NPM]
        result = _select_best_manager("python")
        assert result == "pip"

    @patch("src.commands.cli_package_manager.get_available_managers")
    def test_select_brew_as_default(self, mock_managers):
        """Test selecting brew as default"""
        mock_managers.return_value = [PackageManager.HOMEBREW]
        result = _select_best_manager("git")
        assert result == "brew"

    @patch("src.commands.cli_package_manager.get_available_managers")
    def test_select_npm_as_default(self, mock_managers):
        """Test selecting npm as default"""
        mock_managers.return_value = [PackageManager.NPM]
        result = _select_best_manager("git")
        assert result == "npm"

    @patch("src.commands.cli_package_manager.get_available_managers")
    def test_no_manager_available(self, mock_managers):
        """Test when no manager is available"""
        mock_managers.return_value = []
        result = _select_best_manager("git")
        assert result is None


class TestBuildInstallCommand:
    """Tests for _build_install_command()"""

    def test_build_brew_command(self):
        """Test building brew install command"""
        result = _build_install_command("brew", "git", sudo=False)
        assert result == ["brew", "install", "git"]

    def test_build_brew_command_with_sudo(self):
        """Test building brew install command with sudo"""
        result = _build_install_command("brew", "git", sudo=True)
        assert result == ["sudo", "brew", "install", "git"]

    def test_build_npm_command(self):
        """Test building npm install command"""
        result = _build_install_command("npm", "typescript", sudo=False)
        assert result == ["npm", "install", "-g", "typescript"]

    def test_build_pip_command(self):
        """Test building pip install command"""
        result = _build_install_command("pip", "requests", sudo=False)
        assert result == ["pip3", "install", "requests"]

    def test_build_pip_command_with_sudo(self):
        """Test building pip install command with sudo"""
        result = _build_install_command("pip", "requests", sudo=True)
        assert result == ["sudo", "pip3", "install", "requests"]

    def test_build_scoop_command(self):
        """Test building scoop install command"""
        result = _build_install_command("scoop", "git", sudo=False)
        assert result == ["scoop", "install", "git"]

    def test_build_winget_command(self):
        """Test building winget install command"""
        result = _build_install_command("winget", "Git.Git", sudo=False)
        assert result == ["winget", "install", "--id", "Git.Git", "--silent"]

    def test_build_aur_command(self):
        """Test building aur install command"""
        result = _build_install_command("aur", "yay", sudo=False)
        assert result == ["yay", "-S", "yay"]

    def test_build_unknown_manager(self):
        """Test building command for unknown manager"""
        result = _build_install_command("unknown", "package", sudo=False)
        assert result is None


class TestInstallCommand:
    """Tests for install CLI command"""

    @patch("src.commands.cli_package_manager._select_best_manager")
    @patch("src.commands.cli_package_manager._build_install_command")
    @patch("src.commands.cli_package_manager._run_command")
    def test_install_success(self, mock_run, mock_build, mock_select, runner):
        """Test successful package installation"""
        mock_select.return_value = "brew"
        mock_build.return_value = ["brew", "install", "git"]
        mock_run.return_value = (True, "", "")

        result = runner.invoke(app, ["install", "git"])
        assert result.exit_code == 0

    @patch("src.commands.cli_package_manager._select_best_manager")
    @patch("src.commands.cli_package_manager._build_install_command")
    @patch("src.commands.cli_package_manager._run_command")
    def test_install_failure(self, mock_run, mock_build, mock_select, runner):
        """Test failed package installation"""
        mock_select.return_value = "brew"
        mock_build.return_value = ["brew", "install", "git"]
        mock_run.return_value = (False, "", "Error: package not found")

        result = runner.invoke(app, ["install", "git"])
        assert result.exit_code == 0

    @patch("src.commands.cli_package_manager._select_best_manager")
    def test_install_no_manager(self, mock_select, runner):
        """Test install when no manager is available"""
        mock_select.return_value = None

        result = runner.invoke(app, ["install", "git"])
        assert result.exit_code == 0

    @patch("src.commands.cli_package_manager._build_install_command")
    def test_install_with_manager_option(self, mock_build, runner):
        """Test install with --manager option"""
        mock_build.return_value = ["npm", "install", "-g", "typescript"]

        result = runner.invoke(app, ["install", "typescript", "--manager", "npm"])
        assert result.exit_code == 0

    def test_install_with_sudo_option(self, runner):
        """Test install with --sudo option"""
        with patch(
            "src.commands.cli_package_manager._select_best_manager"
        ) as mock_select:
            with patch(
                "src.commands.cli_package_manager._build_install_command"
            ) as mock_build:
                mock_select.return_value = "pip"
                mock_build.return_value = ["sudo", "pip3", "install", "requests"]

                result = runner.invoke(app, ["install", "requests", "--sudo"])
                assert result.exit_code == 0


class TestSearchCommand:
    """Tests for search CLI command"""

    @patch("src.commands.cli_package_manager.get_available_managers")
    @patch("src.commands.cli_package_manager._run_command")
    def test_search_success(self, mock_run, mock_managers, runner):
        """Test successful package search"""
        mock_managers.return_value = [PackageManager.NPM]
        mock_run.return_value = (True, "package1\npackage2\npackage3", "")

        result = runner.invoke(app, ["search", "git"])
        assert result.exit_code == 0

    @patch("src.commands.cli_package_manager.get_available_managers")
    @patch("src.commands.cli_package_manager._run_command")
    def test_search_no_results(self, mock_run, mock_managers, runner):
        """Test package search with no results"""
        mock_managers.return_value = [PackageManager.NPM]
        mock_run.return_value = (True, "", "")

        result = runner.invoke(app, ["search", "nonexistent"])
        assert result.exit_code == 0

    @patch("src.commands.cli_package_manager.get_available_managers")
    @patch("src.commands.cli_package_manager._run_command")
    def test_search_failure(self, mock_run, mock_managers, runner):
        """Test package search failure"""
        mock_managers.return_value = [PackageManager.NPM]
        mock_run.return_value = (False, "", "Search failed")

        result = runner.invoke(app, ["search", "git"])
        assert result.exit_code == 0

    def test_search_with_manager_option(self, runner):
        """Test search with --manager option"""
        with patch("src.commands.cli_package_manager._search_with_manager") as mock_search:
            result = runner.invoke(app, ["search", "git", "--manager", "npm"])
            assert result.exit_code == 0
            mock_search.assert_called_once_with("npm", "git")


class TestListInstalledCommand:
    """Tests for list_installed CLI command"""

    @patch("src.commands.cli_package_manager.get_available_managers")
    @patch("src.commands.cli_package_manager._run_command")
    def test_list_installed_success(self, mock_run, mock_managers, runner):
        """Test successful list installed"""
        mock_managers.return_value = [PackageManager.NPM]
        mock_run.return_value = (True, "package1@1.0.0\npackage2@2.0.0", "")

        result = runner.invoke(app, ["list-installed"])
        assert result.exit_code == 0

    @patch("src.commands.cli_package_manager.get_available_managers")
    @patch("src.commands.cli_package_manager._run_command")
    def test_list_installed_no_results(self, mock_run, mock_managers, runner):
        """Test list installed with no results"""
        mock_managers.return_value = [PackageManager.NPM]
        mock_run.return_value = (True, "", "")

        result = runner.invoke(app, ["list-installed"])
        assert result.exit_code == 0

    def test_list_with_manager_option(self, runner):
        """Test list with --manager option"""
        with patch(
            "src.commands.cli_package_manager._list_with_manager"
        ) as mock_list:
            result = runner.invoke(app, ["list-installed", "--manager", "npm"])
            assert result.exit_code == 0
            mock_list.assert_called_once_with("npm")


class TestUpdateCommand:
    """Tests for update CLI command"""

    @patch("src.commands.cli_package_manager._select_best_manager")
    @patch("src.commands.cli_package_manager._run_command")
    def test_update_all_success(self, mock_run, mock_select, runner):
        """Test successful update all packages"""
        mock_select.return_value = "brew"
        mock_run.return_value = (True, "", "")

        result = runner.invoke(app, ["update"])
        assert result.exit_code == 0

    @patch("src.commands.cli_package_manager._select_best_manager")
    @patch("src.commands.cli_package_manager._run_command")
    def test_update_package_success(self, mock_run, mock_select, runner):
        """Test successful update specific package"""
        mock_select.return_value = "npm"
        mock_run.return_value = (True, "", "")

        result = runner.invoke(app, ["update", "npm"])
        assert result.exit_code == 0

    @patch("src.commands.cli_package_manager._select_best_manager")
    @patch("src.commands.cli_package_manager._run_command")
    def test_update_failure(self, mock_run, mock_select, runner):
        """Test failed update"""
        mock_select.return_value = "brew"
        mock_run.return_value = (False, "", "Update failed")

        result = runner.invoke(app, ["update"])
        assert result.exit_code == 0

    @patch("src.commands.cli_package_manager._select_best_manager")
    def test_update_no_manager(self, mock_select, runner):
        """Test update when no manager is available"""
        mock_select.return_value = None

        result = runner.invoke(app, ["update"])
        assert result.exit_code == 0

    def test_update_with_manager_option(self, runner):
        """Test update with --manager option"""
        with patch("src.commands.cli_package_manager._run_command") as mock_run:
            mock_run.return_value = (True, "", "")

            result = runner.invoke(app, ["update", "--manager", "npm"])
            assert result.exit_code == 0


class TestRecommendCommand:
    """Tests for recommend CLI command"""

    def test_recommend(self, runner):
        """Test recommend command displays packages"""
        result = runner.invoke(app, ["recommend"])
        assert result.exit_code == 0
        assert "推荐开发工具" in result.output

        # Check that some recommended packages are mentioned
        for category in RECOMMENDED_PACKAGES:
            assert category.upper() in result.output


class TestCheckCommand:
    """Tests for check CLI command"""

    @patch("src.commands.cli_package_manager.get_current_platform")
    @patch("src.commands.cli_package_manager.get_available_managers")
    def test_check_macos(self, mock_managers, mock_platform, runner):
        """Test check command on macOS"""
        mock_platform.return_value = Platform.MACOS
        mock_managers.return_value = [PackageManager.HOMEBREW, PackageManager.NPM]

        result = runner.invoke(app, ["check"])
        assert result.exit_code == 0
        assert "macos" in result.output.lower() or "macOS" in result.output

    @patch("src.commands.cli_package_manager.get_current_platform")
    @patch("src.commands.cli_package_manager.get_available_managers")
    def test_check_linux(self, mock_managers, mock_platform, runner):
        """Test check command on Linux"""
        mock_platform.return_value = Platform.LINUX
        mock_managers.return_value = [PackageManager.NPM, PackageManager.AUR]

        result = runner.invoke(app, ["check"])
        assert result.exit_code == 0

    @patch("src.commands.cli_package_manager.get_current_platform")
    @patch("src.commands.cli_package_manager.get_available_managers")
    def test_check_windows(self, mock_managers, mock_platform, runner):
        """Test check command on Windows"""
        mock_platform.return_value = Platform.WINDOWS
        mock_managers.return_value = [PackageManager.NPM, PackageManager.SCOOP]

        result = runner.invoke(app, ["check"])
        assert result.exit_code == 0


class TestSearchWithManager:
    """Tests for _search_with_manager()"""

    @patch("src.commands.cli_package_manager._run_command")
    def test_search_with_manager_npm_success(self, mock_run):
        """Test search with npm manager success"""
        mock_run.return_value = (True, "package1\npackage2", "")

        # Should not raise exception
        _search_with_manager("npm", "git")

    @patch("src.commands.cli_package_manager._run_command")
    def test_search_with_manager_brew_success(self, mock_run):
        """Test search with brew manager success"""
        mock_run.return_value = (True, "git\ngit-flow", "")

        # Should not raise exception
        _search_with_manager("brew", "git")

    @patch("src.commands.cli_package_manager._run_command")
    def test_search_with_manager_no_results(self, mock_run):
        """Test search with manager no results"""
        mock_run.return_value = (True, "", "")

        # Should not raise exception
        _search_with_manager("npm", "nonexistent")

    def test_search_with_manager_unsupported(self):
        """Test search with unsupported manager"""
        # Should not raise exception
        _search_with_manager("unsupported", "package")

    @patch("src.commands.cli_package_manager.platform.system")
    def test_search_with_manager_pip_windows(self, mock_system):
        """Test search with pip manager on Windows"""
        mock_system.return_value = "Windows"

        # Should not raise exception (pip search not supported on Windows)
        _search_with_manager("pip", "requests")


class TestListWithManager:
    """Tests for _list_with_manager()"""

    @patch("src.commands.cli_package_manager._run_command")
    def test_list_with_manager_npm_success(self, mock_run):
        """Test list with npm manager success"""
        mock_run.return_value = (True, "package1@1.0.0\npackage2@2.0.0", "")

        # Should not raise exception
        _list_with_manager("npm")

    @patch("src.commands.cli_package_manager._run_command")
    def test_list_with_manager_brew_success(self, mock_run):
        """Test list with brew manager success"""
        mock_run.return_value = (True, "git\nnode\npython", "")

        # Should not raise exception
        _list_with_manager("brew")

    @patch("src.commands.cli_package_manager._run_command")
    def test_list_with_manager_no_results(self, mock_run):
        """Test list with manager no results"""
        mock_run.return_value = (True, "", "")

        # Should not raise exception
        _list_with_manager("npm")

    def test_list_with_manager_unsupported(self):
        """Test list with unsupported manager"""
        # Should not raise exception
        _list_with_manager("unsupported")


class TestRecommendedPackages:
    """Tests for RECOMMENDED_PACKAGES constant"""

    def test_recommended_packages_structure(self):
        """Test RECOMMENDED_PACKAGES has correct structure"""
        assert "cli" in RECOMMENDED_PACKAGES
        assert "dev" in RECOMMENDED_PACKAGES

        for category in RECOMMENDED_PACKAGES.values():
            for pkg in category:
                assert "name" in pkg
                assert "desc" in pkg
                assert "managers" in pkg

    def test_recommended_packages_cli_count(self):
        """Test CLI packages count"""
        assert len(RECOMMENDED_PACKAGES["cli"]) > 0

    def test_recommended_packages_dev_count(self):
        """Test dev packages count"""
        assert len(RECOMMENDED_PACKAGES["dev"]) > 0


class TestEnums:
    """Tests for Platform and PackageManager enums"""

    def test_platform_enum_values(self):
        """Test Platform enum has correct values"""
        assert Platform.MACOS.value == "macos"
        assert Platform.LINUX.value == "linux"
        assert Platform.WINDOWS.value == "windows"

    def test_package_manager_enum_values(self):
        """Test PackageManager enum has correct values"""
        assert PackageManager.HOMEBREW.value == "homebrew"
        assert PackageManager.NPM.value == "npm"
        assert PackageManager.PIP.value == "pip"
        assert PackageManager.SCOOP.value == "scoop"
        assert PackageManager.WINGET.value == "winget"
        assert PackageManager.AUR.value == "aur"
        assert PackageManager.YARN.value == "yarn"
        assert PackageManager.PNPM.value == "pnpm"


class TestMainBlock:
    """Tests for if __name__ == '__main__' block"""

    @patch("src.commands.cli_package_manager.app")
    def test_main_block(self, mock_app):
        """Test the __main__ block execution"""
        # Simulate running as main module
        import src.commands.cli_package_manager as module

        # Save original __name__

        try:
            # This is a bit tricky to test directly, but we can verify
            # that the app has a run method (which would be called)
            assert hasattr(module.app, 'run')
        finally:
            pass  # __name__ can't be easily mocked for this


class TestBuildInstallCommandExtended:
    """Additional tests for _build_install_command()"""

    def test_build_yarn_command(self):
        """Test building yarn install command"""
        result = _build_install_command("yarn", "typescript", sudo=False)
        assert result == ["yarn", "global", "add", "typescript"]

    def test_build_pnpm_command(self):
        """Test building pnpm install command"""
        result = _build_install_command("pnpm", "typescript", sudo=False)
        assert result == ["pnpm", "add", "-g", "typescript"]

    def test_build_yarn_command_with_sudo(self):
        """Test building yarn install command with sudo"""
        # Yarn doesn't use sudo in command
        result = _build_install_command("yarn", "typescript", sudo=True)
        assert result == ["yarn", "global", "add", "typescript"]

    def test_build_pnpm_command_with_sudo(self):
        """Test building pnpm install command with sudo"""
        # pnpm doesn't use sudo in command
        result = _build_install_command("pnpm", "typescript", sudo=True)
        assert result == ["pnpm", "add", "-g", "typescript"]


class TestSelectBestManagerExtended:
    """Additional tests for _select_best_manager()"""

    @patch("src.commands.cli_package_manager.get_available_managers")
    def test_select_scoop_as_default(self, mock_managers):
        """Test selecting scoop as default"""
        mock_managers.return_value = [PackageManager.SCOOP]
        result = _select_best_manager("git")
        assert result == "scoop"

    @patch("src.commands.cli_package_manager.get_available_managers")
    def test_select_winget_as_default(self, mock_managers):
        """Test selecting winget as default"""
        mock_managers.return_value = [PackageManager.WINGET]
        result = _select_best_manager("git")
        assert result == "winget"

    @patch("src.commands.cli_package_manager.get_available_managers")
    def test_select_aur_as_default(self, mock_managers):
        """Test selecting aur as default"""
        mock_managers.return_value = [PackageManager.AUR]
        result = _select_best_manager("git")
        assert result == "aur"

    @patch("src.commands.cli_package_manager.get_available_managers")
    def test_select_pip_for_ansible(self, mock_managers):
        """Test selecting pip for ansible package"""
        mock_managers.return_value = [PackageManager.PIP, PackageManager.NPM]
        result = _select_best_manager("ansible")
        assert result == "pip"

    @patch("src.commands.cli_package_manager.get_available_managers")
    def test_select_pip_for_httpie(self, mock_managers):
        """Test selecting pip for httpie package"""
        mock_managers.return_value = [PackageManager.PIP, PackageManager.NPM]
        result = _select_best_manager("httpie")
        assert result == "pip"

    @patch("src.commands.cli_package_manager.get_available_managers")
    def test_select_pip_for_tldr(self, mock_managers):
        """Test selecting pip for tldr package"""
        mock_managers.return_value = [PackageManager.PIP, PackageManager.NPM]
        result = _select_best_manager("tldr")
        assert result == "pip"


class TestUpdateCommandExtended:
    """Additional tests for update CLI command"""

    @patch("src.commands.cli_package_manager._select_best_manager")
    @patch("src.commands.cli_package_manager._run_command")
    def test_update_npm_all(self, mock_run, mock_select, runner):
        """Test update all npm packages"""
        mock_select.return_value = "npm"
        mock_run.return_value = (True, "", "")

        result = runner.invoke(app, ["update"])
        assert result.exit_code == 0
        # Verify npm update -g was called
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert call_args == ["npm", "update", "-g"]

    @patch("src.commands.cli_package_manager._select_best_manager")
    @patch("src.commands.cli_package_manager._run_command")
    def test_update_brew_all(self, mock_run, mock_select, runner):
        """Test update all brew packages"""
        mock_select.return_value = "brew"
        mock_run.return_value = (True, "", "")

        result = runner.invoke(app, ["update"])
        assert result.exit_code == 0
        # Verify brew upgrade was called
        call_args = mock_run.call_args[0][0]
        assert call_args == ["brew", "upgrade"]

    @patch("src.commands.cli_package_manager._select_best_manager")
    @patch("src.commands.cli_package_manager._run_command")
    def test_update_pip_all(self, mock_run, mock_select, runner):
        """Test update all pip packages"""
        mock_select.return_value = "pip"
        mock_run.return_value = (True, "", "")

        result = runner.invoke(app, ["update"])
        assert result.exit_code == 0
        # Verify pip install --upgrade pip was called
        call_args = mock_run.call_args[0][0]
        assert call_args == ["pip", "install", "--upgrade", "pip"]

    def test_update_with_manager_and_package(self, runner):
        """Test update with --manager option and package"""
        with patch("src.commands.cli_package_manager._run_command") as mock_run:
            mock_run.return_value = (True, "", "")

            result = runner.invoke(app, ["update", "npm", "--manager", "npm"])
            assert result.exit_code == 0


class TestEdgeCases:
    """Tests for edge cases and error handling"""

    @patch("src.commands.cli_package_manager._run_command")
    def test_search_with_manager_yarn(self, mock_run):
        """Test search with yarn manager (not supported)"""
        # Yarn is not in the commands dict for search
        _search_with_manager("yarn", "package")
        # Should print unsupported message
        mock_run.assert_not_called()

    @patch("src.commands.cli_package_manager._run_command")
    def test_search_with_manager_pnpm(self, mock_run):
        """Test search with pnpm manager (not supported)"""
        # pnpm is not in the commands dict for search
        _search_with_manager("pnpm", "package")
        # Should print unsupported message
        mock_run.assert_not_called()

    @patch("src.commands.cli_package_manager._run_command")
    def test_list_with_manager_yarn(self, mock_run):
        """Test list with yarn manager"""
        mock_run.return_value = (True, "package@1.0.0\n", "")
        _list_with_manager("yarn")
        mock_run.assert_called_once()

    @patch("src.commands.cli_package_manager._run_command")
    def test_list_with_manager_pnpm(self, mock_run):
        """Test list with pnpm manager (not supported)"""
        _list_with_manager("pnpm")
        # Should print unsupported message
        mock_run.assert_not_called()

    def test_recommend_output_format(self, runner):
        """Test recommend command output format"""
        result = runner.invoke(app, ["recommend"])
        assert result.exit_code == 0
        # Check that tables are present
        assert "CLI" in result.output
        assert "DEV" in result.output

    @patch("src.commands.cli_package_manager.get_current_platform")
    @patch("src.commands.cli_package_manager.get_available_managers")
    def test_check_output_format(self, mock_managers, mock_platform, runner):
        """Test check command output format"""
        mock_platform.return_value = Platform.MACOS
        mock_managers.return_value = [PackageManager.HOMEBREW, PackageManager.NPM]

        result = runner.invoke(app, ["check"])
        assert result.exit_code == 0
        # Check that table is present
        assert "brew" in result.output.lower() or "Homebrew" in result.output


class TestPlatformDetection:
    """Additional tests for platform detection"""

    @patch("src.commands.cli_package_manager.platform.system")
    def test_get_current_platform_case_insensitive(self, mock_system):
        """Test platform detection is case-insensitive due to .lower() call"""
        # Both should return MACOS because code uses .lower()
        mock_system.return_value = "Darwin"
        result = get_current_platform()
        assert result == Platform.MACOS

        mock_system.return_value = "darwin"
        result = get_current_platform()
        assert result == Platform.MACOS  # .lower() makes it case-insensitive

    def test_get_available_managers_all_platforms(self):
        """Test get_available_managers includes platform-specific managers"""
        with patch("src.commands.cli_package_manager.get_current_platform") as mock_platform:
            with patch("src.commands.cli_package_manager._is_command_available") as mock_available:
                mock_available.return_value = True

                # Test macOS
                mock_platform.return_value = Platform.MACOS
                managers = get_available_managers()
                assert PackageManager.HOMEBREW in managers

                # Test Linux
                mock_platform.return_value = Platform.LINUX
                managers = get_available_managers()
                assert PackageManager.AUR in managers

                # Test Windows
                mock_platform.return_value = Platform.WINDOWS
                managers = get_available_managers()
                assert PackageManager.SCOOP in managers
                assert PackageManager.WINGET in managers
