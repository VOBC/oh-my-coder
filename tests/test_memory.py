"""
记忆系统单元测试

覆盖三层记忆：
- ShortTermMemory
- LongTermMemory
- LearningsMemory
- MemoryManager
"""

import tempfile
import time
from pathlib import Path

import pytest

from src.memory.manager import MemoryConfig, MemoryManager
from src.memory.short_term import ShortTermMemory
from src.memory.long_term import LongTermMemory, ProjectPreference, UserPreference
from src.memory.learnings import LearningEntry, LearningsMemory


# ─────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────


@pytest.fixture
def temp_dir():
    """临时目录 fixture"""
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def short_term(temp_dir):
    return ShortTermMemory(temp_dir, max_messages=10)


@pytest.fixture
def long_term(temp_dir):
    return LongTermMemory(temp_dir)


@pytest.fixture
def learnings(temp_dir):
    return LearningsMemory(temp_dir)


@pytest.fixture
def memory_mgr(temp_dir):
    config = MemoryConfig(
        storage_dir=temp_dir,
        short_term_max_messages=5,
    )
    return MemoryManager(config)


# ─────────────────────────────────────────────────────────────────
# ShortTermMemory
# ─────────────────────────────────────────────────────────────────


class TestShortTermMemory:
    def test_create_session(self, short_term):
        session = short_term.create_session(Path("/tmp/project"), "test task")
        assert session is not None
        assert session.task == "test task"
        assert session.session_id is not None
        assert len(session.messages) == 0

    def test_add_message(self, short_term):
        session = short_term.create_session()
        session.add_message("user", "hello")
        assert len(session.messages) == 1
        assert session.messages[0].role == "user"
        assert session.messages[0].content == "hello"

    def test_message_limit(self, short_term):
        """超过 max_messages 时数据正常保存"""
        session = short_term.create_session()
        for i in range(15):
            session.add_message("user", f"msg {i}")
        assert len(session.messages) == 15

    def test_save_and_load_session(self, short_term):
        session = short_term.create_session(Path("/tmp/test"), "save test")
        session.add_message("assistant", "response")
        short_term.save_session(session)

        # 新实例读取
        loaded = short_term.load_session(session.session_id)
        assert loaded is not None
        assert loaded.task == "save test"
        assert len(loaded.messages) == 1
        assert loaded.messages[0].content == "response"

    def test_get_nonexistent_session(self, short_term):
        assert short_term.load_session("no-such-id") is None

    def test_current_session(self, short_term):
        session = short_term.create_session()
        current = short_term.get_current_session()
        assert current is not None
        assert current.session_id == session.session_id


# ─────────────────────────────────────────────────────────────────
# LongTermMemory
# ─────────────────────────────────────────────────────────────────


class TestLongTermMemory:
    def test_get_user_prefs_default(self, long_term):
        prefs = long_term.get_user_prefs()
        assert isinstance(prefs, UserPreference)
        assert prefs.default_model == "deepseek"

    def test_update_user_prefs(self, long_term):
        long_term.update_user_prefs(default_model="kimi", theme="dark")
        prefs = long_term.get_user_prefs()
        assert prefs.default_model == "kimi"
        assert prefs.theme == "dark"

    def test_user_prefs_persistence(self, temp_dir):
        lt1 = LongTermMemory(temp_dir)
        lt1.update_user_prefs(default_model="kimi")
        del lt1

        lt2 = LongTermMemory(temp_dir)
        assert lt2.get_user_prefs().default_model == "kimi"

    def test_add_recent_project(self, long_term, temp_dir):
        """添加的项目必须实际存在，get_recent_projects 才会返回"""
        project = temp_dir / "my-project"
        project.mkdir()
        long_term.add_recent_project(project)
        recent = long_term.get_recent_projects(limit=5)
        assert any(p.resolve() == project.resolve() for p in recent)

    def test_add_recent_project_non_existent(self, long_term):
        """不存在的项目不会出现在 recent"""
        long_term.add_recent_project(Path("/tmp/does-not-exist-12345"))
        recent = long_term.get_recent_projects(limit=5)
        assert len(recent) == 0

    def test_project_prefs(self, long_term):
        project = Path("/tmp/test-project")
        prefs = long_term.get_project_prefs(project)
        assert isinstance(prefs, ProjectPreference)

        long_term.update_project_prefs(project, name="TestProj", notes="a test")
        prefs2 = long_term.get_project_prefs(project)
        assert prefs2.name == "TestProj"


