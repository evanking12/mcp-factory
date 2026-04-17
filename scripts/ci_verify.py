#!/usr/bin/env python3
"""CI/E2E verification helpers for MCP Factory.

These checks intentionally assert observable outputs: invocable counts, MCP
schema shape, tool-call events, sentinel output, and downloadable artifacts.
"""

from __future__ import annotations

import argparse
import base64
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path
from urllib import error, request


ROOT = Path(__file__).resolve().parents[1]
DISCOVERY_MAIN = ROOT / "src" / "discovery" / "main.py"
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "scripts"
SPONSOR_MANIFEST = ROOT / "tests" / "fixtures" / "sponsor" / "sponsor-binary-manifest.json"
SPONSOR_REPO_FIXTURE = ROOT / "tests" / "fixtures" / "sponsor_repo_fixture"
BRIDGE_ACTIVITY_BLOB = "_vm/last_bridge_activity.json"

WINDOWS_GPT_PROOF_TARGETS = [
    "kernel32_dll",
    "notepad_exe",
    "stdole2_tlb",
    "registry_contoso",
    "system32_directory",
]

DEFAULT_FIXTURES = [
    "sample_openapi.yaml",
    "sample_jsonrpc.json",
    "sample.wsdl",
    "sample.idl",
    "sample.jndi",
    "sample.sql",
    "sample.py",
    "sample.js",
    "sample.rb",
    "sample.php",
    "sample.ps1",
    "sample.bat",
]


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _extract_invocables(data: object) -> list[dict]:
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict) and isinstance(data.get("invocables"), list):
        return [x for x in data["invocables"] if isinstance(x, dict)]
    return []


def _validate_invocables(data: object, *, min_invocables: int, label: str) -> list[dict]:
    invocables = _extract_invocables(data)
    if len(invocables) < min_invocables:
        raise AssertionError(f"{label}: expected at least {min_invocables} invocables, found {len(invocables)}")
    for idx, inv in enumerate(invocables):
        if not inv.get("name"):
            raise AssertionError(f"{label}: invocable[{idx}] missing name")
        if "source_type" not in inv and "kind" not in inv:
            raise AssertionError(f"{label}: invocable[{idx}] missing source_type/kind")
        if "execution" not in inv:
            raise AssertionError(f"{label}: invocable[{idx}] missing execution")
    return invocables


def _validate_mcp_schema(data: object, *, min_tools: int, label: str) -> list[dict]:
    if not isinstance(data, dict):
        raise AssertionError(f"{label}: schema is not a JSON object")
    tools = data.get("tools")
    if not isinstance(tools, list) or len(tools) < min_tools:
        raise AssertionError(f"{label}: expected at least {min_tools} tools, found {len(tools) if isinstance(tools, list) else 0}")
    for idx, tool in enumerate(tools):
        fn = tool.get("function") if isinstance(tool, dict) else None
        if tool.get("type") != "function" or not isinstance(fn, dict):
            raise AssertionError(f"{label}: tool[{idx}] is not an OpenAI function tool")
        if not fn.get("name"):
            raise AssertionError(f"{label}: tool[{idx}] missing function.name")
        params = fn.get("parameters")
        if not isinstance(params, dict) or params.get("type") != "object":
            raise AssertionError(f"{label}: tool[{idx}] has invalid parameters schema")
    return tools


def cmd_validate_discovery(args: argparse.Namespace) -> int:
    data = _load_json(Path(args.path))
    invocables = _validate_invocables(data, min_invocables=args.min_invocables, label=args.path)
    print(f"OK discovery: {args.path} invocables={len(invocables)}")
    return 0


def cmd_validate_mcp_schema(args: argparse.Namespace) -> int:
    data = _load_json(Path(args.path))
    tools = _validate_mcp_schema(data, min_tools=args.min_tools, label=args.path)
    print(f"OK mcp schema: {args.path} tools={len(tools)}")
    return 0


def _run_discovery_fixture(target: Path, out_dir: Path) -> tuple[Path, list[dict]]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src" / "discovery")
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    cmd = [
        sys.executable,
        str(DISCOVERY_MAIN),
        "--target",
        str(target),
        "--out",
        str(out_dir),
        "--no-demangle",
    ]
    proc = subprocess.run(cmd, cwd=str(ROOT), env=env, capture_output=True, text=True, timeout=180)
    if proc.returncode != 0:
        raise AssertionError(
            f"{target.name}: discovery failed rc={proc.returncode}\nSTDOUT:\n{proc.stdout[-2000:]}\nSTDERR:\n{proc.stderr[-2000:]}"
        )
    mcp_files = sorted(out_dir.glob("*_mcp.json")) or sorted(out_dir.glob("*.json"))
    if not mcp_files:
        raise AssertionError(f"{target.name}: discovery produced no JSON artifacts")
    merged: list[dict] = []
    for mcp_file in mcp_files:
        merged.extend(_validate_invocables(_load_json(mcp_file), min_invocables=0, label=str(mcp_file)))
    if not merged:
        raise AssertionError(f"{target.name}: discovery artifacts contained zero invocables")
    return mcp_files[0], merged


def cmd_run_fixture_contract(args: argparse.Namespace) -> int:
    out_root = Path(args.out)
    out_root.mkdir(parents=True, exist_ok=True)
    fixtures = args.fixtures or DEFAULT_FIXTURES
    summary = []
    for fixture_name in fixtures:
        target = FIXTURE_DIR / fixture_name
        if not target.exists():
            raise AssertionError(f"fixture missing: {target}")
        fixture_out = out_root / fixture_name.replace(".", "_").replace("-", "_")
        if fixture_out.exists():
            shutil.rmtree(fixture_out)
        fixture_out.mkdir(parents=True, exist_ok=True)
        artifact, invocables = _run_discovery_fixture(target, fixture_out)
        summary.append({"fixture": fixture_name, "artifact": str(artifact), "invocables": len(invocables)})
        print(f"OK fixture {fixture_name}: invocables={len(invocables)} artifact={artifact.name}")

    (out_root / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"OK fixture contract: {len(summary)} fixtures")
    return 0


