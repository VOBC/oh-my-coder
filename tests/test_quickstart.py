"""Tests for src/commands/quickstart.py"""
from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest

from src.commands.quickstart import (
    MODEL_CATEGORIES,
    REGISTER_URLS,
    _call_model_demo,
    _check_api_key_works,
    _get_hunyuan_access_token,
    _get_wenxin_access_token,
    _set_env_var,
    _truncate,
    detect_completed_steps,
)

# ── Constants ───────────────────────────────────────────────────

class TestConstants:
    def test_model_categories_not_empty(self):
        total = sum(len(v) for v in MODEL_CATEGORIES.values())
        assert total >= 2

    def test_register_urls_match_categories(self):
        for cat_models in MODEL_CATEGORIES.values():
            for m in cat_models:
                assert m["id"] in REGISTER_URLS

    def test_each_model_has_required_fields(self):
        for cat_models in MODEL_CATEGORIES.values():
            for m in cat_models:
                assert "id" in m
                assert "name" in m
                assert "api_key_env" in m
                assert "model_name" in m
                assert "register_url" in m


# ── _truncate ───────────────────────────────────────────────────

class TestTruncate:
    def test_short_string_unchanged(self):
        assert _truncate("hello", 10) == "hello"

    def test_exact_length_unchanged(self):
        assert _truncate("hello", 5) == "hello"

    def test_long_string_truncated(self):
        result = _truncate("abcdefghij", 5)
        assert result == "abcde\n..."

    def test_empty_string(self):
        assert _truncate("", 10) == ""

    def test_none_like_empty(self):
        # Actually it receives str, but test empty
        assert _truncate("", 100) == ""


# ── _set_env_var ────────────────────────────────────────────────

