import json
import os

INPUT_PATH = os.path.join("artifacts", "selected-invocables.json")
OUTPUT_BASE = "generated"

def main():
    if not os.path.exists(INPUT_PATH):
        raise FileNotFoundError("Missing selected-invocables.json")

    with open(INPUT_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    component_name = data["component_name"]
    metadata = data["metadata"]
    invocables = data["selected_invocables"]

    project_path = os.path.join(OUTPUT_BASE, component_name)
    os.makedirs(project_path, exist_ok=True)

    exe_path = metadata["target_path"]

    # Create simple Flask server
    server_code = f"""
from flask import Flask, request, jsonify
import subprocess

app = Flask(__name__)

TARGET_EXECUTABLE = r\"{exe_path}\"

@app.route("/tools", methods=["GET"])
def list_tools():
    return jsonify({[inv["name"] for inv in invocables]})

@app.route("/invoke", methods=["POST"])
def invoke():
    data = request.json
    tool = data.get("tool")
    args = data.get("args", {{}})

    command = [TARGET_EXECUTABLE, tool]
    for value in args.values():
        command.append(str(value))

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10
        )

        return jsonify({{
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.returncode
        }})

    except Exception as e:
        return jsonify({{"error": str(e)}}), 500

if __name__ == "__main__":
    app.run(port=5000)
"""

    with open(os.path.join(project_path, "server.py"), "w", encoding="utf-8") as f:
        f.write(server_code)

    with open(os.path.join(project_path, "requirements.txt"), "w") as f:
        f.write("flask\n")

    print("Generated MCP server at:")
    print(project_path)

if __name__ == "__main__":
    main()
