"""测试 summary.py — 任务总结模块"""

import json
from io import StringIO

import pytest

from src.core.summary import (
    ModelUsage,
    StepRecord,
    TaskSummary,
    _generate_recommendations,
    _infer_models,
    _write_html_summary,
    _write_txt_summary,
    generate_summary,
    load_summary,
    print_summary,
    print_summary_compact,
    quick_summary,
    save_summary,
)

# ===== StepRecord =====


class TestStepRecord:
    def test_defaults(self):
        s = StepRecord(agent="Coder", status="completed", duration=1.5)
        assert s.tokens == 0
        assert s.cost == 0.0
        assert s.result == ""
        assert s.error == ""

    def test_to_dict(self):
        s = StepRecord(agent="Coder", status="failed", duration=2.0, tokens=100, cost=0.5, result="ok", error="err")
        d = s.to_dict()
        assert d["agent"] == "Coder"
        assert d["cost"] == 0.5


# ===== ModelUsage =====


class TestModelUsage:
    def test_defaults(self):
        m = ModelUsage(provider="deepseek", model_name="chat")
        assert m.calls == 0


# ===== TaskSummary =====


class TestTaskSummary:
    def test_defaults(self):
        t = TaskSummary(task="test", workflow="build")
        assert t.success is True
        assert t.steps_completed == []
        assert t.models_used == []

    def test_to_dict(self):
        t = TaskSummary(task="t", workflow="w", total_tokens=100)
        d = t.to_dict()
        assert d["total_tokens"] == 100

    def test_from_dict(self):
        d = {"task": "t", "workflow": "w", "total_tokens": 50}
        t = TaskSummary.from_dict(d)
        assert t.total_tokens == 50


# ===== _infer_models =====


class TestInferModels:
    def test_build(self):
        assert len(_infer_models("build", 3)) == 3

    def test_review(self):
        assert _infer_models("review", 1) == ["deepseek-chat"]

    def test_debug(self):
        assert _infer_models("debug", 1) == ["deepseek-chat"]

    def test_test(self):
        assert len(_infer_models("test", 2)) == 2

    def test_unknown(self):
        assert _infer_models("custom", 1) == ["deepseek-chat"]


# ===== _generate_recommendations =====


class TestGenerateRecommendations:
    def test_no_issues(self):
        recs = _generate_recommendations([], 0.01, 100, "build")
        assert "良好" in recs[0]

    def test_high_cost(self):
        recs = _generate_recommendations([], 2.0, 100, "build")
        assert any("成本较高" in r for r in recs)

    def test_medium_cost(self):
        recs = _generate_recommendations([], 0.2, 100, "build")
        assert any("适中" in r for r in recs)

    def test_high_tokens(self):
        recs = _generate_recommendations([], 0.01, 60000, "build")
        assert any("Token" in r for r in recs)

    def test_long_duration(self):
        steps = [StepRecord(agent="a", status="completed", duration=70)]
        recs = _generate_recommendations(steps, 0.01, 100, "build")
        assert any("时间较长" in r for r in recs)

    def test_failed_steps(self):
        steps = [StepRecord(agent="a", status="failed", duration=1, error="oops")]
        recs = _generate_recommendations(steps, 0.01, 100, "build")
        assert any("失败" in r for r in recs)


# ===== generate_summary =====


class TestGenerateSummary:
    def test_basic(self):
        steps = [
            {"agent": "Coder", "status": "completed", "duration": 5.0, "tokens": 500, "result": "done"},
            {"agent": "Reviewer", "status": "completed", "duration": 3.0, "tokens": 200, "result": "ok"},
        ]
        s = generate_summary("实现模块", "build", steps)
        assert s.success is True
        assert s.agent_count == 2
        assert s.total_tokens == 700

    def test_with_failure(self):
        steps = [
            {"agent": "Coder", "status": "completed", "duration": 5.0, "tokens": 500, "result": "done"},
            {"agent": "Coder", "status": "failed", "duration": 2.0, "tokens": 100, "error": "bug", "result": ""},
        ]
        s = generate_summary("修bug", "debug", steps)
        assert s.success is False
        assert len(s.errors) == 1

    def test_cost_estimation(self):
        steps = [{"agent": "A", "status": "completed", "duration": 1, "tokens": 100000}]
        s = generate_summary("test", "build", steps)
        assert s.total_cost > 0  # auto-estimated

    def test_with_custom_times(self):
        from datetime import datetime, timedelta
        start = datetime(2026, 1, 1, 10, 0)
        end = start + timedelta(minutes=5)
        s = generate_summary("t", "build", [], start_time=start, end_time=end)
        assert s.duration_seconds == 300.0


