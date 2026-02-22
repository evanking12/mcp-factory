# ADR 0007: Directory Scan — §2.a Installed-Instance Target

**Date:** 2026-02-22  
**Status:** ACCEPTED  
**Owner:** Evan King  
**Relates to:** Section 2 (Specifying the Target), §2.a "installed instance" requirement

---

## Problem Statement

`main.py` accepted only a single file path via `--target` / `--dll`.  The project
specification §2.a explicitly requires:

> "Users must be able to provide the system a **copy of the target file** or an
> **installed instance**. Example: appC.exe or **c:\Program Files\AppD\\**"

An *installed instance* is a directory — a software installation folder that may
contain a mix of DLLs, EXEs, scripts, SQL files, config descriptors, and other
artifacts.  Without directory support, MCP Factory could not satisfy this
requirement, leaving §2.a partially unimplemented.

---

## Decision

Implement `analyze_directory(dir_path, out_dir, args)` in `src/discovery/main.py`
and wire it into the existing pipeline with minimal disruption to the single-file
code path.

### Design choices

| Choice | Rationale |
|--------|-----------|
| **`rglob('*')` + extension filter** | Handles nested install trees (e.g. `bin/`, `lib/`, `plugins/`) without requiring the caller to know internal layout. |
| **`RECOGNIZED_EXTENSIONS` frozenset** | Single, auditable list of extensions that maps to a non-UNKNOWN `FileType`; easy to extend if new analyzers are added. |
| **`classify_file()` final arbitration** | Extension filtering is a fast pre-screen; `classify_file()` does authoritative type detection including content-sniffing for `.json`/`.xml`/`.yaml`. Files that classify as `UNKNOWN` after sniffing are silently skipped. |
| **Recursive `main()` call per file** | Re-uses every existing analyzer and routing decision without duplicating routing logic.  `sys.argv` is swapped atomically around each call and restored in a `finally` block to avoid state leakage. |
| **Per-file sub-directory** | Each file writes its artifacts to `out_dir/<stem>/` so individual outputs are preserved and browseable alongside the aggregate. |
| **Aggregate `<dir>_scan_mcp.json`** | Merges all invocables into one file with the standard `{ metadata, invocables, summary }` schema so `select_invocables.py` can load the directory result with zero UI changes. |

### Files changed

| File | Change |
|------|--------|
| `src/discovery/main.py` | Added `RECOGNIZED_EXTENSIONS`, `analyze_directory()`, and a six-line directory-check branch at the top of `main()`. |
| `src/ui/select_invocables.py` | Changed `--dll` to `--target` in the subprocess command; updated `--target` help text; softened "File not found" to "Target not found". |
| `scripts/demo_all_capabilities.py` | Added Section 10 "Directory Scan (§2.a)" that passes `tests/fixtures/scripts/` as the target. |
| `docs/sections-2-3.md` | Updated §2.a status, target count (28 → 29), demo section, and test-results table. |
| `docs/copilot-log/entries.md` | Added session log entry. |

---

## Consequences

**Positive:**
- §2.a is now fully satisfied — both a single file and an installed instance directory
  are valid inputs.
- No breaking changes to the existing single-file pipeline.
- `select_invocables.py` works transparently on directory targets.
- `demo_all_capabilities.py` carries a living regression test (Section 10) for the
  directory walk path.

**Negative / Trade-offs:**
- `sys.argv` mutation in `analyze_directory()` is not thread-safe.  Acceptable for
  the current single-threaded CLI; would need refactoring if parallelism is added.
- Recursive `main()` calls re-parse argparse on every file.  Negligible overhead for
  typical install directories (<100 files); noted for future optimisation.
- Files with duplicate stems inside the same directory share a sub-output directory
  (e.g. `foo.dll` and `foo.py` would both write to `out_dir/foo/`).  Artifacts are
  distinct because the analyzer names them differently, but the directory is shared.
  Acceptable for the current scope.

---

## Alternatives Considered

| Alternative | Rejected because |
|-------------|-----------------|
| Extract `_dispatch_single_file()` helper | Larger refactor, same end result; adds complexity without meaningful benefit for the use case. |
| Subprocess call per file | Cross-process overhead; harder to test; loses in-process captured output. |
| `--input-dir` as a separate argument | Would add a second mutually-exclusive input mode; `--target` already carries the right semantics per the spec. |
