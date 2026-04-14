#!/bin/bash
#
# Oh My Coder 一键安装脚本 (macOS/Linux)
# 使用方法: curl -fsSL https://raw.githubusercontent.com/VOBC/oh-my-coder/main/install.sh | bash
#

set -e  # 遇到错误立即退出

# 配置
REPO_URL="https://github.com/VOBC/oh-my-coder.git"
REPO_NAME="oh-my-coder"
INSTALL_DIR="${HOME}/${REPO_NAME}"
MIN_PYTHON_VERSION="3.9"
AUTO_CONFIRM="${AUTO_CONFIRM:-false}"
INSTALL_DEV="no"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印函数
print_step() { echo -e "${BLUE}==>${NC} $1"; }
print_success() { echo -e "${GREEN}✓${NC} $1"; }
print_warning() { echo -e "${YELLOW}⚠${NC} $1"; }
print_error() { echo -e "${RED}✗${NC} $1"; }

# 检查命令是否存在
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# 获取操作系统
get_os() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if command -v apt-get >/dev/null 2>&1; then
            echo "ubuntu/debian"
        elif command -v yum >/dev/null 2>&1; then
            echo "centos/rhel"
        elif command -v pacman >/dev/null 2>&1; then
            echo "arch"
        elif command -v apk >/dev/null 2>&1; then
            echo "alpine"
        else
            echo "linux"
        fi
    else
        echo "unknown"
    fi
}

# 检查 Python 版本
check_python() {
    print_step "检查 Python 环境..."
    
    if command_exists python3; then
        PYTHON_CMD="python3"
    elif command_exists python; then
        PYTHON_CMD="python"
    else
        print_error "未找到 Python，请先安装 Python ${MIN_PYTHON_VERSION}+"
        print_step "安装方法:"
        echo "  macOS: brew install python"
        echo "  Ubuntu/Debian: sudo apt install python3 python3-pip python3-venv"
        echo "  CentOS/RHEL: sudo yum install python3 python3-pip"
        exit 1
    fi
    
    PYTHON_VERSION=$(${PYTHON_CMD} --version 2>&1 | sed 's/Python //')
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
    
    if [[ "$PYTHON_MAJOR" -lt 3 ]] || [[ "$PYTHON_MAJOR" -eq 3 && "$PYTHON_MINOR" -lt 9 ]]; then
        print_error "Python 版本过低: ${PYTHON_VERSION}，需要 ${MIN_PYTHON_VERSION}+"
        exit 1
    fi
    
    print_success "Python ${PYTHON_VERSION} 已安装"
}

# 检查 pip
check_pip() {
    print_step "检查 pip..."
    
    if ! ${PYTHON_CMD} -m pip --version >/dev/null 2>&1; then
        print_warning "pip 未安装，正在安装..."
        
        OS=$(get_os)
        case $OS in
            macos)
                ${PYTHON_CMD} -m ensurepip --default-pip 2>/dev/null || brew install python
                ;;
            ubuntu|debian)
                sudo apt update && sudo apt install -y python3-pip
                ;;
            centos|rhel)
                sudo yum install -y python3-pip
                ;;
            arch)
                sudo pacman -S python-pip
                ;;
            alpine)
                apk add --no-cache py3-pip
                ;;
            *)
                ${PYTHON_CMD} -m ensurepip --default-pip
                ;;
        esac
    fi
    
    print_success "pip 已安装"
}

# 创建虚拟环境
setup_venv() {
    print_step "创建虚拟环境..."
    
    cd "${INSTALL_DIR}"
    
    if [ -d ".venv" ]; then
        print_warning "虚拟环境已存在，跳过创建"
    else
        ${PYTHON_CMD} -m venv .venv
        print_success "虚拟环境已创建"
    fi
    
    # 激活虚拟环境
    source .venv/bin/activate
    
    # 升级 pip
    pip install --upgrade pip --quiet
    
    print_success "虚拟环境已激活"
}

# 安装依赖
install_dependencies() {
    print_step "安装项目依赖..."
    
    cd "${INSTALL_DIR}"
    source .venv/bin/activate
    
    # 安装项目（包含所有依赖）
    pip install -e . --quiet
    
    # 安装开发依赖（可选）
    if [[ "$INSTALL_DEV" == "yes" ]]; then
        pip install -e ".[dev]" --quiet
    fi
    
    print_success "依赖安装完成"
}

