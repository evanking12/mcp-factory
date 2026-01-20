# csv_script.py - Advanced DLL Export Analyzer

A comprehensive Python 3 script that extracts DLL export information using `dumpbin /exports` and generates detailed analysis with multiple tiers of enrichment including header file parsing, documentation extraction, and C++ name demangling.

## Features

### Core Functionality
- Runs `dumpbin /exports` on any DLL file
- Generates raw dumpbin output text file
- Parses exports into structured CSV and Markdown reports
- Deduplicates export names automatically
- Handles missing tools and format quirks

### Advanced Analysis (Tiered Pipeline)

The script implements a tiered analysis approach, providing progressively richer information:

**Tier 1: Exports + Headers + Documentation**
- Full function signatures with return types and parameters
- Documentation comments extracted from headers
- References to documentation files
- Complete API information

**Tier 2: Exports + Headers**
- Function signatures with return types and parameters
- Header file locations with line numbers
- No documentation file scanning

**Tier 3: Exports + Demangle**
- C++ name demangling using `undname.exe`
- Basic export information
- Useful for C++ libraries

**Tier 4: Exports Only**
- Raw export names and ordinals
- Minimal processing
- Always succeeds

**Tier 5: Metadata Only**
- DLL file information (size, modified date)
- Export count
- Fallback when other tiers fail

## Requirements

- **Python 3.6 or later**
- **Windows operating system**
- **Visual Studio Build Tools** - Must be run from **Visual Studio x64 Native Tools Command Prompt** (or ensure `dumpbin.exe` is in PATH)
- **Optional:** `undname.exe` for C++ name demangling (included with Visual Studio)

## Installation

No installation required. Just download the script and run it from the Visual Studio command prompt.

## Usage

### Basic Usage - Exports Only

```powershell
python csv_script.py --dll C:\path\to\library.dll
```

### Full Analysis - With Headers and Documentation

```powershell
python csv_script.py --dll C:\path\to\libzstd.dll --headers C:\zstd\lib --docs C:\zstd\doc
```

### Specify Output Directory

```powershell
python csv_script.py --dll C:\path\to\library.dll --out C:\output\directory
```

### Reuse Existing Raw Export File

```powershell
python csv_script.py --exports-raw existing_exports_raw.txt --headers C:\include
```

### Custom Tool Paths

```powershell
python csv_script.py --dll library.dll --dumpbin "C:\Program Files\...\dumpbin.exe" --undname "C:\Program Files\...\undname.exe"
```

### Add Tag to Output Files

```powershell
python csv_script.py --dll library.dll --tag v1.0 --headers include
```

## Example: Analyzing libzstd.dll

Here's the exact command to perform a complete analysis of `libzstd.dll`:

```powershell
# Navigate to the script directory
cd C:\Users\evanw\Downloads\capstone_project\mcp-factory\src\scripts

# Full analysis with headers and documentation
python csv_script.py --dll "C:\vcpkg\packages\zstd_x64-windows\bin\libzstd.dll" --headers "C:\vcpkg\packages\zstd_x64-windows\include" --docs "C:\zstd\doc" --out "C:\zstd_analysis"

# Basic analysis without headers
python csv_script.py --dll "C:\vcpkg\packages\zstd_x64-windows\bin\libzstd.dll"

# Analysis with custom output directory
python csv_script.py --dll "C:\path\to\libzstd.dll" --headers "C:\path\to\zstd\include" --out "C:\my_analysis" --tag zstd_v1
```

### Expected Output Structure

The script generates multiple files in the output directory (default: `./mcp_dumpbin_out`):

```
mcp_dumpbin_out/
├── libzstd_exports_raw.txt          # Raw dumpbin output
├── libzstd_tier1_api.csv            # Tier 1: Full analysis CSV
├── libzstd_tier1_api.md             # Tier 1: Full analysis report
├── libzstd_tier2_api.csv            # Tier 2: Headers only CSV
├── libzstd_tier2_api.md             # Tier 2: Headers only report
├── libzstd_tier3_api.csv            # Tier 3: Demangled exports CSV
├── libzstd_tier3_api.md             # Tier 3: Demangled exports report
├── libzstd_tier4_api.csv            # Tier 4: Basic exports CSV
├── libzstd_tier4_api.md             # Tier 4: Basic exports report
├── libzstd_tier5_metadata.md        # Tier 5: DLL metadata
└── libzstd_tiers.md                 # Summary of all tiers
```

