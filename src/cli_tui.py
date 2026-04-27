"""
TUI 交互界面 - 简易交互界面

基于 Bubble Tea 设计理念，提供键盘驱动的 TUI 体验。

快捷键：
- ↑/↓: 导航
- Enter: 确认
- Esc: 返回/退出
- 1-7: 快速选择工作流
- m: 切换模型
- a: 查看所有 Agent
- q: 退出
"""

from __future__ import annotations

import subprocess
from enum import Enum
from pathlib import Path

import typer
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text


# Rich 14 removed Keys, define manually
class Keys:
    Up = "\x1b[A"
    Down = "\x1b[B"
    Left = "\x1b[D"
    Right = "\x1b[C"
    Enter = "\r"
    Escape = "\x1b"
    CtrlC = "\x03"


app = typer.Typer(help="TUI 交互界面 - 键盘驱动的终端交互")
console = Console()


class State(Enum):
    """TUI 状态机"""

    MAIN = "main"
    WORKFLOW = "workflow"
    MODEL = "model"
    AGENTS = "agents"
    TASK = "task"
    CONFIRM = "confirm"


# 工作流选项
WORKFLOWS = [
    ("explore", "探索代码库", "了解项目结构和代码组织"),
    ("build", "构建/开发", "实现新功能或重构代码"),
    ("debug", "调试修复", "定位和修复 Bug"),
    ("review", "代码审查", "审查代码质量和安全性"),
    ("test", "测试生成", "生成单元测试和集成测试"),
    ("pair", "结对编程", "与 AI 一起协作开发"),
    ("autopilot", "自动驾驶", "全自动完成复杂任务"),
]

# 支持的模型
MODELS = [
    ("deepseek", "DeepSeek", "60元免费额度，速度快"),
    ("glm", "智谱 GLM", "200万 Tokens免费"),
    ("mimo", "MiMo", "1M上下文，完全免费"),
    ("qwen", "通义千问", "阿里云，免费额度"),
    ("wenxin", "文心一言", "百度，免费额度"),
]

# Agent 分类
AGENT_CATEGORIES = {
    "构建/分析": [
        "ExploreAgent",
        "AnalystAgent",
        "PlannerAgent",
        "ArchitectAgent",
        "ExecutorAgent",
        "VerifierAgent",
        "DebuggerAgent",
        "TracerAgent",
        "PerformanceAgent",
    ],
    "审查": [
        "CodeReviewerAgent",
        "SecurityReviewerAgent",
    ],
    "领域": [
        "TestEngineerAgent",
        "DesignerAgent",
        "VisionAgent",
        "DocumentAgent",
        "WriterAgent",
        "ScientistAgent",
        "GitMasterAgent",
        "CodeSimplifierAgent",
        "QATesterAgent",
        "DatabaseAgent",
        "APIAgent",
        "DevOpsAgent",
        "UMLAgent",
        "MigrationAgent",
        "AuthAgent",
        "DataAgent",
    ],
    "协调": [
        "PromptAgent",
        "SelfImprovingAgent",
        "SkillManageAgent",
        "CriticAgent",
    ],
}


