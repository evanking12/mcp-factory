# GitHub Actions Proof Hardening

## Campaign Start Packet

- `wider_goal`: make the sponsor demo proof pipeline hard to fake, regress, or
  misread.
- `current_frontier`: lightweight deployed smoke checks plus artifact integrity
  validation for the existing sponsor proof bundle.
- `stop_gate`: focused hardening workflows pass, then a full Sponsor Demo E2E
  run passes and `sponsor-proof-integrity.yml` validates that run.
- `dominant_blocker`: current proof is strong, but deployment health, transcript
  integrity, runtime-mode downgrades, and caveat wording are not checked by a
  single lightweight readiness gate.
- `expected_delivery_or_proving_target`: GitHub Actions workflows
  `demo-readiness.yml`, `deployed-provider-smoke.yml`, and
  `sponsor-proof-integrity.yml`, plus new `ci_verify.py` commands.
- `delegation_authorization`: absent for this implementation turn; work kept
  local.
- `operator_constraints`:
  - `time_budget`: keep new workflows light; do not start the Windows bridge VM
    or call GPT from readiness checks.
  - `merge_or_push_expectation`: commit/push after local tests and campaign
    writeback are current.
  - `allowed_risk_level`: low; add guards without weakening current sponsor
    proof semantics.
- `required_outputs`: campaign files, active prompt, tranche summaries,
  evaluations, workflow artifacts, failure diagnosis, and closeout after final
  proof.

## Tranches

1. `001-deployed-smoke-gates` (`bounded_fix`): add deployed UI and provider
   matrix smoke commands.
2. `002-demo-readiness-workflow` (`bounded_fix`): add a lightweight readiness
   workflow with scheduled/manual triggers.
3. `003-artifact-transcript-integrity` (`bounded_fix`): validate final artifact
   completeness, final-summary schema, and transcript integrity.
4. `004-runtime-downgrade-and-caveat-guards` (`bounded_fix`): fail on runtime
   downgrades or overclaiming.
5. `005-operational-resilience` (`bounded_fix`): record Azure operational
   posture and failure classification artifacts.
6. `006-final-proof-hardening-closeout` (`authoritative_validation`): run
   focused hardening workflows, full Sponsor Demo E2E, proof integrity, and
   closeout.

## Campaign Log

- Initialized campaign from imported dynamic prompt doctrine.
- Added local verifier commands and focused tests.
- Added GitHub Actions workflows for readiness, provider smoke, and proof
  integrity.
- Next evidence branch: dispatch focused workflows and record run URLs.

