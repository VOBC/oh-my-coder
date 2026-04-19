# 🧪 测试

> 本文从 README.md 迁移而来。

## 🧪 测试

```bash
# 运行所有测试（770 个测试）
pytest

# 运行指定测试
pytest tests/test_web.py -v

# 带覆盖率
pytest --cov=src --cov-report=term-missing

# 仅 Web 界面测试
pytest tests/test_web.py -v

# 仅集成测试
pytest tests/test_integration.py -v

# 仅单元测试
pytest -m unit -v
```

---

