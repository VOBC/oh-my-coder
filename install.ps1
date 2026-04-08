<#
.SYNOPSIS
    Oh My Coder 一键安装脚本 (Windows)

.DESCRIPTION
    使用方法:
    powershell -c "irm https://raw.githubusercontent.com/VOBC/oh-my-coder/main/install.ps1 | iex"

.NOTES
    作者: VOBC
    版本: 1.0.0
#>

[CmdletBinding()]
param(
    [string]$InstallDir = "$env:USERPROFILE\oh-my-coder",
    [switch]$InstallDev,
    [switch]$SkipApiKey
)

$ErrorActionPreference = "Stop"

# 配置
$RepoUrl = "https://github.com/VOBC/oh-my-coder.git"
$MinPythonVersion = "3.9"

# 颜色函数
function Write-Step { Write-Host "==>" -ForegroundColor Cyan -NoNewline; Write-Host " $args" }
function Write-Success { Write-Host "[OK]" -ForegroundColor Green -NoNewline; Write-Host " $args" }
function Write-Warning { Write-Host "[!]" -ForegroundColor Yellow -NoNewline; Write-Host " $args" }
function Write-Error { Write-Host "[X]" -ForegroundColor Red -NoNewline; Write-Host " $args" }

# 检查 Python
function Test-Python {
    Write-Step "检查 Python 环境..."
    
    $pythonCmd = $null
    
    # 尝试多个 Python 命令
    @("python3", "python", "py") | ForEach-Object {
        if (Get-Command $_ -ErrorAction SilentlyContinue) {
            $pythonCmd = $_
        }
    }
    
    if (-not $pythonCmd) {
        Write-Error "未找到 Python，请先安装 Python $MinPythonVersion+"
        Write-Step "安装方法:"
        Write-Host "  - 下载 Python: https://www.python.org/downloads/"
        Write-Host "  - 或使用 winget: winget install Python.Python.3.11"
        Write-Host "  - 或使用 chocolatey: choco install python"
        exit 1
    }
    
    $pythonVersion = & $pythonCmd --version 2>&1
    $versionMatch = [regex]::Match($pythonVersion, '(\d+)\.(\d+)')
    
    if ($versionMatch.Success) {
        $major = [int]$versionMatch.Groups[1].Value
        $minor = [int]$versionMatch.Groups[2].Value
        
        if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 9)) {
            Write-Error "Python 版本过低: $($versionMatch.Value)，需要 $MinPythonVersion+"
            exit 1
        }
    }
    
    Write-Success "Python $pythonVersion 已安装"
    return $pythonCmd
}

# 检查 pip
function Test-Pip {
    param([string]$PythonCmd)
    
    Write-Step "检查 pip..."
    
    try {
        & $PythonCmd -m pip --version 2>&1 | Out-Null
        Write-Success "pip 已安装"
        return $true
    }
    catch {
        Write-Warning "pip 未安装，正在安装..."
        
        try {
            & $PythonCmd -m ensurepip --default-pip 2>&1 | Out-Null
            Write-Success "pip 已安装"
            return $true
        }
        catch {
            Write-Error "pip 安装失败: $_"
            return $false
        }
    }
}

# 克隆或更新仓库
function Initialize-Repository {
    param([string]$RepoUrl, [string]$InstallDir)
    
    Write-Step "准备项目..."
    
    if (Test-Path $InstallDir) {
        Write-Warning "目录 $InstallDir 已存在"
        $response = Read-Host "是否更新代码? (Y/n)"
        if ($response -ne "n") {
            Set-Location $InstallDir
            git pull origin main 2>&1 | Out-Null
        }
    }
    else {
        Write-Step "克隆仓库..."
        git clone $RepoUrl $InstallDir
        Write-Success "仓库已克隆到 $InstallDir"
    }
    
    Set-Location $InstallDir
}

# 创建虚拟环境
function New-VirtualEnvironment {
    param([string]$PythonCmd, [string]$InstallDir)
    
    Write-Step "创建虚拟环境..."
    
    Set-Location $InstallDir
    $venvPath = Join-Path $InstallDir ".venv"
    
    if (Test-Path $venvPath) {
        Write-Warning "虚拟环境已存在，跳过创建"
    }
    else {
        & $PythonCmd -m venv $venvPath
        Write-Success "虚拟环境已创建"
    }
    
    # Windows 虚拟环境路径
    $activatePath = Join-Path $venvPath "Scripts\Activate.ps1"
    
    # 激活虚拟环境
    & $activatePath
    
    # 升级 pip
    & python -m pip install --upgrade pip --quiet
    
    Write-Success "虚拟环境已激活"
    return $venvPath
}

# 安装依赖
function Install-Dependencies {
    param([string]$VenvPath, [switch]$InstallDev)
    
    Write-Step "安装项目依赖..."
    
    $pipPath = Join-Path $VenvPath "Scripts\pip.exe"
    
    # 安装项目
    & $pipPath install -e . --quiet
    
    # 安装开发依赖
    if ($InstallDev) {
        & $pipPath install -e ".[dev]" --quiet
    }
    
    Write-Success "依赖安装完成"
}

