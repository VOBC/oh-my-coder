"""Tests for src/config/workflow_loader.py"""

from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

from src.config.workflow_loader import (
    StepConfig,
    WorkflowConfig,
    WorkflowLoader,
)
from src.core.orchestrator import WORKFLOW_TEMPLATES

# ---------------------------------------------------------------------------
# StepConfig & WorkflowConfig
# ---------------------------------------------------------------------------

class TestStepConfig:
    def test_defaults(self):
        s = StepConfig(id="s1", agent="explore", description="探索")
        assert s.dependencies == []
        assert s.timeout == 300.0
        assert s.retry == 0
        assert s.metadata == {}

    def test_to_workflow_step(self):
        s = StepConfig(
            id="s1", agent="explore", description="探索代码库",
            dependencies=["s0"], retry=2, timeout=60.0, metadata={"key": "val"},
        )
        ws = s.to_workflow_step()
        assert ws.agent_name == "explore"
        assert ws.description == "探索代码库"
        assert ws.dependencies == ["s0"]
        assert ws.retry_count == 2
        assert ws.timeout == 60.0
        assert ws.metadata == {"key": "val", "step_id": "s1"}


class TestWorkflowConfig:
    def test_defaults(self):
        c = WorkflowConfig(name="test")
        assert c.description == ""
        assert c.steps == []
        assert c.metadata == {}
        assert c.source == "builtin"

    def test_to_workflow_steps(self):
        c = WorkflowConfig(
            name="wf", steps=[
                StepConfig(id="s1", agent="a1", description="d1"),
                StepConfig(id="s2", agent="a2", description="d2", dependencies=["s1"]),
            ],
        )
        steps = c.to_workflow_steps()
        assert len(steps) == 2
        assert steps[0].agent_name == "a1"
        assert steps[1].dependencies == ["s1"]


# ---------------------------------------------------------------------------
# WorkflowLoader
# ---------------------------------------------------------------------------

