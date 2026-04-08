"""
CLI 工具示例

演示如何使用 Oh My Coder 开发命令行工具。

场景：实现一个项目管理 CLI 工具
"""

# ============================================================
# 第一步：定义 CLI 工具需求
# ============================================================

# CLI 命令：
# omc run "设计并实现一个项目管理 CLI 工具 'pm'，功能包括：
# 1. 创建项目：pm new <project_name>
# 2. 添加任务：pm add <task_name> [--priority high|medium|low]
# 3. 列出任务：pm list [--status all|todo|doing|done]
# 4. 开始任务：pm start <task_id>
# 5. 完成任务：pm done <task_id>
# 6. 删除任务：pm delete <task_id>
# 7. 统计报告：pm report [--weekly|--monthly]
# 要求：使用 Typer 框架，支持 SQLite 存储，彩色输出" -w build

# ============================================================
# 预期生成的代码结构
# ============================================================

"""
pm/
├── __init__.py
├── __main__.py          # 入口点
├── cli.py               # CLI 命令定义
├── core/
│   ├── __init__.py
│   ├── database.py      # 数据库操作
│   ├── models.py        # 数据模型
│   └── report.py        # 报告生成
├── utils/
│   ├── __init__.py
│   ├── display.py       # 显示工具
│   └── config.py        # 配置管理
└── tests/
    ├── __init__.py
    └── test_cli.py      # CLI 测试
"""

# ============================================================
# 示例：生成的 CLI 命令
# ============================================================

import typer
from typing import Optional
from pathlib import Path
from enum import Enum
from rich.console import Console
from rich.table import Table
from rich.progress import track
from datetime import datetime, timedelta
import json

app = typer.Typer(
    name="pm",
    help="📋 项目管理 CLI 工具",
    add_completion=True,
)
console = Console()


