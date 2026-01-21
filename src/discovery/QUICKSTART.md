# Developer Quick Start

## For Section 2-3 (API Discovery)

If you're working on export analysis, header matching, or improving the core pipeline:

```python
# Basic workflow
from src.discovery.pe_parse import get_exports_from_dumpbin
from src.discovery.headers_scan import scan_headers
from src.discovery.exports import demangle_with_undname, deduplicate_exports
from src.discovery.schema import write_csv

# Get exports from DLL
exports = get_exports_from_dumpbin("my_library.dll")

# Match to headers
matches = scan_headers("include/dir", exports)

# Enrich with demangling
exports = demangle_with_undname(exports, "undname.exe")

# Deduplicate
exports = deduplicate_exports(exports)

# Write output
write_csv(exports, "output.csv", matches)
```

## For Section 4 (MCP Schema Generation)

If you're designing the MCP protocol schema:

```python
# Import only what you need (no csv_script.py dependencies!)
from src.discovery.schema import Invocable, ExportedFunc, MatchInfo

# The unified Invocable record is your schema
invocable = Invocable(
    name="function_name",
    type="export",  # or "com", "cli", "dotnet"
    ordinal=42,
    hint=0x1234,
    rva=0x5678,
    return_type="HRESULT",
    parameters="LPSTR path, DWORD flags",
    doc_comment="Does something useful",
    header_file="api.h",
    header_line=123
)

# Export to any format
invocable.to_dict()  # for JSON serialization
invocable.to_csv_row()  # for CSV output
```

## For Testing

```bash
# Run on fixtures (PowerShell)
.\scripts\run_fixtures.ps1 -VcpkgExe "C:\path\to\vcpkg.exe"

# Run manual test on zstd
python src/discovery/main.py \
  --dll tests/fixtures/vcpkg_installed/x64-windows/bin/zstd.dll \
  --headers tests/fixtures/vcpkg_installed/x64-windows/include \
  --out test_output --tag test

# Verify output
ls test_output/  # Should show 7 files: tier2_api.csv, tier4_api.csv, exports_raw.txt, etc.
```

## Module Dependencies Graph

```
schema.py (no dependencies)
    ↓
    ├← classify.py
    ├← pe_parse.py
    ├← exports.py
    ├← headers_scan.py
    ├← docs_scan.py
    └← com_scan.py
            ↓
            main.py (imports all 7)
```

**Key insight:** You can import `schema.py` independently without pulling in the entire pipeline.

## Adding a New Feature

### Example: Add archive format detection (Tier B)

```python
# 1. Add to schema.py if needed
# (In this case, existing FileType enum is sufficient)

# 2. Create archive_scan.py
# src/discovery/archive_scan.py
def scan_archives(dll_path):
    """Detect if DLL is embedded in archive (MSI, installer, etc.)"""
    # implementation...
    return archive_info

# 3. Update main.py
from src.discovery import archive_scan

def main():
    # ... existing code ...
    archive_info = archive_scan.scan_archives(dll_path)
    # ... output archive info ...

# 4. Add tests
# tests/discovery/test_archive_scan.py
def test_scan_archives():
    # ...
```

## Debugging

**All modules print to stderr for debugging:**

```bash
# Capture debug output
python src/discovery/main.py --dll library.dll 2> debug.log
```

**Check what was detected:**

```python
from src.discovery.classify import classify_file, get_architecture

file_type = classify_file("library.dll")  # FileType.PE_DLL
arch = get_architecture("library.dll")     # "x64"
```

## Common Issues

| Problem | Solution |
|---------|----------|
| `ModuleNotFoundError: No module named 'src'` | Run from repo root: `cd mcp-factory` |
| `FileNotFoundError: dumpbin.exe` | Specify: `--dumpbin "C:\path\to\dumpbin.exe"` |
| No headers matched | Check header directory path has .h files; try: `python -c "from src.discovery.headers_scan import iter_header_files; print(list(iter_header_files('.')))"` |
| Forwarded exports show as "00000000" | Expected until `resolve_forwarders()` is implemented (Tier A feature) |

## Next Steps

1. **Understand the architecture:** Read ADR-0002
2. **Test locally:** Run `run_fixtures.ps1` on your machine
3. **Pick a Tier A feature:** See roadmap in [src/discovery/README.md](README.md)
4. **Write unit tests:** Create `tests/discovery/test_your_feature.py`
5. **Submit PR:** Reference ADR in commit message

---

**Questions?** See [copilot-log.md](../../docs/copilot-log.md) for architectural decisions and [lab-notes.md](../../docs/lab-notes.md) for what's been done.
