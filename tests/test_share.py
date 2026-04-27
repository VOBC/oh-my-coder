"""
Tests for share functionality (P2-4)
- src/commands/share.py (CLI 命令)
- src/web/share_api.py (API 端点)
"""

import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# ========================================
# Fixtures
# ========================================


@pytest.fixture
def history_dir(tmp_path):
    """创建临时历史目录并写入测试数据"""
    h_dir = tmp_path / "history"
    h_dir.mkdir()

    # 写入测试历史
    history_data = {
        "history_id": "test_001",
        "task_description": "实现用户认证系统",
        "workflow_name": "build",
        "steps": [
            {
                "step_id": "explore_abc123",
                "agent_name": "Explorer",
                "description": "探索项目结构",
                "status": "completed",
                "input_context": {"task": "实现用户认证系统"},
                "output": {"files": ["src/auth.py", "src/models.py"]},
                "tokens_used": 500,
                "cost": 0.001,
                "duration_seconds": 3.2,
            },
            {
                "step_id": "executor_def456",
                "agent_name": "Executor",
                "description": "实现认证逻辑",
                "status": "completed",
                "input_context": {"task": "实现用户认证系统"},
                "output": {"files_created": ["src/auth.py"]},
                "tokens_used": 2000,
                "cost": 0.004,
                "duration_seconds": 8.5,
            },
        ],
        "total_tokens": 2500,
        "total_cost": 0.005,
        "total_duration": 11.7,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "tags": ["auth", "backend"],
    }

    with open(h_dir / "history_test_001.json", "w", encoding="utf-8") as f:
        json.dump(history_data, f, ensure_ascii=False)

    return h_dir


@pytest.fixture
def share_dir(tmp_path):
    """创建临时分享目录"""
    s_dir = tmp_path / "shares"
    s_dir.mkdir()
    return s_dir


@pytest.fixture
def sample_share_data():
    """示例分享数据"""
    return {
        "share_id": "abcd1234",
        "version": 1,
        "created_at": datetime.now().isoformat(),
        "expires_at": None,
        "tags": ["test", "demo"],
        "session": {
            "history": {
                "history_id": "test_001",
                "task_description": "实现用户认证系统",
                "workflow_name": "build",
                "steps": [
                    {
                        "step_id": "explore_abc123",
                        "agent_name": "Explorer",
                        "description": "探索项目结构",
                        "status": "completed",
                    }
                ],
                "total_tokens": 500,
                "total_cost": 0.001,
            }
        },
    }


# ========================================
# CLI Tests (src/commands/share.py)
# ========================================


