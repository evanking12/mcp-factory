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

