"""
cli_gateway 测试 — 覆盖简化后的 Gateway CLI 命令（status / stop / start 异常路径）

注意：omc gateway start 会阻塞（asyncio.run + 无限 sleep），
因此只测「依赖导入失败 → typer.Exit(1)」的异常分支，
正常启动路径不在单测内覆盖（需手动 / Ctrl+C）。
"""
from typer.testing import CliRunner

from src.commands import cli_gateway
from src.commands.cli_gateway import app

runner = CliRunner()


def test_gateway_app_help():
    """app 注册为 gateway 子命令，help 可正常输出"""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "多平台消息网关" in result.stdout


def test_status_prints_table():
    """status 命令调用真实 gateway.status() 并打印平台表"""
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    # 真实 status 输出包含平台枚举名（如 TELEGRAM）
    assert "telegram" in result.stdout


def test_status_import_error_exits(monkeypatch):
    """_load_gateway 抛异常时 status 以 typer.Exit(1) 退出"""
    def boom():
        raise RuntimeError("deps missing")

    monkeypatch.setattr(cli_gateway, "_load_gateway", boom)
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 1


def test_stop_prints_hint():
    """stop 命令输出需要 Ctrl+C 的提示"""
    result = runner.invoke(app, ["stop"])
    assert result.exit_code == 0
    assert "Ctrl+C" in result.stdout


def test_start_import_error_exits(monkeypatch):
    """Gateway 导入/实例化失败时 start 以 typer.Exit(1) 退出"""
    class _Boom:
        def __init__(self, *a, **k):
            raise RuntimeError("deps missing")

    monkeypatch.setattr("src.gateway.gateway.Gateway", _Boom)
    result = runner.invoke(app, ["start"])
    assert result.exit_code == 1