class TestWorkflowLoader:
    def setup_method(self):
        self.loader = WorkflowLoader(default_workflows_dir=Path("/fake/default"))

    # -- parse_yaml_string --

    def test_parse_yaml_string_basic(self):
        yaml_str = """
name: myflow
description: A flow
steps:
  - id: s1
    agent: explore
    description: 探索
    dependencies: [s0]
    timeout: 60
    retry: 1
    metadata:
      key: val
"""
        cfg = self.loader.parse_yaml_string(yaml_str, name="myflow")
        assert cfg is not None
        assert cfg.name == "myflow"
        assert cfg.description == "A flow"
        assert cfg.source == "user"
        assert len(cfg.steps) == 1
        s = cfg.steps[0]
        assert s.id == "s1"
        assert s.agent == "explore"
        assert s.dependencies == ["s0"]
        assert s.timeout == 60.0
        assert s.retry == 1
        assert s.metadata == {"key": "val"}

    def test_parse_yaml_string_defaults(self):
        yaml_str = """
steps:
  - agent: explore
"""
        cfg = self.loader.parse_yaml_string(yaml_str, name="flow1")
        assert cfg is not None
        s = cfg.steps[0]
        assert s.id == "explore"  # fallback: s.get("id", s.get("agent", "step"))
        assert s.description == ""
        assert s.dependencies == []
        assert s.timeout == 300.0
        assert s.retry == 0
        assert s.metadata == {}

    def test_parse_yaml_string_empty(self):
        cfg = self.loader.parse_yaml_string("", name="empty")
        assert cfg is not None
        assert cfg.steps == []
        assert cfg.name == "empty"

    def test_parse_yaml_string_invalid(self):
        with patch("src.config.workflow_loader.yaml.safe_load", side_effect=Exception("boom")):
            cfg = self.loader.parse_yaml_string("anything", name="bad")
            assert cfg is None

    # -- load_workflow fallback --

    def test_load_workflow_fallback(self):
        with patch.object(self.loader, "get_workflow_config", return_value=None):
            steps = self.loader.load_workflow("build")
        assert isinstance(steps, list)
        assert len(steps) > 0

    def test_load_workflow_fallback_missing_name(self):
        with patch.object(self.loader, "get_workflow_config", return_value=None):
            steps = self.loader.load_workflow("nonexistent")
        assert steps == []

    def test_load_workflow_from_config(self):
        cfg = WorkflowConfig(name="test", steps=[
            StepConfig(id="s1", agent="a1", description="d1"),
        ])
        with patch.object(self.loader, "get_workflow_config", return_value=cfg):
            steps = self.loader.load_workflow("test")
        assert len(steps) == 1

    # -- get_workflow_config --

    def _path_exists_side_effect(self, paths_that_exist):
        """Return a side_effect function for Path.exists that checks against a set."""
        def side_effect(self_path):
            return str(self_path) in paths_that_exist
        return side_effect

    def test_get_workflow_config_no_file(self):
        with patch.object(Path, "exists", return_value=False):
            result = self.loader.get_workflow_config("myflow")
            assert result is None

    def test_get_workflow_config_from_default_file(self):
        yaml_content = "name: build\nsteps:\n  - id: s1\n    agent: explore\n    description: 探索代码库"
        default_path_str = str(self.loader._default_dir / "build.yaml")
        def exists_se(p):
            return str(p) == default_path_str

        with patch.object(Path, "exists", exists_se), \
             patch("builtins.open", mock_open(read_data=yaml_content)), \
             patch.object(Path, "stat", return_value=MagicMock(st_mtime=100.0)):
            cfg = self.loader.get_workflow_config("build")
            assert cfg is not None
            assert cfg.name == "build"
            assert cfg.source == "builtin"
            assert len(cfg.steps) == 1

    def test_get_workflow_config_user_overrides_default(self):
        yaml_content = "name: build\nsteps:\n  - id: u1\n    agent: myagent\n    description: custom"
        user_path_str = str(self.loader._user_dir / "build.yaml")
        def exists_se(p):
            return str(p) == user_path_str

        with patch.object(Path, "exists", exists_se), \
             patch("builtins.open", mock_open(read_data=yaml_content)), \
             patch.object(Path, "stat", return_value=MagicMock(st_mtime=100.0)):
            cfg = self.loader.get_workflow_config("build")
            assert cfg is not None
            assert cfg.source == "user"

    def test_get_workflow_config_cache_ttl(self):
        cfg = WorkflowConfig(name="cached", steps=[
            StepConfig(id="s1", agent="a1", description="d1"),
        ])
        now = time.time()
        self.loader._cache["cached"] = (now, 100.0, cfg)

        user_path_str = str(self.loader._user_dir / "cached.yaml")
        def exists_se(p):
            return str(p) == user_path_str

        with patch.object(Path, "exists", exists_se), \
             patch.object(Path, "stat", return_value=MagicMock(st_mtime=100.0)), \
             patch("time.time", return_value=now + 1.0):
            result = self.loader.get_workflow_config("cached")
            assert result is cfg

    def test_get_workflow_config_cache_expired(self):
        old_cfg = WorkflowConfig(name="old", steps=[])
        now = time.time()
        self.loader._cache["expired"] = (now - 10.0, 100.0, old_cfg)

        yaml_content = "name: expired\nsteps:\n  - id: s1\n    agent: a1\n    description: new"
        user_path_str = str(self.loader._user_dir / "expired.yaml")
        def exists_se(p):
            return str(p) == user_path_str

        with patch.object(Path, "exists", exists_se), \
             patch("builtins.open", mock_open(read_data=yaml_content)), \
             patch.object(Path, "stat", return_value=MagicMock(st_mtime=200.0)), \
             patch("time.time", return_value=now):
            result = self.loader.get_workflow_config("expired")
            assert result is not old_cfg
            assert result.name == "expired"

    def test_get_workflow_config_yaml_error(self):
        # Test exception during file read: no cache, force fresh read that fails
        default_path_str = str(self.loader._default_dir / "broken.yaml")
        def exists_se(p):
            return str(p) == default_path_str

        with patch.object(Path, "exists", exists_se), \
             patch.object(Path, "stat", return_value=MagicMock(st_mtime=100.0)), \
             patch("builtins.open", side_effect=OSError("read error")):
            result = self.loader.get_workflow_config("broken")
            assert result is None

    def test_get_workflow_config_yaml_parse_error_clears_cache(self):
        # Cached entry exists, but expired; new read raises → cache cleared
        old_cfg = WorkflowConfig(name="broken", steps=[])
        now = time.time()
        self.loader._cache["broken"] = (now - 10.0, 100.0, old_cfg)  # expired

        default_path_str = str(self.loader._default_dir / "broken.yaml")
        def exists_se(p):
            return str(p) == default_path_str

        with patch.object(Path, "exists", exists_se), \
             patch.object(Path, "stat", return_value=MagicMock(st_mtime=200.0)), \
             patch("builtins.open", side_effect=OSError("read error")), \
             patch("time.time", return_value=now):
            result = self.loader.get_workflow_config("broken")
            assert result is None
            assert "broken" not in self.loader._cache

    # -- list_workflows / list_builtins / is_builtin --

    def test_list_workflows(self):
        default_files = [MagicMock(stem="build"), MagicMock(stem="review")]
        user_files = [MagicMock(stem="custom")]
        def exists_se(p):
            return p == self.loader._default_dir or p == self.loader._user_dir
        def glob_se(self_path, pattern):
            if str(self_path) == str(self.loader._default_dir):
                return default_files
            if str(self_path) == str(self.loader._user_dir):
                return user_files
            return []

        with patch.object(Path, "exists", exists_se), \
             patch.object(Path, "glob", glob_se):
            names = self.loader.list_workflows()
        assert "build" in names
        assert "custom" in names
        assert "debug" in names

    def test_list_workflows_dirs_missing(self):
        with patch.object(Path, "exists", return_value=False):
            names = self.loader.list_workflows()
        assert set(names) == set(WORKFLOW_TEMPLATES.keys())

    def test_list_builtins(self):
        default_files = [MagicMock(stem="build")]
        def exists_se(p):
            return p == self.loader._default_dir
        def glob_se(self_path, pattern):
            if str(self_path) == str(self.loader._default_dir):
                return default_files
            return []

        with patch.object(Path, "exists", exists_se), \
             patch.object(Path, "glob", glob_se):
            names = self.loader.list_builtins()
        assert "build" in names
        assert "debug" in names

    def test_is_builtin_true(self):
        with patch.object(self.loader, "list_builtins", return_value=["build", "review"]):
            assert self.loader.is_builtin("build") is True

    def test_is_builtin_false(self):
        with patch.object(self.loader, "list_builtins", return_value=["build"]):
            assert self.loader.is_builtin("custom") is False

    # -- save_workflow --

    def test_save_workflow(self):
        cfg = WorkflowConfig(
            name="test_save", description="desc",
            steps=[StepConfig(id="s1", agent="a1", description="d1")],
        )
        with patch.object(self.loader, "_ensure_user_dir"), \
             patch("builtins.open", mock_open()), \
             patch("yaml.dump"):
            self.loader.save_workflow("test_save", cfg)
        assert "test_save" not in self.loader._cache

    # -- delete_workflow --

    def test_delete_workflow_user(self):
        user_path_str = str(self.loader._user_dir / "myflow.yaml")
        str(self.loader._default_dir / "myflow.yaml")
        def exists_se(p):
            s = str(p)
            return s == user_path_str

        with patch.object(Path, "exists", exists_se), \
             patch.object(Path, "unlink"):
            assert self.loader.delete_workflow("myflow") is True
        assert "myflow" not in self.loader._cache

    def test_delete_workflow_builtin_denied(self):
        default_path_str = str(self.loader._default_dir / "build.yaml")
        def exists_se(p):
            return str(p) == default_path_str

        with patch.object(Path, "exists", exists_se):
            assert self.loader.delete_workflow("build") is False

    def test_delete_workflow_nonexistent(self):
        with patch.object(Path, "exists", return_value=False):
            assert self.loader.delete_workflow("noflow") is False

    # -- _ensure_user_dir --

    def test_ensure_user_dir(self):
        with patch.object(Path, "mkdir") as m_mkdir:
            self.loader._ensure_user_dir()
            m_mkdir.assert_called_once_with(parents=True, exist_ok=True)
