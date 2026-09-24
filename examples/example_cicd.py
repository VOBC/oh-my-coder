#!/usr/bin/env python3
"""
CI/CD 集成示例 - 展示如何在 CI 环境中使用 Oh My Coder

适用场景：
- GitHub Actions
- GitLab CI
- Jenkins
- 任何 CI/CD 环境

运行方式：
    python examples/example_cicd.py

前置条件：
    export DEEPSEEK_API_KEY=your_key_here
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


# ============================================================
# 场景 1: GitHub Actions
# ============================================================
def demo_github_actions():
    """GitHub Actions 集成示例"""
    print("\n" + "=" * 60)
    print("场景 1: GitHub Actions 集成")
    print("=" * 60)

    workflow_yaml = """# .github/workflows/code-review.yml
name: Code Review

on:
  pull_request:
    paths:
      - "**.py"
      - "src/**"
      - "tests/**"

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install Oh My Coder
        run: |
          pip install oh-my-coder

      - name: Run Code Review
        env:
          DEEPSEEK_API_KEY: \\${{ secrets.DEEPSEEK_API_KEY }}
        run: |
          omc run "审查 PR 中变更的代码" \\
            --workflow review \\
            --context "\\${{ github.event.pull_request.title }}" \\
            --output review-report.md

      - name: Upload Review Report
        uses: actions/upload-artifact@v4
        with:
          name: code-review-report
          path: review-report.md

      - name: Post Review Comment
        uses: actions/github-script@v7
        with:
          script: |
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: "Code review completed. See artifacts for details."
            })
"""

    print("\n  工作流文件内容:")
    print("-" * 50)
    print(workflow_yaml)

    # 实际生成的配置
    print("\n  推荐的 CI 专用配置 (config/ci-review.yaml):")
    print("-" * 50)
    ci_config = """\
# CI 环境专用配置 - 高效、快速、最小输出
name: ci-reviewer
model: deepseek
temperature: 0.2

environment:
  max_tokens: 8000
  timeout: 60
  retry: 1  # CI 环境中减少重试，快速失败

permissions:
  allowed_patterns:
    - "^cat"
    - "^grep"
    - "^git diff"
    - "^ruff"
    - "^flake8"
  denied_patterns:
    - ".*"  # CI 中禁止所有写入操作

prompts:
  system: |
    你是一个严格的 CI 代码审查机器人。
    只报告阻塞性问题，简洁输出，不要废话。
    输出格式：
    ## 阻塞问题: [无 | 列表]
    ## 建议: [最多 3 条]
"""
    print(ci_config)


# ============================================================
# 场景 2: GitLab CI
# ============================================================
def demo_gitlab_ci():
    """GitLab CI 集成示例"""
    print("\n" + "=" * 60)
    print("场景 2: GitLab CI 集成")
    print("=" * 60)

    gitlab_ci = """# .gitlab-ci.yml
stages:
  - test
  - review

code-review:
  stage: review
  image: python:3.11-slim
  before_script:
    - pip install oh-my-coder
  script:
    - omc run "审查变更的代码" --workflow review
  artifacts:
    reports:
      markdown: review-report.md
    expire_in: 1 week
  only:
    - merge_requests
  variables:
    DEEPSEEK_API_KEY: $DEEPSEEK_API_KEY
"""

    print("\n  .gitlab-ci.yml 示例:")
    print("-" * 50)
    print(gitlab_ci)


# ============================================================
# 场景 3: Pre-commit Hook
# ============================================================
def demo_precommit():
    """Pre-commit Hook 集成"""
    print("\n" + "=" * 60)
    print("场景 3: Pre-commit Hook 集成")
    print("=" * 60)

    pre_commit_config = """\
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: omc-review
        name: Oh My Coder Review
        entry: omc run "审查暂存的变更" --workflow review
        language: system
        pass_filenames: true
        stages: [commit-msg, pre-commit]
"""

    print("\n  .pre-commit-config.yaml 示例:")
    print("-" * 50)
    print(pre_commit_config)

    hook_script = """\
#!/bin/bash
# .git/hooks/pre-commit (可选自定义钩子)

# 只在有暂存文件时运行审查
STAGED_FILES=$(git diff --cached --name-only --diff-filter=ACM | grep '\\.py$')

