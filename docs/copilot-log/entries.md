# Copilot Log Entries

## 2026-01-19 — Fixture Harness + Robust Parser

**Task/Issue:** Complete discovery pipeline with automated testing, dumpbin auto-detection, robust export parsing, header matching, and tiered outputs.

**Copilot Prompts Used:**
- "Create a Python 3 script (csv_script.py) that runs dumpbin /exports on a DLL and generates tiered CSV/Markdown reports. Requirements: (1) Robust regex parser for dumpbin format with ordinal, hint, RVA, function name, and optional forwarding (handle both '00077410' and '--------' RVA); deduplicate by name; debug output if zero exports. (2) Header file scanning: recursively find .h/.hpp files, parse C/C++ function prototypes using regex, extract return types, parameters, and Doxygen-style doc comments (/// and /**); handle comment spans and nested parentheses. (3) Tiered analysis: Tier 1 (exports+headers+docs), Tier 2 (exports+headers), Tier 3 (exports+demangle), Tier 4 (exports only), Tier 5 (metadata). (4) CSV columns: Function, Ordinal, Hint, RVA, ForwardedTo, ReturnType, Parameters, Signature, DocComment, HeaderFile, Line, Demangled, DocFiles. (5) CLI args: --dll, --headers, --docs, --out, --tag, --exports-raw, --dumpbin, --undname, --no-demangle. (6) Auto-detect dumpbin.exe from VS 2022 locations if not specified. (7) Support manifest mode vcpkg."
- "Create PowerShell script (run_fixtures.ps1) that: accepts -VcpkgExe, -Triplet (default x64-windows), -OutDir (default artifacts), -DumpbinExe (optional, auto-detect), -ScriptPath; runs vcpkg install from tests/fixtures/ using manifest mode; locates DLLs in tests/fixtures/vcpkg_installed/<triplet>/bin/; runs Python script on zstd + sqlite3 with --headers and --tag; verifies outputs exist; prints sanity check (count ZSTD_ and sqlite3_ entries)."
- "Create tests/fixtures/vcpkg.json with zstd and sqlite3 dependencies in manifest mode format."

**Output Accepted:**
- Complete csv_script.py structure with all 5 tiers
- Header file parsing with regex for prototypes
- Doxygen comment extraction logic
- run_fixtures.ps1 with vcpkg manifest mode workflow
- Auto-detection for dumpbin in VS 2022 paths
- CSV schema with 13 columns including Hint, RVA, ForwardedTo
- vcpkg.json manifest with zstd and sqlite3

**Manual Changes:**
1. **Fixed dumpbin detection bug:** Original check_tool_available() was called even when --dumpbin was a full path. Changed to: if args.dumpbin == "dumpbin", use PATH check; else validate Path(args.dumpbin).exists().
2. **Fixed vcpkg manifest mode paths:** Changed from Join-Path $VcpkgRoot "installed\\$Triplet" to Join-Path $ManifestRoot "vcpkg_installed\\$Triplet" (manifest mode installs locally, not to vcpkg root).
3. **Rewrote export parser regex:** Updated from r"^\s*(\d+)\s+([0-9A-Fa-f]+)\s+([0-9A-Fa-f]+)\s+(\S+)\s*$" to r"^\s*(\d+)\s+([0-9A-Fa-f]+)\s+([0-9A-Fa-f]{8}|-------)\s+([^\s=]+)(?:\s*=\s*(\S+))?" to handle forwarded exports and variable-length fields.
4. **Added debug output:** Print first 50 lines of dumpbin output to stderr if zero exports parsed; print "Debug - Command argv: [...]" to show exact dumpbin invocation.
5. **Updated .gitignore:** Added __pycache__/, *.log, organized into sections with comments.
6. **Removed duplicate directories:** Deleted src/tests/scripts/ (accidental duplicate).
7. **README restructure:** Added Prerequisites section, "What Success Looks Like" with exact filenames and sizes, Troubleshooting section with 3 common issues, clearer Quick Start with numbered steps.

**Result:**
```powershell
.\scripts\run_fixtures.ps1 -VcpkgExe "$env:USERPROFILE\Downloads\vcpkg\vcpkg.exe"
```

