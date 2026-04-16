#!/usr/bin/env python3
"""CI/E2E verification helpers for MCP Factory.

These checks intentionally assert observable outputs: invocable counts, MCP
schema shape, tool-call events, sentinel output, and downloadable artifacts.
"""

from __future__ import annotations

import argparse
import json
import os
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


def _write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _bridge_analyze_once(
    bridge_url: str,
    bridge_secret: str,
    target: str,
    *,
    timeout: int,
    raw_path: Path,
) -> dict:
    body = {
        "path": target,
        "hints": "github actions bridge e2e",
        "types": ["gui", "com", "cli", "registry", "dotnet", "rpc", "ghidra"],
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

    job_id = _upload_file(base_url, target, key=args.pipeline_key or "", hints=f"e2e sentinel {sentinel}")
    status_history: list[dict] = []
    deadline = time.monotonic() + args.timeout
    while True:
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
    print(
        "OK cloud GPT E2E: "
        f"job={job_id} tool={selected[0]['name']} sentinel={sentinel} "
        f"invocables={len(invocables)} schema_tools={len(tools)} "
        f"downloaded_schema={downloaded_schema_ok} transcript={transcript_path}"
    )
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

    summary = []
    failures = 0

    for target, required in [(t, True) for t in required_targets] + [(t, False) for t in optional_targets]:
        safe_name = _safe_target_name(target)
        target_dir = out_dir / safe_name
        target_dir.mkdir(parents=True, exist_ok=True)
        raw_path = target_dir / f"{safe_name}.raw.jsonl"
        summary_path = target_dir / f"{safe_name}.summary.json"
        error_path = target_dir / f"{safe_name}.error.txt"

        health_before = _bridge_health(bridge_url, args.bridge_secret)
        attempts = []
        result = _bridge_analyze_once(
            bridge_url,
            args.bridge_secret,
            target,
            timeout=args.timeout,
            raw_path=raw_path,
        )
        attempts.append(result)

        initial_payload = result.get("payload") or {}
        if not result["ok"] or not _extract_invocables(initial_payload):
            retry_health = _bridge_health(bridge_url, args.bridge_secret)
            retry_raw_path = target_dir / f"{safe_name}.retry.raw.jsonl"
            retry_result = _bridge_analyze_once(
                bridge_url,
                args.bridge_secret,
                target,
                timeout=args.timeout,
                raw_path=retry_raw_path,
            )
            retry_result["health_before_retry"] = retry_health
            attempts.append(retry_result)
            result = retry_result

        payload = result.get("payload") or {}
        invocables = _extract_invocables(payload)
        bridge_errors = payload.get("errors") if isinstance(payload, dict) else None
        passed = bool(result.get("ok") and len(invocables) > 0)
        health_after = _bridge_health(bridge_url, args.bridge_secret)
        first_names = [str(inv.get("name", "")) for inv in invocables[:20]]
        error_text = ""
        if not passed:
            error_text = str(result.get("error") or bridge_errors or f"invocables={len(invocables)}")
            error_path.write_text(error_text, encoding="utf-8")
            if required:
                failures += 1

        item = {
            "target": target,
            "category": _target_category(target),
            "required": required,
            "passed": passed,
            "invocable_count": len(invocables),
            "first_20_invocable_names": first_names,
            "bridge_http_status": result.get("http_status"),
            "exception": error_text,
            "elapsed_seconds": result.get("elapsed_seconds"),
            "retry_count": max(0, len(attempts) - 1),
            "raw_response_path": result.get("raw_response_path") or str(raw_path),
            "summary_path": str(summary_path),
            "bridge_errors": bridge_errors,
            "health_before": health_before,
            "health_after": health_after,
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
        summary.append(item)
        status = "OK" if passed else ("OPTIONAL-FAIL" if not required else "FAIL")
        print(f"{status} bridge target {target}: invocables={len(invocables)} retry_count={item['retry_count']}")

    summary_file = out_dir / "summary.json"
    _write_json(summary_file, {"targets": summary, "failures": failures})
    legacy_out = Path(args.out) if args.out else None
    if legacy_out:
        _write_json(legacy_out, {"targets": summary, "failures": failures})
    if failures:
        raise AssertionError(f"{failures} required bridge target(s) failed; see {summary_file}")
    print(f"OK direct bridge E2E: {len(summary)} target(s), artifacts={out_dir}")
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
    p.set_defaults(func=cmd_cloud_gpt_e2e)

    p = sub.add_parser("direct-bridge-e2e")
    p.add_argument("--bridge-url", required=True)
    p.add_argument("--bridge-secret", required=True)
    p.add_argument("--targets", nargs="*")
    p.add_argument("--optional-targets", nargs="*")
    p.add_argument("--timeout", type=int, default=240)
    p.add_argument("--out", default="")
    p.add_argument("--out-dir", default="ci_artifacts/windows-bridge-e2e")
    p.set_defaults(func=cmd_direct_bridge_e2e)

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
