# Dynamic Campaign: Sponsor Pushback Hardening

## Governing Contract

This campaign may act only on repository files, CI artifacts, and explicit
user-provided paths. It must not claim production legacy runtimes where the
proof is adapter-backed.

## Tranches

1. Caveat and proof index docs.
2. JSON-RPC 2.0 hosted runtime strictness.
3. Repo ingestion fixture and GPT proof.
4. Windows GPT tool-result-observed proof matrix.
5. Workflow wiring and final report sections.
6. Operational closeout with green/focused runs.

## Passing Criteria

- Baseline report-only rendering from run `24542583216` still passes.
- JSON-RPC success and error envelopes are tested.
- Repo fixture discovery finds multiple invocables and GPT calls the selected
  repo-derived tool with a sentinel result.
- Windows GPT matrix produces one generated tool-call transcript per target.
- README, proof index, and caveat docs explain artifact interpretation.
