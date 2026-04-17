# Runtime Proof Expansion Campaign

This campaign turns the sponsor demo from a broad proof bundle into a stronger
runtime-verifiable evidence system without taking on deep arbitrary binary
semantic recovery.

The campaign operates sequentially by tranche. A tranche is not complete until
its focused tests, artifacts, and writeback prove the pass criteria. CI
artifacts, not chat memory, decide whether the next tranche can start.

Baseline before this campaign:

- Commit baseline: `73c8b80` or newer.
- Historical green fallback: Sponsor Demo E2E run `24542583216`.
- Required final state: a newer full green `Sponsor Demo E2E` run whose
  artifact contains `final-summary.md`, `final-summary.json`,
  `sponsor-report.html`, GPT transcripts, Windows summaries, repo-ingestion
  summaries, and a requirement matrix.

Out of scope:

- Ghidra stripped-binary recovery.
- Guaranteed semantic recovery for arbitrary undocumented DLL/EXE files.
- Remote DCOM activation.
- Production CORBA ORB/IIOP unless explicitly implemented and verified.

