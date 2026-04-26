# AGENTS_CHECKLIST.md — 提交前自检清单

> 每次提交代码前逐项检查，全部 ✅ 后再 commit。

## HTTP 状态码

- [ ] **429 Rate Limit** — 不重试当前 provider，直接 failover
- [ ] **401 Unauthorized** — 重试 3 次后 failover；检查 API Key 配置
- [ ] **403 Forbidden** — 同 401 逻辑
- [ ] **500 Server Error** — 重试 3 次（递增等待），再 failover
- [ ] **502/503/504 Gateway Error** — 同 500 逻辑
- [ ] **网络超时 (ConnectTimeout/ReadTimeout)** — 重试 3 次后 failover

## 错误路径

- [ ] 所有 provider 均失败 → 抛 NoModelAvailableError
- [ ] 所有 provider 均 429 → 抛 RateLimitError（含建议）
- [ ] DeepSeek 适配器 HTTP 错误 → 抛 DeepSeekAPIError（含 status code）
- [ ] DeepSeek 适配器网络错误 → 抛 DeepSeekAPIError（含 "网络请求失败"）
- [ ] 缓存命中 → 跳过网络请求，直接返回
- [ ] 异常不影响后续请求（路由器状态一致）

## 空值 / 非法参数兜底

- [ ] 空 messages 列表 → 不 crash，正常路由
- [ ] API Key 为 None → 模型不初始化，跳过该 provider
- [ ] JSON 响应缺少 choices 字段 → 抛异常不静默吞掉
- [ ] JSON 响应 usage 缺失 → 默认 0 token
- [ ] 复杂度非法值 → 降级为 medium
- [ ] 未知 TaskType → 默认 medium tier

## 通用检查

- [ ] `python3 -m pytest tests/ -q` — 全部通过
- [ ] `python3 -m ruff check --fix src/ tests/` — 无 lint
- [ ] `python3 -m black src/ tests/` — 格式一致
- [ ] `git diff HEAD src/` — 无意外改动
- [ ] 新代码有对应测试
- [ ] 无硬编码路径 / 用户名 / API Key
- [ ] Python 3.9 兼容：用 `Union` 不用 `|`，`Optional` 不用 `X | None`
