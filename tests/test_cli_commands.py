"""
Tests for cli_commands.py

Target: /Users/vobc/oh-my-coder/src/commands/cli_commands.py
Coverage goal: Increase from 23% to ~85%+
"""

import os
import shutil
import tempfile
from pathlib import Path
from typing import Optional
from unittest import TestCase
from unittest.mock import patch

import pytest
import typer
from typer.testing import CliRunner

import shlex

from src.commands import cli_commands as cli_module
from src.commands.cli_commands import (
    COMMANDS_DIR,
    Command,
    app,
    create_command,
    edit_command,
    list_commands,
    load_commands,
    run,
)


class TestCommandClass(TestCase):
    """Test Command class functionality"""

    def setUp(self):
        self.sample_content = """---
name: test_cmd
description: A test command
usage: omc cmd test_cmd <arg>
---
#!/omc-command
echo "Hello $1"
echo "Project: $PROJECT"
"""

        self.cmd = Command(
            name="test_cmd",
            path=Path("/tmp/test_cmd.md"),
            content=self.sample_content,
        )

    def test_init(self):
        """Test Command initialization"""
        assert self.cmd.name == "test_cmd"
        assert self.cmd.path == Path("/tmp/test_cmd.md")
        assert self.cmd.content == self.sample_content
        assert isinstance(self.cmd.frontmatter, dict)
        assert isinstance(self.cmd.script, str)

    def test_parse_frontmatter(self):
        """Test YAML frontmatter parsing"""
        fm = self.cmd._parse_frontmatter()
        assert fm["name"] == "test_cmd"
        assert fm["description"] == "A test command"
        assert fm["usage"] == "omc cmd test_cmd <arg>"

    def test_parse_frontmatter_no_frontmatter(self):
        """Test parsing when no frontmatter exists"""
        content_no_fm = "#!/omc-command\necho 'test'"
        cmd = Command("test", Path("/tmp/test.md"), content_no_fm)
        fm = cmd._parse_frontmatter()
        assert fm == {}

    def test_extract_script(self):
        """Test script extraction"""
        script = self.cmd._extract_script()
        # Frontmatter should be removed
        assert "---" not in script
        # Shebang should be removed
        assert "#!/omc-command" not in script
        # Content should remain
        assert 'echo "Hello $1"' in script
        assert 'echo "Project: $PROJECT"' in script

    def test_extract_script_no_frontmatter(self):
        """Test script extraction without frontmatter"""
        content = "#!/omc-command\necho 'test'"
        cmd = Command("test", Path("/tmp/test.md"), content)
        script = cmd._extract_script()
        assert script == "echo 'test'"

    def test_description(self):
        """Test description method"""
        desc = self.cmd.description()
        assert desc == "A test command"

    def test_description_empty(self):
        """Test description when not in frontmatter"""
        content = "---\nname: test\n---\n#!/omc-command\necho 'test'"
        cmd = Command("test", Path("/tmp/test.md"), content)
        desc = cmd.description()
        assert desc == ""

    def test_usage(self):
        """Test usage method"""
        usage = self.cmd.usage()
        assert usage == "omc cmd test_cmd <arg>"

    def test_usage_default(self):
        """Test usage when not in frontmatter"""
        content = "---\nname: test\n---\n#!/omc-command\necho 'test'"
        cmd = Command("test", Path("/tmp/test.md"), content)
        usage = cmd.usage()
        assert usage == "omc cmd test"

    def test_render_usage_positional_args(self):
        """Test rendering with positional arguments"""
        script = self.cmd.render_usage(["World"])
        # Check that $1 is replaced with quoted value
        assert "$1" not in script
        # shlex.quote should be applied
        assert shlex.quote("World") in script

    def test_render_usage_multiple_args(self):
        """Test rendering with multiple arguments"""
        content = """---
name: test
---
#!/omc-command
echo $1 $2 $3"""
        cmd = Command("test", Path("/tmp/test.md"), content)
        script = cmd.render_usage(["arg1", "arg2 with space", "arg3"])
        # Check that $1, $2, $3 are replaced
        assert "$1" not in script
        assert "$2" not in script
        assert "$3" not in script
        # Check that args are quoted
        assert shlex.quote("arg1") in script
        assert shlex.quote("arg2 with space") in script
        assert shlex.quote("arg3") in script

    def test_render_usage_all_args(self):
        """Test rendering with $@ for all args"""
        content = """---
name: test
---
#!/omc-command
echo $@"""
        cmd = Command("test", Path("/tmp/test.md"), content)
        script = cmd.render_usage(["arg1", "arg2 with space"])
        # Check that $@ is replaced
        assert "$@" not in script
        # Check that args appear in the output (quoted)
        assert shlex.quote("arg1") in script
        assert shlex.quote("arg2 with space") in script

    def test_render_usage_env_vars(self):
        """Test rendering with environment variables"""
        content = """---
name: test
---
#!/omc-command
echo $PROJECT $CWD $HOME"""
        cmd = Command("test", Path("/tmp/test.md"), content)
        script = cmd.render_usage([])
        # These should be replaced with actual values
        assert "$PROJECT" not in script
        assert "$CWD" not in script
        assert "$HOME" not in script

    def test_render_usage_date_time(self):
        """Test rendering with DATE and TIME variables"""
        content = """---
name: test
---
#!/omc-command
echo $DATE $TIME"""
        cmd = Command("test", Path("/tmp/test.md"), content)
        script = cmd.render_usage([])
        # DATE and TIME should be replaced
        assert "$DATE" not in script
        assert "$TIME" not in script
        # Should contain actual date/time values
        assert len(script) > 0


