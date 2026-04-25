# 安装指南

## 系统要求

- Python 3.10+
- Git
- API Key（见[模型配置](models.md)）

## 一键安装

```bash
git clone https://github.com/VOBC/oh-my-coder.git
cd oh-my-coder
pip install --upgrade pip
pip install -e .
```

安装脚本支持交互式配置 API Key：

```bash
bash install.sh
```

## 配置 API Key

将示例配置复制为 `.env`：

```bash
cp examples/.env.example .env
# 编辑 .env，填入真实 Key
```

或在终端直接设置环境变量：

```bash
# DeepSeek（推荐，性价比高）
export DEEPSEEK_API_KEY=sk-xxxxx

# 智谱 GLM（GLM-4-Flash 开源免费）
export GLM_API_KEY=your_key_here

# 可选：其他模型
export WENXIN_API_KEY=your_api_key
export WENXIN_SECRET_KEY=your_secret_key
export TONGYI_API_KEY=your_key
export KIMI_API_KEY=your_key
export HUNYUAN_API_KEY=your_api_key
export HUNYUAN_SECRET_KEY=your_secret_key
```

## 自定义 API 地址

使用代理或私有部署：

```bash
export DEEPSEEK_API_BASE=https://your-proxy.com/v1
```

## 验证安装

```bash
omc --version
omc --help
```

## Web 界面

```bash
python -m src.web.app
# 浏览器打开 http://localhost:8000
```

## 卸载

```bash
pip uninstall oh-my-coder
```
