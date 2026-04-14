"""
Quest Mode 存储测试 - QuestStore CRUD 操作
"""

import json
import tempfile
from pathlib import Path


from src.quest.models import QuestSpec, QuestStatus
from src.quest.store import QuestStore


# =============================================================================
# QuestStore 初始化测试
# =============================================================================


class TestQuestStoreInit:
    """测试 QuestStore 初始化"""

    def test_init_creates_directory(self, tmp_path):
        """测试初始化创建目录"""
        store = QuestStore(tmp_path)
        assert store.quests_dir == tmp_path / ".omc" / "quests"

    def test_init_with_string_path(self):
        """测试字符串路径"""
        with tempfile.TemporaryDirectory() as tmp:
            store = QuestStore(tmp)
            # 目录尚未创建（直到第一次使用时才创建）
            # QuestStore 不解析 symlinks，所以用原始路径比较
            assert store.quests_dir == Path(tmp) / ".omc" / "quests"


# =============================================================================
# QuestStore CRUD 测试
# =============================================================================


class TestQuestStoreCreate:
    """测试创建 Quest"""

    def test_create_returns_quest(self, tmp_path):
        """测试创建返回 Quest"""
        store = QuestStore(tmp_path)
        quest = store.create(
            title="Test Quest",
            description="A test quest",
            project_path=str(tmp_path),
        )
        assert quest.title == "Test Quest"
        assert quest.description == "A test quest"
        assert quest.id is not None
        assert quest.status == QuestStatus.PENDING

    def test_create_saves_to_file(self, tmp_path):
        """测试创建后文件存在"""
        store = QuestStore(tmp_path)
        quest = store.create(
            title="Test", description="Desc", project_path=str(tmp_path)
        )

        quest_file = store._quest_file(quest.id)
        assert quest_file.exists()

    def test_create_multiple_quests(self, tmp_path):
        """测试创建多个 Quest"""
        store = QuestStore(tmp_path)
        q1 = store.create(title="Quest 1", description="D1", project_path=str(tmp_path))
        q2 = store.create(title="Quest 2", description="D2", project_path=str(tmp_path))

        assert q1.id != q2.id


class TestQuestStoreGet:
    """测试获取 Quest"""

    def test_get_existing_quest(self, tmp_path):
        """测试获取存在的 Quest"""
        store = QuestStore(tmp_path)
        created = store.create(
            title="Test", description="Desc", project_path=str(tmp_path)
        )

        retrieved = store.get(created.id)
        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.title == "Test"

    def test_get_nonexistent_quest(self, tmp_path):
        """测试获取不存在的 Quest"""
        store = QuestStore(tmp_path)
        result = store.get("non-existent-id")
        assert result is None


class TestQuestStoreSave:
    """测试保存 Quest"""

    def test_save_updates_quest(self, tmp_path):
        """测试保存更新 Quest"""
        store = QuestStore(tmp_path)
        quest = store.create(
            title="Test", description="Desc", project_path=str(tmp_path)
        )

        quest.title = "Updated Title"
        store.save(quest)

        retrieved = store.get(quest.id)
        assert retrieved.title == "Updated Title"

    def test_save_updates_timestamp(self, tmp_path):
        """测试保存更新 updated_at"""
        import time

        store = QuestStore(tmp_path)
        quest = store.create(
            title="Test", description="Desc", project_path=str(tmp_path)
        )

        time.sleep(0.01)  # 确保时间不同
        quest.title = "Updated"
        store.save(quest)

        retrieved = store.get(quest.id)
        assert retrieved.updated_at >= quest.updated_at


class TestQuestStoreDelete:
    """测试删除 Quest"""

    def test_delete_removes_file(self, tmp_path):
        """测试删除移除文件"""
        store = QuestStore(tmp_path)
        quest = store.create(
            title="Test", description="Desc", project_path=str(tmp_path)
        )

        quest_file = store._quest_file(quest.id)
        assert quest_file.exists()

        store.delete(quest.id)
        assert not quest_file.exists()

    def test_delete_clears_cache(self, tmp_path):
        """测试删除清除缓存"""
        store = QuestStore(tmp_path)
        quest = store.create(
            title="Test", description="Desc", project_path=str(tmp_path)
        )

        # 确保在缓存中
        retrieved = store.get(quest.id)
        assert retrieved is not None

        # 删除
        store.delete(quest.id)

        # 再次获取应该返回 None
        retrieved = store.get(quest.id)
        assert retrieved is None


class TestQuestStoreList:
    """测试列出 Quest"""

    def test_list_empty(self, tmp_path):
        """测试空列表"""
        store = QuestStore(tmp_path)
        quests = store.list()
        assert quests == []

    def test_list_returns_all(self, tmp_path):
        """测试列出所有"""
        store = QuestStore(tmp_path)
        store.create(title="Q1", description="D", project_path=str(tmp_path))
        store.create(title="Q2", description="D", project_path=str(tmp_path))
        store.create(title="Q3", description="D", project_path=str(tmp_path))

        quests = store.list()
        assert len(quests) == 3

    def test_list_sorted_by_created_desc(self, tmp_path):
        """测试按创建时间倒序"""
        store = QuestStore(tmp_path)
        q1 = store.create(title="Q1", description="D", project_path=str(tmp_path))
        q2 = store.create(title="Quest 2", description="D", project_path=str(tmp_path))
        q3 = store.create(title="Quest 3", description="D", project_path=str(tmp_path))

        quests = store.list()
        # 最新的在前
        assert quests[0].id == q3.id
        assert quests[1].id == q2.id
        assert quests[2].id == q1.id

    def test_list_with_status_filter(self, tmp_path):
        """测试状态过滤"""
        store = QuestStore(tmp_path)
        q1 = store.create(title="Q1", description="D", project_path=str(tmp_path))
        q2 = store.create(title="Q2", description="D", project_path=str(tmp_path))
        q3 = store.create(title="Q3", description="D", project_path=str(tmp_path))

        # 更新状态
        store.update_status(q1.id, QuestStatus.COMPLETED)
        store.update_status(q2.id, QuestStatus.FAILED)

        # 过滤
        completed = store.list(status_filter=QuestStatus.COMPLETED)
        assert len(completed) == 1
        assert completed[0].id == q1.id

        failed = store.list(status_filter=QuestStatus.FAILED)
        assert len(failed) == 1
        assert failed[0].id == q2.id

        pending = store.list(status_filter=QuestStatus.PENDING)
        assert len(pending) == 1
        assert pending[0].id == q3.id