# ===== print_summary / print_summary_compact =====


class TestPrintSummary:
    def test_print_summary(self, capsys):
        s = TaskSummary(task="测试任务", workflow="build", success=True, duration_seconds=10.0, total_cost=0.5, total_tokens=1000, agent_count=2, models_used=["deepseek-chat"])
        print_summary(s)
        captured = capsys.readouterr()
        assert "✅" in captured.out
        assert "测试任务" in captured.out

    def test_print_summary_failed(self, capsys):
        s = TaskSummary(task="fail task", workflow="debug", success=False, errors=["Coder: bug"])
        print_summary(s)
        captured = capsys.readouterr()
        assert "❌" in captured.out

    def test_print_summary_with_steps(self, capsys):
        s = TaskSummary(
            task="t", workflow="build", success=True,
            steps_completed=[{"agent": "AgentCoder", "status": "completed", "duration": 5.0, "tokens": 100, "result": "done"}],
        )
        print_summary(s)
        captured = capsys.readouterr()
        assert "Coder" in captured.out

    def test_print_summary_compact(self, capsys):
        s = TaskSummary(task="测试", workflow="build", success=True, duration_seconds=5.0, total_cost=0.01, agent_count=1)
        print_summary_compact(s)
        captured = capsys.readouterr()
        assert "✅" in captured.out


# ===== save_summary / load_summary =====


class TestSaveAndLoad:
    def test_save_json(self, tmp_path):
        s = TaskSummary(task="测试", workflow="build", total_tokens=100, total_cost=0.5)
        path = save_summary(s, output_dir=tmp_path, format="json")
        assert path.exists()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["total_tokens"] == 100

    def test_save_txt(self, tmp_path):
        s = TaskSummary(task="测试", workflow="build", success=True, duration_seconds=10.0, total_tokens=1000, total_cost=0.5, recommendations=["建议"])
        path = save_summary(s, output_dir=tmp_path, format="txt")
        assert path.exists()
        content = path.read_text(encoding="utf-8")
        assert "测试" in content

    def test_save_html(self, tmp_path):
        s = TaskSummary(task="测试", workflow="build", success=True, steps_completed=[{"agent": "Coder", "status": "completed", "duration": 5.0, "result": "ok"}])
        path = save_summary(s, output_dir=tmp_path, format="html")
        assert path.exists()
        content = path.read_text(encoding="utf-8")
        assert "<html" in content

    def test_save_custom_filename(self, tmp_path):
        s = TaskSummary(task="t", workflow="build")
        path = save_summary(s, output_dir=tmp_path, format="json", filename="custom.json")
        assert path.name == "custom.json"

    def test_save_invalid_format(self, tmp_path):
        s = TaskSummary(task="t", workflow="build")
        with pytest.raises(ValueError, match="不支持"):
            save_summary(s, output_dir=tmp_path, format="pdf")

    def test_load_json(self, tmp_path):
        s = TaskSummary(task="加载测试", workflow="build", total_tokens=200)
        path = save_summary(s, output_dir=tmp_path, format="json")
        loaded = load_summary(path)
        assert loaded.total_tokens == 200
        assert loaded.task == "加载测试"

    def test_load_non_json(self, tmp_path):
        txt = tmp_path / "summary.txt"
        txt.write_text("text", encoding="utf-8")
        with pytest.raises(ValueError, match="不支持"):
            load_summary(txt)


# ===== _write_txt / _write_html helpers =====


class TestWriteHelpers:
    def test_txt_with_recommendations(self):
        s = TaskSummary(task="t", workflow="w", success=True, recommendations=["rec1"])
        f = StringIO()
        _write_txt_summary(f, s)
        assert "rec1" in f.getvalue()

    def test_txt_no_recommendations(self):
        s = TaskSummary(task="t", workflow="w", success=False)
        f = StringIO()
        _write_txt_summary(f, s)
        assert "失败" in f.getvalue()

    def test_html_basic(self):
        s = TaskSummary(task="t", workflow="w", success=True, duration_seconds=10.0, total_cost=0.5, total_tokens=1000, agent_count=1)
        f = StringIO()
        _write_html_summary(f, s)
        html = f.getvalue()
        assert "✅" in html


# ===== quick_summary =====


class TestQuickSummary:
    def test_basic(self):
        s = quick_summary("快速测试", "build", 5.0, 500, ["步骤1", "步骤2"])
        assert s.success is True
        assert len(s.steps_completed) == 2

    def test_with_workflow(self):
        s = quick_summary("t", "review", 1.0, 100, ["a"])
        assert s.workflow == "review"