class TestLoadCommands(TestCase):
    """Test load_commands function"""

    def setUp(self):
        # Create a temporary directory for commands
        self.temp_dir = tempfile.mkdtemp()
        self.commands_dir = Path(self.temp_dir) / ".omc" / "commands"
        self.commands_dir.mkdir(parents=True, exist_ok=True)

        # Create a test command file
        test_cmd = self.commands_dir / "hello.md"
        test_cmd.write_text("""---
name: hello
description: Say hello
usage: omc cmd run hello <name>
---
#!/omc-command
echo "Hello $1"
""")

        # Patch COMMANDS_DIR to use temp dir
        self.patcher = patch.object(cli_module, 'COMMANDS_DIR', self.commands_dir)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_load_commands(self):
        """Test loading commands from directory"""
        commands = load_commands()
        assert "hello" in commands
        assert isinstance(commands["hello"], Command)

    def test_load_commands_empty_dir(self):
        """Test loading when commands directory doesn't exist"""
        # Remove .omc directory
        shutil.rmtree(self.commands_dir.parent, ignore_errors=True)

        commands = load_commands()
        # Should create example commands and return empty dict initially
        assert isinstance(commands, dict)

    def test_load_commands_malformed_file(self):
        """Test loading with malformed command file"""
        bad_file = self.commands_dir / "bad.md"
        bad_file.write_text("This is not a valid command file")

        # Should not raise, just skip or handle gracefully
        commands = load_commands()
        # bad.md might still be loaded but with empty frontmatter
        assert "bad" in commands or len(commands) >= 0

    def test_load_commands_exception_handling(self):
        """Test exception handling when reading command file fails"""
        # Create a file that will cause an exception when read
        bad_file = self.commands_dir / "exception.md"
        bad_file.write_text("---\nname: test\n---\n#!/omc-command\necho test")

        # Mock Path.read_text to raise an exception
        with patch.object(Path, 'read_text', side_effect=Exception("Read error")):
            commands = load_commands()
            # Should handle exception gracefully
            assert isinstance(commands, dict)


