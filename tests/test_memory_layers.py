"""
补充测试：Memory 三层未覆盖的方法

覆盖 short_term / long_term / learnings 中之前测试未覆盖的方法。
"""

import json
import tempfile
import time
from pathlib import Path

import pytest

from src.memory.learnings import LearningsMemory, LearningEntry
from src.memory.long_term import LongTermMemory, ProjectPreference, UserPreference
from src.memory.short_term import Message, SessionContext, ShortTermMemory


# =============================================================================
# ShortTermMemory 补充测试
# =============================================================================


class TestShortTermMemoryExtra:
    """ShortTermMemory 未覆盖方法测试"""

    def test_set_current_session(self, tmp_path):
        """set_current_session 设置当前会话"""
        stm = ShortTermMemory(tmp_path)
        session = stm.create_session(task="test task")
        assert stm.get_current_session().session_id == session.session_id

        # 创建新会话并切换
        session2 = stm.create_session(task="task 2")
        assert stm.get_current_session().session_id == session2.session_id

    def test_compress_if_needed_under_limit(self, tmp_path):
        """消息数未超过限制时不压缩"""
        stm = ShortTermMemory(tmp_path, max_messages=100)
        session = stm.create_session()
        for i in range(5):
            session.add_message("user", f"msg {i}")

        result = stm.compress_if_needed(session)
        assert len(result) == 5  # 未压缩

    def test_compress_if_needed_over_limit(self, tmp_path):
        """消息数超过限制时压缩"""
        stm = ShortTermMemory(tmp_path, max_messages=10)
        session = stm.create_session()
        # 添加超过限制的消息
        for i in range(20):
            session.add_message("user", f"msg {i}")

        result = stm.compress_if_needed(session)
        # 压缩后应保留 <= max_messages//2 + system msgs
        assert len(result) <= 10  # 至少压缩了一半

    def test_list_sessions(self, tmp_path):
        """list_sessions 列出所有会话"""
        stm = ShortTermMemory(tmp_path)
        # 创建多个会话
        for i in range(3):
            session = stm.create_session(task=f"task {i}")
            session.add_message("user", f"msg in session {i}")
            stm.save_session(session)

        sessions = stm.list_sessions()
        assert len(sessions) == 3

    def test_list_sessions_sort_by_last_active(self, tmp_path):
        """list_sessions 按最后活跃时间倒序"""
        stm = ShortTermMemory(tmp_path)
        s1 = stm.create_session(task="oldest")
        stm.save_session(s1)
        time.sleep(0.01)

        s2 = stm.create_session(task="newest")
        stm.save_session(s2)

        sessions = stm.list_sessions()
        assert sessions[0].task == "newest"
        assert sessions[-1].task == "oldest"

    def test_clear_expired(self, tmp_path):
        """clear_expired 清理过期会话"""
        stm = ShortTermMemory(tmp_path)
        session = stm.create_session()
        stm.save_session(session)

        # 模拟过期：直接修改 last_active
        old_file = tmp_path / "short-term" / f"{session.session_id}.json"
        data = json.loads(old_file.read_text())
        data["last_active"] = time.time() - 100 * 3600  # 100小时前
        old_file.write_text(json.dumps(data))

        stm.clear_expired(max_age_hours=24)
        assert stm.load_session(session.session_id) is None

    def test_clear_expired_does_not_remove_recent(self, tmp_path):
        """clear_expired 不清理最近活跃的会话"""
        stm = ShortTermMemory(tmp_path)
        session = stm.create_session()
        stm.save_session(session)

        stm.clear_expired(max_age_hours=24)
        assert stm.load_session(session.session_id) is not None


