# Tranche 007: Proof Portal Closeout

## Objective

Regenerate the sponsor proof portal and close the campaign with a newer full
green Sponsor Demo E2E run.

## Required Work

- Update README, proof index, caveats, and final summary/report wording.
- Run focused workflows:
  - report-only
  - repo-ingestion proof
  - Windows GPT matrix
  - SOAP and SQL one-case GPT matrix checks if useful
- Run full `Sponsor Demo E2E`.
- Download the artifact and verify final summary fields.
- Write `CLOSEOUT.md` only after the final green run exists.

## Passing Criteria

- Latest full Sponsor Demo E2E is green.
- Artifact contains `final-summary.md`, `final-summary.json`,
  `sponsor-report.html`, GPT transcripts, Windows summaries, repo-ingestion
  summary, and requirement matrix.
- README and proof index point to the canonical run.
- Worktree is clean after commit and push.

## Writeback

Status: pending final green.

- Local report semantics now include runtime mode counts, runtime-backed cases,
  adapter-backed cases, transcript paths, and canonical run URL support.
- README, proof index, caveats, and manifest now state JSON-RPC/SOAP/SQL runtime
  support, REST validation, JNDI/RPC lightweight runtime proofs, and CORBA
  adapter-backed boundaries.
- Next gate is commit/push, focused workflows, full Sponsor Demo E2E, artifact
  inspection, `CLOSEOUT.md`, and canonical run link update.
