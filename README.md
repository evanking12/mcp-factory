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
- **Git** — Download from [git-scm.com](https://git-scm.com)
- **Visual Studio Build Tools 2022** — Download from [visualstudio.microsoft.com](https://visualstudio.microsoft.com/downloads/)
  - During installation, **select the "Desktop development with C++" workload**
  - This installs `dumpbin.exe` and development tools (required for binary analysis)

**Auto-installed by setup script:**
- Python 3.8+ (auto-detects existing installation)
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

**The script handles everything:**
- ✅ Detects Python 3.8+ (or uses existing installation)
- ✅ Auto-detects/bootstraps vcpkg (~100 MB download, one-time)
- ✅ Auto-detects dumpbin from Visual Studio
- ✅ Installs zstd + sqlite3 test libraries
- ✅ Runs DLL export analysis on both
- ✅ **Shows confidence analysis with color-coded output** 🔴🟡🟢
- ✅ Generates detailed CSV/Markdown reports

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
- `zstd_tier2_api_zstd_fixture.csv` - Full analysis with headers (119 KB)
- `zstd_confidence_summary_zstd_fixture.txt` - Confidence breakdown

**SQLite3 (294 exports):**
- `sqlite3_tier2_api_sqlite3_fixture.csv` - Full analysis with headers (89 KB)
- `sqlite3_confidence_summary_sqlite3_fixture.txt` - Confidence breakdown

## Advanced Usage

### Analyze Your Own DLL

```powershell
python src/discovery/csv_script.py --dll path/to/your_library.dll --headers path/to/include/ --out ./results
```

See `python src/discovery/csv_script.py --help` for all options.

## What This Iteration Covers

This is Iteration 1: a discovery prototype that covers DLL export inventory + header matching. Full Section 2–3 support (EXE/COM/RPC/registry scanning, richer hints, and interactive selection UX) is planned for later iterations.

This release implements **Sections 2–3** of the project requirements:

- **Section 2: Target Binary Selection**
  - Accepts user-specified DLL paths (`--dll` parameter)
  - Supports vcpkg-installed dependencies for testing
  - Auto-detects dumpbin.exe from Visual Studio Build Tools

- **Section 3: Function Discovery & Display**
  - Extracts all exported functions via `dumpbin /exports`
  - Matches exports to header file prototypes (return types, parameters)
  - Parses Doxygen-style documentation comments
  - Generates tiered CSV/Markdown reports (5 levels: full → metadata only)
  - Captures function metadata: ordinal, hint, RVA, forwarding info

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

- Architecture: `docs/architecture.md`
- Product flow (Sections 2–5): `docs/product-flow.md`
- Schemas: `docs/schemas/`
- Compliance/Security/Cost: `docs/`
- References: `docs/references.md`

---

**Sponsored by Microsoft** | Mentored by Microsoft Engineers  
_Last updated: January 2026_