### Sample CSV Output (Tier 1)

```csv
Function,Ordinal,ReturnType,Parameters,Signature,DocComment,HeaderFile,Line,Demangled,DocFiles
ZSTD_compress,1,size_t,"void* dst, size_t dstCapacity, const void* src, size_t srcSize, int compressionLevel","size_t ZSTD_compress(void* dst, size_t dstCapacity, const void* src, size_t srcSize, int compressionLevel)","Simple API - Compress data in a single step",C:\zstd\lib\zstd.h,156,,C:\zstd\doc\zstd_manual.md
ZSTD_decompress,2,size_t,"void* dst, size_t dstCapacity, const void* src, size_t compressedSize","size_t ZSTD_decompress(void* dst, size_t dstCapacity, const void* src, size_t compressedSize)","Decompress compressed data",C:\zstd\lib\zstd.h,168,,C:\zstd\doc\zstd_manual.md
```

### Sample Markdown Report (Excerpt)

```markdown
# API Report: libzstd.dll

Generated: 2026-01-19 14:30:00

Total Exports: 145

## ZSTD_compress

**Ordinal:** 1

**Signature:** `size_t ZSTD_compress(void* dst, size_t dstCapacity, const void* src, size_t srcSize, int compressionLevel)`

**Header:** `C:\zstd\lib\zstd.h:156`

**Documentation:**

Simple API - Compress data in a single step
Compresses `src` content as a single zstd compressed frame into already allocated `dst`.
Returns compressed size written into `dst`, or an error code if it fails.

**Referenced in:**

- `C:\zstd\doc\zstd_manual.md`
- `C:\zstd\doc\README.md`

---
```

## Command-Line Arguments

### Required (one of)

| Argument | Description |
|----------|-------------|
| `--dll PATH` | Path to the DLL file to analyze |
| `--exports-raw PATH` | Path to existing raw dumpbin output (alternative to --dll) |

### Optional

| Argument | Default | Description |
|----------|---------|-------------|
| `--headers DIR` | _(none)_ | Root folder to search for header files (.h, .hpp, etc.) |
| `--docs DIR` | _(none)_ | Root folder to search for documentation files (.md, .txt, etc.) |
| `--out DIR` | `./mcp_dumpbin_out` | Output directory for generated files |
| `--tag STRING` | _(none)_ | Optional tag added to output filenames (e.g., `_v1`) |
| `--dumpbin PATH` | `dumpbin` | Path to dumpbin.exe or name on PATH |
| `--undname PATH` | `undname` | Path to undname.exe or name on PATH |
| `--no-demangle` | _(flag)_ | Skip C++ name demangling step |
| `--max-doc-hits N` | `2` | Maximum documentation file hits per function |

## CSV Output Columns

| Column | Description | Tier Availability |
|--------|-------------|-------------------|
| **Function** | Name of the exported function | All tiers |
| **Ordinal** | Export ordinal number | All tiers |
| **ReturnType** | Return type (from header) | Tier 1, 2 |
| **Parameters** | Function parameters (from header) | Tier 1, 2 |
| **Signature** | Complete function signature | Tier 1, 2 |
| **DocComment** | Documentation comment (from header) | Tier 1, 2 |
| **HeaderFile** | Source header file path | Tier 1, 2 |
| **Line** | Line number in header file | Tier 1, 2 |
| **Demangled** | Demangled C++ name | Tier 1, 2, 3 |
| **DocFiles** | Documentation file paths (semicolon-separated) | Tier 1 |

## How to Open Visual Studio x64 Native Tools Command Prompt

### Method 1: Start Menu
1. Press **Win + S** and search for "x64 Native Tools Command Prompt for VS"
2. Click the result to launch

### Method 2: From Any Terminal
```powershell
# Visual Studio 2022 Community
"C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat"

# Visual Studio 2022 Professional
"C:\Program Files\Microsoft Visual Studio\2022\Professional\VC\Auxiliary\Build\vcvars64.bat"

# Visual Studio 2022 Enterprise
"C:\Program Files\Microsoft Visual Studio\2022\Enterprise\VC\Auxiliary\Build\vcvars64.bat"
```

### Method 3: Developer PowerShell
1. Open "Developer PowerShell for VS 2022" from Start Menu
2. Already has all tools in PATH

## Advanced Features

### Header File Parsing

The script performs sophisticated header file analysis:

