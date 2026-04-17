from __future__ import annotations

import json
import sys
import xmlrpc.client
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api import executor
from api.legacy_provider import router


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_legacy_provider_routes_echo_sentinel() -> None:
    client = _client()
    sentinel = "MCP_FACTORY_LEGACY_SENTINEL"

    health = client.get("/api/legacy/health").json()
    assert health["status"] == "ok"
    assert set(["rest", "jsonrpc", "soap", "sql", "corba", "rpc", "jndi"]).issubset(health["enabled_providers"])
    assert health["provider_modes"]["jsonrpc"] == "real_runtime"
    assert health["provider_modes"]["soap"] == "real_runtime"
    assert health["provider_modes"]["sql"] == "real_runtime"
    assert health["provider_modes"]["rest"] == "validated_runtime"
    assert health["provider_modes"]["jndi"] == "ldap_jndi_runtime"
    assert health["provider_modes"]["rpc"] == "xmlrpc_runtime"
    assert health["provider_modes"]["corba"] == "corba_idl_runtime"

    assert sentinel in client.post("/api/legacy/rest/tickets", json={"sentinel": sentinel}).text
    assert sentinel in client.post(
        "/api/legacy/jsonrpc",
        json={"jsonrpc": "2.0", "method": "createTicket", "params": {"sentinel": sentinel}, "id": 7},
    ).text
    assert sentinel in client.post(
        "/api/legacy/soap",
        headers={"SOAPAction": "SubmitTicket"},
        content=(
            '<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">'
            f"<soapenv:Body><SubmitTicket><sentinel>{sentinel}</sentinel></SubmitTicket></soapenv:Body>"
            "</soapenv:Envelope>"
        ),
    ).text
    assert sentinel in client.post("/api/legacy/sql/GetCustomerInfo", json={"sentinel": sentinel}).text
    assert sentinel in client.post("/api/legacy/corba/getCustomer", json={"sentinel": sentinel}).text
    rpc_body = xmlrpc.client.dumps(({"sentinel": sentinel},), methodname="RpcCreateTicket")
    assert sentinel in client.post("/api/legacy/rpc/RpcCreateTicket", content=rpc_body, headers={"Content-Type": "text/xml"}).text
    assert sentinel in client.post("/api/legacy/jndi/lookup", json={"name": "jdbc/ContosoCustomerDB", "sentinel": sentinel}).text


def test_jsonrpc_runtime_returns_standard_errors() -> None:
    client = _client()

    invalid = client.post("/api/legacy/jsonrpc", json={"jsonrpc": "1.0", "method": "getCustomer", "id": 8})
    assert invalid.status_code == 400
    assert invalid.json()["error"]["code"] == -32600

    missing = client.post("/api/legacy/jsonrpc", json={"jsonrpc": "2.0", "method": "missingMethod", "id": 9})
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == -32601


def test_rest_runtime_validates_declared_openapi_routes() -> None:
    client = _client()

    ok = client.get("/api/legacy/rest/customers/1", params={"sentinel": "MCP_FACTORY_REST_ROUTE"})
    assert ok.status_code == 200
    assert ok.json()["runtime_mode"] == "validated_runtime"
    assert "MCP_FACTORY_REST_ROUTE" in ok.text

    rejected = client.delete("/api/legacy/rest/customers/1")
    assert rejected.status_code == 404
    assert rejected.json()["runtime_mode"] == "validated_runtime"
    assert "not declared" in rejected.json()["error"]


def test_soap_runtime_validates_envelope_and_dispatches_operation() -> None:
    client = _client()
    sentinel = "MCP_FACTORY_SOAP_RUNTIME"
    valid = client.post(
        "/api/legacy/soap",
        headers={"SOAPAction": "GetCustomer"},
        content=(
            '<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">'
            f"<soapenv:Body><GetCustomer><sentinel>{sentinel}</sentinel></GetCustomer></soapenv:Body>"
            "</soapenv:Envelope>"
        ),
    )
    assert valid.status_code == 200
    assert "<runtimeMode>real_runtime</runtimeMode>" in valid.text
    assert sentinel in valid.text

    invalid = client.post("/api/legacy/soap", content=f"<NotSoap>{sentinel}</NotSoap>")
    assert invalid.status_code == 400
    assert "<soapenv:Fault>" in invalid.text

    unknown = client.post(
        "/api/legacy/soap",
        headers={"SOAPAction": "UnknownOperation"},
        content=(
            '<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">'
            "<soapenv:Body><UnknownOperation /></soapenv:Body></soapenv:Envelope>"
        ),
    )
    assert unknown.status_code == 404
    assert "Unknown SOAP operation" in unknown.text