class TUISession:
    """TUI 会话状态"""

    def __init__(self):
        self.state = State.MAIN
        self.selected_workflow: str | None = None
        self.selected_model: str = "deepseek"
        self.task_input: str = ""
        self.cursor: int = 0
        self.confirm_choice: bool = False

    def render(self) -> Panel:
        """渲染当前状态"""
        if self.state == State.MAIN:
            return self._render_main()
        if self.state == State.WORKFLOW:
            return self._render_workflow()
        if self.state == State.MODEL:
            return self._render_model()
        if self.state == State.AGENTS:
            return self._render_agents()
        if self.state == State.TASK:
            return self._render_task()
        if self.state == State.CONFIRM:
            return self._render_confirm()
        return Panel("Unknown state")

    def _render_main(self) -> Panel:
        """主菜单"""
        content = Text()
        content.append("🤖 Oh My Coder TUI\n\n", style="bold cyan")
        content.append("请选择操作:\n\n", style="white")

        for i, (key, desc, _) in enumerate(WORKFLOWS):
            marker = "▶ " if i == self.cursor else "  "
            style = "cyan bold" if i == self.cursor else "white"
            content.append(f"{marker}[{i + 1}] {key:<12}", style=style)
            content.append(f" {desc}\n", style="dim")

        content.append("\n[快捷键] ", style="dim")
        content.append("m", style="cyan")
        content.append(" 模型  ", style="dim")
        content.append("a", style="cyan")
        content.append(" Agent  ", style="dim")
        content.append("q", style="cyan")
        content.append(" 退出\n", style="dim")

        return Panel(
            content,
            title="[bold cyan]Oh My Coder TUI[/bold cyan]",
            border_style="cyan",
        )

    def _render_workflow(self) -> Panel:
        """工作流选择"""
        content = Text()
        content.append("📋 选择工作流\n\n", style="bold cyan")

        for i, (key, desc, detail) in enumerate(WORKFLOWS):
            marker = "▶ " if i == self.cursor else "  "
            style = "cyan bold" if i == self.cursor else "white"
            content.append(f"{marker}{key:<12}", style=style)
            content.append(f"{desc} - {detail}\n", style="dim")

        content.append("\n[快捷键] ", style="dim")
        content.append("↑↓", style="cyan")
        content.append(" 导航  ", style="dim")
        content.append("Enter", style="cyan")
        content.append(" 确认  ", style="dim")
        content.append("Esc", style="cyan")
        content.append(" 返回", style="dim")

        return Panel(content, title="[bold]工作流选择[/bold]", border_style="cyan")

    def _render_model(self) -> Panel:
        """模型选择"""
        content = Text()
        content.append("🔧 选择模型\n\n", style="bold cyan")

        for i, (key, name, desc) in enumerate(MODELS):
            marker = "▶ " if i == self.cursor else "  "
            style = "cyan bold" if i == self.cursor else "white"
            current = " ◀ 当前" if key == self.selected_model else ""
            content.append(f"{marker}{name:<12}", style=style)
            content.append(f"{desc}{current}\n", style="dim")

        content.append("\n[快捷键] ", style="dim")
        content.append("↑↓", style="cyan")
        content.append(" 导航  ", style="dim")
        content.append("Enter", style="cyan")
        content.append(" 确认  ", style="dim")
        content.append("Esc", style="cyan")
        content.append(" 返回", style="dim")

        return Panel(content, title="[bold]模型选择[/bold]", border_style="cyan")

    def _render_agents(self) -> Panel:
        """Agent 列表"""
        content = Text()
        content.append("🤖 Agent 清单（共31个）\n\n", style="bold cyan")

        for category, agents in list(AGENT_CATEGORIES.items())[:3]:  # 只显示前3类
            content.append(f"[bold]{category}:[/bold]\n", style="white")
            for agent in agents[:5]:  # 每类只显示5个
                content.append(f"  • {agent}\n", style="dim")
            if len(agents) > 5:
                content.append(f"  ... 共{len(agents)}个\n", style="dim")

        content.append("\n[快捷键] ", style="dim")
        content.append("Esc", style="cyan")
        content.append(" 返回主菜单", style="dim")

        return Panel(
            content,
            title="[bold]Agent 列表[/bold]",
            border_style="cyan",
            width=60,
        )

    def _render_task(self) -> Panel:
        """任务输入"""
        content = Text()
        content.append("📝 输入任务\n\n", style="bold cyan")
        content.append(
            f"工作流: [cyan]{self.selected_workflow}[/cyan]\n", style="white"
        )
        content.append(f"模型: [cyan]{self.selected_model}[/cyan]\n\n", style="white")
        content.append("请描述你的任务:\n", style="dim")
        content.append("[dim]输入任务后按 Enter 确认[/dim]\n\n", style="dim")
        content.append("[快捷键] ", style="dim")
        content.append("Esc", style="cyan")
        content.append(" 返回  ", style="dim")
        content.append("Enter", style="cyan")
        content.append(" 确认任务", style="dim")

        return Panel(content, title="[bold]任务输入[/bold]", border_style="cyan")

    def _render_confirm(self) -> Panel:
        """确认执行"""
        content = Text()
        content.append("✅ 确认执行\n\n", style="bold cyan")
        content.append("命令: [cyan]omc run[/cyan] ", style="white")
        content.append(f'"[yellow]{self.task_input}[/yellow]"', style="white")
        content.append(
            f" [cyan]--workflow {self.selected_workflow}[/cyan]\n", style="white"
        )
        content.append(f"模型: [cyan]{self.selected_model}[/cyan]\n\n", style="white")

        content.append("[快捷键] ", style="dim")
        content.append("y", style="cyan")
        content.append(" 执行  ", style="dim")
        content.append("n", style="cyan")
        content.append(" 返回  ", style="dim")
        content.append("Esc", style="cyan")
        content.append(" 取消", style="dim")

        return Panel(content, title="[bold]确认[/bold]", border_style="cyan")

    def handle_key(self, key: str) -> bool:
        """处理键盘事件，返回是否需要继续"""
        if key == "q":
            return False

        if self.state == State.MAIN:
            return self._handle_main(key)
        if self.state == State.WORKFLOW:
            return self._handle_workflow(key)
        if self.state == State.MODEL:
            return self._handle_model(key)
        if self.state == State.AGENTS:
            return self._handle_agents(key)
        if self.state == State.TASK:
            return self._handle_task(key)
        if self.state == State.CONFIRM:
            return self._handle_confirm(key)

        return True

    def _handle_slash_command(self, raw_input: str) -> bool:
        """检测并执行 /skill 命令，返回是否保持 TUI（False=退出）"""
        # 解析 /skill-name [file-path]
        parts = raw_input.strip().split(maxsplit=2)
        if not parts or not parts[0].startswith("/"):
            return False

        skill_name = parts[0][1:]  # 去掉 /
        file_path = parts[1] if len(parts) > 1 else None

        # 读取代码
        code_content = ""
        if file_path:
            p = Path(file_path)
            if p.is_file():
                code_content = p.read_text()
            else:
                console.print(f"[red]File not found: {file_path}[/red]")
                return True
        else:
            # 尝试从当前工作区读取
            ws_code = self._collect_workspace_code()
            code_content = ws_code if ws_code else "# No code provided"

        # 执行 skill（通过 omc skill run）
        cmd = ["omc", "skill", "run", skill_name]
        try:
            result = subprocess.run(
                cmd, input=code_content, capture_output=True, text=True, timeout=30
            )
            console.print(
                Panel.fit(
                    f"[green]✓ Skill /{skill_name} executed[/green]",
                    border_style="green",
                )
            )
            if result.stdout:
                console.print(
                    Syntax(
                        result.stdout[:2000],
                        "python",
                        theme="monokai",
                        line_numbers=True,
                    )
                )
            if result.stderr:
                console.print(f"[red]{result.stderr[:500]}[/red]")
        except subprocess.TimeoutExpired:
            console.print("[red]✗ Skill execution timed out[/red]")
        except Exception as exc:
            console.print(f"[red]✗ Skill failed: {exc}[/red]")

        console.print("[dim]Press any key to continue...[/dim]")
        self._wait_key()
        return True

    def _collect_workspace_code(self) -> str:
        """收集当前工作区中的代码文件"""
        code_files = list(Path.cwd().rglob("*.py"))[:10]
        snippets = []
        for f in code_files[:3]:
            try:
                lines = f.read_text().splitlines()[:50]
                snippets.append(
                    f"# === {f.relative_to(Path.cwd())} ===\n" + "\n".join(lines)
                )
            except Exception:
                pass
        return "\n\n".join(snippets)

    def _wait_key(self) -> None:
        """等待任意键输入"""
        console.input("")

    def _handle_main(self, key: str) -> bool:
        """主菜单键盘处理"""
        if key == Keys.Up:
            self.cursor = max(0, self.cursor - 1)
        elif key == Keys.Down:
            self.cursor = min(len(WORKFLOWS) - 1, self.cursor + 1)
        elif key in ["1", "2", "3", "4", "5", "6", "7"]:
            idx = int(key) - 1
            if idx < len(WORKFLOWS):
                self.cursor = idx
                self.selected_workflow = WORKFLOWS[idx][0]
                self.state = State.TASK
        elif key in ["\n", "enter"]:
            self.selected_workflow = WORKFLOWS[self.cursor][0]
            self.state = State.TASK
        elif key.lower() == "m":
            self.state = State.MODEL
            self.cursor = 0
        elif key.lower() == "a":
            self.state = State.AGENTS
        return True

    def _handle_workflow(self, key: str) -> bool:
        """工作流选择键盘处理"""
        if key == Keys.Up:
            self.cursor = max(0, self.cursor - 1)
        elif key == Keys.Down:
            self.cursor = min(len(WORKFLOWS) - 1, self.cursor + 1)
        elif key in ["\n", "enter"]:
            self.selected_workflow = WORKFLOWS[self.cursor][0]
            self.state = State.TASK
        elif key in ["escape", "ctrl+c"]:
            self.state = State.MAIN
            self.cursor = 0
        return True

    def _handle_model(self, key: str) -> bool:
        """模型选择键盘处理"""
        if key == Keys.Up:
            self.cursor = max(0, self.cursor - 1)
        elif key == Keys.Down:
            self.cursor = min(len(MODELS) - 1, self.cursor + 1)
        elif key in ["\n", "enter"]:
            self.selected_model = MODELS[self.cursor][0]
            self.state = State.MAIN
        elif key in ["escape", "ctrl+c"]:
            self.state = State.MAIN
        return True

    def _handle_agents(self, key: str) -> bool:
        """Agent 列表键盘处理"""
        if key in ["escape", "ctrl+c", "q"]:
            self.state = State.MAIN
        return True

    def _handle_task(self, key: str) -> bool:
        """任务输入键盘处理"""
        if key in ["escape", "ctrl+c"]:
            self.state = State.MAIN
        elif key in ["\n", "enter"]:
            if self.task_input.strip():
                # 检测 /skill 命令
                if self.task_input.strip().startswith("/"):
                    self._handle_slash_command(self.task_input)
                    self.task_input = ""
                    self.state = State.MAIN
                else:
                    self.state = State.CONFIRM
        elif key == "backspace":
            self.task_input = self.task_input[:-1]
        elif len(key) == 1:
            self.task_input += key
        return True

    def _handle_confirm(self, key: str) -> bool:
        """确认执行键盘处理"""
        if key.lower() == "y":
            self._execute_task()
            return False
        if key.lower() == "n":
            self.state = State.TASK
        elif key in ["escape", "ctrl+c"]:
            self.state = State.MAIN
            self.task_input = ""
        return True

    def _execute_task(self):
        """执行任务"""
        console.print("\n[yellow]正在启动:[/yellow]")
        console.print(
            f'  omc run "{self.task_input}" --workflow {self.selected_workflow} --model {self.selected_model}'
        )
        console.print("\n[dim]（实际执行功能开发中）[/dim]")


