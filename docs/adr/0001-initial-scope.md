# ADR 0001 — Initial Scope and MVP Targets

## Status
Accepted

## Context
We need a first demo that takes an existing binary and produces an invocable inventory that can later generate an MCP server.

## Decision
Iteration 1 focuses on native DLL export discovery (dumpbin /exports → CSV/JSON inventory). CLI help scraping is next.

## Consequences
- Provides quick, real artifacts for sponsor review
- Full signature inference and safe invocation require enrichment (PDB/docs/tracing) in later iterations