# 配置 API Key
function Set-ApiKey {
    param([string]$InstallDir, [switch]$SkipApiKey)
    
    if ($SkipApiKey) {
        Write-Step "跳过 API Key 配置"
        return
    }
    
    Write-Step "配置 API Key..."
    
    $envFile = Join-Path $InstallDir ".env"
    
    if (Test-Path $envFile) {
        Write-Warning ".env 文件已存在"
        $response = Read-Host "是否要重新配置? (y/N)"
        if ($response -ne "y") {
            Write-Step "跳过 API Key 配置"
            return
        }
    }
    
    Write-Host ""
    Write-Step "请选择要使用的模型:"
    Write-Host ""
    Write-Host "  1) DeepSeek（推荐，免费额度高，每天 4000 万 token）"
    Write-Host "  2) 通义千问（阿里）"
    Write-Host "  3) 智谱 GLM"
    Write-Host "  4) Kimi（月暗）"
    Write-Host "  5) 其他（稍后手动配置）"
    Write-Host ""
    $choice = Read-Host "请输入选项 [1-5] 或直接回车跳过"
    
    switch ($choice) {
        "1" {
            Write-Host ""
            $apiKey = Read-Host "请输入 DeepSeek API Key"
            if ($apiKey) {
                "DEEPSEEK_API_KEY=$apiKey" | Out-File -FilePath $envFile -Encoding UTF8
                Write-Success "已保存 DeepSeek API Key"
            }
        }
        "2" {
            Write-Host ""
            $apiKey = Read-Host "请输入通义千问 API Key"
            if ($apiKey) {
                "TONGYI_API_KEY=$apiKey" | Out-File -FilePath $envFile -Encoding UTF8
                Write-Success "已保存通义千问 API Key"
            }
        }
        "3" {
            Write-Host ""
            $apiKey = Read-Host "请输入智谱 GLM API Key"
            if ($apiKey) {
                "GLM_API_KEY=$apiKey" | Out-File -FilePath $envFile -Encoding UTF8
                Write-Success "已保存智谱 GLM API Key"
            }
        }
        "4" {
            Write-Host ""
            $apiKey = Read-Host "请输入 Kimi API Key"
            if ($apiKey) {
                "KIMI_API_KEY=$apiKey" | Out-File -FilePath $envFile -Encoding UTF8
                Write-Success "已保存 Kimi API Key"
            }
        }
        default {
            Write-Step "跳过 API Key 配置"
            if (-not (Test-Path $envFile)) {
                Copy-Item (Join-Path $InstallDir ".env.example") $envFile
                Write-Warning "已创建 .env 文件，请编辑并填入你的 API Key"
            }
        }
    }
}

# 验证安装
function Test-Installation {
    param([string]$VenvPath)
    
    Write-Step "验证安装..."
    
    $omcPath = Join-Path $VenvPath "Scripts\omc.exe"
    
    if (Test-Path $omcPath) {
        $version = & $omcPath --version 2>&1
        Write-Success "CLI 安装成功: $version"
    }
    else {
        Write-Warning "CLI 验证失败，请检查安装"
    }
}

# 打印使用说明
function Show-Usage {
    param([string]$InstallDir, [bool]$hasApiKey)
    
    Write-Host ""
    Write-Host "========================================"
    Write-Host "  安装完成！" -ForegroundColor Green
    Write-Host "========================================"
    Write-Host ""
    Write-Host "使用方法:"
    Write-Host ""
    Write-Host "  1. 激活虚拟环境:"
    Write-Host "     cd $InstallDir"
    Write-Host "     .\.venv\Scripts\Activate.ps1"
    Write-Host ""
    Write-Host "  2. 运行 CLI:"
    Write-Host "     omc --help"
    Write-Host ""
    Write-Host "  3. 或者直接使用:"
    Write-Host "     $InstallDir\.venv\Scripts\omc.exe --help"
    Write-Host ""
    
    if (-not $hasApiKey) {
        Write-Host "  4. 配置 API Key（如果还没配置）:"
        Write-Host "     notepad $InstallDir\.env"
        Write-Host ""
        Write-Host "  推荐使用 DeepSeek（免费额度高）:"
        Write-Host "     https://platform.deepseek.com/"
        Write-Host ""
    }
    
    Write-Host "========================================"
    Write-Host ""
    Write-Host "快速开始:"
    Write-Host "  omc init my-project      # 初始化项目"
    Write-Host "  omc plan ""任务描述""   # 规划任务"
    Write-Host "  omc run                  # 执行任务"
    Write-Host ""
}

# 主安装流程
function Main {
    Write-Host ""
    Write-Host "========================================"
    Write-Host "  Oh My Coder 一键安装脚本 (Windows)"
    Write-Host "========================================"
    Write-Host ""
    
    # 检查环境
    $pythonCmd = Test-Python
    $pipOk = Test-Pip -PythonCmd $pythonCmd
    
    # 准备仓库
    Initialize-Repository -RepoUrl $RepoUrl -InstallDir $InstallDir
    
    # 安装
    $venvPath = New-VirtualEnvironment -PythonCmd $pythonCmd -InstallDir $InstallDir
    Install-Dependencies -VenvPath $venvPath -InstallDev:$InstallDev
    Set-ApiKey -InstallDir $InstallDir -SkipApiKey:$SkipApiKey
    Test-Installation -VenvPath $venvPath
    
    # 检查是否配置了 API Key
    $envFile = Join-Path $InstallDir ".env"
    $hasApiKey = $false
    if (Test-Path $envFile) {
        $content = Get-Content $envFile -Raw
        if ($content -match "API_KEY=") {
            $hasApiKey = $true
        }
    }
    
    Show-Usage -InstallDir $InstallDir -hasApiKey:$hasApiKey
}

# 运行
Main
