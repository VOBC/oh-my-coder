# 教程

## 场景一：实现新功能

```bash
omc run "为博客系统实现评论功能"
```

系统会自动：
1. 探索现有项目结构
2. 分析评论功能需求
3. 设计数据库表和 API
4. 生成代码
5. 运行测试验证

## 场景二：代码审查

```bash
omc run "审查 src/ 目录的代码质量" -w review
```

审查内容：
- 代码坏味道检测
- 安全漏洞扫描
- 性能问题识别
- 最佳实践建议

## 场景三：修复 Bug

```bash
omc run "修复用户登录接口的并发安全问题" -w debug
```

流程：
1. 定位问题根因（TracerAgent）
2. 分析问题模式
3. 制定修复方案
4. 执行修复
5. 验证修复正确性

## 场景四：后台长时间任务

```bash
omc quest start "实现完整的用户管理系统"
```

- 后台执行，不阻塞终端
- 实时推送进度（SSE）
- 支持暂停/恢复/取消

## 场景五：团队协作

```bash
# 创建团队
omc team create my-team

# 查看团队统计
omc team stats my-team --period week
```

## 场景六：利用历史经验

```bash
# 能力包自动学习
# 工作流完成后，系统自动评估是否值得沉淀经验
# 经验自动注入到后续 Agent 的系统 Prompt
```

## 调试技巧

### 查看 Agent 执行日志

```bash
omc run "..." -v  # 详细输出
```

### 保存检查点

```bash
omc checkpoint save "完成核心逻辑"
# 继续工作...
omc checkpoint restore chk_001  # 如需回退
```

### 使用特定模型

```bash
export OMC_DEFAULT_MODEL=deepseek-reasoner
omc run "实现复杂算法"
```