class TestSessionContext:
    """SessionContext 数据类补充测试"""

    def test_get_recent_messages(self):
        session = SessionContext(session_id="test")
        for i in range(30):
            session.add_message("user", f"msg {i}")

        recent = session.get_recent_messages(limit=10)
        assert len(recent) == 10
        # 最近10条
        assert recent[-1].content == "msg 29"

    def test_get_recent_messages_no_limit(self):
        session = SessionContext(session_id="test")
        for i in range(5):
            session.add_message("user", f"msg {i}")

        recent = session.get_recent_messages()  # 默认 20
        assert len(recent) == 5

    def test_to_dict_from_dict_roundtrip(self):
        session = SessionContext(session_id="roundtrip", task="test")
        session.add_message("user", "hello")
        session.add_message("assistant", "world")

        data = session.to_dict()
        restored = SessionContext.from_dict(data)

        assert restored.session_id == "roundtrip"
        assert restored.task == "test"
        assert len(restored.messages) == 2
        assert restored.messages[0].content == "hello"
        assert restored.messages[1].content == "world"

    def test_from_dict_with_variables(self):
        data = {
            "session_id": "var-test",
            "project_path": "/tmp/test",
            "task": "task",
            "messages": [],
            "variables": {"key1": "val1", "key2": 42},
            "created_at": time.time(),
            "last_active": time.time(),
        }
        session = SessionContext.from_dict(data)
        assert session.variables["key1"] == "val1"
        assert session.variables["key2"] == 42


class TestMessage:
    """Message 数据类测试"""

    def test_message_with_metadata(self):
        msg = Message(role="user", content="hello", metadata={"source": "cli"})
        assert msg.metadata["source"] == "cli"
        assert msg.timestamp > 0

    def test_message_default_metadata(self):
        msg = Message(role="assistant", content="response")
        assert msg.metadata == {}


# =============================================================================
# LongTermMemory 补充测试
# =============================================================================


class TestLongTermMemoryExtra:
    """LongTermMemory 未覆盖方法测试"""

    def test_load_projects_lazy(self, tmp_path):
        """_load_projects 是惰性加载"""
        lt = LongTermMemory(tmp_path)
        # 在调用任何方法之前，projects 应该为空
        projects = lt._load_projects()
        assert projects == {}

    def test_user_prefs_default_values(self, tmp_path):
        """默认用户偏好有合理的值"""
        lt = LongTermMemory(tmp_path)
        prefs = lt.get_user_prefs()
        assert prefs.default_model == "deepseek"
        assert prefs.default_workflow == "build"
        assert prefs.theme == "auto"
        assert prefs.editor == "code"
        assert prefs.shell == "bash"

    def test_update_user_prefs_multiple_fields(self, tmp_path):
        """一次更新多个偏好字段"""
        lt = LongTermMemory(tmp_path)
        lt.update_user_prefs(
            default_model="kimi",
            theme="dark",
            editor="vim",
        )
        prefs = lt.get_user_prefs()
        assert prefs.default_model == "kimi"
        assert prefs.theme == "dark"
        assert prefs.editor == "vim"

    def test_get_recent_projects_nonexistent_paths(self, tmp_path):
        """不存在的项目路径不会返回"""
        lt = LongTermMemory(tmp_path)
        lt.add_recent_project(Path("/tmp/does-not-exist-xyz"))
        recent = lt.get_recent_projects(limit=5)
        assert len(recent) == 0

    def test_get_recent_projects_limit(self, tmp_path):
        """get_recent_projects 限制返回数量"""
        lt = LongTermMemory(tmp_path)
        # 添加 10 个项目
        for i in range(10):
            p = tmp_path / f"proj{i}"
            p.mkdir()
            lt.add_recent_project(p)

        recent = lt.get_recent_projects(limit=3)
        assert len(recent) == 3

    def test_add_recent_project_max_10(self, tmp_path):
        """recent_projects 最多保留 10 个"""
        lt = LongTermMemory(tmp_path)
        prefs = lt.get_user_prefs()

        for i in range(15):
            p = tmp_path / f"proj{i}"
            p.mkdir()
            lt.add_recent_project(p)

        prefs2 = lt.get_user_prefs()
        assert len(prefs2.recent_projects) <= 10

    def test_add_recent_project_removes_duplicate(self, tmp_path):
        """add_recent_project 移除已存在的条目"""
        lt = LongTermMemory(tmp_path)
        p = tmp_path / "dup"
        p.mkdir()

        lt.add_recent_project(p)
        lt.add_recent_project(p)
        prefs = lt.get_user_prefs()

        # 只应有一个
        assert prefs.recent_projects.count(str(p.resolve())) == 1
        # 新添加的应该在最前面
        assert prefs.recent_projects[0] == str(p.resolve())