def _http_json(method: str, url: str, *, key: str = "", body: object | None = None, timeout: int = 60) -> dict:
    data = None if body is None else json.dumps(body).encode("utf-8")
    headers = {"Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    if key:
        headers["X-Pipeline-Key"] = key
    req = request.Request(url, data=data, headers=headers, method=method)
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise AssertionError(f"{method} {url} failed: HTTP {exc.code}: {detail}") from exc
    return json.loads(raw) if raw else {}


def _http_bytes(method: str, url: str, *, key: str = "", body: bytes | None = None, content_type: str = "", timeout: int = 60) -> bytes:
    headers = {}
    if key:
        headers["X-Pipeline-Key"] = key
    if content_type:
        headers["Content-Type"] = content_type
    req = request.Request(url, data=body, headers=headers, method=method)
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise AssertionError(f"{method} {url} failed: HTTP {exc.code}: {detail}") from exc


def _upload_file(base_url: str, target: Path, *, key: str, hints: str) -> str:
    boundary = f"----mcpfactory-{uuid.uuid4().hex}"
    parts: list[bytes] = []
    parts.append(
        (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="hints"\r\n\r\n'
            f"{hints}\r\n"
        ).encode("utf-8")
    )
    parts.append(
        (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{target.name}"\r\n'
            f"Content-Type: application/octet-stream\r\n\r\n"
        ).encode("utf-8")
    )
    parts.append(target.read_bytes())
    parts.append(f"\r\n--{boundary}--\r\n".encode("utf-8"))
    raw = _http_bytes(
        "POST",
        f"{base_url.rstrip('/')}/api/analyze",
        key=key,
        body=b"".join(parts),
        content_type=f"multipart/form-data; boundary={boundary}",
        timeout=120,
    )
    payload = json.loads(raw.decode("utf-8"))
    job_id = payload.get("job_id")
    if not job_id:
        raise AssertionError(f"upload response missing job_id: {payload}")
    return job_id


def _poll_job(base_url: str, job_id: str, *, key: str, timeout_seconds: int) -> dict:
    deadline = time.monotonic() + timeout_seconds
    last = {}
    while time.monotonic() < deadline:
        last = _http_json("GET", f"{base_url.rstrip('/')}/api/jobs/{job_id}", key=key, timeout=30)
        status = last.get("status")
        message = last.get("message", "")
        print(f"job {job_id}: status={status} progress={last.get('progress')} message={message}")
        if status == "done":
            return last
        if status == "error":
            raise AssertionError(f"job {job_id} failed: {last.get('error') or message}")
        time.sleep(5)
    raise AssertionError(f"job {job_id} timed out after {timeout_seconds}s; last={last}")


def cmd_poll_job(args: argparse.Namespace) -> int:
    payload = _poll_job(args.base_url, args.job_id, key=args.pipeline_key or "", timeout_seconds=args.timeout)
    result = payload.get("result") or {}
    invocables = _validate_invocables(result, min_invocables=args.min_invocables, label=args.job_id)
    print(f"OK job {args.job_id}: invocables={len(invocables)}")
    return 0


def _parse_sse(raw: str) -> list[dict]:
    events = []
    for block in raw.split("\n\n"):
        for line in block.splitlines():
            if not line.startswith("data:"):
                continue
            payload = line[5:].strip()
            if not payload:
                continue
            events.append(json.loads(payload))
    return events


def _safe_tool_name(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.\-]", "_", name)[:64]


def _select_invocable_for_case(case: dict, invocables: list[dict]) -> dict:
    preferred = str(case.get("preferred_tool_name") or "").lower()
    if preferred:
        for inv in invocables:
            if str(inv.get("name", "")).lower() == preferred:
                return inv
    expected = str(case.get("expect_source_type") or "").lower()
    if expected:
        for inv in invocables:
            source_type = str(inv.get("source_type") or inv.get("kind") or "").lower()
            if source_type == expected:
                return inv
    if invocables:
        return invocables[0]
    raise AssertionError(f"{case.get('id', '<unknown>')}: no invocable available for GPT proof")


def _provider_required_seen(text: str) -> bool:
    lowered = text.lower()
    return (
        "provider required" in lowered
        or "live execution requires" in lowered
        or "requires a configured backing" in lowered
        or "requires a live" in lowered
    )


RUNTIME_MODE_BY_FORMAT_CASE = {
    "openapi": "validated_runtime",
    "jsonrpc": "real_runtime",
    "soap_wsdl": "real_runtime",
    "sql": "real_runtime",
    "jndi": "ldap_runtime",
    "rpc_idl_contract": "msrpc_runtime",
    "corba_idl": "corba_orb_runtime",
    "python": "local_runtime",
    "javascript": "local_runtime",
    "ruby": "local_runtime",
    "php": "local_runtime",
    "powershell": "local_runtime",
    "cmd": "local_runtime",
}


STRETCH_PROOF_REQUIREMENTS = [
    {
        "id": "jsonrpc_runtime",
        "label": "JSON-RPC 2.0 runtime",
        "target_mode": "jsonrpc_runtime",
        "current_mode": "real_runtime",
        "required_artifacts": ["ci_artifacts/demo/gpt-format-matrix/jsonrpc/transcript.json"],
    },
    {
        "id": "soap_runtime",
        "label": "SOAP/WSDL runtime",
        "target_mode": "soap_runtime",
        "current_mode": "real_runtime",
        "required_artifacts": ["ci_artifacts/demo/gpt-format-matrix/soap_wsdl/transcript.json"],
    },
    {
        "id": "sqlite_runtime",
        "label": "SQLite SQL runtime",
        "target_mode": "sqlite_runtime",
        "current_mode": "real_runtime",
        "required_artifacts": ["ci_artifacts/demo/gpt-format-matrix/sql/transcript.json"],
    },
    {
        "id": "rest_validated_runtime",
        "label": "OpenAPI/REST route-validated runtime",
        "target_mode": "rest_validated_runtime",
        "current_mode": "validated_runtime",
        "required_artifacts": ["ci_artifacts/demo/gpt-format-matrix/openapi/transcript.json"],
    },
    {
        "id": "ldap_runtime",
        "label": "Real LDAP/JNDI runtime",
        "target_mode": "ldap_runtime",
        "current_mode": "ldap_runtime",
        "required_artifacts": [
            "ci_artifacts/demo/legacy/jndi_ldap/ldap-server-config.ldif",
            "ci_artifacts/demo/legacy/jndi_ldap/bind-result.json",
            "ci_artifacts/demo/legacy/jndi_ldap/search-result.json",
            "ci_artifacts/demo/gpt-format-matrix/jndi/transcript.json",
        ],
    },
    {
        "id": "corba_orb_runtime",
        "label": "CORBA ORB/IIOP runtime",
        "target_mode": "corba_orb_runtime",
        "current_mode": "corba_idl_runtime",
        "required_artifacts": [
            "ci_artifacts/demo/legacy/corba_orb/contoso_support.idl",
            "ci_artifacts/demo/legacy/corba_orb/orb-server.log",
            "ci_artifacts/demo/legacy/corba_orb/client-invocation.json",
            "ci_artifacts/demo/gpt-format-matrix/corba_idl/transcript.json",
        ],
    },
    {
        "id": "msrpc_runtime",
        "label": "Controlled MSRPC / Windows RPC runtime",
        "target_mode": "msrpc_runtime",
        "current_mode": "xmlrpc_runtime",
        "required_artifacts": [
            "ci_artifacts/demo/legacy/msrpc/contoso_rpc.idl",
            "ci_artifacts/demo/legacy/msrpc/endpoint-registration.json",
            "ci_artifacts/demo/legacy/msrpc/client-invocation.json",
            "ci_artifacts/demo/gpt-format-matrix/rpc_idl_contract/transcript.json",
        ],
    },
    {
        "id": "remote_dcom_runtime",
        "label": "Controlled remote DCOM runtime",
        "target_mode": "remote_dcom_runtime",
        "current_mode": "com_runtime",
        "required_artifacts": [
            "ci_artifacts/demo/windows/dcom/dcom.summary.json",
            "ci_artifacts/demo/windows/dcom/remote-activation-transcript.json",
        ],
    },
    {
        "id": "evidence_ranked_binary_recovery",
        "label": "Ghidra + dynamic evidence-ranked binary recovery",
        "target_mode": "evidence_ranked_binary_recovery",
        "current_mode": "not_yet_run",
        "required_artifacts": [
            "ci_artifacts/demo/ghidra/summary.json",
            "ci_artifacts/demo/ghidra/undocumented_fixture/evidence-ranking.json",
            "ci_artifacts/demo/ghidra/undocumented_fixture/transcript.json",
        ],
    },
    {
        "id": "windows_runtime_fixture",
        "label": "Compiled Windows fixture runtime invocation",
        "target_mode": "windows_runtime_fixture",
        "current_mode": "tool_result_observed",
        "required_artifacts": [
            "ci_artifacts/demo/windows/runtime_fixture/runtime_fixture.summary.json",
            "ci_artifacts/demo/windows-gpt/summary.json",
        ],
    },
    {
        "id": "repo_live_execution",
        "label": "Expanded multi-language repo live execution",
        "target_mode": "repo_live_execution",
        "current_mode": "repo_live_execution",
        "required_artifacts": ["ci_artifacts/demo/repo-ingestion/summary.json"],
    },
]


def _runtime_mode_for_case(case: dict) -> str:
    return str(case.get("runtime_mode") or RUNTIME_MODE_BY_FORMAT_CASE.get(str(case.get("id")), "unknown"))


def _runtime_mode_counts(cases: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in cases:
        mode = str(item.get("runtime_mode") or "unknown")
        counts[mode] = counts.get(mode, 0) + 1
    return dict(sorted(counts.items()))


def _load_optional_summary(path: Path) -> dict:
    return _load_json(path) if path.exists() else {"passed": False, "missing": str(path)}


def _build_stretch_proof_matrix(
    *,
    gpt_matrix: dict,
    repo_ingestion: dict,
    com_runtime: dict,
    stretch_runtime: dict,
    ghidra_recovery: dict,
    remote_dcom: dict,
    windows_runtime: dict,
) -> dict:
    mode_counts = gpt_matrix.get("runtime_mode_counts") or {}
    cases = gpt_matrix.get("cases") or []
    case_by_id = {str(item.get("id")): item for item in cases if isinstance(item, dict)}

    def gpt_case_passed(case_id: str) -> bool:
        item = case_by_id.get(case_id)
        if item:
            return bool(item.get("passed") and item.get("tool_call_seen") and item.get("tool_result_seen"))
        return case_id in set(gpt_matrix.get("runtime_backed_cases") or [])

    stretch_sources = {
        "ldap_runtime": stretch_runtime.get("ldap_runtime") or {},
        "corba_orb_runtime": stretch_runtime.get("corba_orb_runtime") or {},
        "msrpc_runtime": stretch_runtime.get("msrpc_runtime") or {},
        "remote_dcom_runtime": remote_dcom,
        "evidence_ranked_binary_recovery": ghidra_recovery,
        "windows_runtime_fixture": windows_runtime,
        "repo_live_execution": repo_ingestion,
    }
    gpt_cases = {
        "jsonrpc_runtime": "jsonrpc",
        "soap_runtime": "soap_wsdl",
        "sqlite_runtime": "sql",
        "rest_validated_runtime": "openapi",
    }

    entries = []
    for requirement in STRETCH_PROOF_REQUIREMENTS:
        proof_id = requirement["id"]
        source = stretch_sources.get(proof_id, {})
        passed = bool(source.get("passed"))
        if proof_id in gpt_cases:
            passed = gpt_case_passed(gpt_cases[proof_id])
        if proof_id == "repo_live_execution":
            passed = bool(repo_ingestion.get("passed"))
        if proof_id == "remote_dcom_runtime":
            passed = bool(remote_dcom.get("passed") and remote_dcom.get("remote_dcom_activation_claimed"))
        if proof_id == "windows_runtime_fixture":
            passed = bool(windows_runtime.get("passed"))
        if proof_id == "evidence_ranked_binary_recovery":
            passed = bool(ghidra_recovery.get("passed"))

        status = "pass" if passed else ("not_yet_run" if source.get("missing") or not source else "fail")
        entries.append(
            {
                **requirement,
                "status": status,
                "passed": passed,
                "source_summary": source.get("summary_path", source.get("missing", "")) if isinstance(source, dict) else "",
                "current_count": mode_counts.get(requirement["current_mode"], 0),
            }
        )

    return {
        "passed": all(item["passed"] for item in entries),
        "total": len(entries),
        "passed_count": sum(1 for item in entries if item["passed"]),
        "not_yet_run_count": sum(1 for item in entries if item["status"] == "not_yet_run"),
        "failed_ids": [item["id"] for item in entries if item["status"] == "fail"],
        "not_yet_run_ids": [item["id"] for item in entries if item["status"] == "not_yet_run"],
        "entries": entries,
    }


def _call_generated_tool_with_gpt(
    *,
    base_url: str,
    pipeline_key: str,
    job_id: str,
    component_name: str,
    selected: dict,
    artifact_dir: Path,
    prompt: str,
    chat_timeout: int,
) -> dict:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    _write_json(artifact_dir / "selected-invocable.json", selected)
    gen = _http_json(
        "POST",
        f"{base_url.rstrip('/')}/api/generate",
        key=pipeline_key or "",
        body={"job_id": job_id, "component_name": component_name, "selected": [selected]},
        timeout=120,
    )
    schema = gen.get("mcp_schema") or {}
    tools = _validate_mcp_schema(schema, min_tools=1, label=f"{component_name} generated schema")
    _write_json(artifact_dir / "generated-mcp-schema.json", schema)

    downloaded_schema_ok = False
    try:
        (artifact_dir / "downloaded-mcp-schema.json").write_bytes(
            _http_bytes(
                "GET",
                f"{base_url.rstrip('/')}/api/download/{job_id}/mcp_schema.json",
                key=pipeline_key or "",
                timeout=60,
            )
        )
        downloaded_schema_ok = True
    except Exception as exc:
        (artifact_dir / "downloaded-mcp-schema.error.txt").write_text(str(exc), encoding="utf-8")

    raw_chat = _http_bytes(
        "POST",
        f"{base_url.rstrip('/')}/api/chat",
        key=pipeline_key or "",
        body=json.dumps({
            "job_id": job_id,
            "messages": [{"role": "user", "content": prompt}],
            "tools": tools,
            "invocables": [selected],
        }).encode("utf-8"),
        content_type="application/json",
        timeout=chat_timeout,
    ).decode("utf-8", errors="replace")
    events = _parse_sse(raw_chat)
    tool_results = [evt for evt in events if evt.get("type") == "tool_result"]
    return {
        "schema": schema,
        "tools": tools,
        "events": events,
        "tool_results": tool_results,
        "tool_call_seen": any(evt.get("type") == "tool_call" for evt in events),
        "tool_result_seen": bool(tool_results),
        "downloaded_schema_exists": downloaded_schema_ok,
    }


def _safe_target_name(target: str) -> str:
    leaf = target.replace("\\", "/").rstrip("/").split("/")[-1]
    safe = "".join(ch.lower() if ch.isalnum() else "_" for ch in leaf)
    while "__" in safe:
        safe = safe.replace("__", "_")
    return safe.strip("_") or "target"


def _target_category(target: str) -> str:
    leaf = target.replace("\\", "/").rstrip("/").split("/")[-1]
    suffix = Path(leaf).suffix.lower()
    if suffix == ".dll":
        return "dll"
    if suffix in {".exe", ".com"}:
        return "exe"
    if suffix in {".tlb", ".olb"}:
        return "typelib"
    if suffix in {".cmd", ".bat"}:
        return "cmd"
    return suffix.lstrip(".") or "unknown"


def _bridge_health(bridge_url: str, bridge_secret: str, *, timeout: int = 10) -> dict:
    req = request.Request(
        f"{bridge_url.rstrip('/')}/health",
        headers={"X-Bridge-Key": bridge_secret},
        method="GET",
    )
    started = time.perf_counter()
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            try:
                payload = json.loads(raw) if raw else None
            except json.JSONDecodeError:
                payload = None
            return {
                "ok": 200 <= resp.status < 300,
                "status": resp.status,
                "body": raw,
                "json": payload,
                "elapsed_seconds": round(time.perf_counter() - started, 3),
            }
    except Exception as exc:
        return {
            "ok": False,
            "status": None,
            "body": "",
            "error": str(exc),
            "elapsed_seconds": round(time.perf_counter() - started, 3),
        }


def _wait_bridge_health(
    bridge_url: str,
    bridge_secret: str,
    *,
    timeout: int = 45,
    interval: float = 3.0,
) -> dict:
    deadline = time.monotonic() + max(0, timeout)
    attempts = 0
    last: dict = {"ok": False, "error": "bridge health was not checked"}
    while True:
        attempts += 1
        remaining = max(1, int(deadline - time.monotonic())) if timeout else 1
        last = _bridge_health(bridge_url, bridge_secret, timeout=min(10, remaining))
        if last.get("ok"):
            last["attempts"] = attempts
            last["waited_seconds"] = max(0, round(timeout - max(0, deadline - time.monotonic()), 3))
            return last
        if time.monotonic() >= deadline:
            last["attempts"] = attempts
            last["wait_timeout_seconds"] = timeout
            return last
        time.sleep(interval)


def _bridge_cache_key(bridge_url: str) -> str:
    return bridge_url.rstrip("/")


def _int_or_none(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _bridge_health_payload(health: dict) -> dict:
    payload = health.get("json")
    if isinstance(payload, dict):
        return payload
    body = health.get("body")
    if isinstance(body, str) and body.strip():
        try:
            parsed = json.loads(body)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def _bridge_health_identity(health: dict) -> dict | None:
    payload = _bridge_health_payload(health)
    process_id = _int_or_none(payload.get("process_id"))
    creation_date = payload.get("creation_date")
    if process_id is None or creation_date in (None, ""):
        return None
    return {
        "process_id": process_id,
        "creation_date": str(creation_date),
        "session_id": _int_or_none(payload.get("session_id")),
    }


def _load_bridge_session_cache(cache_path: Path | None) -> dict:
    if not cache_path or not cache_path.exists():
        return {}
    try:
        data = _load_json(cache_path)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _cached_bridge_session_proof(
    *,
    cache_path: Path | None,
    bridge_url: str,
    health: dict,
    resource_group: str,
    vm_name: str,
    required_session_id: int | None,
) -> dict | None:
    if not health.get("ok"):
        return None
    identity = _bridge_health_identity(health)
    if not identity:
        return None
    cache = _load_bridge_session_cache(cache_path)
    entry = cache.get(_bridge_cache_key(bridge_url))
    if not isinstance(entry, dict):
        return None
    if str(entry.get("vm_name") or "") != str(vm_name or ""):
        return None
    if str(entry.get("resource_group") or "") != str(resource_group or ""):
        return None
    if _int_or_none(entry.get("process_id")) != identity["process_id"]:
        return None
    if str(entry.get("creation_date") or "") != identity["creation_date"]:
        return None
    cached_session_id = _int_or_none(entry.get("session_id"))
    health_session_id = identity.get("session_id")
    if health_session_id is not None and cached_session_id != health_session_id:
        return None
    if required_session_id is not None and cached_session_id != required_session_id:
        return None
    proof = {
        "attempted": False,
        "ok": True,
        "cached": True,
        "source": "bridge_session_cache",
        "process_id": identity["process_id"],
        "creation_date": identity["creation_date"],
        "session_id": cached_session_id,
        "checked_at": entry.get("checked_at"),
        "vm_name": entry.get("vm_name"),
        "resource_group": entry.get("resource_group"),
    }
    return proof


def _write_bridge_session_cache(
    *,
    cache_path: Path | None,
    bridge_url: str,
    health: dict,
    process_info: dict,
    resource_group: str,
    vm_name: str,
) -> None:
    if not cache_path or not process_info.get("ok"):
        return
    process_id = _int_or_none(process_info.get("process_id"))
    session_id = _int_or_none(process_info.get("session_id"))
    creation_date = process_info.get("creation_date")
    identity = _bridge_health_identity(health)
    if identity and identity.get("process_id") == process_id:
        creation_date = identity.get("creation_date")
        if identity.get("session_id") is not None:
            session_id = identity.get("session_id")
    if process_id is None or creation_date in (None, ""):
        return
    cache = _load_bridge_session_cache(cache_path)
    cache[_bridge_cache_key(bridge_url)] = {
        "process_id": process_id,
        "creation_date": str(creation_date),
        "session_id": session_id,
        "checked_at": time.time(),
        "vm_name": vm_name,
        "resource_group": resource_group,
    }
    _write_json(cache_path, cache)


def _ps_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _restart_bridge_task(
    *,
    resource_group: str,
    vm_name: str,
    task_name: str,
    timeout: int = 90,
) -> dict:
    if not resource_group or not vm_name:
        return {
            "attempted": False,
            "ok": False,
            "error": "bridge restart skipped: resource group or VM name missing",
        }

    script = f"""
$ErrorActionPreference = "Continue"
$taskName = {_ps_quote(task_name)}
Write-Output "restart_task=$taskName"
$task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if (-not $task) {{
    Write-Output "task_missing=$taskName"
    exit 2
}}
Stop-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2
Start-ScheduledTask -TaskName $taskName
Start-Sleep -Seconds 3
Write-Output "task_info:"
Get-ScheduledTaskInfo -TaskName $taskName -ErrorAction SilentlyContinue |
    Select-Object TaskName,LastRunTime,LastTaskResult |
    ConvertTo-Json -Compress
Write-Output "port_8090:"
Get-NetTCPConnection -LocalPort 8090 -State Listen -ErrorAction SilentlyContinue |
    Select-Object LocalAddress,LocalPort,OwningProcess,State |
    ConvertTo-Json -Compress
"""
    cmd = [
        _az_executable(), "vm", "run-command", "invoke",
        "-g", resource_group,
        "-n", vm_name,
        "--command-id", "RunPowerShellScript",
        "--scripts", script,
        "--query", "value[].message",
        "-o", "tsv",
    ]
    started = time.perf_counter()
    try:
        proc = subprocess.run(cmd, check=False, capture_output=True, text=True, timeout=timeout)
        return {
            "attempted": True,
            "ok": proc.returncode == 0,
            "returncode": proc.returncode,
            "stdout": proc.stdout[-4000:],
            "stderr": proc.stderr[-4000:],
            "elapsed_seconds": round(time.perf_counter() - started, 3),
        }
    except Exception as exc:
        return {
            "attempted": True,
            "ok": False,
            "error": str(exc),
            "elapsed_seconds": round(time.perf_counter() - started, 3),
        }


def _restart_bridge_vm(*, resource_group: str, vm_name: str, timeout: int = 420) -> dict:
    if not resource_group or not vm_name:
        return {
            "attempted": False,
            "ok": False,
            "error": "VM restart skipped: resource group or VM name missing",
        }
    cmd = [_az_executable(), "vm", "restart", "-g", resource_group, "-n", vm_name]
    started = time.perf_counter()
    try:
        proc = subprocess.run(cmd, check=False, capture_output=True, text=True, timeout=timeout)
        return {
            "attempted": True,
            "ok": proc.returncode == 0,
            "returncode": proc.returncode,
            "stdout": proc.stdout[-4000:],
            "stderr": proc.stderr[-4000:],
            "elapsed_seconds": round(time.perf_counter() - started, 3),
        }
    except Exception as exc:
        return {
            "attempted": True,
            "ok": False,
            "error": str(exc),
            "elapsed_seconds": round(time.perf_counter() - started, 3),
        }


def _ensure_bridge_vm_running(*, resource_group: str, vm_name: str, timeout: int = 360) -> dict:
    if not resource_group or not vm_name:
        return {
            "attempted": False,
            "ok": False,
            "error": "VM start skipped: resource group or VM name missing",
        }

    view_cmd = [
        _az_executable(), "vm", "get-instance-view",
        "-g", resource_group,
        "-n", vm_name,
        "--query", "instanceView.statuses[?starts_with(code, 'PowerState/')].displayStatus|[0]",
        "-o", "tsv",
    ]
    started = time.perf_counter()
    try:
        view = subprocess.run(view_cmd, check=False, capture_output=True, text=True, timeout=60)
        power = view.stdout.strip()
        if view.returncode == 0 and power == "VM running":
            return {
                "attempted": True,
                "ok": True,
                "already_running": True,
                "power": power,
                "elapsed_seconds": round(time.perf_counter() - started, 3),
            }
    except Exception:
        power = ""

    cmd = [_az_executable(), "vm", "start", "-g", resource_group, "-n", vm_name]
    try:
        proc = subprocess.run(cmd, check=False, capture_output=True, text=True, timeout=timeout)
        return {
            "attempted": True,
            "ok": proc.returncode == 0,
            "already_running": False,
            "power": power,
            "returncode": proc.returncode,
            "stdout": proc.stdout[-4000:],
            "stderr": proc.stderr[-4000:],
            "elapsed_seconds": round(time.perf_counter() - started, 3),
        }
    except Exception as exc:
        return {
            "attempted": True,
            "ok": False,
            "already_running": False,
            "power": power,
            "error": str(exc),
            "elapsed_seconds": round(time.perf_counter() - started, 3),
        }


def _bridge_process_info(
    *,
    resource_group: str,
    vm_name: str,
    timeout: int = 90,
) -> dict:
    if not resource_group or not vm_name:
        return {
            "attempted": False,
            "ok": False,
            "error": "bridge process check skipped: resource group or VM name missing",
        }

    script = """
$ErrorActionPreference = "Continue"
$conn = Get-NetTCPConnection -LocalPort 8090 -State Listen -ErrorAction SilentlyContinue |
    Select-Object -First 1
if (-not $conn) {
    @{ ok = $false; error = "port 8090 is not listening" } | ConvertTo-Json -Compress
    exit 0
}
$proc = Get-CimInstance Win32_Process -Filter "ProcessId=$($conn.OwningProcess)"
if (-not $proc) {
    @{ ok = $false; error = "listener process not found"; process_id = $conn.OwningProcess } |
        ConvertTo-Json -Compress
    exit 0
}
@{
    ok = $true
    process_id = $proc.ProcessId
    parent_process_id = $proc.ParentProcessId
    name = $proc.Name
    command_line = $proc.CommandLine
    creation_date = $proc.CreationDate
    session_id = $proc.SessionId
} | ConvertTo-Json -Compress
"""
    cmd = [
        _az_executable(), "vm", "run-command", "invoke",
        "-g", resource_group,
        "-n", vm_name,
        "--command-id", "RunPowerShellScript",
        "--scripts", script,
        "--query", "value[0].message",
        "-o", "tsv",
    ]
    started = time.perf_counter()
    try:
        proc = subprocess.run(cmd, check=False, capture_output=True, text=True, timeout=timeout)
        result = {
            "attempted": True,
            "ok": proc.returncode == 0,
            "returncode": proc.returncode,
            "stdout": proc.stdout[-4000:],
            "stderr": proc.stderr[-4000:],
            "elapsed_seconds": round(time.perf_counter() - started, 3),
        }
        if proc.returncode == 0 and proc.stdout.strip():
            try:
                payload = json.loads(proc.stdout.strip().splitlines()[-1])
                result.update(payload if isinstance(payload, dict) else {"raw_payload": payload})
            except json.JSONDecodeError:
                result["parse_error"] = "failed to parse bridge process JSON"
        return result
    except Exception as exc:
        return {
            "attempted": True,
            "ok": False,
            "error": str(exc),
            "elapsed_seconds": round(time.perf_counter() - started, 3),
        }


def _az_executable() -> str:
    return shutil.which("az") or shutil.which("az.cmd") or "az"


def _run_vm_powershell_json(*, resource_group: str, vm_name: str, script: str, timeout: int) -> dict:
    cmd = [
        _az_executable(), "vm", "run-command", "invoke",
        "-g", resource_group,
        "-n", vm_name,
        "--command-id", "RunPowerShellScript",
        "--scripts", script,
        "--query", "value[].message",
        "-o", "json",
    ]
    started = time.perf_counter()
    try:
        proc = subprocess.run(cmd, check=False, capture_output=True, text=True, timeout=timeout)
        result = {
            "attempted": True,
            "ok": proc.returncode == 0,
            "returncode": proc.returncode,
            "stdout": proc.stdout[-4000:],
            "stderr": proc.stderr[-4000:],
            "elapsed_seconds": round(time.perf_counter() - started, 3),
        }
        if proc.returncode == 0 and proc.stdout.strip():
            candidate_lines = proc.stdout.strip().splitlines()
            try:
                outer = json.loads(proc.stdout)
                if isinstance(outer, dict) and isinstance(outer.get("value"), list):
                    candidate_lines = [
                        str(item.get("message", ""))
                        for item in outer["value"]
                        if isinstance(item, dict) and str(item.get("message", "")).strip()
                    ] or candidate_lines
                elif isinstance(outer, list):
                    candidate_lines = [
                        str(item)
                        for item in outer
                        if str(item).strip()
                    ] or candidate_lines
            except json.JSONDecodeError:
                pass
            flattened_lines: list[str] = []
            for candidate in candidate_lines:
                flattened_lines.extend(str(candidate).splitlines())
            for line in reversed(flattened_lines):
                try:
                    payload = json.loads(line)
                    if isinstance(payload, dict):
                        result.update(payload)
                        break
                except json.JSONDecodeError:
                    continue
            else:
                result["parse_error"] = "failed to parse JSON payload from VM command output"
        return result
    except Exception as exc:
        return {
            "attempted": True,
            "ok": False,
            "error": str(exc),
            "elapsed_seconds": round(time.perf_counter() - started, 3),
        }


def _run_local_powershell_json(*, script: str, timeout: int) -> dict:
    module_path_reset = (
        "$machinePath = [Environment]::GetEnvironmentVariable('PSModulePath', 'Machine'); "
        "$userPath = [Environment]::GetEnvironmentVariable('PSModulePath', 'User'); "
        "$env:PSModulePath = (($machinePath, $userPath) | Where-Object { $_ }) -join ';'; "
        "Import-Module Microsoft.PowerShell.Security -ErrorAction Stop; "
    )
    cmd = ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", module_path_reset + script]
    started = time.perf_counter()
    try:
        proc = subprocess.run(cmd, check=False, capture_output=True, text=True, timeout=timeout)
        result = {
            "attempted": True,
            "ok": proc.returncode == 0,
            "returncode": proc.returncode,
            "stdout": proc.stdout[-4000:],
            "stderr": proc.stderr[-4000:],
            "elapsed_seconds": round(time.perf_counter() - started, 3),
        }
        if proc.returncode == 0 and proc.stdout.strip():
            candidate_lines = proc.stdout.strip().splitlines()
            try:
                outer = json.loads(proc.stdout)
                if isinstance(outer, dict) and isinstance(outer.get("value"), list):
                    candidate_lines = [
                        str(item.get("message", ""))
                        for item in outer["value"]
                        if isinstance(item, dict) and str(item.get("message", "")).strip()
                    ] or candidate_lines
            except json.JSONDecodeError:
                pass
            for line in reversed(candidate_lines):
                try:
                    payload = json.loads(line)
                    if isinstance(payload, dict):
                        result.update(payload)
                        break
                except json.JSONDecodeError:
                    continue
            else:
                result["parse_error"] = "failed to parse JSON payload from local PowerShell output"
        return result
    except Exception as exc:
        return {
            "attempted": True,
            "ok": False,
            "error": str(exc),
            "elapsed_seconds": round(time.perf_counter() - started, 3),
        }


def _az_tsv(args: list[str], *, timeout: int = 120) -> str:
    proc = subprocess.run([_az_executable(), *args, "-o", "tsv"], check=False, capture_output=True, text=True, timeout=timeout)
    if proc.returncode != 0:
        raise RuntimeError(f"az {' '.join(args)} failed: {proc.stderr.strip() or proc.stdout.strip()}")
    return proc.stdout.strip()


def _get_vm_private_ip(*, resource_group: str, vm_name: str, timeout: int = 120) -> str:
    nic_id = _az_tsv(
        [
            "vm",
            "show",
            "-g",
            resource_group,
            "-n",
            vm_name,
            "--query",
            "networkProfile.networkInterfaces[0].id",
        ],
        timeout=timeout,
    )
    if not nic_id:
        raise RuntimeError(f"VM {vm_name} has no network interface")
    private_ip = _az_tsv(
        [
            "network",
            "nic",
            "show",
            "--ids",
            nic_id,
            "--query",
            "ipConfigurations[0].privateIPAddress",
        ],
        timeout=timeout,
    )
    if not private_ip:
        raise RuntimeError(f"VM {vm_name} has no private IP")
    return private_ip


def _ensure_bridge_health(
    bridge_url: str,
    bridge_secret: str,
    *,
    timeout: int,
    restart_resource_group: str = "",
    restart_vm_name: str = "",
    restart_task_name: str = "MCP-Factory-Bridge-Interactive",
    restart_timeout: int = 90,
    required_session_id: int | None = 1,
    session_cache_path: Path | None = None,
) -> dict:
    health = _wait_bridge_health(bridge_url, bridge_secret, timeout=timeout)
    process_info = None
    if health.get("ok") and required_session_id is not None and restart_resource_group and restart_vm_name:
        cached_proof = _cached_bridge_session_proof(
            cache_path=session_cache_path,
            bridge_url=bridge_url,
            health=health,
            resource_group=restart_resource_group,
            vm_name=restart_vm_name,
            required_session_id=required_session_id,
        )
        if cached_proof:
            health["bridge_process"] = cached_proof
            health["restart_attempted"] = False
            return health
        process_info = _bridge_process_info(
            resource_group=restart_resource_group,
            vm_name=restart_vm_name,
            timeout=restart_timeout,
        )
        health["bridge_process"] = process_info
        if process_info.get("ok") and process_info.get("session_id") == required_session_id:
            _write_bridge_session_cache(
                cache_path=session_cache_path,
                bridge_url=bridge_url,
                health=health,
                process_info=process_info,
                resource_group=restart_resource_group,
                vm_name=restart_vm_name,
            )
            health["restart_attempted"] = False
            return health
        health["ok"] = False
        health["error"] = (
            f"bridge process SessionId must be {required_session_id}; "
            f"found {process_info.get('session_id')}"
        )
    elif health.get("ok"):
        health["restart_attempted"] = False
        return health

    if not restart_resource_group or not restart_vm_name:
        health["restart_attempted"] = False
        health["restart_skipped"] = "restart_resource_group or restart_vm_name missing"
        return health

    print(
        "RESTART bridge: health check failed; "
        f"starting scheduled task {restart_task_name} on {restart_vm_name}"
    )
    vm_start = _ensure_bridge_vm_running(
        resource_group=restart_resource_group,
        vm_name=restart_vm_name,
        timeout=max(360, restart_timeout),
    )
    restart = _restart_bridge_task(
        resource_group=restart_resource_group,
        vm_name=restart_vm_name,
        task_name=restart_task_name,
        timeout=restart_timeout,
    )
    recovered = _wait_bridge_health(bridge_url, bridge_secret, timeout=timeout)
    recovered["restart_attempted"] = True
    recovered["vm_start_result"] = vm_start
    recovered["restart_result"] = restart
    if recovered.get("ok") and required_session_id is not None and restart_resource_group and restart_vm_name:
        process_info = _bridge_process_info(
            resource_group=restart_resource_group,
            vm_name=restart_vm_name,
            timeout=restart_timeout,
        )
        recovered["bridge_process"] = process_info
        if not process_info.get("ok") or process_info.get("session_id") != required_session_id:
            recovered["ok"] = False
            recovered["error"] = (
                f"bridge process SessionId must be {required_session_id}; "
                f"found {process_info.get('session_id')}"
            )
            print(
                "RESTART bridge VM: bridge listener is not in the required "
                f"SessionId={required_session_id}; rebooting {restart_vm_name} for AutoLogon"
            )
            vm_restart = _restart_bridge_vm(
                resource_group=restart_resource_group,
                vm_name=restart_vm_name,
                timeout=max(420, restart_timeout),
            )
            recovered["vm_restart_result"] = vm_restart
            if vm_restart.get("ok"):
                after_vm_restart = _wait_bridge_health(
                    bridge_url,
                    bridge_secret,
                    timeout=max(timeout, 90),
                )
                after_vm_restart["restart_attempted"] = True
                after_vm_restart["vm_start_result"] = vm_start
                after_vm_restart["restart_result"] = restart
                after_vm_restart["vm_restart_result"] = vm_restart
                process_info = _bridge_process_info(
                    resource_group=restart_resource_group,
                    vm_name=restart_vm_name,
                    timeout=restart_timeout,
                )
                after_vm_restart["bridge_process"] = process_info
                if process_info.get("ok") and process_info.get("session_id") == required_session_id:
                    _write_bridge_session_cache(
                        cache_path=session_cache_path,
                        bridge_url=bridge_url,
                        health=after_vm_restart,
                        process_info=process_info,
                        resource_group=restart_resource_group,
                        vm_name=restart_vm_name,
                    )
                    return after_vm_restart
                after_vm_restart["ok"] = False
                after_vm_restart["error"] = (
                    f"bridge process SessionId must be {required_session_id}; "
                    f"found {process_info.get('session_id')} after VM restart"
                )
                return after_vm_restart
        else:
            _write_bridge_session_cache(
                cache_path=session_cache_path,
                bridge_url=bridge_url,
                health=recovered,
                process_info=process_info,
                resource_group=restart_resource_group,
                vm_name=restart_vm_name,
            )
    return recovered


def _write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _touch_bridge_lease(*, storage_account: str, container: str, reason: str, job_id: str = "") -> None:
    payload = {
        "updated_at": time.time(),
        "reason": reason,
        "job_id": job_id,
        "source": "github-actions",
    }
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, suffix=".json") as fh:
        json.dump(payload, fh)
        temp_path = fh.name
    try:
        cmd = [
            _az_executable(), "storage", "blob", "upload",
            "--auth-mode", "login",
            "--account-name", storage_account,
            "--container-name", container,
            "--name", BRIDGE_ACTIVITY_BLOB,
            "--file", temp_path,
            "--overwrite", "true",
            "--only-show-errors",
        ]
        subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=60)
        print(f"LEASE bridge activity touched: reason={reason} job_id={job_id or '-'}")
    finally:
        Path(temp_path).unlink(missing_ok=True)


def _case_bool(value: object, default: bool = True) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).lower() not in {"0", "false", "no", "off"}


def _seconds(value: object) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return 0.0
    return 0.0


def _bridge_health_records(item: dict) -> list[dict]:
    records: list[dict] = []
    for key in ("health_before", "post_grace_health"):
        value = item.get(key)
        if isinstance(value, dict):
            records.append(value)
    for attempt in item.get("attempts") or []:
        if isinstance(attempt, dict) and isinstance(attempt.get("health_before_retry"), dict):
            records.append(attempt["health_before_retry"])
    return records


def _bridge_target_classification(item: dict) -> str:
    if item.get("passed"):
        if any(bool(record.get("vm_restart_result", {}).get("attempted")) for record in _bridge_health_records(item)):
            return "passed_after_vm_restart"
        if any(bool(record.get("restart_attempted")) for record in _bridge_health_records(item)):
            return "passed_after_bridge_recovery"
        if item.get("session_cache_used"):
            return "passed_cached_session"
        return "passed"

    text = " ".join(
        str(part or "")
        for part in [
            item.get("exception"),
            item.get("bridge_errors"),
            " ".join(str(attempt.get("error") or "") for attempt in item.get("attempts") or [] if isinstance(attempt, dict)),
            item.get("health_before", {}).get("error") if isinstance(item.get("health_before"), dict) else "",
            item.get("post_grace_health", {}).get("error") if isinstance(item.get("post_grace_health"), dict) else "",
        ]
    ).lower()
    if "sessionid" in text or "session id" in text:
        return "bridge_session_recovery_failed"
    if "timed out" in text or "timeout" in text:
        return "analyzer_timeout"
    if "connection reset" in text or "connection aborted" in text:
        return "bridge_connection_reset"
    if item.get("bridge_http_status") not in (None, 200):
        return "bridge_http_failure"
    if int(item.get("matched_invocable_count") or 0) < int(item.get("min_invocables") or 1):
        return "no_matching_invocables"
    return "failed"


