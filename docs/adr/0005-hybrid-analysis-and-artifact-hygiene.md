# ADR 0005: Hybrid Analysis Routing & Strict Artifact Hygiene

**Date:** 2026-01-27  
**Status:** ACCEPTED  
**Owner:** Evan King  
**Relates to:** Sections 2-3 (Discovery), Section 4 (MCP Generation)

---

## Problem Statement

1.  **Siloed Analysis Limits:** Previous architecture (ADR-0002) treated files as single-type entities (DLL vs EXE vs .NET). This failed for key Windows system files:
    *   `shell32.dll`: Is both a **COM Server** and a **Native DLL**. Analyzing only one ignored half its capabilities.
    *   `notepad.exe`: Is a **GUI App**, but might expose registered **COM** interfaces.
2.  **Artifact Noise ("The Empty File Problem"):** The pipeline previously generated "Safe/Empty" outputs for every analysis attempt. Running COM analysis on `kernel32.dll` (pure native) produced a valid but empty `kernel32_com_objects_mcp.json`.
    *   **Impact:** Downstream MCP generators (Section 4) would ingest these files and potentially create "Ghost Tools" or clutter the agent's context with empty servers.
3.  **Legacy Redundancy:** The pipeline was generating dual outputs for .NET (`*.json` and `*_mcp.json`) to support older tooling. This doubled storage/IO and confused consumers about the "Source of Truth".

## Decision

We have implemented a **Hybrid Routing Engine** with **Strict Artifact Hygiene**.

### 1. Hybrid Routing Logic (Fall-through Analysis)
We moved from a "Switch Case" router to a "Capabilities" router in `src/discovery/main.py`:
*   **Sequential Dispatch:** A file classification (e.g., `COM_OBJECT`) is no longer a terminal state.
*   **Fall-through:** After COM analysis completes, the router checks if the file *also* qualifies for Native Export analysis (is it a PE file?).
*   **Result:** `shell32.dll` now triggers *both* `analyze_com_object` and `analyze_native_dll`, producing two distinct, correct MCP artifacts.

### 2. Strict Artifact Hygiene (Suppression Policy)
We inverted the output logic: **Silence is Golden.**
*   **Previous**: "Try analysis -> Object count 0 -> Write empty JSON 'success'."
*   **New**: "Try analysis -> Object count 0 -> **Abort & Log**. Write nothing."
*   **Rationale**: The absence of an artifact now meaningfully signals "Feature Not Present".
*   **Benefit**: Section 4 can blindly ingest `output/*.json`. If a file exists, it contains invocable tools.

### 3. Deprecation of Legacy Formats
*   Removed generation of non-MCP `_dotnet_methods.json`.
*   Standardized solely on `*_mcp.json` schema v2.0.0 (from ADR-0004).

## Rationale

### Why "Hybrid" is better than "Batch"
Old ADRs (0004) focused on **Batch Validation** (processing 400+ files fast). While valuable for stability, it missed *functional correctness*. A batch run that says "Pass" for `shell32.dll` (because it successfully found 0 exports in COM mode) provides false confidence.
*   **Hybrid Analysis** prioritizes **Completeness**: It ensures we don't miss hidden surfaces in complex system binaries.

### Why Delete Empty Files?
AI Agents act on context window availability. Flooding the context with "Kernel32 has 0 COM objects" is worse than useless—it's distracting. By enforcing **Strict Hygiene**, we ensure the agent is only presented with *actionable* tools.

## Consequences

### Positive
*   **Higher Fidelity**: We accurately map the "Multi-paradigm" nature of Windows binaries.
*   **Clean Hand-off**: Section 4 no longer needs to filter invalid/empty JSONs.
*   **reduced IO**: We stop writing thousands of empty files during a full system scan.

### Negative
*   **Complexity**: `main.py` routing logic is more complex than a simple dispatch table.
*   **Validation**: Tests must now check for *file absence* as a success condition (e.g., "Verify kernel32 has NO com_objects.json").

## Verification
*   **Script**: `scripts/validate_features.py`
*   **Metric**: "Noise" check (ensure `kernel32` has native JSON but *no* COM JSON).
*   **Result**: 11/11 tests pass, accurately distinguishing between pure-native, pure-COM, and hybrid files.
