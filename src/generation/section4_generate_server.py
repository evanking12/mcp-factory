"""
section4_generate_server.py
Generates a Flask-based MCP server with /tools, /invoke, and /chat endpoints
from a selected-invocables.json file. The /chat endpoint uses OpenAI function
calling (compatible with api.openai.com and Azure OpenAI via .env variables).
"""

import json
import os
import textwrap

INPUT_PATH = os.path.join("artifacts", "selected-invocables.json")
OUTPUT_BASE = "generated"

# ---------------------------------------------------------------------------
# Server template — placeholders are replaced by _inject() below.
# __COMPONENT_NAME__  → component name string (no quotes, used in comments)
# __INVOCABLES_JSON__ → JSON-serialised list of invocable dicts
# ---------------------------------------------------------------------------
SERVER_TEMPLATE = r'''# Generated MCP server — __COMPONENT_NAME__
# Run:  pip install -r requirements.txt  &&  cp .env.example .env  (fill values)
#       python server.py

import os
import json
import ctypes
import subprocess
from flask import Flask, request, jsonify, send_from_directory
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, static_folder="static")

# ── Tool registry (injected by generator) ──────────────────────────────────
INVOCABLES = __INVOCABLES_JSON__

INVOCABLE_MAP = {inv["name"]: inv for inv in INVOCABLES}


def _build_openai_functions():
    """Convert the invocable list into OpenAI function-calling schema objects."""
    fns = []
    for inv in INVOCABLES:
        props = {}
        required = []
        for p in inv.get("parameters", []):
            props[p["name"]] = {
                "type": "string",
                "description": p.get("description", ""),
            }
            if p.get("required", False):
                required.append(p["name"])
        fns.append({
            "type": "function",
            "function": {
                "name": inv["name"],
                "description": inv.get("description") or f"Invoke {inv['name']} from __COMPONENT_NAME__",
                "parameters": {
                    "type": "object",
                    "properties": props,
                    "required": required,
                },
            },
        })
    return fns


OPENAI_FUNCTIONS = _build_openai_functions()


# ── Execution helpers ───────────────────────────────────────────────────────

def _execute_tool(name: str, args: dict) -> str:
    inv = INVOCABLE_MAP.get(name)
    if not inv:
        return f"Unknown tool: {name}"
    execution = inv.get("execution", {})
    method = execution.get("method", "")
    if method == "dll_import":
        return _execute_dll(execution, args)
    return _execute_cli(execution, name, args)


def _execute_dll(execution: dict, args: dict) -> str:
    dll_path = execution.get("dll_path", "")
    func_name = execution.get("function_name", "")
    try:
        lib = ctypes.CDLL(dll_path)
        fn = getattr(lib, func_name)
        fn.restype = ctypes.c_size_t
        # Pass positional string args if any were supplied.
        c_args = [ctypes.c_char_p(v.encode()) for v in args.values() if isinstance(v, str)]
        result = fn(*c_args) if c_args else fn()
        return f"Returned: {result}"
    except Exception as exc:
        return f"DLL call error: {exc}"


def _execute_cli(execution: dict, name: str, args: dict) -> str:
    target = execution.get("target_path") or execution.get("dll_path", "")
    cmd = [target, name] + [str(v) for v in args.values()]
    # Suppress any GUI window the binary might open (Windows only).
    creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
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


# ── Routes ──────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/tools", methods=["GET"])
def list_tools():
    return jsonify([inv["name"] for inv in INVOCABLES])


@app.route("/invoke", methods=["POST"])
def invoke():
    body = request.json or {}
    name = body.get("tool", "")
    args = body.get("args", {})
    result = _execute_tool(name, args)
    return jsonify({"result": result})


@app.route("/chat", methods=["POST"])
def chat():
    body = request.json or {}
    history = body.get("history", [])          # [{role, content}, ...]
    user_message = body.get("message", "").strip()
    if not user_message:
        return jsonify({"error": "message is required"}), 400

    client = OpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_BASE_URL") or None,
    )
    model = os.getenv("OPENAI_DEPLOYMENT", "gpt-4o-mini")

    system_prompt = (
        "You are a helpful assistant with access to binary tools from __COMPONENT_NAME__. "
        "When a user asks you to call or test a function, use the provided tools. "
        "Explain what the tool does and report its output clearly."
    )

    messages = (
        [{"role": "system", "content": system_prompt}]
        + history
        + [{"role": "user", "content": user_message}]
    )

    response = client.chat.completions.create(
        model=model,
        messages=messages,
        tools=OPENAI_FUNCTIONS or None,
        tool_choice="auto" if OPENAI_FUNCTIONS else "none",
    )

    msg = response.choices[0].message
    tool_outputs = []

    if msg.tool_calls:
        tool_messages = []
        for tc in msg.tool_calls:
            fn_name = tc.function.name
            try:
                fn_args = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                fn_args = {}
            result = _execute_tool(fn_name, fn_args)
            tool_outputs.append({"name": fn_name, "args": fn_args, "result": result})
            tool_messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result,
            })

        # Feed tool results back for a natural-language summary.
        messages.append(msg.model_dump(exclude_none=True))
        messages.extend(tool_messages)
        followup = client.chat.completions.create(model=model, messages=messages)
        reply = followup.choices[0].message.content or ""
    else:
        reply = msg.content or ""

    # Return updated history (strip system message so the client can replay it).
    updated_history = messages[1:]

    return jsonify({
        "reply": reply,
        "tool_outputs": tool_outputs,
        "updated_history": updated_history,
    })


@app.route("/download/invocables")
def download_invocables():
    """Serve the raw invocables list as a JSON download."""
    resp = app.response_class(
        response=json.dumps(INVOCABLES, indent=2),
        status=200,
        mimetype="application/json",
    )
    resp.headers["Content-Disposition"] = "attachment; filename=selected-invocables.json"
    return resp


if __name__ == "__main__":
    app.run(port=5000, debug=True)
'''