- **Prototype Extraction:** Finds function declarations and definitions
- **Comment Parsing:** Extracts Doxygen-style documentation (`///`, `/**`)
- **Parameter Parsing:** Handles complex parameter lists with nested parentheses
- **Return Type Cleaning:** Removes storage class specifiers and calling conventions
- **Comment Detection:** Avoids false matches in comments or preprocessor directives

### Documentation Scanning

When `--docs` is provided:

- Scans Markdown, text, reStructuredText, AsciiDoc, and Doxygen files
- Finds mentions of exported functions
- Links functions to their documentation
- Configurable hit limit per function

### C++ Name Demangling

When `undname.exe` is available:

- Automatically detects C++ mangled names (starting with `?`)
- Demangled names to human-readable form
- Helps identify C++ class methods and operators

### Intelligent Export Matching

For C++ exports:

- Tries original export name first
- Falls back to demangled name
- Extracts class method names from namespaces
- Handles overloaded functions

## Error Handling

The script gracefully handles:

- Missing DLL files → Clear error message
- dumpbin not in PATH → Helpful instructions
- Malformed dumpbin output → Continues with partial data
- Missing header/doc directories → Skips those tiers
- Duplicate export names → Automatic deduplication
- Empty export sections → Warning with graceful exit
- Forwarded exports → Handled correctly
- Timeout scenarios → 30-second timeout on commands

## Bug Fixes (from csv_script10.py)

### Fixed: check_dumpbin_available() ignores --dumpbin
- Now properly uses the `--dumpbin` argument when checking availability
- Prevents false "dumpbin not found" errors with custom paths

### Fixed: prints raw output path in --exports-raw mode
- Only prints raw output path when it was actually generated
- Cleaner output when reusing existing raw files

## Limitations

- **Export-Only Data:** `dumpbin /exports` provides only names and ordinals, not full signatures
- **Header Dependency:** Full analysis requires access to header files
- **Basic Demangling:** Uses `undname.exe`; may not handle all C++ mangling schemes
- **Comment Formats:** Best with Doxygen-style comments (`///`, `/**`)
- **Windows Only:** Requires Windows-specific tools (dumpbin, undname)
- **Single DLL:** Analyzes one DLL at a time (batch mode possible with scripting)

## Use Cases

### For MCP Server Development
- Generate function schemas for MCP tool definitions
- Extract parameter types and documentation
- Build safety wrappers with error handling notes
- Create JSON schemas from function signatures

### For API Documentation
- Generate comprehensive API reference from DLLs
- Cross-reference code and documentation
- Audit exported vs. documented functions
- Track API changes between versions

### For Reverse Engineering
- Understand undocumented DLLs
- Find function signatures in headers
- Demangle C++ exports
- Map exports to source code

### For Integration Projects
- FFI (Foreign Function Interface) bindings
- Dynamic library loading
- API compatibility checking
- Function availability testing

## Future Enhancements

Potential improvements:

- **PDB Parsing:** Extract full debug information from PDB files
- **Full Demangling:** Better C++ demangling support
- **JSON Output:** Structured JSON format for programmatic use
- **Schema Generation:** Auto-generate MCP tool schemas
- **Batch Mode:** Analyze multiple DLLs in one run
- **Dependency Analysis:** Track inter-DLL dependencies
- **Diff Mode:** Compare exports between DLL versions
- **Safety Analysis:** Detect thread safety, error codes, ownership patterns

## Troubleshooting

### "dumpbin not found in PATH"

**Solution:** Run from Visual Studio x64 Native Tools Command Prompt, or specify `--dumpbin` with full path.

### "No exports parsed"

**Possible causes:**
- DLL has no exports (is it a resource-only DLL?)
- Dumpbin output format changed
- DLL is corrupted

**Solution:** Check the raw output file for dumpbin errors.

### "Header root not found"

**Solution:** Verify the path specified in `--headers` exists and is accessible.

### No prototypes found in headers

**Possible causes:**
- Export names don't match header declarations
- Headers use macros or preprocessor directives
- Functions declared in private/internal headers

**Solution:** 
- Check if export names match function names in headers
- Try with demangled names for C++ exports
- Ensure all relevant headers are in the scan path

## License

See project LICENSE file.

## Contributing

This script is part of the mcp-factory project. For bugs or enhancements, please create an issue or pull request.

## Version History

- **v2.0** (csv_script.py): Tiered pipeline with header parsing and documentation extraction
- **v1.0** (csv_script10.py): Basic dumpbin export extraction with CSV output