def _add_bridge_timing_diagnostics(item: dict) -> dict:
    records = _bridge_health_records(item)
    analyzer_seconds = round(sum(_seconds(attempt.get("elapsed_seconds")) for attempt in item.get("attempts") or [] if isinstance(attempt, dict)), 3)
    retry_seconds = round(sum(_seconds(attempt.get("elapsed_seconds")) for attempt in (item.get("attempts") or [])[1:] if isinstance(attempt, dict)), 3)
    health_wait_seconds = round(sum(_seconds(record.get("waited_seconds") or record.get("elapsed_seconds")) for record in records), 3)
    session_check_seconds = round(
        sum(
            _seconds((record.get("bridge_process") or {}).get("elapsed_seconds"))
            for record in records
            if isinstance(record.get("bridge_process"), dict)
            and (record.get("bridge_process") or {}).get("attempted")
            and not (record.get("bridge_process") or {}).get("cached")
        ),
        3,
    )
    restart_seconds = round(
        sum(_seconds((record.get("restart_result") or {}).get("elapsed_seconds")) for record in records if isinstance(record.get("restart_result"), dict)),
        3,
    )
    vm_restart_seconds = round(
        sum(_seconds((record.get("vm_restart_result") or {}).get("elapsed_seconds")) for record in records if isinstance(record.get("vm_restart_result"), dict)),
        3,
    )
    cache_used = any(
        isinstance(record.get("bridge_process"), dict)
        and bool((record.get("bridge_process") or {}).get("cached"))
        for record in records
    )
    post_health = item.get("post_grace_health") if isinstance(item.get("post_grace_health"), dict) else {}
    post_grace_total = round(_seconds(item.get("configured_post_grace_seconds", item.get("post_grace_seconds"))) + _seconds(post_health.get("waited_seconds") or post_health.get("elapsed_seconds")), 3)
    dominant = {
        "analyzer": analyzer_seconds,
        "retry": retry_seconds,
        "health_wait": health_wait_seconds,
        "session_check": session_check_seconds,
        "bridge_restart": restart_seconds,
        "vm_restart": vm_restart_seconds,
        "post_grace": post_grace_total,
    }
    dominant_time_source = max(dominant, key=dominant.get) if any(value > 0 for value in dominant.values()) else "unknown"
    item["session_cache_used"] = cache_used
    item.update(
        {
            "health_wait_seconds": health_wait_seconds,
            "session_check_seconds": session_check_seconds,
            "bridge_analyzer_seconds": analyzer_seconds,
            "retry_seconds": retry_seconds,
            "restart_seconds": restart_seconds,
            "vm_restart_seconds": vm_restart_seconds,
            "post_grace_seconds": post_grace_total,
            "dominant_time_source": dominant_time_source,
            "timeout_or_failure_classification": _bridge_target_classification(item),
        }
    )
    return item


def _filter_invocables(
    invocables: list[dict],
    *,
    expect_source_type: str = "",
    expect_name_contains: str = "",
) -> list[dict]:
    filtered = invocables
    if expect_source_type:
        expected = expect_source_type.lower()
        filtered = [
            inv for inv in filtered
            if str(inv.get("source_type") or inv.get("kind") or "").lower() == expected
        ]
    if expect_name_contains:
        needle = expect_name_contains.lower()
        filtered = [
            inv for inv in filtered
            if needle in str(inv.get("name", "")).lower()
            or needle in str(inv.get("description", "")).lower()
        ]
    return filtered


def _bridge_analyze_once(
    bridge_url: str,
    bridge_secret: str,
    target: str,
    *,
    hints: str,
    types: list[str],
    timeout: int,
    raw_path: Path,
) -> dict:
    body = {
        "path": target,
        "hints": hints,
        "types": types,
    }
    if Path(target).exists():
        import base64

        raw = Path(target).read_bytes()
        body["content"] = base64.b64encode(raw).decode("ascii")

    req = request.Request(
        f"{bridge_url.rstrip('/')}/analyze",
        data=json.dumps(body).encode("utf-8"),
        headers={"X-Bridge-Key": bridge_secret, "Content-Type": "application/json"},
        method="POST",
    )
    started = time.perf_counter()
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            raw_lines = [line.decode("utf-8", errors="replace").strip() for line in resp.readlines() if line.strip()]
            raw_text = "\n".join(raw_lines)
            raw_path.write_text(raw_text, encoding="utf-8")
            try:
                payload = json.loads(raw_lines[-1]) if raw_lines else {}
            except json.JSONDecodeError as exc:
                return {
                    "ok": False,
                    "http_status": resp.status,
                    "payload": {},
                    "error": f"invalid bridge JSON response: {exc}",
                    "elapsed_seconds": round(time.perf_counter() - started, 3),
                    "raw_response_path": str(raw_path),
                }
            return {
                "ok": True,
                "http_status": resp.status,
                "payload": payload,
                "elapsed_seconds": round(time.perf_counter() - started, 3),
                "raw_response_path": str(raw_path),
            }
    except error.HTTPError as exc:
        raw_text = exc.read().decode("utf-8", errors="replace")
        raw_path.write_text(raw_text, encoding="utf-8")
        return {
            "ok": False,
            "http_status": exc.code,
            "payload": {},
            "error": raw_text or str(exc),
            "elapsed_seconds": round(time.perf_counter() - started, 3),
            "raw_response_path": str(raw_path),
        }
    except Exception as exc:
        raw_path.write_text(str(exc), encoding="utf-8")
        return {
            "ok": False,
            "http_status": None,
            "payload": {},
            "error": str(exc),
            "elapsed_seconds": round(time.perf_counter() - started, 3),
            "raw_response_path": str(raw_path),
        }


def cmd_cloud_gpt_e2e(args: argparse.Namespace) -> int:
    base_url = args.base_url.rstrip("/")
    target = Path(args.target)
    sentinel = args.sentinel or f"MCP_FACTORY_E2E_{uuid.uuid4().hex[:10]}"

    def touch(reason: str) -> None:
        if args.lease_storage_account and args.lease_container:
            _touch_bridge_lease(
                storage_account=args.lease_storage_account,
                container=args.lease_container,
                reason=f"gpt4o-e2e-{reason}",
                job_id=args.lease_job_id,
            )

    touch("upload-start")
    job_id = _upload_file(base_url, target, key=args.pipeline_key or "", hints=f"e2e sentinel {sentinel}")
    touch(f"uploaded-{job_id}")
    status_history: list[dict] = []
    deadline = time.monotonic() + args.timeout
    while True:
        touch(f"poll-{job_id}")
        job = _http_json("GET", f"{base_url}/api/jobs/{job_id}", key=args.pipeline_key or "", timeout=30)
        status_history.append(job)
        status = job.get("status")
        print(f"job {job_id}: status={status} progress={job.get('progress')} message={job.get('message', '')}")
        if status == "done":
            break
        if status == "error":
            raise AssertionError(f"job {job_id} failed: {job.get('error') or job.get('message')}")
        if time.monotonic() >= deadline:
            raise AssertionError(f"job {job_id} timed out after {args.timeout}s; last={job}")
        time.sleep(5)
    result = job.get("result") or {}
    invocables = _validate_invocables(result, min_invocables=1, label=f"job {job_id}")

    selected = [inv for inv in invocables if inv.get("name") == args.tool_name]
    if not selected:
        selected = invocables[:1]
    if not selected:
        raise AssertionError("no invocable selected for E2E")

    artifact_dir = Path(args.artifact_dir)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    selected_path = artifact_dir / "selected-invocable.json"
    status_history_path = artifact_dir / "job-status-history.json"
    _write_json(selected_path, selected[0])
    _write_json(status_history_path, status_history)

    touch(f"generate-{job_id}")
    gen = _http_json(
        "POST",
        f"{base_url}/api/generate",
        key=args.pipeline_key or "",
        body={"job_id": job_id, "component_name": f"e2e-{job_id}", "selected": selected},
        timeout=120,
    )
    schema = gen.get("mcp_schema") or {}
    tools = _validate_mcp_schema(schema, min_tools=1, label=f"generated schema {job_id}")
    generated_schema_path = artifact_dir / "generated-mcp-schema.json"
    _write_json(generated_schema_path, schema)

    touch(f"chat-{job_id}")
    prompt = (
        f"Call the tool named {selected[0]['name']} now. "
        f"The successful tool output must contain this sentinel: {sentinel}. "
        "Do not just say done."
    )
    chat_body = {
        "job_id": job_id,
        "messages": [{"role": "user", "content": prompt}],
        "tools": tools,
        "invocables": selected,
    }
    raw_chat = _http_bytes(
        "POST",
        f"{base_url}/api/chat",
        key=args.pipeline_key or "",
        body=json.dumps(chat_body).encode("utf-8"),
        content_type="application/json",
        timeout=args.chat_timeout,
    ).decode("utf-8", errors="replace")
    events = _parse_sse(raw_chat)
    if not any(evt.get("type") == "tool_call" for evt in events):
        raise AssertionError(f"GPT E2E failed: no tool_call event in transcript: {events}")
    tool_results = [evt for evt in events if evt.get("type") == "tool_result"]
    if not any(sentinel in str(evt.get("result", "")) for evt in tool_results):
        raise AssertionError(f"GPT E2E failed: sentinel not found in tool_result events: {tool_results}")

    downloaded_schema_ok = False
    downloaded_schema_path = artifact_dir / "downloaded-mcp-schema.json"
    touch(f"download-schema-{job_id}")
    try:
        downloaded_schema_path.write_bytes(
            _http_bytes("GET", f"{base_url}/api/download/{job_id}/mcp_schema.json", key=args.pipeline_key or "", timeout=60)
        )
        downloaded_schema_ok = True
    except Exception as exc:
        (artifact_dir / "downloaded-mcp-schema.error.txt").write_text(str(exc), encoding="utf-8")

    transcript_path = Path(args.transcript or f"gpt4o-e2e-{job_id}.json")
    transcript_path.parent.mkdir(parents=True, exist_ok=True)
    transcript_path.write_text(json.dumps({"job_id": job_id, "sentinel": sentinel, "events": events}, indent=2), encoding="utf-8")
    touch(f"complete-{job_id}")
    print(
        "OK cloud GPT E2E: "
        f"job={job_id} tool={selected[0]['name']} sentinel={sentinel} "
        f"invocables={len(invocables)} schema_tools={len(tools)} "
        f"downloaded_schema={downloaded_schema_ok} transcript={transcript_path}"
    )
    return 0


def cmd_cloud_gpt_format_matrix(args: argparse.Namespace) -> int:
    base_url = args.base_url.rstrip("/")
    manifest = _load_json(Path(args.manifest))
    out_root = Path(args.artifact_dir)
    out_root.mkdir(parents=True, exist_ok=True)
    sentinel_prefix = args.sentinel_prefix or f"MCP_FACTORY_FORMAT_{uuid.uuid4().hex[:8]}"

    def touch(reason: str) -> None:
        if args.lease_storage_account and args.lease_container:
            _touch_bridge_lease(
                storage_account=args.lease_storage_account,
                container=args.lease_container,
                reason=f"gpt-format-matrix-{reason}",
                job_id=args.lease_job_id,
            )

    summaries: list[dict] = []
    for case in manifest.get("non_vm_cases", []):
        case_id = case["id"]
        if args.only_case and case_id != args.only_case:
            continue
        case_dir = out_root / case_id
        case_dir.mkdir(parents=True, exist_ok=True)
        sentinel = f"{sentinel_prefix}_{case_id}"
        proof_level = case.get("proof_level", "provider_required")
        runtime_mode = _runtime_mode_for_case(case)
        started = time.perf_counter()
        item = {
            "id": case_id,
            "category": case.get("category", case_id),
            "proof_level": proof_level,
            "runtime_mode": runtime_mode,
            "expected_result": case.get("expected_result", ""),
            "passed": False,
            "tool_call_seen": False,
            "tool_result_seen": False,
            "sentinel_seen": False,
            "provider_required_seen": False,
            "transcript_path": str(case_dir / "transcript.json"),
            "job_id": "",
            "selected_tool": "",
            "schema_tool_count": 0,
            "error": "",
            "elapsed_seconds": 0.0,
        }
        print(f"START GPT format case {case_id}: category={item['category']} proof_level={proof_level} runtime_mode={runtime_mode}")
        try:
            touch(f"{case_id}-upload-start")
            target = ROOT / case["path"]
            job_id = _upload_file(
                base_url,
                target,
                key=args.pipeline_key or "",
                hints=f"sponsor format matrix {case_id} {proof_level} sentinel {sentinel}",
            )
            item["job_id"] = job_id

            status_history: list[dict] = []
            deadline = time.monotonic() + args.timeout
            while True:
                touch(f"{case_id}-poll-{job_id}")
                job = _http_json("GET", f"{base_url}/api/jobs/{job_id}", key=args.pipeline_key or "", timeout=30)
                status_history.append(job)
                status = job.get("status")
                print(f"GPT {case_id}: job={job_id} status={status} progress={job.get('progress')} message={job.get('message', '')}")
                if status == "done":
                    break
                if status == "error":
                    raise AssertionError(f"job {job_id} failed: {job.get('error') or job.get('message')}")
                if time.monotonic() >= deadline:
                    raise AssertionError(f"job {job_id} timed out after {args.timeout}s; last={job}")
                time.sleep(5)

            _write_json(case_dir / "job-status-history.json", status_history)
            result = job.get("result") or {}
            invocables = _validate_invocables(
                result,
                min_invocables=int(case.get("min_invocables", 1)),
                label=f"{case_id} discovery",
            )
            matched = _filter_invocables(
                invocables,
                expect_source_type=case.get("expect_source_type", ""),
                expect_name_contains=case.get("expect_name_contains", ""),
            )
            selected = _select_invocable_for_case(case, matched or invocables)
            if proof_level == "real_execution" and not selected.get("parameters"):
                selected = {
                    **selected,
                    "parameters": [{"name": "sentinel", "type": "string", "description": "Deterministic E2E sentinel"}],
                }
            selected_name = selected.get("name", "")
            tool_name = _safe_tool_name(selected_name)
            item["selected_tool"] = selected_name
            _write_json(case_dir / "selected-invocable.json", selected)

            touch(f"{case_id}-generate-{job_id}")
            gen = _http_json(
                "POST",
                f"{base_url}/api/generate",
                key=args.pipeline_key or "",
                body={"job_id": job_id, "component_name": f"format-{case_id}-{job_id}", "selected": [selected]},
                timeout=120,
            )
            schema = gen.get("mcp_schema") or {}
            tools = _validate_mcp_schema(schema, min_tools=1, label=f"{case_id} generated schema")
            item["schema_tool_count"] = len(tools)
            _write_json(case_dir / "generated-mcp-schema.json", schema)

            downloaded_schema_ok = False
            try:
                touch(f"{case_id}-download-schema-{job_id}")
                (case_dir / "downloaded-mcp-schema.json").write_bytes(
                    _http_bytes("GET", f"{base_url}/api/download/{job_id}/mcp_schema.json", key=args.pipeline_key or "", timeout=60)
                )
                downloaded_schema_ok = True
            except Exception as exc:
                (case_dir / "downloaded-mcp-schema.error.txt").write_text(str(exc), encoding="utf-8")

            if proof_level == "real_execution":
                prompt = (
                    f"Call the tool named {tool_name} now. "
                    f"Use this exact sentinel string as the value for every required string argument: {sentinel}. "
                    f"The successful tool output must contain this sentinel: {sentinel}. "
                    "Do not just say done."
                )
            else:
                prompt = (
                    f"Call the tool named {tool_name} now. "
                    "This is a contract proof and no live backing provider is configured. "
                    "The expected tool result must state that a live provider, endpoint, or service is required. "
                    "Do not just say done."
                )

            touch(f"{case_id}-chat-{job_id}")
            raw_chat = _http_bytes(
                "POST",
                f"{base_url}/api/chat",
                key=args.pipeline_key or "",
                body=json.dumps({
                    "job_id": job_id,
                    "messages": [{"role": "user", "content": prompt}],
                    "tools": tools,
                    "invocables": [selected],
                }).encode("utf-8"),
                content_type="application/json",
                timeout=args.chat_timeout,
            ).decode("utf-8", errors="replace")
            events = _parse_sse(raw_chat)
            tool_results = [evt for evt in events if evt.get("type") == "tool_result"]
            result_text = "\n".join(str(evt.get("result", "")) for evt in tool_results)
            item["tool_call_seen"] = any(evt.get("type") == "tool_call" for evt in events)
            item["tool_result_seen"] = bool(tool_results)
            item["sentinel_seen"] = bool(sentinel in result_text)
            item["provider_required_seen"] = _provider_required_seen(result_text)
            item["downloaded_schema_exists"] = downloaded_schema_ok
            transcript = {
                "case_id": case_id,
                "job_id": job_id,
                "sentinel": sentinel,
                "proof_level": proof_level,
                "runtime_mode": runtime_mode,
                "selected_tool": selected_name,
                "events": events,
            }
            _write_json(case_dir / "transcript.json", transcript)

            if not item["tool_call_seen"]:
                raise AssertionError("GPT did not emit a tool_call")
            if not item["tool_result_seen"]:
                raise AssertionError("tool_result event missing")
            if proof_level == "real_execution" and not item["sentinel_seen"]:
                raise AssertionError("sentinel not found in real execution tool_result")
            if proof_level == "provider_required" and not item["provider_required_seen"]:
                raise AssertionError("provider-required result was not observed")
            if not downloaded_schema_ok:
                raise AssertionError("downloaded MCP schema artifact missing")
            item["passed"] = True
            touch(f"{case_id}-complete-{job_id}")
        except Exception as exc:
            item["error"] = str(exc)
            (case_dir / "error.txt").write_text(str(exc), encoding="utf-8")
        finally:
            item["elapsed_seconds"] = round(time.perf_counter() - started, 3)
            _write_json(case_dir / "summary.json", item)
            summaries.append(item)
            status = "OK" if item["passed"] else "FAIL"
            print(
                f"{status} GPT format {case_id}: "
                f"tool_call={item['tool_call_seen']} tool_result={item['tool_result_seen']} "
                f"sentinel={item['sentinel_seen']} provider_required={item['provider_required_seen']} "
                f"elapsed={item['elapsed_seconds']}s"
            )

    failures = [item for item in summaries if not item.get("passed")]
    real_cases = [item for item in summaries if item.get("proof_level") == "real_execution"]
    provider_cases = [item for item in summaries if item.get("proof_level") == "provider_required"]
    runtime_mode_counts = _runtime_mode_counts(summaries)
    adapter_backed_cases = [item["id"] for item in summaries if item.get("runtime_mode") == "adapter_backed"]
    runtime_backed_cases = [
        item["id"]
        for item in summaries
        if item.get("runtime_mode") in {"real_runtime", "validated_runtime", "lookup_runtime", "ldap_runtime", "xmlrpc_runtime", "msrpc_runtime", "corba_idl_runtime", "corba_orb_runtime", "local_runtime"}
    ]
    aggregate = {
        "cases": summaries,
        "total": len(summaries),
        "failures": len(failures),
        "failed_ids": [item["id"] for item in failures],
        "real_execution_cases": [item["id"] for item in real_cases],
        "real_execution_total": len(real_cases),
        "real_execution_passed": sum(1 for item in real_cases if item.get("passed") and item.get("sentinel_seen")),
        "provider_required_cases": [item["id"] for item in provider_cases],
        "provider_required_total": len(provider_cases),
        "provider_required_tool_call_passed": sum(
            1 for item in provider_cases
            if item.get("passed") and item.get("tool_call_seen") and item.get("provider_required_seen")
        ),
        "not_live_executed_because_provider_required": [item["id"] for item in provider_cases],
        "all_required_cases_live_execution": len(provider_cases) == 0 and len(real_cases) == len(summaries),
        "runtime_mode_counts": runtime_mode_counts,
        "runtime_backed_cases": runtime_backed_cases,
        "adapter_backed_cases": adapter_backed_cases,
    }
    _write_json(out_root / "summary.json", aggregate)
    if failures:
        raise AssertionError(f"{len(failures)} GPT format matrix case(s) failed: {aggregate['failed_ids']}")
    print(f"OK GPT format matrix: {len(summaries)} case(s), artifacts={out_root}")
    return 0


def cmd_ldap_runtime_proof(args: argparse.Namespace) -> int:
    base_url = args.base_url.rstrip("/")
    artifact_dir = Path(args.artifact_dir)
    matrix_out = Path(args.matrix_out)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    sentinel = args.sentinel or f"MCP_FACTORY_LDAP_RUNTIME_{uuid.uuid4().hex[:8]}"
    key = args.pipeline_key or ""

    print(f"START LDAP runtime proof: base_url={base_url}")
    health = _http_json("GET", f"{base_url}/api/legacy/health", key=key, timeout=args.timeout)
    provider_modes = health.get("provider_modes") or {}
    if provider_modes.get("jndi") != "ldap_runtime":
        raise AssertionError(f"legacy provider jndi mode is not ldap_runtime: {provider_modes.get('jndi')!r}")

    ldif = _http_bytes("GET", f"{base_url}/api/legacy/jndi/ldif", key=key, timeout=args.timeout).decode("utf-8")
    bind = _http_json(
        "POST",
        f"{base_url}/api/legacy/jndi/bind",
        key=key,
        body={"principal": "cn=serviceaccount,dc=contoso,dc=com", "sentinel": sentinel},
        timeout=args.timeout,
    )
    search = _http_json(
        "POST",
        f"{base_url}/api/legacy/jndi/search",
        key=key,
        body={"filter": "ContosoCustomerDB", "sentinel": sentinel},
        timeout=args.timeout,
    )
    lookup = _http_json(
        "POST",
        f"{base_url}/api/legacy/jndi/lookup",
        key=key,
        body={"name": "jdbc/ContosoCustomerDB", "sentinel": sentinel},
        timeout=args.timeout,
    )

    checks = {
        "provider_mode_is_ldap_runtime": provider_modes.get("jndi") == "ldap_runtime",
        "ldif_has_contoso_entry": "ContosoCustomerDB" in ldif and "objectClass: javaNamingReference" in ldif,
        "bind_uses_ldapv3_wire": bind.get("wire_protocol") == "ldapv3" and bool(bind.get("bound")),
        "search_uses_ldapv3_wire": search.get("wire_protocol") == "ldapv3" and bool(search.get("entries")),
        "lookup_uses_ldapv3_wire": lookup.get("wire_protocol") == "ldapv3" and bool(lookup.get("lookup_found")),
        "sentinel_echoed": sentinel in json.dumps(lookup, sort_keys=True),
    }
    passed = all(checks.values())
    (artifact_dir / "ldap-server-config.ldif").write_text(ldif, encoding="utf-8")
    _write_json(artifact_dir / "health.json", health)
    _write_json(artifact_dir / "bind-result.json", bind)
    _write_json(artifact_dir / "search-result.json", search)
    _write_json(artifact_dir / "lookup-result.json", lookup)

    summary = {
        "id": "ldap_runtime",
        "passed": passed,
        "proof_level": "real_runtime",
        "runtime_mode": "ldap_runtime",
        "provider": "jndi",
        "wire_protocol": "ldapv3",
        "sentinel": sentinel,
        "checks": checks,
        "artifacts": {
            "ldif": str(artifact_dir / "ldap-server-config.ldif"),
            "bind": str(artifact_dir / "bind-result.json"),
            "search": str(artifact_dir / "search-result.json"),
            "lookup": str(artifact_dir / "lookup-result.json"),
            "health": str(artifact_dir / "health.json"),
        },
        "notes": "Controlled LDAPv3-compatible runtime proof for deterministic JNDI bind/search/lookup, not enterprise directory migration.",
    }
    _write_json(artifact_dir / "summary.json", summary)

    matrix = _load_optional_summary(matrix_out)
    if not isinstance(matrix, dict) or matrix.get("missing"):
        matrix = {}
    matrix["ldap_runtime"] = summary
    matrix["passed"] = all(bool(value.get("passed")) for value in matrix.values() if isinstance(value, dict) and "passed" in value)
    _write_json(matrix_out, matrix)
    if not passed:
        raise AssertionError(f"LDAP runtime proof failed checks: {[name for name, ok in checks.items() if not ok]}")
    print(f"OK LDAP runtime proof: artifacts={artifact_dir}")
    return 0


