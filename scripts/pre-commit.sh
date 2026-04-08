#!/bin/bash
# pre-commit.sh - 提交前必须运行的检查
# 使用方法: ./scripts/pre-commit.sh && git commit -m "message"

set -e  # 任何命令失败立即退出

echo "======================================"
echo "🔍 提交前检查开始"
echo "======================================"

echo ""
echo "1️⃣  运行 ruff check..."
python3 -m ruff check src/ tests/

echo ""
echo "2️⃣  运行 black check..."
python3 -m black --check src/ tests/

echo ""
echo "3️⃣  运行 pytest..."
python3 -m pytest tests/ -q --tb=short

echo ""
echo "======================================"
echo "✅ 所有检查通过！可以提交了。"
echo "======================================"
