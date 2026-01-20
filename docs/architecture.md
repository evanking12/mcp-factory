# Architecture

## Goal
Generate an MCP server/tool schema from existing binaries (DLL/EXE/CLI/repo) by discovering invocable surfaces, normalizing them, enriching metadata, and generating deployable MCP components.

## Pipeline (high level)
1. Acquire target (file upload or installed path) + free-text hints
2. Discover invocable surfaces (exports/help/registry/etc.)
3. Normalize into `inventory.json` (provenance + confidence)
4. User selects subset -> `selection.json`
5. Generate MCP tools/server + deploy verification instance
6. Verify via chat UI + downloadable outputs

## Components
- Discovery: DLL exports parser, CLI help scraper, registry inspector (future)
- Schema: inventory/selection/tool contracts
- Generator: MCP tool definitions + server wrapper
- Verification UI: chat interface + output download

## Open questions
- Primary demo target(s) preferred by sponsor
- Human-in-the-loop tolerance vs fully automatic wrappers
- Sandboxing requirements for invoking binaries
