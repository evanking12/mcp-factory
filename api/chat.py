"""api/chat.py – Agentic chat completions with tool-call execution loop.

stream_chat(body) – async generator yielding SSE events in real time so the
                    UI can render tool calls and results as they happen instead
                    of waiting for all rounds to complete.

Each round the OpenAI call runs in a thread executor so the event loop is
never blocked — SSE events are flushed to the client between rounds.

SSE event format:  data: <json>\n\n
Event types:
  tool_result events include "error": null on success or a structured error payload on failure.
  {"type": "token",       "content": "..."}          – final text content
  {"type": "tool_call",   "name": "...", "args": {}}  – tool about to execute
  {"type": "tool_result", "name": "...", "result": "..."} – tool output
    {"type": "status",      "stage": "...", "message": "..."} – keepalive/progress
  {"type": "done",        "rounds": N}                – final event
  {"type": "error",       "message": "..."}           – fatal error
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from pathlib import Path
from typing import Any, AsyncGenerator

from fastapi import HTTPException

from api.config import OPENAI_ENDPOINT, OPENAI_DEPLOYMENT, OPENAI_MAX_TOOLS
from api.error_enrichment import build_error_payload
from api.executor import _execute_tool_traced
from api.storage import _register_invocables, _get_invocable
from api.telemetry import _openai_client

logger = logging.getLogger("mcp_factory.api")

# Keep only the last N non-system conversation turns sent to the model each
# round to bound token growth on long sessions.
_CONTEXT_WINDOW_TURNS = 20

_PROVIDER_LABELS = {
    "http_request": "OpenAPI/REST",
    "jsonrpc": "JSON-RPC",
    "soap": "SOAP/WSDL",
    "sql_exec": "SQL",
    "jndi_lookup": "LDAP/JNDI",
    "corba_iiop": "CORBA ORB/IIOP",
    "rpc_call": "MSRPC/RPC",
    "observed_result": "Windows observed proof",
}

_CALC_DIGIT_TO_TOOL = {
    "0": "press_zero",
    "1": "press_one",
    "2": "press_two",
    "3": "press_three",
    "4": "press_four",
    "5": "press_five",
    "6": "press_six",
    "7": "press_seven",
    "8": "press_eight",
    "9": "press_nine",
}
_CALC_OPERATOR_TO_TOOL = {
    "+": "press_plus",
    "plus": "press_plus",
    "add": "press_plus",
    "added": "press_plus",
    "addition": "press_plus",
    "-": "press_minus",
    "minus": "press_minus",
    "subtract": "press_minus",
    "subtracted": "press_minus",
    "*": "press_multiply_by",
    "x": "press_multiply_by",
    "×": "press_multiply_by",
    "multiply": "press_multiply_by",
    "multiplied": "press_multiply_by",
    "times": "press_multiply_by",
    "/": "press_divide_by",
    "÷": "press_divide_by",
    "divide": "press_divide_by",
    "divided": "press_divide_by",
}


def _tool_names_from_schema(tools: list[dict[str, Any]]) -> set[str]:
    names: set[str] = set()
    for tool in tools or []:
        fn = tool.get("function") if isinstance(tool, dict) else {}
        name = fn.get("name") if isinstance(fn, dict) else tool.get("name")
        if name:
            names.add(str(name))
    return names


def _calculator_tool_names(invocables: list[dict[str, Any]], tools: list[dict[str, Any]]) -> set[str]:
    names = _tool_names_from_schema(tools)
    for inv in invocables or []:
        name = str(inv.get("name") or "")
        if name:
            names.add(name)
    calc_names = {
        name for name in names
        if name.startswith("press_") and (
            name in set(_CALC_DIGIT_TO_TOOL.values())
            or name in set(_CALC_OPERATOR_TO_TOOL.values())
            or name == "press_equals"
        )
    }
    return calc_names


def _parse_simple_calculator_request(text: str) -> dict[str, Any] | None:
    """Return required calculator tools for simple arithmetic requests.

    This is intentionally narrow. It catches demo-relevant requests like
    "4 x 2", "calculate 4 * 2", and "add 4 and 2" without trying to become a
    general math parser.
    """
    query = (text or "").lower().replace("×", "x")
    symbol_match = re.search(r"(?<!\d)(\d{1,6})\s*([+\-*/x÷])\s*(\d{1,6})(?!\d)", query)
    word_match = None
    if not symbol_match:
        word_match = re.search(
            r"\b(add|plus|subtract|minus|multiply|multiplied|times|divide|divided)\b\s+(\d{1,6})(?:\s+(?:and|by))?\s+(\d{1,6})",
            query,
        )
    if symbol_match:
        left, op, right = symbol_match.group(1), symbol_match.group(2), symbol_match.group(3)
    elif word_match:
        op, left, right = word_match.group(1), word_match.group(2), word_match.group(3)
    else:
        return None

    op_tool = _CALC_OPERATOR_TO_TOOL.get(op)
    if not op_tool:
        return None

    required: list[str] = []
    for digit in left:
        required.append(_CALC_DIGIT_TO_TOOL[digit])
    required.append(op_tool)
    for digit in right:
        required.append(_CALC_DIGIT_TO_TOOL[digit])
    required.append("press_equals")

    left_i = int(left)
    right_i = int(right)
    expected: float | int
    if op_tool == "press_plus":
        expected = left_i + right_i
    elif op_tool == "press_minus":
        expected = left_i - right_i
    elif op_tool == "press_multiply_by":
        expected = left_i * right_i
    elif op_tool == "press_divide_by":
        expected = left_i / right_i if right_i else float("inf")
    else:
        return None
    expected_text = str(int(expected)) if isinstance(expected, float) and expected.is_integer() else str(expected)
    return {
        "expression": f"{left} {op} {right}",
        "required_tools": required,
        "expected_result": expected_text,
    }


def _calculator_missing_tool_error(calc: dict[str, Any], available_tools: set[str]) -> dict[str, Any] | None:
    missing = [tool for tool in calc["required_tools"] if tool not in available_tools]
    if not missing:
        return None
    deduped_missing = list(dict.fromkeys(missing))
    message = (
        f"Cannot perform calculator request '{calc['expression']}' because the selected MCP tool "
        f"surface is missing: {', '.join(deduped_missing)}."
    )
    return {
        "category": "missing_selected_invocable",
        "severity": "blocking",
        "classified_name": "missing_selected_invocable",
        "raw_code": None,
        "what_tried": [{
            "expression": calc["expression"],
            "required_tools": calc["required_tools"],
            "available_calculator_tools": sorted(available_tools),
        }],
        "known_good": [],
        "suggestion": "Go back to Select Invocables and include the missing function, or ask for an operation using the selected tools.",
        "human": message,
    }


def _display_value_from_result(result: str) -> str:
    match = re.search(r"Display shows:\s*([^\r\n.]+)", result or "", flags=re.IGNORECASE)
    if match:
        return match.group(1).strip()
    try:
        data = json.loads(result or "")
    except Exception:
        return ""
    if isinstance(data, dict):
        for key in ("display", "display_value", "actual_display"):
            if data.get(key) is not None:
                return str(data[key]).strip()
    return ""


def _calculator_postcondition_error(calc: dict[str, Any] | None, tool_name: str, result: str) -> dict[str, Any] | None:
    if not calc or tool_name != "press_equals":
        return None
    actual = _display_value_from_result(result)
    expected = str(calc["expected_result"])
    if not actual or actual == expected:
        return None
    message = (
        f"Calculator result mismatch for '{calc['expression']}': expected display {expected}, "
        f"but the application reported {actual}."
    )
    return {
        "category": "gui_validation",
        "severity": "blocking",
        "classified_name": "calculator_display_mismatch",
        "raw_code": None,
        "what_tried": [{
            "expression": calc["expression"],
            "expected_display": expected,
            "actual_display": actual,
            "tool": tool_name,
        }],
        "known_good": [],
        "suggestion": "Do not claim success. Re-run only after selecting the exact calculator buttons required by the request.",
        "human": message,
    }


def _extract_result_metadata(result: str) -> dict[str, Any]:
    text = result or ""
    metadata: dict[str, Any] = {}
    if not text:
        return metadata
    try:
        parsed = json.loads(text)
    except Exception:
        parsed = None
    if isinstance(parsed, dict):
        business = parsed.get("business_result") if isinstance(parsed.get("business_result"), dict) else {}
        proof = parsed.get("proof") if isinstance(parsed.get("proof"), dict) else {}
        metadata.update({
            "runtime_mode": parsed.get("runtime_mode") or proof.get("runtime_mode") or business.get("runtime_mode") or "",
            "operation": parsed.get("operation") or proof.get("operation") or "",
            "provider": parsed.get("provider") or proof.get("provider") or "",
            "customerName": business.get("customerName") or parsed.get("customerName") or "",
            "status": parsed.get("status") or business.get("status") or "",
            "sentinel": parsed.get("sentinel") or proof.get("sentinel") or business.get("proof_sentinel") or "",
        })
        return {k: v for k, v in metadata.items() if v}
    patterns = {
        "runtime_mode": r"<runtimeMode>([^<]+)</runtimeMode>",
        "operation": r"<operation>([^<]+)</operation>",
        "customerName": r"<customerName>([^<]+)</customerName>",
        "status": r"<status>([^<]+)</status>",
        "sentinel": r"<sentinel>([^<]+)</sentinel>",
        "provider": r"<provider>([^<]+)</provider>",
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, text)
        if match:
            metadata[key] = match.group(1)
    return metadata


def _tool_trace_metadata(inv: dict | None, fn_name: str, job_id: str) -> dict[str, Any]:
    if not inv:
        return {"backend_route": "unknown_tool", "artifact_hints": []}
    execution = inv.get("execution") or inv.get("mcp", {}).get("execution", {})
    method = execution.get("method", "") or ""
    backend_route = ""
    if method == "http_request":
        backend_route = "/api/legacy/rest"
    elif method == "jsonrpc":
        backend_route = "/api/legacy/jsonrpc"
    elif method == "soap":
        backend_route = "/api/legacy/soap"
    elif method == "sql_exec":
        backend_route = f"/api/legacy/sql/{fn_name}"
    elif method == "jndi_lookup":
        backend_route = "/api/legacy/jndi/lookup"
    elif method == "corba_iiop":
        backend_route = f"/api/legacy/corba/{fn_name}"
    elif method == "rpc_call":
        backend_route = f"/api/legacy/rpc/{fn_name}"
    elif method == "observed_result":
        backend_route = "windows_bridge_summary"
    elif method in {"dll_import", "gui_action"}:
        backend_route = "windows_bridge"
    elif method:
        backend_route = _PROVIDER_LABELS.get(method, method)
    artifact_hints = []
    if job_id:
        artifact_hints = [
            f"/api/download/{job_id}/mcp_schema.json",
            f"/api/download/{job_id}/mcp_server.py",
        ]
    return {
        "execution_method": method,
        "execution_label": _PROVIDER_LABELS.get(method, method or "generated tool"),
        "source_type": inv.get("source_type") or inv.get("kind") or "",
        "runtime_mode": inv.get("runtime_mode") or execution.get("runtime_mode") or "",
        "backend_route": backend_route,
        "artifact_hints": artifact_hints,
    }


def _keyword_filter_tools(query: str, tools: list, top_k: int) -> list:
    """Score tools by keyword overlap with query; return up to top_k.

    Used as a zero-cost fallback when the semantic embedding cache is cold
    (container restart, no Azure AI Search, embed_and_index failure).
    Exact tool-name matches score highest so that direct requests like
    'Use IsBrowsable' always surface the right tool.
    """
    q_lower = query.lower()
    words = [w.strip("\"'().,;:!?") for w in q_lower.split() if len(w) > 2]

    scored: list[tuple[float, dict]] = []
    for t in tools:
        fn   = t.get("function", {})
        name = fn.get("name", "").lower()
        desc = (fn.get("description", "") or "").lower()
        score = 0.0
        for w in words:
            if w == name:
                score += 10.0       # exact name match — highest weight
            elif w in name:
                score += 4.0        # partial name match
            elif w in desc:
                score += 1.0        # description mention
        if score > 0:
            scored.append((score, t))

    scored.sort(key=lambda x: x[0], reverse=True)
    result = [t for _, t in scored[:top_k]]

    # Pad with first tools if we don't have enough keyword matches
    if len(result) < top_k:
        seen = {t.get("function", {}).get("name") for t in result}
        for t in tools:
            if len(result) >= top_k:
                break
            if t.get("function", {}).get("name") not in seen:
                result.append(t)
    return result


def _sse(event: dict) -> str:
    """Format a dict as a single SSE data line."""
    return f"data: {json.dumps(event)}\n\n"


def _build_system_message(invocables: list) -> dict:
    return {
        "role": "system",
        "content": (
            "You are an AI agent with direct control over a Windows application via MCP tools.\n"
            "RULES:\n"
            "1. When asked to perform an action, call the appropriate tool(s) immediately. "
            "You may call multiple tools in a single response to perform sequences faster "
            "(e.g. to calculate 4 × 3 you would call press_four, press_multiply_by, press_three, press_equals all at once).\n"
            "   Match the user's intent to the exact tool name — for multiply use press_multiply_by, "
            "for divide use press_divide_by, for add use press_plus, for subtract use press_minus.\n"
            "2. After all tool calls finish, always write a plain-text sentence summarising "
            "what happened and the result visible on screen.\n"
            "3. Use only the tools provided in this session. If a requested digit, operator, menu item, "
            "or action is not available as a tool, say it is not available; do not substitute another tool "
            "and do not claim the requested task succeeded.\n"
            "4. Never launch an application that is already open — call the launch tool only once per session.\n"
            "5. If the user asks about your capabilities (e.g. 'list your tools', 'what can you do'), "
            "reply with plain text only — do not call any tools.\n"
            "Use only the tools provided in this session."
        ),
    }


async def stream_chat(body: dict[str, Any]) -> AsyncGenerator[str, None]:
    """Async generator: runs the agentic tool-call loop yielding SSE events
    between rounds so the browser sees progress in real time.

    Each OpenAI call runs in a thread executor so the async event loop is
    never blocked — SSE events flush to the client immediately after each
    yield.  No OpenAI stream=True is used; we get per-round feedback instead
    of per-token, which is much more reliable with the sync AzureOpenAI client.
    """
    messages: list   = body.get("messages", [])
    tools: list      = body.get("tools", [])
    invocables: list = body.get("invocables", [])
    job_id: str      = body.get("job_id", "")

    if not messages:
        yield _sse({"type": "error", "message": "No messages provided"})
        return
    if not OPENAI_ENDPOINT:
        yield _sse({"type": "error", "message": "Azure OpenAI endpoint not configured"})
        return

    inv_map: dict[str, dict] = {}
    for inv in invocables:
        raw_name = inv.get("name", "")
        if not raw_name:
            continue
        inv_map[raw_name] = inv
        inv_map[re.sub(r"[^a-zA-Z0-9_.\-]", "_", raw_name)[:64]] = inv

    MAX_TOOL_ROUNDS = 10
    _last_call_signature = ""

    # Build conversation: system prompt first, then last N user/assistant turns.
    sys_msgs  = [m for m in messages if m.get("role") == "system"]
    user_msgs = [m for m in messages if m.get("role") != "system"]
    if not sys_msgs:
        sys_msgs = [_build_system_message(invocables)]
    conversation = sys_msgs + user_msgs[-_CONTEXT_WINDOW_TURNS:]

    _AI_SEARCH_TOP_K = OPENAI_MAX_TOOLS
    _active_tools = list(tools)
    _called_launchers: set[str] = set()
    _tools_executed: list[str] = []  # names of tool calls that actually ran
    _last_user_message = next(
        (m.get("content", "") for m in reversed(conversation) if m.get("role") == "user"),
        "",
    )
    _calculator_request = _parse_simple_calculator_request(_last_user_message)
    _calculator_tools = _calculator_tool_names(invocables, tools)
    if _calculator_request and _calculator_tools:
        preflight_error = _calculator_missing_tool_error(_calculator_request, _calculator_tools)
        if preflight_error:
            result = preflight_error["human"]
            trace = {
                "backend": "selected_tool_preflight",
                "tool": "calculator_preflight",
                "category": "missing_selected_invocable",
                "severity": "blocking",
                "expected_result": _calculator_request["expected_result"],
                "required_tools": _calculator_request["required_tools"],
                "available_calculator_tools": sorted(_calculator_tools),
            }
            yield _sse({
                "type": "tool_result",
                "name": "calculator_preflight",
                "result": result,
                "error": preflight_error,
                "trace": trace,
                "runtime_mode": "",
                "backend_route": "selected_tool_preflight",
                "artifact_hints": [],
                "result_metadata": {},
            })
            yield _sse({
                "type": "token",
                "content": (
                    f"I cannot perform `{_calculator_request['expression']}` with the selected MCP tools. "
                    f"{result}"
                ),
            })
            yield _sse({"type": "done", "rounds": 0})
            return

    loop = asyncio.get_event_loop()

    # Only re-register (and re-upload to blob) when the server doesn't already
    # have this job's invocables in memory.  The UI re-sends the full list on
    # every message (~2 MB for 1000 tools), so skipping this on subsequent
    # turns avoids a redundant 2 MB blob upload that would block the async
    # generator before the first SSE event is yielded.
    if job_id and invocables:
        from api.storage import _JOB_INVOCABLE_MAPS as _jimap  # type: ignore
        if job_id not in _jimap:
            loop.run_in_executor(None, _register_invocables, job_id, invocables)

    try:
        client = _openai_client()

        # ── P5: Initial semantic tool selection (mirrors run_chat) ─────────
        # stream_chat had no filtering at all — every tool was sent on every
        # round, which blows the token budget for large schemas like shell32
        # and causes the model to hang on round 2+ (after tool execution).
        if len(tools) > _AI_SEARCH_TOP_K and job_id and _last_user_message:
            try:
                from search import retrieve_tools as _retrieve_tools  # type: ignore
                _semantic_tools = await loop.run_in_executor(
                    None,
                    lambda: _retrieve_tools(job_id, _last_user_message, client, top_k=_AI_SEARCH_TOP_K),
                )
                if _semantic_tools:
                    _active_tools = _semantic_tools
                    logger.info(
                        "[%s] stream_chat: semantic selected %d/%d tools",
                        job_id, len(_active_tools), len(tools),
                    )
                else:
                    _active_tools = _keyword_filter_tools(_last_user_message, tools, _AI_SEARCH_TOP_K)
                    logger.warning(
                        "[%s] stream_chat: semantic empty; keyword fallback %d→%d",
                        job_id, len(tools), _AI_SEARCH_TOP_K,
                    )
            except Exception as _se:
                logger.warning("[%s] stream_chat: semantic retrieval failed: %s", job_id, _se)
                _active_tools = _keyword_filter_tools(_last_user_message, tools, _AI_SEARCH_TOP_K)

        for _round in range(MAX_TOOL_ROUNDS):
            # ── Per-round semantic re-selection ────────────────────────────
            # After round 0, re-query using the model's last assistant content
            # as the search string so the retrieved set tracks what the model
            # is currently working on rather than the original user prompt.
            if _round > 0 and len(tools) > _AI_SEARCH_TOP_K and job_id:
                _rolling_query = _last_user_message
                for m in reversed(conversation):
                    if m.get("role") == "assistant" and m.get("content"):
                        _rolling_query = m["content"]
                        break
                try:
                    from search import retrieve_tools as _retrieve_tools  # type: ignore
                    _semantic_tools = await loop.run_in_executor(
                        None,
                        lambda q=_rolling_query: _retrieve_tools(job_id, q, client, top_k=_AI_SEARCH_TOP_K),
                    )
                    if _semantic_tools:
                        _active_tools = [t for t in _semantic_tools
                                         if t.get("function", {}).get("name") not in _called_launchers]
                    else:
                        _kw = _keyword_filter_tools(_rolling_query, tools, _AI_SEARCH_TOP_K)
                        _active_tools = [t for t in _kw
                                         if t.get("function", {}).get("name") not in _called_launchers]
                except Exception as _re:
                    logger.warning(
                        "[%s] stream_chat: semantic refresh failed round %d: %s", job_id, _round, _re
                    )
                    _kw = _keyword_filter_tools(_rolling_query, tools, _AI_SEARCH_TOP_K)
                    _active_tools = [t for t in _kw
                                     if t.get("function", {}).get("name") not in _called_launchers]
            elif _called_launchers:
                # Exclude already-fired launcher tools so the model can't re-launch.
                _active_tools = [t for t in _active_tools
                                 if t.get("function", {}).get("name") not in _called_launchers]

            kwargs: dict = {
                "model":       OPENAI_DEPLOYMENT,
                "messages":    conversation,
                "temperature": 0,
            }
            if _active_tools:
                kwargs["tools"]       = _active_tools
                kwargs["tool_choice"] = "auto"

            # Run the blocking OpenAI call in a thread so the event loop stays
            # free to flush already-yielded SSE events to the client.
            _OPENAI_HARD_TIMEOUT = 120  # seconds before we give up and surface an error
            _openai_t0 = time.perf_counter()
            _openai_future = loop.run_in_executor(
                None,
                lambda kw=kwargs: client.chat.completions.create(**kw),
            )
            while True:
                try:
                    response = await asyncio.wait_for(asyncio.shield(_openai_future), timeout=5.0)
                    break
                except asyncio.TimeoutError:
                    if time.perf_counter() - _openai_t0 > _OPENAI_HARD_TIMEOUT:
                        yield _sse({"type": "error", "message": "Model took too long to respond — try again."})
                        return
                    yield _sse({
                        "type": "status",
                        "stage": "openai",
                        "message": "Waiting for model response...",
                    })
            _openai_ms = (time.perf_counter() - _openai_t0) * 1000.0
            msg = response.choices[0].message
            logger.info(
                "[stream_chat/%d] openai latency=%.1f ms tool_calls=%d content=%s",
                _round,
                _openai_ms,
                len(msg.tool_calls or []),
                bool(msg.content),
            )

            # ── No tool calls → final text answer ─────────────────────────
            if not msg.tool_calls:
                if msg.content:
                    yield _sse({"type": "token", "content": msg.content})
                elif _tools_executed:
                    # Model returned no summary text (common at temperature=0 after
                    # tool calls).  Force one final text-only completion so the user
                    # gets a real conversational response instead of a terse fallback.
                    try:
                        # Don't include tools here — tool_choice=none means they
                        # can never fire; they only waste context tokens on round 2+.
                        _summary_kw = {
                            "model":       OPENAI_DEPLOYMENT,
                            "messages":    conversation,
                            "temperature": 0.3,
                        }
                        _summary_future = loop.run_in_executor(
                            None,
                            lambda kw=_summary_kw: client.chat.completions.create(**kw),
                        )
                        while True:
                            try:
                                _summary_resp = await asyncio.wait_for(
                                    asyncio.shield(_summary_future), timeout=5.0
                                )
                                break
                            except asyncio.TimeoutError:
                                yield _sse({"type": "status", "stage": "openai",
                                            "message": "Generating response..."})
                        _summary_text = _summary_resp.choices[0].message.content
                        if _summary_text:
                            yield _sse({"type": "token", "content": _summary_text})
                        else:
                            names = ", ".join(_tools_executed[-3:])
                            yield _sse({"type": "token",
                                        "content": f"Done — executed {len(_tools_executed)} step(s): {names}."})
                    except Exception as _se:
                        logger.warning("[stream_chat] Summary call failed: %s", _se)
                        names = ", ".join(_tools_executed[-3:])
                        yield _sse({"type": "token",
                                    "content": f"Done — executed {len(_tools_executed)} step(s): {names}."})
                yield _sse({"type": "done", "rounds": _round + 1})
                return

            # ── Loop detection ─────────────────────────────────────────────
            _this_sig = "|".join(
                f"{tc.function.name}:{tc.function.arguments}" for tc in msg.tool_calls
            )
            if _this_sig == _last_call_signature:
                logger.warning("[stream_chat] Loop detected — stopping")
                yield _sse({"type": "done", "rounds": _round + 1})
                return
            _last_call_signature = _this_sig

            # Append assistant turn with tool_calls to conversation
            conversation.append({
                "role": "assistant",
                "content": msg.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in msg.tool_calls
                ],
            })

            # ── Execute each tool call, streaming result events immediately ─
            for tc in msg.tool_calls:
                fn_name = tc.function.name
                try:
                    fn_args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    fn_args = {}

                inv = inv_map.get(fn_name)
                if inv is None and job_id:
                    inv = _get_invocable(job_id, fn_name)
                trace_meta = _tool_trace_metadata(inv, fn_name, job_id)

                yield _sse({
                    "type": "tool_call",
                    "name": fn_name,
                    "args": fn_args,
                    **trace_meta,
                })

                if inv is not None:
                    # Tool execution can be slow (pywinauto, GUI interaction) —
                    # run in executor so the SSE response stays live.
                    _TOOL_HARD_TIMEOUT = 30  # seconds; DLL/COM/GUI calls can hang
                    _tool_t0 = time.perf_counter()
                    _tool_future = loop.run_in_executor(
                        None, lambda i=inv, a=fn_args: _execute_tool_traced(i, a)
                    )
                    tool_error = None
                    while True:
                        try:
                            traced_result = await asyncio.wait_for(
                                asyncio.shield(_tool_future), timeout=5.0
                            )
                            tool_result = traced_result["result_str"]
                            tool_error = traced_result.get("error")
                            tool_trace = traced_result.get("trace") or {}
                            break
                        except asyncio.TimeoutError:
                            if time.perf_counter() - _tool_t0 > _TOOL_HARD_TIMEOUT:
                                tool_result = f"Tool '{fn_name}' timed out after {_TOOL_HARD_TIMEOUT}s — the call may have hung (COM/DLL deadlock or blocking dialog)."
                                tool_trace = {**trace_meta, "backend": trace_meta.get("execution_method") or "timeout"}
                                break
                            yield _sse({
                                "type": "status",
                                "stage": "tool",
                                "name": fn_name,
                                "message": f"Waiting for tool '{fn_name}'...",
                            })
                    if tool_error is None:
                        tool_error = build_error_payload(fn_name, tool_result)
                    if tool_error is None:
                        tool_error = _calculator_postcondition_error(_calculator_request, fn_name, tool_result)
                        if tool_error:
                            tool_trace = {
                                **tool_trace,
                                "category": "gui_validation",
                                "severity": "blocking",
                                "expected_result": _calculator_request["expected_result"] if _calculator_request else "",
                                "actual_display": _display_value_from_result(tool_result),
                            }
                    _tool_ms = (time.perf_counter() - _tool_t0) * 1000.0
                    if inv.get("source_type") == "cli" and \
                            Path(inv.get("dll_path", "")).stem.lower() == fn_name.lower():
                        _called_launchers.add(fn_name)
                else:
                    tool_result = (
                        f"Tool '{fn_name}' not found — pass 'invocables' in the "
                        f"request body or call /api/generate first."
                    )
                    tool_error = build_error_payload(
                        fn_name,
                        tool_result,
                        {"backend": "unknown_tool", "category": "unknown_tool", "severity": "blocking"},
                    )
                    _tool_ms = 0.0
                    tool_trace = {"backend": "unknown_tool", "tool": fn_name, "backend_route": "unknown_tool"}

                result_metadata = _extract_result_metadata(tool_result)
                yield _sse({
                    "type": "tool_result",
                    "name": fn_name,
                    "result": tool_result,
                    "error": tool_error,
                    "trace": tool_trace,
                    "runtime_mode": result_metadata.get("runtime_mode") or tool_trace.get("runtime_mode") or trace_meta.get("runtime_mode") or "",
                    "backend_route": tool_trace.get("backend_route") or trace_meta.get("backend_route") or "",
                    "artifact_hints": trace_meta.get("artifact_hints") or [],
                    "result_metadata": result_metadata,
                })
                logger.info(
                    "[stream_chat/%d] tool=%s latency=%.1f ms result=%s",
                    _round,
                    fn_name,
                    _tool_ms,
                    tool_result[:120],
                )
                _tools_executed.append(fn_name)

                conversation.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": tool_result,
                })

            # Trim conversation to bound token size each round.
            _sys  = [m for m in conversation if m.get("role") == "system"]
            _rest = [m for m in conversation if m.get("role") != "system"]
            conversation = _sys + _rest[-_CONTEXT_WINDOW_TURNS:]

        yield _sse({"type": "done", "rounds": MAX_TOOL_ROUNDS})

    except Exception as exc:
        logger.error("stream_chat error: %s", exc)
        yield _sse({"type": "error", "message": str(exc)})
