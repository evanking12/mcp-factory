# Sections 2–3: Target Binary Selection + Function Discovery

**Iteration 1 Deliverable**

## Overview

This is Iteration 1: a discovery prototype that covers DLL export inventory + header matching. Full Section 2–3 support (EXE/COM/RPC/registry scanning, richer hints, and interactive selection UX) is planned for later iterations.

This iteration implements the foundational discovery pipeline for DLL export analysis, covering project requirements Sections 2 and 3.

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

3. **Auto-Detection of Analysis Tools**
   - Automatically locates `dumpbin.exe` from VS 2022 installations
   - Searches: Community, Professional, Enterprise, BuildTools editions
   - Fallback to PATH if not in standard locations
   - Manual override: `--dumpbin "C:\path\to\dumpbin.exe"`

### What's Supported

- ✅ Single DLL analysis per invocation
- ✅ Windows PE/COFF DLL format (standard Windows DLLs)
- ✅ DLLs with standard export tables (ordinal + name exports)
- ✅ Forwarded exports (RVA = "--------", name = "Func = OtherDll.Func")

### What's Not Supported Yet

- ❌ Batch processing multiple DLLs in one command
- ❌ Interactive UI for DLL selection
- ❌ Auto-discovery of system DLLs
- ❌ .NET assemblies or managed code

## Section 3: Function Discovery & Display

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