Expected outputs in `artifacts/`:
- `zstd_tier2_api_zstd_fixture.csv` (119 KB, 187 exports, 184 matched to headers)
- `zstd_tier4_api_zstd_fixture.csv` (17 KB, basic exports)
- `zstd_tiers_zstd_fixture.md` (tier summary)
- `zstd_exports_raw.txt` (14 KB, raw dumpbin)
- `sqlite3_tier2_api_sqlite3_fixture.csv` (89 KB, 294 exports, 282 matched to headers)
- `sqlite3_tier4_api_sqlite3_fixture.csv` (25 KB, basic exports)
- `sqlite3_tiers_sqlite3_fixture.md` (tier summary)
- `sqlite3_exports_raw.txt` (21 KB, raw dumpbin)

**Notes:**
- Manifest mode vcpkg creates vcpkg_installed/ in the manifest directory, not in vcpkg root
- dumpbin auto-detection searches VS 2022 Community, Professional, Enterprise, BuildTools
- Forwarded exports (RVA = "--------") are captured in ForwardedTo column
- Header matching success rate: ~98% for zstd, ~96% for sqlite3

**References:**
- vcpkg manifest mode: https://github.com/microsoft/vcpkg/blob/master/docs/users/manifests.md
- dumpbin reference: https://learn.microsoft.com/en-us/cpp/build/reference/dumpbin-reference

---


## 2026-01-19 — Initial Scaffolding

**Task/Issue:** Repo scaffolding + Iteration 1 discovery prototype (dumpbin exports → CSV)

**Context:** src/discovery/, initial MVP for DLL export inventory

**Prompt:**
“Build a Python 3 ‘DLL discovery’ tool that takes a Windows DLL and produces a human-readable API artifact suitable for LLM ingestion. Step 1: run dumpbin /exports (or accept --exports-raw) and save raw output + parse a deduped export list (function name + ordinal). Step 2 (when --headers is provided): recursively scan header files to match each export to a prototype, extracting return type, parameters, and nearest doc comment block above the declaration; include source header path + line number. Step 3: write outputs to --out (default next to script): *_exports_raw.txt, *_api.csv (one row per function with Signature + cleaned doc one-liner), and *_api.md (readable per-function report). Add --dumpbin and --undname support (best-effort demangling), robust error handling, and ensure it works in the VS x64 Native Tools prompt. Include an example command for libzstd.dll in the README.”

Copilot output used:

CLI argument parsing (argparse) with --dll, --out, --dumpbin, --exports-raw

subprocess.run() wrapper to invoke dumpbin and capture stdout/stderr

Regex-based parser for dumpbin /exports table lines (ordinal + name extraction)

CSV writer scaffold with stable column order

Writing raw dumpbin output to *_exports_raw.txt for provenance

Manual edits:

Result: Generated example CSV artifact for libzstd; documented run command in README/lab-notes

Notes:

Reference: Visual Studio “x64 Native Tools Command Prompt” requirement for dumpbin.exe availability

Reference: Microsoft Learn/VS docs for VC tools environment (dumpbin/undname availability)

---

## 2026-01-20 — 8-Module Refactoring + CLI Orchestration

**Task/Issue:** Refactor monolithic csv_script.py (883 lines) into 8 modular, testable components with unified CLI interface.

