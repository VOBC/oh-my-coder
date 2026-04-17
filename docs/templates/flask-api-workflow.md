# Flask API 开发工作流

## 模板信息
- **名称**: flask-api
- **类别**: workflow
- **适用场景**: RESTful API 开发、Web 服务开发
- **预计时间**: 30-60 分钟

## 工作流定义

```yaml
name: flask-api
description: Flask API 开发工作流 - 从设计到部署
version: 1.0.0

steps:
  - agent: architect
    description: 设计 API 架构和数据模型
    timeout: 300
    
  - agent: planner
    description: 制定开发计划和任务分解
    dependencies: [architect]
    timeout: 180
    
  - agent: executor
    description: 实现 Flask 路由和业务逻辑
    dependencies: [planner]
    timeout: 600
    
  - agent: test-engineer
    description: 编写单元测试和集成测试
    dependencies: [executor]
    timeout: 300
    
  - agent: verifier
    description: 运行测试验证功能正确性
    dependencies: [test-engineer]
    timeout: 180

environment:
  framework: flask
  python_version: "3.9"
  required_packages:
    - flask
    - flask-restful
    - pytest
    - pytest-cov
```

## 使用说明

### 快速开始

```bash
omc template use flask-api --task "创建用户管理 API，包含 CRUD 操作"
```

### 手动触发

```bash
omc run build --workflow flask-api --task "开发商品管理 API"
```

### 预期产出

1. **架构设计文档** (`docs/api_design.md`)
   - API 端点列表
   - 数据模型定义
   - 认证授权方案

2. **代码实现** (`app/`, `routes/`, `models/`)
   - Flask 应用骨架
   - RESTful 路由
   - 数据模型
   - 中间件

3. **测试用例** (`tests/`)
   - 单元测试
   - 集成测试
   - 测试覆盖率报告

## 最佳实践

1. **API 设计原则**
   - 遵循 RESTful 规范
   - 使用统一的响应格式
   - 版本控制（/api/v1/）

2. **安全性**
   - 输入验证
   - 错误处理
   - 日志记录

3. **性能优化**
   - 数据库索引
   - 缓存策略
   - 异步处理

## 示例任务

- "创建用户认证 API，支持 JWT"
- "开发文件上传下载 API"
- "构建电商订单管理 API"

## 注意事项

- 确保 Python 环境已安装 Flask
- 建议使用虚拟环境
- 测试数据库使用 SQLite，生产环境切换到 PostgreSQL

## 相关资源

- [Flask 官方文档](https://flask.palletsprojects.com/)
- [Flask-RESTful 扩展](https://flask-restful.readthedocs.io/)
- [API 设计指南](https://restfulapi.net/)