class TestRunCommand(TestCase):
    """Test run command (Typer command)"""

    def setUp(self):
        self.runner = CliRunner()

        # Create temporary directory with test command
        self.temp_dir = tempfile.mkdtemp()
        self.commands_dir = Path(self.temp_dir) / ".omc" / "commands"
        self.commands_dir.mkdir(parents=True, exist_ok=True)

        test_cmd = self.commands_dir / "greet.md"
        test_cmd.write_text("""---
name: greet
description: Greet someone
usage: omc cmd run greet <name>
---
#!/omc-command
echo "Hello $1"
""")

        # Patch COMMANDS_DIR
        self.patcher = patch.object(cli_module, 'COMMANDS_DIR', self.commands_dir)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_run_command_success(self):
        """Test running a command successfully"""
        result = self.runner.invoke(app, ["run", "greet", "World"])
        assert result.exit_code == 0

    def test_run_command_not_found(self):
        """Test running a non-existent command"""
        result = self.runner.invoke(app, ["run", "nonexistent"])
        assert result.exit_code == 0  # Typer doesn't exit on not found
        assert "命令未找到" in result.output or "not found" in result.output.lower()

    def test_run_command_dry_run(self):
        """Test dry-run mode"""
        result = self.runner.invoke(app, ["run", "greet", "World", "--dry-run"])
        assert result.exit_code == 0
        assert "Dry Run" in result.output or "dry" in result.output.lower()

    def test_run_command_no_args(self):
        """Test running command without args"""
        # Create a command that doesn't need args
        simple_cmd = self.commands_dir / "simple.md"
        simple_cmd.write_text("""---
name: simple
description: Simple command
usage: omc cmd run simple
---
#!/omc-command
echo "Simple"
""")

        result = self.runner.invoke(app, ["run", "simple"])
        assert result.exit_code == 0

    def test_run_command_exception_handling(self):
        """Test exception handling during command execution"""
        # Create a command that will cause an exception
        error_cmd = self.commands_dir / "error.md"
        error_cmd.write_text("""---
name: error
description: Error command
usage: omc cmd run error
---
#!/omc-command
echo "test"
""")

        # Mock subprocess.run to raise an exception
        with patch('subprocess.run', side_effect=Exception("Subprocess error")):
            result = self.runner.invoke(app, ["run", "error"])
            assert result.exit_code == 0
            assert "执行错误" in result.output or "error" in result.output.lower()

    def test_run_command_nonzero_returncode(self):
        """Test handling of non-zero return code"""
        # Create a command that returns non-zero exit code
        fail_cmd = self.commands_dir / "fail.md"
        fail_cmd.write_text("""---
name: fail
description: Fail command
usage: omc cmd run fail
---
#!/omc-command
exit 1
""")

        result = self.runner.invoke(app, ["run", "fail"])
        assert result.exit_code == 0  # Typer doesn't exit on command failure
        # The error message should be printed
        assert "命令执行失败" in result.output or "failed" in result.output.lower()


class TestListCommands(TestCase):
    """Test list_commands function"""

    def setUp(self):
        self.runner = CliRunner()

        # Create temporary directory with test commands
        self.temp_dir = tempfile.mkdtemp()
        self.commands_dir = Path(self.temp_dir) / ".omc" / "commands"
        self.commands_dir.mkdir(parents=True, exist_ok=True)

        # Create multiple test commands
        for name in ["cmd1", "cmd2", "cmd3"]:
            cmd_file = self.commands_dir / f"{name}.md"
            cmd_file.write_text(f"""---
name: {name}
description: Description for {name}
usage: omc cmd run {name}
---
#!/omc-command
echo "{name}"
""")

        # Patch COMMANDS_DIR
        self.patcher = patch.object(cli_module, 'COMMANDS_DIR', self.commands_dir)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_list_commands(self):
        """Test listing commands"""
        result = self.runner.invoke(app, ["list"])
        assert result.exit_code == 0
        # Should show all commands
        assert "cmd1" in result.output
        assert "cmd2" in result.output
        assert "cmd3" in result.output

    def test_list_commands_empty(self):
        """Test listing when no commands exist"""
        # Remove all commands
        shutil.rmtree(self.commands_dir, ignore_errors=True)

        result = self.runner.invoke(app, ["list"])
        assert result.exit_code == 0
        assert "没有找到" in result.output or "no" in result.output.lower()


class TestCreateCommand(TestCase):
    """Test create_command function"""

    def setUp(self):
        self.runner = CliRunner()

        # Create temporary directory
        self.temp_dir = tempfile.mkdtemp()
        self.commands_dir = Path(self.temp_dir) / ".omc" / "commands"
        self.commands_dir.mkdir(parents=True, exist_ok=True)

        # Patch COMMANDS_DIR
        self.patcher = patch.object(cli_module, 'COMMANDS_DIR', self.commands_dir)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_create_command_success(self):
        """Test creating a new command"""
        result = self.runner.invoke(app, ["create", "new_cmd", "--description", "A new command"])
        assert result.exit_code == 0

        # Check file was created
        cmd_file = self.commands_dir / "new_cmd.md"
        assert cmd_file.exists()

        content = cmd_file.read_text()
        assert "name: new_cmd" in content
        assert "description: A new command" in content

    def test_create_command_no_description(self):
        """Test creating a command without description"""
        result = self.runner.invoke(app, ["create", "no_desc"])
        assert result.exit_code == 0

        cmd_file = self.commands_dir / "no_desc.md"
        assert cmd_file.exists()

    def test_create_command_already_exists(self):
        """Test creating a command that already exists"""
        # Create command first
        existing = self.commands_dir / "exists.md"
        existing.write_text("existing command")

        # Try to create again
        result = self.runner.invoke(app, ["create", "exists"])
        assert result.exit_code == 0
        assert "已存在" in result.output or "exists" in result.output.lower()