@app.command()
def start(
    task: str | None = typer.Argument(None, help="任务描述（可选）"),
    workflow: str | None = typer.Option(None, "--workflow", "-w", help="指定工作流"),
    model: str | None = typer.Option(None, "--model", "-m", help="指定模型"),
):
    """启动 TUI 交互界面"""
    session = TUISession()

    # 如果直接提供了参数，跳过 TUI
    if task or workflow:
        if task:
            session.task_input = task
        if workflow:
            session.selected_workflow = workflow
        if model:
            session.selected_model = model

        session.state = State.CONFIRM if task else State.TASK
        with Live(session.render(), console=console, refresh_per_second=30):
            session.handle_key("\n")
        return

    # 交互式 TUI
    console.print(
        Panel.fit(
            "[bold cyan]🤖 Oh My Coder TUI[/bold cyan]\n[dim]键盘驱动的交互界面[/dim]",
            border_style="cyan",
        )
    )

    with Live(session.render(), console=console, refresh_per_second=30) as live:
        while True:
            key = console.input("")

            # 处理任务输入模式
            if session.state == State.TASK and key not in [
                "\n",
                "enter",
                "escape",
                "ctrl+c",
            ]:
                if key == "backspace":
                    session.task_input = session.task_input[:-1]
                elif len(key) == 1 and key.isprintable():
                    session.task_input += key
                live.update(session.render())
                continue

            if not session.handle_key(key):
                break

            live.update(session.render())


