#!/bin/bash
#
# Oh My Coder - 3 行命令快速开始
#
# 使用方法（任选一种）：
#
#   # 方式一：一条命令搞定（推荐）
#   bash <(curl -fsSL https://git.io/oh-my-coder)
#
#   # 方式二：手动三步
#   git clone https://github.com/VOBC/oh-my-coder.git && cd oh-my-coder
#   ./install.sh
#   omc run "实现一个待办事项 CLI"
#
#   # 方式三：已有项目，本地安装
#   git clone https://github.com/VOBC/oh-my-coder.git && cd oh-my-coder
#   python3 -m venv .venv && source .venv/bin/activate
#   pip install -e . --quiet
#   omc agents                    # 查看所有 Agent
#   omc run "给这个项目写测试"       # 运行你的第一个任务
#

set -e

REPO_URL="https://github.com/VOBC/oh-my-coder.git"
INSTALL_DIR="${HOME}/oh-my-coder"

# 颜色
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'

info()  { echo -e "${BLUE}→${NC} $1"; }
ok()    { echo -e "${GREEN}✓${NC} $1"; }
warn()  { echo -e "${YELLOW}⚠${NC} $1"; }
fail()  { echo -e "${RED}✗${NC} $1"; }

# 检测环境
detect_os() {
    if [[ "$OSTYPE" == "darwin"* ]]; then echo "macos"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then echo "linux"
    else echo "unknown"; fi
}

# 检查 Python
check_python() {
    local python_cmd=""
    if command -v python3 >/dev/null 2>&1; then python_cmd="python3"
    elif command -v python >/dev/null 2>&1; then python_cmd="python"
    else
        fail "未找到 Python 3"
        echo ""
        echo "  macOS:  brew install python"
        echo "  Linux:  sudo apt install python3 python3-venv"
        exit 1
    fi
    echo "$python_cmd"
}

# 克隆或更新
clone_repo() {
    if [ -d "$INSTALL_DIR" ]; then
        info "目录已存在: $INSTALL_DIR"
        read -p "是否更新代码? [Y/n]: " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Nn]$ ]]; then
            git -C "$INSTALL_DIR" pull origin main 2>/dev/null || warn "git pull 失败"
        fi
    else
        info "克隆仓库..."
        git clone "$REPO_URL" "$INSTALL_DIR"
    fi
}

# 安装依赖
install_deps() {
    local py_cmd="$1"
    cd "$INSTALL_DIR"

    # 虚拟环境
    if [ ! -d ".venv" ]; then
        $py_cmd -m venv .venv
        ok "虚拟环境已创建"
    else
        info "虚拟环境已存在"
    fi

    source .venv/bin/activate
    pip install --upgrade pip -q
    pip install -e . -q
    ok "依赖安装完成"
}

# 配置 API Key
setup_api_key() {
    cd "$INSTALL_DIR"
    if [ -f ".env" ] && grep -q "API_KEY" .env 2>/dev/null; then
        info ".env 已配置，跳过"
        return
    fi

    echo ""
    echo "请选择模型（直接回车跳过，稍后手动配置）："
    echo "  1) DeepSeek（推荐，免费额度高）"
    echo "  2) 智谱 GLM（永久免费 400 万 token）"
    echo "  3) 通义千问（阿里）"
    echo "  4) Kimi（月暗）"
    echo ""
    read -p "请输入选项 [1-4] 或直接回车: " choice

    local env_file="$INSTALL_DIR/.env"
    case $choice in
        1) read -p "DeepSeek API Key: " key
           [ -n "$key" ] && echo "DEEPSEEK_API_KEY=$key" > "$env_file" && ok "已保存 DeepSeek Key" ;;
        2) read -p "智谱 API Key: " key
           [ -n "$key" ] && echo "GLM_API_KEY=$key" > "$env_file" && ok "已保存智谱 Key" ;;
        3) read -p "通义千问 API Key: " key
           [ -n "$key" ] && echo "TONGYI_API_KEY=$key" > "$env_file" && ok "已保存通义千问 Key" ;;
        4) read -p "Kimi API Key: " key
           [ -n "$key" ] && echo "KIMI_API_KEY=$key" > "$env_file" && ok "已保存 Kimi Key" ;;
        *)
           if [ ! -f "$env_file" ]; then
               echo "# 请填入你的 API Key" > "$env_file"
               warn "已创建 .env 文件，请编辑填入 API Key"
           fi
           ;;
    esac
}

# 运行 Demo
run_demo() {
    cd "$INSTALL_DIR"
    source .venv/bin/activate

    echo ""
    echo "=========================================="
    echo "  🎉 安装完成！"
    echo "=========================================="
    echo ""
    echo "  1. 查看所有 Agent:"
    echo "     omc agents"
    echo ""
    echo "  2. 运行你的第一个任务:"
    echo "     omc run \"实现一个待办事项 CLI\""
    echo ""
    echo "  3. 自动路由（AI 决定用哪个 Agent）:"
    echo "     omc run \"重构这个项目\" -w autopilot"
    echo ""
    echo "  4. 文档生成:"
    echo "     omc run \"生成项目架构文档\" -w doc"
    echo ""
    echo "  查看更多帮助: omc --help"
    echo ""
}

# -------- 主流程 --------
main() {
    echo ""
    echo "=========================================="
    echo -e "  ${BLUE}Oh My Coder${NC}  -  3 步快速开始"
    echo "=========================================="
    echo ""

    # Step 1: Clone
    info "[1/3] 克隆仓库..."
    clone_repo

    # Step 2: Install
    info "[2/3] 安装依赖..."
    PY_CMD=$(check_python)
    install_deps "$PY_CMD"

    # Step 3: Configure
    info "[3/3] 配置 API Key..."
    setup_api_key

    run_demo
}

main "$@"
