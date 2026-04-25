# 部署指南

本文档介绍如何部署 Oh My Coder 到各种平台。

## 📋 目录

- [Docker 部署](#docker-部署)
- [Vercel 部署](#vercel-部署)
- [Railway 部署](#railway-部署)
- [手动部署](#手动部署)

---

## 🐳 Docker 部署

### 一键启动

```bash
# 克隆项目
git clone https://github.com/VOBC/oh-my-coder.git
cd oh-my-coder

# 设置环境变量
export DEEPSEEK_API_KEY=your_api_key

# 启动服务
docker-compose up -d
```

### 访问

打开浏览器访问 http://localhost:8000

### 停止服务

```bash
docker-compose down
```

---

## ▲ Vercel 部署

### 前提条件

- GitHub 账号
- Vercel 账号

### 一键部署

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/VOBC/oh-my-coder)

### 手动部署

1. Fork 项目到你的 GitHub
2. 登录 [Vercel](https://vercel.com)
3. 点击 "New Project"
4. 导入你 Fork 的仓库
5. 设置环境变量：

   | 变量名 | 说明 |
   |--------|------|
   | DEEPSEEK_API_KEY | DeepSeek API Key |
   | TONGYI_API_KEY | 通义千问 API Key |
   | WENXIN_API_KEY | 文心一言 API Key |

6. 点击 "Deploy"

---

## 🚂 Railway 部署

### 一键部署

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new/template?template=https://github.com/VOBC/oh-my-coder)

### 手动部署

1. 登录 [Railway](https://railway.app)
2. 点击 "New Project"
3. 选择 "Deploy from GitHub repo"
4. 选择 oh-my-coder 仓库
5. 添加环境变量（同上）
6. 部署完成后获取 URL

---

## 🔧 手动部署

### Ubuntu/Debian

```bash
# 安装依赖
sudo apt update
sudo apt install -y python3.11 python3-pip

# 克隆项目
git clone https://github.com/VOBC/oh-my-coder.git
cd oh-my-coder

# 安装
pip install --upgrade pip
pip install -e .[dev]

# 设置环境变量
export DEEPSEEK_API_KEY=your_api_key

# 启动
uvicorn src.web.app:app --host 0.0.0.0 --port 8000
```

### 使用 Systemd 服务

```bash
# 创建服务文件
sudo nano /etc/systemd/system/ohmycoder.service
```

内容：

```ini
[Unit]
Description=Oh My Coder Web Service
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/oh-my-coder
Environment="DEEPSEEK_API_KEY=your_api_key"
ExecStart=/usr/bin/uvicorn src.web.app:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable ohmycoder
sudo systemctl start ohmycoder
```

---

## 🔐 安全配置

### 生产环境建议

1. **使用 HTTPS**：配置 SSL 证书
2. **限制访问**：设置防火墙规则
3. **环境变量**：使用密钥管理服务
4. **日志监控**：配置日志收集

### Nginx 反向代理

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## 📊 环境变量

| 变量名 | 必需 | 说明 |
|--------|------|------|
| DEEPSEEK_API_KEY | ✅ | DeepSeek API 密钥 |
| TONGYI_API_KEY | ⬜ | 通义千问 API 密钥 |
| WENXIN_API_KEY | ⬜ | 文心一言 API 密钥 |
| KIMI_API_KEY | ⬜ | Kimi API 密钥 |
| GLM_API_KEY | ⬜ | 智谱 GLM API 密钥 |
| BAICHUAN_API_KEY | ⬜ | 百川 API 密钥 |
| MINIMAX_API_KEY | ⬜ | Minimax API 密钥 |
| SPARK_API_KEY | ⬜ | 讯飞星火 API 密钥 |
| TIANGONG_API_KEY | ⬜ | 天工 API 密钥 |
| DOUBAO_API_KEY | ⬜ | 豆包 API 密钥 |
| HUNYUAN_API_KEY | ⬜ | 混元 API 密钥 |

---

## ❓ 常见问题

### Q: 端口被占用怎么办？

```bash
# 查看端口占用
lsof -i :8000

# 使用其他端口
uvicorn src.web.app:app --port 8001
```

### Q: 如何更新？

```bash
git pull origin main
pip install --upgrade pip
pip install -e .[dev]
```

### Q: 如何查看日志？

```bash
# Docker
docker-compose logs -f web

# Systemd
sudo journalctl -u ohmycoder -f
```
