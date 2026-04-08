# Docker 部署配置
# 支持 Docker 一键部署

# 构建阶段
FROM python:3.11-slim as builder

WORKDIR /app

# 安装构建依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY pyproject.toml .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

# 运行阶段
FROM python:3.11-slim

WORKDIR /app

# 复制依赖
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# 复制源码
COPY src/ ./src/
COPY examples/ ./examples/
COPY docs/ ./docs/

# 创建状态目录
RUN mkdir -p .omc/state

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 启动命令
CMD ["uvicorn", "src.web.app:app", "--host", "0.0.0.0", "--port", "8000"]