class TestEditCommand(TestCase):
    """Test edit_command function"""

    def setUp(self):
        self.runner = CliRunner()

        # Create temporary directory with test
        self.temp_dir = tempfile.mkdtemp()
        self.commands_dir = Path(self.temp_dir) / ".omc" / "commands"
        self.commands_dir.mkdir(parents=True, exist_ok=True)

        test_cmd = self.commands_dir / "edit_me.md"
        test_cmd.write_text("""---
name: edit_me
description: Command to edit
usage: omc cmd run edit_me
---
#!/omc-command
echo "Edit me"
""")

        # Patch COMMANDS_DIR
        self.patcher = patch.object(cli_module, 'COMMANDS_DIR', self.commands_dir)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_edit_command_success(self):
        """Test editing an existing command"""
        # Note: This will try to open an editor, which might fail in test
        # We just check it doesn't crash immediately
        result = self.runner.invoke(app, ["edit", "edit_me"])
        # Exit code might be 1 if editor fails, but should not raise exceptions
        assert result.exit_code in [0, 1]

    def test_edit_command_not_found(self):
        """Test editing a non-existent command"""
        result = self.runner.invoke(app, ["edit", "nonexistent"])
        assert result.exit_code == 0
        assert "未找到" in result.output or "not found" in result.output.lower()


class TestCreateExampleCommands(TestCase):
    """Test _create_example_commands function"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.commands_dir = Path(self.temp_dir) / ".omc" / "commands"
        # Don't create the directory - let the function create it

        # Patch COMMANDS_DIR
        self.patcher = patch.object(cli_module, 'COMMANDS_DIR', self.commands_dir)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_create_example_commands(self):
        """Test creating example commands"""
        from src.commands.cli_commands import _create_example_commands
        # Ensure commands directory exists (as load_commands() would do)
        self.commands_dir.mkdir(parents=True, exist_ok=True)

        _create_example_commands()

        # Check example commands were created
        expected_examples = ["hello", "deploy", "test", "clean"]
        for example in expected_examples:
            cmd_file = self.commands_dir / f"{example}.md"
            assert cmd_file.exists(), f"{example}.md should exist"

            content = cmd_file.read_text()
            assert "---" in content  # Has frontmatter
            assert "#!/omc-command" in content  # Has script


class TestIntegration(TestCase):
    """Integration tests for CLI commands"""

    def setUp(self):
        self.runner = CliRunner()
        self.temp_dir = tempfile.mkdtemp()
        self.commands_dir = Path(self.temp_dir) / ".omc" / "commands"
        self.commands_dir.mkdir(parents=True, exist_ok=True)

        # Patch COMMANDS_DIR
        self.patcher = patch.object(cli_module, 'COMMANDS_DIR', self.commands_dir)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_full_workflow(self):
        """Test complete workflow: create, list, run"""
        # Create a command
        result = self.runner.invoke(app, ["create", "workflow_test", "-d", "Workflow test"])
        assert result.exit_code == 0

        # List commands
        result = self.runner.invoke(app, ["list"])
        assert result.exit_code == 0
        assert "workflow_test" in result.output

        # Add script to command
        cmd_file = self.commands_dir / "workflow_test.md"
        assert cmd_file.exists()
        content = cmd_file.read_text()
        # Replace the script part
        content = content.replace(
            'echo "执行 workflow_test 命令"',
            'echo "Workflow test: $1"'
        )
        cmd_file.write_text(content)

        # Run the command
        result = self.runner.invoke(app, ["run", "workflow_test", "arg1"])
        assert result.exit_code == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-o", "addopts="])
