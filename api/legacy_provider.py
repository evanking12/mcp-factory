"""Deterministic legacy-provider runtimes for sponsor demo tool execution.

These endpoints are intentionally small and predictable. They provide live,
runtime-backed or runtime-shaped backing services for generated MCP tools while
avoiding claims that the capstone performs generalized CORBA estate migration,
arbitrary enterprise MSRPC estate support, enterprise directory migration, or
remote DCOM infrastructure.
"""

from __future__ import annotations

import json
import re
import sqlite3
import xmlrpc.client
import hashlib
from typing import Any
from xml.etree import ElementTree as ET

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response

from api.corba_runtime import (
    CONTOSO_CORBA_IDL,
    CorbaRuntimeUnavailable,
    corba_orb_enabled,
    corba_orb_invoke,
)
from api.ldap_runtime import (
    BASE_DN,
    LDAP_BINDINGS as JNDI_BINDINGS,
    DEFAULT_BIND_DN,
    ldap_bind,
    ldap_config_ldif,
    ldap_entry as _ldap_entry,
    ldap_lookup,
    ldap_search,
)
from api.msrpc_runtime import (
    CONTOSO_MSRPC_IDL,
    MsrpcRuntimeUnavailable,
    msrpc_invoke,
    msrpc_runtime_enabled,
)

router = APIRouter(prefix="/api/legacy", tags=["legacy-provider"])

PROVIDER_VERSION = "runtime-proof-expansion-v1"
PROVIDERS = {
    "rest": "OpenAPI/REST validated Contoso runtime",
    "jsonrpc": "JSON-RPC 2.0 hosted Contoso runtime",
    "soap": "SOAP/WSDL envelope-validating Contoso runtime",
    "sql": "SQLite-backed Contoso runtime",
    "corba": "CORBA ORB/IIOP Contoso runtime" if corba_orb_enabled() else "CORBA IDL object-registry runtime-shaped provider",
    "rpc": "DCE/RPC-compatible Contoso runtime" if msrpc_runtime_enabled() else "XML-RPC hosted Contoso runtime",
    "jndi": "LDAPv3-compatible JNDI binding runtime",
}
PROVIDER_MODES = {
    "rest": "validated_runtime",
    "jsonrpc": "real_runtime",
    "soap": "real_runtime",
    "sql": "real_runtime",
    "corba": "corba_orb_runtime" if corba_orb_enabled() else "corba_idl_runtime",
    "rpc": "msrpc_runtime" if msrpc_runtime_enabled() else "xmlrpc_runtime",
    "jndi": "ldap_runtime",
}