# 配置 API Key
configure_api_key() {
    print_step "配置 API Key..."
    
    cd "${INSTALL_DIR}"
    
    # 创建 .env 文件
    if [ -f ".env" ]; then
        print_warning ".env 文件已存在"
        if [[ "$AUTO_CONFIRM" == "true" ]]; then
            print_step "自动模式：跳过 API Key 配置"
            return
        fi
        read -p "是否要重新配置? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_step "跳过 API Key 配置"
            return
        fi
    fi

    # 自动模式跳过交互式配置
    if [[ "$AUTO_CONFIRM" == "true" ]]; then
        print_step "自动模式：跳过 API Key 配置"
        if [ ! -f ".env" ]; then
            cp .env.example .env 2>/dev/null || echo "# 请手动配置 API Key" > .env
            print_warning "已创建 .env 文件，请稍后编辑并填入你的 API Key"
        fi
        return
    fi
    
    echo ""
    print_step "请选择要使用的模型（按回车跳过，稍后手动配置）:"
    echo ""
    echo "  1) DeepSeek（推荐，免费额度高，每天 4000 万 token）"
    echo "  2) 通义千问（阿里）"
    echo "  3) 智谱 GLM"
    echo "  4) Kimi（月暗）"
    echo "  5) 其他（稍后手动配置）"
    echo ""
    read -p "请输入选项 [1-5] 或直接回车跳过: " choice
    
    case $choice in
        1)
            echo ""
            read -p "请输入 DeepSeek API Key: " api_key
            if [ -n "$api_key" ]; then
                echo "DEEPSEEK_API_KEY=$api_key" > .env
                print_success "已保存 DeepSeek API Key"
            fi
            ;;
        2)
            echo ""
            read -p "请输入通义千问 API Key: " api_key
            if [ -n "$api_key" ]; then
                echo "TONGYI_API_KEY=$api_key" > .env
                print_success "已保存通义千问 API Key"
            fi
            ;;
        3)
            echo ""
            read -p "请输入智谱 GLM API Key: " api_key
            if [ -n "$api_key" ]; then
                echo "GLM_API_KEY=$api_key" > .env
                print_success "已保存智谱 GLM API Key"
            fi
            ;;
        4)
            echo ""
            read -p "请输入 Kimi API Key: " api_key
            if [ -n "$api_key" ]; then
                echo "KIMI_API_KEY=$api_key" > .env
                print_success "已保存 Kimi API Key"
            fi
            ;;
        *)
            print_step "跳过 API Key 配置"
            if [ ! -f ".env" ]; then
                cp .env.example .env
                print_warning "已创建 .env 文件，请编辑并填入你的 API Key"
            fi
            ;;
    esac
}

# 验证安装
verify_installation() {
    print_step "验证安装..."
    
    cd "${INSTALL_DIR}"
    source .venv/bin/activate
    
    # 测试 CLI 是否可用
    if command -v omc >/dev/null 2>&1; then
        OMC_CMD="omc"
    else
        OMC_CMD="${INSTALL_DIR}/.venv/bin/omc"
    fi
    
    echo ""
    print_step "运行 omc --version..."
    if $OMC_CMD --version 2>&1; then
        print_success "CLI 安装成功"
    else
        print_warning "CLI 验证失败，尝试直接运行..."
        python -m src.cli --version 2>&1 || print_warning "模块验证失败"
    fi
    
    echo ""
    print_step "运行 omc model current..."
    python -m src.cli model current 2>&1 || true
    
    # 测试 Python 模块
    if python -c "import oh_my_coder" 2>/dev/null; then
        print_success "Python 模块导入成功"
    else
        print_warning "Python 模块导入失败，请检查依赖"
    fi
    
    echo ""
}

# 打印使用说明
print_usage() {
    echo ""
    echo "========================================"
    echo -e "${GREEN}安装完成！${NC}"
    echo "========================================"
    echo ""
    echo "使用方法:"
    echo ""
    echo "  1. 激活虚拟环境:"
    echo "     cd ${INSTALL_DIR}"
    echo "     source .venv/bin/activate"
    echo ""
    echo "  2. 运行 CLI:"
    echo "     omc --help"
    echo ""
    echo "  3. 或者直接使用:"
    echo "     ${INSTALL_DIR}/.venv/bin/omc --help"
    echo ""
    
    if [ ! -f "${INSTALL_DIR}/.env" ] || ! grep -q "API_KEY=" "${INSTALL_DIR}/.env" 2>/dev/null; then
        echo "  4. 配置 API Key（如果还没配置）:"
        echo "     nano ${INSTALL_DIR}/.env"
        echo ""
        echo "  推荐使用 DeepSeek（免费额度高）:"
        echo "     https://platform.deepseek.com/"
        echo ""
    fi
    
    echo "========================================"
    echo ""
    echo "快速开始:"
    echo "  omc init my-project      # 初始化项目"
    echo "  omc plan \"任务描述\"     # 规划任务"
    echo "  omc run                  # 执行任务"
    echo ""
}

# 主安装流程
main() {
    echo ""
    echo "========================================"
    echo -e "${BLUE}  Oh My Coder 一键安装脚本${NC}"
    echo "========================================"
    echo ""
    
    # 解析参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            -y|--yes)
                AUTO_CONFIRM="true"
                shift
                ;;
            --dev)
                INSTALL_DEV="yes"
                shift
                ;;
            --dir)
                INSTALL_DIR="$2"
                shift 2
                ;;
            --help|-h)
                echo "使用方法: $0 [选项]"
                echo ""
                echo "选项:"
                echo "  -y, --yes       自动确认所有提示（无人值守安装）"
                echo "  --dir <路径>    指定安装目录（默认: ~/oh-my-coder）"
                echo "  --dev           同时安装开发依赖"
                echo "  -h, --help      显示帮助"
                exit 0
                ;;
            *)
                print_error "未知参数: $1"
                exit 1
                ;;
        esac
    done
    
    # 检查环境
    check_python
    check_pip
    
    # 克隆或更新仓库
    print_step "准备项目..."
    
    if [ -d "${INSTALL_DIR}" ]; then
        print_warning "目录 ${INSTALL_DIR} 已存在"
        if [[ "$AUTO_CONFIRM" == "true" ]]; then
            print_step "自动模式：更新代码..."
            cd "${INSTALL_DIR}"
            git pull origin main 2>/dev/null || print_warning "git pull 失败，请手动更新"
        else
            read -p "是否更新代码? (Y/n): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Nn]$ ]]; then
                cd "${INSTALL_DIR}"
                git pull origin main 2>/dev/null || print_warning "git pull 失败，请手动更新"
            fi
        fi
    else
        print_step "克隆仓库..."
        git clone "${REPO_URL}" "${INSTALL_DIR}"
        print_success "仓库已克隆到 ${INSTALL_DIR}"
    fi
    
    # 安装
    setup_venv
    install_dependencies
    configure_api_key
    verify_installation
    print_usage
}

# 运行
main "$@"
