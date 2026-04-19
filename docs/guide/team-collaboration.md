# 团队协作功能

Oh My Coder 支持团队协作，允许多人共享任务状态、查看团队统计和接收通知。

## 📋 功能概览

- **多人共享任务状态**：团队成员可以查看所有任务的状态
- **团队使用统计**：记录和分析团队的使用情况
- **消息通知**：实时推送任务完成、失败等通知

---

## 🚀 快速开始

### 1. 创建团队

```bash
curl -X POST http://localhost:8000/api/team/create \
  -H "Content-Type: application/json" \
  -d '{
    "name": "我的开发团队",
    "owner_id": "user_001",
    "description": "产品开发团队"
  }'
```

响应：

```json
{
  "team_id": "team_abc123",
  "name": "我的开发团队",
  "owner_id": "user_001",
  "invite_code": "X7KJ9L",
  "member_count": 1
}
```

### 2. 加入团队

分享邀请码给团队成员：

```bash
curl -X POST http://localhost:8000/api/team/join \
  -H "Content-Type: application/json" \
  -d '{
    "invite_code": "X7KJ9L",
    "user_id": "user_002",
    "display_name": "张三"
  }'
```

### 3. 创建团队任务

```bash
curl -X POST http://localhost:8000/api/team/task/create \
  -H "Content-Type: application/json" \
  -d '{
    "team_id": "team_abc123",
    "creator_id": "user_001",
    "title": "实现用户登录",
    "workflow": "build",
    "model": "deepseek"
  }'
```

---

## 📊 团队统计

### 查询团队统计

```bash
curl "http://localhost:8000/api/team/team_abc123/stats?period=week"
```

响应：

```json
{
  "team_id": "team_abc123",
  "period": "week",
  "total_tasks": 156,
  "successful_tasks": 142,
  "failed_tasks": 14,
  "success_rate": 91.0,
  "total_tokens": 2300000,
  "total_cost": 23.0,
  "avg_execution_time": 45.2,
  "top_models": [
    {"model": "deepseek", "count": 80, "tokens": 1200000},
    {"model": "tongyi", "count": 50, "tokens": 800000}
  ],
  "top_users": [
    {"user_id": "user_001", "count": 60, "cost": 9.0},
    {"user_id": "user_002", "count": 45, "cost": 7.5}
  ]
}
```

### 统计周期

| 参数值 | 说明 |
|--------|------|
| `day` | 最近 24 小时 |
| `week` | 最近 7 天 |
| `month` | 最近 30 天 |

---

## 🔔 消息通知

### 通知类型

| 类型 | 说明 |
|------|------|
| `task_created` | 新任务创建 |
| `task_completed` | 任务执行完成 |
| `task_failed` | 任务执行失败 |
| `team_broadcast` | 团队广播消息 |
| `user_mention` | 用户提及 |

### 获取通知

```bash
curl "http://localhost:8000/api/team/team_abc123/notifications"
```

### WebSocket 实时推送

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/team_abc123/user_001');

ws.onmessage = (event) => {
  const notification = JSON.parse(event.data);
  console.log('收到通知:', notification);
};
```

### 广播消息

```bash
curl -X POST http://localhost:8000/api/team/broadcast \
  -H "Content-Type: application/json" \
  -d '{
    "team_id": "team_abc123",
    "title": "系统维护通知",
    "message": "今晚 10 点进行系统维护",
    "priority": "high"
  }'
```

---

## 🔐 权限管理

### 成员角色

| 角色 | 权限 |
|------|------|
| `owner` | 所有权限，包括删除团队、管理成员 |
| `admin` | 管理任务、邀请成员 |
| `member` | 创建任务、查看统计 |

### 检查权限

```python
from src.team import team_auth, MemberRole

# 检查用户是否有管理员权限
has_permission = team_auth.check_permission(
    user_id="user_002",
    team_id="team_abc123",
    required_role=MemberRole.ADMIN
)
```

### 更新成员角色

```bash
curl -X POST "http://localhost:8000/api/team/team_abc123/update-role" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_002",
    "new_role": "admin",
    "requester_id": "user_001"
  }'
```

---

## 🗄️ 数据存储

### Redis（任务状态）

团队任务状态存储在 Redis 中，支持：
- 任务创建/更新/删除
- 实时状态同步
- 任务订阅推送

启动 Redis：

```bash
docker run -d -p 6379:6379 redis:7-alpine
```

### SQLite（统计数据）

使用记录存储在 SQLite 数据库：
- 自动创建 `.omc/team_stats.db`
- 保留 30 天数据
- 支持按日/周/月统计

---

## 📡 API 参考

### 团队管理

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/team/create` | 创建团队 |
| POST | `/api/team/join` | 加入团队 |
| POST | `/api/team/leave` | 离开团队 |
| POST | `/api/team/delete` | 删除团队 |
| GET | `/api/team/{team_id}` | 获取团队信息 |
| GET | `/api/team/user/{user_id}` | 获取用户团队 |

### 任务同步

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/team/task/create` | 创建任务 |
| PUT | `/api/team/task/{task_id}/status` | 更新状态 |
| GET | `/api/team/task/{task_id}` | 获取任务 |
| GET | `/api/team/{team_id}/tasks` | 团队任务列表 |
| POST | `/api/team/task/{task_id}/subscribe` | 订阅任务 |

### 统计分析

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/team/usage/record` | 记录使用 |
| GET | `/api/team/{team_id}/stats` | 团队统计 |
| GET | `/api/team/{team_id}/user/{user_id}/stats` | 用户统计 |

### 消息通知

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/team/broadcast` | 广播消息 |
| GET | `/api/team/{team_id}/notifications` | 团队通知 |
| POST | `/api/team/notification/{id}/read` | 标记已读 |

---

## ❓ 常见问题

### Q: 如何重新生成邀请码？

```bash
curl -X POST "http://localhost:8000/api/team/team_abc123/regenerate-invite?requester_id=user_001"
```

### Q: 数据保留多长时间？

统计数据保留 30 天，任务状态保留在 Redis 中（可配置）。

### Q: 支持多少团队成员？

没有硬性限制，但建议单团队不超过 100 人。

---

## 🔧 高级配置

### 自定义 Redis 地址

```python
from src.team import TaskSync

task_sync = TaskSync(redis_url="redis://custom-host:6379")
await task_sync.connect()
```

### 自定义统计数据库路径

```python
from src.team import TeamStatistics

team_stats = TeamStatistics(db_path="/custom/path/stats.db")
```

### 注册自定义通知处理器

```python
from src.team import team_notifier, NotificationType

async def custom_handler(notification):
    # 发送邮件、短信等
    print(f"收到通知: {notification.title}")

team_notifier.register_handler(NotificationType.TASK_COMPLETED, custom_handler)
```
