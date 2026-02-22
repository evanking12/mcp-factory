# Mac Compatibility

MCP Factory is **Windows-first** but was explicitly refactored to **not crash on Mac** — Windows-only features degrade gracefully to empty results with a log warning rather than errors.

## What's Hard-Gated to Windows

| Feature | Why Windows-Only | Behavior on Mac |
|---|---|---|
| PE/DLL/EXE binary analysis | `.dll`/`.exe` files only exist on Windows | No binaries to point at; irrelevant |
| COM Registry scan (`com_scan.py`) | Uses `winreg` module | `try: import winreg` → `except ImportError: return []` — silently skips |
| Type Library parsing (`tlb_analyzer.py`) | Uses `pythoncom` from `pywin32` | `try: import pythoncom` → `except: pythoncom = None` — silently skips |
| PDB debug symbol analysis (`pdb_analyzer.py`) | Uses `DbgHelp.dll` via ctypes | Explicit `if sys.platform != "win32": return []` — silently skips |
| .NET reflection (`dotnet_analyzer.py`) | Spawns `powershell` subprocess | Subprocess fails, returns empty |

`pywin32` is conditionally installed — `requirements.txt` specifies `pywin32>=306; sys_platform == 'win32'`, so `pip install` won't even attempt it on Mac.

## What Fully Works on Mac

| Feature | Analyzer | Notes |
|---|---|---|
| Python scripts (`.py`) | `script_analyzer.py` | Pure Python regex |
| Shell scripts (`.sh`) | `script_analyzer.py` | |
| JavaScript / TypeScript | `js_analyzer.py` | |
| SQL files | `sql_analyzer.py` | |
| PowerShell scripts (`.ps1`) | `script_analyzer.py` | Text parsing only, no execution |
| Batch / VBScript | `script_analyzer.py` | Text parsing only |
| OpenAPI specs (`.yaml`/`.json`) | `openapi_analyzer.py` | |
| WSDL / IDL / JNDI descriptors | respective analyzers | |
| JSON-RPC service descriptors | `jsonrpc` handler | |
| MCP JSON generation | `schema.py` | |
| `select_invocables.py` UI | `src/ui/` | |

## Practical Guidance for Mac

Mac teammates can use MCP Factory productively for the **script and protocol side** of the pipeline — the parts that generate MCP servers from source code and service descriptors. The binary analysis features (COM, PE exports, .NET reflection) return empty and log a warning rather than crashing.

The architecture split is: **discovery of Windows binaries happens on Windows; generation of MCP JSON from scripts and APIs works everywhere.**