def cmd_corba_orb_runtime_proof(args: argparse.Namespace) -> int:
    base_url = args.base_url.rstrip("/")
    artifact_dir = Path(args.artifact_dir)
    matrix_out = Path(args.matrix_out)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    sentinel = args.sentinel or f"MCP_FACTORY_CORBA_ORB_{uuid.uuid4().hex[:8]}"
    key = args.pipeline_key or ""

    print(f"START CORBA ORB runtime proof: base_url={base_url}")
    health = _http_json("GET", f"{base_url}/api/legacy/health", key=key, timeout=args.timeout)
    provider_modes = health.get("provider_modes") or {}
    if provider_modes.get("corba") != "corba_orb_runtime":
        raise AssertionError(f"legacy provider corba mode is not corba_orb_runtime: {provider_modes.get('corba')!r}")

    idl = _http_bytes("GET", f"{base_url}/api/legacy/corba/idl", key=key, timeout=args.timeout).decode("utf-8")
    invocation = _http_json(
        "POST",
        f"{base_url}/api/legacy/corba/ICustomerService_getCustomer",
        key=key,
        body={"sentinel": sentinel},
        timeout=args.timeout,
    )
    orb_invocation = invocation.get("orb_invocation") or {}
    server_log = orb_invocation.get("server_log") or []
    checks = {
        "provider_mode_is_corba_orb_runtime": provider_modes.get("corba") == "corba_orb_runtime",
        "idl_has_contoso_interface": "interface CustomerService" in idl and "module ContosoSupport" in idl,
        "object_reference_is_ior": str(orb_invocation.get("object_reference", "")).startswith("IOR:"),
        "wire_protocol_is_iiop": orb_invocation.get("wire_protocol") == "IIOP",
        "server_registered_object": any("registered ICustomerService" in str(item) for item in server_log),
        "client_result_has_sentinel": sentinel in json.dumps(invocation, sort_keys=True),
        "provider_result_mode": invocation.get("runtime_mode") == "corba_orb_runtime",
    }
    passed = all(checks.values())
    (artifact_dir / "contoso_support.idl").write_text(idl, encoding="utf-8")
    (artifact_dir / "object-reference.txt").write_text(str(orb_invocation.get("object_reference", "")), encoding="utf-8")
    (artifact_dir / "orb-server.log").write_text("\n".join(str(item) for item in server_log), encoding="utf-8")
    _write_json(artifact_dir / "health.json", health)
    _write_json(artifact_dir / "client-invocation.json", invocation)
    summary = {
        "id": "corba_orb_runtime",
        "passed": passed,
        "proof_level": "real_runtime",
        "runtime_mode": "corba_orb_runtime",
        "provider": "corba",
        "wire_protocol": "IIOP",
        "orb": orb_invocation.get("orb", "OmniORB"),
        "sentinel": sentinel,
        "checks": checks,
        "artifacts": {
            "idl": str(artifact_dir / "contoso_support.idl"),
            "object_reference": str(artifact_dir / "object-reference.txt"),
            "server_log": str(artifact_dir / "orb-server.log"),
            "client_invocation": str(artifact_dir / "client-invocation.json"),
            "health": str(artifact_dir / "health.json"),
        },
        "notes": "Controlled OmniORB/IIOP proof for deterministic Contoso IDL, not generalized CORBA estate support.",
    }
    _write_json(artifact_dir / "summary.json", summary)

    matrix = _load_optional_summary(matrix_out)
    if not isinstance(matrix, dict) or matrix.get("missing"):
        matrix = {}
    matrix["corba_orb_runtime"] = summary
    matrix["passed"] = all(bool(value.get("passed")) for value in matrix.values() if isinstance(value, dict) and "passed" in value)
    _write_json(matrix_out, matrix)
    if not passed:
        raise AssertionError(f"CORBA ORB runtime proof failed checks: {[name for name, ok in checks.items() if not ok]}")
    print(f"OK CORBA ORB runtime proof: artifacts={artifact_dir}")
    return 0


def cmd_msrpc_runtime_proof(args: argparse.Namespace) -> int:
    base_url = args.base_url.rstrip("/")
    artifact_dir = Path(args.artifact_dir)
    matrix_out = Path(args.matrix_out)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    sentinel = args.sentinel or f"MCP_FACTORY_MSRPC_{uuid.uuid4().hex[:8]}"
    key = args.pipeline_key or ""

    print(f"START MSRPC runtime proof: base_url={base_url}")
    health = _http_json("GET", f"{base_url}/api/legacy/health", key=key, timeout=args.timeout)
    provider_modes = health.get("provider_modes") or {}
    if provider_modes.get("rpc") != "msrpc_runtime":
        raise AssertionError(f"legacy provider rpc mode is not msrpc_runtime: {provider_modes.get('rpc')!r}")

    idl = _http_bytes("GET", f"{base_url}/api/legacy/rpc/idl", key=key, timeout=args.timeout).decode("utf-8")
    invocation = _http_json(
        "POST",
        f"{base_url}/api/legacy/rpc/RpcCreateTicket",
        key=key,
        body={"sentinel": sentinel},
        timeout=args.timeout,
    )
    msrpc = invocation.get("msrpc_invocation") or {}
    server_log = msrpc.get("server_log") or []
    checks = {
        "provider_mode_is_msrpc_runtime": provider_modes.get("rpc") == "msrpc_runtime",
        "idl_has_contoso_interface": "interface ContosoRpcSupport" in idl and "uuid(" in idl,
        "binding_is_ncacn_ip_tcp": str(msrpc.get("binding", "")).startswith("ncacn_ip_tcp:"),
        "wire_protocol_is_dcerpc": str(msrpc.get("wire_protocol", "")).startswith("DCE/RPC"),
        "server_registered_interface": any("registered uuid=" in str(item) for item in server_log),
        "client_result_has_sentinel": sentinel in json.dumps(invocation, sort_keys=True),
        "provider_result_mode": invocation.get("runtime_mode") == "msrpc_runtime",
    }
    passed = all(checks.values())
    (artifact_dir / "contoso_rpc.idl").write_text(idl, encoding="utf-8")
    _write_json(artifact_dir / "endpoint-registration.json", {
        "binding": msrpc.get("binding"),
        "interface_uuid": msrpc.get("interface_uuid"),
        "interface_version": msrpc.get("interface_version"),
        "server_log": server_log,
    })
    _write_json(artifact_dir / "client-invocation.json", invocation)
    summary = {
        "id": "msrpc_runtime",
        "passed": passed,
        "proof_level": "real_runtime",
        "runtime_mode": "msrpc_runtime",
        "provider": "rpc",
        "wire_protocol": "DCE/RPC v5 over ncacn_ip_tcp",
        "rpc_stack": msrpc.get("rpc_stack", "impacket"),
        "sentinel": sentinel,
        "checks": checks,
        "artifacts": {
            "idl": str(artifact_dir / "contoso_rpc.idl"),
            "endpoint_registration": str(artifact_dir / "endpoint-registration.json"),
            "client_invocation": str(artifact_dir / "client-invocation.json"),
        },
        "notes": "Controlled DCE/RPC-compatible proof for deterministic Contoso RPC IDL, not arbitrary enterprise MSRPC estate support.",
    }
    _write_json(artifact_dir / "summary.json", summary)

    matrix = _load_optional_summary(matrix_out)
    if not isinstance(matrix, dict) or matrix.get("missing"):
        matrix = {}
    matrix["msrpc_runtime"] = summary
    matrix["passed"] = all(bool(value.get("passed")) for value in matrix.values() if isinstance(value, dict) and "passed" in value)
    _write_json(matrix_out, matrix)
    if not passed:
        raise AssertionError(f"MSRPC runtime proof failed checks: {[name for name, ok in checks.items() if not ok]}")
    print(f"OK MSRPC runtime proof: artifacts={artifact_dir}")
    return 0


def _windows_observed_invocable(label: str, summary: dict) -> dict:
    description = (
        f"Return the recorded Windows bridge discovery proof for {label}. "
        "This is a generated proof tool for sponsor CI; it observes the discovery artifact and does not claim "
        "semantic execution of arbitrary Windows system binaries."
    )
    observed = {
        "label": label,
        "target": summary.get("target"),
        "category": summary.get("category"),
        "passed": summary.get("passed"),
        "matched_invocable_count": summary.get("matched_invocable_count"),
        "invocable_count": summary.get("invocable_count"),
        "first_20_invocable_names": summary.get("first_20_invocable_names") or [],
        "timeout_or_failure_classification": summary.get("timeout_or_failure_classification") or "",
    }
    return {
        "name": f"{label}_observed_result",
        "source_type": "windows_bridge_observed_result",
        "description": description,
        "parameters": [
            {
                "name": "acknowledgement",
                "type": "string",
                "description": "Short note confirming the Windows target proof being requested.",
            }
        ],
        "execution": {
            "method": "observed_result",
            "target_label": label,
            "artifact_path": f"ci_artifacts/demo/windows/{label}/{label}.summary.json",
            "summary_path": summary.get("summary_path") or f"ci_artifacts/demo/windows/{label}/{label}.summary.json",
            "source": "windows_bridge_summary",
            "observed_result": observed,
        },
    }


def cmd_windows_gpt_tool_matrix(args: argparse.Namespace) -> int:
    base_url = args.base_url.rstrip("/")
    windows_dir = Path(args.windows_dir)
    out_root = Path(args.artifact_dir)
    out_root.mkdir(parents=True, exist_ok=True)
    targets = [args.only_target] if args.only_target else list(WINDOWS_GPT_PROOF_TARGETS)
    summaries: list[dict] = []

    for label in targets:
        case_dir = out_root / label
        case_dir.mkdir(parents=True, exist_ok=True)
        started = time.perf_counter()
        item = {
            "id": label,
            "proof_level": "tool_result_observed",
            "passed": False,
            "discovery_summary_exists": False,
            "selected_invocable_exists": False,
            "generated_schema_exists": False,
            "downloaded_schema_exists": False,
            "tool_call_seen": False,
            "tool_result_seen": False,
            "transcript_exists": False,
            "job_id": "",
            "selected_tool": "",
            "error": "",
            "elapsed_seconds": 0.0,
        }
        summary_path = windows_dir / label / f"{label}.summary.json"
        print(f"START Windows GPT proof {label}: summary={summary_path}")
        try:
            if not summary_path.exists():
                raise AssertionError(f"Windows discovery summary missing: {summary_path}")
            item["discovery_summary_exists"] = True
            summary = _load_json(summary_path)
            if not summary.get("passed"):
                raise AssertionError(f"Windows discovery summary did not pass: {summary_path}")
            if int(summary.get("matched_invocable_count") or 0) < 1:
                raise AssertionError(f"Windows discovery summary has no matched invocables: {summary_path}")
            selected = _windows_observed_invocable(label, summary)
            item["selected_tool"] = selected["name"]
            item["selected_invocable_exists"] = True
            job_id = f"win-{label}-{uuid.uuid4().hex[:8]}"
            item["job_id"] = job_id
            tool_name = _safe_tool_name(selected["name"])
            proof = _call_generated_tool_with_gpt(
                base_url=base_url,
                pipeline_key=args.pipeline_key or "",
                job_id=job_id,
                component_name=f"windows-{label}-{job_id}",
                selected=selected,
                artifact_dir=case_dir,
                prompt=(
                    f"Call the tool named {tool_name} now. "
                    f"It must return the recorded Windows bridge discovery proof for {label}. "
                    "Do not just say done."
                ),
                chat_timeout=args.chat_timeout,
            )
            item["generated_schema_exists"] = bool(proof["tools"])
            item["downloaded_schema_exists"] = bool(proof["downloaded_schema_exists"])
            item["tool_call_seen"] = bool(proof["tool_call_seen"])
            item["tool_result_seen"] = bool(proof["tool_result_seen"])
            transcript = {
                "case_id": label,
                "job_id": job_id,
                "proof_level": "tool_result_observed",
                "selected_tool": selected["name"],
                "source_summary": str(summary_path),
                "events": proof["events"],
            }
            _write_json(case_dir / "transcript.json", transcript)
            item["transcript_exists"] = True
            if not item["tool_call_seen"]:
                raise AssertionError("GPT did not emit a tool_call")
            if not item["tool_result_seen"]:
                raise AssertionError("tool_result event missing")
            if not item["downloaded_schema_exists"]:
                raise AssertionError("downloaded MCP schema artifact missing")
            item["passed"] = True
        except Exception as exc:
            item["error"] = str(exc)
            (case_dir / "error.txt").write_text(str(exc), encoding="utf-8")
        finally:
            item["elapsed_seconds"] = round(time.perf_counter() - started, 3)
            _write_json(case_dir / "summary.json", item)
            summaries.append(item)
            print(
                f"{'OK' if item['passed'] else 'FAIL'} Windows GPT {label}: "
                f"tool_call={item['tool_call_seen']} tool_result={item['tool_result_seen']} "
                f"elapsed={item['elapsed_seconds']}s"
            )

    failures = [item for item in summaries if not item.get("passed")]
    aggregate = {
        "cases": summaries,
        "total": len(summaries),
        "passed": len(summaries) - len(failures),
        "failures": len(failures),
        "failed_ids": [item["id"] for item in failures],
        "proof_level": "tool_result_observed",
        "targets": targets,
    }
    _write_json(out_root / "summary.json", aggregate)
    if failures:
        raise AssertionError(f"{len(failures)} Windows GPT tool proof case(s) failed: {aggregate['failed_ids']}")
    print(f"OK Windows GPT tool matrix: {len(summaries)} case(s), artifacts={out_root}")
    return 0


def cmd_windows_com_runtime_proof(args: argparse.Namespace) -> int:
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sentinel = args.sentinel or f"MCP_FACTORY_COM_RUNTIME_{uuid.uuid4().hex[:10]}"
    script = f"""
$ErrorActionPreference = "Stop"
$sentinel = {_ps_quote(sentinel)}
$dict = New-Object -ComObject Scripting.Dictionary
$dict.Add("sentinel", $sentinel)
$shell = New-Object -ComObject WScript.Shell
$value = $dict.Item("sentinel")
$result = [ordered]@{{
    passed = ($value -eq $sentinel)
    proof_level = "com_runtime"
    runtime_mode = "com_runtime"
    dcom_surface = "local_com_automation"
    remote_dcom_activation_claimed = $false
    com_objects = @("Scripting.Dictionary", "WScript.Shell")
    sentinel = $sentinel
    dictionary_count = $dict.Count
    shell_type = $shell.GetType().FullName
    notes = "Local COM automation proof on the Windows bridge VM; remote DCOM activation is not claimed."
}}
$result | ConvertTo-Json -Compress
"""
    payload = _run_vm_powershell_json(
        resource_group=args.resource_group,
        vm_name=args.vm_name,
        script=script,
        timeout=args.timeout,
    )
    summary = {
        "label": "com_runtime",
        "target": "Windows local COM automation",
        "passed": bool(payload.get("passed")) and bool(payload.get("ok", True)),
        "proof_level": payload.get("proof_level", "com_runtime"),
        "runtime_mode": payload.get("runtime_mode", "com_runtime"),
        "dcom_surface": payload.get("dcom_surface", "local_com_automation"),
        "remote_dcom_activation_claimed": bool(payload.get("remote_dcom_activation_claimed", False)),
        "sentinel": payload.get("sentinel", sentinel),
        "com_objects": payload.get("com_objects", []),
        "elapsed_seconds": payload.get("elapsed_seconds"),
        "raw": payload,
    }
    _write_json(out_path, summary)
    if not summary["passed"]:
        raise AssertionError(f"Windows COM runtime proof failed; see {out_path}")
    print(f"OK Windows COM runtime proof: {out_path}")
    return 0


def _remote_dcom_server_setup_script(*, username: str, password: str, sentinel: str) -> str:
    return f"""
$ErrorActionPreference = "Stop"
$username = {_ps_quote(username)}
$password = {_ps_quote(password)}
$sentinel = {_ps_quote(sentinel)}
$secure = ConvertTo-SecureString $password -AsPlainText -Force
$user = Get-LocalUser -Name $username -ErrorAction SilentlyContinue
if ($null -eq $user) {{
    New-LocalUser -Name $username -Password $secure -PasswordNeverExpires -AccountNeverExpires | Out-Null
}} else {{
    $user | Set-LocalUser -Password $secure
    Enable-LocalUser -Name $username
}}
$memberName = "$env:COMPUTERNAME\\$username"
$isAdmin = $false
try {{
    $isAdmin = [bool](Get-LocalGroupMember -Group "Administrators" -ErrorAction SilentlyContinue | Where-Object {{ $_.Name -eq $memberName -or $_.Name -like "*\\$username" }})
}} catch {{ $isAdmin = $false }}
if (-not $isAdmin) {{
    Add-LocalGroupMember -Group "Administrators" -Member $username
}}
if (-not (Test-Path "HKLM:\\SOFTWARE\\Microsoft\\Ole")) {{
    New-Item -Path "HKLM:\\SOFTWARE\\Microsoft\\Ole" -Force | Out-Null
}}
New-ItemProperty -Path "HKLM:\\SOFTWARE\\Microsoft\\Ole" -Name "EnableDCOM" -PropertyType String -Value "Y" -Force | Out-Null
New-Item -Path "HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System" -Force | Out-Null
New-ItemProperty -Path "HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System" -Name "LocalAccountTokenFilterPolicy" -PropertyType DWord -Value 1 -Force | Out-Null
New-Item -Path "HKLM:\\SOFTWARE\\MCPFactory\\DCOM" -Force | Out-Null
New-ItemProperty -Path "HKLM:\\SOFTWARE\\MCPFactory\\DCOM" -Name "Sentinel" -PropertyType String -Value $sentinel -Force | Out-Null
$firewallRules = @()
try {{
    Enable-NetFirewallRule -DisplayGroup "COM+ Network Access" -ErrorAction SilentlyContinue | Out-Null
}} catch {{ }}
foreach ($rule in @(
    @{{ Name = "MCPFactory-Remote-DCOM-EndpointMapper"; Port = "135" }},
    @{{ Name = "MCPFactory-Remote-DCOM-DynamicRPC"; Port = "49152-65535" }}
)) {{
    if (-not (Get-NetFirewallRule -DisplayName $rule.Name -ErrorAction SilentlyContinue)) {{
        New-NetFirewallRule -DisplayName $rule.Name -Direction Inbound -Action Allow -Protocol TCP -LocalPort $rule.Port | Out-Null
    }}
    $firewallRules += $rule.Name
}}
$clsid = ""
$appid = ""
try {{ $clsid = (Get-Item "Registry::HKEY_CLASSES_ROOT\\WScript.Shell\\CLSID").GetValue("") }} catch {{ }}
try {{
    if ($clsid) {{ $appid = (Get-Item "Registry::HKEY_CLASSES_ROOT\\CLSID\\$clsid").GetValue("AppID") }}
}} catch {{ }}
$result = [ordered]@{{
    passed = ($clsid -ne "")
    proof_level = "remote_dcom_runtime"
    runtime_mode = "remote_dcom_runtime"
    dcom_surface = "server_configured_for_remote_activation"
    remote_dcom_activation_claimed = $false
    server_computer_name = $env:COMPUTERNAME
    prog_id = "WScript.Shell"
    clsid = $clsid
    appid = $appid
    dcom_enabled = "Y"
    local_account_token_filter_policy = 1
    proof_user = $username
    firewall_rules = $firewallRules
    registry_sentinel_path = "HKLM\\SOFTWARE\\MCPFactory\\DCOM\\Sentinel"
    sentinel_configured = $true
}}
Write-Output ($result | ConvertTo-Json -Depth 12 -Compress)
"""


def _remote_dcom_client_script(*, username: str, password: str, server_target: str, sentinel: str) -> str:
    proof_path = f"C:\\Windows\\Temp\\mcp-factory-remote-dcom-{uuid.uuid4().hex[:8]}.json"
    inner = f"""
$ErrorActionPreference = "Stop"
$serverTarget = {_ps_quote(server_target)}
$sentinel = {_ps_quote(sentinel)}
$proofPath = {_ps_quote(proof_path)}
$result = [ordered]@{{
    passed = $false
    proof_level = "remote_dcom_runtime"
    runtime_mode = "remote_dcom_runtime"
    dcom_surface = "remote_activation_invocation"
    remote_dcom_activation_claimed = $true
    client_computer_name = $env:COMPUTERNAME
    server_target = $serverTarget
    prog_id = "WScript.Shell"
    remote_computer_name = ""
    remote_sentinel = ""
    distinct_remote_context = $false
    error = ""
}}
try {{
    $type = [type]::GetTypeFromProgID("WScript.Shell", $serverTarget, $true)
    $object = [Activator]::CreateInstance($type)
    $remoteComputer = $object.ExpandEnvironmentStrings("%COMPUTERNAME%")
    $remoteSentinel = $object.RegRead("HKLM\\SOFTWARE\\MCPFactory\\DCOM\\Sentinel")
    $result.remote_computer_name = [string]$remoteComputer
    $result.remote_sentinel = [string]$remoteSentinel
    $result.distinct_remote_context = ([string]$remoteComputer -ne "" -and [string]$remoteComputer -ne $env:COMPUTERNAME)
    $result.passed = ($result.distinct_remote_context -and [string]$remoteSentinel -eq $sentinel)
}} catch {{
    $result.error = $_.Exception.Message
}}
$result | ConvertTo-Json -Depth 12 -Compress | Set-Content -Path $proofPath -Encoding UTF8
"""
    encoded = base64.b64encode(inner.encode("utf-16le")).decode("ascii")
    return f"""
$ErrorActionPreference = "Stop"
$username = {_ps_quote(username)}
$password = {_ps_quote(password)}
$proofPath = {_ps_quote(proof_path)}
$scriptPath = $proofPath -replace "\\.json$", ".ps1"
$secure = ConvertTo-SecureString $password -AsPlainText -Force
$user = Get-LocalUser -Name $username -ErrorAction SilentlyContinue
if ($null -eq $user) {{
    New-LocalUser -Name $username -Password $secure -PasswordNeverExpires -AccountNeverExpires | Out-Null
}} else {{
    $user | Set-LocalUser -Password $secure
    Enable-LocalUser -Name $username
}}
try {{
    $memberName = "$env:COMPUTERNAME\\$username"
    $isAdmin = [bool](Get-LocalGroupMember -Group "Administrators" -ErrorAction SilentlyContinue | Where-Object {{ $_.Name -eq $memberName -or $_.Name -like "*\\$username" }})
    if (-not $isAdmin) {{ Add-LocalGroupMember -Group "Administrators" -Member $username }}
}} catch {{ }}
try {{ Start-Service seclogon -ErrorAction SilentlyContinue }} catch {{ }}
$encoded = {_ps_quote(encoded)}
$inner = [Text.Encoding]::Unicode.GetString([Convert]::FromBase64String($encoded))
Set-Content -Path $scriptPath -Value $inner -Encoding UTF8
$powerShellPath = Join-Path $env:SystemRoot "System32\\WindowsPowerShell\\v1.0\\powershell.exe"
$taskName = "MCPFactoryRemoteDcomProof-" + ([Guid]::NewGuid().ToString("N"))
$taskRun = "`"$powerShellPath`" -NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`""
$taskStart = (Get-Date).AddMinutes(1).ToString("HH:mm")
$taskCreateOutput = & schtasks.exe /Create /TN $taskName /TR $taskRun /SC ONCE /ST $taskStart /RU ".\\$username" /RP $password /RL HIGHEST /F 2>&1
$taskCreateExit = $LASTEXITCODE
if ($taskCreateExit -ne 0) {{
    [ordered]@{{
        passed = $false
        runtime_mode = "remote_dcom_runtime"
        proof_level = "remote_dcom_runtime"
        dcom_surface = "remote_activation_invocation"
        remote_dcom_activation_claimed = $true
        client_computer_name = $env:COMPUTERNAME
        task_create_exit_code = $taskCreateExit
        task_create_output = ($taskCreateOutput -join "`n")
        error = "failed to create scheduled task for local DCOM proof user"
    }} | ConvertTo-Json -Depth 12 -Compress
    exit 0
}}
$taskRunOutput = & schtasks.exe /Run /TN $taskName 2>&1
$taskRunExit = $LASTEXITCODE
for ($i = 0; $i -lt 60; $i++) {{
    if (Test-Path $proofPath) {{ break }}
    Start-Sleep -Seconds 2
}}
& schtasks.exe /Delete /TN $taskName /F | Out-Null
if (-not (Test-Path $proofPath)) {{
    [ordered]@{{
        passed = $false
        runtime_mode = "remote_dcom_runtime"
        proof_level = "remote_dcom_runtime"
        dcom_surface = "remote_activation_invocation"
        remote_dcom_activation_claimed = $true
        client_computer_name = $env:COMPUTERNAME
        task_create_exit_code = $taskCreateExit
        task_run_exit_code = $taskRunExit
        task_run_output = ($taskRunOutput -join "`n")
        error = "remote DCOM proof file was not created"
    }} | ConvertTo-Json -Depth 12 -Compress
    exit 0
}}
$proof = Get-Content -Path $proofPath -Raw | ConvertFrom-Json
[ordered]@{{
    passed = ([bool]$proof.passed -and $taskCreateExit -eq 0 -and $taskRunExit -eq 0)
    runtime_mode = "remote_dcom_runtime"
    proof_level = "remote_dcom_runtime"
    dcom_surface = "remote_activation_invocation"
    remote_dcom_activation_claimed = $true
    client_computer_name = $env:COMPUTERNAME
    task_create_exit_code = $taskCreateExit
    task_run_exit_code = $taskRunExit
    proof_path = $proofPath
    proof = $proof
}} | ConvertTo-Json -Depth 20 -Compress
"""


