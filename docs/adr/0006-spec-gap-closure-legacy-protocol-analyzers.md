# ADR 0006: Spec-Gap Closure — Legacy Protocol & Spec-Format Analyzers

**Date:** 2026-02-22  
**Status:** ACCEPTED  
**Owner:** Evan King  
**Relates to:** Sections 2-3 (Discovery), §1 Spec Requirements

---

## Problem Statement

After completing multi-language support (ADR-0002, ADR-0005), `sections-2-3.md` listed four open gaps explicitly marked "Not Supported Yet":

1. **JNDI** — Java Naming and Directory Interface bindings (`.jndi`, `.properties`, Spring XML)
2. **SOAP/WSDL** — Web service descriptor files (`.wsdl`)
3. **CORBA IDL** — Interface Definition Language interface files (`.idl`)
4. **OpenAPI / JSON-RPC** — REST service contracts (`.yaml`/`.yml`) and JSON-RPC 2.0 descriptors (`.json`)
5. **PDB Symbols** — Program Database debug symbol files (`.pdb`), a Windows-specific invocable surface not reachable via `pefile` export tables

These gaps were explicitly required by the project specification (§1) and blocked a complete §2-3 compliance claim. The `demo_all_capabilities.py` suite also still contained `notepad.exe` — a GUI-only EXE with no invocable surface — inflating the pass count without representational value.

---

## Decision

We implemented **five new analyzer modules** and updated the pipeline, demo infrastructure, and UI to achieve full §2-3 spec coverage.

### 1. New Analyzer Modules

#### `src/discovery/openapi_analyzer.py`
- Parses OpenAPI 3.x / Swagger 2.x YAML and JSON and JSON-RPC 2.0 service descriptors.
- HTTP operations (`GET /customers/{id}` etc.) become `openapi_operation` invocables.
- JSON-RPC `methods[]` entries become `jsonrpc_method` invocables.
- Execution metadata: `http_request` (with `http_method` + `path`) or `jsonrpc` (with `rpc_version: "2.0"`).
- Confidence: `guaranteed` for all entries (spec files are authoritative contracts).

#### `src/discovery/wsdl_analyzer.py`
- Parses SOAP/WSDL 1.1 (and limited 2.0) XML using `lxml`.
- Extracts `<wsdl:operation>` entries with `<wsdl:input>`/`<wsdl:output>` message names.
- Emits `soap_operation` invocables; execution metadata: `{"method": "soap", "action": ..., "interface": ...}`.
- Key robustness fix: `_local(tag)` guards against lxml `Comment`/`PI` nodes whose `.tag` is a callable, not a string.

#### `src/discovery/idl_analyzer.py`
- Regex-based parser for CORBA IDL method declarations inside `interface` blocks.
- Handles `module::Interface` namespacing, `oneway` methods, `in/out/inout` parameter directions, `sequence<T>` types, and `raises(...)` clauses.
- Doc comments extracted from the **original** (un-stripped) source using line-number alignment with the comment-stripped clean source — preserving `_strip_comments()` newline-count invariant.
- Emits `corba_method` invocables; execution metadata: `{"method": "corba_iiop", "interface": ..., "operation": ...}`.

#### `src/discovery/jndi_analyzer.py`
- Parses JNDI `.properties` / `.jndi` files and Spring XML `<beans>` context files.
- Recognises eight binding subtypes: `jndi_datasource`, `jndi_jms`, `jndi_rmi`, `jndi_ldap`, `jndi_mail`, `jndi_ejb`, `jndi_env_entry`, `jndi_lookup`.
- Execution metadata: `{"method": "jndi_lookup", "jndi_name": ..., "subtype": ...}`.

#### `src/discovery/pdb_analyzer.py`
- Uses `dbghelp.dll` via `ctypes` (`SymInitialize` / `SymLoadModuleEx` / `SymEnumSymbols`) to enumerate PDB symbols on Windows.
- Emits `pdb_symbol` invocables; execution metadata: `{"method": "dll_import", "source": "pdb_symbols"}`.
- Confidence is `low` (C public symbols carry no type decorations); filtered to function-like entries only.
- Falls back gracefully with a logged warning on non-Windows or if `dbghelp.dll` is unavailable.

### 2. Pipeline Updates

| File | Change |
|------|--------|
| `src/discovery/classify.py` | Added 6 new `FileType` enum values: `OPENAPI_SPEC`, `JSONRPC_SPEC`, `WSDL_FILE`, `CORBA_IDL`, `JNDI_CONFIG`, `PDB_FILE`; extension + content-peek detection added to `classify_file()` |
| `src/discovery/main.py` | Imports for all 5 new analyzers; 6 new `_SCRIPT_DISPATCH` entries; 5 new `ANALYZER_REGISTRY` entries |
| `src/discovery/schema.py` | Added 6 new branches to `_get_execution_metadata()` covering `openapi_operation`, `jsonrpc_method`, `soap_operation`, `corba_method`, `jndi_*`, `pdb_symbol` |
| `src/ui/select_invocables.py` | `_KIND_LABELS` extended with human-readable labels for all 6 new file type suffixes |