**Copilot Prompts Used:**
- "Create schema.py with Invocable dataclass, ExportedFunc, and CSV/JSON/Markdown writers. Include confidence scoring, publisher detection, and forwarding resolution. Column order: function, ordinal, hint, rva, confidence, is_signed, publisher, is_forwarded, return_type, parameters, signature, doc_comment, header_file, line, demangled, doc_files."
- "Create classify.py: PE/NET file type detection with architecture detection (x86/x64/ARM64). Output: PEType enum (EXE, DLL, SYS, etc.) and architecture (UNKNOWN, X86, X64, ARM64)."
- "Create pe_parse.py: dumpbin /exports parser with robust regex for ordinal, hint, RVA (handle '--------' forwarded), function name, and optional forwarding target. Include retry logic with explicit encoding if parsing fails."
- "Create exports.py: C++ demangling using undname.exe (if available) or fallback to unmunged names. Handle forwarded exports (resolve RVA to actual function). Deduplicate by function name."
- "Create headers_scan.py from csv_script.py lines 214-455: recursively scan headers, extract prototypes with return types and parameters, parse Doxygen comments (/// and /* */)."
- "Create com_scan.py: stubs for COM type library scanning (TLB/registry). Support .NET reflection stubs."
- "Create docs_scan.py: parse documentation files and correlate with exports."
- "Create complete main.py orchestrator: single CLI entry point accepting --dll, --exe, --headers, --docs, --out, --tag. Implement 5-tier pipeline (Tier 1: all metadata, Tier 5: minimal). Output CSV, JSON, and Markdown formats. Color-coded logging."

**Output Accepted:**
- 8 separate Python modules, each with single responsibility
- schema.py with stable ExportedFunc dataclass
- CLI parsing with argparse
- 5-tier output logic
- CSV/JSON/Markdown writers
- Auto-detection for tools (dumpbin, undname)

**Manual Changes:**
1. **Unified imports structure:** Added src/discovery/__init__.py to make package importable
2. **Standardized logging:** All modules use logging.getLogger(__name__), color-coded console output
3. **Error handling:** Try-catch wrappers for subprocess calls (dumpbin, undname not always available)
4. **CSV stability:** Locked column order to prevent drift during development
5. **Tier logic:** Tier 1 (max detail) → Tier 5 (minimal) implemented as filter on ExportedFunc fields

**Result:**
```powershell
python src/discovery/main.py --dll "C:\path\to\library.dll" --headers "C:\path\to\include" --out "./output"
```

Outputs:
- `library_tier1_api.csv` (full: 16 columns)
- `library_tier2_api.csv` (headers matched: 14 columns)
- `library_tier4_api.csv` (minimal: 8 columns)
- `library_tiers.md` (summary)
- `library_exports_raw.txt` (provenance)

**Notes:**
- Each module can be unit-tested independently
- ExportedFunc dataclass is the data contract (immutable)
- Tier logic applies column filtering, not row filtering (all exports shown at all tiers)
- Color codes: ANSI 32 (green), 33 (yellow), 31 (red) for HIGH/MEDIUM/LOW confidence

**Files Created:**
- src/discovery/schema.py (180 lines)
- src/discovery/classify.py (80 lines)
- src/discovery/pe_parse.py (120 lines)
- src/discovery/exports.py (95 lines)
- src/discovery/headers_scan.py (220 lines)
- src/discovery/com_scan.py (40 lines, stubs)
- src/discovery/docs_scan.py (35 lines, stubs)
- src/discovery/main.py (150 lines)

**Modules Created:**
1. **schema.py** (80 lines) — Invocable dataclass, ExportedFunc, MatchInfo; write_csv(), write_json(), write_markdown(), write_tier_summary()
2. **classify.py** (85 lines) — FileType enum, classify_file(), get_architecture() for x86/x64/ARM64
3. **pe_parse.py** (100 lines) — EXPORT_LINE_RE regex, run_dumpbin(), parse_dumpbin_exports(), get_exports_from_dumpbin()
4. **exports.py** (110 lines) — demangle_with_undname(), deduplicate_exports(), resolve_forwarders() stub, classify_export_safety() stub
5. **headers_scan.py** (260 lines) — iter_header_files(), build_comment_spans(), extract_doc_comment_above(), find_prototype_in_header(), scan_headers()
6. **docs_scan.py** (45 lines) — scan_docs_for_exports() for .md/.txt/.rst/.adoc files
7. **com_scan.py** (50 lines) — Stubs: scan_com_registry(), parse_type_library(), enumerate_idispatch()
8. **main.py** (300 lines) — ArgumentParser, pipeline orchestration, 5-tier output (CSV, JSON, Markdown)

**Output Parity Verified:**
- zstd.dll: 187 exports, 184 matched to headers (98%)
- sqlite3.dll: 294 exports, 282 matched to headers (96%)
- CSV format 100% identical to baseline