class TestShareCore:
    """测试分享核心逻辑"""

    def test_export_session_creates_file(self, history_dir, share_dir, monkeypatch):
        """导出会话应创建分享文件"""
        from src.commands.share import export_session

        monkeypatch.setattr("src.commands.share.SHARE_DIR", share_dir)

        result = export_session(
            task_id="test_001",
            history_dir=history_dir,
        )

        assert result != {}
        assert "share_id" in result
        assert len(result["share_id"]) == 8
        assert result["session"]["history"]["history_id"] == "test_001"

        # 验证文件存在
        share_file = share_dir / f"share_{result['share_id']}.json"
        assert share_file.exists()

    def test_export_session_latest(self, history_dir, share_dir, monkeypatch):
        """不指定 task_id 时导出最近的"""
        from src.commands.share import export_session

        monkeypatch.setattr("src.commands.share.SHARE_DIR", share_dir)

        result = export_session(history_dir=history_dir)
        assert result != {}
        assert "share_id" in result

    def test_export_session_not_found(self, history_dir, share_dir, monkeypatch):
        """不存在的 task_id 应返回空"""
        from src.commands.share import export_session

        monkeypatch.setattr("src.commands.share.SHARE_DIR", share_dir)

        result = export_session(task_id="nonexistent", history_dir=history_dir)
        assert result == {}

    def test_export_with_config_sanitization(
        self, history_dir, share_dir, tmp_path, monkeypatch
    ):
        """导出时配置应脱敏"""
        from src.commands.share import _sanitize_config

        monkeypatch.setattr("src.commands.share.SHARE_DIR", share_dir)

        # 测试脱敏函数
        config = {
            "deepseek_api_key": "sk-1234567890abcdef",
            "model": "deepseek",
            "nested": {
                "secret_token": "tok_xyz",
                "value": 42,
            },
        }
        safe = _sanitize_config(config)
        assert safe["deepseek_api_key"] == "sk-1****"
        assert safe["model"] == "deepseek"
        assert safe["nested"]["secret_token"] == "tok_****"
        assert safe["nested"]["value"] == 42

    def test_export_with_expiration(self, history_dir, share_dir, monkeypatch):
        """导出时设置过期时间"""
        from src.commands.share import export_session

        monkeypatch.setattr("src.commands.share.SHARE_DIR", share_dir)

        result = export_session(
            task_id="test_001",
            history_dir=history_dir,
            expires_hours=24,
        )

        assert result != {}
        assert result["expires_at"] is not None

    def test_import_session(
        self, history_dir, share_dir, sample_share_data, monkeypatch
    ):
        """导入分享应创建新的历史记录"""
        from src.commands.share import import_session

        monkeypatch.setattr("src.commands.share.SHARE_DIR", share_dir)

        # 先写入分享文件
        share_id = sample_share_data["share_id"]
        share_file = share_dir / f"share_{share_id}.json"
        with open(share_file, "w", encoding="utf-8") as f:
            json.dump(sample_share_data, f)

        import_dir = share_dir / "imported"
        import_dir.mkdir()

        result = import_session(share_id, target_dir=import_dir)
        assert result != {}
        assert "imported_from" in result
        assert result["imported_from"] == share_id
        assert "_imported_" in result["history_id"]

    def test_import_expired_share(self, share_dir, monkeypatch):
        """导入过期分享应失败"""
        from src.commands.share import import_session

        monkeypatch.setattr("src.commands.share.SHARE_DIR", share_dir)

        # 创建过期分享
        expired_data = {
            "share_id": "expired1",
            "version": 1,
            "created_at": (datetime.now() - timedelta(hours=2)).isoformat(),
            "expires_at": (datetime.now() - timedelta(hours=1)).isoformat(),
            "tags": [],
            "session": {"history": {"history_id": "exp_001"}},
        }
        share_file = share_dir / "share_expired1.json"
        with open(share_file, "w", encoding="utf-8") as f:
            json.dump(expired_data, f)

        result = import_session("expired1")
        assert result == {}

    def test_list_shares(self, share_dir, sample_share_data, monkeypatch):
        """列出分享"""
        from src.commands.share import list_shares

        monkeypatch.setattr("src.commands.share.SHARE_DIR", share_dir)

        # 写入两个分享
        for i in range(2):
            data = sample_share_data.copy()
            data["share_id"] = f"share{i:04d}"
            with open(share_dir / f"share_share{i:04d}.json", "w") as f:
                json.dump(data, f)

        shares = list_shares()
        assert len(shares) >= 2

    def test_delete_share(self, share_dir, sample_share_data, monkeypatch):
        """删除分享"""
        from src.commands.share import delete_share

        monkeypatch.setattr("src.commands.share.SHARE_DIR", share_dir)

        share_id = sample_share_data["share_id"]
        share_file = share_dir / f"share_{share_id}.json"
        with open(share_file, "w", encoding="utf-8") as f:
            json.dump(sample_share_data, f)

        assert share_file.exists()
        result = delete_share(share_id)
        assert result is True
        assert not share_file.exists()

    def test_delete_nonexistent_share(self, share_dir, monkeypatch):
        """删除不存在的分享应失败"""
        from src.commands.share import delete_share

        monkeypatch.setattr("src.commands.share.SHARE_DIR", share_dir)

        result = delete_share("nonexistent")
        assert result is False

    def test_get_share(self, share_dir, sample_share_data, monkeypatch):
        """获取分享详情"""
        from src.commands.share import get_share

        monkeypatch.setattr("src.commands.share.SHARE_DIR", share_dir)

        share_id = sample_share_data["share_id"]
        share_file = share_dir / f"share_{share_id}.json"
        with open(share_file, "w", encoding="utf-8") as f:
            json.dump(sample_share_data, f)

        data = get_share(share_id)
        assert data is not None
        assert data["share_id"] == share_id

    def test_get_share_not_found(self, share_dir, monkeypatch):
        """获取不存在的分享应返回 None"""
        from src.commands.share import get_share

        monkeypatch.setattr("src.commands.share.SHARE_DIR", share_dir)

        data = get_share("nonexistent")
        assert data is None