### 3. Demo & Fixture Infrastructure

- **`tests/fixtures/scripts/sample_openapi.yaml`** — OpenAPI 3.0 spec with 9 operations (Customer CRUD, Orders, Support, Analytics).
- **`tests/fixtures/scripts/sample_jsonrpc.json`** — JSON-RPC 2.0 descriptor with 5 methods (calculator/currency).
- **`tests/fixtures/scripts/sample.wsdl`** — WSDL 1.1 service with 7 operations (ContosoCustomerService).
- **`tests/fixtures/scripts/sample.idl`** — CORBA IDL with 3 interfaces × 4–5 methods each (12 total).
- **`tests/fixtures/scripts/sample.jndi`** — JNDI properties with 12 bindings (JDBC, JMS, mail, RMI, EJB, LDAP).
- PDB fixture reuses existing `tests/fixtures/vcpkg_installed/x64-windows/bin/zstd.pdb`.

- **`scripts/demo_legacy_protocols.py`** — Standalone 6-target verification suite. Validates invocable count, full JSON schema, no `method=unknown`, all key fields present.
- **`scripts/demo_all_capabilities.py`** — Removed `notepad.exe` (zero invocable surface). Added Section 9 "Legacy Protocols & Spec Formats" with all 6 new targets.

### 4. Removed: `notepad.exe`

`notepad.exe` was a pure GUI EXE with no exported symbols, no COM registration, and no script-layer invocables. It was generating 0-invocable noise. Removed from `demo_all_capabilities.py` per ADR-0005 Strict Artifact Hygiene policy.

---

## Rationale

### Why these five analyzers now?

The project specification §1 explicitly names JNDI, SOAP, CORBA, OpenAPI/JSON-RPC, and PDB as required invocable surfaces. With §2-3 otherwise complete (23/23 demo targets passing), these were the only remaining blockers for a full compliance claim.

### Why `dbghelp.dll` for PDB (not a Python PDB library)?

PDB parsing is a proprietary Microsoft format. No pure-Python library handles the full symbol stream reliably. `dbghelp.dll` is present on every Windows installation and is the officially supported interface for symbol enumeration. Since the pipeline already requires Windows for COM/TLB analysis, this introduces no new platform constraint.

### Why regex for CORBA IDL (not a grammar parser)?

CORBA IDL grammars are large (ANTLR grammars are 800+ lines). For the invocable discovery use-case we only need method names, parameter lists, return types, and doc comments — all of which are reliably extractable with targeted regex patterns. A full grammar would add a dependency and parse-tree traversal complexity with no meaningful accuracy gain for this task.

### Why line-number alignment for IDL doc-comment extraction?

`_strip_comments()` removes `//` and `/* */` comments from the source before regex matching. Naive doc-comment extraction from the stripped source would always return empty strings. Since `_strip_comments()` preserves newline counts (block comments are replaced with an equal number of `\n` characters), the line number of any match in the clean source is identical to its line number in the original source, enabling accurate backward-scan for doc comments without re-running the regex on raw text.

---

## Consequences

### Positive
- **Full §2-3 spec compliance**: All source types named in the project specification are now handled.
- **Demo count**: `demo_all_capabilities.py` now runs **28/28** targets across 9 sections (up from 23/23 across 8 sections), with all targets producing real invocables.
- **Standalone verifiability**: `scripts/demo_legacy_protocols.py` provides an isolated 6-target regression suite for the new analyzers.
- **UI coverage**: `select_invocables.py` displays all new source types with human-readable kind labels.
- **Execution completeness**: Every new invocable carries a concrete `execution.method` — no `unknown` values.

### Negative / Limitations
- **PDB confidence is `low`**: C PDB public symbols carry no type decoration. Confidence will remain low until a DIA SDK integration or type-database cross-reference is added.
- **IDL `oneway` methods**: The `oneway` modifier is captured in the signature string but not surfaced as a separate field — acceptable for current §4 use.
- **JNDI Spring XML**: Spring XML context file support is basic (datasource + JMS beans); advanced Spring profiles/environments are not parsed.
- **PDB Windows-only**: `pdb_analyzer.py` silently returns an empty list on non-Windows hosts.

---

## Verification

- **Script**: `scripts/demo_legacy_protocols.py`
- **Result**: **6/6 PASS** — OpenAPI (9 invocables, GUARANTEED), JSON-RPC (5, GUARANTEED), WSDL (7, GUARANTEED), CORBA IDL (12, GUARANTEED), JNDI (12, HIGH), PDB (871, LOW)

- **Full suite**: `scripts/demo_all_capabilities.py`
- **Result**: **28/28 PASS** across 9 sections

- **Sections doc**: `docs/sections-2-3.md` updated — "What's Not Supported Yet" section cleared.
