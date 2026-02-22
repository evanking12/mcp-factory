# Sections 2–3: Binary Discovery & Confidence Analysis

**Status:** ✅ Complete — Full Spec Coverage (29/29 demo targets)

## Source Type Coverage ✅

| Source | Analyzer | Invocable kinds |
|--------|----------|-----------------|
| PE native DLL/EXE | `exports.py` | `export` |
| .NET assemblies | `pe_parse.py` | `dotnet` |
| COM / Type Library | `com_scan.py` | `com` |
| CLI tools (EXE argv) | `cli_analyzer.py` | `cli` |
| RPC interfaces | `rpc_scan.py` | `rpc` |
| SQL files | `sql_analyzer.py` | `sql_procedure`, `sql_function`, `sql_view`, `sql_table`, `sql_trigger` |
| Python | `script_analyzer.py` | `python_function` |
| PowerShell | `script_analyzer.py` | `powershell_function` |
| Shell / Bash | `script_analyzer.py` | `shell_function` |
| Batch / CMD | `script_analyzer.py` | `batch_label` |
| VBScript | `script_analyzer.py` | `vbscript_function`, `vbscript_sub` |
| Ruby | `script_analyzer.py` | `ruby_method` |
| PHP | `script_analyzer.py` | `php_function` |
| JavaScript | `js_analyzer.py` | `js_function`, `js_arrow`, `js_cli` |
| TypeScript | `js_analyzer.py` | `ts_method` |
| OpenAPI 3.x / Swagger 2.x | `openapi_analyzer.py` | `openapi_operation` |
| JSON-RPC 2.0 | `openapi_analyzer.py` | `jsonrpc_method` |
| SOAP / WSDL 1.1 | `wsdl_analyzer.py` | `soap_operation` |
| CORBA IDL | `idl_analyzer.py` | `corba_method` |
| JNDI config | `jndi_analyzer.py` | `jndi_datasource`, `jndi_jms`, `jndi_rmi`, `jndi_ldap`, `jndi_mail`, `jndi_ejb`, `jndi_env_entry`, `jndi_lookup` |
| PDB debug symbols | `pdb_analyzer.py` | `pdb_symbol` |
| **Directory (installed instance)** | `main.py` (`analyze_directory`) | all kinds (aggregated) |

## Schema Uniformity ✅

Every source type serializes through `schema.Invocable.to_mcp_dict()` producing identical JSON structure:
- Top-level keys: `metadata`, `invocables`, `summary`
- Per-invocable keys: `name`, `kind`, `confidence`, `description`, `return_type`, `parameters`, `execution`

## Execution Metadata ✅

Every invocable carries a complete `execution` block so an LLM can call any invocable without additional lookup:

| Method | Used by |
|--------|---------|
| `http_request` | OpenAPI operations |
| `jsonrpc` | JSON-RPC 2.0 methods |
| `soap` | SOAP/WSDL operations |
| `corba_iiop` | CORBA IDL methods |
| `jndi_lookup` | JNDI bindings |
| `dll_import` (pdb) | PDB symbols |
| `dll_import` | PE native exports |
| `dotnet_reflection` | .NET methods |
| `com_dispatch` | COM objects |
| `subprocess` | CLI tools |
| `python_subprocess` | Python functions |
| `powershell` | PowerShell functions |
| `bash` | Shell functions |
| `cmd_call` | Batch labels |
| `cscript` | VBScript subs/functions |
| `ruby`, `php`, `node`, `ts-node` | Respective script runtimes |
| `sql_exec` | SQL stored procs, views, tables |

## §3 Tool Selection ✅

`scripts/select_invocables.py` — lists all discovered invocables, pre-selects guaranteed/high confidence, allows user deselection, writes `selected-invocables.json` for §4 hand-off.

## Artifact Hygiene (ADR-0005) ✅

- No empty JSON files — every output file contains usable invocables
- Param names are real names, not type annotations or positional indices
- Descriptions are actual sentences, not separator lines or parameter tables
- Execution method is always a concrete, callable method string

## §2.a Directory Walk ✅

`main.py` (`analyze_directory`) — when `--target` is a directory, rglobs for all recognized
extensions, classifies each file, runs the appropriate analyzer, and writes individual
`*_mcp.json` files per sub-file plus an aggregate `<dir>_scan_mcp.json` that merges all
invocables.  `select_invocables.py --target <dir>` passes the directory through to `main.py`
and loads the aggregate for the interactive selection UI.

## Demo ✅

`scripts/demo_all_capabilities.py` — 29/29 targets succeed across all source types (10 sections,
including Section 10 directory scan).

`scripts/demo_legacy_protocols.py` — 6/6 targets succeed (dedicated regression suite for spec-gap analyzers).

## Test Results

| Metric | Value |
|--------|-------|
| Demo pass rate | 100% (29/29 targets) |
| Schema key uniformity | 100% (22 source types + directory, identical structure) |
| Header match rate (zstd) | 98.4% |
| Header match rate (sqlite3) | 95.9% |

## What's Not Supported Yet ❌

- **Deep .NET type graph**: Full reflection beyond method signatures (generic types, nested classes)

## Known Limitations

- **Obfuscated binaries**: Export names that are GUIDs or ordinals only get `confidence: low`
- **Runtime-only resolution**: Functions resolved via `LoadLibrary` at runtime are not static exports
- **PowerShell untyped params**: `$Name` without a `[Type]` decorator shows as `arg0`