def test_sql_runtime_uses_sqlite_and_returns_deterministic_contoso_data() -> None:
    client = _client()

    customer = client.post("/api/legacy/sql/GetCustomerInfo", json={"customer_id": 1, "sentinel": "MCP_FACTORY_SQL_RUNTIME"})
    assert customer.status_code == 200
    data = customer.json()
    assert data["runtime_mode"] == "real_runtime"
    assert data["database"] == "sqlite"
    assert data["result"]["customer"][0]["name"] == "Ada Lovelace"
    assert "MCP_FACTORY_SQL_RUNTIME" in data["proof"]

    gpt_style = client.post(
        "/api/legacy/sql/GetCustomerInfo",
        json={
            "args": {
                "customer_id": "MCP_FACTORY_SQL_AS_CUSTOMER_ID",
                "include_orders": "MCP_FACTORY_SQL_AS_CUSTOMER_ID",
            }
        },
    )
    assert gpt_style.status_code == 200
    assert gpt_style.json()["result"]["customer"][0]["id"] == 1
    assert "MCP_FACTORY_SQL_AS_CUSTOMER_ID" in gpt_style.json()["proof"]

    ticket = client.post(
        "/api/legacy/sql/CreateSupportTicket",
        json={"customerId": 1, "subject": "Runtime proof", "description": "MCP_FACTORY_SQL_TICKET"},
    )
    assert ticket.status_code == 200
    assert ticket.json()["result"]["status"] == "Open"


def test_jndi_and_rpc_runtime_modes_are_explicit() -> None:
    client = _client()

    jndi = client.post("/api/legacy/jndi/lookup", json={"name": "jdbc/ContosoCustomerDB", "sentinel": "MCP_FACTORY_JNDI"})
    assert jndi.status_code == 200
    assert jndi.json()["runtime_mode"] == "ldap_jndi_runtime"
    assert jndi.json()["lookup_found"] is True
    assert jndi.json()["binding"]["type"] == "javax.sql.DataSource"
    assert jndi.json()["ldap_entry"]["dn"].endswith("dc=contoso,dc=com")

    bind = client.post("/api/legacy/jndi/bind", json={"principal": "cn=serviceaccount,dc=contoso,dc=com"})
    assert bind.status_code == 200
    assert bind.json()["bound"] is True

    search = client.post("/api/legacy/jndi/search", json={"filter": "Customer"})
    assert search.status_code == 200
    assert search.json()["entries"]

    rpc_payload = xmlrpc.client.dumps(({"sentinel": "MCP_FACTORY_RPC"},), methodname="RpcCreateTicket")
    rpc = client.post("/api/legacy/rpc/RpcCreateTicket", content=rpc_payload, headers={"Content-Type": "text/xml"})
    assert rpc.status_code == 200
    values, _method = xmlrpc.client.loads(rpc.text.encode("utf-8"))
    assert values[0]["runtime_mode"] == "xmlrpc_runtime"
    assert values[0]["transport"] == "xmlrpc"
    assert "MCP_FACTORY_RPC" in values[0]["sentinel"]

    missing_payload = xmlrpc.client.dumps(({"sentinel": "MCP_FACTORY_RPC"},), methodname="RpcMissing")
    missing = client.post("/api/legacy/rpc/RpcMissing", content=missing_payload, headers={"Content-Type": "text/xml"})
    assert "<fault>" in missing.text


def test_corba_idl_runtime_validates_object_registry() -> None:
    client = _client()

    ok = client.post("/api/legacy/corba/ICustomerService_getCustomer", json={"sentinel": "MCP_FACTORY_CORBA"})
    assert ok.status_code == 200
    data = ok.json()
    assert data["runtime_mode"] == "corba_idl_runtime"
    assert data["repository_id"] == "IDL:contoso.com/CustomerService/ICustomerService:1.0"
    assert data["corba_response"]["reply_status"] == "NO_EXCEPTION"
    assert "MCP_FACTORY_CORBA" in data["sentinel"]

    rejected = client.post("/api/legacy/corba/deleteEverything", json={"sentinel": "MCP_FACTORY_CORBA"})
    assert rejected.status_code == 404
    assert "not declared" in rejected.json()["error"]


class _Resp:
    def __init__(self, text: str, status_code: int = 200, payload: dict | None = None) -> None:
        self.text = text
        self.status_code = status_code
        self._payload = payload

    def json(self) -> dict:
        return self._payload if self._payload is not None else json.loads(self.text)


