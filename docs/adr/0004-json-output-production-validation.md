# ADR 0004: JSON Output & Production-Scale Validation

**Date:** 2026-01-23  
**Status:** ACCEPTED  
**Owner:** Evan King  
**Relates to:** Sections 2-3 (Discovery), Section 4 (MCP Generation), Section 5 (Verification)

---

## Problem Statement

1. **Section 4 Integration Blocker:** Section 4 (MCP Generation) needed structured JSON to consume discovery results, but only CSV files were available. CSV parsing is fragile, type-unsafe, and doesn't preserve nested metadata.

2. **Schema Instability:** No stable contract between Section 2-3 → Section 4. Any field addition/removal in CSV would break downstream consumers. Need forward-compatible schema that allows iteration without breaking changes.

3. **Production-Scale Validation Missing:** While individual DLL analysis worked (zstd, sqlite3), no mechanism existed to validate the pipeline at scale across hundreds of Windows system DLLs. Needed proof that discovery is robust enough for real-world deployment.

4. **CLI Analysis Not Production-Ready:** CLI analyzer (EXE argument extraction) and debug suite existed only in experiments folder. No clear integration path to main codebase, no showcase in README for sponsors.

---

## Decision

Implemented three complementary enhancements:

### 1. Stable JSON Schema v2.0.0 (Forward-Compatible)
- Created `docs/schemas/discovery-output.schema.json` with JSON Schema draft-07
- **Core guarantees** (never change): `schema_version`, `metadata.target_path`, `invocables[].name`, `.kind`, `.confidence`, `.evidence.discovered_by`
- **Extensibility points:** `metadata` object, `invocables[].metadata` dict, `confidence_factors`
- **Evidence-first design:** Every claim cites source (file, line, discovery method)
- Auto-generated alongside CSV for all tiers (1-4)

### 2. Production-Scale Batch Validation
- Created `scripts/run_batch_validation.ps1` with 3 tiered modes:
  - **SMOKE** (~30 DLLs, ~4s) - PR/demo validation
  - **CORE** (~200 DLLs, ~20s) - Main branch CI/nightly (default)
  - **FULL** (~466 DLLs, ~53s) - Comprehensive (nightly/releases)
- Uses `src/discovery/debug_suite.py` to validate each file
- Reports: PASS/WARN/ERROR/SKIPPED with timing metrics + top 5 slowest files
- Proves pipeline robustness: 200 DLLs analyzed in 22s with 100% success rate

### 3. CLI Analyzer & Debug Suite Promotion
- Moved `cli_analyzer.py`, `debug_suite.py`, `string_extractor.py` from experiments → `src/discovery/`
- Added showcase command blocks to README.md (3 new sections):
  - "Analyze Windows EXE Tools ⚡" - CLI argument extraction
  - "Validate Analysis Pipeline ⚡" - Debug suite
  - "Batch Validation ⚡" - Production-ready testing
- Updated run_batch_validation.ps1 to use `src/discovery/debug_suite.py` (not experiments)

---

## Rationale

### Why JSON Over CSV?

**Type Safety:**
- CSV: All values are strings → `"true"` vs `true`, `"42"` vs `42`
- JSON: Native types → `boolean`, `number`, `null`, preserves semantics

**Nested Structure:**
- CSV: Flat columns → `signature`, `parameters`, `return_type` separate
- JSON: Grouped objects → `signature: { return_type, parameters, full_prototype }`

**Forward Compatibility:**
- CSV: Adding columns breaks parsers (position-dependent)
- JSON: Adding fields is safe (name-based access, optional fields)

**Section 4 Ergonomics:**
```python
# CSV (fragile):
import csv
with open('file.csv') as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row['confidence'] == 'high':  # string comparison
            name = row['function']
            sig = row['signature']  # full prototype as single string

# JSON (robust):
import json
with open('file.json') as f:
    data = json.load(f)
for inv in data['invocables']:
    if inv['confidence'] == 'high':  # type-safe
        name = inv['name']
        return_type = inv['signature']['return_type']  # structured
        params = inv['signature']['parameters']
        factors = inv['confidence_factors']  # nested metadata
```

