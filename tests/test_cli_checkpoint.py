"""测试 cli_checkpoint.py — Checkpoint CLI 命令"""

from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from src.commands.cli_checkpoint import app

runner = CliRunner()


class TestListCommand:
    """测试 list 命令"""

    @patch("src.commands.cli_checkpoint.CheckpointManager")
    def test_list_empty(self, mock_cm_class):
        """测试无快照时显示提示信息"""
        mock_cm = MagicMock()
        mock_cm.list.return_value = []
        mock_cm_class.return_value = mock_cm

        result = runner.invoke(app, ["list"])
        assert result.exit_code == 0
        assert "暂无快照" in result.output

    @patch("src.commands.cli_checkpoint.CheckpointManager")
    def test_list_with_checkpoints(self, mock_cm_class):
        """测试列出快照"""
        mock_cm = MagicMock()
        mock_cm.list.return_value = [
            {
                "id": "cp-001",
                "task_id": "task-123",
                "description": "Before refactoring",
                "file_count": 5,
                "total_size": 2048,
                "created_at": "2024-01-15T10:30:00",
            },
            {
                "id": "cp-002",
                "task_id": "task-456",
                "description": "After adding feature X",
                "file_count": 8,
                "total_size": 4096,
                "created_at": "2024-01-15T11:00:00",
            },
        ]
        mock_cm_class.return_value = mock_cm

        result = runner.invoke(app, ["list"])
        assert result.exit_code == 0
        assert "cp-001" in result.output
        assert "cp-002" in result.output
        assert "Checkpoint 列表" in result.output

    @patch("src.commands.cli_checkpoint.CheckpointManager")
    def test_list_with_task_filter(self, mock_cm_class):
        """测试按任务 ID 过滤"""
        mock_cm = MagicMock()
        mock_cm.list.return_value = [
            {
                "id": "cp-001",
                "task_id": "task-123",
                "description": "Test",
                "file_count": 1,
                "total_size": 1024,
                "created_at": "2024-01-15T10:30:00",
            }
        ]
        mock_cm_class.return_value = mock_cm

        result = runner.invoke(app, ["list", "--task", "task-123"])
        assert result.exit_code == 0
        mock_cm.list.assert_called_once_with(task_id="task-123", limit=20)

    @patch("src.commands.cli_checkpoint.CheckpointManager")
    def test_list_with_limit(self, mock_cm_class):
        """测试限制返回条数"""
        mock_cm = MagicMock()
        mock_cm.list.return_value = []
        mock_cm_class.return_value = mock_cm

        result = runner.invoke(app, ["list", "--limit", "10"])
        assert result.exit_code == 0
        mock_cm.list.assert_called_once_with(task_id=None, limit=10)

    @patch("src.commands.cli_checkpoint.CheckpointManager")
    def test_list_with_project_path(self, mock_cm_class):
        """测试指定项目路径"""
        mock_cm = MagicMock()
        mock_cm.list.return_value = []
        mock_cm_class.return_value = mock_cm

        result = runner.invoke(app, ["list", "--project", "/tmp/test"])
        assert result.exit_code == 0
        mock_cm_class.assert_called_once_with(project_path=Path("/tmp/test"))