class TestUserPreference:
    """UserPreference 数据类测试"""

    def test_to_dict_from_dict(self):
        prefs = UserPreference(
            user_id="test-user",
            default_model="kimi",
            theme="dark",
            editor="vim",
        )
        data = prefs.to_dict()
        restored = UserPreference.from_dict(data)
        assert restored.user_id == "test-user"
        assert restored.default_model == "kimi"
        assert restored.theme == "dark"


class TestProjectPreference:
    """ProjectPreference 数据类测试"""

    def test_to_dict_from_dict(self):
        prefs = ProjectPreference(
            project_path="/tmp/test",
            name="TestProject",
            language="python",
            framework="fastapi",
        )
        data = prefs.to_dict()
        restored = ProjectPreference.from_dict(data)
        assert restored.name == "TestProject"
        assert restored.language == "python"
        assert restored.framework == "fastapi"

    def test_default_values(self):
        prefs = ProjectPreference(project_path="/tmp/test")
        assert prefs.default_model == "deepseek"
        assert prefs.default_workflow == "build"
        assert prefs.custom_commands == {}


# =============================================================================
# LearningsMemory 补充测试
# =============================================================================


class TestLearningsMemoryExtra:
    """LearningsMemory 未覆盖方法测试"""

    def test_add_entry(self, tmp_path):
        """add 方法添加学习条目"""
        lm = LearningsMemory(tmp_path)
        entry = lm.add(
            title="Test Entry",
            content="This is test content",
            category="note",
            tags=["test", "demo"],
            context="during testing",
        )
        assert entry.title == "Test Entry"
        assert entry.category == "note"
        assert "test" in entry.tags
        assert entry.context == "during testing"
        assert entry.id != ""

    def test_add_entry_id_generation(self, tmp_path):
        """add 生成唯一 ID"""
        lm = LearningsMemory(tmp_path)
        e1 = lm.add("First Entry", "content 1")
        e2 = lm.add("Second Entry", "content 2")
        assert e1.id != e2.id

    def test_add_default_category(self, tmp_path):
        """add 默认 category 为 note"""
        lm = LearningsMemory(tmp_path)
        entry = lm.add("Title", "Content")
        assert entry.category == "note"

    def test_search_content(self, tmp_path):
        """搜索内容匹配"""
        lm = LearningsMemory(tmp_path)
        lm.add("Python Tip", "Use list comprehension instead of loops", "note")
        results = lm.search("list comprehension")
        assert len(results) >= 1

    def test_search_tags(self, tmp_path):
        """搜索标签匹配"""
        lm = LearningsMemory(tmp_path)
        lm.add("Docker Lesson", "Content here", tags=["docker", "devops"])
        results = lm.search("docker")
        assert len(results) >= 1

    def test_search_empty_query(self, tmp_path):
        """空查询匹配所有（因为空字符串 in 任何字符串都返回 True）"""
        lm = LearningsMemory(tmp_path)
        lm.add("A", "content a")
        lm.add("B", "content b")
        results = lm.search("")
        # 空字符串匹配一切，这是当前实现的行为
        assert len(results) == 2

    def test_delete_entry(self, tmp_path):
        """delete 方法删除条目"""
        lm = LearningsMemory(tmp_path)
        entry = lm.add("To Delete", "Will be deleted")
        assert lm.delete(entry.id) is True

        # 再次删除应返回 False
        assert lm.delete(entry.id) is False

    def test_delete_nonexistent(self, tmp_path):
        """删除不存在的 ID"""
        lm = LearningsMemory(tmp_path)
        assert lm.delete("no-such-id") is False

    def test_categories_constant(self, tmp_path):
        """CATEGORIES 定义正确"""
        from src.memory.learnings import LearningsMemory

        assert "error" in LearningsMemory.CATEGORIES
        assert "solution" in LearningsMemory.CATEGORIES
        assert "best-practice" in LearningsMemory.CATEGORIES
        assert "note" in LearningsMemory.CATEGORIES


class TestLearningEntry:
    """LearningEntry 数据类测试"""

    def test_to_dict_from_dict(self):
        entry = LearningEntry(
            id="test-id",
            category="note",
            title="Test Title",
            content="Test content",
            tags=["tag1"],
            context="test context",
        )
        data = entry.to_dict()
        restored = LearningEntry.from_dict(data)
        assert restored.id == "test-id"
        assert restored.title == "Test Title"
        assert restored.category == "note"
        assert restored.tags == ["tag1"]
