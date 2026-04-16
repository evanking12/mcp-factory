"""api/executor.py – Tool execution backends: DLL (ctypes), CLI (subprocess), GUI (pywinauto), bridge.

Exports:
  _CTYPES_RESTYPE, _CTYPES_ARGTYPE – Windows-only ctypes type maps.
  _resolve_dll_path  – search for a DLL relative to the project root.
  _execute_dll       – call a native DLL function via ctypes.
  _execute_cli       – run a CLI tool via subprocess.
  _execute_gui       – drive GUI via pywinauto (Windows only).
  _call_execute_bridge – forward execution to the Windows VM bridge.
  _execute_tool      – top-level dispatch: picks the right backend.
"""

from __future__ import annotations

import ctypes
import json
import logging
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from api.config import IS_WINDOWS, GUI_BRIDGE_URL, GUI_BRIDGE_SECRET
from api.vm_lifecycle import ensure_bridge_ready, touch_bridge_activity

logger = logging.getLogger("mcp_factory.api")

# ── ctypes type maps (Windows-only) ────────────────────────────────────────
_CTYPES_RESTYPE: dict = {}
_CTYPES_ARGTYPE: dict = {}

if IS_WINDOWS:
    _CTYPES_RESTYPE = {
        "void":           None,
        "bool":           ctypes.c_bool,
        "int":            ctypes.c_int,
        "unsigned":       ctypes.c_uint,
        "unsigned int":   ctypes.c_uint,
        "long":           ctypes.c_long,
        "unsigned long":  ctypes.c_ulong,
        "size_t":         ctypes.c_size_t,
        "float":          ctypes.c_float,
        "double":         ctypes.c_double,
        "char*":          ctypes.c_char_p,
        "const char*":    ctypes.c_char_p,
        "char *":         ctypes.c_char_p,
        "const char *":   ctypes.c_char_p,
    }
    _CTYPES_ARGTYPE = {
        "int":            ctypes.c_int,
        "unsigned":       ctypes.c_uint,
        "unsigned int":   ctypes.c_uint,
        "long":           ctypes.c_long,
        "unsigned long":  ctypes.c_ulong,
        "size_t":         ctypes.c_size_t,
        "float":          ctypes.c_float,
        "double":         ctypes.c_double,
        "bool":           ctypes.c_bool,
        "string":         ctypes.c_char_p,
        "str":            ctypes.c_char_p,
        "char*":          ctypes.c_char_p,
        "const char*":    ctypes.c_char_p,
        "char *":         ctypes.c_char_p,
        "const char *":   ctypes.c_char_p,
    }


# ── Execution helpers ──────────────────────────────────────────────────────

def _resolve_dll_path(raw: str) -> str:
    """Return an absolute path for *raw*, searching likely anchors."""
    p = Path(raw)
    if p.is_absolute() and p.exists():
        return str(p)
    project_root = Path(__file__).resolve().parent.parent
    candidate = project_root / raw
    if candidate.exists():
        return str(candidate)
    return raw  # let ctypes emit the real error


