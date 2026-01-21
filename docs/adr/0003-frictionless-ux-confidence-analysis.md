# ADR 0003: Frictionless User Experience & Confidence Analysis

**Date:** 2026-01-21  
**Status:** ACCEPTED  
**Owner:** Evan King  
**Relates to:** Sections 2-3 (Discovery), Section 4 (MCP Generation)

---

## Problem Statement

1. **Deployment Friction:** Users needed to:
   - Manually install vcpkg
   - Find Visual Studio / dumpbin.exe
   - Navigate complex prerequisite setup
   - Trust that analysis output is reliable

2. **Quality Uncertainty:** DLL export analysis produces variable-quality results:
   - Some exports have full signatures (high confidence)
   - Some have only names (medium confidence)
   - Some are forwarded/unresolvable (low confidence)
   - No way to signal confidence to downstream consumers (Section 4, LLMs, users)

3. **Team Efficiency:** Section 4 needs to know which exports are trustworthy enough to generate full MCP tool definitions vs. requiring manual verification.

---

## Decision

Implement two complementary patterns:

### 1. Frictionless Deployment (One-Command Setup)
- Auto-detect vcpkg, dumpbin, Python, Git
- Bootstrap vcpkg from GitHub if missing
- Validate prerequisites with [+]/[-] indicators
- Complete setup in 30-45 seconds on any Windows machine
- Achieved via: `scripts/setup-dev.ps1` (boot checks) + `scripts/run_fixtures.ps1` (auto-detection)

### 2. Confidence Analysis with Color-Coded Output
- Score each export on 6 factors: header_match, doc_comment, signature_complete, parameter_count, return_type, non_forwarded
- Assign confidence level: HIGH (≥6 factors), MEDIUM (≥4 factors), LOW (<4 factors)
- Print color-coded summary (RED/YELLOW/GREEN) to terminal
- Include sample exports per confidence level + improvement suggestions
- Emit to both terminal + structured file (`*_confidence_summary.txt`)

---

## Rationale

### Why Frictionless UX Matters

**Professional Signal:** Most capstone projects require complex setup. One-command reproducible deployment on clean machines signals:
- Thoughtful engineering (dependency management, error handling)
- User empathy (removal of friction)
- Confidence in quality (willing to be tested immediately)

**Real-World Relevance:** Production tools are frictionless:
- Docker: `docker run`
- Node.js tools: `npm install -g && tool`
- Python tools: `pip install && tool`

Students who build frictionless tools stand out in interviews.

**Trust Building:** Microsoft sees:
1. One command
2. Dependencies auto-detect and bootstrap
3. Results in 30 seconds
4. Output is structured and professional

→ "This person understands real engineering."

### Why Confidence Scoring Matters

**For Section 4 (MCP Generation):**
- HIGH confidence exports → auto-generate full MCP tool definitions
- MEDIUM confidence → use generated definitions but flag for review
- LOW confidence → skip or require manual specification
- Prevents generating MCP tools for untrustworthy exports

**For LLMs (Future):**
- Confidence metadata helps Claude/GPT know which tools to trust
- "This export is HIGH confidence (full signature + header match + doc)"
- "This export is LOW confidence (name only, no header match)"

**For Users:**
- Transparency about analysis quality
- Shows roadmap to improve (e.g., "Provide headers for 100% match")
- Demonstrates analytical rigor (not just "we found 187 exports")

**Specificity = Credibility:**
Instead of: "We analyze DLLs"  
Say: "187 exports, 8 HIGH confidence (4.3%), 176 MEDIUM (94.1%), 3 LOW (1.6%), 98.4% header match rate"

→ "This is rigorous analysis."

---

## Alternatives Considered

### 1. Skip Confidence Scoring
**Rejected.** Why:
- No way to distinguish high-quality vs. low-quality exports
- Section 4 can't prioritize which exports to wrap
- No signal of analysis rigor to Microsoft
- Leaves quality assessment to downstream (inefficient)

### 2. Static Confidence (Always "Good" or "Requires Headers")
**Rejected.** Why:
- Binary classification too coarse
- Can't adapt to different DLL characteristics
- No room to improve confidence (no "better if you provide X")
- Inflexible for future enhancements

### 3. Confidence Without Color/Terminal Output
**Rejected.** Why:
- Color makes analysis results immediately visible + memorable
- Terminal output in meeting/demo is immediate feedback
- Color (RED/YELLOW/GREEN) is universally understood
- Structured output alone is harder to assess at a glance

---

## Implementation

