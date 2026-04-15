# Windows 安装指南

> 🪟 从零开始，在 Windows 上安装 Oh My Coder

## 第一步：安装 Python

Oh My Coder 需要 **Python 3.10 或更高版本**。

1. 打开浏览器，访问 [python.org/downloads](https://www.python.org/downloads/)
2. 下载最新的 Python 3.10+ 安装包（通常页面顶部就有大按钮）
3. 运行安装程序

> ⚠️ **关键一步**：安装界面底部有一个选项 **「Add Python to PATH」**，**务必勾选！**
>
> `截图：Python 安装界面，红框标注 Add Python to PATH 选项`
>
> 不勾选的话，后续在命令行里敲 `python` 会提示「不是内部或外部命令」，到时候还得手动修环境变量，很麻烦。

4. 点击 **Install Now** 完成安装

验证一下：

```powershell
python --version
# 应该输出类似 Python 3.12.x
```

## 第二步：克隆项目

打开 PowerShell（按 `Win + X`，选择「Windows PowerShell」或「终端」）：

```powershell
# 如果没有 git，先装一个
# 方式1：winget（推荐）
winget install Git.Git

# 方式2：从 https://git-scm.com/download/win 下载安装包
```

然后克隆仓库：

```powershell
cd ~
git clone https://github.com/VOBC/oh-my-coder.git
cd oh-my-coder
```

## 第三步：创建虚拟环境

虚拟环境能把你项目的依赖隔离起来，不会搞乱系统 Python。

```powershell
python -m venv venv
```

激活虚拟环境：

```powershell
# PowerShell
.\venv\Scripts\Activate.ps1

# CMD
.\venv\Scripts\activate.bat
```

激活成功后，命令行前面会出现 `(venv)` 标识：

```
(venv) PS C:\Users\yourname\oh-my-coder>
```

> **PowerShell 权限报错？**
>
> 如果激活时出现类似这样的错误：
>
> ```
> .\venv\Scripts\Activate.ps1 : 无法加载文件，因为在此系统上禁止运行脚本
> ```
>
> 这是 Windows 的执行策略限制。解决方法：
>
> ```powershell
> # 以管理员身份运行 PowerShell，执行：
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```
>
> 然后重新执行 `.\venv\Scripts\Activate.ps1` 就可以了。
>
> 如果你不想改全局策略，也可以用 CMD 代替 PowerShell 来激活虚拟环境。

## 第四步：安装项目

```powershell
pip install -e .
```

> 💡 如果下载速度很慢，可以换国内镜像：
>
> ```powershell
> pip install -e . -i https://pypi.tuna.tsinghua.edu.cn/simple
> ```

安装过程可能需要 1-3 分钟，取决于网速。

## 第五步：配置 API Key

Oh My Coder 需要至少一个模型的 API Key 才能工作。**推荐用 GLM-4-Flash，免费使用。**

### 获取 API Key

1. 访问 [智谱开放平台](https://open.bigmodel.cn/)
2. 注册账号并登录
3. 在 API Keys 页面创建新 Key

### 设置环境变量

**PowerShell（当前会话有效）：**

```powershell
$env:GLM_API_KEY = "你的API Key"
```

**永久生效（写入配置文件）：**

```powershell
# 打开 PowerShell 配置文件
notepad $PROFILE

# 在文件中添加（如果文件不存在就新建）：
$env:GLM_API_KEY = "你的API Key"

# 保存后重启 PowerShell 即可
```

**或者用 .env 文件：**

```powershell
# 复制示例文件
copy examples\.env.example .env

# 编辑 .env，填入真实 Key
notepad .env
```

### 其他模型（可选）

```powershell
# DeepSeek（推荐，性价比高）
$env:DEEPSEEK_API_KEY = "sk-xxx"

# 小米 MiMo（免费）
$env:MIMOAPIKEY = "xxx"

# 更多模型见 docs/guide/models.md
```

## 第六步：验证安装

```powershell
omc --version
```

看到版本号就说明安装成功了！🎉

试试跑一个简单任务：

```powershell
omc explore .
```

## 常见报错 Q&A

### ❌ 「python 不是内部或外部命令」

**原因**：安装 Python 时没勾选「Add Python to PATH」。

**解决**：

1. 重新运行 Python 安装程序，选择 **Modify**
2. 勾选 **「Add Python to environment variables」**
3. 完成后**重启 PowerShell**

或者手动添加：

1. 找到 Python 安装路径（通常是 `C:\Users\你的用户名\AppData\Local\Programs\Python\Python312`）
2. 右键「此电脑」→ 属性 → 高级系统设置 → 环境变量
3. 在「用户变量」的 `Path` 中添加 Python 目录和 `Scripts` 子目录

### ❌ 「pip install 报 SSL 证书错误」

```
Could not fetch URL https://pypi.org/simple/: There was a problem confirming the ssl certificate
```

**原因**：公司内网代理或防火墙拦截了 HTTPS 请求。

**解决**：

```powershell
# 方法1：换国内镜像
pip install -e . -i https://pypi.tuna.tsinghua.edu.cn/simple

# 方法2：信任 pypi（仅限开发机，生产环境不推荐）
pip install -e . --trusted-host pypi.org --trusted-host files.pythonhosted.org
```

### ❌ 「omc 命令找不到」

**原因**：虚拟环境没激活，或者安装失败。

**解决**：

```powershell
# 1. 确认虚拟环境已激活（命令行前面有 (venv)）
.\venv\Scripts\Activate.ps1

# 2. 确认安装成功
pip show oh-my-coder

# 3. 如果还是不行，重新安装
pip install -e .
```

### ❌ 「Permission denied」或权限不足

**原因**：终端没有管理员权限，或者杀毒软件拦截。

**解决**：

1. 右键 PowerShell → **以管理员身份运行**
2. 检查杀毒软件是否拦截了 Python 脚本执行
3. 尝试将项目目录加入杀毒软件白名单

### ❌ 「UnicodeDecodeError」编码错误

**原因**：Windows 默认编码是 GBK，部分文件内容包含中文。

**解决**：

```powershell
# 设置 Python 默认编码为 UTF-8
$env:PYTHONUTF8 = "1"

# 或者写入 PowerShell 配置文件，永久生效
Add-Content $PROFILE '$env:PYTHONUTF8 = "1"'
```

---

## 下一步

- 📖 [入门教程](STARTER.md) - 从零开始用 Oh My Coder
- 🤖 [模型选型指南](MODELS.md) - 选择最适合你的模型
- ❓ [常见问题](FAQ.md) - 更多问题解答