def _remote_dcom_server_cleanup_script(*, username: str) -> str:
    return f"""
$ErrorActionPreference = "Continue"
$username = {_ps_quote(username)}
Remove-Item -Path "HKLM:\\SOFTWARE\\MCPFactory\\DCOM" -Recurse -Force -ErrorAction SilentlyContinue
foreach ($name in @("MCPFactory-Remote-DCOM-EndpointMapper", "MCPFactory-Remote-DCOM-DynamicRPC")) {{
    Get-NetFirewallRule -DisplayName $name -ErrorAction SilentlyContinue | Remove-NetFirewallRule -ErrorAction SilentlyContinue
}}
try {{ Remove-LocalUser -Name $username -ErrorAction SilentlyContinue }} catch {{ }}
$result = [ordered]@{{
    attempted = $true
    removed_user = $username
    removed_firewall_rules = @("MCPFactory-Remote-DCOM-EndpointMapper", "MCPFactory-Remote-DCOM-DynamicRPC")
    removed_registry_path = "HKLM\\SOFTWARE\\MCPFactory\\DCOM"
}}
Write-Output ($result | ConvertTo-Json -Depth 8 -Compress)
"""


def _remote_dcom_invocable(summary: dict) -> dict:
    return {
        "name": "remote_dcom_activation_result",
        "source_type": "remote_dcom_runtime",
        "description": "Return the recorded controlled remote DCOM activation and invocation proof from CI.",
        "parameters": [
            {
                "name": "acknowledgement",
                "type": "string",
                "description": "Short note confirming the remote DCOM proof being requested.",
            }
        ],
        "execution": {
            "method": "observed_result",
            "artifact_path": "ci_artifacts/demo/windows/dcom/dcom.summary.json",
            "summary_path": "ci_artifacts/demo/windows/dcom/dcom.summary.json",
            "source": "remote_dcom_runtime_summary",
            "observed_result": summary,
        },
    }


def cmd_windows_remote_dcom_runtime_proof(args: argparse.Namespace) -> int:
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_dir = Path(args.artifact_dir)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    transcript_path = artifact_dir / "remote-activation-transcript.json"
    sentinel = args.sentinel or f"MCP_FACTORY_REMOTE_DCOM_{uuid.uuid4().hex[:8]}"
    server_target = args.server_target or _get_vm_private_ip(resource_group=args.resource_group, vm_name=args.server_vm_name)
    if args.client_mode == "azure-vm" and not args.client_vm_name:
        raise AssertionError("--client-vm-name is required when --client-mode azure-vm")
    cleanup_payload: dict = {"attempted": False}

    server_setup = _run_vm_powershell_json(
        resource_group=args.resource_group,
        vm_name=args.server_vm_name,
        script=_remote_dcom_server_setup_script(username=args.dcom_username, password=args.dcom_password, sentinel=sentinel),
        timeout=args.timeout,
    )
    client_script = _remote_dcom_client_script(
        username=args.dcom_username,
        password=args.dcom_password,
        server_target=server_target,
        sentinel=sentinel,
    )
    if args.client_mode == "local":
        client_invocation = _run_local_powershell_json(script=client_script, timeout=args.timeout)
    else:
        client_invocation = _run_vm_powershell_json(
            resource_group=args.resource_group,
            vm_name=args.client_vm_name,
            script=client_script,
            timeout=args.timeout,
        )
    if args.cleanup:
        cleanup_payload = _run_vm_powershell_json(
            resource_group=args.resource_group,
            vm_name=args.server_vm_name,
            script=_remote_dcom_server_cleanup_script(username=args.dcom_username),
            timeout=args.timeout,
        )

    proof = client_invocation.get("proof") or {}
    checks = {
        "server_setup_ok": bool(server_setup.get("ok", True) and server_setup.get("passed")),
        "client_invocation_ok": bool(client_invocation.get("ok", True)),
        "remote_activation_claimed": bool(client_invocation.get("remote_dcom_activation_claimed", True)),
        "client_proof_passed": bool(proof.get("passed") or client_invocation.get("passed")),
        "distinct_remote_context": bool(proof.get("distinct_remote_context")),
        "remote_sentinel_matches": proof.get("remote_sentinel") == sentinel,
    }
    runtime_passed = all(checks.values())
    summary = {
        "label": "remote_dcom_runtime",
        "target": "Controlled remote DCOM WScript.Shell activation",
        "passed": runtime_passed,
        "proof_level": "remote_dcom_runtime",
        "runtime_mode": "remote_dcom_runtime",
        "dcom_surface": "remote_dcom_activation_invocation",
        "remote_dcom_activation_claimed": True,
        "sentinel": sentinel,
        "server_vm_name": args.server_vm_name,
        "client_vm_name": args.client_vm_name,
        "client_mode": args.client_mode,
        "server_target": server_target,
        "prog_id": "WScript.Shell",
        "clsid": server_setup.get("clsid", ""),
        "appid": server_setup.get("appid", ""),
        "checks": checks,
        "artifacts": {
            "summary": str(out_path),
            "remote_activation_transcript": str(transcript_path),
        },
        "server_setup": {k: v for k, v in server_setup.items() if k not in {"stdout", "stderr"}},
        "client_invocation": {k: v for k, v in client_invocation.items() if k not in {"stdout", "stderr"}},
        "server_cleanup": {k: v for k, v in cleanup_payload.items() if k not in {"stdout", "stderr"}},
        "notes": "Controlled remote DCOM activation/invocation from a distinct Azure Windows client context; not arbitrary enterprise DCOM estate support.",
    }

    if runtime_passed and args.base_url:
        selected = _remote_dcom_invocable(summary)
        proof_result = _call_generated_tool_with_gpt(
            base_url=args.base_url.rstrip("/"),
            pipeline_key=args.pipeline_key or "",
            job_id=f"dcom-{uuid.uuid4().hex[:8]}",
            component_name=f"remote-dcom-{uuid.uuid4().hex[:8]}",
            selected=selected,
            artifact_dir=artifact_dir,
            prompt=(
                "Call the tool named remote_dcom_activation_result now. "
                "It must return the controlled remote DCOM activation proof from CI."
            ),
            chat_timeout=args.chat_timeout,
        )
        summary["gpt_tool_proof"] = {
            "generated_schema_exists": bool(proof_result["tools"]),
            "downloaded_schema_exists": bool(proof_result["downloaded_schema_exists"]),
            "tool_call_seen": bool(proof_result["tool_call_seen"]),
            "tool_result_seen": bool(proof_result["tool_result_seen"]),
            "transcript_path": str(artifact_dir / "transcript.json"),
        }
        transcript = {
            "case_id": "remote_dcom_runtime",
            "proof_level": "remote_dcom_runtime",
            "selected_tool": selected["name"],
            "source_summary": str(out_path),
            "events": proof_result["events"],
        }
        _write_json(artifact_dir / "transcript.json", transcript)
        runtime_passed = runtime_passed and all(summary["gpt_tool_proof"][key] for key in ("generated_schema_exists", "downloaded_schema_exists", "tool_call_seen", "tool_result_seen"))
        summary["passed"] = runtime_passed

    _write_json(transcript_path, {
        "server_setup": server_setup,
        "client_invocation": client_invocation,
        "server_cleanup": cleanup_payload,
        "checks": checks,
    })
    _write_json(out_path, summary)
    if not summary["passed"]:
        raise AssertionError(f"Remote DCOM runtime proof failed checks: {[name for name, ok in checks.items() if not ok]}; see {out_path}")
    print(f"OK remote DCOM runtime proof: {out_path}")
    return 0


def _select_repo_fixture_invocable(invocables: list[dict]) -> dict:
    for inv in invocables:
        if inv.get("name") == "repo_echo_sentinel":
            return inv
    for inv in invocables:
        if str(inv.get("source_type", "")).lower() in {"python", "python_script", "script"}:
            return inv
    if invocables:
        return invocables[0]
    raise AssertionError("repo fixture discovery produced no invocables")


def cmd_repo_ingestion_gpt_proof(args: argparse.Namespace) -> int:
    base_url = args.base_url.rstrip("/")
    target_dir = Path(args.target_dir)
    out_root = Path(args.artifact_dir)
    out_root.mkdir(parents=True, exist_ok=True)
    sentinel = args.sentinel or f"MCP_FACTORY_REPO_{uuid.uuid4().hex[:8]}"
    item = {
        "id": "sponsor_repo_fixture",
        "proof_level": "repo_live_execution",
        "passed": False,
        "target_dir": str(target_dir),
        "discovery_artifact": "",
        "invocable_count": 0,
        "selected_tool": "",
        "job_id": "",
        "tool_call_seen": False,
        "tool_result_seen": False,
        "sentinel_seen": False,
        "downloaded_schema_exists": False,
        "generated_schema_exists": False,
        "error": "",
        "elapsed_seconds": 0.0,
    }
    started = time.perf_counter()
    try:
        if not target_dir.exists() or not target_dir.is_dir():
            raise AssertionError(f"repo fixture directory missing: {target_dir}")
        discovery_dir = out_root / "discovery"
        if discovery_dir.exists():
            shutil.rmtree(discovery_dir)
        discovery_dir.mkdir(parents=True, exist_ok=True)
        artifact, invocables = _run_discovery_fixture(target_dir, discovery_dir)
        item["discovery_artifact"] = str(artifact)
        item["invocable_count"] = len(invocables)
        if len(invocables) < args.min_invocables:
            raise AssertionError(f"repo fixture expected at least {args.min_invocables} invocables, found {len(invocables)}")
        selected = _select_repo_fixture_invocable(invocables)
        if not selected.get("parameters"):
            selected = {
                **selected,
                "parameters": [{"name": "sentinel", "type": "string", "description": "Deterministic repo proof sentinel"}],
            }
        item["selected_tool"] = str(selected.get("name") or "")
        job_id = f"repo-{uuid.uuid4().hex[:8]}"
        item["job_id"] = job_id
        tool_name = _safe_tool_name(item["selected_tool"])
        proof = _call_generated_tool_with_gpt(
            base_url=base_url,
            pipeline_key=args.pipeline_key or "",
            job_id=job_id,
            component_name=f"repo-fixture-{job_id}",
            selected=selected,
            artifact_dir=out_root,
            prompt=(
                f"Call the tool named {tool_name} now. "
                f"Use this exact sentinel string for every required string argument: {sentinel}. "
                f"The successful tool output must contain this sentinel: {sentinel}. "
                "Do not just say done."
            ),
            chat_timeout=args.chat_timeout,
        )
        tool_results = proof["tool_results"]
        result_text = "\n".join(str(evt.get("result", "")) for evt in tool_results)
        item["tool_call_seen"] = bool(proof["tool_call_seen"])
        item["tool_result_seen"] = bool(proof["tool_result_seen"])
        item["sentinel_seen"] = sentinel in result_text
        item["downloaded_schema_exists"] = bool(proof["downloaded_schema_exists"])
        item["generated_schema_exists"] = bool(proof["tools"])
        _write_json(out_root / "transcript.json", {
            "case_id": item["id"],
            "job_id": job_id,
            "sentinel": sentinel,
            "proof_level": item["proof_level"],
            "selected_tool": item["selected_tool"],
            "events": proof["events"],
        })
        if not item["tool_call_seen"]:
            raise AssertionError("GPT did not emit a tool_call")
        if not item["tool_result_seen"]:
            raise AssertionError("tool_result event missing")
        if not item["sentinel_seen"]:
            raise AssertionError("sentinel not found in repo fixture tool_result")
        if not item["downloaded_schema_exists"]:
            raise AssertionError("downloaded MCP schema artifact missing")
        item["passed"] = True
    except Exception as exc:
        item["error"] = str(exc)
        (out_root / "error.txt").write_text(str(exc), encoding="utf-8")
    finally:
        item["elapsed_seconds"] = round(time.perf_counter() - started, 3)
        _write_json(out_root / "summary.json", item)
    print(
        f"{'OK' if item['passed'] else 'FAIL'} repo ingestion GPT proof: "
        f"invocables={item['invocable_count']} tool_call={item['tool_call_seen']} "
        f"tool_result={item['tool_result_seen']} sentinel={item['sentinel_seen']}"
    )
    if not item["passed"]:
        raise AssertionError(f"repo ingestion GPT proof failed: {item['error']}")
    return 0


def _run_bridge_case(
    *,
    bridge_url: str,
    bridge_secret: str,
    target: str,
    out_dir: Path,
    label: str = "",
    kind: str = "system_path",
    hints: str = "github actions bridge e2e",
    types: list[str] | None = None,
    min_invocables: int = 1,
    required: bool = True,
    timeout: int = 180,
    health_timeout: int = 45,
    post_grace: float = 3.0,
    bridge_resource_group: str = "",
    bridge_vm_name: str = "",
    bridge_task_name: str = "MCP-Factory-Bridge-Interactive",
    bridge_restart_timeout: int = 90,
    bridge_required_session_id: int | None = 1,
    bridge_session_cache: Path | None = None,
    expect_source_type: str = "",
    expect_name_contains: str = "",
) -> dict:
    safe_name = _safe_target_name(label or target)
    target_dir = out_dir / safe_name
    target_dir.mkdir(parents=True, exist_ok=True)
    raw_path = target_dir / f"{safe_name}.raw.jsonl"
    summary_path = target_dir / f"{safe_name}.summary.json"
    error_path = target_dir / f"{safe_name}.error.txt"
    requested_types = types or ["gui", "com", "cli", "registry", "dotnet", "rpc", "directory", "ghidra"]
    bridge_session_cache = bridge_session_cache or (out_dir / ".bridge-session-cache.json")

    case_started = time.perf_counter()
    print(f"START bridge target label={safe_name} kind={kind} target={target}")
    health_before = _ensure_bridge_health(
        bridge_url,
        bridge_secret,
        timeout=health_timeout,
        restart_resource_group=bridge_resource_group,
        restart_vm_name=bridge_vm_name,
        restart_task_name=bridge_task_name,
        restart_timeout=bridge_restart_timeout,
        required_session_id=bridge_required_session_id,
        session_cache_path=bridge_session_cache,
    )
    attempts = []
    started = time.perf_counter()
    if health_before.get("ok"):
        result = _bridge_analyze_once(
            bridge_url,
            bridge_secret,
            target,
            hints=hints,
            types=requested_types,
            timeout=timeout,
            raw_path=raw_path,
        )
    else:
        error_text = (
            f"bridge health not ready after {health_timeout}s: "
            f"{health_before.get('error') or health_before.get('body') or health_before}"
        )
        raw_path.write_text(error_text, encoding="utf-8")
        result = {
            "ok": False,
            "http_status": None,
            "payload": {},
            "error": error_text,
            "elapsed_seconds": 0,
            "raw_response_path": str(raw_path),
        }
    attempts.append(result)

    initial_payload = result.get("payload") or {}
    initial_invocables = _filter_invocables(
        _extract_invocables(initial_payload),
        expect_source_type=expect_source_type,
        expect_name_contains=expect_name_contains,
    )
    if not result["ok"] or len(initial_invocables) < min_invocables:
        retry_health = _ensure_bridge_health(
            bridge_url,
            bridge_secret,
            timeout=health_timeout,
            restart_resource_group=bridge_resource_group,
            restart_vm_name=bridge_vm_name,
            restart_task_name=bridge_task_name,
            restart_timeout=bridge_restart_timeout,
            required_session_id=bridge_required_session_id,
            session_cache_path=bridge_session_cache,
        )
        retry_raw_path = target_dir / f"{safe_name}.retry.raw.jsonl"
        if retry_health.get("ok"):
            retry_result = _bridge_analyze_once(
                bridge_url,
                bridge_secret,
                target,
                hints=hints,
                types=requested_types,
                timeout=timeout,
                raw_path=retry_raw_path,
            )
        else:
            error_text = (
                f"bridge health not ready before retry after {health_timeout}s: "
                f"{retry_health.get('error') or retry_health.get('body') or retry_health}"
            )
            retry_raw_path.write_text(error_text, encoding="utf-8")
            retry_result = {
                "ok": False,
                "http_status": None,
                "payload": {},
                "error": error_text,
                "elapsed_seconds": 0,
                "raw_response_path": str(retry_raw_path),
            }
        retry_result["health_before_retry"] = retry_health
        attempts.append(retry_result)
        result = retry_result

    payload = result.get("payload") or {}
    all_invocables = _extract_invocables(payload)
    matched_invocables = _filter_invocables(
        all_invocables,
        expect_source_type=expect_source_type,
        expect_name_contains=expect_name_contains,
    )
    bridge_errors = payload.get("errors") if isinstance(payload, dict) else None
    passed = bool(result.get("ok") and len(matched_invocables) >= min_invocables)
    health_after = _bridge_health(bridge_url, bridge_secret)
    first_names = [str(inv.get("name", "")) for inv in matched_invocables[:20]]
    post_grace_health = None
    if post_grace > 0:
        print(f"GRACE bridge target {safe_name}: sleeping {post_grace:g}s before health verification")
        time.sleep(post_grace)
        post_grace_health = _ensure_bridge_health(
            bridge_url,
            bridge_secret,
            timeout=health_timeout,
            restart_resource_group=bridge_resource_group,
            restart_vm_name=bridge_vm_name,
            restart_task_name=bridge_task_name,
            restart_timeout=bridge_restart_timeout,
            required_session_id=bridge_required_session_id,
            session_cache_path=bridge_session_cache,
        )
        if not post_grace_health.get("ok"):
            passed = False
    error_text = ""
    if not passed:
        error_text = str(
            result.get("error")
            or bridge_errors
            or (
                "bridge not healthy after post-grace: "
                f"{post_grace_health.get('error') or post_grace_health}"
                if post_grace_health and not post_grace_health.get("ok")
                else ""
            )
            or f"matched_invocables={len(matched_invocables)} min_invocables={min_invocables}"
        )
        error_path.write_text(error_text, encoding="utf-8")

    item = {
        "label": safe_name,
        "target": target,
        "kind": kind,
        "category": _target_category(target),
        "required": required,
        "passed": passed,
        "invocable_count": len(all_invocables),
        "matched_invocable_count": len(matched_invocables),
        "min_invocables": min_invocables,
        "expect_source_type": expect_source_type,
        "expect_name_contains": expect_name_contains,
        "first_20_invocable_names": first_names,
        "bridge_http_status": result.get("http_status"),
        "exception": error_text,
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "total_elapsed_seconds": round(time.perf_counter() - case_started, 3),
        "bridge_elapsed_seconds": result.get("elapsed_seconds"),
        "retry_count": max(0, len(attempts) - 1),
        "health_wait_timeout_seconds": health_timeout,
        "configured_post_grace_seconds": post_grace,
        "post_grace_seconds": post_grace,
        "bridge_restart_resource_group": bridge_resource_group,
        "bridge_restart_vm_name": bridge_vm_name,
        "bridge_restart_task_name": bridge_task_name,
        "bridge_required_session_id": bridge_required_session_id,
        "bridge_session_cache_path": str(bridge_session_cache),
        "raw_response_path": result.get("raw_response_path") or str(raw_path),
        "summary_path": str(summary_path),
        "bridge_errors": bridge_errors,
        "health_before": health_before,
        "health_after": health_after,
        "post_grace_health": post_grace_health,
        "attempts": [
            {
                "ok": attempt.get("ok"),
                "http_status": attempt.get("http_status"),
                "elapsed_seconds": attempt.get("elapsed_seconds"),
                "error": attempt.get("error", ""),
                "raw_response_path": attempt.get("raw_response_path"),
                "health_before_retry": attempt.get("health_before_retry"),
            }
            for attempt in attempts
        ],
    }
    _add_bridge_timing_diagnostics(item)
    _write_json(summary_path, item)
    status = "OK" if passed else ("OPTIONAL-FAIL" if not required else "FAIL")
    print(
        f"{status} bridge target {safe_name}: "
        f"matched={len(matched_invocables)} total={len(all_invocables)} "
        f"retry_count={item['retry_count']} elapsed={item['elapsed_seconds']}s"
    )
    return item


def cmd_bridge_target_e2e(args: argparse.Namespace) -> int:
    out_dir = Path(args.out_dir)
    item = _run_bridge_case(
        bridge_url=args.bridge_url.rstrip("/"),
        bridge_secret=args.bridge_secret,
        target=args.target,
        out_dir=out_dir,
        label=args.label,
        kind=args.kind,
        hints=args.hints,
        types=args.types,
        min_invocables=args.min_invocables,
        required=_case_bool(args.required),
        timeout=args.timeout,
        health_timeout=args.health_timeout,
        post_grace=args.post_grace,
        bridge_resource_group=args.bridge_resource_group,
        bridge_vm_name=args.bridge_vm_name,
        bridge_task_name=args.bridge_task_name,
        bridge_restart_timeout=args.bridge_restart_timeout,
        bridge_required_session_id=args.bridge_required_session_id if args.bridge_required_session_id >= 0 else None,
        bridge_session_cache=Path(args.bridge_session_cache) if args.bridge_session_cache else out_dir / ".bridge-session-cache.json",
        expect_source_type=args.expect_source_type,
        expect_name_contains=args.expect_name_contains,
    )
    if item["required"] and not item["passed"]:
        raise AssertionError(f"required bridge target failed: {item['label']}; see {item['summary_path']}")
    return 0


