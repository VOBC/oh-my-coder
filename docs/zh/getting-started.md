# 快速开始

## 第一步：安装

```bash
git clone https://github.com/VOBC/oh-my-coder.git
cd oh-my-coder
pip install -e .
```

## 第二步：配置 API Key

```bash
# 推荐：DeepSeek（性价比最高）
export DEEPSEEK_API_KEY=sk-xxxxx

# 或者：GLM（免费使用）
export GLM_API_KEY=your_key_here
```

## 第三步：运行

=== "CLI"

    ```bash
    # 探索当前项目
    omc explore .

    # 执行开发任务
    omc run "实现一个 REST API"

    # 启动后台任务
    omc quest start "重构用户模块"
    ```

=== "Web 界面"

    ```bash
    python -m src.web.app
    # 打开浏览器访问 http://localhost:8000
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
