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
        # import httpx is local inside _check_api_key_works → patch the right namespace
        with patch("src.commands.quickstart.httpx.get", side_effect=httpx.ConnectError("fail")):
            assert _check_api_key_works("DEEPSEEK_API_KEY", "deepseek") is True

    def test_glm_network_error_fallback_true(self, monkeypatch):
        """httpx exception inside glm branch → fallback to return True (lines 149-150)"""
        monkeypatch.setenv("ZHIPUAI_API_KEY", "longkey1234567890")
        with patch("src.commands.quickstart.httpx.get", side_effect=httpx.ConnectError("fail")):
            assert _check_api_key_works("ZHIPUAI_API_KEY", "glm") is True

    def test_deepseek_http_error_500(self, monkeypatch):
        """deepseek with 500 status → return False (line ~148)"""
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-longenoughkey12345")
        mock_resp = MagicMock(status_code=500)
        with patch("src.commands.quickstart.httpx.get", return_value=mock_resp):
            assert _check_api_key_works("DEEPSEEK_API_KEY", "deepseek") is False


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

    def test_config_file_malformed_json(self, monkeypatch, tmp_path):
        """Config file exists but has invalid JSON → except Exception: pass (lines 149-150)"""
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
        monkeypatch.delenv("OMC_DEFAULT_MODEL", raising=False)
        config_dir = tmp_path / ".config" / "oh-my-coder"
        config_dir.mkdir(parents=True)
        # Write malformed JSON to trigger the except Exception: pass branch
        (config_dir / "config.json").write_text("{not valid json}")
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        steps = detect_completed_steps()
        # Should NOT crash; model step is False since no key/env
        assert steps["model"] is False
        assert steps["apikey"] is False

    def test_verify_with_http_error_on_check(self, monkeypatch, tmp_path):
        """API key present but _check_api_key_works returns False (network/format error)"""
        monkeypatch.setenv("KIMI_API_KEY", "sk-short")  # short key → returns False without HTTP call
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        steps = detect_completed_steps()
        # apikey is True (env var is set), but verify is False (key too short)
        assert steps["apikey"] is True
        assert steps["verify"] is False


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

    @pytest.mark.asyncio
    async def test_doubao_success(self, monkeypatch):
        monkeypatch.setenv("DOUBAO_API_KEY", "dk123456789012")
        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "sort code"}}]
        }
        with patch("httpx.post", return_value=mock_resp):
            result = await _call_model_demo({"id": "doubao", "api_key_env": "DOUBAO_API_KEY"})
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_tongyi_success(self, monkeypatch):
        monkeypatch.setenv("TONGYI_API_KEY", "tk123456789012")
        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "sort code"}}]
        }
        with patch("httpx.post", return_value=mock_resp):
            result = await _call_model_demo({"id": "tongyi", "api_key_env": "TONGYI_API_KEY"})
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_minimax_success(self, monkeypatch):
        monkeypatch.setenv("MINIMAX_API_KEY", "mk123456789012")
        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "sort code"}}]
        }
        with patch("httpx.post", return_value=mock_resp):
            result = await _call_model_demo({"id": "minimax", "api_key_env": "MINIMAX_API_KEY"})
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_hunyuan_no_token(self, monkeypatch):
        monkeypatch.setenv("HUNYUAN_API_KEY", "hk1234567890")
        with patch("src.commands.quickstart._get_hunyuan_access_token", return_value=None):
            result = await _call_model_demo({"id": "hunyuan", "api_key_env": "HUNYUAN_API_KEY"})
        assert result["success"] is False
        assert "access_token" in result["error"]

    @pytest.mark.asyncio
    async def test_server_error_with_text_body(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test1234567890")
        mock_resp = MagicMock(status_code=502)
        mock_resp.json.side_effect = Exception("not json")
        mock_resp.text = "bad gateway"
        with patch("httpx.post", return_value=mock_resp):
            result = await _call_model_demo({"id": "deepseek", "api_key_env": "DEEPSEEK_API_KEY"})
        assert result["success"] is False
        assert "502" in result["error"]

    @pytest.mark.asyncio
    async def test_generic_exception(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test1234567890")
        with patch("httpx.post", side_effect=RuntimeError("unexpected")):
            result = await _call_model_demo({"id": "deepseek", "api_key_env": "DEEPSEEK_API_KEY"})
        assert result["success"] is False
        assert "请求失败" in result["error"]

    @pytest.mark.asyncio
    async def test_response_result_field(self, monkeypatch):
        """Test wenxin-style result field"""
        monkeypatch.setenv("WENXIN_API_KEY", "wk1234567890")
        monkeypatch.setenv("WENXIN_SECRET_KEY", "ws1234567890")
        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = {"result": "def qs(a): pass"}
        with patch("src.commands.quickstart._get_wenxin_access_token", return_value="tok"):
            with patch("httpx.post", return_value=mock_resp):
                result = await _call_model_demo({"id": "wenxin", "api_key_env": "WENXIN_API_KEY"})
        assert result["success"] is True
        assert result["code"] == "def qs(a): pass"

    @pytest.mark.asyncio
    async def test_server_error_message_in_error_field(self, monkeypatch):
        """Test error message extraction from error.message"""
        monkeypatch.setenv("KIMI_API_KEY", "kk123456789012")
        mock_resp = MagicMock(status_code=403)
        mock_resp.json.return_value = {"error": {"message": "forbidden"}}
        with patch("httpx.post", return_value=mock_resp):
            result = await _call_model_demo({"id": "kimi", "api_key_env": "KIMI_API_KEY"})
        assert result["success"] is False
        assert "forbidden" in result["error"]


# ── _step1_select_model ────────────────────────────────────────

from src.commands.quickstart import (
    _show_summary,
    _step1_select_model,
    _step2_config_apikey,
    _step3_run_demo,
    app,
)


class TestStep1SelectModel:
    def test_user_selects_valid(self):
        with patch("src.commands.quickstart.Prompt.ask", return_value="1"):
            result = _step1_select_model()
        assert result is not None
        assert result["id"] == "deepseek"

    def test_user_skips_with_enter(self):
        with patch("src.commands.quickstart.Prompt.ask", return_value=""):
            result = _step1_select_model()
        assert result is None

    def test_user_skips_with_whitespace(self):
        with patch("src.commands.quickstart.Prompt.ask", return_value="   "):
            result = _step1_select_model()
        assert result is None

    def test_invalid_choice(self):
        with patch("src.commands.quickstart.Prompt.ask", return_value="999"):
            result = _step1_select_model()
        assert result is None

    def test_select_second_model(self):
        with patch("src.commands.quickstart.Prompt.ask", return_value="2"):
            result = _step1_select_model()
        assert result is not None
        assert result["id"] == "glm"

    def test_select_last_paid_model(self):
        total = sum(len(v) for v in MODEL_CATEGORIES.values())
        last = MODEL_CATEGORIES["国产付费"][-1]
        with patch("src.commands.quickstart.Prompt.ask", return_value=str(total)):
            result = _step1_select_model()
        assert result is not None
        assert result["id"] == last["id"]


# ── _step2_config_apikey ────────────────────────────────────────

class TestStep2ConfigApikey:
    def test_new_key_input(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        model_info = MODEL_CATEGORIES["国产免费"][0]
        monkeypatch.delenv(model_info["api_key_env"], raising=False)
        with patch("src.commands.quickstart.Prompt.ask", return_value="sk-new-key-12345"):
            with patch("src.commands.quickstart.Confirm.ask", return_value=False):
                result = _step2_config_apikey(model_info)
        assert result is True

    def test_empty_key_skipped(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        model_info = MODEL_CATEGORIES["国产免费"][0]
        monkeypatch.delenv(model_info["api_key_env"], raising=False)
        with patch("src.commands.quickstart.Prompt.ask", return_value=""):
            result = _step2_config_apikey(model_info)
        assert result is False

    def test_existing_key_keep(self, monkeypatch):
        model_info = MODEL_CATEGORIES["国产免费"][0]
        monkeypatch.setenv(model_info["api_key_env"], "sk-existing-key-12345")
        with patch("src.commands.quickstart.Confirm.ask", return_value=False):
            result = _step2_config_apikey(model_info)
        assert result is True

    def test_existing_key_update(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        model_info = MODEL_CATEGORIES["国产免费"][0]
        monkeypatch.setenv(model_info["api_key_env"], "sk-existing-key-12345")
        with patch("src.commands.quickstart.Confirm.ask", return_value=True):
            with patch("src.commands.quickstart.Prompt.ask", return_value="sk-updated-67890"):
                result = _step2_config_apikey(model_info)
        assert result is True

    def test_existing_key_update_via_main_flow(self, tmp_path, monkeypatch):
        """
        User has existing key, says 'yes' to update → enters new key.
        This exercises the Confirm.ask=True branch (line ~213 pass statement)
        and the subsequent new-key input flow.
        """
        monkeypatch.chdir(tmp_path)
        model_info = MODEL_CATEGORIES["国产付费"][0]  # use a different model
        monkeypatch.setenv(model_info["api_key_env"], "sk-oldkey-long12345")
        with patch("src.commands.quickstart.Confirm.ask", return_value=True):
            with patch("src.commands.quickstart.Prompt.ask", return_value="sk-newkey-updated-99"):
                result = _step2_config_apikey(model_info)
        assert result is True
        # Verify the new key was written to the env
        assert os.getenv(model_info["api_key_env"]) == "sk-newkey-updated-99"


# ── _step3_run_demo ────────────────────────────────────────────

class TestStep3RunDemo:
    def test_user_skips(self):
        model_info = MODEL_CATEGORIES["国产免费"][0]
        with patch("src.commands.quickstart.Confirm.ask", return_value=False):
            result = _step3_run_demo(model_info)
        assert result is False

    @pytest.mark.asyncio
    async def _fake_call_model_demo(self, model_info):
        return {"success": False, "error": "bad key"}

    def test_success(self):
        model_info = MODEL_CATEGORIES["国产免费"][0]
        async def fake_call(mi):
            return {"success": True, "code": "def qs(a): pass"}
        with patch("src.commands.quickstart.Confirm.ask", return_value=True):
            with patch("src.commands.quickstart._call_model_demo", side_effect=fake_call):
                result = _step3_run_demo(model_info)
        assert result is True

    def test_failure(self):
        model_info = MODEL_CATEGORIES["国产免费"][0]
        with patch("src.commands.quickstart.Confirm.ask", return_value=True):
            async def fake(mi):
                return {"success": False, "error": "bad key"}
            with patch("src.commands.quickstart._call_model_demo", side_effect=fake):
                result = _step3_run_demo(model_info)
        assert result is False

    def test_exception_during_call(self):
        model_info = MODEL_CATEGORIES["国产免费"][0]
        with patch("src.commands.quickstart.Confirm.ask", return_value=True):
            async def fake(mi):
                raise RuntimeError("boom")
            with patch("src.commands.quickstart._call_model_demo", side_effect=fake):
                result = _step3_run_demo(model_info)
        assert result is False


# ── _show_summary ──────────────────────────────────────────────

class TestShowSummary:
    def test_shows_without_error(self):
        model_info = MODEL_CATEGORIES["国产免费"][0]
        _show_summary(model_info, {"model": True, "apikey": True, "verify": True})

    def test_partial_completion(self):
        model_info = MODEL_CATEGORIES["国产免费"][0]
        _show_summary(model_info, {"model": True, "apikey": False, "verify": False})


# ── main command ────────────────────────────────────────────────
from typer.testing import CliRunner

runner = CliRunner()


class TestMainCommand:
    def _run(self, args, **patch_kwargs):
        """Helper: run quickstart with mocked dependencies. Returns (exit_code, output)."""
        patches = patch_kwargs.pop("patches", {})
        with patch("src.commands.quickstart.Confirm.ask", return_value=True):
            with patch("src.commands.quickstart.Prompt.ask", return_value=""):
                with patch("src.commands.quickstart.detect_completed_steps", return_value={"model": False, "apikey": False, "verify": False}):
                    with patch("src.commands.quickstart._step1_select_model", return_value=None):
                        for _target, _retval in patches.items():
                            pass  # handled below
                        # Apply custom patches via context managers
                        from contextlib import ExitStack
                        stack = ExitStack()
                        for target, retval in patches.items():
                            stack.enter_context(patch(target, return_value=retval))
                        with stack:
                            result = runner.invoke(app, args, catch_exceptions=False)
        return result.exit_code, result.output

    def test_model_flag_unknown(self):
        result = runner.invoke(app, ["--model", "nonexistent"], catch_exceptions=False)
        assert result.exit_code == 1

    def test_model_flag_with_key(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-longkey12345678")
        with patch("src.commands.quickstart._step3_run_demo", return_value=True):
            with patch("src.commands.quickstart._show_summary"):
                result = runner.invoke(app, ["--model", "deepseek"], catch_exceptions=False)
        assert result.exit_code == 0

    def test_model_flag_verify_fails(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-longkey12345678")
        with patch("src.commands.quickstart._step3_run_demo", return_value=False):
            with patch("src.commands.quickstart._show_summary"):
                result = runner.invoke(app, ["--model", "deepseek"], catch_exceptions=False)
        assert result.exit_code == 1

    def test_model_flag_no_key_runs_step2(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
        with patch("src.commands.quickstart._step2_config_apikey", return_value=True):
            with patch("src.commands.quickstart._step3_run_demo", return_value=True):
                with patch("src.commands.quickstart._show_summary"):
                    result = runner.invoke(app, ["--model", "deepseek"], catch_exceptions=False)
        assert result.exit_code == 0

    def test_step_model(self):
        with patch("src.commands.quickstart._step1_select_model", return_value=None):
            result = runner.invoke(app, ["--step", "model"], catch_exceptions=False)
        assert result.exit_code == 0

    def test_step_apikey_no_model(self):
        result = runner.invoke(app, ["--step", "apikey"], catch_exceptions=False)
        assert result.exit_code == 1

    def test_step_verify_no_key(self, monkeypatch):
        for env in ["DEEPSEEK_API_KEY", "KIMI_API_KEY", "DOUBAO_API_KEY", "ZHIPUAI_API_KEY",
                     "TONGYI_API_KEY", "MINIMAX_API_KEY", "WENXIN_API_KEY", "HUNYUAN_API_KEY",
                     "BAICHUAN_API_KEY"]:
            monkeypatch.delenv(env, raising=False)
        result = runner.invoke(app, ["--step", "verify"], catch_exceptions=False)
        assert result.exit_code == 1

    def test_step_verify_success(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-longkey12345678")
        with patch("src.commands.quickstart._step3_run_demo", return_value=True):
            result = runner.invoke(app, ["--step", "verify"], catch_exceptions=False)
        assert result.exit_code == 0

    def test_step_verify_failure(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-longkey12345678")
        with patch("src.commands.quickstart._step3_run_demo", return_value=False):
            result = runner.invoke(app, ["--step", "verify"], catch_exceptions=False)
        assert result.exit_code == 1

    def test_unknown_step(self):
        result = runner.invoke(app, ["--step", "badstep"], catch_exceptions=False)
        assert result.exit_code == 1

    def test_full_flow_cancel(self):
        with patch("src.commands.quickstart.Confirm.ask", return_value=False):
            result = runner.invoke(app, [], catch_exceptions=False)
        assert result.exit_code == 0

    def test_full_flow_no_model_selected(self):
        with patch("src.commands.quickstart.Confirm.ask", return_value=True):
            with patch("src.commands.quickstart.detect_completed_steps", return_value={"model": False, "apikey": False, "verify": False}):
                with patch("src.commands.quickstart._step1_select_model", return_value=None):
                    result = runner.invoke(app, [], catch_exceptions=False)
        assert result.exit_code == 0

    def test_full_flow_all_steps(self):
        model_info = MODEL_CATEGORIES["国产免费"][0]
        with patch("src.commands.quickstart.Confirm.ask", return_value=True):
            with patch("src.commands.quickstart.detect_completed_steps", return_value={"model": False, "apikey": False, "verify": False}):
                with patch("src.commands.quickstart._step1_select_model", return_value=model_info):
                    with patch("src.commands.quickstart._step2_config_apikey", return_value=True):
                        with patch("src.commands.quickstart._step3_run_demo", return_value=True):
                            with patch("src.commands.quickstart._show_summary"):
                                result = runner.invoke(app, [], catch_exceptions=False)
        assert result.exit_code == 0

    def test_full_flow_verify_fails(self):
        model_info = MODEL_CATEGORIES["国产免费"][0]
        with patch("src.commands.quickstart.Confirm.ask", return_value=True):
            with patch("src.commands.quickstart.detect_completed_steps", return_value={"model": False, "apikey": False, "verify": False}):
                with patch("src.commands.quickstart._step1_select_model", return_value=model_info):
                    with patch("src.commands.quickstart._step2_config_apikey", return_value=True):
                        with patch("src.commands.quickstart._step3_run_demo", return_value=False):
                            with patch("src.commands.quickstart._show_summary"):
                                result = runner.invoke(app, [], catch_exceptions=False)
        assert result.exit_code == 1

    def test_full_flow_skip_step1_detected_model(self, monkeypatch):
        model_info = MODEL_CATEGORIES["国产免费"][0]
        monkeypatch.setenv(model_info["api_key_env"], "sk-longkey12345678")
        with patch("src.commands.quickstart.Confirm.ask", return_value=True):
            with patch("src.commands.quickstart.detect_completed_steps", return_value={"model": True, "apikey": True, "verify": True}):
                with patch("src.commands.quickstart._step3_run_demo", return_value=True) as mock_run:
                    with patch("src.commands.quickstart._show_summary"):
                        result = runner.invoke(app, [], catch_exceptions=False)
        assert result.exit_code == 0
        mock_run.assert_not_called()

    def test_force_flag(self):
        model_info = MODEL_CATEGORIES["国产免费"][0]
        with patch("src.commands.quickstart.Confirm.ask", return_value=True):
            with patch("src.commands.quickstart.detect_completed_steps", return_value={"model": False, "apikey": False, "verify": False}):
                with patch("src.commands.quickstart._step1_select_model", return_value=model_info):
                    with patch("src.commands.quickstart._step2_config_apikey", return_value=True):
                        with patch("src.commands.quickstart._step3_run_demo", return_value=True):
                            with patch("src.commands.quickstart._show_summary"):
                                result = runner.invoke(app, ["--force"], catch_exceptions=False)
        assert result.exit_code == 0

    def test_full_flow_user_skips_then_detected_key(self, monkeypatch):
        """User presses enter in step1, but a key is already configured"""
        model_info = MODEL_CATEGORIES["国产免费"][0]
        monkeypatch.setenv(model_info["api_key_env"], "sk-longkey12345678")
        with patch("src.commands.quickstart.Confirm.ask", return_value=True):
            with patch("src.commands.quickstart.detect_completed_steps", return_value={"model": False, "apikey": False, "verify": False}):
                with patch("src.commands.quickstart._step1_select_model", return_value=None):
                    with patch("src.commands.quickstart._step2_config_apikey", return_value=True):
                        with patch("src.commands.quickstart._step3_run_demo", return_value=True):
                            with patch("src.commands.quickstart._show_summary"):
                                result = runner.invoke(app, [], catch_exceptions=False)
        assert result.exit_code == 0

    def test_full_flow_completed_model_but_no_key(self):
        """model step completed but apikey not"""
        with patch("src.commands.quickstart.Confirm.ask", return_value=True):
            with patch("src.commands.quickstart.detect_completed_steps", return_value={"model": True, "apikey": False, "verify": False}):
                with patch("src.commands.quickstart._step2_config_apikey", return_value=True):
                    with patch("src.commands.quickstart._step3_run_demo", return_value=True):
                        with patch("src.commands.quickstart._show_summary"):
                            result = runner.invoke(app, [], catch_exceptions=False)
        assert result.exit_code == 0

    def test_model_flag_kimi(self, monkeypatch):
        monkeypatch.setenv("KIMI_API_KEY", "sk-longkey12345678")
        with patch("src.commands.quickstart._step3_run_demo", return_value=True):
            with patch("src.commands.quickstart._show_summary"):
                result = runner.invoke(app, ["--model", "kimi"], catch_exceptions=False)
        assert result.exit_code == 0

    def test_model_flag_doubao(self, monkeypatch):
        monkeypatch.setenv("DOUBAO_API_KEY", "sk-longkey12345678")
        with patch("src.commands.quickstart._step3_run_demo", return_value=True):
            with patch("src.commands.quickstart._show_summary"):
                result = runner.invoke(app, ["--model", "doubao"], catch_exceptions=False)
        assert result.exit_code == 0

    def test_model_flag_glm(self, monkeypatch):
        monkeypatch.setenv("ZHIPUAI_API_KEY", "sk-longkey12345678")
        with patch("src.commands.quickstart._step3_run_demo", return_value=True):
            with patch("src.commands.quickstart._show_summary"):
                result = runner.invoke(app, ["--model", "glm"], catch_exceptions=False)
        assert result.exit_code == 0
