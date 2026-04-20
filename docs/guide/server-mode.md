# Server 模式 API 文档

> 远程 AI 编程助手 REST API

## 启动服务

```bash
omc server start --port 8080
# 或设置 API Key（推荐生产环境）
omc server start --port 8080 --api-key your-secret-key
```

**API Key 认证**：设置后，所有请求需在 Header 中添加 `X-API-Key: your-secret-key`

---

## 接口列表

### `POST /api/v1/run` — 提交任务

**请求体：**
```json
{
  "prompt": "帮我写一个快速排序算法，用 Python",
  "metadata": {
    "language": "python",
    "workspace": "/path/to/project"
  }
}
```

**响应：**
```json
{
  "task_id": "a1b2c3d4e5f6",
  "status": "pending",
  "created_at": "2026-04-20T12:15:00",
  "prompt": "帮我写一个快速排序算法，用 Python",
  "metadata": {}
}
```

**字段说明：**
| 字段 | 类型 | 说明 |
|------|------|------|
| `task_id` | string | 任务唯一 ID，用于后续查询 |
| `status` | string | 任务状态：`pending` / `running` / `completed` / `failed` |

---

### `GET /api/v1/status/{task_id}` — 查询状态

**响应：**
```json
{
  "task_id": "a1b2c3d4e5f6",
  "status": "running",
  "created_at": "2026-04-20T12:15:00",
  "started_at": "2026-04-20T12:15:01",
  "completed_at": null,
  "execution_time": 0.0
}
```

---

### `GET /api/v1/result/{task_id}` — 获取结果

**成功响应（completed）：**
```json
{
  "task_id": "a1b2c3d4e5f6",
  "status": "completed",
  "result": {
    "output": "def quicksort(arr): ...",
    "status": "ok"
  },
  "error": null,
  "execution_time": 12.5,
  "completed_at": "2026-04-20T12:15:13"
}
```

**失败响应（failed）：**
```json
{
  "task_id": "a1b2c3d4e5f6",
  "status": "failed",
  "result": null,
  "error": "Agent execution failed: ...",
  "execution_time": 5.2,
  "completed_at": "2026-04-20T12:15:08"
}
```

---

### `GET /api/v1/tasks` — 列出任务

**查询参数：**
- `limit`（默认 50）：返回数量上限

**响应：**
```json
{
  "total": 12,
  "tasks": [
    {
      "task_id": "a1b2c3d4e5f6",
      "status": "completed",
      "created_at": "2026-04-20T12:15:00",
      "execution_time": 12.5,
      "prompt_preview": "帮我写一个快速排序算法..."
    }
  ]
}
```

---

### `DELETE /api/v1/tasks/{task_id}` — 删除任务

**响应：**
```json
{
  "task_id": "a1b2c3d4e5f6",
  "deleted": "true"
}
```

---

## 使用示例

### cURL

```bash
# 1. 启动任务
curl -X POST http://localhost:8080/api/v1/run \
  -H "Content-Type: application/json" \
  -d '{"prompt": "写一个斐波那契数列函数"}'

# 2. 查询状态
curl http://localhost:8080/api/v1/status/a1b2c3d4e5f6

# 3. 获取结果
curl http://localhost:8080/api/v1/result/a1b2c3d4e5f6
```

### 带认证

```bash
curl -X POST http://localhost:8080/api/v1/run \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-secret-key" \
  -d '{"prompt": "写一个斐波那契数列函数"}'
```

---

## 其他接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 服务健康检查 |
| `/health` | GET | 服务状态 |
| `/docs` | GET | Swagger UI（交互式文档）|
| `/redoc` | GET | ReDoc 文档 |

---

## 从手机调用

手机和电脑在同一局域网时：

```bash
# 电脑端
omc server start --port 8080 --host 0.0.0.0 --api-key your-key

# 手机端（替换 192.168.x.x 为电脑 IP）
curl -X POST http://192.168.x.x:8080/api/v1/run \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-key" \
  -d '{"prompt": "帮我解释这段代码"}'
```

查找电脑 IP：
- macOS: `ifconfig | grep "inet " | grep -v 127.0.0.1`
- Linux: `ip addr show`
- Windows: `ipconfig`
