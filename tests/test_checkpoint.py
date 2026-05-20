"""Tests for src/core/checkpoint.py"""

import json
from pathlib import Path

import pytest

from src.core.checkpoint import (
    MAX_SNAPSHOT_FILES,
    Checkpoint,
    CheckpointManager,
    SnapshotEntry,
)


class TestSnapshotEntry:
    """Test SnapshotEntry dataclass"""

    def test_create_entry(self):
        entry = SnapshotEntry(
            path="src/main.py",
            sha256="abc123",
            size=1024,
            modified_at="2026-05-20T14:00:00",
        )
        assert entry.path == "src/main.py"
        assert entry.sha256 == "abc123"
        assert entry.size == 1024
        assert entry.modified_at == "2026-05-20T14:00:00"


class TestCheckpoint:
    """Test Checkpoint dataclass"""

    def test_create_checkpoint(self):
        cp = Checkpoint(
            id="20260520-140000-001-task1",
            task_id="task1",
            description="Test checkpoint",
            created_at="2026-05-20T14:00:00",
            file_count=5,
            total_size=10240,
            working_dir="/tmp/project",
        )
        assert cp.id == "20260520-140000-001-task1"
        assert cp.task_id == "task1"
        assert cp.file_count == 5
        assert len(cp.entries) == 0

    def test_to_dict(self):
        entry = SnapshotEntry(
            path="src/main.py",
            sha256="abc123",
            size=1024,
            modified_at="2026-05-20T14:00:00",
        )
        cp = Checkpoint(
            id="cp1",
            task_id="task1",
            description="Test",
            created_at="2026-05-20T14:00:00",
            file_count=1,
            total_size=1024,
            working_dir="/tmp",
            entries=[entry],
        )
        data = cp.to_dict()
        assert data["id"] == "cp1"
        assert data["task_id"] == "task1"
        assert len(data["entries"]) == 1
        assert data["entries"][0]["path"] == "src/main.py"

    def test_from_dict(self):
        data = {
            "id": "cp1",
            "task_id": "task1",
            "description": "Test",
            "created_at": "2026-05-20T14:00:00",
            "file_count": 1,
            "total_size": 1024,
            "working_dir": "/tmp",
            "entries": [
                {
                    "path": "src/main.py",
                    "sha256": "abc123",
                    "size": 1024,
                    "modified_at": "2026-05-20T14:00:00",
                }
            ],
        }
        cp = Checkpoint.from_dict(data)
        assert cp.id == "cp1"
        assert len(cp.entries) == 1
        assert cp.entries[0].path == "src/main.py"
        assert isinstance(cp.entries[0], SnapshotEntry)


