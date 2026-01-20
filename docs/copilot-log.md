# GitHub Copilot & Claude Development Log

**Project:** mcp-factory  
**Iteration:** 1 (Sections 2–3: Target Binary Selection + Function Discovery)  
**Note:** Tracks AI-assisted architectural and coding work. All output is reviewed, validated, and often enhanced with manual changes.

## 2026-01-19 — Fixture Harness + Robust Parser

**Task:** Complete discovery pipeline with automated testing, dumpbin auto-detection, robust export parsing, header matching, and tiered outputs.

**Combined Prompt:**
"Create a Python 3 script (csv_script.py) that runs dumpbin /exports on a DLL and generates tiered CSV/Markdown reports. Requirements: (1) Robust regex parser for dumpbin format with ordinal, hint, RVA, function name, and optional forwarding (handle both '00077410' and '--------' RVA); deduplicate by name; debug output if zero exports. (2) Header file scanning: recursively find .h/.hpp files, parse C/C++ function prototypes using regex, extract return types, parameters, and Doxygen-style doc comments (/// and /**); handle comment spans and nested parentheses. (3) Tiered analysis: Tier 1 (exports+headers+docs), Tier 2 (exports+headers), Tier 3 (exports+demangle), Tier 4 (exports only), Tier 5 (metadata). (4) CSV columns: Function, Ordinal, Hint, RVA, ForwardedTo, ReturnType, Parameters, Signature, DocComment, HeaderFile, Line, Demangled, DocFiles. (5) CLI args: --dll, --headers, --docs, --out, --tag, --exports-raw, --dumpbin, --undname, --no-demangle. (6) Auto-detect dumpbin.exe from VS 2022 locations if not specified. (7) Support manifest mode vcpkg. PLUS: Create PowerShell script (run_fixtures.ps1) that: accepts -VcpkgExe, -Triplet (default x64-windows), -OutDir (default artifacts), -DumpbinExe (optional, auto-detect), -ScriptPath; runs vcpkg install from tests/fixtures/ using manifest mode; locates DLLs in tests/fixtures/vcpkg_installed/<triplet>/bin/; runs Python script on zstd + sqlite3 with --headers and --tag; verifies outputs exist; prints sanity check (count ZSTD_ and sqlite3_ entries). Include tests/fixtures/vcpkg.json with zstd + sqlite3 dependencies."

**Copilot Output Accepted:**
- Complete csv_script.py structure with all 5 tiers
- Header file parsing with regex for prototypes
- Doxygen comment extraction logic
- run_fixtures.ps1 with vcpkg manifest mode workflow
- Auto-detection for dumpbin in VS 2022 paths
- CSV schema with 13 columns including Hint, RVA, ForwardedTo
- vcpkg.json manifest with zstd and sqlite3

**Manual Changes:**
1. **Fixed dumpbin detection bug:** Original `check_tool_available()` was called even when `--dumpbin` was a full path. Changed to: if `args.dumpbin == "dumpbin"`, use PATH check; else validate `Path(args.dumpbin).exists()`.
2. **Fixed vcpkg manifest mode paths:** Changed from `Join-Path $VcpkgRoot "installed\\$Triplet"` to `Join-Path $ManifestRoot "vcpkg_installed\\$Triplet"` (manifest mode installs locally, not to vcpkg root).
3. **Rewrote export parser regex:** Updated from `r"^\s*(\d+)\s+([0-9A-Fa-f]+)\s+([0-9A-Fa-f]+)\s+(\S+)\s*$"` to `r"^\s*(\d+)\s+([0-9A-Fa-f]+)\s+([0-9A-Fa-f]{8}|-------)\s+([^\s=]+)(?:\s*=\s*(\S+))?"` to handle forwarded exports and variable-length fields.
4. **Added debug output:** Print first 50 lines of dumpbin output to stderr if zero exports parsed; print "Debug - Command argv: [...]" to show exact dumpbin invocation.
5. **Updated .gitignore:** Added `__pycache__/`, `*.log`, organized into sections with comments.
6. **Removed duplicate directories:** Deleted `src/tests/scripts/` (accidental duplicate).
7. **README restructure:** Added Prerequisites section, "What Success Looks Like" with exact filenames and sizes, Troubleshooting section with 3 common issues, clearer Quick Start with numbered steps.

**Result:**
```powershell
.\scripts\run_fixtures.ps1 -VcpkgExe "$env:USERPROFILE\Downloads\vcpkg\vcpkg.exe"
```

**Expected Outputs in `artifacts/`:**
- `zstd_tier2_api_zstd_fixture.csv` (119 KB, 187 exports, 184 matched to headers)
- `zstd_tier4_api_zstd_fixture.csv` (17 KB, basic exports)
- `zstd_tiers_zstd_fixture.md` (tier summary)
- `zstd_exports_raw.txt` (14 KB, raw dumpbin)
- `sqlite3_tier2_api_sqlite3_fixture.csv` (89 KB, 294 exports, 282 matched to headers)
- `sqlite3_tier4_api_sqlite3_fixture.csv` (25 KB, basic exports)
- `sqlite3_tiers_sqlite3_fixture.md` (tier summary)
- `sqlite3_exports_raw.txt` (21 KB, raw dumpbin)

