"""
OpenAPI 规范

提供标准的 API 文档和 Swagger UI。
"""

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

# API 版本
API_VERSION = "1.0.0"


def custom_openapi(app: FastAPI) -> dict:
    """
    自定义 OpenAPI 规范

    Args:
        app: FastAPI 应用实例

    Returns:
        OpenAPI 规范字典
    """

    def generate() -> dict:
        if app.openapi_schema:
            return app.openapi_schema

        openapi_schema = get_openapi(
            title="Oh My Coder API",
            version=API_VERSION,
            description="""
## 多智能体 AI 编程助手

Oh My Coder 是一个强大的多智能体 AI 编程系统，支持：
- 🤖 **18 个专业 Agent** - 规划、架构、编码、测试、审查等
- 🌐 **11 个国产大模型** - DeepSeek、通义千问、文心一言等
- 🔄 **智能工作流** - 预定义模板 + 自定义流程
- 📊 **任务历史追踪** - 完整的执行记录和回放

### 认证方式

所有 API 请求需要通过以下方式认证：

1. **API Key**: 在请求头添加 `X-API-Key`
2. **Bearer Token**: 在请求头添加 `Authorization: Bearer <token>`

### 速率限制

- 默认: 100 请求/分钟
- 执行任务: 10 并发

### 错误处理

所有错误返回标准格式：

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "错误描述",
    "details": {}
  }
}
```
            """,
            routes=app.routes,
            tags=[
                {
                    "name": "execute",
                    "description": "任务执行相关 API",
                },
                {
                    "name": "history",
                    "description": "历史记录管理",
                },
                {
                    "name": "agents",
                    "description": "Agent 状态管理",
                },
                {
                    "name": "templates",
                    "description": "工作流模板管理",
                },
                {
                    "name": "plugins",
                    "description": "插件系统管理",
                },
            ],
        )

        # 添加安全定义
        openapi_schema["components"]["securitySchemes"] = {
            "ApiKeyAuth": {
                "type": "apiKey",
                "in": "header",
                "name": "X-API-Key",
            },
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
            },
        }

        # 全局安全要求
        openapi_schema["security"] = [{"ApiKeyAuth": []}, {"BearerAuth": []}]

        # 添加服务器信息
        openapi_schema["servers"] = [
            {
                "url": "http://localhost:8000",
                "description": "本地开发服务器",
            },
            {
                "url": "https://api.ohmycoder.com",
                "description": "生产服务器",
            },
        ]

        # 添加外部文档
        openapi_schema["externalDocs"] = {
            "url": "https://github.com/VOBC/oh-my-coder/blob/main/docs/API.md",
            "description": "完整 API 文档",
        }

        app.openapi_schema = openapi_schema
        return app.openapi_schema

    return generate()


# API 响应模型
OPENAPI_RESPONSES = {
    "400": {
        "description": "请求参数错误",
        "content": {
            "application/json": {
                "example": {
                    "error": {
                        "code": "BAD_REQUEST",
                        "message": "缺少必要参数",
                        "details": {"field": "task"},
                    }
                }
            }
        },
    },
    "401": {
        "description": "认证失败",
        "content": {
            "application/json": {
                "example": {
                    "error": {
                        "code": "UNAUTHORIZED",
                        "message": "API Key 无效",
                    }
                }
            }
        },
    },
    "429": {
        "description": "请求过于频繁",
        "content": {
            "application/json": {
                "example": {
                    "error": {
                        "code": "RATE_LIMIT",
                        "message": "请求超过速率限制",
                        "details": {"retry_after": 60},
                    }
                }
            }
        },
    },
    "500": {
        "description": "服务器内部错误",
        "content": {
            "application/json": {
                "example": {
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": "服务器内部错误",
                    }
                }
            }
        },
    },
}


# API 示例
OPENAPI_EXAMPLES = {
    "execute_request": {
        "summary": "执行开发任务",
        "value": {
            "task": "实现用户登录功能，包括表单验证和错误处理",
            "project_path": "/Users/user/projects/myapp",
            "model": "deepseek",
            "workflow": "build",
        },
    },
    "execute_response": {
        "summary": "任务启动响应",
        "value": {
            "status": "started",
            "task_id": "task-abc123",
            "message": "任务已启动，请通过 SSE 连接获取进度",
            "sse_url": "/sse/execute/task-abc123",
        },
    },
    "history_list": {
        "summary": "历史记录列表",
        "value": {
            "records": [
                {
                    "task_id": "task-abc123",
                    "task": "实现用户登录功能",
                    "workflow": "build",
                    "status": "completed",
                    "started_at": "2024-01-15T10:30:00",
                    "completed_at": "2024-01-15T10:45:00",
                    "stats": {
                        "total_tokens": 15000,
                        "execution_time": 900,
                    },
                }
            ],
            "pagination": {"total": 100, "limit": 50, "offset": 0},
        },
    },
    "agent_status": {
        "summary": "Agent 状态",
        "value": {
            "agents": [
                {
                    "name": "Planner",
                    "status": "idle",
                    "channel": "BUILD",
                    "level": "MEDIUM",
                    "description": "规划开发计划",
                },
                {
                    "name": "Executor",
                    "status": "running",
                    "current_task": "生成登录表单代码",
                    "progress": 75,
                    "channel": "BUILD",
                    "level": "LOW",
                },
            ]
        },
    },
}
