"""Structured diagnostics for tool-call failures.

The execution layer historically returned plain strings. This module keeps that
contract intact while giving chat, UI, and generated servers a consistent error
object when a result is clearly a failure.
"""

from __future__ import annotations

import json
import re
from typing import Any


_HEX_RE = re.compile(r"0x[0-9a-fA-F]{4,8}")
_SENTINEL_VALUES = {"0xffffffff", "4294967295", "-1"}


def _first_code(text: str) -> str | None:
    match = _HEX_RE.search(text or "")
    if match:
        return match.group(0)
    for token in _SENTINEL_VALUES:
        if token in (text or "").lower():
            return token
    return None


def _category_from_text(text: str) -> tuple[str | None, str]:
    lower = (text or "").lower()
    if "no_exception" in lower and any(token in lower for token in ("runtime_mode", "business_result", "proof_level")):
        return None, "recoverable"
    if any(token in lower for token in ("0xffffffff", "4294967295")):
        return "sentinel", "recoverable"
    if "bridge /execute error" in lower or "bridge" in lower and "unreachable" in lower:
        return "bridge_unreachable", "blocking"
    if "timed out" in lower or "timeout" in lower:
        return "timeout", "blocking"
    if "not found" in lower and "tool" in lower:
        return "unknown_tool", "blocking"
    if "no executable path" in lower:
        return "no_executable", "blocking"
    if "schema" in lower and ("mismatch" in lower or "invalid" in lower):
        return "schema_mismatch", "recoverable"
    if "<soapenv:fault" in lower or "<soap:fault" in lower or "<fault" in lower or "soap fault" in lower:
        return "soap_fault", "recoverable"
    if "hresult" in lower:
        return "hresult", "recoverable"
    if "winerror" in lower or "win32" in lower:
        return "win32", "recoverable"
    if "ntstatus" in lower:
        return "ntstatus", "recoverable"
    error_prefixes = (
        "dll call error:",
        "cli error:",
        "gui close error:",
        "script error:",
        "http error:",
        "sql error:",
        "json-rpc error:",
    )
    if lower.startswith(error_prefixes) or "exception" in lower:
        return "exception", "blocking"
    if lower.startswith("provider required:"):
        return "provider_required", "blocking"
    return None, "recoverable"


def _looks_like_success_payload(text: str) -> bool:
    stripped = (text or "").strip()
    if not stripped:
        return False
    if stripped.startswith("<") and "<fault" not in stripped.lower() and "faultstring" not in stripped.lower():
        success_tokens = (
            "response",
            "<status>found</status>",
            "<runtimemode>",
            "<provider>",
            "legacyproviderresult",
        )
        lower = stripped.lower()
        return any(token in lower for token in success_tokens)
    if not stripped.startswith(("{", "[")):
        return False
    try:
        data = json.loads(stripped)
    except Exception:
        return False
    if isinstance(data, list):
        return bool(data) and all(isinstance(item, dict) for item in data)
    if not isinstance(data, dict):
        return False
    if data.get("error"):
        return False
    if data.get("passed") is True:
        return True
    if str(data.get("status") or "").lower() in {"found", "ok", "success", "passed"}:
        return True
    if data.get("business_result") or data.get("proof") or data.get("runtime_mode"):
        return True
    if str(data.get("proof_level") or "").lower() == "tool_result_observed":
        return True
    response = data.get("corba_response")
    if isinstance(response, dict) and str(response.get("reply_status") or "").upper() == "NO_EXCEPTION":
        return True
    observed = data.get("observed_result")
    if isinstance(observed, dict) and observed.get("passed") is True:
        return True
    return False


def build_error_payload(
    function_name: str,
    raw_result: int | str | None = None,
    trace: dict[str, Any] | None = None,
    exception: str | None = None,
    findings_for_fn: list[dict[str, Any]] | None = None,
    extra_sentinels: dict[str, str] | None = None,
) -> dict[str, Any] | None:
    """Return a structured error payload, or None when the result looks OK."""
    text = str(exception or raw_result or "")
    if exception is None and _looks_like_success_payload(text):
        return None
    category = (trace or {}).get("category")
    severity = (trace or {}).get("severity") or "recoverable"
    if not category:
        category, severity = _category_from_text(text)
    if not category:
        return None

    raw_code = (trace or {}).get("raw_code") or _first_code(text)
    classified_name = None
    if raw_code and extra_sentinels:
        classified_name = extra_sentinels.get(str(raw_code)) or extra_sentinels.get(str(raw_code).lower())

    known_good: list[dict[str, Any]] = []
    for finding in findings_for_fn or []:
        working_call = finding.get("working_call") or finding.get("args")
        if not isinstance(working_call, dict):
            continue
        known_good.append({
            "args": working_call,
            "confidence": finding.get("confidence") or finding.get("status") or "unknown",
            "recorded_at": finding.get("recorded_at"),
        })
    seen = set()
    deduped_known_good = []
    for item in known_good:
        key = repr(sorted(item["args"].items()))
        if key in seen:
            continue
        seen.add(key)
        deduped_known_good.append(item)

    suggestions = {
        "sentinel": "Use a known-good argument template if available, or run a narrower probe before retrying.",
        "bridge_unreachable": "Retry after the Windows bridge health check passes; this is infrastructure, not schema generation.",
        "timeout": "Retry with a narrower tool or inspect whether the target opened a blocking dialog.",
        "unknown_tool": "Generate/register the selected invocables before chatting, or call a tool name from the generated schema.",
        "missing_selected_invocable": "Go back to Select Invocables and include the missing function, or ask for an operation using the selected tools.",
        "incomplete_tool_sequence": "Do not claim success. Retry only after selecting and executing the full required tool sequence.",
        "no_executable": "Select an invocable with an executable path or rerun discovery for this target.",
        "schema_mismatch": "Regenerate the schema and retry with the parameter names shown in the generated tool.",
        "gui_validation": "Inspect the visible application state and retry only after selecting the exact GUI actions required for this request.",
        "soap_fault": "Inspect the SOAP fault, then retry with values that match the WSDL operation contract.",
        "provider_required": "Enable the matching hosted provider runtime before treating this as a passing live execution proof.",
        "exception": "Inspect the backend trace and retry with the generated schema's required arguments.",
    }
    if deduped_known_good:
        suggestions["sentinel"] = (
            "Retry with a known-good argument template from diagnostics before changing the schema."
        )

    human = text or f"Tool '{function_name}' failed with category {category}."
    return {
        "category": category,
        "severity": severity,
        "classified_name": classified_name,
        "raw_code": raw_code,
        "what_tried": (trace or {}).get("what_tried") or (trace or {}).get("probe_tried") or [],
        "known_good": deduped_known_good,
        "suggestion": suggestions.get(category, "Inspect the backend trace and retry with corrected arguments."),
        "human": human,
    }
