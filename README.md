# MCP Factory

> Automated generation of Model Context Protocol servers from Windows binaries

**Project:** USF CSE Senior Design Capstone - Microsoft Sponsored  
**Team:** Evan King, Layalie AbuOleim, Caden Spokas, Thinh Nguyen  
**Objective:** Enable AI agents to interact with legacy Windows applications through automated MCP server generation

## Business Scenario

Enterprise organizations need AI-powered customer service that can invoke existing internal tools lacking API documentation or modern integration points. MCP Factory bridges this gap by automatically analyzing Windows binaries and generating standards-compliant Model Context Protocol servers.

## Current Status (Week 1)

- [x] **Sections 2-3: Binary Discovery** (Evan) - DLL export analysis with header matching - **WORKING**
- [ ] **Section 4: MCP Generation** (Team) - JSON schema output
- [ ] **Section 5: Verification UI** (Team) - Interactive validation
- [ ] **Section 6: Deployment** (Team) - Azure integration

## Key Features

- 🔍 **Zero-config setup** - Auto-detects vcpkg and Visual Studio toolchain
- 📊 **Tiered analysis** - 5 output levels from detailed to metadata-only
- 🧪 **Reproducible fixtures** - Automated test suite with zstd + sqlite3
- 📝 **Header matching** - Extracts function prototypes and Doxygen comments
- ⚡ **Fast execution** - Processes 500+ exports in seconds

## Prerequisites

- **Python 3.6+** - Ensure `python` is available in PATH
- **Visual Studio Build Tools** - Provides `dumpbin.exe` for DLL analysis (auto-detected from common VS 2022 locations)
- **PowerShell** - For running automation scripts
- **git** - For cloning vcpkg and this repository
- **vcpkg** - Package manager for installing test fixtures (see Quick Start)

## Quick Start

Run the complete fixture test with automatic tool detection:

```powershell
# 1. Clone this repo
git clone https://github.com/evanking12/mcp-factory.git
cd mcp-factory

# 2. Allow PowerShell scripts (one-time per session)
Set-ExecutionPolicy -Scope Process Bypass

# 3. Run fixture test (auto-installs vcpkg if needed, auto-detects dumpbin)
.\scripts\run_fixtures.ps1 -BootstrapVcpkg
```

**Alternative:** If you already have vcpkg installed:
```powershell
.\scripts\run_fixtures.ps1
```

The script will automatically:
- Locate vcpkg in PATH, `$env:USERPROFILE\Downloads\vcpkg`, or repo-local vcpkg
- Detect dumpbin.exe from Visual Studio installations
- Bootstrap into VS developer environment if needed

### What Success Looks Like

After running, you'll see these files in `artifacts/`:

**ZSTD (187 exports):**
- `zstd_tier2_api_zstd_fixture.csv` - Full analysis with headers (119 KB)
- `zstd_tier4_api_zstd_fixture.csv` - Basic exports (17 KB)
- `zstd_tiers_zstd_fixture.md` - Tier summary
- `zstd_exports_raw.txt` - Raw dumpbin output (14 KB)

**SQLite3 (294 exports):**
- `sqlite3_tier2_api_sqlite3_fixture.csv` - Full analysis with headers (89 KB)
- `sqlite3_tier4_api_sqlite3_fixture.csv` - Basic exports (25 KB)
- `sqlite3_tiers_sqlite3_fixture.md` - Tier summary
- `sqlite3_exports_raw.txt` - Raw dumpbin output (21 KB)

The script will print: `FIXTURE TEST COMPLETED SUCCESSFULLY` and show export counts.

## Troubleshooting

**"vcpkg not found"**
- The script auto-detects vcpkg in PATH and common locations
- Use `-BootstrapVcpkg` to auto-install: `.\scripts\run_fixtures.ps1 -BootstrapVcpkg`
- Or specify manually: `-VcpkgExe "$env:USERPROFILE\Downloads\vcpkg\vcpkg.exe"`

**"dumpbin not found in PATH"**
- The script auto-detects dumpbin from Visual Studio installations
- If detection fails, it will bootstrap into VS developer environment automatically
- Or specify manually: `-DumpbinExe "C:\Path\To\dumpbin.exe"`

**"cannot be loaded because running scripts is disabled"**
- Run: `Set-ExecutionPolicy -Scope Process Bypass` before the script

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

## What It Doesn't Cover Yet

- **Section 4: User Deselection UI** - No interactive checkbox interface for excluding functions
- **Section 5: MCP Generation** - No JSON schema output for Model Context Protocol tools
- **Section 6: Verification Chat UI** - No LLM-based validation interface
- **Azure/Aspire Integration** - Deployment pipeline not yet implemented

## Advanced Usage

### Direct Python Script

Analyze any DLL directly:

```powershell
# Basic analysis (exports only)
python src\discovery\csv_script.py --dll "C:\path\to\your.dll" --out "output"

# Full analysis with header matching
python src\discovery\csv_script.py --dll "C:\path\to\your.dll" --headers "C:\path\to\headers" --out "detailed_output"

# With documentation extraction
python src\discovery\csv_script.py --dll "C:\path\to\your.dll" --headers "C:\path\to\headers" --docs "C:\path\to\docs" --out "full_output"

# Custom dumpbin path
python src\discovery\csv_script.py --dll "C:\path\to\your.dll" --dumpbin "C:\custom\path\dumpbin.exe" --out "output"
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
│   ├── csv_script.py            # DLL export analyzer
│   └── README_csv_script.md     # Tool documentation
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