def test_executor_routes_openapi_jsonrpc_soap_to_legacy_provider(monkeypatch) -> None:
    calls: list[tuple[str, str, dict]] = []

    monkeypatch.setattr(executor, "ENABLE_LEGACY_PROVIDERS", True)
    monkeypatch.setattr(executor, "LEGACY_PROVIDER_BASE_URL", "http://legacy.local/api/legacy")
    monkeypatch.setattr(executor, "PIPELINE_API_KEY", "secret")

    def fake_request(method: str, url: str, **kwargs):
        calls.append((method, url, kwargs))
        assert kwargs["headers"]["X-Pipeline-Key"] == "secret"
        return _Resp("MCP_FACTORY_REST")

    def fake_post(url: str, **kwargs):
        calls.append(("POST", url, kwargs))
        assert kwargs["headers"]["X-Pipeline-Key"] == "secret"
        if url.endswith("/jsonrpc"):
            return _Resp("", payload={"jsonrpc": "2.0", "id": 1, "result": {"sentinel": "MCP_FACTORY_JSONRPC"}})
        return _Resp("MCP_FACTORY_SOAP")

    monkeypatch.setattr("httpx.request", fake_request)
    monkeypatch.setattr("httpx.post", fake_post)

    assert "MCP_FACTORY_REST" in executor._execute_tool(
        {"name": "getCustomer", "execution": {"method": "http_request", "path": "/customers/{customerId}", "http_method": "GET"}},
        {"customerId": "MCP_FACTORY_REST"},
    )
    assert "MCP_FACTORY_JSONRPC" in executor._execute_tool(
        {"name": "getCustomerProfile", "execution": {"method": "jsonrpc"}},
        {"sentinel": "MCP_FACTORY_JSONRPC"},
    )
    assert "MCP_FACTORY_SOAP" in executor._execute_tool(
        {"name": "GetCustomer", "execution": {"method": "soap", "action": "GetCustomer"}},
        {"sentinel": "MCP_FACTORY_SOAP"},
    )

    assert calls[0][1] == "http://legacy.local/api/legacy/rest/customers/MCP_FACTORY_REST"
    assert calls[1][1] == "http://legacy.local/api/legacy/jsonrpc"
    assert calls[2][1] == "http://legacy.local/api/legacy/soap"


def test_executor_routes_sql_corba_rpc_jndi_to_legacy_provider(monkeypatch) -> None:
    urls: list[str] = []

    monkeypatch.setattr(executor, "ENABLE_LEGACY_PROVIDERS", True)
    monkeypatch.setattr(executor, "LEGACY_PROVIDER_BASE_URL", "http://legacy.local/api/legacy")
    monkeypatch.setattr(executor, "PIPELINE_API_KEY", "")

    def fake_post(url: str, **kwargs):
        urls.append(url)
        if url.endswith("rpc/RpcCreateTicket"):
            response = xmlrpc.client.dumps(({"sentinel": "MCP_FACTORY_LEGACY"},), methodresponse=True)
            return _Resp(response)
        return _Resp("MCP_FACTORY_LEGACY")

    monkeypatch.setattr("httpx.post", fake_post)

    cases = [
        ({"name": "GetCustomerInfo", "execution": {"method": "sql_exec", "statement": "SELECT 1"}}, "sql/GetCustomerInfo"),
        ({"name": "getCustomer", "execution": {"method": "corba_iiop"}}, "corba/getCustomer"),
        ({"name": "RpcCreateTicket", "execution": {"method": "rpc_call"}}, "rpc/RpcCreateTicket"),
        ({"name": "jdbc/ContosoCustomerDB", "execution": {"method": "jndi_lookup"}}, "jndi/lookup"),
    ]
    for inv, suffix in cases:
        assert "MCP_FACTORY_LEGACY" in executor._execute_tool(inv, {"sentinel": "MCP_FACTORY_LEGACY"})
        assert urls[-1].endswith(suffix)


def test_executor_observed_result_returns_windows_summary_payload() -> None:
    result = executor._execute_tool(
        {
            "name": "notepad_exe_observed_result",
            "execution": {
                "method": "observed_result",
                "target_label": "notepad_exe",
                "artifact_path": "ci_artifacts/demo/windows/notepad_exe/notepad_exe.summary.json",
                "observed_result": {"matched_invocable_count": 4, "passed": True},
            },
        },
        {"acknowledgement": "confirm"},
    )
    data = json.loads(result)
    assert data["proof_level"] == "tool_result_observed"
    assert data["target_label"] == "notepad_exe"
    assert data["observed_result"]["matched_invocable_count"] == 4
