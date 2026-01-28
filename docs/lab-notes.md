# Lab Notes

## 2026-01-19: Iteration 1 Foundation
**Goal:** Initialize repo + implement complete dumpbin→CSV→tiered analysis pipeline with fixtures.  
**Work done:**
- Implemented csv_script.py with 5-tier analysis (exports + headers + docs + demangle + metadata)
- Created run_fixtures.ps1 with vcpkg manifest automation and robust tool detection
- Set up zstd + sqlite3 test fixtures via vcpkg.json
- Auto-detection for dumpbin.exe and Visual Studio environment bootstrapping
- Verified outputs: 187 ZSTD exports, 294 sqlite3 exports with 96-98% header matching

**Verified outputs:**
- `artifacts/zstd_tier2_api_zstd_fixture.csv` (187 exports, 184 header-matched)
- `artifacts/sqlite3_tier2_api_sqlite3_fixture.csv` (294 exports, 282 header-matched)
- All tier outputs (1-5) verified for both fixtures
- Run time: ~5 minutes including vcpkg bootstrap

---

## 2026-01-20: Modular Architecture Design & Implementation
**Goal:** Plan architecture refactoring to enable feature expansion and team parallelization.  
**Work done:**
- Analyzed csv_script.py (500 lines, mixed concerns)
- Designed 8-module architecture with clear interfaces
- Created responsibility matrix and dependency graph
- Documented in ADR-0002 (decision rationale + implementation plan)
- **Implemented all 8 modules** with full integration testing

**Architecture Modules Created:**
- `schema.py` (80 lines): Invocable dataclass + CSV/JSON/MD writers
- `pe_parse.py` (100 lines): PE file parsing (dumpbin wrapper)
- `exports.py` (110 lines): Export normalization, demangling, forwarding
- `headers_scan.py` (260 lines): Header prototype extraction (migrated from csv_script.py)
- `docs_scan.py` (45 lines): Documentation correlation
- `classify.py` (85 lines): File type detection (PE/NET/script) + architecture (x86/x64/ARM64)
- `com_scan.py` (50 lines): COM registry analysis (stub for Section 4)
- `main.py` (300 lines): CLI orchestration with full pipeline

**Output Parity Verified:**
- zstd.dll: 187 exports, 184 matched to headers ✓
- sqlite3.dll: 294 exports, 282 matched to headers ✓
- CSV format matches csv_script.py exactly ✓
- All 5 tiers generated correctly ✓

**Implementation:** See ADR-0002 for comprehensive design rationale, alternatives considered, and feature roadmap. See copilot-log.md for extraction sequence and testing details.

---

## 2026-01-21: Confidence Scoring + Frictionless Deployment

**Goal:** Implement human-readable confidence analysis. Fix path resolution bugs in setup scripts. Create one-command reproducible setup for any Windows machine.

**Work Done:**

1. **Confidence Scoring** (6 factors, 3 tiers)
   - Implemented `score_confidence()` function:
     - Analyzes 6 factors: header_match, doc_comment, signature_complete, parameter_count, return_type, non_forwarded
     - Assigns confidence: HIGH (≥6), MEDIUM (≥4), LOW (<4)
   - Implemented `generate_confidence_summary()`:
     - Color-coded terminal output (RED=LOW, YELLOW=MEDIUM, GREEN=HIGH)
     - Sample exports per confidence level
     - Improvement suggestions (e.g., "Provide header files for 100% match")
     - Structured file output (`*_confidence_summary_*.txt`)

2. **Frictionless Setup**
   - Designed `scripts/setup-dev.ps1` with pre-flight checks:
     - Repository root detection (3-fallback chain)
     - Python 3.8+ validation
     - Git availability check
     - PowerShell 5.1+ confirmation
     - [+]/[-] ASCII indicators (green/red)
   - Fixed path resolution bugs in `run_fixtures.ps1`:
     - Issue: `$PSCommandPath` empty when invoked via `&` operator
     - Solution: 3-method fallback (PSCommandPath → MyInvocation → Get-Location)
     - Explicit validation before Split-Path to prevent empty string errors
   - Added vcpkg bootstrap detection and filtering (suppress LICENSE/Downloading output)

