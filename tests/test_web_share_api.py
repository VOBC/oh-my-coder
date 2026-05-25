"""
Tests for src/web/share_api.py

Tests Pydantic models, helper functions, and FastAPI routes for share API.
"""
import json
from unittest.mock import MagicMock, mock_open, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.web.share_api import (
    ShareCreateRequest,
    ShareDetailResponse,
    ShareImportRequest,
    ShareResponse,
    _sanitize_config,
    _share_path,
    router,
)


# ========================================
# Fixtures
# ========================================
@pytest.fixture
def app():
    test_app = FastAPI()
    test_app.include_router(router)
    return test_app


@pytest.fixture
def client(app):
    return TestClient(app)


# ========================================
# Helper Function Tests
# ========================================
class TestSanitizeConfig:
    def test_no_secrets(self):
        config = {"name": "test", "port": 8080}
        assert _sanitize_config(config) == config

    def test_sanitize_api_key(self):
        config = {"api_key": "sk-12345678"}
        result = _sanitize_config(config)
        assert result["api_key"] == "sk-1****"

    def test_sanitize_token(self):
        config = {"access_token": "ghp_abcdef123456"}
        result = _sanitize_config(config)
        assert result["access_token"] == "ghp_****"

    def test_sanitize_secret(self):
        config = {"client_secret": "mysecretvalue"}
        result = _sanitize_config(config)
        assert result["client_secret"] == "myse****"

    def test_sanitize_password(self):
        config = {"db_password": "p@ssw0rd123"}
        result = _sanitize_config(config)
        assert result["db_password"] == "p@ss****"

    def test_short_secret_value(self):
        config = {"key": "abc"}
        result = _sanitize_config(config)
        assert result["key"] == "****"

    def test_nested_dict(self):
        config = {"outer": {"api_key": "sk-12345678", "name": "inner"}}
        result = _sanitize_config(config)
        assert result["outer"]["api_key"] == "sk-1****"
        assert result["outer"]["name"] == "inner"

    def test_empty_config(self):
        assert _sanitize_config({}) == {}

    def test_non_string_values(self):
        config = {"port": 8080, "enabled": True, "items": [1, 2, 3]}
        assert _sanitize_config(config) == config

    def test_case_insensitive_key_match(self):
        config = {"API_KEY": "sk-12345678", "Token": "tok123456"}
        result = _sanitize_config(config)
        assert result["API_KEY"] == "sk-1****"
        assert result["Token"] == "tok1****"


class TestSharePath:
    @patch("src.web.share_api.SHARE_DIR")
    def test_basic(self, mock_dir):
        mock_dir.__truediv__ = MagicMock(return_value=MagicMock())
        _share_path("abc12345")
        mock_dir.__truediv__.assert_called_once_with("share_abc12345.json")


# ========================================
# Pydantic Model Tests
# ========================================
class TestShareCreateRequest:
    def test_defaults(self):
        req = ShareCreateRequest()
        assert req.task_id is None
        assert req.include_config is True
        assert req.tags == []
        assert req.expires_hours == 0

    def test_custom(self):
        req = ShareCreateRequest(
            task_id="abc", include_config=False, tags=["t1"], expires_hours=24
        )
        assert req.task_id == "abc"
        assert req.include_config is False
        assert req.tags == ["t1"]
        assert req.expires_hours == 24


class TestShareImportRequest:
    def test_defaults(self):
        req = ShareImportRequest()
        assert req.target_dir is None

    def test_custom(self):
        req = ShareImportRequest(target_dir="/tmp/imports")
        assert req.target_dir == "/tmp/imports"


class TestShareResponse:
    def test_defaults(self):
        r = ShareResponse(share_id="abc", created_at="2026-01-01T00:00:00")
        assert r.share_id == "abc"
        assert r.expires_at is None
        assert r.tags == []
        assert r.task == ""
        assert r.steps == 0

    def test_full(self):
        r = ShareResponse(
            share_id="abc",
            created_at="2026-01-01T00:00:00",
            expires_at="2026-02-01T00:00:00",
            tags=["t1"],
            task="Fix bug",
            steps=5,
        )
        assert r.tags == ["t1"]
        assert r.task == "Fix bug"
        assert r.steps == 5