class Priority(str, Enum):
    """任务优先级"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Status(str, Enum):
    """任务状态"""
    TODO = "todo"
    DOING = "doing"
    DONE = "done"


# ============================================================
# 项目命令
# ============================================================

@app.command("new")
def create_project(
    name: str = typer.Argument(..., help="项目名称"),
    description: str = typer.Option(None, "--desc", "-d", help="项目描述"),
):
    """创建新项目"""
    from .core.database import Database
    
    db = Database()
    project = db.create_project(name, description)
    
    console.print(f"✅ 项目创建成功！", style="green")
    console.print(f"   项目ID: {project['id']}")
    console.print(f"   名称: {project['name']}")
    
    # 切换到新项目
    db.set_current_project(project['id'])
    console.print(f"   已切换到项目: {name}", style="cyan")


@app.command("projects")
def list_projects():
    """列出所有项目"""
    from .core.database import Database
    
    db = Database()
    projects = db.get_all_projects()
    
    table = Table(title="📁 项目列表")
    table.add_column("ID", style="cyan")
    table.add_column("名称", style="green")
    table.add_column("任务数", justify="right")
    table.add_column("创建时间")
    
    for p in projects:
        task_count = db.get_task_count(p['id'])
        table.add_row(
            str(p['id']),
            p['name'],
            str(task_count),
            p['created_at'][:10]
        )
    
    console.print(table)


# ============================================================
# 任务命令
# ============================================================

@app.command("add")
def add_task(
    name: str = typer.Argument(..., help="任务名称"),
    priority: Priority = typer.Option(Priority.MEDIUM, "--priority", "-p", help="优先级"),
    due_date: str = typer.Option(None, "--due", "-d", help="截止日期 (YYYY-MM-DD)"),
):
    """添加新任务"""
    from .core.database import Database
    
    db = Database()
    project_id = db.get_current_project()
    
    if not project_id:
        console.print("❌ 请先创建或选择一个项目", style="red")
        raise typer.Exit(1)
    
    # 解析截止日期
    due = None
    if due_date:
        try:
            due = datetime.strptime(due_date, "%Y-%m-%d")
        except ValueError:
            console.print("❌ 日期格式错误，请使用 YYYY-MM-DD", style="red")
            raise typer.Exit(1)
    
    task = db.create_task(
        project_id=project_id,
        name=name,
        priority=priority.value,
        due_date=due
    )
    
    # 根据优先级显示不同颜色
    color = {"high": "red", "medium": "yellow", "low": "blue"}[priority.value]
    
    console.print(f"✅ 任务已添加", style="green")
    console.print(f"   #{task['id']} [{priority.value}]", style=color)
    console.print(f"   {name}")


@app.command("list")
def list_tasks(
    status: Status = typer.Option(Status.TODO, "--status", "-s", help="任务状态"),
    all_status: bool = typer.Option(False, "--all", "-a", help="显示所有状态"),
):
    """列出任务"""
    from .core.database import Database
    
    db = Database()
    project_id = db.get_current_project()
    
    if not project_id:
        console.print("❌ 请先选择一个项目", style="red")
        raise typer.Exit(1)
    
    if all_status:
        tasks = db.get_tasks(project_id)
    else:
        tasks = db.get_tasks(project_id, status=status.value)
    
    if not tasks:
        console.print("📭 暂无任务", style="yellow")
        return
    
    # 创建表格
    table = Table(title=f"📋 任务列表 ({status.value if not all_status else '全部'})")
    table.add_column("ID", style="cyan", width=4)
    table.add_column("状态", width=6)
    table.add_column("优先级", width=6)
    table.add_column("任务名称")
    table.add_column("截止日期")
    
    status_colors = {"todo": "white", "doing": "yellow", "done": "green"}
    priority_colors = {"high": "red", "medium": "yellow", "low": "blue"}
    
    for t in tasks:
        status_icon = {"todo": "⏳", "doing": "🔄", "done": "✅"}[t['status']]
        table.add_row(
            str(t['id']),
            f"[{status_colors[t['status']]}]{status_icon}[/]",
            f"[{priority_colors[t['priority']]}]{t['priority']}[/]",
            t['name'],
            t['due_date'][:10] if t.get('due_date') else "-"
        )
    
    console.print(table)
    
    # 显示统计
    stats = db.get_task_stats(project_id)
    console.print(f"\n📊 统计: ", style="bold")
    console.print(f"   ⏳ 待办: {stats['todo']}  🔄 进行中: {stats['doing']}  ✅ 已完成: {stats['done']}")


@app.command("start")
def start_task(
    task_id: int = typer.Argument(..., help="任务ID"),
):
    """开始任务"""
    from .core.database import Database
    
    db = Database()
    task = db.update_task_status(task_id, Status.DOING.value)
    
    if task:
        console.print(f"🔄 任务 #{task_id} 已开始", style="yellow")
        console.print(f"   {task['name']}")
    else:
        console.print(f"❌ 任务 #{task_id} 不存在", style="red")


@app.command("done")
def complete_task(
    task_id: int = typer.Argument(..., help="任务ID"),
):
    """完成任务"""
    from .core.database import Database
    
    db = Database()
    task = db.update_task_status(task_id, Status.DONE.value)
    
    if task:
        console.print(f"✅ 任务 #{task_id} 已完成", style="green")
        console.print(f"   {task['name']}")
    else:
        console.print(f"❌ 任务 #{task_id} 不存在", style="red")


@app.command("delete")
def delete_task(
    task_id: int = typer.Argument(..., help="任务ID"),
    force: bool = typer.Option(False, "--force", "-f", help="强制删除，不确认"),
):
    """删除任务"""
    from .core.database import Database
    
    db = Database()
    task = db.get_task(task_id)
    
    if not task:
        console.print(f"❌ 任务 #{task_id} 不存在", style="red")
        raise typer.Exit(1)
    
    if not force:
        confirm = typer.confirm(f"确定删除任务 '{task['name']}'？")
        if not confirm:
            console.print("已取消", style="yellow")
            raise typer.Exit()
    
    db.delete_task(task_id)
    console.print(f"🗑️  任务 #{task_id} 已删除", style="red")


# ============================================================
# 报告命令
# ============================================================

@app.command("report")
def generate_report(
    weekly: bool = typer.Option(False, "--weekly", "-w", help="周报"),
    monthly: bool = typer.Option(False, "--monthly", "-m", help="月报"),
    output: Path = typer.Option(None, "--output", "-o", help="导出路径"),
):
    """生成统计报告"""
    from .core.database import Database
    from .core.report import ReportGenerator
    
    db = Database()
    project_id = db.get_current_project()
    
    if not project_id:
        console.print("❌ 请先选择一个项目", style="red")
        raise typer.Exit(1)
    
    generator = ReportGenerator(db)
    
    if weekly:
        report = generator.weekly_report(project_id)
        title = "📅 周报"
    elif monthly:
        report = generator.monthly_report(project_id)
        title = "📅 月报"
    else:
        report = generator.summary(project_id)
        title = "📊 项目统计"
    
    # 显示报告
    console.print(f"\n{title}\n", style="bold cyan")
    console.print(report['summary'])
    
    # 导出
    if output:
        output.write_text(json.dumps(report, indent=2, ensure_ascii=False))
        console.print(f"\n📄 报告已导出: {output}", style="green")


# ============================================================
# 主命令
# ============================================================

@app.callback()
def main(
    version: bool = typer.Option(False, "--version", "-v", help="显示版本"),
):
    """📋 项目管理 CLI 工具"""
    if version:
        console.print("pm v1.0.0")
        raise typer.Exit()


if __name__ == "__main__":
    app()


# ============================================================
# 示例：生成的数据模型
# ============================================================

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Project:
    """项目模型"""
    id: int
    name: str
    description: Optional[str]
    created_at: datetime
    updated_at: datetime


@dataclass
class Task:
    """任务模型"""
    id: int
    project_id: int
    name: str
    status: str  # todo, doing, done
    priority: str  # high, medium, low
    due_date: Optional[datetime]
    created_at: datetime
    completed_at: Optional[datetime]


# ============================================================
# 示例：生成的数据库操作
# ============================================================

import sqlite3
from pathlib import Path
from typing import List, Optional
from datetime import datetime


class Database:
    """SQLite 数据库操作"""
    
    def __init__(self, db_path: Path = None):
        if db_path is None:
            db_path = Path.home() / ".pm" / "projects.db"
        
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(db_path))
        self.conn.row_factory = sqlite3.Row
        self._create_tables()
    
    def _create_tables(self):
        """创建数据表"""
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                status TEXT DEFAULT 'todo',
                priority TEXT DEFAULT 'medium',
                due_date TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects(id)
            );
            
            CREATE TABLE IF NOT EXISTS current_project (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                project_id INTEGER
            );
        """)
        self.conn.commit()
    
    def create_project(self, name: str, description: str = None) -> dict:
        """创建项目"""
        cursor = self.conn.execute(
            "INSERT INTO projects (name, description) VALUES (?, ?)",
            (name, description)
        )
        self.conn.commit()
        return self.get_project(cursor.lastrowid)
    
    def get_project(self, project_id: int) -> Optional[dict]:
        """获取项目"""
        row = self.conn.execute(
            "SELECT * FROM projects WHERE id = ?", (project_id,)
        ).fetchone()
        return dict(row) if row else None
    
    def get_all_projects(self) -> List[dict]:
        """获取所有项目"""
        rows = self.conn.execute("SELECT * FROM projects ORDER BY created_at DESC").fetchall()
        return [dict(row) for row in rows]
    
    def set_current_project(self, project_id: int):
        """设置当前项目"""
        self.conn.execute(
            "INSERT OR REPLACE INTO current_project (id, project_id) VALUES (1, ?)",
            (project_id,)
        )
        self.conn.commit()
    
    def get_current_project(self) -> Optional[int]:
        """获取当前项目ID"""
        row = self.conn.execute(
            "SELECT project_id FROM current_project WHERE id = 1"
        ).fetchone()
        return row['project_id'] if row else None
    
    def create_task(self, project_id: int, name: str, priority: str = "medium", 
                    due_date: datetime = None) -> dict:
        """创建任务"""
        cursor = self.conn.execute(
            """INSERT INTO tasks (project_id, name, priority, due_date)
               VALUES (?, ?, ?, ?)""",
            (project_id, name, priority, due_date)
        )
        self.conn.commit()
        return self.get_task(cursor.lastrowid)
    
    def get_task(self, task_id: int) -> Optional[dict]:
        """获取任务"""
        row = self.conn.execute(
            "SELECT * FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()
        return dict(row) if row else None
    
    def get_tasks(self, project_id: int, status: str = None) -> List[dict]:
        """获取项目任务"""
        if status:
            rows = self.conn.execute(
                "SELECT * FROM tasks WHERE project_id = ? AND status = ? ORDER BY priority DESC, created_at",
                (project_id, status)
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM tasks WHERE project_id = ? ORDER BY priority DESC, created_at",
                (project_id,)
            ).fetchall()
        return [dict(row) for row in rows]
    
    def update_task_status(self, task_id: int, status: str) -> Optional[dict]:
        """更新任务状态"""
        completed_at = datetime.now() if status == 'done' else None
        self.conn.execute(
            "UPDATE tasks SET status = ?, completed_at = ? WHERE id = ?",
            (status, completed_at, task_id)
        )
        self.conn.commit()
        return self.get_task(task_id)
    
    def delete_task(self, task_id: int):
        """删除任务"""
        self.conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        self.conn.commit()
    
    def get_task_count(self, project_id: int) -> int:
        """获取任务数量"""
        row = self.conn.execute(
            "SELECT COUNT(*) as count FROM tasks WHERE project_id = ?", (project_id,)
        ).fetchone()
        return row['count']
    
    def get_task_stats(self, project_id: int) -> dict:
        """获取任务统计"""
        rows = self.conn.execute(
            "SELECT status, COUNT(*) as count FROM tasks WHERE project_id = ? GROUP BY status",
            (project_id,)
        ).fetchall()
        return {row['status']: row['count'] for row in rows}


# ============================================================
# 第二步：验证和测试
# ============================================================

# CLI 命令：
# omc run "为 pm CLI 工具生成测试用例" -w test

# 测试示例：
"""
import pytest
from typer.testing import CliRunner
from pm.cli import app

runner = CliRunner()


def test_create_project():
    result = runner.invoke(app, ["new", "测试项目"])
    assert result.exit_code == 0
    assert "创建成功" in result.output


def test_add_task():
    # 先创建项目
    runner.invoke(app, ["new", "测试项目"])
    
    # 添加任务
    result = runner.invoke(app, ["add", "测试任务", "-p", "high"])
    assert result.exit_code == 0
    assert "已添加" in result.output


def test_list_tasks():
    runner.invoke(app, ["new", "测试项目"])
    runner.invoke(app, ["add", "任务1"])
    
    result = runner.invoke(app, ["list", "--all"])
    assert result.exit_code == 0


def test_complete_task():
    runner.invoke(app, ["new", "测试项目"])
    runner.invoke(app, ["add", "任务"])
    
    result = runner.invoke(app, ["done", "1"])
    assert result.exit_code == 0
    assert "已完成" in result.output
"""

# ============================================================
# 第三步：打包发布
# ============================================================

# pyproject.toml 配置：
"""
[project]
name = "pm-cli"
version = "1.0.0"
description = "项目管理 CLI 工具"
dependencies = [
    "typer>=0.9.0",
    "rich>=13.0.0",
]

[project.scripts]
pm = "pm.cli:app"

[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"
"""

# 安装和测试：
"""
pip install -e .
pm --version
pm new my_project
pm add "实现用户认证" -p high
pm list --all
pm report --weekly
"""

# ============================================================
# 运行步骤总结
# ============================================================

"""
完整执行流程：

1. 构建 CLI 工具
   omc run "实现 pm CLI 工具" -w build

2. 生成测试
   omc run "生成 CLI 测试用例" -w test

3. 本地测试
   pip install -e .
   pm --help

4. 代码审查
   omc run "审查 CLI 代码" -w review

5. 打包发布
   pip install build
   python -m build
   twine upload dist/*
"""
