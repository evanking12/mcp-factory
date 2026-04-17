"""Controlled CORBA ORB/IIOP runtime proof for sponsor demo.

This module uses OmniORB/OmniORBpy when available. It generates Python stubs
from a deterministic Contoso IDL file, starts an in-process ORB server, and
invokes that server through an object reference. It is intentionally a controlled
fixture proof, not a generalized CORBA estate migration platform.
"""

from __future__ import annotations

import importlib
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


CONTOSO_CORBA_IDL = """module ContosoSupport {
  interface CustomerService {
    string getCustomer(in string sentinel);
    string registerCustomer(in string sentinel);
    string updateEmail(in string sentinel);
    string getLoyaltyBalance(in string sentinel);
    string redeemPoints(in string sentinel);
  };

  interface OrderService {
    string createOrder(in string sentinel);
    string getOrder(in string sentinel);
    string cancelOrder(in string sentinel);
    string processRefund(in string sentinel);
  };

  interface SupportService {
    string submitTicket(in string sentinel);
    string escalateTicket(in string sentinel);
    string closeTicket(in string sentinel);
  };
};
"""

INTERFACE_FOR_OBJECT = {
    "ICustomerService": "CustomerService",
    "IOrderService": "OrderService",
    "ISupportService": "SupportService",
}


def corba_runtime_available() -> bool:
    try:
        from omniORB import CORBA  # type: ignore  # noqa: F401
    except Exception:
        return False
    return shutil.which("omniidl") is not None


class CorbaRuntimeUnavailable(RuntimeError):
    pass


class CorbaRuntimeError(RuntimeError):
    pass


@dataclass
class CorbaRuntime:
    workdir: Path
    iors: dict[str, str]
    server_log: list[str] = field(default_factory=list)
    version: str = "controlled-corba-orb-runtime-v1"


_runtime_lock = threading.Lock()
_runtime: CorbaRuntime | None = None


def _prepare_modules(workdir: Path) -> tuple[Any, Any]:
    idl_path = workdir / "contoso_support.idl"
    idl_path.write_text(CONTOSO_CORBA_IDL, encoding="utf-8")
    generated_marker = workdir / "ContosoSupport__POA"
    if not generated_marker.exists():
        subprocess.run(
            ["omniidl", "-bpython", str(idl_path)],
            cwd=str(workdir),
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
    if str(workdir) not in sys.path:
        sys.path.insert(0, str(workdir))
    importlib.import_module("contoso_support_idl")
    contoso = importlib.import_module("ContosoSupport")
    contoso_poa = importlib.import_module("ContosoSupport__POA")
    return contoso, contoso_poa


def _service_result(service: str, operation: str, sentinel: str) -> str:
    return f"corba_orb:{service}.{operation}: {sentinel}"


def _servant_class(poa_module: Any, class_name: str, service_name: str) -> type:
    base = getattr(poa_module, class_name)
    methods = {}
    for operation in (
        "getCustomer",
        "registerCustomer",
        "updateEmail",
        "getLoyaltyBalance",
        "redeemPoints",
        "createOrder",
        "getOrder",
        "cancelOrder",
        "processRefund",
        "submitTicket",
        "escalateTicket",
        "closeTicket",
    ):
        methods[operation] = lambda self, sentinel, op=operation: _service_result(service_name, op, sentinel)
    return type(f"{class_name}Servant", (base,), methods)


def ensure_corba_runtime() -> CorbaRuntime:
    global _runtime
    with _runtime_lock:
        if _runtime is not None:
            return _runtime
        if not corba_runtime_available():
            raise CorbaRuntimeUnavailable("OmniORB/omniidl is not available")

        from omniORB import CORBA, PortableServer  # type: ignore

        workdir = Path(tempfile.mkdtemp(prefix="mcp-corba-orb-"))
        contoso, contoso_poa = _prepare_modules(workdir)
        orb = CORBA.ORB_init(["mcp-corba-runtime", "-ORBendPoint", "giop:tcp:127.0.0.1:0"], CORBA.ORB_ID)
        poa = orb.resolve_initial_references("RootPOA")
        poa._get_the_POAManager().activate()

        iors: dict[str, str] = {}
        service_map = {
            "ICustomerService": ("CustomerService", getattr(contoso, "CustomerService"), getattr(contoso_poa, "CustomerService")),
            "IOrderService": ("OrderService", getattr(contoso, "OrderService"), getattr(contoso_poa, "OrderService")),
            "ISupportService": ("SupportService", getattr(contoso, "SupportService"), getattr(contoso_poa, "SupportService")),
        }
        server_log: list[str] = []
        for object_key, (service_name, stub_type, poa_type) in service_map.items():
            servant_type = _servant_class(contoso_poa, service_name, service_name)
            if not issubclass(servant_type, poa_type):
                raise CorbaRuntimeError(f"generated servant type mismatch for {service_name}")
            servant = servant_type()
            ref = servant._this()
            narrowed = ref._narrow(stub_type)
            if narrowed is None:
                raise CorbaRuntimeError(f"failed to narrow servant for {service_name}")
            ior = orb.object_to_string(narrowed)
            iors[object_key] = ior
            server_log.append(f"registered {object_key} service={service_name} ior_prefix={ior[:32]}")

        thread = threading.Thread(target=orb.run, name="controlled-corba-orb", daemon=True)
        thread.start()
        time.sleep(0.05)

        runtime = CorbaRuntime(workdir=workdir, iors=iors, server_log=server_log)
        runtime._orb = orb  # type: ignore[attr-defined]
        runtime._contoso = contoso  # type: ignore[attr-defined]
        _runtime = runtime
        return runtime


def corba_orb_invoke(interface_name: str, operation: str, sentinel: str) -> dict[str, Any]:
    runtime = ensure_corba_runtime()
    object_key = interface_name if interface_name in INTERFACE_FOR_OBJECT else f"I{interface_name}"
    service_name = INTERFACE_FOR_OBJECT.get(object_key)
    if service_name is None or object_key not in runtime.iors:
        raise CorbaRuntimeError(f"unknown CORBA object: {interface_name}")
    from omniORB import CORBA  # type: ignore

    orb = runtime._orb  # type: ignore[attr-defined]
    contoso = runtime._contoso  # type: ignore[attr-defined]
    obj = orb.string_to_object(runtime.iors[object_key])
    narrowed = obj._narrow(getattr(contoso, service_name))
    if narrowed is None:
        raise CorbaRuntimeError(f"failed to narrow object reference for {service_name}")
    if not hasattr(narrowed, operation):
        raise CorbaRuntimeError(f"unknown CORBA operation: {service_name}.{operation}")
    result = getattr(narrowed, operation)(sentinel)
    return {
        "runtime_mode": "corba_orb_runtime",
        "wire_protocol": "IIOP",
        "orb": "OmniORB",
        "idl_file": str(runtime.workdir / "contoso_support.idl"),
        "interface": interface_name,
        "service": service_name,
        "operation": operation,
        "object_reference": runtime.iors[object_key],
        "server_log": runtime.server_log,
        "client_result": result,
    }
