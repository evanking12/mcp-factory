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

## Current Status (Week 3)

- [x] **Sections 2-3: Hybrid Discovery Engine** - **COMPLETE**
  - ✅ **Hybrid Analysis**: Correctly identifying multi-paradigm files (`shell32.dll` = COM + Native)
  - ✅ **Strict Artifact Hygiene**: No empty "ghost" files, redundancy removed (ADR-0005)
  - ✅ **Feature Validation**: 11/11 tests passing across Native, .NET, COM, CLI, and RPC
- [ ] **Section 4: MCP Generation** - JSON schema integration
- [ ] **Section 5: Verification UI** - Interactive validation
- [ ] **Section 6: Deployment** - Azure integration

**Approach:** We have moved from a simple batch analyzer to a **Hybrid Discovery Engine**. The pipeline now intelligently routes files based on capabilities (Native, COM, .NET, CLI) and enforces strict quality standards for generated MCP artifacts.

## Platform Requirements

**⚠️ Windows Only:** This tool is designed exclusively for Windows due to dependencies on:
- **PowerShell** (for .NET reflection and signature verification)
- **Windows Registry** (for COM object discovery)
- **pywin32** (pythoncom for Type Library parsing)
- **PE/COFF** Windows executable format

Mac/Linux support is not feasible without significant feature loss.

## Prerequisites

**Required (install manually on Windows 10/11):**
- **PowerShell** 5.1+ (built into Windows 10+)
- **Python** 3.8+ — Download from [python.org](https://www.python.org/downloads/)
  - Add Python to PATH during installation (checked by default)
- **Git** — Download from [git-scm.com](https://git-scm.com)
- **Visual Studio Build Tools 2022** — Download from [visualstudio.microsoft.com](https://visualstudio.microsoft.com/downloads/)
  - During installation, **select the "Desktop development with C++" workload**
  - This installs development tools (for binary analysis)


## Installation

**Prerequisites:** Git, Python 3.8+, and Visual Studio Build Tools (for `dumpbin.exe`).

```powershell
# Clone and run the demo
git clone https://github.com/evanking12/mcp-factory.git
cd mcp-factory
pip install -r requirements.txt
python scripts/demo_capabilities.py
```

**Troubleshooting:** If you have multiple Python versions installed and `python` points to Python 2.x, use:
```powershell
py -3 -m pip install -r requirements.txt
py -3 scripts/demo_capabilities.py
```

## Quick Start

### 1. Verification Suite ⚡ (The "It Works" Demo)

**What you'll see:**

The **Capabilities Demo** runs a live analysis and prints a real-time confidence dashboard:

```text
MCP FACTORY CAPABILITIES DEMO
=============================

Target           | Type              | Count  | Confidence
-----------------|-------------------|--------|-----------
kernel32.dll     | System API        | 1491   | HIGH
user32.dll       | UI System API     | 1037   | HIGH
System.dll       | .NET Assembly     | 9424   | GUARANTEED
oleaut32.dll     | COM Server        | 12     | HIGH
stdole2.tlb      | Type Library      | 50     | GUARANTEED
ws2_32.dll       | Network API       | 205    | HIGH
shell32.dll      | Hybrid COM/Native | 961    | GUARANTEED
```

**Why this matters:**
- **Guaranteed:** Extracted from explicit metadata (.NET Reflection, Type Libraries).
- **High:** Verified against known System APIs or Header hashes.
- **Medium:** Found via pattern matching (best effort).
- **Low:** Minimal symbols (standard export table only).

### 2. Analyze a Specific File

To analyze a specific binary and generate MCP artifacts:

```powershell
python src/discovery/main.py --dll "C:\Windows\System32\notepad.exe" --out "artifacts"
```

### 3. Analyze Windows CLI Tools

```powershell
# Extract arguments from any Windows command-line tool
python src/discovery/cli_analyzer.py "C:\Windows\System32\ipconfig.exe"
```

## validation_output/ Structure (Strict Hygiene)

The pipeline enforces **Strict Artifact Hygiene** (ADR-0005). We only generate files if features are *actually present*.

```
validation_output/
├── CLI/
│   └── ipconfig.exe/
│       └── ipconfig_cli_mcp.json       # ✅ CLI args found
├── COM/
│   └── ole32.dll/
│       └── ole32_com_objects_mcp.json  # ✅ COM objects found
│   └── kernel32.dll/
│       └── (NO FILE)                   # ✅ Correct: kernel32 has no COM objects
├── DOTNET/
│   └── System.dll/
│       └── System_dotnet_methods_mcp.json
└── NATIVE_DLL/
    └── zstd.dll/
        └── zstd_exports_mcp.json
```

**No more "empty success" files.** If a JSON exists, it contains usable tools for the AI agent.
- ✅ Generates detailed CSV + **JSON** + Markdown reports (see [schemas docs](docs/schemas/README.md))



### Output Files (Demo Mode)

All results from the demo are saved to `demo_output/`. The file format matches the **Stable v2.0.0 MCP JSON Schema**.

**Example structure:**
```
demo_output/
├── kernel32.dll/
│   └── kernel32_exports_mcp.json       # System APIs
├── shell32.dll/
│   ├── shell32_exports_mcp.json        # Native Exports
│   └── shell32_com_objects_mcp.json    # COM Objects
└── System.dll/
    └── System_dotnet_methods_mcp.json  # .NET Methods
```

**JSON Schema:** See [docs/schemas/discovery-output.schema.json](docs/schemas/discovery-output.schema.json) for the formal schema definition consumed by Section 4 (MCP generation).

## Advanced Usage

### Analyze Any DLL/EXE

Use `main.py` to target any file. The system will auto-detect if it's a Native DLL, COM Server, .NET Assembly, or CLI Tool (or a mix!).

```powershell
# Basic analysis
python src/discovery/main.py --dll "path/to/file.dll" --out "custom_output"

# With C++ Headers (for higher confidence)
python src/discovery/main.py --dll "mylib.dll" --headers "include/" --out "out"
```

### CLI Tool Analysis

Specifically target command-line arguments:

```powershell
python src/discovery/cli_analyzer.py "C:\Program Files\Git\bin\git.exe"
```

## Repository Structure
```
mcp-factory/
├── scripts/                      # PowerShell automation
│   ├── demo_capabilities.py      # Main demo runner
│   ├── validate_features.py      # Feature validation suite
│   ├── analyze_json_anomalies.py # Hygiene verification
│   └── run_fixtures.ps1          # (Legacy) Fixture runner
├── src/discovery/                # Section 2-3: Discovery pipeline
│   ├── main.py                   # CLI orchestrator
│   ├── analyze_dots.py           # .NET Reflection
│   ├── cli_analyzer.py           # CLI Argument parsing
│   ├── com_scan.py               # COM Registry scanning
│   ├── exports.py                # Native Exports
│   └── rpc_scan.py               # RPC Interface scanning
├── demo_output/                  # Generated demo artifacts
├── artifacts/                    # Legacy test artifacts
└── docs/                         # Documentation
```

## Team Responsibilities

- **Sections 2-3 (Binary Analysis):** Evan King - DLL/EXE export discovery, header matching, tiered output
- **Section 4 (MCP Generation):** Layalie AbuOleim, Caden Spokas - JSON schema generation, tool definitions
- **Section 5 (Verification):** Thinh Nguyen - Interactive UI, LLM-based validation
- **Integration & Deployment:** Team effort - Azure deployment, CI/CD, documentation

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
_Last updated: January 2026_