def cmd_direct_bridge_e2e(args: argparse.Namespace) -> int:
    bridge_url = args.bridge_url.rstrip("/")
    required_targets = args.targets or [
        r"C:\Windows\System32\kernel32.dll",
        r"C:\Windows\System32\cmd.exe",
        r"C:\Windows\System32\notepad.exe",
        r"C:\Windows\System32\shell32.dll",
    ]
    optional_targets = args.optional_targets or []
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    bridge_session_cache = Path(args.bridge_session_cache) if args.bridge_session_cache else out_dir / ".bridge-session-cache.json"

    summary = [
        _run_bridge_case(
            bridge_url=bridge_url,
            bridge_secret=args.bridge_secret,
            target=target,
            out_dir=out_dir,
            required=required,
            timeout=args.timeout,
            health_timeout=args.health_timeout,
            post_grace=args.post_grace,
            bridge_resource_group=args.bridge_resource_group,
            bridge_vm_name=args.bridge_vm_name,
            bridge_task_name=args.bridge_task_name,
            bridge_restart_timeout=args.bridge_restart_timeout,
            bridge_required_session_id=args.bridge_required_session_id if args.bridge_required_session_id >= 0 else None,
            bridge_session_cache=bridge_session_cache,
        )
        for target, required in [(t, True) for t in required_targets] + [(t, False) for t in optional_targets]
    ]
    failures = sum(1 for item in summary if item.get("required") and not item.get("passed"))
    summary_file = out_dir / "summary.json"
    _write_json(summary_file, {"targets": summary, "failures": failures})
    legacy_out = Path(args.out) if args.out else None
    if legacy_out:
        _write_json(legacy_out, {"targets": summary, "failures": failures})
    if failures:
        raise AssertionError(f"{failures} required bridge target(s) failed; see {summary_file}")
    print(f"OK direct bridge E2E: {len(summary)} target(s), artifacts={out_dir}")
    return 0


def cmd_summarize_bridge_e2e(args: argparse.Namespace) -> int:
    out_dir = Path(args.out_dir)
    summaries = []
    for path in sorted(out_dir.glob("*/*.summary.json")):
        summaries.append(_load_json(path))
    if not summaries:
        raise AssertionError(f"no bridge target summaries found under {out_dir}")
    counts = _count_required_optional(summaries)
    failures = [item for item in summaries if item.get("required", True) and not item.get("passed")]
    aggregate = {
        "targets": summaries,
        "total": len(summaries),
        "failures": len(failures),
        "failed_labels": [item.get("label") for item in failures],
        "required_total": counts["required_total"],
        "required_passed": counts["required_passed"],
        "required_failures": counts["required_failed"],
        "required_failed_labels": counts["required_failed_ids"],
        "optional_total": counts["optional_total"],
        "optional_passed": counts["optional_passed"],
        "optional_failures": counts["optional_failed"],
        "optional_failed_labels": counts["optional_failed_ids"],
    }
    _write_json(out_dir / "summary.json", aggregate)
    for item in summaries:
        status = "OK" if item.get("passed") else ("OPTIONAL-FAIL" if not item.get("required", True) else "FAIL")
        print(
            f"{status} {item.get('label')}: "
            f"matched={item.get('matched_invocable_count')} total={item.get('invocable_count')} "
            f"elapsed={item.get('elapsed_seconds')}s"
        )
    if failures:
        raise AssertionError(f"{len(failures)} required bridge target(s) failed: {aggregate['failed_labels']}")
    print(f"OK bridge summary: {len(summaries)} target(s)")
    return 0


def cmd_touch_bridge_lease(args: argparse.Namespace) -> int:
    _touch_bridge_lease(
        storage_account=args.storage_account,
        container=args.container,
        reason=args.reason,
        job_id=args.job_id,
    )
    return 0


def cmd_run_sponsor_contract(args: argparse.Namespace) -> int:
    manifest_path = Path(args.manifest)
    manifest = _load_json(manifest_path)
    out_root = Path(args.out)
    out_root.mkdir(parents=True, exist_ok=True)
    summary = []
    failures = 0
    for case in manifest.get("non_vm_cases", []):
        proof_level = case.get("proof_level")
        if proof_level and proof_level not in {"real_execution", "provider_required"}:
            raise AssertionError(f"{case.get('id', '<unknown>')}: invalid proof_level={proof_level!r}")
        runtime_mode = _runtime_mode_for_case(case)
        if runtime_mode not in {
            "local_runtime",
            "real_runtime",
            "validated_runtime",
            "lookup_runtime",
            "ldap_runtime",
            "xmlrpc_runtime",
            "msrpc_runtime",
            "corba_idl_runtime",
            "corba_orb_runtime",
            "adapter_backed",
            "unknown",
        }:
            raise AssertionError(f"{case.get('id', '<unknown>')}: invalid runtime_mode={runtime_mode!r}")
        if case.get("id") == "corba_idl" and runtime_mode == "adapter_backed":
            raise AssertionError("corba_idl: stale runtime_mode='adapter_backed'; expected corba_orb_runtime or corba_idl_runtime")
        expected_result = case.get("expected_result")
        if expected_result and expected_result not in {"sentinel", "provider_required"}:
            raise AssertionError(f"{case.get('id', '<unknown>')}: invalid expected_result={expected_result!r}")
        case_id = case["id"]
        target = ROOT / case["path"]
        case_out = out_root / case_id
        if case_out.exists():
            shutil.rmtree(case_out)
        case_out.mkdir(parents=True, exist_ok=True)
        try:
            artifact, invocables = _run_discovery_fixture(target, case_out)
            matched = _filter_invocables(
                invocables,
                expect_source_type=case.get("expect_source_type", ""),
                expect_name_contains=case.get("expect_name_contains", ""),
            )
            min_invocables = int(case.get("min_invocables", 1))
            passed = len(matched) >= min_invocables
            error_text = "" if passed else f"matched_invocables={len(matched)} min_invocables={min_invocables}"
            item = {
                **case,
                "runtime_mode": runtime_mode,
                "artifact": str(artifact),
                "passed": passed,
                "invocable_count": len(invocables),
                "matched_invocable_count": len(matched),
                "first_20_invocable_names": [str(inv.get("name", "")) for inv in matched[:20]],
                "error": error_text,
            }
        except Exception as exc:
            passed = False
            item = {**case, "passed": False, "error": str(exc)}
        summary.append(item)
        if not passed:
            failures += 1
        print(
            f"{'OK' if passed else 'FAIL'} sponsor fixture {case_id}: "
            f"matched={item.get('matched_invocable_count', 0)} total={item.get('invocable_count', 0)}"
        )
    _write_json(out_root / "summary.json", {"cases": summary, "failures": failures})
    if failures:
        raise AssertionError(f"{failures} sponsor fixture case(s) failed; see {out_root / 'summary.json'}")
    print(f"OK sponsor fixture contract: {len(summary)} case(s)")
    return 0


def _count_pass_fail(items: list[dict]) -> dict:
    failures = [item for item in items if not item.get("passed")]
    return {
        "total": len(items),
        "passed": len(items) - len(failures),
        "failed": len(failures),
        "failed_ids": [str(item.get("id") or item.get("label") or item.get("target") or "-") for item in failures],
    }


def _count_required_optional(items: list[dict]) -> dict:
    required = [item for item in items if item.get("required", True)]
    optional = [item for item in items if not item.get("required", True)]
    required_failures = [item for item in required if not item.get("passed")]
    optional_failures = [item for item in optional if not item.get("passed")]
    all_failures = required_failures + optional_failures
    return {
        "total": len(items),
        "passed": len(items) - len(all_failures),
        "failed": len(all_failures),
        "failed_ids": [str(item.get("label") or item.get("id") or item.get("target") or "-") for item in all_failures],
        "required_total": len(required),
        "required_passed": len(required) - len(required_failures),
        "required_failed": len(required_failures),
        "required_failed_ids": [str(item.get("label") or item.get("id") or item.get("target") or "-") for item in required_failures],
        "optional_total": len(optional),
        "optional_passed": len(optional) - len(optional_failures),
        "optional_failed": len(optional_failures),
        "optional_failed_ids": [str(item.get("label") or item.get("id") or item.get("target") or "-") for item in optional_failures],
    }


def _diagnostic_label(item: dict) -> str:
    return str(item.get("label") or item.get("id") or item.get("target") or "-")


def _windows_diagnostics(targets: list[dict]) -> dict:
    slow_threshold = 30.0
    slow_targets = []
    bridge_recovery_events = []
    session_cache_proof = []
    required_failures = []
    optional_failures = []
    for item in targets:
        label = _diagnostic_label(item)
        elapsed = _seconds(item.get("total_elapsed_seconds") or item.get("elapsed_seconds"))
        diagnostic = {
            "label": label,
            "required": item.get("required", True),
            "passed": item.get("passed"),
            "elapsed_seconds": round(elapsed, 3),
            "bridge_analyzer_seconds": _seconds(item.get("bridge_analyzer_seconds") or item.get("bridge_elapsed_seconds")),
            "health_wait_seconds": _seconds(item.get("health_wait_seconds")),
            "session_check_seconds": _seconds(item.get("session_check_seconds")),
            "retry_seconds": _seconds(item.get("retry_seconds")),
            "restart_seconds": _seconds(item.get("restart_seconds")),
            "vm_restart_seconds": _seconds(item.get("vm_restart_seconds")),
            "post_grace_seconds": _seconds(item.get("post_grace_seconds")),
            "dominant_time_source": item.get("dominant_time_source") or "unknown",
            "classification": item.get("timeout_or_failure_classification") or ("passed" if item.get("passed") else "failed"),
        }
        if elapsed >= slow_threshold:
            slow_targets.append(diagnostic)
        if not item.get("passed") and item.get("required", True):
            required_failures.append(diagnostic)
        if not item.get("passed") and not item.get("required", True):
            optional_failures.append(diagnostic)

        records = _bridge_health_records(item)
        recovery_records = [
            record for record in records
            if record.get("restart_attempted")
            or isinstance(record.get("restart_result"), dict)
            or isinstance(record.get("vm_restart_result"), dict)
        ]
        if recovery_records:
            bridge_recovery_events.append(
                {
                    "label": label,
                    "classification": diagnostic["classification"],
                    "restart_seconds": diagnostic["restart_seconds"],
                    "vm_restart_seconds": diagnostic["vm_restart_seconds"],
                    "health_wait_seconds": diagnostic["health_wait_seconds"],
                }
            )

        session_cache_proof.append(
            {
                "label": label,
                "session_cache_used": bool(item.get("session_cache_used")),
                "session_check_seconds": diagnostic["session_check_seconds"],
                "health_before_session_id": (
                    (item.get("health_before") or {}).get("bridge_process") or {}
                ).get("session_id") if isinstance(item.get("health_before"), dict) else None,
                "post_grace_session_id": (
                    (item.get("post_grace_health") or {}).get("bridge_process") or {}
                ).get("session_id") if isinstance(item.get("post_grace_health"), dict) else None,
            }
        )

    return {
        "slow_threshold_seconds": slow_threshold,
        "slow_targets": slow_targets,
        "required_failures": required_failures,
        "optional_failures": optional_failures,
        "bridge_recovery_events": bridge_recovery_events,
        "session_cache_proof": session_cache_proof,
    }


def _append_diagnostic_table(lines: list[str], title: str, rows: list[dict], empty: str) -> None:
    lines.extend(["", f"## {title}", ""])
    if not rows:
        lines.append(empty)
        return
    lines.append("| Target | Required | Status | Elapsed | Dominant | Classification | Analyzer | Health | Session | Retry | Restart | VM Restart |")
    lines.append("|---|---:|---|---:|---|---|---:|---:|---:|---:|---:|---:|")
    for item in rows:
        status = "PASS" if item.get("passed") else "FAIL"
        lines.append(
            "| "
            + " | ".join(
                [
                    str(item.get("label")),
                    str(bool(item.get("required"))),
                    status,
                    f"{_seconds(item.get('elapsed_seconds')):.3f}s",
                    str(item.get("dominant_time_source") or "unknown"),
                    str(item.get("classification") or ""),
                    f"{_seconds(item.get('bridge_analyzer_seconds')):.3f}s",
                    f"{_seconds(item.get('health_wait_seconds')):.3f}s",
                    f"{_seconds(item.get('session_check_seconds')):.3f}s",
                    f"{_seconds(item.get('retry_seconds')):.3f}s",
                    f"{_seconds(item.get('restart_seconds')):.3f}s",
                    f"{_seconds(item.get('vm_restart_seconds')):.3f}s",
                ]
            )
            + " |"
        )


def _matrix_status(condition: bool) -> str:
    return "pass" if condition else "fail"


def _build_requirement_matrix(
    *,
    checks: dict,
    non_vm_counts: dict,
    windows_counts: dict,
    gpt_matrix: dict,
    windows_gpt: dict,
    repo_ingestion: dict,
    schema_tool_count: int,
    job_id: str,
) -> list[dict]:
    real_passed = int(gpt_matrix.get("real_execution_passed", 0))
    real_total = int(gpt_matrix.get("real_execution_total", 0))
    provider_passed = int(gpt_matrix.get("provider_required_tool_call_passed", 0))
    provider_total = int(gpt_matrix.get("provider_required_total", 0))
    gpt_ok = int(gpt_matrix.get("failures", 1)) == 0 and int(gpt_matrix.get("total", 0)) > 0
    all_live_ok = gpt_ok and provider_total == 0 and real_total >= 13 and real_passed == real_total
    windows_ok = windows_counts.get("required_failed") == 0 and windows_counts.get("required_total", 0) > 0
    non_vm_ok = non_vm_counts.get("failed") == 0 and non_vm_counts.get("total", 0) > 0
    gpt_tool_ok = bool(checks.get("gpt_tool_call_seen") and checks.get("gpt_sentinel_seen") and schema_tool_count > 0)
    windows_gpt_ok = int(windows_gpt.get("failures", 1)) == 0 and int(windows_gpt.get("total", 0)) > 0
    com_runtime_ok = bool(checks.get("windows_com_runtime_proof_passed"))
    repo_ok = bool(repo_ingestion.get("passed"))
    return [
        {
            "requirement": "1.a",
            "summary": "Windows 11 / Win32 compiled DLL and EXE targets are accepted and profiled.",
            "implementation_surface": "Windows bridge discovery scans system DLL/EXE/TLB targets.",
            "proof_type": "discovery",
            "status": _matrix_status(windows_ok),
            "artifact_paths": [
                "ci_artifacts/demo/windows/kernel32_dll/kernel32_dll.summary.json",
                "ci_artifacts/demo/windows/notepad_exe/notepad_exe.summary.json",
                "ci_artifacts/demo/windows/stdole2_tlb/stdole2_tlb.summary.json",
                "ci_artifacts/demo/windows-gpt/summary.json",
            ],
            "notes": "Bridge discovery is required; Windows GPT proof observes selected discovery artifacts without claiming arbitrary binary semantic recovery.",
        },
        {
            "requirement": "1.b",
            "summary": "RPC, JNDI, COM/DCOM, SOAP, CORBA, JSON/JSON-RPC technologies are considered.",
            "implementation_surface": "Format providers discover schemas and generate GPT-callable tools backed by hosted runtime providers; COM/TLB is scanned on Windows.",
            "proof_type": "live_execution",
            "status": _matrix_status(all_live_ok and windows_ok and com_runtime_ok),
            "artifact_paths": [
                "ci_artifacts/demo/gpt-format-matrix/openapi/summary.json",
                "ci_artifacts/demo/gpt-format-matrix/jsonrpc/summary.json",
                "ci_artifacts/demo/gpt-format-matrix/soap_wsdl/summary.json",
                "ci_artifacts/demo/gpt-format-matrix/corba_idl/summary.json",
                "ci_artifacts/demo/gpt-format-matrix/rpc_idl_contract/summary.json",
                "ci_artifacts/demo/gpt-format-matrix/jndi/summary.json",
                "ci_artifacts/demo/windows/stdole2_tlb/stdole2_tlb.summary.json",
                "ci_artifacts/demo/windows/com_runtime/com_runtime.summary.json",
                "docs/sponsor/caveats.md",
            ],
            "notes": "JSON-RPC, SOAP, SQL, controlled LDAP/JNDI bind/search/lookup, controlled CORBA ORB/IIOP, and controlled DCE/RPC-compatible RPC IDL are runtime-backed when their focused artifacts are present. REST is route-validated. COM/TLB discovery and local COM automation are proven; remote DCOM activation is not claimed.",
        },
        {
            "requirement": "1.c",
            "summary": "Windows Registry entries are inspected for hints and invocable inventory.",
            "implementation_surface": "Registry fixture is seeded and scanned through the Windows bridge.",
            "proof_type": "discovery",
            "status": _matrix_status(windows_ok),
            "artifact_paths": ["ci_artifacts/demo/windows/registry_contoso/registry_contoso.summary.json"],
            "notes": "The CI target expects a Contoso registry invocable from HKLM inventory; Windows GPT proof adds a generated tool-call observation when present.",
        },
        {
            "requirement": "1.d",
            "summary": "SQL source files are considered candidate executables.",
            "implementation_surface": "SQL fixture discovery and hosted SQL-provider GPT tool proof.",
            "proof_type": "live_execution",
            "status": _matrix_status(gpt_ok and real_passed == real_total and provider_total == 0),
            "artifact_paths": [
                "ci_artifacts/demo/non-vm/sql/contoso_db_sql_file_mcp.json",
                "ci_artifacts/demo/gpt-format-matrix/sql/summary.json",
            ],
            "notes": "SQL is represented as a generated tool backed by an in-memory SQLite runtime with deterministic Contoso data in CI.",
        },
        {
            "requirement": "1.e",
            "summary": "JavaScript, Python, Ruby, PHP, PowerShell, CMD/BAT and other JIT/script executables are valid scope.",
            "implementation_surface": "GPT matrix runs real execution sentinel proofs for script formats plus hosted legacy adapters.",
            "proof_type": "live_execution",
            "status": _matrix_status(real_total >= 6 and real_passed == real_total),
            "artifact_paths": [
                "ci_artifacts/demo/gpt-format-matrix/python/summary.json",
                "ci_artifacts/demo/gpt-format-matrix/javascript/summary.json",
                "ci_artifacts/demo/gpt-format-matrix/ruby/summary.json",
                "ci_artifacts/demo/gpt-format-matrix/php/summary.json",
                "ci_artifacts/demo/gpt-format-matrix/powershell/summary.json",
                "ci_artifacts/demo/gpt-format-matrix/cmd/summary.json",
            ],
            "notes": "The CMD/BAT proof is the deterministic .cmd fixture, not broad cmd.exe introspection.",
        },
        {
            "requirement": "2.a",
            "summary": "Users can provide a file copy or an installed instance/path.",
            "implementation_surface": "Cloud upload covers file copies; Windows bridge scans installed paths/directories.",
            "proof_type": "discovery",
            "status": _matrix_status(non_vm_ok and windows_ok),
            "artifact_paths": [
                "ci_artifacts/demo/non-vm/summary.json",
                "ci_artifacts/demo/windows/system32_directory/system32_directory.summary.json",
                "ci_artifacts/demo/repo-ingestion/summary.json",
            ],
            "notes": "Installed paths must be accessible to the server or VM context that performs discovery. Repo fixture proof covers the sponsor phrase 'existing dll, exe, cmd or a repo' when present.",
        },
        {
            "requirement": "project.repo",
            "summary": "An existing repo/folder can be profiled into invocables and a generated MCP tool.",
            "implementation_surface": "Directory discovery scans a deterministic repository fixture, selects a repo-derived Python callable, generates schema, and GPT calls it.",
            "proof_type": "live_execution",
            "status": _matrix_status(repo_ok),
            "artifact_paths": [
                "tests/fixtures/sponsor_repo_fixture/",
                "ci_artifacts/demo/repo-ingestion/summary.json",
                "ci_artifacts/demo/repo-ingestion/transcript.json",
            ],
            "notes": "This proof is incremental hardening; the baseline file/path proofs remain required for the canonical sponsor gate.",
        },
        {
            "requirement": "2.b",
            "summary": "Users can describe the file with free-text hints.",
            "implementation_surface": "API and CI pass hints into discovery jobs and bridge scans.",
            "proof_type": "process_artifact",
            "status": _matrix_status(non_vm_ok and gpt_ok),
            "artifact_paths": [
                "ci_artifacts/demo/gpt-format-matrix/summary.json",
                "ci_artifacts/demo/windows/summary.json",
            ],
            "notes": "CI uses deterministic hints for sponsor cases; UI exposes a hints field for user-provided descriptions.",
        },
        {
            "requirement": "3.a",
            "summary": "System displays invocable features after target analysis.",
            "implementation_surface": "Discovery summaries include invocable counts; UI job polling displays returned invocables.",
            "proof_type": "discovery",
            "status": _matrix_status(non_vm_ok and windows_ok),
            "artifact_paths": [
                "ci_artifacts/demo/non-vm/summary.json",
                "ci_artifacts/demo/windows/summary.json",
            ],
            "notes": "Per-target summaries include total and matched invocable counts.",
        },
        {
            "requirement": "3.b",
            "summary": "Users may deselect invocable features before generation.",
            "implementation_surface": "GPT proofs write selected invocable artifacts and generation uses that selected subset.",
            "proof_type": "process_artifact",
            "status": _matrix_status(gpt_tool_ok),
            "artifact_paths": [
                "ci_artifacts/demo/gpt4o/selected-invocable.json",
                "ci_artifacts/demo/gpt-format-matrix/cmd/selected-invocable.json",
            ],
            "notes": "The UI exposes checkboxes; CI proves the selected invocable is the one used for schema generation.",
        },
        {
            "requirement": "4.a",
            "summary": "Users specify a generated component name with a suggested default.",
            "implementation_surface": "`/api/generate` accepts `component_name`; UI pre-populates it from job metadata.",
            "proof_type": "process_artifact",
            "status": _matrix_status(bool(checks.get("generated_schema_exists"))),
            "artifact_paths": ["ci_artifacts/demo/gpt4o/generated-mcp-schema.json"],
            "notes": "CI uses a deterministic component name for the generated schema.",
        },
        {
            "requirement": "4.b",
            "summary": "System generates MCP architecture and deploys/verifies an instance.",
            "implementation_surface": "Generated MCP schema/server contract is used by GPT tool-call verification.",
            "proof_type": "live_execution",
            "status": _matrix_status(gpt_tool_ok),
            "artifact_paths": [
                "ci_artifacts/demo/gpt4o/generated-mcp-schema.json",
                "ci_artifacts/demo/gpt4o/transcript.json",
            ],
            "notes": f"Generated schema tool count: {schema_tool_count}. GPT job id: {job_id or '-'}",
        },
        {
            "requirement": "5.a",
            "summary": "Users are presented with a chat interface to interact with the generated output.",
            "implementation_surface": "Cloud chat endpoint accepts generated tools and invocables; UI streams chat events.",
            "proof_type": "live_execution",
            "status": _matrix_status(bool(checks.get("gpt_tool_call_seen"))),
            "artifact_paths": ["ci_artifacts/demo/gpt4o/transcript.json"],
            "notes": "CI verifies the LLM emits a tool call against the generated MCP schema.",
        },
        {
            "requirement": "5.b",
            "summary": "Executable output is relayed to the conversation presentation area.",
            "implementation_surface": "Chat transcript records tool result event containing the sentinel output.",
            "proof_type": "live_execution",
            "status": _matrix_status(bool(checks.get("gpt_sentinel_seen"))),
            "artifact_paths": ["ci_artifacts/demo/gpt4o/transcript.json"],
            "notes": "Sentinel in tool result proves output was returned through the chat event stream.",
        },
        {
            "requirement": "5.c",
            "summary": "Users can download a copy of generated output.",
            "implementation_surface": "Backend serves job artifacts through `/api/download/{job_id}/{filename}`.",
            "proof_type": "live_execution",
            "status": _matrix_status(bool(checks.get("downloaded_schema_exists"))),
            "artifact_paths": ["ci_artifacts/demo/gpt4o/downloaded-mcp-schema.json"],
            "notes": "GitHub Actions artifacts are separate from app blob downloads.",
        },
        {
            "requirement": "6",
            "summary": "Microsoft technologies, budget, access restriction, and compliance guidance are incorporated.",
            "implementation_surface": "Azure Container Apps, Storage, Key Vault, Azure OpenAI, GitHub Actions, VS Code, Aspire, Codespaces, and FERPA docs.",
            "proof_type": "infrastructure",
            "status": _matrix_status(bool(checks.get("vm_deallocation_completed"))),
            "artifact_paths": [
                "README.md",
                "docs/sponsor/non-code-artifacts.md",
                "docs/sponsor/proof-index.md",
                "docs/sponsor/caveats.md",
                "infra/",
                "aspire/AppHost/Program.cs",
                "ci_artifacts/demo/vm-deallocation.json",
            ],
            "notes": "CI deallocates the bridge VM after proof to control cost.",
        },
        {
            "requirement": "7",
            "summary": "Team communication, meeting cadence, document sharing, and delegation are process obligations.",
            "implementation_surface": "Repository docs and campaign writebacks provide technical status; meeting cadence remains a team process item.",
            "proof_type": "process_artifact",
            "status": "pass",
            "artifact_paths": [
                "dynamic_campaigns/sponsor_demo_closeout/",
                "dynamic_campaigns/sponsor_pushback_hardening/",
                "docs/sponsor/non-code-artifacts.md",
                "README.md",
            ],
            "notes": "This is not CI-verifiable; final report records the process evidence location and remaining ownership boundary.",
        },
    ]


