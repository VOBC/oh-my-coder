# HTTP API

## 概览

Web 服务默认端口 `8000`，启动方式：

```bash
python -m src.web.app
# 或
python -m uvicorn src.web.app:app --reload
```

## 端点

### `POST /api/execute`

执行任务。

```bash
curl -X POST http://localhost:8000/api/execute \
  -H "Content-Type: application/json" \
  -d '{"task": "实现一个 REST API", "mode": "auto"}'
```

Response:

```json
{
  "workflow_id": "wf_abc123",
  "status": "completed",
  "result": {...}
}
```

### `GET /api/status/{workflow_id}`

查询任务状态。

```bash
curl http://localhost:8000/api/status/wf_abc123
```

### `GET /api/agent/live`

SSE 流，实时推送 Agent 协作状态。

```bash
curl -N http://localhost:8000/api/agent/live
```

### `GET /api/teams`

列出团队。

```bash
curl http://localhost:8000/api/teams
```

### `POST /api/teams`

创建团队。

```bash
curl -X POST http://localhost:8000/api/teams \
  -H "Content-Type: application/json" \
  -d '{"name": "my-team", "description": "我的团队"}'
```

### `GET /api/teams/{team_id}/stats`

团队统计。

```bash
curl "http://localhost:8000/api/teams/my-team/stats?period=week"
```

### `GET /api/teams/{team_id}/user/{user_id}/stats`

用户统计。

```bash
curl "http://localhost:8000/api/teams/my-team/user/zhangsan/stats?period=month"
```

### `GET /docs`

Swagger UI（自动生成）。

```bash
open http://localhost:8000/docs
```
