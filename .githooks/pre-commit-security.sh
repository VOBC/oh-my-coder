#!/bin/bash
# 预提交安全检查钩子
# 安装: cp .githooks/pre-commit-security.sh .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit

set -e

echo "======================================"
echo "🔒 安全检查"
echo "======================================"

# 1. 检查 str(e) 模式
echo ""
echo "1️⃣  检查 str(e) 异常信息泄露..."
STRE_ISSUES=$(grep -r "str(e)" --include="*.py" src/ 2>/dev/null | grep -v "# safe" | grep -v "str(e) is" | grep -v "str(e) ==" || true)
if [ -n "$STRE_ISSUES" ]; then
    echo "❌ 发现 str(e) 模式（可能泄露敏感信息）:"
    echo "$STRE_ISSUES"
    exit 1
fi
echo "✅ 无 str(e) 泄露风险"

# 2. 检查 in url 模式
echo ""
echo "2️⃣  检查 in url 不安全模式..."
INURL_ISSUES=$(grep -r "in.*url\|in url" --include="*.py" src/ tests/ 2>/dev/null | grep -v "urlparse" | grep -v "__pycache__" | grep "\".*in.*url\"" || true)
if [ -n "$INURL_ISSUES" ]; then
    echo "⚠️  发现 in url 模式（请确认是否安全）:"
    echo "$INURL_ISSUES"
fi
echo "✅ URL 验证检查完成"

# 3. 检查 MD5 使用
echo ""
echo "3️⃣  检查弱加密算法..."
MD5_ISSUES=$(grep -r "hashlib.md5\|hashlib.sha1" --include="*.py" src/ 2>/dev/null | grep -v "# safe\|# non-crypto\|# cache" || true)
if [ -n "$MD5_ISSUES" ]; then
    echo "⚠️  发现 MD5/SHA1 使用（请确认非密码用途）:"
    echo "$MD5_ISSUES"
fi
echo "✅ 加密算法检查完成"

# 4. 检查 workflow permissions
echo ""
echo "4️⃣  检查 workflow permissions..."
for f in .github/workflows/*.yml; do
    if [ -f "$f" ]; then
        if ! grep -q "^permissions:" "$f"; then
            echo "❌ $f 缺少 permissions 声明"
            exit 1
        fi
    fi
done
echo "✅ 所有 workflow 有 permissions"

echo ""
echo "======================================"
echo "✅ 安全检查通过"
echo "======================================"
