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
