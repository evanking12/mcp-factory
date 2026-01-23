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

## Current Status (Week 1)

- [x] **Sections 2-3: Binary Discovery** (Evan) - DLL export analysis with header matching - **WORKING**
  - ✅ 5/5 tests passing (zstd: 98.4% match, sqlite3: 95.9% match)
- [ ] **Section 4: MCP Generation** (Team) - JSON schema output
- [ ] **Section 5: Verification UI** (Team) - Interactive validation
- [ ] **Section 6: Deployment** (Team) - Azure integration

**Approach:** Phased delivery across 6 sections. Section 2-3 (binary discovery) is the foundation—extract what's callable, who calls it, how to invoke it. Sections 4-6 (MCP generation, verification UI, Azure deployment) consume this foundation in parallel.

## Prerequisites

**Required (install manually):**
- **PowerShell** 5.1+ (built into Windows 10+)
- **Python** 3.8+ — Download from [python.org](https://www.python.org/downloads/)
  - Add Python to PATH during installation (checked by default)
- **Git** — Download from [git-scm.com](https://git-scm.com)
- **Visual Studio Build Tools 2022** — Download from [visualstudio.microsoft.com](https://visualstudio.microsoft.com/downloads/)
  - During installation, **select the "Desktop development with C++" workload**
  - This installs `dumpbin.exe` and development tools (required for binary analysis)

**Auto-installed by setup script:**
- vcpkg (~100 MB, one-time download to `$env:USERPROFILE\Downloads\vcpkg`)
- zstd + sqlite3 test libraries

## Quick Start

### One-Command Setup ⚡ (Just Works)

```powershell
# Clone, set execution policy, run setup - that's it!
git clone https://github.com/evanking12/mcp-factory.git
cd mcp-factory
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\setup-dev.ps1
```

**Not working?** See [Troubleshooting Guide](docs/TROUBLESHOOTING.md) for solutions.

### Analyze Windows EXE Tools ⚡ (CLI Argument Extraction)

```powershell
# Extract arguments from any Windows command-line tool
python src\discovery\cli_analyzer.py "C:\Windows\System32\ipconfig.exe"
python src\discovery\cli_analyzer.py "C:\Windows\System32\whoami.exe"
```

**What you'll see:** Extracted flags, options, and subcommands with evidence of which help format worked.

### Validate Analysis Pipeline ⚡ (Debug Suite)

```powershell
# Run validation suite on your DLL exports
python src\discovery\debug_suite.py --file "artifacts\zstd_exports_raw.txt"
```

**What you'll see:** PASS/WARN/ERROR status for each pipeline module with timing analysis and evidence ledger.

### Batch Validation ⚡ (Production-Ready Testing)

```powershell
# Quick smoke test (~30 DLLs from system, ~4 seconds)
.\scripts\run_batch_validation.ps1 -Mode smoke

# Core validation (~200 DLLs, ~20 seconds) - recommended for demos
.\scripts\run_batch_validation.ps1 -Mode core

# Full validation (~466 DLLs, ~53 seconds) - comprehensive testing
.\scripts\run_batch_validation.ps1 -Mode full
```

**What you'll see:** Color-coded PASS/WARN/ERROR counts, metrics (files/second, avg time/file), and top 5 slowest files.

**Status meanings:**
- **[PASS]** = File successfully analyzed by debug_suite.py (all critical pipeline modules ran)
- **[WARN]** = File analyzed but with degraded functionality (e.g., no headers found, falls back to exports-only)
- **[ERROR]** = File analysis failed (corrupted binary, parsing error, pipeline crash)
- **[SKIPPED]** = File inaccessible (permission denied, locked by process)

**Note:** PASS means "pipeline ran successfully", not "functions are invokable". Invokability is determined by confidence scoring within the pipeline.
This is important going into future iterations -- before we can have a successful confidence summary, we must first ensure the code is not broken!

**The script handles everything:**
- ✅ Detects Python 3.8+ (or uses existing installation)
- ✅ Auto-detects/bootstraps vcpkg (~100 MB download, one-time)
- ✅ Auto-detects dumpbin from Visual Studio
- ✅ Installs zstd + sqlite3 test libraries
- ✅ Runs DLL export analysis on both
- ✅ **Shows confidence analysis with color-coded output** 🔴🟡🟢
- ✅ Generates detailed CSV + **JSON** + Markdown reports (see [schemas docs](docs/schemas/README.md))

### What You'll See

After running, you'll see colored confidence summaries like:

```
CONFIDENCE BREAKDOWN
------------------------------------------------------------
LOW     Confidence:   3 exports (  1.6%)
MEDIUM  Confidence: 176 exports ( 94.1%)
HIGH    Confidence:   8 exports (  4.3%)
```

Plus sample exports showing WHY each confidence level was assigned.

### Output Files

All results saved to `artifacts/`:

**ZSTD (187 exports):**
- `zstd_tier2_api_zstd_fixture.csv` - Tabular data (119 KB)
- `zstd_tier2_api_zstd_fixture.json` - **Structured JSON for Section 4** (320 KB)
- `zstd_tier2_api_zstd_fixture.md` - Human-readable report
- `zstd_confidence_summary_zstd_fixture.txt` - Confidence breakdown

**SQLite3 (294 exports):**
- `sqlite3_tier2_api_sqlite3_fixture.csv` - Tabular data (89 KB)
- `sqlite3_tier2_api_sqlite3_fixture.json` - **Structured JSON for Section 4** (375 KB)
- `sqlite3_tier2_api_sqlite3_fixture.md` - Human-readable report
- `sqlite3_confidence_summary_sqlite3_fixture.txt` - Confidence breakdown

**JSON Schema:** See [docs/schemas/discovery-output.schema.json](docs/schemas/discovery-output.schema.json) for the stable v2.0.0 schema consumed by Section 4 (MCP generation).

## Advanced Usage

### Analyze Your Own DLL

```powershell
python src/discovery/csv_script.py --dll path/to/your_library.dll --headers path/to/include/ --out ./results
```

See `python src/discovery/csv_script.py --help` for all options.


## Sample Output (for Section 4)

One exported function from discovery, in both formats:

**CSV row:**
```
function,ordinal,rva,confidence,is_signed,publisher,is_forwarded
ZSTD_compress,1,0x12345,High,True,Zstandard Project,False
```

**JSON object:**
```json
{"function":"ZSTD_compress","ordinal":1,"rva":"0x12345","confidence":"High","is_signed":true,"publisher":"Zstandard Project","is_forwarded":false}
```

Full sample outputs are generated during `setup-dev.ps1` in `artifacts/` directory (created at runtime). **Schema reference:** [docs/schemas/v1.0.json](docs/schemas/v1.0.json)

## Next Steps (Iteration 2+)

### High Priority (Weeks 2-3)
- **Section 4 Prep:** JSON schema generation foundation for MCP tool definitions
- **.NET Reflection:** Analyze .NET assemblies (CLR metadata, type information)
- **Type Library Parsing:** COM type information extraction from TLBs

### Medium Priority (Weeks 4-5)
- **Interactive UI:** Checkbox interface for excluding functions before schema generation
- **PDB Parsing:** Enhanced type information from program databases
- **Safety Annotations:** Automatic detection of thread safety, error codes, ownership

### Future (Weeks 6-8)
- **Section 5:** MCP schema to interactive validation chat UI
- **Azure Integration:** Deployment to Azure Container Instances
- **CLI Tools:** EXE command-line argument extraction and analysis
- **RPC/Registry:** Windows RPC endpoint and registry scanning

## Advanced Usage

### Direct Python Script

Analyze any DLL directly:

```powershell
# Basic analysis (exports only)
python src\discovery\main.py --dll "C:\path\to\your.dll" --out "output"

# Full analysis with header matching
python src\discovery\main.py --dll "C:\path\to\your.dll" --headers "C:\path\to\headers" --out "detailed_output"

# With documentation extraction
python src\discovery\main.py --dll "C:\path\to\your.dll" --headers "C:\path\to\headers" --docs "C:\path\to\docs" --out "full_output"

# Custom dumpbin path
python src\discovery\main.py --dll "C:\path\to\your.dll" --dumpbin "C:\custom\path\dumpbin.exe" --out "output"

# Show all options
python src\discovery\main.py --help
```

### Fixture Script Options

```powershell
# With auto-detection (recommended)
.\scripts\run_fixtures.ps1

# Explicit vcpkg path
.\scripts\run_fixtures.ps1 -VcpkgExe "$env:USERPROFILE\Downloads\vcpkg\vcpkg.exe"

# Custom output directory
.\scripts\run_fixtures.ps1 -OutDir "test_output"

# Different triplet (e.g., static linking)
.\scripts\run_fixtures.ps1 -Triplet "x64-windows-static"

# Specify dumpbin location
.\scripts\run_fixtures.ps1 -DumpbinExe "C:\Path\To\dumpbin.exe"
```

## One-Command Demo

For a completely automated setup from scratch:

```powershell
# Clone, setup, and run - everything is auto-detected
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\run_fixtures.ps1 -BootstrapVcpkg
```

Expected completion time: ~5 minutes (vcpkg clone/build + analysis).
Verify success: See 8 files in `artifacts/` directory matching the "What Success Looks Like" section above.

## Next Iteration Preview

**Planned for Iteration 2:**
- Interactive deselection UI (checkbox interface for excluding functions)
- JSON schema generation for MCP tool definitions
- PDB parsing for additional type information
- Safety wrapper annotations (error codes, ownership, thread safety)

## Repository Structure

```
mcp-factory/
├── scripts/                      # PowerShell automation
│   ├── run_fixtures.ps1         # Main fixture test runner
│   └── smoke_test.ps1           # Output verification
├── src/discovery/               # Section 2-3: Discovery pipeline
│   ├── main.py                  # CLI orchestrator
│   ├── schema.py                # Data models and CSV/JSON writers
│   ├── pe_parse.py              # PE header parsing
│   ├── classify.py              # File type detection
│   ├── exports.py               # Export enrichment (demangle, forwarding)
│   ├── headers_scan.py          # Header prototype matching
│   ├── docs_scan.py             # Documentation correlation
│   └── com_scan.py              # COM analysis (plugin registry)
├── tests/fixtures/              # Test dependencies
│   └── vcpkg.json               # vcpkg manifest (zstd, sqlite3)
├── artifacts/                   # Generated outputs (gitignored)
└── docs/
    ├── sections-2-3.md          # Current iteration scope
    └── copilot-log.md           # Development log
```

### Sanity Check Commands

Verify the CSVs contain expected exports:

```powershell
# Check for ZSTD_ functions (should find 180+ entries)
Select-String -Path "artifacts\zstd_tier2_api_zstd_fixture.csv" -Pattern "ZSTD_" | Measure-Object

# Check for sqlite3_ functions (should find 280+ entries)
Select-String -Path "artifacts\sqlite3_tier2_api_sqlite3_fixture.csv" -Pattern "sqlite3_" | Measure-Object

# View first 10 exports
Get-Content "artifacts\zstd_tier2_api_zstd_fixture.csv" | Select-Object -First 11
```

## Team Responsibilities

- **Sections 2-3 (Binary Analysis):** Evan King - DLL/EXE export discovery, header matching, tiered output
- **Section 4 (MCP Generation):** Layalie AbuOleim, Caden Spokas - JSON schema generation, tool definitions
- **Section 5 (Verification):** Thinh Nguyen - Interactive UI, LLM-based validation
- **Integration & Deployment:** Team effort - Azure deployment, CI/CD, documentation

## Data Contract Stability (for Section 4)

Section 2-3 produces a stable JSON schema that Section 4 teams depend on:

- **Schema:** [docs/schemas/v1.0.json](docs/schemas/v1.0.json) - Formal JSON Schema with required fields, types, and constraints
- **Versioning:** Breaking changes → v2.0. See [CHANGELOG.md](CHANGELOG.md)
- **For Section 4 teams:** Pin schema version in MCP generation to prevent drift

## Contributing

This is an active capstone project. For development setup and workflow guidelines, see [CONTRIBUTING.md](CONTRIBUTING.md).

Questions? Contact via GitHub issues or @evanking12.

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
