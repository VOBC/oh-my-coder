"""
CheckpointManager 单元测试
"""

import json
from pathlib import Path

import pytest

from src.core.checkpoint import CheckpointManager


@pytest.fixture
def tmp_proj(tmp_path):
    """创建临时项目目录结构"""
    proj = tmp_path / "testproject"
    proj.mkdir()
    # 创建一些测试文件
    (proj / "main.py").write_text("print('hello')", encoding="utf-8")
    (proj / "config.json").write_text('{"key": "value"}', encoding="utf-8")
    sub = proj / "src"
    sub.mkdir()
    (sub / "utils.py").write_text("def foo(): pass", encoding="utf-8")
    return proj


@pytest.fixture
def cm(tmp_proj):
    return CheckpointManager(project_path=tmp_proj)


class TestCreate:
    def test_create_basic(self, cm, tmp_proj):
        cp_id = cm.create(task_id="test-task", description="初始快照")
        assert cp_id.startswith("20")  # 时间戳前缀
        assert "test-task" in cp_id

        # 索引已更新
        assert cp_id in cm._index
        assert cm._index[cp_id]["task_id"] == "test-task"
        assert cm._index[cp_id]["description"] == "初始快照"

        # snapshot 文件存在
        cp_dir = Path(cm._index[cp_id]["path"])
        assert (cp_dir / "manifest.json").exists()
        assert (cp_dir / "snapshot" / "main.py").exists()

    def test_create_stores_all_files(self, cm, tmp_proj):
        cp_id = cm.create(task_id="multi-file", description="多文件快照")
        manifest = json.loads(
            (Path(cm._index[cp_id]["path"]) / "manifest.json").read_text(
                encoding="utf-8"
            )
        )
        paths = {e["path"] for e in manifest["entries"]}
        assert "main.py" in paths
        assert "config.json" in paths
        assert "src/utils.py" in paths

    def test_create_ignores_git(self, cm, tmp_proj):
        (tmp_proj / ".git").mkdir()
        (tmp_proj / ".git" / "config").write_text("gitconfig", encoding="utf-8")
        (tmp_proj / "main.py").write_text("x", encoding="utf-8")

        cp_id = cm.create(task_id="ignore-test", description="忽略测试")
        manifest = json.loads(
            (Path(cm._index[cp_id]["path"]) / "manifest.json").read_text(
                encoding="utf-8"
            )
        )
        paths = {e["path"] for e in manifest["entries"]}
        assert ".git" not in str(paths)
        assert ".git/config" not in paths

    def test_create_max_files_limit(self, cm, tmp_proj):
        # 创建超过 MAX_SNAPSHOT_FILES 的文件
        for i in range(150):
            (tmp_proj / f"file_{i}.txt").write_text(f"content {i}", encoding="utf-8")

        cp_id = cm.create(task_id="many-files", description="超多文件", max_files=50)
        manifest = json.loads(
            (Path(cm._index[cp_id]["path"]) / "manifest.json").read_text(
                encoding="utf-8"
            )
        )
        assert manifest["file_count"] <= 50


class TestRestore:
    def test_restore_basic(self, cm, tmp_proj):
        # 先创建快照
        (tmp_proj / "main.py").write_text("original", encoding="utf-8")
        cp_id = cm.create(task_id="restore-test", description="原始状态")

        # 修改文件
        (tmp_proj / "main.py").write_text("modified", encoding="utf-8")
        assert tmp_proj.joinpath("main.py").read_text(encoding="utf-8") == "modified"

        # 恢复
        backup_path = cm.restore(cp_id)
        assert tmp_proj.joinpath("main.py").read_text(encoding="utf-8") == "original"
        assert Path(backup_path).exists()

    def test_restore_creates_backup(self, cm, tmp_proj):
        (tmp_proj / "main.py").write_text("content", encoding="utf-8")
        cp_id = cm.create(task_id="backup-test", description="备份测试")
        (tmp_proj / "main.py").write_text("changed", encoding="utf-8")

        backup_path = cm.restore(cp_id)
        # 备份目录中应有修改后的文件（restore 前的当前状态）
        backed_up = Path(backup_path) / "main.py"
        assert backed_up.exists()
        assert backed_up.read_text(encoding="utf-8") == "changed"
        # 恢复后工作区回到原始内容
        assert tmp_proj.joinpath("main.py").read_text(encoding="utf-8") == "content"

    def test_restore_nonexistent_raises(self, cm):
        with pytest.raises(FileNotFoundError):
            cm.restore("nonexistent-id")


