# GitHub Actions Proof Hardening

This campaign hardens the sponsor proof pipeline so the demo is verified by
GitHub Actions, not just by manual UI testing.

Current goal:

- Verify deployed UI and deployed pipeline smoke paths.
- Validate sponsor proof artifacts and GPT transcripts.
- Guard runtime modes against silent downgrades.
- Guard sponsor caveats against overclaiming.
- Record operational proof and failure diagnosis artifacts.

Baseline proof:

- Fallback canonical green run: `24568108685`
- Stronger current full proof: `24578415657`

No Ghidra or undocumented binary recovery work belongs in this campaign.

