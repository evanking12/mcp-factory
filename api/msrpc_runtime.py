"""Controlled DCE/RPC-compatible runtime proof for sponsor RPC IDL."""

from __future__ import annotations

import importlib
import os
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any


CONTOSO_MSRPC_IDL = """[
  uuid(8fdb84f1-4c9f-4f6e-9b26-f4d7fb3f0c10),
  version(1.0)
]
interface ContosoRpcSupport {
  void RpcCreateTicket([in, string] wchar_t* sentinel);
  void RpcGetTicketStatus([in, string] wchar_t* sentinel);
  void RpcCloseTicket([in, string] wchar_t* sentinel);
};
"""

CONTEXT_UUID = ("8fdb84f1-4c9f-4f6e-9b26-f4d7fb3f0c10", "1.0")
OPNUMS = {
    "RpcCreateTicket": 0,
    "RpcGetTicketStatus": 1,
    "RpcCloseTicket": 2,
}


def msrpc_runtime_available() -> bool:
    try:
        importlib.import_module("impacket.dcerpc.v5.rpcrt")
        importlib.import_module("impacket.dcerpc.v5.transport")
        importlib.import_module("impacket.uuid")
    except Exception:
        return False
    return True


def msrpc_runtime_enabled() -> bool:
    return os.getenv("ENABLE_MSRPC_RUNTIME", "").strip().lower() in {"1", "true", "yes"} and msrpc_runtime_available()


class MsrpcRuntimeUnavailable(RuntimeError):
    pass


@dataclass
class MsrpcRuntime:
    host: str
    port: int
    server_log: list[str] = field(default_factory=list)
    version: str = "controlled-msrpc-runtime-v1"

    @property
    def binding(self) -> str:
        return f"ncacn_ip_tcp:{self.host}[{self.port}]"


_runtime_lock = threading.Lock()
_runtime: MsrpcRuntime | None = None


def _decode_payload(data: bytes) -> str:
    return data.decode("utf-8", errors="replace").rstrip("\x00")


def _callback(operation: str, runtime: MsrpcRuntime):
    def inner(data: bytes) -> bytes:
        sentinel = _decode_payload(data)
        result = f"msrpc:{operation}: {sentinel}"
        runtime.server_log.append(f"op={operation} bytes={len(data)} sentinel={sentinel}")
        return result.encode("utf-8")

    return inner


def ensure_msrpc_runtime() -> MsrpcRuntime:
    global _runtime
    with _runtime_lock:
        if _runtime is not None:
            return _runtime
        if not msrpc_runtime_available():
            raise MsrpcRuntimeUnavailable("Impacket DCE/RPC runtime is not available")

        from impacket.dcerpc.v5.rpcrt import DCERPCServer  # type: ignore

        runtime = MsrpcRuntime(host="127.0.0.1", port=0)
        server = DCERPCServer()
        server.setListenAddress(runtime.host)
        server.setListenPort(0)
        runtime.port = int(server.getListenPort())
        server.addCallbacks(CONTEXT_UUID, b"\\pipe\\contoso_rpc", {opnum: _callback(name, runtime) for name, opnum in OPNUMS.items()})
        server.daemon = True
        server.start()
        runtime.server_log.append(f"registered uuid={CONTEXT_UUID[0]} version={CONTEXT_UUID[1]} binding={runtime.binding}")
        runtime._server = server  # type: ignore[attr-defined]
        _runtime = runtime
        time.sleep(0.05)
        return runtime


def msrpc_invoke(procedure: str, sentinel: str) -> dict[str, Any]:
    runtime = ensure_msrpc_runtime()
    if procedure not in OPNUMS:
        raise MsrpcRuntimeUnavailable(f"unknown RPC procedure: {procedure}")

    from impacket.dcerpc.v5 import transport  # type: ignore
    from impacket.uuid import uuidtup_to_bin  # type: ignore

    call_id = uuid.uuid4().hex
    rpc_transport = transport.DCERPCTransportFactory(runtime.binding)
    dce = rpc_transport.get_dce_rpc()
    dce.connect()
    try:
        dce.bind(uuidtup_to_bin(CONTEXT_UUID))
        dce.call(OPNUMS[procedure], sentinel.encode("utf-8"))
        response = dce.recv()
    finally:
        try:
            dce.disconnect()
        except Exception:
            pass
    response_text = _decode_payload(response)
    return {
        "runtime_mode": "msrpc_runtime",
        "wire_protocol": "DCE/RPC v5 over ncacn_ip_tcp",
        "rpc_stack": "impacket",
        "idl": CONTOSO_MSRPC_IDL,
        "interface_uuid": CONTEXT_UUID[0],
        "interface_version": CONTEXT_UUID[1],
        "binding": runtime.binding,
        "procedure": procedure,
        "opnum": OPNUMS[procedure],
        "call_id": call_id,
        "server_log": runtime.server_log,
        "client_result": response_text,
    }