**Notes:**
- Manifest mode vcpkg creates `vcpkg_installed/` in the manifest directory, not in vcpkg root
- dumpbin auto-detection searches VS 2022 Community, Professional, Enterprise, BuildTools
- Forwarded exports (RVA = "--------") are captured in ForwardedTo column
- Header matching success rate: ~98% for zstd, ~96% for sqlite3

---

## 2026-01-20 — Architecture Design & Refactoring Strategy

**Task:** Design modular architecture for csv_script.py to enable feature expansion, improve testability, and unblock Section 4 team for parallel work.

**Context:** 
- csv_script.py is 500 lines with mixed concerns (parsing, extraction, enrichment, output)
- Need clean architecture before adding .NET/COM/CLI analyzers
- Section 4 team needs stable data contracts to design MCP schemas in parallel
- Total timeline is 12 weeks; must validate priorities with Microsoft before deep implementation

**Prompts Used:**
1. Copilot: "Design modular architecture for binary analysis pipeline with separate responsibilities for classify, parse, extract, enrich, output"
2. Claude: "Filter 50 ambitious features to high-ROI items given 12-week timeline and unknown requirements"  
3. Claude: "Documentation and git workflow best practices for academic capstone with sponsor review"

**Copilot Output Accepted:**
- 8-module architecture with clear input/output contracts per module
- Interface matrix (module dependencies and data flow)
- Testing strategy: unit tests per module + integration test against fixtures
- Dataclass design for Invocable record (unified callable representation)

**Manual Enhancements:**
1. **Feature filtering:** Started with 50 ambitious ideas (decompiler integration, ETW tracing, YARA rules), filtered to Tier A (5 items) based on:
   - Time-to-ROI ratio (what's doable in 1-2 days with high value?)
   - What unblocks Section 4 (JSON output is priority)
   - External dependency reduction (dumpbin removal improves portability)
   - Validation needed (don't over-optimize for unknown Microsoft priorities)

2. **Timeline mapping:** Each Tier A feature sized:
   - PE export parsing without dumpbin: 1.5 days (high value, moderate complexity)
   - Forwarder resolution: 1 day (solves real problem, simple logic)
   - JSON writer: 0.5 days (unblocks Section 4)
   - Architecture detection: 0.5 days (low complexity, prevents bugs)
   - Digital signatures: 1 day (trust/vendor info, moderate complexity)

3. **Team coordination design:** schema.py planned to be:
   - Importable by Section 4 team without csv_script.py dependencies
   - Single source of truth for "what is an Invocable?"
   - Enables parallel design of MCP schema generation

4. **Documentation strategy:** Clear separation of concerns:
   - lab-notes.md: What happened (decisions made, outcomes)
   - ADR-0003: Why (context, alternatives, tradeoffs)
   - copilot-log.md: How AI helped (prompts, outputs, manual changes)
   - git commits: Tied to ADRs, reference decision rationale

**Design Decisions & Rationale:**

| Decision | Rationale | Alternative | Trade-off |
|----------|-----------|-------------|-----------|
| Refactor before features | Modularization unblocks team + easier feature additions | Ship features on csv_script.py | 2-3 days refactoring time vs future flexibility |
| 8 modules | Single responsibility + testability + aligns with analyzer types (PE, .NET, COM) | Fewer larger modules | More files, clearer boundaries |
| Keep dumpbin initially | Proven, reduces refactoring risk; can replace incrementally | Direct PE parsing now | Depends on VS, but reduces scope of refactoring |
| Wait for Microsoft direction | Don't optimize for unknown requirements | Build all 50 features now | Some features may be wrong priorities |
| schema.py first | Foundation module; enables Section 4 to start design in parallel | Extract all modules in parallel | Sequentially dependent, but creates stable contract |

**Result:**
- ADR-0002: Modular Analyzer Architecture (comprehensive decision document)
- lab-notes.md: Updated with modularization plan
- Refactoring plan: Start Jan 21 with schema.py extraction
- Feature roadmap: See ADR-0002 for detailed plans

**Key Outcomes:**
✅ Architecture prioritizes team coordination (Section 4 can import schema.py independently)  
✅ Realistic feature pipeline avoids over-commitment  
✅ Decision rationale documented for Microsoft sponsor review  
✅ Modular design supports incremental improvements without breaking changes

**References:**
- vcpkg manifest mode: https://github.com/microsoft/vcpkg/blob/master/docs/users/manifests.md
- dumpbin reference: https://learn.microsoft.com/en-us/cpp/build/reference/dumpbin-reference

---