# ---------------------------------------------------------------------------
# Chat UI template
# ---------------------------------------------------------------------------
HTML_TEMPLATE = r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MCP Factory — __COMPONENT_NAME__</title>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  :root {
    --bg: #0d1117; --surface: #161b22; --border: #30363d;
    --accent: #58a6ff; --user-bg: #1f6feb; --tool-bg: #1a3a1a;
    --text: #c9d1d9; --muted: #8b949e; --error: #f85149;
    --radius: 10px; --font: system-ui, -apple-system, sans-serif;
  }
  body { background: var(--bg); color: var(--text); font-family: var(--font);
         display: flex; flex-direction: column; height: 100dvh; }
  header { background: var(--surface); border-bottom: 1px solid var(--border);
           padding: 12px 20px; display: flex; align-items: center;
           justify-content: space-between; flex-shrink: 0; }
  header h1 { font-size: 1rem; font-weight: 600; color: var(--accent); }
  header span { font-size: .8rem; color: var(--muted); }
  #download-btn {
    background: var(--surface); border: 1px solid var(--border); color: var(--accent);
    padding: 5px 14px; border-radius: 6px; cursor: pointer; font-size: .8rem;
    text-decoration: none; transition: background .15s;
  }
  #download-btn:hover { background: var(--border); }
  #chat-window { flex: 1; overflow-y: auto; padding: 20px;
                 display: flex; flex-direction: column; gap: 12px; }
  .bubble { max-width: 75%; padding: 10px 14px; border-radius: var(--radius);
            line-height: 1.5; font-size: .9rem; white-space: pre-wrap; word-break: break-word; }
  .bubble.user { background: var(--user-bg); align-self: flex-end;
                 border-bottom-right-radius: 3px; }
  .bubble.assistant { background: var(--surface); border: 1px solid var(--border);
                       align-self: flex-start; border-bottom-left-radius: 3px; }
  .bubble.error { background: #2d1117; border: 1px solid var(--error);
                   color: var(--error); align-self: flex-start; }
  .tool-block { background: var(--tool-bg); border: 1px solid #2e5c2e;
                border-radius: var(--radius); padding: 10px 14px; font-size: .8rem;
                align-self: flex-start; max-width: 75%; }
  .tool-block .tool-name { color: #3fb950; font-weight: 600; margin-bottom: 4px; }
  .tool-block .tool-args { color: var(--muted); margin-bottom: 4px; }
  .tool-block .tool-result { color: var(--text); white-space: pre-wrap; word-break: break-word; }
  .typing { align-self: flex-start; color: var(--muted); font-size: .85rem;
            padding: 6px 14px; animation: blink .9s infinite; }
  @keyframes blink { 0%,100% { opacity:.4 } 50% { opacity:1 } }
  footer { background: var(--surface); border-top: 1px solid var(--border);
           padding: 12px 16px; display: flex; gap: 10px; flex-shrink: 0; }
  #msg-input { flex: 1; background: var(--bg); border: 1px solid var(--border);
               color: var(--text); border-radius: 8px; padding: 10px 14px;
               font-size: .9rem; resize: none; height: 44px; line-height: 1.4;
               outline: none; transition: border .15s; }
  #msg-input:focus { border-color: var(--accent); }
  #send-btn { background: var(--accent); color: #000; border: none; border-radius: 8px;
              padding: 0 20px; font-size: .9rem; font-weight: 600; cursor: pointer;
              transition: opacity .15s; }
  #send-btn:disabled { opacity: .4; cursor: not-allowed; }
  ::-webkit-scrollbar { width: 6px; } ::-webkit-scrollbar-track { background: transparent; }
  ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
</style>
</head>
<body>
<header>
  <h1>MCP Factory &mdash; __COMPONENT_NAME__</h1>
  <div style="display:flex;align-items:center;gap:16px">
    <span id="model-label">model: gpt-4o-mini</span>
    <a id="download-btn" href="/download/invocables" download="selected-invocables.json">
      &#8595; Download invocables.json
    </a>
  </div>