class TestSetEnvVar:
    def test_sets_os_environ(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _set_env_var("TEST_QS_KEY", "secret123")
        assert os.getenv("TEST_QS_KEY") == "secret123"

    def test_writes_to_dot_env(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _set_env_var("TEST_QS_KEY", "secret123")
        content = (tmp_path / ".env").read_text()
        assert "TEST_QS_KEY=secret123" in content

    def test_updates_existing_dot_env(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".env").write_text("EXISTING=val1\n")
        _set_env_var("TEST_QS_KEY", "newval")
        content = (tmp_path / ".env").read_text()
        assert "EXISTING=val1" in content
        assert "TEST_QS_KEY=newval" in content

    def test_writes_to_home_env(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        home_env = tmp_path / ".omc.env"
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        _set_env_var("TEST_QS_KEY", "hval")
        assert home_env.exists()
        assert "TEST_QS_KEY=hval" in home_env.read_text()


# ── _check_api_key_works ────────────────────────────────────────

class TestCheckApiKeyWorks:
    def test_no_key_returns_false(self, monkeypatch):
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
        assert _check_api_key_works("DEEPSEEK_API_KEY", "deepseek") is False

    def test_short_key_returns_false(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "short")
        assert _check_api_key_works("DEEPSEEK_API_KEY", "deepseek") is False

    def test_deepseek_200(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-longenoughkey12345")
        mock_resp = MagicMock(status_code=200)
        with patch("httpx.get", return_value=mock_resp):
            assert _check_api_key_works("DEEPSEEK_API_KEY", "deepseek") is True

    def test_deepseek_401_still_true(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-longenoughkey12345")
        mock_resp = MagicMock(status_code=401)
        with patch("httpx.get", return_value=mock_resp):
            assert _check_api_key_works("DEEPSEEK_API_KEY", "deepseek") is True

    def test_deepseek_500_returns_false(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-longenoughkey12345")
        mock_resp = MagicMock(status_code=500)
        with patch("httpx.get", return_value=mock_resp):
            assert _check_api_key_works("DEEPSEEK_API_KEY", "deepseek") is False

    def test_glm_200(self, monkeypatch):
        monkeypatch.setenv("ZHIPUAI_API_KEY", "longkey123456789")
        mock_resp = MagicMock(status_code=200)
        with patch("httpx.get", return_value=mock_resp):
            assert _check_api_key_works("ZHIPUAI_API_KEY", "glm") is True

    def test_unknown_provider_fallback(self, monkeypatch):
        monkeypatch.setenv("KIMI_API_KEY", "longkey123456789")
        assert _check_api_key_works("KIMI_API_KEY", "kimi") is True

    def test_network_error_fallback_true(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-longenoughkey12345")
        with patch("httpx.get", side_effect=httpx.ConnectError("fail")):
            assert _check_api_key_works("DEEPSEEK_API_KEY", "deepseek") is True


# ── detect_completed_steps ──────────────────────────────────────

class TestDetectCompletedSteps:
    def test_no_config(self, monkeypatch, tmp_path):
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
        monkeypatch.delenv("OMC_DEFAULT_MODEL", raising=False)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        steps = detect_completed_steps()
        assert steps["model"] is False
        assert steps["apikey"] is False

    def test_with_config_file_model(self, monkeypatch, tmp_path):
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
        config_dir = tmp_path / ".config" / "oh-my-coder"
        config_dir.mkdir(parents=True)
        (config_dir / "config.json").write_text(json.dumps({"default_model": "deepseek-chat"}))
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        steps = detect_completed_steps()
        assert steps["model"] is True

    def test_with_env_model(self, monkeypatch):
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
        monkeypatch.setenv("OMC_DEFAULT_MODEL", "glm-4-flash")
        steps = detect_completed_steps()
        assert steps["model"] is True

    def test_with_api_key_set(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-longkey12345678901")
        with patch.object(os, "getenv", side_effect=os.getenv):
            with patch("src.commands.quickstart._check_api_key_works", return_value=True):
                steps = detect_completed_steps()
                assert steps["apikey"] is True
                assert steps["verify"] is True


# ── _get_wenxin_access_token ────────────────────────────────────

class TestGetWenxinAccessToken:
    def test_success(self):
        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = {"access_token": "tok123"}
        with patch("httpx.get", return_value=mock_resp):
            result = _get_wenxin_access_token("api_key")
        assert result == "tok123"

    def test_failure(self):
        mock_resp = MagicMock(status_code=500)
        with patch("httpx.get", return_value=mock_resp):
            assert _get_wenxin_access_token("bad") is None

    def test_network_error(self):
        with patch("httpx.get", side_effect=Exception("fail")):
            assert _get_wenxin_access_token("key") is None


# ── _get_hunyuan_access_token ───────────────────────────────────

class TestGetHunyuanAccessToken:
    def test_success(self):
        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = {"token": {"access_token": "tok456"}}
        with patch("httpx.post", return_value=mock_resp):
            result = _get_hunyuan_access_token("sid", "skey")
        assert result == "tok456"

    def test_failure(self):
        mock_resp = MagicMock(status_code=500)
        with patch("httpx.post", return_value=mock_resp):
            assert _get_hunyuan_access_token("s", "k") is None

    def test_network_error(self):
        with patch("httpx.post", side_effect=Exception("fail")):
            assert _get_hunyuan_access_token("s", "k") is None


# ── _call_model_demo ────────────────────────────────────────────

class TestCallModelDemo:
    @pytest.mark.asyncio
    async def test_deepseek_success(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test1234567890")
        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "def quicksort(arr):\n    pass"}}]
        }
        with patch("httpx.post", return_value=mock_resp):
            result = await _call_model_demo({"id": "deepseek", "api_key_env": "DEEPSEEK_API_KEY"})
        assert result["success"] is True
        assert "quicksort" in result["code"]

    @pytest.mark.asyncio
    async def test_glm_success(self, monkeypatch):
        monkeypatch.setenv("ZHIPUAI_API_KEY", "longkey1234567890")
        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "def qs(a): pass"}}]
        }
        with patch("httpx.post", return_value=mock_resp):
            result = await _call_model_demo({"id": "glm", "api_key_env": "ZHIPUAI_API_KEY"})
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_no_api_key(self, monkeypatch):
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
        result = await _call_model_demo({"id": "deepseek", "api_key_env": "DEEPSEEK_API_KEY"})
        assert result["success"] is False
        assert "未配置" in result["error"]

    @pytest.mark.asyncio
    async def test_server_error(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test1234567890")
        mock_resp = MagicMock(status_code=500)
        mock_resp.json.return_value = {"error": {"message": "internal error"}}
        with patch("httpx.post", return_value=mock_resp):
            result = await _call_model_demo({"id": "deepseek", "api_key_env": "DEEPSEEK_API_KEY"})
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_timeout(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test1234567890")
        with patch("httpx.post", side_effect=httpx.TimeoutException("timeout")):
            result = await _call_model_demo({"id": "deepseek", "api_key_env": "DEEPSEEK_API_KEY"})
        assert result["success"] is False
        assert "超时" in result["error"]

    @pytest.mark.asyncio
    async def test_wenxin_success(self, monkeypatch):
        monkeypatch.setenv("WENXIN_API_KEY", "wk1234567890")
        monkeypatch.setenv("WENXIN_SECRET_KEY", "ws1234567890")
        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = {"result": "def qs(a): pass"}
        with patch("src.commands.quickstart._get_wenxin_access_token", return_value="tok"):
            with patch("httpx.post", return_value=mock_resp):
                result = await _call_model_demo({"id": "wenxin", "api_key_env": "WENXIN_API_KEY"})
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_wenxin_no_token(self, monkeypatch):
        monkeypatch.setenv("WENXIN_API_KEY", "wk1234567890")
        with patch("src.commands.quickstart._get_wenxin_access_token", return_value=None):
            result = await _call_model_demo({"id": "wenxin", "api_key_env": "WENXIN_API_KEY"})
        assert result["success"] is False
        assert "access_token" in result["error"]

    @pytest.mark.asyncio
    async def test_hunyuan_success(self, monkeypatch):
        monkeypatch.setenv("HUNYUAN_API_KEY", "hk1234567890")
        monkeypatch.setenv("HUNYUAN_SECRET_KEY", "hs1234567890")
        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "code here"}}]
        }
        with patch("src.commands.quickstart._get_hunyuan_access_token", return_value="atok"):
            with patch("httpx.post", return_value=mock_resp):
                result = await _call_model_demo({"id": "hunyuan", "api_key_env": "HUNYUAN_API_KEY"})
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_unsupported_provider(self, monkeypatch):
        monkeypatch.setenv("BAICHUAN_API_KEY", "bk1234567890")
        result = await _call_model_demo({"id": "baichuan", "api_key_env": "BAICHUAN_API_KEY"})
        assert result["success"] is False
        assert "暂不支持" in result["error"]

    @pytest.mark.asyncio
    async def test_kimi_success(self, monkeypatch):
        monkeypatch.setenv("KIMI_API_KEY", "kk123456789012")
        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "sort code"}}]
        }
        with patch("httpx.post", return_value=mock_resp):
            result = await _call_model_demo({"id": "kimi", "api_key_env": "KIMI_API_KEY"})
        assert result["success"] is True
