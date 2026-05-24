# 快速开始

## 第一步：安装

**推荐：使用虚拟环境（避免权限警告）**

```bash
git clone https://github.com/VOBC/oh-my-coder.git
cd oh-my-coder
python3 -m venv venv
source venv/bin/activate
pip install -e ".[web]"
```

激活虚拟环境后，所有 `pip` 和 `omc` 命令都会在隔离环境中运行，不会触发权限警告。

**或者使用用户安装（会有权限警告，可忽略）**：

```bash
pip install -e ".[web]"
```

> 💡 如果不使用虚拟环境，会出现 `Defaulting to user installation because normal site-packages is not writeable` 警告，这是正常的，可以安全忽略。

## 第二步：配置 API Key

```bash
# 推荐：DeepSeek（性价比最高）
export DEEPSEEK_API_KEY=sk-xxxxx

# 或者：GLM（免费使用）
export GLM_API_KEY=your_key_here
```

## 第三步：运行

## CLI

```bash
# 探索当前项目
omc explore .

# 执行开发任务
omc run "实现一个 REST API"

# 启动后台任务
omc quest start "重构用户模块"
```

## Web 界面

**如果使用虚拟环境**，请先激活：

```bash
source venv/bin/activate
```

然后启动 Web 服务：

```bash
# 方式一：直接启动（开发，端口 8000）
python -m src.web.app
# 浏览器打开: http://localhost:8000

# 方式二：通过 CLI 启动（推荐，支持自动端口切换）
omc server start
# 默认 http://localhost:8080，端口被占用时自动切换（8081, 8082...）
```

## 常见任务示例

### 探索新项目

```bash
omc explore /path/to/project
```

### 实现一个功能

```bash
omc run "为电商系统实现订单管理模块，包含增删改查"
```

### 代码审查

```bash
omc run "审查 src/ 目录下的代码质量" -w review
```

### 调试问题

```bash
omc run "修复登录接口的内存泄漏问题" -w debug
```

## 下一步

- [Agent 列表 →](../guide/agents.md)
- [执行模式 →](../guide/workflows.md)
- [常见问题 →](../zh/tutorials.md)