JSONRPC_METHODS = {
    "jsonrpc_method",
    "getCustomer",
    "getCustomerProfile",
    "lookupCustomer",
    "lookupOrderStatus",
    "createSupportTicket",
    "createTicket",
}
SOAP_OPERATIONS = {
    "GetCustomer",
    "CreateOrder",
    "SubmitTicket",
    "GetOrderStatus",
    "ProcessRefund",
}
REST_ROUTES = [
    ("GET", re.compile(r"^customers/[^/]+$")),
    ("POST", re.compile(r"^customers$")),
    ("POST", re.compile(r"^orders$")),
    ("GET", re.compile(r"^orders/[^/]+$")),
    ("POST", re.compile(r"^orders/[^/]+/cancel$")),
    ("POST", re.compile(r"^orders/[^/]+/refund$")),
    ("POST", re.compile(r"^tickets$")),
    ("GET", re.compile(r"^customers/[^/]+/loyalty$")),
]
RPC_METHODS = {
    "RpcCreateTicket",
    "RpcGetTicketStatus",
    "RpcCloseTicket",
}
CORBA_OBJECTS = {
    "ICustomerService": {
        "repository_id": "IDL:contoso.com/CustomerService/ICustomerService:1.0",
        "object_ref": "corbaloc:iiop:legacy-provider/Contoso/ICustomerService",
        "operations": {"getCustomer", "registerCustomer", "updateEmail", "getLoyaltyBalance", "redeemPoints"},
    },
    "IOrderService": {
        "repository_id": "IDL:contoso.com/CustomerService/IOrderService:1.0",
        "object_ref": "corbaloc:iiop:legacy-provider/Contoso/IOrderService",
        "operations": {"createOrder", "getOrder", "cancelOrder", "processRefund"},
    },
    "ISupportService": {
        "repository_id": "IDL:contoso.com/CustomerService/ISupportService:1.0",
        "object_ref": "corbaloc:iiop:legacy-provider/Contoso/ISupportService",
        "operations": {"submitTicket", "escalateTicket", "closeTicket"},
    },
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


def _lookup_payload_value(value: Any, *names: str) -> Any:
    if not isinstance(value, dict):
        return None
    candidates: list[dict[str, Any]] = []
    args = value.get("args")
    if isinstance(args, dict):
        candidates.append(args)
    candidates.append(value)
    normalized_names = {name for name in names}
    normalized_names.update(name.replace("_", "") for name in names)
    normalized_names.update(name.lower() for name in names)
    normalized_names.update(name.lstrip("@") for name in names)
    for candidate in candidates:
        for key, child in candidate.items():
            key_variants = {str(key), str(key).replace("_", ""), str(key).lower(), str(key).lstrip("@")}
            if normalized_names & key_variants:
                return child
    return None


def _nonempty(value: Any, default: str) -> str:
    text = "" if value is None else str(value).strip()
    return text or default


def build_demo_result(provider: str, operation: str, args: Any, sentinel: str | None = None) -> dict[str, Any]:
    """Return a sponsor-readable Contoso business result with proof fields.

    Raw protocol details still live in transport-specific fields and CI artifacts.
    This payload is optimized for the UI/video path: domain-shaped first,
    evidence fields always present.
    """
    proof_sentinel = sentinel or extract_sentinel(args)
    op = operation.split("/")[-1]
    op_lower = op.lower()
    customer_id = _nonempty(
        _lookup_payload_value(args, "customerId", "customer_id", "id"),
        proof_sentinel,
    )
    order_id = _nonempty(_lookup_payload_value(args, "orderId", "order_id"), "1001")
    subject = _nonempty(_lookup_payload_value(args, "subject"), "Customer service demo request")
    lookup_name = _nonempty(_lookup_payload_value(args, "name", "lookup_name", "binding"), "jdbc/ContosoCustomerDB")

    base = {
        "proof_sentinel": proof_sentinel,
        "provider": provider,
        "operation": op,
        "runtime_mode": PROVIDER_MODES.get(provider, "adapter_backed"),
    }
    if "ticket" in op_lower or "support" in op_lower or "rpc" in op_lower or op_lower in {"submitticket", "escalateticket", "closeticket"}:
        ticket_hash = hashlib.sha1(f"{provider}:{op}:{proof_sentinel}".encode("utf-8")).hexdigest()[:5].upper()
        return {
            **base,
            "kind": "support_ticket",
            "ticketId": f"TICKET-{ticket_hash}",
            "customerId": customer_id,
            "subject": subject,
            "status": "open" if "close" not in op_lower else "closed",
            "priority": "normal",
            "summary": f"Created Contoso support ticket for {customer_id}",
        }
    if "order" in op_lower or "refund" in op_lower or "cancel" in op_lower:
        status = "refund_requested" if "refund" in op_lower else "cancelled" if "cancel" in op_lower else "found"
        return {
            **base,
            "kind": "order",
            "orderId": order_id,
            "customerId": customer_id,
            "status": status,
            "total": 128.50,
            "summary": f"Order {order_id} status is {status}",
        }
    if "loyalty" in op_lower or "redeem" in op_lower:
        return {
            **base,
            "kind": "loyalty",
            "customerId": customer_id,
            "tier": "Gold",
            "points": 4200,
            "status": "available",
            "summary": f"Customer {customer_id} has 4200 loyalty points",
        }
    if provider == "jndi":
        return {
            **base,
            "kind": "directory_binding",
            "lookupName": lookup_name,
            "bindingType": "javax.sql.DataSource" if lookup_name.startswith("jdbc/") else "java.naming.Reference",
            "status": "found",
            "summary": f"Resolved JNDI binding {lookup_name}",
        }
    if "customer" in op_lower or provider in {"jsonrpc", "soap", "rest", "corba"}:
        return {
            **base,
            "kind": "customer",
            "customerId": customer_id,
            "customerName": "Contoso Demo Customer",
            "supportTier": "Gold",
            "status": "found",
            "recommendedAction": "Display account summary and offer support-ticket creation",
            "summary": f"Found Contoso customer {customer_id}",
        }
    return {
        **base,
        "kind": "legacy_operation",
        "status": "completed",
        "summary": f"Executed {provider} operation {op}",
    }


def build_legacy_result(provider: str, operation: str, args: Any) -> dict[str, Any]:
    sentinel = extract_sentinel(args)
    demo_result = build_demo_result(provider, operation, args, sentinel)
    return {
        "provider": provider,
        "operation": operation,
        "version": PROVIDER_VERSION,
        "runtime_mode": PROVIDER_MODES.get(provider, "adapter_backed"),
        "sentinel": sentinel,
        "status": demo_result.get("status", "completed"),
        "business_result": demo_result,
        "result": demo_result["summary"],
        "proof": {
            "sentinel": sentinel,
            "provider": provider,
            "runtime_mode": PROVIDER_MODES.get(provider, "adapter_backed"),
            "operation": operation,
        },
        "args": args if isinstance(args, (dict, list)) else {"value": args},
    }


def _xml_escape(value: Any) -> str:
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].split(":")[-1]


