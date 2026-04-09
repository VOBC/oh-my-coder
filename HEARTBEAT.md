# HEARTBEAT.md

## 今日完成（2026-04-09）

### CLI 增强 ✅
- [x] `--model` 参数：`deepseek`、`kimi:high` 格式
- [x] `--dry-run` 预览
- [x] `omc config` show/set/list
- [x] 桌面通知（osascript 零依赖）
- [x] 结果验收 UI + 下一步建议
- [x] `load_dotenv()` 让 .env 生效

### 今日教训

**F541 f-string 无占位符（又犯了！）**：
```python
# ❌ 错误 - ruff F541
console.print(f"[dim]text[/dim]")

# ✅ 正确
console.print("[dim]text[/dim]")
```
→ 快速修复：`ruff check --fix`

## 待完成

1. **git push**（网络超时，手动补）
2. **测试覆盖**：为 `notify.py` 加测试
3. **安装脚本 CI**：验证 `install.sh` 干净环境

## 经验教训提醒

**提交前必须运行**：
```bash
pytest && ruff check && black
```
（每次都要跑，不要偷懒）

**Rich console.print**：无 `{}` 占位符时不用 `f` 前缀

**Python 3.9**：`Union[X, Y]` 不要用 `X | Y`

**Typer 命令**：`@app.command("kebab-case")` 显式指定

