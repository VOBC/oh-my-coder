# MCP Server

oh-my-coder 内置 MCP (Model Context Protocol) 支持，可作为 MCP Server 向 AI 模型提供上下文。

## 工作原理

```
oh-my-coder (MCP Server)
    │
    ├── Tools: run / explore / quest / checkpoint
    │
    ├── Resources: project structure / git history / agent states
    │
    └── Prompts: task templates / workflow guides
```

## 配置 MCP Client

在 Cursor / Claude Desktop 等 MCP Client 中配置：

```json
{
  "mcpServers": {
    "oh-my-coder": {
      "command": "python",
      "args": ["-m", "src.mcp.server"]
    }
  }
}
```

## 可用 Tools

| Tool | 说明 |
|------|------|
| `omc_run` | 执行开发任务 |
| `omc_explore` | 探索项目结构 |
| `omc_quest_start` | 启动后台任务 |
| `omc_quest_status` | 查看任务状态 |
| `omc_checkpoint_save` | 保存检查点 |
| `omc_agents` | 列出 Agent |

## 可用 Resources

| Resource | 说明 |
|----------|------|
| `project://structure` | 项目文件树 |
| `project://git-log` | 最近 git commit |
| `agent://active` | 当前运行中的 Agent |
