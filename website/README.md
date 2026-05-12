# Oh My Coder 官网

## 部署方式

### GitHub Pages（推荐）

1. 进入仓库设置：`Settings > Pages`
2. Source 选择 **Deploy from a branch**
3. Branch: `main`，Folder: `/website`
4. 保存后等待 1-2 分钟
5. 访问：`https://vobc.github.io/oh-my-coder`

### 本地预览

```bash
# 进入 website 目录
cd website

# Python 简单服务器
python3 -m http.server 8080

# 或 Node.js
npx serve .
```

## 文件结构

```
website/
├── index.html      # 主页面（单页应用）
├── README.md       # 本文件
└── CNAME           # 自定义域名（可选）
```

## 自定义域名（可选）

1. 在 `CNAME` 文件中写入域名，如：`oh-my-coder.com`
2. 在域名服务商添加 CNAME 记录指向 `vobc.github.io`
3. GitHub Pages 设置中配置自定义域名

## 技术栈

- 纯 HTML + CSS + JavaScript
- 无构建工具，无依赖
- 响应式设计，支持移动端