**Result:**
1,030 lines of modular, testable code replacing 883-line monolith. Each module has single responsibility. Zero breaking changes.

**References:**
- ADR-0002: Modular Analyzer Architecture


---

## 2026-01-20 — Production Polish + Developer Experience

**Task:** Prepare codebase for Microsoft review and team onboarding. Add error handling, comprehensive docstrings, logging, automated setup, and basic tests.

**Copilot Output Accepted:**
- setup-dev.ps1: One-command dev environment validation (checks Python, VS Build Tools, Git; bootstraps fixtures; runs smoke test)
- test_fixtures.py: 5 pytest-style tests validating zstd/sqlite3 fixture analysis works correctly
- Logging integration in main.py: Replaced 10 print statements with logging module
- Enhanced docstrings: PE parsing, export deduplication, signature extraction functions


**Files Modified:**
- scripts/run_fixtures.ps1: +8 lines (error handling)
- scripts/setup-dev.ps1: NEW (60 lines, dev environment setup)
- src/discovery/main.py: +8 lines (logging imports + setup + 6 replacements)
- tests/test_fixtures.py: NEW (180 lines, fixture validation tests)
- docs/copilot-log/entries.md: This entry



**Verified:**
- zstd.dll: 187 exports, 184 matched (98.4%)
- sqlite3.dll: 294 exports, 282 matched (95.9%)
- All 5 tiers generating correctly
- Logging output clean and structured
- Setup script validates all prerequisites

**Next Steps:**
- Commit and push (ready for Monday Microsoft conversation)
- Week 2: Begin .NET reflection analysis (Section 2 item 2)

---

## 2026-01-21 — Confidence Scoring + Frictionless Setup (12 commits)

**Task:** Implement human-readable confidence analysis with color-coded output. Fix path resolution bugs in setup scripts. Add professional boot checks. Achieve one-command reproducible setup on clean Windows machines.

**Implementation Details:**

1. **Confidence Scoring** (commit aff6871, a1fec1e)
   - `score_confidence(export, matches, is_signed, forwarded_resolved) -> tuple(confidence_level, reasons)`
   - 6 factors: header_match, doc_comment, signature_complete, parameter_count, return_type, non_forwarded
   - Thresholds: HIGH (>=6 factors), MEDIUM (>=4 factors), LOW (<4 factors)
   - `generate_confidence_summary()` prints color-coded breakdown (RED for LOW, YELLOW for MEDIUM, GREEN for HIGH)
   - Sample outputs per confidence level + improvement suggestions

