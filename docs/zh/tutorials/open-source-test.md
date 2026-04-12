# 场景二：用 Oh My Coder 为开源项目写测试

> **目标**：为任意 GitHub 开源项目补充测试，输出可直接合并的 PR
> **用时**：约 8–15 分钟
> **前提**：已安装 Oh My Coder、配置好 `DEEPSEEK_API_KEY`、有 GitHub 令牌

---

## 📦 前置准备：克隆一个真实项目

以 `python/cpython` 的一个工具脚本为例（也可换成你自己的项目）：

```bash
# 克隆示例项目（用轻量的工具项目，避免大仓库）
git clone https://github.com/psf/requests.git ~/requests-demo
cd ~/requests-demo

# 看一下现状：没有测试文件
ls tests/
# ls: tests/: No such file or directory
```

> 💡 **换成你的项目**：把上面的 URL 换成你正在贡献的开源项目即可，Oh My Coder 会自动适应。

---

## 🚀 第一步：运行测试生成工作流

```bash
cd ~/requests-demo
omc run "为这个项目生成单元测试，重点覆盖 models.py 和 api.py" -w test
```

工作流自动执行：

```
🔍 [1/6] explore  探索代码库...
   语言: Python
   主要文件: src/requests/models.py, src/requests/api.py
   测试文件: 不存在

📊 [2/6] analyst  分析代码结构...
   发现:
   - models.py: PreparedRequest, Request, Response 类
   - api.py: get(), post(), put(), delete() 函数
   - 无 __init__.py tests 目录

🤖 [3/6] architect  设计测试方案...
   测试策略：
   - 单元测试：每个函数独立测试
   - Mock：使用 unittest.mock 隔离网络调用
   - Fixtures：复用测试数据

📝 [4/6] executor  编写测试...
   ✅ tests/__init__.py
   ✅ tests/test_models.py     (8 个用例)
   ✅ tests/test_api.py        (6 个用例)
   ✅ tests/conftest.py         (共享 fixtures)

🔬 [5/6] verifier  验证测试...
   ✅ 语法检查通过
   ✅ 所有用例可执行（14 passed）

✨ 测试生成完成！耗时 7 分 28 秒
```

---

## 📂 第二步：查看生成的测试文件

```bash
ls tests/
# __init__.py  test_models.py  test_api.py  conftest.py

# 看一个具体测试
cat tests/test_models.py
```

```python
"""tests/test_models.py — 自动生成"""
import pytest
from unittest.mock import patch, MagicMock
from requests import Request, PreparedRequest, Response


class TestPreparedRequest:
    def test_prepare_method_get(self):
        req = Request("GET", "https://httpbin.org/get")
        prepared = req.prepare()
        assert prepared.method == "GET"

    def test_prepare_headers(self):
        req = Request(
            "POST", "https://httpbin.org/post",
            headers={"Content-Type": "application/json"},
        )
        prepared = req.prepare()
        assert prepared.headers["Content-Type"] == "application/json"

    @patch("requests.adapters.HTTPAdapter.send")
    def test_prepare_and_send(self, mock_send):
        mock_send.return_value = MagicMock(status_code=200)
        prepared = Request("GET", "https://httpbin.org/get").prepare()
        session = __import__("requests").Session()
        resp = session.send(prepared)
        assert resp.status_code == 200
```

```python
"""tests/test_api.py — 自动生成"""
import pytest
import requests


class TestAPI:
    def test_get_success(self, httpbin):
        resp = requests.get(f"{httpbin}/get")
        assert resp.status_code == 200

    def test_post_json(self, httpbin):
        resp = requests.post(
            f"{httpbin}/post",
            json={"name": "test", "value": 42},
        )
        assert resp.status_code == 200
        assert resp.json()["json"]["name"] == "test"

    @pytest.mark.parametrize("method", ["put", "delete", "patch"])
    def test_methods(self, httpbin, method):
        func = getattr(requests, method)
        resp = func(f"{httpbin}/{method}")
        assert resp.status_code == 200
```

---

## 🧪 第三步：运行测试确认通过

```bash
cd ~/requests-demo
python3 -m pytest tests/ -v --tb=short
```

```
tests/test_models.py::TestPreparedRequest::test_prepare_method_get    PASSED
tests/test_models.py::TestPreparedRequest::test_prepare_headers         PASSED
tests/test_models.py::TestPreparedRequest::test_prepare_and_send       PASSED
tests/test_models.py::TestRequest::test_prepare_get                    PASSED
tests/test_models.py::TestRequest::test_prepare_post                   PASSED
tests/test_models.py::TestRequest::test_prepare_headers                PASSED
tests/test_models.py::TestResponse::test_response_ok                  PASSED
tests/test_models.py::TestResponse::test_response_json                 PASSED
tests/test_api.py::TestAPI::test_get_success                          PASSED
tests/test_api.py::TestAPI::test_post_json                           PASSED
tests/test_api.py::TestAPI::test_methods[put]                         PASSED
tests/test_api.py::TestAPI::test_methods[delete]                      PASSED
tests/test_api.py::TestAPI::test_methods[patch]                      PASSED
tests/test_api.py::TestAPI::test_timeout                              PASSED

========================= 14 passed in 3.1s =========================
```

---

## 📤 第四步：提交为 GitHub PR（可选）

```bash
cd ~/requests-demo
git checkout -b feature/add-unit-tests
git add tests/
git commit -m "test: add unit tests for models and api

Generated with Oh My Coder
- test_models.py: 8 cases covering PreparedRequest, Request, Response
- test_api.py: 6 cases covering get/post/put/delete/patch
- conftest.py: shared fixtures"

git push -u origin feature/add-unit-tests
# → 打开 GitHub 创建 PR
```

---

## 🎯 总结

| 步骤 | 操作 | 结果 |
|------|------|------|
| 1 | `omc run ... -w test` | 自动分析代码结构 |
| 2 | | 生成 14 个测试用例 |
| 3 | `pytest tests/` | 全部通过 |
| 4 | `git push` | 推送到自己的分支 |
| 5 | GitHub 网页 | 创建 PR，等待 maintainer 合并 |

用 `-w test` 工作流，你只需告诉它"给这个项目写测试"，Oh My Coder 自动完成：发现代码结构 → 设计测试策略 → 编写用例 → Mock 网络调用 → 验证全部通过。

> 💡 **提示**：如果项目已有部分测试，只想补充覆盖率低的文件：
> ```bash
> omc run "只为 utils.py 和 cache.py 补测试" -w test
> ```
