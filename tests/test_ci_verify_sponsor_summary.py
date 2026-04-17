from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import ci_verify


def _write(path: Path, data: dict) -> None:
    ci_verify._write_json(path, data)


def _summary_args(tmp_path: Path) -> SimpleNamespace:
    non_vm = tmp_path / "non-vm" / "summary.json"
    windows = tmp_path / "windows" / "summary.json"
    gpt_matrix = tmp_path / "gpt-format-matrix" / "summary.json"
    gpt_dir = tmp_path / "gpt4o"
    deallocation = tmp_path / "vm-deallocation.json"

    _write(non_vm, {"cases": [{"id": "python", "passed": True}], "failures": 0})
    _write(
        gpt_matrix,
        {
            "cases": [{"id": "cmd", "passed": True, "proof_level": "real_execution"}],
            "total": 1,
            "failures": 0,
            "failed_ids": [],
            "real_execution_total": 1,
            "real_execution_passed": 1,
            "provider_required_total": 0,
            "provider_required_tool_call_passed": 0,
            "not_live_executed_because_provider_required": [],
        },
    )
    _write(
        gpt_dir / "transcript.json",
        {
            "job_id": "job-1",
            "sentinel": "SENTINEL",
            "events": [
                {"type": "tool_call", "name": "EchoSentinel"},
                {"type": "tool_result", "result": "SENTINEL"},
            ],
        },
    )
    _write(gpt_dir / "selected-invocable.json", {"name": "EchoSentinel"})
    _write(gpt_dir / "generated-mcp-schema.json", {"tools": [{"name": "EchoSentinel"}]})
    _write(gpt_dir / "downloaded-mcp-schema.json", {"tools": [{"name": "EchoSentinel"}]})
    _write(gpt_dir / "job-status-history.json", [{"status": "done"}])
    _write(deallocation, {"attempted": True, "completed": True})

    return SimpleNamespace(
        non_vm_summary=str(non_vm),
        windows_summary=str(windows),
        gpt_artifact_dir=str(gpt_dir),
        gpt_matrix_summary=str(gpt_matrix),
        vm_deallocation=str(deallocation),
        out=str(tmp_path / "final-summary.json"),
        markdown=str(tmp_path / "final-summary.md"),
    )


def test_optional_windows_diagnostic_failure_does_not_fail_final_summary(tmp_path: Path) -> None:
    args = _summary_args(tmp_path)
    _write(
        Path(args.windows_summary),
        {
            "targets": [
                {"label": "cmd_exe", "required": False, "passed": False},
                {"label": "notepad_exe", "required": True, "passed": True},
            ],
            "failures": 0,
            "optional_failures": 1,
            "optional_failed_labels": ["cmd_exe"],
        },
    )

    assert ci_verify.cmd_summarize_sponsor_demo(args) == 0
    summary = ci_verify._load_json(Path(args.out))

    assert summary["passed"] is True
    assert summary["checks"]["windows_targets_passed"] is True
    assert summary["windows"]["optional_failed_ids"] == ["cmd_exe"]


def test_required_windows_failure_fails_final_summary(tmp_path: Path) -> None:
    args = _summary_args(tmp_path)
    _write(
        Path(args.windows_summary),
        {
            "targets": [
                {"label": "cmd_fixture", "required": True, "passed": False},
                {"label": "notepad_exe", "required": True, "passed": True},
            ],
            "failures": 1,
            "failed_labels": ["cmd_fixture"],
        },
    )

    with pytest.raises(AssertionError):
        ci_verify.cmd_summarize_sponsor_demo(args)

    summary = ci_verify._load_json(Path(args.out))
    assert summary["passed"] is False
    assert summary["windows"]["required_failed_ids"] == ["cmd_fixture"]


def test_bridge_summary_treats_optional_failures_as_non_blocking(tmp_path: Path) -> None:
    windows = tmp_path / "windows"
    _write(windows / "cmd_exe" / "cmd_exe.summary.json", {"label": "cmd_exe", "required": False, "passed": False})
    _write(windows / "notepad_exe" / "notepad_exe.summary.json", {"label": "notepad_exe", "required": True, "passed": True})

    assert ci_verify.cmd_summarize_bridge_e2e(SimpleNamespace(out_dir=str(windows))) == 0
    summary = ci_verify._load_json(windows / "summary.json")

    assert summary["failures"] == 0
    assert summary["optional_failures"] == 1
    assert summary["required_failures"] == 0


def test_bridge_timing_diagnostics_include_retry_restart_and_failure_class() -> None:
    item = {
        "label": "cmd_exe",
        "required": False,
        "passed": False,
        "matched_invocable_count": 0,
        "min_invocables": 1,
        "configured_post_grace_seconds": 3,
        "health_before": {
            "ok": True,
            "waited_seconds": 0.5,
            "bridge_process": {"attempted": True, "cached": False, "elapsed_seconds": 4.0, "session_id": 1},
        },
        "post_grace_health": {
            "ok": True,
            "waited_seconds": 0.25,
            "bridge_process": {"attempted": False, "cached": True, "session_id": 1},
        },
        "attempts": [
            {"ok": False, "elapsed_seconds": 10.0, "error": "connection reset"},
            {
                "ok": False,
                "elapsed_seconds": 20.0,
                "error": "matched_invocables=0",
                "health_before_retry": {
                    "ok": True,
                    "waited_seconds": 1.0,
                    "restart_attempted": True,
                    "restart_result": {"attempted": True, "elapsed_seconds": 7.0},
                    "vm_restart_result": {"attempted": True, "elapsed_seconds": 30.0},
                    "bridge_process": {"attempted": True, "cached": False, "elapsed_seconds": 5.0, "session_id": 1},
                },
            },
        ],
    }

    ci_verify._add_bridge_timing_diagnostics(item)

    assert item["bridge_analyzer_seconds"] == 30.0
    assert item["retry_seconds"] == 20.0
    assert item["restart_seconds"] == 7.0
    assert item["vm_restart_seconds"] == 30.0
    assert item["session_check_seconds"] == 9.0
    assert item["session_cache_used"] is True
    assert item["timeout_or_failure_classification"] == "bridge_connection_reset"


def test_final_summary_markdown_contains_diagnostic_sections(tmp_path: Path) -> None:
    args = _summary_args(tmp_path)
    _write(
        Path(args.windows_summary),
        {
            "targets": [
                {
                    "label": "notepad_exe",
                    "required": True,
                    "passed": True,
                    "total_elapsed_seconds": 64.0,
                    "bridge_analyzer_seconds": 30.0,
                    "health_wait_seconds": 1.0,
                    "session_check_seconds": 0.0,
                    "retry_seconds": 0.0,
                    "restart_seconds": 0.0,
                    "vm_restart_seconds": 0.0,
                    "post_grace_seconds": 3.0,
                    "dominant_time_source": "analyzer",
                    "timeout_or_failure_classification": "passed_cached_session",
                    "session_cache_used": True,
                    "health_before": {"bridge_process": {"session_id": 1}},
                    "post_grace_health": {"bridge_process": {"session_id": 1}},
                }
            ],
            "failures": 0,
        },
    )

    assert ci_verify.cmd_summarize_sponsor_demo(args) == 0
    text = Path(args.markdown).read_text(encoding="utf-8")

    assert "## Slow Windows Targets" in text
    assert "notepad_exe" in text
    assert "## Bridge Recovery Events" in text
    assert "## Session And Cache Proof" in text
