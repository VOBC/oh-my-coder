# 快速开始详细指南

> 本文从 README.md 迁移而来，提供完整的环境配置与使用说明。

## 🚀 快速开始

### 1. 安装依赖

```bash
git clone https://github.com/VOBC/oh-my-coder.git
cd oh-my-coder

# 推荐创建虚拟环境（已有可跳过）
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

pip install --upgrade pip
pip install -e .
```


> ⚠️ **首次使用**：请将 `examples/.env.example` 复制为 `.env` 并填入真实 API Key，再运行以下命令加载：
> ```bash
> cp examples/.env.example .env
> # 编辑 .env，填入真实 Key 后：
> export $(cat .env | grep -v '^#' | xargs)
> ```
>
> 或直接在终端设置环境变量（见下方）。

```bash
# DeepSeek（推荐，性价比高）
export DEEPSEEK_API_KEY=your_key_here

# 可选：其他模型（按生产就绪度排序）
export MIMO_API_KEY=your_key             # 小米 MiMo
export GLM_API_KEY=your_key              # 智谱 GLM
export KIMI_API_KEY=your_key             # Kimi
export DOUBAO_API_KEY=your_key           # 字节豆包
export TIANGONG_API_KEY=your_key         # 天工AI
export BAICHUAN_API_KEY=your_key         # 百川智能
export TONGYI_API_KEY=your_key           # 通义千问（Beta：高并发偶发超时）
export MINIMAX_API_KEY=your_key          # MiniMax（Beta：无函数调用）
export SPARK_API_KEY=your_key            # 讯飞星火（Beta：需同时配置 SPARK_APP_ID 和 SPARK_SECRET_KEY）
export SPARK_APP_ID=your_app_id          # 讯飞星火 APP ID
export SPARK_SECRET_KEY=your_secret     # 讯飞星火 SECRET KEY
export WENXIN_API_KEY=your_key           # 文心一言（待完善：需同时配置 WENXIN_SECRET_KEY）
export WENXIN_SECRET_KEY=your_secret    # 文心一言 SECRET KEY
export HUNYUAN_API_KEY=your_key          # 腾讯混元（待完善：需同时配置 HUNYUAN_SECRET_KEY）
export HUNYUAN_SECRET_KEY=your_secret   # 腾讯混元 SECRET KEY
```

<details>
<summary>📖 详细配置说明</summary>

### 模型特定配置

**DeepSeek**
```bash
export DEEPSEEK_API_KEY=sk-xxxxx
# API 地址: https://api.deepseek.com
# 模型: deepseek-chat, deepseek-reasoner
```

**文心一言**
```bash
export WENXIN_API_KEY=your_api_key
export WENXIN_SECRET_KEY=your_secret_key
# 需要在百度智能云控制台获取
```

**腾讯混元**
```bash
export HUNYUAN_API_KEY=your_api_key
export HUNYUAN_SECRET_KEY=your_secret_key
# 需要在腾讯云控制台获取
```

### 自定义 API 地址

如果需要使用代理或私有部署：
```bash
export DEEPSEEK_API_BASE=https://your-proxy.com/v1
```

</details>

### 3. 运行

```bash
# 🌐 Web 界面（推荐，新手友好）
python -m src.web.app
# 浏览器打开: http://localhost:8000

# 💻 CLI
omc explore .
omc run "实现一个 REST API"
```

---

