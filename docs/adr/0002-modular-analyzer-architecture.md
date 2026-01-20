# ADR-0002: Modular Analyzer Architecture

**Date:** 2026-01-20  
**Status:** Accepted  
**Context:** Iteration 1 (Sections 2–3)  
**Deciders:** Evan King (lead), team discussion with Claude

---

## Problem Statement

csv_script.py is 500 lines with mixed concerns:
- PE format parsing
- Export extraction and normalization
- Header file scanning
- Documentation correlation
- C++ name demangling
- Multiple output formats (CSV, Markdown, Tier levels)

This monolithic design:
- **Limits testability:** Hard to unit test individual extraction methods
- **Blocks team parallelization:** Section 4 can't start MCP schema design without stable contract
- **Resists feature addition:** Adding .NET/COM/CLI analyzers would further bloat the script
- **Obscures decisions:** Logic is intertwined; hard to see why things are done

---

## Decision

Refactor csv_script.py into **8 specialized modules** with clear input/output contracts.

```
src/discovery/
├── main.py              # CLI orchestration, pipeline execution
├── schema.py            # Invocable dataclass + output writers
├── classify.py          # File type detection (PE/NET/script)
├── pe_parse.py          # PE structure parsing (dumpbin wrapper)
├── exports.py           # Export normalization, demangling, forwarders
├── headers_scan.py      # Header prototype extraction (regex-based)
├── docs_scan.py         # Documentation correlation
└── com_scan.py          # COM registry analysis (stub for now)

tests/
├── unit/
│   ├── test_pe_parse.py     # Unit tests for PE parsing
│   ├── test_exports.py      # Unit tests for export normalization
│   └── test_classify.py     # Unit tests for file classification
└── integration/
    └── test_full_pipeline.py # Verify outputs match baseline
```

---

## Module Responsibilities

| Module | Input | Output | Dependencies | Testable | Status |
|--------|-------|--------|--------------|----------|--------|
| **schema.py** | Raw data (exports, signatures, docs) | `Invocable` objects + CSV/JSON/MD | None (foundation) | Yes - dataclass | New |
| **pe_parse.py** | File path | ExportTable dict (ordinals, names, RVAs, hints) | subprocess (dumpbin) | Yes - compare to dumpbin | Extracted |
| **exports.py** | ExportTable | List[Export] (demangled, deduplicated) | pe_parse, undname.exe | Yes - mock data | Extracted |
| **headers_scan.py** | List[Export], headers dir | Dict[name→Signature] | - | Yes - regex patterns | Extracted |
| **docs_scan.py** | List[Export], docs dir | Dict[name→List[doc_files]] | - | Yes - file discovery | Extracted |
| **classify.py** | File path | FileType enum | - | Yes - return type | Extracted |
| **com_scan.py** | File path | List[COM_object] | Registry, TLB libs | Partial (stub) | Stub |
| **main.py** | CLI args | Pipeline execution | All modules | Yes - fixture test | Refactored |

---

## Design Rationale

### 1. Why Modularize Now?

**Before:** csv_script.py handles everything, ~500 lines  
**After:** Each module has single responsibility, ~50-100 lines each

**Benefits:**
- **Testability:** Each module can be unit tested independently
- **Team parallelization:** Section 4 imports schema.py to design MCP schemas without waiting for full csv_script.py
- **Feature addition:** Adding .NET/CLI analyzers doesn't require refactoring core
- **Debugging:** When something breaks, you know which module to look at
- **Code review:** Smaller modules are easier to review

### 2. Why schema.py First?

`schema.py` defines the `Invocable` dataclass:

```python
@dataclass
class Invocable:
    name: str                      # Function name
    source_type: str               # "export" | "com" | "cli" | "dotnet"
    ordinal: Optional[int]         # Export ordinal (PE only)
    signature: Optional[str]       # Full function signature
    return_type: Optional[str]     # Return type
    parameters: Optional[str]      # Parameter list
    doc_comment: Optional[str]     # Documentation from header
    doc_files: List[str]           # Referenced documentation files
    confidence: float              # 0.0-1.0 score
    evidence: List[str]            # Why we're confident
```

**Why first?**
- Defines contract between modules
- Section 4 can start designing "how to convert Invocable→MCP tool definition"
- All analyzers (PE, COM, .NET) produce Invocables
- Writers (CSV, JSON, MD) consume Invocables

**Enables parallelization:**
```python
# Section 4 can start with this immediately
from src.discovery.schema import Invocable, to_mcp_tool_definition

def convert_invocables_to_mcp(invocables: List[Invocable]) -> List[MCPToolDef]:
    return [to_mcp_tool_definition(inv) for inv in invocables]
```

### 3. Why Keep dumpbin Initially?

**Gradient approach:** Replace tools incrementally, not all at once.

| Timeline | pe_parse.py | Justification |
|----------|-------------|---------------|
| Jan 21-22 | Wraps dumpbin | Proven, low-risk refactoring |
| Feb 1-7 | ~50% direct parsing | Validate approach, keep dumpbin fallback |
| Feb 8+ | ~100% direct parsing | Full PE parsing, no external deps |

**Rationale:**
- dumpbin is proven, tested by Microsoft
- Direct PE parsing is moderate complexity (DOS header, COFF header, sections, export table)
- Replacing all at once introduces risk (parsing bugs, format misunderstandings)
- Gradual replacement allows: validate against dumpbin output, catch edge cases