class TestRestoreCommand:
    """测试 restore 命令"""

    @patch("src.commands.cli_checkpoint.CheckpointManager")
    def test_restore_checkpoint_not_found(self, mock_cm_class):
        """测试回滚不存在的快照"""
        mock_cm = MagicMock()
        mock_cm.get_checkpoint.return_value = None
        mock_cm_class.return_value = mock_cm

        result = runner.invoke(app, ["restore", "nonexistent"])
        assert result.exit_code == 1
        assert "未找到 Checkpoint" in result.output

    @patch("src.commands.cli_checkpoint.CheckpointManager")
    def test_restore_with_confirm(self, mock_cm_class):
        """测试确认后回滚"""
        mock_cm = MagicMock()
        mock_checkpoint = MagicMock()
        mock_checkpoint.task_id = "task-123"
        mock_checkpoint.description = "Test checkpoint"
        mock_checkpoint.file_count = 5
        mock_cm.get_checkpoint.return_value = mock_checkpoint
        mock_cm.restore.return_value = "/tmp/backup"
        mock_cm_class.return_value = mock_cm

        result = runner.invoke(app, ["restore", "cp-001", "--yes"])
        assert result.exit_code == 0
        assert "回滚成功" in result.output
        assert "cp-001" in result.output
        mock_cm.restore.assert_called_once_with("cp-001")

    @patch("src.commands.cli_checkpoint.CheckpointManager")
    def test_restore_without_confirm_cancelled(self, mock_cm_class):
        """测试用户取消回滚"""
        mock_cm = MagicMock()
        mock_checkpoint = MagicMock()
        mock_checkpoint.task_id = "task-123"
        mock_checkpoint.description = "Test"
        mock_checkpoint.file_count = 5
        mock_cm.get_checkpoint.return_value = mock_checkpoint
        mock_cm_class.return_value = mock_cm

        result = runner.invoke(app, ["restore", "cp-001"], input="no\n")
        assert result.exit_code == 0
        assert "已取消" in result.output
        mock_cm.restore.assert_not_called()

    @patch("src.commands.cli_checkpoint.CheckpointManager")
    def test_restore_without_confirm_confirmed(self, mock_cm_class):
        """测试用户输入 yes 后回滚"""
        mock_cm = MagicMock()
        mock_checkpoint = MagicMock()
        mock_checkpoint.task_id = "task-123"
        mock_checkpoint.description = "Test"
        mock_checkpoint.file_count = 5
        mock_cm.get_checkpoint.return_value = mock_checkpoint
        mock_cm.restore.return_value = "/tmp/backup"
        mock_cm_class.return_value = mock_cm

        result = runner.invoke(app, ["restore", "cp-001"], input="yes\n")
        assert result.exit_code == 0
        assert "回滚成功" in result.output
        mock_cm.restore.assert_called_once_with("cp-001")

    @patch("src.commands.cli_checkpoint.CheckpointManager")
    def test_restore_failure(self, mock_cm_class):
        """测试回滚失败"""
        mock_cm = MagicMock()
        mock_checkpoint = MagicMock()
        mock_checkpoint.task_id = "task-123"
        mock_checkpoint.description = "Test"
        mock_checkpoint.file_count = 5
        mock_cm.get_checkpoint.return_value = mock_checkpoint
        mock_cm.restore.side_effect = Exception("Restore failed")
        mock_cm_class.return_value = mock_cm

        result = runner.invoke(app, ["restore", "cp-001", "--yes"])
        assert result.exit_code == 1
        assert "回滚失败" in result.output


class TestDiffCommand:
    """测试 diff 命令"""

    @patch("src.commands.cli_checkpoint.CheckpointManager")
    def test_diff_checkpoint_not_found(self, mock_cm_class):
        """测试查看不存在的快照差异"""
        mock_cm = MagicMock()
        mock_cm.diff.side_effect = FileNotFoundError("Checkpoint not found: cp-001")
        mock_cm_class.return_value = mock_cm

        result = runner.invoke(app, ["diff", "cp-001"])
        assert result.exit_code == 1
        assert "Checkpoint not found" in result.output

    @patch("src.commands.cli_checkpoint.CheckpointManager")
    def test_diff_with_changes(self, mock_cm_class):
        """测试查看差异"""
        mock_cm = MagicMock()
        mock_cm.diff.return_value = {
            "added": ["/tmp/new_file.py"],
            "removed": ["/tmp/deleted_file.py"],
            "modified": ["/tmp/changed_file.py"],
        }
        mock_cm.format_diff.return_value = (
            "[green]+ new_file.py[/green]\n"
            "[red]- deleted_file.py[/red]\n"
            "[yellow]M changed_file.py[/yellow]"
        )
        mock_cm_class.return_value = mock_cm

        result = runner.invoke(app, ["diff", "cp-001"])
        assert result.exit_code == 0
        assert "cp-001" in result.output
        assert "共 3 处变更" in result.output


class TestDeleteCommand:
    """测试 delete 命令"""

    @patch("src.commands.cli_checkpoint.CheckpointManager")
    def test_delete_success(self, mock_cm_class):
        """测试删除快照"""
        mock_cm = MagicMock()
        mock_cm.delete.return_value = True
        mock_cm_class.return_value = mock_cm

        result = runner.invoke(app, ["delete", "cp-001"])
        assert result.exit_code == 0
        assert "已删除" in result.output
        assert "cp-001" in result.output
        mock_cm.delete.assert_called_once_with("cp-001")

    @patch("src.commands.cli_checkpoint.CheckpointManager")
    def test_delete_not_found(self, mock_cm_class):
        """测试删除不存在的快照"""
        mock_cm = MagicMock()
        mock_cm.delete.return_value = False
        mock_cm_class.return_value = mock_cm

        result = runner.invoke(app, ["delete", "nonexistent"])
        assert result.exit_code == 1
        assert "未找到 Checkpoint" in result.output


