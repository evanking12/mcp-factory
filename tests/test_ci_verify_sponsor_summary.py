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
    windows_gpt = tmp_path / "windows-gpt" / "summary.json"
    repo_ingestion = tmp_path / "repo-ingestion" / "summary.json"
    com_runtime = tmp_path / "windows" / "com_runtime" / "com_runtime.summary.json"
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
            "runtime_mode_counts": {"local_runtime": 1},
            "runtime_backed_cases": ["cmd"],
            "adapter_backed_cases": [],
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
    _write(
        com_runtime,
        {
            "passed": True,
            "proof_level": "com_runtime",
            "runtime_mode": "com_runtime",
            "dcom_surface": "local_com_automation",
            "remote_dcom_activation_claimed": False,
            "com_objects": ["Scripting.Dictionary", "WScript.Shell"],
        },
    )

    return SimpleNamespace(
        non_vm_summary=str(non_vm),
        windows_summary=str(windows),
        gpt_artifact_dir=str(gpt_dir),
        gpt_matrix_summary=str(gpt_matrix),
        windows_gpt_summary=str(windows_gpt),
        repo_ingestion_summary=str(repo_ingestion),
        com_runtime_summary=str(com_runtime),
        vm_deallocation=str(deallocation),
        out=str(tmp_path / "final-summary.json"),
        markdown=str(tmp_path / "final-summary.md"),
        html="",
        canonical_run_url="",
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


def test_final_summary_contains_requirement_matrix(tmp_path: Path) -> None:
    args = _summary_args(tmp_path)
    _write(
        Path(args.windows_summary),
        {
            "targets": [
                {"label": "kernel32_dll", "required": True, "passed": True},
                {"label": "system32_directory", "required": True, "passed": True},
                {"label": "registry_contoso", "required": True, "passed": True},
                {"label": "stdole2_tlb", "required": True, "passed": True},
            ],
            "failures": 0,
        },
    )

    assert ci_verify.cmd_summarize_sponsor_demo(args) == 0
    summary = ci_verify._load_json(Path(args.out))
    matrix = summary["requirement_matrix"]

    assert len(matrix) >= 15
    assert all(row.get("artifact_paths") or row.get("notes") for row in matrix)
    by_req = {row["requirement"]: row for row in matrix}
    assert by_req["2.a"]["status"] == "pass"
    assert "ci_artifacts/demo/windows/system32_directory/system32_directory.summary.json" in by_req["2.a"]["artifact_paths"]
    assert by_req["1.e"]["proof_type"] == "live_execution"

    text = Path(args.markdown).read_text(encoding="utf-8")
    assert "## Requirement Proof Matrix" in text
    assert "system32_directory" in text


def test_docs_and_ui_state_installed_path_caveat() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    ui = (ROOT / "ui" / "main.py").read_text(encoding="utf-8")

    assert "system32_directory" in readme
    assert "server or Windows bridge VM context" in readme
    assert "pipeline server or Windows bridge VM context" in ui


def test_ui_backend_route_and_semantics_alignment() -> None:
    ui = (ROOT / "ui" / "main.py").read_text(encoding="utf-8")
    api = (ROOT / "api" / "main.py").read_text(encoding="utf-8")

    for route in ["/api/analyze", "/api/analyze-path", "/api/generate", "/api/chat", "/api/download/{job_id}/{filename}"]:
        assert route in api
    assert "/api/chat/stream" in ui
    assert "provider required fallback" in ui
    assert "live execution" in ui
    assert "CI Proof Bundle" in ui
    assert "GitHub Actions proof bundle is separate from app /api/download job artifacts" in ui
    assert "`/api/download/${state.jobId}/${encodeURIComponent" in ui
    assert "schemaBlob" in ui
    assert "Load SOAP/WSDL Showcase" in ui
    assert "Legacy Protocol Showcase" in ui
    assert "24568108685" in ui
    assert "Run Canonical Proof" in ui
    assert "tool_call:" in ui
    assert "tool_result:" in ui


def test_final_summary_all_live_matrix_has_zero_required_provider_cases(tmp_path: Path) -> None:
    args = _summary_args(tmp_path)
    cases = [
        "openapi",
        "jsonrpc",
        "soap_wsdl",
        "corba_idl",
        "rpc_idl_contract",
        "jndi",
        "sql",
        "python",
        "javascript",
        "ruby",
        "php",
        "powershell",
        "cmd",
    ]
    _write(
        Path(args.gpt_matrix_summary),
        {
            "cases": [
                {
                    "id": case_id,
                    "passed": True,
                    "proof_level": "real_execution",
                    "tool_call_seen": True,
                    "tool_result_seen": True,
                    "sentinel_seen": True,
                    "runtime_mode": {
                        "openapi": "validated_runtime",
                        "jsonrpc": "real_runtime",
                        "soap_wsdl": "real_runtime",
                        "sql": "real_runtime",
                        "jndi": "ldap_jndi_runtime",
                        "rpc_idl_contract": "xmlrpc_runtime",
                        "corba_idl": "corba_idl_runtime",
                    }.get(case_id, "local_runtime"),
                }
                for case_id in cases
            ],
            "total": len(cases),
            "failures": 0,
            "failed_ids": [],
            "real_execution_cases": cases,
            "real_execution_total": len(cases),
            "real_execution_passed": len(cases),
            "provider_required_cases": [],
            "provider_required_total": 0,
            "provider_required_tool_call_passed": 0,
            "not_live_executed_because_provider_required": [],
            "all_required_cases_live_execution": True,
            "runtime_mode_counts": {
                "corba_idl_runtime": 1,
                "local_runtime": 6,
                "ldap_jndi_runtime": 1,
                "real_runtime": 3,
                "validated_runtime": 1,
                "xmlrpc_runtime": 1,
            },
            "runtime_backed_cases": cases,
            "adapter_backed_cases": [],
        },
    )
    _write(
        Path(args.windows_summary),
        {
            "targets": [
                {"label": "kernel32_dll", "required": True, "passed": True},
                {"label": "system32_directory", "required": True, "passed": True},
                {"label": "registry_contoso", "required": True, "passed": True},
                {"label": "stdole2_tlb", "required": True, "passed": True},
            ],
            "failures": 0,
        },
    )

    assert ci_verify.cmd_summarize_sponsor_demo(args) == 0
    summary = ci_verify._load_json(Path(args.out))
    text = Path(args.markdown).read_text(encoding="utf-8")

    assert summary["gpt_format_matrix"]["real_execution_passed"] == 13
    assert summary["gpt_format_matrix"]["provider_required_total"] == 0
    assert summary["gpt_format_matrix"]["runtime_mode_counts"]["real_runtime"] == 3
    assert summary["gpt_format_matrix"]["adapter_backed_cases"] == []
    assert summary["proof_semantics"]["provider_required"]["cases"] == []
    assert summary["proof_semantics"]["runtime_modes"]["cases_by_mode"]["corba_idl_runtime"] == ["corba_idl"]
    assert summary["com_runtime"]["passed"] is True
    assert "Real execution format proofs: 13/13" in text
    assert "Required provider-required cases: 0" in text
    assert "Runtime mode `corba_idl_runtime`: corba_idl" in text
    assert "## COM/DCOM Surface Proof" in text


def test_sponsor_report_html_rendering(tmp_path: Path) -> None:
    markdown = tmp_path / "final-summary.md"
    html = tmp_path / "sponsor-report.html"
    markdown.write_text("# Sponsor Demo E2E Summary\n\nOverall: PASS\n\n| Requirement | Status |\n|---|---|\n| 1.b | pass |\n", encoding="utf-8")

    rc = ci_verify.cmd_render_sponsor_report(SimpleNamespace(markdown=str(markdown), out=str(html)))

    assert rc == 0
    rendered = html.read_text(encoding="utf-8")
    assert "<h1>Sponsor Demo E2E Summary</h1>" in rendered
    assert "<table>" in rendered
    assert "1.b" in rendered


def test_sponsor_workflows_expose_fast_iteration_controls() -> None:
    workflow = (ROOT / ".github" / "workflows" / "sponsor-demo-e2e.yml").read_text(encoding="utf-8")
    com_workflow = (ROOT / ".github" / "workflows" / "sponsor-windows-com-runtime.yml").read_text(encoding="utf-8")
    report_only = (ROOT / ".github" / "workflows" / "sponsor-demo-report-only.yml").read_text(encoding="utf-8")
    fixture = (ROOT / ".github" / "workflows" / "sponsor-report-fixture.yml").read_text(encoding="utf-8")

    for token in [
        "skip_windows_targets",
        "skip_gpt_matrix",
        "only_windows_target",
        "only_gpt_case",
        "skip_windows_gpt_matrix",
        "only_windows_gpt_target",
        "skip_repo_ingestion",
        "report_only_run_id",
        "--only-case",
        "windows-gpt-tool-matrix",
        "repo-ingestion-gpt-proof",
        "sponsor-report.html",
        "--canonical-run-url",
        "windows-com-runtime-proof",
        "--com-runtime-summary",
    ]:
        assert token in workflow
    assert "windows-com-runtime-proof" in com_workflow
    assert "gh run download" in report_only
    assert "tests/test_legacy_provider_executor.py" in fixture


def test_pushback_docs_and_index_reference_caveats() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    proof_index = (ROOT / "docs" / "sponsor" / "proof-index.md").read_text(encoding="utf-8")
    caveats = (ROOT / "docs" / "sponsor" / "caveats.md").read_text(encoding="utf-8")
    non_code = (ROOT / "docs" / "sponsor" / "non-code-artifacts.md").read_text(encoding="utf-8")

    assert "24568108685" in proof_index
    assert "24547629781" in proof_index
    assert "24542583216" in proof_index
    assert "sponsor-report.html" in proof_index
    assert "SOAP is now runtime-backed" in caveats
    assert "SQLite-backed" in caveats
    assert "CORBA IDL is runtime-shaped" in caveats
    assert "Remote DCOM activation" in caveats
    assert "$150/month" in non_code
    assert "FERPA" in non_code
    assert "docs/sponsor/proof-index.md" in readme


def test_windows_gpt_summary_is_optional_but_reported(tmp_path: Path) -> None:
    args = _summary_args(tmp_path)
    _write(Path(args.windows_summary), {"targets": [{"label": "kernel32_dll", "required": True, "passed": True}], "failures": 0})
    _write(
        Path(args.windows_gpt_summary),
        {
            "cases": [
                {
                    "id": "kernel32_dll",
                    "passed": True,
                    "proof_level": "tool_result_observed",
                    "tool_call_seen": True,
                    "tool_result_seen": True,
                    "transcript_exists": True,
                }
            ],
            "total": 1,
            "passed": 1,
            "failures": 0,
            "failed_ids": [],
            "proof_level": "tool_result_observed",
        },
    )

    assert ci_verify.cmd_summarize_sponsor_demo(args) == 0
    summary = ci_verify._load_json(Path(args.out))
    text = Path(args.markdown).read_text(encoding="utf-8")

    assert summary["windows_gpt_tool_matrix"]["passed"] == 1
    assert summary["checks"]["windows_gpt_tool_matrix_passed"] is True
    assert "## Windows GPT Tool-Call Proofs" in text
    assert "kernel32_dll" in text


def test_repo_fixture_discovery_finds_python_and_js_invocables(tmp_path: Path) -> None:
    artifact, invocables = ci_verify._run_discovery_fixture(ci_verify.SPONSOR_REPO_FIXTURE, tmp_path / "repo")
    names = {str(inv.get("name")) for inv in invocables}

    assert artifact.exists()
    assert "repo_echo_sentinel" in names
    assert len(invocables) >= 2


def test_windows_gpt_tool_matrix_records_observed_result_summary(tmp_path: Path, monkeypatch) -> None:
    windows_dir = tmp_path / "windows"
    out_dir = tmp_path / "windows-gpt"
    _write(
        windows_dir / "kernel32_dll" / "kernel32_dll.summary.json",
        {
            "label": "kernel32_dll",
            "target": "C:\\Windows\\System32\\kernel32.dll",
            "category": "dll",
            "passed": True,
            "matched_invocable_count": 2,
            "invocable_count": 2,
            "first_20_invocable_names": ["GetLastError"],
        },
    )

    def fake_tool_call(**kwargs):
        artifact_dir = kwargs["artifact_dir"]
        ci_verify._write_json(artifact_dir / "selected-invocable.json", kwargs["selected"])
        ci_verify._write_json(artifact_dir / "generated-mcp-schema.json", {"tools": [{"type": "function", "function": {"name": "kernel32_dll_observed_result", "parameters": {"type": "object"}}}]})
        ci_verify._write_json(artifact_dir / "downloaded-mcp-schema.json", {"tools": []})
        return {
            "tools": [{"type": "function"}],
            "events": [
                {"type": "tool_call", "name": "kernel32_dll_observed_result"},
                {"type": "tool_result", "result": "tool_result_observed"},
            ],
            "tool_results": [{"type": "tool_result", "result": "tool_result_observed"}],
            "tool_call_seen": True,
            "tool_result_seen": True,
            "downloaded_schema_exists": True,
        }

    monkeypatch.setattr(ci_verify, "_call_generated_tool_with_gpt", fake_tool_call)

    rc = ci_verify.cmd_windows_gpt_tool_matrix(
        SimpleNamespace(
            base_url="https://pipeline.example",
            pipeline_key="key",
            windows_dir=str(windows_dir),
            artifact_dir=str(out_dir),
            only_target="kernel32_dll",
            chat_timeout=1,
        )
    )

    assert rc == 0
    summary = ci_verify._load_json(out_dir / "summary.json")
    assert summary["passed"] == 1
    assert summary["cases"][0]["proof_level"] == "tool_result_observed"
    assert (out_dir / "kernel32_dll" / "transcript.json").exists()


def test_repo_ingestion_gpt_proof_records_sentinel_summary(tmp_path: Path, monkeypatch) -> None:
    repo_dir = tmp_path / "fixture"
    repo_dir.mkdir()
    (repo_dir / "README.md").write_text("fixture", encoding="utf-8")
    discovery_artifact = tmp_path / "artifact.json"
    selected = {
        "name": "repo_echo_sentinel",
        "kind": "python_function",
        "parameters": [{"name": "sentinel", "type": "string"}],
        "execution": {"method": "python_subprocess", "script_content": "def repo_echo_sentinel(sentinel): return sentinel"},
    }

    def fake_discovery(target: Path, out_dir: Path):
        ci_verify._write_json(discovery_artifact, {"invocables": [selected, {"name": "repoDescribeOrder", "kind": "js_function", "execution": {"method": "node"}}]})
        return discovery_artifact, [selected, {"name": "repoDescribeOrder", "kind": "js_function", "execution": {"method": "node"}}]

    def fake_tool_call(**kwargs):
        sentinel = "MCP_FACTORY_REPO_TEST"
        artifact_dir = kwargs["artifact_dir"]
        ci_verify._write_json(artifact_dir / "selected-invocable.json", kwargs["selected"])
        ci_verify._write_json(artifact_dir / "generated-mcp-schema.json", {"tools": []})
        ci_verify._write_json(artifact_dir / "downloaded-mcp-schema.json", {"tools": []})
        return {
            "tools": [{"type": "function"}],
            "events": [
                {"type": "tool_call", "name": "repo_echo_sentinel"},
                {"type": "tool_result", "result": sentinel},
            ],
            "tool_results": [{"type": "tool_result", "result": sentinel}],
            "tool_call_seen": True,
            "tool_result_seen": True,
            "downloaded_schema_exists": True,
        }

    monkeypatch.setattr(ci_verify, "_run_discovery_fixture", fake_discovery)
    monkeypatch.setattr(ci_verify, "_call_generated_tool_with_gpt", fake_tool_call)

    rc = ci_verify.cmd_repo_ingestion_gpt_proof(
        SimpleNamespace(
            base_url="https://pipeline.example",
            pipeline_key="key",
            target_dir=str(repo_dir),
            artifact_dir=str(tmp_path / "repo-proof"),
            sentinel="MCP_FACTORY_REPO_TEST",
            min_invocables=2,
            chat_timeout=1,
        )
    )

    assert rc == 0
    summary = ci_verify._load_json(tmp_path / "repo-proof" / "summary.json")
    assert summary["passed"] is True
    assert summary["tool_call_seen"] is True
    assert summary["tool_result_seen"] is True
    assert summary["sentinel_seen"] is True


def test_final_summary_makes_proof_semantics_explicit(tmp_path: Path) -> None:
    args = _summary_args(tmp_path)
    _write(
        Path(args.gpt_matrix_summary),
        {
            "cases": [
                {"id": "cmd", "passed": True, "proof_level": "real_execution", "runtime_mode": "local_runtime"},
                {"id": "openapi", "passed": True, "proof_level": "provider_required", "runtime_mode": "validated_runtime"},
            ],
            "total": 2,
            "failures": 0,
            "failed_ids": [],
            "real_execution_cases": ["cmd"],
            "real_execution_total": 1,
            "real_execution_passed": 1,
            "provider_required_cases": ["openapi"],
            "provider_required_total": 1,
            "provider_required_tool_call_passed": 1,
            "not_live_executed_because_provider_required": ["openapi"],
            "runtime_mode_counts": {"local_runtime": 1, "validated_runtime": 1},
        },
    )
    _write(Path(args.windows_summary), {"targets": [{"label": "kernel32_dll", "required": True, "passed": True}], "failures": 0})

    assert ci_verify.cmd_summarize_sponsor_demo(args) == 0
    summary = ci_verify._load_json(Path(args.out))

    assert summary["proof_semantics"]["live_execution"]["cases"] == ["cmd"]
    assert summary["proof_semantics"]["provider_required"]["cases"] == ["openapi"]
    assert summary["proof_semantics"]["runtime_modes"]["cases_by_mode"]["local_runtime"] == ["cmd"]
    text = Path(args.markdown).read_text(encoding="utf-8")
    assert "## Proof Semantics" in text
    assert "does not claim local live execution" in text


def test_sponsor_manifest_rejects_stale_corba_adapter_mode(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    ci_verify._write_json(
        manifest,
        {
            "non_vm_cases": [
                {
                    "id": "corba_idl",
                    "kind": "file",
                    "category": "CORBA/IDL",
                    "path": "tests/fixtures/sponsor/contoso_service.idl",
                    "min_invocables": 1,
                    "proof_level": "real_execution",
                    "runtime_mode": "adapter_backed",
                    "expected_result": "sentinel",
                }
            ]
        },
    )
    with pytest.raises(AssertionError, match="stale runtime_mode='adapter_backed'"):
        ci_verify.cmd_run_sponsor_contract(SimpleNamespace(manifest=str(manifest), out=str(tmp_path / "out")))


def test_final_summary_contains_mcp_llm_story(tmp_path: Path) -> None:
    args = _summary_args(tmp_path)
    _write(Path(args.windows_summary), {"targets": [{"label": "kernel32_dll", "required": True, "passed": True}], "failures": 0})

    assert ci_verify.cmd_summarize_sponsor_demo(args) == 0
    summary = ci_verify._load_json(Path(args.out))
    story = summary["mcp_llm_proof_story"]

    assert story["passed"] is True
    assert story["canonical_live_proof"] == "deterministic_cmd_fixture"
    assert [step["step"] for step in story["steps"]] == [
        "target_supplied",
        "invocables_discovered",
        "mcp_schema_generated",
        "llm_called_tool",
        "tool_result_returned",
        "artifact_downloaded",
    ]
    assert story["schema_tool_count"] == 1
    text = Path(args.markdown).read_text(encoding="utf-8")
    assert "## MCP Generation And LLM Invocation" in text
    assert "downloaded-mcp-schema.json" in text
