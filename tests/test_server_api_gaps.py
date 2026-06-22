"""
Tests covering remaining gaps in server_api.py:
- get_auth() function (FastAPI dependency)
- run_agent_task() async function
"""
from __future__ import annotations

from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.api.server_api import (
    AuthContext,
    TaskStatus,
    get_auth,
    run_agent_task,
)


# ── get_auth ───────────────────────────────────────────────────────────


class TestGetAuth:
    """Test get_auth FastAPI dependency."""

    def test_get_auth_matching_key(self):
        ctx = AuthContext("secret-key")
        result = get_auth(x_api_key="secret-key", auth_ctx=ctx)
        assert result == "secret-key"

    def test_get_auth_wrong_key_raises_401(self):
        from fastapi import HTTPException
        ctx = AuthContext("secret-key")
        with pytest.raises(HTTPException) as exc_info:
            get_auth(x_api_key="wrong-key", auth_ctx=ctx)
        assert exc_info.value.status_code == 401

    def test_get_auth_no_key_required(self):
        ctx = AuthContext(None)
        result = get_auth(x_api_key=None, auth_ctx=ctx)
        assert result is None

    def test_get_auth_empty_key_vs_none_required(self):
        ctx = AuthContext(None)
        result = get_auth(x_api_key="", auth_ctx=ctx)
        assert result == ""


# ── run_agent_task ─────────────────────────────────────────────────────


class TestRunAgentTask:
    """Test run_agent_task background execution."""

    @pytest.mark.asyncio
    async def test_run_agent_task_degraded_fallback(self):
        """When Orchestrator import fails, fallback to degraded response."""
        store = Mock()
        store.update = AsyncMock()

        # Patch the Orchestrator import inside the try block of run_agent_task
        with patch("src.core.orchestrator.Orchestrator", side_effect=ImportError("no orch")):
            await run_agent_task(prompt="hello", task_id="t1", store=store)

        assert store.update.call_count == 2
        store.update.assert_any_call("t1", TaskStatus.RUNNING)
        call_args = store.update.call_args_list[1]
        assert call_args[0][0] == "t1"
        assert call_args[0][1] == TaskStatus.COMPLETED
        result = call_args[1]["result"]
        assert result["status"] == "degraded"
        assert result["output"] == "hello"

    @pytest.mark.asyncio
    async def test_run_agent_task_outer_exception(self):
        """Outer exception handler catches failures and marks task FAILED."""
        store = Mock()
        # Raise on first call (RUNNING update), but succeed on retry for FAILED
        store.update = AsyncMock(side_effect=[RuntimeError("boom"), None])

        await run_agent_task(prompt="test", task_id="t-fail", store=store)

        assert store.update.call_count == 2
        store.update.assert_any_call("t-fail", TaskStatus.RUNNING)
        store.update.assert_any_call("t-fail", TaskStatus.FAILED, error="RuntimeError")
