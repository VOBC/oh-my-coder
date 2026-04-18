# PR Review 安全清单

> 每个 PR 必须勾选以下安全项才能合并

## 必须检查项（阻塞性）

- [ ] **无 str(e) 泄露**: 所有 `except` 块中没有 `str(e)`，使用 `type(e).__name__` 或 `"Internal server error"`
- [ ] **URL 验证安全**: 没有 `"domain" in url` 模式，使用 `urlparse(url).netloc`
- [ ] **无弱加密**: 没有 `hashlib.md5` / `hashlib.sha1`（非密码用途需注释 `# safe`）
- [ ] **Workflow 权限**: 所有 `.github/workflows/*.yml` 有 `permissions:` 声明
- [ ] **无硬编码密钥**: 没有硬编码 API Key / Password / Token

## 建议检查项（非阻塞性）

- [ ] **无命令注入**: `subprocess` 使用参数列表而非 `shell=True`
- [ ] **输入验证**: 所有用户输入都有验证和净化
- [ ] **路径安全**: 文件路径拼接使用 `pathlib.Path`，避免字符串拼接
- [ ] **日志脱敏**: 日志中没有敏感信息（API Key、密码等）

## 快速自检命令

```bash
# 提交前运行
bash .githooks/pre-commit

# 或手动检查
grep -rn "str(e)" src/ tests/ --include="*.py"
grep -rn 'in.*url' src/ tests/ --include="*.py" | grep -v urlparse
grep -rn "hashlib.md5\|hashlib.sha1" src/ --include="*.py"
```

## 参考文档

- [安全编码规范](../../SECURITY_CODING_GUIDE.md)
- [CodeQL 解决方案](security-whackamole-investigation.md)
- [小麦的 6 条经验](security-whackamole-investigation.md#经验教训整合小麦的-6-条核心经验)

---

**Reviewer**: 请在 PR 中评论 "✅ 安全清单已检查" 确认完成