class TestCheckpointManagerInit:
    """Test CheckpointManager initialization"""

    def test_init_with_path(self, tmp_path):
        cm = CheckpointManager(project_path=tmp_path)
        assert cm.project_path == tmp_path
        assert cm.checkpoint_root == tmp_path / ".omc" / "checkpoints"
        assert cm.index_file == tmp_path / ".omc" / "checkpoints" / "index.json"

    def test_init_without_path(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        cm = CheckpointManager()
        assert cm.project_path == tmp_path

    def test_init_creates_directories(self, tmp_path):
        cm = CheckpointManager(project_path=tmp_path)
        assert cm.checkpoint_root.exists()
        assert cm.backup_root.exists()

    def test_load_index_existing(self, tmp_path):
        index_data = {"cp1": {"id": "cp1", "task_id": "task1"}}
        index_file = tmp_path / ".omc" / "checkpoints" / "index.json"
        index_file.parent.mkdir(parents=True, exist_ok=True)
        index_file.write_text(json.dumps(index_data), encoding="utf-8")

        cm = CheckpointManager(project_path=tmp_path)
        assert "cp1" in cm._index

    def test_load_index_missing(self, tmp_path):
        cm = CheckpointManager(project_path=tmp_path)
        assert cm._index == {}

    def test_load_index_invalid_json(self, tmp_path):
        index_file = tmp_path / ".omc" / "checkpoints" / "index.json"
        index_file.parent.mkdir(parents=True, exist_ok=True)
        index_file.write_text("{invalid json}", encoding="utf-8")

        cm = CheckpointManager(project_path=tmp_path)
        assert cm._index == {}


class TestCheckpointManagerCreate:
    """Test CheckpointManager.create"""

    def test_create_simple(self, tmp_path):
        # 创建测试文件
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("print('hello')")

        cm = CheckpointManager(project_path=tmp_path)
        cp_id = cm.create(task_id="task1", description="Initial checkpoint")

        assert cp_id in cm._index
        assert cm._index[cp_id]["task_id"] == "task1"
        assert cm._index[cp_id]["description"] == "Initial checkpoint"
        assert cm._index[cp_id]["file_count"] >= 1

    def test_create_with_multiple_files(self, tmp_path):
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "a.py").write_text("a = 1")
        (tmp_path / "src" / "b.py").write_text("b = 2")
        (tmp_path / "README.md").write_text("# Project")

        cm = CheckpointManager(project_path=tmp_path)
        cp_id = cm.create(task_id="task1")

        assert cm._index[cp_id]["file_count"] == 3

    def test_create_ignores_git(self, tmp_path):
        (tmp_path / ".git").mkdir()
        (tmp_path / ".git" / "config").write_text("git config")
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("code")

        cm = CheckpointManager(project_path=tmp_path)
        cp_id = cm.create(task_id="task1")

        # .git 目录应该被忽略
        assert cm._index[cp_id]["file_count"] == 1

    def test_create_ignores_pycache(self, tmp_path):
        (tmp_path / "__pycache__").mkdir()
        (tmp_path / "__pycache__" / "module.cpython-39.pyc").write_bytes(b"binary")
        (tmp_path / "main.py").write_text("code")

        cm = CheckpointManager(project_path=tmp_path)
        cp_id = cm.create(task_id="task1")

        # __pycache__ 应该被忽略
        assert cm._index[cp_id]["file_count"] == 1

    def test_create_manifest_saved(self, tmp_path):
        (tmp_path / "main.py").write_text("code")

        cm = CheckpointManager(project_path=tmp_path)
        cp_id = cm.create(task_id="task1")

        cp_dir = cm.checkpoint_root / "task1" / cp_id
        manifest_file = cp_dir / "manifest.json"
        assert manifest_file.exists()

        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        assert manifest["id"] == cp_id
        assert manifest["task_id"] == "task1"

    def test_create_snapshot_files_saved(self, tmp_path):
        (tmp_path / "main.py").write_text("print('hello world')")

        cm = CheckpointManager(project_path=tmp_path)
        cp_id = cm.create(task_id="task1")

        cp_dir = cm.checkpoint_root / "task1" / cp_id / "snapshot"
        assert (cp_dir / "main.py").exists()
        assert (cp_dir / "main.py").read_text() == "print('hello world')"

    def test_create_max_files_limit(self, tmp_path):
        # 创建多个文件
        for i in range(10):
            (tmp_path / f"file{i}.txt").write_text(f"content {i}")

        cm = CheckpointManager(project_path=tmp_path)
        cp_id = cm.create(task_id="task1", max_files=5)

        # 应该只保存 5 个文件
        assert cm._index[cp_id]["file_count"] == 5


class TestCheckpointManagerRestore:
    """Test CheckpointManager.restore"""

    def test_restore_simple(self, tmp_path):
        # 创建原始文件
        (tmp_path / "main.py").write_text("original content")

        cm = CheckpointManager(project_path=tmp_path)
        cp_id = cm.create(task_id="task1", description="Before change")

        # 修改文件
        (tmp_path / "main.py").write_text("modified content")

        # 恢复
        backup_dir = cm.restore(cp_id)

        # 验证恢复
        assert (tmp_path / "main.py").read_text() == "original content"

        # 验证备份
        assert Path(backup_dir).exists()
        backup_metadata = Path(backup_dir) / "metadata.json"
        assert backup_metadata.exists()

    def test_restore_nonexistent(self, tmp_path):
        cm = CheckpointManager(project_path=tmp_path)
        with pytest.raises(FileNotFoundError, match="不存在"):
            cm.restore("nonexistent-cp-id")

    def test_restore_creates_backup(self, tmp_path):
        (tmp_path / "main.py").write_text("v1")

        cm = CheckpointManager(project_path=tmp_path)
        cp_id = cm.create(task_id="task1")

        (tmp_path / "main.py").write_text("v2")

        backup_dir = cm.restore(cp_id)

        # 备份应该包含 v2
        backup_file = Path(backup_dir) / "main.py"
        assert backup_file.exists()
        assert backup_file.read_text() == "v2"

    def test_restore_new_file(self, tmp_path):
        (tmp_path / "main.py").write_text("original")

        cm = CheckpointManager(project_path=tmp_path)
        cp_id = cm.create(task_id="task1", description="Initial state")

        # 创建新文件
        (tmp_path / "new_file.py").write_text("new content")

        # 恢复
        cm.restore(cp_id)

        # 恢复只覆盖/创建 snapshot 中的文件，不会删除新文件
        # （这是预期行为，因为 checkpoint 不是完整的版本控制）
        assert (tmp_path / "new_file.py").exists()  # 新文件仍然存在
        assert (tmp_path / "main.py").read_text() == "original"  # 原文件已恢复