3. **Professional Polish**
   - "MCP Factory Development Setup" banner with visual hierarchy
   - Boot checks run before analysis (clean phase separation)
   - Fixed Unicode encoding issues (replaced ✓/✗ with ASCII [+]/[-])
   - Color-coded confidence output in terminal

**Test Results:**
- zstd.dll: 187 exports (8 HIGH [4.3%], 176 MEDIUM [94.1%], 3 LOW [1.6%])
  - Header match: 184/187 (98.4%)
- sqlite3.dll: 294 exports (8 HIGH [2.7%], 274 MEDIUM [93.2%], 12 LOW [4.1%])
  - Header match: 282/294 (95.9%)
- Setup time: 30-45 seconds on fresh machines
- Tested on 2+ Windows machines without pre-installed vcpkg ✓
- All 5 output tiers generated correctly ✓

**Files Modified:**
- `scripts/setup-dev.ps1`: Complete rewrite (100 lines) with boot checks + path detection
- `scripts/run_fixtures.ps1`: +25 lines (robust path resolution + filtering)
- `src/discovery/main.py`: +35 lines (score_confidence + generate_confidence_summary + ANSI colors)
- `README.md`: +40 lines (confidence analysis section + examples)

**Design Documentation:**
- ADR-0003 created: "Frictionless UX + Confidence Analysis" decision rationale
  - Rationale: Production-grade signal, transparency for Section 4 prioritization, user trust
  - Integration: Section 4 uses confidence metadata to auto-wrap HIGH exports
  - Alternatives considered: Skip confidence, static thresholds, no color coding

**Strategic Impact:**
- ✅ One-command setup (any Windows machine, any prerequisite state)
- ✅ Reproducible deployment (proven on 2+ machines)
- ✅ Transparent analysis quality (no guessing about result reliability)
- ✅ Section 4 enabled: Can prioritize HIGH confidence exports for auto-wrapping
- ✅ Professional signal: Frictionless UX demonstrates real engineering
- ✅ Microsoft-ready: Can be demoed in 30 seconds, proof of reproducibility

**Next Steps:**
- Push commits to GitHub (ready for Microsoft conversation)
- Week 2: Begin .NET reflection analysis (Section 2, Item 2)
- Coordinate with Section 4 on consuming confidence metadata

---

## 2026-01-22: Experiments Folder Strategy — Research Sandbox for Advanced Features

**Goal:** Establish a structured research environment for WIP features without destabilizing the production-ready src/discovery/ pipeline. Create clear tracking between experimental work and integration roadmap.

**Why We Went This Route:**

1. **Risk Management**
   - Main pipeline (src/discovery/) is working, tested, and reproducible
   - Experimentation could introduce regressions or breaking changes
   - Needed a sandbox to iterate on advanced features (CLI extraction, .NET reflection, PDB parsing)
   - Separating experiments/ from src/ protects the demo-ready foundation

2. **Team Coordination**
   - Section 4 (MCP Generation) depends on stable CSV/JSON output from src/discovery/
   - If teammates start contributing, experiments/ won't block their integration work
   - Clear contract: src/discovery/ is the stable API, experiments/ is forward-looking R&D
   - Feature parity tracking (FEATURES_AHEAD.md) shows what's ready to merge vs. what's still WIP

3. **Evidence-First Expansion**
   - DLL exports (src/) are well-understood: dumpbin → headers → confidence scoring
   - EXE CLI extraction requires new evidence sources: --help output, argument parsing heuristics
   - .NET reflection, COM type libraries, PDB symbols all need separate validation
   - Each new "invocable surface" gets prototyped in experiments/ with its own test harness before merging

**Work Done:**