class TestDiff:
    def test_diff_added(self, cm, tmp_proj):
        cp_id = cm.create(task_id="diff-test", description="测试 diff")
        (tmp_proj / "new_file.py").write_text("new content", encoding="utf-8")

        diff = cm.diff(cp_id)
        assert "new_file.py" in diff["added"]
        assert "main.py" in diff["unchanged"]

    def test_diff_modified(self, cm, tmp_proj):
        (tmp_proj / "main.py").write_text("v1", encoding="utf-8")
        cp_id = cm.create(task_id="mod-test", description="修改前")
        (tmp_proj / "main.py").write_text("v2", encoding="utf-8")

        diff = cm.diff(cp_id)
        assert "main.py" in diff["modified"]

    def test_diff_removed(self, cm, tmp_proj):
        (tmp_proj / "to_remove.py").write_text("temp", encoding="utf-8")
        cp_id = cm.create(task_id="remove-test", description="删除前")
        (tmp_proj / "to_remove.py").unlink()

        diff = cm.diff(cp_id)
        assert "to_remove.py" in diff["removed"]

    def test_diff_empty(self, cm, tmp_proj):
        (tmp_proj / "main.py").write_text("same", encoding="utf-8")
        cp_id = cm.create(task_id="no-change", description="无变化")
        diff = cm.diff(cp_id)
        assert "main.py" in diff["unchanged"]


class TestList:
    def test_list_all(self, cm, tmp_proj):
        cm.create(task_id="task-a", description="a")
        cm.create(task_id="task-b", description="b")
        all_list = cm.list()
        assert len(all_list) == 2

    def test_list_filter_task_id(self, cm, tmp_proj):
        cm.create(task_id="shared-task", description="a")
        cm.create(task_id="shared-task", description="b")
        cm.create(task_id="other", description="c")
        assert len(cm.list(task_id="shared-task")) == 2
        assert len(cm.list(task_id="other")) == 1

    def test_list_sorted_by_time(self, cm, tmp_proj):
        import time
        cm.create(task_id="t1", description="first")
        time.sleep(0.05)  # 确保 created_at 不同
        cm.create(task_id="t2", description="second")
        all_list = cm.list()
        # 最新的在前
        assert all_list[0]["task_id"] == "t2"
        assert all_list[1]["task_id"] == "t1"


class TestDelete:
    def test_delete_exists(self, cm, tmp_proj):
        cp_id = cm.create(task_id="delete-me", description="删除测试")
        assert cm.delete(cp_id) is True
        assert cp_id not in cm._index

    def test_delete_not_exists(self, cm):
        assert cm.delete("nonexistent") is False


class TestGetCheckpoint:
    def test_get_checkpoint(self, cm, tmp_proj):
        cp_id = cm.create(task_id="get-test", description="获取测试")
        cp = cm.get_checkpoint(cp_id)
        assert cp is not None
        assert cp.id == cp_id
        assert cp.task_id == "get-test"
        assert len(cp.entries) >= 1

    def test_get_checkpoint_none(self, cm):
        assert cm.get_checkpoint("no-such") is None


class TestFormatDiff:
    def test_format_with_changes(self, cm):
        diff = {
            "added": ["new.py"],
            "removed": ["old.py"],
            "modified": ["main.py"],
            "unchanged": [],
        }
        formatted = cm.format_diff(diff)
        assert "🆕 新增" in formatted
        assert "❌ 已删除" in formatted
        assert "🔄 已修改" in formatted

    def test_format_empty(self, cm):
        diff = {"added": [], "removed": [], "modified": [], "unchanged": ["main.py"]}
        formatted = cm.format_diff(diff)
        assert "✅ 未变" in formatted


class TestStats:
    def test_get_stats(self, cm, tmp_proj):
        cm.create(task_id="s1", description="stat1")
        cm.create(task_id="s2", description="stat2")
        stats = cm.get_stats()
        assert stats["total_checkpoints"] == 2
        assert stats["total_files"] >= 2
        assert stats["total_size_bytes"] > 0


class TestBackupPath:
    def test_backup_root_exists(self, cm):
        assert cm.backup_root.exists()
        assert cm.backup_root.name == "backup"
