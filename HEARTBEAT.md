# HEARTBEAT.md

## 今日完成（2026-04-11）

### ✅ 5 AI 评测 README 改进（P0全部通过，P1部分完成）
### ✅ notifications.py 标准库导入补全（commit b469fc5）
### ✅ vision.py f-string 多余前缀移除（commit e1dc6bd）
### ✅ 通知渠道扩展至 7 种新平台（commit e1e3283）
### ✅ README 改进 + 配套文件完善（commit 026023e）
### ✅ 文档年份 2025 → 2026（commit d95b2c9）
### ✅ CI 修复：test_document_agent.py 未使用导入、black 格式化（commit 0d61e10）
### ✅ CI 修复：test_vision_agent.py black 格式化（commit e9ea459）

## 待完成任务
- P1-2 README 目录导航（Table of Contents）：未完成，待后续迭代

## 今日教训（已存 MEMORY.md）

1. **black 格式化必须全量**：只修 CI 报的一个文件不够，CI 每次都报新的文件，因为每次 CI 只测全部文件中的一个子集
2. **git push 超时** → `scutil --proxy` 查系统代理，有 HTTPEnable 就加 `-c http.proxy=http://127.0.0.1:4780`
3. **提交前必须跑完整套**：
   ```bash
   python3 -m black src/ tests/
   python3 -m ruff check --fix src/ tests/
   python3 -m pytest tests/ -q
   git diff HEAD src/ tests/
   ```

## 提交前必跑（无豁免）

```bash
# 1. 代码质量三件套（全量，不要只修一个文件）
python3 -m black src/ tests/
python3 -m ruff check --fix src/ tests/
python3 -m pytest tests/ -q

# 2. 本地检查
git diff HEAD src/ tests/ | head -20   # 无输出 = 没有未提交修改
git status

# 3. push（有系统代理时）
git -c http.proxy=http://127.0.0.1:4780 push origin main
```

## 项目状态

- HEAD: `e9ea459`（已推送）
- GitHub: https://github.com/VOBC/oh-my-coder