1. **CLI Analyzer** (experiments/cli_analyzer.py)
   - Parses 4 help formats: `--help`, `/help`, `-h`, `/?`
   - Tested on 7 Windows tools (git, ipconfig, tasklist, robocopy, sfc, whoami, systeminfo)
   - Extracts 76 arguments + 35 subcommands with 100% success rate
   - Evidence: Which help format succeeded, exact output captured
   - Ready to merge: No breaking changes, just needs `--exe` flag in main.py

2. **Debug Suite** (experiments/debug_suite.py)
   - 9-breakpoint validation pipeline (classify → pe_parse → exports → headers → confidence)
   - PASS/WARN/SKIP/ERROR/CRITICAL status per module
   - Evidence ledger: Every claim cites source file + line number
   - Timing analysis: Identifies slow modules
   - Tested on kernel32.dll (1481 exports), git.exe, ipconfig.exe
   - Purpose: Catch regressions before they reach src/, validate integration candidates

3. **String Extractor** (experiments/string_extractor.py)
   - Fallback for binaries with no exports (packed/obfuscated DLLs)
   - Mines ASCII + UTF-16LE strings, detects Windows API patterns (Create*, Get*, Set*)
   - Confidence: HIGH (API prefix), MEDIUM (PascalCase), LOW (weak pattern)
   - Evidence: Byte offset in binary, encoding detected, pattern matched
   - Use case: When dumpbin returns zero exports, try string mining

4. **Feature Tracking** (FEATURES_AHEAD.md, ROADMAP.md)
   - FEATURES_AHEAD.md: Feature comparison table (experiments vs. src/)
     - Shows what's ready to merge (cli_analyzer, string_extractor, debug_suite)
     - Module parity table (classify, pe_parse, exports identical between folders)
     - Integration status per feature
   - ROADMAP.md: 10-tier roadmap with Section 2-3 progress tracker
     - Maps every sponsor requirement to implementation status (✅ DONE, 🔶 Planned)
     - Visual progress bars: 67% Section 2, 80% Section 3
     - Phased next steps: Week 2 (DLL+EXE), Weeks 3-4 (COM/.NET/PDB), Weeks 4-5 (Folder intake), Weeks 5-6 (Interactive UI)




---

## 2026-01-27: Hybrid Analysis & Production Hardening

**Goal:** Address "Siloed Analysis" limitations (missing features in hybrid files like `shell32.dll`) and fix "Artifact Noise" (empty reports for invalid features).

**Work done:**
- **Hybrid Routing Implementation:**
    - Refactored `main.py` to use "Capabilities Fall-through" logic.
    - `COM_OBJECT` files now fall through to `analyze_native_dll` if applicable.
    - `PE_EXE` files now explicitly attempt `analyze_com_object` (e.g., for GUI apps with registered interfaces).
- **Strict Artifact Hygiene (ADR-0005):**
    - **Noise Suppression:** Logic added to `analyze_com_object` to silently abort if 0 objects are found.
    - **Redundancy Removal:** Deleted code generating legacy _dotnet_methods.json duplicates.
- **Validation Suite Hardening:**
    - Updated `comprehensive_validation_safe.ps1` expectations for hybrid files.
    - Created `analyze_json_anomalies.py` for automated schema auditing.
    - Cleaned up ad-hoc test scripts to keep workspace strictly focused on the pipeline.

**Test Results:**
- **Validation Suite:** 11/11 tests passed across Native, .NET, COM, CLI, and RPC categories.
- **Hybrid verification:** `shell32.dll` correctly generates TWO artifacts (one for COM, one for Native).
- **Hygiene verification:** `kernel32.dll` generates ZERO COM artifacts (correctly).
- **Anomaly Check:** Scanned 30+ generated JSONs with 0 errors found.

**Files Modified:**
- `src/discovery/main.py`: +30 lines (routing logic), -15 lines (legacy removal)
- `scripts/comprehensive_validation_safe.ps1`: Updated test expectations
- `scripts/analyze_json_anomalies.py`: New utility

**Design Documentation:**
- **ADR-0005:** Hybrid Analysis & Strict Artifact Hygiene

