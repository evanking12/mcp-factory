# Sections 2–3: Target Binary Selection + Function Discovery

**Status: Iteration 1 Complete (2026-01-21)**

## Overview

Section 2–3 discovery pipeline is fully functional and production-ready:
- ✅ DLL export extraction (100% reliable)
- ✅ Header matching (98%+ accuracy)
- ✅ Confidence analysis (human-readable scoring)
- ✅ Frictionless deployment (one-command setup)
- ✅ Color-coded output (professional presentation)

See [ADR-0002](adr/0002-modular-analyzer-architecture.md) (architecture) and [ADR-0003](adr/0003-frictionless-ux-confidence-analysis.md) (confidence + frictionless UX) for design decisions.

## Section 2: Target Binary Selection

### Current Implementation

The discovery pipeline accepts target DLLs through:

1. **Direct Path Specification**
   - CLI parameter: `--dll "C:\path\to\library.dll"`
   - Supports any Windows DLL with exported symbols
   - Validates file existence before processing

2. **Vcpkg Manifest Mode**
   - Test fixtures defined in `tests/fixtures/vcpkg.json`
   - Automated installation via `scripts/run_fixtures.ps1`
   - Currently includes: zstd, sqlite3
   - Frictionless setup: `Set-ExecutionPolicy -Scope Process Bypass; .\scripts\setup-dev.ps1`

3. **Auto-Detection of Analysis Tools**
   - Automatically locates `dumpbin.exe` from VS 2022 installations
   - Searches: Community, Professional, Enterprise, BuildTools editions
   - Fallback to PATH if not in standard locations
   - Manual override: `--dumpbin "C:\path\to\dumpbin.exe"`
   - Bootstraps vcpkg from GitHub if missing (no manual setup required)

### What's Supported

- ✅ Single DLL analysis per invocation
- ✅ Windows PE/COFF DLL format (standard Windows DLLs)
- ✅ DLLs with standard export tables (ordinal + name exports)
- ✅ Forwarded exports (RVA = "--------", name = "Func = OtherDll.Func")
- ✅ Auto-detection of all prerequisites (Python, Visual Studio, vcpkg, Git)
- ✅ One-command setup on clean Windows machines

### What's Not Supported Yet

- ❌ Batch processing multiple DLLs in one command (Iteration 2)
- ❌ Interactive UI for DLL selection (Iteration 2)
- ❌ Auto-discovery of system DLLs (Iteration 2)
- ❌ .NET assemblies or managed code (Section 3, future)

## Section 3: Function Discovery & Analysis

### Current Implementation

The discovery pipeline extracts and enriches function metadata through a multi-stage process:

#### Stage 1: Export Extraction
- Executes `dumpbin /exports <dll>` to retrieve raw export table
- Parses output using regex: `r"^\s*(\d+)\s+([0-9A-Fa-f]+)\s+([0-9A-Fa-f]{8}|--------)\s+([^\s=]+)(?:\s*=\s*(\S+))?"`
- Captures: ordinal, hint, RVA, function name, optional forwarding target
- Handles edge cases: forwarded exports, variable field widths, missing RVAs

#### Stage 2: Header File Matching
- Recursively scans `--headers` directory for `.h`/`.hpp` files
- Parses C/C++ function prototypes using regex patterns
- Extracts: return type, function name, parameter list
- Matches exports to prototypes by exact name
- Handles: nested parentheses, function pointers, multi-line declarations

#### Stage 3: Documentation Extraction
- Scans `--docs` directory for documentation files
- Recognizes Doxygen-style comments: `///` and `/** */`
- Associates doc comments with function signatures
- Preserves comment structure and formatting

#### Stage 4: Confidence Scoring (NEW, 2026-01-21)
- **6-Factor Analysis:**
  - header_match: Signature found in provided headers
  - doc_comment: Doxygen documentation present
  - signature_complete: Full parameter list extracted
  - parameter_count: >0 parameters (vs void)
  - return_type: Non-void return type
  - non_forwarded: Direct export (not delegated to another DLL)
- **Confidence Tiers:**
  - HIGH: ≥6 factors (most reliable, safe for auto-wrapping)
  - MEDIUM: ≥4 factors (high confidence, recommend review)
  - LOW: <4 factors (requires manual verification)
