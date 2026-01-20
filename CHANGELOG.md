# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
