# Sections 2–3: Binary Discovery & Confidence Analysis

**Status:** ✅ Complete (Production Hardened)

## What's Complete ✅
- **Hybrid Analysis Engine**: Capability-based routing (`shell32.dll` -> COM + Native).
- **5-Tier Discovery**:
  - Tier 1: Exports + Headers + Docs (98% match on zstd)
  - Tier 2: Exports + Headers
  - Tier 3: Exports + Demangling
  - Tier 4: Exports Only
  - Tier 5: Metadata
- **Confidence Scoring**: 6-factor analysis (High/Medium/Low) with color-coded confidence summaries.
- **Strict Artifact Hygiene**:
  - Valid MCP JSON v2.0 (`*_mcp.json`)
  - No empty "ghost" files (Noise suppression)
  - No legacy formats (Redundancy removal)
- **Validation Suite**: 11/11 Passing on `scripts/validate_features.py`.

## In Progress 🚀
- **Section 4 Hand-off**: JSON schemas are stable (ADR-0004).
- **.NET Reflection**: Currently supported via `pe_parse.py` (Tier 4), deeper reflection planned.

## What's Not Supported Yet ❌
- **Deep .NET Reflection**: Full type graph for managed DLLs (currently extraction only).
- **PDB Parsing**: Program Database symbols not yet integrated.

## Test Results
| Metric | Value |
|--------|-------|
| Validation Pass Rate | 100% (11/11 system files) |
| Header Match Rate (zstd) | 98.4% |
| Header Match Rate (sqlite3)| 95.9% |
| Anomaly Scan | 0 Errors |

## Known Limitations
- **Obfuscated Binaries**: Headers cannot match if export names are obfuscated.
- **Runtime-only Features**: Functions resolved purely via `LoadLibrary` inside the app are not static exports.

## Next Iteration Scope
- **Interactive UI (Section 5)**: Allow users to deselect Low confidence exports.
- **Azure Deployment (Section 6)**: Containerizing the generated MCP server.