- **Output:** Color-coded terminal summary + sample exports per tier + improvement suggestions

#### Stage 5: Demangling (Optional)
- Supports C++ name demangling via `undname.exe` (if available)
- Disabled by default (`--no-demangle` is default behavior)
- Useful for analyzing C++ libraries with mangled exports

### Output Format: Tiered CSV/Markdown + Confidence Summary

The pipeline generates 5 tiers of analysis detail:

| Tier | Name | Contents | Use Case |
|------|------|----------|----------|
| 1 | Full Analysis | Exports + Headers + Docs + Demangle + Confidence | Complete API documentation |
| 2 | Header Match | Exports + Headers + Confidence | Prototype discovery (most used) |
| 3 | Demangle Only | Exports + Demangle | C++ symbol analysis |
| 4 | Exports Only | Basic export table | Minimal metadata |
| 5 | Metadata | Summary stats + confidence breakdown | Quick overview |

**CSV Columns (Tier 1/2):**
- `Function`: Exported symbol name
- `Ordinal`: Export table ordinal number
- `Hint`: Name table hint (optimization for loader)
- `RVA`: Relative Virtual Address (or "--------" for forwarded)
- `ForwardedTo`: Target DLL.Function for forwarded exports
- `ReturnType`: Function return type (from headers)
- `Parameters`: Function parameter list (from headers)
- `Signature`: Complete function signature
- `DocComment`: Extracted documentation
- `Confidence`: HIGH / MEDIUM / LOW (new)
- `HeaderFile`: Source header file path
- `Line`: Line number in header file
- `Demangled`: C++ demangled name (if applicable)
- `DocFiles`: Documentation file references

**Confidence Summary File** (`*_confidence_summary_*.txt`):**
```
============================================================
CONFIDENCE ANALYSIS SUMMARY
============================================================

DLL: zstd.dll
Total Exports: 187

CONFIDENCE BREAKDOWN
LOW     Confidence:   3 exports (  1.6%)
MEDIUM  Confidence: 176 exports ( 94.1%)
HIGH    Confidence:   8 exports (  4.3%)

SAMPLE EXPORTS BY CONFIDENCE
[HIGH] ZSTD_compress
[HIGH] ZSTD_decompress
...
[MEDIUM] ZSTD_isError
...
[LOW] ZSTD_versionNumber
...

WAYS TO IMPROVE CONFIDENCE
- Provide header files: Would improve header_match factor
- Ensure undname.exe available: Helps identify C++ mangled names
```

### Validation & Quality Metrics

The fixture test (`scripts/run_fixtures.ps1`) validates discovery quality:

**ZSTD (187 total exports):**
- 184/187 matched to headers (98.4% match rate)
- Confidence distribution: 8 HIGH (4.3%), 176 MEDIUM (94.1%), 3 LOW (1.6%)
- All `ZSTD_*` prefixed functions captured
- Header match from: `zstd.h`, `zdict.h`, `zstd_errors.h`

**SQLite3 (294 total exports):**
- 282/294 matched to headers (95.9% match rate)
- Confidence distribution: 8 HIGH (2.7%), 274 MEDIUM (93.2%), 12 LOW (4.1%)
- All `sqlite3_*` prefixed functions captured
- Header match from: `sqlite3.h`, `sqlite3ext.h`

### Deployment & Reproducibility

**One-Command Setup:**
```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\setup-dev.ps1
```

**What Happens:**
1. Boot checks: Validates repo root, Python, Git, PowerShell
2. Auto-detection: Finds vcpkg, Visual Studio, dumpbin
3. Bootstrap: Downloads & builds vcpkg (if missing)
4. Install: Runs `vcpkg install` for zstd + sqlite3
5. Analysis: Runs analysis on both DLLs
6. Output: Generates confidence summaries + CSVs + Markdown

**Setup Time:** 30-45 seconds (on clean Windows machines, no pre-installed tools)  
**Tested:** 2+ machines with Windows 10/11, VS 2022 Community

### What's Supported

- ✅ Ordinal + name exports
- ✅ Forwarded exports (cross-DLL function aliases)
- ✅ C function prototypes
- ✅ C++ function prototypes (basic patterns)
- ✅ Doxygen documentation comments
- ✅ Multi-line function declarations
- ✅ Function pointers in parameters
- ✅ Confidence-driven prioritization for downstream (Section 4)
- ✅ Professional color-coded terminal output
- ✅ Frictionless one-command deployment

