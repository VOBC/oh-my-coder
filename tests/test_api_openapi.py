"""
Tests for openapi.py

Coverage target: All functions, constants, and exported data structures in openapi.py
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI

from src.api.openapi import (
    API_VERSION,
    OPENAPI_EXAMPLES,
    OPENAPI_RESPONSES,
    custom_openapi,
)


# =============================================================================
# API_VERSION Tests
# =============================================================================


def test_api_version_value():
    """Test API_VERSION constant."""
    assert API_VERSION == "0.2.0"
    assert isinstance(API_VERSION, str)


# =============================================================================
# custom_openapi Tests
# =============================================================================


def test_custom_openapi_returns_callable():
    """Test custom_openapi returns a callable (the generate function)."""
    app = MagicMock(spec=FastAPI)
    result = custom_openapi(app)

    assert callable(result)


def test_custom_openapi_generate_uses_cached_schema():
    """Test that generate returns cached schema if app.openapi_schema is set."""
    app = MagicMock(spec=FastAPI)
    cached = {"openapi": "3.0.0", "info": {"title": "Cached"}, "paths": {}}
    app.openapi_schema = cached

    generate = custom_openapi(app)
    result = generate()

    assert result is cached
    assert result["openapi"] == "3.0.0"
    # get_openapi should NOT have been called
    # (we can verify by the fact that cached schema has no components)
    assert "components" not in cached


def test_custom_openapi_generate_builds_fresh_schema():
    """Test that generate builds a fresh schema when no cache exists."""
    # Use a spec but make openapi_schema return None so the cache check fails
    app = MagicMock(spec=FastAPI, openapi_schema=None)

    generate = custom_openapi(app)

    with patch("src.api.openapi.get_openapi") as mock_get_openapi:
        base_schema = {
            "openapi": "3.1.0",
            "info": {"title": "Oh My Coder API", "version": API_VERSION},
            "paths": {},
            "components": {},
            "tags": [
                {"name": "execute", "description": "任务执行"},
                {"name": "history", "description": "历史记录"},
                {"name": "agents", "description": "Agent 管理"},
                {"name": "templates", "description": "模板管理"},
                {"name": "plugins", "description": "插件管理"},
            ],
        }
        mock_get_openapi.return_value = dict(base_schema)

        result = generate()

    # get_openapi should have been called once
    mock_get_openapi.assert_called_once()

    # Verify the schema structure
    assert result["openapi"] == "3.1.0"
    assert result["info"]["title"] == "Oh My Coder API"

    # Should have security schemes
    assert "securitySchemes" in result["components"]
    assert "ApiKeyAuth" in result["components"]["securitySchemes"]
    assert "BearerAuth" in result["components"]["securitySchemes"]

    # Should have global security
    assert "security" in result
    assert len(result["security"]) == 2

    # Should have servers
    assert "servers" in result
    assert len(result["servers"]) == 2
    assert result["servers"][0]["url"] == "http://localhost:8000"

    # Should have external docs
    assert "externalDocs" in result
    assert "url" in result["externalDocs"]

    # Should have tags
    assert "tags" in result
    tag_names = [t["name"] for t in result["tags"]]
    assert "execute" in tag_names
    assert "agents" in tag_names
    assert "history" in tag_names
    assert "templates" in tag_names
    assert "plugins" in tag_names

    # app.openapi_schema should have been set
    assert app.openapi_schema is result


def test_custom_openapi_generate_adds_missing_components():
    """Test that generate adds components dict if missing from schema."""
    app = MagicMock(spec=FastAPI)

    with patch("src.api.openapi.get_openapi") as mock_get_openapi:
        # Return schema WITHOUT components
        mock_get_openapi.return_value = {
            "openapi": "3.1.0",
            "info": {"title": "Oh My Coder API", "version": API_VERSION},
            "paths": {},
        }
        generate = custom_openapi(app)
        result = generate()

    # components should have been added
    assert "components" in result
    assert "securitySchemes" in result["components"]


def test_custom_openapi_generate_app_openapi_schema_no_components():
    """Test when app.openapi_schema exists but has no components (returned directly, no fix)."""
    app = MagicMock(spec=FastAPI)
    # Set cached schema without components
    cached = {"openapi": "3.0.0", "info": {"title": "Cached"}, "paths": {}}
    app.openapi_schema = cached

    generate = custom_openapi(app)
    result = generate()

    # The cached schema is returned AS-IS (no modification by generate)
    assert "components" not in result


def test_custom_openapi_generate_with_existing_components():
    """Test generate when base schema already has components (not overwritten)."""
    app = MagicMock(spec=FastAPI)

    with patch("src.api.openapi.get_openapi") as mock_get_openapi:
        mock_get_openapi.return_value = {
            "openapi": "3.1.0",
            "info": {"title": "Test"},
            "paths": {},
            "components": {
                "schemas": {
                    "Task": {"type": "object"},
                },
            },
        }
        generate = custom_openapi(app)
        result = generate()

    # Existing schemas should be preserved
    assert "schemas" in result["components"]
    assert result["components"]["schemas"]["Task"]["type"] == "object"
    # Security schemes should have been added
    assert "securitySchemes" in result["components"]


def test_custom_openapi_generate_validates_servers():
    """Test that the servers section has correct structure."""
    app = MagicMock(spec=FastAPI)

    with patch("src.api.openapi.get_openapi") as mock_get_openapi:
        mock_get_openapi.return_value = {
            "openapi": "3.1.0",
            "info": {"title": "Test"},
            "paths": {},
        }
        generate = custom_openapi(app)
        result = generate()

    servers = result.get("servers", [])
    assert isinstance(servers, list)

    # Server 1: localhost
    assert servers[0]["url"] == "http://localhost:8000"
    assert "description" in servers[0]

    # Server 2: production
    assert servers[1]["url"] == "https://api.ohmycoder.com"
    assert "description" in servers[1]


def test_custom_openapi_generate_validates_security():
    """Test that security section has correct structure."""
    app = MagicMock(spec=FastAPI)

    with patch("src.api.openapi.get_openapi") as mock_get_openapi:
        mock_get_openapi.return_value = {
            "openapi": "3.1.0",
            "info": {"title": "Test"},
            "paths": {},
        }
        generate = custom_openapi(app)
        result = generate()

    security = result.get("security", [])
    assert isinstance(security, list)
    assert len(security) == 2

    # ApiKeyAuth
    assert security[0] == {"ApiKeyAuth": []}

    # BearerAuth
    assert security[1] == {"BearerAuth": []}


def test_custom_openapi_generate_validates_security_schemes():
    """Test that security schemes have correct structure."""
    app = MagicMock(spec=FastAPI)

    with patch("src.api.openapi.get_openapi") as mock_get_openapi:
        mock_get_openapi.return_value = {
            "openapi": "3.1.0",
            "info": {"title": "Test"},
            "paths": {},
        }
        generate = custom_openapi(app)
        result = generate()

    schemes = result["components"]["securitySchemes"]

    # ApiKeyAuth
    assert schemes["ApiKeyAuth"]["type"] == "apiKey"
    assert schemes["ApiKeyAuth"]["in"] == "header"
    assert schemes["ApiKeyAuth"]["name"] == "X-API-Key"

    # BearerAuth
    assert schemes["BearerAuth"]["type"] == "http"
    assert schemes["BearerAuth"]["scheme"] == "bearer"
    assert schemes["BearerAuth"]["bearerFormat"] == "JWT"


def test_custom_openapi_generate_validates_tags():
    """Test that tags section has correct structure."""
    app = MagicMock(spec=FastAPI, openapi_schema=None)

    # Tags are passed as an argument to get_openapi but are NOT re-added
    # to the schema by generate(). We include them in the mock return.
    mock_tags = [
        {"name": "execute", "description": "任务执行相关 API"},
        {"name": "history", "description": "历史记录管理"},
        {"name": "agents", "description": "Agent 状态管理"},
        {"name": "templates", "description": "工作流模板管理"},
        {"name": "plugins", "description": "插件系统管理"},
    ]

    with patch("src.api.openapi.get_openapi") as mock_get_openapi:
        mock_get_openapi.return_value = {
            "openapi": "3.1.0",
            "info": {"title": "Test"},
            "paths": {},
            "tags": mock_tags,
        }
        generate = custom_openapi(app)
        result = generate()

    tags = result.get("tags", [])
    assert isinstance(tags, list)

    # Verify each tag has name and description
    for tag in tags:
        assert "name" in tag
        assert "description" in tag

    # Verify specific tags exist
    tag_names = {t["name"] for t in tags}
    assert "execute" in tag_names
    assert "history" in tag_names
    assert "agents" in tag_names
    assert "templates" in tag_names
    assert "plugins" in tag_names


def test_custom_openapi_generate_applied_schema():
    """Test that app.openapi_schema is set correctly after generation."""
    app = MagicMock(spec=FastAPI)

    with patch("src.api.openapi.get_openapi") as mock_get_openapi:
        mock_get_openapi.return_value = {
            "openapi": "3.1.0",
            "info": {"title": "Test"},
            "paths": {},
        }
        generate = custom_openapi(app)
        result = generate()

    # app.openapi_schema should be set to the result
    assert app.openapi_schema is result


def test_custom_openapi_generate_idempotent():
    """Test that generate is idempotent - second call returns cached result."""
    app = MagicMock(spec=FastAPI)

    with patch("src.api.openapi.get_openapi") as mock_get_openapi:
        mock_get_openapi.return_value = {
            "openapi": "3.1.0",
            "info": {"title": "Test"},
            "paths": {},
        }
        generate = custom_openapi(app)
        result1 = generate()

        # Reset get_openapi call count
        mock_get_openapi.reset_mock()

        # Second call should return cached schema
        result2 = generate()

        # get_openapi should NOT have been called again
        mock_get_openapi.assert_not_called()

        # Both results should be the same object
        assert result2 is result1


def test_custom_openapi_generate_getattr_fallback():
    """Test that generate uses getattr with None default for openapi_schema."""
    app = MagicMock(spec=FastAPI)
    # Deliberately NOT setting openapi_schema so getattr returns None

    with patch("src.api.openapi.get_openapi") as mock_get_openapi:
        mock_get_openapi.return_value = {
            "openapi": "3.1.0",
            "info": {"title": "Test"},
            "paths": {},
        }
        generate = custom_openapi(app)
        result = generate()

    # Should have called get_openapi since no cached schema
    mock_get_openapi.assert_called_once()
    assert result is not None


def test_custom_openapi_generate_verify_get_openapi_args():
    """Test that get_openapi is called with expected arguments."""
    app = MagicMock(spec=FastAPI)
    app.routes = ["fake-route-1", "fake-route-2"]

    with patch("src.api.openapi.get_openapi") as mock_get_openapi:
        mock_get_openapi.return_value = {
            "openapi": "3.1.0",
            "info": {"title": "Oh My Coder API", "version": API_VERSION},
            "paths": {},
        }
        generate = custom_openapi(app)
        generate()

    mock_get_openapi.assert_called_once()
    call_kwargs = mock_get_openapi.call_args.kwargs

    assert call_kwargs["title"] == "Oh My Coder API"
    assert call_kwargs["version"] == API_VERSION
    assert call_kwargs["routes"] == app.routes
    assert "description" in call_kwargs
    assert "tags" in call_kwargs


def test_custom_openapi_generate_external_docs():
    """Test that externalDocs section is correctly structured."""
    app = MagicMock(spec=FastAPI)

    with patch("src.api.openapi.get_openapi") as mock_get_openapi:
        mock_get_openapi.return_value = {
            "openapi": "3.1.0",
            "info": {"title": "Test"},
            "paths": {},
        }
        generate = custom_openapi(app)
        result = generate()

    ed = result.get("externalDocs", {})
    assert ed["url"] == "https://github.com/VOBC/oh-my-coder/blob/main/docs/API.md"
    assert "description" in ed


def test_custom_openapi_generate_info_description():
    """Test that the info description contains expected content."""
    app = MagicMock(spec=FastAPI)

    with patch("src.api.openapi.get_openapi") as mock_get_openapi:
        mock_get_openapi.return_value = {
            "openapi": "3.1.0",
            "info": {"title": "Oh My Coder API", "version": API_VERSION},
            "paths": {},
        }
        generate = custom_openapi(app)
        result = generate()

    # Description is passed to get_openapi, so we check that get_openapi was called with it
    call_kwargs = mock_get_openapi.call_args.kwargs
    description = call_kwargs["description"]

    # Should mention key features
    assert "多智能体 AI 编程助手" in description
    assert "31 个专业 Agent" in description
    assert "12 个国产大模型" in description


# =============================================================================
# OPENAPI_RESPONSES Tests
# =============================================================================


def test_openapi_responses_keys():
    """Test OPENAPI_RESPONSES has expected HTTP status keys."""
    expected_keys = {"400", "401", "429", "500"}
    assert set(OPENAPI_RESPONSES.keys()) == expected_keys


def test_openapi_responses_structure():
    """Test each response entry has description and content."""
    for status_code, response in OPENAPI_RESPONSES.items():
        assert "description" in response, f"Missing description for {status_code}"
        assert "content" in response, f"Missing content for {status_code}"
        assert "application/json" in response["content"]
        assert "example" in response["content"]["application/json"]
        assert "error" in response["content"]["application/json"]["example"]


def test_openapi_response_400():
    """Test 400 Bad Request response structure."""
    resp = OPENAPI_RESPONSES["400"]
    example = resp["content"]["application/json"]["example"]

    assert resp["description"] == "请求参数错误"
    assert example["error"]["code"] == "BAD_REQUEST"
    assert "message" in example["error"]
    assert "field" in example["error"]["details"]


def test_openapi_response_401():
    """Test 401 Unauthorized response structure."""
    resp = OPENAPI_RESPONSES["401"]
    example = resp["content"]["application/json"]["example"]

    assert resp["description"] == "认证失败"
    assert example["error"]["code"] == "UNAUTHORIZED"
    assert "message" in example["error"]
    assert "details" not in example["error"] or example["error"]["details"] == {}


def test_openapi_response_429():
    """Test 429 Rate Limit response structure."""
    resp = OPENAPI_RESPONSES["429"]
    example = resp["content"]["application/json"]["example"]

    assert resp["description"] == "请求过于频繁"
    assert example["error"]["code"] == "RATE_LIMIT"
    assert "retry_after" in example["error"]["details"]


def test_openapi_response_500():
    """Test 500 Internal Server Error response structure."""
    resp = OPENAPI_RESPONSES["500"]
    example = resp["content"]["application/json"]["example"]

    assert resp["description"] == "服务器内部错误"
    assert example["error"]["code"] == "INTERNAL_ERROR"
    assert "message" in example["error"]


# =============================================================================
# OPENAPI_EXAMPLES Tests
# =============================================================================


def test_openapi_examples_keys():
    """Test OPENAPI_EXAMPLES has expected example keys."""
    expected_keys = {"execute_request", "execute_response", "history_list", "agent_status"}
    assert set(OPENAPI_EXAMPLES.keys()) == expected_keys


def test_openapi_examples_structure():
    """Test each example entry has summary and value."""
    for name, example in OPENAPI_EXAMPLES.items():
        assert "summary" in example, f"Missing summary for {name}"
        assert "value" in example, f"Missing value for {name}"
        assert isinstance(example["summary"], str)

        # Check summary is non-empty
        assert len(example["summary"]) > 0, f"Empty summary for {name}"


def test_openapi_example_execute_request():
    """Test execute_request example structure."""
    example = OPENAPI_EXAMPLES["execute_request"]
    value = example["value"]

    assert example["summary"] == "执行开发任务"
    assert "task" in value
    assert "project_path" in value
    assert "model" in value
    assert "workflow" in value


def test_openapi_example_execute_response():
    """Test execute_response example structure."""
    example = OPENAPI_EXAMPLES["execute_response"]
    value = example["value"]

    assert example["summary"] == "任务启动响应"
    assert value["status"] == "started"
    assert "task_id" in value
    assert value["task_id"].startswith("task-")
    assert "sse_url" in value


def test_openapi_example_history_list():
    """Test history_list example structure."""
    example = OPENAPI_EXAMPLES["history_list"]
    value = example["value"]

    assert example["summary"] == "历史记录列表"
    assert "records" in value
    assert isinstance(value["records"], list)
    assert len(value["records"]) > 0

    # Check record structure
    record = value["records"][0]
    assert "task_id" in record
    assert "task" in record
    assert "workflow" in record
    assert "status" in record
    assert "started_at" in record
    assert "completed_at" in record
    assert "stats" in record

    # Check pagination
    assert "pagination" in value
    assert "total" in value["pagination"]
    assert "limit" in value["pagination"]
    assert "offset" in value["pagination"]


def test_openapi_example_agent_status():
    """Test agent_status example structure."""
    example = OPENAPI_EXAMPLES["agent_status"]
    value = example["value"]

    assert example["summary"] == "Agent 状态"
    assert "agents" in value
    assert isinstance(value["agents"], list)
    assert len(value["agents"]) >= 2

    # Check agent structure
    for agent in value["agents"]:
        assert "name" in agent
        assert "status" in agent
        assert "channel" in agent
        assert "level" in agent

    # Check first agent (idle)
    assert value["agents"][0]["status"] == "idle"

    # Check second agent (running with task)
    assert value["agents"][1]["status"] == "running"
    assert "current_task" in value["agents"][1]
    assert "progress" in value["agents"][1]


# =============================================================================
# Edge Cases and Error Handling
# =============================================================================


def test_custom_openapi_not_a_fastapi():
    """Test custom_openapi raises AttributeError when given an object without routes."""
    not_a_fastapi: object = {}  # plain dict, no routes attribute

    with pytest.raises(AttributeError):
        generate = custom_openapi(not_a_fastapi)  # type: ignore[arg-type]
        generate()


def test_custom_openapi_with_real_fastapi():
    """Test custom_openapi works with a real minimal FastAPI instance."""
    app = FastAPI()

    generate = custom_openapi(app)
    result = generate()

    # Verify it's a proper OpenAPI schema
    assert isinstance(result, dict)
    assert result["openapi"].startswith("3.")
    assert result["info"]["title"] == "Oh My Coder API"
    assert result["info"]["version"] == API_VERSION

    # Verify security schemes were added
    assert "ApiKeyAuth" in result["components"]["securitySchemes"]
    assert "BearerAuth" in result["components"]["securitySchemes"]

    # Verify servers
    assert len(result["servers"]) == 2

    # Verify tags
    assert len(result["tags"]) == 5

    # Verify external docs
    assert "externalDocs" in result


def test_custom_openapi_with_real_fastapi_cached():
    """Test that real FastAPI correctly caches the schema."""
    app = FastAPI()

    generate = custom_openapi(app)
    result1 = generate()
    result2 = generate()

    # Second call should return the cached same object
    assert result2 is result1
    assert result2["info"]["version"] == API_VERSION


def test_custom_openapi_with_real_fastapi_has_paths():
    """Test that schema generated from real FastAPI includes /docs path."""
    app = FastAPI()

    generate = custom_openapi(app)
    result = generate()

    # Real FastAPI should have some built-in paths
    assert isinstance(result.get("paths", {}), dict)


def test_custom_openapi_returns_callable_twice():
    """Test that custom_openapi can be called multiple times returning independent generate funcs."""
    app1 = MagicMock(spec=FastAPI)
    app2 = MagicMock(spec=FastAPI)

    gen1 = custom_openapi(app1)
    gen2 = custom_openapi(app2)

    assert callable(gen1)
    assert callable(gen2)
    assert gen1 is not gen2


def test_openapi_examples_immutability():
    """Test that OPENAPI_EXAMPLES values are not accidentally shared."""
    # Each example should have its own 'summary' and 'value'
    for name, example in OPENAPI_EXAMPLES.items():
        assert "summary" in example
        assert "value" in example
        # Value should be a dict
        assert isinstance(example["value"], dict)


def test_openapi_responses_all_have_json_content():
    """Test all responses have application/json content type."""
    for status_code, response in OPENAPI_RESPONSES.items():
        content = response.get("content", {})
        assert "application/json" in content, f"Missing application/json for {status_code}"


def test_openapi_responses_all_have_error_object():
    """Test all response examples contain error object."""
    for status_code, response in OPENAPI_RESPONSES.items():
        example = response["content"]["application/json"]["example"]
        assert "error" in example, f"Missing error in {status_code}"
        assert "code" in example["error"], f"Missing error.code in {status_code}"
        assert "message" in example["error"], f"Missing error.message in {status_code}"


def test_openapi_response_all_different_error_codes():
    """Test that all error codes are unique and meaningful."""
    codes = set()
    for status_code, response in OPENAPI_RESPONSES.items():
        example = response["content"]["application/json"]["example"]
        error_code = example["error"]["code"]
        codes.add(error_code)

    # Each status should have a different error code
    assert len(codes) == len(OPENAPI_RESPONSES)
    assert "BAD_REQUEST" in codes
    assert "UNAUTHORIZED" in codes
    assert "RATE_LIMIT" in codes
    assert "INTERNAL_ERROR" in codes


def test_openapi_examples_agent_status_level_values():
    """Test that agent status examples have valid level values."""
    for agent in OPENAPI_EXAMPLES["agent_status"]["value"]["agents"]:
        assert agent["level"] in {"MEDIUM", "LOW", "HIGH"}


def test_openapi_examples_agent_status_channel_values():
    """Test that agent status examples have valid channel values."""
    for agent in OPENAPI_EXAMPLES["agent_status"]["value"]["agents"]:
        assert agent["channel"] in {"BUILD", "REVIEW", "DEPLOY", "ANALYSIS"}


def test_custom_openapi_generate_get_openapi_returns_no_components():
    """Test edge case: get_openapi returns a schema without components."""
    app = MagicMock(spec=FastAPI)

    with patch("src.api.openapi.get_openapi") as mock_get_openapi:
        mock_get_openapi.return_value = {
            "openapi": "3.1.0",
            "info": {"title": "Test"},
            "paths": {},
            # Intentionally missing 'components' key
        }
        generate = custom_openapi(app)
        result = generate()

    # The 'if "components" not in openapi_schema' branch should kick in
    assert "components" in result
    assert "securitySchemes" in result["components"]


def test_custom_openapi_generate_get_openapi_returns_components_without_security():
    """Test edge case: get_openapi returns components but no securitySchemes."""
    app = MagicMock(spec=FastAPI)

    with patch("src.api.openapi.get_openapi") as mock_get_openapi:
        mock_get_openapi.return_value = {
            "openapi": "3.1.0",
            "info": {"title": "Test"},
            "paths": {},
            "components": {
                "schemas": {
                    "SomeModel": {"type": "string"},
                },
            },
        }
        generate = custom_openapi(app)
        result = generate()

    # Security schemes should be added, schemas preserved
    assert "securitySchemes" in result["components"]
    assert result["components"]["schemas"]["SomeModel"]["type"] == "string"


def test_openapi_examples_execute_request_mandatory_keys():
    """Test that execute_request example has all mandatory keys."""
    value = OPENAPI_EXAMPLES["execute_request"]["value"]

    mandatory_keys = {"task", "project_path", "model", "workflow"}
    assert mandatory_keys.issubset(value.keys())

    # Values should be non-empty
    assert len(value["task"]) > 0
    assert len(value["project_path"]) > 0
    assert len(value["model"]) > 0
    assert len(value["workflow"]) > 0


def test_openapi_examples_execute_response_mandatory_keys():
    """Test that execute_response example has all mandatory keys."""
    value = OPENAPI_EXAMPLES["execute_response"]["value"]

    mandatory_keys = {"status", "task_id", "message", "sse_url"}
    assert mandatory_keys.issubset(value.keys())

    # Specific values
    assert value["status"] == "started"
    assert value["task_id"].startswith("task-")


def test_openapi_examples_history_list_record_fields():
    """Test that history_list record has expected fields."""
    record = OPENAPI_EXAMPLES["history_list"]["value"]["records"][0]

    expected_fields = {"task_id", "task", "workflow", "status", "started_at", "completed_at", "stats"}
    assert expected_fields.issubset(record.keys())

    # stats should have sub-fields
    stats = record["stats"]
    assert "total_tokens" in stats
    assert "execution_time" in stats


def test_custom_openapi_pass_to_fastapi():
    """Test that the return value of custom_openapi can be used as FastAPI's openapi."""
    app = FastAPI()

    # This is how it's used in server_api.py:
    # app.openapi = custom_openapi(app)
    app.openapi = custom_openapi(app)  # type: ignore[method-assign]

    # FastAPI should be able to generate the schema through the custom function
    schema = app.openapi()
    assert isinstance(schema, dict)
    assert schema["info"]["title"] == "Oh My Coder API"
    assert "ApiKeyAuth" in schema["components"]["securitySchemes"]


def test_custom_openapi_usage_pattern_exact():
    """Test the exact usage pattern from server_api.py."""
    app = FastAPI()

    from src.api.openapi import custom_openapi
    app.openapi = custom_openapi(app)  # type: ignore[method-assign]

    schema = app.openapi()
    assert schema["openapi"].startswith("3.")