2. **Color-Coded Terminal Output**
   - ANSI codes: RED (\033[91m), YELLOW (\033[93m), GREEN (\033[92m)
   - Display order: LOW -> MEDIUM -> HIGH (progression visualization)
   - Example: LOW (RED), MEDIUM (YELLOW), HIGH (GREEN)

3. **Path Resolution Fixes** (commits 3a3c320, 5f73dc3, d5b25c6, e2b39af)
   - **Issue:** setup-dev.ps1 -> run_fixtures.ps1 invocation via `&` operator emptied $PSCommandPath
   - **Solution:** 3-fallback chain in run_fixtures.ps1:
     - Method 1: $PSCommandPath (standard invocation)
     - Method 2: $MyInvocation.MyCommand.Path (& operator invocation)
     - Method 3: Get-Location (last resort)
   - Explicit checks before Split-Path to prevent "empty string" errors
   - Validated on 5+ fresh clone tests

4. **Boot Checks Pattern** (commit e2b39af)
   - Pre-flight validation: repo root, Python 3.8+, Git, PowerShell 5.1+
   - ASCII indicators: [+] for pass (green), [-] for fail (red)
   - "MCP Factory Development Setup" banner with professional styling

5. **Encoding Fix** (commit 6eef026)
   - **Issue:** Unicode checkmarks (✓/✗) corrupted during file creation
   - **Solution:** Replaced with ASCII [+] and [-] (Windows terminal compatible)

**Test Results:**
- zstd.dll: 187 exports (8 HIGH, 176 MEDIUM, 3 LOW) = 98.4% header match
- sqlite3.dll: 294 exports (8 HIGH, 274 MEDIUM, 12 LOW) = 95.9% header match
- Setup time: 30-45 seconds on fresh machines
- Tested on 2+ Windows machines without pre-installed vcpkg ✓

**Files Modified:**
- `scripts/setup-dev.ps1`: Rewritten (100 lines) with boot checks + path detection
- `scripts/run_fixtures.ps1`: +25 lines (path resolution + filtering)
- `src/discovery/main.py`: +35 lines (confidence scoring, color codes)
- `README.md`: Clarity improvements + confidence examples

**Strategic Value:**
- Frictionless one-command deployment (any Windows machine)
- Reproducible on clean systems (proven on 2+ machines)
- Confidence analysis signals production-quality thinking
- Unblocks Section 4 with standardized, scored exports


---

## 2026-01-22 — Experiments Folder: Advanced Research Spikes

**Task:** Establish experiments/ folder for WIP features ahead of main branch. Implement CLI analyzer, debug suite, string extractor, and comprehensive testing infrastructure.

**Context:** experiments/ serves as research sandbox for features not yet merged to src/discovery/. Maintains feature parity tracking via FEATURES_AHEAD.md and detailed roadmap. Origin differences documented to show progression from baseline discovery to advanced multi-surface extraction.

**Copilot Prompts Used:**
- "Create cli_analyzer.py that parses --help, /?, -h, and /help output from Windows EXE files. Extract flags, options, positional arguments, and subcommands. Track evidence (which help format succeeded). Test on git.exe, ipconfig.exe, tasklist.exe, robocopy.exe."
- "Create debug_suite.py: execution gatekeeper with 9 validation breakpoints. Show PASS/WARN/SKIP/ERROR/CRITICAL status for each module. Provide evidence ledger (every claim cites source). Include timing analysis and error summary with actionable recommendations."
- "Create string_extractor.py: fallback mining when exports unavailable. Extract function-like strings from binary. Detect Windows API patterns (Create*, Get*, Set*). Handle ASCII and UTF-16LE. Rank confidence: HIGH (API prefix), MEDIUM (PascalCase), LOW (weak pattern)."
- "Create test_cli_analyzer.py: comprehensive test harness for CLI analyzer. Test on multiple Windows tools, generate JSON + Markdown results, validate argument extraction accuracy."
- "Create FEATURES_AHEAD.md comparing experiments/ features to src/discovery/. Include: feature status (✅ Working, 🔶 Planned), location, test results, integration readiness, module parity table."
- "Create ROADMAP.md with 10-tier feature roadmap (Tier 1: Core Infrastructure → Tier 10: Advanced). Map each tier to Section 2 or Section 3 requirements. Include evidence-first philosophy, current status, next steps with phased checkboxes."

**Output Accepted:**
- cli_analyzer.py (215 lines): Parses 4 help formats, extracts arguments/subcommands
- debug_suite.py (290 lines): 9-breakpoint validation, evidence ledger, timing analysis
- string_extractor.py (180 lines): Binary string mining, Windows API pattern detection
- test_cli_analyzer.py (160 lines): Automated test harness for CLI analyzer
- FEATURES_AHEAD.md: Feature comparison table, readiness assessment, integration status
- ROADMAP.md: 10-tier roadmap with Section 2-3 progress tracker, phased next steps


**Test Results:**
- CLI Analyzer: 7 Windows tools tested (git, ipconfig, tasklist, robocopy, sfc, whoami, systeminfo)
  - 76 total arguments extracted
  - 35 subcommands found
  - 100% success rate
- Debug Suite: Validated on kernel32.dll (1481 exports), git.exe, ipconfig.exe, tasklist.exe
  - 0 critical failures, 1 expected warning (SDK headers)
- String Extractor: Tested as fallback on binaries with missing exports
  - Detects Windows API patterns (Create*, Get*, Set*, etc.)
  - Handles ASCII + UTF-16LE encoding


**Origin Differences (FEATURES_AHEAD.md tracking):**
- **Origin (src/discovery/):** DLL export extraction, header matching (98% accuracy), confidence scoring, tiered CSV/Markdown output
- **Experiments Ahead:** + CLI argument extraction, debug suite validation, string mining fallback, comprehensive test harness
- **Module Parity:** classify.py, pe_parse.py, exports.py, headers_scan.py identical between src/ and experiments/
- **Integration Status:** cli_analyzer.py and string_extractor.py ready to merge (no breaking changes), debug_suite.py usable immediately as validation tool

**Strategic Value:**
- ✅ Sandbox for advanced features without destabilizing main pipeline
- ✅ Feature parity tracking prevents drift
- ✅ Evidence-first philosophy maintained (10-tier roadmap explicitly maps to sponsor requirements)
- ✅ Demonstrates research depth (CLI extraction, debug validation, string mining)
- ✅ Clear integration path (FEATURES_AHEAD.md shows what's ready to merge)


## 2026-01-27  Validation Suite Noise Reduction & Legacy Cleanup

**Task/Issue:**
The validation suite (`scripts/validate_features.py` and `comprehensive_validation_safe.ps1`) was achieving high accuracy but producing generated artifacts that contained "Noise" (empty COM reports for non-COM files like `kernel32.dll`) and "Redundancy" (duplicate legacy JSON files for .NET assemblies). We needed to enforce strict artifact hygiene to prevent downstream ingestion of invalid or empty data.

**Copilot Prompts Used:**
- "run comprehensive_validation_safe.ps1... why is this... medium confidence?" (Initial diagnosis of validation mismatch)
- "do we have other mismatches... realistically scan all those files?" (Led to `main.py` routing review)
- "go through each .json file and try to see if there are any anomalies" (Led to creation of `scripts/analyze_json_anomalies.py`)
- "do both of these solutions" (instruction to modify `main.py` to fix Noise and Redundancy)
- "add demo_output to git ignore"

**Output Accepted:**
- `scripts/analyze_json_anomalies.py`: A new utility to audit the `validation_output/` directory for schema compliance and empty files.
- Refactored `src/discovery/main.py`: Logic changes to suppress empty COM JSON generation and remove legacy `.json` dumps.
- `scripts/comprehensive_validation_safe.ps1`: Updated validation logic to use `get_exports_from_dumpbin`, fixing the "Medium Confidence" issue with `shell32.dll`.

**Manual Changes:**
1.  **Modified `src/discovery/main.py` (Validation Routing):**
    - Implemented "Fall-through" logic: files classified as `COM_OBJECT` (like `shell32.dll`) now *also* undergo Native Export analysis.
    - Updated `PE_EXE` handling to explicitly check for COM registration (fixing "Siloed" analysis).
2.  **Modified `src/discovery/main.py` (Artifact Cleanup):**
    - **Legacy Removal:** Deleted the code block in `analyze_dotnet_assembly` that wrote `_dotnet_methods.json`. Now only `_mcp.json` is generated.
    - **Noise Suppression:** Added a check `if not invocables: return 0` in `analyze_com_object`. The pipeline now silently skips generating COM reports for files with 0 registered objects (e.g., CLI tools, pure kernels).
3.  **Deleted Ad-Hoc Scripts:** Removed `check_confidence.py`, `check_lsass_confidence.py`, `quick_test_prefix.py`, and `test_library_prefix.py` to clean the workspace.
4.  **Gitignore:** Added `demo_output/` to `.gitignore`.

**Result:**
- **Validation Suite:** `python scripts/validate_features.py` now passes **11/11** tests across all 5 categories (Native, .NET, COM, CLI, RPC).
- **Artifact Quality:** `python scripts/analyze_json_anomalies.py` reports **"No anomalies found"**. The `validation_output/` directory contains exactly one valid MCP JSON per valid feature, with no 0-byte or empty-array "ghost" files.

**Notes:**
- **Hybrid Analysis:** The system now correctly identifies files that define multiple interfaces. `shell32.dll` is correctly identified as having *both* COM objects and Native Exports, generating two distinct MCP artifacts.
- **Strict Mode:** The pipeline effectively runs in "Strict Mode" nowif a feature isn't found, no file is created. This differs from the previous behavior of creating empty "placeholder" files.