def _execute_dll(inv: dict, execution: dict, args: dict) -> str:
    if not IS_WINDOWS:
        return "DLL execution is only supported on Windows."
    dll_path  = _resolve_dll_path(execution.get("dll_path", ""))
    func_name = execution.get("function_name", "")

    ret_str = (
        inv.get("return_type")
        or (inv.get("signature") or {}).get("return_type", "unknown")
        or "unknown"
    ).strip()
    restype = _CTYPES_RESTYPE.get(ret_str.lower(), ctypes.c_size_t)

    params = list(inv.get("parameters") or [])
    if not params:
        sig_str = (inv.get("signature") or {}).get("parameters", "")
        if sig_str:
            for chunk in sig_str.split(","):
                tokens = chunk.strip().split()
                if len(tokens) >= 2:
                    raw_type = " ".join(tokens[:-1]).lower().strip("*").rstrip()
                    pname    = tokens[-1].lstrip("*")
                    params.append({"name": pname, "type": raw_type})

    try:
        lib = ctypes.CDLL(dll_path)
        fn  = getattr(lib, func_name)
        fn.restype = restype

        c_args = []
        if params and args:
            for p in params:
                pname = p.get("name", "")
                ptype = p.get("type", "string").lower().strip("*").rstrip()
                val   = args.get(pname)
                if val is None:
                    continue
                atype = _CTYPES_ARGTYPE.get(ptype, ctypes.c_char_p)
                if atype == ctypes.c_char_p:
                    c_args.append(ctypes.c_char_p(str(val).encode()))
                else:
                    c_args.append(atype(int(val)))
        elif args:
            for v in args.values():
                if isinstance(v, bool):
                    c_args.append(ctypes.c_bool(v))
                elif isinstance(v, int):
                    c_args.append(ctypes.c_size_t(v))
                elif isinstance(v, float):
                    c_args.append(ctypes.c_double(v))
                elif isinstance(v, str):
                    c_args.append(ctypes.c_char_p(v.encode()))

        result = fn(*c_args)
        if restype == ctypes.c_char_p:
            if isinstance(result, bytes):
                return f"Returned: {result.decode(errors='replace')}"
        return f"Returned: {result}"
    except Exception as exc:
        return f"DLL call error: {exc}"


def _execute_cli(execution: dict, name: str, args: dict) -> str:
    target = (
        execution.get("executable_path")
        or execution.get("target_path")
        or execution.get("dll_path", "")
    )
    if not target:
        return f"CLI error: no executable path configured for '{name}'"

    exe_stem = Path(target).stem.lower()
    if exe_stem == name.lower():
        # Launch-the-app invocable — just open it
        try:
            if IS_WINDOWS:
                subprocess.Popen(
                    [target],
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
            else:
                subprocess.Popen([target])
            return (
                f"{Path(target).name} has been launched successfully. "
                "The application is now open. "
                "DO NOT call this launch tool again — it is already running. "
                "Proceed directly to using the other tools to interact with it."
            )
        except Exception as exc:
            return f"CLI error: {exc}"

    cmd = [target, name] + [str(v) for v in args.values()]
    creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if IS_WINDOWS else 0
    try:
        r = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10,
            creationflags=creation_flags,
        )
        return r.stdout or r.stderr or f"exit_code={r.returncode}"
    except Exception as exc:
        return f"CLI error: {exc}"


def _execute_gui(execution: dict, name: str, args: dict) -> str:
    if not IS_WINDOWS:
        return "GUI actions are only supported on Windows."
    try:
        from pywinauto.application import Application  # type: ignore
    except ImportError:
        return "pywinauto is not installed; GUI actions unavailable."

    exe_path    = execution.get("exe_path", "")
    action_type = execution.get("action_type", "menu_click")

    # Minimal GUI dispatch — delegates to the generated server's full
    # implementation when running locally on Windows; here we handle the
    # most common actions for the cloud demo path.
    if action_type == "close_app":
        try:
            app = Application(backend="uia").connect(path=exe_path, timeout=3)
            app.kill()
            return "App closed."
        except Exception as exc:
            return f"GUI close error: {exc}"

    return (
        f"GUI action '{action_type}' requested for '{exe_path}'. "
        "Full GUI automation requires Windows with pywinauto installed."
    )


def _provider_required(kind: str, name: str, detail: str = "") -> str:
    suffix = f" {detail}" if detail else ""
    return (
        f"Provider required: {kind} tool '{name}' was discovered and exposed as an MCP tool, "
        f"but live execution requires a configured backing provider/endpoint/service.{suffix}"
    )