if [ -n "$STAGED_FILES" ]; then
    echo "🔍 运行 Oh My Coder 代码审查..."
    omc run "审查以下变更: $STAGED_FILES" --workflow review --no-confirm

    if [ $? -ne 0 ]; then
        echo "❌ 代码审查未通过，请修复后重试"
        exit 1
    fi
fi
"""
    print("\n  自定义 pre-commit 钩子:")
    print("-" * 50)
    print(hook_script)


# ============================================================
# 场景 4: Dockerfile 集成
# ============================================================
def demo_dockerfile():
    """Docker 环境集成"""
    print("\n" + "=" * 60)
    print("场景 4: Docker 环境集成")
    print("=" * 60)

    dockerfile = """# Dockerfile.review
FROM python:3.11-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir oh-my-coder

# 复制应用代码
COPY . .

# 默认命令：运行审查
CMD ["omc", "run", "审查 /app 代码", "--workflow", "review"]
"""

    docker_compose = """# docker-compose.yml
services:
  review:
    build:
      context: .
      dockerfile: Dockerfile.review
    environment:
      - DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY}
    volumes:
      - ./src:/app/src:ro
    command: omc run "审查 /app/src" --workflow review --output /app/report.md
"""

    print("  Dockerfile.review:")
    print("-" * 50)
    print(dockerfile)
    print("\n  docker-compose.yml:")
    print("-" * 50)
    print(docker_compose)


# ============================================================
# 场景 5: 实际 CI 脚本
# ============================================================
def demo_ci_script():
    """实际可用的 CI 脚本"""
    print("\n" + "=" * 60)
    print("场景 5: 实际 CI 脚本")
    print("=" * 60)

    ci_script = """#!/bin/bash
# scripts/ci-review.sh - 在 CI 中运行的审查脚本

set -e

echo "🤖 开始自动化代码审查..."

# 获取变更文件
CHANGED_FILES=$(git diff --name-only origin/main...HEAD 2>/dev/null || git diff --name-only HEAD~1..HEAD)

if [ -z "$CHANGED_FILES" ]; then
    echo "没有变更文件，跳过审查"
    exit 0
fi

echo "变更文件:"
echo "$CHANGED_FILES"

# 运行审查
REPORT_FILE="code-review-$(date +%Y%m%d-%H%M%S).md"

omc run "审查以下变更的代码质量: $CHANGED_FILES" \\
    --workflow review \\
    --output "$REPORT_FILE" \\
    --no-confirm

# 检查结果
if [ -f "$REPORT_FILE" ]; then
    echo "✅ 审查报告已生成: $REPORT_FILE"
    cat "$REPORT_FILE"

    # 如果包含严重问题，退出失败
    if grep -q "阻塞" "$REPORT_FILE"; then
        BLOCKING=$(grep -A 5 "阻塞" "$REPORT_FILE" || true)
        if [ -n "$BLOCKING" ] && [ "$BLOCKING" != "阻塞问题: [无]" ]; then
            echo "❌ 发现阻塞问题，CI 失败"
            exit 1
        fi
    fi
else
    echo "⚠️  未生成审查报告，继续执行"
fi

echo "✅ CI 审查完成"
"""

    print("  scripts/ci-review.sh:")
    print("-" * 50)
    print(ci_script)


# ============================================================
# 主函数
# ============================================================
def main():
    print(
        """
╔══════════════════════════════════════════════════════╗
║        Oh My Coder - CI/CD 集成示例                  ║
╚══════════════════════════════════════════════════════╝
    """
    )

    demos = [
        ("GitHub Actions", demo_github_actions),
        ("GitLab CI", demo_gitlab_ci),
        ("Pre-commit Hook", demo_precommit),
        ("Docker 集成", demo_dockerfile),
        ("CI 审查脚本", demo_ci_script),
    ]

    for name, demo_fn in demos:
        try:
            demo_fn()
        except Exception as e:
            print(f"\n  ⚠️  {name} 演示出错: {e}")

    print(
        """
╔══════════════════════════════════════════════════════╗
║                   示例运行完毕                        ║
║                                                        ║
║  快速开始:                                             ║
║  1. 复制 relevant 的配置到你的项目                    ║
║  2. 设置 DEEPSEEK_API_KEY 环境变量                     ║
║  3. 配置 CI_SECRET 存储 API Key                       ║
║  4. 推送代码，观察自动审查结果                         ║
╚══════════════════════════════════════════════════════╝
    """
    )


if __name__ == "__main__":
    main()