@app.command("agents")
def list_agents():
    """列出所有 Agent"""
    table = Table(title="[bold cyan]🤖 Agent 清单[/bold cyan]")
    table.add_column("分类", style="cyan")
    table.add_column("Agent", style="white")

    for category, agents in AGENT_CATEGORIES.items():
        table.add_row(category, ", ".join(agents))

    console.print(table)
    console.print(
        f"\n[dim]共 {sum(len(a) for a in AGENT_CATEGORIES.values())} 个 Agent[/dim]"
    )


@app.command("workflows")
def list_workflows():
    """列出所有工作流"""
    table = Table(title="[bold cyan]📋 工作流清单[/bold cyan]")
    table.add_column("编号", style="cyan", width=4)
    table.add_column("工作流", style="white")
    table.add_column("说明", style="dim")

    for i, (key, desc, _) in enumerate(WORKFLOWS, 1):
        table.add_row(str(i), f"[bold]{key}[/bold]", desc)

    console.print(table)


@app.command("models")
def list_models():
    """列出所有可用模型"""
    table = Table(title="[bold cyan]🔧 模型清单[/bold cyan]")
    table.add_column("模型", style="cyan")
    table.add_column("说明", style="dim")

    for _key, name, desc in MODELS:
        table.add_row(name, desc)

    console.print(table)


if __name__ == "__main__":
    app()