def _materialize_script(execution: dict, preferred_path: str) -> tuple[str, str | None]:
    script_content = execution.get("script_content")
    if preferred_path and Path(preferred_path).exists():
        return preferred_path, None
    if not script_content:
        return preferred_path, None
    suffix = Path(preferred_path).suffix or ".tmp"
    fd, tmp_path = tempfile.mkstemp(suffix=suffix)
    with os.fdopen(fd, "w", encoding="utf-8", newline="") as fh:
        fh.write(script_content)
    return tmp_path, tmp_path


def _execute_script_local(execution: dict, name: str, args: dict) -> str:
    method = execution.get("method", "")
    script_path = (
        execution.get("script_path")
        or execution.get("module_path")
        or ""
    )
    func_name = execution.get("function_name") or execution.get("method_name") or name
    arg_values = list(args.values())
    tmp_path: str | None = None
    try:
        script_path, tmp_path = _materialize_script(execution, script_path)
        if method == "python_subprocess":
            arg_repr = ", ".join(repr(v) for v in arg_values)
            code = (
                "import importlib.util; "
                f"spec=importlib.util.spec_from_file_location('m', r'{script_path}'); "
                "m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); "
                f"print(m.{func_name}({arg_repr}))"
            )
            cmd = [sys.executable, "-c", code]
        elif method in ("node", "ts-node"):
            interp = "ts-node" if method == "ts-node" else "node"
            if func_name:
                arg_repr = ", ".join(json.dumps(v) for v in arg_values)
                code = (
                    f"const m=require({json.dumps(script_path)}); "
                    f"Promise.resolve(m[{json.dumps(func_name)}]({arg_repr}))"
                    ".then(v => { if (v !== undefined) console.log(v); })"
                    ".catch(e => { console.error(e && e.stack || e); process.exit(1); });"
                )
                cmd = [interp, "-e", code]
            else:
                cmd = [interp, script_path] + [str(v) for v in arg_values]
        elif method == "ruby":
            if func_name:
                arg_repr = ", ".join(repr(v) for v in arg_values)
                cmd = ["ruby", "-r", script_path, "-e", f"puts {func_name}({arg_repr})"]
            else:
                cmd = ["ruby", script_path] + [str(v) for v in arg_values]
        elif method == "php":
            if func_name:
                arg_repr = ", ".join(json.dumps(v) for v in arg_values)
                cmd = ["php", "-r", f"require {json.dumps(script_path)}; echo {func_name}({arg_repr});"]
            else:
                cmd = ["php", script_path] + [str(v) for v in arg_values]
        elif method in ("powershell", "cmd_call", "cmd", "cscript"):
            return _provider_required("Windows script runtime", name, "Run this tool through the Windows bridge.")
        else:
            return f"Script error: unsupported method '{method}'"

        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return r.stdout or r.stderr or f"exit_code={r.returncode}"
    except FileNotFoundError as exc:
        return f"Script error: interpreter not found - {exc}"
    except subprocess.TimeoutExpired:
        return "Script error: timed out after 30 s"
    except Exception as exc:
        return f"Script error: {exc}"
    finally:
        if tmp_path:
            Path(tmp_path).unlink(missing_ok=True)


