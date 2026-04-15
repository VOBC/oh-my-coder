# 快速开始

## 环境要求

- Python 3.10+
- pip

## 安装

```bash
bash <(curl -sL https://ohmycoder.ai/install.sh)
```

## 配置模型

编辑 `.env` 文件，添加你的 API Key：

```bash
# GLM (免费)
GLM_API_KEY=your-key-here

# DeepSeek
DEEPSEEK_API_KEY=your-key-here
```

## 开始使用

```bash
# 交互式聊天
omc chat

# 查看所有 Agent
omc agents

# 执行任务
omc run "帮我写一个 Python 脚本"
```

## 下一步

- 查看 [完整文档](https://vobc.github.io/oh-my-coder/)
- 了解更多 [Agent 类型](https://vobc.github.io/oh-my-coder/guide/agents/)