class TestCheckpointManagerDiff:
    """Test CheckpointManager.diff"""

    def test_diff_no_changes(self, tmp_path):
        (tmp_path / "main.py").write_text("original")

        cm = CheckpointManager(project_path=tmp_path)
        cp_id = cm.create(task_id="task1")

        result = cm.diff(cp_id)

        assert len(result["added"]) == 0
        assert len(result["removed"]) == 0
        assert len(result["modified"]) == 0
        assert len(result["unchanged"]) >= 1

    def test_diff_modified_file(self, tmp_path):
        (tmp_path / "main.py").write_text("original")

        cm = CheckpointManager(project_path=tmp_path)
        cp_id = cm.create(task_id="task1", description="Original")

        # 修改文件
        (tmp_path / "main.py").write_text("modified")

        result = cm.diff(cp_id)

        assert "main.py" in result["modified"]

    def test_diff_added_file(self, tmp_path):
        cm = CheckpointManager(project_path=tmp_path)
        cp_id = cm.create(task_id="task1", description="Empty")

        # 添加新文件
        (tmp_path / "new_file.py").write_text("new")

        result = cm.diff(cp_id)

        assert "new_file.py" in result["added"]

    def test_diff_removed_file(self, tmp_path):
        (tmp_path / "old_file.py").write_text("old")

        cm = CheckpointManager(project_path=tmp_path)
        cp_id = cm.create(task_id="task1", description="With old file")

        # 删除文件
        (tmp_path / "old_file.py").unlink()

        result = cm.diff(cp_id)

        assert "old_file.py" in result["removed"]

    def test_diff_nonexistent_checkpoint(self, tmp_path):
        cm = CheckpointManager(project_path=tmp_path)
        with pytest.raises(FileNotFoundError, match="不存在"):
            cm.diff("nonexistent-cp-id")


class TestCheckpointManagerDelete:
    """Test CheckpointManager.delete"""

    def test_delete_simple(self, tmp_path):
        (tmp_path / "main.py").write_text("code")

        cm = CheckpointManager(project_path=tmp_path)
        cp_id = cm.create(task_id="task1")

        assert cp_id in cm._index

        result = cm.delete(cp_id)

        assert result is True
        assert cp_id not in cm._index

    def test_delete_removes_directory(self, tmp_path):
        (tmp_path / "main.py").write_text("code")

        cm = CheckpointManager(project_path=tmp_path)
        cp_id = cm.create(task_id="task1")

        cp_dir = cm.checkpoint_root / "task1" / cp_id
        assert cp_dir.exists()

        cm.delete(cp_id)

        assert not cp_dir.exists()

    def test_delete_nonexistent(self, tmp_path):
        cm = CheckpointManager(project_path=tmp_path)
        result = cm.delete("nonexistent-cp-id")

        assert result is False


class TestCheckpointManagerList:
    """Test CheckpointManager.list"""

    def test_list_empty(self, tmp_path):
        cm = CheckpointManager(project_path=tmp_path)
        results = cm.list()

        assert len(results) == 0

    def test_list_multiple(self, tmp_path):
        (tmp_path / "main.py").write_text("code")

        cm = CheckpointManager(project_path=tmp_path)

        cm.create(task_id="task1", description="CP1")
        cm.create(task_id="task2", description="CP2")

        results = cm.list()

        assert len(results) == 2

    def test_list_filter_by_task_id(self, tmp_path):
        (tmp_path / "main.py").write_text("code")

        cm = CheckpointManager(project_path=tmp_path)

        cm.create(task_id="task1", description="CP1")
        cm.create(task_id="task2", description="CP2")
        cm.create(task_id="task1", description="CP3")

        results = cm.list(task_id="task1")

        assert len(results) == 2
        assert all(r["task_id"] == "task1" for r in results)

    def test_list_sorted_by_time(self, tmp_path):
        (tmp_path / "main.py").write_text("code")

        cm = CheckpointManager(project_path=tmp_path)

        cp_id1 = cm.create(task_id="task1")
        cp_id2 = cm.create(task_id="task2")

        results = cm.list()

        # 应该按时间倒序
        assert results[0]["id"] == cp_id2
        assert results[1]["id"] == cp_id1

    def test_list_with_limit(self, tmp_path):
        (tmp_path / "main.py").write_text("code")

        cm = CheckpointManager(project_path=tmp_path)

        for i in range(10):
            cm.create(task_id=f"task{i}")

        results = cm.list(limit=5)

        assert len(results) == 5