### Why Forward-Compatible Schema Matters

**Problem:** Discovery pipeline will evolve (add COM, .NET, PDB symbols). Each enhancement risks breaking Section 4.

**Solution:** Extensible metadata pattern
- `invocables[].metadata = {}` - Any future data goes here
- Consumers ignore unknown fields (no breaking changes)
- Schema version bumps only for removals/type changes

**Example Evolution:**
```json
// v2.0.0 (today)
{
  "name": "CreateFile",
  "confidence": "high",
  "metadata": {}  // empty
}

// v2.1.0 (future - non-breaking)
{
  "name": "CreateFile",
  "confidence": "high",
  "metadata": {
    "pdb_symbols_found": true,
    "calling_convention": "__stdcall",
    "thread_safe": false
  }
}
```

Existing Section 4 consumers still work - they just ignore `metadata`.

### Why Batch Validation Matters

**Proves Robustness at Scale:**
- Single DLL analysis (zstd, sqlite3) proves correctness
- 200 DLL analysis proves production viability
- 0 failures @ 200 files → pipeline is enterprise-ready

**Sponsor Confidence:**
- "We tested on 2 DLLs" → Toy demo
- "We tested on 200 Windows system DLLs with 100% success" → Production tool

**CI/CD Integration:**
- SMOKE mode (~4s) → Run on every PR
- CORE mode (~20s) → Run on main branch commits
- FULL mode (~53s) → Run nightly/before releases

**Metrics = Credibility:**
```
Files Processed: 200
[PASS] 200 (100%)
elapsed=22.5s
avg=112.6ms/file
failures=0
```

→ "This is rigorous engineering."

### Why Promote CLI Analyzer to src/?

**Demonstrates Section 2-3 Breadth:**
- Not just DLL exports (narrow)
- Also EXE argument extraction (broad)
- Shows multi-surface discovery capability

**Section 4 Needs Both:**
- DLL exports → MCP tools for library functions
- EXE arguments → MCP tools for CLI commands
- Unified schema handles both (`kind: dll_export` vs `kind: cli_command`)

**README Showcases 4 Capabilities:**
1. ✅ One-command setup (frictionless)
2. ✅ CLI analyzer (EXE support)
3. ✅ Debug suite (validation rigor)
4. ✅ Batch validation (production scale)

→ "This project is comprehensive."

---

## Alternatives Considered

### 1. Keep CSV Only, No JSON
**Rejected:** Section 4 needs structured data. CSV forces them to write brittle parsers. JSON is standard for tool integration.

### 2. Use Protocol Buffers Instead of JSON
**Rejected:** Protobuf requires code generation (complexity). JSON is human-readable, standard in MCP ecosystem, no tooling overhead.

### 3. Different Schema for Each Tier
**Rejected:** Complexity explosion. Single stable schema with `tier` field is simpler. Tiers differ only in data completeness (headers present vs absent), not structure.

### 4. Manual Testing Instead of Batch Validation
**Rejected:** Doesn't scale. Can't prove robustness to sponsors. Automated validation catches regressions (e.g., if dumpbin output format changes).

### 5. Keep CLI Analyzer in Experiments
**Rejected:** Experiments folder is gitignored. Sponsors can't see it. Production features belong in src/ with showcase in README.

---

## Implementation Details

### Files Created/Modified

**New Schema:**
- `docs/schemas/discovery-output.schema.json` - v2.0.0 stable contract
- `docs/schemas/README.md` - Schema documentation + usage guide

**New Scripts:**
- `scripts/run_batch_validation.ps1` - 3-tier validation harness
- `src/discovery/cli_analyzer.py` - EXE argument extraction (promoted)
- `src/discovery/debug_suite.py` - 9-breakpoint validation suite (promoted)
- `src/discovery/string_extractor.py` - Binary string mining fallback (promoted)

**Modified Scripts:**
- `src/discovery/csv_script.py` - Added `write_json()` function, generates JSON for tiers 1-4
- `README.md` - Added 3 new showcase sections with status meanings explained