# ─────────────────────────────────────────────────────────────────
# LearningsMemory
# ─────────────────────────────────────────────────────────────────


class TestLearningsMemory:
    def test_add_learning(self, learnings):
        entry = learnings.add(
            title="test title",
            content="test content",
            category="note",
            tags=["tag1"],
        )
        assert isinstance(entry, LearningEntry)
        assert entry.title == "test title"
        assert entry.category == "note"
        # 搜索自己的内容
        results = learnings.search("test")
        assert any(e.title == "test title" for e in results)

    def test_search_by_title(self, learnings):
        learnings.add("rust vs go", "content about rust", "note")
        learnings.add("python tips", "content about python", "note")

        results = learnings.search("python")
        assert any(e.title == "python tips" for e in results)

    def test_search_no_match(self, learnings):
        learnings.add("title1", "content1", "note")
        results = learnings.search("not found xyz")
        assert len(results) == 0

    def test_get_by_category(self, learnings):
        learnings.add("entry1", "c1", "error")
        learnings.add("entry2", "c2", "solution")
        learnings.add("entry3", "c3", "error")

        results = learnings.get_by_category("error")
        assert len(results) == 2

    def test_get_recent(self, learnings):
        for i in range(5):
            learnings.add(f"title {i}", f"content {i}", "note")
            time.sleep(0.01)  # 确保 timestamp 不同

        recent = learnings.get_recent(limit=3)
        assert len(recent) == 3
        # 最新在前面
        assert recent[0].title == "title 4"

    def test_search_by_category(self, learnings):
        learnings.add("p1", "content", "error")
        learnings.add("p2", "content", "note")
        results = learnings.search("content", category="note")
        assert len(results) == 1
        assert results[0].category == "note"

    def test_delete(self, learnings):
        entry = learnings.add("to delete", "delete me", "note")
        assert learnings.delete(entry.id) is True
        assert learnings.delete("nonexistent") is False


# ─────────────────────────────────────────────────────────────────
# MemoryManager
# ─────────────────────────────────────────────────────────────────


class TestMemoryManager:
    def test_from_project(self, temp_dir):
        project = temp_dir / "myproject"
        project.mkdir()
        mgr = MemoryManager.from_project(project)
        assert mgr.config.storage_dir == project / ".omc" / "memory"

    def test_create_session(self, memory_mgr):
        session = memory_mgr.create_session(Path("/tmp"), "manager task")
        assert session is not None
        assert session.task == "manager task"

    def test_user_prefs_roundtrip(self, memory_mgr):
        memory_mgr.update_user_prefs(default_model="glm", theme="light")
        prefs = memory_mgr.get_user_prefs()
        assert prefs.default_model == "glm"
        assert prefs.theme == "light"

    def test_add_and_search_learning(self, memory_mgr):
        memory_mgr.add_learning(
            title="CI lesson",
            content="always run ruff before commit",
            category="lesson",
            tags=["ci", "git"],
        )
        # 搜索 tag
        results = memory_mgr.search_learnings("ci")
        assert any(e.title == "CI lesson" for e in results)

    def test_recall(self, memory_mgr):
        memory_mgr.add_learning("deploy tip", "use docker compose", "ops")
        memory_mgr.update_user_prefs(default_model="deepseek")

        results = memory_mgr.recall("docker")
        assert "learnings" in results
        assert any(e.title == "deploy tip" for e in results["learnings"])

    def test_recent_projects(self, memory_mgr, temp_dir):
        """只在存在的项目才返回"""
        p1 = temp_dir / "proj1"
        p2 = temp_dir / "proj2"
        p1.mkdir()
        p2.mkdir()

        memory_mgr.add_recent_project(p1)
        memory_mgr.add_recent_project(p2)
        recent = memory_mgr.get_recent_projects(limit=5)
        assert any(p.resolve() == p1.resolve() for p in recent)
        assert any(p.resolve() == p2.resolve() for p in recent)
