#!/bin/bash
#
# 发布前安全检查脚本
# 基于 Claude Code 源码泄露教训（51.2万行源码外泄 + API token 泄露）
#
# 检查项：
# 1. 没有 .map 源码映射文件（防止源码被还原）
# 2. 没有真实 API Key 硬编码（非示例占位符）
# 3. 没有 .env 文件被打包
# 4. 没有敏感路径（如 ~/.ssh/、/etc/）
# 5. 没有危险的 build 产物
#
# 用法: bash scripts/pre_publish_security_check.sh [--dir <path>]
#

set -euo pipefail

# 颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

ERRORS=0
WARNINGS=0

# 默认检查当前目录
CHECK_DIR="${1:-.}"

echo -e "${CYAN}========================================"
echo -e "  发布前安全检查"
echo -e "========================================${NC}"
echo -e "检查目录: ${CHECK_DIR}"
echo ""

# ── 检查 1: .map 源码映射文件 ───────────────────────────────────────────────
echo -e "${CYAN}[1/5] 检查 .map 源码映射文件...${NC}"
MAP_FILES=$(find "$CHECK_DIR" -type f \( -name "*.map" -o -name "*.js.map" -o -name "*.ts.map" \) 2>/dev/null || true)
if [[ -n "$MAP_FILES" ]]; then
    echo -e "${RED}✗ 发现 .map 文件（可能泄露源码）:${NC}"
    echo "$MAP_FILES" | while read -r f; do echo "  - $f"; done
    ((ERRORS++))
else
    echo -e "${GREEN}✓ 无 .map 文件${NC}"
fi
echo ""

# ── 检查 2: API Key / Token 硬编码 ─────────────────────────────────────────
echo -e "${CYAN}[2/5] 检查 API Key / Token 硬编码...${NC}"

# 只检查看起来像真实 key 的模式，排除示例占位符
# 匹配：export VAR=sk-xxxx 或 "VAR": "ghp_xxxx" 等真实 key 格式
REAL_KEY_PATTERN='(DEEPSEEK_API_KEY|KIMI_API_KEY|DOUBAO_API_KEY|TIANGONG_API_KEY|GLM_API_KEY|OPENAI_API_KEY|GITHUB_TOKEN|PRIVATE_KEY|ANTHROPIC_API_KEY)\s*[=:]\s*["'"'"'a-zA-Z0-9_-]{10,}'

# 搜索真实 key（排除 test 文件、example 目录、demo 文件）
FOUND_KEYS=""
for ext in py js ts go json yaml yml; do
    result=$(find "$CHECK_DIR" -type f -name "*.$ext" \
        ! -path "*/.git/*" \
        ! -path "*/tests/*" \
        ! -path "*/examples/*" \
        ! -name "*test*.$ext" \
        ! -name "demo.py" \
        ! -name "*.demo.*" \
        ! -name ".env*" \
        2>/dev/null \
        -exec grep -l -E "$REAL_KEY_PATTERN" {} \; || true)
    if [[ -n "$result" ]]; then
        FOUND_KEYS="$FOUND_KEYS"$'\n'"$result"
    fi
done

if [[ -n "$FOUND_KEYS" ]]; then
    echo -e "${RED}✗ 发现疑似真实 API Key 硬编码:${NC}"
    echo "$FOUND_KEYS" | grep -v '^$' | sort -u | while read -r f; do echo "  - $f"; done
    ((ERRORS++))
else
    echo -e "${GREEN}✓ 未发现真实 API Key 硬编码${NC}"
fi

# 检查 .env 文件（不应该被 commit）
ENV_FILES=$(find "$CHECK_DIR" -type f -name ".env" ! -name ".env.example" ! -name ".env.template" ! -path "*/.git/*" 2>/dev/null || true)
if [[ -n "$ENV_FILES" ]]; then
    echo "$ENV_FILES" | while read -r f; do echo "  - $f"; done
    ((WARNINGS++))
fi
echo ""

# ── 检查 3: 敏感目录 ─────────────────────────────────────────────────────────
echo -e "${CYAN}[3/5] 检查敏感目录...${NC}"

SENSITIVE_DIRS=$(find "$CHECK_DIR" -type d \( -name ".ssh" -o -name "credentials" -o -name "secrets" -o -name ".aws" \) ! -path "*/.git/*" 2>/dev/null || true)
if [[ -n "$SENSITIVE_DIRS" ]]; then
    echo -e "${RED}✗ 发现敏感目录:${NC}"
    echo "$SENSITIVE_DIRS" | while read -r d; do echo "  - $d"; done
    ((ERRORS++))
else
    echo -e "${GREEN}✓ 无敏感目录${NC}"
fi
echo ""

# ── 检查 4: 危险 build 产物 ─────────────────────────────────────────────────
echo -e "${CYAN}[4/5] 检查危险 build 产物...${NC}"

DANGEROUS_BUILDS=$(find "$CHECK_DIR" -type f \( -name "*.pyc" -o -name "__pycache__" -o -name "node_modules" -o -name ".pytest_cache" -o -name ".ruff_cache" \) ! -path "*/.git/*" -print 2>/dev/null | head -20 || true)
if [[ -n "$DANGEROUS_BUILDS" ]]; then
    echo -e "${YELLOW}⚠ 发现 build 缓存（建议添加到 .gitignore）:${NC}"
    echo "$DANGEROUS_BUILDS" | while read -r f; do echo "  - $f"; done
    ((WARNINGS++))
    echo -e "${GREEN}✓ 无 build 缓存文件${NC}"
fi
echo ""

# ── 检查 5: requirements / pyproject.toml ───────────────────────────────────
echo -e "${CYAN}[5/5] 检查配置文件...${NC}"

if [[ -f "$CHECK_DIR/pyproject.toml" ]]; then
    echo -e "${GREEN}✓ pyproject.toml 存在${NC}"
fi

if [[ -f "$CHECK_DIR/requirements.txt" ]]; then
    SUSPICIOUS=$(grep -iE "eval\(|exec\(.*shell" "$CHECK_DIR/requirements.txt" 2>/dev/null || true)
    if [[ -n "$SUSPICIOUS" ]]; then
        echo -e "${YELLOW}⚠ requirements.txt 中发现可疑依赖:${NC}"
        echo "$SUSPICIOUS" | while read -r l; do echo "  - $l"; done
        ((WARNINGS++))
        echo -e "${GREEN}✓ requirements.txt 无可疑依赖${NC}"
    fi
fi
echo ""

# ── 总结 ──────────────────────────────────────────────────────────────────────
echo -e "${CYAN}========================================"
echo -e "  检查结果"
echo -e "========================================${NC}"
echo -e "  ${RED}错误: $ERRORS${NC}"
echo -e "  ${YELLOW}警告: $WARNINGS${NC}"
echo ""

if [[ $ERRORS -gt 0 ]]; then
    echo -e "${RED}✗ 安全检查未通过！发布前请修复以上 $ERRORS 个错误。${NC}"
    exit 1
elif [[ $WARNINGS -gt 0 ]]; then
    echo -e "${YELLOW}⚠ 安全检查通过，但有 $WARNINGS 个警告。${NC}"
    exit 0
else
    echo -e "${GREEN}✓ 安全检查全部通过，可以发布！${NC}"
    exit 0
fi