class TestInfoCommand:
    """测试 info 命令"""

    @patch("src.commands.cli_checkpoint.CheckpointManager")
    def test_info_checkpoint_not_found(self, mock_cm_class):
        """测试查看不存在的快照详情"""
        mock_cm = MagicMock()
        mock_cm.get_checkpoint.return_value = None
        mock_cm_class.return_value = mock_cm

        result = runner.invoke(app, ["info", "nonexistent"])
        assert result.exit_code == 1
        assert "未找到 Checkpoint" in result.output

    @patch("src.commands.cli_checkpoint.CheckpointManager")
    def test_info_success(self, mock_cm_class):
        """测试查看快照详情"""
        mock_cm = MagicMock()
        mock_checkpoint = MagicMock()
        mock_checkpoint.id = "cp-001"
        mock_checkpoint.task_id = "task-123"
        mock_checkpoint.description = "Test checkpoint"
        mock_checkpoint.created_at = "2024-01-15T10:30:00"
        mock_checkpoint.file_count = 5
        mock_checkpoint.total_size = 2048
        mock_checkpoint.working_dir = "/tmp/test"
        mock_checkpoint.entries = [
            MagicMock(path="/tmp/test/file1.py", size=100),
            MagicMock(path="/tmp/test/file2.py", size=200),
        ]
        mock_cm.get_checkpoint.return_value = mock_checkpoint
        mock_cm_class.return_value = mock_cm

        result = runner.invoke(app, ["info", "cp-001"])
        assert result.exit_code == 0
        assert "cp-001" in result.output
        assert "task-123" in result.output
        assert "Test checkpoint" in result.output


class TestStatsCommand:
    """测试 stats 命令"""

    @patch("src.commands.cli_checkpoint.CheckpointManager")
    def test_stats(self, mock_cm_class):
        """测试查看统计"""
        mock_cm = MagicMock()
        mock_cm.get_stats.return_value = {
            "total_checkpoints": 10,
            "total_files": 50,
            "total_size_bytes": 102400,
        }
        mock_cm_class.return_value = mock_cm

        result = runner.invoke(app, ["stats"])
        assert result.exit_code == 0
        assert "Checkpoint 统计" in result.output
        assert "10" in result.output
        assert "50" in result.output
        assert "100" in result.output  # 102400 // 1024 = 100 KB


class TestEdgeCases:
    """测试边缘情况"""

    @patch("src.commands.cli_checkpoint.CheckpointManager")
    def test_list_size_formatting(self, mock_cm_class):
        """测试文件大小格式化"""
        mock_cm = MagicMock()
        # 测试小于 1KB 的情况
        mock_cm.list.return_value = [
            {
                "id": "cp-001",
                "task_id": "task-123",
                "description": "Test",
                "file_count": 1,
                "total_size": 500,  # < 1024 bytes
                "created_at": "2024-01-15T10:30:00",
            }
        ]
        mock_cm_class.return_value = mock_cm

        result = runner.invoke(app, ["list"])
        assert result.exit_code == 0
        assert "<1 KB" in result.output

    @patch("src.commands.cli_checkpoint.CheckpointManager")
    def test_list_long_description(self, mock_cm_class):
        """测试描述过长时截断"""
        mock_cm = MagicMock()
        mock_cm.list.return_value = [
            {
                "id": "cp-001",
                "task_id": "task-123",
                "description": "A" * 100,  # 长描述
                "file_count": 1,
                "total_size": 1024,
                "created_at": "2024-01-15T10:30:00",
            }
        ]
        mock_cm_class.return_value = mock_cm

        result = runner.invoke(app, ["list"])
        assert result.exit_code == 0
        # Rich 表格会自动截断过长的文本，这里只检查部分内容
        assert "cp-001" in result.output
        assert "AAA" in result.output  # 描述的前几个字符

    @patch("src.commands.cli_checkpoint.CheckpointManager")
    def test_info_many_files(self, mock_cm_class):
        """测试文件列表超过 30 个时显示省略"""
        mock_cm = MagicMock()
        mock_checkpoint = MagicMock()
        mock_checkpoint.id = "cp-001"
        mock_checkpoint.task_id = "task-123"
        mock_checkpoint.description = "Test"
        mock_checkpoint.created_at = "2024-01-15T10:30:00"
        mock_checkpoint.file_count = 50
        mock_checkpoint.total_size = 10240
        mock_checkpoint.working_dir = "/tmp/test"
        # 创建 50 个文件条目
        mock_checkpoint.entries = [
            MagicMock(path=f"/tmp/test/file{i}.py", size=100) for i in range(50)
        ]
        mock_cm.get_checkpoint.return_value = mock_checkpoint
        mock_cm_class.return_value = mock_cm

        result = runner.invoke(app, ["info", "cp-001"])
        assert result.exit_code == 0
        assert "还有 20 个文件" in result.output  # 50 - 30 = 20