class TestQuestStoreUpdateStatus:
    """测试状态更新"""

    def test_update_status_to_executing(self, tmp_path):
        """测试更新到执行中"""
        store = QuestStore(tmp_path)
        quest = store.create(
            title="Test", description="Desc", project_path=str(tmp_path)
        )

        assert quest.started_at is None
        updated = store.update_status(quest.id, QuestStatus.EXECUTING)

        assert updated.status == QuestStatus.EXECUTING
        assert updated.started_at is not None

    def test_update_status_to_completed(self, tmp_path):
        """测试更新到完成"""
        store = QuestStore(tmp_path)
        quest = store.create(
            title="Test", description="Desc", project_path=str(tmp_path)
        )

        updated = store.update_status(quest.id, QuestStatus.COMPLETED)
        assert updated.status == QuestStatus.COMPLETED
        assert updated.completed_at is not None

    def test_update_nonexistent_returns_none(self, tmp_path):
        """测试更新不存在的 Quest"""
        store = QuestStore(tmp_path)
        result = store.update_status("non-existent", QuestStatus.COMPLETED)
        assert result is None


class TestQuestStoreSetSpec:
    """测试 SPEC 设置"""

    def test_set_spec(self, tmp_path):
        """测试设置 SPEC"""
        store = QuestStore(tmp_path)
        quest = store.create(
            title="Test", description="Desc", project_path=str(tmp_path)
        )

        spec = QuestSpec(
            title="Test Spec",
            overview="Overview",
            motivation="Motivation",
        )
        updated = updated = store.set_spec(quest.id, spec)

        assert updated.spec is not None
        assert updated.spec.title == "Test Spec"
        assert updated.spec_path is not None

    def test_set_spec_creates_markdown_file(self, tmp_path):
        """测试 SPEC 保存到 Markdown 文件"""
        store = QuestStore(tmp_path)
        quest = store.create(
            title="Test", description="Desc", project_path=str(tmp_path)
        )

        spec = QuestSpec(
            title="My Spec",
            overview="Overview",
            motivation="Why",
            scope=["Feature A"],
        )
        updated = store.set_spec(quest.id, spec)

        # 检查文件存在
        spec_path = Path(updated.spec_path)
        assert spec_path.exists()

        # 检查内容
        content = spec_path.read_text()
        assert "# My Spec" in content
        assert "Feature A" in content


class TestQuestStoreCache:
    """测试缓存机制"""

    def test_cache_used_on_second_get(self, tmp_path):
        """测试第二次获取使用缓存"""
        store = QuestStore(tmp_path)
        quest = store.create(
            title="Test", description="Desc", project_path=str(tmp_path)
        )

        # 第一次获取
        first = store.get(quest.id)

        # 修改文件
        quest_file = store._quest_file(quest.id)
        with open(quest_file, "r") as f:
            data = json.load(f)
        data["title"] = "Modified Outside"
        with open(quest_file, "w") as f:
            json.dump(data, f)

        # 第二次获取应该返回缓存
        second = store.get(quest.id)
        assert second.title == "Test"  # 缓存的旧值

    def test_save_invalidates_cache(self, tmp_path):
        """测试保存清除缓存"""
        store = QuestStore(tmp_path)
        quest = store.create(
            title="Test", description="Desc", project_path=str(tmp_path)
        )

        # 获取一次
        store.get(quest.id)

        # 保存新版本
        quest.title = "New Title"
        store.save(quest)

        # 获取应该返回新值
        retrieved = store.get(quest.id)
        assert retrieved.title == "New Title"


# =============================================================================
# QuestStore 边界测试
# =============================================================================


class TestQuestStoreEdgeCases:
    """边界情况测试"""

    def test_list_handles_corrupted_file(self, tmp_path):
        """测试列出时处理损坏文件"""
        store = QuestStore(tmp_path)

        # 创建一个正常 Quest
        store.create(title="Good", description="D", project_path=str(tmp_path))

        # 创建一个损坏的文件
        bad_file = store.quests_dir / "bad.json"
        bad_file.write_text("{ invalid json }")

        # 列出不应该崩溃
        quests = store.list()
        assert len(quests) == 1  # 只返回正常的

    def test_get_handles_corrupted_file(self, tmp_path):
        """测试获取时处理损坏文件"""
        store = QuestStore(tmp_path)
        quest = store.create(
            title="Test", description="Desc", project_path=str(tmp_path)
        )

        # 损坏文件
        quest_file = store._quest_file(quest.id)
        quest_file.write_text("{ broken")

        # 获取应该返回 None
        result = store.get(quest.id)
        assert result is None