# ========================================
# API Tests (src/web/share_api.py)
# ========================================


class TestShareAPI:
    """测试分享 API 端点"""

    @pytest.fixture
    def client(self, history_dir, share_dir, monkeypatch):
        """创建测试客户端"""
        import sys

        project_root = Path(__file__).parent.parent.parent
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))

        from src.web.app import app

        # 替换目录
        monkeypatch.setattr("src.web.share_api.SHARE_DIR", share_dir)
        monkeypatch.setattr("src.web.share_api.HISTORY_DIR", history_dir)

        return TestClient(app)

    def test_create_share_api(self, client, history_dir):
        """POST /api/share 创建分享"""
        resp = client.post(
            "/api/share",
            json={
                "task_id": "test_001",
                "include_config": False,
                "tags": ["api-test"],
                "expires_hours": 0,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "share_id" in data
        assert len(data["share_id"]) == 8
        assert data["tags"] == ["api-test"]

    def test_create_share_not_found(self, client):
        """POST /api/share 不存在的任务"""
        resp = client.post(
            "/api/share",
            json={"task_id": "nonexistent"},
        )
        assert resp.status_code == 404

    def test_list_shares_api(self, client, share_dir, sample_share_data):
        """GET /api/share 列出分享"""
        # 先创建一个
        share_id = sample_share_data["share_id"]
        with open(share_dir / f"share_{share_id}.json", "w") as f:
            json.dump(sample_share_data, f)

        resp = client.get("/api/share")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert any(s["share_id"] == share_id for s in data)

    def test_get_share_api(self, client, share_dir, sample_share_data):
        """GET /api/share/{id} 获取详情"""
        share_id = sample_share_data["share_id"]
        with open(share_dir / f"share_{share_id}.json", "w") as f:
            json.dump(sample_share_data, f)

        resp = client.get(f"/api/share/{share_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["share_id"] == share_id
        assert "session" in data

    def test_get_share_not_found_api(self, client):
        """GET /api/share/{id} 不存在"""
        resp = client.get("/api/share/nonexistent")
        assert resp.status_code == 404

    def test_import_share_api(self, client, share_dir, sample_share_data):
        """POST /api/share/{id}/import 导入"""
        share_id = sample_share_data["share_id"]
        with open(share_dir / f"share_{share_id}.json", "w") as f:
            json.dump(sample_share_data, f)

        resp = client.post(f"/api/share/{share_id}/import", json={})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "imported"
        assert "_imported_" in data["history_id"]

    def test_delete_share_api(self, client, share_dir, sample_share_data):
        """DELETE /api/share/{id} 删除"""
        share_id = sample_share_data["share_id"]
        with open(share_dir / f"share_{share_id}.json", "w") as f:
            json.dump(sample_share_data, f)

        resp = client.delete(f"/api/share/{share_id}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "deleted"

        # 确认已删除
        resp = client.get(f"/api/share/{share_id}")
        assert resp.status_code == 404

    def test_create_share_with_expiration(self, client):
        """POST /api/share 带过期时间"""
        resp = client.post(
            "/api/share",
            json={
                "task_id": "test_001",
                "expires_hours": 48,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["expires_at"] is not None

    def test_import_expired_share_api(self, client, share_dir):
        """POST /api/share/{id}/import 过期分享"""
        expired_data = {
            "share_id": "exp_api1",
            "version": 1,
            "created_at": (datetime.now() - timedelta(hours=2)).isoformat(),
            "expires_at": (datetime.now() - timedelta(hours=1)).isoformat(),
            "tags": [],
            "session": {"history": {"history_id": "exp_001"}},
        }
        with open(share_dir / "share_exp_api1.json", "w") as f:
            json.dump(expired_data, f)

        resp = client.post("/api/share/exp_api1/import", json={})
        assert resp.status_code == 410

    def test_get_expired_share_api(self, client, share_dir):
        """GET /api/share/{id} 过期分享"""
        expired_data = {
            "share_id": "exp_get1",
            "version": 1,
            "created_at": (datetime.now() - timedelta(hours=2)).isoformat(),
            "expires_at": (datetime.now() - timedelta(hours=1)).isoformat(),
            "tags": [],
            "session": {"history": {}},
        }
        with open(share_dir / "share_exp_get1.json", "w") as f:
            json.dump(expired_data, f)

        resp = client.get("/api/share/exp_get1")
        assert resp.status_code == 410
