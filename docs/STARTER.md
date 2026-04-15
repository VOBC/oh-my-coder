# 入门教程（小白版）

> 🎉 零基础？没碰过 AI 编程工具？没问题！跟着做就行。

## 你需要什么

一台电脑，就这些。不需要付费，不需要翻墙。

我们用 **GLM-4-Flash**，智谱 AI 的模型，**永久免费**。

## 准备工作（10 分钟）

### 1. 安装 Python

**Mac 用户**：

```bash
# 打开终端，输入：
brew install python
```

没有 brew？先装一个：[brew.sh](https://brew.sh/)

**Windows 用户**：

去看 [Windows 安装指南](WINDOWS_INSTALL.md)，写得很详细。

**Linux 用户**：

```bash
sudo apt install python3 python3-pip python3-venv
```

### 2. 获取免费 API Key

1. 打开 [智谱开放平台](https://open.bigmodel.cn/)
2. 注册账号（手机号就行）
3. 登录后，进入 API Keys 页面
4. 点「创建 API Key」，复制下来

> 🔑 这个 Key 是免费的，GLM-4-Flash 永久免费使用。

### 3. 安装 Oh My Coder

```bash
# 下载项目
git clone https://github.com/VOBC/oh-my-coder.git
cd oh-my-coder

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Mac/Linux:
source venv/bin/activate
# Windows PowerShell:
.\venv\Scripts\Activate.ps1

# 安装
pip install -e .
```

### 4. 配置 API Key

```bash
# Mac/Linux:
export GLM_API_KEY="你刚才复制的Key"

# Windows PowerShell:
$env:GLM_API_KEY = "你刚才复制的Key"
```

搞定！来验证一下：

```bash
omc --version
```

看到版本号就说明安装成功了 🎉

---

## 实操案例 1：写一个小工具

**目标**：让 AI 帮你写一个文件批量重命名工具。

```bash
omc run "写一个 Python 小工具：把指定目录下的图片文件按日期重命名，格式为 YYYYMMDD_序号.扩展名"
```

AI 会自动完成：分析需求 → 设计方案 → 写代码 → 验证。

你可能看到这样的输出：

```
🚀 Oh My Coder
任务: 写一个 Python 小工具：把指定目录下的图片文件按日期重命名
工作流: build

✅ Explore    → 识别项目结构
✅ Analyst    → 分析需求：读取 EXIF 日期、按日期排序、批量重命名
✅ Architect  → 设计单文件 CLI 工具
✅ Executor   → 生成 rename_photos.py (87 行)
✅ Verifier   → 代码检查通过

完成！
```

**看看 AI 生成的文件**：

```bash
# 找到生成的文件
ls *.py
# 或查看内容
cat rename_photos.py
```

试试运行：

```bash
python rename_photos.py --help
```

> 💡 第一次跑的时候觉得神奇？习惯就好。这就是 AI 编程——你描述需求，AI 写代码。

---

## 实操案例 2：修复一个报错

**目标**：你有一段代码报错了，让 AI 帮你修。

先造一个有 bug 的文件：

```bash
# 创建一个有 bug 的 Python 文件
cat > buggy.py << 'EOF'
def calculate_average(numbers):
    total = 0
    for n in numbers:
        total += n
    return total / len(numbers)

# 测试
print(calculate_average([1, 2, 3, 4, 5]))
print(calculate_average([]))  # 这里会报错！除以零
EOF
```

运行它，果然报错了：

```bash
python buggy.py
# 输出: 3.0
# 然后报错: ZeroDivisionError: division by zero
```

让 AI 来修：

```bash
omc run "修复 buggy.py 中的除零错误，空列表应该返回 0" -w debug
```

AI 会定位问题、生成修复方案。修复后的代码可能是：

```python
def calculate_average(numbers):
    if not numbers:
        return 0
    total = 0
    for n in numbers:
        total += n
    return total / len(numbers)
```

> 🎯 这个例子很小，但想象一下：一个 500 行的文件报了一个奇怪的错，AI 能帮你快速定位和修复，这就是价值。

---

## 实操案例 3：生成一段文档

**目标**：给一段代码自动生成 API 文档。

先写一个简单的模块：

```bash
cat > myapi.py << 'EOF'
class UserAPI:
    """用户管理 API"""
    
    def __init__(self, base_url, api_key):
        self.base_url = base_url
        self.api_key = api_key
        self.headers = {"Authorization": f"Bearer {api_key}"}
    
    def get_user(self, user_id):
        """获取用户信息"""
        import httpx
        resp = httpx.get(f"{self.base_url}/users/{user_id}", headers=self.headers)
        return resp.json()
    
    def create_user(self, name, email):
        """创建用户"""
        import httpx
        resp = httpx.post(
            f"{self.base_url}/users",
            json={"name": name, "email": email},
            headers=self.headers
        )
        return resp.json()
    
    def delete_user(self, user_id):
        """删除用户"""
        import httpx
        resp = httpx.delete(f"{self.base_url}/users/{user_id}", headers=self.headers)
        return resp.json()
EOF
```

让 AI 生成文档：

```bash
omc run "为 myapi.py 生成完整的 API 文档，包括：类说明、每个方法的参数、返回值、使用示例"
```

AI 会生成格式规范的文档，可能包含：

- 类概述和使用场景
- 每个方法的参数表和类型
- 返回值结构
- 完整的调用示例代码

> 📝 写文档是最枯燥的事，让 AI 做就好了。

---

## 下一步可以做什么

恭喜！你已经会用 Oh My Coder 了 🎉

### 换一个更强的模型

GLM-4-Flash 免费但能力有限。如果你需要更强的代码能力：

| 模型 | 价格 | 适合 |
|------|------|------|
| DeepSeek-V3 | 极低（几毛/天） | 代码生成、日常开发 |
| DeepSeek-R1 | 低 | 复杂推理、架构设计 |
| Kimi | 低 | 大项目、长文件分析 |

获取 DeepSeek Key：[platform.deepseek.com](https://platform.deepseek.com/)

```bash
export DEEPSEEK_API_KEY="你的Key"
```

系统会自动在 GLM 和 DeepSeek 之间选择最优模型。

### 探索更多 Agent

Oh My Coder 有 30 个专业 Agent：

```bash
# 查看所有 Agent
omc agents

# 代码审查
omc run "审查当前项目的代码质量" -w review

# 生成测试
omc run "为 src/ 目录生成单元测试" -w test

# 性能优化
omc run "分析性能瓶颈并给出优化建议"
```

### 试试不同工作流

```bash
# 构建模式：完整的开发流程
omc run "实现一个 TODO API" -w build

# 调试模式：定位和修复 Bug
omc run "修复登录超时的问题" -w debug

# 审查模式：代码质量 + 安全
omc run "审查 src/api 目录" -w review

# 结对编程：Explorer + Critic 交替审查
omc run "重构数据库模块" -w pair
```

### 加入社区

- ⭐ 给项目点个 Star：[github.com/VOBC/oh-my-coder](https://github.com/VOBC/oh-my-coder)
- 🐛 遇到问题？[提交 Issue](https://github.com/VOBC/oh-my-coder/issues)
- 💬 想聊聊天？[讨论区](https://github.com/VOBC/oh-my-coder/discussions)

---

> 💪 记住：所有高手都是从新手过来的。你已经迈出了第一步，继续用下去，你会发现 AI 编程越用越顺手。
