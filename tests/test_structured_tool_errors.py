from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src" / "generation"))

from api.discovery import _safe_discovery_tag
from api.chat import _extract_result_metadata, _tool_trace_metadata
from api.error_enrichment import build_error_payload
from api.executor import _execute_tool_traced
from section4_generate_server import generate_mcp_sdk_artifacts


def test_discovery_tag_sanitizes_frontend_soap_wsdl_hint():
    tag = _safe_discovery_tag("Video demo target: SOAP/WSDL legacy customer service")
    assert "/" not in tag
    assert "\\" not in tag
    assert ":" not in tag
    assert tag.startswith("Video_demo_target_SOAP_WSDL")


def test_error_payload_classifies_no_executable():
    payload = build_error_payload(
        "LaunchThing",
        "CLI error: no executable path configured for 'LaunchThing'",
    )
    assert payload is not None
    assert payload["category"] == "no_executable"
    assert payload["severity"] == "blocking"
    assert payload["suggestion"]


def test_error_payload_classifies_soap_fault():
    payload = build_error_payload(
        "SubmitTicket",
        "<soapenv:Envelope><soapenv:Body><soapenv:Fault><faultstring>Bad request</faultstring></soapenv:Fault></soapenv:Body></soapenv:Envelope>",
    )
    assert payload is not None
    assert payload["category"] == "soap_fault"
    assert "WSDL" in payload["suggestion"]


def test_successful_sentinel_result_is_not_an_error():
    payload = build_error_payload(
        "GetCustomer",
        "<GetCustomerResponse><customerId>MCP_FACTORY_UI_DEMO_SENTINEL</customerId><status>found</status></GetCustomerResponse>",
    )
    assert payload is None


def test_domain_json_success_with_no_exception_is_not_an_error():
    payload = build_error_payload(
        "getCustomer",
        (
            '{"provider":"corba","runtime_mode":"corba_orb_runtime",'
            '"status":"found","business_result":{"customerName":"Contoso Demo Customer"},'
            '"corba_response":{"reply_status":"NO_EXCEPTION"}}'
        ),
    )
    assert payload is None


def test_observed_result_success_with_timeout_field_name_is_not_an_error():
    payload = build_error_payload(
        "kernel32_dll_observed_result",
        (
            '{"proof_level":"tool_result_observed","observed_result":{'
            '"passed":true,"timeout_or_failure_classification":"passed_cached_session"}}'
        ),
    )
    assert payload is None


def test_execute_tool_traced_preserves_plain_result_and_adds_error():
    inv = {
        "name": "LaunchThing",
        "execution": {"method": "cli"},
    }
    traced = _execute_tool_traced(inv, {})
    assert "CLI error: no executable path" in traced["result_str"]
    assert traced["trace"]["backend"] == "cli"
    assert traced["error"]["category"] == "no_executable"


def test_ui_renders_structured_tool_errors():
    ui = (ROOT / "ui" / "main.py").read_text(encoding="utf-8")
    assert "if (evt.error) appendToolError(evt.name, evt.error);" in ui
    assert "function appendToolError" in ui
    assert "tool-error-badge" in ui
    assert "Live Proof Trace" in ui
    assert "function appendTraceEvent" in ui
    assert "appendTraceEvent('tool_call', evt);" in ui
    assert "appendTraceEvent(evt.error ? 'error' : 'tool_result', evt);" in ui
    assert "/api/download" in ui
    chat = (ROOT / "api" / "chat.py").read_text(encoding="utf-8")
    assert '"trace": tool_trace' in chat
    assert '"backend_route": tool_trace.get("backend_route")' in chat


def test_chat_trace_helpers_extract_soap_metadata():
    xml = (
        "<LegacyProviderResult><runtimeMode>real_runtime</runtimeMode>"
        "<operation>GetCustomer</operation><customerName>Contoso Demo Customer</customerName>"
        "<status>found</status><sentinel>MCP_FACTORY_SOAP_VIDEO</sentinel></LegacyProviderResult>"
    )
    meta = _extract_result_metadata(xml)
    assert meta["runtime_mode"] == "real_runtime"
    assert meta["operation"] == "GetCustomer"
    assert meta["customerName"] == "Contoso Demo Customer"
    assert meta["status"] == "found"


def test_chat_trace_helpers_map_provider_routes():
    meta = _tool_trace_metadata(
        {
            "name": "GetCustomer",
            "source_type": "soap",
            "execution": {"method": "soap", "runtime_mode": "real_runtime"},
        },
        "GetCustomer",
        "job-123",
    )
    assert meta["execution_method"] == "soap"
    assert meta["backend_route"] == "/api/legacy/soap"
    assert meta["runtime_mode"] == "real_runtime"
    assert "/api/download/job-123/mcp_schema.json" in meta["artifact_hints"]


def test_generated_mcp_server_formats_error_payloads():
    artifacts = generate_mcp_sdk_artifacts(
        "structured_error_component",
        [{
            "name": "LaunchThing",
            "description": "Launch a fixture.",
            "parameters": [],
            "execution": {"method": "cli"},
        }],
    )
    server = artifacts["mcp_server_py"]
    assert "_format_tool_result" in server
    assert "_tool_error_payload" in server
    assert 'json.dumps({"error": payload}' in server
