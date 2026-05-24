# 快速开始

## 安装

```bash
git clone https://github.com/VOBC/oh-my-coder.git
cd oh-my-coder

# 创建虚拟环境（避免 pip 权限警告）
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装
pip install -e .
```

## 配置 API Key

```bash
# 复制配置模板
cp examples/.env.example .env

# 编辑 .env，填入你的 API Key
# 最少只需配置一个：
# DEEPSEEK_API_KEY=sk-xxx
# GLM_API_KEY=xxx
# MIMO_API_KEY=xxx
```

## 启动

```bash
# Web 界面（推荐）
omc server start
# 浏览器打开: http://localhost:8080

# CLI 模式
omc run "帮我实现一个 REST API"
```

---

**常见问题**：

- **端口被占用**：`omc server start` 会自动切换到 8081/8082/...
- **pip 警告**：确保已激活虚拟环境（`source venv/bin/activate`）
- **更多模型配置**：见 [模型配置文档](configuration.md)
