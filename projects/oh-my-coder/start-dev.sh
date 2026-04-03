#!/bin/bash
# Oh My Coder 开发启动脚本

echo "🚀 Oh My Coder 开发环境"
echo "========================"

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "❌ 需要安装 Python 3.10+"
    exit 1
fi

# 创建虚拟环境
if [ ! -d "venv" ]; then
    echo "📦 创建虚拟环境..."
    python3 -m venv venv
fi

# 激活环境
source venv/bin/activate

# 安装依赖
echo "📥 安装依赖..."
pip install -r requirements.txt -q

# 启动开发服务器
echo "✅ 启动开发服务器..."
python -m uvicorn src.main:app --reload --port 8000
