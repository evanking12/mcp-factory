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

## 2026-01-20: Modular Architecture Design
**Goal:** Plan architecture refactoring to enable feature expansion and team parallelization.  
**Work done:**
- Analyzed csv_script.py complexity (500 lines, mixed responsibilities)
- Designed 8-module architecture with clean input/output contracts
- Created module responsibility matrix and dependency graph
- Planned Tier A feature implementation (5 high-ROI items)
- Documented architecture in ADR-0003, implementation plan in lab-notes

**Architecture Modules (8 total):**
- `schema.py`: Invocable dataclass + CSV/JSON/MD writers (foundation)
- `pe_parse.py`: PE file parsing (wraps dumpbin, will replace)
- `exports.py`: Export normalization, demangling, forwarding
- `headers_scan.py`: Header prototype extraction (existing regex)
- `docs_scan.py`: Documentation correlation
- `classify.py`: File type detection (PE/NET/script) - stub
- `com_scan.py`: COM registry analysis - stub
- `main.py`: CLI orchestration

**Implementation Plan:**
- **Jan 21-22:** Extract modules + create unit tests (2-3 days)
- **Jan 23-27:** Implement Tier A features (5 features, ~5 days)
- **Jan 28+:** Await Microsoft direction before Tier B/C

**Tier A Features (High ROI):**
1. PE export parsing without dumpbin (1.5 days) - Removes VS dependency
2. Forwarder resolution chain (1 day) - Resolves A→B→C exports  
3. JSON output writer in schema.py (0.5 days) - Unblocks Section 4
4. Architecture detection x86/x64/ARM64 (0.5 days) - Correct tool selection
5. Digital signature extraction (1 day) - Trust/vendor identification

**Next Steps:**
- Create ADR-0003 documenting architecture decision
- Initialize module directory structure (8 stubs)
- Begin extraction of schema.py (foundation module)
- Verify refactored outputs match baseline
