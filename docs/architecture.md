# Architecture

## Goal
Generate an MCP server/tool schema from existing binaries (DLL/EXE/CLI/repo) by discovering invocable surfaces, normalizing them, enriching metadata, and generating deployable MCP components.

## Pipeline (high level)
1. Acquire target (file upload or installed path) + free-text hints
2. Discover invocable surfaces (exports/help/registry/etc.)
3. **Score confidence** in each surface (6-factor analysis)
4. Normalize into `inventory.json` (provenance + confidence)
5. User selects subset -> `selection.json`
6. Generate MCP tools/server + deploy verification instance
7. Verify via chat UI + downloadable outputs

## Components

### Discovery Layer
- **DLL Export Analysis** (Sections 2)
  - `pe_parse.py`: dumpbin wrapper + export parser
  - `exports.py`: Demangling, forwarding, deduplication
  - `headers_scan.py`: Prototype extraction from C/C++ headers (98% match rate)
  - Outputs: CSV (Tier 2), JSON (Tier 3), Markdown (Tier 4), Metadata (Tier 5)
  
- **.NET Reflection Analysis** (Section 3, future)
  - Type discovery via System.Reflection
  - Public method extraction
  - Signature normalization
  
- **CLI Help Scraper** (future)
  - Parse --help / -h output
  - Extract subcommands and parameters

### Quality & Confidence Layer
- **Confidence Scoring** (new, 2026-01-21)
  - `score_confidence(export, matches, is_signed, forwarded) -> (level, reasons)`
  - 6 factors: header_match, doc_comment, signature_complete, parameter_count, return_type, non_forwarded
  - Tiers: HIGH (≥6), MEDIUM (≥4), LOW (<4)
  - `generate_confidence_summary()`: Color-coded output (RED/YELLOW/GREEN) + suggestions
  - Enables downstream prioritization (Section 4 auto-wraps HIGH confidence exports)

### Setup & Automation Layer
- **Boot Checks** (new, 2026-01-21)
  - Pre-flight validation: repo root, Python 3.8+, Git, PowerShell 5.1+
  - Indicators: [+] (pass, green), [-] (fail, red)
  - Fail-fast on missing prerequisites
  
- **Frictionless Deployment** (scripts/)
  - `scripts/setup-dev.ps1`: One-command setup with auto-detection
  - `scripts/run_fixtures.ps1`: Robust path resolution (3-method fallback), vcpkg bootstrap
  - Auto-detects dumpbin, Visual Studio, vcpkg
  - Tested on clean machines (no pre-installed tools)
  
### Schema & Output
- `schema.py`: Invocable dataclass (name, ordinal, signature, confidence, doc)
  - Writers: CSV, JSON, Markdown
  - Supports 5-tier output (exports only → metadata-rich)

### Integration Points
- **Section 4 (MCP Generation)**: Consumes confidence metadata
  - HIGH confidence → auto-generate MCP tool definitions
  - MEDIUM confidence → auto-generate + flag for review
  - LOW confidence → skip or require manual spec
  
- **Future LLM Integration**: Confidence metadata helps Claude/GPT prioritize trustworthy exports
- **Section 5 (UI)**: Displays confidence breakdown, allows filtering by confidence tier

## Design Decisions

| Decision | Rationale | Reference |
|----------|-----------|-----------|
| Modular 8-module architecture | Enable team parallelization, testability, feature expansion | ADR-0002 |
| Confidence scoring with color | Transparency + quality signal + Section 4 prioritization | ADR-0003 |
| Frictionless one-command setup | Reproducibility, professional signal, user empathy | ADR-0003 |
| Header matching for signatures | 98% accuracy enables high-confidence auto-wrapping | Iteration 1 results |
| 5-tier output model | Gradual enrichment; supports various downstream needs | MVP analysis |

## Open Questions
- How to handle confidence in .NET reflection (Section 3)?
- Should users override confidence scores?
- Integration with external documentation sources?
- Semantic analysis (infer safety from function names)?

