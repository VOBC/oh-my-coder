#!/bin/bash
# 全库安全扫描脚本 - 每周运行一次
# 用法: bash scripts/security-scan.sh

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

ERRORS=0
WARNINGS=0

echo "======================================"
echo "🔍 全库安全扫描"
echo "======================================"
echo "时间: $(date)"
echo ""

# 1. str(e) 检查
echo "1️⃣  扫描 str(e) 异常信息泄露..."
STRE_COUNT=$(grep -rn "str(e)" src/ tests/ --include="*.py" 2>/dev/null | grep -v "# safe" | grep -v "__pycache__" | grep -v "test_security_patterns.py" | grep -v "str(e)\[:" | wc -l)
if [ "$STRE_COUNT" -gt 0 ]; then
    echo -e "${RED}❌ 发现 $STRE_COUNT 处 str(e)${NC}"
    grep -rn "str(e)" src/ tests/ --include="*.py" | grep -v "# safe" | grep -v "__pycache__" | head -10
    ERRORS=$((ERRORS + STRE_COUNT))
else
    echo -e "${GREEN}✅ 无 str(e) 泄露风险${NC}"
fi

# 2. in url 检查 (只检查 assert 语句中的不安全用法)
echo ""
echo "2️⃣  扫描 in url 不安全模式..."
INURL_COUNT=$(grep -rn "assert.*in.*url\|in url" src/ tests/ --include="*.py" 2>/dev/null | grep -v "urlparse" | grep -v "__pycache__" | grep -v "# noqa" | wc -l)
if [ "$INURL_COUNT" -gt 0 ]; then
    echo -e "${YELLOW}⚠️  发现 $INURL_COUNT 处 in url 模式${NC}"
    grep -rn "in.*url\|in url" src/ tests/ --include="*.py" | grep -v "urlparse" | grep -v "__pycache__" | head -5
    WARNINGS=$((WARNINGS + INURL_COUNT))
else
    echo -e "${GREEN}✅ 无 in url 风险${NC}"
fi

# 3. MD5/SHA1 检查
echo ""
echo "3️⃣  扫描弱加密算法..."
MD5_COUNT=$(grep -rn "hashlib\.md5\|hashlib\.sha1" src/ tests/ --include="*.py" 2>/dev/null | grep -v "# safe" | grep -v "__pycache__" | grep -v "test_security" | wc -l)
if [ "$MD5_COUNT" -gt 0 ]; then
    echo -e "${YELLOW}⚠️  发现 $MD5_COUNT 处 MD5/SHA1${NC}"
    grep -rn "hashlib\.md5\|hashlib\.sha1" src/ tests/ --include="*.py" | grep -v "# safe" | grep -v "__pycache__" | head -5
    WARNINGS=$((WARNINGS + MD5_COUNT))
else
    echo -e "${GREEN}✅ 无弱加密算法${NC}"
fi

# 4. workflow permissions 检查
echo ""
echo "4️⃣  扫描 workflow permissions..."
MISSING_PERM=0
for f in .github/workflows/*.yml; do
    if [ -f "$f" ]; then
        if ! grep -q "^permissions:" "$f"; then
            echo -e "${RED}❌ $f 缺少 permissions${NC}"
            MISSING_PERM=$((MISSING_PERM + 1))
        fi
    fi
done
if [ "$MISSING_PERM" -eq 0 ]; then
    echo -e "${GREEN}✅ 所有 workflow 有 permissions${NC}"
else
    ERRORS=$((ERRORS + MISSING_PERM))
fi

# 5. 硬编码密钥检查
echo ""
echo "5️⃣  扫描硬编码敏感信息..."
SECRETS_COUNT=$(grep -rn "api_key\|apikey\|password\|secret\|token" src/ tests/ --include="*.py" 2>/dev/null | grep -E "(=\s*[\"'][^\"']{8,}[\"'])" | grep -v "example\|test\|mock\|__pycache__" | wc -l)
if [ "$SECRETS_COUNT" -gt 0 ]; then
    echo -e "${YELLOW}⚠️  发现 $SECRETS_COUNT 处可能的硬编码密钥${NC}"
    WARNINGS=$((WARNINGS + SECRETS_COUNT))
else
    echo -e "${GREEN}✅ 无明显硬编码密钥${NC}"
fi

# 6. subprocess shell=True 检查
echo ""
echo "6️⃣  扫描命令注入风险..."
SHELL_COUNT=$(grep -rn "shell=True" src/ tests/ --include="*.py" 2>/dev/null | grep -v "__pycache__" | wc -l)
if [ "$SHELL_COUNT" -gt 0 ]; then
    echo -e "${YELLOW}⚠️  发现 $SHELL_COUNT 处 shell=True${NC}"
    grep -rn "shell=True" src/ tests/ --include="*.py" | grep -v "__pycache__" | head -5
    WARNINGS=$((WARNINGS + SHELL_COUNT))
else
    echo -e "${GREEN}✅ 无 shell=True 风险${NC}"
fi

echo ""
echo "======================================"
echo "📊 扫描结果"
echo "======================================"
echo -e "错误: ${RED}$ERRORS${NC}"
echo -e "警告: ${YELLOW}$WARNINGS${NC}"
echo ""

if [ $ERRORS -gt 0 ]; then
    echo -e "${RED}❌ 发现严重安全问题，需要立即修复${NC}"
    echo -e "${CYAN}📖 参考: docs/security/security-whackamole-investigation.md${NC}"
    exit 1
elif [ $WARNINGS -gt 0 ]; then
    echo -e "${YELLOW}⚠️  发现警告，建议检查${NC}"
    exit 0
else
    echo -e "${GREEN}✅ 全库安全扫描通过${NC}"
    exit 0
fi