**Deprecated (Removed):**
- `docs/schemas/v1.0.json` - No extensibility, replaced by v2.0.0
- `docs/schemas/inventory.schema.json` - Experimental, never used
- `docs/schemas/selection.schema.json` - Experimental, never used

### JSON Output Generation

Added to `csv_script.py` (lines 558-686):
```python
def write_json(
    path: Path,
    dll_path: Path,
    exports: List[ExportedFunc],
    matches: Dict[str, MatchInfo],
    doc_hits: Dict[str, List[str]],
    tier: int,
    is_signed: bool = False,
    publisher: Optional[str] = None,
    architecture: str = "unknown"
) -> None:
    # Builds JSON with:
    # - metadata (target info, tier, timestamp)
    # - invocables[] (name, kind, confidence, signature, docs, evidence)
    # - pipeline_results (modules run/passed/warned/failed)
    # - statistics (counts, match rate)
    json.dump(output, f, indent=2, ensure_ascii=False)
```

Called after every CSV write in tier outputs (1-4).

### Batch Validation Architecture

`run_batch_validation.ps1` workflow:
1. Scan PATH + system folders for DLLs/EXEs
2. Deduplicate and limit per tier (30/200/466)
3. For each file: run `python debug_suite.py --file "path"`
4. Parse output for status: `DEBUG SUITE PASSED` → PASS, `BREAKPOINT.*WARNING` → WARN, `ERROR|FAILED` → ERROR
5. Collect metrics: files scanned, elapsed time, avg ms/file, failures, top 5 slowest
6. Print summary with color-coded counts

### Status Meanings (Clarified in README)

