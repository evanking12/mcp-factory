# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-02-22

### Added
- **Interactive invocable selection UI** — `src/ui/select_invocables.py`: rich terminal table with confidence-based defaults (`guaranteed`+`high` on, `medium`+`low` off), toggle/range/filter commands, description hint highlighting (Section 2.b), writes `selected-invocables.json` for Section 4 consumption
- **Hybrid binary detection** — selection UI automatically detects multi-output binaries (e.g. `shell32.dll` produces both native exports and COM interfaces), merges them into one unified list with a `Source` column, announces the merge clearly
- **`src/ui/` module** — new package for user-facing entry points

### Changed
- **Flat invocable schema** — `Invocable.to_dict()` in `schema.py` now emits the clean LLM-ready contract: `name`, `kind`, `confidence`, `description`, `return_type`, `parameters[]`, `execution`. Removed pipeline-internal wrappers: `tool_id`, `ordinal`, `rva`, `confidence_factors`, `signature{}`, `documentation{}`, `evidence{}`, `mcp{}`, `metadata{}`
- **`parameters` promoted to flat list** — was a string inside `signature.parameters`; now a top-level list of `{name, type, required, description}` matching OpenAI/Anthropic function-calling spec
- **`confidence` added `guaranteed` level** — four levels now: `guaranteed` > `high` > `medium` > `low`; scoring is factor-first (data measured before label set)
- **`section4_select_tools.py`** — removed `schema_version` from required-key validation; reads flat `description` field; drops `schema_version` from output
- **`docs/schemas/discovery-output.schema.json`** — rewritten to match flat schema; removed `schema_version`, `tier`, `evidence`, `confidence_factors`, `signature{}`, `documentation{}`; added `return_type`, flat `parameters[]`, `execution{}`, `guaranteed` confidence level

### Fixed
- `_get_execution_metadata()` in `schema.py`: `dotnet` and `com` source types had duplicate `"method"` dict keys — Python silently discarded the first, losing `"dotnet_reflection"` / `"com_automation"`. Fixed to use explicit `method`/`function_name`/`type_name` keys
- `cli` source type fell through to `method: "unknown"` — now correctly emits `method: "subprocess"` with `executable_path` and `arg_style`

## [1.0.0] - 2026-01-20

### Added
- **Direct PE parsing** - Native PE header export extraction (optional dumpbin fallback)
- **Forwarded export resolution** - Maps export chains to real targets
- **Digital signature extraction** - Identifies signed/unsigned binaries and publishers
- **Confidence scoring** - Transparent reasoning for export invocability (Low/Medium/High)
- **Structured logging** - Production-ready logging with error handling
- **GitHub Actions CI** - Automated tests on Python 3.8, 3.10, 3.11 (Windows)
- **Data contract schema** - [docs/schemas/v1.0.json](docs/schemas/v1.0.json) for Section 4 integration
- **Test suite** - 5 fixture tests validating PE parsing + header matching on zstd.dll + sqlite3.dll

### Changed
- Refactored monolithic `csv_script.py` into 8 modular files (schema, classify, pe_parse, exports, headers_scan, docs_scan, com_scan, main)
- Python version requirement: 3.8+ (was 3.6+, now enforced via pyproject.toml)

### Fixed
- PE header parsing handles forwarded exports correctly
- Export deduplication preserves ordinal data
- Signature extraction works on both signed and unsigned binaries

## [0.1.0] - 2026-01-19

### Added
- Initial discovery prototype (Sections 2-3)
- DLL export extraction via dumpbin
- Header file prototype matching
- Tiered CSV/Markdown output (5 levels: full → metadata only)
- PowerShell automation (run_fixtures.ps1, setup-dev.ps1)
- Test fixtures (zstd.dll: 187 exports, sqlite3.dll: 294 exports)

---

## Versioning Policy

### Breaking Changes (Major Version)
- Changes to the JSON schema structure (field removal, type change, required field addition)
- Python version requirement increases (e.g., 3.8 → 3.10)
- Output format changes that break Section 4 parsing

### Non-Breaking Changes (Minor Version)
- New optional fields in JSON output
- New command-line options
- Performance improvements
- New analyzer modules (as long as existing output remains valid)

### Patches (Patch Version)
- Bug fixes
- Documentation updates
- Internal refactoring

**For Section 4 Teams:** Always pin to a major version (e.g., v1.x.x) to ensure compatibility. Breaking changes will increment the major version number.