def _soap_params(operation_node: ET.Element) -> dict[str, str]:
    return {_local_name(child.tag): (child.text or "") for child in list(operation_node)}


def _safe_xml_name(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(name)).strip("_")
    if not cleaned or not re.match(r"^[A-Za-z_]", cleaned):
        cleaned = f"field_{cleaned or 'value'}"
    return cleaned


def _xml_fragment(name: str, value: Any) -> str:
    safe_name = _safe_xml_name(name)
    if isinstance(value, dict):
        inner = "".join(_xml_fragment(k, v) for k, v in value.items())
        return f"<{safe_name}>{inner}</{safe_name}>"
    if isinstance(value, list):
        item_name = safe_name[:-1] if safe_name.endswith("s") else "item"
        inner = "".join(_xml_fragment(item_name, item) for item in value)
        return f"<{safe_name}>{inner}</{safe_name}>"
    if isinstance(value, bool):
        text = "true" if value else "false"
    else:
        text = "" if value is None else str(value)
    return f"<{safe_name}>{_xml_escape(text)}</{safe_name}>"


def _soap_fault(message: str, *, status_code: int = 400) -> Response:
    envelope = (
        '<?xml version="1.0"?>'
        '<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">'
        "<soapenv:Body><soapenv:Fault>"
        "<faultcode>soapenv:Client</faultcode>"
        f"<faultstring>{_xml_escape(message)}</faultstring>"
        "</soapenv:Fault></soapenv:Body></soapenv:Envelope>"
    )
    return Response(content=envelope, media_type="text/xml", status_code=status_code)