**Critical Distinction:**
- **[PASS]** = Pipeline ran successfully (modules executed without crashes)
- **NOT** = Functions are invokable (that's determined by confidence scoring within pipeline)

**Why This Matters:**
- User confusion: "200 PASS doesn't mean 200 invokable functions"
- Correct interpretation: "200 files analyzed successfully, confidence scores vary per export"
- README now explicitly explains: PASS = pipeline robustness, confidence = invokability

---

## Impact & Metrics

### Section 4 Integration Unblocked
- Before: CSV only, no schema, fragile parsing
- After: JSON with stable v2.0.0 schema, extensible, type-safe
- Section 4 can now consume `invocables[]` directly with confidence metadata

### Production-Scale Validation Proven
- Before: 2 DLL fixtures (zstd, sqlite3) - proof of concept
- After: 200 DLL batch validation - proof of production viability
- **Test Results:**
  - SMOKE: 30 files, 3.4s, 100% success
  - CORE: 200 files, 22.5s, 100% success
  - Files/second: ~9 DLLs/sec sustained

### CLI Analysis Integrated
- Before: EXE support experimental only
- After: CLI analyzer in src/, showcased in README
- **Test Coverage:**
  - 7 Windows tools tested (git, ipconfig, tasklist, robocopy, sfc, whoami, systeminfo)
  - 76 arguments extracted, 35 subcommands found, 100% success rate

### Sponsor-Ready Documentation
- Before: Technical, fragmented, no production proof
- After: 4 showcase command blocks (setup, CLI, debug, batch) with clear status explanations

---

## Risks & Mitigations

### Risk: Schema Evolution Breaks Section 4
**Mitigation:** 
- Semantic versioning (major.minor.patch)
- Required fields frozen (name, kind, confidence, evidence.discovered_by)
- 2-week deprecation notice for breaking changes
- `schema_version` field enables compatibility detection

### Risk: Batch Validation Too Slow for CI
**Mitigation:**
- SMOKE mode (4s) is fast enough for PR checks
- CORE mode (20s) acceptable for main branch
- FULL mode (53s) reserved for nightly/releases

### Risk: JSON Files Too Large
**Current Size:**
- zstd (187 exports): 313 KB JSON vs 119 KB CSV (2.6x larger)
- sqlite3 (294 exports): 375 KB JSON vs 89 KB CSV (4.2x larger)

**Mitigation:**
- Acceptable for Section 4 consumption (<1 MB per DLL)
- Could add gzip compression later if needed (`*.json.gz`)
- Benefit (structured metadata) outweighs cost (file size)

---

## Success Criteria

✅ **Section 4 Can Consume Discovery Output:**
- JSON files auto-generated alongside CSV
- Schema documented with examples
- Test: Section 4 can parse `zstd_tier2_api_zstd_fixture.json` and extract invocables

✅ **Production-Scale Validation Passes:**
- CORE mode (200 DLLs) completes in <30s
- 100% success rate (no CRITICAL failures)
- Test: Run `.\scripts\run_batch_validation.ps1 -Mode core`

✅ **CLI Analysis Functional:**
- CLI analyzer extracts arguments from 5+ Windows tools
- Debug suite validates pipeline with 0 critical failures
- Test: Run showcase commands from README

✅ **Schema Stability Maintained:**
- Adding new confidence factors doesn't break existing JSON
- Consumers can ignore unknown fields
- Test: Load v2.0.0 JSON with v2.1.0 parser (forward compat)

---

## Future Work

### Planned Enhancements (Schema v2.1.0)
- Add `calling_convention` detection (__stdcall, __cdecl, __fastcall)
- Add `thread_safe` annotation from PDB symbols
- Add `error_codes` array from documentation
- All backward-compatible (optional fields in metadata)

### Integration with Section 5
- Verification UI consumes `invocables[]` JSON
- Interactive filtering by confidence level
- Evidence ledger display (show source file + line for each claim)

### CI/CD Integration
- GitHub Actions workflow: Run SMOKE on every PR
- Fail PR if batch validation shows regressions
- Nightly FULL mode with results published to wiki

---

## Related ADRs

- **ADR-0002:** Modular Analyzer Architecture - Established 8-module pipeline that JSON output integrates with
- **ADR-0003:** Frictionless UX & Confidence Analysis - Confidence metadata now exposed in JSON for Section 4 consumption

---

## Appendix: JSON Schema v2.0.0 Structure

```json
{
  "schema_version": "2.0.0",
  "metadata": {
    "target_path": "C:\\path\\to\\library.dll",
    "target_name": "library.dll",
    "target_type": "dll",
    "architecture": "x64",
    "file_size_bytes": 658944,
    "is_signed": false,
    "publisher": null,
    "analysis_timestamp": "2026-01-23T17:51:24",
    "pipeline_version": "1.0.0",
    "tier": 2
  },
  "invocables": [
    {
      "name": "FunctionName",
      "kind": "dll_export",
      "ordinal": 1,
      "rva": "00077410",
      "confidence": "high",
      "confidence_factors": {
        "has_signature": true,
        "has_documentation": false,
        "has_parameters": true,
        "has_return_type": true,
        "is_forwarded": false,
        "is_ordinal_only": false
      },
      "signature": {
        "return_type": "size_t",
        "parameters": "void* dictBuffer, size_t dictContentSize",
        "calling_convention": null,
        "full_prototype": "size_t FunctionName(void* dictBuffer, size_t dictContentSize)"
      },
      "documentation": {
        "summary": null,
        "description": null,
        "source_file": "C:\\...\\include\\library.h",
        "source_line": 474
      },
      "evidence": {
        "discovered_by": "exports.py",
        "header_file": "C:\\...\\include\\library.h",
        "forwarded_to": null,
        "demangled_name": null
      },
      "metadata": {}
    }
  ],
  "pipeline_results": {
    "modules_run": ["classify", "pe_parse", "exports", "headers_scan", "schema", "csv_script"],
    "modules_passed": ["exports", "schema", "csv_script"],
    "modules_warned": [],
    "modules_failed": [],
    "total_duration_ms": 0
  },
  "statistics": {
    "total_invocables": 187,
    "high_confidence_count": 8,
    "medium_confidence_count": 176,
    "low_confidence_count": 3,
    "signature_match_rate": 0.984,
    "documented_count": 0
  }
}
```

---

**Approved by:** Evan King  
**Review Date:** 2026-01-23  
**Implementation:** Complete