### 4. Why These 8 Modules?

Each module aligns with a **data transformation step**:

1. **classify.py** → File type detection (route to correct analyzer)
2. **pe_parse.py** → Raw PE data extraction
3. **exports.py** → Export enrichment (demangle, deduplicate, resolve)
4. **headers_scan.py** → Signature extraction
5. **docs_scan.py** → Documentation linkage
6. **schema.py** → Unified Invocable objects + output writing
7. **com_scan.py** → COM-specific extraction (future)
8. **main.py** → CLI + orchestration

**Not combined because:**
- Each has distinct testing strategy
- Future .NET/CLI analyzers follow same pattern
- Different failure modes (missing headers ≠ missing COM registry)

---

## Alternatives Considered

### Alternative 1: Keep csv_script.py as-is
- **Pro:** No refactoring time, works now
- **Con:** Section 4 has unclear data contracts, hard to add features, unmaintainable at 1000+ lines
- **Rejected**

### Alternative 2: Partial refactoring (extract only output writers)
- **Pro:** Less refactoring work
- **Con:** Core logic still mixed, Section 4 can't parallelize, doesn't solve testability
- **Rejected**

### Alternative 3: Full rewrite in Rust/C#
- **Pro:** Better performance, type safety
- **Con:** 2+ weeks of work, team knows Python, breaks existing fixtures
- **Rejected**

### Alternative 4: Modular Python design (this choice)
- **Pro:** Refactoring time is 2-3 days, testable, enables team parallelization, extensible
- **Con:** Some code duplication in validation logic (acceptable)
- **Accepted**

---

## Implementation Plan

### Phase 1: Extract Modules (Jan 21-22)

1. **Day 1:** Extract schema.py + create test for Invocable dataclass
2. **Day 2:** Extract pe_parse.py, exports.py, headers_scan.py
3. **Day 3:** Extract docs_scan.py, classify.py, com_scan.py
4. **Verification:** Run full pipeline, compare CSV output to baseline

### Phase 2: Unit Tests (Concurrent)

For each module:
```python
# test_exports.py
def test_demangle_cpp_name():
    assert demangle("?func@namespace@@...") == "namespace::func"

def test_resolve_forwarded_export():
    assert resolve_forwarded("kernel32.DeleteFile") == "ntdll.NtDeleteFile"
```

### Phase 3: Verify Baseline (Day 3)

```powershell
.\scripts\run_fixtures.ps1
# Verify artifacts identical to pre-refactoring
```

### Phase 4: Document Decisions (Day 3)

- ADR-0003 (this file)
- lab-notes.md entry
- copilot-log.md entry

---

## Tier A Features (Post-Refactoring)

Once refactoring verified, implement 5 high-ROI features:

| Feature | Module | Days | Benefit |
|---------|--------|------|---------|
| PE parsing without dumpbin | pe_parse.py | 1.5 | Remove VS dependency |
| Forwarder resolution | exports.py | 1.0 | Resolve A→B→C chains |
| JSON output | schema.py | 0.5 | Unblock Section 4 |
| Architecture detection | classify.py | 0.5 | x86/x64/ARM64 routing |
| Digital signatures | schema.py | 1.0 | Trust/vendor info |

**Total:** ~5 days, **highly aligned with team needs**

---

## Future Enhancements (Post-Microsoft Direction)

- **Tier B (Medium ROI, weeks 4-6):**
  - COM registry + TLB parsing (com_scan.py)
  - .NET metadata analysis (new dotnet_scan.py)
  - PDB symbol file support (pe_parse.py enhancement)

- **Tier C (Lower ROI, conditional):**
  - Decompiler integration (Ghidra/IDA)
  - ETW tracing for dynamic analysis
  - Packed/obfuscated detection (classify.py enhancement)

---

## Trade-offs & Acceptance Criteria

| Trade-off | Accept? | Rationale |
|-----------|---------|-----------|
| 2-3 days refactoring vs shipping features now | ✅ Yes | Better foundation saves 10+ days later |
| Some code duplication (validation) | ✅ Yes | Minimal (<5% lines), acceptable for modularity |
| More files to maintain | ✅ Yes | Easier to navigate than 500-line monolith |
| Keep dumpbin dependency initially | ✅ Yes | Risk mitigation, gradual replacement |

**Acceptance Criteria:**
- [ ] All 8 modules extract successfully
- [ ] Unit tests pass for pe_parse.py, exports.py
- [ ] Integration test: CSV output identical to baseline
- [ ] Section 4 can import schema.py and design MCP conversion
- [ ] ADR-0003 + lab-notes.md + copilot-log.md are coherent

---

## Questions for Microsoft Sponsors

1. **Priority on file types:** Should we prioritize .NET assemblies and COM objects, or focus on native PE first?
2. **Performance constraints:** Are there DLL size limits or scanning time constraints we should design for?
3. **Data contracts:** Do you want Invocable objects (our proposal) or different schema?
4. **Feedback timing:** When could we get feedback on initial implementation so we can adjust Tier B/C priorities?

---

## References

- [ADR-0001: Initial Scope](0001-initial-scope.md) - Project scope and constraints
- [ADR-0003: PE Parsing Strategy](0003-pe-parsing-strategy.md) - Why dumpbin + regex initially (future)
- [lab-notes.md](../lab-notes.md) - Implementation timeline and status
- [CONTRIBUTING.md](../../CONTRIBUTING.md) - Module development guidelines