### What's Not Supported Yet

- ❌ Interactive deselection UI (checkboxes to exclude functions) → Iteration 2
- ❌ User-driven confidence overrides → Future
- ❌ Advanced C++ templates (partial support only) → Future
- ❌ COM/ATL interfaces (vtable analysis) → Future
- ❌ Inline assembly stubs → Future
- ❌ Export-by-ordinal-only (no name in export table) → Future

## Integration with Section 4 (MCP Generation)

**Confidence metadata enables intelligent prioritization:**
- **HIGH confidence** exports → Auto-generate MCP tool definition (minimal review needed)
- **MEDIUM confidence** exports → Auto-generate + flag for review
- **LOW confidence** exports → Skip or require manual specification

**Example:**
```json
{
  "function": "ZSTD_compress",
  "ordinal": 1,
  "confidence": "HIGH",
  "confidence_factors": [
    "header_match",
    "signature_complete",
    "parameter_count",
    "non_forwarded"
  ],
  "mcp_wrapper_auto_generated": true
}
```

Section 4 can use `confidence` field to decide whether to auto-wrap or require human review.

## Testing & Verification

### Automated Fixture Test

```powershell
.\scripts\run_fixtures.ps1 -VcpkgExe "C:\vcpkg\vcpkg.exe"
```

**Expected Outputs:**
- 8 files in `artifacts/` (4 per DLL: tier2, tier4, tiers.md, exports_raw.txt)
- 2 confidence summary files (one per DLL)
- `FIXTURE TEST COMPLETED SUCCESSFULLY` message
- Sanity check: ZSTD_ count ≈ 187, sqlite3_ count ≈ 294
- Confidence breakdown shown in color (RED/YELLOW/GREEN)

### Smoke Test

```powershell
.\scripts\smoke_test.ps1
```

**Verifies:**
- Tier2 CSV files exist
- CSV files contain expected function prefixes
- File sizes within expected ranges
- Confidence summary files present

## Known Limitations

1. **No Duplicate Export Handling**: If a DLL exports the same name multiple times (different ordinals), only the first is captured
2. **Header Matching Heuristic**: Relies on exact name match; doesn't handle renamed exports or wrapper functions
3. **No PDB Integration**: Type information is limited to what's in headers (no debug symbols)
4. **Single-Threaded**: Large DLLs with thousands of exports may take several seconds
5. **Confidence is Deterministic**: Based on heuristics; doesn't account for domain-specific safety requirements (may add in future)

## Next Iteration Scope

See parent [docs/product-flow.md](product-flow.md) for full project roadmap.

**Iteration 2 (Sections 4–5, Feb):**
- Interactive deselection UI (exclude unwanted functions)
- JSON schema generation for MCP tool definitions (using confidence tiers)
- PDB parsing for enhanced type information
- Safety wrapper annotations
- Web-based UI for confidence filtering

**Future Iterations:**
- Verification chat UI (LLM-based validation)
- Azure/Aspire deployment pipeline
- Semantic analysis (infer function purpose from names/signatures)
- External documentation sources (GitHub, docs.rs, etc.)


### Current Implementation

The discovery pipeline extracts and enriches function metadata through a multi-stage process:

#### Stage 1: Export Extraction
- Executes `dumpbin /exports <dll>` to retrieve raw export table
- Parses output using regex: `r"^\s*(\d+)\s+([0-9A-Fa-f]+)\s+([0-9A-Fa-f]{8}|--------)\s+([^\s=]+)(?:\s*=\s*(\S+))?"`
- Captures: ordinal, hint, RVA, function name, optional forwarding target
- Handles edge cases: forwarded exports, variable field widths, missing RVAs

#### Stage 2: Header File Matching
- Recursively scans `--headers` directory for `.h`/`.hpp` files
- Parses C/C++ function prototypes using regex patterns
- Extracts: return type, function name, parameter list
- Matches exports to prototypes by exact name
- Handles: nested parentheses, function pointers, multi-line declarations

#### Stage 3: Documentation Extraction
- Scans `--docs` directory for documentation files
- Recognizes Doxygen-style comments: `///` and `/** */`
- Associates doc comments with function signatures
- Preserves comment structure and formatting