def _append_requirement_matrix(lines: list[str], rows: list[dict]) -> None:
    lines.extend(["", "## Requirement Proof Matrix", ""])
    lines.append("| Requirement | Status | Proof | Implementation Surface | Evidence | Notes |")
    lines.append("|---|---|---|---|---|---|")
    for row in rows:
        evidence = "<br>".join(f"`{path}`" for path in row.get("artifact_paths") or [])
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row.get("requirement", "")),
                    str(row.get("status", "")),
                    str(row.get("proof_type", "")),
                    str(row.get("implementation_surface", "")).replace("|", "/"),
                    evidence.replace("|", "/"),
                    str(row.get("notes", "")).replace("|", "/"),
                ]
            )
            + " |"
        )


def _proof_semantics(gpt_matrix: dict) -> dict:
    cases = gpt_matrix.get("cases") or []
    real_cases = [str(item.get("id")) for item in cases if isinstance(item, dict) and item.get("proof_level") == "real_execution"]
    provider_cases = [str(item.get("id")) for item in cases if isinstance(item, dict) and item.get("proof_level") == "provider_required"]
    runtime_modes: dict[str, list[str]] = {}
    for item in cases:
        if not isinstance(item, dict):
            continue
        mode = str(item.get("runtime_mode") or "unknown")
        runtime_modes.setdefault(mode, []).append(str(item.get("id")))
    if not real_cases:
        real_cases = [str(item) for item in gpt_matrix.get("real_execution_cases") or []]
    if not provider_cases:
        provider_cases = [str(item) for item in gpt_matrix.get("provider_required_cases") or gpt_matrix.get("not_live_executed_because_provider_required") or []]
    if not runtime_modes:
        for mode, count in (gpt_matrix.get("runtime_mode_counts") or {}).items():
            runtime_modes[str(mode)] = [f"{count} case(s)"]
    return {
        "live_execution": {
            "cases": real_cases,
            "meaning": "The generated tool is called by the LLM and returns a deterministic sentinel from local executable/script execution, hosted runtime providers, or runtime-shaped legacy providers.",
        },
        "provider_required": {
            "cases": provider_cases,
            "meaning": "The format is discovered and a tool schema is generated; providers are disabled or unreachable, so the tool reports that a live provider, endpoint, service, or database is required.",
        },
        "runtime_modes": {
            "cases_by_mode": dict(sorted(runtime_modes.items())),
            "meaning": "Runtime modes distinguish local execution, real hosted runtimes, route-validated REST, controlled LDAP-compatible bind/search/lookup, controlled DCE/RPC-compatible RPC, CORBA ORB/IIOP proof, and any remaining adapter-backed legacy protocol modeling.",
        },
    }


def _append_proof_semantics(lines: list[str], semantics: dict) -> None:
    live = semantics.get("live_execution", {})
    provider = semantics.get("provider_required", {})
    lines.extend(["", "## Proof Semantics", ""])
    lines.append(
        "- Live execution sentinel proofs: "
        + (", ".join(live.get("cases") or []) if live.get("cases") else "none")
        + "."
    )
    lines.append(
        "- Provider-required tool-call proofs: "
        + (", ".join(provider.get("cases") or []) if provider.get("cases") else "none")
        + "."
    )
    lines.append(
        "- Provider-required means discovery, schema generation, LLM tool-call selection, and expected provider-required result were proven; it does not claim local live execution of the protocol or database."
    )
    runtime_modes = semantics.get("runtime_modes", {}).get("cases_by_mode") or {}
    for mode, cases in runtime_modes.items():
        lines.append(f"- Runtime mode `{mode}`: " + (", ".join(cases) if cases else "none") + ".")
    if not provider.get("cases"):
        lines.append("- Required provider-required cases: 0. Current required format proofs are live execution proofs.")


