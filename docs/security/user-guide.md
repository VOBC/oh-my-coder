# 安全指南 - API密钥管理

## 🚨 重要提醒
**永远不要将真实的API密钥提交到版本控制系统！**

## 发生了什么
- 2026-04-14: GitHub Secret Scanning检测到DeepSeek API密钥泄露
- 泄露的密钥: `sk-c97a288039be450b819a2e80104452b1`
- 泄露位置: 历史提交中的`.env.example`文件
- 处理状态: ✅ 已清理git历史并强制推送

## 处理步骤
1. ✅ 已撤销泄露的DeepSeek API密钥
2. ✅ 已使用git-filter-repo清理git历史
3. ✅ 已强制推送到GitHub
4. ✅ 已更新MEMORY.md删除敏感信息

## 预防措施

### 1. 本地开发环境配置
```bash
# 复制示例文件
cp .env.example .env

# 编辑.env文件，填入你的API密钥
# 注意: .env文件已被.gitignore排除
```

### 2. .env.example文件规范
- 只包含占位符: `your_api_key`
- 不要包含真实的API密钥
- 定期检查是否有误提交

### 3. 预提交检查
```bash
# 运行安全扫描
./scripts/check-secrets.sh

# 或添加到git hooks
cp scripts/check-secrets.sh .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

### 4. 如果发现API密钥泄露
1. **立即撤销密钥** - 在对应平台撤销泄露的密钥
2. **清理git历史** - 使用git-filter-repo或git filter-branch
3. **强制推送** - 更新远程仓库
4. **通知协作者** - 所有人需要重新克隆

## 安全最佳实践

### ✅ 应该做的
- 使用`.env`文件管理API密钥
- 将`.env`添加到`.gitignore`
- 使用环境变量加载API密钥
- 定期轮换API密钥
- 使用最小权限原则

### ❌ 不应该做的
- 不要在代码中硬编码API密钥
- 不要提交`.env`文件到git
- 不要在README中展示真实密钥
- 不要使用过于简单的密钥
- 不要共享个人API密钥

## 紧急联系人
- GitHub Security: https://github.com/security
- DeepSeek Support: https://platform.deepseek.com/

## 更新记录
- 2026-04-14: 创建安全指南，记录API密钥泄露处理过程

---
**记住: 安全是每个人的责任！**