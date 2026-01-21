# Product Flow (Sections 2–5)

## 1) Setup & Validation (NEW - 2026-01-21)
System performs:
- Boot checks: repository root, Python 3.8+, Git, PowerShell 5.1+
- Auto-detection: vcpkg, Visual Studio, dumpbin.exe
- Bootstrap: Downloads vcpkg from GitHub if missing
- Fixture installation: Installs zstd + sqlite3 for testing

Output:
- Professional setup banner with [+]/[-] indicators
- Analysis output on test fixtures (zstd.dll, sqlite3.dll)
- Confidence analysis summaries (HIGH/MEDIUM/LOW breakdown)

## 2) Specify Target
Inputs supported:
- Path to binary file (e.g., `C:\...\app.exe`, `...\lib.dll`)
- Path to installed instance (e.g., `C:\Program Files\App\`)
- Free-text hints describing expected features

Outputs:
- Target registered as `target.json` with metadata (path/type/hints)

## 3) Display Invocables with Confidence Scoring
System produces `inventory.json` showing:
- invocable feature list
- confidence scoring (HIGH/MEDIUM/LOW based on 6 factors)
- provenance + confidence + risk level per export
- default: all selected
- color-coded summary (RED/YELLOW/GREEN)

User can:
- Review confidence breakdown
- Deselect low-confidence exports (if needed)
- Produce `selection.json`

## 4) Generate MCP Architecture
Inputs:
- `target.json`
- `selection.json` (with confidence metadata)
- generated component name (suggested)

Outputs:
- MCP server/tool package (generated code/config)
- deployed verification instance endpoint
- Auto-wrapping strategy: HIGH confidence → auto-generate, MEDIUM → flag for review, LOW → skip/manual

## 5) Verify Output
UI:
- chat interface to invoke tools
- displays stdout/stderr/results
- allows download of outputs/logs
- confidence metadata visible for each tool