def _execute_http_contract(execution: dict, name: str, args: dict) -> str:
    method = execution.get("method", "")
    base_url = execution.get("base_url")
    if not base_url:
        labels = {
            "http_request": "OpenAPI/REST endpoint",
            "jsonrpc": "JSON-RPC endpoint",
            "soap": "SOAP endpoint",
        }
        return _provider_required(labels.get(method, "HTTP endpoint"), name)
    try:
        import httpx
        if method == "http_request":
            http_method = execution.get("http_method", "get").upper()
            path = execution.get("path", "/")
            url = base_url.rstrip("/") + "/" + path.lstrip("/")
            resp = httpx.request(http_method, url, json=args or None, timeout=15)
            return resp.text or f"HTTP {resp.status_code}"
        if method == "jsonrpc":
            payload = {"jsonrpc": "2.0", "method": name, "params": list(args.values()), "id": 1}
            resp = httpx.post(base_url.rstrip("/"), json=payload, timeout=15)
            data = resp.json()
            if "error" in data:
                return f"JSON-RPC error: {data['error']}"
            return json.dumps(data.get("result"), indent=2)
        if method == "soap":
            action = execution.get("action", name)
            params_xml = "".join(f"<{k}>{v}</{k}>" for k, v in args.items())
            body = (
                '<?xml version="1.0"?>'
                '<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"'
                ' xmlns:tns="urn:service">'
                f'<soapenv:Body><tns:{action}>{params_xml}</tns:{action}></soapenv:Body>'
                '</soapenv:Envelope>'
            )
            resp = httpx.post(
                base_url.rstrip("/"),
                content=body.encode(),
                headers={"Content-Type": "text/xml; charset=utf-8", "SOAPAction": f'"{action}"'},
                timeout=15,
            )
            return resp.text
        return f"HTTP error: unsupported method '{method}'"
    except Exception as exc:
        return f"HTTP error: {exc}"


def _execute_sql_contract(execution: dict, name: str, args: dict) -> str:
    source_file = execution.get("source_file", "")
    statement = execution.get("statement", "")
    if source_file and Path(source_file).suffix.lower() in {".db", ".sqlite", ".sqlite3"} and Path(source_file).exists():
        try:
            r = subprocess.run(["sqlite3", source_file, statement], capture_output=True, text=True, timeout=15)
            return r.stdout or r.stderr or f"exit_code={r.returncode}"
        except FileNotFoundError:
            return _provider_required("SQL database", name, "sqlite3 is not installed in this runtime.")
        except Exception as exc:
            return f"SQL error: {exc}"
    return _provider_required("SQL database", name)


def _is_windows_path(value: str) -> bool:
    return bool(value and (":\\" in value or value.startswith("\\\\")))


def _should_use_bridge(method: str, execution: dict) -> bool:
    if not GUI_BRIDGE_URL or not GUI_BRIDGE_SECRET:
        return False
    if method in {"dll_import", "gui_action", "com_invoke", "com_dispatch", "dotnet_reflection", "powershell", "cmd_call", "cmd", "cscript"}:
        return True
    target = (
        execution.get("executable_path")
        or execution.get("target_path")
        or execution.get("dll_path")
        or execution.get("exe_path")
        or ""
    )
    return method in {"subprocess", "cli"} and _is_windows_path(str(target))


# Cache bridge reachability briefly to avoid hammering /health on every call,
# but never pin failures forever (transient network blips are common).
_bridge_reachable: bool | None = None  # None = untested
_bridge_checked_at: float = 0.0
_BRIDGE_CACHE_TTL_SECONDS = 120.0  # 2 min — long enough to skip probes during chat
_BRIDGE_FAIL_TTL_SECONDS = 15.0   # re-probe sooner after a failure

# Persistent httpx client with connection pooling — avoids TCP/TLS handshake
# on every call.  Created lazily so module import doesn't require httpx.
_bridge_client = None  # httpx.Client | None


def _get_bridge_client():
    """Return (or lazily create) a persistent httpx.Client for the bridge."""
    global _bridge_client
    if _bridge_client is None:
        import httpx
        _bridge_client = httpx.Client(
            base_url=GUI_BRIDGE_URL,
            headers={"X-Bridge-Key": GUI_BRIDGE_SECRET},
            timeout=httpx.Timeout(connect=5.0, read=30.0, write=10.0, pool=5.0),
            limits=httpx.Limits(max_keepalive_connections=5, keepalive_expiry=120),
        )
    return _bridge_client