class TestShareDetailResponse:
    def test_defaults(self):
        r = ShareDetailResponse(share_id="abc", created_at="2026-01-01T00:00:00")
        assert r.version == 1
        assert r.session == {}


# ========================================
# POST /api/share — create_share
# ========================================
class TestCreateShare:
    @patch("uuid.uuid4")
    @patch("src.web.share_api.datetime")
    @patch("src.web.share_api._share_path")
    @patch("src.web.share_api._ensure_dir")
    def test_create_with_task_id_success(
        self, mock_ensure, mock_sp, mock_dt, mock_uuid4, client
    ):
        history_data = {"task_description": "Fix bug", "steps": [{"a": "read"}]}
        mock_hist_dir = MagicMock()
        mock_hist_file = MagicMock()
        mock_hist_file.exists.return_value = True
        mock_hist_dir.__truediv__ = MagicMock(return_value=mock_hist_file)

        mock_dt.now.return_value = MagicMock(
            isoformat=lambda: "2026-05-25T10:00:00",
            timestamp=lambda: 1000000.0,
        )
        mock_uuid4.return_value = MagicMock(hex="a1b2c3d4" + "0" * 16)

        with (
            patch("src.web.share_api.HISTORY_DIR", mock_hist_dir),
            patch("builtins.open", mock_open(read_data=json.dumps(history_data))),
            patch("json.load", return_value=history_data),
        ):
            resp = client.post(
                "/api/share",
                json={"task_id": "task1", "include_config": False},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["share_id"] == "a1b2c3d4"
            assert "history" in data["session"]

    @patch("src.web.share_api._ensure_dir")
    def test_create_with_task_id_not_found(self, mock_ensure, client):
        mock_hist_dir = MagicMock()
        mock_hist_dir.__truediv__ = MagicMock(
            return_value=MagicMock(exists=lambda: False)
        )
        with patch("src.web.share_api.HISTORY_DIR", mock_hist_dir):
            resp = client.post("/api/share", json={"task_id": "missing_task"})
            assert resp.status_code == 404
            assert "任务不存在" in resp.json()["detail"]

    @patch("src.web.share_api._ensure_dir")
    def test_create_no_task_id_no_history(self, mock_ensure, client):
        mock_hist_dir = MagicMock()
        mock_hist_dir.glob.return_value = []
        with patch("src.web.share_api.HISTORY_DIR", mock_hist_dir):
            resp = client.post("/api/share", json={})
            assert resp.status_code == 404
            assert "没有历史记录" in resp.json()["detail"]

    @patch("src.web.share_api._ensure_dir")
    def test_create_no_task_id_uses_latest(self, mock_ensure, client):
        history_data = {"task_description": "Latest task", "steps": []}
        mock_hist_file = MagicMock()
        mock_hist_file.stat().st_mtime = 9999
        mock_hist_dir = MagicMock()
        mock_hist_dir.glob.return_value = [mock_hist_file]
        mock_hist_dir.__truediv__ = MagicMock(return_value=mock_hist_file)

        with (
            patch("src.web.share_api.HISTORY_DIR", mock_hist_dir),
            patch("uuid.uuid4") as m_uuid,
            patch("src.web.share_api.datetime") as m_dt,
            patch("src.web.share_api._share_path"),
            patch("builtins.open", mock_open(read_data=json.dumps(history_data))),
            patch("json.load", return_value=history_data),
        ):
            m_uuid.return_value = MagicMock(hex="b1" * 8)
            m_dt.now.return_value = MagicMock(
                isoformat=lambda: "2026-05-25T10:00:00",
                timestamp=lambda: 1000000.0,
            )
            resp = client.post("/api/share", json={"include_config": False})
            assert resp.status_code == 200

    @patch("src.web.share_api._ensure_dir")
    def test_create_history_read_error(self, mock_ensure, client):
        mock_hist_dir = MagicMock()
        mock_hist_file = MagicMock()
        mock_hist_file.exists.return_value = True
        mock_hist_dir.__truediv__ = MagicMock(return_value=mock_hist_file)
        with (
            patch("src.web.share_api.HISTORY_DIR", mock_hist_dir),
            patch("builtins.open", side_effect=OSError("read err")),
        ):
            resp = client.post("/api/share", json={"task_id": "task1"})
            assert resp.status_code == 500

    @patch("uuid.uuid4")
    @patch("src.web.share_api.datetime")
    @patch("src.web.share_api._share_path")
    @patch("src.web.share_api._ensure_dir")
    def test_create_with_expires_hours(
        self, mock_ensure, mock_sp, mock_dt, mock_uuid4, client
    ):
        history_data = {"steps": []}
        mock_hist_dir = MagicMock()
        mock_hist_file = MagicMock()
        mock_hist_file.exists.return_value = True
        mock_hist_dir.__truediv__ = MagicMock(return_value=mock_hist_file)

        from datetime import datetime as real_dt

        now_ts = real_dt(2026, 5, 25, 10, 0, 0).timestamp()
        mock_dt.now.return_value = MagicMock(
            isoformat=lambda: "2026-05-25T10:00:00",
            timestamp=lambda: now_ts,
        )
        mock_dt.fromtimestamp = real_dt.fromtimestamp
        mock_uuid4.return_value = MagicMock(hex="c1" * 8)

        with (
            patch("src.web.share_api.HISTORY_DIR", mock_hist_dir),
            patch("builtins.open", mock_open(read_data=json.dumps(history_data))),
            patch("json.load", return_value=history_data),
        ):
            resp = client.post(
                "/api/share",
                json={"task_id": "t1", "include_config": False, "expires_hours": 24},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["expires_at"] is not None

    @patch("uuid.uuid4")
    @patch("src.web.share_api.datetime")
    @patch("src.web.share_api._share_path")
    @patch("src.web.share_api._ensure_dir")
    def test_create_include_config(
        self, mock_ensure, mock_sp, mock_dt, mock_uuid4, client
    ):
        history_data = {"steps": []}
        config_data = {"model": "gpt-4", "api_key": "sk-12345678"}
        mock_hist_dir = MagicMock()
        mock_hist_file = MagicMock()
        mock_hist_file.exists.return_value = True
        mock_hist_dir.__truediv__ = MagicMock(return_value=mock_hist_file)

        mock_dt.now.return_value = MagicMock(
            isoformat=lambda: "2026-05-25T10:00:00",
            timestamp=lambda: 1748196000.0,
        )
        mock_uuid4.return_value = MagicMock(hex="d1" * 8)

        config_path = MagicMock()
        config_path.exists.return_value = True

        load_count = [0]

        def fake_load(fh):
            load_count[0] += 1
            if load_count[0] == 1:
                return history_data
            return config_data

        with (
            patch("src.web.share_api.HISTORY_DIR", mock_hist_dir),
            patch("builtins.open", mock_open()),
            patch("json.load", side_effect=fake_load),
            patch("src.web.share_api.Path") as mock_path_cls,
        ):
            mock_path_cls.home.return_value.__truediv__ = MagicMock(
                return_value=MagicMock(
                    __truediv__=MagicMock(return_value=config_path)
                )
            )
            resp = client.post(
                "/api/share",
                json={"task_id": "t1", "include_config": True},
            )
            assert resp.status_code == 200

    @patch("uuid.uuid4")
    @patch("src.web.share_api.datetime")
    @patch("src.web.share_api._share_path")
    @patch("src.web.share_api._ensure_dir")
    def test_create_include_config_missing_file(
        self, mock_ensure, mock_sp, mock_dt, mock_uuid4, client
    ):
        history_data = {"steps": []}
        mock_hist_dir = MagicMock()
        mock_hist_file = MagicMock()
        mock_hist_file.exists.return_value = True
        mock_hist_dir.__truediv__ = MagicMock(return_value=mock_hist_file)

        mock_dt.now.return_value = MagicMock(
            isoformat=lambda: "2026-05-25T10:00:00",
            timestamp=lambda: 1748196000.0,
        )
        mock_uuid4.return_value = MagicMock(hex="e1" * 8)

        config_path = MagicMock()
        config_path.exists.return_value = False

        with (
            patch("src.web.share_api.HISTORY_DIR", mock_hist_dir),
            patch("builtins.open", mock_open(read_data=json.dumps(history_data))),
            patch("json.load", return_value=history_data),
            patch("src.web.share_api.Path") as mock_path_cls,
        ):
            mock_path_cls.home.return_value.__truediv__ = MagicMock(
                return_value=MagicMock(
                    __truediv__=MagicMock(return_value=config_path)
                )
            )
            resp = client.post(
                "/api/share",
                json={"task_id": "t1", "include_config": True},
            )
            assert resp.status_code == 200

    @patch("src.web.share_api._ensure_dir")
    def test_create_with_history_prefix_fallback(self, mock_ensure, client):
        history_data = {"steps": []}
        candidates = [
            MagicMock(exists=lambda: False),
            MagicMock(exists=lambda: True),
        ]
        mock_hist_dir = MagicMock()
        mock_hist_dir.__truediv__ = MagicMock(side_effect=candidates)

        with (
            patch("src.web.share_api.HISTORY_DIR", mock_hist_dir),
            patch("uuid.uuid4") as m_uuid,
            patch("src.web.share_api.datetime") as m_dt,
            patch("src.web.share_api._share_path"),
            patch("builtins.open", mock_open(read_data=json.dumps(history_data))),
            patch("json.load", return_value=history_data),
        ):
            m_uuid.return_value = MagicMock(hex="f1" * 8)
            m_dt.now.return_value = MagicMock(
                isoformat=lambda: "2026-05-25T10:00:00",
                timestamp=lambda: 1748196000.0,
            )
            resp = client.post(
                "/api/share", json={"task_id": "t1", "include_config": False}
            )
            assert resp.status_code == 200

    @patch("src.web.share_api._ensure_dir")
    def test_create_json_decode_error(self, mock_ensure, client):
        mock_hist_dir = MagicMock()
        mock_hist_file = MagicMock()
        mock_hist_file.exists.return_value = True
        mock_hist_dir.__truediv__ = MagicMock(return_value=mock_hist_file)
        with (
            patch("src.web.share_api.HISTORY_DIR", mock_hist_dir),
            patch("builtins.open", mock_open(read_data="not json")),
            patch("json.load", side_effect=json.JSONDecodeError("", "", 0)),
        ):
            resp = client.post("/api/share", json={"task_id": "task1"})
            assert resp.status_code == 500


# ========================================
# GET /api/share — list_shares
# ========================================
class TestListShares:
    @patch("src.web.share_api._ensure_dir")
    def test_list_empty(self, mock_ensure, client):
        with patch(
            "src.web.share_api.SHARE_DIR",
            MagicMock(glob=MagicMock(return_value=[])),
        ):
            resp = client.get("/api/share")
            assert resp.status_code == 200
            assert resp.json() == []

    @patch("src.web.share_api._ensure_dir")
    def test_list_with_shares(self, mock_ensure, client):
        share_data = {
            "share_id": "a1b2c3d4",
            "created_at": "2026-05-25T10:00:00",
            "expires_at": None,
            "tags": ["bugfix"],
            "session": {
                "history": {
                    "task_description": "Fix bug",
                    "steps": [{"action": "read"}, {"action": "edit"}],
                }
            },
        }
        mock_dir = MagicMock()
        mock_dir.glob.return_value = [MagicMock()]
        with (
            patch("src.web.share_api.SHARE_DIR", mock_dir),
            patch("builtins.open", mock_open(read_data=json.dumps(share_data))),
            patch("json.load", return_value=share_data),
        ):
            resp = client.get("/api/share")
            assert resp.status_code == 200
            data = resp.json()
            assert len(data) == 1
            assert data[0]["share_id"] == "a1b2c3d4"
            assert data[0]["task"] == "Fix bug"
            assert data[0]["steps"] == 2
            assert data[0]["tags"] == ["bugfix"]

    @patch("src.web.share_api._ensure_dir")
    def test_list_skips_invalid_files(self, mock_ensure, client):
        mock_dir = MagicMock()
        mock_dir.glob.return_value = [MagicMock()]
        with (
            patch("src.web.share_api.SHARE_DIR", mock_dir),
            patch("builtins.open", side_effect=OSError("err")),
        ):
            resp = client.get("/api/share")
            assert resp.status_code == 200
            assert resp.json() == []

    @patch("src.web.share_api._ensure_dir")
    def test_list_with_missing_fields(self, mock_ensure, client):
        share_data = {"share_id": "a1", "created_at": "2026-05-25T10:00:00"}
        mock_dir = MagicMock()
        mock_dir.glob.return_value = [MagicMock()]
        with (
            patch("src.web.share_api.SHARE_DIR", mock_dir),
            patch("builtins.open", mock_open(read_data="{}")),
            patch("json.load", return_value=share_data),
        ):
            resp = client.get("/api/share")
            data = resp.json()
            assert len(data) == 1
            assert data[0]["task"] == ""
            assert data[0]["steps"] == 0

    @patch("src.web.share_api._ensure_dir")
    def test_list_sorted_by_created_at_desc(self, mock_ensure, client):
        shares = [
            {"share_id": "old", "created_at": "2026-01-01T00:00:00", "session": {"history": {}}},
            {"share_id": "new", "created_at": "2026-05-25T00:00:00", "session": {"history": {}}},
        ]
        mock_dir = MagicMock()
        mock_dir.glob.return_value = [MagicMock(), MagicMock()]
        load_count = [0]

        def fake_load(*a):
            d = shares[load_count[0]]
            load_count[0] += 1
            return d

        with (
            patch("src.web.share_api.SHARE_DIR", mock_dir),
            patch("builtins.open", mock_open()),
            patch("json.load", side_effect=fake_load),
        ):
            resp = client.get("/api/share")
            data = resp.json()
            assert data[0]["share_id"] == "new"
            assert data[1]["share_id"] == "old"

    @patch("src.web.share_api._ensure_dir")
    def test_list_with_expires_at(self, mock_ensure, client):
        share_data = {
            "share_id": "x1",
            "created_at": "2026-05-25T10:00:00",
            "expires_at": "2026-06-25T10:00:00",
            "session": {"history": {}},
        }
        mock_dir = MagicMock()
        mock_dir.glob.return_value = [MagicMock()]
        with (
            patch("src.web.share_api.SHARE_DIR", mock_dir),
            patch("builtins.open", mock_open(read_data=json.dumps(share_data))),
            patch("json.load", return_value=share_data),
        ):
            resp = client.get("/api/share")
            data = resp.json()[0]
            assert data["expires_at"] == "2026-06-25T10:00:00"


# ========================================
# GET /api/share/{share_id} — get_share
# ========================================
class TestGetShare:
    def test_not_found(self, client):
        mock_path = MagicMock()
        mock_path.exists.return_value = False
        with patch("src.web.share_api._share_path", return_value=mock_path):
            resp = client.get("/api/share/nonexistent")
            assert resp.status_code == 404
            assert "分享不存在" in resp.json()["detail"]

    def test_success(self, client):
        share_data = {
            "share_id": "a1b2c3d4",
            "version": 1,
            "created_at": "2026-05-25T10:00:00",
            "expires_at": None,
            "tags": ["t1"],
            "session": {"history": {}},
        }
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        with (
            patch("src.web.share_api._share_path", return_value=mock_path),
            patch("builtins.open", mock_open(read_data=json.dumps(share_data))),
            patch("json.load", return_value=share_data),
        ):
            resp = client.get("/api/share/a1b2c3d4")
            assert resp.status_code == 200
            assert resp.json()["share_id"] == "a1b2c3d4"

    def test_expired_share(self, client):
        from datetime import datetime, timedelta

        past = (datetime.now() - timedelta(hours=1)).isoformat()
        share_data = {
            "share_id": "a1b2c3d4",
            "created_at": "2026-05-25T10:00:00",
            "expires_at": past,
            "session": {},
        }
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        with (
            patch("src.web.share_api._share_path", return_value=mock_path),
            patch("builtins.open", mock_open(read_data="{}")),
            patch("json.load", return_value=share_data),
        ):
            resp = client.get("/api/share/a1b2c3d4")
            assert resp.status_code == 410
            assert "已过期" in resp.json()["detail"]

    def test_not_expired(self, client):
        from datetime import datetime, timedelta

        future = (datetime.now() + timedelta(hours=24)).isoformat()
        share_data = {
            "share_id": "a1b2c3d4",
            "created_at": "2026-05-25T10:00:00",
            "expires_at": future,
            "session": {},
        }
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        with (
            patch("src.web.share_api._share_path", return_value=mock_path),
            patch("builtins.open", mock_open(read_data="{}")),
            patch("json.load", return_value=share_data),
        ):
            resp = client.get("/api/share/a1b2c3d4")
            assert resp.status_code == 200

    def test_read_error(self, client):
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        with (
            patch("src.web.share_api._share_path", return_value=mock_path),
            patch("builtins.open", side_effect=OSError("err")),
        ):
            resp = client.get("/api/share/a1b2c3d4")
            assert resp.status_code == 500

    def test_no_expires_at(self, client):
        """Share without expires_at should not check expiration"""
        share_data = {
            "share_id": "a1b2c3d4",
            "created_at": "2026-05-25T10:00:00",
            "session": {},
        }
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        with (
            patch("src.web.share_api._share_path", return_value=mock_path),
            patch("builtins.open", mock_open(read_data="{}")),
            patch("json.load", return_value=share_data),
        ):
            resp = client.get("/api/share/a1b2c3d4")
            assert resp.status_code == 200


# ========================================
# POST /api/share/{share_id}/import — import_share
# ========================================
class TestImportShare:
    def test_not_found(self, client):
        mock_path = MagicMock()
        mock_path.exists.return_value = False
        with patch("src.web.share_api._share_path", return_value=mock_path):
            resp = client.post("/api/share/xyz/import", json={})
            assert resp.status_code == 404

    def test_success_no_target_dir(self, client):
        share_data = {
            "expires_at": None,
            "session": {"history": {"history_id": "orig123", "steps": []}},
        }
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        with (
            patch("src.web.share_api._share_path", return_value=mock_path),
            patch("builtins.open", mock_open(read_data=json.dumps(share_data))),
            patch("json.load", return_value=share_data),
            patch("json.dump"),
            patch("src.web.share_api.HISTORY_DIR", MagicMock()),
            patch("src.web.share_api.datetime") as m_dt,
            patch("uuid.uuid4") as m_uuid,
        ):
            m_dt.now.return_value = MagicMock(isoformat=lambda: "2026-05-25T10:00:00")
            m_uuid.return_value = MagicMock(hex="new" * 4)
            resp = client.post("/api/share/a1b2c3d4/import", json={})
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "imported"
            assert "a1b2c3d4" in data["history_id"]

    def test_success_with_target_dir(self, client):
        share_data = {
            "expires_at": None,
            "session": {"history": {"history_id": "orig", "steps": []}},
        }
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_target_dir = MagicMock()
        with (
            patch("src.web.share_api._share_path", return_value=mock_path),
            patch("builtins.open", mock_open(read_data=json.dumps(share_data))),
            patch("json.load", return_value=share_data),
            patch("json.dump"),
            patch("src.web.share_api.HISTORY_DIR", MagicMock()),
            patch("src.web.share_api.datetime") as m_dt,
            patch("uuid.uuid4") as m_uuid,
            patch("src.web.share_api.Path", return_value=mock_target_dir),
        ):
            m_dt.now.return_value = MagicMock(isoformat=lambda: "2026-05-25T10:00:00")
            m_uuid.return_value = MagicMock(hex="new" * 4)
            resp = client.post(
                "/api/share/a1b2c3d4/import",
                json={"target_dir": "/custom/dir"},
            )
            assert resp.status_code == 200

    def test_empty_history(self, client):
        share_data = {"expires_at": None, "session": {"history": {}}}
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        with (
            patch("src.web.share_api._share_path", return_value=mock_path),
            patch("builtins.open", mock_open(read_data="{}")),
            patch("json.load", return_value=share_data),
        ):
            resp = client.post("/api/share/a1b2c3d4/import", json={})
            assert resp.status_code == 400
            assert "历史数据" in resp.json()["detail"]

    def test_no_history_key(self, client):
        share_data = {"expires_at": None, "session": {}}
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        with (
            patch("src.web.share_api._share_path", return_value=mock_path),
            patch("builtins.open", mock_open(read_data="{}")),
            patch("json.load", return_value=share_data),
        ):
            resp = client.post("/api/share/a1b2c3d4/import", json={})
            assert resp.status_code == 400

    def test_expired_share(self, client):
        from datetime import datetime, timedelta

        past = (datetime.now() - timedelta(hours=1)).isoformat()
        share_data = {"expires_at": past, "session": {"history": {"steps": []}}}
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        with (
            patch("src.web.share_api._share_path", return_value=mock_path),
            patch("builtins.open", mock_open(read_data="{}")),
            patch("json.load", return_value=share_data),
        ):
            resp = client.post("/api/share/a1b2c3d4/import", json={})
            assert resp.status_code == 410

    def test_read_error(self, client):
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        with (
            patch("src.web.share_api._share_path", return_value=mock_path),
            patch("builtins.open", side_effect=OSError("err")),
        ):
            resp = client.post("/api/share/a1b2c3d4/import", json={})
            assert resp.status_code == 500

    def test_import_response_fields(self, client):
        share_data = {
            "expires_at": None,
            "session": {"history": {"history_id": "h1", "steps": []}},
        }
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        with (
            patch("src.web.share_api._share_path", return_value=mock_path),
            patch("builtins.open", mock_open(read_data=json.dumps(share_data))),
            patch("json.load", return_value=share_data),
            patch("json.dump"),
            patch("src.web.share_api.HISTORY_DIR", MagicMock()),
            patch("src.web.share_api.datetime") as m_dt,
            patch("uuid.uuid4") as m_uuid,
        ):
            m_dt.now.return_value = MagicMock(isoformat=lambda: "2026-05-25T10:00:00")
            m_uuid.return_value = MagicMock(hex="nn" * 4)
            resp = client.post("/api/share/a1b2c3d4/import", json={})
            data = resp.json()
            assert "status" in data
            assert "history_id" in data
            assert "share_id" in data
            assert "file" in data


# ========================================
# DELETE /api/share/{share_id} — delete_share
# ========================================
class TestDeleteShare:
    def test_not_found(self, client):
        mock_path = MagicMock()
        mock_path.exists.return_value = False
        with patch("src.web.share_api._share_path", return_value=mock_path):
            resp = client.delete("/api/share/nonexistent")
            assert resp.status_code == 404

    def test_success(self, client):
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        with patch("src.web.share_api._share_path", return_value=mock_path):
            resp = client.delete("/api/share/a1b2c3d4")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "deleted"
            assert data["share_id"] == "a1b2c3d4"
            mock_path.unlink.assert_called_once()