class TestCheckpointManagerGetCheckpoint:
    """Test CheckpointManager.get_checkpoint"""

    def test_get_existing(self, tmp_path):
        (tmp_path / "main.py").write_text("code")

        cm = CheckpointManager(project_path=tmp_path)
        cp_id = cm.create(task_id="task1", description="Test CP")

        cp = cm.get_checkpoint(cp_id)

        assert cp is not None
        assert cp.id == cp_id
        assert cp.task_id == "task1"
        assert cp.description == "Test CP"

    def test_get_nonexistent(self, tmp_path):
        cm = CheckpointManager(project_path=tmp_path)
        cp = cm.get_checkpoint("nonexistent-cp-id")

        assert cp is None


class TestCheckpointManagerHelperMethods:
    """Test CheckpointManager helper methods"""

    def test_is_ignored_git(self, tmp_path):
        cm = CheckpointManager(project_path=tmp_path)
        assert cm._is_ignored(tmp_path / ".git" / "config") is True

    def test_is_ignored_pycache(self, tmp_path):
        cm = CheckpointManager(project_path=tmp_path)
        assert cm._is_ignored(tmp_path / "__pycache__" / "module.pyc") is True

    def test_is_ignored_env(self, tmp_path):
        cm = CheckpointManager(project_path=tmp_path)
        assert cm._is_ignored(tmp_path / ".env") is True

    def test_is_ignored_pyc(self, tmp_path):
        cm = CheckpointManager(project_path=tmp_path)
        assert cm._is_ignored(tmp_path / "module.pyc") is True

    def test_is_not_ignored(self, tmp_path):
        cm = CheckpointManager(project_path=tmp_path)
        assert cm._is_ignored(tmp_path / "src" / "main.py") is False

    def test_file_sha256(self, tmp_path):
        test_file = tmp_path / "test.txt"
        test_file.write_text("hello")

        sha256 = CheckpointManager._file_sha256(test_file)

        assert isinstance(sha256, str)
        assert len(sha256) == 64  # SHA256 是 64 字符


class TestCheckpointManagerStats:
    """Test CheckpointManager.get_stats"""

    def test_get_stats_empty(self, tmp_path):
        cm = CheckpointManager(project_path=tmp_path)
        stats = cm.get_stats()

        assert stats["total_checkpoints"] == 0
        assert stats["total_size_bytes"] == 0
        assert stats["total_files"] == 0

    def test_get_stats_with_checkpoints(self, tmp_path):
        (tmp_path / "main.py").write_text("code")

        cm = CheckpointManager(project_path=tmp_path)
        cm.create(task_id="task1")
        cm.create(task_id="task2")

        stats = cm.get_stats()

        assert stats["total_checkpoints"] == 2
        assert stats["total_size_bytes"] >= 0
        assert stats["total_files"] >= 0


class TestCheckpointManagerFormatDiff:
    """Test CheckpointManager.format_diff"""

    def test_format_diff_empty(self):
        cm = CheckpointManager()
        result = cm.format_diff({"added": [], "removed": [], "modified": [], "unchanged": []})

        assert "无差异" in result

    def test_format_diff_with_added(self):
        cm = CheckpointManager()
        result = cm.format_diff({"added": ["src/new.py"], "removed": [], "modified": [], "unchanged": []})

        assert "新增" in result
        assert "src/new.py" in result

    def test_format_diff_with_modified(self):
        cm = CheckpointManager()
        result = cm.format_diff({"added": [], "removed": [], "modified": ["src/main.py"], "unchanged": []})

        assert "已修改" in result
        assert "src/main.py" in result

    def test_format_diff_with_removed(self):
        cm = CheckpointManager()
        result = cm.format_diff({"added": [], "removed": ["src/old.py"], "modified": [], "unchanged": []})

        assert "已删除" in result
        assert "src/old.py" in result


class TestConstants:
    """Test module constants"""

    def test_max_snapshot_files(self):
        assert isinstance(MAX_SNAPSHOT_FILES, int)
        assert MAX_SNAPSHOT_FILES == 100