def _check_bridge_alive() -> bool:
    """Quick /health probe with TTL caching."""
    global _bridge_reachable, _bridge_checked_at
    now = time.monotonic()
    ttl = _BRIDGE_CACHE_TTL_SECONDS if _bridge_reachable else _BRIDGE_FAIL_TTL_SECONDS
    if _bridge_reachable is not None and (now - _bridge_checked_at) < ttl:
        return _bridge_reachable
    _bridge_reachable = False
    try:
        client = _get_bridge_client()
        t0 = time.perf_counter()
        r = client.get("/health", timeout=5.0)
        dt_ms = (time.perf_counter() - t0) * 1000.0
        _bridge_reachable = r.status_code == 200
        logger.info("[bridge] /health status=%s latency=%.1f ms", r.status_code, dt_ms)
    except Exception:
        logger.info("[bridge] /health probe failed")
    _bridge_checked_at = now
    return _bridge_reachable


def _call_execute_bridge(inv: dict, args: dict) -> str | None:
    """Forward a tool-call to the Windows VM bridge /execute endpoint.

    Returns the result string on success, or None only when the bridge is not
    configured.  On a transport/HTTP failure, returns an error string so the
    caller never silently falls through to Linux execution (which would
    produce misleading 'No such file or directory' errors for Windows paths).
    """
    if not GUI_BRIDGE_URL or not GUI_BRIDGE_SECRET:
        return None
    global _bridge_client
    try:
        touch_bridge_activity("execute", "")
        client = _get_bridge_client()
        t0 = time.perf_counter()
        resp = client.post(
            "/execute",
            json={"invocable": inv, "args": args},
        )
        dt_ms = (time.perf_counter() - t0) * 1000.0
        resp.raise_for_status()
        logger.info(
            "[bridge] /execute tool=%s status=%s latency=%.1f ms",
            inv.get("name", "<unknown>"),
            resp.status_code,
            dt_ms,
        )
        return resp.json().get("result", "")
    except Exception as exc:
        # Reset the pooled client so the next call gets a fresh connection
        # instead of retrying a dead keepalive socket.
        _bridge_client = None
        logger.warning("[bridge] /execute failed for tool=%s: %s", inv.get("name", "<unknown>"), exc)
        return f"Bridge /execute error: {exc} — the Windows VM bridge is temporarily unreachable. Try again."


def _execute_tool(inv: dict, args: dict) -> str:
    """Dispatch a single tool call to the correct backend."""
    name      = inv.get("name", "")
    execution = inv.get("execution") or inv.get("mcp", {}).get("execution", {})
    method    = execution.get("method", "")

    # Windows-native methods must run on the Windows VM.  Provider contracts
    # and portable script runtimes execute locally so they can produce explicit,
    # deterministic results instead of being accidentally routed to the bridge.
    if _should_use_bridge(method, execution):
        if not ensure_bridge_ready(timeout_seconds=90):
            return (
                "Bridge /execute error: Windows analysis VM did not become healthy "
                "before timeout. Try again in a few minutes."
            )
        return _call_execute_bridge(inv, args) or "Bridge returned an empty result."
    if method == "dll_import":
        return _execute_dll(inv, execution, args)
    if method == "gui_action":
        return _execute_gui(execution, name, args)
    if method in ("python_subprocess", "node", "ts-node", "ruby", "php", "powershell", "cmd_call", "bash", "cmd", "cscript"):
        return _execute_script_local(execution, name, args)
    if method in ("http_request", "jsonrpc", "soap"):
        return _execute_http_contract(execution, name, args)
    if method == "sql_exec":
        return _execute_sql_contract(execution, name, args)
    if method == "rpc_call":
        iface = execution.get("interface_uuid") or execution.get("endpoint") or name
        return _provider_required("RPC endpoint", name, f"Discovered interface: {iface}.")
    if method == "corba_iiop":
        iface = execution.get("interface") or name
        return _provider_required("CORBA ORB/IIOP endpoint", name, f"Discovered interface: {iface}.")
    if method == "jndi_lookup":
        lookup = execution.get("lookup_name") or name
        return _provider_required("JNDI provider", name, f"Discovered binding: {lookup}.")
    return _execute_cli(execution, name, args)
