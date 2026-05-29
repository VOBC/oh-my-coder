"""
conftest.py - pytest 全局 fixtures

提供可复用的 fixture 工厂函数，减少测试代码重复。
"""

import asyncio
import json

import pytest
from fastapi.testclient import TestClient

from src.agents.persistence.store import AgentConfig, AgentState
from src.quest.models import Quest, QuestStep
from src.web.app import app

# ---------------------------------------------------------------------------
# Web 客户端
# ---------------------------------------------------------------------------


@pytest.fixture
def client():
    """创建测试客户端"""
    return TestClient(app)


# ---------------------------------------------------------------------------
# 临时目录
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_skill_dir(tmp_path):
    """临时 skills 目录（供 SkillManager 测试复用）"""
    d = tmp_path / "skills"
    d.mkdir()
    return d


@pytest.fixture
def tmp_config(tmp_path):
    """创建临时配置文件和目录。

    返回 ``(config_dir, config_file)`` 元组：
    - ``config_dir``: 临时配置目录 (Path)
    - ``config_file``: 配置文件路径 (Path)，预填默认 JSON 配置

    可通过 ``config_data`` 参数覆盖默认配置内容。

    用法::

        def test_something(tmp_config):
            config_dir, config_file = tmp_config
            # 或自定义内容:
            config_dir, config_file = tmp_config(config_data={"key": "value"})
    """

    def _make(config_data=None):
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        if config_data is None:
            config_data = {
                "model": "deepseek",
                "max_tokens": 8000,
                "temperature": 0.7,
            }

        config_file = config_dir / "config.json"
        config_file.write_text(json.dumps(config_data, ensure_ascii=False))

        return config_dir, config_file

    return _make


# ---------------------------------------------------------------------------
# Quest 工厂
# ---------------------------------------------------------------------------


@pytest.fixture
def make_quest():
    """Quest 对象工厂，返回真实 :class:`Quest` 实例。

    所有必填字段均有合理默认值，可通过 ``**kwargs`` 覆盖：

    用法::

        def test_with_default(make_quest):
            quest = make_quest()

        def test_with_override(make_quest):
            quest = make_quest(status=QuestStatus.EXECUTING, priority=QuestPriority.HIGH)
    """

    def _make(**kwargs):
        defaults = {
            "id": "quest-001",
            "title": "Test Quest",
            "description": "A test quest",
            "project_path": "/tmp/test",
        }
        defaults.update(kwargs)
        return Quest(**defaults)

    return _make


@pytest.fixture
def make_quest_step():
    """QuestStep 对象工厂，返回真实 :class:`QuestStep` 实例。

    用法::

        def test_step(make_quest_step):
            step = make_quest_step()
            step = make_quest_step(status=QuestStatus.COMPLETED, result="done")
    """

    def _make(**kwargs):
        defaults = {
            "step_id": "S1",
            "title": "Step 1",
            "description": "Do something",
            "agent": "executor",
        }
        defaults.update(kwargs)
        return QuestStep(**defaults)

    return _make


# ---------------------------------------------------------------------------
# Agent 工厂
# ---------------------------------------------------------------------------


@pytest.fixture
def make_agent():
    """AgentConfig 对象工厂，返回真实 :class:`AgentConfig` 实例。

    用法::

        def test_agent(make_agent):
            config = make_agent()
            config = make_agent(name="planner", model="kimi", tools=["read", "write"])
    """

    def _make(**kwargs):
        defaults = {
            "name": "test-agent",
        }
        defaults.update(kwargs)
        return AgentConfig(**defaults)

    return _make


@pytest.fixture
def make_agent_state():
    """AgentState 对象工厂，返回真实 :class:`AgentState` 实例。

    用法::

        def test_state(make_agent_state):
            state = make_agent_state(agent_name="explore", total_tokens=5000)
    """

    def _make(**kwargs):
        defaults = {
            "agent_name": "test-agent",
        }
        defaults.update(kwargs)
        return AgentState(**defaults)

    return _make


# ---------------------------------------------------------------------------
# 模型响应 Mock
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_model_response():
    """模拟模型响应工厂，返回类似模型 API 响应的字典。

    用法::

        def test_call(mock_model_response):
            resp = mock_model_response(content="Hello", cost=0.002)
            assert resp["content"] == "Hello"
    """

    def _mock(content="OK", cost=0.001, model="mock"):
        return {
            "content": content,
            "usage": {"cost": cost},
            "model": model,
        }

    return _mock


# ---------------------------------------------------------------------------
# Event Loop 修复（asyncio.run 导致 Python 3.9 get_event_loop 失败）
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _restore_event_loop():
    """每个测试后重置 event loop，避免 asyncio.run() 污染后续测试。"""
    yield
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
