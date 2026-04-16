#!/usr/bin/env python3
"""CI/E2E verification helpers for MCP Factory.

These checks intentionally assert observable outputs: invocable counts, MCP
schema shape, tool-call events, sentinel output, and downloadable artifacts.
"""

from __future__ import annotations

import argparse
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
BRIDGE_ACTIVITY_BLOB = "_vm/last_bridge_activity.json"

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
            return {
                "ok": 200 <= resp.status < 300,
                "status": resp.status,
                "body": raw,
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
        "az", "vm", "run-command", "invoke",
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
    cmd = ["az", "vm", "restart", "-g", resource_group, "-n", vm_name]
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
        "az", "vm", "get-instance-view",
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

    cmd = ["az", "vm", "start", "-g", resource_group, "-n", vm_name]
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
        "az", "vm", "run-command", "invoke",
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
) -> dict:
    health = _wait_bridge_health(bridge_url, bridge_secret, timeout=timeout)
    process_info = None
    if health.get("ok") and required_session_id is not None and restart_resource_group and restart_vm_name:
        process_info = _bridge_process_info(
            resource_group=restart_resource_group,
            vm_name=restart_vm_name,
            timeout=restart_timeout,
        )
        health["bridge_process"] = process_info
        if process_info.get("ok") and process_info.get("session_id") == required_session_id:
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
                    return after_vm_restart
                after_vm_restart["ok"] = False
                after_vm_restart["error"] = (
                    f"bridge process SessionId must be {required_session_id}; "
                    f"found {process_info.get('session_id')} after VM restart"
                )
                return after_vm_restart
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
            "az", "storage", "blob", "upload",
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
        case_dir = out_root / case_id
        case_dir.mkdir(parents=True, exist_ok=True)
        sentinel = f"{sentinel_prefix}_{case_id}"
        proof_level = case.get("proof_level", "provider_required")
        started = time.perf_counter()
        item = {
            "id": case_id,
            "category": case.get("category", case_id),
            "proof_level": proof_level,
            "expected_result": case.get("expected_result", ""),
            "passed": False,
            "tool_call_seen": False,
            "tool_result_seen": False,
            "sentinel_seen": False,
            "provider_required_seen": False,
            "job_id": "",
            "selected_tool": "",
            "schema_tool_count": 0,
            "error": "",
            "elapsed_seconds": 0.0,
        }
        print(f"START GPT format case {case_id}: category={item['category']} proof_level={proof_level}")
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
    aggregate = {
        "cases": summaries,
        "total": len(summaries),
        "failures": len(failures),
        "failed_ids": [item["id"] for item in failures],
        "real_execution_total": len(real_cases),
        "real_execution_passed": sum(1 for item in real_cases if item.get("passed") and item.get("sentinel_seen")),
        "provider_required_total": len(provider_cases),
        "provider_required_tool_call_passed": sum(
            1 for item in provider_cases
            if item.get("passed") and item.get("tool_call_seen") and item.get("provider_required_seen")
        ),
        "not_live_executed_because_provider_required": [item["id"] for item in provider_cases],
    }
    _write_json(out_root / "summary.json", aggregate)
    if failures:
        raise AssertionError(f"{len(failures)} GPT format matrix case(s) failed: {aggregate['failed_ids']}")
    print(f"OK GPT format matrix: {len(summaries)} case(s), artifacts={out_root}")
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
        "bridge_elapsed_seconds": result.get("elapsed_seconds"),
        "retry_count": max(0, len(attempts) - 1),
        "health_wait_timeout_seconds": health_timeout,
        "post_grace_seconds": post_grace,
        "bridge_restart_resource_group": bridge_resource_group,
        "bridge_restart_vm_name": bridge_vm_name,
        "bridge_restart_task_name": bridge_task_name,
        "bridge_required_session_id": bridge_required_session_id,
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
    _write_json(summary_path, item)
    status = "OK" if passed else ("OPTIONAL-FAIL" if not required else "FAIL")
    print(
        f"{status} bridge target {safe_name}: "
        f"matched={len(matched_invocables)} total={len(all_invocables)} "
        f"retry_count={item['retry_count']} elapsed={item['elapsed_seconds']}s"
    )
    return item


