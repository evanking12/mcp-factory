"""Deterministic legacy-provider adapters for sponsor demo tool execution.

These endpoints are intentionally small and predictable. They do not claim to
be production CORBA/RPC/JNDI infrastructure; they provide live backing services
for the generated MCP tools so GPT proof cases observe a real tool result.
"""

from __future__ import annotations

import json
import re
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response

router = APIRouter(prefix="/api/legacy", tags=["legacy-provider"])

PROVIDER_VERSION = "legacy-live-green-v1"
PROVIDERS = {
    "rest": "OpenAPI/REST deterministic Contoso adapter",
    "jsonrpc": "JSON-RPC 2.0 deterministic Contoso adapter",
    "soap": "SOAP/WSDL deterministic Contoso adapter",
    "sql": "SQL source deterministic Contoso adapter",
    "corba": "CORBA IDL deterministic adapter",
    "rpc": "RPC IDL deterministic adapter",
    "jndi": "JNDI lookup deterministic adapter",
}


def _collect_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        strings: list[str] = []
        for child in value.values():
            strings.extend(_collect_strings(child))
        return strings
    if isinstance(value, (list, tuple)):
        strings = []
        for child in value:
            strings.extend(_collect_strings(child))
        return strings
    return []


def extract_sentinel(value: Any) -> str:
    """Return the strongest deterministic sentinel-like string from a payload."""
    strings = [item for item in _collect_strings(value) if item]
    for item in strings:
        if "MCP_FACTORY" in item:
            return item
    for item in strings:
        if "sentinel" in item.lower():
            return item
    return strings[0] if strings else "legacy-provider-ok"


def build_legacy_result(provider: str, operation: str, args: Any) -> dict[str, Any]:
    sentinel = extract_sentinel(args)
    return {
        "provider": provider,
        "operation": operation,
        "version": PROVIDER_VERSION,
        "sentinel": sentinel,
        "result": f"{provider}:{operation}: {sentinel}",
        "args": args if isinstance(args, (dict, list)) else {"value": args},
    }


async def _json_or_query(request: Request, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = dict(request.query_params)
    if request.method in {"POST", "PUT", "PATCH"}:
        body = await request.body()
        if body:
            try:
                parsed = json.loads(body.decode("utf-8"))
                if isinstance(parsed, dict):
                    payload.update(parsed)
                else:
                    payload["body"] = parsed
            except Exception:
                payload["body"] = body.decode("utf-8", errors="replace")
    if extra:
        payload.update(extra)
    return payload


@router.get("/health")
def legacy_health() -> dict[str, Any]:
    return {
        "status": "ok",
        "version": PROVIDER_VERSION,
        "enabled_providers": sorted(PROVIDERS),
        "providers": PROVIDERS,
    }


@router.api_route("/rest/{operation:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def rest_provider(operation: str, request: Request) -> JSONResponse:
    payload = await _json_or_query(request, {"path": f"/{operation}"})
    return JSONResponse(build_legacy_result("rest", operation or "root", payload))


@router.post("/jsonrpc")
async def jsonrpc_provider(request: Request) -> JSONResponse:
    payload = await request.json()
    method = str(payload.get("method") or "jsonrpc_method")
    params = payload.get("params")
    result = build_legacy_result("jsonrpc", method, params if params is not None else payload)
    return JSONResponse({"jsonrpc": "2.0", "id": payload.get("id", 1), "result": result})


@router.post("/soap")
async def soap_provider(request: Request) -> Response:
    body = (await request.body()).decode("utf-8", errors="replace")
    action = request.headers.get("SOAPAction", "").strip('"') or "SoapOperation"
    sentinel = extract_sentinel(body)
    # Fall back to the first operation-shaped tag when SOAPAction is absent.
    if action == "SoapOperation":
        match = re.search(r"<(?:\w+:)?([A-Za-z_][\w.-]*)\b", body)
        if match:
            action = match.group(1)
    envelope = (
        '<?xml version="1.0"?>'
        '<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">'
        "<soapenv:Body>"
        f"<LegacyProviderResult><provider>soap</provider><operation>{action}</operation>"
        f"<sentinel>{sentinel}</sentinel><result>soap:{action}: {sentinel}</result>"
        "</LegacyProviderResult>"
        "</soapenv:Body>"
        "</soapenv:Envelope>"
    )
    return Response(content=envelope, media_type="text/xml")


@router.post("/sql/{operation}")
async def sql_provider(operation: str, request: Request) -> JSONResponse:
    payload = await _json_or_query(request, {"operation": operation})
    return JSONResponse(build_legacy_result("sql", operation, payload))


@router.post("/corba/{operation}")
async def corba_provider(operation: str, request: Request) -> JSONResponse:
    payload = await _json_or_query(request, {"operation": operation})
    return JSONResponse(build_legacy_result("corba", operation, payload))


@router.post("/rpc/{procedure}")
async def rpc_provider(procedure: str, request: Request) -> JSONResponse:
    payload = await _json_or_query(request, {"procedure": procedure})
    return JSONResponse(build_legacy_result("rpc", procedure, payload))


@router.post("/jndi/lookup")
async def jndi_provider(request: Request) -> JSONResponse:
    payload = await _json_or_query(request)
    lookup = str(payload.get("lookup_name") or payload.get("name") or payload.get("binding") or "lookup")
    return JSONResponse(build_legacy_result("jndi", lookup, payload))