### Boot Checks Pattern (`setup-dev.ps1`)

```powershell
function Write-Check {
    param([string]$Message, [bool]$Success = $true)
    if ($Success) {
        Write-Host "  [+] $Message" -ForegroundColor Green
    } else {
        Write-Host "  [−] $Message" -ForegroundColor Red
    }
}

# Validation: repo root, Python, Git, PowerShell
```

**Characteristics:**
- ASCII indicators [+]/[-] (terminal-compatible, no encoding issues)
- Professional "Setup" banner with visual hierarchy
- Early error detection (fail fast if prereqs missing)
- Validation output separate from analysis output (clean stdout)

### Confidence Analysis (`main.py`)

```python
def score_confidence(export: Invocable, matches: dict, 
                    is_signed: bool, forwarded_resolved: bool) -> tuple:
    """Score confidence in export invocability."""
    reasons = []
    points = 0
    
    # 6 factors
    if matches.get('header_match'): points += 1
    if matches.get('doc_comment'): points += 1
    if matches.get('signature_complete'): points += 1
    if matches.get('parameter_count'): points += 1
    if matches.get('return_type'): points += 1
    if not is_forwarded_export: points += 1
    
    # Thresholds
    if points >= 6: confidence = 'high'
    elif points >= 4: confidence = 'medium'
    else: confidence = 'low'
    
    return confidence, reasons
```

**Terminal Output:**
```
============================================================
CONFIDENCE ANALYSIS SUMMARY
============================================================

DLL: zstd.dll
Total Exports: 187
Analysis Date: 2026-01-21

CONFIDENCE BREAKDOWN
------------------------------------------------------------
LOW     Confidence:   3 exports (  1.6%)
MEDIUM  Confidence: 176 exports ( 94.1%)
HIGH    Confidence:   8 exports (  4.3%)

CONFIDENCE FACTORS (by frequency)
------------------------------------------------------------
...
```

**File Output:** `*_confidence_summary_*.txt` with:
- Summary statistics
- Sample exports per confidence level
- Improvement suggestions

---

## Integration Points

### Section 4 (MCP Generation)
- Consume confidence metadata from `*_confidence_summary.txt`
- HIGH confidence → auto-wrap as MCP tool (minimal review)
- MEDIUM confidence → auto-wrap + flag for review
- LOW confidence → skip or require manual spec

### Future Enhancements
- Semantic analysis (infer safety from function names)
- Type inference from signatures
- External documentation sources (GitHub, docs.rs, etc.)
- User-provided trust overrides

---

## Verification

### Fresh Machine Tests
| Machine | OS | VS | vcpkg | Python | Result | Time |
|---------|----|----|-------|--------|--------|------|
| Dev | Win10 | 2022 Community | No | Yes | ✓ | 35s |
| Test 1 | Win11 | 2022 Community | No | Yes | ✓ | 42s |

### Output Quality
| DLL | Total | HIGH | MEDIUM | LOW | Header Match |
|-----|-------|------|--------|-----|--------------|
| zstd.dll | 187 | 8 | 176 | 3 | 98.4% |
| sqlite3.dll | 294 | 8 | 274 | 12 | 95.9% |

### Terminal Output
- Color-coded output renders correctly in Windows Terminal ✓
- ASCII indicators display on all terminal emulators ✓
- No encoding corruption ✓
- Boot checks display before analysis (clear phase separation) ✓

---

## Consequences

### Positive
- ✅ Reproducible on clean Windows machines
- ✅ Professional first impression (frictionless deployment)
- ✅ Transparent about analysis quality
- ✅ Enables intelligent prioritization in Section 4
- ✅ Sets precedent for frictionless UX in future sections

### Costs
- +35 lines of Python (confidence scoring)
- +25 lines of PowerShell (robust path resolution)
- +100 lines of setup-dev.ps1 (boot checks + auto-detection)
- Small runtime overhead (~5% longer analysis, negligible)

### Open Questions
- Should confidence be auto-tuned based on DLL characteristics?
- Should users be able to override confidence scores?
- How to handle confidence in .NET reflection (Section 3)?

---

## References
- **Previous ADR:** ADR-0002 (Modular Analyzer Architecture)
- **Related Code:** 
  - `scripts/setup-dev.ps1` (boot checks + auto-detection)
  - `src/discovery/main.py:score_confidence()` + `generate_confidence_summary()`
  - `README.md` (one-command setup + confidence examples)
- **Commits:** aff6871, a1fec1e, 3a3c320-6eef026 (confidence + setup fixes)