#### Stage 4: Demangling (Optional)
- Supports C++ name demangling via `undname.exe` (if available)
- Disabled by default (`--no-demangle` is default behavior)
- Useful for analyzing C++ libraries with mangled exports

### Output Format: Tiered CSV/Markdown

The pipeline generates 5 tiers of analysis detail:

| Tier | Name | Contents | Use Case |
|------|------|----------|----------|
| 1 | Full Analysis | Exports + Headers + Docs + Demangle | Complete API documentation |
| 2 | Header Match | Exports + Headers | Prototype discovery |
| 3 | Demangle Only | Exports + Demangle | C++ symbol analysis |
| 4 | Exports Only | Basic export table | Minimal metadata |
| 5 | Metadata | Summary stats | Quick overview |

**CSV Columns (Tier 1/2):**
- `Function`: Exported symbol name
- `Ordinal`: Export table ordinal number
- `Hint`: Name table hint (optimization for loader)
- `RVA`: Relative Virtual Address (or "--------" for forwarded)
- `ForwardedTo`: Target DLL.Function for forwarded exports
- `ReturnType`: Function return type (from headers)
- `Parameters`: Function parameter list (from headers)
- `Signature`: Complete function signature
- `DocComment`: Extracted documentation
- `HeaderFile`: Source header file path
- `Line`: Line number in header file
- `Demangled`: C++ demangled name (if applicable)
- `DocFiles`: Documentation file references

### Validation & Quality Metrics

The fixture test (`scripts/run_fixtures.ps1`) validates discovery quality:

**ZSTD (187 total exports):**
- 184/187 matched to headers (98.4% match rate)
- All `ZSTD_*` prefixed functions captured
- Header match from: `zstd.h`, `zdict.h`, `zstd_errors.h`

**SQLite3 (294 total exports):**
- 282/294 matched to headers (95.9% match rate)
- All `sqlite3_*` prefixed functions captured
- Header match from: `sqlite3.h`, `sqlite3ext.h`

### What's Supported

- ✅ Ordinal + name exports
- ✅ Forwarded exports (cross-DLL function aliases)
- ✅ C function prototypes
- ✅ C++ function prototypes (basic patterns)
- ✅ Doxygen documentation comments
- ✅ Multi-line function declarations
- ✅ Function pointers in parameters

### What's Not Supported Yet

- ❌ Interactive deselection UI (checkboxes to exclude functions)
- ❌ User-driven filtering (e.g., "exclude internal functions")
- ❌ Advanced C++ templates (partial support only)
- ❌ COM/ATL interfaces (vtable analysis)
- ❌ Inline assembly stubs
- ❌ Export-by-ordinal-only (no name in export table)

## Testing & Verification

### Automated Fixture Test

```powershell
.\scripts\run_fixtures.ps1 -VcpkgExe "C:\vcpkg\vcpkg.exe"
```

**Expected Outputs:**
- 8 files in `artifacts/` (4 per DLL: tier2, tier4, tiers.md, exports_raw.txt)
- `FIXTURE TEST COMPLETED SUCCESSFULLY` message
- Sanity check: ZSTD_ count ≈ 187, sqlite3_ count ≈ 294

### Smoke Test

```powershell
.\scripts\smoke_test.ps1
```

**Verifies:**
- Tier2 CSV files exist
- CSV files contain expected function prefixes
- File sizes within expected ranges

## Known Limitations

1. **No Duplicate Export Handling**: If a DLL exports the same name multiple times (different ordinals), only the first is captured
2. **Header Matching Heuristic**: Relies on exact name match; doesn't handle renamed exports or wrapper functions
3. **No PDB Integration**: Type information is limited to what's in headers (no debug symbols)
4. **Single-Threaded**: Large DLLs with thousands of exports may take several seconds

## Next Iteration Scope

See parent [docs/product-flow.md](product-flow.md) for full project roadmap.

**Iteration 2 (Sections 4–5):**
- Interactive deselection UI (exclude unwanted functions)
- JSON schema generation for MCP tool definitions
- PDB parsing for enhanced type information
- Safety wrapper annotations

**Future Iterations:**
- Verification chat UI (LLM-based validation)
- Azure/Aspire deployment pipeline
- Web-based dashboard
