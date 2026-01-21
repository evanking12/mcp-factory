# Binary Discovery Pipeline

Modular analyzer for extracting exports, APIs, and metadata from compiled binaries (PE DLLs, .NET assemblies, COM objects).

## Architecture (ADR-0002)

**8 specialized modules with single responsibility principle:**

### Foundation
- **schema.py** — Unified data models and output writers
  - `ExportedFunc`: ordinal, hint, RVA, forwarded_to, demangled
  - `Invocable`: unified callable record (exports, COM, CLI, .NET)
  - `MatchInfo`: header match metadata
  - Writers: CSV (13 columns), JSON, Markdown

### Analyzers
- **classify.py** — File type and architecture detection
  - `FileType` enum: PE_DLL, PE_EXE, DOTNET_ASSEMBLY, COM_OBJECT, SCRIPT, UNKNOWN
  - `get_architecture()`: x86, x64, ARM64 detection from PE machine type

- **pe_parse.py** — PE export extraction
  - Wraps dumpbin.exe (future: direct PE parsing without external tool dependency)
  - Regex-based parser for dumpbin /exports output
  - Handles forwarded exports and variable-length fields

- **exports.py** — Export enrichment
  - `demangle_with_undname()`: C++ name demangling via undname.exe
  - `deduplicate_exports()`: Remove duplicates, keep last by ordinal
  - Stubs: `resolve_forwarders()`, `classify_export_safety()` (future Tier B)

- **headers_scan.py** — Header prototype extraction
  - Recursive .h/.hpp/.hxx/.inl scanning
  - Comment span detection (// and /* */) + Doxygen parsing (/// and /**)
  - Regex-based prototype extraction with parameter/return type parsing
  - ~260 lines of complex logic for reliable header matching

- **docs_scan.py** — Documentation correlation
  - Search .md/.txt/.rst/.adoc files for export mentions
  - Maps exports to documentation references

### Extensibility
- **com_scan.py** — COM object discovery (stubs)
  - Placeholder for registry CLSID enumeration
  - Placeholder for TLB parsing, IDispatch enumeration
  - Enables Section 4 team to implement in parallel

### Orchestration
- **main.py** — CLI entry point and pipeline coordinator
  - Arguments: --dll or --exports-raw, --headers, --docs, --out, --tag, etc.
  - Full pipeline: load → deduplicate → demangle → match headers/docs → write tiers
  - 5-tier output system (Tier 1: full, Tier 5: metadata only)
  - Outputs: CSV, JSON, Markdown

## Usage

```bash
# Analyze a DLL with headers
python main.py \
  --dll "path/to/library.dll" \
  --headers "path/to/include/dir" \
  --out results \
  --tag my_library

# Or use pre-extracted exports
python main.py \
  --exports-raw exports.txt \
  --headers "path/to/include/dir" \
  --out results \
  --tag my_library

# Control demangling and tools
python main.py \
  --dll library.dll \
  --headers includes \
  --dumpbin "C:\Program Files\...\dumpbin.exe" \
  --undname "C:\Program Files\...\undname.exe" \
  --no-demangle  # skip C++ demangling

# Limit documentation search
python main.py \
  --dll library.dll \
  --docs "path/to/docs" \
  --max-doc-hits 5
```

## Output Tiers

| Tier | Exports | Headers | Docs | Demangled | Purpose |
|------|---------|---------|------|-----------|---------|
| 1 | ✓ | ✓ | ✓ | ✓ | Complete API documentation |
| 2 | ✓ | ✓ | ✗ | ✗ | API signatures from headers |
| 3 | ✓ | ✗ | ✗ | ✓ | Demangled exports (C++) |
| 4 | ✓ | ✗ | ✗ | ✗ | Raw export list |
| 5 | ✗ | ✗ | ✗ | ✗ | Metadata only (counts, stats) |

## Testing

### Fixtures
- `tests/fixtures/vcpkg.json` — zstd (187 exports) + sqlite3 (294 exports)
- Run via: `scripts/run_fixtures.ps1 -VcpkgExe <path>`

### Manual Testing
```bash
python main.py --help                    # Verify CLI
python main.py --dll tests/fixtures/vcpkg_installed/x64-windows/bin/zstd.dll \
  --headers tests/fixtures/vcpkg_installed/x64-windows/include \
  --out test_output --tag refactored
```

## Design Rationale

**Why 8 modules?**
- Single responsibility principle (each module has one reason to change)
- Enables unit testing of individual analyzers
- Allows team parallelization (Section 4 can implement features independently)
- Supports feature increments (add new analyzers without modifying existing code)

**Why not replace dumpbin immediately?**
- dumpbin is proven, reliable, on all Windows machines with VS installed
- Direct PE parsing will be a Tier A feature (1.5 days) after refactoring validation
- Preserves backward compatibility during transition

**Why keep csv_script.py?**
- Retained as reference during refactoring validation
- Will be deleted after main.py parity is confirmed

## Dependencies

- **Python 3.6+** (re, pathlib, subprocess, argparse)
- **dumpbin.exe** (auto-detected from VS 2022 or specified via --dumpbin)
- **undname.exe** (optional, for C++ demangling; auto-detected)

## Roadmap (ADR-0002)

### Tier A (1-2 days each, high ROI)
- [ ] Direct PE export parsing (replace dumpbin.exe dependency)
- [ ] Forwarder resolution chain (resolve forwarded exports to real exports)
- [ ] JSON output writer (unblock Section 4 MCP schema generation)
- [ ] Digital signature extraction (vendor/trust info)

### Tier B (2-5 days, Microsoft-directed)
- [ ] .NET assembly analyzer (Section 4)
- [ ] COM type library parsing (Section 4)
- [ ] C++/CLI hybrid detection

### Tier C (Future, low priority)
- [ ] Decompiler integration (IDA, Ghidra API)
- [ ] ETW tracing for call chains
- [ ] Behavior analysis (YARA rules, etc.)

## Contributing

1. **Adding a new analyzer**: Create `new_analyzer.py` with `analyze_*()` function, import in main.py
2. **Extending schema**: Add fields to dataclasses in schema.py, update writers
3. **Testing**: Create `test_module_name.py` in tests/discovery/, import module + fixtures
4. **Documentation**: Update this README + ADR-0002 + copilot-log.md

## References

- [ADR-0002: Modular Analyzer Architecture](../../docs/adr/0002-modular-analyzer-architecture.md)
- [dumpbin reference](https://learn.microsoft.com/en-us/cpp/build/reference/dumpbin-reference)
- [PE/COFF specification](https://learn.microsoft.com/en-us/windows/win32/debug/pe-format)
- [Fixture automation](../../scripts/run_fixtures.ps1)