def _render_sponsor_report_html(markdown_text: str) -> str:
    """Render a small self-contained HTML report from the final markdown."""
    lines = markdown_text.splitlines()
    body: list[str] = []
    in_table = False

    def close_table() -> None:
        nonlocal in_table
        if in_table:
            body.append("</tbody></table>")
            in_table = False

    for line in lines:
        if line.startswith("|") and line.endswith("|"):
            cells = [html.escape(cell.strip()).replace("&lt;br&gt;", "<br>") for cell in line.strip("|").split("|")]
            if all(set(cell.replace("-", "").strip()) == set() for cell in cells):
                continue
            if not in_table:
                body.append("<table><tbody>")
                in_table = True
            tag = "th" if any(cell.lower() in {"requirement", "status", "proof", "target"} for cell in cells) else "td"
            body.append("<tr>" + "".join(f"<{tag}>{cell}</{tag}>" for cell in cells) + "</tr>")
            continue
        close_table()
        if line.startswith("# "):
            body.append(f"<h1>{html.escape(line[2:].strip())}</h1>")
        elif line.startswith("## "):
            body.append(f"<h2>{html.escape(line[3:].strip())}</h2>")
        elif line.startswith("- "):
            body.append(f"<p class=\"bullet\">{html.escape(line[2:].strip())}</p>")
        elif line.strip():
            body.append(f"<p>{html.escape(line.strip())}</p>")
    close_table()
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Sponsor Demo Report</title>
  <style>
    body { font-family: "Segoe UI", system-ui, sans-serif; margin: 32px; color: #172033; background: #f7f8fb; }
    main { max-width: 1180px; margin: 0 auto; background: white; border: 1px solid #d9deea; border-radius: 8px; padding: 28px; }
    h1 { margin: 0 0 16px; font-size: 2rem; }
    h2 { margin-top: 30px; border-top: 1px solid #e5e8f0; padding-top: 20px; }
    p { line-height: 1.5; }
    .bullet::before { content: "- "; color: #3467eb; font-weight: 700; }
    table { width: 100%; border-collapse: collapse; margin: 14px 0 24px; font-size: 0.9rem; }
    th, td { border: 1px solid #d9deea; padding: 8px 10px; text-align: left; vertical-align: top; }
    th { background: #eef2ff; }
    code { background: #eef1f6; border-radius: 4px; padding: 1px 4px; }
  </style>
</head>
<body><main>
""" + "\n".join(body) + "\n</main></body></html>\n"


def cmd_render_sponsor_report(args: argparse.Namespace) -> int:
    markdown_path = Path(args.markdown)
    if not markdown_path.exists():
        raise AssertionError(f"markdown report missing: {markdown_path}")
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(_render_sponsor_report_html(markdown_path.read_text(encoding="utf-8")), encoding="utf-8")
    print(f"OK sponsor report html: {out_path}")
    return 0


def _build_mcp_llm_story(
    *,
    checks: dict,
    job_id: str,
    selected_tool: str,
    sentinel: str,
    schema_tool_count: int,
    artifacts: dict,
) -> dict:
    steps = [
        {
            "step": "target_supplied",
            "status": "pass" if job_id else "fail",
            "evidence": [artifacts["job_status_history"]],
            "notes": f"Cloud proof job id: {job_id or '-'}",
        },
        {
            "step": "invocables_discovered",
            "status": "pass" if selected_tool else "fail",
            "evidence": [artifacts["selected_invocable"], artifacts["job_status_history"]],
            "notes": f"Selected invocable: {selected_tool or '-'}",
        },
        {
            "step": "mcp_schema_generated",
            "status": "pass" if checks.get("generated_schema_exists") else "fail",
            "evidence": [artifacts["generated_schema"]],
            "notes": f"Generated schema tool count: {schema_tool_count}",
        },
        {
            "step": "llm_called_tool",
            "status": "pass" if checks.get("gpt_tool_call_seen") else "fail",
            "evidence": [artifacts["transcript"]],
            "notes": "Transcript includes a tool_call event.",
        },
        {
            "step": "tool_result_returned",
            "status": "pass" if checks.get("gpt_sentinel_seen") else "fail",
            "evidence": [artifacts["transcript"]],
            "notes": f"Tool result includes sentinel: {sentinel or '-'}",
        },
        {
            "step": "artifact_downloaded",
            "status": "pass" if checks.get("downloaded_schema_exists") else "fail",
            "evidence": [artifacts["downloaded_schema"]],
            "notes": "Downloaded through /api/download/{job_id}/mcp_schema.json.",
        },
    ]
    return {
        "canonical_live_proof": "deterministic_cmd_fixture",
        "job_id": job_id,
        "selected_tool": selected_tool,
        "sentinel": sentinel,
        "schema_tool_count": schema_tool_count,
        "steps": steps,
        "passed": all(step["status"] == "pass" for step in steps),
    }


def _append_mcp_llm_story(lines: list[str], story: dict) -> None:
    lines.extend(["", "## MCP Generation And LLM Invocation", ""])
    lines.append(f"Canonical live proof: `{story.get('canonical_live_proof')}`")
    lines.append(f"Job ID: `{story.get('job_id') or '-'}`")
    lines.append(f"Selected tool: `{story.get('selected_tool') or '-'}`")
    lines.append(f"Schema tool count: `{story.get('schema_tool_count')}`")
    lines.append("")
    lines.append("| Step | Status | Evidence | Notes |")
    lines.append("|---|---|---|---|")
    for step in story.get("steps") or []:
        evidence = "<br>".join(f"`{path}`" for path in step.get("evidence") or [])
        lines.append(
            f"| {step.get('step')} | {step.get('status')} | {evidence} | "
            f"{str(step.get('notes') or '').replace('|', '/')} |"
        )


def _append_windows_gpt_proofs(lines: list[str], windows_gpt: dict) -> None:
    lines.extend(["", "## Windows GPT Tool-Call Proofs", ""])
    if windows_gpt.get("missing"):
        lines.append(f"Windows GPT proof matrix was not present in this artifact: `{windows_gpt.get('missing')}`.")
        return
    lines.append(
        f"Summary: {windows_gpt.get('passed', 0)}/{windows_gpt.get('total', 0)} "
        f"tool-result-observed proofs passed."
    )
    lines.append("")
    lines.append("| Target | Status | Tool Call | Tool Result | Transcript | Proof Level |")
    lines.append("|---|---|---:|---:|---:|---|")
    for item in windows_gpt.get("cases") or []:
        lines.append(
            f"| {item.get('id')} | {'pass' if item.get('passed') else 'fail'} | "
            f"{bool(item.get('tool_call_seen'))} | {bool(item.get('tool_result_seen'))} | "
            f"{bool(item.get('transcript_exists'))} | {item.get('proof_level', 'tool_result_observed')} |"
        )


def _append_repo_ingestion_proof(lines: list[str], repo_ingestion: dict) -> None:
    lines.extend(["", "## Repo Ingestion Proof", ""])
    if repo_ingestion.get("missing"):
        lines.append(f"Repo ingestion proof was not present in this artifact: `{repo_ingestion.get('missing')}`.")
        return
    lines.append(f"Status: {'PASS' if repo_ingestion.get('passed') else 'FAIL'}")
    lines.append(f"- Fixture directory: `{repo_ingestion.get('target_dir', 'tests/fixtures/sponsor_repo_fixture')}`")
    lines.append(f"- Invocables discovered: {repo_ingestion.get('invocable_count', 0)}")
    lines.append(f"- Selected repo-derived tool: `{repo_ingestion.get('selected_tool') or '-'}`")
    lines.append(f"- GPT tool call seen: {bool(repo_ingestion.get('tool_call_seen'))}")
    lines.append(f"- Tool result seen: {bool(repo_ingestion.get('tool_result_seen'))}")
    lines.append(f"- Sentinel seen: {bool(repo_ingestion.get('sentinel_seen'))}")


def _append_com_runtime_proof(lines: list[str], com_runtime: dict) -> None:
    lines.extend(["", "## COM/DCOM Surface Proof", ""])
    if com_runtime.get("missing"):
        lines.append(f"COM runtime proof was not present in this artifact: `{com_runtime.get('missing')}`.")
        return
    lines.append(f"Status: {'PASS' if com_runtime.get('passed') else 'FAIL'}")
    lines.append(f"- Proof level: `{com_runtime.get('proof_level', 'com_runtime')}`")
    lines.append(f"- Runtime mode: `{com_runtime.get('runtime_mode', 'com_runtime')}`")
    lines.append(f"- Surface: `{com_runtime.get('dcom_surface', 'local_com_automation')}`")
    lines.append(f"- Remote DCOM activation claimed: {bool(com_runtime.get('remote_dcom_activation_claimed'))}")
    lines.append(f"- COM objects: {', '.join(com_runtime.get('com_objects') or []) or '-'}")


def _append_stretch_proof_matrix(lines: list[str], stretch_matrix: dict) -> None:
    lines.extend(["", "## Stretch Goal Proof Matrix", ""])
    lines.append(
        f"Summary: {stretch_matrix.get('passed_count', 0)}/{stretch_matrix.get('total', 0)} "
        "stretch proofs passed."
    )
    lines.append("")
    lines.append("| Proof | Status | Target Mode | Current Mode | Required Artifacts |")
    lines.append("|---|---|---|---|---|")
    for item in stretch_matrix.get("entries") or []:
        artifacts = "<br>".join(f"`{path}`" for path in item.get("required_artifacts") or [])
        lines.append(
            f"| {item.get('label')} | {item.get('status')} | `{item.get('target_mode')}` | "
            f"`{item.get('current_mode')}` | {artifacts} |"
        )
    lines.extend(
        [
            "",
            "## Hard Legacy Runtime Proofs",
            "",
            "LDAP/JNDI, CORBA ORB/IIOP, MSRPC, and remote DCOM are treated as hard stretch proofs. "
            "They are not considered complete until their focused runtime artifacts exist and the "
            "final stretch proof matrix marks them `pass`.",
            "",
            "## Undocumented Binary Recovery Proof",
            "",
            "Ghidra/dynamic recovery is treated as an evidence-ranked proof. The project should only "
            "claim recovered invocations for fixtures with `confirmed_invocation` or explicitly accepted "
            "`probable_invocation` evidence.",
            "",
            "## Remaining Truthful Boundaries",
            "",
            "Until the stretch matrix passes, the canonical public claim remains the prior green proof. "
            "Even after Ghidra recovery passes, arbitrary closed-source binary semantic recovery remains "
            "best-effort and evidence-ranked, not guaranteed perfect recovery.",
        ]
    )


def cmd_summarize_sponsor_demo(args: argparse.Namespace) -> int:
    non_vm_path = Path(args.non_vm_summary)
    windows_path = Path(args.windows_summary)
    gpt_dir = Path(args.gpt_artifact_dir)
    gpt_matrix_path = Path(args.gpt_matrix_summary)
    windows_gpt_path = Path(args.windows_gpt_summary)
    repo_ingestion_path = Path(args.repo_ingestion_summary)
    com_runtime_path = Path(args.com_runtime_summary)
    stretch_runtime_path = Path(args.stretch_runtime_summary)
    ghidra_recovery_path = Path(args.ghidra_recovery_summary)
    remote_dcom_path = Path(args.remote_dcom_summary)
    windows_runtime_path = Path(args.windows_runtime_summary)
    deallocation_path = Path(args.vm_deallocation)
    out_path = Path(args.out)
    canonical_run_url = str(getattr(args, "canonical_run_url", "") or os.getenv("CANONICAL_SPONSOR_RUN_URL", ""))
    require_remote_dcom = bool(getattr(args, "require_remote_dcom", False))

    non_vm = _load_json(non_vm_path) if non_vm_path.exists() else {"cases": [], "failures": 1, "missing": str(non_vm_path)}
    windows = _load_json(windows_path) if windows_path.exists() else {"targets": [], "failures": 1, "missing": str(windows_path)}
    gpt_matrix = _load_json(gpt_matrix_path) if gpt_matrix_path.exists() else {"cases": [], "failures": 1, "missing": str(gpt_matrix_path)}
    windows_gpt = _load_json(windows_gpt_path) if windows_gpt_path.exists() else {"cases": [], "failures": 0, "missing": str(windows_gpt_path)}
    repo_ingestion = _load_json(repo_ingestion_path) if repo_ingestion_path.exists() else {"passed": False, "missing": str(repo_ingestion_path)}
    com_runtime = _load_json(com_runtime_path) if com_runtime_path.exists() else {"passed": False, "missing": str(com_runtime_path)}
    stretch_runtime = _load_optional_summary(stretch_runtime_path)
    ghidra_recovery = _load_optional_summary(ghidra_recovery_path)
    remote_dcom = _load_optional_summary(remote_dcom_path)
    windows_runtime = _load_optional_summary(windows_runtime_path)
    transcript_path = gpt_dir / "transcript.json"
    selected_path = gpt_dir / "selected-invocable.json"
    generated_schema_path = gpt_dir / "generated-mcp-schema.json"
    downloaded_schema_path = gpt_dir / "downloaded-mcp-schema.json"
    job_history_path = gpt_dir / "job-status-history.json"

    events = []
    sentinel = ""
    job_id = ""
    if transcript_path.exists():
        transcript = _load_json(transcript_path)
        events = transcript.get("events") or []
        sentinel = str(transcript.get("sentinel") or "")
        job_id = str(transcript.get("job_id") or "")

    schema_tool_count = 0
    if generated_schema_path.exists():
        schema = _load_json(generated_schema_path)
        schema_tool_count = len(schema.get("tools") or [])

    tool_call_seen = any(evt.get("type") == "tool_call" for evt in events if isinstance(evt, dict))
    tool_results = [evt for evt in events if isinstance(evt, dict) and evt.get("type") == "tool_result"]
    sentinel_seen = bool(sentinel and any(sentinel in str(evt.get("result", "")) for evt in tool_results))
    selected_tool = ""
    if selected_path.exists():
        selected_tool = str(_load_json(selected_path).get("name") or "")

    deallocation = _load_json(deallocation_path) if deallocation_path.exists() else {"attempted": False}
    non_vm_counts = _count_pass_fail(non_vm.get("cases") or [])
    windows_targets = windows.get("targets") or []
    windows_counts = _count_required_optional(windows_targets)
    diagnostics = _windows_diagnostics(windows_targets)
    checks = {
        "non_vm_formats_passed": non_vm_counts["failed"] == 0 and non_vm_counts["total"] > 0 and int(non_vm.get("failures", 0)) == 0,
        "windows_targets_passed": (
            windows_counts["required_failed"] == 0
            and windows_counts["required_total"] > 0
            and int(windows.get("failures", windows_counts["required_failed"])) == 0
        ),
        "gpt_format_matrix_passed": int(gpt_matrix.get("failures", 1)) == 0 and int(gpt_matrix.get("total", 0)) > 0,
        "gpt_tool_call_seen": tool_call_seen,
        "gpt_sentinel_seen": sentinel_seen,
        "generated_schema_exists": generated_schema_path.exists() and schema_tool_count > 0,
        "downloaded_schema_exists": downloaded_schema_path.exists(),
        "job_history_exists": job_history_path.exists(),
        "windows_gpt_tool_matrix_passed": int(windows_gpt.get("failures", 1)) == 0 and int(windows_gpt.get("total", 0)) > 0,
        "repo_ingestion_proof_passed": bool(repo_ingestion.get("passed")),
        "windows_com_runtime_proof_passed": bool(com_runtime.get("passed")),
        "remote_dcom_runtime_proof_passed": bool(
            remote_dcom.get("passed")
            and remote_dcom.get("runtime_mode") == "remote_dcom_runtime"
            and remote_dcom.get("remote_dcom_activation_claimed")
            and (remote_dcom.get("gpt_tool_proof") or {}).get("tool_call_seen")
            and (remote_dcom.get("gpt_tool_proof") or {}).get("tool_result_seen")
        ),
        "vm_deallocation_attempted": bool(deallocation.get("attempted")),
        "vm_deallocation_completed": bool(deallocation.get("completed")),
    }
    gate_checks = {
        key: value for key, value in checks.items()
        if key not in {"windows_gpt_tool_matrix_passed", "repo_ingestion_proof_passed"}
    }
    if not require_remote_dcom:
        gate_checks.pop("remote_dcom_runtime_proof_passed", None)
    passed = all(gate_checks.values())
    requirement_matrix = _build_requirement_matrix(
        checks=checks,
        non_vm_counts=non_vm_counts,
        windows_counts=windows_counts,
        gpt_matrix=gpt_matrix,
        windows_gpt=windows_gpt,
        repo_ingestion=repo_ingestion,
        schema_tool_count=schema_tool_count,
        job_id=job_id,
    )
    proof_semantics = _proof_semantics(gpt_matrix)
    stretch_proof_matrix = _build_stretch_proof_matrix(
        gpt_matrix=gpt_matrix,
        repo_ingestion=repo_ingestion,
        com_runtime=com_runtime,
        stretch_runtime=stretch_runtime,
        ghidra_recovery=ghidra_recovery,
        remote_dcom=remote_dcom,
        windows_runtime=windows_runtime,
    )
    artifacts = {
        "non_vm_summary": str(non_vm_path),
        "windows_summary": str(windows_path),
        "gpt_format_matrix_summary": str(gpt_matrix_path),
        "windows_gpt_summary": str(windows_gpt_path),
        "repo_ingestion_summary": str(repo_ingestion_path),
        "com_runtime_summary": str(com_runtime_path),
        "stretch_runtime_summary": str(stretch_runtime_path),
        "ghidra_recovery_summary": str(ghidra_recovery_path),
        "remote_dcom_summary": str(remote_dcom_path),
        "windows_runtime_summary": str(windows_runtime_path),
        "transcript": str(transcript_path),
        "selected_invocable": str(selected_path),
        "generated_schema": str(generated_schema_path),
        "downloaded_schema": str(downloaded_schema_path),
        "job_status_history": str(job_history_path),
        "vm_deallocation": str(deallocation_path),
    }
    mcp_llm_story = _build_mcp_llm_story(
        checks=checks,
        job_id=job_id,
        selected_tool=selected_tool,
        sentinel=sentinel,
        schema_tool_count=schema_tool_count,
        artifacts=artifacts,
    )
    summary = {
        "passed": passed,
        "checks": checks,
        "proof_semantics": proof_semantics,
        "mcp_llm_proof_story": mcp_llm_story,
        "requirement_matrix": requirement_matrix,
        "stretch_goals_passed": bool(stretch_proof_matrix.get("passed")),
        "stretch_proof_matrix": stretch_proof_matrix,
        "runtime_mode_matrix": {
            "gpt_format_modes": gpt_matrix.get("runtime_mode_counts", {}),
            "stretch_modes": {
                item["id"]: item["target_mode"]
                for item in stretch_proof_matrix.get("entries", [])
            },
        },
        "legacy_runtime_matrix": {
            "ldap_runtime": stretch_runtime.get("ldap_runtime", {"missing": stretch_runtime.get("missing", "")}),
            "corba_orb_runtime": stretch_runtime.get("corba_orb_runtime", {"missing": stretch_runtime.get("missing", "")}),
            "msrpc_runtime": stretch_runtime.get("msrpc_runtime", {"missing": stretch_runtime.get("missing", "")}),
            "remote_dcom_runtime": remote_dcom,
        },
        "ghidra_binary_recovery": ghidra_recovery,
        "remote_dcom": remote_dcom,
        "required_remote_dcom": require_remote_dcom,
        "corba_orb": stretch_runtime.get("corba_orb_runtime", {"missing": stretch_runtime.get("missing", "")}),
        "ldap_runtime": stretch_runtime.get("ldap_runtime", {"missing": stretch_runtime.get("missing", "")}),
        "msrpc_runtime": stretch_runtime.get("msrpc_runtime", {"missing": stretch_runtime.get("missing", "")}),
        "non_vm": non_vm_counts,
        "windows": windows_counts,
        "gpt_format_matrix": {
            "total": gpt_matrix.get("total", 0),
            "failures": gpt_matrix.get("failures", 1),
            "failed_ids": gpt_matrix.get("failed_ids", []),
            "real_execution_passed": gpt_matrix.get("real_execution_passed", 0),
            "real_execution_total": gpt_matrix.get("real_execution_total", 0),
            "provider_required_tool_call_passed": gpt_matrix.get("provider_required_tool_call_passed", 0),
            "provider_required_total": gpt_matrix.get("provider_required_total", 0),
            "not_live_executed_because_provider_required": gpt_matrix.get("not_live_executed_because_provider_required", []),
            "all_required_cases_live_execution": bool(gpt_matrix.get("all_required_cases_live_execution")),
            "runtime_mode_counts": gpt_matrix.get("runtime_mode_counts", {}),
            "runtime_backed_cases": gpt_matrix.get("runtime_backed_cases", []),
            "adapter_backed_cases": gpt_matrix.get("adapter_backed_cases", []),
        },
        "windows_gpt_tool_matrix": {
            "total": windows_gpt.get("total", 0),
            "passed": windows_gpt.get("passed", 0),
            "failures": windows_gpt.get("failures", 0),
            "failed_ids": windows_gpt.get("failed_ids", []),
            "proof_level": windows_gpt.get("proof_level", "tool_result_observed"),
            "missing": windows_gpt.get("missing", ""),
        },
        "repo_ingestion": {
            "passed": bool(repo_ingestion.get("passed")),
            "invocable_count": repo_ingestion.get("invocable_count", 0),
            "selected_tool": repo_ingestion.get("selected_tool", ""),
            "tool_call_seen": bool(repo_ingestion.get("tool_call_seen")),
            "tool_result_seen": bool(repo_ingestion.get("tool_result_seen")),
            "sentinel_seen": bool(repo_ingestion.get("sentinel_seen")),
            "missing": repo_ingestion.get("missing", ""),
        },
        "com_runtime": {
            "passed": bool(com_runtime.get("passed")),
            "proof_level": com_runtime.get("proof_level", "com_runtime"),
            "runtime_mode": com_runtime.get("runtime_mode", "com_runtime"),
            "dcom_surface": com_runtime.get("dcom_surface", "local_com_automation"),
            "remote_dcom_activation_claimed": bool(com_runtime.get("remote_dcom_activation_claimed")),
            "com_objects": com_runtime.get("com_objects", []),
            "missing": com_runtime.get("missing", ""),
        },
        "gpt": {
            "job_id": job_id,
            "selected_tool": selected_tool,
            "sentinel": sentinel,
            "tool_call_events": sum(1 for evt in events if isinstance(evt, dict) and evt.get("type") == "tool_call"),
            "tool_result_events": len(tool_results),
            "schema_tool_count": schema_tool_count,
        },
        "artifacts": artifacts,
        "diagnostics": diagnostics,
        "canonical_run_url": canonical_run_url,
    }
    _write_json(out_path, summary)

    markdown = Path(args.markdown) if args.markdown else None
    if markdown:
        gpt_matrix_total = int(gpt_matrix.get("total", 0))
        gpt_matrix_failures = int(gpt_matrix.get("failures", 1))
        gpt_matrix_passed = max(0, gpt_matrix_total - gpt_matrix_failures)
        lines = [
            "# Sponsor Demo E2E Summary",
            "",
            f"Overall: {'PASS' if passed else 'FAIL'}",
            "",
            f"- Sponsor non-VM formats: {non_vm_counts['passed']}/{non_vm_counts['total']} passed",
            f"- Windows VM required targets: {windows_counts['required_passed']}/{windows_counts['required_total']} passed",
            f"- Windows VM optional diagnostics: {windows_counts['optional_passed']}/{windows_counts['optional_total']} passed",
            f"- GPT format matrix: {gpt_matrix_passed}/{gpt_matrix_total} passed",
            f"- Real execution format proofs: {gpt_matrix.get('real_execution_passed', 0)}/{gpt_matrix.get('real_execution_total', 0)}",
            f"- Provider-required tool-call proofs: {gpt_matrix.get('provider_required_tool_call_passed', 0)}/{gpt_matrix.get('provider_required_total', 0)}",
            f"- Runtime-backed/provider-mode counts: {json.dumps(gpt_matrix.get('runtime_mode_counts', {}), sort_keys=True)}",
            f"- Adapter-backed required format cases: {', '.join(gpt_matrix.get('adapter_backed_cases', [])) or 'none'}",
            f"- Windows GPT tool-result-observed proofs: {windows_gpt.get('passed', 0)}/{windows_gpt.get('total', 0)}",
            f"- Repo ingestion GPT proof passed: {bool(repo_ingestion.get('passed'))}",
            f"- Windows COM runtime proof passed: {bool(com_runtime.get('passed'))}",
            f"- Controlled Remote DCOM runtime proof passed: {checks['remote_dcom_runtime_proof_passed']}",
            f"- Stretch proof matrix: {stretch_proof_matrix.get('passed_count', 0)}/{stretch_proof_matrix.get('total', 0)} passed",
            f"- Stretch proofs not yet run: {', '.join(stretch_proof_matrix.get('not_yet_run_ids', [])) or 'none'}",
            f"- GPT tool call seen: {checks['gpt_tool_call_seen']}",
            f"- Sentinel seen in tool result: {checks['gpt_sentinel_seen']}",
            f"- Generated schema tools: {schema_tool_count}",
            f"- Downloaded schema artifact exists: {checks['downloaded_schema_exists']}",
            f"- VM deallocation attempted: {checks['vm_deallocation_attempted']}",
            f"- VM deallocation completed: {checks['vm_deallocation_completed']}",
            "",
            f"Final summary artifact: `{out_path}`",
        ]
        if canonical_run_url:
            lines.append(f"- Canonical green run: {canonical_run_url}")
        if non_vm_counts["failed_ids"]:
            lines.append(f"- Failed sponsor formats: {', '.join(non_vm_counts['failed_ids'])}")
        if windows_counts["required_failed_ids"]:
            lines.append(f"- Failed required Windows targets: {', '.join(windows_counts['required_failed_ids'])}")
        if windows_counts["optional_failed_ids"]:
            lines.append(f"- Failed optional Windows diagnostics: {', '.join(windows_counts['optional_failed_ids'])}")
        if gpt_matrix.get("failed_ids"):
            lines.append(f"- Failed GPT format matrix cases: {', '.join(gpt_matrix.get('failed_ids', []))}")
        if gpt_matrix.get("not_live_executed_because_provider_required"):
            lines.append(
                "- Not live-executed because a provider is required: "
                + ", ".join(gpt_matrix.get("not_live_executed_because_provider_required", []))
            )
        _append_proof_semantics(lines, proof_semantics)
        _append_mcp_llm_story(lines, mcp_llm_story)
        _append_windows_gpt_proofs(lines, windows_gpt)
        _append_repo_ingestion_proof(lines, repo_ingestion)
        _append_com_runtime_proof(lines, com_runtime)
        _append_stretch_proof_matrix(lines, stretch_proof_matrix)
        _append_requirement_matrix(lines, requirement_matrix)
        _append_diagnostic_table(
            lines,
            "Slow Windows Targets",
            diagnostics["slow_targets"],
            f"No Windows target met the slow threshold ({diagnostics['slow_threshold_seconds']:.0f}s).",
        )
        _append_diagnostic_table(
            lines,
            "Required Windows Failures",
            diagnostics["required_failures"],
            "No required Windows target failed.",
        )
        _append_diagnostic_table(
            lines,
            "Optional Diagnostic Failures",
            diagnostics["optional_failures"],
            "No optional diagnostic target failed.",
        )
        lines.extend(["", "## Bridge Recovery Events", ""])
        if diagnostics["bridge_recovery_events"]:
            lines.append("| Target | Classification | Health | Restart | VM Restart |")
            lines.append("|---|---|---:|---:|---:|")
            for item in diagnostics["bridge_recovery_events"]:
                lines.append(
                    f"| {item['label']} | {item['classification']} | "
                    f"{_seconds(item.get('health_wait_seconds')):.3f}s | "
                    f"{_seconds(item.get('restart_seconds')):.3f}s | "
                    f"{_seconds(item.get('vm_restart_seconds')):.3f}s |"
                )
        else:
            lines.append("No bridge restart or VM restart recovery was recorded.")
        lines.extend(["", "## Session And Cache Proof", ""])
        lines.append("| Target | Cache used | Session check | Health-before SessionId | Post-grace SessionId |")
        lines.append("|---|---:|---:|---:|---:|")
        for item in diagnostics["session_cache_proof"]:
            lines.append(
                f"| {item['label']} | {item['session_cache_used']} | "
                f"{_seconds(item.get('session_check_seconds')):.3f}s | "
                f"{item.get('health_before_session_id')} | {item.get('post_grace_session_id')} |"
            )
        markdown.parent.mkdir(parents=True, exist_ok=True)
        markdown_text = "\n".join(lines) + "\n"
        markdown.write_text(markdown_text, encoding="utf-8")
        html_arg = getattr(args, "html", "") or ""
        if html_arg:
            html_path = Path(html_arg)
            html_path.parent.mkdir(parents=True, exist_ok=True)
            html_path.write_text(_render_sponsor_report_html(markdown_text), encoding="utf-8")

    print(f"Sponsor Demo E2E {'PASS' if passed else 'FAIL'}: summary={out_path}")
    if not passed:
        raise AssertionError(f"Sponsor Demo E2E failed; see {out_path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("validate-discovery")
    p.add_argument("--path", required=True)
    p.add_argument("--min-invocables", type=int, default=1)
    p.set_defaults(func=cmd_validate_discovery)

    p = sub.add_parser("validate-mcp-schema")
    p.add_argument("--path", required=True)
    p.add_argument("--min-tools", type=int, default=1)
    p.set_defaults(func=cmd_validate_mcp_schema)

    p = sub.add_parser("run-fixture-contract")
    p.add_argument("--out", required=True)
    p.add_argument("--fixtures", nargs="*")
    p.set_defaults(func=cmd_run_fixture_contract)

    p = sub.add_parser("run-sponsor-contract")
    p.add_argument("--manifest", default=str(SPONSOR_MANIFEST))
    p.add_argument("--out", required=True)
    p.set_defaults(func=cmd_run_sponsor_contract)

    p = sub.add_parser("touch-bridge-lease")
    p.add_argument("--storage-account", required=True)
    p.add_argument("--container", required=True)
    p.add_argument("--reason", required=True)
    p.add_argument("--job-id", default="")
    p.set_defaults(func=cmd_touch_bridge_lease)

    p = sub.add_parser("poll-job")
    p.add_argument("--base-url", required=True)
    p.add_argument("--job-id", required=True)
    p.add_argument("--pipeline-key", default=os.getenv("PIPELINE_API_KEY", ""))
    p.add_argument("--timeout", type=int, default=420)
    p.add_argument("--min-invocables", type=int, default=1)
    p.set_defaults(func=cmd_poll_job)

    p = sub.add_parser("cloud-gpt-e2e")
    p.add_argument("--base-url", required=True)
    p.add_argument("--pipeline-key", default=os.getenv("PIPELINE_API_KEY", ""))
    p.add_argument("--target", required=True)
    p.add_argument("--tool-name", default="EchoSentinel")
    p.add_argument("--sentinel", default="")
    p.add_argument("--timeout", type=int, default=600)
    p.add_argument("--chat-timeout", type=int, default=240)
    p.add_argument("--transcript", default="")
    p.add_argument("--artifact-dir", default="ci_artifacts/gpt4o-tool-e2e")
    p.add_argument("--lease-storage-account", default="")
    p.add_argument("--lease-container", default="")
    p.add_argument("--lease-job-id", default="")
    p.set_defaults(func=cmd_cloud_gpt_e2e)

    p = sub.add_parser("cloud-gpt-format-matrix")
    p.add_argument("--base-url", required=True)
    p.add_argument("--pipeline-key", default=os.getenv("PIPELINE_API_KEY", ""))
    p.add_argument("--manifest", default=str(SPONSOR_MANIFEST))
    p.add_argument("--artifact-dir", default="ci_artifacts/demo/gpt-format-matrix")
    p.add_argument("--sentinel-prefix", default="")
    p.add_argument("--timeout", type=int, default=600)
    p.add_argument("--chat-timeout", type=int, default=240)
    p.add_argument("--lease-storage-account", default="")
    p.add_argument("--lease-container", default="")
    p.add_argument("--lease-job-id", default="")
    p.add_argument("--only-case", default="")
    p.set_defaults(func=cmd_cloud_gpt_format_matrix)

    p = sub.add_parser("ldap-runtime-proof")
    p.add_argument("--base-url", required=True)
    p.add_argument("--pipeline-key", default=os.getenv("PIPELINE_API_KEY", ""))
    p.add_argument("--artifact-dir", default="ci_artifacts/demo/legacy/jndi_ldap")
    p.add_argument("--matrix-out", default="ci_artifacts/demo/legacy-runtime-matrix/summary.json")
    p.add_argument("--sentinel", default="")
    p.add_argument("--timeout", type=int, default=60)
    p.set_defaults(func=cmd_ldap_runtime_proof)

    p = sub.add_parser("corba-orb-runtime-proof")
    p.add_argument("--base-url", required=True)
    p.add_argument("--pipeline-key", default=os.getenv("PIPELINE_API_KEY", ""))
    p.add_argument("--artifact-dir", default="ci_artifacts/demo/legacy/corba_orb")
    p.add_argument("--matrix-out", default="ci_artifacts/demo/legacy-runtime-matrix/summary.json")
    p.add_argument("--sentinel", default="")
    p.add_argument("--timeout", type=int, default=90)
    p.set_defaults(func=cmd_corba_orb_runtime_proof)

    p = sub.add_parser("msrpc-runtime-proof")
    p.add_argument("--base-url", required=True)
    p.add_argument("--pipeline-key", default=os.getenv("PIPELINE_API_KEY", ""))
    p.add_argument("--artifact-dir", default="ci_artifacts/demo/legacy/msrpc")
    p.add_argument("--matrix-out", default="ci_artifacts/demo/legacy-runtime-matrix/summary.json")
    p.add_argument("--sentinel", default="")
    p.add_argument("--timeout", type=int, default=90)
    p.set_defaults(func=cmd_msrpc_runtime_proof)

    p = sub.add_parser("windows-gpt-tool-matrix")
    p.add_argument("--base-url", required=True)
    p.add_argument("--pipeline-key", default=os.getenv("PIPELINE_API_KEY", ""))
    p.add_argument("--windows-dir", default="ci_artifacts/demo/windows")
    p.add_argument("--artifact-dir", default="ci_artifacts/demo/windows-gpt")
    p.add_argument("--only-target", default="")
    p.add_argument("--chat-timeout", type=int, default=240)
    p.set_defaults(func=cmd_windows_gpt_tool_matrix)

    p = sub.add_parser("windows-com-runtime-proof")
    p.add_argument("--resource-group", default=os.getenv("RESOURCE_GROUP", ""))
    p.add_argument("--vm-name", default=os.getenv("VM_NAME", ""))
    p.add_argument("--out", default="ci_artifacts/demo/windows/com_runtime/com_runtime.summary.json")
    p.add_argument("--sentinel", default="")
    p.add_argument("--timeout", type=int, default=120)
    p.set_defaults(func=cmd_windows_com_runtime_proof)

    p = sub.add_parser("windows-remote-dcom-runtime-proof")
    p.add_argument("--resource-group", default=os.getenv("RESOURCE_GROUP", ""))
    p.add_argument("--server-vm-name", default=os.getenv("VM_NAME", ""))
    p.add_argument("--client-mode", choices=["azure-vm", "local"], default="azure-vm")
    p.add_argument("--client-vm-name", default="")
    p.add_argument("--server-target", default="")
    p.add_argument("--dcom-username", default="mcpdcom")
    p.add_argument("--dcom-password", required=True)
    p.add_argument("--base-url", default="")
    p.add_argument("--pipeline-key", default=os.getenv("PIPELINE_API_KEY", ""))
    p.add_argument("--out", default="ci_artifacts/demo/windows/dcom/dcom.summary.json")
    p.add_argument("--artifact-dir", default="ci_artifacts/demo/windows/dcom")
    p.add_argument("--sentinel", default="")
    p.add_argument("--timeout", type=int, default=420)
    p.add_argument("--chat-timeout", type=int, default=240)
    p.add_argument("--cleanup", action=argparse.BooleanOptionalAction, default=True)
    p.set_defaults(func=cmd_windows_remote_dcom_runtime_proof)

    p = sub.add_parser("repo-ingestion-gpt-proof")
    p.add_argument("--base-url", required=True)
    p.add_argument("--pipeline-key", default=os.getenv("PIPELINE_API_KEY", ""))
    p.add_argument("--target-dir", default=str(SPONSOR_REPO_FIXTURE))
    p.add_argument("--artifact-dir", default="ci_artifacts/demo/repo-ingestion")
    p.add_argument("--sentinel", default="")
    p.add_argument("--min-invocables", type=int, default=2)
    p.add_argument("--chat-timeout", type=int, default=240)
    p.set_defaults(func=cmd_repo_ingestion_gpt_proof)

    p = sub.add_parser("direct-bridge-e2e")
    p.add_argument("--bridge-url", required=True)
    p.add_argument("--bridge-secret", required=True)
    p.add_argument("--targets", nargs="*")
    p.add_argument("--optional-targets", nargs="*")
    p.add_argument("--timeout", type=int, default=240)
    p.add_argument("--health-timeout", type=int, default=45)
    p.add_argument("--post-grace", type=float, default=3.0)
    p.add_argument("--bridge-resource-group", default=os.getenv("RESOURCE_GROUP", ""))
    p.add_argument("--bridge-vm-name", default=os.getenv("VM_NAME", ""))
    p.add_argument("--bridge-task-name", default=os.getenv("BRIDGE_TASK_NAME", "MCP-Factory-Bridge-Interactive"))
    p.add_argument("--bridge-restart-timeout", type=int, default=90)
    p.add_argument("--bridge-required-session-id", type=int, default=1)
    p.add_argument("--bridge-session-cache", default="")
    p.add_argument("--out", default="")
    p.add_argument("--out-dir", default="ci_artifacts/windows-bridge-e2e")
    p.set_defaults(func=cmd_direct_bridge_e2e)

    p = sub.add_parser("bridge-target-e2e")
    p.add_argument("--bridge-url", required=True)
    p.add_argument("--bridge-secret", required=True)
    p.add_argument("--target", required=True)
    p.add_argument("--label", default="")
    p.add_argument("--kind", default="system_path")
    p.add_argument("--hints", default="github actions bridge e2e")
    p.add_argument("--types", nargs="*")
    p.add_argument("--timeout", type=int, default=180)
    p.add_argument("--health-timeout", type=int, default=45)
    p.add_argument("--post-grace", type=float, default=3.0)
    p.add_argument("--bridge-resource-group", default=os.getenv("RESOURCE_GROUP", ""))
    p.add_argument("--bridge-vm-name", default=os.getenv("VM_NAME", ""))
    p.add_argument("--bridge-task-name", default=os.getenv("BRIDGE_TASK_NAME", "MCP-Factory-Bridge-Interactive"))
    p.add_argument("--bridge-restart-timeout", type=int, default=90)
    p.add_argument("--bridge-required-session-id", type=int, default=1)
    p.add_argument("--bridge-session-cache", default="")
    p.add_argument("--min-invocables", type=int, default=1)
    p.add_argument("--required", default="true")
    p.add_argument("--expect-source-type", default="")
    p.add_argument("--expect-name-contains", default="")
    p.add_argument("--out-dir", default="ci_artifacts/windows-bridge-e2e")
    p.set_defaults(func=cmd_bridge_target_e2e)

    p = sub.add_parser("summarize-bridge-e2e")
    p.add_argument("--out-dir", default="ci_artifacts/windows-bridge-e2e")
    p.set_defaults(func=cmd_summarize_bridge_e2e)

    p = sub.add_parser("summarize-sponsor-demo")
    p.add_argument("--non-vm-summary", default="ci_artifacts/demo/non-vm/summary.json")
    p.add_argument("--windows-summary", default="ci_artifacts/demo/windows/summary.json")
    p.add_argument("--gpt-artifact-dir", default="ci_artifacts/demo/gpt4o")
    p.add_argument("--gpt-matrix-summary", default="ci_artifacts/demo/gpt-format-matrix/summary.json")
    p.add_argument("--windows-gpt-summary", default="ci_artifacts/demo/windows-gpt/summary.json")
    p.add_argument("--repo-ingestion-summary", default="ci_artifacts/demo/repo-ingestion/summary.json")
    p.add_argument("--com-runtime-summary", default="ci_artifacts/demo/windows/com_runtime/com_runtime.summary.json")
    p.add_argument("--stretch-runtime-summary", default="ci_artifacts/demo/legacy-runtime-matrix/summary.json")
    p.add_argument("--ghidra-recovery-summary", default="ci_artifacts/demo/ghidra/summary.json")
    p.add_argument("--remote-dcom-summary", default="ci_artifacts/demo/windows/dcom/dcom.summary.json")
    p.add_argument("--windows-runtime-summary", default="ci_artifacts/demo/windows/runtime_fixture/runtime_fixture.summary.json")
    p.add_argument("--vm-deallocation", default="ci_artifacts/demo/vm-deallocation.json")
    p.add_argument("--out", default="ci_artifacts/demo/final-summary.json")
    p.add_argument("--markdown", default="")
    p.add_argument("--html", default="")
    p.add_argument("--canonical-run-url", default="")
    p.add_argument("--require-remote-dcom", action="store_true")
    p.set_defaults(func=cmd_summarize_sponsor_demo)

    p = sub.add_parser("render-sponsor-report")
    p.add_argument("--markdown", default="ci_artifacts/demo/final-summary.md")
    p.add_argument("--out", default="ci_artifacts/demo/sponsor-report.html")
    p.set_defaults(func=cmd_render_sponsor_report)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.func(args)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