</header>
<div id="chat-window">
  <div class="bubble assistant">
    Hi! I have access to the tools exported by <strong>__COMPONENT_NAME__</strong>.
    Ask me to call a function, describe what one does, or list available tools.
  </div>
</div>
<footer>
  <textarea id="msg-input" placeholder="Ask me to call a function…" rows="1"></textarea>
  <button id="send-btn">Send</button>
</footer>

<script>
  const chatWindow = document.getElementById('chat-window');
  const msgInput   = document.getElementById('msg-input');
  const sendBtn    = document.getElementById('send-btn');
  let history = [];

  function scrollToBottom() {
    chatWindow.scrollTop = chatWindow.scrollHeight;
  }

  function appendBubble(cls, text) {
    const d = document.createElement('div');
    d.className = `bubble ${cls}`;
    d.textContent = text;
    chatWindow.appendChild(d);
    scrollToBottom();
    return d;
  }

  function appendToolBlock(t) {
    const d = document.createElement('div');
    d.className = 'tool-block';
    const argsStr = Object.keys(t.args || {}).length
      ? JSON.stringify(t.args, null, 2) : '(no args)';
    d.innerHTML =
      `<div class="tool-name">&#10551; ${t.name}</div>` +
      `<div class="tool-args">args: ${argsStr}</div>` +
      `<div class="tool-result">${t.result}</div>`;
    chatWindow.appendChild(d);
    scrollToBottom();
  }

  function setLoading(v) {
    sendBtn.disabled = v;
    msgInput.disabled = v;
  }

  async function sendMessage() {
    const text = msgInput.value.trim();
    if (!text) return;
    msgInput.value = '';
    msgInput.style.height = '44px';

    appendBubble('user', text);
    setLoading(true);

    const typing = document.createElement('div');
    typing.className = 'typing';
    typing.textContent = 'Thinking…';
    chatWindow.appendChild(typing);
    scrollToBottom();

    try {
      const res = await fetch('/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, history }),
      });
      const data = await res.json();
      chatWindow.removeChild(typing);

      if (data.error) {
        appendBubble('error', 'Error: ' + data.error);
      } else {
        (data.tool_outputs || []).forEach(t => appendToolBlock(t));
        appendBubble('assistant', data.reply);
        history = data.updated_history || history;
      }
    } catch (err) {
      chatWindow.removeChild(typing);
      appendBubble('error', 'Network error: ' + err.message);
    }

    setLoading(false);
    msgInput.focus();
  }

  sendBtn.addEventListener('click', sendMessage);
  msgInput.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
  });
  msgInput.addEventListener('input', () => {
    msgInput.style.height = 'auto';
    msgInput.style.height = Math.min(msgInput.scrollHeight, 120) + 'px';
  });

  // Fetch and display model from server env
  fetch('/tools').then(r => r.json()).then(tools => {
    document.getElementById('model-label').textContent =
      `${tools.length} tools loaded`;
  }).catch(() => {});
</script>
</body>
</html>
'''

ENV_EXAMPLE = """\
# Copy to .env and fill in your credentials.
# Works with both api.openai.com (set OPENAI_BASE_URL=) and Azure OpenAI.

OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=
OPENAI_DEPLOYMENT=gpt-4o-mini
"""

REQUIREMENTS = """\
flask>=3.0
openai>=1.0
python-dotenv>=1.0
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _inject(template: str, component_name: str, invocables_json: str) -> str:
    """Replace all placeholder tokens in a template string."""
    return (
        template
        .replace("__COMPONENT_NAME__", component_name)
        .replace("__INVOCABLES_JSON__", invocables_json)
    )


def _write(path: str, content: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)
    print(f"  wrote {path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if not os.path.exists(INPUT_PATH):
        raise FileNotFoundError(f"Missing {INPUT_PATH}")

    with open(INPUT_PATH, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    component_name = data["component_name"]
    invocables = data["selected_invocables"]

    project_path = os.path.join(OUTPUT_BASE, component_name)
    static_path = os.path.join(project_path, "static")
    os.makedirs(static_path, exist_ok=True)

    invocables_json = json.dumps(invocables, indent=2)

    print(f"Generating MCP server for '{component_name}' ({len(invocables)} tools) …")

    _write(
        os.path.join(project_path, "server.py"),
        _inject(SERVER_TEMPLATE, component_name, invocables_json),
    )
    _write(
        os.path.join(static_path, "index.html"),
        _inject(HTML_TEMPLATE, component_name, invocables_json),
    )
    _write(os.path.join(project_path, "requirements.txt"), REQUIREMENTS)
    _write(os.path.join(project_path, ".env.example"), ENV_EXAMPLE)

    print(f"\nDone!  cd {project_path}")
    print("  pip install -r requirements.txt")
    print("  cp .env.example .env   # then fill in your API key")
    print("  python server.py")
    print("  open http://localhost:5000")


if __name__ == "__main__":
    main()
