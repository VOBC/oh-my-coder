# CLI 命令参考

## 概览

```bash
omc [command] [options]
```

## 命令

### `omc explore`

探索项目结构。

```bash
omc explore <path>
```

### `omc run`

执行开发任务。

```bash
omc run "<task description>" [options]

Options:
  -m, --mode MODE   执行模式：auto / sequential / parallel（默认: auto）
  -y, --yes         自动确认所有操作
  -v, --verbose     详细输出
```

### `omc quest`

Quest Mode 后台任务管理。

```bash
# 启动异步任务
omc quest start "<task>"

# 查看任务状态
omc quest status <quest_id>

# 列出所有任务
omc quest list

# 取消任务
omc quest cancel <quest_id>
```

### `omc agents`

列出所有可用 Agent。

```bash
omc agents [options]

Options:
  --model MODEL   指定模型（默认: deepseek-chat）
  --json           JSON 格式输出
```

### `omc checkpoint`

检查点管理。

```bash
omc checkpoint save "<message>"   # 保存检查点
omc checkpoint list               # 列出检查点
omc checkpoint restore <id>        # 恢复到检查点
```

### `omc team`

团队协作管理。

```bash
omc team create <team_name>              # 创建团队
omc team list                            # 列出团队
omc team stats <team_id>                 # 查看统计
omc team stats <team_id> --period month  # 月统计
```

## 环境变量

| 变量 | 说明 |
|------|------|
| `OMC_DEFAULT_MODEL` | 默认模型 |
| `OMC_MODEL_TIER` | 模型层级（low/medium/high） |
| `DEEPSEEK_API_KEY` | DeepSeek API Key |
| `GLM_API_KEY` | 智谱 GLM API Key |
| `WENXIN_API_KEY` | 文心一言 API Key |
