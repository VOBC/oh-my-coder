# Web 界面预览

> 本文从 README.md 迁移而来。

## 🌐 Web 界面预览

启动后访问 **http://localhost:8000**：

> 📸 截图位置：`docs/screenshots/`（运行后请添加 `web-ui.png` 和 `cli-demo.png`）

| 功能 | 说明 |
|------|------|
| 🎨 **可视化工作流** | 实时显示 Explore → Analyst → Architect → Executor → Verifier 流水线动画 |
| ⚡ **SSE 实时推送** | 无轮询，任务进度毫秒级更新 |
| 🤝 **Agent 协作 HUD** | Dashboard 右侧实时面板：活跃（红点）+ 已完成（绿勾）+ 待执行（灰），每 2 秒自动刷新 |
| 📋 **多视图输出** | 每个 Agent 的输出独立标签页，随时切换 |
| 📊 **成本统计** | Token 消耗、执行时间、步骤完成情况 |
| 🌙 **深色模式** | 明暗主题一键切换 |
| 💡 **示例任务** | 内置 4 种任务模板，一键填入 |

### API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/execute` | 异步执行（SSE 实时推送） |
| `POST` | `/api/execute-sync` | 同步执行（直接返回结果） |
| `GET` | `/api/tasks` | 列出所有任务 |
| `GET` | `/api/tasks/{id}` | 获取任务详情 |
| `GET` | `/sse/execute/{id}` | SSE 流，接收实时进度 |
| `GET` | `/api/agent/live` | SSE 流，多 Agent 协作状态实时推送 |
| `GET` | `/health` | 健康检查 |

### curl 调用示例

```bash
# 异步执行（带 SSE 进度）
curl -X POST http://localhost:8000/api/execute \
  -H "Content-Type: application/json" \
  -d '{"task": "实现一个 REST API", "workflow": "build"}'

# 同步执行（直接返回）
curl -X POST http://localhost:8000/api/execute-sync \
  -H "Content-Type: application/json" \
  -d '{"task": "审查代码质量", "workflow": "review"}'
```

---