def _sqlite_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE Customers (
            id INTEGER PRIMARY KEY,
            name TEXT,
            email TEXT,
            phone TEXT,
            tier TEXT,
            loyalty_points INTEGER,
            created_at TEXT
        );
        CREATE TABLE Orders (
            id INTEGER PRIMARY KEY,
            customer_id INTEGER,
            status TEXT,
            total REAL,
            shipping_address TEXT,
            coupon_code TEXT,
            created_at TEXT
        );
        CREATE TABLE Tickets (
            id INTEGER PRIMARY KEY,
            customer_id INTEGER,
            subject TEXT,
            description TEXT,
            priority TEXT,
            status TEXT,
            created_at TEXT
        );
        CREATE TABLE OrderLineItems (
            order_id INTEGER,
            product_sku TEXT,
            quantity INTEGER,
            unit_price REAL
        );
        INSERT INTO Customers VALUES
            (1, 'Ada Lovelace', 'ada@contoso.example', '555-0101', 'Gold', 4200, '2026-01-10'),
            (2, 'Grace Hopper', 'grace@contoso.example', '555-0102', 'Platinum', 9300, '2026-01-11');
        INSERT INTO Orders VALUES
            (1001, 1, 'Shipped', 128.50, '1 Contoso Way', 'SPRING', '2026-02-01'),
            (1002, 1, 'Pending', 42.00, '1 Contoso Way', NULL, '2026-02-12');
        INSERT INTO Tickets VALUES
            (501, 1, 'Existing ticket', 'Deterministic fixture', 'Normal', 'Open', '2026-03-01');
        INSERT INTO OrderLineItems VALUES
            (1001, 'SKU-100', 2, 50.00),
            (1001, 'SKU-200', 1, 28.50);
        """
    )
    return conn


def _rows(cursor: sqlite3.Cursor) -> list[dict[str, Any]]:
    return [dict(row) for row in cursor.fetchall()]


def _arg(payload: dict[str, Any], name: str, default: Any = None) -> Any:
    args = payload.get("args")
    if isinstance(args, dict):
        for key in (name, name.lstrip("@"), name.replace("_", ""), name.lower()):
            if key in args:
                return args[key]
    for key in (name, name.lstrip("@"), name.replace("_", ""), name.lower()):
        if key in payload:
            return payload[key]
    return default


def _int_arg(payload: dict[str, Any], name: str, default: int) -> int:
    value = _arg(payload, name, default)
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _float_arg(payload: dict[str, Any], name: str, default: float) -> float:
    value = _arg(payload, name, default)
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _jndi_lookup_name(payload: dict[str, Any]) -> str:
    raw_lookup = payload.get("lookup_name") or payload.get("name") or payload.get("binding") or "lookup"
    if isinstance(raw_lookup, list):
        raw_lookup = raw_lookup[0] if raw_lookup else "lookup"
    return str(raw_lookup)


def _corba_match_operation(raw_operation: str) -> tuple[str, str, dict[str, Any]] | None:
    operation = raw_operation.split("/")[-1]
    for interface_name, obj in CORBA_OBJECTS.items():
        for candidate in obj["operations"]:
            if operation == candidate or operation == f"{interface_name}_{candidate}" or operation.endswith(f"_{candidate}"):
                return interface_name, candidate, obj
    return None


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
        "provider_modes": PROVIDER_MODES,
        "runtime_backed": sorted(k for k, v in PROVIDER_MODES.items() if v in {"real_runtime", "validated_runtime", "lookup_runtime", "ldap_runtime", "xmlrpc_runtime", "msrpc_runtime", "corba_idl_runtime", "corba_orb_runtime"}),
        "adapter_backed": sorted(k for k, v in PROVIDER_MODES.items() if v == "adapter_backed"),
    }


@router.api_route("/rest/{operation:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def rest_provider(operation: str, request: Request) -> JSONResponse:
    normalized = operation.strip("/")
    method = request.method.upper()
    if not any(route_method == method and pattern.match(normalized) for route_method, pattern in REST_ROUTES):
        return JSONResponse(
            {
                "provider": "rest",
                "runtime_mode": PROVIDER_MODES["rest"],
                "error": f"OpenAPI route not declared for {method} /{normalized}",
                "allowed_route_count": len(REST_ROUTES),
            },
            status_code=404,
        )
    payload = await _json_or_query(request, {"path": f"/{operation}"})
    return JSONResponse(build_legacy_result("rest", operation or "root", payload))


@router.post("/jsonrpc")
async def jsonrpc_provider(request: Request) -> JSONResponse:
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse(
            {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": "Parse error"},
            },
            status_code=400,
        )
    if not isinstance(payload, dict) or payload.get("jsonrpc") != "2.0":
        request_id = payload.get("id") if isinstance(payload, dict) else None
        return JSONResponse(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32600, "message": "Invalid Request"},
            },
            status_code=400,
        )
    method = str(payload.get("method") or "jsonrpc_method")
    if method not in JSONRPC_METHODS:
        return JSONResponse(
            {
                "jsonrpc": "2.0",
                "id": payload.get("id"),
                "error": {"code": -32601, "message": "Method not found"},
            },
            status_code=404,
        )
    params = payload.get("params")
    result = build_legacy_result("jsonrpc", method, params if params is not None else payload)
    return JSONResponse({"jsonrpc": "2.0", "id": payload.get("id", 1), "result": result})


@router.post("/soap")
async def soap_provider(request: Request) -> Response:
    body = (await request.body()).decode("utf-8", errors="replace")
    action = request.headers.get("SOAPAction", "").strip('"') or "SoapOperation"
    try:
        root = ET.fromstring(body)
    except ET.ParseError as exc:
        return _soap_fault(f"Invalid SOAP XML: {exc}")
    if _local_name(root.tag) != "Envelope":
        return _soap_fault("SOAP Envelope element is required")
    body_node = next((child for child in root.iter() if _local_name(child.tag) == "Body"), None)
    if body_node is None:
        return _soap_fault("SOAP Body element is required")
    operation_node = next((child for child in list(body_node) if _local_name(child.tag) != "Fault"), None)
    if operation_node is None:
        return _soap_fault("SOAP operation element is required")
    if action == "SoapOperation":
        action = _local_name(operation_node.tag)
    action = action.split("/")[-1]
    if action not in SOAP_OPERATIONS:
        return _soap_fault(f"Unknown SOAP operation: {action}", status_code=404)
    params = _soap_params(operation_node)
    sentinel = extract_sentinel(params if params else body)
    payload = {"args": params, **params}
    business_result = build_demo_result("soap", action, payload, sentinel)
    envelope = (
        '<?xml version="1.0"?>'
        '<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">'
        "<soapenv:Body>"
        f"<{action}Response><LegacyProviderResult><provider>soap</provider>"
        f"<runtimeMode>{PROVIDER_MODES['soap']}</runtimeMode><operation>{_xml_escape(action)}</operation>"
        f"<sentinel>{_xml_escape(sentinel)}</sentinel><status>{_xml_escape(str(business_result.get('status', 'completed')))}</status>"
        f"{_xml_fragment('businessResult', business_result)}"
        f"<result>{_xml_escape(str(business_result['summary']))}</result>"
        "<transportProof><soapEnvelopeValidated>true</soapEnvelopeValidated><soapBodyValidated>true</soapBodyValidated></transportProof>"
        "</LegacyProviderResult>"
        f"</{action}Response>"
        "</soapenv:Body>"
        "</soapenv:Envelope>"
    )
    return Response(content=envelope, media_type="text/xml")


@router.post("/sql/{operation}")
async def sql_provider(operation: str, request: Request) -> JSONResponse:
    payload = await _json_or_query(request, {"operation": operation})
    sentinel = extract_sentinel(payload)
    with _sqlite_connection() as conn:
        op = operation.lower()
        if op == "getcustomerinfo":
            customer_id = _int_arg(payload, "customer_id", _int_arg(payload, "customerId", 1))
            customer = _rows(conn.execute("SELECT * FROM Customers WHERE id = ?", (customer_id,)))
            orders = _rows(conn.execute("SELECT id, status, total, created_at FROM Orders WHERE customer_id = ? ORDER BY created_at DESC", (customer_id,)))
            result: Any = {"customer": customer, "orders": orders}
        elif op == "createsupportticket":
            customer_id = _int_arg(payload, "customer_id", _int_arg(payload, "customerId", 1))
            subject = str(_arg(payload, "subject", "Sponsor proof ticket"))
            description = str(_arg(payload, "description", sentinel))
            priority = str(_arg(payload, "priority", "Normal"))
            cur = conn.execute(
                "INSERT INTO Tickets (customer_id, subject, description, priority, status, created_at) VALUES (?, ?, ?, ?, 'Open', '2026-04-17')",
                (customer_id, subject, description, priority),
            )
            result = {"ticket_id": cur.lastrowid, "status": "Open"}
        elif op == "createorder":
            customer_id = _int_arg(payload, "customer_id", _int_arg(payload, "customerId", 1))
            address = str(_arg(payload, "shipping_address", _arg(payload, "shippingAddress", "1 Contoso Way")))
            coupon = _arg(payload, "coupon_code", _arg(payload, "couponCode", None))
            cur = conn.execute(
                "INSERT INTO Orders (customer_id, status, total, shipping_address, coupon_code, created_at) VALUES (?, 'Pending', 64.25, ?, ?, '2026-04-17')",
                (customer_id, address, coupon),
            )
            result = {"order_id": cur.lastrowid, "status": "Pending"}
        elif op == "getorderdetails":
            order_id = _int_arg(payload, "order_id", _int_arg(payload, "orderId", 1001))
            order = _rows(conn.execute("SELECT * FROM Orders WHERE id = ?", (order_id,)))
            line_items = _rows(conn.execute("SELECT * FROM OrderLineItems WHERE order_id = ?", (order_id,)))
            result = {"order": order, "line_items": line_items}
        elif op == "calculatediscount":
            order_total = _float_arg(payload, "order_total", _float_arg(payload, "orderTotal", 100.0))
            loyalty_years = _int_arg(payload, "loyalty_years", _int_arg(payload, "loyaltyYears", 3))
            rate = 0.15 if loyalty_years > 5 else 0.10 if loyalty_years > 2 else 0.05
            result = {"discount": round(order_total * rate, 2), "rate": rate}
        elif op == "customerordersummary":
            result = _rows(conn.execute(
                "SELECT c.id, c.name, c.email, c.tier, COUNT(o.id) AS total_orders, "
                "COALESCE(SUM(o.total), 0) AS lifetime_value, MAX(o.created_at) AS last_order_date "
                "FROM Customers c LEFT JOIN Orders o ON c.id = o.customer_id "
                "GROUP BY c.id, c.name, c.email, c.tier"
            ))
        else:
            result = build_legacy_result("sql", operation, payload)
    return JSONResponse({
        "provider": "sql",
        "operation": operation,
        "version": PROVIDER_VERSION,
        "runtime_mode": PROVIDER_MODES["sql"],
        "database": "sqlite",
        "sentinel": sentinel,
        "business_result": build_demo_result("sql", operation, payload, sentinel),
        "result": result,
        "proof": f"sql:{operation}: {sentinel}",
    })


@router.post("/corba/{operation}")
async def corba_provider(operation: str, request: Request) -> JSONResponse:
    payload = await _json_or_query(request, {"operation": operation})
    matched = _corba_match_operation(operation)
    if matched is None:
        return JSONResponse(
            {
                "provider": "corba",
                "runtime_mode": PROVIDER_MODES["corba"],
                "error": f"CORBA IDL operation not declared: {operation}",
                "allowed_interfaces": sorted(CORBA_OBJECTS),
            },
            status_code=404,
        )
    interface_name, method_name, obj = matched
    result = build_legacy_result("corba", method_name, payload)
    if PROVIDER_MODES["corba"] == "corba_orb_runtime":
        try:
            orb_result = corba_orb_invoke(interface_name, method_name, extract_sentinel(payload))
        except CorbaRuntimeUnavailable as exc:
            return JSONResponse(
                {
                    "provider": "corba",
                    "runtime_mode": "corba_orb_runtime",
                    "error": str(exc),
                    "notes": "CORBA ORB runtime is required for this stretch proof and was not downgraded.",
                },
                status_code=503,
            )
        result.update({
            "runtime_mode": "corba_orb_runtime",
            "idl_module": "ContosoSupport",
            "interface": interface_name,
            "repository_id": obj["repository_id"],
            "object_ref": orb_result["object_reference"],
            "allowed_operation": True,
            "corba_request": {
                "object_key": interface_name,
                "operation": method_name,
                "repository_id": obj["repository_id"],
                "args": payload.get("args", payload),
            },
            "corba_response": {
                "reply_status": "NO_EXCEPTION",
                "operation": method_name,
                "result": orb_result["client_result"],
            },
            "orb_invocation": orb_result,
        })
        return JSONResponse(result)
    result.update({
        "runtime_mode": PROVIDER_MODES["corba"],
        "idl_module": "Contoso.CustomerService",
        "interface": interface_name,
        "repository_id": obj["repository_id"],
        "object_ref": obj["object_ref"],
        "allowed_operation": True,
        "corba_request": {
            "object_key": interface_name,
            "operation": method_name,
            "repository_id": obj["repository_id"],
            "args": payload.get("args", payload),
        },
        "corba_response": {
            "reply_status": "NO_EXCEPTION",
            "operation": method_name,
            "result": result["result"],
        },
    })
    return JSONResponse(result)


@router.get("/corba/idl")
def corba_idl_provider() -> Response:
    return Response(content=CONTOSO_CORBA_IDL, media_type="text/plain")


@router.post("/rpc/{procedure}")
async def rpc_provider(procedure: str, request: Request) -> Response:
    body = await request.body()
    parsed_args: Any = {}
    method_name = procedure
    if body.strip().startswith(b"<"):
        try:
            params, parsed_method = xmlrpc.client.loads(body)
            method_name = parsed_method or procedure
            parsed_args = list(params)
        except Exception as exc:
            fault = xmlrpc.client.Fault(400, f"Invalid XML-RPC request: {exc}")
            return Response(content=xmlrpc.client.dumps(fault), media_type="text/xml", status_code=400)
    else:
        payload = await _json_or_query(request, {"procedure": procedure})
        parsed_args = payload.get("args", payload)
    if method_name not in RPC_METHODS:
        fault = xmlrpc.client.Fault(404, f"RPC method not declared in IDL: {method_name}")
        return Response(content=xmlrpc.client.dumps(fault), media_type="text/xml", status_code=200)
    if PROVIDER_MODES["rpc"] == "msrpc_runtime":
        try:
            msrpc_result = msrpc_invoke(method_name, extract_sentinel(parsed_args))
        except MsrpcRuntimeUnavailable as exc:
            return Response(
                content=json.dumps({
                    "provider": "rpc",
                    "runtime_mode": "msrpc_runtime",
                    "error": str(exc),
                    "notes": "MSRPC runtime is required for this stretch proof and was not downgraded.",
                }),
                media_type="application/json",
                status_code=503,
            )
        result = build_legacy_result("rpc", method_name, parsed_args)
        result.update({
            "runtime_mode": "msrpc_runtime",
            "transport": "dcerpc",
            "idl_interface": "ContosoRpcSupport",
            "declared_method": method_name,
            "msrpc_invocation": msrpc_result,
            "sentinel": extract_sentinel(parsed_args),
            "result": msrpc_result["client_result"],
        })
        return Response(content=json.dumps(result), media_type="application/json")
    result = build_legacy_result("rpc", method_name, parsed_args)
    result.update({
        "runtime_mode": PROVIDER_MODES["rpc"],
        "transport": "xmlrpc",
        "idl_interface": "ContosoRpcSupport",
        "declared_method": method_name,
    })
    return Response(content=xmlrpc.client.dumps((result,), methodresponse=True), media_type="text/xml")


@router.get("/rpc/idl")
def rpc_idl_provider() -> Response:
    return Response(content=CONTOSO_MSRPC_IDL, media_type="text/plain")


@router.post("/jndi/bind")
async def jndi_bind_provider(request: Request) -> JSONResponse:
    payload = await _json_or_query(request)
    principal = str(payload.get("principal") or DEFAULT_BIND_DN)
    bind = ldap_bind(principal, str(payload.get("credential") or "contoso-demo"))
    ok = bool(bind.get("bound"))
    return JSONResponse({
        "provider": "jndi",
        "runtime_mode": PROVIDER_MODES["jndi"],
        "operation": "bind",
        "protocol": "ldap",
        "wire_protocol": "ldapv3",
        "principal": principal,
        "bound": ok,
        "ldap_result": bind,
        "sentinel": extract_sentinel(payload),
        "business_result": {
            "kind": "directory_bind",
            "provider": "jndi",
            "runtime_mode": PROVIDER_MODES["jndi"],
            "principal": principal,
            "status": "bound" if ok else "denied",
            "proof_sentinel": extract_sentinel(payload),
            "summary": f"LDAP bind {'succeeded' if ok else 'failed'} for {principal}",
        },
    }, status_code=200 if ok else 401)


@router.post("/jndi/search")
async def jndi_search_provider(request: Request) -> JSONResponse:
    payload = await _json_or_query(request)
    query = str(payload.get("filter") or payload.get("query") or "")
    search = ldap_search(query, base_dn=str(payload.get("base_dn") or BASE_DN))
    return JSONResponse({
        "provider": "jndi",
        "runtime_mode": PROVIDER_MODES["jndi"],
        "operation": "search",
        "protocol": "ldap",
        "wire_protocol": "ldapv3",
        "base_dn": search["base_dn"],
        "filter": search["filter"],
        "entries": search["entries"],
        "ldap_result": search,
        "sentinel": extract_sentinel(payload),
        "business_result": {
            "kind": "directory_search",
            "provider": "jndi",
            "runtime_mode": PROVIDER_MODES["jndi"],
            "baseDn": search["base_dn"],
            "filter": search["filter"],
            "matchCount": len(search["entries"]),
            "status": "found" if search["entries"] else "empty",
            "proof_sentinel": extract_sentinel(payload),
            "summary": f"LDAP search returned {len(search['entries'])} Contoso binding(s)",
        },
    })


@router.post("/jndi/lookup")
async def jndi_provider(request: Request) -> JSONResponse:
    payload = await _json_or_query(request)
    lookup = _jndi_lookup_name(payload)
    lookup_result = ldap_lookup(lookup)
    binding = lookup_result["binding"]
    result = build_legacy_result("jndi", lookup, payload)
    result.update({
        "runtime_mode": PROVIDER_MODES["jndi"],
        "protocol": "ldap",
        "wire_protocol": "ldapv3",
        "operation": "lookup",
        "lookup_name": lookup,
        "binding": binding,
        "ldap_entry": lookup_result["ldap_entry"],
        "ldap_result": lookup_result,
        "lookup_found": lookup in JNDI_BINDINGS,
    })
    return JSONResponse(result)


@router.get("/jndi/ldif")
def jndi_ldif_provider() -> Response:
    return Response(content=ldap_config_ldif(), media_type="text/plain")
