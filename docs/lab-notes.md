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
- Analyzed csv_script.py (500 lines, mixed concerns)
- Designed 8-module architecture with clear interfaces
- Created responsibility matrix and dependency graph
- Documented in ADR-0002 (decision rationale + implementation plan)

**Architecture Modules:**
- `schema.py`: Invocable dataclass + CSV/JSON/MD writers
- `pe_parse.py`: PE file parsing (dumpbin wrapper)
- `exports.py`: Export normalization, demangling, forwarding
- `headers_scan.py`: Header prototype extraction
- `docs_scan.py`: Documentation correlation
- `classify.py`: File type detection (PE/NET/script)
- `com_scan.py`: COM registry analysis (stub)
- `main.py`: CLI orchestration

**Implementation:** See ADR-0002 for comprehensive design rationale, alternatives considered, and feature roadmap.
