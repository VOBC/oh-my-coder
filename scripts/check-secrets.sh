#!/bin/bash
# 安全扫描脚本 - 检查是否有API密钥泄露风险

echo "🔍 开始安全扫描..."

# 检查.env文件是否被git跟踪
if git ls-files | grep -q '\.env$'; then
    echo "❌ 警告: .env文件被git跟踪！这可能导致API密钥泄露。"
    echo "   建议: git rm --cached .env"
    exit 1
fi

# 检查是否有真实的API密钥模式
PATTERNS=(
    "sk-[a-zA-Z0-9]{32,}"
    "Bearer [a-zA-Z0-9]{32,}"
    "api[_-]?key[=:][ ]*[a-zA-Z0-9]{32,}"
    "secret[=:][ ]*[a-zA-Z0-9]{32,}"
    "token[=:][ ]*[a-zA-Z0-9]{32,}"
)

FOUND_SECRETS=0
for pattern in "${PATTERNS[@]}"; do
    if git grep -n "$pattern" -- '*.py' '*.md' '*.txt' '*.env' '*.json' '*.yaml' '*.yml' 2>/dev/null | grep -v "your_api_key" | grep -v "sk-xxxxx" | grep -v "test" | grep -v "example" > /dev/null; then
        echo "❌ 检测到可能的API密钥泄露模式: $pattern"
        FOUND_SECRETS=1
    fi
done

if [ $FOUND_SECRETS -eq 0 ]; then
    echo "✅ 安全扫描通过: 未检测到API密钥泄露"
else
    echo "⚠️  发现潜在安全问题，请检查上述警告"
    exit 1
fi