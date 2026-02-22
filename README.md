# MCP Factory

> Automated generation of Model Context Protocol servers from Windows binaries

**Project:** USF CSE Senior Design Capstone - Microsoft Sponsored  
**Objective:** Enable AI agents to interact with Windows applications through automated MCP server generation

## Team

| Role | Member | GitHub |
|------|--------|--------|
| Lead & Sections 2-3 | Evan King | [@evanking12](https://github.com/evanking12) |
| Section 4 (MCP Generation) | Layalie AbuOleim | [@abuoleim1](https://github.com/abuoleim1) |
| Section 4 (MCP Generation) | Caden Spokas | [@bustlingbungus](https://github.com/bustlingbungus) |
| Section 5 (Verification) | Thinh Nguyen | [@TheNgith](https://github.com/TheNgith) |

## Business Scenario

Enterprise organizations need AI-powered customer service that can invoke existing internal tools lacking API documentation or modern integration points. MCP Factory bridges this gap by automatically analyzing Windows binaries and generating standards-compliant Model Context Protocol servers.

## Current Status

- [x] **Sections 2-3: Hybrid Discovery Engine** - **COMPLETE — Full Spec Coverage**
  - ✅ **Hybrid Analysis**: Multi-paradigm routing (`shell32.dll` → COM + Native exports)
  - ✅ **§2.a Installed-Instance Directory**: `--target` now accepts a directory (e.g. `C:\Program Files\AppD\`) — walks the tree, classifies every recognized file, runs per-file analysis, and writes an aggregate `<dir>_scan_mcp.json`
  - ✅ **Broad Source Coverage**: PE DLL/EXE, .NET, COM/TLB, RPC, CLI, SQL, 9 scripting languages (Python, PowerShell, Shell, Batch, VBScript, Ruby, PHP, JavaScript, TypeScript), **and all §1 legacy protocol formats** (OpenAPI, JSON-RPC, SOAP/WSDL, CORBA IDL, JNDI, PDB symbols)
  - ✅ **Uniform MCP JSON**: Every source type emits the same `{ name, kind, confidence, description, return_type, parameters, execution }` schema — zero structural differences across 22+ analyzed target types; `return_type` is always a string (`"unknown"` when not statically determinable)
  - ✅ **Correct Execution Metadata**: Each invocable carries a ready-to-use execution block (`dll_import`, `com_dispatch`, `python_subprocess`, `node`, `cscript`, `sql_exec`, `http_request`, `soap`, `corba_iiop`, `jndi_lookup`, etc.)
  - ✅ **Strict Artifact Hygiene**: No empty "ghost" files, no separator lines in descriptions, correct parameter names (ADR-0005)
  - ✅ **§3 Tool Selection**: `select_invocables.py` — displays full invocable list, filters by confidence, writes `selected-invocables.json` for §4
  - ✅ **Demo Suite**: 29/29 targets succeed across all source types (10 sections, including §2.a directory scan)
- [x] **Section 4: MCP Generation** - In progress (reads `selected-invocables.json`)
- [ ] **Section 5: Verification UI** - Interactive validation
- [ ] **Section 6: Deployment** - Azure integration

**Approach:** A **Hybrid Discovery Engine** that intelligently routes any target file to the appropriate analyzers based on detected capabilities, producing a uniform MCP JSON contract that §4 consumes directly.

## Platform Requirements

This tool is designed around Windows. If you are on a Mac, see [docs/mac-compatibility.md](docs/mac-compatibility.md).

## Prerequisites

**Required (install manually on Windows 10/11):**
- **PowerShell** 5.1+ (built into Windows 10+)
- **Python** 3.8+ — Download from [python.org](https://www.python.org/downloads/)
  - Add Python to PATH during installation (checked by default)
- **Git** — Download from [git-scm.com](https://git-scm.com)




## Installation

**Prerequisites:** Git, Python 3.8+, and Visual Studio Build Tools (for `dumpbin.exe`).

```powershell
# Clone and run the demo
git clone https://github.com/evanking12/mcp-factory.git
cd mcp-factory
pip install -r requirements.txt
python scripts/demo_all_capabilities.py
```

**Troubleshooting:** If you have multiple Python versions installed and `python` points to Python 2.x, use:
```powershell
py -3 -m pip install -r requirements.txt
py -3 scripts/demo_all_capabilities.py
```

## Quick Start

### 1. Capabilities Demo ⚡ (The "It Works" Demo)

**What you'll see:**

`demo_all_capabilities.py` runs 29 live analyses across all supported source types and reports per-target results:

```text
MCP FACTORY — ALL CAPABILITIES DEMO
=====================================

[Section 1: Native PE]
  kernel32.dll     ...  exports_mcp.json      1491 invocables
  user32.dll       ...  exports_mcp.json      1037 invocables
  zstd.dll         ...  exports_mcp.json        16 invocables

[Section 2: .NET Assemblies]
  System.dll       ...  dotnet_methods_mcp.json  143 invocables
  mscorlib.dll     ...  dotnet_methods_mcp.json   48 invocables

[Section 3: COM / Type Library]
  shell32.dll           ...  com_objects_mcp.json        482 invocables
  oleaut32.dll          ...  com_objects_mcp.json         12 invocables
  stdole2.tlb           ...  com_objects_mcp.json         50 invocables

[Section 4: CLI Tools]
  cmd.exe               ...  cli_mcp.json                  8 invocables
  git.exe               ...  cli_mcp.json                 35 invocables

[Section 5: SQL]
  sample.sql            ...  sql_file_mcp.json            14 invocables
  sqlite3.dll           ...  exports_mcp.json             16 invocables

[Section 6: Scripting Languages]
  sample.py             ...  python_script_mcp.json        5 invocables
  sample.ps1            ...  powershell_script_mcp.json    4 invocables
  sample.sh             ...  shell_script_mcp.json         5 invocables
  sample.bat            ...  batch_script_mcp.json         4 invocables
  sample.vbs            ...  vbscript_mcp.json             4 invocables
  sample.rb             ...  ruby_script_mcp.json          4 invocables
  sample.php            ...  php_script_mcp.json           5 invocables

[Section 7: JavaScript / TypeScript]
  sample.js             ...  javascript_mcp.json           6 invocables
  sample.ts             ...  typescript_mcp.json           5 invocables

[Section 8: RPC Interfaces]
  lsass.exe             ...  rpc_mcp.json                  8 invocables

[Section 9: Legacy Protocols & Spec Formats]
  sample_openapi.yaml   ...  openapi_spec_mcp.json         9 invocables
  sample_jsonrpc.json   ...  jsonrpc_spec_mcp.json         5 invocables
  sample.wsdl           ...  wsdl_file_mcp.json            7 invocables
  sample.idl            ...  corba_idl_mcp.json           12 invocables
  sample.jndi           ...  jndi_config_mcp.json         12 invocables
  zstd.pdb              ...  pdb_file_mcp.json           871 invocables

[Section 10: Directory Scan (§2.a installed-instance)]
  scripts/  (dir)       ...  scripts_scan_mcp.json      1184 invocables

Summary: 29 succeeded  0 skipped  (29 total)
```

**Why this matters:** Every output — regardless of source type — produces the same JSON schema that §4 consumes. A PE export, a Python function, and a SQL stored procedure all look identical to the MCP generator.

**Confidence levels:**
- **guaranteed:** Explicit metadata (type annotations, doc comments + return type)
- **high:** Partial docs or exported with header match
- **medium:** Pattern-matched, best effort
- **low:** Minimal information (symbol name only)

### 2. Analyze a Specific File or Installed Directory

To analyze a specific binary, script, or installed application directory:

```powershell
# Native DLL
python src/discovery/main.py --target "C:\Windows\System32\kernel32.dll" --out artifacts

# Script file
python src/discovery/main.py --target "path\to\service.py" --out artifacts

# OpenAPI / WSDL / IDL / JNDI / PDB — same command, format auto-detected
python src/discovery/main.py --target "api\openapi.yaml" --out artifacts

# Installed application directory (§2.a) — walks tree, analyses every recognized file
python src/discovery/main.py --target "C:\Program Files\MyApp\" --out artifacts
```

### 3. Analyze Windows CLI Tools

```powershell
# Extract arguments from any Windows command-line tool
python src/discovery/cli_analyzer.py "C:\Windows\System32\ipconfig.exe"
```

## validation_output/ Structure (Strict Hygiene)

The pipeline enforces **Strict Artifact Hygiene** (ADR-0005). Files are only generated when features are actually present.

```
demo_output/unified/
├── shell32.dll/
│   ├── shell32_exports_mcp.json        # ✅ native exports found
│   └── shell32_com_objects_mcp.json    # ✅ COM objects found
├── kernel32.dll/
│   └── kernel32_exports_mcp.json       # ✅ exports only (no COM → no com file)
├── sample.py/
│   └── sample_python_script_mcp.json   # ✅ functions found
└── sample.sql/
    └── sample_sql_file_mcp.json        # ✅ stored procs + tables + views found
```

**No more "empty success" files.** If a JSON exists, it contains usable, LLM-callable tools.



### Output Files (Demo Mode)

All results from the demo are saved to `demo_output/unified/`. The file format matches the **Stable v2.0.0 MCP JSON Schema**.

**Example structure:**
```
demo_output/unified/
├── kernel32.dll/
│   └── kernel32_exports_mcp.json        # Native exports
├── shell32.dll/
│   ├── shell32_exports_mcp.json         # Native exports
│   └── shell32_com_objects_mcp.json     # COM objects
├── mscorlib.dll/
│   └── mscorlib_dotnet_methods_mcp.json # .NET methods
├── sample.py/
│   └── sample_python_script_mcp.json    # Python functions
├── sample.sql/
│   └── sample_sql_file_mcp.json         # Stored procs, views, tables
└── sample.ts/
    └── sample_typescript_mcp.json       # TypeScript methods
```

Every JSON file has identical top-level structure:
```json
{
  "metadata": { "tier": 4, "target_name": "...", "target_type": "..." },
  "invocables": [
    {
      "name": "compress_file",
      "kind": "python_function",
      "confidence": "guaranteed",
      "description": "Compress source into dest using the specified level.",
      "return_type": "int",
      "parameters": [{"name": "source", "type": "string", "required": true}],
      "execution": {
        "method": "python_subprocess",
        "module_path": "...",
        "function_name": "compress_file"
      }
    }
  ],
  "summary": { "total_invocables": 1, "by_source_type": {"python_function": 1} }
}
```

**JSON Schema:** See [docs/schemas/discovery-output.schema.json](docs/schemas/discovery-output.schema.json) for the formal schema definition consumed by Section 4 (MCP generation).

## Advanced Usage

### Analyze Any DLL/EXE

Use `main.py` to target any file. The system will auto-detect if it's a Native DLL, COM Server, .NET Assembly, or CLI Tool (or a mix!).

```powershell
# Basic analysis
python src/discovery/main.py --target "path/to/file.dll" --out custom_output

# With C++ Headers (for higher confidence)
python src/discovery/main.py --target mylib.dll --headers include/ --out out

# Installed application directory
python src/discovery/main.py --target "C:\Program Files\MyApp\" --out custom_output
```

### 3. Interactive Invocable Selection (§2-3 hand-off to §4)

Run the selection UI to review discovered tools and choose what the MCP server exposes:

```powershell
# Single file
python src/ui/select_invocables.py --target tests/fixtures/vcpkg_installed/x64-windows/bin/zstd.dll

# Installed directory (§2.a) — same flag, directory support is transparent
python src/ui/select_invocables.py --target tests/fixtures/scripts/

# With a free-text hint (§2.b) — highlights matching rows in the table
python src/ui/select_invocables.py --target zstd.dll --description "compress decompress streaming"

# From an already-generated discovery JSON (skip re-analysis)
python src/ui/select_invocables.py --input artifacts/discovery-output.json
```

The UI defaults **guaranteed + high confidence ON**, medium + low OFF (§3.b). Commands: `<n>` toggle row, `3-10` range, `g` guaranteed+high only, `m` toggle medium, `l` toggle low, `a`/`n` all/none, `f <text>` filter, `done` save → `artifacts/selected-invocables.json`.

### Analyze Windows CLI Tools

```powershell
python src/discovery/cli_analyzer.py "C:\Program Files\Git\bin\git.exe"
```

## Repository Structure
```
mcp-factory/
├── scripts/
│   ├── demo_all_capabilities.py   # Main demo — 29 targets, all source types (10 sections)
│   ├── demo_legacy_protocols.py   # Standalone 6-target suite for spec-gap analyzers
│   ├── validate_features.py       # Validation suite
│   └── analyze_json_anomalies.py  # Hygiene verification
├── src/discovery/                 # Sections 2-3: Discovery pipeline
│   ├── main.py                    # CLI orchestrator — single file OR directory walk (§2.a)
│   ├── classify.py                # File-type detection (22+ source types)
│   ├── exports.py                 # Native PE exports (pefile)
│   ├── pe_parse.py                # .NET reflection
│   ├── com_scan.py                # COM registry + TLB scanning
│   ├── cli_analyzer.py            # CLI argument extraction
│   ├── rpc_scan.py                # RPC interface scanning
│   ├── sql_analyzer.py            # SQL stored procs, views, tables, triggers
│   ├── script_analyzer.py         # Python, PowerShell, Shell, Batch, VBScript, Ruby, PHP
│   ├── js_analyzer.py             # JavaScript + TypeScript
│   ├── openapi_analyzer.py        # OpenAPI 3.x / Swagger 2.x + JSON-RPC 2.0
│   ├── wsdl_analyzer.py           # SOAP / WSDL 1.1
│   ├── idl_analyzer.py            # CORBA IDL interfaces
│   ├── jndi_analyzer.py           # JNDI bindings (.properties, Spring XML)
│   ├── pdb_analyzer.py            # PDB debug symbols (dbghelp.dll)
│   └── schema.py                  # Unified Invocable schema → MCP JSON
├── src/ui/
│   └── select_invocables.py       # Interactive §3 selection UI (rich table, confidence filter)
├── src/generation/                # Section 4: MCP server generation
│   ├── section4_select_tools.py
│   └── section4_generate_server.py
├── tests/
│   └── fixtures/scripts/          # Sample files for all supported source types
│       ├── sample_openapi.yaml    # OpenAPI 3.0 fixture (9 operations)
│       ├── sample_jsonrpc.json    # JSON-RPC 2.0 fixture (5 methods)
│       ├── sample.wsdl            # WSDL 1.1 fixture (7 operations)
│       ├── sample.idl             # CORBA IDL fixture (12 methods)
│       └── sample.jndi            # JNDI fixture (12 bindings)
├── demo_output/unified/           # Generated demo artifacts (one sub-dir per target)
└── docs/
    ├── adr/                       # Architecture Decision Records (ADR-0001 → ADR-0007)
    ├── copilot-log/entries.md     # Session-by-session development log
    ├── sections-2-3.md            # §2-3 feature coverage reference (29/29 targets)
    └── schemas/                   # JSON schema contracts for Section 4
```

## Team Responsibilities

- **Sections 2-3 (Binary Analysis):** Evan King - DLL/EXE export discovery, header matching, tiered output
- **Section 4 (MCP Generation):** Layalie AbuOleim, Caden Spokas - JSON schema generation, tool definitions
- **Section 5 (Verification):** Thinh Nguyen - Interactive UI, LLM-based validation
- **Integration & Deployment:** Team effort - Azure deployment, CI/CD, documentation

##Section 4:
- run python src/generation/section4_select_tools.py
- It will print your invocables list (reads discovery-output.json which is a description of what a program can do)
You optionally remove some by number (user selects which tools are allowed)
You enter a component name
It writes: (saves selected-invocables.json) which is the filtered tool list
artifacts/selected-invocables.json this is the approved list of tools AI is allowed to call, without it section 4 doesnt know what to generate.
-the command: python3 src/generation/section4_generate_server.py generates runnable wrapper MCP server. satisfies requirement 4b
  Discovered tools
• Selected tools
• Generated MCP architecture
• Wrapped the executable
• Launched the server
test it with curl http://127.0.0.1:5000/tools
or curl -X POST http://127.0.0.1:5000/invoke \
-H "Content-Type: application/json" \
-d '{"tool":"get-account-balance","args":{"accountNumber":"12345"}}'
in a new terminal window


## Data Contract Stability (for Section 4)

Section 2-3 produces a stable JSON schema that Section 4 teams depend on:

- **Schema:** [docs/schemas/discovery-output.schema.json](docs/schemas/discovery-output.schema.json) - Formal JSON Schema
- **Versioning:** Breaking changes → v2.0. See [CHANGELOG.md](CHANGELOG.md)
- **For Section 4 teams:** Pin schema version in MCP generation to prevent drift

## Contributing

This is an active capstone project. For development setup and workflow guidelines, see [CONTRIBUTING.md](CONTRIBUTING.md).

## Documentation

| Document | Description |
|----------|-------------|
| [Project Description](docs/project_description.md) | Original sponsor requirements (Sections 1-7) |
| [Architecture](docs/architecture.md) | System design and component overview |
| [Sections 2-3 Details](docs/sections-2-3.md) | Binary discovery implementation |
| [Product Flow](docs/product-flow.md) | Full pipeline (Sections 2-5) |
| [Schemas](docs/schemas/) | JSON schema contracts for Section 4 |
| [ADRs](docs/adr/) | Architecture decision records |
| [Troubleshooting](docs/TROUBLESHOOTING.md) | Common issues and solutions |

---

**Sponsored by Microsoft** | Mentored by Microsoft Engineers  
_Last updated: February 22, 2026 — §2.a directory scan complete, 29/29 demo targets_