def cmd_bridge_target_e2e(args: argparse.Namespace) -> int:
    item = _run_bridge_case(
        bridge_url=args.bridge_url.rstrip("/"),
        bridge_secret=args.bridge_secret,
        target=args.target,
        out_dir=Path(args.out_dir),
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
    failures = [item for item in summaries if item.get("required", True) and not item.get("passed")]
    aggregate = {
        "targets": summaries,
        "total": len(summaries),
        "failures": len(failures),
        "failed_labels": [item.get("label") for item in failures],
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


def cmd_summarize_sponsor_demo(args: argparse.Namespace) -> int:
    non_vm_path = Path(args.non_vm_summary)
    windows_path = Path(args.windows_summary)
    gpt_dir = Path(args.gpt_artifact_dir)
    gpt_matrix_path = Path(args.gpt_matrix_summary)
    deallocation_path = Path(args.vm_deallocation)
    out_path = Path(args.out)

    non_vm = _load_json(non_vm_path) if non_vm_path.exists() else {"cases": [], "failures": 1, "missing": str(non_vm_path)}
    windows = _load_json(windows_path) if windows_path.exists() else {"targets": [], "failures": 1, "missing": str(windows_path)}
    gpt_matrix = _load_json(gpt_matrix_path) if gpt_matrix_path.exists() else {"cases": [], "failures": 1, "missing": str(gpt_matrix_path)}
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
    windows_counts = _count_pass_fail(windows.get("targets") or [])
    checks = {
        "non_vm_formats_passed": non_vm_counts["failed"] == 0 and non_vm_counts["total"] > 0 and int(non_vm.get("failures", 0)) == 0,
        "windows_targets_passed": windows_counts["failed"] == 0 and windows_counts["total"] > 0 and int(windows.get("failures", 0)) == 0,
        "gpt_format_matrix_passed": int(gpt_matrix.get("failures", 1)) == 0 and int(gpt_matrix.get("total", 0)) > 0,
        "gpt_tool_call_seen": tool_call_seen,
        "gpt_sentinel_seen": sentinel_seen,
        "generated_schema_exists": generated_schema_path.exists() and schema_tool_count > 0,
        "downloaded_schema_exists": downloaded_schema_path.exists(),
        "job_history_exists": job_history_path.exists(),
        "vm_deallocation_attempted": bool(deallocation.get("attempted")),
        "vm_deallocation_completed": bool(deallocation.get("completed")),
    }
    passed = all(checks.values())
    summary = {
        "passed": passed,
        "checks": checks,
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
        },
        "gpt": {
            "job_id": job_id,
            "selected_tool": selected_tool,
            "sentinel": sentinel,
            "tool_call_events": sum(1 for evt in events if isinstance(evt, dict) and evt.get("type") == "tool_call"),
            "tool_result_events": len(tool_results),
            "schema_tool_count": schema_tool_count,
        },
        "artifacts": {
            "non_vm_summary": str(non_vm_path),
            "windows_summary": str(windows_path),
            "gpt_format_matrix_summary": str(gpt_matrix_path),
            "transcript": str(transcript_path),
            "selected_invocable": str(selected_path),
            "generated_schema": str(generated_schema_path),
            "downloaded_schema": str(downloaded_schema_path),
            "job_status_history": str(job_history_path),
            "vm_deallocation": str(deallocation_path),
        },
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
            f"- Windows VM targets: {windows_counts['passed']}/{windows_counts['total']} passed",
            f"- GPT format matrix: {gpt_matrix_passed}/{gpt_matrix_total} passed",
            f"- Real execution format proofs: {gpt_matrix.get('real_execution_passed', 0)}/{gpt_matrix.get('real_execution_total', 0)}",
            f"- Provider-required tool-call proofs: {gpt_matrix.get('provider_required_tool_call_passed', 0)}/{gpt_matrix.get('provider_required_total', 0)}",
            f"- GPT tool call seen: {checks['gpt_tool_call_seen']}",
            f"- Sentinel seen in tool result: {checks['gpt_sentinel_seen']}",
            f"- Generated schema tools: {schema_tool_count}",
            f"- Downloaded schema artifact exists: {checks['downloaded_schema_exists']}",
            f"- VM deallocation attempted: {checks['vm_deallocation_attempted']}",
            f"- VM deallocation completed: {checks['vm_deallocation_completed']}",
            "",
            f"Final summary artifact: `{out_path}`",
        ]
        if non_vm_counts["failed_ids"]:
            lines.append(f"- Failed sponsor formats: {', '.join(non_vm_counts['failed_ids'])}")
        if windows_counts["failed_ids"]:
            lines.append(f"- Failed Windows targets: {', '.join(windows_counts['failed_ids'])}")
        if gpt_matrix.get("failed_ids"):
            lines.append(f"- Failed GPT format matrix cases: {', '.join(gpt_matrix.get('failed_ids', []))}")
        if gpt_matrix.get("not_live_executed_because_provider_required"):
            lines.append(
                "- Not live-executed because a provider is required: "
                + ", ".join(gpt_matrix.get("not_live_executed_because_provider_required", []))
            )
        markdown.parent.mkdir(parents=True, exist_ok=True)
        markdown.write_text("\n".join(lines) + "\n", encoding="utf-8")

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
    p.set_defaults(func=cmd_cloud_gpt_format_matrix)

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
    p.add_argument("--vm-deallocation", default="ci_artifacts/demo/vm-deallocation.json")
    p.add_argument("--out", default="ci_artifacts/demo/final-summary.json")
    p.add_argument("--markdown", default="")
    p.set_defaults(func=cmd_summarize_sponsor_demo)

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
